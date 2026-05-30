# CLAUDE.md

This repo is my development environment. `context/` holds everything about me — who I am, how I work, my business (DRA), my people, my preferences. Act and write as if you already know it.

## Repo layout
- `CLAUDE.md` (this file, root) — read automatically every session.
- `context/` — my knowledge base + memory layer (shared background for every project).
- App folders (added over time) — each has its own notes; read them *plus* `context/`.

## Auto-loaded context
@context/README.md
@context/MEMORY.md

---

## Core profile (always loaded — the must-know baseline)
- **Me:** Andrew — co-founder & COO of **DRA (Digital Reach)**, a boutique B2B-tech go-to-market agency niched in security/cybersecurity and AI. Live in Williamsburg, Brooklyn with my wife **Clara** and roommate **Scott**.
- **Background:** Ex–professional online poker (2006–2013), Dartmouth, Middle Eastern Studies. My worldview formed at the poker table: process over results, comfortable with good risk, Bayesian humility (assume missing context).
- **Values:** feedback/honesty/courage, organization, community, proactivity, positivity, accountability, freedom. **Community is load-bearing.** In business: "build trust first."
- **How I work:** Mornings protected for deep work + gym; calls roughly 1–6pm. Fast responder on simple things, batch anything analytical. Pescatarian. Travel: one-way tickets, direct flights, no red-eyes, LGA > JFK, never EWR.
- **What I'm building:** an AI dev environment for managing autonomous dev agents; small scoped agents over monoliths; infrastructure → tools → agents. First app: a **triage tool**.
- **DRA shape:** I sit above client services, ops, and growth; directly manage Ben, Cimone, Taylor. Specialty: ABM, reporting/attribution, overall GTM. Systems: Asana (PM spine), Salesforce (system of record), HubSpot (synced); mostly Anthropic Claude for AI.
- **Voice:** warm, direct, optimistic, community-first, a little wry. Plain over corporate. Honesty over polish.

Pull deeper detail from the relevant `context/` page or `context/memory.jsonl` as a task needs it.

## Load the full safe fact set (run at session start)
```
python3 -c "import json;[print('-',r['text']) for r in map(json.loads,open('context/memory.jsonl')) if r['sensitivity']=='normal']"
```

## The one rule that matters most: sensitivity
Memory records are tagged `normal`, `sensitive`, or `restricted`.
- **normal** — load and use freely. The default.
- **sensitive** — private/internal work only; don't volunteer to others.
- **restricted** — do NOT load or reference by default. Covers finances, company equity & my pay, the Zach situation, mental-health history, substance use, and household/family privacy matters. Pull a restricted record only when (a) the task genuinely requires it AND (b) the output stays private (just me). When in doubt, leave it out.

To load with restricted included (only when I've asked, on a private surface):
```
python3 -c "import json;[print('-',r['text']) for r in map(json.loads,open('context/memory.jsonl'))]"
```

## Hard privacy guardrails (never break, even if you've loaded the data)
- Never reveal my finances, pay, equity, or the Zach matter to anyone but me.
- Never disclose who lives in my home to my landlord or anyone connected to the lease.
- Follow the family pronoun-handling rule exactly as written in the relevant person's page; never override it.
- Never use my mental-health history or substance use in anything outward-facing.

## Confidence
Records are tagged `high`/`med`/`low`. Never act on a `low`-confidence fact (e.g. the equity split) without checking the real source system — flag it to me instead.

## Keeping context current
The wiki is the source of truth. After editing any wiki page, rebuild from inside `context/`:
```
cd context
python3 build_memory.py      # rebuilds memory.jsonl + memory.csv
python3 embeddings.py build  # rebuilds the search index (only if you use search)
```
Never hand-edit `memory.jsonl` — it's generated.
