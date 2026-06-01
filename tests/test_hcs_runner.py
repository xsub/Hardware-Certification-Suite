from __future__ import annotations

import unittest

from hcs.runner import UNSUPPORTED_RE, StepResult, parse_recap_line, run_status


def step(status: str) -> StepResult:
    return StepResult(
        step=1,
        pass_index=1,
        pass_count=1,
        test_id="example",
        display_name="Example",
        status=status,
        status_reason="ok",
        return_code=0,
        started_at="2026-06-01T00:00:00Z",
        finished_at="2026-06-01T00:00:01Z",
        duration_seconds=1.0,
        command=[],
        artifacts=[],
        ansible_recap={},
    )


class RunnerStatusTests(unittest.TestCase):
    def test_run_status_marks_unsupported_as_warning(self) -> None:
        self.assertEqual(run_status([step("passed"), step("unsupported")]), "passed_with_warnings")

    def test_run_status_failed_wins(self) -> None:
        self.assertEqual(run_status([step("unsupported"), step("failed")]), "failed")

    def test_parse_recap_line(self) -> None:
        parsed = parse_recap_line(
            "127.0.0.1 : ok=8 changed=3 unreachable=0 failed=0 skipped=1 rescued=0 ignored=0"
        )

        self.assertIsNotNone(parsed)
        assert parsed is not None
        host, stats = parsed
        self.assertEqual(host, "127.0.0.1")
        self.assertEqual(stats["ok"], 8)
        self.assertEqual(stats["skipped"], 1)

    def test_unsupported_marker_can_be_seen_in_ansible_debug_output(self) -> None:
        match = UNSUPPORTED_RE.search('    "msg": "HCS_UNSUPPORTED: nvidia-smi not found"')

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.group("reason"), "nvidia-smi not found")


if __name__ == "__main__":
    unittest.main()
