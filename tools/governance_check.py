"""Check the repo against the constitution. Run: python3 tools/governance_check.py"""
import sys
from pathlib import Path

import governance_rules as rules


def check_layout(root: Path) -> list[str]:
    """Article 3: top-level entries and per-folder file names."""
    problems = []
    for rel in rules.iter_files(root):
        top = rel.parts[0]
        if top not in rules.ALLOWED_TOP_LEVEL:
            problems.append(f"{rel.as_posix()}: '{top}' is not an allowed top-level item (CONSTITUTION.md Article 3)")
            continue
        if top in rules.FOLDER_RULES:
            if len(rel.parts) != 2:
                problems.append(f"{rel.as_posix()}: '{top}/' must not contain sub-folders (Article 3)")
            elif not rules.FOLDER_RULES[top].match(rel.name):
                problems.append(f"{rel.as_posix()}: wrong name or type for '{top}/', expected {rules.FOLDER_HINTS[top]} (Article 3)")
    return problems


def check_sizes(root: Path) -> list[str]:
    """Article 3: no file over the size limit."""
    limit_mb = rules.MAX_FILE_BYTES / (1024 * 1024)
    problems = []
    for rel in rules.iter_files(root):
        size = (Path(root) / rel).stat().st_size
        if size > rules.MAX_FILE_BYTES:
            problems.append(f"{rel.as_posix()}: file is {size / (1024 * 1024):.1f} MB, limit is {limit_mb:.0f} MB (Article 3)")
    return problems


def check_repo(root: Path) -> list[str]:
    root = Path(root)
    return check_layout(root) + check_sizes(root)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    problems = check_repo(root)
    for problem in problems:
        print(problem)
    if problems:
        print(f"FAILED: {len(problems)} problem(s)")
        return 1
    print("OK: no governance problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
