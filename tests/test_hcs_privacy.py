from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hcs.__main__ import main
from hcs.privacy import audit_artifacts, scan_line


class PrivacyAuditTests(unittest.TestCase):
    def test_scan_line_detects_and_redacts_sensitive_identifiers(self) -> None:
        findings = scan_line(
            "runner/run.summary.json",
            7,
            "Serial Number: ABC123 mac 52:54:00:12:34:56 ip 10.0.0.5 disk wwn-0xabc",
        )

        categories = {finding.category for finding in findings}
        self.assertIn("serial", categories)
        self.assertIn("mac_address", categories)
        self.assertIn("ip_address", categories)
        self.assertIn("storage_id", categories)
        self.assertTrue(all("ABC123" not in finding.sample for finding in findings))
        self.assertTrue(all("52:54:00:12:34:56" not in finding.sample for finding in findings))
        self.assertTrue(all("10.0.0.5" not in finding.sample for finding in findings))

    def test_loopback_ip_is_not_reported(self) -> None:
        findings = scan_line("runner/config.requested.json", 1, '"inventory": "127.0.0.1,"')

        self.assertEqual(findings, [])

    def test_audit_artifacts_scans_text_files_under_sandbox(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            runner = sandbox / "runner"
            runner.mkdir(parents=True)
            (runner / "run.summary.json").write_text("Local IP: 192.168.122.10\n", encoding="utf-8")
            (runner / "blob.bin").write_bytes(b"Serial Number: ABC123")

            audit = audit_artifacts(sandbox)

        self.assertFalse(audit.ok)
        self.assertEqual(len(audit.findings), 1)
        self.assertEqual(audit.findings[0].category, "ip_address")

    def test_cli_audit_artifacts_returns_one_when_findings_exist(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            runner = sandbox / "runner"
            runner.mkdir(parents=True)
            (runner / "run.summary.json").write_text("MAC: 52:54:00:12:34:56\n", encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                rc = main(["audit-artifacts", str(sandbox)])

        self.assertEqual(rc, 1)

    def test_cli_audit_artifacts_returns_zero_without_findings(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "run"
            runner = sandbox / "runner"
            runner.mkdir(parents=True)
            (runner / "run.summary.json").write_text("inventory: 127.0.0.1\n", encoding="utf-8")

            with redirect_stdout(io.StringIO()):
                rc = main(["audit-artifacts", str(sandbox)])

        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
