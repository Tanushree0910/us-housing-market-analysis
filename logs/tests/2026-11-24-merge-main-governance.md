# Test: Merge of main (branch and agent governance) into the housing-analysis branch

## What was tested
Merging `origin/main` (PR #2, constitution 1.1 with branch, worktree and agent rules) into `claude/charming-rubin-9jw9w3`, with the owner's approval, so pull request #4 can merge.

## How
1. `git merge --no-ff --no-commit origin/main`. Three files conflicted: `.gitignore`, `README.md` and `CONSTITUTION.md`. All other files merged automatically, including `CLAUDE.md`, which keeps this branch's "Adding raw data" section alongside main's worktree rules.
2. Resolved as follows:
   - `.gitignore`: keeps both sides.
   - `README.md`: keeps this branch's findings and adds main's "Protect main" line under Governance. Main's placeholder "Findings: _To be added._" was dropped.
   - `CONSTITUTION.md`: both amendments combined, version 1.3 ([decision 0006](../../docs/decisions/0006-constitution-1-3-merge.md)).
3. Renumbered this branch's decisions, because main already used 0002: Power BI project format → 0003, owner-downloaded data → 0004, Zillow-only data → 0005. All references were updated: README, plan, design doc, test logs, session journals and SQL comments. A repo-wide search afterwards found no reference still pointing to an old number.
4. `python tools/governance_check.py`: no problems.
5. `python -m unittest discover -s tests -t .`: 131 tests, 6 failures/errors, all in tests that came with main's new hooks. A temporary detached checkout of `origin/main` alone fails the same tests on this PC (8 there), so they are an existing Windows issue, not caused by the merge: [BUG-003](../bugs/BUG-003-git-guard-tests-fail-on-windows.md). GitHub's Linux CI is the reference for these hook tests. The merge itself passes: every failure also happens on main alone.
6. The SQL and Power BI files are unchanged by the merge (apart from comments that now say "decision 0005"). `sqlcmd -S localhost -E -C -b -I -i sql/99_validation_checks.sql` still passes all 60 checks.

## Result
PASS

## Bugs
[BUG-003](../bugs/BUG-003-git-guard-tests-fail-on-windows.md)
