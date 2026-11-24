# BUG-004: Hooks misread Git Bash drive paths like /c/Users/...

## Status
Fixed

## Found
2026-11-24, agent session 3ec9f889 on the owner's PC, while fixing [BUG-003](BUG-003-git-guard-tests-fail-on-windows.md).

## What happened
On Windows, Git Bash (the shell behind Claude Code's Bash tool) writes drive paths as `/c/Users/...`. The hooks resolve such a path with Python's `Path`, which on Windows reads it as `C:\c\Users\...`, a folder that does not exist. So a `cd` to a Git Bash path lands nowhere the hooks recognise.

Checked with `git_guard.decide` on a temporary repo with a worktree:
- `cd "C:\...\repo" && git commit -m x` → deny (correct)
- `cd "/c/.../repo" && git commit -m x` → allowed (wrong: this commits in the main project folder, which Article 5 forbids)
- `cd "/c/.../repo/.worktrees/w" && git commit -m x` → allowed (correct, but only because unknown folders are allowed)

So the main-folder rule fails open for Git Bash paths. The same path reading is used for raw-data and `rm` checks, so those can likely be bypassed the same way. On Linux this cannot happen.

## Cause
`shellparse.absolute` passes the path straight to `pathlib.Path`, which does not know the MSYS/Git Bash `/<drive>/...` form.

## Fix
Fixed 2026-11-24 on branch `claude/hooks-gitbash-paths`. New `shellparse.from_git_bash` turns a leading `/<letter>/` or a bare `/<letter>` into `<LETTER>:/`, only when `os.name == "nt"`. `shellparse.absolute` calls it before building the path, so every check that reads paths through it (main-folder and worktree checks for `cd` and `git -C`, raw-data checks, `rm -r` checks, edit paths) now sees the real folder. Paths like `/cd/x`, `/tmp/x` and `//c/x` are left alone, and Linux behaviour is unchanged.

## Test log
[2026-11-24-hooks-gitbash-paths.md](../tests/2026-11-24-hooks-gitbash-paths.md). Found during [2026-11-24-hooks-windows-paths.md](../tests/2026-11-24-hooks-windows-paths.md).
