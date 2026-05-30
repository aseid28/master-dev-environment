"""
Karpathy Council — multi-model design decision resolver.

Triggered when the agent writes council_request.json to the project workspace.
Spawns N Claude API calls with distinct persona system prompts, aggregates their
votes and reasoning, and writes council_decision.json with the recommendation.

Personas (configurable):
  - pragmatist: ship fast, minimize dependencies
  - security: minimize attack surface, follow OWASP
  - scalability: design for 10x without a rewrite
  - simplicity: fewer abstractions, easier to debug
  - devil_advocate: steelman the minority view

Usage:
  from agent_loop.council import convene
  decision = convene(request_path, work_dir)
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

COUNCIL_MEMBERS = {
    "pragmatist": (
        "You are the Pragmatist on a software design council. "
        "You prioritize shipping working software fast over architectural perfection. "
        "You favor fewer dependencies, simpler code, and decisions that unblock the team. "
        "When evaluating options, ask: which one gets us to working software fastest with fewest risks?"
    ),
    "security": (
        "You are the Security Expert on a software design council. "
        "You prioritize minimizing attack surface, following OWASP Top 10 guidance, "
        "and avoiding patterns that introduce vulnerabilities (SQL injection, secrets in logs, "
        "unvalidated inputs, insecure defaults). "
        "When evaluating options, ask: which one is hardest to exploit?"
    ),
    "scalability": (
        "You are the Scalability Architect on a software design council. "
        "You think about how the system behaves at 10x current load, "
        "where the bottlenecks will be, and what will require a painful rewrite later. "
        "When evaluating options, ask: which one will we not regret in two years?"
    ),
    "simplicity": (
        "You are the Simplicity Advocate on a software design council. "
        "You favor fewer abstractions, less indirection, and code that a new engineer "
        "can understand in 10 minutes. You are suspicious of clever solutions. "
        "When evaluating options, ask: which one is easiest to debug at 2am?"
    ),
    "devil_advocate": (
        "You are the Devil's Advocate on a software design council. "
        "Your job is to steelman the option that seems least popular and find its genuine merits. "
        "You challenge consensus and surface hidden tradeoffs the group might miss. "
        "When evaluating options, ask: what is everyone underestimating about the less-obvious choice?"
    ),
}

COUNCIL_MODEL = "claude-haiku-4-5-20251001"  # Fast, cheap; good enough for structured debate


def _ask_member(
    persona_name: str,
    system_prompt: str,
    question: str,
    context: str,
    options: list[str],
    api_key: str,
) -> dict:
    try:
        import anthropic
    except ImportError:
        return {"persona": persona_name, "error": "anthropic SDK not installed"}

    client = anthropic.Anthropic(api_key=api_key)

    user_message = (
        f"## Design Decision\n\n"
        f"**Question:** {question}\n\n"
        f"**Options:**\n"
        + "\n".join(f"- {o}" for o in options)
        + f"\n\n**Context:**\n{context}\n\n"
        f"## Your Task\n\n"
        f"Respond with a JSON object with exactly these fields:\n"
        f'{{"vote": "<one of the option strings, verbatim>", '
        f'"confidence": <1-5>, '
        f'"reasoning": "<2-3 sentences>", '
        f'"key_concern": "<the single most important thing to watch out for>"}}'
    )

    try:
        message = client.messages.create(
            model=COUNCIL_MODEL,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = message.content[0].text if message.content else "{}"
        # Extract JSON from response (model may wrap in markdown)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        parsed = json.loads(raw[start:end]) if start != -1 else {}
        parsed["persona"] = persona_name
        return parsed
    except Exception as e:
        return {"persona": persona_name, "error": str(e)}


def convene(
    request_path: str | Path,
    work_dir: str | Path,
    api_key: Optional[str] = None,
    personas: Optional[list[str]] = None,
) -> dict:
    """
    Read council_request.json, run the council, write council_decision.json.
    Returns the full decision dict.
    """
    request_path = Path(request_path)
    work_dir = Path(work_dir)

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY required for Karpathy Council")

    request = json.loads(request_path.read_text())
    decision_id = request.get("decision_id", "unknown")
    question = request["question"]
    context = request.get("context", "")
    options = request["options"]

    active_personas = personas or list(COUNCIL_MEMBERS.keys())
    print(f"[council] Convening for: {decision_id}", flush=True)
    print(f"[council] Question: {question}", flush=True)
    print(f"[council] Options: {options}", flush=True)
    print(f"[council] Polling {len(active_personas)} members...", flush=True)

    votes: list[dict] = []
    with ThreadPoolExecutor(max_workers=len(active_personas)) as executor:
        futures = {
            executor.submit(
                _ask_member,
                name,
                prompt,
                question,
                context,
                options,
                api_key,
            ): name
            for name, prompt in COUNCIL_MEMBERS.items()
            if name in active_personas
        }
        for future in as_completed(futures):
            vote = future.result()
            votes.append(vote)
            print(f"  [{vote.get('persona')}] → {vote.get('vote', 'ERROR')} "
                  f"(confidence: {vote.get('confidence', '?')})", flush=True)

    # Aggregate: weighted vote by confidence
    tally: dict[str, float] = {}
    for v in votes:
        if "error" in v or "vote" not in v:
            continue
        choice = v["vote"]
        confidence = v.get("confidence", 3)
        tally[choice] = tally.get(choice, 0) + confidence

    if not tally:
        winner = options[0]
        rationale = "Council could not reach consensus — defaulting to first option."
    else:
        winner = max(tally, key=lambda k: tally[k])
        total_weight = sum(tally.values())
        winner_pct = round(tally[winner] / total_weight * 100)
        supporting = [v for v in votes if v.get("vote") == winner and "error" not in v]
        rationale = (
            f"**Recommendation: {winner}** ({winner_pct}% of weighted votes)\n\n"
            f"**Supporting reasoning:**\n"
            + "\n".join(
                f"- [{v['persona']}]: {v.get('reasoning', '')}"
                for v in supporting
            )
        )
        dissent = [v for v in votes if v.get("vote") != winner and "error" not in v]
        if dissent:
            rationale += "\n\n**Dissenting views:**\n" + "\n".join(
                f"- [{v['persona']}] preferred {v.get('vote')}: {v.get('reasoning', '')}"
                for v in dissent
            )

    key_concerns = [v.get("key_concern", "") for v in votes if v.get("key_concern")]

    decision = {
        "decision_id": decision_id,
        "question": question,
        "options": options,
        "recommendation": winner,
        "rationale": rationale,
        "key_concerns": key_concerns,
        "vote_tally": tally,
        "raw_votes": votes,
        "convened_at": time.time(),
    }

    decision_path = work_dir / "council_decision.json"
    decision_path.write_text(json.dumps(decision, indent=2))
    print(f"[council] Decision written to {decision_path}", flush=True)
    print(f"[council] Recommendation: {winner}", flush=True)

    # Remove the request file so the agent doesn't re-trigger
    request_path.unlink(missing_ok=True)

    return decision


def format_for_agent(decision: dict) -> str:
    """Format council decision for injection into agent's CLAUDE.md context."""
    return (
        f"## Karpathy Council Decision\n\n"
        f"**Decision ID:** {decision['decision_id']}\n"
        f"**Question:** {decision['question']}\n\n"
        f"{decision['rationale']}\n\n"
        f"**Key concerns to keep in mind:**\n"
        + "\n".join(f"- {c}" for c in decision.get("key_concerns", []))
        + "\n\nImplement the recommendation above. Do not re-open this decision."
    )
