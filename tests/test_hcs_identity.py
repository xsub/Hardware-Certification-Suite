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
    parse_os_release,
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


if __name__ == "__main__":
    unittest.main()
