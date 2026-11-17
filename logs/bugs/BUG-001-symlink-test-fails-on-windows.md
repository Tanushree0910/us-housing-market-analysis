# BUG-001: Symlink test errors on the owner's Windows PC

## Status
Fixed

## Found
2026-11-17, agent session running on the owner's PC (plan Task 2).

## What happened
`python -m unittest discover -s tests -t .` reported 1 error out of 79 tests: `test_guard_resolves_symlinked_project` stopped with `OSError: [WinError 1314] A required privilege is not held by the client` when it tried to create a symlink.

## Cause
Windows only lets a normal user create symlinks when Developer Mode is on or the process runs as administrator. The test assumed symlinks always work, which is true on GitHub's Linux runner but not on this PC. The guard itself is not at fault.

## Fix
The test now skips itself, with the reason, when the operating system refuses to create the symlink. It still runs in full on GitHub Actions (Linux). Turning on Developer Mode was not done, because it changes a Windows security setting.

## Test log
[2026-11-17-new-raw-files.md](../tests/2026-11-17-new-raw-files.md)
