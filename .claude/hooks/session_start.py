"""SessionStart hook: record where the session began and brief the agent."""
import datetime
import json
from pathlib import Path

import hooklib


def decide(payload: dict, project: Path) -> dict:
    session_id = payload.get("session_id", "unknown0")
    state_file = hooklib.state_path(project, session_id)
    if not state_file.exists():
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {"date": datetime.date.today().isoformat(),
                 "head": hooklib.git(project, "rev-parse", "HEAD").strip(),
                 "status": hooklib.git_status(project)}
        state_file.write_text(json.dumps(state), encoding="utf-8")
    state = hooklib.load_state(project, session_id)
    journal = hooklib.journal_path(project, state["date"], session_id).relative_to(project).as_posix()
    context = (
        "This repo is governed by CONSTITUTION.md. Read it before doing any work.\n"
        f"Your session journal is {journal}. If you change anything in the repo, copy "
        f"{hooklib.JOURNAL_TEMPLATE} there and fill in every section before you finish; "
        "the session cannot end until it is complete.\n"
        "Log every bug in logs/bugs/ and every test or validation run in logs/tests/ "
        "(templates in docs/templates/). Raw data in data/*.csv is read-only."
    )
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}


if __name__ == "__main__":
    hooklib.run(decide)
