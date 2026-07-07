from __future__ import annotations

import unittest

from hcs.result_contract import ContractResult, build_result_contract


def result(test_id: str, status: str, *, scope: str = "required") -> ContractResult:
    return ContractResult(
        test_id=test_id,
        status=status,
        status_reason="ok",
        scope=scope,
    )


class ResultContractTests(unittest.TestCase):
    def test_required_passes_without_manual_tests_are_certification_ready(self) -> None:
        contract = build_result_contract(
            status="passed",
            results=[result("hw_detection", "passed")],
            required_unexercised=[],
            manual_tests={},
            dry_run=False,
            interrupted=False,
        )

        self.assertEqual(contract["verdict"], "passed")
        self.assertTrue(contract["certification_ready"])
        self.assertFalse(contract["blocking_reasons"])

    def test_required_unsupported_is_incomplete(self) -> None:
        contract = build_result_contract(
            status="passed_with_warnings",
            results=[result("network", "unsupported")],
            required_unexercised=[
                {"test_id": "network", "reason": "unsupported: needs a distinct SUT"}
            ],
            manual_tests={},
            dry_run=False,
            interrupted=False,
        )

        self.assertEqual(contract["verdict"], "incomplete")
        self.assertFalse(contract["certification_ready"])
        self.assertTrue(contract["review_required"])
        self.assertIn("network required test not exercised", contract["blocking_reasons"][0])

    def test_failed_result_is_not_certification_ready(self) -> None:
        failed = result("cpu", "failed")
        failed = ContractResult(
            test_id=failed.test_id,
            status=failed.status,
            status_reason="stress failed",
            scope=failed.scope,
        )
        contract = build_result_contract(
            status="failed",
            results=[failed],
            required_unexercised=[],
            manual_tests={},
            dry_run=False,
            interrupted=False,
        )

        self.assertEqual(contract["verdict"], "failed")
        self.assertFalse(contract["certification_ready"])
        self.assertIn("cpu failed", contract["blocking_reasons"][0])

    def test_required_manual_tests_keep_automated_report_incomplete(self) -> None:
        contract = build_result_contract(
            status="passed",
            results=[result("hw_detection", "passed")],
            required_unexercised=[],
            manual_tests={"usb": {"required": True, "reason": "physical port validation"}},
            dry_run=False,
            interrupted=False,
        )

        self.assertEqual(contract["verdict"], "incomplete")
        self.assertFalse(contract["certification_ready"])
        self.assertIn("usb required manual test", contract["blocking_reasons"][0])

    def test_optional_warning_does_not_block_required_evidence(self) -> None:
        contract = build_result_contract(
            status="passed_with_warnings",
            results=[
                result("hw_detection", "passed"),
                result("gpu_burn", "unsupported", scope="optional"),
            ],
            required_unexercised=[],
            manual_tests={},
            dry_run=False,
            interrupted=False,
        )

        self.assertEqual(contract["verdict"], "passed")
        self.assertTrue(contract["certification_ready"])
        self.assertTrue(contract["review_required"])
        self.assertIn("gpu_burn optional test", contract["review_notes"][0])

    def test_dry_run_and_interrupted_are_distinct_verdicts(self) -> None:
        dry_run = build_result_contract(
            status="dry_run",
            results=[result("hw_detection", "skipped")],
            required_unexercised=[],
            manual_tests={},
            dry_run=True,
            interrupted=False,
        )
        interrupted = build_result_contract(
            status="interrupted",
            results=[result("hw_detection", "passed")],
            required_unexercised=[],
            manual_tests={},
            dry_run=False,
            interrupted=True,
        )

        self.assertEqual(dry_run["verdict"], "dry_run")
        self.assertEqual(interrupted["verdict"], "interrupted")
        self.assertFalse(dry_run["certification_ready"])
        self.assertFalse(interrupted["certification_ready"])


if __name__ == "__main__":
    unittest.main()
