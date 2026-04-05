---
name: kb-ingest
description: Ingest documents into the PARA Knowledge Base. Classifies, moves, links, and indexes new documents from Inbox or a specified path. Use when new documents need processing into the vault.
argument-hint: [file-or-folder-path]
---

# KB Ingest — Document Intake + Classification + Linking

Process new documents into the Knowledge Base. Reads content, classifies into the right PARA location, generates metadata, creates wikilinks, updates related documents, and maintains indexes.

## Usage

```
/kb-ingest                      # Process all files in Inbox/
/kb-ingest path/to/file.md      # Process a specific file
/kb-ingest path/to/folder/      # Process all .md files in a folder
```

## Execution Flow

For each document to ingest:

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
type: paper                   # paper|note|reference|meeting|idea|log
tags:
  - "#proj/project-name"      # if project-related
  - "#type/paper"             # document type
  - "#topic/kubernetes"       # subject matter
related:
  - "[[Related Document]]"    # discovered relationships
source: https://...           # URL or citation (if applicable)
---
```

### 5. SUMMARIZE (long documents only)
For documents over 500 words:
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

### 9. LOG
Append to `0. Common/log.md`:
```
[2026-04-05] ingest | Document Title | → 2. Areas/Paper/ | updated 2 docs
```

## Batch Mode

When processing multiple files (Inbox/ or folder):
1. Read all files first for batch classification
2. Classify all at once (cross-document decisions are better)
3. Process moves, links, and backlinks
4. Update indexes once at end (not per-file)
5. Single batch log entry

## Obsidian CLI Integration

When available:
```bash
obsidian search query="related term"     # find related docs
obsidian backlinks file="Document"       # check existing backlinks
obsidian tags                            # verify tag consistency
```

Fallback (no CLI):
```
Grep for related terms, Glob for file discovery,
Read frontmatter for existing tags/links
```

## Safety Rules

- **Never delete** the original file — move only
- **Never modify** source document content beyond frontmatter and summary
- **Preserve** all existing wikilinks and formatting
- **Ask user** before creating new subdirectories
- **Ask user** when classification confidence is low
