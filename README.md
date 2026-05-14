# Code Streak Dashboard

Generate a GitHub-profile SVG dashboard with a Duolingo-style coding streak, a fire graphic, contribution trends, comment and test counts, and a language pie chart.

The generated dashboard is static SVG, so it can be embedded directly in a GitHub profile README:

```md
<a href="https://github.com/YOUR_USERNAME/code-streak-dashboard">
  <img src="https://raw.githubusercontent.com/YOUR_USERNAME/code-streak-dashboard/main/dist/dashboard.svg" alt="Code streak dashboard" width="920">
</a>
```

## What It Shows

- Current and longest coding streak from the GitHub contribution calendar.
- Coding activity over the last 12 months.
- Last 49 days of activity as a compact heat strip.
- Comment lines found by scanning public source repositories.
- Detected test cases, test files, and test lines.
- Most common languages by repository language byte counts.

## Use It For Your Own Profile

1. Fork or copy this repository.
2. Go to your fork's `Settings -> Actions -> General` and enable `Read and write permissions` for workflows.
3. Optional: set a repository variable named `DASHBOARD_USERNAME` if the dashboard should track a username other than the repo owner.
4. Optional: add a secret named `DASHBOARD_GITHUB_TOKEN` with `read:user` and public repository access for higher API rate limits or richer contribution data.
5. Run the `Generate dashboard` workflow once from the Actions tab.
6. Embed `dist/dashboard.svg` in your GitHub profile README with the snippet above.

The workflow runs daily and commits updated files into `dist/`.

## Local Development

```bash
PYTHONPATH=src python -m unittest discover -s tests
PYTHONPATH=src python -m code_streak_dashboard --username kathigg --output-dir dist --scan-limit 30
```

## Notes On Metrics

The streak uses GitHub's contribution calendar with a one-day grace window, so the streak does not reset before the current day is over if you contributed yesterday but have not coded yet today.

Comment and test counts are approximate. The scanner clones up to 30 public, owned, non-fork repositories by default and counts common source-file comment styles plus common test patterns such as `def test_*`, `test(...)`, `it(...)`, `@Test`, Rust `#[test]`, and Go `func Test*`.

## Attribution

The fire graphic is based on [OpenMoji FIRE 1F525](https://openmoji.org/library/emoji-1F525/), an open internet-sourced emoji graphic, not a company logo. OpenMoji is licensed under CC BY-SA 4.0.
