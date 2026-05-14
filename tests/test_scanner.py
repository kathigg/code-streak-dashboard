from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from code_streak_dashboard.scanner import scan_checkout


class ScannerTest(unittest.TestCase):
    def test_scan_checkout_counts_comments_and_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            src = tmp_path / "src"
            tests = tmp_path / "tests"
            src.mkdir()
            tests.mkdir()
            (src / "app.py").write_text(
                "# module comment\n\n"
                "def add(a, b):\n"
                "    return a + b  # inline comment is intentionally not counted\n",
                encoding="utf-8",
            )
            (tests / "test_app.py").write_text(
                "def test_add():\n"
                "    assert 1 + 1 == 2\n",
                encoding="utf-8",
            )

            stats = scan_checkout(tmp_path)

        self.assertEqual(stats.source_files, 2)
        self.assertEqual(stats.comment_lines, 1)
        self.assertEqual(stats.test_files, 1)
        self.assertEqual(stats.test_cases, 1)
        self.assertEqual(stats.test_lines, 2)


if __name__ == "__main__":
    unittest.main()
