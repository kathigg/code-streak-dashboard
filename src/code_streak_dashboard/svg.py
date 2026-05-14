from __future__ import annotations

import html
import json
from pathlib import Path

from .metrics import DashboardMetrics, StreakAwardMetric


WIDTH = 920
HEIGHT = 760
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO_FONT = "ui-monospace, SFMono-Regular, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace"


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
        "<desc id=\"desc\">Coding streak dashboard.</desc>",
        _defs(),
        f'<rect width="{WIDTH}" height="{HEIGHT}" rx="24" fill="#ffffff"/>',
        '<rect x="18" y="18" width="884" height="724" rx="16" fill="#ffffff" stroke="#d0d7de" stroke-width="1"/>',
        _header(metrics),
        _streak_card(metrics),
        _metric_card(356, 120, "Active days", f"{metrics.active_days}", "#2da44e"),
        _metric_card(536, 120, "Comments", f"{metrics.comment_lines:,}", "#0969da"),
        _metric_card(716, 120, "Tests", f"{test_value:,}", "#bf8700"),
        _awards_card(metrics),
        _activity_chart(metrics, max_month),
        _recent_grid(metrics),
        "</svg>",
    ]
    return "\n".join(line.rstrip() for line in "\n".join(parts).splitlines()) + "\n"


def _defs() -> str:
    return """
<defs>
  <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="2" stdDeviation="6" flood-color="#1f2328" flood-opacity="0.04"/>
  </filter>
  <linearGradient id="chartWash" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" stop-color="#2da44e" stop-opacity="0.18"/>
    <stop offset="100%" stop-color="#2da44e" stop-opacity="0.02"/>
  </linearGradient>
</defs>
"""


def _header(metrics: DashboardMetrics) -> str:
    return f"""
<g transform="translate(52 52)">
  <text x="0" y="0" fill="#24292f" font-family="{FONT}" font-size="32" font-weight="600" letter-spacing="-0.4">
    {_e(metrics.display_name)}'s code streak
  </text>
  <line x1="0" y1="42" x2="816" y2="42" stroke="#d8dee4" stroke-width="1"/>
</g>
"""


def _streak_card(metrics: DashboardMetrics) -> str:
    return f"""
<g filter="url(#softShadow)">
  <rect x="52" y="112" width="268" height="150" rx="12" fill="#ffffff" stroke="#d0d7de" stroke-width="1"/>
  <rect x="70" y="130" width="66" height="66" rx="10" fill="#f6f8fa" stroke="#d0d7de" stroke-width="1"/>
  {_fire_icon(78, 136, 52)}
  <text x="168" y="136" fill="#57606a" font-family="{FONT}" font-size="12" font-weight="600" letter-spacing="0.6">
    Current streak
  </text>
  <text x="168" y="210" fill="#24292f" font-family="{MONO_FONT}" font-size="56" font-weight="700">
    {metrics.current_streak}
  </text>
  <line x1="70" y1="232" x2="302" y2="232" stroke="#2da44e" stroke-width="3" stroke-linecap="round"/>
</g>
"""


def _metric_card(x: int, y: int, title: str, value: str, accent: str) -> str:
    return f"""
<g filter="url(#softShadow)">
  <rect x="{x}" y="{y}" width="150" height="132" rx="12" fill="#ffffff" stroke="#d0d7de" stroke-width="1"/>
  <circle cx="{x + 126}" cy="{y + 26}" r="8" fill="{accent}" opacity="0.14"/>
  <line x1="{x + 24}" y1="{y + 26}" x2="{x + 58}" y2="{y + 26}" stroke="{accent}" stroke-width="3" stroke-linecap="round"/>
  <text x="{x + 24}" y="{y + 48}" fill="#57606a" font-family="{FONT}" font-size="12" font-weight="600" letter-spacing="0.6">
    {_e(title)}
  </text>
  <text x="{x + 24}" y="{y + 96}" fill="#24292f" font-family="{MONO_FONT}" font-size="34" font-weight="700">
    {_e(value)}
  </text>
</g>
"""


