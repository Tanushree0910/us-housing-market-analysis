# 0006: Constitution 1.3 combines two parallel amendments

## Date
2026-11-24

## Status
Accepted

## Decision
Two branches amended the constitution at the same time, starting from version 1.0. Both called their result "version 1.1":
- `main` adopted decision 0002 (branch, GitHub and agent governance): Article 5 rewritten for worktrees and owner-approved merges, plus new Articles 7 (safety) and 8 (AI agents and helper agents).
- The housing-analysis branch (`claude/charming-rubin-9jw9w3`) changed Article 2 (agents may add files the owner downloaded) and Article 3 (Power BI project folders), in decisions first numbered 0002 and 0003.

When `main` was merged into the housing-analysis branch, the owner approved:
- combining both sets of changes, unchanged, into **version 1.3**;
- renumbering the branch's decisions so numbers stay unique: Power BI project format 0002 → **0003**, owner-downloaded data 0003 → **0004**, Zillow-only data 0004 → **0005**. Every reference in the repo was updated.

## Reason
The two amendments change different articles and do not contradict each other, so both apply. Decision numbers must be unique, and `main`'s 0002 was merged first, so the branch's decisions move up. The version jumps to 1.3 because 1.1 and 1.2 had both already been used on the branch.

## Alternatives
- Keep the branch's numbers and renumber `main`'s decision: rejected, because `main` is already published and other records point to its 0002.
- Rebase the branch onto `main` instead of merging: rejected, because it rewrites published history, which Article 7 blocks.
