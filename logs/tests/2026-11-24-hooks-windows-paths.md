# Test: Hook tests pass on Windows after the drive-path fix

## What was tested
The fix for [BUG-003](../bugs/BUG-003-git-guard-tests-fail-on-windows.md): `.claude/hooks/shellparse.py` now keeps the backslashes of unquoted Windows drive paths (`C:\...`) when it splits a command. Tested on the owner's Windows 11 PC (Python 3.12), in the worktree `.worktrees/hooks-windows-paths` on branch `claude/hooks-windows-paths`.

## How
1. Before the fix, `python -m unittest discover -s tests -t .`: 131 tests, 5 failures and 1 error, the 6 tests named in BUG-003.
2. Called `shellparse.tokens` directly: `cd C:\Users\tanus\Temp\tmp1 && git commit -m y` gave `['cd', 'C:UserstanusTemptmp1', ...]`, which confirmed the cause.
3. Added `WindowsPathTokenTests` (3 tests) to `tests/test_git_guard.py`. Before the fix, the 2 Windows-path tests failed and the POSIX-escape test passed.
4. Applied the fix, then ran `python -m unittest discover -s tests -t .` again: 134 tests, all pass, 1 skipped (the symlink test from BUG-001, which needs symlink rights on Windows).
5. `python tools/governance_check.py`: `OK: no governance problems`.
6. Called `git_guard.decide` on a temporary repo with `cd "<path>" && git commit -m x` for several path forms. Backslash and forward-slash drive paths work correctly. Git Bash paths (`/c/...`) to the main folder are wrongly allowed: a separate problem, logged as [BUG-004](../bugs/BUG-004-hooks-misread-git-bash-drive-paths.md).

## Result
PASS

## Bugs
[BUG-003](../bugs/BUG-003-git-guard-tests-fail-on-windows.md) (fixed), [BUG-004](../bugs/BUG-004-hooks-misread-git-bash-drive-paths.md) (found, open)
