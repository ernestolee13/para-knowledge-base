---
name: kb-init
description: Initialize or adopt a portable PARA Knowledge Base in an Obsidian vault. Detects numbered, standard, or configured roots; creates indexes and a log when requested; and installs shared rules/config for Claude Code, Codex, and local consumers.
---

# KB Init — PARA Knowledge Base Setup

Set up the Knowledge Base layer on an existing PARA-structured Obsidian vault.

## What It Does

1. **Detect vault** — find `.obsidian/` and existing `.para-kb/config.json`
2. **Detect structure** — use configured, numbered, or unnumbered PARA roots without renaming folders
3. **Create portable config** — write `.para-kb/config.json` without an absolute vault path
4. **Create indexes and log** — only for missing files, unless the user explicitly requests replacement
5. **Install agent guidance** — append a marker-bounded KB rules fragment to `CLAUDE.md` and/or `AGENTS.md`, preserving existing content
6. **Detect Obsidian CLI** — configure the preferred search/backlink path and fallback strategy

## Prerequisites

An Obsidian vault with either numbered or unnumbered PARA folders. Numbered example:

```
Vault/
├── 0. Common/        (shared: daily notes, dashboard, etc.)
├── 1. Projects/      (active projects with deliverables)
├── 2. Areas/         (ongoing responsibilities, no end date)
├── 3. Resources/     (reference material by topic)
├── 4. Archive/       (completed or paused items)
└── Inbox/            (optional — raw input landing zone)
```

Standard unnumbered roots (`Common/`, `Projects/`, `Areas/`, `Resources/`, `Archive/`) are also supported. For another layout, create `.para-kb/config.json` from `templates/para-kb.config.json` and set `para_roots` explicitly. `Inbox/` is optional in every profile.

## Execution Flow

```
Step 1: Detect vault root and configuration
  Find .obsidian/ directory → that parent is the vault root
  If .para-kb/config.json exists → validate and use it as source of truth
  Else detect numbered or standard PARA roots
  If neither profile is unambiguous → stop before creating folders and request a custom config

Step 2: Create/adopt portable config
  Resolve the bundled helper from ${CLAUDE_PLUGIN_ROOT:-${PLUGIN_ROOT:-}}
  Run: python3 "$PARA_KB_PLUGIN_ROOT/scripts/para_kb_telemetry.py" init-config --profile auto
  The config stores only vault-relative paths and never overwrites an existing valid config
  With --config-only or --adopt → stop after config + agent guidance; do not rewrite notes or indexes

Step 3: Check existing state
  If _index.md or index.md already exist:
    Default → preserve and adopt them
    --force-indexes → replace only after an explicit destructive confirmation
  Never overwrite CLAUDE.md, AGENTS.md, .para-kb/config.json, or a human log wholesale

Step 4: Scan and generate _index.md per category
  For each configured PARA directory:
    List subdirectories and standalone .md files
    Read overview files for status (0.*.md, *-Project.md, project-overview.md)
    Generate _index.md:
      - frontmatter: title, type: kb-index, updated: today
      - summary line with counts
      - one line per item: **name** — status/description
    Target: 10-20 lines of content per index

Step 5: Generate top-level {common}/index.md
  Aggregate from category indexes:
    Projects: count + highlights
    Areas: count + major areas
    Resources: count + categories
    Archive: completed/paused counts
    Recent: placeholder for log entries
  Target: ~30 lines

Step 6: Create {common}/log.md
  Header + initial entry:
    "[date] init | KB initialized | N index files created"

Step 7: Update agent guidance
  Render templates/KB-RULES.md.template with configured roots and paths
  If CLAUDE.md exists → append/update only the marker-bounded PARA KB section
  If AGENTS.md exists → append/update only the same marker-bounded section
  If neither exists → create the file appropriate to the active host from its wrapper template
  Never replace unrelated instructions in either file
  Shared rules include:
    Vault structure description
    KB operation rules (ingest/query/lint)
    Project lifecycle summary (promotion, durable-knowledge capture, decompose-before-archive — see templates/CLAUDE.md.template)
    Tag conventions (#proj/, #type/, #topic/)
    Wikilink rules
    Index management rules

Step 8: Detect tooling
  which obsidian → if found:
    Run: obsidian version
    Run: obsidian tags sort=count counts limit=20
    Log "obsidian CLI v{version} detected — search, backlinks, tags available"
    Record existing tag conventions for future ingest/lint use
  If not found:
    Log "obsidian CLI not available — using grep/glob fallback"
    Note: All skills fully functional without CLI
```

## Tag Conventions (Established at Init)

Detect existing tag patterns first via `obsidian tags sort=count counts` (or Grep fallback). Adapt to the vault's established conventions rather than imposing new ones.

Common patterns found in PARA vaults:

| Prefix | Purpose | Example |
|--------|---------|---------|
| `#proj/<name>` | Project identifier | `#proj/product-launch`, `#proj/research-dashboard` |
| `#study/paper/<topic>` | Research papers | `#study/paper/machine-learning`, `#study/paper/data-science` |
| `#type/<type>` | Document type | `#type/paper`, `#type/meeting` |
| `#topic/<topic>` | Subject matter | `#topic/productivity`, `#topic/ml` |

**Important:** If the vault already uses `#study/paper` instead of `#type/paper`, follow the existing convention. Consistency over idealism.

## Arguments

| Argument | Effect |
|----------|--------|
| `--config-only` | Create/validate `.para-kb/config.json` and agent guidance only; do not touch notes or indexes |
| `--adopt` | Alias for non-destructive config-only adoption of an existing vault |
| `--profile numbered\|standard\|custom` | Select a structure when auto-detection is ambiguous; custom requires an existing edited config |
| `--force-indexes` | Replace existing generated indexes only after explicit destructive confirmation |

## After Init

Run these as needed:
- `/kb-ingest` — process documents in Inbox
- `/kb-query "question"` — search the knowledge base
- `/kb-lint` — check vault health
- `/kb-index` — rebuild all indexes

Local consumers can now discover `.para-kb/config.json` automatically. Keep `.para-kb/`, the active telemetry JSONL, its archive directory, and runtime state out of knowledge indexes and normal query context.