def _awards_card(metrics: DashboardMetrics) -> str:
    next_award = next((award for award in metrics.awards if not award.unlocked), None)
    if next_award:
        progress = min(metrics.current_streak / next_award.threshold, 1)
    else:
        progress = 1
    progress_width = 248 * progress
    badges = "\n".join(
        _award_badge(78 + index * 98, 316, award)
        for index, award in enumerate(metrics.awards[:8])
    )
    return f"""
<g filter="url(#softShadow)">
  <rect x="52" y="282" width="816" height="130" rx="12" fill="#ffffff" stroke="#d0d7de" stroke-width="1"/>
  <text x="80" y="314" fill="#24292f" font-family="{FONT}" font-size="20" font-weight="600" letter-spacing="-0.2">
    Streak awards
  </text>
  <rect x="592" y="300" width="248" height="8" rx="4" fill="#d8dee4"/>
  <rect x="592" y="300" width="{progress_width:.1f}" height="8" rx="4" fill="#2da44e"/>
  {badges}
</g>
"""


def _award_badge(x: int, y: int, award: StreakAwardMetric) -> str:
    display_title = _award_display_title(award.title)
    threshold_fill = "#24292f" if award.unlocked else "#8c959f"
    title_fill = "#24292f" if award.unlocked else "#8c959f"
    circle_fill = "#dafbe1" if award.unlocked else "#f6f8fa"
    opacity = "1" if award.unlocked else "0.62"
    stroke = "#2da44e" if award.active else ("#40c463" if award.unlocked else "#d0d7de")
    return f"""
<g opacity="{opacity}">
  <title>{_e(award.title)}</title>
  <path d="M{x + 28} {y} L{x + 54} {y + 14} L{x + 54} {y + 44} L{x + 28} {y + 58} L{x + 2} {y + 44} L{x + 2} {y + 14} Z" fill="#ffffff" stroke="{stroke}" stroke-width="3"/>
  <circle cx="{x + 28}" cy="{y + 29}" r="17" fill="{circle_fill}"/>
  <text x="{x + 28}" y="{y + 35}" text-anchor="middle" fill="{threshold_fill}" font-family="{MONO_FONT}" font-size="14" font-weight="800">
    {award.threshold}d
  </text>
  <text x="{x + 28}" y="{y + 82}" text-anchor="middle" fill="{title_fill}" font-family="{FONT}" font-size="10" font-weight="700">
    {_e(display_title)}
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
        f'<text x="{chart_x + index * step:.1f}" y="{chart_y + chart_h + 28}" text-anchor="middle" fill="#8c959f" font-family="{FONT}" font-size="10">{_e(month.label)}</text>'
        for index, month in enumerate(metrics.monthly)
    )
    value_labels = "\n".join(
        f'<circle cx="{point.split(",")[0]}" cy="{point.split(",")[1]}" r="4" fill="#ffffff" stroke="#2da44e" stroke-width="2"/>'
        for point in points
    )
    return f"""
<g filter="url(#softShadow)">
  <rect x="{x0}" y="{y0}" width="{width}" height="{height}" rx="12" fill="#ffffff" stroke="#d0d7de" stroke-width="1"/>
  <text x="{x0 + 28}" y="{y0 + 30}" fill="#24292f" font-family="{FONT}" font-size="20" font-weight="600" letter-spacing="-0.2">
    Coding over time
  </text>
  <line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="#d8dee4" stroke-width="1"/>
  <line x1="{chart_x}" y1="{chart_y}" x2="{chart_x}" y2="{chart_y + chart_h}" stroke="#d8dee4" stroke-width="1"/>
  <path d="M {' L '.join(area_points)} Z" fill="url(#chartWash)"/>
  <polyline points="{' '.join(points)}" fill="none" stroke="#2da44e" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
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
        color = _heat_color(intensity) if day.count else "#ebedf0"
        cells.append(
            f'<rect x="{x0 + col * 10}" y="{y0}" width="7" height="28" rx="3.5" fill="{color}"><title>{_e(day.date)}: {day.count}</title></rect>'
        )
    return f"""
<g>
  <text x="{x0}" y="{y0 - 18}" fill="#24292f" font-family="{FONT}" font-size="13" font-weight="600">
    Last 49 days
  </text>
  {''.join(cells)}
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
        return "#216e39"
    if intensity >= 0.5:
        return "#30a14e"
    if intensity >= 0.25:
        return "#40c463"
    return "#9be9a8"


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
