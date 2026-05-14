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
        self.assertIn("Streak awards", svg)
        self.assertIn("-apple-system", svg)
        self.assertIn("#24292f", svg)
        self.assertIn("#2da44e", svg)
        self.assertNotIn("#ff3d81", svg)
        self.assertNotIn("#39ff14", svg)
        self.assertNotIn("Language mix", svg)
        self.assertNotIn("Contribution rhythm", svg)
        self.assertNotIn("comment lines scanned", svg)
        self.assertNotIn("milestone prizes", svg)
        self.assertNotIn("Unlocked", svg)
        self.assertNotIn("Locked", svg)


if __name__ == "__main__":
    unittest.main()
