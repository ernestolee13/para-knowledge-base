---
name: kb-query
description: Query the PARA Knowledge Base to find information, synthesize answers from multiple documents, and optionally save insights. Use when asking questions about vault content or needing cross-document analysis.
argument-hint: "<question>"
---

# KB Query — Knowledge Search + Synthesis

Search the Knowledge Base, synthesize answers from multiple documents, cite sources with wikilinks, and optionally accumulate new insights as vault documents.

## Usage

```
/kb-query "list all papers related to ML" (또는 "k8s 관련 논문 전체 목록")
/kb-query "my-webapp deployment status" (또는 "bilingua 배포 상태")
/kb-query "documents referencing MyProject" (또는 "ChaosEater를 참조하는 문서")
/kb-query "summary of work in last 2 weeks" (또는 "최근 2주 작업 요약")
```

## Route Selection

Choose the optimal search path by question type. **Do not always start from the top-level index** — pick the fastest route.

### Route A: Direct Folder Access
**When:** Target is clearly in one PARA category.
```
"my-webapp deployment status" → read 1. Projects/my-webapp/ directly
"paper list" → read 2. Areas/Paper/_index.md then scan Paper/
```

### Route B: Tag Cross-Collection
**When:** Need to gather documents across folders by topic.
```
"everything about my-project" → search for #proj/my-project OR #topic/kubernetes across vault
"ML optimization related" → search #topic/ml-optimization
```

### Route C: Backlink Traversal
**When:** Need to find what references a specific document or entity.
```
"where is MyProject used" → search for [[MyProject]] and "MyProject"
"documents referencing this paper" → search for [[Paper Title]]
```

With obsidian CLI:
```bash
obsidian backlinks file="DocumentName"
```
Without CLI: Grep for `[[DocumentName]]` across vault.

### Route D: Index + Log Browse
**When:** Broad overview or temporal queries.
```
"최근 뭐 했지" → read 0. Common/log.md (last 20 entries)
"전체 현황" → read 0. Common/index.md
"Projects 개요" → read 1. Projects/_index.md
```

### Route E: Full-Text Search
**When:** Specific term or concept lookup.
```
"Prometheus metric setup" → Grep "Prometheus" across vault
"gradient descent" → Grep "gradient.descent" across vault
```

### Combined Routes
Complex questions may combine routes:
```
"key techniques in papers referenced by my-project"
  Route A: read project docs for paper references
  Route A: read each referenced paper
  Synthesize: compare techniques
```

## Execution Flow

### 1. PARSE
- Extract: subject, scope, temporal range, expected output type
- Select route(s): A, B, C, D, E, or combination
- Estimate token budget (stay under 10K tokens of source reading)

### 2. SEARCH
- Start with `_index.md` for orientation (10-20 lines, cheap)
- Read full documents only when needed for the answer
- Use Grep for targeted term search
- Expand with backlinks if initial results are insufficient

### 3. SYNTHESIZE
- Combine information from multiple sources
- **Always cite** with `[[wikilinks]]`
- Format by output type:
  - Lists: include file locations
  - Analysis: include evidence and reasoning
  - Timelines: chronological order
  - Comparisons: structured table

### 4. ACCUMULATE (optional)
Decide whether the result is worth saving:

| Result Type | Action |
|-------------|--------|
| Simple factual answer | Respond only |
| New insight or synthesis | Offer to save as document |
| Cross-document comparison | Suggest saving |
| List/catalog | Suggest if useful for reuse |

If saving:
- Choose PARA location
- Create with proper frontmatter and tags
- Add wikilinks to source documents
- Update `_index.md` and `log.md`
- Backlink from source documents

### 5. RESPOND

Format:
```markdown
## Answer
{Direct answer}

### Sources
- [[Doc 1]] — relevant detail
- [[Doc 2]] — relevant detail

### Related
- [[Other Doc]] — might be useful
```

## Obsidian CLI Integration

When `obsidian` is available (Obsidian 1.12+), prefer it for these operations:

```bash
# Route B: tag-based collection
obsidian tags sort=count counts          # tag inventory
obsidian search query="#proj/my-project"  # tag search

# Route C: backlink traversal
obsidian backlinks file="MyProject"      # precise backlinks

# Route E: full-text search
obsidian search query="Prometheus" limit=10   # native vault search

# Reading content
obsidian read file="Note Name"           # read by wikilink name
obsidian read path="1. Projects/_index.md"  # read by path
```

**Detection:** Check `which obsidian` or try direct call. If unavailable, fall back to Grep/Glob/Read tools.

**Complementary with kepano/obsidian-skills:** The `obsidian-cli` SKILL.md from kepano provides the full CLI reference. This skill focuses on *when* and *why* to use each command for knowledge queries.

## Token Efficiency

- Read `_index.md` first (~10-20 lines) before full documents
- Use CLI `search` or `Grep` to find specific sections, not read entire files
- For large documents, use `offset` + `limit` to read relevant portions
- Prioritize: index → frontmatter → target section → full document
