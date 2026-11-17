# 0001: Adopt the repo governance system

## Date
2026-11-17

## Status
Accepted

## Decision
Adopt `CONSTITUTION.md` (version 1.0) as the repo's rules. Enforce them with an automatic checker on GitHub (`tools/governance_check.py` plus tests) and with Claude Code hooks (`.claude/hooks/`). Keep session journals, bug logs, test logs and decision records using the templates in `docs/templates/`.

## Reason
The owner wanted clear rules for themselves and for the AI agents working in the repo, plus automatic enforcement, so that raw data stays untouched, files stay organised, and every agent session leaves a written record.

## Alternatives
- Written rules only, without checks: rejected because nothing would stop mistakes.
- Also locking `main` so it only accepts changes that pass the checks: not chosen for now. It can be added later by turning on GitHub branch protection.
- Rules for outside collaborators (code of conduct, contribution guide): not needed while the repo is run by the owner and AI agents.
