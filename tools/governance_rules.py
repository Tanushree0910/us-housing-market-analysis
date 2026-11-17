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


# Article 2: the data manifest table header in data/SOURCES.md.
SOURCES_HEADER = ["File", "Source", "URL", "Added", "SHA-256"]


def _cells(line: str) -> list[str]:
    return [c.strip().strip("`").strip() for c in line.strip().strip("|").split("|")]


def parse_sources(text: str) -> dict[str, str]:
    """Map raw file name -> SHA-256 from the manifest table."""
    result = {}
    in_table = False
    for line in text.replace("\r\n", "\n").split("\n"):
        if not line.strip().startswith("|"):
            in_table = False
            continue
        cells = _cells(line)
        if cells == SOURCES_HEADER:
            in_table = True
            continue
        if not in_table or all(set(c) <= set("-: ") for c in cells):
            continue
        if len(cells) == len(SOURCES_HEADER):
            result[cells[0]] = cells[4].lower()
    return result


# Article 4: record folders -> (file name pattern, required headings).
RECORD_TYPES = {
    "logs/sessions": (re.compile(r"^\d{4}-\d{2}-\d{2}-[0-9a-zA-Z]{8}\.md$"),
                      ["Goal", "What changed", "Tests run", "Bugs found", "Next steps"]),
    "logs/bugs": (re.compile(r"^BUG-\d{3}-[a-z0-9-]+\.md$"),
                  ["Status", "Found", "What happened", "Cause", "Fix", "Test log"]),
    "logs/tests": (re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+\.md$"),
                   ["What was tested", "How", "Result", "Bugs"]),
    "docs/decisions": (re.compile(r"^\d{4}-[a-z0-9-]+\.md$"),
                       ["Date", "Status", "Decision", "Reason", "Alternatives"]),
}

RECORD_NAME_HINTS = {
    "logs/sessions": "YYYY-MM-DD-<first 8 characters of session id>.md",
    "logs/bugs": "BUG-NNN-kebab-title.md",
    "logs/tests": "YYYY-MM-DD-kebab-title.md",
    "docs/decisions": "NNNN-kebab-title.md",
}

ALLOWED_VALUES = {
    ("logs/bugs", "Status"): {"Open", "Fixed"},
    ("logs/tests", "Result"): {"PASS", "FAIL"},
    ("docs/decisions", "Status"): {"Proposed", "Accepted", "Replaced"},
}


def _sections(text: str) -> dict[str, list[str]]:
    """Heading name -> non-empty body lines, for every '## ' heading."""
    sections = {}
    current = None
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.rstrip()
        if stripped.startswith("## "):
            current = stripped[3:].strip()
            sections.setdefault(current, [])
        elif stripped.startswith("# "):
            current = None
        elif current is not None and stripped.strip():
            sections[current].append(stripped.strip())
    return sections


def record_problems(folder: str, filename: str, text: str) -> list[str]:
    """Everything wrong with one record file, as plain-English messages."""
    pattern, headings = RECORD_TYPES[folder]
    where = f"{folder}/{filename}"
    if not pattern.match(filename):
        return [f"{where}: wrong file name, expected {RECORD_NAME_HINTS[folder]} (Article 4)"]
    problems = []
    if PLACEHOLDER in text:
        problems.append(f"{where}: still contains the placeholder {PLACEHOLDER}; fill in every section (Article 4)")
    sections = _sections(text)
    for heading in headings:
        if heading not in sections:
            problems.append(f"{where}: missing section '## {heading}' (Article 4)")
        elif not sections[heading]:
            problems.append(f"{where}: section '## {heading}' is empty (Article 4)")
        elif (folder, heading) in ALLOWED_VALUES:
            value = sections[heading][0].strip("*` ")
            allowed = ALLOWED_VALUES[(folder, heading)]
            if value not in allowed:
                problems.append(f"{where}: '## {heading}' must be one of {', '.join(sorted(allowed))}, found '{value}' (Article 4)")
    return problems
