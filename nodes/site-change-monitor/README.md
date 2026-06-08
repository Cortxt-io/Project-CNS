# Site Change Monitor - MVP

Local CLI tool that monitors webpages for meaningful content changes.

## What it does

1. Reads a list of URLs from `config.yaml`
2. Fetches each page's HTML
3. Extracts meaningful text (strips scripts, nav, styles, etc.)
4. Saves a timestamped snapshot to `data/snapshots/`
5. Compares against the previous snapshot
6. Classifies each change as **meaningful** or **noise**
7. Prints a clear terminal summary
8. Generates a JSON report and static HTML report per run

## Setup

```bash
cd projects/site-change-monitor
pip install -r requirements.txt
```

## Usage

```bash
# Run with default config.yaml
python -m src.cli

# Custom config file
python -m src.cli --config my_urls.yaml

# Show diff details even for noise changes
python -m src.cli --verbose

# Custom data directory
python -m src.cli --data-dir ./my_snapshots
```

First run will save snapshots with no diff (nothing to compare yet).
Second run will show diffs against the first run.

## Config format

```yaml
urls:
  - url: "https://example.com"
    label: "Example homepage"
  - url: "https://competitor.com/pricing"
    label: "Competitor pricing"

filters:
  min_change_chars: 10
  ignore_whitespace_only: true
  ignore_timestamp_patterns: true
```

## Snapshot format

JSON files stored in `data/snapshots/<url_slug>/<timestamp>.json`:

```json
{
  "url": "https://example.com",
  "label": "Example homepage",
  "fetched_at": "2026-05-02T12:00:00+00:00",
  "text": "extracted page text..."
}
```

## Noise reduction heuristics

- **Whitespace-only changes** are filtered out
- **Timestamp/date patterns** are normalized before comparison
- **Small changes** below a character threshold are flagged as noise
- **Cookie/GDPR boilerplate** phrases are detected and filtered

## Reports

Each run generates a structured JSON report and a static HTML report in `data/reports/<run_id>/`.

### Data directory layout

```
data/
  snapshots/
    <url_slug>/
      <timestamp>.json          # one per fetch
  reports/
    <run_id>/
      report.json               # structured run summary
      report.html               # self-contained HTML report
      diffs/
        <url_slug>.diff.txt     # unified diff (only for changed URLs)
```

### JSON report structure

```json
{
  "run_id": "20260502_120000",
  "generated_at": "2026-05-02T12:00:00+00:00",
  "summary": {
    "total_urls": 3,
    "changed": 1,
    "unchanged": 2,
    "major": 1,
    "minor": 0
  },
  "results": [
    {
      "url": "https://example.com",
      "label": "Example homepage",
      "status": "changed",
      "severity": "major",
      "summary": "Content changed (142 chars, 2 added / 1 removed lines).",
      "snapshot_current": "snapshots/example_com__abc123/20260502_120000.json",
      "snapshot_previous": "snapshots/example_com__abc123/20260501_120000.json",
      "diff_path": "reports/20260502_120000/diffs/example_com__abc123.diff.txt"
    }
  ]
}
```

### Severity rules

| Status | Severity | Meaning |
|--------|----------|---------|
| unchanged | none | No content change detected |
| changed | minor | Change detected but classified as noise |
| changed | major | Meaningful content change that passed all noise filters |

### HTML report

Self-contained static file (inline CSS, no JS). Open directly in a browser.
Shows a summary bar and a table of all monitored URLs with status, severity, and artifact paths.

## What this MVP does NOT do

- No JavaScript rendering (static HTML only)
- No scheduling/cron (run manually or wire up yourself)
- No notifications (Slack, email, etc.)
- No web dashboard
- No database
- No authentication or multi-user
- No deployment -- local only

These are intentional scope cuts for fast validation.
