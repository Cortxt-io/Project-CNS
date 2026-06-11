---
created: '2026-06-08'
updated: '2026-06-08'
slug: cns-core
title: CNS Core
kind: component
part_of: infrastructure
stage: working
status: early_mvp
feeds: []
depends_on: []
summary: CLI, markdown-parser, validator och exportörer — substratet som läser, skriver och validerar varje nod.
type: cli
domain: cortxt
tags: []
url_live: ''
url_repo: https://github.com/rian010194/Project-CNS
---

## Syfte

CNS-kärnan: CLI-entrypoint (cns.py), frontmatter-parser (md_parser.py), schemavalidator (validator.py) och exportörer (json_exporter, xlsx_exporter). Motorn som definierar vad en nod *är* — frontmatter-schemat, kind/stage-modellen, de kind-medvetna sektionsmallarna och relationerna part_of/feeds/depends_on. Nästan allt annat vilar på den.

## Beroenden

Inga interna — detta är grundbulten. Externt: Python, frontmatter, rich, openpyxl.

## Status

Working. CLI:t kör list/show/new/update/validate/quest/export samt analyze/devwatch/devlog/eventstream.

## Nästa steg

## Risker

- **Technical**: Filnamnet project.md är hårdkodat i glob (`*/project.md`) på flera ställen — byte till node.md kräver koordinerad migrering.
- **Technical**: Markdown + git som databas saknar transaktioner; samtidiga skrivningar kan ge konflikter.

## Arbetslogg

## Anteckningar

Placeringen skaver: cns-core är mer fundamental än "drift/hosting/lagring" — ett argument finns för part_of: cortxt direkt. Lämnar den i infrastructure pragmatiskt. Idealt borde många andra noder få depends_on: cns-core, men det är en separat additiv migrering, inte en del av att skapa den här noden.
