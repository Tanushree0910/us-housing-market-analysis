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
3. Every raw file has a row in `data/SOURCES.md` with its file name, source, URL, date added and SHA-256 fingerprint. The fingerprint proves the file has not been changed.
4. Cleaned or derived data is produced by SQL. It is never saved over a raw file.

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

## Article 5 — How changes are made

1. Agents work on a branch, never directly on `main`.
2. Every change must pass the automatic checks (`python3 tools/governance_check.py` and the tests) before it is merged.
3. Only the owner approves merges into `main`.

## Article 6 — Amendments

1. Only the owner may change this constitution.
2. An agent may propose an amendment. The amendment is applied only after the owner says yes.
3. Every amendment is recorded as a decision in `docs/decisions/`, and the version line below is updated.

## How these rules are enforced

- **Automatic checks on GitHub** run `tools/governance_check.py` and the tests on every push and pull request.
- **Claude Code hooks** in `.claude/` brief each agent session at start, block edits to raw data, ask the owner before any change to this document, and stop a session from ending without a complete journal.

---

Version 1.1 — amended 2026-11-17 (decision 0002) — amendments are recorded in `docs/decisions/`.
