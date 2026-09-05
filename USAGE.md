# USAGE - Practical Operations Guide

README explains the concept, install flow, and skill list. This guide explains how to run the plugin day to day after installation.

Korean guide: [USAGE.ko.md](./USAGE.ko.md)
Fictional initialized-vault examples: [examples/](./examples/)

> Examples assume Claude Code, an Obsidian vault, and optional Obsidian CLI support. The same operating pattern works in other agent runtimes when they can read and write the vault files.

---

## 1. Five-minute first setup

```bash
# 1) Install the plugin, if needed
/plugin marketplace add ernestolee13/para-knowledge-base
/plugin install para-knowledge-base@para-knowledge-base

# 2) Open Claude Code in your Obsidian vault
cd ~/path/to/your-vault
claude

# 3) Initialize the KB layer
/kb-init

# 4) Smoke check
/kb-lint
ls Inbox
```

After `/kb-init`, your vault should have a small operational layer like this:

```text
CLAUDE.md
Inbox/
0. Common/
  index.md
  log.md
  query-telemetry.jsonl        # optional, only if configured
1. Projects/
  _index.md
  <project>/
    _index.md                  # optional project hub for large/frequent projects
2. Areas/
  _index.md
3. Resources/
  _index.md
4. Archive/
  _index.md
```

The exact folder names can differ, but the operating idea should stay stable: one schema file, cheap indexes, a change log, and optional request-level telemetry.

---

## 2. Daily and weekly operating loop

Use the skills as a maintenance loop, not as one-off commands:

| Frequency | Action | Why |
|---|---|---|
| Daily or whenever Inbox has files | `/kb-ingest` | Compile raw notes into durable PARA pages |
| During normal questions | `/kb-query "..."` | Start from indexes/tags/backlinks before reading full documents |
| Weekly or before review | `/kb-lint` | Find broken links, orphans, stale indexes, and drift |
| After large moves or cleanup | `/kb-index` | Rebuild maps after structure changed |

The plugin is most useful when new notes enter `Inbox/` regularly and `/kb-ingest` is run before the Inbox becomes a second unprocessed archive.

---

## 3. Inbox input channels

At least one capture path should feed `Inbox/`.

| Channel | Typical source | Flow |
|---|---|---|
| Manual drop | Finder/file manager | Save `.md` notes into `Inbox/` |
| Web clipping | Obsidian Web Clipper, Defuddle, browser automation | Clean page to markdown, then ingest |
| Chat or team messages | Slack/Discord/export scripts | Save useful messages as markdown |
| RSS/newsletters | RSS automation, email filters | Save candidate articles or summaries |
| Voice notes | Local transcription tools | Transcribe, save, ingest |
| Meeting notes | Calendar or meeting note automation | Drop raw notes into Inbox |

If `Inbox/` is always empty, `/kb-ingest` has nothing to compile.

---

## 4. Change procedure for moves, archives, and new pages

When files move, avoid leaving the indexes and wikilinks stale:

1. Move or create the files. Prefer Obsidian-aware move commands when available.
2. Update the relevant category `_index.md`.
3. Update `0. Common/index.md` if category counts or important entrypoints changed.
4. Review any dashboard or project hub that points to the old location.
5. Check unresolved links or backlinks for the moved topic.
6. Append one line to `0. Common/log.md` with date, change type, summary, and updated indexes.

For example:

```markdown
[2026-07-02] move | Archived completed product-launch notes | updated: 1. Projects/_index.md, 4. Archive/_index.md
```

This log is not meant to capture every edit. It should capture structural changes that help future agents understand why the vault changed.

---

## 5. Query routes

`/kb-query` should pick the cheapest route that can answer the question.

| Route | Good for | First move |
|---|---|---|
| A. Direct folder | Clear project/category question | Read the category index or project hub first |
| B. Tag/topic collection | Topic spans folders | Search tags or topic indexes, then inspect candidates |
| C. Backlink/reference | "What cites this?" or dependency questions | Use backlinks or targeted wikilink search |
| D. Index/log browse | Recent activity, overview, trend, status | Read only the relevant index/log window |
| E. Full-text search | Specific phrase, error, term, or unknown location | Use capped context search before opening files |

Example prompts:

```text
/kb-query "What is the current status and remaining risk for product launch?"
/kb-query "Find the notes related to customer interviews across the vault."
/kb-query "Which pages refer to the pricing plan?"
/kb-query "Summarize structural KB changes from the last two weeks."
/kb-query "Where did I write about retry policy configuration?"
```

The user should ask in natural language. The skill should choose routes based on the vault structure.

---

## 6. Optional query and build telemetry

Indexes tell the agent where to look. Telemetry tells you whether that lookup process is getting heavier over time.

Recommended path:

```text
0. Common/.telemetry/query-telemetry.jsonl
```

Principles:

