"""
Notifier: writes structured events to SQLite and pushes them to connected
dashboard WebSocket clients. No outbound communication (email/Slack/webhook)
unless explicitly enabled per event.

Events are durable — written to DB first, then broadcast. Dashboard clients
that reconnect will see the full event history.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).parent.parent / ".sessions" / "events.db"


class EventType:
    AGENT_STARTED = "agent_started"
    MILESTONE_RUNNING = "milestone_running"
    SOFT_CAP_WARNING = "soft_cap_warning"
    HARD_CAP_REACHED = "hard_cap_reached"
    MILESTONE_BELIEF = "milestone_belief"
    CLEANUP_STARTED = "cleanup_started"
    CLEANUP_COMPLETE = "cleanup_complete"
    COUNCIL_REQUESTED = "council_requested"
    COUNCIL_DECIDED = "council_decided"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETE = "complete"
    SESSION_ENDED = "session_ended"
    NEEDS_REVIEW = "needs_review"


def _get_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            project_id TEXT NOT NULL,
            milestone_id TEXT,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_state (
            session_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            milestone_id TEXT,
            status TEXT NOT NULL,
            cost_usd REAL DEFAULT 0,
            cost_cap_usd REAL DEFAULT 0,
            model TEXT,
            last_updated REAL NOT NULL
        )
    """)
    conn.commit()
    return conn


class Notifier:
    def __init__(self, session_id: str, project_id: str, db_path: Path = DB_PATH):
        self.session_id = session_id
        self.project_id = project_id
        self.db_path = db_path
        self._ws_clients: list = []  # filled by dashboard backend

    def emit(
        self,
        event_type: str,
        milestone_id: Optional[str] = None,
        payload: Optional[dict] = None,
    ) -> None:
        """Write event to DB. Dashboard backend broadcasts from DB."""
        conn = _get_db(self.db_path)
        conn.execute(
            "INSERT INTO events (session_id, project_id, milestone_id, event_type, payload, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                self.session_id,
                self.project_id,
                milestone_id,
                event_type,
                json.dumps(payload or {}),
                time.time(),
            ),
        )
        conn.commit()
        conn.close()

    def update_agent_state(
        self,
        status: str,
        milestone_id: Optional[str] = None,
        cost_usd: float = 0.0,
        cost_cap_usd: float = 0.0,
        model: str = "",
    ) -> None:
        conn = _get_db(self.db_path)
        conn.execute(
            """
            INSERT INTO agent_state
                (session_id, project_id, milestone_id, status, cost_usd, cost_cap_usd, model, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                milestone_id = excluded.milestone_id,
                status = excluded.status,
                cost_usd = excluded.cost_usd,
                cost_cap_usd = excluded.cost_cap_usd,
                last_updated = excluded.last_updated
            """,
            (
                self.session_id,
                self.project_id,
                milestone_id,
                status,
                cost_usd,
                cost_cap_usd,
                model,
                time.time(),
            ),
        )
        conn.commit()
        conn.close()

    # ── Convenience methods ───────────────────────────────────────────────────

    def agent_started(self, milestone_id: str, cost_cap_usd: float, model: str) -> None:
        self.emit(EventType.AGENT_STARTED, milestone_id, {
            "cost_cap_usd": cost_cap_usd, "model": model
        })
        self.update_agent_state("running", milestone_id, 0, cost_cap_usd, model)

    def soft_cap_warning(self, milestone_id: str, cost_usd: float) -> None:
        self.emit(EventType.SOFT_CAP_WARNING, milestone_id, {"cost_usd": cost_usd})

    def hard_cap_reached(self, milestone_id: str, cost_usd: float) -> None:
        self.emit(EventType.HARD_CAP_REACHED, milestone_id, {"cost_usd": cost_usd})
        self.update_agent_state("hard_cap", milestone_id, cost_usd)

    def milestone_belief(self, milestone_id: str) -> None:
        self.emit(EventType.MILESTONE_BELIEF, milestone_id)
        self.update_agent_state("cleanup", milestone_id)

    def cleanup_complete(self, milestone_id: str, result: dict) -> None:
        status = "awaiting_approval" if result.get("clean") else "needs_review"
        self.emit(EventType.CLEANUP_COMPLETE, milestone_id, result)
        self.update_agent_state(status, milestone_id)

    def council_requested(self, milestone_id: str, decision_id: str, question: str) -> None:
        self.emit(EventType.COUNCIL_REQUESTED, milestone_id, {
            "decision_id": decision_id, "question": question
        })

    def council_decided(self, milestone_id: str, decision: dict) -> None:
        self.emit(EventType.COUNCIL_DECIDED, milestone_id, {
            "decision_id": decision.get("decision_id"),
            "recommendation": decision.get("recommendation"),
        })

    def awaiting_approval(self, milestone_id: str, cleanup_result: dict) -> None:
        self.emit(EventType.AWAITING_APPROVAL, milestone_id, cleanup_result)
        self.update_agent_state("awaiting_approval", milestone_id)

    def approved(self, milestone_id: str) -> None:
        self.emit(EventType.APPROVED, milestone_id)
        self.update_agent_state("complete", milestone_id)

    def rejected(self, milestone_id: str, feedback: str) -> None:
        self.emit(EventType.REJECTED, milestone_id, {"feedback": feedback})
        self.update_agent_state("running", milestone_id)

    def session_ended(self, milestone_id: str, reason: str) -> None:
        self.emit(EventType.SESSION_ENDED, milestone_id, {"reason": reason})
        self.update_agent_state("ended", milestone_id)


# ── Query helpers (used by dashboard backend) ─────────────────────────────────

def get_all_agents(db_path: Path = DB_PATH) -> list[dict]:
    conn = _get_db(db_path)
    rows = conn.execute(
        "SELECT * FROM agent_state ORDER BY last_updated DESC"
    ).fetchall()
    cols = [d[0] for d in conn.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]


def get_agent_events(session_id: str, db_path: Path = DB_PATH) -> list[dict]:
    conn = _get_db(db_path)
    rows = conn.execute(
        "SELECT * FROM events WHERE session_id = ? ORDER BY created_at ASC",
        (session_id,),
    ).fetchall()
    cols = [d[0] for d in conn.description]
    conn.close()
    return [dict(zip(cols, row)) for row in rows]
