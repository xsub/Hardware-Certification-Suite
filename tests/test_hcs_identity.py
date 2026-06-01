from __future__ import annotations

import unittest

from hcs.identity import ALMALINUX_ASCII_LOGO, DistroIdentity, distro_logo, parse_os_release


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


if __name__ == "__main__":
    unittest.main()
