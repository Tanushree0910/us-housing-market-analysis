import importlib.util
import sys
import unittest
from pathlib import Path

from tests.helpers import REPO

HOOKS = REPO / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))
_spec = importlib.util.spec_from_file_location("hook_agent_guard", HOOKS / "agent_guard.py")
agent_guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(agent_guard)


def call(tool="Agent", **tool_input):
    return agent_guard.decide({"tool_name": tool, "tool_input": tool_input}, Path("/proj"))


def decision(result):
    return result["hookSpecificOutput"]["permissionDecision"] if result else None


class AgentGuardTests(unittest.TestCase):
    def test_named_models_allowed(self):
        for model in ("sonnet", "opus", "haiku", "claude-sonnet-5-5"):
            self.assertIsNone(call(model=model, prompt="x"), model)
            self.assertIsNone(call("Task", model=model, prompt="x"), model)

    def test_fable_denied(self):
        for model in ("fable", "claude-fable-5-2", "Fable"):
            result = call(model=model, prompt="x")
            self.assertEqual(decision(result), "deny", model)
            self.assertIn("Article 8", result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_missing_model_denied(self):
        for result in (call(prompt="x"), call(prompt="x", model=""), call(prompt="x", model=None)):
            self.assertEqual(decision(result), "deny")
            self.assertIn("sonnet", result["hookSpecificOutput"]["permissionDecisionReason"])

    def test_fork_denied(self):
        self.assertEqual(decision(call(subagent_type="fork", model="sonnet", prompt="x")), "deny")

    def test_remote_session_rules(self):
        tool = "mcp__claude-code-remote__create_session"
        self.assertEqual(decision(call(tool, prompt="x")), "deny")
        self.assertEqual(decision(call(tool, model="claude-fable-5-2")), "deny")
        self.assertIsNone(call(tool, model="claude-sonnet-5-5"))

    def test_other_tools_ignored(self):
        self.assertIsNone(call("Bash", command="ls"))
        self.assertIsNone(call("Read", file_path="/x"))


if __name__ == "__main__":
    unittest.main()
