# Branch, GitHub and Agent Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:**
- Protect `main` on GitHub and locally.
- Confine agents to worktrees.
- Block or ask about dangerous commands, and make merges ask.
- Govern helper-agent models.
- Brief agents at session start and check their work at session end.

**Architecture:**
- Two new PreToolUse hooks:
  - `git_guard.py`: branches, worktrees, dangerous commands, merges, GitHub writes.
  - `agent_guard.py`: helper models.
- These share a new shell parser `shellparse.py`, extracted from `guard.py`.
- `session_start.py` is extended.
- `stop_journal.py` becomes `session_end.py` with more checks.
- The GitHub ruleset is a JSON file the owner imports.

**Tech Stack:** Python 3.12+ stdlib, `unittest`, Claude Code hooks, GitHub rulesets.

**Spec:** `docs/superpowers/specs/2026-11-18-branch-and-agent-governance-design.md`

## Global Constraints

- Hooks fail open: any exception → no output, exit 0 (`hooklib.run`).
- Main-protected branch names: `{"main", "master"}`.
- Agent worktrees live at `<main checkout>/.worktrees/<name>/`.
- Main checkout = parent of `git rev-parse --path-format=absolute --git-common-dir`, run in the hook's project dir.
- Allowed helper models: anything except names containing `fable` (case-insensitive). The model must be given explicitly. Forks are blocked.
- Deny/ask reasons are plain English, name the constitution article, and include the exact fix command starting with `cd` to the full folder path.
- Test command (run inside the worktree): `python3 -m unittest discover -s tests -t .`

## Review Focus

1. **Session running from inside a worktree:** `CLAUDE_PROJECT_DIR` is the worktree, not the main checkout. The worktree must still be recognised as a worktree, and its files must stay editable. Test in Task 2.
2. **Raw data and the constitution inside a worktree:** `.worktrees/x/data/a.csv` and `.worktrees/x/CONSTITUTION.md` must get the same deny/ask as in the main checkout. Test in Task 1.
3. **Ordinary git work in a worktree:** `git commit`, `git push -u origin feature`, `git fetch`, `git status` must never be blocked. Test in Task 2.
4. **`cd` into a worktree inside one command:** `cd .worktrees/x && git commit -m y` is judged by the worktree, not by the main checkout. Test in Task 2.
5. **Helper call that names no model:** denied, with a message saying how to name one. Test in Task 3.

---

### Task 1: Shared shell parser and worktree-aware raw-data guard

**Files:**
- Create: `.claude/hooks/shellparse.py`
- Modify: `.claude/hooks/guard.py`, `.claude/hooks/hooklib.py`, `tests/test_hooks.py`

**Interfaces:**
- Produces in `shellparse.py`, moved from `guard.py` with no change in behaviour:
  - `tokens(line) -> list[str]`
  - `command_lines(command) -> list[list[str]]`
  - `segments(tokens) -> list[list[str]]`
  - `strip_prefixes(words) -> list[str]`
  - `absolute(base: Path, path_text: str, cwd: Path | None) -> Path`
  - `iter_commands(project: Path, command: str, start_cwd: Path | None) -> Iterator[tuple[list[str], list[str], Path | None]]`. It yields `(segment_tokens, words_after_prefixes, cwd)` and applies `cd` tracking. `cd` segments are consumed, not yielded.
- Produces in `hooklib.py`:
  - `main_checkout(project: Path) -> Path` (falls back to `project` when git fails).
  - `repo_relative(project: Path, path: Path) -> Path | None`. The path relative to the main checkout, with a leading `.worktrees/<name>/` removed. `None` when outside.
- `guard.is_raw_data` and the constitution check use `repo_relative`.

- [ ] **Step 1: Failing tests** (in `tests/test_hooks.py`, using a real git repo with a worktree, via a new helper `make_repo_with_worktree() -> tuple[TempRepo, Path]` in `tests/helpers.py`):
  - `test_guard_denies_raw_csv_inside_worktree`: Edit `.worktrees/w/data/a.csv` → deny
  - `test_guard_asks_for_constitution_inside_worktree` → ask
  - `test_guard_allows_worktree_sql`: Edit `.worktrees/w/sql/01_a.sql` → None
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. Existing guard tests must pass unchanged.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `refactor: share shell parsing and make the data guard worktree-aware`.

### Task 2: `git_guard.py` (worktrees, main protection, dangerous commands, merges, GitHub writes)

**Files:**
- Create: `.claude/hooks/git_guard.py`, `tests/test_git_guard.py`

**Interfaces:**
- Consumes: `shellparse.iter_commands`, `hooklib.main_checkout`.
- Produces: `git_guard.decide(payload, project) -> dict | None`, with the same output shape as `guard.decide`.
- Edit tools:
  - Allowed when the target is outside the main checkout, or inside `.worktrees/<name>/` whose branch is not main/master.
  - Otherwise deny. The reason gives `cd <main> && git worktree add .worktrees/<name> -b <branch> origin/main`.
