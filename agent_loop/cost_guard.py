"""
Cost guard: tracks cumulative USD spend per agent session and enforces the hard cap.

Pricing constants (update when Anthropic publishes new rates):
  claude-opus-4-8:  $15 / 1M input tokens, $75 / 1M output tokens
  claude-sonnet-4-6: $3 / 1M input tokens, $15 / 1M output tokens
  claude-haiku-4-5:  $0.80 / 1M input, $4 / 1M output

State is persisted to a JSON file at {session_dir}/cost_state.json so the
orchestrator and hooks can both read/write it atomically.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


PRICING_USD_PER_1M: dict[str, dict[str, float]] = {
    "claude-opus-4-8":   {"input": 15.00, "output": 75.00},
    "claude-opus-4-7":   {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6": {"input": 3.00,  "output": 15.00},
    "claude-haiku-4-5":  {"input": 0.80,  "output": 4.00},
}
DEFAULT_PRICING = {"input": 15.00, "output": 75.00}

SOFT_CAP_FRACTION = 0.80  # Warn at 80% of cap


@dataclass
class CostState:
    session_id: str
    project_id: str
    model: str
    cost_cap_usd: float
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    soft_cap_warned: bool = False
    hard_cap_hit: bool = False
    turn_count: int = 0
    events: list[dict] = field(default_factory=list)

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.cost_cap_usd - self.total_cost_usd)

    @property
    def pct_used(self) -> float:
        return self.total_cost_usd / self.cost_cap_usd if self.cost_cap_usd > 0 else 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["remaining_usd"] = self.remaining_usd
        d["pct_used"] = round(self.pct_used * 100, 1)
        return d


class CostGuard:
    def __init__(self, state_path: str | Path):
        self.state_path = Path(state_path)

    def _load(self) -> CostState:
        data = json.loads(self.state_path.read_text())
        events = data.pop("events", [])
        data.pop("remaining_usd", None)
        data.pop("pct_used", None)
        state = CostState(**data)
        state.events = events
        return state

    def _save(self, state: CostState) -> None:
        self.state_path.write_text(json.dumps(state.to_dict(), indent=2))

    @classmethod
    def init(
        cls,
        state_path: str | Path,
        session_id: str,
        project_id: str,
        model: str,
        cost_cap_usd: float,
    ) -> "CostGuard":
        state = CostState(
            session_id=session_id,
            project_id=project_id,
            model=model,
            cost_cap_usd=cost_cap_usd,
        )
        guard = cls(state_path)
        guard._save(state)
        return guard

    def record_turn(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> dict:
        """
        Record token usage for one agent turn.
        Returns a status dict: {"status": "ok"|"soft_cap"|"hard_cap", "state": ...}
        """
        state = self._load()
        pricing = PRICING_USD_PER_1M.get(state.model, DEFAULT_PRICING)

        # Cache reads are billed at 10% of input price; cache writes at 25%
        turn_cost = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
            + (cache_read_tokens / 1_000_000) * pricing["input"] * 0.10
            + (cache_write_tokens / 1_000_000) * pricing["input"] * 0.25
        )

        state.total_input_tokens += input_tokens + cache_read_tokens + cache_write_tokens
        state.total_output_tokens += output_tokens
        state.total_cost_usd += turn_cost
        state.turn_count += 1
        state.events.append({
            "turn": state.turn_count,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "turn_cost_usd": round(turn_cost, 6),
            "cumulative_cost_usd": round(state.total_cost_usd, 6),
        })

        if state.total_cost_usd >= state.cost_cap_usd:
            state.hard_cap_hit = True
            self._save(state)
            return {"status": "hard_cap", "state": state.to_dict()}

        if not state.soft_cap_warned and state.pct_used >= SOFT_CAP_FRACTION:
            state.soft_cap_warned = True
            self._save(state)
            return {"status": "soft_cap", "state": state.to_dict()}

        self._save(state)
        return {"status": "ok", "state": state.to_dict()}

    def read(self) -> CostState:
        return self._load()

    def is_hard_capped(self) -> bool:
        return self._load().hard_cap_hit

    def is_soft_capped(self) -> bool:
        state = self._load()
        return state.pct_used >= SOFT_CAP_FRACTION

    def summary(self) -> str:
        state = self._load()
        return (
            f"[cost] ${state.total_cost_usd:.4f} / ${state.cost_cap_usd:.2f} "
            f"({state.pct_used:.1f}%) — "
            f"{state.total_input_tokens:,} in / {state.total_output_tokens:,} out — "
            f"turn {state.turn_count}"
        )


def tokens_from_env() -> Optional[tuple[int, int, int, int]]:
    """
    Read token counts from env vars set by Claude Code's hook system.
    Returns (input, output, cache_read, cache_write) or None if not present.
    """
    try:
        return (
            int(os.environ.get("CLAUDE_INPUT_TOKENS", "0")),
            int(os.environ.get("CLAUDE_OUTPUT_TOKENS", "0")),
            int(os.environ.get("CLAUDE_CACHE_READ_TOKENS", "0")),
            int(os.environ.get("CLAUDE_CACHE_WRITE_TOKENS", "0")),
        )
    except (ValueError, TypeError):
        return None
