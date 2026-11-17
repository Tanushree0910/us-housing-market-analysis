# Governance Minor Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the nine minor findings from the final review of the governance branch before it merges (PR Tanushree0910/us-housing-market-analysis#1).

**Architecture:** Same structure as the original build. Rules stay in `tools/governance_rules.py`; checker in `tools/governance_check.py`; hooks in `.claude/hooks/`. No new top-level items, no constitution amendment.

**Tech Stack:** Python 3.12+ standard library, `unittest`, GitHub Actions, Claude Code hooks.

**Spec:** `docs/superpowers/specs/2026-11-16-governance-design.md` (unchanged). The nine findings below are the requirements for this plan.

| # | Finding | Task |
|---|---|---|
| M1 | Guard over-blocks: `> results/data/out.csv`, heredoc text or quoted text that mentions a write | 1 |
| M2 | Upper-case `.CSV` not handled by the shell guard or the checker | 1, 2 |
| M3 | `CLAUDE.md` tells agents to add raw files, which the guard blocks | 4 |
| M4 | Malformed `data/SOURCES.md` rows are skipped silently | 2 |
| M5 | A UTF-8 BOM before a first-line heading makes that section look missing | 2 |
| M6 | Local checker flags clutter (`.DS_Store`, `.vscode/`) that never reaches GitHub | 2 |
| M7 | Guard compares paths without resolving symlinks | 1 |
| M8 | Workflow runs twice on same-repo PRs and has no read-only permissions | 4 |
| M9 | Stop hook enforces the journal for one retry only | 3 |

## Global Constraints

- Python standard library only; Python 3.12 and 3.13.
- Hooks never crash a session: any exception → no output, exit 0.
- Raw data path rule: a path is raw data when, resolved against the project, it is exactly `data/<name>` with `<name>` ending in `.csv` in any letter case.
- Stop hook retry limit: `MAX_JOURNAL_BLOCKS = 3`.
- Test command: `cd /home/user/us-housing-market-analysis && python3 -m unittest discover -s tests -t .`

## Review Focus

1. **Command that writes a non-raw file whose path contains `data/`** (e.g. `> exports/metadata/x.csv`, `> data/derived/x.csv`) → allowed. Test in Task 1.
2. **Repo is not a git checkout** (zip download) → checker falls back to walking folders and still works. Test in Task 2.
3. **Stop hook with no state file and repeated blocks** → counter still stored and limit still applies. Test in Task 3.
4. **Header row in SOURCES.md with different spacing or capitalisation** (`| file | source |…`, `SHA256`) → reported clearly, not silently empty. Test in Task 2.
5. **Agent writes a heredoc script that itself writes to `data/x.csv`** → allowed at the shell-text level (CI fingerprint is the backstop). Test in Task 1.

---

### Task 1: Guard accuracy (M1, M2 shell part, M7)

**Files:**
- Modify: `.claude/hooks/guard.py`, `tests/test_hooks.py`

**Interfaces:**
- Produces: `guard.is_raw_data(project: Path, path_text: str) -> bool`. Resolves `path_text` against `project` with `Path.resolve(strict=False)` for both sides; true when the result relative to the project is two parts, first `data`, second ending `.csv` case-insensitively.
- `_check_bash(project: Path, command: str)` (gains `project`). Before splitting, remove heredoc bodies: text after a `<<WORD` / `<<'WORD'` / `<<-WORD` line up to the line equal to `WORD`. Tokenise each segment with `shlex.shlex(segment, posix=True, punctuation_chars=True)` so `>`, `>>`, `|` and `;` are their own tokens and quoted text stays one token. A redirect is a write only when the token after `>` / `>>` passes `is_raw_data`. Every existing write rule (rm, mv, sed -i, curl -o, dd of=, etc.) uses `is_raw_data` instead of `CSV_TOKEN`; `CSV_TOKEN` and `REDIRECT_TO_CSV` are removed.
- `_check_edit` uses `is_raw_data` too.

- [ ] **Step 1: Failing tests:**
  - `test_guard_allows_redirect_to_other_data_paths`: `grep x f > results/data/out.csv`, `echo 1 > exports/metadata/x.csv`, `echo 1 > data/derived/x.csv` → `None`
  - `test_guard_allows_quoted_mentions`: `echo 'a > data/x.csv'`, `git commit -m "rm data/a.csv"` → `None`
  - `test_guard_allows_heredoc_body_mentions`: `cat > /tmp/s.sh <<'EOF'\nrm data/a.csv\nEOF` → `None`; `cat > data/a.csv <<'EOF'\nx\nEOF` → `deny`
  - `test_guard_denies_uppercase_csv`: `truncate -s0 data/X.CSV` and Edit of `data/X.CSV` → `deny`
  - `test_guard_resolves_symlinked_project`: temp dir with a symlink `link -> real`; project = `link`, Edit `file_path` = `real/data/a.csv` → `deny`
  - All existing guard tests keep passing unchanged.
- [ ] **Step 2:** Run test command → new tests FAIL.
- [ ] **Step 3:** Implement as above.
- [ ] **Step 4:** Test command → all PASS.
- [ ] **Step 5:** Commit `fix: make the raw-data guard precise about which paths it blocks`.