- Bash, per command, with `dir` = tracked cwd (or `git -C` path):
  - **Deny (Article 7):**
    - `rm` with a recursive flag on `/`, `~`, `$HOME`, the main checkout, any ancestor of it, a `.git`, or `*`/`.` when `dir` is the main checkout;
    - `git push` with `-f`, `--force`, `--force-with-lease`, `--force-if-includes` or a `+` refspec;
    - `git filter-branch`, `git filter-repo`, `git reflog expire`;
    - `mkfs*`; `dd` with `of=/dev/…`; a redirect into `/dev/sd*` or `/dev/nvme*`;
    - `curl`/`wget` piped into `sh`/`bash`/`zsh`/`python*`;
    - `gh repo delete`; `chmod -R 777`; the fork-bomb text `:(){`.
  - **Deny (Article 5, protect main):**
    - `git push` whose refspec targets main/master (`main`, `HEAD:main`, `:main`, `+main`, `refs/heads/main`), or uses `--all`/`--mirror`;
    - `git push --delete main`;
    - `git branch -d/-D/-m/-M main|master`;
    - `git update-ref refs/heads/main|master`;
    - a no-refspec `git push` while `dir`'s branch is main/master.
  - **Deny (Article 5, worktrees only):** `git commit|merge|rebase|cherry-pick|revert|am|reset|push` when `dir` is the main checkout, or its branch is main/master.
  - **Ask (Article 7):**
    - `git reset --hard`, `git clean` with `-f`;
    - `git branch -D <other>`;
    - `git checkout -- <path>`, `git checkout .`, `git restore` without `--staged`;
    - `git stash drop|clear`;
    - `git worktree remove -f|--force`;
    - `rm` with a recursive flag on anything else.
  - **Ask (Article 5, merging):** `git merge`, `gh pr merge`.
- MCP tools:
  - `mcp__github__merge_pull_request`, `mcp__github__enable_pr_auto_merge` → ask.
  - `mcp__github__create_or_update_file`, `push_files`, `delete_file` with `branch` main/master → deny.
- Order: the first deny wins; otherwise the first ask.

- [ ] **Step 1: Failing tests** in `tests/test_git_guard.py` (real repo plus worktree from `make_repo_with_worktree`; branch names `main` and `feature`):
  - `test_edit_in_main_checkout_denied_with_worktree_command` (asserts `"git worktree add"` in reason)
  - `test_edit_in_feature_worktree_allowed`
  - `test_edit_in_worktree_on_main_denied`
  - `test_edit_outside_project_allowed` (e.g. `/tmp/x.txt`)
  - `test_session_inside_worktree_can_edit` (project = the worktree path, Review Focus 1)
  - `test_commit_in_main_checkout_denied`, `test_commit_in_feature_worktree_allowed`
  - `test_cd_into_worktree_then_commit_allowed` (Review Focus 4)
  - `test_ordinary_git_in_worktree_never_blocked`: `git status`, `git fetch origin`, `git push -u origin feature`, `git log`, `git diff`, `git worktree add .worktrees/n -b n` from the main checkout (Review Focus 3)
  - `test_push_to_main_denied`: five refspec forms plus `--all`
  - `test_force_push_denied`: four forms
  - `test_delete_or_rename_main_denied`
  - `test_dangerous_commands_denied`: one line per deny item above
  - `test_risky_commands_ask`: one line per ask item above
  - `test_merge_commands_ask`: `git merge feature` (in a worktree), `gh pr merge 1`, the MCP merge and auto-merge tools
  - `test_github_mcp_write_to_main_denied_and_feature_allowed`
  - `test_rm_inside_worktree_of_single_file_allowed`: `rm .worktrees/w/sql/old.sql` → None
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: add git guard for worktrees, main protection and dangerous commands`.

### Task 3: `agent_guard.py` (helper models)

**Files:**
- Create: `.claude/hooks/agent_guard.py`, `tests/test_agent_guard.py`

**Interfaces:**
- Produces: `agent_guard.decide(payload, project) -> dict | None`.
  - For `Agent`/`Task`:
    - `subagent_type == "fork"` → deny;
    - missing or empty `model` → deny ("name the model: sonnet, opus or haiku");
    - a model containing `fable` → deny.
  - `mcp__claude-code-remote__create_session`: missing model or fable → deny.
  - All reasons cite Article 8.

- [ ] **Step 1: Failing tests:**
  - `test_named_models_allowed` (sonnet, opus, haiku, `claude-sonnet-5-5`)
  - `test_fable_denied` (`fable`, `claude-fable-5-2`, `Fable`)
  - `test_missing_model_denied` (Review Focus 5)
  - `test_fork_denied`
  - `test_remote_session_rules`
  - `test_other_tools_ignored`
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: add helper-agent model guard`.

### Task 4: Session start briefing and session end checks

