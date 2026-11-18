import datetime
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPO, make_repo_with_worktree, run_git

HOOKS = REPO / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))


def load(name):
    spec = importlib.util.spec_from_file_location(f"hook_{name}", HOOKS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


session_start = load("session_start")
session_end = load("session_end")
git_guard = load("git_guard")

SID = "abcd1234-ffff-0000-1111-222233334444"
GOOD_JOURNAL = ("# Session journal\n\n## Goal\ng\n\n## What changed\nc\n\n## Tests run\nt\n\n"
                "## Bugs found\nNone\n\n## Next steps\nNone\n")


class SessionStartBriefingTests(unittest.TestCase):
    def setUp(self):
        self.repo, self.wt = make_repo_with_worktree()

    def tearDown(self):
        self.repo.cleanup()

    def context(self, project=None):
        result = session_start.decide({"session_id": SID}, project or self.repo.root)
        return result["hookSpecificOutput"]["additionalContext"]

    def test_start_warns_on_main(self):
        text = self.context()
        self.assertIn("WARNING", text)
        self.assertIn("'main'", text)

    def test_start_lists_worktrees_and_skills(self):
        text = self.context()
        self.assertIn(".worktrees/w", text)
        self.assertIn("feature", text)
        for skill in ("superpowers:using-superpowers", "superpowers:brainstorming",
                      "superpowers:writing-plans", "superpowers:using-git-worktrees",
                      "superpowers:test-driven-development", "superpowers:systematic-debugging",
                      "superpowers:verification-before-completion",
                      "superpowers:finishing-a-development-branch"):
            self.assertIn(skill, text)
        self.assertIn("git worktree add", text)

    def test_start_includes_owner_rules(self):
        text = self.context()
        self.assertIn(f"cd {self.repo.root.resolve()}", text)
        self.assertIn("attach", text)
        self.assertIn("merge", text.lower())
        self.assertIn("sonnet", text.lower())
        self.assertIn("fable", text.lower())

    def test_start_records_worktrees_in_state(self):
        self.context()
        state = json.loads((self.repo.root / ".claude/state" / f"{SID}.json").read_text())
        self.assertIn(str(self.wt.resolve()), state["worktrees"])


class SessionEndTests(unittest.TestCase):
    def setUp(self):
        self.repo, self.wt = make_repo_with_worktree()
        self.root = self.repo.root
        self.journal = f"logs/sessions/{datetime.date.today().isoformat()}-abcd1234.md"

    def tearDown(self):
        self.repo.cleanup()

    def start(self):
        session_start.decide({"session_id": SID}, self.root)

    def end(self, **extra):
        return session_end.decide({"session_id": SID, **extra}, self.root)

    def wt_write(self, rel, text="x"):
        """Write a file the way an agent does: through the Write tool, which the git guard sees."""
        path = self.wt / rel
        git_guard.decide({"tool_name": "Write", "session_id": SID,
                          "tool_input": {"file_path": str(path)}}, self.root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def wt_commit(self):
        run_git(self.wt, "add", "-A")
        run_git(self.wt, "commit", "-q", "-m", "work")

    def add_origin(self):
        self._bare = tempfile.TemporaryDirectory()
        run_git(self._bare.name, "init", "-q", "--bare")
        run_git(self.root, "remote", "add", "origin", self._bare.name)
        run_git(self.root, "push", "-q", "origin", "main")
        self.addCleanup(self._bare.cleanup)

    def test_end_blocks_uncommitted_worktree_changes(self):
        self.start()
        self.wt_write(self.journal, GOOD_JOURNAL)
        self.wt_commit()
        self.wt_write("sql/01_a.sql", "select 1")
        result = self.end()
        self.assertEqual(result["decision"], "block")
        self.assertIn("uncommitted", result["reason"])
        self.assertIn(str(self.wt.resolve()), result["reason"])

    def test_end_blocks_unpushed_commits_until_pushed(self):
        self.add_origin()
        self.start()
        self.wt_write("sql/01_a.sql", "select 1")
        self.wt_write(self.journal, GOOD_JOURNAL)
        self.wt_commit()
        result = self.end()
        self.assertEqual(result["decision"], "block")
        self.assertIn("not been pushed", result["reason"])
        self.assertIn("git push -u origin feature", result["reason"])
        run_git(self.wt, "push", "-q", "-u", "origin", "feature")
        self.assertIsNone(self.end())

    def test_end_blocks_checker_problems_in_worktree(self):
        self.start()
        self.wt_write("notes.txt")
        self.wt_write(self.journal, GOOD_JOURNAL)
        self.wt_commit()
        result = self.end()
        self.assertEqual(result["decision"], "block")
        self.assertIn("notes.txt", result["reason"])

    def test_end_blocks_missing_journal(self):
        self.start()
        self.wt_write("sql/01_a.sql", "select 1")
        self.wt_commit()
        result = self.end()
        self.assertEqual(result["decision"], "block")
        self.assertIn(self.journal, result["reason"])

    def test_end_accepts_committed_journal_in_worktree(self):
        self.start()
        self.wt_write("sql/01_a.sql", "select 1")
        self.wt_write(self.journal, GOOD_JOURNAL)
        self.wt_commit()
        self.assertIsNone(self.end())

    def test_end_ignores_untouched_preexisting_worktree(self):
        (self.wt / "sql").mkdir(exist_ok=True)
        (self.wt / "sql" / "01_old.sql").write_text("someone else's work in progress")
        self.start()
        self.assertIsNone(self.end())

    def test_end_counts_new_worktree_as_changed(self):
        self.start()
        command = "git worktree add -q .worktrees/n -b n"
        git_guard.decide({"tool_name": "Bash", "session_id": SID, "cwd": str(self.root),
                          "tool_input": {"command": command}}, self.root)
        run_git(self.root, "worktree", "add", "-q", ".worktrees/n", "-b", "n")
        self.assertEqual(self.end()["decision"], "block")

    def test_end_ignores_other_sessions_worktrees(self):
        self.start()
        run_git(self.root, "worktree", "add", "-q", ".worktrees/other", "-b", "other")
        (self.root / ".worktrees" / "other" / "wip.txt").write_text("someone else's work")
        self.wt.joinpath("wip2.txt").write_text("also not this session's")
        self.assertIsNone(self.end())

    def test_end_counts_worktree_entered_with_cd(self):
        self.start()
        git_guard.decide({"tool_name": "Bash", "session_id": SID, "cwd": str(self.root),
                          "tool_input": {"command": f"cd {self.wt} && touch sql/x.sql"}}, self.root)
        (self.wt / "sql").mkdir(exist_ok=True)
        (self.wt / "sql" / "01_x.sql").write_text("select 1")
        self.assertEqual(self.end()["decision"], "block")

    def test_end_does_not_blame_session_for_main_folder_changes(self):
        self.start()
        (self.root / "notes.md").write_text("the owner's own edit")
        self.assertIsNone(self.end())


class SettingsTests(unittest.TestCase):
    def test_settings_wire_all_hooks(self):
        settings = json.loads((REPO / ".claude/settings.json").read_text())["hooks"]

        def scripts(event, matcher=None):
            return {hook["command"].split("/")[-1].split(".py")[0]
                    for entry in settings[event] if entry.get("matcher") == matcher
                    for hook in entry["hooks"]}

        self.assertEqual(scripts("SessionStart"), {"session_start"})
        self.assertEqual(scripts("Stop"), {"session_end"})
        self.assertEqual(scripts("PreToolUse", "Edit|Write|MultiEdit|NotebookEdit|Bash"), {"guard", "git_guard"})
        self.assertEqual(scripts("PreToolUse", "mcp__github__.*"), {"git_guard"})
        self.assertEqual(scripts("PreToolUse", "Agent|Task|mcp__claude-code-remote__create_session"),
                         {"agent_guard"})


if __name__ == "__main__":
    unittest.main()
