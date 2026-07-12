---
slug: juvahem
title: Juvahem
# current_phase BORTTAGET — härleds (lab/scripts/phase_derive.py). `status:` per fas likaså.
phases:
  discovery:
    epics:
      - { title: "Vision: beslutsverktyg för den som väljer var hen ska flytta (290 kommuner mot din profil)", done: true }
  spec:
    epics:
      - { title: "Profil-input + ranknings-output (290 kommuner mot dina prioriteringar)", done: true, nodes: [juvahem-scoring] }
      - { title: "Datamodell + moat: Kolada/JobTech/SCB ger ärligt försprång", done: true, nodes: [juvahem-etl] }
  mvp:
    epics:
      - { title: "ETL-pipeline (datakällor → kommun-score, provenance per värde)", done: true, nodes: [juvahem-etl] }
      - { title: "Scoring mot profilens prioriteringar (transparent WSM; dual-career = ett läge)", done: true, nodes: [juvahem-scoring] }
      - { title: "Resultat-UI (kartvy + rankning)", done: true, nodes: [juvahem-ui] }
  konsolidera:
    epics:
      - { title: "Tester: scoring/explain/invest/presets/price mot faktisk data — wire:ade i npm test (run-all)", done: true, nodes: [juvahem-scoring] }
      - { title: "Härda data→UI-sömmen: runtime-validering så ETL-fältändring ej tyst bryter UI", done: false, nodes: [juvahem-scoring, juvahem-ui] }
      - { title: "UI-refaktor /jamfor: progressiv avtäckning, flik-expansion, Explanation-dedup (juvahem#6)", done: true, nodes: [juvahem-ui] }
      - { title: "UI på designsystemet (shadcn-svelte) så features komponeras", done: false, nodes: [juvahem-ui] }
  live:
    epics:
      - { title: "Konsoliderad version ersätter vibe-v1 på juvahem.se", done: false, nodes: [juvahem-ui] }
  users:
    epics: []
  validated:
    epics: []
  paying:
    epics: []
open_decisions:
  - { title: "Gratis-data-MVP räcker eller krävs betald datakälla?", why: "Booli var juridiskt spärrad; moat beror på datatillgång.", nodes: [juvahem-etl] }
---

Roadmap för Juvahem (kommunval/relocation — rankar 290 kommuner mot din profil). v1 är live på juvahem.se. Beslut
(decisions/juvahem.md): **refaktorera, inte bygg om** — kodgranskningen visade att kärnan (ETL,
scoring, explain, data-kontrakt) redan är ren och bevisad; arbetet är att konsolidera (tester,
härda sömmen, UI-refaktor på designsystemet), inte starta från noll. Fasen härleds (`cns venture status juvahem`).
