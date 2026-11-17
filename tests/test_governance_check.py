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


HEADER = "| File | Source | URL | Added | SHA-256 |\n|---|---|---|---|---|\n"


def sha(text):
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


def row(name, digest):
    return f"| `{name}` | Zillow | https://example.com | 2026-10-19 | `{digest}` |\n"


class DataManifestTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()

    def tearDown(self):
        self.repo.cleanup()

    def test_csv_without_row_flagged(self):
        self.repo.write("data/a.csv", "1,2")
        self.repo.write("data/SOURCES.md", "Intro\n\n" + HEADER)
        problems = gc.check_data_manifest(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("data/a.csv", problems[0])

    def test_row_without_file_flagged(self):
        self.repo.write("data/SOURCES.md", HEADER + row("gone.csv", sha("x")))
        problems = gc.check_data_manifest(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("gone.csv", problems[0])

    def test_hash_mismatch_flagged(self):
        self.repo.write("data/a.csv", "edited")
        self.repo.write("data/SOURCES.md", HEADER + row("a.csv", sha("original")))
        problems = gc.check_data_manifest(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("changed", problems[0])
        self.assertIn("data/a.csv", problems[0])

    def test_matching_manifest_passes(self):
        self.repo.write("data/a.csv", "1,2")
        self.repo.write("data/SOURCES.md", "Intro\n\n" + HEADER + row("a.csv", sha("1,2")))
        self.assertEqual(gc.check_data_manifest(self.repo.root), [])

    def test_missing_manifest_flagged_only_when_csv_present(self):
        self.repo.write("data/.gitkeep", "")
        self.assertEqual(gc.check_data_manifest(self.repo.root), [])
        self.repo.write("data/a.csv", "1,2")
        problems = gc.check_data_manifest(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("SOURCES.md", problems[0])

    def test_check_repo_includes_manifest(self):
        self.repo.write("data/a.csv", "1,2")
        self.assertTrue(any("SOURCES.md" in p for p in gc.check_repo(self.repo.root)))


VALID_RECORDS = {
    "logs/sessions/2026-11-17-abcd1234.md":
        {"Goal": "g", "What changed": "c", "Tests run": "t", "Bugs found": "None", "Next steps": "n"},
    "logs/bugs/BUG-001-bad-join.md":
        {"Status": "Fixed", "Found": "2026-11-17", "What happened": "w", "Cause": "c", "Fix": "f",
         "Test log": "logs/tests/2026-11-17-join-check.md"},
    "logs/tests/2026-11-17-join-check.md":
        {"What was tested": "w", "How": "h", "Result": "PASS", "Bugs": "None"},
    "docs/decisions/0001-adopt-governance.md":
        {"Date": "2026-11-17", "Status": "Accepted", "Decision": "d", "Reason": "r", "Alternatives": "a"},
}


def record(sections, newline="\n", trailing=""):
    parts = ["# Title"]
    for heading, body in sections.items():
        parts += ["", f"## {heading}{trailing}", body]
    return newline.join(parts) + newline


class RecordTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()

    def tearDown(self):
        self.repo.cleanup()

    def test_valid_record_of_each_type_passes(self):
        for rel, sections in VALID_RECORDS.items():
            self.repo.write(rel, record(sections))
        self.repo.write("logs/bugs/.gitkeep", "")
        self.assertEqual(gc.check_records(self.repo.root), [])

    def test_missing_heading_flagged(self):
        sections = dict(VALID_RECORDS["logs/tests/2026-11-17-join-check.md"])
        del sections["How"]
        self.repo.write("logs/tests/2026-11-17-join-check.md", record(sections))
        problems = gc.check_records(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("How", problems[0])

    def test_empty_section_flagged(self):
        sections = dict(VALID_RECORDS["logs/tests/2026-11-17-join-check.md"], How="   ")
        self.repo.write("logs/tests/2026-11-17-join-check.md", record(sections))
        problems = gc.check_records(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("How", problems[0])

    def test_tbd_flagged(self):
        sections = dict(VALID_RECORDS["logs/sessions/2026-11-17-abcd1234.md"], Goal="_TBD_")
        self.repo.write("logs/sessions/2026-11-17-abcd1234.md", record(sections))
        problems = gc.check_records(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("_TBD_", problems[0])

    def test_bad_record_name_flagged(self):
        self.repo.write("logs/bugs/bad join.md", record(VALID_RECORDS["logs/bugs/BUG-001-bad-join.md"]))
        problems = gc.check_records(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("logs/bugs/bad join.md", problems[0])

    def test_bug_status_must_be_open_or_fixed(self):
        sections = dict(VALID_RECORDS["logs/bugs/BUG-001-bad-join.md"], Status="Done")
        self.repo.write("logs/bugs/BUG-001-bad-join.md", record(sections))
        problems = gc.check_records(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("Status", problems[0])

    def test_crlf_and_trailing_spaces_accepted(self):
        for rel, sections in VALID_RECORDS.items():
            self.repo.write(rel, record(sections, newline="\r\n", trailing="  "))
        self.assertEqual(gc.check_records(self.repo.root), [])

    def test_templates_folder_not_checked(self):
        self.repo.write("docs/templates/bug-log.md", "## Status\n_TBD_\n")
        self.assertEqual(gc.check_records(self.repo.root), [])

    def test_stray_file_in_logs_flagged(self):
        self.repo.write("logs/notes.md", "hi")
        self.repo.write("logs/misc/a.md", "hi")
        problems = gc.check_records(self.repo.root)
        self.assertEqual(len(problems), 2)

    def test_check_repo_includes_records(self):
        self.repo.write("logs/notes.md", "hi")
        self.assertTrue(any("logs/notes.md" in p for p in gc.check_repo(self.repo.root)))


class ReviewFixTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()

    def tearDown(self):
        self.repo.cleanup()

    def test_no_compiled_python_tracked(self):
        import subprocess
        from tests.helpers import REPO
        tracked = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True).stdout
        self.assertNotIn("__pycache__", tracked)

    def test_crlf_copy_of_raw_file_matches_fingerprint(self):
        self.repo.write("data/a.csv", "1,2\r\n3,4\r\n")
        self.repo.write("data/SOURCES.md", HEADER + row("a.csv", sha("1,2\n3,4\n")))
        self.assertEqual(gc.check_data_manifest(self.repo.root), [])

    def test_filled_template_with_instruction_comment_passes(self):
        from tests.helpers import REPO
        filled = {"Open or Fixed": "Open", "PASS or FAIL": "PASS", "Proposed, Accepted or Replaced": "Accepted"}
        for name, folder, filename in (("session-journal", "logs/sessions", "2026-11-17-abcd1234.md"),
                                       ("bug-log", "logs/bugs", "BUG-001-x.md"),
                                       ("test-log", "logs/tests", "2026-11-17-x.md"),
                                       ("decision", "docs/decisions", "0001-x.md")):
            lines = (REPO / "docs/templates" / f"{name}.md").read_text().split("\n")
            out = []
            for line in lines:
                if line.startswith("_TBD_"):
                    rest = line[len("_TBD_"):].strip()
                    line = filled.get(rest, "Done.")
                out.append(line.replace("# NNNN: _TBD_", "# 0001:").replace(": _TBD_", ":"))
            self.assertEqual(gr.record_problems(folder, filename, "\n".join(out)), [], name)


class CheckerAccuracyTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()

    def tearDown(self):
        self.repo.cleanup()

    def test_uppercase_csv_is_raw_data(self):
        self.repo.write("data/A.CSV", "1,2")
        self.repo.write("data/SOURCES.md", HEADER)
        problems = gc.check_data_manifest(self.repo.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("not listed", problems[0])
        self.repo.write("data/SOURCES.md", HEADER + row("A.CSV", sha("1,2")))
        self.assertEqual(gc.check_data_manifest(self.repo.root), [])
        self.assertEqual(gc.check_layout(self.repo.root), [])

    def test_bom_before_first_heading_accepted(self):
        text = "﻿## Goal\ng\n## What changed\nc\n## Tests run\nt\n## Bugs found\nNone\n## Next steps\nNone\n"
        self.assertEqual(gr.record_problems("logs/sessions", "2026-11-17-abcd1234.md", text), [])

    def test_bom_in_sources_accepted(self):
        self.repo.write("data/a.csv", "1,2")
        self.repo.write("data/SOURCES.md", "﻿" + HEADER + row("a.csv", sha("1,2")))
        self.assertEqual(gc.check_data_manifest(self.repo.root), [])

    def test_sources_wrong_header_reported(self):
        self.repo.write("data/a.csv", "1,2")
        self.repo.write("data/SOURCES.md", "| file | source | url | added | SHA256 |\n|---|---|---|---|---|\n"
                        + row("a.csv", sha("1,2")))
        problems = gc.check_data_manifest(self.repo.root)
        self.assertTrue(any("SHA-256" in p and "header" in p for p in problems), problems)

    def test_sources_wrong_cell_count_reported(self):
        self.repo.write("data/a.csv", "1,2")
        bad = f"| `a.csv` | Zillow | https://x.com/a|b | 2026-10-19 | `{sha('1,2')}` |\n"
        self.repo.write("data/SOURCES.md", HEADER + bad)
        problems = gc.check_data_manifest(self.repo.root)
        self.assertTrue(any("a.csv" in p and "5 columns" in p for p in problems), problems)

    def test_sources_bad_hash_reported(self):
        self.repo.write("data/a.csv", "1,2")
        self.repo.write("data/SOURCES.md", HEADER + row("a.csv", "abc"))
        problems = gc.check_data_manifest(self.repo.root)
        self.assertTrue(any("64" in p for p in problems), problems)

    def test_git_repo_ignores_gitignored_clutter(self):
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=self.repo.root, check=True)
        self.repo.write(".gitignore", ".DS_Store\n")
        self.repo.write(".DS_Store", "junk")
        self.assertEqual(gc.check_layout(self.repo.root), [])
        self.repo.write("notes.txt")
        self.assertEqual(len(gc.check_layout(self.repo.root)), 1)

    def test_main_fingerprint_matches_checker(self):
        path = self.repo.write("data/a.csv", "1,2\r\n3,4\r\n")
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(gc.main(["--fingerprint", str(path)]), 0)
        self.assertEqual(out.getvalue().strip(), sha("1,2\n3,4\n"))

    def test_non_git_folder_still_walked(self):
        self.repo.write("notes.txt")
        self.assertEqual(len(gc.check_layout(self.repo.root)), 1)


if __name__ == "__main__":
    unittest.main()
