"""Submission manifest and run-directory validation helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from . import __version__


MANIFEST_SCHEMA_VERSION = 1
MANIFEST_RELATIVE_PATH = Path("runner") / "submission.manifest.json"
REQUIRED_RUNNER_FILES = (
    Path("runner") / "config.requested.json",
    Path("runner") / "run.summary.json",
)
REVIEWER_CONVENIENCE_FILES = (
    Path("runner") / "run.report.txt",
    Path("runner") / "run.report.pdf",
)


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    sandbox_dir: Path
    manifest_path: Path
    issues: tuple[ValidationIssue, ...]

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_sandbox_dir(path: Path) -> Path:
    candidate = path.expanduser()
    if (candidate / "runner" / "run.summary.json").exists():
        return candidate
    if (candidate / "run.summary.json").exists() and candidate.name == "runner":
        return candidate.parent
    if (candidate / "run.summary.json").exists():
        return candidate.parent
    return candidate


def relative_files(root: Path, patterns: Iterable[str]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        found.extend(path.relative_to(root) for path in sorted(root.glob(pattern)) if path.is_file())
    return found


def artifact_entry(sandbox_dir: Path, relative_path: Path, role: str, description: str) -> dict[str, object]:
    path = sandbox_dir / relative_path
    entry: dict[str, object] = {
        "path": relative_path.as_posix(),
        "role": role,
        "description": description,
        "required": role == "required",
        "exists": path.exists(),
    }
    if path.exists() and path.is_file():
        entry["size_bytes"] = path.stat().st_size
        entry["sha256"] = sha256_file(path)
    return entry


def manifest_artifact_path(sandbox_dir: Path, raw_path: str) -> Path:
    relative_path = Path(raw_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError(f"manifest artifact path must stay inside the sandbox: {raw_path}")
    return sandbox_dir / relative_path


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return data


def build_submission_manifest(sandbox_path: Path) -> dict[str, object]:
    sandbox_dir = resolve_sandbox_dir(sandbox_path)
    summary_path = sandbox_dir / "runner" / "run.summary.json"
    summary = load_json(summary_path) if summary_path.exists() else {}
    result_files = relative_files(sandbox_dir, ("runner/tests/*/*.result.json",))
    console_logs = relative_files(sandbox_dir, ("runner/tests/*/*.console.log",))

    artifacts: list[dict[str, object]] = []
    artifacts.extend(
        artifact_entry(sandbox_dir, path, "required", "Required runner contract artifact")
        for path in REQUIRED_RUNNER_FILES
    )
    artifacts.extend(
        artifact_entry(sandbox_dir, path, "required", "Required per-step result contract")
        for path in result_files
    )
    artifacts.extend(
        artifact_entry(sandbox_dir, path, "reviewer_convenience", "Human-readable review artifact")
        for path in REVIEWER_CONVENIENCE_FILES
        if (sandbox_dir / path).exists()
    )
    artifacts.extend(
        artifact_entry(sandbox_dir, path, "reviewer_convenience", "Per-step console log")
        for path in console_logs
    )

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "runner_version": __version__,
        "generated_at": utc_timestamp(),
        "target": {
            "repository": "AlmaLinux/certifications",
            "path_hint": "systems/<vendor>/<system-or-model>/<run-id>/",
            "note": "Final public layout is decided by the AlmaLinux Certification SIG.",
        },
        "run": {
            "run_id": summary.get("paths", {}).get("run_id") if isinstance(summary.get("paths"), dict) else None,
            "preset": summary.get("preset"),
            "profile": summary.get("profile"),
            "status": summary.get("status"),
            "run_verdict": summary.get("run_verdict"),
            "certification_ready": summary.get("certification_ready"),
        },
        "roles": {
            "required": "Must be present for automated validation.",
            "optional": "May be submitted when relevant and safe to publish.",
            "reviewer_convenience": "Useful for human review, not the primary machine contract.",
        },
        "artifacts": artifacts,
    }


def write_submission_manifest(sandbox_path: Path) -> Path:
    sandbox_dir = resolve_sandbox_dir(sandbox_path)
    manifest = build_submission_manifest(sandbox_dir)
    manifest_path = sandbox_dir / MANIFEST_RELATIVE_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def validate_submission(sandbox_path: Path, *, write_manifest: bool = False) -> ValidationReport:
    sandbox_dir = resolve_sandbox_dir(sandbox_path)
    issues: list[ValidationIssue] = []
    manifest_path = sandbox_dir / MANIFEST_RELATIVE_PATH

    if write_manifest:
        try:
            manifest_path = write_submission_manifest(sandbox_dir)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(ValidationIssue("error", f"failed to write submission manifest: {exc}"))
            return ValidationReport(sandbox_dir, manifest_path, tuple(issues))
    elif not manifest_path.exists():
        issues.append(
            ValidationIssue(
                "warning",
                "submission manifest is missing; run `hcs validate-run --write-manifest <sandbox>`",
            )
        )

    for relative_path in REQUIRED_RUNNER_FILES:
        if not (sandbox_dir / relative_path).is_file():
            issues.append(ValidationIssue("error", f"missing required artifact: {relative_path.as_posix()}"))

    summary_path = sandbox_dir / "runner" / "run.summary.json"
    summary: dict[str, object] = {}
    if summary_path.exists():
        try:
            summary = load_json(summary_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(ValidationIssue("error", f"invalid run.summary.json: {exc}"))
    for key in ("run_verdict", "certification_ready", "result_contract"):
        if summary and key not in summary:
            issues.append(ValidationIssue("error", f"run.summary.json is missing `{key}`"))

    contract = summary.get("result_contract")
    if isinstance(contract, dict):
        for reason in contract.get("blocking_reasons", []):
            issues.append(ValidationIssue("warning", f"certification readiness blocker: {reason}"))
    if summary.get("certification_ready") is False:
        issues.append(ValidationIssue("warning", "run.summary.json marks certification_ready=false"))

    result_files = relative_files(sandbox_dir, ("runner/tests/*/*.result.json",))
    summary_results = summary.get("results", [])
    if isinstance(summary_results, list) and len(result_files) < len(summary_results):
        issues.append(
            ValidationIssue(
                "error",
                f"found {len(result_files)} per-step result files for {len(summary_results)} summary results",
            )
        )

    if manifest_path.exists():
        try:
            manifest = load_json(manifest_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(ValidationIssue("error", f"invalid submission.manifest.json: {exc}"))
        else:
            for artifact in manifest.get("artifacts", []):
                if not isinstance(artifact, dict):
                    issues.append(ValidationIssue("error", "manifest artifact entry must be an object"))
                    continue
                path_value = artifact.get("path")
                if not isinstance(path_value, str):
                    issues.append(ValidationIssue("error", "manifest artifact entry is missing path"))
                    continue
                try:
                    artifact_path = manifest_artifact_path(sandbox_dir, path_value)
                except ValueError as exc:
                    issues.append(ValidationIssue("error", str(exc)))
                    continue
                if artifact.get("required") is True and not artifact_path.is_file():
                    issues.append(ValidationIssue("error", f"manifest required artifact is missing: {path_value}"))
                expected_sha = artifact.get("sha256")
                if isinstance(expected_sha, str) and artifact_path.is_file():
                    actual_sha = sha256_file(artifact_path)
                    if actual_sha != expected_sha:
                        issues.append(ValidationIssue("error", f"manifest sha256 mismatch: {path_value}"))

    return ValidationReport(sandbox_dir, manifest_path, tuple(issues))
