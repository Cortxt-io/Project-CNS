---
cost_sek: 8000
created: '2026-05-25'
depends_on: []
family: cns-core
feeds: []
kind: component
layer: infrastructure
mvp_stage: hypothesis
part_of: infrastructure
roi_percent: 400
slug: cns-vault-app
stage: working
status: idea
summary: Flask-webapplikation som exponerar CNS via webb med portföljöversikt, projektsidor
  och AI-review i webbläsaren.
tags:
- python
- flask
- railway
- web
- cns-core
title: CNS Vault App
updated: '2026-05-25'
url_live: https://project-cns-production.up.railway.app
url_repo: https://github.com/rian010194/Project-CNS
value_sek: 40000
---

## Syfte

## Beroenden

## Status

## Nästa steg

## Risker

## Arbetslogg

## Anteckningar

## Problem

CNS lever idag helt i terminalen. Det finns ingen webbyta för att se projektsidor med fullt innehåll, trigga AI-analys eller godkänna förslag utan att öppna en terminal. GitHub Pages-dashboarden är skrivskyddad och statisk – den kan inte interagera med projektdata.

## Solution

En Flask-app på Railway som importerar befintliga CNS-scripts och exponerar dem via webb. Portföljöversikt, projektsidor med hela projektmappen renderad, Analyze-knapp som triggar OpenAI-analys, och Review-vy där förslag godkänns eller avvisas med ett klick. Git används för synkronisering – pull före läsning, commit+push efter skrivning.

## Target Audience

**Primary:** Mig själv – portföljägare som vill hantera CNS-portföljen från webbläsaren utan att vara bunden till en terminal eller en specifik dator.

## Assumptions to Validate

- Flask + Railway-mönstret (git pull/push som synkmekanism) är stabilt nog för sporadisk ensam användning.
- Basic Auth räcker som säkerhetslösning för ett personligt verktyg.
- Latensen från git pull innan varje request är acceptabel (< 3 sek).
- Webbgränssnittet används faktiskt istället för terminalen för review-flödet.
- GitHub Pages + Railway API-integration fungerar utan CORS-problem.

## Why Buy Instead of Build?

- Ger tillgång till hela CNS-portföljen från vilken enhet som helst utan terminal.
- Eliminerar behovet av att vara vid rätt dator för att godkänna AI-förslag.
- Återanvändbart mönster (Flask + git_ops + Railway) för framtida interna verktyg i CNS-familjen.

## MVP Steps

- Hypothesis: verifiera att Flask + git pull/push på Railway fungerar som synkmekanism utan konflikter.
- Solution test: kör portföljöversikt, projektsida och review-flödet mot verkliga projekt på Railway.
- Demand test: används webbappen faktiskt för review istället för terminalen?
- Launch: stabil Railway-deploy med Basic Auth, Analyze-knapp i GitHub Pages-dashboard, dokumenterat i README.

## Cost Estimate

8 000 SEK – Flask-app, templates, git_ops, Railway-setup och integration mot GitHub Pages. Railway-kostnad ~60 SEK/månad (~720 SEK/år) ingår inte i engångskostnaden.

## Value Estimate

40 000 SEK – tillgång till CNS från vilken enhet som helst, snabbare review-flöde, återanvändbart Flask+Railway-mönster för framtida CNS-verktyg, professionell presentation av portföljen.

## ROI

(40 000 - 8 000) / 8 000 = 400%

## Risk Assessment

- **Technical** (score 3/5): Git pull/push som synkmekanism kan ge konflikter om lokala och Railway-ändringar sker samtidigt.
- **Ops** (score 2/5): Railway-appen kan "sova" på gratisplan – första laddningen tar 30–60 sek. Uppgradering till betald plan löser detta.
- **Technical** (score 2/5): CORS-konfiguration krävs för att GitHub Pages ska kunna anropa Railway API.
- **Market** (score 1/5): Personligt verktyg, ingen extern marknadsrisk.

## Timeline

- Vecka 1: Flask-app lokalt – portföljöversikt + projektsida.
- Vecka 2: Review-flöde + git_ops + Basic Auth.
- Vecka 3: Railway-deploy + environment variables + verifiering.
- Vecka 4: GitHub Pages-integration (Analyze-knapp + tryRailwayAction()).

## Notes

Koden lever i app/-mappen i Project-CNS-repot. Inget eget repo. Importerar scripts/ direkt – ingen koddupliciering. Designprincip: spegla Project Vault Dashboard visuellt, Tailwind CDN, identiska statusfärger och kortdesign. git_ops.py är ett fristående utility återanvändbart i framtida Flask-appar i CNS-familjen. Railway environment variables: CNS_USERNAME, CNS_PASSWORD, GITHUB_TOKEN, GITHUB_REPO, OPENAI_API_KEY.
