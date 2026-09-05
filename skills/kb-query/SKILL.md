---
name: kb-query
description: Query the PARA Knowledge Base to find information, synthesize answers from vault documents, inspect recent activity when needed, and record compact query telemetry when configured. Use for any question about Obsidian vault content, projects, references, logs, links, or cross-document analysis.
---

# KB Query

Answer vault-based questions by narrowing the search path before reading full documents. Cite sources with `[[wikilinks]]`. Do not answer from memory alone when the user asks about vault content.

## Core Contract

1. Parse the question: subject, scope, time range, desired output.
2. If query telemetry is configured, start one explicit `kb-query` operation before the first vault lookup and retain the returned `operation_id`.
3. Pick the cheapest route or route combination.
4. Start from indexes, project hubs, tags, backlinks, or short search snippets.
5. Read full documents only when needed for the answer.
6. Synthesize with source `[[wikilinks]]`.
7. Immediately before the final answer, complete that same operation with one semantic `QuerySummary`; the runtime Stop hook then finalizes elapsed time and token deltas including answer generation.

Keep source reading under a small budget by default. Expand only when evidence is insufficient.

## Routes

| Route | Use when | First move |
|---|---|---|
| A. Direct folder | Target project/category is clear | Read the category index or project hub if present, then selected files |
| B. Tag/topic collection | Topic spans folders | Use tag inventory/search, then inspect matched candidates |
| C. Backlink/reference | User asks what cites or depends on something | Use Obsidian backlinks or targeted wikilink search |
| D. Index/log browse | User asks overview, recent activity, trend, or change history | Read relevant index and only the needed log window |
| E. Full-text search | User gives a term, phrase, error, or concept | Use short search/context results before opening files |

Complex questions can combine routes. Example: project status may use Route A for the project hub, Route D for recent `_log.md`, and Route E for a specific term.

## Search Rules

- Do not always start from `0. Common/index.md`; choose the route that best matches the question.
- For project-like names, first try the project hub if the vault uses project hubs (`1. Projects/<slug>/_index.md`) or inspect `1. Projects/_index.md` to resolve the slug. Do not run broad full-text search on the project name before checking indexes.
- For topic-wide questions, prefer tags, backlinks, and short context snippets over reading every match.
- Use `search:context` for specific terms, errors, phrases, or concepts. Avoid high-frequency broad queries such as category names, project names, or large OR patterns unless the output is capped.
- If a first hit-list command returns many files, narrow to candidate paths before requesting context lines. Do not run vault-wide context grep over all matches.
- For recent activity, project `_log.md` files are usually newest-first when the vault uses them. Read from the top.
- For `0. Common/log.md`, parse by `[YYYY-MM-DD]` records and inspect only the requested date range.
- Avoid logs unless the question needs time, change history, trends, or root-cause evidence.
- If the answer is already supported by index/search snippets, do not open more documents just to be exhaustive.
- If a candidate document has no frontmatter `summary` field, read its first paragraph as a lightweight substitute before deciding whether the full document is needed.
- Skip full-body reads for documents with frontmatter `type: data` (large data-style listings — raw exports, link dumps, telemetry-adjacent tables). Read only their frontmatter and `summary` (or first-paragraph fallback) to judge relevance; open the full body only if the user explicitly asks for its contents.

## Obsidian CLI

Prefer Obsidian CLI when available because it returns resolved graph/search results cheaply.

```bash
obsidian vault="<vault name>" search:context query="term"
obsidian vault="<vault name>" tag name="#proj/example"
obsidian vault="<vault name>" backlinks file="Document Name"
obsidian vault="<vault name>" read path="1. Projects/example/_index.md"
```

If the active vault is reliable, the `vault="..."` argument may be omitted. If CLI reports that it cannot find Obsidian, retry once with `vault="<vault name>"`; then fall back to `rg`/limited file reads instead of debugging the CLI during the query.

Fallback hierarchy: index/hub -> tag or filename hit list -> short context snippet -> target section -> full document.

## Response Rules

- Give the direct answer first.
- Cite material evidence using `[[wikilinks]]`; include file paths only when needed for disambiguation.
- Separate evidence from inference when the answer depends on partial search results.
- If useful synthesis should become a durable note, suggest saving it and follow `kb-ingest`/vault write rules only after the user wants that.

