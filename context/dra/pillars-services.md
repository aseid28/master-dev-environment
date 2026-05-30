---
type: DRA
sensitivity: normal
last_updated: 2026-05-30
links: [[dra/index]] · [[dra/org-structure]] · [[dra/data-architecture]] · [[dra/positioning]]
---

# DRA — Pillars & Services

CX (client services) is organized into **four pillars**, biggest → smallest. (We're debating merging #3 and #4.)

## 1. Pipeline Generation (largest)
- **Paid Media** — ads across Google, Bing, LinkedIn, Meta (FB/IG), Reddit, 6sense, Demandbase, + programmatic (StackAdapt, Zeta). The biggest team.
- **SEO / AEO** — organic + LLM-search optimization.
- **Content Syndication** — vendor-managed; one client (run by Danielle Jones).
- **Organic Social** — occasional, client-by-client.
- *(Email marketing could live here; never sold as standalone.)*

## 2. RevOps
- **MOPS (Marketing Ops)** — the biggest sub-team. Marketing-automation platforms; primary **HubSpot** (we're partners) + **Marketo**. Avoid legacy (Pardot, MS Dynamics). Builds lead/account scoring + lifecycling, lead routing, **attribution** (a major line), form handling, MQL logic.
- **CRM** — **Salesforce**-heavy.
- **Chat** — shrinking; was a Drift partner, **Drift sunsets end of Jan 2027**, so winding down.
- **Business Intelligence** — little direct revenue but supports all of pipeline-gen's reporting/strategy; builds internal dashboards; now heavily in the internal AI build. Run by Alexis Miske.

Architecture detail: [[dra/data-architecture]].

## 3. Digital Experience (DX)
- **Creative team** — ad sets, landing pages, email templates, creative retainers.
- **Web Dev team** — full websites, cookie-compliance, GA implementations, web retainers.
- Sells big as whole-website projects (creative phase → dev phase). Not currently profitable — see [[failure-modes]].

## 4. Branded Content (smallest / nascent)
High-value but hard to sell (C-suite audience, abstract deliverables). No current revenue on the books; likely merging into DX or referring out.

## Client outcomes
Ultimately some core **pipeline metric**: efficient cost-per-conversion / per-lead / per-MQL → cost-per-opp → pipeline-per-dollar → (advanced) pipeline influence / multi-touch attribution. Even a website project is ultimately about driving future pipeline.

## Delivery flow
Sell the **Roadmap** → it right-sizes the engagement → sales hands off to the strategist/PM (trust built during the roadmap) → set a 30/60/90 plan against the client's own goals (loaded into Asana, reported against) → execute as **open-and-shut projects** vs. **ongoing retainers**. Standardizing this flow is the in-progress work — today we lean on expensive, experienced people to "tap-dance" over process gaps. See [[dra/data-architecture]].
