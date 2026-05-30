#!/usr/bin/env python3
"""
Claude Code PreToolUse hook — runs before every tool call.

Enforces consume-only mode by scanning Bash commands for write-side operations
and blocking them unless write_enabled is set for this session.

Exit codes:
  0 — allow the tool call
  2 — block the tool call (Claude Code will show the stdout message to the agent)
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


# Patterns that indicate a write/send operation in a Bash command.
# Conservative list — blocks on suspicion; agent can ask Andrew for write permission.
WRITE_PATTERNS = [
    # HTTP write methods
    r"\bcurl\b.*-X\s*(POST|PUT|DELETE|PATCH)",
    r"\bcurl\b.*--request\s*(POST|PUT|DELETE|PATCH)",
    r"\brequests\.(post|put|delete|patch)\b",
    r"\bhttpx\.(post|put|delete|patch)\b",
    r"\bfetch\(.+method.*POST|PUT|DELETE|PATCH",
    # Email / messaging
    r"\bsmtplib\b",
    r"\bsendmail\b",
    r"\bsendgrid\b",
    r"\bslack.*chat\.post",
    r"\btwilio\b",
    r"\bsend_message\b",
    r"\bsend_email\b",
    # Database writes
    r"\bINSERT\s+INTO\b",
    r"\bUPDATE\s+\w+\s+SET\b",
    r"\bDELETE\s+FROM\b",
    r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b",
    r"\bCREATE\s+TABLE\b",
    r"\bALTER\s+TABLE\b",
    # File system destructive ops on external mounts
    r"\brm\s+-rf?\b",
    # Git push / force ops
    r"\bgit\s+push\b",
    r"\bgit\s+reset\s+--hard\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in WRITE_PATTERNS]


def is_write_op(command: str) -> bool:
    return any(p.search(command) for p in COMPILED_PATTERNS)


def write_enabled() -> bool:
    session_dir = os.environ.get("AGENT_SESSION_DIR")
    if not session_dir:
        return True  # Not in a managed session — no restriction

    state_file = Path(session_dir) / "orchestrator_state.json"
    if not state_file.exists():
        return False

    try:
        state = json.loads(state_file.read_text())
        return bool(state.get("write_enabled", False))
    except (json.JSONDecodeError, OSError):
        return False


def main() -> None:
    session_dir = os.environ.get("AGENT_SESSION_DIR")
    if not session_dir:
        # Not a managed session — allow everything
        sys.exit(0)

    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    # Only inspect Bash tool calls
    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    if is_write_op(command) and not write_enabled():
        print(
            "BLOCKED: This command appears to perform a write, send, or delete operation.\n"
            "The current session is in CONSUME-ONLY mode.\n"
            "To enable write access, Andrew must grant it via the dashboard or by setting "
            "write_enabled: true in project.yaml before the next run.\n"
            f"Blocked command: {command[:200]}",
            file=sys.stdout,
        )
        # Log the block
        log_path = Path(session_dir) / "blocked_ops.log"
        with open(log_path, "a") as f:
            f.write(json.dumps({"tool": tool_name, "command": command}) + "\n")
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
