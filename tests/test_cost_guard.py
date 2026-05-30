import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_loop.cost_guard import CostGuard, PRICING_USD_PER_1M, SOFT_CAP_FRACTION


def _make_guard(tmp_path: Path, cap: float = 1.0, model: str = "claude-opus-4-8") -> CostGuard:
    state_path = tmp_path / "cost_state.json"
    return CostGuard.init(state_path, "test-run", "test-project", model, cap)


def test_init_creates_state(tmp_path):
    guard = _make_guard(tmp_path)
    state = guard.read()
    assert state.total_cost_usd == 0.0
    assert state.hard_cap_hit is False
    assert state.turn_count == 0


def test_pricing_math():
    p = PRICING_USD_PER_1M["claude-opus-4-8"]
    cost = (1000 / 1_000_000) * p["input"] + (500 / 1_000_000) * p["output"]
    assert abs(cost - 0.05250) < 0.00001


def test_normal_turn(tmp_path):
    guard = _make_guard(tmp_path, cap=10.0)
    result = guard.record_turn(1000, 500)
    assert result["status"] == "ok"
    assert guard.read().turn_count == 1
    assert guard.read().total_cost_usd > 0


def test_soft_cap_triggers(tmp_path):
    guard = _make_guard(tmp_path, cap=0.10)
    # Burn through 80%+ with large token counts
    result = None
    for _ in range(20):
        result = guard.record_turn(50_000, 10_000)
        if result["status"] != "ok":
            break
    assert result["status"] in ("soft_cap", "hard_cap")


def test_hard_cap_triggers(tmp_path):
    guard = _make_guard(tmp_path, cap=0.001)  # $0.001 — tiny cap
    result = guard.record_turn(100_000, 50_000)
    assert result["status"] == "hard_cap"
    assert guard.is_hard_capped()


def test_hard_cap_sentinel_file(tmp_path):
    guard = _make_guard(tmp_path, cap=0.001)
    guard.record_turn(100_000, 50_000)
    assert guard.read().hard_cap_hit is True


def test_soft_cap_warned_only_once(tmp_path):
    guard = _make_guard(tmp_path, cap=1.0)
    statuses = []
    for _ in range(50):
        r = guard.record_turn(10_000, 5_000)
        statuses.append(r["status"])
        if r["status"] == "hard_cap":
            break
    soft_count = statuses.count("soft_cap")
    assert soft_count <= 1


def test_remaining_usd(tmp_path):
    guard = _make_guard(tmp_path, cap=1.0)
    guard.record_turn(0, 0)
    state = guard.read()
    assert state.remaining_usd == state.cost_cap_usd - state.total_cost_usd


def test_cache_tokens_billed_cheaper(tmp_path):
    d1 = tmp_path / "g1"; d1.mkdir()
    d2 = tmp_path / "g2"; d2.mkdir()
    guard1 = _make_guard(d1, cap=10.0)
    guard2 = _make_guard(d2, cap=10.0)
    # Same token count but guard2 uses cache reads (cheaper)
    guard1.record_turn(input_tokens=10_000, output_tokens=1_000)
    guard2.record_turn(input_tokens=0, output_tokens=1_000, cache_read_tokens=10_000)
    assert guard2.read().total_cost_usd < guard1.read().total_cost_usd
