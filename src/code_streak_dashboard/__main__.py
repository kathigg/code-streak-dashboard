from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from .github_api import collect_profile_data, github_token
from .metrics import build_metrics
from .scanner import ScanStats, scan_repositories
from .svg import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a GitHub profile code streak dashboard.")
    parser.add_argument(
        "--username",
        default=os.getenv("DASHBOARD_USERNAME") or os.getenv("GITHUB_REPOSITORY_OWNER"),
        help="GitHub username to analyze. Defaults to DASHBOARD_USERNAME or repository owner.",
    )
    parser.add_argument(
        "--output-dir",
        default="dist",
        type=Path,
        help="Directory where dashboard.svg and metrics.json will be written.",
    )
    parser.add_argument(
        "--days",
        default=int(os.getenv("DASHBOARD_DAYS", "365")),
        type=int,
        help="Contribution-history window in days.",
    )
    parser.add_argument(
        "--scan-limit",
        default=int(os.getenv("DASHBOARD_SCAN_LIMIT", "30")),
        type=int,
        help="Maximum number of public repositories to clone for comments/tests.",
    )
    parser.add_argument(
        "--no-repo-scan",
        action="store_true",
        help="Skip cloning repositories and only render GitHub API metrics.",
    )
    parser.add_argument(
        "--today",
        help="Testing hook: override today's date as YYYY-MM-DD.",
    )
    args = parser.parse_args()

    if not args.username:
        parser.error("--username is required when DASHBOARD_USERNAME/GITHUB_REPOSITORY_OWNER is unset")
    if args.days < 30:
        parser.error("--days must be at least 30")

    token = github_token()
    profile = collect_profile_data(username=args.username, token=token, days=args.days)
    scan = ScanStats()
    if not args.no_repo_scan and args.scan_limit > 0:
        scan = scan_repositories(profile.repositories, limit=args.scan_limit)

    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else None
    metrics = build_metrics(profile=profile, scan=scan, today=today)
    write_outputs(metrics=metrics, output_dir=args.output_dir)

    print(f"Wrote dashboard for @{args.username} to {args.output_dir}")
    print(
        f"Streak: {metrics.current_streak} current / {metrics.longest_streak} longest; "
        f"comments: {metrics.comment_lines}; tests: {metrics.test_cases or metrics.test_files}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
