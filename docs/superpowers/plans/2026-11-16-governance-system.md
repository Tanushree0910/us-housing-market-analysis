# Repo Governance System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the repo a constitution, record-keeping system (decisions, session journals, bug logs, test logs) and enforcement through a GitHub checker plus Claude Code hooks.

**Architecture:** One shared rules module (`tools/governance_rules.py`) holds every pattern, heading list and limit. The repo checker (`tools/governance_check.py`) and three Claude Code hook scripts (`.claude/hooks/`) import it, so a rule lives in one place. GitHub Actions runs the checker and its tests on every push and pull request.

**Tech Stack:** Python 3.12+ standard library only (no installs), `unittest`, GitHub Actions, Claude Code hooks (`.claude/settings.json`).

**Spec:** `docs/superpowers/specs/2026-11-16-governance-design.md`

## Global Constraints

- Python standard library only; must run on Python 3.12 and 3.13.
- Size limit: 50 MB per file (`MAX_FILE_BYTES = 50 * 1024 * 1024`).
- Placeholder that marks an unfinished record: `_TBD_`.
- Journal path: `logs/sessions/YYYY-MM-DD-<first 8 chars of session id>.md`, date = session start date.
- Raw data files are never moved or renamed; `data/` stays where it is.
- Every hook command in settings uses `python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/<name>.py"`.
- Hooks must never crash a session: any unexpected exception → print nothing, exit 0.
- Checker messages are plain English, one line each, starting with the file path.

## Review Focus

1. **Raw data changed through the shell** (e.g. `sed -i … data/x.csv`, `> data/x.csv`, `rm data/x.csv`) instead of the edit tool → guard hook denies; SHA-256 check in CI catches anything that slips through. Test in Task 4 and Task 2.
2. **Stop hook loops forever** when the agent keeps failing to write the journal → when `stop_hook_active` is true, allow the stop. Test in Task 4.
3. **Read-only session** (questions only, no file changes) → no journal demanded. Test in Task 4.
4. **Path spellings** — absolute paths, `./data/…`, and `data/SOURCES.md` (which IS editable) → guard treats them correctly. Test in Task 4.
5. **Records saved with Windows line endings or trailing spaces after headings** → still recognised. Test in Task 3.

---

### Task 1: Shared rules + layout, naming and size checks

**Files:**
- Create: `tools/governance_rules.py`, `tools/governance_check.py`, `tests/test_governance_check.py`, `tests/__init__.py` (empty)

**Interfaces:**
- Produces in `governance_rules.py`:
  - `ALLOWED_TOP_LEVEL: set[str]` — the 14 entries from spec §2 Article 3
  - `FOLDER_RULES: dict[str, re.Pattern]` — `"data"`: `^(.+\.csv|SOURCES\.md|\.gitkeep)$`; `"sql"`: `^(\d{2}_[a-z0-9_]+\.sql|\.gitkeep)$`; `"powerbi"`: `^([a-z0-9_]+\.pbix|\.gitkeep)$`; `"screenshots"`: `^([a-z0-9-]+\.(png|jpg)|\.gitkeep)$`
  - `MAX_FILE_BYTES: int`, `PLACEHOLDER = "_TBD_"`
  - `SKIP_DIRS = {".git", ".claude/state"}` (relative paths never walked)
  - `iter_files(root: Path) -> list[Path]` — repo-relative paths, sorted, skipping `SKIP_DIRS`
- Produces in `governance_check.py`:
  - `check_layout(root: Path) -> list[str]`
  - `check_sizes(root: Path) -> list[str]`
  - `check_repo(root: Path) -> list[str]` — concatenates every `check_*` (later tasks add theirs here)
  - `main(argv: list[str] | None = None) -> int` — root = `argv[0]` or repo root (parent of `tools/`); prints each problem, then `"OK: no governance problems"` or `"FAILED: N problem(s)"`; returns 0/1. `if __name__ == "__main__": sys.exit(main())`
- Tests import with `sys.path.insert(0, <repo>/tools)`.

- [ ] **Step 1: Write failing tests** in `tests/test_governance_check.py`, each building a temp repo with `tempfile.TemporaryDirectory()`:
  - `test_clean_repo_passes`: `README.md`, `sql/01_load_zhvi.sql`, `data/x.csv` → `check_layout == []`
  - `test_unknown_top_level_flagged`: `notes.txt` → one message containing `"notes.txt"`
  - `test_bad_sql_name_flagged`: `sql/LoadData.sql` → one message containing `"sql/LoadData.sql"`
  - `test_wrong_type_in_screenshots_flagged`: `screenshots/chart.gif` → flagged
  - `test_nested_file_in_ruled_folder_flagged`: `sql/old/01_a.sql` → flagged (ruled folders are flat)
  - `test_oversize_file_flagged`: patch `governance_rules.MAX_FILE_BYTES = 10`, 11-byte file → `check_sizes` has one message
  - `test_git_dir_ignored`: `.git/whatever` → no messages
  - `test_main_returns_1_on_problem_and_0_when_clean`
