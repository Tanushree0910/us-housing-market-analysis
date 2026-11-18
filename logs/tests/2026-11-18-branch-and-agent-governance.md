# Test: branch, GitHub and agent governance

## What was tested
- The new git guard: worktree-only edits and commits, protection of `main`, dangerous commands, risky commands, merges, and GitHub writes.
- The helper-model guard.
- The worktree-aware data guard.
- The session start briefing and session end checks.
- The hook settings wiring.
- The GitHub ruleset file, CODEOWNERS and pull request template.
- The checker skipping `.worktrees/`.

## How
- Ran `python3 -m unittest discover -s tests -t .` inside the worktree: 127 tests, 7 of them added after the final review.
- Ran `python3 tools/governance_check.py`.
- Ran the session start hook by hand against the real repo, to read the briefing it produces.

## Result
PASS

## Bugs
None
