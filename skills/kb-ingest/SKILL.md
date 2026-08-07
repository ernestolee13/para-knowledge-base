---
name: kb-ingest
description: Build and integrate documents in a PARA Knowledge Base. Classifies, creates or moves, summarizes, links, indexes, validates, and records new vault knowledge from Inbox, a specified path, or a direct request to create/update wiki content.
---

# KB Ingest — Document Intake + Classification + Linking

Process new documents into the Knowledge Base. Reads content, classifies into the right PARA location, generates metadata, creates wikilinks, updates related documents, and maintains indexes.

`Inbox/` is optional, not a prerequisite. Apply this workflow when the user directly asks to create, add, organize, or substantially integrate knowledge in the wiki. A direct write in its final PARA folder still performs ANALYZE, metadata, linking, index, validation, human log, and build telemetry steps; only MOVE is skipped.

## Usage

```
/kb-ingest                      # Process all files in Inbox/
/kb-ingest path/to/file.md      # Process a specific file
/kb-ingest path/to/folder/      # Process all .md files in a folder
"위키에 이 내용을 만들어줘"       # Direct creation; route through the same workflow
```

## Execution Flow

For each document to ingest:

### 0. START BUILD TELEMETRY

When telemetry is enabled, start one explicit ingest operation before reading or classifying source material. For a batch, start one operation for the whole batch, not one per file. Retain the exact `operation_id` and parent `request_id` printed by the bundled helper; reuse both in the summary.

```bash
PARA_KB_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
python3 "$PARA_KB_PLUGIN_ROOT/scripts/para_kb_telemetry.py" build-start <<'JSON'
{"source":"kb-ingest-skill","source_kind":"inbox|direct|batch"}
JSON
```

Set `source_kind` from the actual entry route: `inbox` for an Inbox-origin document, `direct` for a direct wiki request or specified file, and `batch` for a multi-document run. The same bundled path works in Claude Code and Codex. Telemetry failure must not block a valid ingest, but do not invent or recover an operation id from a later unrelated request.

### 1. READ
- Read full document content
- Extract existing frontmatter (preserve if present)
- Identify document type: paper, note, reference, meeting, idea, log, etc.
- Note content length (affects summarization decision)

### 2. ANALYZE
- Read relevant `_index.md` files for context (NOT full documents — token-efficient)
- Determine PARA classification:

| Signal | Classification |
|--------|---------------|
| Has deadline, phases, deliverables | `1. Projects/` → which project? |
| Paper/논문, research, study | `2. Areas/Paper/` |
| Career, Interview/면접, resume | `2. Areas/Career/` |
| Ongoing responsibility, no end date | `2. Areas/` → which area? |
| Tutorial, how-to, reference guide | `3. Resources/` → which category? |
| Completed, historical, inactive | `4. Archive/` |
| Unclear | Ask user |

- Identify related existing documents by topic, tags, or content overlap

### 3. MOVE
- Move file to target PARA directory
- Create subdirectory if needed (ask user first)
- If already in correct location, skip move

### 4. FRONTMATTER
Add or update frontmatter fields:

```yaml
---
title: Document Title
created: 2026-04-05          # preserve original if exists
type: paper                   # paper|note|reference|meeting|idea|log|data
summary: One-line summary of the document's content and purpose.
tags:
  - "#proj/project-name"      # if project-related
  - "#type/paper"             # document type
  - "#topic/kubernetes"       # subject matter
related:
  - "[[Related Document]]"    # discovered relationships
source: https://...           # URL or citation (if applicable)
---
```

`summary` is required on every ingested document, not just long ones. It is what `kb-query` reads instead of the full body when narrowing candidates. Write it as a single sentence describing what the document contains — not a teaser. For documents under 500 words, this frontmatter line is the only summary produced; for longer documents, Step 5 below adds a second, longer summary as a body callout.

Use `type: data` for large data-style listings that are not meant to be read in full — raw exports, link/reference dumps, generated tables, telemetry-adjacent lists. `kb-query` skips the body of `type: data` documents and relies on `summary` and frontmatter alone, so make the `summary` field precise about what the data covers (source, scope, row/item count) since it carries more weight than usual.

