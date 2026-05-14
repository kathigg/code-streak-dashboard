from __future__ import annotations

import re
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .github_api import RepositoryInfo


SOURCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".m",
    ".mm",
    ".php",
    ".py",
    ".r",
    ".rb",
    ".rs",
    ".scala",
    ".scss",
    ".sh",
    ".sql",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}

HASH_COMMENT_EXTENSIONS = {".py", ".rb", ".r", ".sh", ".yaml", ".yml"}
SLASH_COMMENT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".m",
    ".mm",
    ".php",
    ".rs",
    ".scala",
    ".scss",
    ".swift",
    ".ts",
    ".tsx",
    ".vue",
}
SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".next",
    ".nuxt",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}
TEST_CASE_PATTERNS = [
    re.compile(r"^\s*def\s+test_[A-Za-z0-9_]*\s*\("),
    re.compile(r"^\s*class\s+Test[A-Za-z0-9_]*\s*[:(]"),
    re.compile(r"^\s*(it|test)\s*\("),
    re.compile(r"^\s*@Test\b"),
    re.compile(r"^\s*#\s*\[\s*test\s*\]"),
    re.compile(r"^\s*func\s+Test[A-Za-z0-9_]*\s*\("),
]


@dataclass
class ScanStats:
    source_files: int = 0
    source_lines: int = 0
    comment_lines: int = 0
    test_files: int = 0
    test_lines: int = 0
    test_cases: int = 0
    scanned_repositories: int = 0
    failed_repositories: int = 0

    def merge(self, other: "ScanStats") -> None:
        self.source_files += other.source_files
        self.source_lines += other.source_lines
        self.comment_lines += other.comment_lines
        self.test_files += other.test_files
        self.test_lines += other.test_lines
        self.test_cases += other.test_cases
        self.scanned_repositories += other.scanned_repositories
        self.failed_repositories += other.failed_repositories


def scan_repositories(repositories: list[RepositoryInfo], limit: int) -> ScanStats:
    """Clone public repositories and scan source files for comments and tests."""

    stats = ScanStats()
    selected = [
        repo
        for repo in repositories
        if not repo.archived and not repo.fork and repo.clone_url.startswith("https://")
    ][:limit]
    if not selected:
        return stats

    with tempfile.TemporaryDirectory(prefix="code-streak-dashboard-") as tmp:
        tmp_path = Path(tmp)
        for repo in selected:
            destination = tmp_path / _safe_repo_dir(repo.name)
            try:
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--depth",
                        "1",
                        "--filter=blob:none",
                        "--single-branch",
                        "--quiet",
                        repo.clone_url,
                        str(destination),
                    ],
                    check=True,
                    env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
                    timeout=120,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                repo_stats = scan_checkout(destination)
                repo_stats.scanned_repositories = 1
                stats.merge(repo_stats)
            except (subprocess.SubprocessError, OSError):
                stats.failed_repositories += 1
            finally:
                shutil.rmtree(destination, ignore_errors=True)
    return stats


def scan_checkout(root: Path) -> ScanStats:
    stats = ScanStats()
    for path in root.rglob("*"):
        if not path.is_file() or _should_skip(path):
            continue
        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue

        text = _read_text(path)
        if text is None:
            continue

        is_test = is_test_file(path)
        stats.source_files += 1
        lines = text.splitlines()
        stats.source_lines += sum(1 for line in lines if line.strip())
        stats.comment_lines += count_comment_lines(lines, path.suffix.lower())
        if is_test:
            stats.test_files += 1
            stats.test_lines += sum(1 for line in lines if line.strip())
            stats.test_cases += count_test_cases(lines)
    return stats


def is_test_file(path: Path) -> bool:
    lower_parts = [part.lower() for part in path.parts]
    name = path.name.lower()
    stem = path.stem.lower()
    return (
        "test" in lower_parts
        or "tests" in lower_parts
        or "__tests__" in lower_parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or ".test." in name
        or ".spec." in name
        or stem.endswith("_spec")
        or stem.endswith("_test")
    )


def count_comment_lines(lines: list[str], suffix: str) -> int:
    comments = 0
    in_block = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if in_block:
            comments += 1
            if "*/" in stripped:
                in_block = False
            continue

        if suffix in HASH_COMMENT_EXTENSIONS and stripped.startswith("#"):
            comments += 1
            continue

        if suffix in {".html", ".vue"} and "<!--" in stripped:
            comments += 1
            continue

        if suffix in SLASH_COMMENT_EXTENSIONS:
            if stripped.startswith("//"):
                comments += 1
            if "/*" in stripped:
                comments += 1
                if "*/" not in stripped.split("/*", 1)[1]:
                    in_block = True

    return comments


def count_test_cases(lines: list[str]) -> int:
    return sum(1 for line in lines if any(pattern.search(line) for pattern in TEST_CASE_PATTERNS))


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def _read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > 2_000_000:
            return None
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _safe_repo_dir(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)
