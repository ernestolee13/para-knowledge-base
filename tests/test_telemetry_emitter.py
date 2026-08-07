from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import para_kb_telemetry as telemetry


class TelemetryEmitterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "Synthetic Vault"
        self.root.mkdir()
        (self.root / ".obsidian").mkdir()
        for folder in ("0. Common", "1. Projects", "2. Areas", "3. Resources", "4. Archive", "Inbox"):
            (self.root / folder).mkdir()
        telemetry.initialize_config(str(self.root), "numbered")
        self.context = telemetry.load_context(None, str(self.root))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def records(self) -> list[dict[str, object]]:
        return [json.loads(line) for line in self.context.telemetry_path.read_text(encoding="utf-8").splitlines()]

    def test_query_lifecycle_is_canonical_and_content_free(self) -> None:
        started = telemetry.start_operation(
            self.context,
            {"source": "kb-query-skill", "request_id": "request-test", "query": "must not survive"},
            "query",
        )
        operation_id = started["operation_id"]
        telemetry.hook_posttool(
            self.context,
            {
                "request_id": "request-test",
                "tool_name": "read",
                "tool_input": {"path": str(self.root / "1. Projects" / "alpha.md"), "prompt": "private"},
                "tool_output": {"path": "/outside/private.md", "body": "private"},
                "duration_ms": 25,
            },
        )
        telemetry.write_query_summary(
            self.context,
            {
                "operation_id": operation_id,
                "request_type": "lookup",
                "route": ["A:direct-folder"],
                "entrypoints": ["1. Projects/_index.md"],
                "documents_read_paths": ["1. Projects/_index.md", "/outside/private.md"],
                "documents_read_count": 1,
                "search_step_count": 1,
                "confidence": "high",
                "query": "must not survive",
            },
        )
        telemetry.hook_stop(self.context, {"request_id": "request-test"})

        records = self.records()
        self.assertEqual(
            [record["event"] for record in records],
            ["QueryStart", "OperationStep", "QuerySummary", "QueryComplete", "Stop"],
        )
        self.assertEqual(records[1]["vault_paths"], ["1. Projects/alpha.md"])
        self.assertEqual(records[2]["documents_read_paths"], ["1. Projects/_index.md"])
        self.assertEqual(records[3]["token_reliability"], "none")
        serialized = json.dumps(records)
        self.assertNotIn("must not survive", serialized)
        self.assertNotIn("/outside/", serialized)

    def test_two_operations_in_one_request_keep_separate_ids_and_no_token_guess(self) -> None:
        query = telemetry.start_operation(
            self.context,
            {"request_id": "request-shared", "total_tokens": 100},
            "query",
        )
        build = telemetry.start_operation(
            self.context,
            {"request_id": "request-shared", "source_kind": "direct", "total_tokens": 120},
            "build",
        )
        telemetry.write_query_summary(
            self.context,
            {
                "operation_id": query["operation_id"],
                "request_type": "lookup",
                "route": ["E:full-text"],
                "entrypoints": [],
                "documents_read_paths": [],
                "search_step_count": 1,
                "confidence": "medium",
            },
        )
        telemetry.write_build_summary(
            self.context,
            {
                "operation_id": build["operation_id"],
                "operation_type": "create",
                "route": "kb-ingest",
                "kb_ingest_used": True,
                "reference_paths": [],
                "created_paths": ["3. Resources/example.md"],
                "updated_paths": [],
                "moved_from_paths": [],
                "moved_to_paths": [],
                "index_paths": ["3. Resources/_index.md"],
                "link_pairs": [],
                "links_added": 0,
                "backlinks_added": 0,
                "frontmatter_completed": 1,
                "summaries_completed": 1,
                "validation": "passed",
                "confidence": "high",
            },
        )
        telemetry.hook_stop(self.context, {"request_id": "request-shared", "total_tokens": 500})

        complete = [record for record in self.records() if record["event"] in {"QueryComplete", "BuildComplete"}]
        self.assertEqual({record["operation_id"] for record in complete}, {query["operation_id"], build["operation_id"]})
        self.assertTrue(all(record["token_total_for_analysis"] is None for record in complete))
        self.assertTrue(all(record["token_reliability"] == "none" for record in complete))

    def test_incomplete_operation_is_not_falsely_completed(self) -> None:
        telemetry.start_operation(self.context, {"request_id": "request-incomplete"}, "query")
        telemetry.hook_stop(self.context, {"request_id": "request-incomplete"})
        records = self.records()
        self.assertNotIn("QueryComplete", [record["event"] for record in records])
        self.assertEqual([record["event"] for record in records], ["QueryStart", "Stop"])
        state = telemetry.load_state(self.context)
        self.assertEqual(state["active_operations"], [])

    def test_non_kb_turn_does_not_emit_telemetry(self) -> None:
        telemetry.hook_userprompt(self.context, {"request_id": "request-plain"})
        telemetry.hook_posttool(
            self.context,
            {"request_id": "request-plain", "tool_name": "read", "tool_input": {"path": "README.md"}},
        )
        telemetry.hook_stop(self.context, {"request_id": "request-plain"})
        self.assertFalse(self.context.telemetry_path.exists())

    def test_explicit_other_request_cannot_capture_or_stop_an_operation(self) -> None:
        started = telemetry.start_operation(self.context, {"request_id": "request-a"}, "query")
        telemetry.hook_posttool(
            self.context,
            {"request_id": "request-b", "tool_name": "read", "tool_input": {"path": "1. Projects/example.md"}},
        )
        telemetry.hook_stop(self.context, {"request_id": "request-b"})
        self.assertEqual([record["event"] for record in self.records()], ["QueryStart"])
        state = telemetry.load_state(self.context)
        self.assertEqual(state["active_operations"][0]["operation_id"], started["operation_id"])

    def test_config_init_is_idempotent_and_supports_custom_roots(self) -> None:
        result = telemetry.initialize_config(str(self.root), "numbered")
        self.assertFalse(result["created"])
        config_path = self.root / ".para-kb/config.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["para_roots"] = {
            "common": "Core/",
            "projects": "Outcomes/",
            "areas": "Responsibilities/",
            "resources": "Library/",
            "archive": "Cold/",
            "inbox": "Capture/",
        }
        config["telemetry"]["active_path"] = "Core/telemetry.jsonl"
        config["telemetry"]["archive_dir"] = "Core/archive"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        loaded = telemetry.load_context(str(config_path), str(self.root))
        self.assertEqual(loaded.telemetry_path.resolve().relative_to(self.root.resolve()).as_posix(), "Core/telemetry.jsonl")

        config["spine_paths"] = ["/outside/private.md"]
        with self.assertRaises(telemetry.TelemetryError):
            telemetry.validate_config(config)

    def test_outside_a_vault_fails_closed_without_creating_files(self) -> None:
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        before = sorted(path.relative_to(outside) for path in outside.rglob("*"))
        with self.assertRaises(telemetry.TelemetryError):
            telemetry.load_context(None, str(outside))
        after = sorted(path.relative_to(outside) for path in outside.rglob("*"))
        self.assertEqual(before, after)

    def test_sanitizer_keeps_only_allowlisted_fields(self) -> None:
        source = self.root / "source.jsonl"
        target = self.root / "sanitized.jsonl"
        source.write_text(
            json.dumps(
                {
                    "schema": telemetry.SCHEMA,
                    "schema_version": 1,
                    "event": "OperationStep",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "source": "test",
                    "operation_id": "operation-test",
                    "operation_kind": "query",
                    "vault_paths": [str(self.root / "1. Projects/example.md"), "/outside/private.md"],
                    "unknown": "drop me",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        result = telemetry.sanitize_file(self.context, source, target)
        self.assertEqual(result, {"ok": True, "written": 1, "skipped": 0})
        record = json.loads(target.read_text(encoding="utf-8"))
        self.assertNotIn("unknown", record)
        self.assertEqual(record["vault_paths"], ["1. Projects/example.md"])

    def test_sanitizer_drops_untyped_nested_content(self) -> None:
        source = self.root / "nested-source.jsonl"
        target = self.root / "nested-sanitized.jsonl"
        source.write_text(
            json.dumps(
                {
                    "schema": telemetry.SCHEMA,
                    "schema_version": 1,
                    "event": "OperationStep",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "source": "test",
                    "operation_id": "operation-test",
                    "operation_kind": "query",
                    "route": {"prompt": "private"},
                    "token_is_operation_delta": "not-a-boolean",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        telemetry.sanitize_file(self.context, source, target)
        record = json.loads(target.read_text(encoding="utf-8"))
        self.assertNotIn("route", record)
        self.assertNotIn("token_is_operation_delta", record)
        self.assertNotIn("private", json.dumps(record))


if __name__ == "__main__":
    unittest.main()
