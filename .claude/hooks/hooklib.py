"""Shared helpers for this repo's Claude Code hooks (see CONSTITUTION.md Article 4)."""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR.parent.parent / "tools"))

import governance_rules as rules  # noqa: E402

JOURNAL_FOLDER = "logs/sessions"
JOURNAL_TEMPLATE = "docs/templates/session-journal.md"


def state_path(project: Path, session_id: str) -> Path:
    return Path(project) / ".claude" / "state" / f"{session_id}.json"


def journal_path(project: Path, date: str, session_id: str) -> Path:
    return Path(project) / JOURNAL_FOLDER / f"{date}-{session_id[:8]}.md"


def load_state(project: Path, session_id: str) -> dict:
    """The session's start record, or today's date and unknown HEAD if missing."""
    try:
        return json.loads(state_path(project, session_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"date": datetime.date.today().isoformat(), "head": ""}


def git(project: Path, *args: str) -> str:
    """Output of a git command, or '' if git fails."""
    try:
        return subprocess.run(["git", *args], cwd=project, capture_output=True,
                              text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def run(handler) -> None:
    """Read the hook payload, call handler(payload, project), print its JSON answer.

    Any error is swallowed: a broken hook must never break a session.
    """
    try:
        payload = json.loads(sys.stdin.read())
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd())
        result = handler(payload, project)
        if result is not None:
            print(json.dumps(result))
    except Exception:  # noqa: BLE001 - hooks must fail open and silent
        pass
    sys.exit(0)
