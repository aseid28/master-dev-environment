"""
Generates a per-run CLAUDE.md that is injected into each agent's working directory.
The file encodes the current milestone, acceptance criteria, cost cap, and
hard boundary rules — the agent reads this as its primary instruction set.
"""
from __future__ import annotations

from pathlib import Path

from agent_loop.project_schema import Milestone, Project


CLAUDE_MD_TEMPLATE = """\
# AGENT INSTRUCTIONS — READ THIS FIRST

You are an autonomous development agent. This file defines your current assignment.
Follow every rule here exactly. These rules override any defaults.

---

## Project: {project_name}

**Current Milestone: [{milestone_id}] {milestone_name}**

{milestone_description}

---

## Acceptance Criteria

You must satisfy ALL of the following before signaling milestone completion:

{acceptance_criteria}

---

## Hard Boundaries — NEVER VIOLATE

1. **Milestone scope is absolute.** You are building milestone `{milestone_id}` only.
   Do not plan, scaffold, stub, or reference work for any future milestone.
   Any file, function, or comment that belongs to a later milestone is out of scope.
   If you find yourself thinking about the next milestone, stop and refocus.

2. **Cost cap is hard.** Your total API spend for this session must not exceed
   **${cost_cap_usd:.2f} USD**. You will be stopped automatically at this limit,
   but you must also track your own spend and stop voluntarily when you approach it.
   When you estimate you have 20% budget remaining, begin wrapping up — don't start
   new features.

3. **Consume-only by default.** Unless `write_enabled` is explicitly set in the
   project config, you must not write to, modify, or delete any external data source.
   This includes: databases, APIs, email, Slack, webhooks, or any networked service.
   Read and fetch are always allowed. Write operations require explicit per-session approval.

4. **No outbound communication.** Do not send emails, Slack messages, webhooks,
   or any other notification without explicit approval. Dashboard alerts are handled
   by the orchestrator, not by you.

5. **Signal, don't act beyond scope.** When you believe you have completed the
   milestone, write the following sentinel to stdout and stop:
   ```
   MILESTONE_BELIEF: {milestone_id}
   ```
   The orchestrator will trigger the cleanup loop. Do not continue working after
   emitting this signal.

6. **Design decisions.** If you reach a significant design decision that you
   cannot resolve with high confidence, write a `council_request.json` in the
   project root with this structure and stop:
   ```json
   {{
     "decision_id": "short-slug",
     "question": "The specific question",
     "context": "Relevant code context and constraints",
     "options": ["Option A", "Option B", "Option C"]
   }}
   ```
   The Karpathy Council will resolve it and inject the answer into your next session.

---

## Context from Previous Milestones

{previous_context}

---

## Working Directory Layout

The project repo is your working directory. Commit frequently to preserve state.
The orchestrator reads your git history; comments in commits are valuable.
"""


def generate(
    project: Project,
    milestone_id: str,
    output_path: str | Path,
    previous_context: str = "",
) -> Path:
    """
    Write a CLAUDE.md for the given milestone into output_path.
    Returns the path to the written file.
    """
    milestone: Milestone = project.get_milestone(milestone_id)

    criteria_block = "\n".join(
        f"- [ ] {c}" for c in milestone.acceptance_criteria
    ) or "- [ ] (No explicit criteria — use your best judgment and document your decisions.)"

    prev_block = previous_context.strip() or "(No previous milestone context — this is the first milestone.)"

    content = CLAUDE_MD_TEMPLATE.format(
        project_name=project.project.name,
        milestone_id=milestone.id,
        milestone_name=milestone.name,
        milestone_description=milestone.description.strip(),
        acceptance_criteria=criteria_block,
        cost_cap_usd=project.project.cost_cap_usd,
        previous_context=prev_block,
    )

    output_path = Path(output_path)
    output_path.write_text(content)
    return output_path


if __name__ == "__main__":
    import sys
    import os

    # Quick CLI: python agent_claude_md.py <project.yaml> <milestone_id> <output_dir>
    if len(sys.argv) < 4:
        print("Usage: agent_claude_md.py <project.yaml> <milestone_id> <output_dir>")
        sys.exit(1)

    sys.path.insert(0, str(Path(__file__).parent.parent))
    proj = Project.load(sys.argv[1])
    out = generate(proj, sys.argv[2], Path(sys.argv[3]) / "CLAUDE.md")
    print(f"Wrote {out}")
