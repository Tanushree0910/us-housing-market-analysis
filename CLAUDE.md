# Agent briefing

This repo is governed by `CONSTITUTION.md`. Read it before doing any work. If this file and the constitution disagree, the constitution wins.

## Your duties
- Work on a branch, never directly on `main`.
- Never edit, rename or delete raw data in `data/*.csv`. A hook blocks it. If a raw file must change, ask the owner.
- Never change `CONSTITUTION.md` unless the owner has said yes. A hook asks the owner before any edit. Record each amendment in `docs/decisions/`.
- Ask the owner before you send, publish, delete, spend money, or change the architecture.
- Follow the folder and naming rules in Article 3 of the constitution.

## Records (templates in `docs/templates/`)
- **Session journal:** if you change anything, fill in `logs/sessions/YYYY-MM-DD-<first 8 characters of session id>.md` before you finish. The start-of-session message gives you the exact path. A hook stops the session from ending until the journal is complete.
- **Bug log:** every bug you find goes in `logs/bugs/BUG-NNN-kebab-title.md`.
- **Test log:** every test or validation run goes in `logs/tests/YYYY-MM-DD-kebab-title.md`.
- **Decision:** every significant decision goes in `docs/decisions/NNNN-kebab-title.md`.
- Never leave the `_TBD_` placeholder in a record.

## Before you commit
Run both, and fix anything they report:

```bash
cd "$CLAUDE_PROJECT_DIR" && python3 tools/governance_check.py
```

```bash
cd "$CLAUDE_PROJECT_DIR" && python3 -m unittest discover -s tests -t .
```

The same checks run on GitHub for every push, and their results show on pull requests.

## Adding raw data
The owner chooses and downloads raw data (CONSTITUTION.md Article 2). You may copy a file the owner downloaded into `data/` unchanged, under its original name, then commit, push and pull it with git. Never edit, rename, re-save or replace it. Add its row to `data/SOURCES.md`, with the fingerprint from `python3 tools/governance_check.py --fingerprint data/<file>`. Use this rather than `sha256sum`, because the check ignores Windows line endings. If you need data the owner hasn't downloaded, ask them for it.
