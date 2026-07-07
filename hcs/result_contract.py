"""Machine-readable result contract helpers for HCS run artifacts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


RESULT_CONTRACT_VERSION = 1
PASS_FAIL_STATUSES = {"passed", "failed"}


@dataclass(frozen=True)
class ContractResult:
    """Small status view used to evaluate certification evidence completeness."""

    test_id: str
    status: str
    status_reason: str
    scope: str


def required_manual_tests(manual_tests: Mapping[str, Mapping[str, object]]) -> list[dict[str, str]]:
    required: list[dict[str, str]] = []
    for test_id, info in manual_tests.items():
        if info.get("required") is True:
            required.append(
                {
                    "test_id": str(test_id),
                    "reason": str(info.get("reason", "required manual test")),
                }
            )
    return required


def build_result_contract(
    *,
    status: str,
    results: Sequence[ContractResult],
    required_unexercised: Sequence[Mapping[str, str]],
    manual_tests: Mapping[str, Mapping[str, object]],
    dry_run: bool,
    interrupted: bool,
) -> dict[str, object]:
    """Return the stable verdict contract embedded in ``run.summary.json``.

    ``status`` remains the backwards-compatible runner headline. The contract
    separates that operational status from certification evidence readiness.
    """

    blocking_reasons: list[str] = []
    review_notes: list[str] = []

    if dry_run:
        blocking_reasons.append("dry-run did not execute automated tests")
    if interrupted:
        blocking_reasons.append("run was interrupted before the planned test set completed")

    failed_results = [result for result in results if result.status == "failed"]
    for result in failed_results:
        blocking_reasons.append(
            f"{result.test_id} failed: {result.status_reason or 'no reason recorded'}"
        )

    for entry in required_unexercised:
        test_id = entry.get("test_id", "unknown")
        reason = entry.get("reason", "required test did not produce a pass/fail verdict")
        blocking_reasons.append(f"{test_id} required test not exercised: {reason}")

    manual_required = required_manual_tests(manual_tests)
    for entry in manual_required:
        blocking_reasons.append(
            f"{entry['test_id']} required manual test not covered by runner: {entry['reason']}"
        )

    if not results:
        blocking_reasons.append("no automated test results were recorded")

    for result in results:
        if result.scope == "required" or result.status in PASS_FAIL_STATUSES:
            continue
        review_notes.append(
            f"{result.test_id} optional test reported {result.status}: "
            f"{result.status_reason or 'no reason recorded'}"
        )

    if dry_run:
        verdict = "dry_run"
    elif interrupted:
        verdict = "interrupted"
    elif failed_results:
        verdict = "failed"
    elif required_unexercised or manual_required or not results:
        verdict = "incomplete"
    else:
        verdict = "passed"

    certification_ready = verdict == "passed"
    review_required = bool(blocking_reasons or review_notes or status == "passed_with_warnings")
    return {
        "schema_version": RESULT_CONTRACT_VERSION,
        "verdict": verdict,
        "certification_ready": certification_ready,
        "review_required": review_required,
        "blocking_reasons": blocking_reasons,
        "review_notes": review_notes,
    }
