from __future__ import annotations

import json
from contextlib import redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hcs.__main__ import main
from hcs.presets import (
    get_preset,
    limiting_duration_value,
    preset_selected_tests,
    preset_test_extra_vars,
    preset_test_profiles,
    preset_test_scopes,
)


class RunnerPresetTests(unittest.TestCase):
    def test_preset_selects_enabled_tests_and_profiles(self) -> None:
        preset = {
            "profile": "check",
            "tests": {
                "hw_detection": {"enabled": False},
                "gpu_burn": {
                    "enabled": True,
                    "profile": "short",
                    "duration": "120",
                    "snap": {"install": True, "remove_after": True},
                },
            },
        }

        self.assertEqual(preset_selected_tests(preset), ("gpu_burn",))
        self.assertEqual(preset_test_profiles(preset), {"gpu_burn": "short"})
        self.assertEqual(
            preset_test_scopes(preset),
            {
                "hw_detection": "optional",
                "gpu_burn": "optional",
            },
        )
        self.assertEqual(
            preset_test_extra_vars(preset),
            {
                "gpu_burn": {
                    "gpu_burn_duration": "120",
                    "gpu_burn_install_snap": "true",
                    "gpu_burn_remove_snap_after": "true",
                }
            },
        )

    def test_duration_cap_uses_more_restrictive_value(self) -> None:
        self.assertEqual(limiting_duration_value("gpu_burn", "check", "10m"), "60")
        self.assertEqual(limiting_duration_value("cpu", "check", "10m"), "120s")

    def test_builtin_certification_preset_declares_required_and_optional_tests(self) -> None:
        preset = get_preset({}, "certification")

        self.assertIsNotNone(preset)
        assert preset is not None
        self.assertEqual(preset["profile"], "long")
        self.assertEqual(
            preset_selected_tests(preset),
            ("hw_detection", "containers", "kvm", "cpu", "network", "ltp", "phoronix"),
        )
        scopes = preset_test_scopes(preset)
        self.assertEqual(scopes["hw_detection"], "required")
        self.assertEqual(scopes["phoronix"], "required")
        self.assertEqual(scopes["raid"], "optional")
        self.assertEqual(scopes["gpu_burn"], "optional")

    def test_explicit_profile_ignores_default_preset_test_selection(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "hcs-runner.yml"
            sandbox = root / "run"
            config.write_text(
                """
run:
  default_preset: default
presets:
  default:
    profile: check
    tests:
      hw_detection:
        enabled: true
""",
                encoding="utf-8",
            )

            with redirect_stdout(io.StringIO()):
                rc = main(
                    [
                        "run",
                        "--config",
                        str(config),
                        "--profile",
                        "medium",
                        "--sandbox-dir",
                        str(sandbox),
                        "--dry-run",
                    ]
                )

            summary = json.loads((sandbox / "runner" / "run.summary.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(
            [result["test_id"] for result in summary["results"]],
            ["hw_detection", "containers", "kvm", "cpu", "network", "raid"],
        )

    def test_builtin_certification_preset_dry_run_records_required_scopes(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox = root / "run"

            with redirect_stdout(io.StringIO()):
                rc = main(
                    [
                        "run",
                        "--preset",
                        "certification",
                        "--sandbox-dir",
                        str(sandbox),
                        "--dry-run",
                    ]
                )

            summary = json.loads((sandbox / "runner" / "run.summary.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(
            [result["test_id"] for result in summary["results"]],
            ["hw_detection", "containers", "kvm", "cpu", "network", "ltp", "phoronix"],
        )
        self.assertTrue(all(result["scope"] == "required" for result in summary["results"]))


if __name__ == "__main__":
    unittest.main()
