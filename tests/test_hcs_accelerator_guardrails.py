from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from hcs.config import build_sandbox_paths
from hcs.preflight import run_preflight
from hcs.runner import RunnerOptions


ROOT = Path(__file__).resolve().parents[1]


def ai_env(tmp: str, **overrides: str) -> dict[str, str]:
    env = os.environ.copy()
    root = Path(tmp)
    env.update(
        {
            "HCS_AI_LLM_SUBMISSION_EVIDENCE": "true",
            "HCS_AI_LLM_BUILD_FROM_SOURCE": "false",
            "HCS_AI_LLM_DOWNLOAD_MODEL": "false",
            "HCS_AI_LLM_LOG_FILE": str(root / "ai-llm.log"),
            "HCS_AI_LLM_RESULT_FILE": str(root / "ai-llm.result.json"),
            "HCS_AI_LLM_BENCH_JSON_FILE": str(root / "ai-llm.llama-bench.json"),
            "HCS_AI_LLM_MODEL_DIR": str(root / "models"),
            "HCS_AI_LLM_SOURCE_DIR": str(root / "llama.cpp"),
        }
    )
    env.update(overrides)
    return env


class AcceleratorGuardrailTests(unittest.TestCase):
    def test_ai_submission_evidence_requires_model_checksum(self) -> None:
        with TemporaryDirectory() as tmp:
            completed = subprocess.run(
                ["bash", str(ROOT / "tests" / "ai_llm" / "run_test.sh")],
                check=False,
                env=ai_env(tmp),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            result = json.loads((Path(tmp) / "ai-llm.result.json").read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 4)
        self.assertEqual(result["status"], "failed")
        self.assertIn("requires ai_llm_model_sha256", result["status_reason"])

    def test_ai_submission_evidence_rejects_unpinned_source_ref(self) -> None:
        with TemporaryDirectory() as tmp:
            completed = subprocess.run(
                ["bash", str(ROOT / "tests" / "ai_llm" / "run_test.sh")],
                check=False,
                env=ai_env(
                    tmp,
                    HCS_AI_LLM_MODEL_SHA256="0" * 64,
                    HCS_AI_LLM_SOURCE_REF="master",
                ),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            result = json.loads((Path(tmp) / "ai-llm.result.json").read_text(encoding="utf-8"))

        self.assertEqual(completed.returncode, 4)
        self.assertIn("requires a pinned ai_llm_source_ref", result["status_reason"])

    @mock.patch("hcs.preflight.shutil.which", return_value="/usr/bin/ansible-playbook")
    def test_preflight_errors_for_submit_ai_without_model_checksum(self, _which: object) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            playbook = root / "automated.yml"
            playbook.write_text("---\n", encoding="utf-8")
            options = RunnerOptions(
                preset_name=None,
                profile="check",
                inventory="127.0.0.1,",
                connection="local",
                playbook=playbook,
                paths=build_sandbox_paths(
                    config={},
                    profile="check",
                    base_dir=root,
                    sandbox_dir=root / "run",
                    run_id="ai",
                ),
                extra_vars={"ai_llm_submission_evidence": "true"},
                selected_tests=("ai_llm",),
                test_profiles={},
                test_extra_vars={},
                test_scopes={},
                repeat=1,
                dry_run=False,
                stop_on_failure=False,
            )

            report = run_preflight(options)

        self.assertFalse(report.ok)
        self.assertTrue(any(check.name == "ai_llm" for check in report.errors))


if __name__ == "__main__":
    unittest.main()
