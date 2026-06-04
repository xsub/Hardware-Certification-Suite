from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hcs.config import build_sandbox_paths, load_config, sandbox_child


class RunnerConfigTests(unittest.TestCase):
    def test_missing_default_config_is_empty(self) -> None:
        with TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                os.chdir(tmp)
                self.assertEqual(load_config(None), {})
            finally:
                os.chdir(previous)

    def test_default_base_dir_is_var_tmp(self) -> None:
        with TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                os.chdir(tmp)
                paths = build_sandbox_paths(
                    config={},
                    profile="check",
                    base_dir=None,
                    sandbox_dir=None,
                    run_id=None,
                )
            finally:
                os.chdir(previous)

        self.assertEqual(paths.sandbox_dir.parent, Path("/var/tmp"))

    def test_default_config_is_loaded_from_current_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "hcs-runner.yml"
            config_path.write_text("run:\n  base_dir: /var/tmp\n", encoding="utf-8")

            previous = Path.cwd()
            try:
                os.chdir(tmp)
                config = load_config(None)
                paths = build_sandbox_paths(
                    config=config,
                    profile="check",
                    base_dir=None,
                    sandbox_dir=None,
                    run_id=None,
                )
            finally:
                os.chdir(previous)

        self.assertEqual(config["run"]["base_dir"], "/var/tmp")
        self.assertEqual(paths.sandbox_dir.parent, Path("/var/tmp"))
        self.assertRegex(paths.run_id, r"^check-[0-9a-f]{8}$")


class SandboxChildTests(unittest.TestCase):
    def test_relative_child_stays_inside_root(self) -> None:
        root = Path("/var/tmp/AlmaLinux-HCS-run")
        self.assertEqual(sandbox_child(root, None, "logs"), root / "logs")

    def test_absolute_child_inside_root_is_allowed(self) -> None:
        root = Path("/var/tmp/AlmaLinux-HCS-run")
        self.assertEqual(sandbox_child(root, "/var/tmp/AlmaLinux-HCS-run/logs", "logs"), root / "logs")

    def test_relative_escape_is_rejected(self) -> None:
        root = Path("/var/tmp/AlmaLinux-HCS-run")
        with self.assertRaises(ValueError):
            sandbox_child(root, "../escape", "logs")

    def test_absolute_outside_root_is_rejected(self) -> None:
        root = Path("/var/tmp/AlmaLinux-HCS-run")
        with self.assertRaises(ValueError):
            sandbox_child(root, "/etc/passwd", "logs")


if __name__ == "__main__":
    unittest.main()
