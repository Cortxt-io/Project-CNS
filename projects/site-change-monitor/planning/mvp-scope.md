---
quest_started: '2026-05-02'
quest_updated: '2026-05-02'
slug: site-change-monitor
---

## Current Slice

Basic monitor + diff + alert loop via CLI.

- Fetch URLs from config.yaml
- Extract meaningful text (strip scripts, nav, boilerplate)
- Save timestamped snapshots to data/snapshots/
- Diff against previous snapshot
- Classify changes as meaningful vs noise
- Print clear summary to terminal

## Next Steps

1. **Simple scheduler**: add a `--watch` mode with configurable interval, or cron-friendly exit codes, so monitoring runs unattended without external wiring.
2. **JSON/HTML report per run**: write a structured report file alongside terminal output so downstream tools (dashboards, notifications) can consume results programmatically.

## Not Now

- Authentication, billing, or user accounts
- Web dashboard or hosted service
- Slack/email/webhook notifications (manual integration only for now)
- JavaScript rendering (Playwright/Puppeteer)
- Multi-user or team features
- Deployment automation or Docker packaging
- Database backend
- Complex selector-based extraction rules
