# Changelog

## 0.6.2 (2026-09-06)

### Changed
- Public docs no longer carry one maintainer vault's private naming. `USAGE.ko.md` archive examples now use a generic `4. Archive/<slug>/` path instead of a vault-specific sub-folder name, and the 0.4.0 personalization checklist describes the ingest hookup as the user's own daily routine rather than naming a private script. No behavior change.

## 0.6.1 (2026-09-05)

### Fixed
- `kb-lint` grep fallback no longer reports false-positive broken links and orphans on macOS/iCloud vaults. The fallback path (used only when the `obsidian` CLI is unavailable) now documents three guards that Obsidian's own resolver already applies: normalize filenames and link targets to Unicode NFC before comparing (macOS stores Hangul filenames as NFD), convert the `\|` table-cell alias escape back to `|` before splitting a wikilink, and scan all files rather than only `*.md` so asset embeds resolve (while still flagging an extensionless link to a non-note as genuinely unresolved). The CLI path was already correct; this only hardens the fallback.

## 0.6.0 (2026-09-05)

### Changed
- `kb-init` now defaults query/build telemetry to a hidden `0. Common/.telemetry/` location (active log plus an `archive/` for rollover), so the operational JSONL and its archive no longer show up as an empty folder in the Obsidian file explorer. The path stays fully configurable in `.para-kb/config.json` (`telemetry.active_path` / `archive_dir`); existing configs are untouched. The default telemetry directory is also added to `exclusions`.

### Added
- README documents input sources as an extension point: the KB wikifies any Markdown dropped into `Inbox/`, so non-Markdown formats only need an existing converter (Obsidian Web Clipper, the official Importer plugin) instead of a bundled one.

## 0.5.0 (2026-08-07)

### Changed
- Query/build telemetry now documents explicit operation boundaries (`Start → Summary → Complete`) and stable `operation_id` joins. Whole-turn/session Stop time is diagnostic only and must not be reported as a unit query or ingest duration.
- Shared hooks remain silent outside explicit KB operations and never attach an explicitly different request to a leftover operation.
- Telemetry guidance now treats vault root, PARA prefixes, index names, semantic spine paths, active log, and archive directory as adapter configuration rather than fixed numbered paths.
- The sanitized telemetry example uses operation-scoped duration/token fields and omits raw query text.

### Added
- Portable `.para-kb/config.json` and versioned query/build telemetry contracts with synthetic fixtures.
- A standard-library Python emitter, sanitizer, shared Claude/Codex hooks, exact operation state, conservative token attribution, log rotation, and fail-closed vault discovery.
- A validated Codex plugin manifest alongside the existing Claude Code manifest.
- Non-destructive numbered/standard/custom vault adoption guidance and shared CLAUDE/AGENTS rule templates.

## 0.4.2 (2026-07-05)

### Added
- **kb-query**: fallback rule for documents with no frontmatter `summary` — read the first paragraph as a lightweight substitute before deciding whether the full document is needed.
- **kb-query**: exclusion rule for frontmatter `type: data` documents (large data-style listings — raw exports, link dumps, telemetry-adjacent tables) — read only frontmatter and `summary`, skip the body unless the user explicitly asks for its contents.
- **kb-ingest**: `summary` is now a required frontmatter field on every ingested document (previously only implied for long documents via the body callout). Added `data` to the documented `type` enum with tagging guidance paired to the new kb-query exclusion rule.
- **kb-lint**: `summary` added to the Frontmatter Quality check table as a recommended field.
- **templates/CLAUDE.md.template**: Frontmatter Standard section synced with the new required `summary` field and `data` type; new "Project Lifecycle (PARA Flow)" section so freshly initialized vaults start with the promotion/decompose flow built in.
- **kb-init**: Step 6 execution flow now lists the project lifecycle summary among the KB rules content it writes into a fresh `CLAUDE.md`, keeping the skill's own description in sync with the template.
- **kb-ingest**: new "Project Lifecycle (PARA Flow)" section — promotion into a project (move project-unique deliverables, link rather than move Areas/Resources material), durable-knowledge capture during the project (write reusable findings to Resources instead of burying them in the project folder), and a decompose-before-archive pass at completion (reusable knowledge → Resources, standing responsibilities → Areas, project-unique record → Archive). Closes the gap where the previous classification table only covered static routing, not project-to-project knowledge flow.
- **README**: new "Project Lifecycle" subsection under Concept summarizing the same flow in one paragraph.
- **USAGE.md / USAGE.ko.md**: new troubleshooting entry for a real failure mode — a marketplace registration can be lost from `~/.claude/plugins/known_marketplaces.json` while the plugin's cache and install records remain, silently disabling all of the plugin's skills. Documents the check and the re-registration fix.

