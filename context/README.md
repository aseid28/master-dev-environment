---
type: index
subject: Andrew (DRA co-founder / COO)
generated: 2026-05-30
purpose: personal knowledge base, written first-person, built to load as agent context
---

# The Wiki

A structured, cross-linked knowledge base about me, generated from ~47k words of voice transcripts and a personal-assistant briefing doc. Written in first person on purpose — it's meant to be loaded as context by my development agents, and later forked into the [[Garry Tan gBrain]] using the same machinery.

## How to read the metadata
Every page opens with a YAML header. Agents parse it; I read the body.
- **type** — page category (People, DRA, Values, etc.)
- **sensitivity** — load policy (see tiers below)
- **last_updated** — staleness check
- **links** — `[[double-bracket]]` cross-refs (Obsidian-native)

Per-fact tags appear inline where it matters: `durable` vs `mutable`, a confidence read, and a sensitivity flag.

## Sensitivity tiers
- **normal** — load freely.
- **restricted** — present in the page, flagged inline, **excluded from general agent context by default**. Covers finances, intimacy, mental-health history, substance use, the Scott/landlord situation, Dave's pronouns-around-parents, and the Zach litigation. Load only when the task explicitly needs it and the surface is private.
- **sensitive** — load with care; don't volunteer to third parties.

## Map
**Self**
- [[bio-timeline]] — the dated arc
- [[values]] — what I optimize for
- [[frameworks]] — the mental models I actually run
- [[body-health]] — training, injuries, metrics *(restricted facts inside)*
- [[routines-preferences]] — schedule, diet, travel, tech, taste
- [[goals-projects]] — what I'm building, the 12-mo / 5-yr picture
- [[failure-modes]] — anti-patterns, personal and operational

**People** (`/people`)
- [[people/clara-merlino]] · [[people/parents]] · [[people/james]] · [[people/dave]]
- [[people/ben-childs]] · [[people/zach]] *(restricted)*
- [[people/inner-circle]] — Scott, Nick, Adrian, Sam, the Dans, + support pros

**DRA** (`/dra`)
- [[dra/index]] — what it is, my role, the plan
- [[dra/org-structure]] · [[dra/roster]]
- [[dra/pillars-services]] · [[dra/data-architecture]] · [[dra/tech-stack]]
- [[dra/financials-equity]] *(restricted)* · [[dra/clients-competitors]] · [[dra/positioning]]

## Known data-quality flags
- Birth: PA briefing says **Aug 3, 1987, Palo Alto**. Transcript garbled it ("2000 or 1987," "born in Connecticut"). Treating the briefing as canonical.
- Equity splits and some org details are self-reported with hedging — marked low/med confidence on their pages. Reconcile against Salesforce/cap table before any agent acts on them.
- Several names are phonetic from voice (e.g., Zach's surname, Cimone vs Simone). Verify spellings against the actual roster system.
