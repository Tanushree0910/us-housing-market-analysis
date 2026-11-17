"""Stop hook: a session that changed the repo must leave a complete journal (Article 4)."""
from pathlib import Path

import hooklib


def _changed(project: Path, state: dict, journal_rel: str) -> bool:
    status = hooklib.git(project, "status", "--porcelain", "--untracked-files=all")
    for line in status.splitlines():
        path = line[3:].strip().strip('"')
        if path == journal_rel or path.startswith(".claude/state/"):
            continue
        return True
    head = hooklib.git(project, "rev-parse", "HEAD").strip()
    return bool(state.get("head")) and head != state["head"]


def decide(payload: dict, project: Path) -> dict | None:
    if payload.get("stop_hook_active"):
        return None
    session_id = payload.get("session_id", "unknown0")
    state = hooklib.load_state(project, session_id)
    journal = hooklib.journal_path(project, state["date"], session_id)
    journal_rel = journal.relative_to(project).as_posix()
    if not _changed(project, state, journal_rel):
        return None
    if journal.is_file():
        problems = hooklib.rules.record_problems(hooklib.JOURNAL_FOLDER, journal.name,
                                                 journal.read_text(encoding="utf-8", errors="replace"))
    else:
        problems = [f"{journal_rel}: does not exist yet"]
    if not problems:
        return None
    reason = ("This session changed the repo, so its journal must be complete before you finish "
              f"(CONSTITUTION.md Article 4). Journal: {journal_rel} — copy "
              f"{hooklib.JOURNAL_TEMPLATE} and fill in every section.\nProblems:\n- "
              + "\n- ".join(problems))
    return {"decision": "block", "reason": reason}


if __name__ == "__main__":
    hooklib.run(decide)
