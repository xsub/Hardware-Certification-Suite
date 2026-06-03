from __future__ import annotations

import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from rich.console import Console

from hcs.config import build_sandbox_paths
from hcs.runner import (
    RESULT_RE,
    UNSUPPORTED_RE,
    CertificationRunner,
    RunnerOptions,
    StepResult,
    ansible_subprocess_env,
    derive_status,
    parse_recap_line,
    run_status,
)


def recap(**counters: int) -> dict[str, dict[str, int]]:
    base = {
        "ok": 1,
        "changed": 0,
        "unreachable": 0,
        "failed": 0,
        "skipped": 0,
        "rescued": 0,
        "ignored": 0,
    }
    base.update(counters)
    return {"sut": base}


def step(status: str) -> StepResult:
    return StepResult(
        step=1,
        pass_index=1,
        pass_count=1,
        test_id="example",
        display_name="Example",
        status=status,
        status_reason="ok",
        return_code=0,
        started_at="2026-06-01T00:00:00Z",
        finished_at="2026-06-01T00:00:01Z",
        duration_seconds=1.0,
        command=[],
        artifacts=[],
        ansible_recap={},
    )


class RunnerStatusTests(unittest.TestCase):
    def test_run_status_marks_unsupported_as_warning(self) -> None:
        self.assertEqual(run_status([step("passed"), step("unsupported")]), "passed_with_warnings")

    def test_run_status_failed_wins(self) -> None:
        self.assertEqual(run_status([step("unsupported"), step("failed")]), "failed")

    def test_parse_recap_line(self) -> None:
        parsed = parse_recap_line(
            "127.0.0.1 : ok=8 changed=3 unreachable=0 failed=0 skipped=1 rescued=0 ignored=0"
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        host, stats = parsed
        self.assertEqual(host, "127.0.0.1")
        self.assertEqual(stats["ok"], 8)
        self.assertEqual(stats["skipped"], 1)

    def test_unsupported_marker_can_be_seen_in_ansible_debug_output(self) -> None:
        match = UNSUPPORTED_RE.search('    "msg": "HCS_UNSUPPORTED: nvidia-smi not found"')

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group("reason"), "nvidia-smi not found")


class DeriveStatusTests(unittest.TestCase):
    def test_explicit_pass_overrides_tolerated_ignored(self) -> None:
        status, _ = derive_status(
            return_code=0,
            result_status="pass",
            result_reason=None,
            unsupported_reason=None,
            recap=recap(ignored=1),
        )
        self.assertEqual(status, "passed")

    def test_explicit_fail_overrides_zero_return_code(self) -> None:
        status, reason = derive_status(
            return_code=0,
            result_status="fail",
            result_reason="thermal trip",
            unsupported_reason=None,
            recap=recap(),
        )
        self.assertEqual(status, "failed")
        self.assertEqual(reason, "thermal trip")

    def test_nonzero_return_code_overrides_explicit_pass(self) -> None:
        status, _ = derive_status(
            return_code=2,
            result_status="pass",
            result_reason=None,
            unsupported_reason=None,
            recap=recap(),
        )
        self.assertEqual(status, "failed")

    def test_unsupported_marker_yields_warning(self) -> None:
        status, reason = derive_status(
            return_code=0,
            result_status=None,
            result_reason=None,
            unsupported_reason="nvidia-smi not found",
            recap=recap(),
        )
        self.assertEqual(status, "unsupported")
        self.assertEqual(reason, "nvidia-smi not found")

    def test_recap_failure_without_markers(self) -> None:
        status, _ = derive_status(
            return_code=0,
            result_status=None,
            result_reason=None,
            unsupported_reason=None,
            recap=recap(failed=1),
        )
        self.assertEqual(status, "failed")

    def test_clean_run_passes(self) -> None:
        status, reason = derive_status(
            return_code=0,
            result_status=None,
            result_reason=None,
            unsupported_reason=None,
            recap=recap(),
        )
        self.assertEqual(status, "passed")
        self.assertEqual(reason, "ok")


class ResultMarkerTests(unittest.TestCase):
    def test_parses_status_and_reason_from_debug_json(self) -> None:
        match = RESULT_RE.search('    "msg": "HCS_RESULT: fail disk SMART errors"')

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group("status"), "fail")
        self.assertEqual(match.group("reason").strip(), "disk SMART errors")

    def test_bare_pass_has_empty_reason(self) -> None:
        match = RESULT_RE.search("HCS_RESULT: pass")

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group("status"), "pass")
        self.assertEqual(match.group("reason").strip(), "")


def make_runner(tmp: str) -> CertificationRunner:
    paths = build_sandbox_paths(
        config={},
        profile="check",
        base_dir=Path(tmp),
        sandbox_dir=None,
        run_id="test",
    )
    options = RunnerOptions(
        preset_name=None,
        profile="check",
        inventory="127.0.0.1,",
        connection="local",
        playbook=Path("automated.yml"),
        paths=paths,
        extra_vars={},
        selected_tests=("hw_detection",),
        test_profiles={},
        test_extra_vars={},
        test_scopes={},
        repeat=1,
        dry_run=True,
        stop_on_failure=False,
    )
    return CertificationRunner(options, console=Console(file=io.StringIO()))


class GracefulStopTests(unittest.TestCase):
    def test_interrupt_still_writes_partial_report(self) -> None:
        with TemporaryDirectory() as tmp:
            runner = make_runner(tmp)

            def interrupt(*_args: object, **_kwargs: object) -> int:
                raise KeyboardInterrupt

            runner._execute_plan = interrupt  # type: ignore[assignment]
            exit_code = runner.run()

            self.assertEqual(exit_code, 130)
            self.assertTrue((runner.run_dir / "run.summary.json").exists())
            self.assertTrue((runner.run_dir / "run.report.txt").exists())


class AnsibleEnvTests(unittest.TestCase):
    def test_pins_default_callback_over_user_setting(self) -> None:
        env = ansible_subprocess_env({"PATH": "/usr/bin", "ANSIBLE_STDOUT_CALLBACK": "yaml"})

        self.assertEqual(env["ANSIBLE_STDOUT_CALLBACK"], "default")
        self.assertEqual(env["ANSIBLE_NOCOLOR"], "1")
        self.assertEqual(env["PATH"], "/usr/bin")


if __name__ == "__main__":
    unittest.main()
