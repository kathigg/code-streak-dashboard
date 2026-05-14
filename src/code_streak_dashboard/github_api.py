from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


API_ROOT = "https://api.github.com"
GRAPHQL_URL = f"{API_ROOT}/graphql"


class GitHubApiError(RuntimeError):
    """Raised when GitHub returns an unrecoverable API error."""


@dataclass(frozen=True)
class RepositoryInfo:
    name: str
    clone_url: str
    html_url: str
    archived: bool = False
    fork: bool = False
    languages: dict[str, dict[str, str | int | None]] = field(default_factory=dict)


@dataclass(frozen=True)
class ContributionDay:
    date: str
    count: int


@dataclass(frozen=True)
class GitHubProfileData:
    username: str
    display_name: str | None
    contribution_days: list[ContributionDay]
    repositories: list[RepositoryInfo]
    total_contributions: int = 0
    commit_contributions: int = 0
    pull_request_contributions: int = 0
    review_contributions: int = 0
    issue_contributions: int = 0


def github_token() -> str | None:
    """Return the best available token without requiring one for public data."""

    return (
        os.getenv("DASHBOARD_GITHUB_TOKEN")
        or os.getenv("GH_TOKEN")
        or os.getenv("GITHUB_TOKEN")
        or None
    )


def collect_profile_data(username: str, token: str | None, days: int) -> GitHubProfileData:
    """Collect contribution and repository-language data.

    GraphQL gives the most accurate contribution calendar. REST is kept as a
    public-data fallback so forks still render something when no token is set.
    """

    if token:
        try:
            return _collect_graphql_profile(username=username, token=token, days=days)
        except GitHubApiError as exc:
            print(f"GraphQL collection failed, falling back to REST: {exc}")

    return _collect_rest_profile(username=username, token=token, days=days)


def _request_json(
    url: str,
    token: str | None = None,
    method: str = "GET",
    body: dict[str, Any] | None = None,
) -> Any:
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "code-streak-dashboard",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise GitHubApiError(f"{exc.code} {exc.reason}: {message[:300]}") from exc
    except urllib.error.URLError as exc:
        raise GitHubApiError(str(exc)) from exc


def _collect_graphql_profile(username: str, token: str, days: int) -> GitHubProfileData:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days - 1)
    query = """
    query DashboardProfile($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        name
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          totalIssueContributions
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
        repositories(first: 100, ownerAffiliations: OWNER, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            name
            url
            visibility
            isArchived
            isFork
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    """
    result = _request_json(
        GRAPHQL_URL,
        token=token,
        method="POST",
        body={
            "query": query,
            "variables": {
                "login": username,
                "from": start.isoformat().replace("+00:00", "Z"),
                "to": now.isoformat().replace("+00:00", "Z"),
            },
        },
    )
    errors = result.get("errors")
    if errors:
        raise GitHubApiError("; ".join(error.get("message", "unknown error") for error in errors))

    user = result.get("data", {}).get("user")
    if not user:
        raise GitHubApiError(f"GitHub user not found: {username}")

    collection = user["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    contribution_days = [
        ContributionDay(date=day["date"], count=int(day["contributionCount"]))
        for week in calendar["weeks"]
        for day in week["contributionDays"]
    ]
    repositories = []
    for repo in user["repositories"]["nodes"]:
        if repo.get("visibility") != "PUBLIC":
            continue
        languages = {}
        for edge in repo["languages"]["edges"]:
            language = edge["node"]["name"]
            languages[language] = {
                "size": int(edge["size"]),
                "color": edge["node"].get("color"),
            }
        repositories.append(
            RepositoryInfo(
                name=repo["name"],
                clone_url=f"https://github.com/{username}/{repo['name']}.git",
                html_url=repo["url"],
                archived=bool(repo["isArchived"]),
                fork=bool(repo["isFork"]),
                languages=languages,
            )
        )

    return GitHubProfileData(
        username=username,
        display_name=user.get("name"),
        contribution_days=contribution_days,
        repositories=repositories,
        total_contributions=int(calendar["totalContributions"]),
        commit_contributions=int(collection["totalCommitContributions"]),
        pull_request_contributions=int(collection["totalPullRequestContributions"]),
        review_contributions=int(collection["totalPullRequestReviewContributions"]),
        issue_contributions=int(collection["totalIssueContributions"]),
    )


def _collect_rest_profile(username: str, token: str | None, days: int) -> GitHubProfileData:
    repositories = _rest_repositories(username=username, token=token)
    for repo in repositories:
        languages_url = f"{API_ROOT}/repos/{username}/{urllib.parse.quote(repo.name)}/languages"
        try:
            languages_payload = _request_json(languages_url, token=token)
        except GitHubApiError:
            languages_payload = {}
        repo.languages.update(
            {
                language: {"size": int(size), "color": None}
                for language, size in languages_payload.items()
            }
        )

    events = _rest_public_events(username=username, token=token, days=days)
    contribution_days = [
        ContributionDay(date=day, count=count)
        for day, count in sorted(events.items())
    ]

    return GitHubProfileData(
        username=username,
        display_name=None,
        contribution_days=contribution_days,
        repositories=repositories,
        total_contributions=sum(events.values()),
    )


def _rest_repositories(username: str, token: str | None) -> list[RepositoryInfo]:
    repos: list[RepositoryInfo] = []
    page = 1
    while True:
        url = (
            f"{API_ROOT}/users/{urllib.parse.quote(username)}/repos"
            f"?type=owner&sort=updated&per_page=100&page={page}"
        )
        payload = _request_json(url, token=token)
        if not payload:
            break
        for repo in payload:
            repos.append(
                RepositoryInfo(
                    name=repo["name"],
                    clone_url=repo["clone_url"],
                    html_url=repo["html_url"],
                    archived=bool(repo.get("archived")),
                    fork=bool(repo.get("fork")),
                )
            )
        if len(payload) < 100:
            break
        page += 1
    return repos


def _rest_public_events(username: str, token: str | None, days: int) -> dict[str, int]:
    earliest = datetime.now(timezone.utc) - timedelta(days=days - 1)
    counts: dict[str, int] = {}
    for page in range(1, 4):
        url = f"{API_ROOT}/users/{urllib.parse.quote(username)}/events/public?per_page=100&page={page}"
        try:
            payload = _request_json(url, token=token)
        except GitHubApiError:
            break
        if not payload:
            break
        for event in payload:
            created_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
            if created_at < earliest:
                continue
            if event["type"] not in {
                "PushEvent",
                "PullRequestEvent",
                "PullRequestReviewEvent",
                "CreateEvent",
            }:
                continue
            day = created_at.date().isoformat()
            counts[day] = counts.get(day, 0) + 1
    return counts
