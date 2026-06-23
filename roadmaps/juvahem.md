---
slug: juvahem
title: Juvahem
current_phase: spec
phases:
  spec:
    status: active
    epics:
      - { title: "Re-spec: parets kombinerade profil-input + ranknings-output (290 kommuner)", done: false }
      - { title: "Datamodell + moat: vilken data ger ärligt försprång (Kolada m.m.)", done: false }
  mvp:
    status: todo
    epics:
      - { title: "ETL-pipeline (datakällor → kommun-score)", done: false }
      - { title: "Scoring mot parets profil + UI", done: false }
  live:
    status: todo
    epics:
      - { title: "Deploy på juvahem.se (ren ombyggnad ersätter vibe-versionen)", done: false }
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
  - { title: "Bygga om från grunden eller rädda vibe-koden?", why: "v1 är vibe-kodad och live; avgör om ombyggnaden startar rent eller refaktorerar." }
  - { title: "Gratis-data-MVP räcker eller krävs betald datakälla?", why: "Booli var juridiskt spärrad; moat beror på datatillgång." }
---

Ombyggnads-roadmap för Juvahem (par-relocation, rankar 290 kommuner). v1 vibe-kodad och live på
juvahem.se — detta är den rena planen ombyggnaden drivs mot. Finslipa epics + beslut.
