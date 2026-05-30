"""
Agent Dashboard — FastAPI backend.

Endpoints:
  GET  /agents                          — list all agent sessions with state
  GET  /agents/{session_id}             — single agent detail
  GET  /agents/{session_id}/events      — event log
  POST /agents/{session_id}/approve     — approve milestone
  POST /agents/{session_id}/reject      — reject milestone with feedback
  POST /agents/{session_id}/grant-write — enable write mode for session
  WS   /agents/{session_id}/ws          — real-time event stream
  WS   /agents/{project_id}/{run_id}/terminal — xterm.js ↔ tmux proxy
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent_loop.notifier import get_all_agents, get_agent_events, DB_PATH
from agent_loop.milestone_engine import MilestoneEngine
from dashboard.backend.terminal_ws import terminal_ws_handler

SESSIONS_DIR = Path(__file__).parent.parent.parent / ".sessions"
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

app = FastAPI(title="Agent Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections: session_id → list of websockets
_ws_connections: dict[str, list[WebSocket]] = {}


# ── Models ────────────────────────────────────────────────────────────────────

class RejectRequest(BaseModel):
    feedback: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_session_dir(session_id: str) -> Path:
    # Sessions are stored under .sessions/{project_id}/{run_id}
    # session_id format from agent_state table: stored as run_id
    for project_dir in SESSIONS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        candidate = project_dir / session_id
        if candidate.exists():
            return candidate
    raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")


def _read_cost_state(session_dir: Path) -> Optional[dict]:
    cost_path = session_dir / "cost_state.json"
    if cost_path.exists():
        return json.loads(cost_path.read_text())
    return None


def _read_milestone_state(session_dir: Path) -> Optional[dict]:
    ms_path = session_dir / "milestone_state.json"
    if ms_path.exists():
        return json.loads(ms_path.read_text())
    return None


async def _broadcast(session_id: str, event: dict) -> None:
    dead = []
    for ws in _ws_connections.get(session_id, []):
        try:
            await ws.send_json(event)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_connections[session_id].remove(ws)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/agents")
def list_agents() -> list[dict]:
    agents = get_all_agents(DB_PATH)
    for agent in agents:
        try:
            session_dir = _get_session_dir(agent["session_id"])
            cost = _read_cost_state(session_dir)
            if cost:
                agent["cost_usd"] = cost.get("total_cost_usd", 0)
                agent["pct_used"] = cost.get("pct_used", 0)
                agent["turn_count"] = cost.get("turn_count", 0)
        except HTTPException:
            pass
    return agents


@app.get("/agents/{session_id}")
def get_agent(session_id: str) -> dict:
    agents = get_all_agents(DB_PATH)
    match = next((a for a in agents if a["session_id"] == session_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Agent not found")

    session_dir = _get_session_dir(session_id)
    match["cost_state"] = _read_cost_state(session_dir)
    match["milestone_state"] = _read_milestone_state(session_dir)
    return match


@app.get("/agents/{session_id}/events")
def get_events(session_id: str) -> list[dict]:
    return get_agent_events(session_id, DB_PATH)


@app.post("/agents/{session_id}/approve")
async def approve_milestone(session_id: str) -> dict:
    session_dir = _get_session_dir(session_id)
    ms_state = _read_milestone_state(session_dir)
    if not ms_state:
        raise HTTPException(status_code=400, detail="No milestone state found")

    engine = MilestoneEngine(session_dir, ms_state["project_id"], ms_state["milestone_id"])
    engine.approve()

    await _broadcast(session_id, {"type": "approved", "milestone_id": ms_state["milestone_id"]})
    return {"status": "approved", "milestone_id": ms_state["milestone_id"]}


@app.post("/agents/{session_id}/reject")
async def reject_milestone(session_id: str, body: RejectRequest) -> dict:
    session_dir = _get_session_dir(session_id)
    ms_state = _read_milestone_state(session_dir)
    if not ms_state:
        raise HTTPException(status_code=400, detail="No milestone state found")

    engine = MilestoneEngine(session_dir, ms_state["project_id"], ms_state["milestone_id"])
    engine.reject(body.feedback)

    await _broadcast(session_id, {
        "type": "rejected",
        "milestone_id": ms_state["milestone_id"],
        "feedback": body.feedback,
    })
    return {"status": "rejected", "milestone_id": ms_state["milestone_id"]}


@app.post("/agents/{session_id}/grant-write")
async def grant_write(session_id: str) -> dict:
    session_dir = _get_session_dir(session_id)
    state_file = session_dir / "orchestrator_state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    state["write_enabled"] = True
    state_file.write_text(json.dumps(state, indent=2))
    await _broadcast(session_id, {"type": "write_granted"})
    return {"status": "write_enabled", "session_id": session_id}


@app.post("/agents/{session_id}/revoke-write")
async def revoke_write(session_id: str) -> dict:
    session_dir = _get_session_dir(session_id)
    state_file = session_dir / "orchestrator_state.json"
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
    state["write_enabled"] = False
    state_file.write_text(json.dumps(state, indent=2))
    await _broadcast(session_id, {"type": "write_revoked"})
    return {"status": "write_revoked", "session_id": session_id}


@app.websocket("/agents/{session_id}/ws")
async def agent_websocket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    if session_id not in _ws_connections:
        _ws_connections[session_id] = []
    _ws_connections[session_id].append(websocket)

    try:
        # Send current state immediately on connect
        agents = get_all_agents(DB_PATH)
        match = next((a for a in agents if a["session_id"] == session_id), None)
        if match:
            await websocket.send_json({"type": "state", "data": match})

        # Poll for new events and push them
        last_event_id = 0
        while True:
            await asyncio.sleep(2)
            events = get_agent_events(session_id, DB_PATH)
            new_events = [e for e in events if e["id"] > last_event_id]
            for event in new_events:
                await websocket.send_json({"type": "event", "data": event})
                last_event_id = max(last_event_id, event["id"])
    except WebSocketDisconnect:
        _ws_connections[session_id].remove(websocket)


@app.websocket("/agents/{project_id}/{run_id}/terminal")
async def agent_terminal(websocket: WebSocket, project_id: str, run_id: str) -> None:
    await terminal_ws_handler(websocket, project_id, run_id)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# Serve React frontend — must be last (catch-all)
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")
