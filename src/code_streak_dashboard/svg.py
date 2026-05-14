from __future__ import annotations

import html
import json
from pathlib import Path

from .metrics import DashboardMetrics, StreakAwardMetric


WIDTH = 920
HEIGHT = 760
OPENMOJI_FIRE_SOURCE = "https://openmoji.org/library/emoji-1F525/"


def write_outputs(metrics: DashboardMetrics, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "dashboard.svg").write_text(render_dashboard_svg(metrics), encoding="utf-8")
    (output_dir / "metrics.json").write_text(
        json.dumps(_metrics_json(metrics), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def render_dashboard_svg(metrics: DashboardMetrics) -> str:
    max_month = max((month.count for month in metrics.monthly), default=1) or 1
    test_value = metrics.test_cases or metrics.test_files

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
        f"<title id=\"title\">{_e(metrics.username)} coding streak dashboard</title>",
        "<desc id=\"desc\">GitHub profile dashboard showing coding streak, streak awards, contribution graph, comments, and tests.</desc>",
        _defs(),
        f'<rect width="{WIDTH}" height="{HEIGHT}" rx="34" fill="url(#bg)"/>',
        '<rect x="18" y="18" width="884" height="724" rx="28" fill="#fff8ec" opacity="0.92"/>',
        '<rect x="18" y="18" width="884" height="724" rx="28" fill="url(#grain)" opacity="0.32"/>',
        _header(metrics),
        _streak_card(metrics),
        _metric_card(356, 120, "Active days", f"{metrics.active_days}", "days with contributions", "#0f766e"),
        _metric_card(536, 120, "Comments", f"{metrics.comment_lines:,}", "comment lines scanned", "#b45309"),
        _metric_card(716, 120, "Tests", f"{test_value:,}", _test_caption(metrics), "#2563eb"),
        _awards_card(metrics),
        _activity_chart(metrics, max_month),
        _recent_grid(metrics),
        _footer(metrics),
        "</svg>",
    ]
    return "\n".join(line.rstrip() for line in "\n".join(parts).splitlines()) + "\n"


def _defs() -> str:
    return """
<defs>
  <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
    <stop offset="0%" stop-color="#10231f"/>
    <stop offset="44%" stop-color="#1b4d3e"/>
    <stop offset="100%" stop-color="#f59e0b"/>
  </linearGradient>
  <linearGradient id="flameFill" x1="0" x2="1" y1="0" y2="1">
    <stop offset="0%" stop-color="#ffef74"/>
    <stop offset="52%" stop-color="#ff9f1c"/>
    <stop offset="100%" stop-color="#e63900"/>
  </linearGradient>
  <pattern id="grain" width="18" height="18" patternUnits="userSpaceOnUse">
    <path d="M0 18 L18 0" stroke="#d6a13a" stroke-width="1" opacity="0.25"/>
  </pattern>
  <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#10231f" flood-opacity="0.18"/>
  </filter>
</defs>
"""


def _header(metrics: DashboardMetrics) -> str:
    return f"""
<g transform="translate(52 52)">
  <text x="0" y="0" fill="#17352e" font-family="Georgia, 'Trebuchet MS', serif" font-size="34" font-weight="800">
    {_e(metrics.display_name)}'s code streak
  </text>
  <text x="2" y="34" fill="#53645f" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="14">
    Contribution rhythm, repository scan stats, and streak prizes for @{_e(metrics.username)}
  </text>
</g>
"""


def _streak_card(metrics: DashboardMetrics) -> str:
    streak_word = "day" if metrics.current_streak == 1 else "days"
    return f"""
<g filter="url(#softShadow)">
  <rect x="52" y="112" width="268" height="150" rx="24" fill="#17352e"/>
  <path d="M52 220 C110 186 168 260 320 196 L320 262 L52 262 Z" fill="#235f4e" opacity="0.72"/>
  {_fire_icon(78, 136, 82)}
  <text x="168" y="168" fill="#fff8ec" font-family="Georgia, 'Trebuchet MS', serif" font-size="48" font-weight="900">
    {metrics.current_streak}
  </text>
  <text x="170" y="196" fill="#ffd166" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="17" font-weight="700">
    {streak_word} in a row
  </text>
  <text x="170" y="222" fill="#cfe6dc" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="13">
    Longest streak: {metrics.longest_streak} days
  </text>
</g>
"""


def _metric_card(x: int, y: int, title: str, value: str, caption: str, color: str) -> str:
    return f"""
<g filter="url(#softShadow)">
  <rect x="{x}" y="{y}" width="150" height="132" rx="22" fill="#fffdf7"/>
  <circle cx="{x + 26}" cy="{y + 30}" r="10" fill="{color}"/>
  <text x="{x + 46}" y="{y + 35}" fill="#53645f" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="13" font-weight="700">
    {_e(title)}
  </text>
  <text x="{x + 24}" y="{y + 82}" fill="#17352e" font-family="Georgia, 'Trebuchet MS', serif" font-size="32" font-weight="900">
    {_e(value)}
  </text>
  <text x="{x + 24}" y="{y + 108}" fill="#6c7a76" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="12">
    {_e(caption)}
  </text>
</g>
"""


def _awards_card(metrics: DashboardMetrics) -> str:
    next_award = next((award for award in metrics.awards if not award.unlocked), None)
    if next_award:
        progress = min(metrics.current_streak / next_award.threshold, 1)
        days_remaining = max(next_award.threshold - metrics.current_streak, 0)
        day_word = "day" if days_remaining == 1 else "days"
        progress_label = f"{days_remaining} {day_word} to {next_award.title}"
    else:
        progress = 1
        progress_label = "All streak awards unlocked"
    progress_width = 248 * progress
    badges = "\n".join(
        _award_badge(78 + index * 98, 316, award)
        for index, award in enumerate(metrics.awards[:8])
    )
    return f"""
<g filter="url(#softShadow)">
  <rect x="52" y="282" width="816" height="130" rx="24" fill="#fffdf7"/>
  <text x="80" y="314" fill="#17352e" font-family="Georgia, 'Trebuchet MS', serif" font-size="22" font-weight="800">
    Streak awards
  </text>
  <text x="280" y="314" fill="#6c7a76" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="12">
    GitHub-style milestone prizes
  </text>
  <rect x="592" y="300" width="248" height="10" rx="5" fill="#e9eee8"/>
  <rect x="592" y="300" width="{progress_width:.1f}" height="10" rx="5" fill="#f59e0b"/>
  <text x="840" y="329" text-anchor="end" fill="#53645f" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="12">
    {_e(progress_label)}
  </text>
  {badges}
</g>
"""


def _award_badge(x: int, y: int, award: StreakAwardMetric) -> str:
    display_title = _award_display_title(award.title)
    fill = award.color if award.unlocked else "#d8ded8"
    text_fill = "#fff8ec" if award.unlocked else "#6c7a76"
    subtitle_fill = "#53645f" if award.unlocked else "#8a9692"
    opacity = "1" if award.unlocked else "0.72"
    stroke = "#17352e" if award.active else "#fffdf7"
    return f"""
<g opacity="{opacity}">
  <title>{_e(award.title)}: {_e(award.subtitle)}</title>
  <path d="M{x + 28} {y} L{x + 54} {y + 14} L{x + 54} {y + 44} L{x + 28} {y + 58} L{x + 2} {y + 44} L{x + 2} {y + 14} Z" fill="{fill}" stroke="{stroke}" stroke-width="3"/>
  <circle cx="{x + 28}" cy="{y + 29}" r="17" fill="#fff8ec" opacity="0.18"/>
  <text x="{x + 28}" y="{y + 35}" text-anchor="middle" fill="{text_fill}" font-family="Georgia, 'Trebuchet MS', serif" font-size="16" font-weight="900">
    {award.threshold}d
  </text>
  <text x="{x + 28}" y="{y + 78}" text-anchor="middle" fill="#17352e" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="10" font-weight="800">
    {_e(display_title)}
  </text>
  <text x="{x + 28}" y="{y + 92}" text-anchor="middle" fill="{subtitle_fill}" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="9">
    {_e("Unlocked" if award.unlocked else "Locked")}
  </text>
</g>
"""


def _award_display_title(title: str) -> str:
    short_names = {
        "First Spark": "Spark",
        "Century Flame": "Century",
        "Phoenix Year": "Phoenix",
    }
    return short_names.get(title, title.split()[0])


def _activity_chart(metrics: DashboardMetrics, max_month: int) -> str:
    x0, y0, width, height = 52, 430, 816, 190
    chart_x, chart_y, chart_w, chart_h = x0 + 28, y0 + 50, width - 58, 92
    step = chart_w / max(1, len(metrics.monthly) - 1)
    points = []
    area_points = [f"{chart_x},{chart_y + chart_h}"]
    for index, month in enumerate(metrics.monthly):
        x = chart_x + index * step
        y = chart_y + chart_h - (month.count / max_month) * chart_h
        points.append(f"{x:.1f},{y:.1f}")
        area_points.append(f"{x:.1f},{y:.1f}")
    area_points.append(f"{chart_x + chart_w},{chart_y + chart_h}")
    month_labels = "\n".join(
        f'<text x="{chart_x + index * step:.1f}" y="{chart_y + chart_h + 28}" text-anchor="middle" fill="#75837f" font-family="\'Trebuchet MS\', Verdana, sans-serif" font-size="10">{_e(month.label)}</text>'
        for index, month in enumerate(metrics.monthly)
    )
    value_labels = "\n".join(
        f'<circle cx="{point.split(",")[0]}" cy="{point.split(",")[1]}" r="4.5" fill="#f59e0b" stroke="#17352e" stroke-width="2"/>'
        for point in points
    )
    return f"""
<g filter="url(#softShadow)">
  <rect x="{x0}" y="{y0}" width="{width}" height="{height}" rx="24" fill="#fffdf7"/>
  <text x="{x0 + 28}" y="{y0 + 30}" fill="#17352e" font-family="Georgia, 'Trebuchet MS', serif" font-size="22" font-weight="800">
    Coding over time
  </text>
  <text x="{x0 + width - 28}" y="{y0 + 30}" text-anchor="end" fill="#6c7a76" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="12">
    {metrics.total_contributions:,} contributions / 365 days
  </text>
  <line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="#d8ded8" stroke-width="1"/>
  <line x1="{chart_x}" y1="{chart_y}" x2="{chart_x}" y2="{chart_y + chart_h}" stroke="#d8ded8" stroke-width="1"/>
  <path d="M {' L '.join(area_points)} Z" fill="#f59e0b" opacity="0.22"/>
  <polyline points="{' '.join(points)}" fill="none" stroke="#17352e" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  {value_labels}
  {month_labels}
</g>
"""


def _recent_grid(metrics: DashboardMetrics) -> str:
    x0, y0 = 52, 660
    cells = []
    max_count = max((day.count for day in metrics.recent_days), default=1) or 1
    for index, day in enumerate(metrics.recent_days):
        col = index % 49
        intensity = day.count / max_count
        color = _heat_color(intensity) if day.count else "#e9eee8"
        cells.append(
            f'<rect x="{x0 + col * 10}" y="{y0}" width="7" height="28" rx="3.5" fill="{color}"><title>{_e(day.date)}: {day.count}</title></rect>'
        )
    return f"""
<g>
  <text x="{x0}" y="{y0 - 18}" fill="#17352e" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="13" font-weight="800">
    Last 49 days
  </text>
  {''.join(cells)}
</g>
"""


def _footer(metrics: DashboardMetrics) -> str:
    scan_note = f"{metrics.scanned_repositories} repos scanned"
    if metrics.failed_repositories:
        scan_note += f", {metrics.failed_repositories} skipped"
    return f"""
<g>
  <text x="52" y="716" fill="#53645f" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="12">
    Fire graphic source: OpenMoji 1F525 • Generated {metrics.generated_at}
  </text>
  <text x="868" y="716" text-anchor="end" fill="#53645f" font-family="'Trebuchet MS', Verdana, sans-serif" font-size="12">
    Source scan: {_e(scan_note)} • {metrics.source_files:,} files • {metrics.source_lines:,} nonblank lines
  </text>
</g>
"""


def _fire_icon(x: int, y: int, size: int) -> str:
    scale = size / 72
    # Based on OpenMoji FIRE (1F525), CC BY-SA 4.0: https://openmoji.org/library/emoji-1F525/
    return f"""
<g transform="translate({x} {y}) scale({scale:.4f})">
  <path fill="#FCEA2B" d="M51.3344,58.3018c7.563-9.7894,4.0318-21.8721,2.4461-25.5688c-0.1799-0.4193-0.9302-0.5566-0.982-0.1006c-0.1225,1.0797-0.4061,2.3611-2.0041,1.9736c-0.8203-0.1989-1.3479-0.556-1.3479-1.8802c0.511-15.0494-10.5109-25.2968-14.3463-28.5356c-0.5103-0.4309-1.2668,0.0293-1.1587,0.7039c2.456,15.3348-1.6079,14.2846-3.0986,13.8192c-0.2593-0.081-0.5408,0.0546-0.6603,0.3074c-4.5882,9.7014-3.4112,14.2653-3.519,17.4455c0,0.2569,0,0.687,0,0.9581c0,1.746-1.4154,2.5822-2.5607,2.0714c-2.0545-0.9163-2.4047-6.3729-2.4134-7.8235c-0.0041-0.6828-0.8094-0.8791-1.202-0.332c-8.8048,12.267-2.3251,23.1974-0.0822,26.3171c0.6459,0.8984,0.9025,2.0748,0.5354,3.1298c-0.0412,0.1183-0.0896,0.2352-0.1465,0.349c-0.3988,0.7981,0.6707,1.4,0.6707,1.4c1.3155,1.2339,5.4651,5.1806,14.2817,5.1805c7.1344-0.0001,11.9478-3.0595,13.8297-4.7247c0.8829-0.7812,1.2761-0.8594,1.2732-1.6827C50.8459,60.3243,50.8238,58.8066,51.3344,58.3018"/>
  <path fill="#F1B31C" d="M36.2938,32.5579c-0.2946,1.4609-1.3196,4.0019-4.2072,8.3499c-0.0592,0.1064-0.1172,0.2104-0.1764,0.3168c-0.3088,0.6893-1.3555,3.3414-1.0617,7.0514c-0.0002,0.0018-0.573,4.337-2.977,3.9757c-0.5095-0.0766-0.9214-0.2506-1.2541-0.4772c-0.6105-0.4159-1.4234,0.1082-1.3489,0.8525c0.3195,3.1924,1.6034,8.0822,6.1526,11.6721c0,0,1.2832,1.0598,1.4415,1.9748c0.0052,0.0303,0.029,0.0506,0.0591,0.0506l5.2741,0c0.1832,0,0.2083-0.024,0.2135-0.0594c0.0356-0.2402,0.3643-1.2504,3.2024-3.7732c1.9966-1.7748,3.1652-3.898,3.7424-5.3482c0.2048-0.5145-0.101-1.1173-0.6389-1.2068c-0.3438-0.0572-0.7127-0.3603-1.0133-1.1841c-0.0063-0.0235-0.2167-0.8383,0.6013-2.5595c0.3805-0.8006,0.4242-1.6645,0.36-2.3655c-0.0579-0.6322-0.723-0.998-1.2816-0.7156c-0.7839,0.3965-1.8694,0.5304-2.5993-1.0753c0,0-0.6584-1.5662-0.0859-5.4515c0.437-2.9656-1.0106-7.8615-2.8279-10.3747C37.4192,31.5887,36.4459,31.8032,36.2938,32.5579z"/>
  <path fill="none" stroke="#101820" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21.6298,61.5562c3.479,3.6108,8.6702,5.4754,13.9925,5.4754c5.0546,0,10.7077-1.9624,14.2409-5.4677"/>
  <path fill="none" stroke="#101820" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21.5108,57.4557c0,0-10.5321-11.2011-0.4546-25.9791c0,0,0.1969,4.0589,1.2551,6.5816c0.4834,1.0362,1.2122,1.9569,2.3487,1.9569c1.3355,0,2.4181-0.8972,2.4181-2.5708c0-0.2599,0-0.6721,0-0.9184c0.105-3.0996-0.5251-7.6659,3.5708-17.19c0,0,7.0365,3.7835,3.9909-14.6122c0,0,14.8798,10.4421,14.2762,28.217c0,1.2693,0.9678,2.2983,2.1617,2.2983s2.1617-1.029,2.1617-2.2983c0.075,0.1341,6.3219,13.078-2.514,24.515"/>
</g>
"""


def _heat_color(intensity: float) -> str:
    if intensity >= 0.75:
        return "#0f5132"
    if intensity >= 0.5:
        return "#198754"
    if intensity >= 0.25:
        return "#6bbf59"
    return "#b7e4a8"


def _test_caption(metrics: DashboardMetrics) -> str:
    if metrics.test_cases:
        return f"{metrics.test_files:,} files detected"
    return f"{metrics.test_lines:,} test lines"


def _metrics_json(metrics: DashboardMetrics) -> dict[str, object]:
    return {
        "username": metrics.username,
        "generated_at": metrics.generated_at,
        "current_streak": metrics.current_streak,
        "longest_streak": metrics.longest_streak,
        "active_days": metrics.active_days,
        "total_contributions": metrics.total_contributions,
        "comments": {"lines": metrics.comment_lines},
        "tests": {
            "cases": metrics.test_cases,
            "files": metrics.test_files,
            "lines": metrics.test_lines,
        },
        "source_scan": {
            "files": metrics.source_files,
            "lines": metrics.source_lines,
            "repositories": metrics.scanned_repositories,
            "failed_repositories": metrics.failed_repositories,
        },
        "languages": [
            {
                "name": language.name,
                "size": language.size,
                "percent": round(language.percent, 4),
                "color": language.color,
            }
            for language in metrics.languages
        ],
        "awards": [
            {
                "threshold": award.threshold,
                "title": award.title,
                "subtitle": award.subtitle,
                "unlocked": award.unlocked,
                "active": award.active,
                "color": award.color,
            }
            for award in metrics.awards
        ],
        "monthly": [{"month": month.key, "count": month.count} for month in metrics.monthly],
    }


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)