### Fixed
- **USAGE.ko.md**: troubleshooting table referenced commands that do not exist (`/plugin update`, `/plugin reinstall`). Replaced with verified commands (`/plugin marketplace update`, `/reload-plugins`, cache-clear + reinstall) confirmed against current Claude Code plugin documentation.
- **kb-lint**: softened a hardcoded assumption about `obsidian-cli orphans` behavior "as of cli 1.12" into a conditional check — CLI behavior around `userIgnoreFilters` should be verified per install rather than assumed from a fixed version.

## 0.4.1 (2026-07-02)

### Changed
- Generalized project hub support: category indexes remain the default, while `1. Projects/<slug>/_index.md` is now documented as an optional local entrypoint for larger or frequently queried project folders.
- Updated `kb-query` route selection to avoid broad project-name searches before checking indexes or project hubs.
- Removed non-standard `argument-hint` frontmatter from skills so skill metadata validates cleanly.
- Made the default `USAGE.md` English for public distribution and preserved the Korean guide as `USAGE.ko.md`.

### Added
- Optional query telemetry guidance. When hooks or wrappers are configured, `kb-query` can leave compact request-level records in `0. Common/query-telemetry.jsonl` for later analysis of route choice, inspected document count, elapsed time, tool calls, and token usage where available.
- README/USAGE/template notes explaining that telemetry is operational data, not knowledge content, and should not be indexed or read during ordinary vault search.
- Sanitized `examples/` showing fictional initialized indexes, a project hub, structural change log entries, and request-level telemetry records.
- README first-run context showing the expected post-`/kb-init` operating layer and links to English/Korean usage guides.

## 0.4.0 (2026-05-09)

### Added (USAGE)
- **`USAGE.md` Section 10 — Personalization Checklist** — 6-item list users walk through after install: `userIgnoreFilters`, `type` enum updates, tag prefixes, `_index` categorization, your own daily ingest routine hookup, log.md habit. Plugin reads vault-specific config; users own the conventions.
- **`USAGE.md` Section 11 — Anti-patterns** — common pitfalls discovered through real-world cleanup: sub-`_index.md` (breaks 2-tier concept), trusting raw `unresolved` counts (false-positive heavy), target-only progress measurement (instances ≠ targets), orphan-zero perfectionism, `_index.md` count drift.

### Fixed (kb-index SKILL)
- Corrected non-functional CLI example: `obsidian search query="type: kb-index"` → `grep -rln "^type: kb-index"` (search is full-text only, not frontmatter)

### Changed (kb-index SKILL)
- **Tier 3 generate rules** now explicitly state: one `_index.md` per PARA category only (no sub-folder `_index.md`), use `##` sub-section headers for catalog within the same file when sub-folder grows ≥6 items, link to overview files directly (`[[0. <project> 프로젝트 개요|<project>]]`) to prevent overview-file orphans.
- **Top-level index header rule**: each PARA section header must be a wikilink to its category `_index` (`## [[1. Projects/_index|Projects]]`). Without this, the four PARA `_index.md` files themselves register as orphans.

### Validated in operational use
- Confirmed that hub/index repair and user-configured exclusions reduce false-positive orphan results and unresolved-link noise. Exact effects vary by vault.

## 0.3.2 (2026-05-09)

### Added
- **kb-lint: "Obsidian-Native Exclusion Filters" section** — read `.obsidian/app.json` `userIgnoreFilters` and post-filter `obsidian orphans` results. Vault-specific exclusion intent (personal journals, templates, drafts) is honored without per-vault hardcoding in the plugin.
- `obsidian-cli orphans` does not natively respect `userIgnoreFilters`; SKILL.md now documents the post-filter pattern with a Python snippet.

### Validated
- Confirmed that reading user-configured filters excludes intentionally ignored journals, templates, and drafts from orphan analysis. Exact effects vary by vault.

