# Agent briefing

This repo is governed by `CONSTITUTION.md`. Read it before doing any work. If this file and the constitution disagree, the constitution wins.

## Where you work (Article 5)
- Never work on `main` and never change anything in the main project folder. Work only in a worktree on your own branch:
  `cd <project folder> && git fetch origin && git worktree add .worktrees/<name> -b <branch> origin/main`
- Never push to `main`, force-push, or delete or rename `main`. `main` changes only through a pull request.
- Merge only when the owner asks. Every merge command raises an approval prompt.

## Your duties
- Never edit, rename or delete raw data in `data/*.csv`. A hook blocks it. If a raw file must change, ask the owner.
- Never change `CONSTITUTION.md` unless the owner has said yes. A hook asks the owner before any edit. Record each amendment in `docs/decisions/`.
- Ask the owner before you send, publish, delete, spend money, or change the architecture.
- Dangerous commands are blocked, and commands that throw work away ask the owner first (Article 7).
- Follow the folder and naming rules in Article 3 of the constitution.

## Helpers (Article 8)
- Name the model on every helper: `sonnet` by default, `haiku` for quick simple tasks, `opus` for hard reasoning.
- Fable is never used. Don't use `fork` helpers.

## Talking to the owner (Article 8)
- Every command you give the owner starts with `cd` to the full folder path, git commands included.
- Never ask the owner to attach, upload or share a file or folder that is already in the project folder or the repo. Look first. If you truly can't reach something, say where you looked.

## Records (templates in `docs/templates/`)
- **Session journal:** if you change anything, fill in `logs/sessions/YYYY-MM-DD-<first 8 characters of session id>.md` in your worktree before you finish. The start-of-session message gives you the exact path.
- **Bug log:** every bug you find goes in `logs/bugs/BUG-NNN-kebab-title.md`.
- **Test log:** every test or validation run goes in `logs/tests/YYYY-MM-DD-kebab-title.md`.
- **Decision:** every significant decision goes in `docs/decisions/NNNN-kebab-title.md`.
- Never leave the `_TBD_` placeholder in a record.

## Before you finish
A hook stops the session from ending until every worktree you changed is committed and pushed, the governance check passes and your journal is complete. Run both checks in your worktree and fix anything they report:

```bash
cd <your worktree> && python3 tools/governance_check.py
```

```bash
cd <your worktree> && python3 -m unittest discover -s tests -t .
```

The same checks run on GitHub for every push, and their results show on pull requests.

## Adding raw data
Adding or replacing raw data is the owner's job. If new data is needed, ask the owner to put the file in `data/` under its original name. Then add its row to `data/SOURCES.md`, with the fingerprint from `python3 tools/governance_check.py --fingerprint data/<file>`. Use this rather than `sha256sum`, because the check ignores Windows line endings.
