---
title: Cortxt Graph View
slug: cortxt-graph-view
status: idea
mvp_stage: hypothesis
family: cns-core
cost_sek: 5000
value_sek: 20000
roi_percent: 300
tags:
  - react
  - reactflow
  - dashboard
  - graph
  - visualization
url_repo: https://github.com/rian010194/cortxt
url_live: https://app.cortxt.io
created: '2026-05-27'
updated: '2026-05-27'
summary: Interaktiv Reactflow-graf i cortxt-dashboard-app som visualiserar projektberoenden och familjestrukturer med edges och hierarkisk layout.
---

## Problem

Kortgriden i cortxt-dashboard-app visar projekt platt utan kontext om hur de hänger ihop. Beroenden som docs-watch → dev-changelog-engine-mini → github-pages är osynliga. Det finns ingen vy som kommunicerar portföljens arkitektur och flöden på ett visuellt sätt.

## Solution

En Reactflow-graf i graph-overlayet i cortxt-dashboard-app. Noder grupperade per family, edges baserade på beroendedata i project.md. Klick på nod navigerar till projektdetaljsidan. Kräver att beroenden är maskinläsbara i project.md-schemat och att family-enum-migrationen är klar.

## Target Audience

**Primary:** Mig själv — för att förstå portföljens struktur och beroenden på ett ögonblick.

**Secondary:** Besökare på app.cortxt.io som vill förstå hur projekten hänger ihop.

## Assumptions to Validate

- Beroenden i project.md kan representeras som ett enkelt fält (depends_on: [slug1, slug2]) utan att det blir för komplext att underhålla.
- Reactflow GroupNode med edges ger faktiskt ett mervärde jämfört med kortgriden för att förstå portföljstrukturen.
- Family-enum-migrationen är klar innan graph-vyn byggs ut.

## Why Buy Instead of Build?

- En beroendegraf kommunicerar systemarkitektur på ett sätt som text och kortgrid inte kan.
- Visualiserar pipelines (docs-watch → changelog-engine → github-pages) på ett sätt som är omedelbart begripligt.

## MVP Steps

- [ ] Hypothesis: lägg till depends_on-fält i project.md-schemat och validera att det fungerar i CNS.
- [ ] Solution test: bygg graph-vy med edges baserade på depends_on, verifiera att beroendepilarna stämmer.
- [ ] Demand test: används graph-vyn faktiskt för att förstå portföljen?
- [ ] Launch: stabil graph-vy med edges, family-rubriker synliga, klickbara noder.

## Cost Estimate

5 000 SEK (ca 20h x 250 kr/h) — Reactflow edge-implementation, depends_on-schema, layout-algoritm.

## Value Estimate

20 000 SEK — visuell kommunikation av portföljarkitektur, professionell presentation, bättre förståelse av beroenden.

## ROI

(20 000 - 5 000) / 5 000 = 300%

## Risk Assessment

- **Technical** (score 3/5): Reactflow automatisk layout med edges kräver en layout-algoritm (dagre eller liknande) — inte trivialt med GroupNodes.
- **Ops** (score 1/5): Lever i befintligt cortxt-repo, ingen ny infrastruktur.

## Timeline

- Förutsättning 1: family-enum-migration klar i alla project.md-filer.
- Förutsättning 2: depends_on-fält tillagt i CNS-schemat och validator.py.
- Vecka 1: edges i graph-vy baserade på depends_on.
- Vecka 2: layout-algoritm, rubrik-fix, polish.

## Notes

Graph-vyn i cortxt-dashboard-app visar idag "Coming soon" i overlayet. Byggs ut när förutsättningarna ovan är uppfyllda. Koden för grundläggande Reactflow-overlay finns redan i apps/dashboard/src/components/GraphView.jsx.