- [ ] **Step 2:** `cd /home/user/us-housing-market-analysis && python3 -m unittest discover -s tests -v` → FAIL (module not found).
- [ ] **Step 3:** Implement the interfaces above.
- [ ] **Step 4:** Same command → all PASS. Then `python3 tools/governance_check.py` on the real repo → `OK: no governance problems` (the existing CSVs, `.gitkeep` files and `docs/` are all allowed).
- [ ] **Step 5:** Commit `feat: add governance rules and layout/size checker`.

### Task 2: Data manifest and raw-file fingerprints

**Files:**
- Create: `data/SOURCES.md`
- Modify: `tools/governance_rules.py`, `tools/governance_check.py`, `tests/test_governance_check.py`

**Interfaces:**
- Consumes: `iter_files`, `check_repo` from Task 1.
- Produces:
  - `governance_rules.parse_sources(text: str) -> dict[str, str]` — filename → sha256, read from the markdown table whose header is exactly `| File | Source | URL | Added | SHA-256 |`; ignores the separator row; strips backticks and spaces in cells.
  - `governance_check.check_data_manifest(root: Path) -> list[str]` — flags: `data/SOURCES.md` missing; a `data/*.csv` with no row; a row whose file is missing; a fingerprint mismatch (message contains `"changed"` and tells the reader raw data must not be edited). Hash with `hashlib.sha256` in 1 MB chunks. Added to `check_repo`.

- [ ] **Step 1: Failing tests:** `test_csv_without_row_flagged`, `test_row_without_file_flagged`, `test_hash_mismatch_flagged` (asserts `"changed"` in message), `test_matching_manifest_passes`, `test_missing_manifest_flagged_only_when_csv_present`.
- [ ] **Step 2:** Run tests → new ones FAIL.
- [ ] **Step 3:** Implement. Write `data/SOURCES.md`: one-line intro ("Raw files exactly as downloaded. Never edit them; see CONSTITUTION.md Article 2.") then the table with these rows:

| File | Source | URL | Added | SHA-256 |
|---|---|---|---|---|
| `Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv` | Zillow Research — ZHVI, metro, monthly, smoothed & seasonally adjusted | https://www.zillow.com/research/data/ | 2026-10-19 | `f921b1a98ae8b14a58c50a8be28c2dbe1bc141af8b6afcf88acb5f0ebff3b8e7` |
| `Metro_zori_uc_sfrcondomfr_sm_month.csv` | Zillow Research — ZORI, metro, monthly, smoothed | https://www.zillow.com/research/data/ | 2026-10-19 | `1397d89685ad547c94771e6527fb58c5ff057e1c6c3c57b4637ff98de1f45c5a` |

- [ ] **Step 4:** Tests PASS; `python3 tools/governance_check.py` reports no data problems.
- [ ] **Step 5:** Commit `feat: add data source manifest with fingerprint check`.

### Task 3: Record templates and record-format checks

**Files:**
- Create: `docs/templates/decision.md`, `docs/templates/bug-log.md`, `docs/templates/test-log.md`, `docs/templates/session-journal.md`, `logs/sessions/.gitkeep`, `logs/bugs/.gitkeep`, `logs/tests/.gitkeep`, `docs/decisions/.gitkeep`
- Modify: `tools/governance_rules.py`, `tools/governance_check.py`, `tests/test_governance_check.py`

**Interfaces:**
- Produces in `governance_rules.py`:
  - `RECORD_TYPES: dict[str, tuple[re.Pattern, list[str]]]` keyed by folder:
    - `"logs/sessions"`: `^\d{4}-\d{2}-\d{2}-[0-9a-zA-Z]{8}\.md$`, `["Goal", "What changed", "Tests run", "Bugs found", "Next steps"]`
    - `"logs/bugs"`: `^BUG-\d{3}-[a-z0-9-]+\.md$`, `["Status", "Found", "What happened", "Cause", "Fix", "Test log"]`
    - `"logs/tests"`: `^\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$`, `["What was tested", "How", "Result", "Bugs"]`
    - `"docs/decisions"`: `^\d{4}-[a-z0-9-]+\.md$`, `["Date", "Status", "Decision", "Reason", "Alternatives"]`
  - `ALLOWED_VALUES = {("logs/bugs", "Status"): {"Open", "Fixed"}, ("logs/tests", "Result"): {"PASS", "FAIL"}, ("docs/decisions", "Status"): {"Proposed", "Accepted", "Replaced"}}` — first non-empty line under that heading must be one of these.
  - `record_problems(folder: str, filename: str, text: str) -> list[str]` — bad name, missing heading, empty section, `_TBD_` present, value not allowed. Normalise `\r\n` → `\n`; match headings as `## <name>` after `rstrip()`.
