# PARA Knowledge Base — Claude Code Plugin

> **LLM as Knowledge Compiler** — Karpathy's LLM Knowledge Base pattern, optimized for PARA Obsidian vaults

---

## Inspiration

Inspired by [Karpathy's llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — the idea that an LLM should act as a **knowledge compiler**, not a search engine. Rather than re-retrieving and re-summarizing raw notes on every query, knowledge is compiled once into structured wiki-style articles, then maintained incrementally as new information arrives.

This plugin applies that pattern to PARA-structured Obsidian vaults.

---

## Why this plugin?

If you already have a PARA vault with hundreds of notes, Claude Code can read them — but **every conversation starts from scratch**. Each query re-reads files, re-discovers structure, and burns tokens figuring out what's where.

This plugin fixes that by adding a **persistent knowledge layer** on top of your existing vault:

**The problem without a KB:**
```
User: "What do I know about distributed systems?"
Claude: reads 30+ files → 15K tokens → synthesizes answer → forgotten next session
User: (asks again next week)
Claude: reads the same 30+ files again → 15K tokens again
```

**With this plugin:**
```
/kb-ingest              → new notes classified, linked, indexed (once)
/kb-query "distributed systems"  → reads _index.md (50 tokens) → targets 2 files (400 tokens) → done
```

### What you get on top of your existing PARA vault

| Already have | This plugin adds |
|---|---|
| Folders organized by PARA | `_index.md` per category — Claude reads 10 lines instead of scanning 100 files |
| Notes with some tags | Tag convention detection + consistency enforcement across vault |
| Manual wikilinks | Auto-generated wikilinks on ingest — first occurrence of known terms linked automatically |
| CLAUDE.md with basic rules | Full vault schema — structure, KB operations, tag system, navigation strategies |
| Raw notes in Inbox | One-command classification + move + metadata + linking |

### Token efficiency

| Operation | Without plugin | With plugin |
|---|---|---|
| "What projects am I working on?" | Scan all project folders ~3K tokens | Read `_index.md` ~50 tokens |
| "Find everything about topic X" | Grep entire vault ~5K tokens | Tag search via index ~200 tokens |
| Ingest a new document | Manual: move, tag, link, update index | `/kb-ingest` — all automated, ~500 tokens |
| Weekly health check | Not possible | `/kb-lint` — orphans, broken links, stale content |

The key insight: **indexes are cheap to read, and they tell Claude exactly where to look.** Instead of scanning your whole vault every time, Claude reads a 10-line index, picks the right folder, and reads only what's needed.

---

## Concept

### The 3-Layer Architecture

```
Inbox/          ← raw capture (fleeting notes, clippings, meeting notes)
PARA/           ← compiled knowledge wiki (Projects / Areas / Resources / Archives)
CLAUDE.md       ← vault schema (topics, conventions, wikilink vocabulary)
```

- **Inbox** is the staging area. Raw, unprocessed, low-friction.
- **PARA** is the knowledge base. LLM-compiled, structured, cross-linked.
- **CLAUDE.md** is the schema. Tells the LLM what topics exist, how notes are organized, what wikilinks are canonical.

### The 3 Core Operations

| Operation | What it does |
|-----------|-------------|
| **Ingest** | Takes raw Inbox notes, extracts knowledge, merges into PARA wiki pages |
| **Query**  | Answers questions by reading compiled PARA pages (not raw notes) |
| **Lint**   | Audits knowledge base for gaps, broken wikilinks, stale content |

### RAG vs. Knowledge Base

| RAG (Retrieval) | KB (Compilation) |
|-----------------|------------------|
| Retrieves chunks on each query | Knowledge compiled once, maintained incrementally |
| Quality varies with retrieval precision | Consistent quality — LLM synthesizes on ingest |
| No persistent synthesis | Synthesis is durable; query is fast |
| Good for large document corpuses | Good for personal knowledge that evolves over time |

For a personal PARA vault, the KB pattern wins: your notes are small enough to compile, and the value compounds as the KB grows more interconnected.

---

## Skills

### `/kb-init`
Initializes the knowledge base structure in your vault. Creates `CLAUDE.md` schema, sets up PARA folder conventions, and generates top-level `_index.md` files for each PARA category.

### `/kb-ingest`
Processes notes from your Inbox. The LLM reads each raw note, determines which PARA page it belongs to (or creates a new one), and merges the knowledge — updating wikilinks, adding cross-references, and moving the source note to Archives when done.

### `/kb-query`
Answers a question using the compiled knowledge base. Reads relevant PARA pages directly rather than performing fuzzy retrieval over raw notes. Returns a cited answer with links to the source pages.

### `/kb-lint`
Audits the knowledge base. Checks for broken wikilinks, orphaned notes, pages with no backlinks, topics mentioned in CLAUDE.md that have no corresponding page, and pages that haven't been updated in a configurable period.

### `/kb-index`
Regenerates `_index.md` files at two levels:
- **Top-level** (`_index.md`): full map of all PARA categories and key topics
- **Category-level** (`Projects/_index.md`, `Areas/_index.md`, etc.): topic lists with one-line summaries

---

## Key Features

### Hierarchical Indexing
Two-tier index system keeps navigation fast even as the vault grows:
- Top-level `_index.md` gives a full vault map
- Per-category `_index.md` gives a focused topic list

### 4 Navigation Methods
The KB is designed to be navigable four ways simultaneously:
1. **Folders** — PARA hierarchy provides structure
2. **Tags** — status, type, and topic tags for filtered views
3. **Wikilinks + Backlinks** — every concept links forward and backward
4. **Indexes** — `_index.md` files for when you want a map, not a search

### Automatic Wikilink Generation
During ingest, the LLM automatically generates wikilinks between related concepts. New terms are registered in `CLAUDE.md` so future ingests stay consistent.

### Obsidian CLI Integration
When the [Obsidian CLI](https://help.obsidian.md/cli) (built into Obsidian 1.12+) is available, skills use it for precise vault operations:

| CLI Command | Used by | Purpose |
|-------------|---------|---------|
| `obsidian search query="term"` | kb-query, kb-ingest | Full-text vault search |
| `obsidian backlinks file="Note"` | kb-query, kb-lint | Find referencing documents |
| `obsidian tags` | kb-lint, kb-ingest | Tag inventory and consistency |
| `obsidian property:set` | kb-ingest | Frontmatter updates |
| `obsidian read file="Note"` | kb-query | Read note content |

**Without CLI**, all skills fall back to Grep/Glob/Read tools — fully functional but slightly less precise for backlink resolution and search.

---

## Installation

### Install as marketplace
```shell
# Add the marketplace
/plugin marketplace add ernestolee13/para-knowledge-base

# Install the plugin
/plugin install para-knowledge-base@para-knowledge-base
```

### Manual install
```shell
git clone https://github.com/ernestolee13/para-knowledge-base.git
# Then add to your Claude Code plugin settings
```

Then open Claude Code in your vault directory. Skills become available as `/kb-init`, `/kb-ingest`, `/kb-query`, `/kb-lint`, `/kb-index`.

### Recommended: Install with kepano/obsidian-skills

This plugin works best alongside [kepano's obsidian-skills](https://github.com/kepano/obsidian-skills), which adds Obsidian CLI commands, markdown syntax, bases, and canvas skills. Together they cover both **vault management** (this plugin) and **content creation** (obsidian-skills).

```shell
# Install both
/plugin marketplace add kepano/obsidian-skills
/plugin install obsidian@obsidian-skills

/plugin marketplace add ernestolee13/para-knowledge-base
/plugin install para-knowledge-base@para-knowledge-base
```

---

## Quick Start

1. Open Claude Code with your Obsidian vault as the working directory.
2. Run `/kb-init` — creates `CLAUDE.md` schema, `_index.md` files, and `log.md`.
3. Drop notes into your `Inbox/` folder.
4. Run `/kb-ingest` — classifies, moves, links, and indexes Inbox documents.
5. Ask questions with `/kb-query "What do I know about X?"`.
6. Run `/kb-lint` periodically to check vault health.
7. Run `/kb-index` to rebuild all indexes after major reorganization.

---

## Obsidian CLI Setup (Recommended)

The Obsidian CLI enhances search, backlink traversal, and tag operations. It's **optional but recommended**.

**Requirements:** Obsidian Desktop **v1.12.0+** (installer version, not just app update).

### macOS
1. Download latest installer from https://obsidian.md/download
2. Replace `/Applications/Obsidian.app` (vault data is preserved)
3. Open Obsidian → **Settings → General → Command line interface → Enable**
4. Restart terminal, verify: `obsidian help`

PATH is auto-added to `~/.zprofile`. For other shells:
```bash
export PATH="$PATH:/Applications/Obsidian.app/Contents/MacOS"
```

### Windows / Linux
1. Download latest installer from https://obsidian.md/download
2. Install over existing (v1.12.4+ required for Windows)
3. Open Obsidian → Settings → General → CLI → Enable
4. Follow shell-specific PATH instructions in the app

### Without CLI
All skills work without the CLI using file-based fallback (Grep, Glob, Read). You get full functionality — the CLI just makes search and backlink operations faster and more precise.

### Works with kepano/obsidian-skills
This plugin is designed to complement [kepano's obsidian-skills](https://github.com/kepano/obsidian-skills) plugin. If you have both installed:
- `obsidian-skills` provides general Obsidian CLI, markdown, bases, and canvas skills
- `para-knowledge-base` adds PARA-specific knowledge management on top
- Both share the same `obsidian` CLI binary — no conflict

---

## Requirements

- [Claude Code](https://claude.ai/code)
- Obsidian vault with PARA folder structure (numbered: `1. Projects/`, `2. Areas/`, `3. Resources/`, `4. Archive/`)
- Optional: Obsidian 1.12+ for CLI integration (see setup above)
- Recommended: [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills) — provides Obsidian CLI, markdown, bases, and canvas skills that complement this plugin

---

## Contributing

Issues and pull requests welcome. Please open an issue first for major changes.

## License

MIT — see [LICENSE](LICENSE)
