---
cost_sek: 2000
created: '2026-05-19'
mvp_stage: solution_test
roi_percent: 650
slug: cns-hosting-infra
status: early_mvp
tags:
- hosting
- infrastructure
- github-actions
- static
title: CNS Hosting Infra
updated: '2026-05-19'
value_sek: 15000
---

## Problem

Alla projekt kräver manuella kommandon och en lokal dator för att köra. Inget kör automatiskt.

## Solution

GitHub Actions för schemalagda körningar, statisk hosting för alla outputs, ingen lokal server behövs.

## Target Audience

**Primary:** Mig själv

## Assumptions to Validate

- GitHub Actions cron räcker för daglig körning av DocsWatch och Changelog Engine Mini
- Statisk hosting (GitHub Pages) räcker för alla tre outputs i MVP
- Snapshot-storage för DocsWatch kan lösas via git commit i samma repo
- Migrering till egen server senare kräver ingen kodändring, bara ny trigger

## Why Buy Instead of Build?

## MVP Steps

- [x] Inventera repos: bekräfta att DocsWatch och Changelog Engine Mini har egna GitHub-repos
- [x] Sätt upp GitHub Actions workflow för DocsWatch (daglig cron, committar snapshots)
- [x] Sätt upp GitHub Actions workflow för Changelog Engine Mini (triggas efter DocsWatch)
- [x] Publicera Dashboard på GitHub Pages
- [x] Verifiera att alla tre outputs är tillgängliga via URL utan lokal dator

## Cost Estimate

## Value Estimate

## ROI

## Risk Assessment

- **Technical** (score 2/5): DocsWatch snapshot-storage via git kan bli klumpigt vid stora diffs
- **Ops** (score 2/5): GitHub Actions cron är inte garanterat exakt – kan vara försenat upp till 15 min
- **Technical** (score 1/5): Privata repos kostar Actions-minuter, men dagliga jobb ryms inom gratiskvoten

## Timeline

## Notes
