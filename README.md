# master-dev-environment

My cloud-based development environment. It holds two kinds of thing:

1. **Context** (`context/`) — a personal knowledge base + memory layer about me. Stable, shared background that every project reads.
2. **Apps** (added over time) — each project gets its own top-level folder with its own notes, building on top of the shared context.

```
master-dev-environment/
  CLAUDE.md         # how Claude Code should use this repo (read first)
  context/          # who I am, how I work, my business, my people  (shared)
  triage-tool/      # example future app — its own folder + own notes
  ...
```

## How it works
- `CLAUDE.md` at the root is read automatically by Claude Code at the start of every session.
- It points Claude Code at `context/` for background, and tells it the privacy/sensitivity rules.
- When work happens inside an app folder, Claude Code reads that app's local notes *plus* the shared `context/`.

## Start here
- Read `CLAUDE.md`, then `context/README.md`.
- The memory layer and how to query it: `context/MEMORY.md`.

## Notes
- The `context/index_*` files are a regenerable search index (`.gitignore`d by default). Rebuild with `cd context && python3 embeddings.py build`.
