# DocsWatch

CLI tool that monitors external documentation, changelogs, and release notes
for meaningful changes. Built for dev teams who want to know when APIs,
platforms, or tools they depend on ship updates, deprecations, or breaking
changes.

## What it does

1. Reads a list of docs/changelog URLs from `config.yaml`
2. Fetches each page and extracts text content
3. Compares against the previous snapshot
4. Classifies changes as meaningful or noise
5. Prints a summary to the terminal
6. Generates a JSON report and static HTML report per run

## Quick start

```bash
pip install -r requirements.txt
python -m src.cli
```

First run saves snapshots. Second run shows diffs.

## Example config

```yaml
urls:
  - label: "Stripe API changelog"
    url: "https://stripe.com/docs/changelog"
  - label: "Vercel changelog"
    url: "https://vercel.com/changelog"
  - label: "Shopify dev changelog"
    url: "https://shopify.dev/changelog"

filters:
  min_change_chars: 10
  ignore_whitespace_only: true
  ignore_timestamp_patterns: true
```

## Options

```bash
python -m src.cli                     # default config.yaml
python -m src.cli --config my.yaml    # custom config
python -m src.cli --verbose           # show noise diffs too
python -m src.cli --data-dir ./store  # custom data directory
```

## Reports

Each run creates `data/reports/<run_id>/` with:
- `report.json` -- structured summary
- `report.html` -- self-contained HTML (open in browser)
- `diffs/*.diff.txt` -- unified diffs for changed pages

## Noise reduction

- Whitespace-only changes are filtered out
- Timestamp/date patterns are normalized before comparison
- Small changes below a character threshold are flagged as noise
- Cookie/GDPR boilerplate phrases are detected and filtered

## What this does NOT do

- No JavaScript rendering (static HTML only)
- No scheduling (run via cron or manually)
- No notifications (Slack, email, etc.)
- No web dashboard
- No pricing/policy/competitor monitoring

## Use cases

- Track when Stripe, Vercel, or Shopify ship API changes
- Detect deprecation notices before they affect your code
- Monitor release notes for platforms your team depends on
- Stay current on breaking changes in third-party docs
