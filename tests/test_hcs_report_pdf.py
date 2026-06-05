from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hcs.report_pdf import REPORTLAB_AVAILABLE, _human_duration, write_pdf_report


SAMPLE_FACTS = [
    ("OS", "AlmaLinux 10.2 (Lavender Lion) x86_64"),
    ("CPU", "Intel Xeon Gold 6438N (128 logical CPUs)"),
    ("Memory", "42.1 GiB / 503.4 GiB (8%)"),
]
SAMPLE_RESULTS = [
    {
        "step": 1,
        "test_id": "hw_detection",
        "display_name": "Hardware detection",
        "scope": "required",
        "status": "passed",
        "status_reason": "ok",
        "return_code": 0,
        "duration_seconds": 64.2,
    },
    {
        "step": 2,
        "test_id": "network",
        "display_name": "Network",
        "scope": "required",
        "status": "unsupported",
        "status_reason": "network test needs a distinct SUT (local/single-host run)",
        "return_code": 0,
        "duration_seconds": 22.3,
    },
]


class HumanDurationTests(unittest.TestCase):
    def test_formats(self) -> None:
        self.assertEqual(_human_duration(45), "45s")
        self.assertEqual(_human_duration(125), "2m 5s")
        self.assertEqual(_human_duration(10487), "2h 54m")


@unittest.skipUnless(REPORTLAB_AVAILABLE, "reportlab not installed")
class WritePdfReportTests(unittest.TestCase):
    def test_writes_a_pdf_file(self) -> None:
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "run.report.pdf"
            written = write_pdf_report(
                out,
                run_id="long-31bda138",
                profile="long",
                preset_name="certification",
                repeat=1,
                status="passed_with_warnings",
                started_at="2026-06-05T09:14:02Z",
                finished_at="2026-06-05T12:41:55Z",
                generated_at="2026-06-05T12:41:56Z",
                system_title="almalinux@sut.lab",
                system_facts=SAMPLE_FACTS,
                results=SAMPLE_RESULTS,
                counts={"passed": 1, "failed": 0, "unsupported": 1, "skipped": 0},
                total_seconds=86.5,
                version="0.2.0",
            )

            self.assertTrue(written)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1000)
            with out.open("rb") as handle:
                self.assertTrue(handle.read(5).startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