**Files:**
- Modify: `.claude/hooks/session_start.py`, `.claude/hooks/hooklib.py`, `tests/test_hooks.py`
- Rename: `.claude/hooks/stop_journal.py` → `.claude/hooks/session_end.py`
- Create: `tests/test_session_hooks.py` (session start and end tests move here from `test_hooks.py`)

**Interfaces:**
- `hooklib.worktrees(main: Path) -> dict[str, dict]`: path → `{"branch": str, "head": str}`, from `git worktree list --porcelain`.
- State gains `"worktrees"` (that map at session start). `"status"` and `"head"` stay as they are for the main checkout.
- `session_start.decide` context adds, in order:
  - **Status:** the main checkout's branch; a `WARNING` line if any worktree or the main checkout is on main/master; the worktree list; whether the main checkout has uncommitted changes.
  - **Before editing:** the `cd … && git worktree add …` command.
  - **Essential skills:** the eight names from spec §6, with "invoke when they apply".
  - **Owner rules:** `cd` commands, never asking for files already reachable, merge only on request, helper models.
- `session_end.decide`, with retry behaviour unchanged (`MAX_JOURNAL_BLOCKS = 3`, reset per turn):
  - A worktree is changed when it is new since the start, its status is non-empty, or its HEAD differs from the start.
  - The main checkout is changed by the existing rule.
  - Problems, collected over all changed places:
    1. uncommitted changes (ignoring `.claude/state/`);
    2. commits not pushed (`git rev-list --count HEAD --not --remotes` > 0, branches only);
    3. `governance_check.check_repo(worktree)` problems;
    4. the session journal at `logs/sessions/<date>-<id8>.md` missing or incomplete in every changed place.
  - Any problem → block, listing all of them.
- `.claude/settings.json`:
  - PreToolUse:
    - `Edit|Write|MultiEdit|NotebookEdit|Bash` → `guard`, `git_guard`;
    - `mcp__github__.*` → `git_guard`;
    - `Agent|Task|mcp__claude-code-remote__create_session` → `agent_guard`.
  - Stop → `session_end`.
  - Same `python3 … || python …` command form.

- [ ] **Step 1: Failing tests** in `tests/test_session_hooks.py`:
  - `test_start_warns_on_main`
  - `test_start_lists_worktrees_and_skills`
  - `test_start_includes_owner_rules`
  - `test_end_blocks_uncommitted_worktree_changes`
  - `test_end_blocks_unpushed_commits` (bare repo as origin)
  - `test_end_blocks_checker_problems_in_worktree`
  - `test_end_accepts_journal_in_worktree`
  - `test_end_allows_clean_pushed_documented_worktree`
  - `test_end_ignores_untouched_preexisting_worktree`
  - existing stop tests moved and still passing
  - `test_settings_wire_all_hooks`
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat: brief agents at session start and check their work at session end`.

### Task 5: GitHub files, constitution v1.1, docs and records

**Files:**
- Create:
  - `.github/rulesets/protect-main.json`
  - `.github/CODEOWNERS`
  - `.github/pull_request_template.md`
  - `docs/github-setup.md`
  - `docs/decisions/0002-branch-and-agent-governance.md`
  - `logs/tests/2026-11-18-branch-and-agent-governance.md`
  - `logs/sessions/2026-11-18-d5488c8e.md`
- Modify:
  - `CONSTITUTION.md` (v1.1: Articles 5, 7, 8 per spec §4.3)
  - `CLAUDE.md`
  - `README.md`
  - `.gitignore` (`.worktrees/`)
  - `tools/governance_rules.py` (`SKIP_DIRS` adds `.worktrees`)
  - `tests/test_governance_check.py`
  - `docs/templates/session-journal.md` (if needed)

- [ ] **Step 1: Failing tests:**
  - `test_worktrees_folder_skipped` (checker ignores `.worktrees/x/notes.txt` in a non-git folder)
  - `test_ruleset_protects_main`: parse the JSON. Assert:
    - target `branch`;
    - include `~DEFAULT_BRANCH`;
    - rule types ⊇ {`deletion`, `non_fast_forward`, `pull_request`, `required_status_checks`};
    - the status-check context is `governance`;
    - `bypass_actors == []`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Write the files.
  - The constitution edit raises the owner's approval prompt (Article 6).
  - `docs/github-setup.md` gives the owner's numbered click-steps: Settings → Rules → Rulesets → New ruleset → Import a ruleset → choose `.github/rulesets/protect-main.json` → Create. It also gives one `cd`-prefixed git command to download the file if needed, and the private-repo/free-plan note.
- [ ] **Step 4:** Run tests and checker → PASS / OK.
- [ ] **Step 5:** Write the test log and session journal.
- [ ] **Step 6:** Commit `docs: constitution v1.1, GitHub ruleset and agent rules`.
- [ ] **Step 7:** Push `claude/determined-goodall-hyfv3b`, confirm the check passes, open a PR. Do not merge without the owner's request.