- Produces in `governance_check.py`: `check_records(root: Path) -> list[str]` — runs `record_problems` on every file in each record folder except `.gitkeep`; added to `check_repo`. Also add `"logs"` and `"docs/decisions"` handling so files directly in `logs/` (not in a sub-folder) are flagged.
- Templates: each has the required `## ` headings with `_TBD_` under each, plus a one-line comment at top giving the file-name pattern. Templates live outside record folders, so they are not checked.

- [ ] **Step 1: Failing tests:** `test_valid_record_of_each_type_passes` (loop over the four types), `test_missing_heading_flagged`, `test_tbd_flagged`, `test_bad_record_name_flagged`, `test_bug_status_must_be_open_or_fixed`, `test_crlf_and_trailing_spaces_accepted` (Review Focus 5), `test_templates_folder_not_checked`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement + create templates and `.gitkeep` files.
- [ ] **Step 4:** Tests PASS; real-repo checker clean.
- [ ] **Step 5:** Commit `feat: add record templates and format checks`.

### Task 4: Claude Code hooks

**Files:**
- Create: `.claude/hooks/hooklib.py`, `.claude/hooks/session_start.py`, `.claude/hooks/guard.py`, `.claude/hooks/stop_journal.py`, `.claude/settings.json`, `.gitignore`, `tests/test_hooks.py`

**Interfaces:**
- Consumes: `RECORD_TYPES`, `record_problems`, `PLACEHOLDER` from `tools/governance_rules.py` (`hooklib` inserts `<project>/tools` into `sys.path`).
- Produces in `hooklib.py`:
  - `state_path(project: Path, session_id: str) -> Path` → `project/.claude/state/<session_id>.json`
  - `journal_path(project: Path, date: str, session_id: str) -> Path` → `project/logs/sessions/<date>-<session_id[:8]>.md`
  - `run(handler)` — reads JSON from stdin, calls `handler(payload, project)` (project = `$CLAUDE_PROJECT_DIR` or `payload["cwd"]`), prints returned dict as JSON if not `None`, swallows every exception, exits 0.
- `session_start.decide(payload: dict, project: Path) -> dict` — writes state `{"date": today ISO, "head": <git rev-parse HEAD or "">}` (only if no state file exists yet, so resume keeps the original date); returns `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <text>}}`. Text: read `CONSTITUTION.md` before working; your journal is `<relative journal path>`, copy `docs/templates/session-journal.md`; log bugs in `logs/bugs/`, tests in `logs/tests/`.
- `guard.decide(payload: dict, project: Path) -> dict | None`:
  - Tools `Edit`, `Write`, `MultiEdit`, `NotebookEdit`: resolve `tool_input["file_path"]` (or `notebook_path`) against project. If it is `data/<name>.csv` → `deny`, reason: raw data is read-only (Article 2), ask the owner. If it is `CONSTITUTION.md` → `ask`, reason: only the owner may amend (Article 6). Else `None`.
  - Tool `Bash`: if `tool_input["command"]` contains a `data/…csv` reference AND any of `rm `, `mv `, `sed -i`, `>`, `truncate`, `tee `, `cp ` with the csv as destination-looking last argument (keep it a simple regex, err on denying) → `deny`. Reading commands (`head`, `cat`, `wc`, `sha256sum`) without those tokens → `None`.
  - Output shape: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny"|"ask", "permissionDecisionReason": str}}`.
- `stop_journal.decide(payload: dict, project: Path) -> dict | None`:
  - `payload.get("stop_hook_active")` true → `None` (Review Focus 2).
  - Load state (missing → date = today, head = "").
  - Changed = `git status --porcelain` non-empty, ignoring `.claude/state/` and the journal file itself, OR current HEAD ≠ state head (when head known).
  - Not changed → `None` (Review Focus 3).
  - Changed and journal missing or `record_problems("logs/sessions", name, text)` non-empty → `{"decision": "block", "reason": <path + list of problems + "copy docs/templates/session-journal.md">}`. Else `None`.
