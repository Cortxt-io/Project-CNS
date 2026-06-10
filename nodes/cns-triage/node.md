---
created: '2026-05-02'
updated: '2026-06-10'
slug: cns-triage
title: CNS Triage
kind: component
part_of: cns-core
stage: working
status: early_mvp
feeds: []
depends_on: []
summary: Intern triage av CNS idé-inkorg och noder — gruppera, resolva/promota idéer och föreslå nästa session.
tags: []
url_live: ''
url_repo: ''
---

## Syfte

Intern triage-förmåga för att hålla CNS rent och handlingsbart: gå igenom idé-inkorgen (`idea_inbox.py`), gruppera överspelade/mogna/klustrade idéer, resolva (`cortxt_resolve_idea`) eller promota (`cortxt_promote_idea_to_issue`) dem, och städa nodmodellen (föräldralösa idé-noder, dubbletter, felplacerade noder). Driver dessutom sessionsrekommendationer via `recommend.py` och triage-sessionsprofilen.

## Beroenden

Läser idé-inkorgen och nodgrafen via datalagret; skrivningar (resolve/promote) går via MCP-verktygen mot GitHub.

## Status

Fungerande: idé-resolve/promote-verktygen och triage-flödet används aktivt. Vidareutveckling pågår (samlat `cortxt_triage`-batchverktyg + TUI-triagevy är fortsatt idéer i inkorgen).

## Nästa steg

## Risker

## Arbetslogg

## Anteckningar

Repurposad 2026-06-10: noden beskrev tidigare en extern supportärende-triage-produkt (auto-genererad framing). Den representerar nu CNS:s interna triage som faktiskt byggts. Slug bytt från legacy `ai-ticket-triage` → `cns-triage` 2026-06-10 (inga GitHub-issues eller barn-noder pekade på gamla sluggen). Historiska loggar (`nodes/cortxt/ARCHITECTURE.md`-exempel, `cns-analyst/planning/quests.md`, quest-f90c4ef6) behåller medvetet gamla namnet.
