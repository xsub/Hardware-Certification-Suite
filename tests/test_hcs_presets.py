from __future__ import annotations

import json
from contextlib import redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hcs.__main__ import main
from hcs.presets import (
    limiting_duration_value,
    preset_selected_tests,
    preset_test_extra_vars,
    preset_test_profiles,
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


if __name__ == "__main__":
    unittest.main()
