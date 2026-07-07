from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from hcs.identity import (
    ALMALINUX_ASCII_LOGO,
    DistroIdentity,
    collect_system_summary,
    default_interface,
    distro_logo,
    format_uptime,
    memory_summary,
    parse_meminfo,
    parse_hw_detection_sut_summary,
    parse_os_release,
    sut_summary_from_hw_detection_log,
    swap_summary,
)


class DistroIdentityTests(unittest.TestCase):
    def test_parse_os_release(self) -> None:
        values = parse_os_release(
            """
            NAME="AlmaLinux"
            ID="almalinux"
            PRETTY_NAME="AlmaLinux 10.0"
            """
        )

        self.assertEqual(values["NAME"], "AlmaLinux")
        self.assertEqual(values["ID"], "almalinux")
        self.assertEqual(values["PRETTY_NAME"], "AlmaLinux 10.0")

    def test_almalinux_has_hardcoded_logo_fallback(self) -> None:
        logo = distro_logo(
            DistroIdentity(
                distro_id="almalinux",
                name="AlmaLinux",
                pretty_name="AlmaLinux 10.0",
            ),
            use_fastfetch=False,
        )

        self.assertIsNotNone(logo)
        assert logo is not None
        self.assertTrue(logo.alma_fallback)
        self.assertIn("'c:.", logo.text)
        self.assertEqual(logo.text, ALMALINUX_ASCII_LOGO)

    def test_non_almalinux_without_fastfetch_has_no_logo(self) -> None:
        logo = distro_logo(
            DistroIdentity(
                distro_id="ubuntu",
                name="Ubuntu",
                pretty_name="Ubuntu 24.04",
            ),
            use_fastfetch=False,
        )

        self.assertIsNone(logo)

    def test_memory_and_swap_summaries(self) -> None:
        meminfo = parse_meminfo(
            """
            MemTotal:       2097152 kB
            MemAvailable:   1048576 kB
            SwapTotal:            0 kB
            SwapFree:             0 kB
            """
        )

        self.assertEqual(memory_summary(meminfo), "1.00 GiB / 2.00 GiB (50%)")
        self.assertEqual(swap_summary(meminfo), "Disabled")

    def test_format_uptime(self) -> None:
        self.assertEqual(format_uptime(176460), "2 days, 1 hour, 1 min")

    def test_default_interface_from_proc_route(self) -> None:
        route = (
            "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT\n"
            "eth0 00000000 01020304 0003 0 0 100 00000000 0 0 0\n"
        )
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "route"
            path.write_text(route, encoding="utf-8")

            self.assertEqual(default_interface(path), "eth0")

    def test_collect_system_summary_includes_supplied_os(self) -> None:
        summary = collect_system_summary(
            DistroIdentity(
                distro_id="almalinux",
                name="AlmaLinux",
                pretty_name="AlmaLinux 10.0",
            )
        )

        self.assertTrue(summary.title)
        self.assertEqual(summary.facts[0].label, "OS")
        self.assertIn("AlmaLinux 10.0", summary.facts[0].value)

    def test_parse_hw_detection_sut_summary_omits_secret_identifiers(self) -> None:
        summary = parse_hw_detection_sut_summary(
            """
            \x1b[0;31mSystem Report\x1b[0m
            System Information
                Manufacturer: Supermicro
                Product Name: SYS-121H-TNR
                Version: 0123456789
                Serial Number: SECRET-SERIAL
                UUID: 11111111-2222-3333-4444-555555555555
                Family: Rack Mount
            Base Board Report
            """
        )

        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary.title, "Supermicro SYS-121H-TNR 0123456789")
        facts = {fact.label: fact.value for fact in summary.facts}
        self.assertEqual(facts["Source"], "logs/hw_detection.log")
        self.assertEqual(facts["Manufacturer"], "Supermicro")
        self.assertEqual(facts["Product"], "SYS-121H-TNR")
        joined = "\n".join(facts.values())
        self.assertNotIn("SECRET-SERIAL", joined)
        self.assertNotIn("11111111-2222-3333-4444-555555555555", joined)

    def test_sut_summary_from_hw_detection_log(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "hw_detection.log"
            path.write_text(
                "System Report\nSystem Information\n    Manufacturer: Alma\n    Product Name: LabBox\n",
                encoding="utf-8",
            )

            summary = sut_summary_from_hw_detection_log(path)

        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary.title, "Alma LabBox")


if __name__ == "__main__":
    unittest.main()