## 0.3.1 (2026-05-09)

### Added
- **kb-lint: "Auto-fix Philosophy" section** — explicit design rationale for not bundling vault-specific batch-fix subcommands (`--batch-weekly-wikilink`, `--fix-moved-projects`, etc.). Plugin provides primitives (categories + CLI/sed) and Claude composes vault-specific fixes from them. Avoids exploding the option surface and keeps the plugin general.
- **Counting caveat in kb-lint** — `obsidian unresolved` counts distinct targets, not instances. Documented mismatch between target-level count change and instance-level fix progress (e.g. fixing 300 daily headers may drop unresolved count by only 1 because the target is shared). SKILL.md now requires reporting both numbers in `--fix` dry-run summary.

### Validated with representative data
- Confirmed that composed daily-header fixes reduce broken targets and that an Inbox-to-project ingest cycle round-trips cleanly with `obsidian move`.

## 0.3.0 (2026-05-09)

### Added
- **`USAGE.md`** — practical operations guide complementing the conceptual README:
  - 5-minute setup checklist
  - Morning routine integration (auto `/kb-ingest` when Inbox > 0) with bash example + tmux polling pattern
  - Weekly review integration (auto `/kb-lint` recommendation based on `obsidian unresolved`/`orphans` counts)
  - Inbox input channels (manual drop, web clipper, Discord/Slack bot, RSS, voice, email)
  - Project move automation via `obsidian move` + 6-step change procedure for vault `CLAUDE.md`
  - `/kb-query` Route examples (A–E) with concrete CLI mappings
  - 8-row troubleshooting table (CLI not found, false positives, plugin cache stale, folder-as-backlinks, etc.)
  - Recommended operating cadence (daily / weekly / quarterly)
- README links to USAGE.md after Quick Start

## 0.2.1 (2026-05-09)

### Fixed
- Corrected obsidian-cli command syntax in SKILL.md examples (verified by running each command):
  - `obsidian tag <name>` → `obsidian tag name=<tag>`
  - `obsidian property:read file=<name> property=<key>` → `obsidian property:read name=<key> file=<name>`
  - `obsidian property:set file=<name> property=<key> value=<v>` → `obsidian property:set name=<key> value=<v> file=<name>`
- Files affected: `skills/kb-lint/SKILL.md`, `skills/kb-query/SKILL.md`, `skills/kb-ingest/SKILL.md`

## 0.2.0 (2026-05-09)

### Changed
- **kb-lint**:
  - Replaced incorrect `obsidian links broken` command (does not exist) with `obsidian unresolved`
  - Orphan check now uses `obsidian orphans` directly — Obsidian's actual link graph
  - Added explicit false-positive exclusion rules: code blocks, inline backticks, Templater variables (`<%...%>`), frontmatter, external paths, folder wikilinks
  - Added `sed` pre-filter mask for grep fallback so false positives are stripped before extraction
  - Expanded orphan exclusion list (project overview files, template folders)
  - Added `--no-cli` flag for forcing grep fallback (debugging)
  - Token Efficiency section emphasizes single CLI call over vault-wide grep+read
- **kb-query**:
  - Route E (full-text) explicitly recommends `obsidian search` and `search:context query=...`
  - Corrected CLI examples — `obsidian tag <name>` for tag-based collection (not `search query="#tag"`)
  - Added Token Efficiency comparison table (CLI 5–25× cheaper than naive grep+read)
- **kb-ingest**:
  - CLI integration expanded with `obsidian move` (auto-updates vault wikilinks), `property:read/set`, `create`, `append`
  - `obsidian move` is now the preferred MOVE step — manual `mv` requires post-grep wikilink replacement

### Notes
- All changes are documentation/SKILL refinements — no API breakage
- Vault CLAUDE.md should reference `obsidian move` in its change procedure for best wikilink integrity (see updated `templates/CLAUDE.md.template` if applicable)

## 0.1.0 (2026-04-05)

### Added
- Initial release
- 5 skills: kb-init, kb-ingest, kb-query, kb-lint, kb-index
- CLAUDE.md and _index.md templates
- Obsidian CLI integration with grep/glob fallback
- Smart diff-based index updates (3-tier strategy)
- Hierarchical indexing (top-level + per-category)
- 4 navigation methods: folders, tags, wikilinks+backlinks, indexes
