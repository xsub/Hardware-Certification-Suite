from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from hcs.__main__ import main
from hcs.config import build_sandbox_paths
from hcs.preflight import run_preflight
from hcs.runner import RunnerOptions


def options(tmp: str, **overrides: object) -> RunnerOptions:
    root = Path(tmp)
    playbook = root / "automated.yml"
    playbook.write_text("---\n", encoding="utf-8")
    defaults: dict[str, object] = {
        "preset_name": None,
        "profile": "check",
        "inventory": "127.0.0.1,",
        "connection": "local",
        "playbook": playbook,
        "paths": build_sandbox_paths(
            config={},
            profile="check",
            base_dir=root,
            sandbox_dir=root / "run",
            run_id="preflight",
        ),
        "extra_vars": {},
        "selected_tests": None,
        "test_profiles": {},
        "test_extra_vars": {},
        "test_scopes": {},
        "repeat": 1,
        "dry_run": False,
        "stop_on_failure": False,
    }
    defaults.update(overrides)
    return RunnerOptions(**defaults)  # type: ignore[arg-type]


class PreflightTests(unittest.TestCase):
    @mock.patch("hcs.preflight.shutil.which", return_value="/usr/bin/ansible-playbook")
    @mock.patch("hcs.preflight.os.geteuid", return_value=0, create=True)
    def test_preflight_ok_for_basic_local_run(self, _geteuid: object, _which: object) -> None:
        with TemporaryDirectory() as tmp:
            report = run_preflight(options(tmp))

        self.assertTrue(report.ok)
        self.assertFalse(report.errors)

    @mock.patch("hcs.preflight.shutil.which", return_value=None)
    def test_preflight_reports_missing_ansible(self, _which: object) -> None:
        with TemporaryDirectory() as tmp:
            report = run_preflight(options(tmp))

        self.assertFalse(report.ok)
        self.assertTrue(any(check.name == "ansible" for check in report.errors))

    @mock.patch("hcs.preflight.shutil.which", return_value="/usr/bin/ansible-playbook")
    def test_remote_network_without_explicit_endpoints_warns(self, _which: object) -> None:
        with TemporaryDirectory() as tmp:
            report = run_preflight(
                options(
                    tmp,
                    profile="medium",
                    inventory="10.0.0.5,",
                    connection=None,
                    selected_tests=None,
                )
            )

        self.assertTrue(report.ok)
        self.assertTrue(any(check.name == "network" for check in report.warnings))

    @mock.patch("hcs.preflight.shutil.which", return_value="/usr/bin/ansible-playbook")
    @mock.patch("hcs.preflight.os.geteuid", return_value=0, create=True)
    def test_cli_preflight(self, _geteuid: object, _which: object) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            playbook = root / "automated.yml"
            playbook.write_text("---\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                rc = main(
                    [
                        "preflight",
                        "--profile",
                        "check",
                        "--playbook",
                        str(playbook),
                        "--sandbox-dir",
                        str(root / "run"),
                    ]
                )

        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