### 5. SUMMARIZE — Extended Body Callout (long documents only)
For documents over 500 words, add a second, longer summary as a body callout in addition to the required frontmatter `summary` line:
- Generate a concise summary after frontmatter (under 200 words)
- For papers: title, authors, key contribution, method, results
- Format: `> **Summary:** ...` callout block

### 6. WIKILINK — Create Forward Links
Scan document content for existing vault entities:
- Document titles → `[[Document Title]]`
- Project names → `[[project-name]]`
- Technical terms matching existing docs → `[[term]]`

Rules:
- Link first occurrence only per term
- Skip code blocks, URLs, and frontmatter
- Maximum ~10 auto-links per document
- Don't link common words even if a doc exists with that name

### 7. BACKLINK — Update Related Documents
For each strongly related document (max 3):
- Check if it already references the new doc
- If not, add to its `## Related Documents` section (create section if missing; use `## 관련 문서` for Korean vaults)
- Append: `- [[New Document]] — brief context`

### 8. INDEX — Update Indexes
- Add one-line entry to the relevant `_index.md`
- Update counts in top-level `0. Common/index.md`
- Maintain sort order within index
- If the target location is `1. Projects/<slug>/` and that folder has a project hub `_index.md`, update the hub's local document list as well. Create a new project hub only when the vault convention or user request calls for project-level entrypoints.

### 9. LOG
Append to `0. Common/log.md`:
```
[2026-04-05] ingest | Document Title | → 2. Areas/Paper/ | updated 2 docs
```

### 10. VALIDATE + BUILD TELEMETRY

After material vault construction, verify the result and complete the exact operation opened in Step 0 with one compact `BuildSummary`. Keep `0. Common/log.md` as the human decision record; the JSONL event is machine evidence for operation duration, token, reference-path, placement, index, and link analysis. The runtime Stop hook emits a linked `BuildComplete` after answer generation.

- Verify every created/moved target exists, required `summary` frontmatter is present, intended wikilinks resolve, and each affected Tier 1/Tier 2 index was updated.
- Record only paths, counts, route, and validation state. Never record prompt text, note bodies, summaries, or copied excerpts.
- List only documents materially consulted in `reference_paths`, not every file surfaced by a command.
- Populate `link_pairs` and counts from the actual final diff/graph. Do not guess.
- Do not hand-estimate duration or tokens. The helper measures `BuildStart → BuildSummary`, and the Stop hook finalizes the same explicit `operation_id`; generic whole-turn time remains a separate diagnostic field.
- Set `kb_ingest_used: true` only when this complete workflow ran. A known partial or bypassed direct write uses `false` and `route: direct-wiki-write`.
- Telemetry failure does not roll back a valid vault write; report the measurement gap only when relevant.

Portable helper example:

```bash
PARA_KB_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}"
python3 "$PARA_KB_PLUGIN_ROOT/scripts/para_kb_telemetry.py" build-summary <<'JSON'
{"source":"kb-ingest-skill","operation_id":"build-... returned by build-start","request_id":"parent id returned by build-start","operation_type":"create","route":"kb-ingest","kb_ingest_used":true,"reference_paths":["3. Resources/topic/Source.md"],"created_paths":["1. Projects/demo/New Note.md"],"updated_paths":[],"moved_from_paths":[],"moved_to_paths":[],"index_paths":["1. Projects/demo/_index.md"],"link_pairs":[{"source_path":"1. Projects/demo/_index.md","target_path":"1. Projects/demo/New Note.md"}],"links_added":1,"backlinks_added":0,"frontmatter_completed":1,"summaries_completed":1,"validation":"passed","confidence":"high"}
JSON
```

The legacy `build-complete` helper command remains a temporary alias for `build-summary`; new instructions and integrations must use the canonical name.

## Batch Mode

When processing multiple files (Inbox/ or folder):
1. Read all files first for batch classification
2. Classify all at once (cross-document decisions are better)
3. Process moves, links, and backlinks
4. Update indexes once at end (not per-file)
5. Single batch human log entry and one batch `BuildSummary`

## Project Lifecycle (PARA Flow)

