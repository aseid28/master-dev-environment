#!/usr/bin/env python3
"""
build_memory.py — derive the agent memory layer from the wiki.

Output:
  memory.jsonl  — canonical, agent-native (one self-describing record per line)
  memory.csv    — human-readable mirror

Record schema:
  id          stable slug
  text        atomic, self-contained fact (useful out of context)
  table       Facts | Assumptions | Anti-patterns | Context  (the 4-table model)
  entity      primary subject
  domain      Bio|Values|Frameworks|Health|Routines|Goals|People|DRA|Community
  status      durable | mutable
  confidence  high | med | low
  sensitivity normal | sensitive | restricted   (restricted = exclude from general context)
  source      wiki page it came from
  tags        list[str]
"""
import json, csv

UPDATED = "2026-05-30"

# (text, table, entity, domain, status, confidence, sensitivity, source, tags)
R = [
# ---------- BIO ----------
("Born 1987-08-03 in Palo Alto, CA (dad finishing a Stanford PhD).","Facts","self","Bio","durable","high","normal","bio-timeline.md",["origin"]),
("Grew up in Lake Oswego, OR (Portland suburb) from age 3.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["origin"]),
("Attended Dartmouth 2005–2009; major Middle Eastern Studies; family legacy school.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["education"]),
("Studied Arabic; study-abroad in Morocco 2007.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["education","languages"]),
("Professional online poker player 2006–2013 (high-stakes, regularly winning).","Facts","self","Bio","durable","high","normal","bio-timeline.md",["poker","work-history"]),
("Wrote the poker book 'Easy Game: Making Sense of No-Limit Hold'em' (2009).","Facts","self","Bio","durable","high","normal","bio-timeline.md",["poker"]),
("Poker's Black Friday (2011-04-15) shut down US online poker and froze his accounts.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["poker"]),
("Lived in Buenos Aires, Bangkok, Paris, and Portland before San Francisco.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["geography"]),
("Moved to San Francisco in 2012; roommates with Ben Childs.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["geography"]),
("First attended Burning Man in 2016; it became central to his life.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["burning-man"]),
("Co-founded Burning Man camp IQE (In Queso Emergency) in 2017.","Facts","self","Community","durable","high","normal","burning-man.md",["burning-man"]),
("Met Clara Merlino on 2018-10-04 in Seattle.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["clara"]),
("Married Clara Merlino on 2025-07-05.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["clara"]),
("Moved to New York / Williamsburg in 2022–2023.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["geography"]),
("Lives at 172 N 10th St 3A, Brooklyn, with Clara and roommate Scott.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["geography","home"]),
("Grandfather 'Papa' (mom's father) taught him piano; died 2016.","Facts","self","Bio","durable","high","normal","bio-timeline.md",["family","music"]),
("Identity anchors: husband, community leader/host, Burning Man organizer, DRA, musician, linguist. Not attached to NY-as-identity or sports fandom.","Context","self","Bio","durable","high","normal","bio-timeline.md",["identity"]),
("Teenage depression; suicidal ideation ~13–15, near-hospitalization, no true attempt; not depressed since ~16–17.","Facts","self","Health","durable","high","restricted","body-health.md",["mental-health"]),

# ---------- VALUES ----------
("Core values: feedback/honesty/courage, organization, community, proactivity, positivity, accountability, freedom.","Facts","self","Values","durable","high","normal","values.md",["values"]),
("Treats mental health and motivation as the precondition above all other goals.","Facts","self","Values","durable","high","normal","values.md",["values","mental-health"]),
("Politically libertarian-leaning: strong social liberalism but skeptical of government as problem-solver.","Facts","self","Values","durable","med","normal","values.md",["politics"]),
("Politically drifted from far-left to centrist; economically centrist, socially liberal.","Facts","self","Values","durable","med","normal","values.md",["politics"]),
("Holds Bayesian humility: assumes missing context, withholds hard conclusions, equivocates.","Facts","self","Frameworks","durable","high","normal","values.md",["epistemics"]),
("No core religious belief (Jewish dad, Catholic mom); gravitates toward Taoism / Tao Te Ching.","Facts","self","Values","durable","high","normal","values.md",["religion"]),
("Defines freedom as the right to choose which freedoms to trade away, not the absence of obligation.","Facts","self","Frameworks","durable","high","normal","frameworks.md",["freedom"]),

# ---------- FRAMEWORKS ----------
("Runs a process-vs-results orientation from poker: judge decisions by process quality, not noisy outcomes.","Facts","self","Frameworks","durable","high","normal","frameworks.md",["poker","decision-making"]),
("Views money as fluid/transactional; deliberately leans into good risks while tracking real downside.","Facts","self","Frameworks","durable","high","normal","frameworks.md",["money","risk"]),
("Lesson 'everywhere I went, there I was': place doesn't fix you; self-relationship does.","Facts","self","Frameworks","durable","high","normal","frameworks.md",["philosophy"]),
("Optimizes for balance across health × work × social (Ikigai); 'moderation, including moderation.'","Facts","self","Frameworks","durable","high","normal","frameworks.md",["balance"]),
("Guardrail against overbooking: makes no plans on Sundays.","Context","self","Routines","mutable","high","normal","frameworks.md",["balance","schedule"]),
("Selling model 'the mechanic problem': clients buy technical work on trust, so 'build trust first.'","Facts","self","DRA","durable","high","normal","frameworks.md",["sales","gtm"]),
("Believes go-to-market is holistic — ads, RevOps, web, brand can't be siloed.","Facts","self","DRA","durable","high","normal","frameworks.md",["gtm"]),
("Build philosophy: infrastructure before tools, tools before agents; small scoped agents over monoliths.","Assumptions","self","Goals","mutable","high","normal","frameworks.md",["ai","build"]),

# ---------- HEALTH ----------
("Lifts every other day on an A/B split; core lifts 3x5; cardio days are elliptical + bouldering.","Context","self","Health","mutable","high","normal","body-health.md",["training"]),
("Working weights: bench ~185, squat ~200, RDL ~365, shoulder press 65–70, rows ~170, weighted pull-ups +45.","Context","self","Health","mutable","med","normal","body-health.md",["training"]),
("Primary fitness metric is strength-to-weight (~3.63 now, target ~4.0).","Assumptions","self","Goals","mutable","high","normal","body-health.md",["fitness","goal"]),
("Wants to drop from ~200 lb to ~190 without losing strength.","Assumptions","self","Goals","mutable","high","normal","body-health.md",["fitness","goal"]),
("Long-standing goal: a 225 lb bench press.","Assumptions","self","Goals","mutable","med","normal","body-health.md",["fitness","goal"]),
("Chronic lower-back pain from a heavy-squat injury at 22; now committed to PT.","Facts","self","Health","durable","high","sensitive","body-health.md",["injury"]),
("Achilles tendinitis in both legs (linked to ski calf injuries); no jogging while flaring.","Facts","self","Health","durable","high","sensitive","body-health.md",["injury"]),
("Keratoconus in left eye, but right eye compensates; overall vision good, checked yearly.","Facts","self","Health","durable","high","sensitive","body-health.md",["vision"]),
("History of high cholesterol (~260 on keto); now on 10 mg atorvastatin daily, bloodwork normal.","Facts","self","Health","durable","high","restricted","body-health.md",["meds"]),
("Tonsils removed at 21 (+ sinus surgery); stopped getting sick the old way.","Facts","self","Health","durable","high","normal","body-health.md",["history"]),
("Therapist Allegra since 2018, ~monthly via Zoom; no current psych meds.","Facts","self","Health","durable","high","restricted","body-health.md",["mental-health"]),
("Alcohol ~6–7 drinks/week, clustered on big nights.","Context","self","Health","mutable","high","restricted","body-health.md",["substances"]),
("Caffeine 1–2 cups/day; morning cup at the gym, second ~2–3pm.","Context","self","Routines","mutable","high","normal","body-health.md",["caffeine"]),
("Enjoys psychedelics (LSD especially, MDMA/MDA, 2C-B, marijuana); mixed on psilocybin; not regular.","Context","self","Health","mutable","high","restricted","body-health.md",["substances"]),
("Sleep averages ~7h45m (8 Sleep mattress + Oura ring); excellent sleeper.","Facts","self","Health","durable","high","normal","body-health.md",["sleep"]),
("Stress shows as running warm and hunched/raised shoulders; has learned to catch and release it.","Context","self","Health","durable","high","sensitive","body-health.md",["stress"]),
("Sauna ~weekly at Bathhouse (Williamsburg); cold plunge but not late at night.","Context","self","Routines","mutable","med","normal","body-health.md",["recovery"]),

# ---------- ROUTINES ----------
("Daily shape: wake 7:30–8:30, coffee + creatine + atorvastatin, walk to Vital climbing gym, triage ~1–1.5h, workout, light lunch, calls ~1–6pm, dinner, bed ~10:30–11.","Context","self","Routines","mutable","high","normal","routines-preferences.md",["schedule"]),
("Protects mornings (to ~noon) for deep work + gym; only sales/high-value client calls allowed before noon.","Context","self","Routines","durable","high","normal","routines-preferences.md",["schedule"]),
("Pescatarian — buys no beef, pork, or chicken for the house (chicken a rare treat).","Facts","self","Routines","durable","high","normal","routines-preferences.md",["diet"]),
("Skips breakfast (coffee is breakfast), small lunch (300–500 cal), robust dinner; loves cooking peasant stews/curries.","Context","self","Routines","mutable","high","normal","routines-preferences.md",["diet"]),
("Travel: one-way tickets always, direct (pays +$100–200 to avoid stops), coach, cheapest fare, airline-agnostic, packs light/never checks.","Context","self","Routines","durable","high","normal","routines-preferences.md",["travel"]),
("Travel: no red-eyes; avoids pre-7:45am departures; if a flight is before 7:45am, pre-book an Uber/Lyft.","Context","self","Routines","durable","high","normal","routines-preferences.md",["travel"]),
("NYC airport preference: LGA > JFK; never EWR unless forced.","Context","self","Routines","durable","high","normal","routines-preferences.md",["travel"]),
("Window seat on night flights, aisle on day flights; won't usually pay to select seats.","Context","self","Routines","durable","high","normal","routines-preferences.md",["travel"]),
("Takes ~1–2 trips/month.","Context","self","Routines","mutable","med","normal","routines-preferences.md",["travel"]),
("Personal tech: MacBook Pro, iPhone, 3-monitor desk, Oura, 8 Sleep, LastPass, Superhuman over Gmail, Chrome work/personal profiles, Rectangle Pro.","Context","self","Routines","mutable","high","normal","routines-preferences.md",["tech"]),
("Note-taking is Apple Notes (idea stream triaged into Asana each morning); wants to move to Obsidian (sync issue stalling it).","Context","self","Routines","mutable","high","normal","routines-preferences.md",["tech","notes"]),
("Favorite band Metric (album 'Fantasies' is all-time favorite); also The Strokes, Daft Punk, indie/electro-pop.","Facts","self","Routines","durable","high","normal","routines-preferences.md",["music"]),
("Most formative books: 'The Idiot' (Dostoevsky), 'The Art of Happiness', 'Love and Limerence' (Tennov).","Facts","self","Routines","durable","high","normal","routines-preferences.md",["books"]),
("Plays MTG (limited/draft, a periodic time-sink) and chess (blitz on chess.com).","Context","self","Routines","mutable","high","normal","routines-preferences.md",["games"]),
("Hosts a weekly Survivor watch party.","Context","self","Routines","mutable","med","normal","routines-preferences.md",["hosting"]),
("Coffee: Cometeer flash-frozen concentrate at home; lattes/chai are a treat-out.","Context","self","Routines","mutable","high","normal","routines-preferences.md",["coffee"]),
("Clothing: almost all thrifted, colorful, relaxed-'swaggy'; wants to buy more good pieces.","Context","self","Routines","mutable","med","normal","routines-preferences.md",["style"]),

# ---------- GOALS ----------
("Top non-DRA project: an AI dev environment for managing autonomous dev agents in the cloud.","Context","self","Goals","mutable","high","normal","goals-projects.md",["ai","build"]),
("Build sequence: this wiki -> Garry Tan gBrain -> dev infrastructure -> the apps.","Assumptions","self","Goals","mutable","high","normal","goals-projects.md",["ai","plan"]),
("Wants dev agents to run autonomously to a cost cap or milestone, then pause for approval.","Assumptions","self","Goals","mutable","high","normal","goals-projects.md",["ai","agents"]),
("Has a backlog of ~40 apps to build, ordered by difficulty x business-risk.","Context","self","Goals","mutable","med","normal","goals-projects.md",["ai","backlog"]),
("Scrapping the monolithic 'LifeOS' in favor of small, single-purpose agents.","Assumptions","self","Goals","mutable","high","normal","goals-projects.md",["ai","scope"]),
("First tool to build: a triage agent that consolidates all inbound channels, ranks by urgency, and pre-drafts delegation/responses.","Assumptions","self","Goals","mutable","high","normal","goals-projects.md",["ai","triage"]),
("12-month professional goals: automate his work, fix triage, grow DRA on both profit and top line.","Assumptions","self","Goals","mutable","high","normal","goals-projects.md",["goal","dra"]),
("12-month personal goals: happy marriage, get genuinely fit, fix back + Achilles, life well-oriented in case of kids.","Assumptions","self","Goals","mutable","high","normal","goals-projects.md",["goal"]),
("5-yr good case: NY apartment + Seattle summer place, 1–2 kids, ski trips, DRA profitable enough to choose his work.","Assumptions","self","Goals","mutable","med","normal","goals-projects.md",["goal","5yr"]),
("'Stop worrying' money number: ~$150–250k/yr passive income (lives well on ~$250k now).","Assumptions","self","Goals","mutable","med","restricted","goals-projects.md",["money","goal"]),
("Skills to develop: AI tooling, leadership, rebuild piano, cooking, writing, Arabic.","Assumptions","self","Goals","mutable","med","normal","goals-projects.md",["skills"]),
("Building habits: fitness, fitness-aligned diet, sleep hygiene, default-to-AI-tools.","Assumptions","self","Goals","mutable","high","normal","goals-projects.md",["habits"]),
("Breaking habits: compulsive/boredom eating, exercise excuses, chronic lateness.","Anti-patterns","self","Goals","durable","high","sensitive","goals-projects.md",["habits"]),
("Bucket list: have kids, maybe live in New Orleans, India/Egypt/safari/Vietnam, ski Alps/Andes/NZ, win a live poker tournament.","Assumptions","self","Goals","mutable","low","normal","goals-projects.md",["bucket-list"]),

# ---------- FAILURE MODES ----------
("Anti-pattern: exports anxiety when stressed — becomes overbearing/micromanaging, undermines his own community-building. The #1 thing to catch.","Anti-patterns","self","Failure Modes","durable","high","sensitive","failure-modes.md",["self"]),
("Anti-pattern: repeatedly chooses his own happiness over potential success (a real trade-off).","Anti-patterns","self","Failure Modes","durable","high","sensitive","failure-modes.md",["self"]),
("Anti-pattern: does easy busywork instead of high-leverage work.","Anti-patterns","self","Failure Modes","durable","high","sensitive","failure-modes.md",["self"]),
("Anti-pattern: bottlenecks projects through himself; wants people to work as though he doesn't exist.","Anti-patterns","self","Failure Modes","durable","high","sensitive","failure-modes.md",["self","dra"]),
("Anti-pattern: automation paralysis — won't spend 2h automating a 5-min daily task despite obvious payoff.","Anti-patterns","self","Failure Modes","mutable","high","sensitive","failure-modes.md",["self","ai"]),
("Anti-pattern: ignored doctors' PT advice for his back at 22 -> years of avoidable chronic pain. Lesson: don't override expert advice outside his expertise.","Anti-patterns","self","Failure Modes","durable","high","sensitive","failure-modes.md",["self","lesson"]),
("Anti-pattern: overestimated his poker edge young, lost a few hundred K against better players.","Anti-patterns","self","Failure Modes","durable","high","sensitive","failure-modes.md",["self","poker"]),
("DRA anti-pattern: over-hired on both Digital Experience and growth/sales; eating margin.","Anti-patterns","DRA","DRA","mutable","high","restricted","failure-modes.md",["dra","ops"]),
("DRA anti-pattern: delivery margin ~60–65% vs. needed ~75% because team utilization is too low (per Parakeeto analysis).","Anti-patterns","DRA","DRA","mutable","high","restricted","failure-modes.md",["dra","finance"]),
("DRA anti-pattern: avoiding the austerity/layoffs that would reach real profitability, partly because the work would fall back on him.","Anti-patterns","DRA","DRA","mutable","high","restricted","failure-modes.md",["dra"]),
("Personal security gap: no VPN habit, doesn't understand the CrowdStrike setup, no backup strategy.","Anti-patterns","self","Failure Modes","mutable","med","sensitive","failure-modes.md",["security"]),
("Mentorship is a self-identified gap — few formal/informal mentors beyond his coach.","Anti-patterns","self","Failure Modes","durable","med","sensitive","people/inner-circle.md",["self"]),

# ---------- BURNING MAN ----------
("Burning Man camp IQE runs ~35 people/year; he is one of two core leaders (with Nick Binger).","Facts","self","Community","durable","high","normal","burning-man.md",["burning-man"]),
("Taking Burning Man off in 2026; returning in 2027.","Context","self","Community","mutable","high","normal","burning-man.md",["burning-man"]),
("Burning Man cadence: a mid-year Reno prep trip (Apr–Jul) + the event ~Aug 20 to ~Sep 2.","Context","self","Community","durable","med","normal","burning-man.md",["burning-man","travel"]),
("Burning Man co-organizers: Nick Binger, Stephanie Stern, Dan Bookstaber.","Facts","self","Community","durable","med","normal","burning-man.md",["burning-man"]),

# ---------- PEOPLE: CLARA ----------
("Clara Merlino is his wife; highest-EQ person he knows; her balance offsets his emotional volatility.","Facts","Clara Merlino","People","durable","high","normal","people/clara-merlino.md",["clara"]),
("Kids: active 'when' discussion, he lets Clara lead; working window late Oct 2026 or Feb 2027, likely not within 12 months.","Assumptions","Clara Merlino","People","mutable","med","normal","people/clara-merlino.md",["clara","kids"]),
("Exploring buying a NY apartment ~Sept 2026.","Assumptions","self","Goals","mutable","med","normal","people/clara-merlino.md",["home"]),
("Clara's trust is, by mutual agreement, NOT marital/joint property; he doesn't plan around it.","Facts","Clara Merlino","People","durable","high","restricted","people/clara-merlino.md",["clara","finance"]),
("Intimacy ~2–3x/week when both in town (~1.5x net with travel).","Context","Clara Merlino","People","mutable","high","restricted","people/clara-merlino.md",["clara"]),
("Built a Vanlife van with Clara during COVID (~90% done); it lives in Seattle with Karen Vezie & Isaac Sappington.","Facts","Clara Merlino","People","durable","high","normal","people/clara-merlino.md",["clara","van"]),

# ---------- PEOPLE: FAMILY ----------
("Parents are alive and together in Issaquah, WA; love French/Italian things, daily morning cappuccino.","Facts","Parents","People","durable","high","normal","people/parents.md",["family"]),
("Dad (~76) founded Sarabyte (ex-Mentor Graphics); doesn't drink; weekly French call with Andrew.","Facts","Dad","People","durable","high","normal","people/parents.md",["family"]),
("Mom (~72–73), former stay-at-home, outstanding cook, loves wine; some emotional tension with her at times.","Facts","Mom","People","durable","high","sensitive","people/parents.md",["family"]),
("Gift in place: an Illy coffee subscription for his parents.","Context","Parents","People","mutable","med","normal","people/parents.md",["family","gift"]),
("James (middle brother, ~39) lives in Juneau, AK with wife Lia and kids Ida (9) and Wally (7); ex-Google sales (20 yrs), semi-retired; trusted for financial advice.","Facts","James","People","durable","high","normal","people/james.md",["family","advice"]),
("Dave (oldest brother, ~42) lives in Issaquah, WA with wife Julia and kids Evie (11) and Dylan (7); senior cybersecurity expert; trusted for technical advice.","Facts","Dave","People","durable","high","normal","people/dave.md",["family","advice"]),
("Dave uses they/them pronouns — but NOT around the parents. Honor they/them in Andrew's contexts; never out them to family.","Facts","Dave","People","durable","high","restricted","people/dave.md",["family","pronouns"]),

# ---------- PEOPLE: CO-FOUNDERS ----------
("Ben Childs is co-founder and President of DRA (sales); friend since elementary school in Lake Oswego.","Facts","Ben Childs","People","durable","high","normal","people/ben-childs.md",["dra","cofounder"]),
("Ben is on a performance plan with salary moved to a commission basis; has chronically missed sales targets.","Facts","Ben Childs","People","mutable","high","restricted","people/ben-childs.md",["dra","perf"]),
("After the 2024–25 restructure, Ben is no longer DRA's majority shareholder; Andrew and Zach could terminate his employment.","Facts","Ben Childs","People","durable","high","restricted","people/ben-childs.md",["dra","equity"]),
("Ben has a form of epilepsy and keeps health/personal matters very close.","Facts","Ben Childs","People","durable","high","restricted","people/ben-childs.md",["health"]),
("Ben takes feedback well but doesn't follow through or change behavior; the most depleting work relationship.","Context","Ben Childs","People","mutable","high","restricted","people/ben-childs.md",["dra","perf"]),
("Working norm: route all sales to Ben + Ashley; Ben's highest-value mode is in-person (planes, conferences, events).","Context","Ben Childs","People","durable","high","normal","people/ben-childs.md",["dra","norm"]),
("Zach is a DRA co-founder who left to start a non-competing agency in politics; best friend since age 5, now largely estranged.","Facts","Zach","People","durable","high","restricted","people/zach.md",["dra","cofounder"]),
("Zach threatened litigation over Ben's alleged fiduciary-duty violations; communication turned hostile.","Facts","Zach","People","durable","high","restricted","people/zach.md",["dra","legal"]),
("Zach pushes hard for profit distributions and resents the founders' salaries; consistently anxiety-inducing for Andrew, especially around money.","Context","Zach","People","mutable","high","restricted","people/zach.md",["dra","money"]),

# ---------- PEOPLE: INNER CIRCLE ----------
("Scott Seiver is his roommate and lifelong friend (poker origin). RESTRICTED: Scott lives there secretly from the landlord — never disclose to the landlord.","Facts","Scott Seiver","People","durable","high","restricted","people/inner-circle.md",["friends","home"]),
("Nick Binger: Burning Man IQE co-leader (poker origin); go-to for technical/logistical problem-solving. Distinct from DRA's Nick Renard.","Facts","Nick Binger","People","durable","high","normal","people/inner-circle.md",["friends","advice"]),
("Adrian: possibly his best friend, lives in SF; one of his two emotional/2am calls.","Facts","Adrian","People","durable","high","normal","people/inner-circle.md",["friends","advice"]),
("Sam Kennedy: Dartmouth friend in Seattle; frequent ski partner and emotional-support person.","Facts","Sam Kennedy","People","durable","high","normal","people/inner-circle.md",["friends"]),
("Dan Bookstaber: NY friend, Burning Man co-organizer, gives informal business advice.","Facts","Dan Bookstaber","People","durable","high","normal","people/inner-circle.md",["friends","advice"]),
("Advice map: emotional -> Clara/Sam/Adrian; logistical -> Nick Binger; financial -> James/Dan Bookstaber; business -> Brian Flanagan.","Context","self","People","durable","high","normal","people/inner-circle.md",["advice"]),
("Brian Flanagan is his executive coach (currently ad-hoc; wants monthly).","Context","Brian Flanagan","People","mutable","high","normal","people/inner-circle.md",["advice","coach"]),
("Lapsed/strained friendships: Conlin (wishes he'd reciprocated), Andy (consciously dropped), Alexis (IQE co-founder), Aviva/Donny (bandwidth).","Context","self","People","mutable","med","sensitive","people/inner-circle.md",["friends","lapsed"]),

# ---------- DRA: CORE ----------
("DRA is a boutique B2B-technology go-to-market agency, niched in security/cybersecurity and AI; Andrew is co-founder and COO.","Facts","DRA","DRA","durable","high","normal","dra/index.md",["dra"]),
("DRA's three service areas: pipeline generation, digital experience, RevOps.","Facts","DRA","DRA","durable","high","normal","dra/index.md",["dra","services"]),
("DRA's flagship product is the Go-to-Market Roadmap: a proprietary maturity-model diagnostic that right-sizes engagements (~$5k, 2–4 weeks).","Facts","DRA","DRA","durable","high","normal","dra/index.md",["dra","product"]),
("As COO, Andrew sits above all of client services, operations, and growth; directly manages Ben, Cimone, and Taylor.","Facts","self","DRA","durable","high","normal","dra/index.md",["dra","role"]),
("Andrew's DRA specialty: ABM, reporting & data attribution, and overall GTM architecture.","Facts","self","DRA","durable","high","normal","dra/index.md",["dra","expertise"]),
("DRA leadership council (5): Andrew, Ben Childs, Cimone McKenzie, Taylor Bridges, Ashley Vaughan.","Facts","DRA","DRA","durable","high","normal","dra/index.md",["dra","org"]),
("Wants to KEEP: managing/mentoring leaders, business-improvement strategy, crisis triage, financial strategy, hard sales, key relationships, podcasts/video, co-founder management.","Context","self","DRA","mutable","high","normal","dra/index.md",["dra","role"]),
("Wants to DELEGATE: task prioritization/follow-up, marketing content + social, financial modeling/QA, difficult client relationships, ABM/RevOps depth, event kickoff, new-tech exploration.","Context","self","DRA","mutable","high","normal","dra/index.md",["dra","role","delegate"]),
("DRA long-term vision: steady profit without long hours or draining work; optional later sale on good terms (no urgency).","Assumptions","self","DRA","mutable","high","normal","dra/index.md",["dra","vision"]),

# ---------- DRA: ORG / ROSTER ----------
("DRA leaders & locations: Taylor Bridges (Denver, pipeline gen/marketing), Cimone McKenzie (LA, ops + de-facto controller), C.R. McPhail they/them (Houston, RevOps), Alexis Miske (Asheville, BI), Jess Boisvenue (paid media), Sam Marmon (DX ops), Ashley Vaughan (sales).","Facts","DRA","DRA","durable","med","normal","dra/org-structure.md",["dra","org"]),
("DRA standouts: Ashley Vaughan, Sam Marmon, C.R. McPhail; likely Taylor Bridges.","Context","DRA","DRA","mutable","med","sensitive","dra/roster.md",["dra","perf"]),
("DRA performance concerns: Ben Childs (plan), Andrew Cabrelli (client bedside manner), Cat McCarty (under-qualified for senior asks).","Context","DRA","DRA","mutable","med","restricted","dra/roster.md",["dra","perf"]),
("DRA accountant: Dave Danic (does DRA + Andrew's & Ben's personal taxes); R&D credits via Strike Tax.","Facts","DRA","DRA","durable","high","normal","dra/roster.md",["dra","finance"]),

# ---------- DRA: PILLARS / ARCH / STACK ----------
("DRA's four CX pillars, biggest to smallest: Pipeline Generation, RevOps, Digital Experience, Branded Content.","Facts","DRA","DRA","durable","high","normal","dra/pillars-services.md",["dra","org"]),
("Drift (DRA's chat tool) sunsets end of January 2027; the chat line is winding down.","Context","DRA","DRA","mutable","high","normal","dra/pillars-services.md",["dra","tools"]),
("Branded Content has no current revenue and is likely merging into DX or being referred out.","Assumptions","DRA","DRA","mutable","med","normal","dra/pillars-services.md",["dra"]),
("DRA data architecture: Asana is the PM spine (dual hierarchy by org and by account), Salesforce is the system of record, HubSpot is the bidirectionally-synced activation layer.","Facts","DRA","DRA","durable","high","normal","dra/data-architecture.md",["dra","systems"]),
("Salesforce uses a custom 'Engagement' object with Upsells/Churn and Renewal children; commissions tracked by role on Opportunity.","Facts","DRA","DRA","durable","high","normal","dra/data-architecture.md",["dra","salesforce"]),
("HubSpot is cheap per-seat (~$15/user/mo), so DRA democratizes data access by licensing everyone (bidirectional sync with Salesforce).","Facts","DRA","DRA","durable","high","normal","dra/data-architecture.md",["dra","hubspot"]),
("In-progress restructure: per-team Asana templates to enable accurate quoting and hiring less-expensive staff who can still execute.","Context","DRA","DRA","mutable","high","normal","dra/data-architecture.md",["dra","ops"]),
("DRA core stack: Asana, Salesforce, HubSpot, WordPress, Webflow, Funnel.io -> Power BI.","Facts","DRA","DRA","durable","high","normal","dra/tech-stack.md",["dra","tools"]),
("DRA is mostly an Anthropic Claude shop for AI (a little OpenAI); building a BigQuery data layer for the internal AI program.","Facts","DRA","DRA","durable","high","normal","dra/tech-stack.md",["dra","ai"]),

# ---------- DRA: FINANCE (restricted) ----------
("DRA revenue this year ~$3.5–4.5M (peaked ~$5.5M); likely bottomed ~Mar–Apr 2026.","Facts","DRA","DRA","mutable","high","restricted","dra/financials-equity.md",["dra","finance"]),
("DRA profit is tight (~4%, should be ~20%); nearly all profit comes from a pass-through financial-services line that could vanish.","Facts","DRA","DRA","mutable","high","restricted","dra/financials-equity.md",["dra","finance"]),
("DRA equity (LOW CONFIDENCE — reconcile vs cap table): capital ~Ben 35 / Zach 35 / Andrew 30; profit ~Andrew 40 / Ben 30 / Zach 30; Andrew vesting last third through end 2027.","Facts","DRA","DRA","durable","low","restricted","dra/financials-equity.md",["dra","equity"]),
("Andrew's DRA salary ~$234,500 + 40% profit interest; only one profit distribution ever (~$33–35k, early 2026).","Facts","self","DRA","mutable","high","restricted","dra/financials-equity.md",["dra","comp"]),
("DRA finance is partly broken: can't cleanly reconcile cash P&L vs accrual P&L vs balance sheet; fragile financial model; pass-through 'NiCE PO' bookkeeping eats Andrew's time; fractional CFO/controller hires have repeatedly failed.","Context","DRA","DRA","mutable","high","restricted","dra/financials-equity.md",["dra","finance"]),

# ---------- DRA: CLIENTS / COMPETITORS / POSITIONING ----------
("DRA serves two tranches: mid-market growth startups (Series A–D) and large enterprises (entered via acquisition or a champion).","Facts","DRA","DRA","durable","high","sensitive","dra/clients-competitors.md",["dra","clients"]),
("DRA's largest client is NICE (multibillion-$ CX software), 6+ years; paid media, creative, ABM + financial services.","Facts","DRA","DRA","durable","high","sensitive","dra/clients-competitors.md",["dra","clients"]),
("Other named DRA clients: Ping, NetSPI, Chainalysis, Accuris; enterprise names include Cloudflare, Cisco, VMware, Broadcom.","Facts","DRA","DRA","durable","med","sensitive","dra/clients-competitors.md",["dra","clients"]),
("DRA sales are dominated by referrals; marketing as a channel is brand-new (started ~1–2 months ago).","Facts","DRA","DRA","durable","high","normal","dra/clients-competitors.md",["dra","sales"]),
("DRA competitors: Refined Labs, Market Bridge, ClientBoost, Metric Theory, ROI DNA, Impactable, Ad Conversions; enterprise holdcos Mediacom, OMD.","Facts","DRA","DRA","durable","med","sensitive","dra/clients-competitors.md",["dra","competitors"]),
("DRA positioning rests on holistic GTM, friendship + honesty ('build trust first'), and a niche + proprietary maturity-model product.","Facts","DRA","DRA","durable","high","normal","dra/positioning.md",["dra","positioning"]),
]

FIELDS = ["id","text","table","entity","domain","status","confidence","sensitivity","source","tags","updated"]

def slug(entity, i):
    base = entity.lower().replace(" ","-").replace("/","-")
    return f"{base}-{i:03d}"

records = []
counter = {}
for (text, table, entity, domain, status, conf, sens, source, tags) in R:
    counter[entity] = counter.get(entity, 0) + 1
    records.append({
        "id": slug(entity, counter[entity]),
        "text": text, "table": table, "entity": entity, "domain": domain,
        "status": status, "confidence": conf, "sensitivity": sens,
        "source": source, "tags": tags, "updated": UPDATED,
    })

with open("memory.jsonl","w") as f:
    for r in records:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

with open("memory.csv","w",newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    for r in records:
        row = dict(r); row["tags"] = ";".join(r["tags"]); w.writerow(row)

# summary
from collections import Counter
print(f"records: {len(records)}")
print("by table:", dict(Counter(r['table'] for r in records)))
print("by sensitivity:", dict(Counter(r['sensitivity'] for r in records)))
print("by domain:", dict(Counter(r['domain'] for r in records)))
