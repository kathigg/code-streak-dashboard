from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from .github_api import GitHubProfileData
from .scanner import ScanStats


LANGUAGE_COLORS = {
    "C": "#555555",
    "C++": "#f34b7d",
    "CSS": "#563d7c",
    "Go": "#00add8",
    "HTML": "#e34c26",
    "Java": "#b07219",
    "JavaScript": "#f1e05a",
    "Jupyter Notebook": "#da5b0b",
    "PHP": "#4f5d95",
    "Python": "#3572A5",
    "R": "#198ce7",
    "Ruby": "#701516",
    "Rust": "#dea584",
    "Shell": "#89e051",
    "Swift": "#F05138",
    "TypeScript": "#3178c6",
}


@dataclass(frozen=True)
class LanguageMetric:
    name: str
    size: int
    color: str
    percent: float


@dataclass(frozen=True)
class MonthMetric:
    key: str
    label: str
    count: int


@dataclass(frozen=True)
class RecentDayMetric:
    date: str
    count: int


@dataclass(frozen=True)
class StreakAwardMetric:
    threshold: int
    title: str
    subtitle: str
    color: str
    unlocked: bool
    active: bool


@dataclass(frozen=True)
class DashboardMetrics:
    username: str
    display_name: str
    generated_at: str
    current_streak: int
    longest_streak: int
    active_days: int
    total_contributions: int
    commit_contributions: int
    pull_request_contributions: int
    review_contributions: int
    issue_contributions: int
    comment_lines: int
    test_cases: int
    test_files: int
    test_lines: int
    source_lines: int
    source_files: int
    scanned_repositories: int
    failed_repositories: int
    languages: list[LanguageMetric]
    monthly: list[MonthMetric]
    recent_days: list[RecentDayMetric]
    awards: list[StreakAwardMetric]


def build_metrics(
    profile: GitHubProfileData,
    scan: ScanStats,
    today: date | None = None,
) -> DashboardMetrics:
    today = today or date.today()
    by_day = {
        datetime.strptime(day.date, "%Y-%m-%d").date(): day.count
        for day in profile.contribution_days
    }
    start = today - timedelta(days=364)
    complete_days = {
        start + timedelta(days=offset): by_day.get(start + timedelta(days=offset), 0)
        for offset in range(365)
    }

    languages = _language_metrics(profile)
    total_contributions = profile.total_contributions or sum(complete_days.values())
    streak = current_streak(complete_days, today=today)
    best_streak = longest_streak(complete_days)

    return DashboardMetrics(
        username=profile.username,
        display_name=profile.display_name or profile.username,
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        current_streak=streak,
        longest_streak=best_streak,
        active_days=sum(1 for count in complete_days.values() if count > 0),
        total_contributions=total_contributions,
        commit_contributions=profile.commit_contributions,
        pull_request_contributions=profile.pull_request_contributions,
        review_contributions=profile.review_contributions,
        issue_contributions=profile.issue_contributions,
        comment_lines=scan.comment_lines,
        test_cases=scan.test_cases,
        test_files=scan.test_files,
        test_lines=scan.test_lines,
        source_lines=scan.source_lines,
        source_files=scan.source_files,
        scanned_repositories=scan.scanned_repositories,
        failed_repositories=scan.failed_repositories,
        languages=languages,
        monthly=monthly_metrics(complete_days, today=today),
        recent_days=[
            RecentDayMetric(date=day.isoformat(), count=complete_days.get(day, 0))
            for day in (today - timedelta(days=offset) for offset in range(48, -1, -1))
        ],
        awards=streak_awards(current_streak=streak, longest_streak=best_streak),
    )


def current_streak(contributions: dict[date, int], today: date) -> int:
    """Return the active streak with a one-day grace window.

    The grace window prevents the streak from showing zero before the current
    day is over when the user contributed yesterday but has not coded yet today.
    """

    if contributions.get(today, 0) > 0:
        cursor = today
    elif contributions.get(today - timedelta(days=1), 0) > 0:
        cursor = today - timedelta(days=1)
    else:
        return 0

    streak = 0
    while contributions.get(cursor, 0) > 0:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def longest_streak(contributions: dict[date, int]) -> int:
    longest = 0
    running = 0
    for day in sorted(contributions):
        if contributions[day] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0
    return longest


def monthly_metrics(contributions: dict[date, int], today: date) -> list[MonthMetric]:
    months = [_shift_month(today.replace(day=1), -offset) for offset in range(11, -1, -1)]
    totals = []
    for month in months:
        next_month = _shift_month(month, 1)
        count = sum(
            contribution_count
            for contribution_day, contribution_count in contributions.items()
            if month <= contribution_day < next_month
        )
        totals.append(MonthMetric(key=month.strftime("%Y-%m"), label=month.strftime("%b"), count=count))
    return totals


def streak_awards(current_streak: int, longest_streak: int) -> list[StreakAwardMetric]:
    """Return GitHub-achievement-style streak prizes.

    Awards stay unlocked once the longest streak reaches the milestone, while
    the active award highlights the current live streak tier.
    """

    definitions = [
        (1, "First Spark", "Start the chain", "#f59e0b"),
        (3, "Kindling", "3-day habit", "#ea580c"),
        (7, "Hot Week", "7-day streak", "#dc2626"),
        (14, "Bonfire", "14-day run", "#b45309"),
        (30, "Forge", "30-day streak", "#7c3aed"),
        (60, "Inferno", "60-day streak", "#be123c"),
        (100, "Century Flame", "100-day streak", "#0f766e"),
        (365, "Phoenix Year", "365-day streak", "#1d4ed8"),
    ]
    return [
        StreakAwardMetric(
            threshold=threshold,
            title=title,
            subtitle=subtitle,
            color=color,
            unlocked=longest_streak >= threshold,
            active=current_streak >= threshold,
        )
        for threshold, title, subtitle, color in definitions
    ]


def _language_metrics(profile: GitHubProfileData) -> list[LanguageMetric]:
    totals: dict[str, dict[str, str | int | None]] = {}
    for repo in profile.repositories:
        if repo.archived or repo.fork:
            continue
        for name, payload in repo.languages.items():
            size = int(payload.get("size") or 0)
            color = payload.get("color") or LANGUAGE_COLORS.get(name) or "#6f7d8c"
            current = totals.setdefault(name, {"size": 0, "color": color})
            current["size"] = int(current["size"]) + size

    total_size = sum(int(payload["size"]) for payload in totals.values())
    if total_size <= 0:
        return []

    ranked = sorted(totals.items(), key=lambda item: int(item[1]["size"]), reverse=True)
    visible = ranked[:6]
    remainder = ranked[6:]
    metrics = [
        LanguageMetric(
            name=name,
            size=int(payload["size"]),
            color=str(payload.get("color") or LANGUAGE_COLORS.get(name) or "#6f7d8c"),
            percent=int(payload["size"]) / total_size,
        )
        for name, payload in visible
    ]
    if remainder:
        other_size = sum(int(payload["size"]) for _, payload in remainder)
        metrics.append(
            LanguageMetric(name="Other", size=other_size, color="#8d99ae", percent=other_size / total_size)
        )
    return metrics


def _shift_month(value: date, offset: int) -> date:
    month_index = value.year * 12 + (value.month - 1) + offset
    year, month_zero_based = divmod(month_index, 12)
    return date(year, month_zero_based + 1, 1)
