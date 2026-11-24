"""PreToolUse hook: branches, worktrees, dangerous commands and merges.

- Article 5: agents work only in worktrees under .worktrees/, never on main;
  main can't be pushed to, deleted or renamed; merging asks the owner.
- Article 7: commands that could wreck the computer, the repo or its history are
  blocked; commands that throw work away ask the owner first.
"""
import os
import re
from pathlib import Path

import hooklib
import shellparse

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
GIT_WRITES = {"commit", "merge", "rebase", "cherry-pick", "revert", "am", "reset", "push"}
FORCE_FLAGS = {"-f", "--force", "--force-with-lease", "--force-if-includes"}
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
GITHUB_FILE_WRITES = {"mcp__github__create_or_update_file", "mcp__github__push_files",
                      "mcp__github__delete_file"}
GITHUB_MERGES = {"mcp__github__merge_pull_request", "mcp__github__enable_pr_auto_merge"}
FORK_BOMB = re.compile(r":\s*\(\s*\)\s*\{")


def _answer(kind: str, reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": kind,
                                   "permissionDecisionReason": reason}}


def _worktree_hint(main: Path) -> str:
    return ("Create a worktree and work there instead:\n"
            f"cd {main} && git fetch origin && git worktree add --no-track .worktrees/<name> -b <branch> origin/main")


# ---------- where a path or command lives ----------

def _existing(path: Path) -> Path:
    while not path.exists() and path != path.parent:
        path = path.parent
    return path


def _place(project: Path, folder: Path | None) -> tuple[str, str]:
    """('main' | 'worktree' | 'outside', branch) for a folder."""
    folder = _existing(Path(folder or project).resolve(strict=False))
    main = hooklib.main_checkout(project)
    top = hooklib.git(folder, "rev-parse", "--show-toplevel").strip()
    if not top:
        return "outside", ""
    top_path = Path(top).resolve(strict=False)
    branch = hooklib.git(folder, "branch", "--show-current").strip()
    if top_path == main:
        return "main", branch
    if top_path.parent == main / hooklib.WORKTREES_FOLDER:
        return "worktree", branch
    return "outside", branch


# ---------- edits ----------

def _check_edit(project: Path, tool_input: dict) -> dict | None:
    path_text = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    if not path_text:
        return None
    path = shellparse.absolute(project, path_text)
    main = hooklib.main_checkout(project)
    if not path.is_relative_to(main):
        return None
    rel = path.relative_to(main)
    if len(rel.parts) >= 3 and rel.parts[0] == hooklib.WORKTREES_FOLDER:
        worktree = main / rel.parts[0] / rel.parts[1]
        branch = hooklib.git(worktree, "branch", "--show-current").strip() if worktree.is_dir() else ""
        if branch in hooklib.MAIN_BRANCHES:
            return _answer("deny", f"This worktree is on '{branch}'. Agents never work on main "
                                   f"(CONSTITUTION.md Article 5). {_worktree_hint(main)}")
        if worktree.is_dir():
            return None
    return _answer("deny", "Agents only edit files inside a worktree under .worktrees/, never in the "
                           f"main project folder (CONSTITUTION.md Article 5). {_worktree_hint(main)}")


# ---------- shell commands ----------

def _git_parts(words: list[str], project: Path, cwd: Path | None) -> tuple[str, list[str], Path | None]:
    """(subcommand, its arguments, folder git runs in) for a git command."""
    args = words[1:]
    while args and args[0].startswith("-"):
        if args[0] == "-C" and len(args) > 1:
            cwd = shellparse.absolute(project, args[1], cwd)
        args = args[2:] if args[0] in shellparse.GIT_VALUE_OPTIONS else args[1:]
    return (args[0] if args else ""), args[1:], cwd


def _ref_name(ref: str) -> str:
    ref = ref.lstrip("+")
    return ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref


def _check_push(args: list[str], branch: str) -> tuple[str, str] | None:
    flags = [a for a in args if a.startswith("-")]
    positional = [a for a in args if not a.startswith("-")]
    refspecs = positional[1:]
    if any(f in FORCE_FLAGS or f.startswith("--force") or re.match(r"^-[a-zA-Z]*f", f) for f in flags) \
            or any(r.startswith("+") for r in refspecs):
        return "deny", "Force-pushing rewrites history and is blocked (CONSTITUTION.md Article 7)."
    if "--all" in flags or "--mirror" in flags:
        return "deny", "Pushing all branches could change main and is blocked (CONSTITUTION.md Article 5)."
    for refspec in refspecs:
        target = refspec.split(":")[-1] if ":" in refspec else refspec
        target = branch if target == "HEAD" else _ref_name(target)
        if target in hooklib.MAIN_BRANCHES:
            return "deny", ("Pushing to main is blocked: main only changes through a pull request "
                            "the owner merges (CONSTITUTION.md Article 5). Push your own branch instead.")
    if not refspecs and branch in hooklib.MAIN_BRANCHES:
        return "deny", "This would push main, which is blocked (CONSTITUTION.md Article 5)."
    return None


