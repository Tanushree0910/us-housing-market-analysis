"""Shared helpers for this repo's Claude Code hooks (see CONSTITUTION.md Article 4)."""
import datetime
import functools
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


def save_state(project: Path, session_id: str, state: dict) -> None:
    path = state_path(project, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")


def git(project: Path, *args: str) -> str:
    """Output of a git command, or '' if git fails."""
    try:
        return subprocess.run(["git", *args], cwd=project, capture_output=True,
                              text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def git_status(project: Path) -> list[str]:
    """Every changed or new file, one 'XY path' line each."""
    return _lines(git(project, "status", "--porcelain", "--untracked-files=all"))


def _lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


WORKTREES_FOLDER = ".worktrees"
MAIN_BRANCHES = {"main", "master"}


def main_checkout(project: Path) -> Path:
    """The repo's main folder, even when called from inside one of its worktrees."""
    return _main_checkout(str(Path(project).resolve(strict=False)))


@functools.lru_cache(maxsize=32)
def _main_checkout(project_str: str) -> Path:
    project = Path(project_str)
    common = git(project, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    if not common:
        return project
    return Path(common).resolve(strict=False).parent


def worktrees(main: Path) -> dict[str, dict]:
    """Every worktree except the main folder: path -> {"branch", "head", "status"}."""
    found = {}
    current = {}
    for line in git(main, "worktree", "list", "--porcelain").splitlines() + [""]:
        if line.startswith("worktree "):
            current = {"path": line[len("worktree "):]}
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):]
        elif line.startswith("branch "):
            current["branch"] = line[len("branch refs/heads/"):]
        elif not line and current.get("path"):
            path = Path(current["path"]).resolve(strict=False)
            if path != Path(main).resolve(strict=False):
                found[str(path)] = {"branch": current.get("branch", ""), "head": current.get("head", ""),
                                    "status": git_status(path)}
            current = {}
    return found


def worktree_of(project: Path, path: Path) -> Path | None:
    """The .worktrees/<name> folder that contains path, or None."""
    main = main_checkout(project)
    try:
        rel = Path(path).resolve(strict=False).relative_to(main)
    except ValueError:
        return None
    if len(rel.parts) >= 2 and rel.parts[0] == WORKTREES_FOLDER:
        return main / rel.parts[0] / rel.parts[1]
    return None


def mark_touched(project: Path, session_id: str, folders: set[Path]) -> None:
    """Remember which worktrees this session worked in, so the end check judges only those."""
    if not session_id or not folders:
        return
    state = load_state(project, session_id)
    touched = set(state.get("touched", []))
    new = {str(Path(f).resolve(strict=False)) for f in folders} - touched
    if new:
        state["touched"] = sorted(touched | new)
        save_state(project, session_id, state)


def repo_relative(project: Path, path: Path) -> Path | None:
    """path relative to the repo, as if it were in the main folder.

    A file in .worktrees/<name>/ is treated like the same file in the main folder,
    so rules about data/ or CONSTITUTION.md apply inside worktrees too.
    Returns None for paths outside the repo.
    """
    try:
        rel = Path(path).resolve(strict=False).relative_to(main_checkout(project))
    except ValueError:
        return None
    if len(rel.parts) >= 2 and rel.parts[0] == WORKTREES_FOLDER:
        return Path(*rel.parts[2:])
    return rel


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
