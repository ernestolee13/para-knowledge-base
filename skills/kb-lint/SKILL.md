---
name: kb-lint
description: Health check for the PARA Knowledge Base. Detects orphan documents, broken links, index drift, tag issues, and stale content. Run periodically or as part of weekly review.
---

# KB Lint — Knowledge Base Health Check

Audit the vault for structural issues, inconsistencies, and maintenance opportunities.

**Token-efficient by design**: prefer `obsidian-cli` calls (single command result) over reading full vault into context. CLI uses Obsidian's actual link resolution — much more accurate than naive `grep` matching.

When `.para-kb/config.json` exists, use its PARA roots, index names, telemetry paths, and exclusions. Remove `.para-kb/`, the Obsidian config directory, active/archive telemetry, runtime state, and generated reports from every document denominator before calculating orphan, frontmatter, stale-content, or index-drift metrics.

## Usage

```
/kb-lint                       # Full report (read-only)
/kb-lint --fix                 # Auto-fix safe issues
/kb-lint --category Projects   # Lint only one category
```

## Checks

### 1. Index Drift
Compare `_index.md` contents against actual files on disk.

| Issue | Meaning |
|-------|---------|
| MISSING | Listed in index but file not found |
| UNLISTED | File exists but not in index |
| STALE_COUNT | Count in top-level index doesn't match |
| STALE_INDEX | `updated` date > 7 days old |

CLI: `obsidian files folder="1. Projects"` for actual files; compare against `_index.md` lines.
Auto-fix: Add unlisted files, remove missing entries, update counts and dates.

### 2. Orphan Documents
Files with no incoming wikilinks.

**With CLI (preferred)**: `obsidian orphans` — uses Obsidian's actual link graph.

**Without CLI**: `comm -13 <(grep wikilinks sorted) <(find files sorted)`.

**Exclude (false positives)**:
- `0. Common/daily/*`, `0. Common/weekly/*`, `_index.md`, `CLAUDE.md`, `Dashboard.md`
- `.para-kb/*`, the configured Obsidian directory, active/archive telemetry, and generated report paths
- `0. ... 프로젝트 개요.md` — referenced by folder name in indexes, not by full filename
- `templates/*`, `_templates/*` — Obsidian Templater templates
- Any file with frontmatter `tags` containing project/topic tags (cross-folder reference is intentional)

Report: List orphans with suggested action (link, tag, or archive).

### 3. Tag Consistency

| Issue | Rule |
|-------|------|
| MISSING_PROJECT_TAG | File in `1. Projects/x/` lacks `#proj/x` |
| MISSING_TYPE_TAG | Paper file lacks `#type/paper` |
| BAD_TAG_FORMAT | Spaces or unexpected casing in tag |
| CROSS_REF_TAG | `#proj/x` tag on file outside Projects — note as intentional cross-reference |

CLI: `obsidian tags` to list all, `obsidian tag name=<tag>` to find files for a tag.
Auto-fix: Use `obsidian property:set` to add missing tags to frontmatter.

### 4. Broken Links

**With CLI (preferred)**: `obsidian unresolved` — Obsidian's resolved link graph reports actual unresolvable wikilinks.

**Without CLI**: `grep -rh -oE '\[\[[^]|#]+' . --include='*.md' | sed 's/^\[\[//' | sort -u` then compare against `find . -name '*.md' -exec basename {} .md \;`.

**False positive exclusion (apply to both CLI and grep results)**:
- Code blocks (` ``` ... ``` `)
- Inline code (` ` ... ` `) — e.g., when `` `[[wikilink]]` `` is shown as documentation
- Templater variables: `<% ... %>` content
- Frontmatter blocks (between `---`)
- External paths starting with `./`, `/`, `http*:`
- Folder wikilinks (`[[1. Projects/foo/]]`) — Obsidian resolves these to folders

