from __future__ import annotations

import io
import json
import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from rich.console import Console
from rich.progress import Progress

from hcs.config import build_sandbox_paths
from hcs.profiles import TESTS
from hcs.runner import (
    RESULT_RE,
    UNSUPPORTED_RE,
    CertificationRunner,
    RunnerOptions,
    StepResult,
    ansible_subprocess_env,
    default_connection,
    derive_status,
    parse_extra_vars,
    parse_recap_line,
    run_status,
    should_refresh_ui,
    summarize_results,
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

    def test_explicit_pass_cannot_mask_hard_failure(self) -> None:
        status, _ = derive_status(
            return_code=0,
            result_status="pass",
            result_reason=None,
            unsupported_reason=None,
            recap=recap(failed=1),
        )
        self.assertEqual(status, "failed")

    def test_explicit_pass_cannot_mask_unreachable(self) -> None:
        status, _ = derive_status(
            return_code=0,
            result_status="pass",
            result_reason=None,
            unsupported_reason=None,
            recap=recap(unreachable=1),
        )
        self.assertEqual(status, "failed")


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


class SummarizeResultsTests(unittest.TestCase):
    def _step(self, status: str, duration: float, name: str) -> StepResult:
        result = step(status)
        result.duration_seconds = duration
        result.display_name = name
        return result

    def test_counts_total_and_slowest(self) -> None:
        results = [
            self._step("passed", 2.0, "A"),
            self._step("failed", 9.0, "B"),
            self._step("unsupported", 1.0, "C"),
        ]
        summary = summarize_results(results)

        self.assertEqual(summary.counts["passed"], 1)
        self.assertEqual(summary.counts["failed"], 1)
        self.assertEqual(summary.counts["unsupported"], 1)
        self.assertEqual(summary.total_seconds, 12.0)
        assert summary.slowest is not None
        self.assertEqual(summary.slowest.display_name, "B")

    def test_empty_results(self) -> None:
        summary = summarize_results([])

        self.assertEqual(summary.total_seconds, 0.0)
        self.assertIsNone(summary.slowest)
        self.assertEqual(summary.counts["passed"], 0)


class ProgressThrottleTests(unittest.TestCase):
    def test_refreshes_after_interval(self) -> None:
        self.assertTrue(should_refresh_ui(0.0, 0.2, interval=0.1))

    def test_skips_within_interval(self) -> None:
        self.assertFalse(should_refresh_ui(1.0, 1.05, interval=0.1))


class AnsibleEnvTests(unittest.TestCase):
    def test_pins_default_callback_over_user_setting(self) -> None:
        env = ansible_subprocess_env({"PATH": "/usr/bin", "ANSIBLE_STDOUT_CALLBACK": "yaml"})

        self.assertEqual(env["ANSIBLE_STDOUT_CALLBACK"], "default")
        self.assertEqual(env["ANSIBLE_NOCOLOR"], "1")
        self.assertEqual(env["PATH"], "/usr/bin")


class DefaultConnectionTests(unittest.TestCase):
    def test_loopback_inventories_run_local(self) -> None:
        for inventory in ("127.0.0.1,", "localhost,", "::1,", "127.0.0.1,localhost,"):
            self.assertEqual(default_connection(inventory), "local", inventory)

    def test_remote_host_defers_to_ansible_default(self) -> None:
        self.assertIsNone(default_connection("10.0.0.5,"))
        self.assertIsNone(default_connection("sut.example.com,"))

    def test_mixed_loopback_and_remote_is_remote(self) -> None:
        self.assertIsNone(default_connection("127.0.0.1,10.0.0.5,"))

    def test_empty_inventory_defers_to_ansible_default(self) -> None:
        self.assertIsNone(default_connection(""))


def build_command_runner(tmp: str, **overrides: object) -> CertificationRunner:
    paths = build_sandbox_paths(
        config={}, profile="check", base_dir=Path(tmp), sandbox_dir=None, run_id="test"
    )
    defaults: dict[str, object] = {
        "preset_name": None,
        "profile": "check",
        "inventory": "127.0.0.1,",
        "connection": "local",
        "playbook": Path("automated.yml"),
        "paths": paths,
        "extra_vars": {},
        "selected_tests": ("cpu",),
        "test_profiles": {},
        "test_extra_vars": {},
        "test_scopes": {},
        "repeat": 1,
        "dry_run": True,
        "stop_on_failure": False,
    }
    defaults.update(overrides)
    options = RunnerOptions(**defaults)  # type: ignore[arg-type]
    return CertificationRunner(options, console=Console(file=io.StringIO()))


def command_extra_vars(command: list[str]) -> dict[str, str]:
    index = command.index("--extra-vars")
    return json.loads(command[index + 1])


class BuildCommandTests(unittest.TestCase):
    def test_includes_tag_inventory_and_connection(self) -> None:
        with TemporaryDirectory() as tmp:
            command = build_command_runner(tmp).build_command(TESTS["cpu"])

        self.assertEqual(command[:6], ["ansible-playbook", "-i", "127.0.0.1,", "automated.yml", "--tags", "cpu"])
        self.assertIn("-c", command)
        self.assertEqual(command[command.index("-c") + 1], "local")

    def test_omits_connection_when_none(self) -> None:
        with TemporaryDirectory() as tmp:
            command = build_command_runner(tmp, connection=None).build_command(TESTS["cpu"])

        self.assertNotIn("-c", command)

    def test_injects_sandbox_paths(self) -> None:
        with TemporaryDirectory() as tmp:
            runner = build_command_runner(tmp)
            extra = command_extra_vars(runner.build_command(TESTS["cpu"]))

        self.assertEqual(extra["hcs_run_id"], runner.paths.run_id)
        self.assertEqual(extra["sandbox_dir"], str(runner.paths.sandbox_dir))
        self.assertEqual(extra["ltp_clone_path"], str(runner.paths.ltp_dir))

    def test_extra_var_precedence_test_over_cli_over_step_over_profile(self) -> None:
        with TemporaryDirectory() as tmp:
            runner = build_command_runner(
                tmp,
                test_profiles={"cpu": "long"},  # step profile: cpu_duration=30m, ltp_suites=syscalls
                extra_vars={"cpu_duration": "9m", "phoronix_need_space": "7"},
                test_extra_vars={"cpu": {"cpu_duration": "5m"}},
            )
            extra = command_extra_vars(runner.build_command(TESTS["cpu"]))

        self.assertEqual(extra["cpu_duration"], "5m")  # per-test wins over cli/step/profile
        self.assertEqual(extra["ltp_suites"], "syscalls")  # step profile wins over base check
        self.assertEqual(extra["phoronix_need_space"], "7")  # cli wins over base profile


class ExecuteStepTests(unittest.TestCase):
    """Drive execute_step end to end against a fake ansible-playbook on PATH."""

    def _run_step(self, tmp: str, script: str) -> object:
        bindir = Path(tmp) / "bin"
        bindir.mkdir()
        fake = bindir / "ansible-playbook"
        fake.write_text(script, encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        runner = build_command_runner(tmp, dry_run=False, selected_tests=("hw_detection",))
        runner.prepare_run_dir()
        previous = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{bindir}{os.pathsep}{previous}"
        try:
            with Progress(console=Console(file=io.StringIO())) as progress:
                task_id = progress.add_task("x", total=None)
                return runner.execute_step(1, 1, TESTS["hw_detection"], progress, task_id)
        finally:
            os.environ["PATH"] = previous

    def test_clean_recap_and_result_marker_pass(self) -> None:
        script = (
            "#!/bin/sh\n"
            'echo "ok: [127.0.0.1] => {"\n'
            'echo \'    "msg": "HCS_RESULT: pass disk healthy"\'\n'
            'echo "}"\n'
            'echo "127.0.0.1 : ok=3 changed=1 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0"\n'
            "exit 0\n"
        )
        with TemporaryDirectory() as tmp:
            result = self._run_step(tmp, script)

        self.assertEqual(result.status, "passed")
        self.assertEqual(result.status_reason, "disk healthy")
        self.assertEqual(result.return_code, 0)
        self.assertEqual(result.ansible_recap["127.0.0.1"]["ok"], 3)

    def test_nonzero_return_code_fails(self) -> None:
        script = (
            "#!/bin/sh\n"
            'echo "127.0.0.1 : ok=1 changed=0 unreachable=0 failed=1 skipped=0 rescued=0 ignored=0"\n'
            "exit 2\n"
        )
        with TemporaryDirectory() as tmp:
            result = self._run_step(tmp, script)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.return_code, 2)


class ParseExtraVarsTests(unittest.TestCase):
    def test_parses_key_value_pairs(self) -> None:
        self.assertEqual(parse_extra_vars(["a=1", "b=x=y"]), {"a": "1", "b": "x=y"})

    def test_rejects_missing_equals(self) -> None:
        with self.assertRaises(ValueError):
            parse_extra_vars(["novalue"])

    def test_rejects_empty_key(self) -> None:
        with self.assertRaises(ValueError):
            parse_extra_vars(["=value"])


if __name__ == "__main__":
    unittest.main()
