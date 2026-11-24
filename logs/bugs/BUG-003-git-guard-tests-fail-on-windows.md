# BUG-003: Git-guard and session-hook tests fail on Windows

## Status
Fixed

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
The shared command splitter `.claude/hooks/shellparse.py` reads commands with Python's `shlex` in POSIX mode. There an unquoted backslash escapes the next character, so `cd C:\Users\me\wt` was read as `cd C:Usersmewt`: a relative folder that does not exist. Every hook that follows `cd`, `pushd` or `git -C`, or judges `rm` targets, uses this splitter (`git_guard.py`, `guard.py`, and the worktree tracking that `session_end.py` relies on). So on Windows:
- a commit after `cd <worktree>` (or `pushd`, or `git -C <worktree>`) was judged in the main folder and denied;
- `rm -rf <whole project>` was not recognised as deleting the project, so it got `ask` instead of `deny` (a weaker block than Article 7.1 requires);
- `cd <worktree> && rm data/a.csv` was not seen as deleting raw data;
- the session-end hook did not learn that the session had entered the worktree.

Confirmed by calling `shellparse.tokens` directly: `cd C:\Users\tanus\Temp\tmp1` came back as `['cd', 'C:UserstanusTemptmp1']`. On Linux the test paths have no backslashes, so CI passed.

## Fix
`shellparse.tokens` now runs a small quote-aware pre-pass (`_keep_drive_backslashes`) before `shlex`. In an unquoted word that starts with a drive letter (`C:\`, also right after `=`), each backslash is kept as a path separator, except before whitespace, where it still escapes the space. Quoted text and all other words are untouched, so POSIX escapes such as `a\ b` and `\$HOME`, and every command without a drive path, split exactly as before. No test was changed or weakened. Three tokenizer tests were added in `tests/test_git_guard.py` (`WindowsPathTokenTests`). They are plain string tests, so they also protect this behaviour on GitHub's Linux runner.

## Test log
[2026-11-24-hooks-windows-paths.md](../tests/2026-11-24-hooks-windows-paths.md) (fix). Found during [2026-11-24-merge-main-governance.md](../tests/2026-11-24-merge-main-governance.md).
