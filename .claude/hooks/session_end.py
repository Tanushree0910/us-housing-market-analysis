"""Stop hook: before a session ends, its work must be tidy (Articles 4 and 5).

For the session's own folder (when it is a worktree) and every worktree this
session worked in (recorded by git_guard) that changed during the session:
- nothing is left uncommitted,
- every commit has been pushed (when the repo has a remote),
- the governance check passes,
- the session journal exists and is complete (in any of those places).

Within one turn the agent is sent back to fix problems up to MAX_JOURNAL_BLOCKS
times. After that the turn is allowed to end, so it can never get stuck, and the
owner is shown a message. The next turn is checked again from scratch.
"""
from pathlib import Path

import hooklib

import governance_check  # noqa: E402  (hooklib puts tools/ on the import path)

MAX_JOURNAL_BLOCKS = 3


def _own_lines(lines: list[str], before: set[str] = frozenset()) -> list[str]:
    """Status lines that are new and not hook scratch files."""
    return [line for line in lines
            if line not in before and not line[3:].strip().strip('"').startswith(".claude/state/")]


def _session_folder_changed(project: Path, state: dict) -> bool:
    if _own_lines(hooklib.git_status(project), set(state.get("status", []))):
        return True
    head = hooklib.git(project, "rev-parse", "HEAD").strip()
    return bool(state.get("head")) and head != state["head"]


def _changed_worktrees(trees: dict[str, dict], project: Path, state: dict) -> dict[str, dict]:
    """Worktrees this session worked in that changed since it started.

    Worktrees the session never touched belong to other sessions or the owner,
    so they are left alone.
    """
    before = state.get("worktrees", {})
    touched = set(state.get("touched", []))
    changed = {}
    for path, info in trees.items():
        if Path(path) == Path(project).resolve(strict=False) or path not in touched:
            continue
        old = before.get(path)
        if old is None or old.get("head") != info["head"] or old.get("status") != info["status"]:
            changed[path] = info
    return changed


def _unpushed(place: Path) -> int:
    if not hooklib.git(place, "remote").strip() or not hooklib.git(place, "branch", "--show-current").strip():
        return 0
    count = hooklib.git(place, "rev-list", "--count", "HEAD", "--not", "--remotes").strip()
    return int(count) if count.isdigit() else 0


def _place_problems(place: Path, label: str, new_lines: list[str]) -> list[str]:
    problems = []
    if new_lines:
        files = ", ".join(line[3:].strip() for line in new_lines[:5]) + (" …" if len(new_lines) > 5 else "")
        problems.append(f"{label} has uncommitted changes ({files}). Commit them: "
                        f"cd {place} && git add -A && git commit -m \"<what changed>\"")
    count = _unpushed(place)
    if count:
        branch = hooklib.git(place, "branch", "--show-current").strip()
        problems.append(f"{label}: {count} commit(s) have not been pushed. Push them: "
                        f"cd {place} && git push -u origin {branch}")
    problems += [f"{label}: {p}" for p in governance_check.check_repo(place)]
    return problems


def _journal_problems(places: list[Path], journal_rel: str) -> list[str]:
    found = []
    for place in places:
        journal = place / journal_rel
        if journal.is_file():
            issues = hooklib.rules.record_problems(hooklib.JOURNAL_FOLDER, journal.name,
                                                   journal.read_text(encoding="utf-8", errors="replace"))
            if not issues:
                return []
            found += issues
    return found or [f"{journal_rel}: does not exist yet. Copy {hooklib.JOURNAL_TEMPLATE} there "
                     "(in the worktree you worked in) and fill in every section."]


def decide(payload: dict, project: Path) -> dict | None:
    session_id = payload.get("session_id", "unknown0")
    project = Path(project).resolve(strict=False)
    state = hooklib.load_state(project, session_id)
    main = hooklib.main_checkout(project)
    journal_rel = hooklib.journal_path(Path("."), state["date"], session_id).as_posix()

    trees = hooklib.worktrees(main)
    problems = []
    changed_places = []
    # The main folder is never an agent's workplace (Article 5): changes there are the
    # owner's, so they are not this session's to commit.
    if project != main and _session_folder_changed(project, state):
        changed_places.append(project)
        new_lines = _own_lines(hooklib.git_status(project), set(state.get("status", [])))
        problems += _place_problems(project, str(project), new_lines)
    for path, info in _changed_worktrees(trees, project, state).items():
        changed_places.append(Path(path))
        problems += _place_problems(Path(path), path, _own_lines(info["status"]))
    if changed_places:
        problems += _journal_problems([project, *[Path(p) for p in trees]], journal_rel)

    if not problems:
        if state.get("journal_blocks"):
            state["journal_blocks"] = 0
            hooklib.save_state(project, session_id, state)
        return None

    # Count only the retries within one turn: a new turn (not a stop-hook retry) starts again.
    blocks = state.get("journal_blocks", 0) if payload.get("stop_hook_active") else 0
    if blocks >= MAX_JOURNAL_BLOCKS:
        return {"systemMessage": f"Session ended with unfinished work (journal: {journal_rel}): "
                                 f"{problems[0]} Please ask the agent to finish it."}
    state["journal_blocks"] = blocks + 1
    hooklib.save_state(project, session_id, state)
    reason = ("Before you finish, tidy up this session's work (CONSTITUTION.md Articles 4 and 5). "
              f"Session journal: {journal_rel} — copy {hooklib.JOURNAL_TEMPLATE}.\nProblems:\n- "
              + "\n- ".join(problems))
    return {"decision": "block", "reason": reason}


if __name__ == "__main__":
    hooklib.run(decide)
