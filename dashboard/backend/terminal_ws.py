"""
WebSocket terminal proxy: browser ↔ tmux session.

Each agent's tmux session is exposed as a bidirectional WebSocket endpoint.
The browser connects with xterm.js; this module spawns a pty-attached
`tmux attach-session` process and pipes data in both directions.

Resize events from xterm.js arrive as JSON: {"type": "resize", "cols": N, "rows": N}
All other binary/text frames are forwarded as-is to the pty stdin.
"""
from __future__ import annotations

import asyncio
import fcntl
import json
import os
import pty
import signal
import struct
import sys
import termios
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from infra.tmux_manager import _session_name, exists as session_exists


async def terminal_ws_handler(websocket: WebSocket, project_id: str, run_id: str) -> None:
    """
    FastAPI WebSocket handler. Mount at: /agents/{project_id}/{run_id}/terminal
    """
    await websocket.accept()

    session = _session_name(project_id, run_id)

    if not session_exists(project_id, run_id):
        await websocket.send_text(f"\r\n[error] Session '{session}' not found.\r\n")
        await websocket.close(code=1008)
        return

    # Spawn tmux attach in a pty
    master_fd, slave_fd = pty.openpty()
    proc = await asyncio.create_subprocess_exec(
        "tmux", "attach-session", "-t", session, "-r",  # -r = read-only
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid,
    )
    os.close(slave_fd)

    # Set initial pty size (default 220x50 — xterm.js will send a resize shortly)
    _resize_pty(master_fd, cols=220, rows=50)

    try:
        await asyncio.gather(
            _pty_to_ws(master_fd, websocket),
            _ws_to_pty(master_fd, websocket),
        )
    except (WebSocketDisconnect, asyncio.CancelledError, OSError):
        pass
    finally:
        try:
            os.kill(proc.pid, signal.SIGHUP)
        except ProcessLookupError:
            pass
        try:
            os.close(master_fd)
        except OSError:
            pass


async def _pty_to_ws(master_fd: int, websocket: WebSocket) -> None:
    """Read from pty stdout → send to WebSocket."""
    loop = asyncio.get_event_loop()
    while True:
        try:
            data = await loop.run_in_executor(None, _read_pty, master_fd)
            if not data:
                break
            await websocket.send_bytes(data)
        except (OSError, WebSocketDisconnect):
            break


async def _ws_to_pty(master_fd: int, websocket: WebSocket) -> None:
    """Read from WebSocket → write to pty stdin (or handle resize)."""
    while True:
        try:
            message = await websocket.receive()
        except WebSocketDisconnect:
            break

        if "bytes" in message:
            data = message["bytes"]
            os.write(master_fd, data)
        elif "text" in message:
            text = message["text"]
            try:
                event = json.loads(text)
                if event.get("type") == "resize":
                    _resize_pty(master_fd, cols=event["cols"], rows=event["rows"])
                else:
                    os.write(master_fd, text.encode())
            except (json.JSONDecodeError, KeyError):
                os.write(master_fd, text.encode())


def _read_pty(master_fd: int, size: int = 4096) -> bytes:
    try:
        return os.read(master_fd, size)
    except OSError:
        return b""


def _resize_pty(master_fd: int, cols: int, rows: int) -> None:
    try:
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
    except OSError:
        pass
