# Test: Hooks read Git Bash drive paths correctly on Windows

## What was tested
The fix for [BUG-004](../bugs/BUG-004-hooks-misread-git-bash-drive-paths.md): `.claude/hooks/shellparse.py` now turns Git Bash drive paths (`/c/Users/...`) into Windows drive paths (`C:/Users/...`) on Windows before resolving them. Tested on the owner's Windows 11 PC (Python 3.12.10), in the worktree `.worktrees/hooks-gitbash-paths` on branch `claude/hooks-gitbash-paths` (based on `claude/hooks-windows-paths`, the unmerged BUG-003 fix).

## How
1. Added tests before the fix:
   - `tests/test_git_guard.py` `GitBashPathTests` (3 tests, run on every system): `from_git_bash` converts `/c/Users/me`, `/D/work`, `/c` and `/c/` with `windows=True`; leaves `/cd/x`, `/tmp/x`, `c/x`, `./c/x`, `C:/x`, `C:\x`, `//c/x`, `~` and the empty string alone; never converts with `windows=False` (Linux).
   - `tests/test_git_guard.py` `GitBashGuardTests` (3 tests, Windows only) on a temporary repo with a worktree: `cd "/c/<main folder>" && git commit` and `git -C /c/<main folder> commit` are denied; the same into the worktree are allowed; `rm -rf /c/<project>` is denied.
   - `tests/test_hooks.py` `GuardGitBashTests` (1 test, Windows only): `rm /c/<folder>/data/a.csv`, `cd "/c/<folder>" && rm data/a.csv`, `echo x > /c/<folder>/data/a.csv` and an Edit of `/c/<folder>/data/a.csv` are denied, for both the main folder and the worktree.
2. Before the fix, `python -m unittest tests.test_git_guard tests.test_hooks`: 3 errors (helper missing) and 3 failures: main-folder commit allowed, raw-data delete allowed, `rm -rf` of the project only asked instead of being denied.
3. Applied the fix, then `python -m unittest discover -s tests -t .`: 141 tests, all pass, 1 skipped (the symlink test from BUG-001).
4. `python tools/governance_check.py`: `OK: no governance problems`.

## Result
PASS

## Bugs
[BUG-004](../bugs/BUG-004-hooks-misread-git-bash-drive-paths.md) (fixed)
