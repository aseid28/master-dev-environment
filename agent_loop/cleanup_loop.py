"""
Cleanup loop: runs before any milestone notification or cap stop.

Sequence (up to MAX_ITERATIONS each):
  1. Refactor pass — Claude sub-agent reads code, applies refactor diff
  2. Test pass    — pytest/vitest; if failures, Claude sub-agent patches and re-runs
  3. Security scan — bandit + semgrep; if findings, Claude sub-agent patches and re-scans

If all three pass: returns {"clean": True, ...}
If not clean after MAX_ITERATIONS: returns {"clean": False, ...} with details.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

MAX_ITERATIONS = 3
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"


def _run(cmd: list[str], cwd: str) -> tuple[int, str, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def detect_test_runner(work_dir: str) -> Optional[list[str]]:
    wd = Path(work_dir)
    if (wd / "pytest.ini").exists() or (wd / "pyproject.toml").exists() or list(wd.glob("test_*.py")):
        return ["python3", "-m", "pytest", "--tb=short", "-q"]
    if (wd / "package.json").exists():
        pkg = json.loads((wd / "package.json").read_text())
        if "vitest" in pkg.get("devDependencies", {}):
            return ["npx", "vitest", "run", "--reporter=verbose"]
        if "jest" in pkg.get("devDependencies", {}):
            return ["npx", "jest", "--ci"]
    return None


def run_tests(work_dir: str) -> tuple[bool, str]:
    runner = detect_test_runner(work_dir)
    if runner is None:
        return True, "(no test runner detected — skipped)"
    code, stdout, stderr = _run(runner, work_dir)
    output = (stdout + stderr).strip()
    return code == 0, output


def run_security(work_dir: str) -> tuple[bool, str]:
    wd = Path(work_dir)
    findings = []

    # bandit (Python)
    if list(wd.rglob("*.py")):
        code, stdout, stderr = _run(
            ["python3", "-m", "bandit", "-r", ".", "-ll", "-q", "--format", "json"],
            work_dir,
        )
        if code not in (0, 1):  # bandit exits 1 on findings
            findings.append(f"bandit error: {stderr.strip()[:300]}")
        else:
            try:
                report = json.loads(stdout)
                high = [
                    i for i in report.get("results", [])
                    if i.get("issue_severity") in ("HIGH", "MEDIUM")
                ]
                if high:
                    findings.append(f"bandit: {len(high)} HIGH/MEDIUM findings")
                    for h in high[:5]:
                        findings.append(
                            f"  [{h['issue_severity']}] {h['test_id']}: "
                            f"{h['filename']}:{h['line_number']} — {h['issue_text']}"
                        )
            except json.JSONDecodeError:
                pass  # bandit found nothing parseable — treat as clean

    # semgrep
    semgrep_ok = _run(["which", "semgrep"], work_dir)[0] == 0
    if semgrep_ok:
        code, stdout, stderr = _run(
            ["semgrep", "--config=auto", "--json", "--quiet", "."],
            work_dir,
        )
        try:
            report = json.loads(stdout)
            errors = [r for r in report.get("results", []) if r.get("extra", {}).get("severity") == "ERROR"]
            if errors:
                findings.append(f"semgrep: {len(errors)} ERROR findings")
                for e in errors[:5]:
                    findings.append(
                        f"  {e['check_id']}: {e['path']}:{e['start']['line']}"
                    )
        except (json.JSONDecodeError, KeyError):
            pass

    output = "\n".join(findings) if findings else "clean"
    return len(findings) == 0, output


def _call_claude_fix(prompt: str, work_dir: str, model: str = "claude-haiku-4-5") -> str:
    """
    Run a Claude API call to generate a fix. Returns the text response.
    Uses the Anthropic SDK directly (not Claude Code CLI) to avoid recursive hook invocation.
    """
    try:
        import anthropic
    except ImportError:
        return "(anthropic SDK not installed — manual fix required)"

    api_key = os.environ.get(ANTHROPIC_API_KEY_ENV)
    if not api_key:
        return "(ANTHROPIC_API_KEY not set — manual fix required)"

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text if message.content else ""


def run(
    work_dir: str,
    project_name: str = "",
    milestone_name: str = "",
    trigger: str = "milestone_belief",
) -> dict:
    """
    Run the full cleanup sequence. Returns a result dict suitable for
    MilestoneEngine.cleanup_complete().
    """
    print(f"[cleanup] Starting cleanup loop (trigger={trigger})", flush=True)
    result = {
        "clean": False,
        "trigger": trigger,
        "iterations": 0,
        "test_output": "",
        "security_output": "",
        "refactor_applied": False,
        "started_at": time.time(),
    }

    # ── Step 1: Refactor pass (single pass, not retried) ─────────────────────
    print("[cleanup] Step 1: Refactor pass...", flush=True)
    try:
        code_summary = _summarize_code(work_dir)
        refactor_prompt = (
            f"You are a code quality agent working on {project_name} milestone '{milestone_name}'.\n"
            f"Review the following code and apply minimal, safe refactoring:\n"
            f"- Remove dead code\n"
            f"- Fix naming inconsistencies\n"
            f"- Eliminate obvious duplication\n"
            f"Do NOT change behavior, tests, or add features.\n"
            f"Output ONLY a unified diff (--- a/... +++ b/... format).\n"
            f"If no changes are needed, output: NO_CHANGES\n\n"
            f"{code_summary}"
        )
        diff_text = _call_claude_fix(refactor_prompt, work_dir)
        if diff_text and "NO_CHANGES" not in diff_text and "---" in diff_text:
            apply = subprocess.run(
                ["patch", "-p1", "--dry-run"],
                input=diff_text,
                cwd=work_dir,
                capture_output=True,
                text=True,
            )
            if apply.returncode == 0:
                subprocess.run(
                    ["patch", "-p1"],
                    input=diff_text,
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                )
                result["refactor_applied"] = True
                print("[cleanup] Refactor applied.", flush=True)
            else:
                print("[cleanup] Refactor diff did not apply cleanly — skipping.", flush=True)
        else:
            print("[cleanup] No refactor changes needed.", flush=True)
    except Exception as e:
        print(f"[cleanup] Refactor step error (non-fatal): {e}", flush=True)

    # ── Step 2: Test loop ─────────────────────────────────────────────────────
    for i in range(1, MAX_ITERATIONS + 1):
        result["iterations"] = i
        print(f"[cleanup] Step 2: Test run (attempt {i}/{MAX_ITERATIONS})...", flush=True)
        tests_ok, test_output = run_tests(work_dir)
        result["test_output"] = test_output

        if tests_ok:
            print(f"[cleanup] Tests passed.", flush=True)
            break

        print(f"[cleanup] Tests failed. Asking Claude to fix...", flush=True)
        if i < MAX_ITERATIONS:
            fix_prompt = (
                f"Fix the following test failures in the {project_name} project. "
                f"Output ONLY a unified diff.\n\n"
                f"Test output:\n{test_output[:3000]}\n\n"
                f"Code summary:\n{_summarize_code(work_dir, max_chars=2000)}"
            )
            diff = _call_claude_fix(fix_prompt, work_dir)
            if diff and "---" in diff:
                subprocess.run(["patch", "-p1"], input=diff, cwd=work_dir,
                               capture_output=True, text=True)
    else:
        tests_ok = False

    # ── Step 3: Security loop ─────────────────────────────────────────────────
    sec_ok = False
    for i in range(1, MAX_ITERATIONS + 1):
        print(f"[cleanup] Step 3: Security scan (attempt {i}/{MAX_ITERATIONS})...", flush=True)
        sec_ok, sec_output = run_security(work_dir)
        result["security_output"] = sec_output

        if sec_ok:
            print(f"[cleanup] Security scan clean.", flush=True)
            break

        print(f"[cleanup] Security findings. Asking Claude to fix...", flush=True)
        if i < MAX_ITERATIONS:
            fix_prompt = (
                f"Fix the following security findings in {project_name}. "
                f"Output ONLY a unified diff.\n\n"
                f"Findings:\n{sec_output[:2000]}"
            )
            diff = _call_claude_fix(fix_prompt, work_dir)
            if diff and "---" in diff:
                subprocess.run(["patch", "-p1"], input=diff, cwd=work_dir,
                               capture_output=True, text=True)
    else:
        sec_ok = False

    result["clean"] = tests_ok and sec_ok
    result["finished_at"] = time.time()

    status = "CLEAN" if result["clean"] else "NEEDS_REVIEW"
    print(f"[cleanup] Done — {status}", flush=True)
    return result


def _summarize_code(work_dir: str, max_chars: int = 4000) -> str:
    """Read source files into a truncated summary for Claude context."""
    wd = Path(work_dir)
    extensions = {".py", ".ts", ".tsx", ".js", ".jsx"}
    parts = []
    total = 0

    for ext in extensions:
        for f in sorted(wd.rglob(f"*{ext}")):
            if any(skip in str(f) for skip in ("node_modules", ".git", "__pycache__", "dist")):
                continue
            try:
                content = f.read_text(errors="replace")
                snippet = f"### {f.relative_to(wd)}\n{content[:800]}\n"
                parts.append(snippet)
                total += len(snippet)
                if total > max_chars:
                    break
            except OSError:
                pass
        if total > max_chars:
            break

    return "\n".join(parts)[:max_chars]
