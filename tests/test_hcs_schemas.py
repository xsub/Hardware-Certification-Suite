from __future__ import annotations

import json
from importlib import resources
import unittest


class SchemaArtifactTests(unittest.TestCase):
    def test_packaged_json_schemas_parse(self) -> None:
        schema_names = {
            "config.requested.schema.json",
            "run.summary.schema.json",
            "step-result.schema.json",
        }

        for schema_name in schema_names:
            with self.subTest(schema=schema_name):
                schema_path = resources.files("hcs").joinpath("schemas", schema_name)
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(schema["type"], "object")

    def test_run_summary_schema_requires_result_contract(self) -> None:
        schema_path = resources.files("hcs").joinpath("schemas", "run.summary.schema.json")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.assertIn("run_verdict", schema["required"])
        self.assertIn("certification_ready", schema["required"])
        self.assertIn("result_contract", schema["required"])


if __name__ == "__main__":
    unittest.main()
