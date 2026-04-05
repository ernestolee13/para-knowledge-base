---
name: kb-lint
description: Health check for the PARA Knowledge Base. Detects orphan documents, broken links, index drift, tag issues, and stale content. Run periodically or as part of weekly review.
argument-hint: [--fix] [--category <name>]
---

# KB Lint — Knowledge Base Health Check

Audit the vault for structural issues, inconsistencies, and maintenance opportunities.

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

**Auto-fix:** Add unlisted files, remove missing entries, update counts and dates.

### 2. Orphan Documents
Files in PARA directories that have:
- No incoming `[[wikilinks]]` from other files
- No entry in any `_index.md`
- No tags

Exclude from check: `0. Common/daily/*`, `0. Common/weekly/*`, `_index.md`, `CLAUDE.md`, `Dashboard.md`.

**Report:** List orphans with suggested action (link, tag, or archive).

### 3. Tag Consistency

| Issue | Rule |
|-------|------|
| MISSING_PROJECT_TAG | File in `1. Projects/x/` lacks `#proj/x` |
| MISSING_TYPE_TAG | Paper file lacks `#type/paper` |
| BAD_TAG_FORMAT | Spaces or unexpected casing in tag |
| CROSS_REF_TAG | `#proj/x` tag on file outside Projects — note as intentional cross-reference |

**Auto-fix:** Add missing `#proj/` and `#type/` tags to frontmatter.

### 4. Broken Links
For each `[[wikilink]]` found in vault documents:
- Verify target file exists
- Report `BROKEN_LINK` if not found

With obsidian CLI: `obsidian links broken`
Without CLI: Grep for `\[\[.*?\]\]`, resolve each target.

### 5. Frontmatter Quality
Check documents in PARA directories for required fields:

| Field | Required? |
|-------|-----------|
| `title` | Yes |
| `created` | Yes |
| `tags` | Recommended |
| `type` | Recommended |

**Report:** Count of documents missing each field, list worst offenders.

### 6. Stale Content

| Issue | Condition |
|-------|-----------|
| POSSIBLY_STALE | Project file not modified >30 days |
| SHOULD_ARCHIVE | Completed project still in `1. Projects/` |
| MISPLACED | Active project found in `4. Archive/` |

## Output Format

```markdown
# KB Lint Report — {date}

## Summary
- Passed: N checks
- Warnings: N items
- Errors: N items

## Details
### Index Drift
...
### Orphan Documents
...
### Tag Issues
...
### Broken Links
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
| Error | Broken links, missing files | Some |
| Warning | Missing tags, orphans, stale content | Most |
| Info | Optimization suggestions | No |

## Log Entry

Append to `0. Common/log.md`:
```
[date] lint | passed N | warnings N | errors N | fixed N
```

## Arguments

| Argument | Effect |
|----------|--------|
| `--fix` | Auto-fix safe issues (index drift, tag addition) |
| `--category <name>` | Limit to one category: Projects, Areas, Resources, Archive |
