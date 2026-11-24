"""Shared test helpers: build throwaway repos and import the tools modules."""
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))


class TempRepo:
    """A temporary folder that behaves like a repo checkout."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def write(self, rel, content="x"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8", newline="")
        return path

    def cleanup(self):
        self._tmp.cleanup()


def run_git(root, *args):
    """Run git in root with a throwaway identity; return stdout."""
    import subprocess
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
                          cwd=root, check=True, capture_output=True, text=True).stdout


def make_repo_with_worktree(branch="feature"):
    """A repo on 'main' with one commit, plus a worktree at .worktrees/w on `branch`."""
    repo = TempRepo()
    run_git(repo.root, "init", "-q", "-b", "main")
    repo.write("README.md", "hi")
    repo.write(".gitignore", ".worktrees/\n.claude/state/\n")
    run_git(repo.root, "add", "-A")
    run_git(repo.root, "commit", "-q", "-m", "init")
    run_git(repo.root, "worktree", "add", "-q", ".worktrees/w", "-b", branch)
    return repo, repo.root / ".worktrees" / "w"
