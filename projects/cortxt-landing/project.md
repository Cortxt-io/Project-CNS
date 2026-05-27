---
title: Cortxt Landing
slug: cortxt-landing
status: early_mvp
mvp_stage: solution_test
family: cns-core
cost_sek: 6000
value_sek: 30000
roi_percent: 400
tags:
  - react
  - vite
  - tailwind
  - reactflow
  - cloudflare-pages
  - marketing
url_repo: https://github.com/rian010194/cortxt
url_live: https://cortxt.io
created: '2026-05-27'
updated: '2026-05-27'
summary: Statisk landningssida för Cortxt på cortxt.io. Förklarar produkten, visar pipeline-diagram och samlar waitlist-intresse.
---

## Problem

Cortxt saknar en publik webbyta som förklarar vad produkten är, vilket problem den löser och varför en utvecklare ska bry sig. Utan landningssida finns ingen möjlighet att samla intresse, testa budskap eller länka till portföljen.

## Solution

En statisk React-app byggd med Vite, Tailwind och Reactflow. Sektioner: Hero, CNS-förklaring, Pipeline-diagram (Reactflow), Builder-sektion, Stack, Vision och Waitlist-formulär. Deployas till cortxt.io via Cloudflare Pages från cortxt-repot (apps/landing/).

## Target Audience

**Primary:** Utvecklare och tech leads som söker strukturerade verktyg för AI-assisterad produktutveckling. Potentiella tidiga användare av Cortxt.

**Secondary:** Framtida arbetsgivare och samarbetspartners som vill förstå vad Cortxt är.

## Assumptions to Validate

- Budskapet "Copilot skriver din kod, Cortxt bestämmer vad som är värt att bygga" resonerar med målgruppen.
- Waitlist-formuläret genererar reella intresseanmälningar från rätt personer.
- Pipeline-diagrammet (Reactflow) kommunicerar systemets komplexitet utan att förvirra.
- cortxt.io som domän upplevs som professionell och minnesvärd.

## Why Buy Instead of Build?

- En publik URL är nödvändig för att validera budskap och samla intresse innan produkten är klar.
- Landningssidan är beviset på att Cortxt faktiskt existerar — inte bara ett CLI-verktyg i en terminal.
- Cloudflare Pages ger global CDN, HTTPS och noll driftkostnad.

## MVP Steps

- [x] Hypothesis: finns det ett budskap som förklarar Cortxt på ett sätt som resonerar?
- [x] Solution test: bygg och deploya landningssidan, verifiera att den laddas korrekt på cortxt.io.
- [ ] Demand test: samla 10+ waitlist-anmälningar från verkliga utvecklare.
- [ ] Launch: polera copy, lägg till analytics, länka från GitHub-profil och relevanta communities.

## Cost Estimate

6 000 SEK (ca 24h × 250 kr/h) — React-komponenter, Reactflow-diagram, Cloudflare Pages-setup, DNS-konfiguration.

## Value Estimate

30 000 SEK — publik närvaro för Cortxt, waitlist-validering, professionell presentation mot arbetsgivare och samarbetspartners.

## ROI

(30 000 - 6 000) / 6 000 = 400%

## Risk Assessment

- **Market** (score 2/5): Budskapet kanske inte resonerar med målgruppen — waitlist-anmälningar validerar detta.
- **Technical** (score 1/5): Statisk React-app med minimal komplexitet, låg teknisk risk.
- **Ops** (score 1/5): Cloudflare Pages är stabilt, noll server att underhålla.

## Timeline

- Vecka 1 (klar): React-komponenter, Reactflow-diagram, Cloudflare Pages-deploy.
- Vecka 2: Waitlist-integration, analytics, copy-iteration baserad på feedback.
- Vecka 3+: Uppdatera innehåll i takt med att produkten mognar.

## Notes

Koden lever i cortxt-repot under apps/landing/. Cloudflare Pages bygger automatiskt vid push till main. DNS hanteras av Cloudflare (nameservers bytta från Porkbun 2026-05-27). Waitlist-formuläret är byggt men inte kopplat till backend ännu.
