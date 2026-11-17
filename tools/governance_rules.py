"""The repo's governance rules in one place.

CONSTITUTION.md states these rules in plain words. The checker
(tools/governance_check.py) and the Claude Code hooks (.claude/hooks/)
read them from here, so each rule is defined once.
"""
import re
from pathlib import Path

# Article 3: what may sit at the top of the repo.
ALLOWED_TOP_LEVEL = {
    "README.md", "CONSTITUTION.md", "CLAUDE.md", ".gitignore",
    "data", "sql", "powerbi", "screenshots", "docs", "logs",
    "tools", "tests", ".github", ".claude",
}

# Article 3: flat folders and the file names allowed in each.
FOLDER_RULES = {
    "data": re.compile(r"^(.+\.csv|SOURCES\.md|\.gitkeep)$"),
    "sql": re.compile(r"^(\d{2}_[a-z0-9_]+\.sql|\.gitkeep)$"),
    "powerbi": re.compile(r"^([a-z0-9_]+\.pbix|\.gitkeep)$"),
    "screenshots": re.compile(r"^([a-z0-9-]+\.(png|jpg)|\.gitkeep)$"),
}

FOLDER_HINTS = {
    "data": "raw .csv files, SOURCES.md or .gitkeep",
    "sql": "NN_snake_case.sql, e.g. 01_load_zhvi.sql",
    "powerbi": "snake_case.pbix",
    "screenshots": "kebab-case.png or kebab-case.jpg",
}

MAX_FILE_BYTES = 50 * 1024 * 1024
PLACEHOLDER = "_TBD_"

# Never walked: git internals, hook scratch state, local tool scratch.
SKIP_DIRS = {".git", ".claude/state", ".superpowers"}
SKIP_DIR_NAMES = {"__pycache__"}


def iter_files(root: Path) -> list[Path]:
    """Every file under root as a repo-relative path, sorted."""
    root = Path(root)
    found = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        rel_str = rel.as_posix()
        if any(rel_str == d or rel_str.startswith(d + "/") for d in SKIP_DIRS):
            continue
        if any(part in SKIP_DIR_NAMES for part in rel.parts):
            continue
        if path.is_file():
            found.append(rel)
    return sorted(found)