def _check_git(sub: str, args: list[str], place: str, branch: str, main: Path) -> list[tuple[str, str]]:
    found = []
    positional = [a for a in args if not a.startswith("-")]
    flags = [a for a in args if a.startswith("-")]
    if sub in GIT_WRITES and (place == "main" or (place == "worktree" and branch in hooklib.MAIN_BRANCHES)):
        where = "the main project folder" if place == "main" else f"branch '{branch}'"
        found.append(("deny", f"'git {sub}' in {where} is blocked: agents only commit and push from a "
                              f"worktree on their own branch (CONSTITUTION.md Article 5). {_worktree_hint(main)}"))
    if sub == "push":
        result = _check_push(args, branch)
        if result:
            found.append(result)
    if sub in {"filter-branch", "filter-repo"} or (sub == "reflog" and positional[:1] == ["expire"]):
        found.append(("deny", f"'git {sub}' rewrites or erases history and is blocked (CONSTITUTION.md Article 7)."))
    if sub == "branch" and any(f in {"-d", "-D", "--delete", "-m", "-M", "--move"} for f in flags) \
            and any(_ref_name(p) in hooklib.MAIN_BRANCHES for p in positional):
        found.append(("deny", "Deleting or renaming main is blocked (CONSTITUTION.md Article 5)."))
    if sub == "update-ref" and any(_ref_name(p) in hooklib.MAIN_BRANCHES for p in positional):
        found.append(("deny", "Changing main directly is blocked (CONSTITUTION.md Article 5)."))
    if sub == "merge":
        found.append(("ask", "Merging happens only when the owner asks (CONSTITUTION.md Article 5). "
                             "Approve only if you asked for this merge."))
    discard = None
    if sub == "reset" and "--hard" in flags:
        discard = "'git reset --hard' throws away uncommitted work"
    elif sub == "clean" and any(re.match(r"^-[a-zA-Z]*f", f) or f == "--force" for f in flags):
        discard = "'git clean' deletes untracked files"
    elif sub == "branch" and any(f in {"-D"} or (f == "--delete" and "--force" in flags) for f in flags):
        discard = "'git branch -D' deletes a branch even if its work isn't merged"
    elif sub == "checkout" and ("--" in args or "." in positional):
        discard = "this 'git checkout' throws away changes to files"
    elif sub == "restore" and not any(f in {"--staged", "-S"} for f in flags):
        discard = "'git restore' throws away changes to files"
    elif sub == "stash" and positional[:1] in (["drop"], ["clear"]):
        discard = "dropping a stash deletes saved work"
    elif sub == "worktree" and positional[:1] == ["remove"] and any(f in {"-f", "--force"} for f in flags):
        discard = "force-removing a worktree deletes its uncommitted work"
    if discard:
        found.append(("ask", f"{discard.capitalize()} (CONSTITUTION.md Article 7). "
                             "Approve only if you're sure."))
    return found


def _check_rm(args: list[str], project: Path, cwd: Path | None, main: Path) -> tuple[str, str] | None:
    flags = [a for a in args if a.startswith("-") and a != "--"]
    if not any(f == "--recursive" or (not f.startswith("--") and re.search(r"[rR]", f)) for f in flags):
        return None
    home = Path.home().resolve(strict=False)
    for target in (a for a in args if not a.startswith("-")):
        if target in {"$HOME", "${HOME}", "~", "~/"}:
            return "deny", f"'rm -r {target}' would delete the home folder and is blocked (CONSTITUTION.md Article 7)."
        if Path(target.rstrip("/")).name == ".git":
            return "deny", f"'rm -r {target}' would delete the repo's git history and is blocked (CONSTITUTION.md Article 7)."
        resolved = shellparse.absolute(project, target, cwd)
        here = Path(cwd or project).resolve(strict=False)
        if len(resolved.parts) <= 2 or resolved == home or main.is_relative_to(resolved) \
                or (target in {"*", ".", "./*"} and here == main):
            return "deny", (f"'rm -r {target}' would delete the computer's files, the home folder or the "
                            "whole project, and is blocked (CONSTITUTION.md Article 7).")
    return "ask", ("Deleting a whole folder can't be undone (CONSTITUTION.md Article 7). "
                   "Approve only if you're sure.")


