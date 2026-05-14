from __future__ import annotations

import unittest
from datetime import date, timedelta

from code_streak_dashboard.github_api import ContributionDay, GitHubProfileData, RepositoryInfo
from code_streak_dashboard.metrics import build_metrics, current_streak, longest_streak, streak_awards
from code_streak_dashboard.scanner import ScanStats


class MetricsTest(unittest.TestCase):
    def test_current_streak_counts_yesterday_with_grace_window(self) -> None:
        today = date(2026, 5, 14)
        contributions = {
            today - timedelta(days=3): 1,
            today - timedelta(days=2): 2,
            today - timedelta(days=1): 1,
            today: 0,
        }

        self.assertEqual(current_streak(contributions, today=today), 3)

    def test_current_streak_is_zero_when_latest_active_day_is_stale(self) -> None:
        today = date(2026, 5, 14)
        contributions = {
            today - timedelta(days=3): 1,
            today - timedelta(days=2): 2,
            today - timedelta(days=1): 0,
            today: 0,
        }

        self.assertEqual(current_streak(contributions, today=today), 0)

    def test_longest_streak_finds_max_run(self) -> None:
        start = date(2026, 5, 1)
        contributions = {
            start + timedelta(days=0): 1,
            start + timedelta(days=1): 1,
            start + timedelta(days=2): 0,
            start + timedelta(days=3): 1,
            start + timedelta(days=4): 1,
            start + timedelta(days=5): 1,
        }

        self.assertEqual(longest_streak(contributions), 3)

    def test_build_metrics_rolls_up_languages(self) -> None:
        profile = GitHubProfileData(
            username="octo",
            display_name=None,
            contribution_days=[
                ContributionDay(date="2026-05-13", count=1),
                ContributionDay(date="2026-05-14", count=2),
            ],
            repositories=[
                RepositoryInfo(
                    name="demo",
                    clone_url="https://github.com/octo/demo.git",
                    html_url="https://github.com/octo/demo",
                    languages={
                        "Python": {"size": 80, "color": "#3572A5"},
                        "TypeScript": {"size": 20, "color": "#3178c6"},
                    },
                )
            ],
            total_contributions=3,
        )

        metrics = build_metrics(
            profile,
            ScanStats(comment_lines=4, test_cases=2),
            today=date(2026, 5, 14),
        )

        self.assertEqual(metrics.current_streak, 2)
        self.assertEqual(metrics.comment_lines, 4)
        self.assertEqual(metrics.test_cases, 2)
        self.assertEqual(metrics.languages[0].name, "Python")
        self.assertEqual(round(metrics.languages[0].percent, 1), 0.8)
        self.assertEqual(metrics.awards[0].title, "First Spark")
        self.assertTrue(metrics.awards[0].unlocked)

    def test_streak_awards_unlock_by_longest_and_activate_by_current(self) -> None:
        awards = streak_awards(current_streak=13, longest_streak=30)
        by_threshold = {award.threshold: award for award in awards}

        self.assertTrue(by_threshold[30].unlocked)
        self.assertFalse(by_threshold[30].active)
        self.assertFalse(by_threshold[60].unlocked)


if __name__ == "__main__":
    unittest.main()
