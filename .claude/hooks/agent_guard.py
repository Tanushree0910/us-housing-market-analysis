"""PreToolUse hook: helper agents (subagents and new sessions) follow Article 8.

- Fable is never used.
- The main session picks Opus, Sonnet or Haiku, and must name it, because a helper
  that names no model silently copies the main session's model.
- "fork" helpers always copy the main session's model, so they are blocked.
"""
from pathlib import Path

import hooklib

HELPER_TOOLS = {"Agent", "Task"}
REMOTE_SESSION_TOOL = "mcp__claude-code-remote__create_session"
NAME_A_MODEL = ("Name the model for this helper: model \"sonnet\" (the default choice), \"haiku\" "
                "(quick, simple tasks) or \"opus\" (hard reasoning).")


def _deny(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": f"{reason} (CONSTITUTION.md Article 8)"}}


def _model_problem(model) -> str | None:
    if not model or not str(model).strip():
        return f"Every helper must name its model. {NAME_A_MODEL}"
    if "fable" in str(model).lower():
        return f"Fable is not used for helpers. {NAME_A_MODEL}"
    return None


def decide(payload: dict, project: Path) -> dict | None:
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input") or {}
    if tool in HELPER_TOOLS:
        if tool_input.get("subagent_type") == "fork":
            return _deny("Fork helpers always copy the main session's model, so they are not used. "
                         f"Use a named helper type instead. {NAME_A_MODEL}")
        problem = _model_problem(tool_input.get("model"))
        return _deny(problem) if problem else None
    if tool == REMOTE_SESSION_TOOL:
        problem = _model_problem(tool_input.get("model"))
        return _deny(problem) if problem else None
    return None


if __name__ == "__main__":
    hooklib.run(decide)
