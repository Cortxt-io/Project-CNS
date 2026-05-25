---
title: "Dev Changelog Engine Mini"
slug: "dev-changelog-engine-mini"
status: early_mvp
tags: [typescript, nodejs, docswatch, digest]
cost_sek: 3000
value_sek: 12000
roi_percent: 300
mvp_stage: solution_test
created: 2026-05-05
updated: 2026-05-11
current_slice: "Step 4 — Markdown & HTML renderers"
summary: Omvandlar DocsWatch-data till prioriterade veckodigest i Markdown och HTML.
family: digest-pipeline
url_repo: https://github.com/rian010194/dev-changelog-engine-mini
url_live: https://rian010194.github.io/dev-changelog-engine-mini/
---

## Problem

Raw change data from DocsWatch is technical and unreadable for quick consumption. There is no automated way to turn monitored site changes into a concise, human-friendly weekly digest.

## Solution

A pipeline that ingests DocsWatch exports, scores changes by relevance, and renders prioritized weekly digests in Markdown and static HTML.

## Target Audience

- Myself (portfolio/learning project)
- Developers who follow documentation changes and want summarized updates

## Assumptions to Validate

- DocsWatch export format is stable enough to build on
- Heuristic scoring provides useful prioritization without ML
- Weekly cadence is the right default for digests

## MVP Steps

- [x] Repository skeleton & ChangeEvent schema
- [x] DocsWatch adapter (data ingestion)
- [x] Scoring heuristics (prioritize changes)
- [x] Markdown & HTML renderer
- [ ] LLM summarizer (concise descriptions)
- [ ] GitHub Pages publishing

## Cost Estimate

~3000 SEK (development time, no infrastructure costs — runs locally with Node.js)

## Value Estimate

~12000 SEK (portfolio value, automation of manual digest writing, reusable pipeline pattern)

## ROI

(12000 - 3000) / 3000 = 300%

## Risk Assessment

- Low: No external dependencies beyond DocsWatch exports
- Medium: LLM summarization quality depends on prompt engineering
- Low: Static output means no hosting complexity

## Notes

- Consumes DocsWatch data but does NOT duplicate its monitoring
- Boundary: DocsWatch watches, this engine summarizes
- Tech stack: TypeScript, Commander.js, Node.js
- Design principle: "AI is a component, not the product"
