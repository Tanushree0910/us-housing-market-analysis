# 0002: Branch, GitHub and agent governance (constitution v1.1)

## Date
2026-11-18

## Status
Accepted

## Decision
Amend the constitution to version 1.1:
- Rewrite Article 5 to cover branches, worktrees and merging.
- Add Article 7 on safety, covering dangerous commands.
- Add Article 8 on AI agents and helper agents.

Enforce these rules with three changes:
- New Claude Code hooks: `git_guard.py`, `agent_guard.py`, the extended `session_start.py`, and `session_end.py`, which replaces `stop_journal.py`.
- A GitHub "Protect main" ruleset, kept in `.github/rulesets/protect-main.json`.
- A CODEOWNERS file and a pull request template.

## Reason
The owner asked for:
- GitHub protection for `main`;
- hooks that block dangerous commands;
- no agent work on `main`, with agents working only in worktrees;
- merges only on the owner's request;
- helper-agent model rules;
- session start and end checks;
- commands for the owner that always start with `cd`;
- no requests to attach or upload files the agent can already reach.

The owner chose which commands are always blocked and which ask first. They also chose that only Fable is blocked for helpers: the main session picks Opus, Sonnet or Haiku.

## Alternatives
- **Hooks only, without a GitHub ruleset:** rejected. Nothing would stop a bad push from another tool or computer.
- **A GitHub ruleset only:** rejected. Local damage, like `git reset --hard`, would not be prevented.
- **Requiring pull request approvals on GitHub:** rejected. The owner is the only person on the repo, and GitHub doesn't allow approving your own pull request.
- **Allowing only Sonnet and Haiku for helpers:** replaced by the owner's later choice to block only Fable.
