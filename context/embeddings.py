#!/usr/bin/env python3
"""
embeddings.py — build a vector index over memory.jsonl and search it with a
HARD sensitivity gate (filter-then-rank, so restricted facts can't leak via
semantic similarity).

Embedder is pluggable:
  - TfidfEmbedder  : offline, zero-network, runs anywhere. Default. Lexical-semantic
                     baseline — good enough at this corpus size.
  - APIEmbedder    : template for a neural model (Voyage/OpenAI/etc). Swap this in
                     when running in a networked env. ONE class changes; the index
                     build + the sensitivity-gated search are identical.

Build:   python3 embeddings.py build
Search:  python3 embeddings.py search "how does andrew like to travel"
"""
import sys, json, pickle, numpy as np
from pathlib import Path

HERE = Path(__file__).parent
JSONL = HERE / "memory.jsonl"
VEC   = HERE / "index_vectors.npy"
META  = HERE / "index_meta.jsonl"
EMB   = HERE / "index_embedder.pkl"   # sklearn vectorizer only (tfidf) — picklable & portable
CFG   = HERE / "index_config.json"    # {"kind": ...} + any API params

TIER_ORDER = {"normal": 0, "sensitive": 1, "restricted": 2}


# ---------- embedders (pluggable) ----------
class TfidfEmbedder:
    """Offline. No network. Deterministic."""
    kind = "tfidf"
    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2),
                                   min_df=1, sublinear_tf=True, norm="l2")
        self.fitted = False
    def fit(self, texts):
        self.vec.fit(texts); self.fitted = True
    def embed(self, texts):
        X = self.vec.transform(texts).astype(np.float32)
        return np.asarray(X.todense())  # already L2-normalized


class APIEmbedder:
    """
    SWAP TARGET for a networked env. Fill in `_call` for your provider
    (Voyage is Anthropic's recommended pairing). Everything else here is unchanged.
        emb = APIEmbedder(model="voyage-3")
        build_index(emb)              # build with neural vectors
        MemoryIndex.load().search(...) # identical search + gate
    """
    kind = "api"
    def __init__(self, model="voyage-3", endpoint=None, api_key=None):
        self.model, self.endpoint, self.api_key = model, endpoint, api_key
    def fit(self, texts):  # no-op for API models
        pass
    def _call(self, texts):
        raise NotImplementedError(
            "Networked env only. Implement provider call here, return np.ndarray "
            "[len(texts), dim], L2-normalized.")
    def embed(self, texts):
        v = np.asarray(self._call(texts), dtype=np.float32)
        return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)


# ---------- build ----------
def build_index(embedder=None):
    embedder = embedder or TfidfEmbedder()
    rows = [json.loads(l) for l in open(JSONL)]
    texts = [r["text"] for r in rows]
    embedder.fit(texts)
    vectors = embedder.embed(texts).astype(np.float32)

    np.save(VEC, vectors)
    with open(META, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    cfg = {"kind": embedder.kind}
    if embedder.kind == "tfidf":
        with open(EMB, "wb") as f:
            pickle.dump(embedder.vec, f)   # the sklearn vectorizer pickles cleanly
    elif embedder.kind == "api":
        cfg.update({"model": embedder.model, "endpoint": embedder.endpoint})
    json.dump(cfg, open(CFG, "w"))
    print(f"indexed {len(rows)} records | dim={vectors.shape[1]} | embedder={embedder.kind}")


# ---------- search (sensitivity-gated) ----------
class MemoryIndex:
    def __init__(self, vectors, meta, embedder):
        self.vectors, self.meta, self.embedder = vectors, meta, embedder

    @classmethod
    def load(cls):
        vectors = np.load(VEC)
        meta = [json.loads(l) for l in open(META)]
        cfg = json.load(open(CFG))
        if cfg["kind"] == "tfidf":
            embedder = TfidfEmbedder()
            embedder.vec = pickle.load(open(EMB, "rb"))
            embedder.fitted = True
        else:
            embedder = APIEmbedder(model=cfg.get("model"), endpoint=cfg.get("endpoint"))
        return cls(vectors, meta, embedder)

    def search(self, query, k=8, max_sensitivity="normal",
               entity=None, domain=None, table=None, min_confidence=None):
        """FILTER FIRST, then rank. Restricted rows are unreachable unless explicitly allowed."""
        cap = TIER_ORDER[max_sensitivity]
        conf_order = {"low": 0, "med": 1, "high": 2}
        cmin = conf_order[min_confidence] if min_confidence else -1

        allowed = [i for i, r in enumerate(self.meta)
                   if TIER_ORDER[r["sensitivity"]] <= cap
                   and (entity is None or r["entity"] == entity)
                   and (domain is None or r["domain"] == domain)
                   and (table is None or r["table"] == table)
                   and conf_order[r["confidence"]] >= cmin]
        if not allowed:
            return []
        q = self.embedder.embed([query])[0]
        sub = self.vectors[allowed]
        sims = sub @ q                      # cosine (vectors are L2-normalized)
        order = np.argsort(-sims)[:k]
        out = []
        for j in order:
            r = dict(self.meta[allowed[j]]); r["score"] = round(float(sims[j]), 3)
            out.append(r)
        return out


# ---------- cli ----------
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build_index()
    elif cmd == "search":
        q = " ".join(sys.argv[2:]) or "what does andrew value"
        idx = MemoryIndex.load()
        for r in idx.search(q, k=6):
            print(f"[{r['score']}] ({r['entity']}/{r['domain']}) {r['text']}")
