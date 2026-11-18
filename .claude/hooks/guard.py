"""PreToolUse hook: protect raw data (Article 2) and the constitution (Article 6).

The same rules apply in the main folder and in every worktree under .worktrees/.
"""
import os
import re
from pathlib import Path

import hooklib
import shellparse

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
FIND_DESTRUCTIVE_EXEC = {"rm", "mv", "shred", "truncate", "unlink"}
DELETE_OR_RENAME = {"rm", "mv", "truncate", "tee", "dd", "shred", "unlink"}
COPY_ONTO_LAST = {"cp", "install", "rsync", "ln"}

RAW_DATA_REASON = ("Raw data files in data/ are read-only (CONSTITUTION.md Article 2). "
                   "Do not edit, rename or delete them; ask the owner if a raw file must change.")
CONSTITUTION_REASON = ("Only the owner may amend CONSTITUTION.md (Article 6). "
                       "Approve this edit only if you asked for this amendment.")


def _answer(kind: str, reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": kind,
                                   "permissionDecisionReason": reason}}


def _relative(project: Path, path_text: str, cwd: Path | None = None) -> Path | None:
    """path_text as a repo-relative path (worktree prefix removed), or None if outside the repo."""
    if not path_text:
        return None
    return hooklib.repo_relative(project, shellparse.absolute(project, path_text, cwd))


def is_raw_data(project: Path, path_text: str, cwd: Path | None = None) -> bool:
    """True when path_text names a raw file: exactly data/<name>.csv (any letter case)."""
    rel = _relative(project, path_text, cwd)
    return (rel is not None and len(rel.parts) == 2 and rel.parts[0] == "data"
            and rel.parts[1].lower().endswith(".csv"))


def _contains_raw_data(project: Path, path_text: str, cwd: Path | None = None) -> bool:
    """True when a search starting at path_text would reach raw files (data/, the repo, or above)."""
    rel = _relative(project, path_text, cwd)
    if rel is not None:
        return rel.parts in {(), ("data",), (hooklib.WORKTREES_FOLDER,)} or is_raw_data(project, path_text, cwd)
    try:
        return hooklib.main_checkout(project).is_relative_to(shellparse.absolute(project, path_text, cwd))
    except (ValueError, OSError):
        return False


def _check_edit(project: Path, tool_input: dict) -> dict | None:
    path_text = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if is_raw_data(project, path_text):
        return _answer("deny", RAW_DATA_REASON)
    rel = _relative(project, path_text)
    if rel is not None and rel.as_posix() == "CONSTITUTION.md":
        return _answer("ask", CONSTITUTION_REASON)
    return None


def _writes_raw(project: Path, segment: list[str], words: list[str], cwd: Path | None) -> bool:
    if any(is_raw_data(project, target, cwd) for target in shellparse.redirect_targets(segment)):
        return True
    if not words:
        return False
    command, args = os.path.basename(words[0]), words[1:]

    if command == "git":
        while args and args[0].startswith("-"):
            if args[0] == "-C" and len(args) > 1:
                cwd = shellparse.absolute(project, args[1], cwd)
            args = args[2:] if args[0] in shellparse.GIT_VALUE_OPTIONS else args[1:]

    def raw(text: str) -> bool:
        return is_raw_data(project, text, cwd)

    for i, arg in enumerate(args):
        option, _, value = arg.partition("=")
        if value and option in {"of", "--output", "--output-document"} and raw(value):
            return True
        nxt = args[i + 1] if i + 1 < len(args) else ""
        if raw(nxt) and ((command == "curl" and arg in {"-o", "--output"})
                         or (command == "wget" and arg in {"-O", "--output-document"})):
            return True
        if ((command == "curl" and arg.startswith("-o")) or (command == "wget" and arg.startswith("-O"))) \
                and len(arg) > 2 and raw(arg[2:]):
            return True

    if command == "find":
        starts = []
        for arg in args:
            if arg.startswith("-") or arg in {"!", "("}:
                break
            starts.append(arg)
        destructive = "-delete" in args or any(
            arg in {"-exec", "-execdir", "-ok", "-okdir"} and i + 1 < len(args)
            and os.path.basename(args[i + 1]) in FIND_DESTRUCTIVE_EXEC
            for i, arg in enumerate(args))
        return destructive and any(_contains_raw_data(project, s, cwd) for s in (starts or ["."]))

    if not any(raw(a) for a in args):
        return False
    if command in DELETE_OR_RENAME:
        return True
    if command == "git" and args and args[0] in {"rm", "mv"}:
        return True
    if command in {"sed", "perl"} and any(a.startswith("--in-place") or re.match(r"^-[a-zA-Z]*i", a)
                                          for a in args):
        return True
    if command in COPY_ONTO_LAST and raw(args[-1]):
        return True
    return False


def _check_bash(project: Path, command: str) -> dict | None:
    for segment, words, cwd in shellparse.iter_commands(project, command):
        if _writes_raw(project, segment, words, cwd):
            return _answer("deny", RAW_DATA_REASON)
    return None


def decide(payload: dict, project: Path) -> dict | None:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if tool in EDIT_TOOLS:
        return _check_edit(project, tool_input)
    if tool == "Bash":
        return _check_bash(project, tool_input.get("command", ""))
    return None


if __name__ == "__main__":
    hooklib.run(decide)
