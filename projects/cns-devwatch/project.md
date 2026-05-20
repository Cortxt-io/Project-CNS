---
cost_sek: 3000
created: '2026-05-20'
mvp_stage: hypothesis
roi_percent: 233
slug: cns-devwatch
status: idea
tags:
- devtools
- monitoring
- internal
- git
- python
title: CNS DevWatch
updated: '2026-05-20'
value_sek: 10000
---

## Problem

CNS har ingen automatisk vy över vad som ändrats i egna project.md-filer dag för dag.

## Solution

Git diff-baserad bevakning av project.md-filer som detekterar och exporterar portföljändringar dagligen.

## Target Audience

**Primary:** Mig själv - portföljägare som vill ha intern monitoring utan manuell genomgång.

## Assumptions to Validate

- Git diff på project.md-filer ger tillräcklig signal om vad som faktiskt förändrats i portföljarbetet.
- Daglig körning är rätt kadens – varken för frekvent (brus) eller för sällan (förlorad kontext).
- Diff-output är strukturerad nog att cns-devlog kan konsumera den utan manuell bearbetning.
- En portföljägare med 5–10 aktiva projekt behöver inte mer än filnivå-diff för att förstå vad som hänt.

## Why Buy Instead of Build?

## MVP Steps

- Hypothesis: verifiera att git log + diff på projects/-mappen ger meningsfull daglig signal.
- Solution test: kör skriptet dagligen i en vecka, utvärdera om output speglar vad som faktiskt gjordes.
- Demand test: kontrollera om output faktiskt används som input till cns-devlog eller ignoreras.
- Launch: schemalägg via GitHub Actions eller cron, integrera med cns-devlog-pipeline.

## Cost Estimate

Uppskattat till 3 000 SEK – enbart utvecklingstid för ett internt Python-skript. Ingen infrastruktur, inga licenser.

## Value Estimate

Uppskattat till 10 000 SEK – sparad tid från manuell genomgång av projektfiler, plus ökad synlighet som driver bättre prioriteringar.

## ROI

(10 000 - 3 000) / 3 000 = 233%

## Risk Assessment

- **Technical** (score 2/5): Git-historik kan saknas eller vara glesa commits – diff ger då ingen signal. Kräver disciplin att committa project.md-ändringar regelbundet.
- **Ops** (score 3/5): Skriptet måste köras dagligen för att ge värde. Om det inte automatiseras tidigt faller det i glömska.
- **Ops** (score 2/5): Output-format måste vara stabilt från dag ett – annars bryts cns-devlog-integrationen vid minsta ändring.

## Timeline

- Vecka 1: Implementera git diff-logik, filtrera på projects/-mappen, exportera till JSON.
- Vecka 2: Kör dagligen manuellt, utvärdera signal vs brus. Justera filter.
- Vecka 3: Koppla output till cns-devlog (även om devlog inte är klar – definiera kontraktet).
- Vecka 4: Automatisera via cron eller GitHub Actions. Dokumentera i Notes.

## Notes

Koden lever i prompt-cns/scripts/ tills vidare – inget eget repo. Hårt beroende: CNS-repot måste vara ett git-repo med regelbunden commit-historik på project.md-filer. Utan commits ingen diff, utan diff inget värde.

Testar att lägga till en rad