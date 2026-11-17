"""Stop hook: a session that changed the repo must leave a complete journal (Article 4).

Within one turn the agent is sent back to finish the journal up to
MAX_JOURNAL_BLOCKS times. After that the turn is allowed to end, so it can never
get stuck, and the owner is shown a message that the journal is unfinished.
The next turn is checked again from scratch.
"""
from pathlib import Path

import hooklib

MAX_JOURNAL_BLOCKS = 3


def _changed(project: Path, state: dict, journal_rel: str) -> bool:
    before = set(state.get("status", []))
    for line in hooklib.git_status(project):
        if line in before:
            continue
        path = line[3:].strip().strip('"')
        if path == journal_rel or path.startswith(".claude/state/"):
            continue
        return True
    head = hooklib.git(project, "rev-parse", "HEAD").strip()
    return bool(state.get("head")) and head != state["head"]


def _journal_problems(journal: Path, journal_rel: str) -> list[str]:
    if not journal.is_file():
        return [f"{journal_rel}: does not exist yet"]
    return hooklib.rules.record_problems(hooklib.JOURNAL_FOLDER, journal.name,
                                         journal.read_text(encoding="utf-8", errors="replace"))


def decide(payload: dict, project: Path) -> dict | None:
    session_id = payload.get("session_id", "unknown0")
    state = hooklib.load_state(project, session_id)
    journal = hooklib.journal_path(project, state["date"], session_id)
    journal_rel = journal.relative_to(project).as_posix()
    problems = _journal_problems(journal, journal_rel) if _changed(project, state, journal_rel) else []

    if not problems:
        if state.get("journal_blocks"):
            state["journal_blocks"] = 0
            hooklib.save_state(project, session_id, state)
        return None

    # Count only the retries within one turn: a new turn (not a stop-hook retry) starts again.
    blocks = state.get("journal_blocks", 0) if payload.get("stop_hook_active") else 0
    if blocks >= MAX_JOURNAL_BLOCKS:
        return {"systemMessage": f"Session ended without a complete journal: {journal_rel}. "
                                 "Please ask the agent to finish it."}
    state["journal_blocks"] = blocks + 1
    hooklib.save_state(project, session_id, state)
    reason = ("This session changed the repo, so its journal must be complete before you finish "
              f"(CONSTITUTION.md Article 4). Journal: {journal_rel} — copy "
              f"{hooklib.JOURNAL_TEMPLATE} and fill in every section.\nProblems:\n- "
              + "\n- ".join(problems))
    return {"decision": "block", "reason": reason}


if __name__ == "__main__":
    hooklib.run(decide)
