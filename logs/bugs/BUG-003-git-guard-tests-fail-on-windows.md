# BUG-003: Git-guard and session-hook tests fail on Windows

## Status
Open

## Found
2026-11-24, agent session on the owner's PC, while merging `main` (PR #2, branch and agent governance) into `claude/charming-rubin-9jw9w3`.

## What happened
On the owner's Windows PC, `python -m unittest discover -s tests -t .` fails 6 of the tests that came with PR #2:
- `test_git_guard`: `test_cd_into_worktree_then_commit_allowed`, `test_cd_with_variable_and_pushd_followed`, `test_commit_in_feature_worktree_allowed`, `test_dangerous_commands_denied`
- `test_hooks`: `test_guard_denies_raw_csv_inside_worktree`
- `test_session_hooks`: `test_end_counts_worktree_entered_with_cd`

Examples:
- `cd <worktree> && git commit` is denied as "in the main project folder", even though it runs inside a worktree.
- `rm -rf C:\Users\…\Temp\tmp…` returns `ask` where the test expects `deny`.

A clean checkout of `main` alone fails the same tests on this PC (8 failures and errors there; the merge fixes 2 of them, the symlink test from BUG-001 among them). So the merge did not cause them. On GitHub's Linux runner the same tests pass.

## Cause
Unknown yet. Every failing test uses Windows paths (`C:\…`, backslashes) in `cd` targets or `rm` arguments, so the guard's path parsing most likely handles only POSIX-style paths. If so, the live hooks could also wrongly block, or fail to block, commands on the owner's PC.

## Fix
Not fixed yet. It is outside the merge, and the hooks are governance architecture the owner owns. Suggested follow-up: make the guard's path handling accept Windows drive paths and backslashes, then re-run these 6 tests on the PC.

## Test log
[2026-11-24-merge-main-governance.md](../tests/2026-11-24-merge-main-governance.md)
