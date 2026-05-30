"""
Main orchestrator: reads project.yaml, manages the agent lifecycle in tmux,
monitors session state, and routes events (cost caps, milestone beliefs,
council requests, dashboard notifications).

Usage:
  python orchestrator.py --project projects/example-triage-tool/project.yaml
  python orchestrator.py --project ... --milestone m2  # resume at specific milestone
  python orchestrator.py --project ... --dry-run       # show plan without executing
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

# Ensure repo root is on path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent_loop.cost_guard import CostGuard
from agent_loop.project_schema import Project
from infra import tmux_manager
from infra.agent_claude_md import generate as generate_claude_md


# ── Constants ───────────────────────────────────────────────────────────────

SESSIONS_DIR = REPO_ROOT / ".sessions"
POLL_INTERVAL_SECS = 5
MILESTONE_BELIEF_SENTINEL = "MILESTONE_BELIEF:"
COUNCIL_REQUEST_FILE = "council_request.json"


# ── Session state ────────────────────────────────────────────────────────────

class AgentSession:
    def __init__(self, project: Project, milestone_id: str, run_id: str):
        self.project = project
        self.milestone_id = milestone_id
        self.run_id = run_id
        self.session_dir = SESSIONS_DIR / project.project.id / run_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

    @property
    def project_id(self) -> str:
        return self.project.project.id

    @property
    def state_path(self) -> Path:
        return self.session_dir / "cost_state.json"

    @property
    def session_log(self) -> Path:
        return self.session_dir / "session.log"

    def env(self) -> dict[str, str]:
        """Environment variables injected into the tmux session."""
        return {
            "AGENT_SESSION_DIR": str(self.session_dir),
            "AGENT_PROJECT_ID": self.project_id,
            "AGENT_RUN_ID": self.run_id,
            "AGENT_MILESTONE_ID": self.milestone_id,
            "AGENT_COST_CAP_USD": str(self.project.project.cost_cap_usd),
            "CLAUDE_CODE_HOOKS": str(REPO_ROOT / "hooks"),
        }

    def write_state(self, key: str, value: object) -> None:
        state_file = self.session_dir / "orchestrator_state.json"
        state = json.loads(state_file.read_text()) if state_file.exists() else {}
        state[key] = value
        state_file.write_text(json.dumps(state, indent=2))

    def read_state(self) -> dict:
        state_file = self.session_dir / "orchestrator_state.json"
        return json.loads(state_file.read_text()) if state_file.exists() else {}


# ── Core orchestration ───────────────────────────────────────────────────────

def launch(project: Project, milestone_id: str, work_dir: str, dry_run: bool = False) -> AgentSession:
    run_id = uuid.uuid4().hex[:8]
    session = AgentSession(project, milestone_id, run_id)
    milestone = project.get_milestone(milestone_id)

    print(f"[orchestrator] Project : {project.project.name}")
    print(f"[orchestrator] Milestone: [{milestone.id}] {milestone.name}")
    print(f"[orchestrator] Cost cap : ${project.project.cost_cap_usd:.2f}")
    print(f"[orchestrator] Run ID  : {run_id}")
    print(f"[orchestrator] Session : {tmux_manager._session_name(project.project.id, run_id)}")
    print(f"[orchestrator] State   : {session.session_dir}")

    if dry_run:
        print("[orchestrator] DRY RUN — no session created.")
        return session

    # Write per-run CLAUDE.md into the work directory
    claude_md_path = generate_claude_md(
        project=project,
        milestone_id=milestone_id,
        output_path=Path(work_dir) / "CLAUDE.md",
    )
    print(f"[orchestrator] CLAUDE.md: {claude_md_path}")

    # Initialize cost guard
    CostGuard.init(
        state_path=session.state_path,
        session_id=run_id,
        project_id=project.project.id,
        model=project.project.model,
        cost_cap_usd=project.project.cost_cap_usd,
    )

    # Register hooks in the session's env
    env = session.env()

    # Create tmux session
    tmux_manager.create(project.project.id, run_id, work_dir, env=env)

    # Build the claude command
    # --print runs headless (non-interactive); remove it for interactive sessions
    claude_cmd = (
        f"claude --model {project.project.model} "
        f"--dangerously-skip-permissions "
        f"'You are an autonomous development agent. Read CLAUDE.md in your current directory for your assignment. Work through it completely. When you believe the milestone is complete, output: MILESTONE_BELIEF: {milestone_id}' "
        f"2>&1 | tee {session.session_log}"
    )
    tmux_manager.send_command(project.project.id, run_id, claude_cmd)

    session.write_state("status", "running")
    session.write_state("milestone_id", milestone_id)
    session.write_state("launched_at", time.time())

    print(f"[orchestrator] Agent launched. Monitoring...")
    return session


def monitor(session: AgentSession) -> str:
    """
    Poll the session state until a terminal event occurs.
    Returns one of: "hard_cap", "soft_cap", "milestone_belief", "council_request", "session_ended"
    """
    guard = CostGuard(session.state_path)

    while True:
        time.sleep(POLL_INTERVAL_SECS)

        # Check hard cap sentinel
        if (session.session_dir / "HARD_CAP_REACHED").exists():
            print(f"\n[orchestrator] HARD CAP reached. Triggering cleanup.")
            session.write_state("status", "cleanup_hard_cap")
            return "hard_cap"

        # Check soft cap
        if guard.is_soft_capped() and not (session.session_dir / "SOFT_CAP_WARNED").exists():
            print(f"\n[orchestrator] Soft cap warning. Agent continuing...")

        # Check session log for MILESTONE_BELIEF sentinel
        if session.session_log.exists():
            log = session.session_log.read_text()
            if MILESTONE_BELIEF_SENTINEL in log:
                print(f"\n[orchestrator] MILESTONE_BELIEF signal detected.")
                session.write_state("status", "cleanup_milestone")
                return "milestone_belief"

        # Check for council request
        council_file = Path(session.read_state().get("work_dir", "")) / COUNCIL_REQUEST_FILE
        if council_file.exists():
            print(f"\n[orchestrator] Council request found: {council_file}")
            session.write_state("status", "council_pending")
            return "council_request"

        # Check if tmux session is still alive
        if not tmux_manager.exists(session.project_id, session.run_id):
            print(f"\n[orchestrator] Session ended (tmux exited).")
            session.write_state("status", "session_ended")
            return "session_ended"

        # Print cost summary
        print(f"\r{guard.summary()}", end="", flush=True)


def run(project_path: str, milestone_id: str | None = None, work_dir: str | None = None, dry_run: bool = False) -> None:
    project = Project.load(project_path)
    target_milestone = milestone_id or project.milestones[0].id
    target_work_dir = work_dir or os.getcwd()

    session = launch(project, target_milestone, target_work_dir, dry_run=dry_run)
    if dry_run:
        return

    event = monitor(session)
    print(f"\n[orchestrator] Event: {event}")

    # Route to appropriate handler
    if event in ("hard_cap", "milestone_belief"):
        print("[orchestrator] Cleanup loop would run here (M3 — not yet implemented).")
        print("[orchestrator] Notifier would alert dashboard (M3 — not yet implemented).")
    elif event == "council_request":
        print("[orchestrator] Karpathy Council would convene here (M3 — not yet implemented).")
    elif event == "session_ended":
        print("[orchestrator] Session ended unexpectedly. Check session log:")
        print(f"  {session.session_log}")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous agent orchestrator")
    parser.add_argument("--project", required=True, help="Path to project.yaml")
    parser.add_argument("--milestone", help="Milestone ID to run (default: first)")
    parser.add_argument("--work-dir", help="Working directory for the agent (default: cwd)")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    args = parser.parse_args()

    run(
        project_path=args.project,
        milestone_id=args.milestone,
        work_dir=args.work_dir,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