Projects are not born in `1. Projects/` and archived unchanged — knowledge should flow in and out as a project moves through PARA. Apply this lifecycle at project start, during active work, and at completion; it runs independently of the per-document ingest flow above, which handles individual incoming notes.

### 1. Project Start — Promotion

Ideas and reference material usually already live in `2. Areas/` or `3. Resources/` before a project exists. When a project starts:

| Signal | Action |
|--------|--------|
| Document is a project-unique deliverable, plan, or decision record | Move into `1. Projects/<slug>/` |
| Document is reference material the project draws on but doesn't own | Keep it in place (`2. Areas/` or `3. Resources/`); link with `[[wikilink]]` from the new project instead of moving |

Do not drag reference material into the project folder just because the project uses it — moving breaks the resource's existing backlinks and duplicates ownership. Link, don't move.

### 2. During — Generate Durable Knowledge

While a project is active, new knowledge surfaces that outlives the project itself (a reusable pattern, a technique, a decision framework). Ask: **would this still be useful after the project ends?**

| Answer | Action |
|--------|--------|
| Yes — reusable beyond this project | Create or update the page in `3. Resources/`; link it from the project instead of duplicating content in the project folder |
| No — specific to this project's execution | Keep it in the project folder as a project-unique record |

Keep the project folder lean: unique history and decisions, not general knowledge that belongs in Resources.

### 3. Project Completion — Decompose & Return

Do not move a completed project folder into `4. Archive/` wholesale without a decompose pass first. Archiving unprocessed folders turns Archive into an unsearched dumping ground and strands reusable knowledge where `kb-query` won't look for it.

Before the move:
1. **Reusable knowledge → `3. Resources/`.** Anything future projects could reuse (patterns, techniques, findings) gets its own Resources page or merges into an existing one.
2. **Ongoing responsibility → `2. Areas/`.** If the project revealed or spawned a standing responsibility with no end date, it becomes (or merges into) an Areas page, not a project artifact.
3. **Everything else (project-unique record) → `4. Archive/<project>/`,** moved as a folder once the two extractions above are done.
4. Update the indexes touched by the move (the project's old category index, `4. Archive/_index.md`, and `3. Resources/`/`2. Areas/` indexes if something was extracted) and append one `log.md` line covering the whole decompose + move.

### Why this matters for the LLM wiki

`kb-query` treats `3. Resources/` as first-class search surface and `4. Archive/` as a lookup of last resort for historical questions only. Reusable knowledge left trapped inside an archived project folder becomes effectively unsearchable — the decompose pass is the return step that makes it retrievable again, not just an organizational tidy-up.

## Obsidian CLI Integration

When available, prefer CLI — uses Obsidian's actual link/tag graph and avoids reading files into context.

```bash
# Discovery
obsidian search:context query="related term"  # related docs with surrounding context
obsidian backlinks file="Document"             # existing backlinks
obsidian tags                                  # full tag inventory
obsidian tag name=<tag>                        # files carrying a tag

# Move (auto-updates wikilinks across vault)
obsidian move path="Inbox/foo.md" to="2. Areas/Paper/foo.md"

# Frontmatter
obsidian property:read name=tags file="Doc"
obsidian property:set name=tags value="['#proj/product-launch','#type/note']" file="Doc"

# Create + append (for backlink updates)
obsidian create file="Doc" content="..."
obsidian append file="Related Doc" content="- [[New Doc]] — context"
```

**`obsidian move` is preferred for the MOVE step** — auto-updates all `[[wikilinks]]` across the vault. Manual `mv` requires post-grep, manual wikilink replacement, affected index updates, and one structural log entry per vault `CLAUDE.md`.

Fallback (no CLI):
- Discovery: Grep + Glob
- Move: `mv` then `grep '[[<old name>]]'` and replace
- Frontmatter: Read + Edit
- Backlink: Edit target file's `## Related Documents` (or `## 관련 문서`) section

## Safety Rules

- **Never delete** the original file — move only
- **Never modify** source document content beyond frontmatter and summary
- **Preserve** all existing wikilinks and formatting
- **Ask user** before creating new subdirectories
- **Ask user** when classification confidence is low
