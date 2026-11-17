# Test: governance minor fixes

## What was tested
The nine minor fixes from the final review: raw-data guard precision, upper-case `.CSV`, symlinked project folders, `SOURCES.md` format messages, files starting with a byte-order mark, git-ignored clutter, stop-hook retries, and the CI workflow trigger and permissions.

## How
`python3 -m unittest discover -s tests -t .` (75 tests: 16 new for these fixes, 4 for the follow-ups from the second review, and 5 for the last small issues) and `python3 tools/governance_check.py` on the real repo.

## Result
PASS

## Bugs
None. The old guard also blocked one of this session's own commands while these fixes were being written. That was the over-blocking issue (M1) that Task 1 fixes, not a new bug.
