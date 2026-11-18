import datetime
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests.helpers import REPO, TempRepo

HOOKS = REPO / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))


def load(name):
    spec = importlib.util.spec_from_file_location(f"hook_{name}", HOOKS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


session_start = load("session_start")
guard = load("guard")
stop_journal = load("session_end")

SID = "abcd1234-ffff-0000-1111-222233334444"
GOOD_JOURNAL = ("# Session journal\n\n## Goal\ng\n\n## What changed\nc\n\n## Tests run\nt\n\n"
                "## Bugs found\nNone\n\n## Next steps\nNone\n")


def git(root, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          cwd=root, check=True, capture_output=True, text=True).stdout


class GitRepo(TempRepo):
    def __init__(self):
        super().__init__()
        git(self.root, "init", "-q")
        self.write("README.md", "hi")
        self.commit()

    def commit(self):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "c")


def decision(result):
    return result["hookSpecificOutput"]["permissionDecision"] if result else None


class SessionStartTests(unittest.TestCase):
    def setUp(self):
        self.repo = GitRepo()

    def tearDown(self):
        self.repo.cleanup()

    def test_session_start_writes_state_and_names_journal(self):
        result = session_start.decide({"session_id": SID}, self.repo.root)
        state = json.loads((self.repo.root / ".claude/state" / f"{SID}.json").read_text())
        today = datetime.date.today().isoformat()
        self.assertEqual(state["date"], today)
        self.assertEqual(state["head"], git(self.repo.root, "rev-parse", "HEAD").strip())
        context = result["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(result["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("CONSTITUTION.md", context)
        self.assertIn(f"logs/sessions/{today}-abcd1234.md", context)

    def test_session_start_keeps_existing_date(self):
        self.repo.write(f".claude/state/{SID}.json", json.dumps({"date": "2020-01-01", "head": ""}))
        result = session_start.decide({"session_id": SID}, self.repo.root)
        state = json.loads((self.repo.root / ".claude/state" / f"{SID}.json").read_text())
        self.assertEqual(state["date"], "2020-01-01")
        self.assertIn("logs/sessions/2020-01-01-abcd1234.md", result["hookSpecificOutput"]["additionalContext"])


class GuardTests(unittest.TestCase):
    root = Path("/proj")

    def edit(self, path, tool="Edit"):
        return guard.decide({"tool_name": tool, "tool_input": {"file_path": path}}, self.root)

    def bash(self, command):
        return guard.decide({"tool_name": "Bash", "tool_input": {"command": command}}, self.root)

    def test_guard_denies_edit_of_raw_csv(self):
        for tool in ("Edit", "Write", "MultiEdit"):
            self.assertEqual(decision(self.edit("data/Metro_x.csv", tool)), "deny")

    def test_guard_denies_absolute_and_dot_slash_paths(self):
        self.assertEqual(decision(self.edit("/proj/data/a.csv")), "deny")
        self.assertEqual(decision(self.edit("./data/a.csv")), "deny")
        self.assertEqual(decision(self.edit("/proj/sql/../data/a.csv")), "deny")

    def test_guard_allows_sources_md(self):
        self.assertIsNone(self.edit("/proj/data/SOURCES.md"))

    def test_guard_allows_sql_file(self):
        self.assertIsNone(self.edit("sql/01_load.sql", "Write"))
        self.assertIsNone(self.edit("/elsewhere/data/a.csv"))

    def test_guard_asks_for_constitution(self):
        self.assertEqual(decision(self.edit("/proj/CONSTITUTION.md")), "ask")

    def test_guard_denies_bash_sed_i_redirect_rm_on_csv(self):
        for command in ("sed -i 's/a/b/' data/a.csv",
                        "echo x > data/a.csv",
                        "cd /proj && rm data/a.csv",
                        "mv ./data/a.csv data/b.csv",
                        "echo x | tee -a /proj/data/a.csv",
                        "cp /tmp/new.csv data/a.csv",
                        "git rm data/a.csv",
                        "truncate -s 0 data/a.csv"):
            self.assertEqual(decision(self.bash(command)), "deny", command)

    def test_guard_allows_bash_head_on_csv(self):
        for command in ("head -3 data/a.csv",
                        "head data/a.csv > /tmp/out.txt",
                        "cp data/a.csv /tmp/",
                        "sha256sum data/*.csv",
                        "sed -n 1p data/a.csv",
                        "rm -rf /tmp/scratch"):
            self.assertIsNone(self.bash(command), command)

    def test_guard_ignores_other_tools(self):
        self.assertIsNone(guard.decide({"tool_name": "Read", "tool_input": {"file_path": "data/a.csv"}}, self.root))


class StopTests(unittest.TestCase):
    def setUp(self):
        self.repo = GitRepo()
        session_start.decide({"session_id": SID}, self.repo.root)
        self.journal = f"logs/sessions/{datetime.date.today().isoformat()}-abcd1234.md"

    def tearDown(self):
        self.repo.cleanup()

    def stop(self, **extra):
        return stop_journal.decide({"session_id": SID, **extra}, self.repo.root)

    def test_stop_allows_when_nothing_changed(self):
        self.assertIsNone(self.stop())

    def test_stop_blocks_when_changed_and_no_journal(self):
        self.repo.write("sql/01_a.sql", "select 1")
        result = self.stop()
        self.assertEqual(result["decision"], "block")
        self.assertIn(self.journal, result["reason"])
        self.assertIn("docs/templates/session-journal.md", result["reason"])

    def test_stop_blocks_when_journal_has_tbd(self):
        self.repo.write("sql/01_a.sql", "select 1")
        self.repo.write(self.journal, GOOD_JOURNAL.replace("\ng\n", "\n_TBD_\n"))
        result = self.stop()
        self.assertEqual(result["decision"], "block")
        self.assertIn("_TBD_", result["reason"])

    def test_stop_allows_with_complete_journal(self):
        self.repo.write("sql/01_a.sql", "select 1")
        self.repo.write(self.journal, GOOD_JOURNAL)
        self.repo.commit()
        self.assertIsNone(self.stop())

    def test_stop_blocks_up_to_limit_then_warns(self):
        self.repo.write("sql/01_a.sql", "select 1")
        self.assertEqual(self.stop()["decision"], "block")
        self.assertEqual(self.stop(stop_hook_active=True)["decision"], "block")
        self.assertEqual(self.stop(stop_hook_active=True)["decision"], "block")
        final = self.stop(stop_hook_active=True)
        self.assertNotIn("decision", final)
        self.assertIn(self.journal, final["systemMessage"])

    def test_stop_counter_resets_after_journal_completed(self):
        self.repo.write("sql/01_a.sql", "select 1")
        self.stop()
        self.stop(stop_hook_active=True)
        self.repo.write(self.journal, GOOD_JOURNAL)
        self.repo.commit()
        self.assertIsNone(self.stop(stop_hook_active=True))
        self.repo.write(self.journal, GOOD_JOURNAL.replace("\ng\n", "\n_TBD_\n"))
        for _ in range(3):
            self.assertEqual(self.stop()["decision"], "block")

    def test_stop_limit_applies_without_state_file(self):
        other = "77777777-0000"
        self.repo.write("sql/01_a.sql", "select 1")
        self.assertEqual(stop_journal.decide({"session_id": other}, self.repo.root)["decision"], "block")
        retry = {"session_id": other, "stop_hook_active": True}
        for _ in range(2):
            self.assertEqual(stop_journal.decide(retry, self.repo.root)["decision"], "block")
        self.assertIn("systemMessage", stop_journal.decide(retry, self.repo.root))

    def test_stop_new_turn_blocks_again_after_limit(self):
        self.repo.write("sql/01_a.sql", "select 1")
        self.stop()
        for _ in range(2):
            self.stop(stop_hook_active=True)
        self.assertIn("systemMessage", self.stop(stop_hook_active=True))
        self.assertEqual(self.stop()["decision"], "block")

    def test_stop_detects_committed_change(self):
        self.repo.write("sql/01_a.sql", "select 1")
        self.repo.commit()
        self.assertEqual(self.stop()["decision"], "block")

    def test_stop_without_state_uses_working_tree_only(self):
        other = "99999999-0000"
        self.assertIsNone(stop_journal.decide({"session_id": other}, self.repo.root))
        self.repo.write("sql/01_a.sql", "select 1")
        self.assertEqual(stop_journal.decide({"session_id": other}, self.repo.root)["decision"], "block")


class GuardWorktreeTests(unittest.TestCase):
    def setUp(self):
        from tests.helpers import make_repo_with_worktree
        self.repo, self.wt = make_repo_with_worktree()

    def tearDown(self):
        self.repo.cleanup()

    def edit(self, path, project=None):
        return guard.decide({"tool_name": "Edit", "tool_input": {"file_path": str(path)}},
                            project or self.repo.root)

    def test_guard_denies_raw_csv_inside_worktree(self):
        self.assertEqual(decision(self.edit(self.wt / "data" / "a.csv")), "deny")
        self.assertEqual(decision(self.edit(self.wt / "data" / "a.csv", project=self.wt)), "deny")
        self.assertEqual(decision(guard.decide(
            {"tool_name": "Bash", "tool_input": {"command": f"cd {self.wt} && rm data/a.csv"}},
            self.repo.root)), "deny")

    def test_guard_asks_for_constitution_inside_worktree(self):
        self.assertEqual(decision(self.edit(self.wt / "CONSTITUTION.md")), "ask")

    def test_guard_allows_worktree_sql(self):
        self.assertIsNone(self.edit(self.wt / "sql" / "01_a.sql"))


class GuardPrecisionTests(unittest.TestCase):
    def bash(self, command):
        return guard.decide({"tool_name": "Bash", "tool_input": {"command": command}}, Path("/proj"))

    def test_guard_allows_redirect_to_other_data_paths(self):
        for command in ("grep x f > results/data/out.csv",
                        "echo 1 > exports/metadata/x.csv",
                        "echo 1 > data/derived/x.csv"):
            self.assertIsNone(self.bash(command), command)

    def test_guard_allows_quoted_mentions(self):
        for command in ("echo 'a > data/x.csv'", 'git commit -m "rm data/a.csv"'):
            self.assertIsNone(self.bash(command), command)

    def test_guard_allows_heredoc_body_mentions(self):
        self.assertIsNone(self.bash("cat > /tmp/s.sh <<'EOF'\nrm data/a.csv\nEOF"))
        self.assertIsNone(self.bash("python3 - <<EOF\nopen('x').write('> data/a.csv')\nEOF\necho done"))
        self.assertEqual(decision(self.bash("cat > data/a.csv <<'EOF'\nx\nEOF")), "deny")
        self.assertEqual(decision(self.bash("cat <<EOF > /tmp/x\nhi\nEOF\nrm data/a.csv")), "deny")

    def test_guard_hash_inside_word_is_not_a_comment(self):
        self.assertEqual(decision(self.bash("echo a#b > data/a.csv")), "deny")
        self.assertEqual(decision(self.bash("curl https://x.com/p#frag -o data/a.csv")), "deny")
        self.assertIsNone(self.bash("ls  # rm data/a.csv"))

    def test_guard_quoted_heredoc_marker_hides_nothing(self):
        self.assertEqual(decision(self.bash("echo '<<EOF'\nrm data/a.csv")), "deny")
        self.assertEqual(decision(self.bash("git commit -m 'note <<EOF'\nrm data/a.csv")), "deny")
        self.assertIsNone(self.bash("cat <<-EOF > /tmp/x\n\trm data/a.csv\n\tEOF"))

    def test_guard_closes_remaining_gaps(self):
        for command in ("for f in x; do rm data/a.csv; done",
                        "if true; then rm data/a.csv; fi",
                        "{ rm data/a.csv; }",
                        "! rm data/a.csv",
                        "sudo -u bob rm data/a.csv",
                        "git -C /proj rm data/a.csv",
                        "time -p rm data/a.csv",
                        "nice -n 5 rm data/a.csv",
                        "curl -odata/a.csv https://x",
                        "wget -Odata/a.csv https://x",
                        "cd data && rm a.csv",
                        "cd /proj/data; truncate -s0 a.csv",
                        "perl -pi -e 's/a/b/' data/a.csv",
                        "find data -name '*.csv' -delete",
                        "find . -name '*.csv' -exec rm {} +"):
            self.assertEqual(decision(self.bash(command)), "deny", command)

    def test_guard_remaining_gap_fixes_do_not_overblock(self):
        for command in ("cd sql && rm a.csv",
                        "cd data && head a.csv",
                        "find /tmp -name '*.csv' -delete",
                        "find data -name '*.csv'",
                        "perl -ne 'print' data/a.csv",
                        "for f in data/*.csv; do wc -l $f; done"):
            self.assertIsNone(self.bash(command), command)

    def test_guard_denies_uppercase_csv(self):
        self.assertEqual(decision(self.bash("truncate -s0 data/X.CSV")), "deny")
        self.assertEqual(decision(guard.decide(
            {"tool_name": "Edit", "tool_input": {"file_path": "data/X.CSV"}}, Path("/proj"))), "deny")

    def test_guard_resolves_symlinked_project(self):
        repo = TempRepo()
        try:
            real = repo.root / "real"
            (real / "data").mkdir(parents=True)
            link = repo.root / "link"
            link.symlink_to(real)
            result = guard.decide({"tool_name": "Edit",
                                   "tool_input": {"file_path": str(real / "data" / "a.csv")}}, link)
            self.assertEqual(decision(result), "deny")
        finally:
            repo.cleanup()


class WorkflowTests(unittest.TestCase):
    def test_workflow_runs_once_and_read_only(self):
        text = (REPO / ".github/workflows/governance.yml").read_text()
        self.assertIn("\n  push:\n", text)
        self.assertNotIn("pull_request", text.split("on:", 1)[1].split("permissions:", 1)[0])
        self.assertRegex(text, r"permissions:\s*\n\s+contents:\s*read")


class ScriptTests(unittest.TestCase):
    def test_hook_script_survives_garbage_stdin(self):
        for name in ("session_start", "guard", "git_guard", "agent_guard", "session_end"):
            run = subprocess.run([sys.executable, str(HOOKS / f"{name}.py")], input="not json",
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, name)
            self.assertEqual(run.stdout, "", name)

    def test_guard_script_prints_deny_json(self):
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "data/x.csv"}, "cwd": str(REPO)})
        run = subprocess.run([sys.executable, str(HOOKS / "guard.py")], input=payload,
                             capture_output=True, text=True)
        self.assertEqual(json.loads(run.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")


class ReviewFixHookTests(unittest.TestCase):
    def test_guard_denies_download_and_dd_and_sudo_writes(self):
        for command in ("curl -sL https://x/y.csv -o data/a.csv",
                        "curl --output data/a.csv https://x",
                        "wget -O data/a.csv https://x",
                        "dd if=/tmp/x of=data/a.csv",
                        "sed --in-place=.bak 's/a/b/' data/a.csv",
                        "sudo rm data/a.csv"):
            self.assertEqual(decision(GuardTests().bash(command)), "deny", command)

    def test_guard_allows_download_elsewhere(self):
        self.assertIsNone(GuardTests().bash("curl -o /tmp/a.csv https://x && head data/a.csv"))

    def test_stop_ignores_changes_that_existed_before_session(self):
        repo = GitRepo()
        try:
            repo.write("sql/01_wip.sql", "owner work in progress")
            session_start.decide({"session_id": SID}, repo.root)
            self.assertIsNone(stop_journal.decide({"session_id": SID}, repo.root))
            repo.write("sql/02_new.sql", "agent work")
            self.assertEqual(stop_journal.decide({"session_id": SID}, repo.root)["decision"], "block")
        finally:
            repo.cleanup()

    def test_settings_hooks_fall_back_to_python(self):
        settings = json.loads((REPO / ".claude/settings.json").read_text())
        for event in settings["hooks"].values():
            for entry in event:
                for hook in entry["hooks"]:
                    self.assertIn("|| python ", hook["command"])


if __name__ == "__main__":
    unittest.main()