Pre-filter command for grep fallback (mask false positives before extraction):
```bash
sed -E '/^---$/,/^---$/d; /^```/,/^```/d; s/`[^`]*`//g; s/<%[^%]*%>//g'
```

**macOS/iCloud + grep-fallback guards** (the CLI path already handles these through Obsidian's own resolver; apply only when `obsidian unresolved`/`orphans` is unavailable — a naive byte-level grep reintroduces all three):
- **Unicode NFC/NFD**: macOS stores Hangul (and other) filenames decomposed (NFD) while wikilink text is usually composed (NFC). Byte comparison then reports live files as broken and orphaned. Normalize both sides to NFC before comparing, e.g. pipe filenames and link targets through `python3 -c "import sys,unicodedata;[sys.stdout.write(unicodedata.normalize('NFC',l)) for l in sys.stdin]"`.
- **Table-cell pipe escape**: inside a markdown table an alias link is written `[[target\|alias]]`, where `\|` escapes the column separator. The naive `grep -oE '\[\[[^]|#]+'` then captures `target\` and flags it broken. Convert `\|` to `|` in the pre-filter (append `s/\\\|/|/g`) so the alias splits at the real separator.
- **Non-`.md` targets**: `[[foo.png]]`, `[[diagram.excalidraw]]` and other asset embeds point at real files, so the existence check must scan `find . -type f`, not only `*.md`. The inverse is a real error, not a false positive: a wikilink to a non-note without its extension (`[[report]]` for `report.pdf`) stays unresolved in Obsidian, so flag it and suggest adding the extension.

**Severity tiers**:
- Real broken (after FP filter, no matching file or folder): error
- Folder wikilink: skip (Obsidian-native)
- Templater/code/external: skip silently

### 5. Frontmatter Quality
Check documents in PARA directories for required fields:

| Field | Required? |
|-------|-----------|
| `title` | Yes |
| `created` | Yes |
| `tags` | Recommended |
| `type` | Recommended |
| `summary` | Recommended — `kb-ingest` writes this on every new document; older documents fall back to their first paragraph in `kb-query` |

CLI: `obsidian property:read name=title file=<name>` to check; bulk via `obsidian properties`.
Report: Count of documents missing each field, list worst offenders.

### 6. Stale Content

| Issue | Condition |
|-------|-----------|
| POSSIBLY_STALE | Project file not modified >30 days |
| SHOULD_ARCHIVE | Completed project still in `1. Projects/` |
| MISPLACED | Active project found in `4. Archive/` |

CLI: `obsidian file path=<file>` for mtime; `find -mtime +30` as fallback.

## Output Format

```markdown
# KB Lint Report — {date}

## Summary
- Passed: N checks
- Warnings: N items
- Errors: N items
- (CLI used: yes|no)

## Details
### Index Drift
...
### Orphan Documents
...
### Tag Issues
...
### Broken Links (real, after FP filter)
...
### Frontmatter Quality
...
### Stale Content
...

## Recommended Actions
1. {highest priority}
2. ...
```

## Severity

| Level | Examples | Auto-fixable |
|-------|----------|-------------|
| Error | Broken links, missing files | Some (--fix) |
| Warning | Missing tags, orphans, stale content | Most (--fix) |
| Info | Optimization suggestions | No |

## Token Efficiency

**Always prefer CLI**. A single `obsidian unresolved` call returns a few hundred bytes; running grep across hundreds of files into context costs 7K–10K tokens unnecessarily.

When CLI is unavailable:
1. Use `find ... -size` and `find ... -mtime` for stat-based checks (no read).
2. Use `grep -l` first to locate files; only `grep -h` content from those.
3. Apply false-positive `sed` mask before extracting wikilinks.
4. Use `comm -23 / -13` on sorted unique sets (linear time, no nested loops).

Avoid: reading every `.md` file into model context. The vault has 700+ files — that exceeds budget by an order of magnitude.

## Log Entry

Append to `0. Common/log.md`:
```
[date] lint | passed N | warnings N | errors N | fixed N | cli: yes|no
```

## Arguments

| Argument | Effect |
|----------|--------|
| `--fix` | Apply safe-category fixes (see Auto-fix Philosophy below) |
| `--category <name>` | Limit to one category: Projects, Areas, Resources, Archive |
| `--no-cli` | Force grep fallback even if obsidian-cli is available (for debugging) |

## Obsidian-Native Exclusion Filters

Obsidian vaults can declare exclusion paths in `.obsidian/app.json` under `userIgnoreFilters` (used by Obsidian's search to hide certain folders — common examples: personal journals, templates, draft directories). The path list is **vault-specific** — no two vaults share the same set, so the plugin reads whatever the user has already configured rather than hardcoding any path.

Whether `obsidian-cli orphans` applies these filters to its output depends on the installed CLI version — do not assume either way. Verify with a quick smoke test (check whether a file inside a known `userIgnoreFilters` path is still listed in `obsidian orphans`) before deciding whether post-filtering is needed. If the CLI does not apply the filters, post-filter to respect the user's intent:

```bash
# Read whatever exclusion paths the user has set in Obsidian
USER_IGNORES=$(python3 -c "
import json
try:
    d = json.load(open('.obsidian/app.json'))
    for p in d.get('userIgnoreFilters', []):
        print(p.rstrip('/'))
except: pass
")

# Apply to path-based results (orphan check)
obsidian orphans | grep -vFf <(echo "$USER_IGNORES") > orphans_filtered.txt
```

`obsidian unresolved` is **target-based**, not path-based, so `userIgnoreFilters` does not apply directly to its output. If a broken target string happens to overlap with an excluded prefix, you may filter as well, but typically `unresolved` is left raw.

**Reporting**: The plugin should output both `raw orphan count` and `filtered orphan count (after userIgnoreFilters)` so the user sees the effect. Effect varies per vault — typically 20-40% reduction when journals/templates are excluded, but a vault that doesn't use `userIgnoreFilters` shows zero change.

**Why this matters**: vault-specific exclusion intent honored *without* per-vault hardcoding inside the plugin. Each user's vault automatically benefits from whatever filters they've already set in Obsidian's GUI.

## Auto-fix Philosophy

This plugin **does not bundle vault-specific batch-fix subcommands** (e.g. `--batch-weekly-wikilink`, `--fix-moved-projects`). Adding one option per pattern explodes the surface and forces every vault to inherit assumptions that may not match.

Instead, the plugin gives Claude:
1. **Pattern categories** (the tables above) to classify broken/orphan into safe vs human-judgment buckets
2. **CLI + sed primitives** (Section "Token Efficiency", "Broken Links") to compose fixes
3. **Safety rules** (vault `CLAUDE.md`: preserve links, update affected indexes, append one structural log entry)

When `/kb-lint --fix` is invoked, Claude:
1. Runs `obsidian unresolved` / `orphans` (or grep+sed fallback)
2. Classifies into safe categories (e.g. old weekly headers, index drift, missing project tags) vs human-judgment (e.g. orphan archive vs link decision, moved-project alias matching)
3. Proposes a dry-run summary of safe-category batch fixes with vault-specific `sed`/`Edit` calls Claude composes from primitives
4. Applies after user confirmation, appends a single `[date] lint --fix | summary | N files | counts before→after` line to `log.md`

**Why this matters**: each vault has unique conventions (Templater patterns, project naming, archive structure). Hardcoding a `--batch-X` for every pattern Claude could detect would freeze the plugin to one vault style. Letting Claude compose fixes from primitives keeps the plugin general while still automating the boring mechanical work.

### Counting caveat

`obsidian unresolved` counts **distinct broken targets**, not **instances** that reference them. If 300 daily files all reference `[[2021-W44]]`, that's 1 unresolved count but 300 instances. After fixing the 300 instances, count drops by only 1 (sometimes 0 if other files still reference the same target). For meaningful "fix progress" measurement, also report **instance count** via `grep -rln '\[\[<target>\]\]' . | wc -l`.

When applying batch fixes, surface both numbers in the dry-run summary — count alone misleads.
