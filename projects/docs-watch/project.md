---
cost_sek: 35000
created: 2026-05-02
current_slice: Focused changelog/docs monitor via CLI, reusing Site Change Monitor
depends_on: []
family: developer-tools
feeds:
- dev-changelog-engine-mini
kind: component
layer: pipeline
mvp_stage: solution_test
part_of: pipeline-extern
pipeline: pipeline-extern
roi_percent: 243
slug: docs-watch
stage: working
status: early_mvp
summary: CLI-verktyg som bevakar externa changelogs och docs för dev-team.
tags:
- devtools
- monitoring
- changelogs
title: DocsWatch
updated: '2026-05-26'
url_repo: https://github.com/rian010194/docs-watch
value_sek: 120000
---

## Syfte

## Beroenden

## Status

## Nästa steg

## Risker

## Arbetslogg

## Anteckningar

## Problem

Development teams depend on external APIs, platforms, and tools (Stripe, Vercel, Shopify, AWS, etc.) whose changelogs, release notes, and deprecation pages update without direct notification. Teams discover breaking changes, deprecations, or new versions too late -- often only when something breaks in production. Manually checking 5-15 changelog pages on a regular basis does not happen in practice.

## Solution

DocsWatch is a lightweight CLI tool that monitors external documentation pages, changelogs, and release notes for meaningful content changes. It fetches pages, extracts text, diffs against previous snapshots, filters noise, and generates a clear per-run report. Built specifically for dev teams who build against external APIs and platforms.

## Target Audience

**Primary:** Developers and tech leads in small-to-mid teams (2-15 people) who build against external APIs and platforms and want to know when those change.

**Secondary:** DevOps and platform engineers responsible for keeping a team's external dependencies current and who need systematic tracking of upstream changes.

## Assumptions to Validate

- Dev teams lack a simple method to watch changelogs/docs they depend on (and do it manually or not at all).
- Text-based diff of changelog pages gives meaningful enough information without JS rendering.
- Changelogs and docs pages change frequently enough (weekly/monthly) to create recurring value.
- Simple noise filtering heuristics (timestamps, whitespace, cookie banners) are sufficient to make output useful.
- A CLI report (HTML/JSON) is enough as delivery format for MVP -- notifications are not needed for validation.

## Why Buy Instead of Build?

- Eliminates the gap between "we should track this" and actually doing it, with zero custom scripting.
- Noise filtering means the output is actionable, not a wall of meaningless diffs.
- Pre-configured for common developer changelog pages, works out of the box in under a minute.

## MVP Steps

- Hypothesis: validate that dev teams want a focused tool to watch external changelogs and docs.
- Solution test: let 2-3 developers monitor their actual dependency changelogs and evaluate whether the reports are useful.
- Demand test: validate whether this is a daily/weekly habit or a nice-to-have.
- Launch: ship a narrow but reliable first version with clear diffs and useful default targets.

## Cost Estimate

Estimated first-year cost is 35,000 SEK. Low because the technical core (fetch, extract, snapshot, diff, report) already exists from Site Change Monitor. Remaining cost is repositioning, config, testing with real changelog pages, and minor adjustments.

## Value Estimate

Estimated first-year value is 120,000 SEK through earlier detection of API changes, deprecations, and breaking changes across external dependencies, reducing production incidents and wasted investigation time.

## ROI

Estimated ROI is 243%, based on 120,000 SEK in value and 35,000 SEK in cost.

## Risk Assessment

- **Market** (score 2/5): Dev teams may not pay for this as a product -- many solve it with ad-hoc scripts or ignore it entirely.
- **Technical** (score 2/5): Some changelog pages are JS-rendered (React SPAs) and return empty HTML with plain fetch. Requires manual URL verification per target.
- **Positioning** (score 3/5): Risk of blending into generic website monitoring in the market's eyes -- requires sharp messaging.
- **Adoption** (score 3/5): CLI-only format may be too manual for daily use -- teams need to remember to run it rather than receiving proactive notifications.

## Timeline

- Week 1-2: Create project. Copy code to new repo. Reposition naming and config. Test end-to-end with real changelog URLs.
- Week 3-4: Run 10-15 times against real targets. Evaluate: does the diff give meaningful info? Does noise filtering work? Which pages need JS rendering?
- Week 5-6: Adjust based on results. Fix obvious gaps. Create a demo run with report to show.
- Week 7-8: Validate with 2-3 other developers. Ask: "Would you use this?". Decide on further investment.

## Notes

This project reuses the complete technical core from Site Change Monitor (fetch, extract, snapshot, diff, JSON+HTML report). The difference is positioning: DocsWatch is exclusively for dev teams monitoring external docs, changelogs, and release notes. It does not cover pricing pages, competitor intel, policy monitoring, or general website change detection. The code lives in its own repo outside the CNS project directory.
