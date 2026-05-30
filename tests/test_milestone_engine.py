import sys
import tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_loop.milestone_engine import MilestoneEngine, MilestoneStatus


def _make_engine(tmp_path: Path) -> MilestoneEngine:
    return MilestoneEngine(tmp_path, "test-project", "m1")


def test_initial_status(tmp_path):
    engine = _make_engine(tmp_path)
    assert engine.status() == MilestoneStatus.IDLE


def test_start(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start()
    assert engine.status() == MilestoneStatus.RUNNING


def test_begin_cleanup(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start()
    engine.begin_cleanup("milestone_belief")
    assert engine.status() == MilestoneStatus.CLEANUP


def test_cleanup_complete_clean(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start()
    engine.begin_cleanup()
    engine.cleanup_complete({"clean": True, "iterations": 1})
    assert engine.status() == MilestoneStatus.AWAITING_APPROVAL


def test_cleanup_complete_dirty(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start()
    engine.begin_cleanup()
    engine.cleanup_complete({"clean": False, "iterations": 3})
    assert engine.status() == MilestoneStatus.NEEDS_REVIEW


def test_approve(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start()
    engine.begin_cleanup()
    engine.cleanup_complete({"clean": True})
    engine.approve()
    assert engine.status() == MilestoneStatus.COMPLETE
    assert engine.is_complete()
    assert engine.can_proceed_to_next()


def test_approve_wrong_state_raises(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start()
    with pytest.raises(RuntimeError):
        engine.approve()


def test_reject(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start()
    engine.begin_cleanup()
    engine.cleanup_complete({"clean": True})
    engine.reject("needs better error handling")
    assert engine.status() == MilestoneStatus.RUNNING


def test_reject_stores_feedback(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start()
    engine.begin_cleanup()
    engine.cleanup_complete({"clean": True})
    engine.reject("add logging")
    fb = engine.feedback_for_agent()
    assert "add logging" in fb


def test_history_recorded(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start()
    engine.begin_cleanup()
    state = engine.read()
    assert len(state["history"]) == 2


def test_can_proceed_only_when_complete(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start()
    assert not engine.can_proceed_to_next()
    engine.begin_cleanup()
    engine.cleanup_complete({"clean": True})
    assert not engine.can_proceed_to_next()
    engine.approve()
    assert engine.can_proceed_to_next()
