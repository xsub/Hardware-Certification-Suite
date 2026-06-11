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

    def test_survives_markup_like_reasons_and_renders_extra_statuses(self) -> None:
        # Reasons are arbitrary role text; <unclosed or </b> sequences used to
        # abort the paragraph parser and the whole PDF was skipped.
        results = [
            dict(SAMPLE_RESULTS[0]),
            {
                "step": 2,
                "test_id": "cpu",
                "display_name": "CPU stress",
                "scope": "required",
                "status": "failed",
                "status_reason": 'stress-ng said: expected <dict>, got </b> & "str"',
                "return_code": 2,
                "duration_seconds": 12.0,
            },
            {
                "step": 3,
                "test_id": "network",
                "display_name": "Network",
                "scope": "required",
                "status": "not_run",
                "status_reason": "not executed: run interrupted",
                "return_code": None,
                "duration_seconds": 0.0,
            },
        ]
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "run.report.pdf"
            written = write_pdf_report(
                out,
                run_id="check-1",
                profile="check",
                preset_name="certification",
                repeat=1,
                status="interrupted",
                started_at="2026-06-11T09:00:00Z",
                finished_at="2026-06-11T09:10:00Z",
                generated_at="2026-06-11T09:10:01Z",
                system_title="almalinux@sut.lab",
                system_facts=SAMPLE_FACTS,
                results=results,
                counts={"passed": 1, "failed": 1, "unsupported": 0, "skipped": 0, "not_run": 1},
                total_seconds=76.2,
                version="0.2.0",
                manual_tests=[
                    ("usb", "required", "Interactive physical-port validation via interactive.yml."),
                    ("pxe", "required", "Interactive boot/network validation via interactive.yml."),
                ],
                inventory="10.0.0.5,",
                required_unexercised=[
                    ("network", "unsupported: needs a distinct SUT <single-host>"),
                    ("phoronix", "not_run: interrupted"),
                ],
            )

            self.assertTrue(written)
            self.assertTrue(out.exists())
            self.assertGreater(out.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
