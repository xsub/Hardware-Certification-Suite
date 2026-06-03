"""Run configuration and sandbox path handling for the HCS runner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
import uuid

import yaml


DEFAULT_BASE_DIR = Path("/var/tmp")
DEFAULT_CONFIG_PATH = Path("hcs-runner.yml")


@dataclass(frozen=True)
class SandboxPaths:
    """Canonical directories owned by one HCS run."""

    run_id: str
    timestamp: str
    sandbox_dir: Path
    runner_dir: Path
    logs_dir: Path
    scratch_dir: Path
    cache_dir: Path
    artifacts_dir: Path
    sut_tests_dir: Path
    phoronix_dir: Path
    ltp_dir: Path

    def as_dict(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "sandbox_dir": str(self.sandbox_dir),
            "runner_dir": str(self.runner_dir),
            "logs_dir": str(self.logs_dir),
            "scratch_dir": str(self.scratch_dir),
            "cache_dir": str(self.cache_dir),
            "artifacts_dir": str(self.artifacts_dir),
            "sut_tests_dir": str(self.sut_tests_dir),
            "phoronix_dir": str(self.phoronix_dir),
            "ltp_dir": str(self.ltp_dir),
        }


def load_config(path: Path | None) -> dict[str, object]:
    if path is None:
        path = Path.cwd() / DEFAULT_CONFIG_PATH
        if not path.exists():
            return {}
    else:
        path = path.expanduser()

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"runner config must be a YAML mapping: {path}")
    return data


def config_section(config: dict[str, object], name: str) -> dict[str, object]:
    section = config.get(name, {})
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ValueError(f"runner config section must be a mapping: {name}")
    return section


def config_path(config: dict[str, object], section: str, key: str) -> Path | None:
    value = config_section(config, section).get(key)
    if value in (None, ""):
        return None
    return Path(str(value))


def config_str(config: dict[str, object], section: str, key: str) -> str | None:
    value = config_section(config, section).get(key)
    if value in (None, ""):
        return None
    return str(value)


def config_extra_vars(config: dict[str, object]) -> dict[str, str]:
    value = config_section(config, "ansible").get("extra_vars", {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("runner config ansible.extra_vars must be a mapping")
    return {str(key): str(raw) for key, raw in value.items()}


def utc_path_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def sanitize_run_id(raw: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", raw).strip(".-")
    return sanitized or uuid.uuid4().hex[:8]


def generated_run_id(profile: str) -> str:
    return sanitize_run_id(f"{profile}-{uuid.uuid4().hex[:8]}")


def sandbox_name(timestamp: str, run_id: str) -> str:
    return f"AlmaLinux-HCS-{timestamp}-RunID-{run_id}"


def sandbox_child(root: Path, configured: str | None, default_name: str) -> Path:
    raw = configured or default_name
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate

    root_resolved = root.resolve(strict=False)
    candidate_resolved = candidate.resolve(strict=False)
    if not candidate_resolved.is_relative_to(root_resolved):
        raise ValueError(f"configured path must stay inside sandbox {root}: {raw}")
    return candidate


def build_sandbox_paths(
    *,
    config: dict[str, object],
    profile: str,
    base_dir: Path | None,
    sandbox_dir: Path | None,
    run_id: str | None,
) -> SandboxPaths:
    paths_cfg = config_section(config, "paths")

    timestamp = utc_path_timestamp()
    final_run_id = sanitize_run_id(run_id or config_str(config, "run", "id") or generated_run_id(profile))
    final_base_dir = base_dir or config_path(config, "run", "base_dir") or DEFAULT_BASE_DIR
    final_sandbox_dir = sandbox_dir or config_path(config, "run", "sandbox_dir")
    if final_sandbox_dir is None:
        final_sandbox_dir = final_base_dir / sandbox_name(timestamp, final_run_id)

    final_sandbox_dir = final_sandbox_dir.expanduser()
    if not final_sandbox_dir.is_absolute():
        final_sandbox_dir = Path.cwd() / final_sandbox_dir

    def path(key: str, default_name: str) -> Path:
        value = paths_cfg.get(key)
        return sandbox_child(final_sandbox_dir, None if value is None else str(value), default_name)

    return SandboxPaths(
        run_id=final_run_id,
        timestamp=timestamp,
        sandbox_dir=final_sandbox_dir,
        runner_dir=path("runner_dir", "runner"),
        logs_dir=path("logs_dir", "logs"),
        scratch_dir=path("scratch_dir", "scratch"),
        cache_dir=path("cache_dir", "cache"),
        artifacts_dir=path("artifacts_dir", "artifacts"),
        sut_tests_dir=path("sut_tests_dir", "sut-tests"),
        phoronix_dir=path("phoronix_dir", "phoronix"),
        ltp_dir=path("ltp_dir", "ltp"),
    )
