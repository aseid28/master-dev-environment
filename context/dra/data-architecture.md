---
type: DRA
sensitivity: normal
last_updated: 2026-05-30
links: [[dra/pillars-services]] · [[dra/tech-stack]] · [[dra/index]]
---

# DRA — Data Architecture

How the three core systems are wired. **Asana** is the spine; **Salesforce** is the system of record; **HubSpot** is the activation/automation layer bidirectionally synced to it.

## Asana (project management — the core)
Two navigable hierarchies over the same work:

**A) By org structure**
`DRA portfolio → Division (Product / CX / Growth) → Pillar (Pipeline Gen, RevOps, DX, Branded Content) → Team/Dept portfolio (Paid Media, SEO, …) → Client-engagement portfolio (e.g. "Ping — Paid Media") → engagement-management project + individual projects.`

**B) By account**
`Account portfolio (owned by the account manager, holds account goals) → account-management project (ad-hoc admin) → the same client-engagement portfolios.`
So "Ping — Paid Media" lives in **both** the Paid Media team portfolio and the Ping account portfolio.

**Goals** attach at every level (engagement → team → pillar → division → company). **Ownership:** account managers own account portfolios; strategists own engagement portfolios; PMs own projects; directors own team portfolios; senior directors own pillar portfolios; I own division + DRA portfolios. **Personnel portfolios** exist per person (work projects, 1:1, training, reviews, personal goals).

**In progress:** building **per-team templates** so we can quote/estimate accurately, give better instructions, and hire less-expensive staff who can still execute. This is the heart of the current restructure.

## Salesforce (system of record)
- **Standard objects:** Account, Contact, Opportunity, Lead (we do use Lead).
- **Hygiene:** Account requires a **domain** (the unique key); dedupe on domain; required attribution fields (first/last touch, digital attribution → single source field that propagates Lead→Contact→Opportunity on conversion). Light use of SF Campaigns.
- **Custom objects:**
  - **Engagement** — the key one. An account has multiple engagements (e.g. Ping Paid Media vs. Ping Content Syndication); opportunities map to engagements (closed-won → new engagement). Two children:
    - **Upsells & Churn** — logs modifications (e.g. +$7k upsell, −$2k churn against a $10k base = $15k).
    - **Renewal** — tracks contract extensions.
- **Commissions** tracked on Opportunity via role-based formulas: **sourcer** (first to discuss; sales or CX, not both), **sales engineer** (tech side), **closer** + **senior closer** (sales side). Also tracked in Gusto/Bamboo at payroll.
- **Record types** per object (Account: prospect/client/partner; Opp: new-logo/renewal/expansion; etc.); validation rules everywhere.
- **Closed-won** triggers a manual **QA call** with stakeholders to lock sourcing/attribution/commissions/amounts. Two amount types: one-off project amount vs. recurring; plus a total-value calc on the opp (sales' primary metric).
- Reports feed BI + the financial model.
- Owned by ops + sales.

## HubSpot (activation layer)
- Every field/property on every object **bidirectionally synced** with Salesforce (most-recent-value wins; formula fields are the rough exception).
- Does for *us* what MOPS does for clients: account lifecycling, hygiene, reporting prep, attribution/sourcing, **form handling**, email marketing/newsletters/operational emails.
- **Cheap per-seat (~$15/user/mo)** vs. expensive Salesforce → we **democratize data** by giving everyone a HubSpot license (bidirectional sync means full access). Adoption is uneven — want people more comfortable self-serving in HubSpot.
- Acknowledged redundancy: SF + HubSpot overlap; keeping both for now because SF does some valuable things and the migration cost is high.
- Information-architecture goal: for every account → an account **Slack channel**, **Asana portfolio**, and **HubSpot record**, all accessible to everyone.
