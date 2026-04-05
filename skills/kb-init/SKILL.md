---
name: kb-init
description: Initialize PARA Knowledge Base in your Obsidian vault. Creates index files, log, and adds KB rules to CLAUDE.md. Run this first before using other kb- skills.
argument-hint: [--force]
---

# KB Init — PARA Knowledge Base Setup

Set up the Knowledge Base layer on an existing PARA-structured Obsidian vault.

## What It Does

1. **Detect vault** — find `.obsidian/` to confirm vault root, locate PARA directories
2. **Create category indexes** — `_index.md` in each PARA directory (Projects, Areas, Resources, Archive)
3. **Create top-level index** — `0. Common/index.md` (~30 lines, vault overview)
4. **Create activity log** — `0. Common/log.md` (append-only)
5. **Update CLAUDE.md** — append KB rules section (preserve existing content)
6. **Detect obsidian CLI** — check availability, configure fallback strategy

## Prerequisites

An Obsidian vault with PARA-style numbered folders:

```
Vault/
├── 0. Common/        (shared: daily notes, dashboard, etc.)
├── 1. Projects/      (active projects with deliverables)
├── 2. Areas/         (ongoing responsibilities, no end date)
├── 3. Resources/     (reference material by topic)
├── 4. Archive/       (completed or paused items)
└── Inbox/            (optional — raw input landing zone)
```

Folder names are matched by number prefix (`1.`, `2.`, `3.`, `4.`), not exact name. `Inbox/` is matched by name.

## Execution Flow

```
Step 1: Detect vault root
  Find .obsidian/ directory → that parent is the vault root
  Verify PARA directories exist (at least 1-4 numbered folders)
  If missing directories → warn and offer to create them

Step 2: Check existing state
  If _index.md or index.md already exist:
    --force → overwrite
    Otherwise → ask user: overwrite, skip, or abort

Step 3: Scan and generate _index.md per category
  For each PARA directory:
    List subdirectories and standalone .md files
    Read overview files for status (0.*.md, *-Project.md, project-overview.md)
    Generate _index.md:
      - frontmatter: title, type: kb-index, updated: today
      - summary line with counts
      - one line per item: **name** — status/description
    Target: 10-20 lines of content per index

Step 4: Generate top-level 0. Common/index.md
  Aggregate from category indexes:
    Projects: count + highlights
    Areas: count + major areas
    Resources: count + categories
    Archive: completed/paused counts
    Recent: placeholder for log entries
  Target: ~30 lines

Step 5: Create 0. Common/log.md
  Header + initial entry:
    "[date] init | KB initialized | N index files created"

Step 6: Update CLAUDE.md
  If exists → read, append KB rules after existing content
  If missing → create from templates/CLAUDE.md.template
  KB rules section includes:
    Vault structure description
    KB operation rules (ingest/query/lint)
    Tag conventions (#proj/, #type/, #topic/)
    Wikilink rules
    Index management rules

Step 7: Detect tooling
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
| `#proj/<name>` | Project identifier | `#proj/my-project`, `#proj/my-webapp` |
| `#study/paper/<topic>` | Research papers | `#study/paper/machine-learning`, `#study/paper/data-science` |
| `#type/<type>` | Document type | `#type/paper`, `#type/meeting` |
| `#topic/<topic>` | Subject matter | `#topic/kubernetes`, `#topic/ml` |

**Important:** If the vault already uses `#study/paper` instead of `#type/paper`, follow the existing convention. Consistency over idealism.

## Arguments

| Argument | Effect |
|----------|--------|
| `--force` | Overwrite existing index files without asking |

## After Init

Run these as needed:
- `/kb-ingest` — process documents in Inbox
- `/kb-query "question"` — search the knowledge base
- `/kb-lint` — check vault health
- `/kb-index` — rebuild all indexes
