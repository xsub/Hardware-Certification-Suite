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


def write_public_submission_fixture(sandbox: Path) -> None:
    runner = sandbox / "runner"
    step_dir = runner / "tests" / "001-pass01-hw_detection"
    step_dir.mkdir(parents=True)
    (runner / "config.requested.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "runner_version": "test",
                "profile": "check",
                "inventory": "127.0.0.1,",
                "paths": {"run_id": "fixture", "sandbox_dir": str(sandbox), "runner_dir": str(runner)},
                "dry_run": False,
                "stop_on_failure": False,
                "tests": ["hw_detection"],
                "repeat": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    step_payload = {
        "schema_version": 1,
        "runner_version": "test",
        "step": 1,
        "pass_index": 1,
        "pass_count": 1,
        "test_id": "hw_detection",
        "display_name": "Hardware detection",
        "preset": None,
        "profile": "check",
        "scope": "required",
        "status": "passed",
        "status_reason": "ok",
        "return_code": 0,
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T00:00:01Z",
        "duration_seconds": 1.0,
        "command": [],
        "artifacts": [],
        "ansible_recap": {},
    }
    (step_dir / "001-pass01-hw_detection.result.json").write_text(
        json.dumps(step_payload) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema_version": 1,
        "runner_version": "test",
        "preset": None,
        "profile": "check",
        "inventory": "127.0.0.1,",
        "connection": "local",
        "repeat": 1,
        "status": "passed",
        "run_verdict": "passed",
        "certification_ready": True,
        "result_contract": {
            "schema_version": 1,
            "verdict": "passed",
            "certification_ready": True,
            "review_required": False,
            "blocking_reasons": [],
            "review_notes": [],
        },
        "interrupted": False,
        "started_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T00:00:01Z",
        "paths": {"run_id": "fixture", "sandbox_dir": str(sandbox), "runner_dir": str(runner)},
        "manual_tests": {},
        "required_unexercised": [],
        "sut_system": {"title": "Fixture SUT", "facts": [{"label": "Source", "value": "fixture"}]},
        "controller_system": {"title": "Fixture controller", "facts": []},
        "results": [
            {
                "step": 1,
                "pass_index": 1,
                "test_id": "hw_detection",
                "scope": "required",
                "status": "passed",
                "status_reason": "ok",
                "return_code": 0,
                "duration_seconds": 1.0,
                "artifacts": [],
                "ansible_recap": {},
            }
        ],
    }
    (runner / "run.summary.json").write_text(json.dumps(summary) + "\n", encoding="utf-8")


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
        privacy = {artifact["path"]: artifact["privacy"] for artifact in manifest["artifacts"]}
        self.assertEqual(privacy["runner/run.summary.json"], "review_before_publish")
        self.assertTrue(
            all(
                value == "private_or_redacted"
                for path, value in privacy.items()
                if path.endswith(".console.log")
            )
        )

    def test_fixture_public_submission_manifest_validates_cleanly(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "fixture-run"
            write_public_submission_fixture(sandbox)
            manifest_path = write_submission_manifest(sandbox)

            report = validate_submission(sandbox)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertTrue(report.ok)
        self.assertFalse(report.warnings)
        self.assertEqual(manifest["run"]["run_verdict"], "passed")
        self.assertTrue(manifest["run"]["certification_ready"])

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

    def test_validate_submission_includes_privacy_warnings(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            self.assertEqual(run_dry(sandbox), 0)
            (sandbox / "runner" / "private-note.txt").write_text(
                "Serial Number: ABC123\n",
                encoding="utf-8",
            )

            report = validate_submission(sandbox)

        self.assertTrue(report.ok)
        self.assertTrue(any("possible serial" in issue.message for issue in report.warnings))

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
