# Branch, GitHub and Agent Governance — Design

**Owner:** repo owner. **Builds on:** `docs/superpowers/specs/2026-11-16-governance-design.md` and `CONSTITUTION.md` v1.0.

## 1. Intent

The owner is learning and wants the repo to protect itself. AI agents must never damage `main`, run destructive commands, merge without being asked, use a model the owner doesn't want, or waste the owner's time asking for files the agent can already reach. Every agent session must start informed and end tidy.

## 2. Owner decisions

1. **GitHub:** `main` only accepts changes through a pull request that passes the governance check. No force-push, no deletion.
2. **Local:** agents never work on `main` and only edit files inside a git worktree at `.worktrees/<name>/`.
3. **Dangerous commands:**
   - **Always blocked:** wiping `/`, the home folder, the project or `.git`; force-pushing; rewriting history; erasing disks; piping internet scripts into a shell; deleting the GitHub repo.
   - **Ask the owner first:** `git reset --hard`, `git clean`, deleting a branch, discarding changes (`git checkout -- .`, `git restore .`), dropping stashes, `rm -r` of a folder, force-removing a worktree.
4. **Merging:** `git merge`, `gh pr merge` and the GitHub merge and auto-merge tools always raise an approval prompt.
5. **Helper agents:**
   - Fable is blocked.
   - The main session chooses Opus, Sonnet or Haiku, and must name the model on every helper.
   - "Fork" helpers are blocked, because they silently copy the main session's model.
   - New remote sessions must also name a non-Fable model.
6. **Session start:** the agent is told:
   - its branch and worktree status, with a warning if it is on `main` or not in a worktree;
   - the existing worktrees;
   - the essential skills;
   - the owner's communication rules.
7. **Session end:** the agent cannot finish while any of these is true:
   - a worktree or the main folder has uncommitted changes;
   - the session journal is incomplete;
   - a changed worktree fails the governance check;
   - commits haven't been pushed.

   The agent gets three retries per turn, then the owner is told (the existing behaviour).
8. **Communication rules:**
   - Every command given to the owner starts with `cd` to the full folder path, git commands included.
   - Never ask the owner to attach, upload or share a file or folder that is in the project folder or repo. Look first. If something truly can't be reached, say where you looked.

## 3. Non-goals

- Forcing a skill to load. Hooks can only inject reminders.
- Requiring PR approvals on GitHub. The owner is the only person, and GitHub doesn't let you approve your own PR.
- Governing the owner's own manual git use. Hooks only run inside Claude Code.

## 4. Design

### 4.1 GitHub (`.github/`)
- `rulesets/protect-main.json`: a GitHub ruleset for the default branch.
  - Rules: `deletion`, `non_fast_forward`, `pull_request` (0 approvals), `required_status_checks` (context `governance`).
  - No bypass actors.
- `CODEOWNERS`: `* @Tanushree0910`.
- `pull_request_template.md`: Summary; Records (journal, test log, decision); Checklist (checker OK, tests OK, merged only on owner's request).
- `docs/github-setup.md`: the owner's exact click-steps to import the ruleset, plus the note that GitHub may not enforce rulesets on a private repo with a free plan.

### 4.2 Hooks (`.claude/hooks/`, Python stdlib, fail open)

| Hook file | Event | Job |
|---|---|---|
| `guard.py` (exists) | PreToolUse: edit tools, Bash | Raw data protection, constitution ask |
| `git_guard.py` (new) | PreToolUse: edit tools, Bash, GitHub MCP write/merge tools | Worktree-only edits, no work on `main`, protect `main`, merge asks, dangerous commands |
| `agent_guard.py` (new) | PreToolUse: `Agent`, `Task`, `mcp__claude-code-remote__create_session` | Helper model rules |
| `session_start.py` (exists, extended) | SessionStart | Briefing and status |
| `stop_journal.py` → `session_end.py` (renamed, extended) | Stop | End-of-session checks |

Key definitions:
- **Main checkout:** the project folder itself (`$CLAUDE_PROJECT_DIR`, or the git common dir's parent when the session runs inside a worktree).
- **Agent worktree:** any folder under `<main checkout>/.worktrees/`.
- **Edit allowed:** the target is outside the main checkout (scratchpad, home config), or inside `.worktrees/<name>/` on a branch other than `main`/`master`.
- **Git writes** (commit, merge, rebase, cherry-pick, revert, am, reset, push) are denied when the directory they run in is the main checkout, or a worktree whose branch is `main`/`master`. The directory comes from `cd` tracking within the command; otherwise from the payload `cwd`.
- **Protect main:** these are denied:
  - pushes whose refspec targets `main`/`master` (`main`, `HEAD:main`, `:main`, `+main`), and `--all`/`--mirror`;
  - deleting, renaming or `update-ref`-ing `main`/`master`;
  - GitHub MCP file writes (`create_or_update_file`, `push_files`, `delete_file`) with `branch` `main`/`master`.

### 4.3 Repo and records
- `.gitignore` gains `.worktrees/`. The checker's `SKIP_DIRS` gains `.worktrees`.
- `CONSTITUTION.md` v1.1:
  - Article 5 rewritten: branches, worktrees, merging only on request.
  - New Article 7: Safety (dangerous commands).
  - New Article 8: AI agents and helper agents (models, session start and end, communication rules).
- Decision `0002-branch-and-agent-governance.md`.
- `CLAUDE.md` and the README Governance section updated.

## 5. Approaches considered

- **Hooks plus GitHub ruleset (chosen):** local hooks catch mistakes before they happen. The ruleset is the hard backstop on GitHub.
- **Hooks only:** nothing stops a bad push from another tool or machine. Rejected.
- **Ruleset only:** mistakes are caught only at push time, after local damage like `git reset --hard`. Rejected.

## 6. Builder's calls

- `git pull` is not treated as a merge command. Updating a feature branch is routine.
- Commands are parsed with the same tokenizer as `guard.py`, moved into a shared `shellparse.py`.
- Worktrees created during the session count as changed for the end checks. Pre-existing worktrees count as changed only if their status or HEAD changed since the start.
- The essential skills named at session start:
  - `superpowers:using-superpowers`
  - `superpowers:brainstorming` (new features)
  - `superpowers:writing-plans` (multi-step work)
  - `superpowers:using-git-worktrees`
  - `superpowers:test-driven-development`
  - `superpowers:systematic-debugging` (bugs)
  - `superpowers:verification-before-completion`
  - `superpowers:finishing-a-development-branch`