- This is operational data, not knowledge content.
- Do not add it to `_index.md`.
- Do not read it during ordinary vault search.
- Read it only when analyzing search cost, usage patterns, or vault performance.
- The bundled shared hook/emitter records numeric facts such as elapsed time, tool calls, paths, and model tokens when available.
- The LLM adds one compact semantic summary with coarse request type, route, entrypoints, material document paths, placement/link evidence, and confidence; it never writes free-form query or note content.
- One semantic query/build operation shares one exact `operation_id` across start, step, summary, and complete events. `request_id` links operations from the same request; legacy `query_id` is only a compatibility alias.
- Measure `QueryStart → QueryComplete` or `BuildStart → BuildComplete`; keep whole-turn/session stop time as a separate diagnostic value.
- Store PARA prefixes, index names, spine paths, telemetry file, archive directory, retention, and exclusions as vault-relative values in `.para-kb/config.json`. Compatible consumers can read the same file.
- If token attribution cannot be separated between operations, retain N/A instead of copying a turn/session total.

Useful later questions:

- How many documents are read per query?
- Is full-text search becoming the default because indexes are weak?
- Are some projects getting expensive enough to need a project hub?
- Are elapsed time, tool count, or token usage increasing month by month?
- Does the vault need sub-indexes, a graph view, an external search index, or a graph database?

See [examples/telemetry/](./examples/telemetry/) for canonical synthetic records and [examples/0. Common/query-telemetry.jsonl](./examples/0.%20Common/query-telemetry.jsonl) for a legacy migration fixture.

---

## 7. Automation patterns

Automation should be conservative. Trigger ingest or reports automatically, but avoid destructive cleanup without review.

### Morning Inbox check

```bash
INBOX_COUNT=$(find "$VAULT/Inbox" -type f -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

if [ "$INBOX_COUNT" -gt 0 ]; then
  tmux send-keys -t "daily-session" \
    "Inbox has ${INBOX_COUNT} markdown files. Run the kb-ingest workflow and summarize the result." \
    Enter
fi
```

### Weekly lint recommendation

```bash
ORPHANS=$(obsidian orphans 2>/dev/null | wc -l | tr -d ' ')
UNRESOLVED=$(obsidian unresolved 2>/dev/null | wc -l | tr -d ' ')

if [ "$ORPHANS" -gt 50 ] || [ "$UNRESOLVED" -gt 100 ]; then
  printf "KB review suggested: %s orphans, %s unresolved links\n" "$ORPHANS" "$UNRESOLVED"
fi
```

Adjust thresholds to vault size. A large archive can have many acceptable orphans; a compact active wiki should have fewer.

---

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `/kb-*` skills don't appear, or only some do, even though the plugin shows as installed | The marketplace registration was lost while the plugin's cache/install entries remained — this can happen silently and disable all skills from the plugin | Check `~/.claude/plugins/known_marketplaces.json` for a `para-knowledge-base` entry. If it's missing, re-register with `/plugin marketplace add ernestolee13/para-knowledge-base`, then run `/plugin install para-knowledge-base@para-knowledge-base` and `/reload-plugins` |
| `/kb-ingest` makes no changes | `Inbox/` is empty | Add an input channel or drop markdown files into Inbox |
| `/kb-query` reads too many files | Indexes or project hubs are stale/missing | Run `/kb-index`, then retry |
| Unresolved link count is very high | Templates, code, external paths, or old links can be false positives | Classify false positives before bulk fixing |
| Orphan count is high | Archives, diaries, and drafts may be intentionally unlinked | Use ignore filters and report filtered counts |
| Obsidian CLI is unavailable | CLI disabled or missing from PATH | Enable Obsidian CLI or let skills fall back to file search |
| Backlinks for a folder fail | Backlinks operate on files, not folders | Query a note or project overview file |
| Telemetry is missing | `.para-kb/config.json` is absent/disabled, hooks are not trusted, or the operation never reached its semantic summary | Run `/kb-init --config-only`, review enabled hooks, then validate with the bundled helper; queries and ingest still work without telemetry |
| Logs are stale | Manual moves did not append `log.md` | Add the structural change line and rebuild indexes if needed |

---

## 9. Personalization checklist

After setup, tune the KB to your vault rather than forcing a universal schema:

- Decide which folders should be excluded from search and lint reports.
- Align frontmatter fields with values you actually use.
- Pick tag prefixes that fit your domain.
- Decide whether large projects need local `_index.md` project hubs.
- Configure query/build telemetry only if you want cost/depth/time/construction analysis; PARA Second Brain Viz can auto-detect the same `.para-kb/config.json` but also works independently with built-in or custom PARA profiles.
- Keep `0. Common/log.md` focused on structural changes.

---

## 10. Anti-patterns

### Creating sub-indexes everywhere

Do not add `_index.md` to every folder by default. Start with category indexes. Add project hubs only where a folder is large, active, or frequently queried.

### Treating raw unresolved counts as truth

Unresolved counts often include templates, code blocks, folder links, or external paths. Separate true broken knowledge links from acceptable technical noise.

### Chasing orphan-zero

Some notes should be isolated: archives, scratch notes, imported references, and personal logs. Measure meaningful orphans, not every file.

### Reading logs during every query

Logs are useful for time, change, trend, and root-cause questions. They are expensive and noisy for ordinary factual queries.

### Forgetting that indexes are compiled artifacts

Indexes are only valuable when maintained. After large reorganizations, run `/kb-index` or update the affected indexes manually.