- `.claude/settings.json`: `SessionStart` (no matcher) → session_start; `PreToolUse` matcher `Edit|Write|MultiEdit|NotebookEdit|Bash` → guard; `Stop` → stop_journal. Each `{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/<name>.py\""}`.
- `.gitignore`: `.claude/state/`, `__pycache__/`.

- [ ] **Step 1: Failing tests** in `tests/test_hooks.py` (load modules with `importlib.util.spec_from_file_location`; temp git repos via `git init` + one commit):
  - `test_session_start_writes_state_and_names_journal`
  - `test_session_start_keeps_existing_date`
  - `test_guard_denies_edit_of_raw_csv`, `test_guard_denies_absolute_and_dot_slash_paths` (Review Focus 4)
  - `test_guard_allows_sources_md`, `test_guard_allows_sql_file`
  - `test_guard_asks_for_constitution`
  - `test_guard_denies_bash_sed_i_redirect_rm_on_csv` (three commands, Review Focus 1)
  - `test_guard_allows_bash_head_on_csv`
  - `test_stop_allows_when_nothing_changed`
  - `test_stop_blocks_when_changed_and_no_journal`
  - `test_stop_blocks_when_journal_has_tbd`
  - `test_stop_allows_with_complete_journal`
  - `test_stop_allows_when_stop_hook_active`
  - `test_stop_detects_committed_change` (new commit, clean tree, no journal → block)
  - `test_hook_script_survives_garbage_stdin` (subprocess, stdin `"not json"` → exit 0, empty stdout)
- [ ] **Step 2:** `python3 -m unittest discover -s tests -v` → new tests FAIL.
- [ ] **Step 3:** Implement scripts, settings, `.gitignore`.
- [ ] **Step 4:** All tests PASS. Also pipe a sample payload into each script by hand and check the JSON printed, e.g. `cd /home/user/us-housing-market-analysis && echo '{"tool_name":"Write","tool_input":{"file_path":"data/x.csv"}}' | python3 .claude/hooks/guard.py` → prints a `deny` decision.
- [ ] **Step 5:** Commit `feat: add Claude Code hooks enforcing journal and data rules`.

### Task 5: Constitution, agent briefing, first decision, CI

**Files:**
- Create: `CONSTITUTION.md`, `CLAUDE.md`, `docs/decisions/0001-adopt-governance-system.md`, `.github/workflows/governance.yml`, `logs/sessions/<date>-<id8>.md` (this session's journal)
- Modify: `README.md` (add Governance section + new folders in Repo structure)

**Interfaces:**
- Consumes: everything above; checker must pass on the final tree.

- [ ] **Step 1:** Write `CONSTITUTION.md` with the six articles of spec §2 in plain language, numbered rules under each, Article 4 linking to the templates and naming table (spec §3), and a footer "Version 1.0 — adopted <date> — amendments recorded in docs/decisions/". No rules beyond the spec.
- [ ] **Step 2:** Write `CLAUDE.md` (≤40 lines): read `CONSTITUTION.md` first; the agent duties of spec §4; how to run the checker (`python3 tools/governance_check.py`) and tests (`python3 -m unittest discover -s tests`); never edit `data/*.csv`; ask the owner before sending, publishing, deleting, spending, or changing architecture or the constitution.
- [ ] **Step 3:** Write decision `0001-adopt-governance-system.md` (Status `Accepted`, Reason and Alternatives drawn from the owner's choices: AI + owner governed, written rules + auto-checks, branch lock not chosen).
- [ ] **Step 4:** Write `.github/workflows/governance.yml`: name `Governance checks`; on `push` and `pull_request`; one job on `ubuntu-latest`: `actions/checkout@v4`, `actions/setup-python@v5` with `python-version: "3.12"`, run `python tools/governance_check.py`, run `python -m unittest discover -s tests -v`.
- [ ] **Step 5:** Update README: "## Governance" section (3–4 lines pointing to `CONSTITUTION.md`, `CLAUDE.md`, the logs and the checker) and add `/docs`, `/logs`, `/tools`, `/tests` to Repo structure.
- [ ] **Step 6:** Write this session's journal from the template; run `cd /home/user/us-housing-market-analysis && python3 tools/governance_check.py && python3 -m unittest discover -s tests` → `OK: no governance problems` and all tests OK.
- [ ] **Step 7:** Commit `docs: add constitution, agent briefing, decision 0001 and CI`, push to `claude/determined-goodall-hyfv3b`, confirm the GitHub Actions run is green.
