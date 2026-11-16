# Repo Governance & Constitution — Design

**Owner:** repo owner (sole authority over vision, rules, architecture, design system)
**Governed parties:** the owner and every AI agent working in the repo
**Enforcement:** written rules + automatic checks on GitHub + Claude Code hooks on the agent's machine

## 1. Documents

| File | Purpose |
|---|---|
| `CONSTITUTION.md` | The rules. Articles listed in §2. |
| `CLAUDE.md` | Short agent briefing; points to the constitution and lists the agent duties in §4. Loaded automatically by Claude Code. |
| `docs/decisions/NNNN-kebab-title.md` | Decision log, one file per decision. |
| `docs/templates/` | `decision.md`, `bug-log.md`, `test-log.md`, `session-journal.md`. |
| `data/SOURCES.md` | Manifest of every raw data file. |
| `logs/sessions/` | Session journals, one per agent session. |
| `logs/bugs/` | Bug logs. |
| `logs/tests/` | Test logs. |

## 2. Constitution articles

1. **Authority.** The owner decides vision, rules, architecture and design system. Agents do coding, docs and repo upkeep. Agents ask before: sending, publishing, deleting, spending money, changing architecture, changing the constitution.
2. **Data.** `data/` holds raw source files exactly as downloaded. Raw files are never edited, renamed or deleted without owner approval. Every raw file has a row in `data/SOURCES.md` (file, source, URL, date added, SHA-256). Derived data is produced by SQL, never saved over raw files.
3. **Folders & naming.** Allowed top-level entries: `README.md`, `CONSTITUTION.md`, `CLAUDE.md`, `.gitignore`, `data/`, `sql/`, `powerbi/`, `screenshots/`, `docs/`, `logs/`, `tools/`, `tests/`, `.github/`, `.claude/`. Per-folder rules:
   - `data/`: `.csv` raw files (original source names kept), `SOURCES.md`, `.gitkeep`
   - `sql/`: `NN_snake_case.sql` (two-digit run order)
   - `powerbi/`: `snake_case.pbix`
   - `screenshots/`: `kebab-case.png` or `.jpg`
   - No file over 50 MB anywhere.
4. **Records.** Session journals, bug logs, test logs and decisions follow the templates and naming in §3.
5. **Change process.** Agents work on a branch, never directly on `main`. Every change passes the automatic checks before merge. The owner approves merges.
6. **Amendments.** Only the owner changes the constitution. An agent may propose an amendment; it is applied only after the owner says yes, and recorded as a decision.

## 3. Record formats

Every record is markdown with `## ` headings. All listed headings are required; none may contain the placeholder `_TBD_`.

| Record | Path pattern | Required headings |
|---|---|---|
| Session journal | `logs/sessions/YYYY-MM-DD-<first 8 chars of session id>.md` | Goal, What changed, Tests run, Bugs found, Next steps |
| Bug log | `logs/bugs/BUG-NNN-kebab-title.md` | Status, Found, What happened, Cause, Fix, Test log |
| Test log | `logs/tests/YYYY-MM-DD-kebab-title.md` | What was tested, How, Result, Bugs |
| Decision | `docs/decisions/NNNN-kebab-title.md` | Date, Status, Decision, Reason, Alternatives |

Bug `Status` is `Open` or `Fixed`. Test `Result` is `PASS` or `FAIL`. Decision `Status` is `Proposed`, `Accepted` or `Replaced`.

## 4. Agent duties (enforced by hooks)

- **Session start:** agent is told to read `CONSTITUTION.md` and given its journal path.
- **Before edits:** writes to raw `data/*.csv` are blocked; writes to `CONSTITUTION.md` require the owner to approve in a prompt.
- **Before ending a session:** if the session changed anything in the repo, the agent cannot finish until its session journal exists and is complete.
- Any bug found gets a bug log; any test or validation run gets a test log.

## 5. Automatic checks (GitHub)

Runs on every push and pull request: folder/naming rules, size limit, data manifest + fingerprints, record formats, and the checker's own tests.
