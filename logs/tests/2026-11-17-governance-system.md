# Test: governance checker and hooks

## What was tested
The repo checker (`tools/governance_check.py`), the data fingerprint check, the record-format checks and the three Claude Code hooks (`.claude/hooks/`).

## How
`python3 tools/governance_check.py` on the real repo, `python3 -m unittest discover -s tests -t .` (43 tests), and each hook script run by hand with a sample payload.

## Result
PASS

## Bugs
None
