---
type: spec
last_updated: 2026-05-30
---

# Memory Layer

Derived from the wiki by `build_memory.py`. **The wiki is canonical; this is generated — never hand-edit `memory.jsonl`.** Re-run the script after editing wiki pages.

- `memory.jsonl` — canonical, agent-native (one record per line).
- `memory.csv` — human-readable mirror.
- **160 records** · Facts 86 / Context 42 / Assumptions 19 / Anti-patterns 13.

## Record schema
`id, text, table, entity, domain, status, confidence, sensitivity, source, tags, updated`
- **text** — atomic and self-contained (usable without the source page).
- **table** — your 4-table model: `Facts` (durable truths) · `Assumptions` (current beliefs/prefs that could change) · `Anti-patterns` (mistakes to never repeat) · `Context` (project-specific/current).
- **status** — `durable | mutable` · **confidence** — `high | med | low`.
- **sensitivity** — `normal | sensitive | restricted`.

## Retrieval rules (read before loading)
1. **Sensitivity is a hard gate.** Default load = `sensitivity == normal`. Load `sensitive` only for internal/private tasks. Load `restricted` (26 rows: finances, equity, intimacy/trust, mental health, substances, Zach, the landlord, Dave's pronouns) **only when the task explicitly requires it AND the output surface is private.**
2. **Filter before search.** Narrow by `entity` / `domain` / `tags` first (cheap, deterministic), then read `text`. e.g. `entity == "DRA" and sensitivity == "normal"`.
3. **Respect confidence.** Never take an action on `confidence == low` (e.g. the equity split) without verifying against the real source system.
4. **Handle Dave's pronoun rule** as written — it's encoded as a restricted record on purpose.

## Quick queries
```python
import json
rows = [json.loads(l) for l in open("memory.jsonl")]

# what an agent loads by default
ctx = [r for r in rows if r["sensitivity"] == "normal"]

# DRA facts, safe surface
dra = [r for r in rows if r["entity"]=="DRA" and r["sensitivity"]!="restricted"]

# anti-patterns to watch
aps = [r for r in rows if r["table"]=="Anti-patterns"]
```

## Regenerate
```
python3 build_memory.py    # rewrites memory.jsonl + memory.csv from the wiki
```

## Next step: semantic retrieval (optional)
Filtering covers you at this size. When the corpus grows (or for the gBrain), add embeddings: embed each `text`, store vectors + metadata in a small vector DB (or a flat numpy index), and at query time **filter by sensitivity first, then vector-match within the allowed set**. That ordering keeps restricted facts out of reach by construction.

---

# Embeddings Index (`embeddings.py`)

Vector search over the 160 records, with the sensitivity gate enforced **before** ranking — so restricted facts are unreachable via semantic similarity unless explicitly unlocked.

Artifacts: `index_vectors.npy` (160 × dim), `index_meta.jsonl` (records in vector order), `index_embedder.pkl` (the fitted vectorizer), `index_config.json` (embedder kind).

```
python3 embeddings.py build                       # build/refresh the index
python3 embeddings.py search "how does he travel"  # quick CLI search
```
```python
from embeddings import MemoryIndex
idx = MemoryIndex.load()
idx.search("equity split", k=5)                          # normal only (default)
idx.search("equity split", k=5, max_sensitivity="restricted")  # private surfaces only
idx.search("what tools", k=5, entity="DRA")              # scoped
idx.search("the model", min_confidence="high")           # confidence floor
```

**`search()` is filter-then-rank:** it builds the allowed candidate set from `max_sensitivity` (+ optional `entity`/`domain`/`table`/`min_confidence`), then runs cosine only within it. Verified: a query aimed straight at equity/salary returns **zero** restricted rows by default.

## Swapping in a neural embedder
The current embedder is **`TfidfEmbedder`** — offline, zero-network, lexical-semantic. Good enough at this size; it will mis-rank on pure paraphrase (no shared words). For the gBrain, swap to a neural model — **only the embedder class changes**, the index build and the gated search are identical:
```python
from embeddings import build_index, APIEmbedder
build_index(APIEmbedder(model="voyage-3"))   # fill in APIEmbedder._call for your provider
```
Run that in a networked env (this sandbox has no network). Voyage is Anthropic's recommended pairing; OpenAI `text-embedding-3-*` or a local `sentence-transformers` model work the same way.

