---
name: kb-index
description: Update Knowledge Base indexes. Smart mode detects changes and updates only what's needed. Full rebuild available with --full flag. Use after adding/moving documents or when indexes feel stale.
argument-hint: [--full] [--category <name>] [--dry-run]
---

# KB Index — Smart Index Update

Update indexes efficiently. By default, detects what changed and updates only affected entries. Full rebuild available when needed.

## Usage

```
/kb-index                      # Smart update (diff-based, fast)
/kb-index --full               # Full rebuild (scan everything)
/kb-index --category Projects  # Update one category only
/kb-index --dry-run            # Preview changes without writing
```

## 3-Tier Strategy

Choose the lightest approach that fits the situation:

### Tier 1: Per-File Update (via kb-ingest) — ~200 tokens
**When:** A single file was ingested or moved.
**How:** kb-ingest already handles this — adds one line to _index.md, updates counts.
**No need to run kb-index separately.**

### Tier 2: Smart Diff Update (default kb-index) — ~500-1500 tokens
**When:** A few files changed, or "something feels off."
**How:** Compare existing _index.md entries against actual files on disk. Only process differences.

### Tier 3: Full Rebuild (kb-index --full) — ~3-4K tokens
**When:** Major reorganization, initial setup, or indexes are badly corrupted.
**How:** Scan everything from scratch, regenerate all indexes.

## Tier 2: Smart Diff — Execution Flow

This is the **default** behavior when you run `/kb-index`.

```
Step 1: READ existing indexes (cheap — ~200 tokens total)
  Read each _index.md (10-20 lines each)
  Read top-level index.md (~30 lines)
  Extract: listed items, counts, last updated date

Step 2: DETECT changes (cheap — tool calls only, no file reads)
  For each PARA category:
    Glob: list current subdirectories and .md files on disk
    Compare against items listed in _index.md
    Classify each item:
      MATCH    — in index AND on disk → skip (no action)
      ADDED    — on disk but NOT in index → needs adding
      REMOVED  — in index but NOT on disk → needs removing

  If zero differences found:
    Log "[date] index | no changes detected" → done
    Total cost: ~200 tokens (just reading indexes + globs)

Step 3: PROCESS only differences
  For ADDED items only:
    Read the new file's overview/frontmatter (~50-100 tokens per file)
    Generate one-line index entry

  For REMOVED items:
    Delete the line from _index.md

  Skip MATCH items entirely — don't re-read, don't regenerate

Step 4: UPDATE indexes
  Edit (not rewrite) each affected _index.md:
    Insert new entries, remove deleted entries
    Update summary count line
    Update "updated: {today}" in frontmatter

  Update top-level index.md:
    Adjust category counts
    Update Recent Activity from log.md (last 5 entries)

Step 5: LOG
  "[date] index-update | added N, removed M | touched K categories"
```

### Token Cost by Scenario

| Scenario | Tokens | Why |
|----------|--------|-----|
| Nothing changed | ~200 | Read 5 indexes + globs |
| 1 file added | ~350 | Above + read 1 overview |
| 3 files added, 1 removed | ~600 | Above + read 3 overviews |
| 10+ files changed | ~1500 | Consider --full instead |
| Major reorg (--full) | ~3-4K | Full vault scan |

## Tier 3: Full Rebuild — Execution Flow

Only runs with `--full` flag. Same as before:

```
1. SCAN each PARA directory
  Projects/: list subdirs, read overview files, extract status
  Areas/: list subdirs, count files, extract topics
  Resources/: list subdirs, count files
  Archive/: count completed vs paused

2. GENERATE _index.md per category (from scratch)
  ---
  title: {Category} Index
  type: kb-index
  updated: {today}
  ---
  # {Category Name}
  {Summary line}
  - **[[item]]** — description
  ...

  Rules:
  - 10-20 lines per index
  - Active/important first, then alphabetical
  - [[wikilinks]] for references

3. GENERATE top-level index.md (from scratch)
  Aggregate categories + last 5 log entries
  Target: ~30 lines

4. LOG
  "[date] index-rebuild | N categories | M total entries"
```

## Smart Detection Details

### How "ADDED" is detected
```
# Glob disk state
disk_items = Glob("1. Projects/*/") + Glob("1. Projects/*.md")

# Parse existing index
index_items = extract_entries_from("1. Projects/_index.md")

# Diff
added = disk_items - index_items
removed = index_items - disk_items
```

### What counts as an "item"
- Projects: subdirectories (each project is a folder)
- Areas: subdirectories (Paper, Career, etc.)
- Resources: subdirectories
- Archive: subdirectories under completed/paused projects (완료/중단 프로젝트)

Standalone .md files in category root are also tracked (e.g., `para-knowledge-base 계획.md` in Projects/).

### When to recommend --full
If diff detects >30% items changed, suggest: "Many changes detected. Rebuild with --full?"

## Obsidian CLI Enhancement

When `obsidian` is available:
```bash
# Faster than glob for large vaults
obsidian search query="type: kb-index" limit=10   # find all index files
obsidian tags sort=count counts                     # tag inventory for index enrichment
```

## Arguments

| Argument | Effect |
|----------|--------|
| (default) | Smart diff update — only process changes |
| `--full` | Full rebuild from scratch |
| `--category <name>` | Limit to: Projects, Areas, Resources, or Archive |
| `--dry-run` | Show what would change without writing |

## Decision Guide

```
"added one file" (파일 하나 추가했어)              → /kb-ingest already handled it (Tier 1)
"a few things changed" (몇개 바뀐 것 같은데)       → /kb-index (Tier 2, default)
"major folder restructure" (폴더 구조 대폭 변경)   → /kb-index --full (Tier 3)
"not sure if index is correct" (인덱스가 맞는지)   → /kb-lint first, then /kb-lint --fix if needed
```