### Task 2: Checker accuracy (M2 checker part, M4, M5, M6)

**Files:**
- Modify: `tools/governance_rules.py`, `tools/governance_check.py`, `tests/test_governance_check.py`, `.gitignore`

**Interfaces:**
- `FOLDER_RULES["data"]` matches `.csv` in any case. `check_data_manifest` selects CSVs with `rel.suffix.lower() == ".csv"`.
- `strip_bom(text: str) -> str` in `governance_rules.py`; applied at the start of `parse_sources` and `record_problems`.
- `sources_problems(text: str) -> list[str]` in `governance_rules.py`: reports (a) no header row exactly matching `SOURCES_HEADER` after trimming cells — message names the expected header; (b) a table row with a cell count other than 5 — message quotes the file cell; (c) a SHA-256 cell that is not 64 hex characters. `check_data_manifest` prefixes each with `data/SOURCES.md: ` and adds them to its output.
- `iter_files(root)`: when `root/.git` exists, list `git ls-files --cached --others --exclude-standard -z` (run in `root`), keeping only paths that exist on disk; otherwise the current folder walk. `SKIP_DIRS` / `SKIP_DIR_NAMES` still apply to both.
- `.gitignore` gains: `.DS_Store`, `Thumbs.db`, `desktop.ini`, `.vscode/`, `.idea/`, `.venv/`, `~$*`.

- [ ] **Step 1: Failing tests:**
  - `test_uppercase_csv_is_raw_data`: `data/A.CSV` not in manifest → "not listed"; in manifest with right hash → no problems; layout allows it
  - `test_bom_before_first_heading_accepted`: session journal text starting `"﻿## Goal\n…"` → `record_problems == []`
  - `test_bom_in_sources_accepted`
  - `test_sources_wrong_header_reported`: header `| file | source | url | added | SHA256 |` → one problem mentioning `SHA-256`
  - `test_sources_wrong_cell_count_reported`: row with 6 cells (URL containing `|`) → problem quoting the file name
  - `test_sources_bad_hash_reported`: hash `abc` → problem
  - `test_git_repo_ignores_gitignored_clutter`: `git init`, `.gitignore` with `.DS_Store`, file `.DS_Store` → `check_layout == []`; untracked `notes.txt` → still flagged
  - `test_non_git_folder_still_walked` (Review Focus 2): plain temp dir with `notes.txt` → flagged
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Test command → PASS; `python3 tools/governance_check.py` → `OK: no governance problems`.
- [ ] **Step 5:** Commit `fix: make the checker clearer about data sources and skip ignored files`.

### Task 3: Stop hook retries (M9)

**Files:**
- Modify: `.claude/hooks/stop_journal.py`, `.claude/hooks/hooklib.py`, `tests/test_hooks.py`

**Interfaces:**
- `hooklib.save_state(project: Path, session_id: str, state: dict) -> None` (creates the folder).
- `stop_journal.MAX_JOURNAL_BLOCKS = 3`.
- `decide` no longer returns early on `stop_hook_active`. Instead: when the journal is incomplete, read `state.get("journal_blocks", 0)`. Below the limit → increment, save, return the block. At the limit → return `{"systemMessage": "Session ended without a complete journal: <journal path>. Please ask the agent to finish it."}` (no block, so the session ends and the owner is told). When the journal is complete or nothing changed → reset `journal_blocks` to 0 and return `None`.

- [ ] **Step 1: Failing tests:**
  - `test_stop_blocks_up_to_limit_then_warns`: changed repo, no journal, `stop_hook_active=True` on calls 2–4 → calls 1–3 block, call 4 returns a dict with `systemMessage` and no `decision`
  - `test_stop_counter_resets_after_journal_completed`
  - `test_stop_limit_applies_without_state_file` (Review Focus 3)
  - Replace `test_stop_allows_when_stop_hook_active` with the first test above.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Test command → PASS.
- [ ] **Step 5:** Commit `fix: stop hook retries the journal up to three times, then tells the owner`.

### Task 4: Briefing, workflow, records (M3, M8)

**Files:**
- Modify: `CLAUDE.md`, `.github/workflows/governance.yml`, `tests/test_hooks.py`
- Create: `logs/tests/2026-11-17-governance-minor-fixes.md`
- Modify: this session's journal `logs/sessions/2026-11-17-d5488c8e.md`

**Interfaces:** none new.

- [ ] **Step 1: Failing test** `test_workflow_runs_once_and_read_only` (parse the YAML as text): `push:` is followed by `branches: [main]`, and the file contains `permissions:` then `contents: read`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Workflow: `on: push: branches: [main]` plus `pull_request:`; top-level `permissions: contents: read`. In `CLAUDE.md`, replace the "Adding a raw data file" section with: adding or replacing raw data is the owner's job; if new data is needed, ask the owner to put the file in `data/` under its original name. Then the agent adds the `data/SOURCES.md` row, getting the fingerprint with `sha256sum data/<file>`.
- [ ] **Step 4:** Test command → PASS; checker OK. Write the test log and update the journal (what changed, tests run).
- [ ] **Step 5:** Commit `docs: clarify raw data ownership and tighten the CI workflow`; push; confirm the PR's "Governance checks" run is green.
