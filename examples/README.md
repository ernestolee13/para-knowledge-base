# Examples

This directory contains fictional, sanitized examples of the files a PARA KB vault may contain after `/kb-init`, light project use, and optional query telemetry setup.

Nothing here is copied from a real private vault. Names, paths, dates, and queries are deliberately generic.

## Tree

```text
examples/
  0. Common/
    index.md
    log.md
    query-telemetry.jsonl
  1. Projects/
    _index.md
    product-launch/
      _index.md
  telemetry/
    query-v1.jsonl
    build-v1.jsonl
    mixed-legacy-v1.jsonl
```

## How to read these examples

- `0. Common/index.md` is the top-level map an agent can read before opening many files.
- `1. Projects/_index.md` is a category-level map.
- `1. Projects/product-launch/_index.md` is an optional project hub for a larger or frequently queried project.
- `0. Common/log.md` captures structural changes, not every edit.
- `0. Common/query-telemetry.jsonl` shows request-level operational records for later cost, depth, and time analysis.
- `telemetry/query-v1.jsonl` and `telemetry/build-v1.jsonl` are the canonical synthetic contract fixtures used by consumers such as PARA Second Brain Viz.
- `telemetry/mixed-legacy-v1.jsonl` demonstrates the aliases that v1 consumers retain during migration.

Telemetry files are intentionally not indexed. They are useful for diagnostics and reports, not for ordinary knowledge retrieval.
