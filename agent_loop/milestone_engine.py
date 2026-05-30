"""
Milestone state machine and boundary enforcement.

State transitions:
  IDLE → RUNNING → CLEANUP → AWAITING_APPROVAL → COMPLETE
                                     ↓ (rejected)
                                  RUNNING (with feedback injected)

State is persisted to {session_dir}/milestone_state.json.
"""
from __future__ import annotations

import json
import time
from enum import Enum
from pathlib import Path


class MilestoneStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    CLEANUP = "cleanup"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    COMPLETE = "complete"
    NEEDS_REVIEW = "needs_review"  # cleanup loop failed to reach clean state
    COUNCIL_PENDING = "council_pending"


class MilestoneEngine:
    def __init__(self, session_dir: str | Path, project_id: str, milestone_id: str):
        self.session_dir = Path(session_dir)
        self.project_id = project_id
        self.milestone_id = milestone_id
        self.state_path = self.session_dir / "milestone_state.json"

    def _load(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text())
        return {
            "project_id": self.project_id,
            "milestone_id": self.milestone_id,
            "status": MilestoneStatus.IDLE,
            "history": [],
            "feedback": [],
            "cleanup_result": None,
            "approved_at": None,
            "created_at": time.time(),
        }

    def _save(self, state: dict) -> None:
        self.state_path.write_text(json.dumps(state, indent=2))

    def _transition(self, state: dict, new_status: MilestoneStatus, note: str = "") -> dict:
        state["history"].append({
            "from": state["status"],
            "to": new_status,
            "at": time.time(),
            "note": note,
        })
        state["status"] = new_status
        return state

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        state = self._load()
        if state["status"] not in (MilestoneStatus.IDLE, MilestoneStatus.RUNNING):
            raise RuntimeError(
                f"Cannot start: milestone is in state '{state['status']}'"
            )
        state = self._transition(state, MilestoneStatus.RUNNING, "Agent launched")
        self._save(state)

    def begin_cleanup(self, trigger: str = "milestone_belief") -> None:
        """Called when agent emits MILESTONE_BELIEF or hard cap is reached."""
        state = self._load()
        state = self._transition(state, MilestoneStatus.CLEANUP, f"trigger={trigger}")
        self._save(state)

    def cleanup_complete(self, result: dict) -> None:
        """Called by cleanup_loop when all checks pass."""
        state = self._load()
        state["cleanup_result"] = result
        if result.get("clean"):
            state = self._transition(state, MilestoneStatus.AWAITING_APPROVAL, "Cleanup passed")
        else:
            state = self._transition(
                state, MilestoneStatus.NEEDS_REVIEW,
                f"Cleanup failed after {result.get('iterations', 0)} iterations"
            )
        self._save(state)

    def approve(self) -> None:
        """Called by Andrew via the dashboard to accept the milestone."""
        state = self._load()
        if state["status"] != MilestoneStatus.AWAITING_APPROVAL:
            raise RuntimeError(
                f"Cannot approve: milestone is in state '{state['status']}' "
                f"(must be awaiting_approval)"
            )
        state["approved_at"] = time.time()
        state = self._transition(state, MilestoneStatus.COMPLETE, "Approved by Andrew")
        self._save(state)

    def reject(self, feedback: str) -> None:
        """
        Called by Andrew to send the milestone back with feedback.
        Agent will be resumed with the feedback injected into context.
        """
        state = self._load()
        if state["status"] not in (MilestoneStatus.AWAITING_APPROVAL, MilestoneStatus.NEEDS_REVIEW):
            raise RuntimeError(
                f"Cannot reject: milestone is in state '{state['status']}'"
            )
        state["feedback"].append({"text": feedback, "at": time.time()})
        state = self._transition(state, MilestoneStatus.RUNNING, f"Rejected: {feedback[:80]}")
        self._save(state)

    def flag_council(self) -> None:
        state = self._load()
        state = self._transition(state, MilestoneStatus.COUNCIL_PENDING, "Council request filed")
        self._save(state)

    def council_resolved(self) -> None:
        state = self._load()
        state = self._transition(state, MilestoneStatus.RUNNING, "Council decision injected")
        self._save(state)

    def status(self) -> MilestoneStatus:
        return MilestoneStatus(self._load()["status"])

    def read(self) -> dict:
        return self._load()

    def feedback_for_agent(self) -> str:
        """Returns accumulated feedback as a formatted string for injection into agent context."""
        state = self._load()
        items = state.get("feedback", [])
        if not items:
            return ""
        lines = ["## Feedback from Andrew\n"]
        for item in items:
            lines.append(f"- {item['text']}")
        return "\n".join(lines)

    def is_complete(self) -> bool:
        return self.status() == MilestoneStatus.COMPLETE

    def can_proceed_to_next(self) -> bool:
        """Hard gate: next milestone only starts after this one is COMPLETE."""
        return self.is_complete()
