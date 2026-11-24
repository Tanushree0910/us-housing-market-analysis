# Constitution of the U.S. Housing Market Analysis Repo

These are the rules for everyone who works in this repo: the owner and every AI agent.
If anything else in the repo disagrees with this document, this document wins.

## Article 1 — Authority

1. The owner decides the project's vision, rules, architecture and design system.
2. AI agents do the coding, documentation and repo upkeep.
3. Agents must ask the owner before they:
   - send or publish anything outside the repo,
   - delete anything,
   - spend money,
   - change the architecture (folder layout, tools, data model),
   - change this constitution.

## Article 2 — Data

1. `data/` holds raw source files exactly as they were downloaded.
2. Raw files are never edited, renamed or deleted without the owner's approval.
3. The owner chooses and downloads raw data. An agent may copy a file the owner downloaded into `data/` unchanged, under its original name, and commit, push and pull it with git.
4. Every raw file has a row in `data/SOURCES.md` with its file name, source, URL, date added and SHA-256 fingerprint. The fingerprint proves the file has not been changed.
5. Cleaned or derived data is produced by SQL. It is never saved over a raw file.

## Article 3 — Folders and naming

1. Only these items may sit at the top of the repo: `README.md`, `CONSTITUTION.md`, `CLAUDE.md`, `.gitignore`, `data/`, `sql/`, `powerbi/`, `screenshots/`, `docs/`, `logs/`, `tools/`, `tests/`, `.github/`, `.claude/`.
2. These folders accept only these files, and have no sub-folders except the Power BI project folders below:

| Folder | Allowed files | Example |
|---|---|---|
| `data/` | raw `.csv` files (original source names), `SOURCES.md` | `Metro_zori_uc_sfrcondomfr_sm_month.csv` |
| `sql/` | `NN_snake_case.sql`, numbered in run order | `01_load_zhvi.sql` |
| `powerbi/` | `snake_case.pbix`, `snake_case.pbip`, and the `snake_case.SemanticModel/` and `snake_case.Report/` folders Power BI Desktop creates (any contents) | `us_housing_market.pbip` |
| `screenshots/` | `kebab-case.png` or `.jpg` | `rent-to-price-map.png` |

3. No file may be larger than 50 MB.

## Article 4 — Records

1. Every record is a markdown file that copies its template from `docs/templates/` and fills in every section. The placeholder `_TBD_` must not remain.

| Record | Where and how it is named | Sections |
|---|---|---|
| Session journal | `logs/sessions/YYYY-MM-DD-<first 8 characters of session id>.md` | Goal, What changed, Tests run, Bugs found, Next steps |
| Bug log | `logs/bugs/BUG-NNN-kebab-title.md` | Status (`Open` or `Fixed`), Found, What happened, Cause, Fix, Test log |
| Test log | `logs/tests/YYYY-MM-DD-kebab-title.md` | What was tested, How, Result (`PASS` or `FAIL`), Bugs |
| Decision | `docs/decisions/NNNN-kebab-title.md` | Date, Status (`Proposed`, `Accepted` or `Replaced`), Decision, Reason, Alternatives |

2. An agent session that changes anything in the repo must leave a complete session journal before it ends.
3. Every bug found gets a bug log. Every test or validation run gets a test log.
4. Every significant decision gets a decision record.

## Article 5 — Branches, worktrees and merging

1. Agents never work on `main`. They never edit, commit or push in the main project folder, or on a `main` or `master` branch.
2. Agents work only inside a git worktree at `.worktrees/<name>/`, on their own branch. They create one with:
   `cd <project folder> && git fetch origin && git worktree add --no-track .worktrees/<name> -b <branch> origin/main`
3. Nobody pushes to `main`, force-pushes it, deletes it or renames it. `main` changes only through a pull request.
4. Every change must pass the automatic checks (`python3 tools/governance_check.py` and the tests) before it is merged.
5. Merging happens only when the owner asks for it. Every merge command (`git merge`, `gh pr merge`, GitHub merge or auto-merge) needs the owner's approval in a prompt.
6. On GitHub, the "Protect main" ruleset (`.github/rulesets/protect-main.json`, set up as described in `docs/github-setup.md`) enforces rules 3 and 4.

## Article 6 — Amendments

1. Only the owner may change this constitution.
2. An agent may propose an amendment. The amendment is applied only after the owner says yes.
3. Every amendment is recorded as a decision in `docs/decisions/`, and the version line below is updated.

## Article 7 — Safety

1. **Always blocked:**
   - deleting the computer's top-level folders, the home folder, the whole project or any `.git` history;
   - force-pushing and rewriting history (`git filter-branch`, `git filter-repo`, `git reflog expire`);
   - writing to disk devices (`mkfs`, `dd` onto a disk);
   - running a script straight from the internet (`curl … | sh`);
   - `chmod -R 777`; fork bombs;
   - deleting the GitHub repository.
2. **Ask the owner first**, for anything that throws work away:
   - `git reset --hard`, `git clean -f`, deleting a branch with `-D`;
   - discarding file changes (`git checkout -- …`, `git checkout .`, `git restore`);
   - dropping stashes;
   - force-removing a worktree;
   - deleting a whole folder.

## Article 8 — AI agents and helper agents

1. **Session start.** Each agent session is told:
   - its branch and worktree status, with a warning if anything is on `main`;
   - how to create a worktree;
   - the essential skills to use;
   - the owner's rules.
2. **Session end.** A session can't end until, for everything it changed:
   - all work is committed and pushed;
   - the governance check passes;
   - the session journal is complete.
3. **Helper agents.**
   - Every helper (subagent or new session) must name its model: Sonnet by default, Haiku for quick simple tasks, Opus for hard reasoning.
   - Fable is never used.
   - "Fork" helpers, which silently copy the main session's model, are not used.
   - Helpers follow this constitution like any other agent.
4. **Talking to the owner.**
   - Every command given to the owner starts with `cd` to the full folder path, git commands included.
   - Agents never ask the owner to attach, upload or share a file or folder that is already in the project folder or the repo. They look first. If something truly can't be reached, they say where they looked.

## How these rules are enforced

- **Automatic checks on GitHub** run `tools/governance_check.py` and the tests on every push and pull request.
- **The "Protect main" ruleset on GitHub** requires pull requests and the governance check for `main`, and blocks force-pushes and deletion (`docs/github-setup.md`).
- **Claude Code hooks** in `.claude/`:
  - brief each agent session at start;
  - block edits to raw data, work outside worktrees, work on `main`, pushes to `main` and dangerous commands;
  - ask the owner before risky commands, merges and any change to this document;
  - enforce the helper-model rules;
  - stop a session from ending until its work is committed, pushed, checked and recorded in its journal.

---

Version 1.3 — amended 2026-11-24: combines version 1.1 (decision 0002, adopted 2026-11-18) with the amendments in decisions 0003 and 0004 (made 2026-11-17 on a parallel branch). Version 1.0 adopted 2026-11-17. Amendments are recorded in `docs/decisions/`.