def _check_other(command: str, args: list[str], segment: list[str]) -> tuple[str, str] | None:
    if command.startswith("mkfs") or (command == "dd" and any(a.startswith("of=/dev/") for a in args)) \
            or any(t.startswith(("/dev/sd", "/dev/nvme", "/dev/disk", "/dev/hd")) for t in shellparse.redirect_targets(segment)):
        return "deny", "Writing to a disk device can erase the computer and is blocked (CONSTITUTION.md Article 7)."
    if command == "gh" and args[:2] == ["repo", "delete"]:
        return "deny", "Deleting the GitHub repository is blocked (CONSTITUTION.md Article 7)."
    if command == "gh" and args[:2] == ["pr", "merge"]:
        return "ask", ("Merging happens only when the owner asks (CONSTITUTION.md Article 5). "
                       "Approve only if you asked for this merge.")
    if command == "chmod" and any(f in {"-R", "--recursive"} for f in args) and "777" in args:
        return "deny", "'chmod -R 777' makes everything writable by anyone and is blocked (CONSTITUTION.md Article 7)."
    return None


def _pipes_to_shell(line_tokens: list[str]) -> bool:
    """curl/wget output piped straight into a shell or python."""
    commands, current = [], []
    for token in line_tokens + [";"]:
        if token in shellparse.SEPARATORS:
            commands.append((shellparse.command_words(current), token))
            current = []
        else:
            current.append(token)
    for (words, sep), (next_words, _) in zip(commands, commands[1:]):
        if sep == "|" and words and next_words and os.path.basename(words[0]) in {"curl", "wget"}:
            target = os.path.basename(next_words[0])
            if target in SHELLS or target.startswith("python"):
                return True
    return False


def _touched_by_command(project: Path, command: str, start_cwd: Path | None) -> set[Path]:
    """Worktrees a command works in: its folder, a git -C folder, or one it creates."""
    found = set()
    for _, words, cwd in shellparse.iter_commands(project, command, start_cwd):
        folders = [Path(cwd or project)]
        if words and os.path.basename(words[0]) == "git":
            sub, args, git_dir = _git_parts(words, project, cwd)
            folders.append(Path(git_dir or cwd or project))
            positional = [a for a in args if not a.startswith("-")]
            if sub == "worktree" and positional[:1] == ["add"] and len(positional) > 1:
                folders.append(shellparse.absolute(project, positional[1], git_dir or cwd))
        for folder in folders:
            worktree = hooklib.worktree_of(project, folder)
            if worktree:
                found.add(worktree)
    return found


def _check_bash(project: Path, command: str, start_cwd: Path | None) -> dict | None:
    if FORK_BOMB.search(command):
        return _answer("deny", "This looks like a fork bomb and is blocked (CONSTITUTION.md Article 7).")
    if any(_pipes_to_shell(line) for line in shellparse.command_lines(command)):
        return _answer("deny", "Running a script straight from the internet is blocked "
                               "(CONSTITUTION.md Article 7). Download it, read it, then run it.")
    main = hooklib.main_checkout(project)
    asks = []
    for segment, words, cwd in shellparse.iter_commands(project, command, start_cwd):
        if not words:
            continue
        name, args = os.path.basename(words[0]), words[1:]
        found = []
        if name == "git":
            sub, git_args, git_dir = _git_parts(words, project, cwd)
            place, branch = _place(project, git_dir)
            found += _check_git(sub, git_args, place, branch, main)
        elif name == "rm":
            result = _check_rm(args, project, cwd, main)
            if result:
                found.append(result)
        result = _check_other(name, args, segment)
        if result:
            found.append(result)
        for kind, reason in found:
            if kind == "deny":
                return _answer("deny", reason)
            asks.append(reason)
    return _answer("ask", asks[0]) if asks else None


def _check_mcp(tool: str, tool_input: dict) -> dict | None:
    if tool in GITHUB_MERGES:
        return _answer("ask", "Merging happens only when the owner asks (CONSTITUTION.md Article 5). "
                              "Approve only if you asked for this merge.")
    if tool in GITHUB_FILE_WRITES and str(tool_input.get("branch", "")) in hooklib.MAIN_BRANCHES:
        return _answer("deny", "Writing files straight to main on GitHub is blocked; use your own branch "
                               "and a pull request (CONSTITUTION.md Article 5).")
    return None


def decide(payload: dict, project: Path) -> dict | None:
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    session_id = payload.get("session_id", "")
    if tool in EDIT_TOOLS:
        path_text = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if path_text:
            worktree = hooklib.worktree_of(project, shellparse.absolute(project, path_text))
            hooklib.mark_touched(project, session_id, {worktree} if worktree else set())
        return _check_edit(project, tool_input)
    if tool == "Bash":
        cwd = Path(payload["cwd"]) if payload.get("cwd") else None
        command = tool_input.get("command", "")
        hooklib.mark_touched(project, session_id, _touched_by_command(project, command, cwd))
        return _check_bash(project, command, cwd)
    if tool.startswith("mcp__github__"):
        return _check_mcp(tool, tool_input)
    return None


if __name__ == "__main__":
    hooklib.run(decide)
