"""Pre-run safety checks for the HCS runner."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import sys

from .profiles import PROFILES
from .runner import RunnerOptions
from .submission import validate_submission


MIN_FREE_BYTES = 5 * 1024 * 1024 * 1024


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class PreflightReport:
    checks: tuple[PreflightCheck, ...]

    @property
    def errors(self) -> tuple[PreflightCheck, ...]:
        return tuple(check for check in self.checks if check.status == "error")

    @property
    def warnings(self) -> tuple[PreflightCheck, ...]:
        return tuple(check for check in self.checks if check.status == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors


def check(name: str, status: str, message: str) -> PreflightCheck:
    return PreflightCheck(name=name, status=status, message=message)


def nearest_existing_parent(path: Path) -> Path:
    candidate = path.expanduser()
    if candidate.exists():
        return candidate if candidate.is_dir() else candidate.parent
    for parent in candidate.parents:
        if parent.exists():
            return parent
    return Path("/")


def selected_test_ids(options: RunnerOptions) -> tuple[str, ...]:
    if options.selected_tests is not None:
        return options.selected_tests
    return PROFILES[options.profile].tests


def run_preflight(options: RunnerOptions) -> PreflightReport:
    checks: list[PreflightCheck] = []
    tests = set(selected_test_ids(options))

    if sys.version_info >= (3, 9):
        checks.append(check("python", "ok", f"Python {sys.version_info.major}.{sys.version_info.minor}"))
    else:
        checks.append(check("python", "error", "Python 3.9 or newer is required"))

    if shutil.which("ansible-playbook"):
        checks.append(check("ansible", "ok", "ansible-playbook is available"))
    else:
        checks.append(check("ansible", "error", "ansible-playbook was not found on PATH"))

    if options.playbook.exists():
        checks.append(check("playbook", "ok", f"playbook exists: {options.playbook}"))
    else:
        checks.append(check("playbook", "error", f"playbook not found: {options.playbook}"))

    parent = nearest_existing_parent(options.paths.sandbox_dir)
    if os.access(parent, os.W_OK):
        checks.append(check("sandbox", "ok", f"sandbox parent is writable: {parent}"))
    else:
        checks.append(check("sandbox", "error", f"sandbox parent is not writable: {parent}"))

    try:
        usage = shutil.disk_usage(parent)
    except OSError as exc:
        checks.append(check("disk", "warning", f"could not inspect free space at {parent}: {exc}"))
    else:
        if usage.free >= MIN_FREE_BYTES:
            checks.append(check("disk", "ok", f"{usage.free // (1024 ** 3)} GiB free at {parent}"))
        else:
            checks.append(check("disk", "warning", f"less than 5 GiB free at {parent}"))

    if options.connection == "local" and (not tests or "hw_detection" in tests):
        geteuid = getattr(os, "geteuid", None)
        if geteuid is not None and geteuid() != 0:
            checks.append(
                check(
                    "privileges",
                    "warning",
                    "local hw_detection needs root to read SMBIOS/DMI; run as root or target a remote SUT",
                )
            )
        else:
            checks.append(check("privileges", "ok", "local privilege check passed"))

    if "network" in tests:
        if options.connection == "local":
            checks.append(check("network", "warning", "network test needs a distinct remote SUT"))
        elif options.network_endpoints:
            checks.append(
                check(
                    "network",
                    "ok",
                    f"explicit endpoints LTS {options.network_endpoints['lts_ip']} -> SUT {options.network_endpoints['sut_ip']}",
                )
            )
        else:
            checks.append(
                check(
                    "network",
                    "warning",
                    "network endpoints will be inferred from the SSH session; prefer --lts-ip/--sut-ip",
                )
            )

    accelerator_tests = tests.intersection({"gpu_burn", "ai_llm"})
    if accelerator_tests:
        checks.append(
            check(
                "accelerator",
                "warning",
                f"{', '.join(sorted(accelerator_tests))} is optional accelerator evidence, not core certification scope",
            )
        )
    if "ai_llm" in tests:
        ai_extra = {
            **options.extra_vars,
            **options.test_extra_vars.get("ai_llm", {}),
            **options.cli_extra_vars,
        }
        if ai_extra.get("ai_llm_submission_evidence") in {"1", "true", "True", "yes", "on"}:
            if not ai_extra.get("ai_llm_model_sha256"):
                checks.append(
                    check(
                        "ai_llm",
                        "error",
                        "ai_llm_submission_evidence=true requires ai_llm_model_sha256",
                    )
                )
        elif not ai_extra.get("ai_llm_model_sha256"):
            checks.append(
                check(
                    "ai_llm",
                    "warning",
                    "AI benchmark has no model checksum; keep it experimental or set ai_llm_submission_evidence=true with ai_llm_model_sha256",
                )
            )

    if (options.paths.runner_dir / "run.summary.json").exists():
        validation = validate_submission(options.paths.sandbox_dir)
        if validation.ok:
            checks.append(check("submission", "ok", "existing run artifacts are structurally valid"))
        else:
            checks.append(
                check(
                    "submission",
                    "error",
                    f"existing run artifacts have {len(validation.errors)} validation error(s)",
                )
            )
        for warning in validation.warnings[:5]:
            checks.append(check("submission", "warning", warning.message))
    else:
        checks.append(check("submission", "ok", "no existing run summary to validate"))

    return PreflightReport(checks=tuple(checks))
