from __future__ import annotations

import unittest
from datetime import date

from code_streak_dashboard.github_api import GitHubProfileData
from code_streak_dashboard.metrics import build_metrics
from code_streak_dashboard.scanner import ScanStats
from code_streak_dashboard.svg import render_dashboard_svg


class SvgTest(unittest.TestCase):
    def test_render_dashboard_svg_contains_expected_sections(self) -> None:
        metrics = build_metrics(
            GitHubProfileData(username="octo", display_name="Octo", contribution_days=[], repositories=[]),
            ScanStats(),
            today=date(2026, 5, 14),
        )

        svg = render_dashboard_svg(metrics)

        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("Coding over time", svg)
        self.assertIn("Language mix", svg)
        self.assertIn("OpenMoji", svg)


if __name__ == "__main__":
    unittest.main()
