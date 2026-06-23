---
slug: orgkomp
title: Orgkomp
current_phase: spec
phases:
  spec:
    status: active
    epics:
      - { title: "Re-spec: redigerbar org-/ansvars-/beroende-utforskare (roller-först typad graf)", done: false }
      - { title: "Datamodell: reports_to / depends_on + lagring/export", done: false }
  mvp:
    status: todo
    epics:
      - { title: "Graf-editor (AntV G6) + roll-modell", done: false }
      - { title: "Import/export (JSON) + localStorage", done: false }
  live:
    status: todo
    epics:
      - { title: "Deploy på orgkomp.com (ren ombyggnad)", done: false }
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
  - { title: "JumpYard-specifik leverans eller generell produkt?", why: "Byggd som kundleverans åt JumpYard; avgör om ombyggnaden generaliseras." }
  - { title: "Bygga om från grunden eller behålla Next/G6-basen?", why: "Live på orgkomp.com; avgör ombyggnadens start." }
---

Ombyggnads-roadmap för Orgkomp (org-/ansvars-utforskare, Next/AntV G6). Live på orgkomp.com (JumpYard-
leverans) — detta är planen ombyggnaden drivs mot. Finslipa epics + beslut.
