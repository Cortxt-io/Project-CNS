---
slug: juvahem
title: Juvahem
current_phase: konsolidera
phases:
  discovery:
    status: done
    epics:
      - { title: "Vision: beslutsverktyg för par som väljer var de ska flytta", done: true }
  spec:
    status: done
    epics:
      - { title: "Parets kombinerade profil-input + ranknings-output (290 kommuner)", done: true, nodes: [juvahem-scoring] }
      - { title: "Datamodell + moat: Kolada/JobTech/SCB ger ärligt försprång", done: true, nodes: [juvahem-etl] }
  mvp:
    status: done
    epics:
      - { title: "ETL-pipeline (datakällor → kommun-score, provenance per värde)", done: true, nodes: [juvahem-etl] }
      - { title: "Scoring mot parets profil (transparent WSM, dual-career)", done: true, nodes: [juvahem-scoring] }
      - { title: "Resultat-UI (kartvy + rankning)", done: true, nodes: [juvahem-ui] }
  konsolidera:
    status: active
    epics:
      - { title: "Tester: scoring + explain mot faktisk data/communes/*.json (kritisk lucka)", done: false, nodes: [juvahem-scoring] }
      - { title: "Härda data→UI-sömmen: runtime-validering så ETL-fältändring ej tyst bryter UI", done: false, nodes: [juvahem-scoring, juvahem-ui] }
      - { title: "UI-refaktor: ett rankings-dataflöde, ta bort Explanation-dubbletten", done: false, nodes: [juvahem-ui] }
      - { title: "UI på designsystemet (shadcn-svelte) så features komponeras", done: false, nodes: [juvahem-ui] }
  live:
    status: todo
    epics:
      - { title: "Konsoliderad version ersätter vibe-v1 på juvahem.se", done: false, nodes: [juvahem-ui] }
  users:
    status: todo
    epics: []
  validated:
    status: todo
    epics: []
  paying:
    status: todo
    epics: []
open_decisions:
  - { title: "Gratis-data-MVP räcker eller krävs betald datakälla?", why: "Booli var juridiskt spärrad; moat beror på datatillgång.", nodes: [juvahem-etl] }
---

Roadmap för Juvahem (par-relocation, rankar 290 kommuner). v1 är live på juvahem.se. Beslut
(decisions/juvahem.md): **refaktorera, inte bygg om** — kodgranskningen visade att kärnan (ETL,
scoring, explain, data-kontrakt) redan är ren och bevisad; arbetet är att konsolidera (tester,
härda sömmen, UI-refaktor på designsystemet), inte starta från noll. Aktuell fas: Konsolidera.
