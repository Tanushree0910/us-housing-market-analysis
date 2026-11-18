"""SessionStart hook: record where the session began and brief the agent (Articles 4, 5, 8)."""
import datetime
from pathlib import Path

import hooklib

ESSENTIAL_SKILLS = [
    ("superpowers:using-superpowers", "at the start, to check which skills apply"),
    ("superpowers:brainstorming", "before building anything new"),
    ("superpowers:writing-plans", "before multi-step work"),
    ("superpowers:using-git-worktrees", "to set up the worktree you work in"),
    ("superpowers:test-driven-development", "for every code change"),
    ("superpowers:systematic-debugging", "for any bug or failing test"),
    ("superpowers:verification-before-completion", "before saying anything is done"),
    ("superpowers:finishing-a-development-branch", "when the work is complete"),
]


def _status_lines(project: Path, main: Path, trees: dict) -> list[str]:
    lines = []
    main_branch = hooklib.git(main, "branch", "--show-current").strip() or "(no branch)"
    lines.append(f"- Main project folder: {main} — branch {main_branch}")
    if main_branch in hooklib.MAIN_BRANCHES:
        lines.append(f"- WARNING: the main folder is on '{main_branch}'. Never edit, commit or push there.")
    if hooklib.git_status(main):
        lines.append("- Note: the main folder has uncommitted changes. They are not yours; leave them alone.")
    if Path(project).resolve(strict=False) == main:
        lines.append("- You are in the main folder. Create or enter a worktree before changing anything.")
    if trees:
        lines.append("- Worktrees:")
        for path, info in sorted(trees.items()):
            rel = Path(path).relative_to(main).as_posix() if Path(path).is_relative_to(main) else path
            branch = info["branch"] or "(no branch)"
            lines.append(f"  - {rel} — branch {branch}")
            if info["branch"] in hooklib.MAIN_BRANCHES:
                lines.append(f"  - WARNING: {rel} is on '{info['branch']}'. Don't work there.")
    else:
        lines.append("- Worktrees: none yet.")
    return lines


def decide(payload: dict, project: Path) -> dict:
    session_id = payload.get("session_id", "unknown0")
    main = hooklib.main_checkout(project)
    trees = hooklib.worktrees(main)
    if not hooklib.state_path(project, session_id).exists():
        hooklib.save_state(project, session_id, {
            "date": datetime.date.today().isoformat(),
            "head": hooklib.git(project, "rev-parse", "HEAD").strip(),
            "status": hooklib.git_status(project),
            "worktrees": trees,
        })
    state = hooklib.load_state(project, session_id)
    journal = hooklib.journal_path(Path("."), state["date"], session_id).as_posix()

    sections = [
        "This repo is governed by CONSTITUTION.md. Read it before doing any work.",
        "STATUS",
        *_status_lines(project, main, trees),
        "BEFORE CHANGING ANYTHING (Article 5)",
        "- Work only inside a worktree on your own branch, never on main. Create one with:",
        f"  cd {main} && git fetch origin && git worktree add .worktrees/<name> -b <branch> origin/main",
        "- Merge only when the owner asks. Never push to main.",
        "ESSENTIAL SKILLS (invoke each when it applies)",
        *[f"- {name}: {when}" for name, when in ESSENTIAL_SKILLS],
        "RECORDS (Article 4)",
        f"- Your session journal is {journal} inside the worktree you work in. Copy "
        f"{hooklib.JOURNAL_TEMPLATE} and fill in every section before you finish.",
        "- Log every bug in logs/bugs/ and every test or validation run in logs/tests/ "
        "(templates in docs/templates/). Raw data in data/*.csv is read-only.",
        "- The session can't end until your worktree is committed and pushed, the journal is "
        "complete and the governance check passes.",
        "OWNER RULES (Article 8)",
        f"- Every command you give the owner starts with cd to the full folder path, e.g. "
        f"cd {main} && git status — git commands included.",
        "- Never ask the owner to attach, upload or share a file or folder that is in the project "
        "folder or the repo. Look first. If you truly can't reach something, say where you looked.",
        "- Helpers: name the model on every helper — sonnet by default, haiku for quick simple tasks, "
        "opus for hard reasoning. Fable is never used. Don't use fork helpers.",
    ]
    return {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(sections)}}


if __name__ == "__main__":
    hooklib.run(decide)
