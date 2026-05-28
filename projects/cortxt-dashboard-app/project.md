---
title: Cortxt Dashboard App
slug: cortxt-dashboard-app
status: early_mvp
mvp_stage: solution_test
family: cns-core
cost_sek: 8000
value_sek: 35000
roi_percent: 338
tags:
- react
- vite
- tailwind
- reactflow
- cloudflare-pages
- dashboard
url_repo: https://github.com/rian010194/cortxt
url_live: https://app.cortxt.io
created: '2026-05-27'
updated: '2026-05-27'
summary: React SPA på app.cortxt.io som visualiserar CNS-portföljen via Railway Flask
  API. Portföljgrid, projektdetaljer och Reactflow graph-overlay.
layer: interface
---

## Problem

CNS-portföljen lever i Markdown och CLI. Det finns ingen visuell webbapp där man kan navigera projekt, läsa fullständig projektdata och se portföljstrukturen som en graf. Den befintliga vanilla JS-dashboarden på GitHub Pages är skrivskyddad och statisk utan projektsidor eller graph-vy.

## Solution

En React SPA byggd med Vite, Tailwind och Reactflow som konsumerar Railway Flask API (/api/projects, /api/project/<slug>/full). Tre vyer: portföljgrid med filter på status och family, projektdetaljsida med renderad Markdown och projektfiler, samt Reactflow graph-overlay grupperad per produktfamilj. HashRouter för statisk hosting. Deployas till app.cortxt.io via Cloudflare Pages från cortxt-repot (apps/dashboard/).

## Target Audience

**Primary:** Mig själv — portföljägare som vill navigera och läsa projektdata från webbläsaren utan att öppna terminalen.

**Secondary:** Framtida arbetsgivare och samarbetspartners som vill se portföljens djup och struktur.

## Assumptions to Validate

- Railway Flask API exponerar tillräckligt med data för att göra appen användbar utan extra endpoints.
- Reactflow graph-vyn ger faktiskt ett mervärde jämfört med kortgriden för att förstå portföljstrukturen.
- app.cortxt.io används faktiskt som primär ingång till portföljen istället för terminalen eller vanilla JS-dashboarden.
- HashRouter fungerar utan problem på Cloudflare Pages.

## Why Buy Instead of Build?

- Ger tillgång till hela CNS-portföljen med full projektdata från vilken enhet som helst.
- Graph-vyn kommunicerar portföljstrukturen på ett sätt som varken terminal eller kortgrid kan.
- Återanvändbart mönster (React + Railway API + Cloudflare Pages) för framtida Cortxt-ytor.

## MVP Steps

- [x] Hypothesis: Railway API exponerar rätt data för att driva en React-dashboard.
- [ ] Solution test: deploya apps/dashboard/, verifiera att portföljgrid, projektdetalj och graph-overlay fungerar mot live API.
- [ ] Demand test: används app.cortxt.io faktiskt som primär ingång istället för terminalen?
- [ ] Launch: stabil deploy, family-enum migrerad, app.cortxt.io custom domain aktiv.

## Cost Estimate

8 000 SEK (ca 32h × 250 kr/h) — React-komponenter, Reactflow graph-vy, hooks mot Railway API, Cloudflare Pages-setup.

## Value Estimate

35 000 SEK — visuell portföljnavigering från vilken enhet som helst, graph-vy som kommunicerar struktur, professionell presentation mot arbetsgivare.

## ROI

(35 000 - 8 000) / 8 000 = 338%

## Risk Assessment

- **Technical** (score 2/5): Reactflow GroupNode-layout kräver manuell positionering — kan bli komplex om antalet projekt växer snabbt.
- **Market** (score 1/5): Personligt verktyg, låg extern marknadsrisk.
- **Ops** (score 1/5): Cloudflare Pages är stabilt, Railway API kör redan.

## Timeline

- Vecka 1 (pågår): Qoder-implementation av apps/dashboard/ — alla komponenter, hooks, graph-vy.
- Vecka 2: Verifiera mot live API, fixa edge cases, aktivera app.cortxt.io custom domain.
- Vecka 3: Demand test — används appen faktiskt? Iterera baserat på egna observationer.

## Notes

Koden lever i cortxt-repot under apps/dashboard/. Ersätter vanilla JS-dashboarden på rian010194.github.io/Project-CNS/ på sikt. Family-enum dual-mapping i labels.js hanterar övergångsperioden. CORS för app.cortxt.io tillagd i prompt-cns/app/server.py.
