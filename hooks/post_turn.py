#!/usr/bin/env python3
"""
Claude Code Stop hook — runs after every agent turn.

Reads token usage from the hook payload (stdin), updates the cost guard,
and exits with code 2 (block + stop) if the hard cap is exceeded.

Claude Code hook contract:
  - stdin: JSON with the stop/turn event
  - exit 0: continue
  - exit 2: block the action (hard stop)
  - stdout: message shown to the agent/user

Environment variables set by the orchestrator when launching the agent session:
  AGENT_SESSION_DIR   — path to the session state directory
  AGENT_PROJECT_ID    — project ID
  AGENT_RUN_ID        — run ID
  AGENT_COST_CAP_USD  — hard cap
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Allow importing from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_loop.cost_guard import CostGuard, tokens_from_env


def main() -> None:
    session_dir = os.environ.get("AGENT_SESSION_DIR")
    if not session_dir:
        # Not running inside a managed agent session — pass through.
        sys.exit(0)

    state_path = Path(session_dir) / "cost_state.json"
    if not state_path.exists():
        # Guard not initialized yet — pass through.
        sys.exit(0)

    # Read the hook payload from stdin
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        payload = {}

    # Extract token usage from the hook payload (Claude Code Stop event structure)
    usage = payload.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)
    cache_write = usage.get("cache_creation_input_tokens", 0)

    # Fall back to env vars if payload doesn't have usage (older Claude Code versions)
    if input_tokens == 0 and output_tokens == 0:
        env_tokens = tokens_from_env()
        if env_tokens:
            input_tokens, output_tokens, cache_read, cache_write = env_tokens

    guard = CostGuard(state_path)
    result = guard.record_turn(input_tokens, output_tokens, cache_read, cache_write)
    status = result["status"]
    state = result["state"]

    summary = (
        f"[cost-guard] ${state['total_cost_usd']:.4f} / ${state['cost_cap_usd']:.2f} "
        f"({state['pct_used']:.1f}%) — turn {state['turn_count']}"
    )

    if status == "hard_cap":
        print(
            f"{summary}\n"
            f"HARD CAP REACHED — session stopped. Remaining budget exhausted.\n"
            f"The orchestrator will trigger the cleanup loop.",
            file=sys.stderr,
        )
        # Write a sentinel file so the orchestrator knows why we stopped
        sentinel = Path(session_dir) / "HARD_CAP_REACHED"
        sentinel.write_text(json.dumps(state, indent=2))
        sys.exit(2)  # Block the next action — Claude Code will stop the session

    if status == "soft_cap":
        print(
            f"{summary}\n"
            f"WARNING: 80% of cost cap reached. Begin wrapping up current work.\n"
            f"Do not start new features. Aim to reach MILESTONE_BELIEF or a clean stopping point.",
            file=sys.stderr,
        )
        # Write soft-cap sentinel so orchestrator can monitor
        sentinel = Path(session_dir) / "SOFT_CAP_WARNED"
        sentinel.write_text(json.dumps(state, indent=2))
        sys.exit(0)  # Continue but warn

    # Normal turn — just log the cost summary for visibility
    print(summary, file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
