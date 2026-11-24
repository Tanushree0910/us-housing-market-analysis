"""Split shell commands into the commands they run, for the PreToolUse guards.

Shared by guard.py (raw data) and git_guard.py (branches, worktrees, dangerous
commands). It is a best-effort reader, not a full shell: anything it misses is
still caught by the GitHub checks.
"""
import os
import re
import shlex
from pathlib import Path
from typing import Iterator

SEPARATORS = {";", "&&", "||", "|", "&", "(", ")", ";;", "|&"}
REDIRECTS = {">", ">>", ">|", "&>", "&>>", ">&"}
INPUT_OPERATORS = {"<", "<<", "<<-", "<<<"}
# Words that come before the real command: shell keywords and command wrappers.
PREFIXES = {"command", "nohup", "exec", "then", "do", "else", "elif", "if", "while", "until",
            "{", "}", "!", "builtin"}
# Wrappers whose options are skipped; options listed here also take a value.
WRAPPER_VALUE_OPTIONS = {
    "sudo": {"-u", "-g", "-U", "-C", "-h", "-p", "-r", "-t", "-D", "-R", "-T"},
    "env": {"-u", "-C", "-S"},
    "nice": {"-n"},
    "time": {"-f", "-o"},
    "ionice": {"-c", "-n", "-p"},
    "timeout": {"-s", "-k"},
}
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


GIT_BASH_DRIVE = re.compile(r"/([A-Za-z])(?=/|$)/?")


def from_git_bash(path_text: str, windows: bool | None = None) -> str:
    """A Git Bash drive path (/c/Users/me) as a Windows one (C:/Users/me); others unchanged.

    Git Bash, the shell behind Claude Code's Bash tool on Windows, writes drive
    paths that way, and pathlib on Windows would read /c/Users as C:\\c\\Users
    (BUG-004). Only done on Windows: on Linux /c is an ordinary folder.
    """
    if not (os.name == "nt" if windows is None else windows):
        return path_text
    drive = GIT_BASH_DRIVE.match(path_text)
    return f"{drive.group(1).upper()}:/{path_text[drive.end():]}" if drive else path_text


def absolute(base: Path, path_text: str, cwd: Path | None = None) -> Path:
    """path_text as a resolved absolute path, relative paths taken from cwd (default base)."""
    path = Path(from_git_bash(os.path.expanduser(path_text)))
    if not path.is_absolute():
        path = Path(cwd or base) / path
    return path.resolve(strict=False)


WORD_BREAKS = set(" \t\r\n;&|()<>")
DRIVE_PATH = re.compile(r"[A-Za-z]:\\")


def _keep_drive_backslashes(line: str) -> str:
    """Double the backslashes of unquoted Windows drive paths so shlex keeps them.

    In a POSIX shell an unquoted backslash escapes the next character, so shlex
    reads C:\\Users\\me as C:Usersme. Commands given on Windows use such paths
    (BUG-003), so in a word that starts with a drive letter ('C:\\', also after
    '=') a backslash is a path separator, except before whitespace, where it
    still escapes the space. Quoted text and every other word are left alone:
    shlex already keeps backslashes in quotes unless they escape a quote.
    """
    out, quote, in_path, i = [], None, False, 0
    while i < len(line):
        ch = line[i]
        if quote:
            if quote == '"' and ch == "\\" and i + 1 < len(line):
                out.append(line[i:i + 2])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch in WORD_BREAKS:
            in_path = False
        elif ch == "\\":
            following = line[i + 1:i + 2]
            if in_path and following and not following.isspace():
                out.append("\\\\")
                i += 1
                continue
            out.append(line[i:i + 2])
            i += 2
            continue
        elif (i == 0 or line[i - 1] in WORD_BREAKS or line[i - 1] == "=") and DRIVE_PATH.match(line, i):
            in_path = True
        out.append(ch)
        i += 1
    return "".join(out)


def tokens(line: str) -> list[str]:
    """Shell words of one line. Like bash, '#' starts a comment only at the start of a word."""
    line = _keep_drive_backslashes(line)
    try:
        lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        found = list(lexer)
    except ValueError:
        found = line.split()
    for i, token in enumerate(found):
        if token.startswith("#"):
            return found[:i]
    return found


def _heredoc_end_word(line_tokens: list[str]) -> str | None:
    """The word that ends a heredoc started on this line (only an unquoted '<<' counts)."""
    for i, token in enumerate(line_tokens[:-1]):
        if token == "<<":
            return line_tokens[i + 1].lstrip("-") or None
    return None


def command_lines(command: str) -> list[list[str]]:
    """Tokens of each command line, with heredoc bodies left out (their text is data)."""
    lines = []
    ending = None
    for line in command.split("\n"):
        if ending is not None:
            if line.lstrip("\t") == ending:
                ending = None
            continue
        line_tokens = tokens(line)
        lines.append(line_tokens)
        ending = _heredoc_end_word(line_tokens)
    return lines


def segments(line_tokens: list[str]) -> list[list[str]]:
    """Split one line's tokens at ; && || | & ( ) into separate commands."""
    found, current = [], []
    for token in line_tokens:
        if token in SEPARATORS:
            found.append(current)
            current = []
        else:
            current.append(token)
    found.append(current)
    return [s for s in found if s]


def strip_prefixes(words: list[str]) -> list[str]:
    """Drop shell keywords, VAR=value settings and wrappers like sudo, keeping the real command."""
    while words:
        first = os.path.basename(words[0])
        if words[0] in PREFIXES or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]):
            words = words[1:]
        elif first in WRAPPER_VALUE_OPTIONS:
            value_options = WRAPPER_VALUE_OPTIONS[first]
            words = words[1:]
            while words and words[0].startswith("-"):
                words = words[2:] if words[0] in value_options else words[1:]
            if first == "timeout" and words:
                words = words[1:]  # the duration
        else:
            break
    return words


def command_words(segment: list[str]) -> list[str]:
    """The words of one command with redirections and their targets removed, prefixes stripped."""
    words = []
    skip_next = False
    for token in segment:
        if skip_next:
            skip_next = False
        elif token in REDIRECTS or token in INPUT_OPERATORS:
            skip_next = True
        else:
            words.append(token)
    return strip_prefixes(words)


def redirect_targets(segment: list[str]) -> list[str]:
    """Files this command writes to with > or >>."""
    return [segment[i + 1] for i, token in enumerate(segment[:-1]) if token in REDIRECTS]


def iter_commands(project: Path, command: str,
                  start_cwd: Path | None = None) -> Iterator[tuple[list[str], list[str], Path | None]]:
    """Yield (segment tokens, command words, folder it runs in) for each command.

    `cd` commands are followed, so later commands are judged in the right folder;
    the `cd` itself is not yielded.
    """
    cwd = start_cwd
    stack = []
    for line_tokens in command_lines(command):
        for segment in segments(line_tokens):
            words = command_words(segment)
            if words[:1] in (["cd"], ["pushd"]):
                if words[0] == "pushd":
                    stack.append(cwd)
                target = os.path.expandvars(words[1]) if len(words) > 1 else ""
                cwd = absolute(project, target, cwd) if target and "$" not in target else start_cwd
                continue
            if words[:1] == ["popd"]:
                cwd = stack.pop() if stack else start_cwd
                continue
            yield segment, words, cwd
