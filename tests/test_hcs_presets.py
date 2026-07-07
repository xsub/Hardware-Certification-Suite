from __future__ import annotations

import json
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hcs.__main__ import main
from hcs.presets import (
    config_warnings,
    get_preset,
    limiting_duration_value,
    parse_duration_seconds,
    preset_duration_warnings,
    preset_selected_tests,
    preset_test_extra_vars,
    preset_test_profiles,
    preset_test_scopes,
)


def requested_config(sandbox: Path) -> dict:
    return json.loads((sandbox / "runner" / "config.requested.json").read_text(encoding="utf-8"))


def run_dry(*args: str) -> int:
    with redirect_stdout(io.StringIO()):
        return main(["run", *args, "--dry-run"])


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

    def test_parse_duration_seconds_handles_suffixes(self) -> None:
        self.assertEqual(parse_duration_seconds("90"), 90)
        self.assertEqual(parse_duration_seconds("90s"), 90)
        self.assertEqual(parse_duration_seconds("5m"), 300)
        self.assertEqual(parse_duration_seconds("2h"), 7200)
        self.assertEqual(parse_duration_seconds("1d"), 86400)

    def test_parse_duration_seconds_rejects_garbage(self) -> None:
        self.assertIsNone(parse_duration_seconds(""))
        self.assertIsNone(parse_duration_seconds("ten"))
        self.assertIsNone(parse_duration_seconds("5x"))

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
        self.assertEqual(scopes["ai_llm"], "optional")

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
        self.assertEqual(summary["status"], "dry_run")
        # The policy's interactive tests must appear in the evidence.
        self.assertEqual(sorted(summary["manual_tests"]), ["pxe", "usb"])
        self.assertTrue(all(entry["required"] for entry in summary["manual_tests"].values()))


class ConfigWarningTests(unittest.TestCase):
    def test_flags_unknown_keys_everywhere(self) -> None:
        config = {"run": {"base_dirr": "/x"}, "presetz": {}, "presets": {}}
        preset = {
            "profile": "check",
            "unknown_key": 1,
            "tests": {"cpu": {"enabled": True, "durationn": "5m"}},
        }
        warnings = config_warnings(config, preset)

        joined = "\n".join(warnings)
        self.assertIn("base_dirr", joined)
        self.assertIn("presetz", joined)
        self.assertIn("unknown_key", joined)
        self.assertIn("durationn", joined)

    def test_clean_config_and_builtin_preset_warn_nothing(self) -> None:
        config = {"run": {"base_dir": "/var/tmp", "default_preset": "certification"}}
        preset = get_preset({}, "certification")

        self.assertEqual(config_warnings(config, preset), [])


class DurationWarningTests(unittest.TestCase):
    def test_warns_when_duration_exceeds_the_profile_cap(self) -> None:
        preset = {"profile": "medium", "tests": {"cpu": {"enabled": True, "duration": "2h"}}}
        warnings = preset_duration_warnings(preset)

        self.assertEqual(len(warnings), 1)
        self.assertIn("cpu", warnings[0])
        self.assertIn("profile cap", warnings[0])

    def test_silent_when_duration_is_within_the_cap(self) -> None:
        preset = {"profile": "medium", "tests": {"cpu": {"enabled": True, "duration": "5m"}}}

        self.assertEqual(preset_duration_warnings(preset), [])

    def test_builtin_certification_preset_warns_nothing(self) -> None:
        self.assertEqual(preset_duration_warnings(get_preset({}, "certification")), [])


class ConnectionDefaultingTests(unittest.TestCase):
    def test_bare_local_run_infers_local_connection(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry("--profile", "check", "--sandbox-dir", str(sandbox)), 0)
            config = requested_config(sandbox)

        self.assertEqual(config["inventory"], "127.0.0.1,")
        self.assertEqual(config["connection"], "local")

    def test_remote_inventory_does_not_force_local_connection(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(
                run_dry("--profile", "check", "--inventory", "10.0.0.5,", "--sandbox-dir", str(sandbox)),
                0,
            )
            config = requested_config(sandbox)

        self.assertEqual(config["inventory"], "10.0.0.5,")
        self.assertIsNone(config["connection"])

    def test_host_shorthand_targets_remote_over_ssh(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry("--profile", "check", "--host", "10.0.0.5", "--sandbox-dir", str(sandbox)), 0)
            config = requested_config(sandbox)

        self.assertEqual(config["inventory"], "10.0.0.5,")
        self.assertIsNone(config["connection"])

    def test_explicit_connection_overrides_inference(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(
                run_dry("--profile", "check", "--host", "10.0.0.5", "-c", "local", "--sandbox-dir", str(sandbox)),
                0,
            )
            config = requested_config(sandbox)

        self.assertEqual(config["connection"], "local")

    def test_certification_preset_remote_host_runs_over_ssh(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(
                run_dry("--preset", "certification", "--host", "sut.example", "--sandbox-dir", str(sandbox)),
                0,
            )
            config = requested_config(sandbox)

        self.assertEqual(config["inventory"], "sut.example,")
        self.assertIsNone(config["connection"])

    def test_explicit_network_endpoints_are_recorded(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(
                run_dry(
                    "--profile",
                    "check",
                    "--lts-ip",
                    "10.0.0.1",
                    "--sut-ip",
                    "10.0.0.2",
                    "--sandbox-dir",
                    str(sandbox),
                ),
                0,
            )
            config = requested_config(sandbox)

        self.assertEqual(config["network_endpoints"], {"lts_ip": "10.0.0.1", "sut_ip": "10.0.0.2"})

    def test_network_endpoints_must_be_a_pair(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    run_dry("--profile", "check", "--lts-ip", "10.0.0.1", "--sandbox-dir", str(sandbox))


if __name__ == "__main__":
    unittest.main()
