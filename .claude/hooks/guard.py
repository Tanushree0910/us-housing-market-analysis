"""PreToolUse hook: protect raw data (Article 2) and the constitution (Article 6)."""
import os
import re
import shlex
from pathlib import Path

import hooklib

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", ";;", "|&"}
REDIRECTS = {">", ">>", ">|", "&>", "&>>", ">&"}
PREFIXES = {"sudo", "command", "nohup", "env", "time"}
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


def _relative(project: Path, path_text: str) -> Path | None:
    """path_text resolved against the project, as a project-relative path, or None if outside."""
    if not path_text:
        return None
    path = Path(path_text)
    if not path.is_absolute():
        path = Path(project) / path
    try:
        return path.resolve(strict=False).relative_to(Path(project).resolve(strict=False))
    except (ValueError, OSError):
        return None


def is_raw_data(project: Path, path_text: str) -> bool:
    """True when path_text names a raw file: exactly data/<name>.csv (any letter case)."""
    rel = _relative(project, path_text)
    return (rel is not None and len(rel.parts) == 2 and rel.parts[0] == "data"
            and rel.parts[1].lower().endswith(".csv"))


def _check_edit(project: Path, tool_input: dict) -> dict | None:
    path_text = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if is_raw_data(project, path_text):
        return _answer("deny", RAW_DATA_REASON)
    rel = _relative(project, path_text)
    if rel is not None and rel.as_posix() == "CONSTITUTION.md":
        return _answer("ask", CONSTITUTION_REASON)
    return None


def _tokens(line: str) -> list[str]:
    """Shell words of one line. Like bash, '#' starts a comment only at the start of a word."""
    try:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        tokens = line.split()
    for i, token in enumerate(tokens):
        if token.startswith("#"):
            return tokens[:i]
    return tokens


def _heredoc_end_word(tokens: list[str]) -> str | None:
    """The word that ends a heredoc started on this line (only an unquoted '<<' counts)."""
    for i, token in enumerate(tokens[:-1]):
        if token == "<<":
            word = tokens[i + 1].lstrip("-")
            return word or None
    return None


def _command_lines(command: str) -> list[list[str]]:
    """Tokens of each command line, with heredoc bodies left out (their text is data)."""
    lines = []
    ending = None
    for line in command.split("\n"):
        if ending is not None:
            if line.lstrip("\t") == ending:
                ending = None
            continue
        tokens = _tokens(line)
        lines.append(tokens)
        ending = _heredoc_end_word(tokens)
    return lines


def _segments(tokens: list[str]) -> list[list[str]]:
    segments, current = [], []
    for token in tokens:
        if token in SEPARATORS:
            segments.append(current)
            current = []
        else:
            current.append(token)
    segments.append(current)
    return [s for s in segments if s]


def _segment_writes_raw(project: Path, tokens: list[str]) -> bool:
    words = []
    skip_next = False
    for i, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        if token in REDIRECTS:
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            if is_raw_data(project, target):
                return True
            skip_next = True
            continue
        if token in {"<", "<<", "<<-", "<<<"}:
            skip_next = True
            continue
        words.append(token)
    while words and (words[0] in PREFIXES or re.match(r"^[A-Za-z_]+=", words[0])):
        words = words[1:]
    if not words:
        return False
    command, args = os.path.basename(words[0]), words[1:]

    def raw(text: str) -> bool:
        return is_raw_data(project, text)

    for i, arg in enumerate(args):
        option, _, value = arg.partition("=")
        if value and option in {"of", "--output", "--output-document"} and raw(value):
            return True
        nxt = args[i + 1] if i + 1 < len(args) else ""
        if raw(nxt) and ((command == "curl" and arg in {"-o", "--output"})
                         or (command == "wget" and arg in {"-O", "--output-document"})):
            return True
    raw_args = [a for a in args if raw(a)]
    if not raw_args:
        return False
    if command in DELETE_OR_RENAME:
        return True
    if command == "git" and args and args[0] in {"rm", "mv"}:
        return True
    if command == "sed" and any(a.startswith("--in-place") or re.match(r"^-[a-zA-Z]*i", a) for a in args):
        return True
    if command in COPY_ONTO_LAST and raw(args[-1]):
        return True
    return False


def _check_bash(project: Path, command: str) -> dict | None:
    for tokens in _command_lines(command):
        for segment in _segments(tokens):
            if _segment_writes_raw(project, segment):
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