## Query Telemetry

Query telemetry is optional. This skill defines the record shape and semantic summary guidance; runtime hooks, wrappers, or local automation must perform any reliable numeric capture. When configured, write query-related operational records to `0. Common/.telemetry/query-telemetry.jsonl`. Do not create multiple query-log files. The telemetry file is not a knowledge note, is not indexed, and is not read during normal vault search.

Hooks or wrappers should record numeric data when possible:
- request id
- timestamps and elapsed time
- tool calls and tool durations
- input/output byte sizes
- model token usage when available

The skill should not hand-estimate numeric cost fields. It opens an explicit operation boundary before retrieval, then adds one compact semantic `QuerySummary` after synthesis is ready and immediately before returning the answer. This fills the fields hooks cannot infer well: route, entrypoints, inspected documents, coarse request type, and confidence. The helper measures the operation and the Stop hook emits `QueryComplete`, so a long unrelated agent turn is never relabeled as query latency.

One skill execution should stay under one `operation_id`, linked to its parent runtime `request_id`:

1. `query-start` creates the operation and prints its `operation_id` and parent `request_id`.
2. Tool calls are recorded while that operation is active.
3. `query-summary` reuses both exact ids and writes `QuerySummary`.
4. The final response Stop hook emits `QueryComplete` with operation elapsed time and measured token delta.

Do not omit the start call, invent ids, or recover them with `latest_state()` at completion. If start failed, write a semantic summary only when useful and leave operation timing unavailable.

`QuerySummary` semantic schema (numeric fields are added by the helper):

```json
{"source":"kb-query-skill","operation_id":"exact id returned by query-start","request_id":"exact parent id returned by query-start","request_type":"lookup|synthesis|maintenance|write|mixed","route":["A:direct-folder","D:index-log"],"entrypoints":["1. Projects/foo/_index.md"],"documents_read_count":3,"documents_read_paths":["1. Projects/foo/_index.md","1. Projects/foo/overview.md"],"search_step_count":2,"confidence":"medium"}
```

Guidelines:
- Record only request type, routes, entrypoints, documents materially inspected, and confidence. Do not record a free-form query summary.
- Put only material evidence documents in `documents_read_paths`: files actually opened/read and used for the answer. Do not include every search hit, directory, config file, telemetry file, or incidental path seen in tool output.
- Leave raw path capture to hooks/wrappers and `AutoPathSummary`; `QuerySummary` should be the concise semantic record, not a full trace.
- Use `request_type` to separate lookup/synthesis from write or maintenance requests.
- Count `search_step_count` as the number of distinct search/narrowing moves, not the number of files read.
- Do not log the prompt, question/query text, copied source text, private note content, or the answer.
- Do not read extra documents just to improve telemetry.
- If telemetry writing fails, answer normally and mention the gap only when the user asked about measurement.

The plugin bundles one portable helper for both Claude Code and Codex. Resolve it from the plugin root; do not use a user-home script path. It discovers `.para-kb/config.json` from the vault working directory and fails closed outside a configured/detectable Obsidian vault.

Start it immediately after parsing the request and before the first vault lookup:

```bash
PARA_KB_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
python3 "$PARA_KB_PLUGIN_ROOT/scripts/para_kb_telemetry.py" query-start <<'JSON'
{"source":"kb-query-skill"}
JSON
```

Retain the printed `operation_id` and `request_id` (`query_id` may also be printed as a one-release compatibility alias). After the final evidence set and synthesis are ready, write the semantic summary immediately before returning the answer:

```bash
PARA_KB_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
python3 "$PARA_KB_PLUGIN_ROOT/scripts/para_kb_telemetry.py" query-summary <<'JSON'
{"source":"kb-query-skill","operation_id":"query-... returned by query-start","request_id":"parent id returned by query-start","request_type":"lookup","route":["E:full-text-search"],"entrypoints":["0. Common/index.md"],"documents_read_count":1,"documents_read_paths":["0. Common/index.md"],"search_step_count":1,"confidence":"medium"}
JSON
```

The legacy `query-complete` helper command remains a temporary alias for `query-summary`; new instructions and integrations must use the canonical name.
