from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hcs.__main__ import main
from hcs.submission import build_submission_manifest, validate_submission, write_submission_manifest


def run_dry(sandbox: Path) -> int:
    with redirect_stdout(io.StringIO()):
        return main(["run", "--profile", "check", "--sandbox-dir", str(sandbox), "--dry-run"])


class SubmissionManifestTests(unittest.TestCase):
    def test_runner_writes_submission_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry(sandbox), 0)

            manifest_path = sandbox / "runner" / "submission.manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["target"]["repository"], "AlmaLinux/certifications")
        self.assertEqual(manifest["run"]["run_verdict"], "dry_run")
        required_paths = {
            artifact["path"]
            for artifact in manifest["artifacts"]
            if artifact["role"] == "required"
        }
        self.assertIn("runner/config.requested.json", required_paths)
        self.assertIn("runner/run.summary.json", required_paths)
        self.assertTrue(any(path.endswith(".result.json") for path in required_paths))

    def test_build_manifest_accepts_runner_directory(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry(sandbox), 0)

            manifest = build_submission_manifest(sandbox / "runner")

        self.assertEqual(manifest["run"]["profile"], "check")

    def test_validate_submission_succeeds_with_warnings_for_dry_run(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry(sandbox), 0)

            report = validate_submission(sandbox)

        self.assertTrue(report.ok)
        self.assertTrue(report.warnings)
        self.assertTrue(any("certification_ready=false" in issue.message for issue in report.warnings))

    def test_validate_submission_detects_missing_required_artifact(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry(sandbox), 0)
            (sandbox / "runner" / "config.requested.json").unlink()

            report = validate_submission(sandbox)

        self.assertFalse(report.ok)
        self.assertTrue(any("config.requested.json" in issue.message for issue in report.errors))

    def test_validate_submission_write_manifest_refreshes_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry(sandbox), 0)
            manifest_path = sandbox / "runner" / "submission.manifest.json"
            manifest_path.unlink()

            report = validate_submission(sandbox, write_manifest=True)

        self.assertTrue(report.ok)
        self.assertEqual(report.manifest_path.name, "submission.manifest.json")

    def test_cli_validate_run(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry(sandbox), 0)

            with redirect_stdout(io.StringIO()):
                rc = main(["validate-run", str(sandbox)])

        self.assertEqual(rc, 0)

    def test_cli_validate_run_reports_errors(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry(sandbox), 0)
            (sandbox / "runner" / "run.summary.json").unlink()

            with redirect_stdout(io.StringIO()):
                rc = main(["validate-run", str(sandbox)])

        self.assertEqual(rc, 1)

    def test_validate_manifest_rejects_paths_outside_sandbox(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry(sandbox), 0)
            manifest_path = sandbox / "runner" / "submission.manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["artifacts"].append(
                {
                    "path": "../outside",
                    "role": "required",
                    "description": "bad path",
                    "required": True,
                    "exists": True,
                }
            )
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            report = validate_submission(sandbox)

        self.assertFalse(report.ok)
        self.assertTrue(any("must stay inside the sandbox" in issue.message for issue in report.errors))

    def test_write_manifest_returns_manifest_path(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry(sandbox), 0)

            manifest_path = write_submission_manifest(sandbox)

        self.assertEqual(manifest_path.name, "submission.manifest.json")


if __name__ == "__main__":
    unittest.main()
