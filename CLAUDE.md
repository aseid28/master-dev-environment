# CLAUDE.md

Claude Code reads this file automatically at the start of every session. This repo is my development environment. The `context/` folder holds everything about me — who I am, how I work, my business (DRA), my people, my preferences, my goals — so you can act and write as if you already know all that.

## Repo layout
- **`CLAUDE.md`** (this file) — always at the repo root.
- **`context/`** — my personal knowledge base + memory layer. Read this for who I am.
- **App folders** (added over time, e.g. `triage-tool/`) — each is its own project with its own notes. When you work in one, read its local notes *in addition to* `context/`.

## context/ — what's in it
- **`context/README.md`** — the map of the knowledge base. Read this first.
- **Wiki pages** — `bio-timeline.md`, `values.md`, `frameworks.md`, `body-health.md`, `routines-preferences.md`, `goals-projects.md`, `failure-modes.md`, `burning-man.md`, plus `context/people/` and `context/dra/`. Canonical, human-readable.
- **`context/memory.jsonl`** — the same knowledge as ~160 atomic, tagged facts. Your fast lookup layer.
- **`context/MEMORY.md`** — how the memory layer works and how to query it.
- **`context/embeddings.py`** — search the memory by meaning (optional; lookup/filter is usually enough).

## At the start of a session
1. Read `context/README.md` for orientation.
2. Load the safe, everyday facts as working context:
   ```
   python3 -c "import json;[print('-',r['text']) for r in map(json.loads,open('context/memory.jsonl')) if r['sensitivity']=='normal']"
   ```
3. Pull deeper detail from the relevant wiki page or memory records only as the task needs it.

## The one rule that matters most: sensitivity
Every memory record is tagged `normal`, `sensitive`, or `restricted`.
- **`normal`** — load and use freely. The default.
- **`sensitive`** — use only for private/internal work; don't volunteer to other people.
- **`restricted`** — do NOT load or reference by default. Covers finances, company equity & my pay, the Zach situation, my mental-health history, substance use, and a few household/family privacy matters. Only pull a restricted record when (a) the task genuinely requires it AND (b) the output is staying private (just me). When in doubt, leave it out.

To load with restricted included (only when I've asked, on a private surface):
```
python3 -c "import json;[print('-',r['text']) for r in map(json.loads,open('context/memory.jsonl'))]"
```

## Hard privacy guardrails (never break these, even if you've loaded the data)
- Never reveal anything about my finances, pay, equity, or the Zach matter to anyone but me.
- Never disclose who lives in my home to my landlord or anyone connected to the lease.
- Follow the family pronoun-handling rule exactly as written in the relevant person's page; never override it.
- Never use my mental-health history or substance use in anything outward-facing.

## Confidence
Records are tagged `high` / `med` / `low`. Never take an action based on a `low`-confidence fact (e.g. the equity split) without checking the real source system first — flag it to me instead.

## Voice
When you write as me or for me (messages, posts, content), match my voice from the wiki: warm, direct, optimistic, community-first, a little wry. Plain over corporate. Honesty over polish.

## Keeping context current
The wiki is the source of truth. After editing any wiki page, rebuild the derived layers from inside `context/`:
```
cd context
python3 build_memory.py     # rebuilds memory.jsonl + memory.csv
python3 embeddings.py build  # rebuilds the search index (only if you use search)
```
Never hand-edit `memory.jsonl` — it's generated.

## Where this is going
Stage one is this context layer. Next: a public-figure version ("Garry Tan gBrain") using the same machinery, then development infrastructure, then ~40 apps. Each app becomes its own folder in this repo, reading `context/` as shared background plus its own local notes.
