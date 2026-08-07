from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "telemetry"
FORBIDDEN_KEYS = {
    "prompt",
    "query",
    "question",
    "answer",
    "note_body",
    "body",
    "excerpt",
    "raw_input",
    "raw_output",
    "tool_input",
    "tool_output",
    "transcript_path",
}


class ContractsAndPrivacyTest(unittest.TestCase):
    def test_json_contracts_and_template_are_valid(self) -> None:
        for path in (
            ROOT / "contracts" / "telemetry-v1.schema.json",
            ROOT / "contracts" / "vault-config-v1.schema.json",
            ROOT / "templates" / "para-kb.config.json",
        ):
            with self.subTest(path=path):
                self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_canonical_fixtures_use_safe_fields_and_relative_paths(self) -> None:
        canonical = [FIXTURES / "query-v1.jsonl", FIXTURES / "build-v1.jsonl"]
        for path in canonical:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                record = json.loads(line)
                with self.subTest(path=path, line=line_number):
                    self.assertEqual(record["schema"], "para-kb.telemetry")
                    self.assertEqual(record["schema_version"], 1)
                    self.assertFalse(FORBIDDEN_KEYS.intersection(record))
                    for key, value in record.items():
                        if key.endswith("_paths") or key in {"entrypoints", "vault_paths"}:
                            self.assertTrue(all(not item.startswith(("/", "~")) for item in value))

    def test_public_source_has_no_workstation_specific_identity_or_vault_path(self) -> None:
        patterns = [
            re.compile("/" + "Users/" + r"[A-Za-z0-9._-]+/"),
            re.compile("/" + "home/" + r"[A-Za-z0-9._-]+/"),
            re.compile("iCloud~md~" + "obsidian"),
        ]
        offenders: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if any(pattern.search(text) for pattern in patterns):
                offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
