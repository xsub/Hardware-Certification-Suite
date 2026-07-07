from __future__ import annotations

import io
import json
import os
import stat
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

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


def make_runner(tmp: str, **overrides: object) -> CertificationRunner:
    paths = build_sandbox_paths(
        config={},
        profile="check",
        base_dir=Path(tmp),
        sandbox_dir=None,
        run_id="test",
    )
    defaults: dict[str, object] = {
        "preset_name": None,
        "profile": "check",
        "inventory": "127.0.0.1,",
        "connection": "local",
        "playbook": Path("automated.yml"),
        "paths": paths,
        "extra_vars": {},
        "selected_tests": ("hw_detection",),
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

    def test_interrupted_run_is_not_reported_as_passed(self) -> None:
        with TemporaryDirectory() as tmp:
            runner = make_runner(tmp, dry_run=False, selected_tests=("hw_detection", "cpu"))

            def interrupt(tests: object, results: list[StepResult]) -> int:
                results.append(step("passed"))
                raise KeyboardInterrupt

            runner._execute_plan = interrupt  # type: ignore[assignment]
            with mock.patch("hcs.runner.shutil.which", return_value="/usr/bin/ansible-playbook"):
                exit_code = runner.run()

            summary = json.loads((runner.run_dir / "run.summary.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 130)
            self.assertEqual(summary["status"], "interrupted")
            self.assertEqual(summary["run_verdict"], "interrupted")
            self.assertFalse(summary["certification_ready"])
            self.assertEqual(summary["result_contract"]["verdict"], "interrupted")
            self.assertTrue(summary["interrupted"])
            statuses = [result["status"] for result in summary["results"]]
            self.assertEqual(statuses, ["passed", "not_run"])
            self.assertIn("run interrupted", summary["results"][1]["status_reason"])

    def test_dry_run_is_not_reported_as_passed(self) -> None:
        with TemporaryDirectory() as tmp:
            runner = make_runner(tmp, dry_run=True)
            exit_code = runner.run()

            summary = json.loads((runner.run_dir / "run.summary.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertEqual(summary["status"], "dry_run")
            self.assertEqual(summary["run_verdict"], "dry_run")
            self.assertFalse(summary["certification_ready"])
            self.assertEqual(summary["results"][0]["status"], "skipped")

    def test_stop_on_failure_records_unexecuted_steps(self) -> None:
        with TemporaryDirectory() as tmp:
            runner = make_runner(
                tmp, dry_run=False, stop_on_failure=True, selected_tests=("hw_detection", "cpu")
            )

            def stop_early(tests: object, results: list[StepResult]) -> int:
                failed = step("failed")
                failed.return_code = 2
                results.append(failed)
                return 2

            runner._execute_plan = stop_early  # type: ignore[assignment]
            with mock.patch("hcs.runner.shutil.which", return_value="/usr/bin/ansible-playbook"):
                runner.run()

            summary = json.loads((runner.run_dir / "run.summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "failed")
            self.assertEqual(summary["run_verdict"], "failed")
            self.assertFalse(summary["certification_ready"])
            statuses = [result["status"] for result in summary["results"]]
            self.assertEqual(statuses, ["failed", "not_run"])
            self.assertIn("stop-on-failure", summary["results"][1]["status_reason"])


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

    def test_whole_loopback_range_and_case_insensitive_names_run_local(self) -> None:
        for inventory in ("127.0.0.2,", "127.255.255.254,", "LOCALHOST,"):
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

    def test_extra_var_precedence_cli_over_test_over_step_over_profile(self) -> None:
        with TemporaryDirectory() as tmp:
            runner = build_command_runner(
                tmp,
                test_profiles={"cpu": "long"},  # step profile: cpu_duration=30m, ltp_suites=syscalls
                extra_vars={"cpu_duration": "9m", "phoronix_need_space": "7"},
                test_extra_vars={"cpu": {"cpu_duration": "5m", "ltp_suites": "fork"}},
                cli_extra_vars={"cpu_duration": "2h"},
            )
            extra = command_extra_vars(runner.build_command(TESTS["cpu"]))

        self.assertEqual(extra["cpu_duration"], "2h")  # explicit CLI wins over everything
        self.assertEqual(extra["ltp_suites"], "fork")  # per-test wins over step profile
        self.assertEqual(extra["phoronix_need_space"], "7")  # preset/config wins over base profile

    def test_anchors_lts_tests_dir_to_the_playbook(self) -> None:
        with TemporaryDirectory() as tmp:
            playbook = Path(tmp) / "repo" / "automated.yml"
            playbook.parent.mkdir()
            playbook.write_text("---\n", encoding="utf-8")
            runner = build_command_runner(tmp, playbook=playbook)
            extra = command_extra_vars(runner.build_command(TESTS["cpu"]))

        self.assertEqual(extra["lts_tests_dir"], str(playbook.resolve().parent / "tests"))


class ExecuteStepTests(unittest.TestCase):
    """Drive execute_step end to end against a fake ansible-playbook on PATH."""

    def _run_step(self, tmp: str, script: str, **overrides: object) -> object:
        bindir = Path(tmp) / "bin"
        bindir.mkdir()
        fake = bindir / "ansible-playbook"
        fake.write_text(script, encoding="utf-8")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        runner = build_command_runner(tmp, dry_run=False, selected_tests=("hw_detection",), **overrides)
        runner.prepare_run_dir()
        previous = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{bindir}{os.pathsep}{previous}"
        try:
            # force_terminal so descriptions really render; a markup regression
            # must surface here instead of being skipped for non-tty consoles.
            console = Console(file=io.StringIO(), force_terminal=True, width=120)
            with Progress(console=console) as progress:
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

    def test_streamed_markup_like_output_does_not_crash_the_runner(self) -> None:
        # Ansible output is not Rich markup; bracketed paths like [/var/tmp/x]
        # in fatal dumps look like closing tags and used to raise MarkupError.
        script = (
            "#!/bin/sh\n"
            'echo "fatal: [127.0.0.1]: FAILED! => msg [/var/tmp/sandbox] [/red] oops"\n'
            'echo "TASK [hw_detection : Collect DMI data] ******"\n'
            'echo "127.0.0.1 : ok=2 changed=0 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0"\n'
            "exit 0\n"
        )
        with TemporaryDirectory() as tmp:
            result = self._run_step(tmp, script)

        self.assertEqual(result.status, "passed")

    def test_step_timeout_terminates_and_fails_the_step(self) -> None:
        script = (
            "#!/bin/sh\n"
            'echo "starting"\n'
            "sleep 30\n"
            'echo "127.0.0.1 : ok=1 changed=0 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0"\n'
            "exit 0\n"
        )
        with TemporaryDirectory() as tmp:
            result = self._run_step(tmp, script, step_timeout=0.5)

        self.assertEqual(result.status, "failed")
        self.assertIn("timed out", result.status_reason)
        self.assertLess(result.duration_seconds, 20.0)

    def test_step_timeout_escalates_to_sigkill_for_term_ignoring_children(self) -> None:
        script = (
            "#!/bin/sh\n"
            "trap '' TERM\n"
            "i=0\n"
            "while [ $i -lt 300 ]; do sleep 0.1 || :; i=$((i+1)); done\n"
        )
        with TemporaryDirectory() as tmp:
            with mock.patch("hcs.runner.TERMINATE_GRACE_SECONDS", 0.3):
                result = self._run_step(tmp, script, step_timeout=0.5)

        self.assertEqual(result.status, "failed")
        self.assertIn("timed out", result.status_reason)
        self.assertLess(result.duration_seconds, 15.0)

    def test_explicit_fail_marker_overrides_an_earlier_pass_marker(self) -> None:
        script = (
            "#!/bin/sh\n"
            'echo \'    "msg": "HCS_RESULT: pass subtest one ok"\'\n'
            'echo \'    "msg": "HCS_RESULT: fail subtest two broke"\'\n'
            'echo "127.0.0.1 : ok=3 changed=0 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0"\n'
            "exit 0\n"
        )
        with TemporaryDirectory() as tmp:
            result = self._run_step(tmp, script)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.status_reason, "subtest two broke")


class RequiredUnexercisedTests(unittest.TestCase):
    def _result(self, test_id: str, status: str, reason: str = "ok") -> StepResult:
        result = step(status)
        result.test_id = test_id
        result.status_reason = reason
        return result

    def test_lists_required_tests_without_a_verdict(self) -> None:
        with TemporaryDirectory() as tmp:
            runner = make_runner(
                tmp,
                dry_run=False,
                selected_tests=("hw_detection", "network"),
                test_scopes={
                    "hw_detection": "required",
                    "network": "required",
                    "raid": "required",
                    "cpu": "optional",
                },
            )
            results = [
                self._result("hw_detection", "passed"),
                self._result("network", "unsupported", "needs a distinct SUT"),
            ]
            unexercised = runner.required_unexercised(results)

        by_id = {entry["test_id"]: entry["reason"] for entry in unexercised}
        self.assertIn("network", by_id)
        self.assertIn("unsupported", by_id["network"])
        self.assertIn("raid", by_id)
        self.assertIn("not selected", by_id["raid"])
        self.assertNotIn("hw_detection", by_id)
        self.assertNotIn("cpu", by_id)

    def test_exercised_required_tests_are_not_listed(self) -> None:
        with TemporaryDirectory() as tmp:
            runner = make_runner(
                tmp,
                dry_run=False,
                selected_tests=("hw_detection",),
                test_scopes={"hw_detection": "required"},
            )
            unexercised = runner.required_unexercised([self._result("hw_detection", "failed", "rc=2")])

        self.assertEqual(unexercised, [])


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
