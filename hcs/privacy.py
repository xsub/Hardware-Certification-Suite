"""Artifact privacy audit helpers for public certification submissions."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from pathlib import Path
import re

from .submission import resolve_sandbox_dir


TEXT_SUFFIXES = {".json", ".txt", ".log", ".yml", ".yaml", ".md"}
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_FINDINGS_PER_FILE = 20


@dataclass(frozen=True)
class PrivacyFinding:
    category: str
    severity: str
    path: str
    line: int
    sample: str


@dataclass(frozen=True)
class PrivacyAudit:
    sandbox_dir: Path
    findings: tuple[PrivacyFinding, ...]

    @property
    def ok(self) -> bool:
        return not self.findings


@dataclass(frozen=True)
class LinePattern:
    category: str
    severity: str
    regex: re.Pattern[str]


LINE_PATTERNS = (
    LinePattern(
        "serial",
        "warning",
        re.compile(
            r"\b(?:serial(?:\s+number)?|system serial|chassis serial|dmi serial)\b"
            r"\s*[:=]\s*[\"']?[^\"'\s,;]+",
            re.IGNORECASE,
        ),
    ),
    LinePattern(
        "dmi_uuid",
        "warning",
        re.compile(
            r"\b(?:uuid|dmi uuid)\b\s*[:=]\s*[\"']?"
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            re.IGNORECASE,
        ),
    ),
    LinePattern(
        "hostname",
        "warning",
        re.compile(r"\b(?:host|hostname|nodename)\b\s*[:=]\s*[\"']?[^\"'\s,;]+", re.IGNORECASE),
    ),
    LinePattern(
        "storage_id",
        "warning",
        re.compile(r"\b(?:wwn-|nvme-eui\.|ata-[A-Za-z0-9_.-]+|scsi-[A-Za-z0-9_.:-]+)", re.IGNORECASE),
    ),
)

MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def is_text_artifact(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def should_scan(path: Path) -> bool:
    if not path.is_file() or not is_text_artifact(path):
        return False
    try:
        return path.stat().st_size <= MAX_FILE_BYTES
    except OSError:
        return False


def redact_sample(line: str) -> str:
    redacted = MAC_RE.sub("<mac>", line)
    redacted = IPV4_RE.sub("<ip>", redacted)
    for pattern in LINE_PATTERNS:
        redacted = pattern.regex.sub(f"<{pattern.category}>", redacted)
    return redacted.strip()[:240]


def ipv4_findings(line: str) -> bool:
    for match in IPV4_RE.finditer(line):
        try:
            address = ipaddress.ip_address(match.group(0))
        except ValueError:
            continue
        if address.is_loopback or address.is_unspecified or address.is_multicast:
            continue
        return True
    return False


def scan_line(relative_path: str, line_no: int, line: str) -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    sample = redact_sample(line)
    if MAC_RE.search(line):
        findings.append(PrivacyFinding("mac_address", "warning", relative_path, line_no, sample))
    if ipv4_findings(line):
        findings.append(PrivacyFinding("ip_address", "warning", relative_path, line_no, sample))
    for pattern in LINE_PATTERNS:
        if pattern.regex.search(line):
            findings.append(PrivacyFinding(pattern.category, pattern.severity, relative_path, line_no, sample))
    return findings


def audit_artifacts(sandbox_path: Path) -> PrivacyAudit:
    sandbox_dir = resolve_sandbox_dir(sandbox_path)
    findings: list[PrivacyFinding] = []
    for path in sorted(sandbox_dir.rglob("*")):
        if not should_scan(path):
            continue
        relative_path = path.relative_to(sandbox_dir).as_posix()
        file_findings = 0
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line_no, line in enumerate(handle, start=1):
                    line_findings = scan_line(relative_path, line_no, line)
                    if not line_findings:
                        continue
                    findings.extend(line_findings)
                    file_findings += len(line_findings)
                    if file_findings >= MAX_FINDINGS_PER_FILE:
                        findings.append(
                            PrivacyFinding(
                                "limit",
                                "warning",
                                relative_path,
                                line_no,
                                "additional privacy findings suppressed for this file",
                            )
                        )
                        break
        except OSError:
            continue
    return PrivacyAudit(sandbox_dir=sandbox_dir, findings=tuple(findings))
