# PARA Knowledge Base interoperability contract

This directory is the producer contract shared by PARA Knowledge Base runtimes and optional local consumers such as the independent [PARA Second Brain Viz Obsidian plugin](https://github.com/ernestolee13/para-second-brain-viz). The contract is deliberately runtime-neutral: Claude Code, Codex, or another wrapper may emit the same records without exposing prompts or note contents.

## Versions

- `vault-config-v1.schema.json` describes `.para-kb/config.json`.
- `telemetry-v1.schema.json` describes canonical JSONL records.
- Producers write `schema: "para-kb.telemetry"` and `schema_version: 1`.
- Consumers must ignore unknown optional fields from a newer compatible producer and warn, rather than silently treating an unknown schema as fully supported.

## Operation lifecycle

Query and build telemetry use explicit operation boundaries:

```text
QueryStart -> OperationStep* -> QuerySummary -> QueryComplete
BuildStart -> OperationStep* -> BuildSummary -> BuildComplete
```

`Summary` is the semantic boundary populated by a skill. `Complete` is the runtime measurement boundary, normally emitted by the Stop hook. `Stop` is an optional turn-level diagnostic and must never be relabeled as one query or ingest duration.

The shared hooks remain silent for ordinary agent turns. They emit `OperationStep`, `Complete`, or diagnostic `Stop` records only after a skill or compatible caller has opened an explicit query/build operation.

Every operation has one opaque `operation_id`. `request_id` links operations created in the same agent request without merging them. `session_id` is optional. Version 0.4.x `query_id` remains a consumer alias for `request_id`; v1 producers do not emit it.

## Privacy boundary

Telemetry is local operational metadata, not knowledge content.

Allowed:

- opaque IDs and timestamps
- vault-relative Markdown or JSONL paths
- route, tool name, counts, validation state, and confidence
- measured duration/token fields with an explicit reliability marker

Forbidden:

- prompt, question, query, answer, note body, summary text, or copied excerpt
- absolute home/vault paths
- raw hook input, raw tool input, or raw tool output
- credentials, environment dumps, or transcript paths

The bundled emitter uses an allowlist and fails closed when it cannot locate a valid vault/config. Public fixtures are synthetic and must never be derived from a user's active telemetry.

## Configuration discovery

The emitter resolves configuration in this order:

1. `--config`
2. `PARA_KB_CONFIG`
3. nearest parent `.para-kb/config.json`
4. conservative in-memory detection from a parent containing `.obsidian`
5. no logging

The config never stores an absolute vault root. All paths are relative to the directory containing `.para-kb/`.

## Compatibility aliases

Consumers may accept these v0.4.x aliases while producers emit only v1 names:

| Legacy | Canonical v1 |
| --- | --- |
| `query_id` | `request_id` |
| `PostToolUse`, `ToolCall` | `OperationStep` |
| `query-complete` CLI | `query-summary` CLI |
| `build-complete` CLI | `build-summary` CLI |
| `total_reported_tokens` | `token_total_for_analysis` |

Missing or inseparable measurements are `null` with `token_reliability: "none"`; they are never fabricated as zero.
