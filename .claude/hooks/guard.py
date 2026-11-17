"""PreToolUse hook: protect raw data (Article 2) and the constitution (Article 6)."""
import os
import re
import shlex
from pathlib import Path

import hooklib

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
CSV_TOKEN = re.compile(r"(?:^|/)data/[^/\s]+\.csv$")
REDIRECT_TO_CSV = re.compile(r">>?\s*['\"]?\S*(?:^|/|\s|['\"])?data/[^/\s'\"]+\.csv")
SEGMENT_SPLIT = re.compile(r"&&|\|\||[;|\n]")

RAW_DATA_REASON = ("Raw data files in data/ are read-only (CONSTITUTION.md Article 2). "
                   "Do not edit, rename or delete them; ask the owner if a raw file must change.")
CONSTITUTION_REASON = ("Only the owner may amend CONSTITUTION.md (Article 6). "
                       "Approve this edit only if you asked for this amendment.")


def _answer(kind: str, reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": kind,
                                   "permissionDecisionReason": reason}}


def _relative(project: Path, file_path: str) -> str | None:
    """file_path as a repo-relative POSIX path, or None if outside the repo."""
    path = Path(file_path)
    if not path.is_absolute():
        path = Path(project) / path
    normal = Path(os.path.normpath(path))
    try:
        return normal.relative_to(os.path.normpath(project)).as_posix()
    except ValueError:
        return None


def _check_edit(project: Path, tool_input: dict) -> dict | None:
    rel = _relative(project, tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    if rel is None:
        return None
    parts = rel.split("/")
    if len(parts) == 2 and parts[0] == "data" and parts[1].lower().endswith(".csv"):
        return _answer("deny", RAW_DATA_REASON)
    if rel == "CONSTITUTION.md":
        return _answer("ask", CONSTITUTION_REASON)
    return None


def _segment_writes_csv(segment: str) -> bool:
    if REDIRECT_TO_CSV.search(segment):
        return True
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    if not tokens:
        return False
    csv_args = [t for t in tokens[1:] if CSV_TOKEN.search(t)]
    if not csv_args:
        return False
    command = os.path.basename(tokens[0])
    if command in {"rm", "mv", "truncate", "tee", "dd", "shred"}:
        return True
    if command == "git" and len(tokens) > 1 and tokens[1] in {"rm", "mv"}:
        return True
    if command == "sed" and any(t == "--in-place" or re.match(r"^-[a-zA-Z]*i", t) for t in tokens[1:]):
        return True
    if command in {"cp", "install", "rsync"} and CSV_TOKEN.search(tokens[-1]):
        return True
    return False


def _check_bash(command: str) -> dict | None:
    if any(_segment_writes_csv(seg) for seg in SEGMENT_SPLIT.split(command)):
        return _answer("deny", RAW_DATA_REASON)
    return None


def decide(payload: dict, project: Path) -> dict | None:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if tool in EDIT_TOOLS:
        return _check_edit(project, tool_input)
    if tool == "Bash":
        return _check_bash(tool_input.get("command", ""))
    return None


if __name__ == "__main__":
    hooklib.run(decide)
