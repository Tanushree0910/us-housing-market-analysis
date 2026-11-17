import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from tests.helpers import TempRepo

import governance_check as gc
import governance_rules as gr


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()

    def tearDown(self):
        self.repo.cleanup()

    def test_clean_repo_passes(self):
        self.repo.write("README.md")
        self.repo.write("sql/01_load_zhvi.sql")
        self.repo.write("data/x.csv")
        self.assertEqual(gc.check_layout(self.repo.root), [])

    def test_unknown_top_level_flagged(self):
        self.repo.write("notes.txt")
        problems = gc.check_layout(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("notes.txt", problems[0])

    def test_bad_sql_name_flagged(self):
        self.repo.write("sql/LoadData.sql")
        problems = gc.check_layout(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("sql/LoadData.sql", problems[0])

    def test_wrong_type_in_screenshots_flagged(self):
        self.repo.write("screenshots/chart.gif")
        problems = gc.check_layout(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("screenshots/chart.gif", problems[0])

    def test_nested_file_in_ruled_folder_flagged(self):
        self.repo.write("sql/old/01_a.sql")
        problems = gc.check_layout(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("sql/old/01_a.sql", problems[0])

    def test_oversize_file_flagged(self):
        self.repo.write("README.md", "x" * 11)
        with mock.patch.object(gr, "MAX_FILE_BYTES", 10):
            problems = gc.check_sizes(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("README.md", problems[0])

    def test_git_dir_ignored(self):
        self.repo.write(".git/whatever")
        self.repo.write(".superpowers/sdd/x.md")
        self.repo.write("tools/__pycache__/a.pyc")
        self.assertEqual(gc.check_layout(self.repo.root), [])

    def test_main_returns_1_on_problem_and_0_when_clean(self):
        self.repo.write("README.md")
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(gc.main([str(self.repo.root)]), 0)
        self.assertIn("OK: no governance problems", out.getvalue())
        self.repo.write("notes.txt")
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(gc.main([str(self.repo.root)]), 1)
        self.assertIn("FAILED: 1 problem(s)", out.getvalue())


if __name__ == "__main__":
    unittest.main()
