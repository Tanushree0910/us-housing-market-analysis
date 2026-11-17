"""Check the repo against the constitution. Run: python3 tools/governance_check.py"""
import hashlib
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


def _sha256(path: Path) -> str:
    """Fingerprint with Windows line endings treated as Unix ones, so a
    Windows checkout of an untouched file still matches."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def check_data_manifest(root: Path) -> list[str]:
    """Article 2: every raw file is listed in data/SOURCES.md and unchanged."""
    root = Path(root)
    csvs = sorted(rel.name for rel in rules.iter_files(root)
                  if len(rel.parts) == 2 and rel.parts[0] == "data" and rel.suffix == ".csv")
    manifest = root / "data" / "SOURCES.md"
    if not manifest.is_file():
        if csvs:
            return ["data/SOURCES.md: missing; every raw data file must be listed there (Article 2)"]
        return []
    listed = rules.parse_sources(manifest.read_text(encoding="utf-8"))
    problems = []
    for name in csvs:
        if name not in listed:
            problems.append(f"data/{name}: not listed in data/SOURCES.md (Article 2)")
        elif _sha256(root / "data" / name) != listed[name]:
            problems.append(f"data/{name}: file has changed since it was recorded in data/SOURCES.md; "
                            "raw data must not be edited (Article 2)")
    for name in sorted(set(listed) - set(csvs)):
        problems.append(f"data/SOURCES.md: lists '{name}' but data/{name} does not exist (Article 2)")
    return problems


def check_records(root: Path) -> list[str]:
    """Article 4: session journals, bug logs, test logs and decisions."""
    root = Path(root)
    problems = []
    for rel in rules.iter_files(root):
        rel_str = rel.as_posix()
        if rel.name == ".gitkeep":
            continue
        folder = rel.parent.as_posix()
        if folder in rules.RECORD_TYPES:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
            problems += rules.record_problems(folder, rel.name, text)
        elif rel.parts[0] == "logs" or rel_str.startswith("docs/decisions/"):
            problems.append(f"{rel_str}: records belong directly in one of "
                            f"{', '.join(sorted(rules.RECORD_TYPES))} (Article 4)")
    return problems


def check_repo(root: Path) -> list[str]:
    root = Path(root)
    return check_layout(root) + check_sizes(root) + check_data_manifest(root) + check_records(root)


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
