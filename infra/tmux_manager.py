"""
tmux session lifecycle manager.
Each agent gets a dedicated tmux session named agent-{project_id}-{run_id}.
All operations are idempotent and safe to call from the orchestrator.
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Optional


SESSION_PREFIX = "agent"


def _session_name(project_id: str, run_id: str) -> str:
    return f"{SESSION_PREFIX}-{project_id}-{run_id}"


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


@dataclass
class SessionInfo:
    name: str
    project_id: str
    run_id: str
    created: str
    attached: bool


def create(
    project_id: str,
    run_id: str,
    work_dir: str,
    env: Optional[dict[str, str]] = None,
) -> str:
    """
    Create a new detached tmux session. Returns the session name.
    Raises if a session with this name already exists.
    """
    name = _session_name(project_id, run_id)
    if exists(project_id, run_id):
        raise RuntimeError(f"Session '{name}' already exists")

    cmd = ["tmux", "new-session", "-d", "-s", name, "-c", work_dir]
    _run(cmd)

    if env:
        for key, value in env.items():
            _run(["tmux", "setenv", "-t", name, key, value])

    return name


def send_command(project_id: str, run_id: str, command: str) -> None:
    """Send a shell command to the session's active pane."""
    name = _session_name(project_id, run_id)
    _run(["tmux", "send-keys", "-t", name, command, "Enter"])


def kill(project_id: str, run_id: str) -> None:
    """Kill the session if it exists. No-op if already gone."""
    if not exists(project_id, run_id):
        return
    name = _session_name(project_id, run_id)
    _run(["tmux", "kill-session", "-t", name])


def exists(project_id: str, run_id: str) -> bool:
    name = _session_name(project_id, run_id)
    result = _run(["tmux", "has-session", "-t", name], check=False)
    return result.returncode == 0


def list_sessions() -> list[SessionInfo]:
    """Return all agent-managed tmux sessions."""
    result = _run(
        ["tmux", "list-sessions", "-F", "#{session_name}\t#{session_created}\t#{session_attached}"],
        check=False,
    )
    if result.returncode != 0:
        return []

    sessions = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        sname, created, attached = parts
        if not sname.startswith(SESSION_PREFIX + "-"):
            continue
        # name format: agent-{project_id}-{run_id}
        # project_id may contain hyphens, run_id is always the last segment
        remainder = sname[len(SESSION_PREFIX) + 1:]
        *proj_parts, run_id = remainder.split("-")
        project_id = "-".join(proj_parts)
        sessions.append(SessionInfo(
            name=sname,
            project_id=project_id,
            run_id=run_id,
            created=created,
            attached=attached == "1",
        ))
    return sessions


def attach(project_id: str, run_id: str) -> None:
    """Attach the current terminal to the session (blocking). For local debugging only."""
    name = _session_name(project_id, run_id)
    subprocess.run(["tmux", "attach-session", "-t", name], check=True)


if __name__ == "__main__":
    import json
    sessions = list_sessions()
    print(json.dumps([s.__dict__ for s in sessions], indent=2))
