---
slug: bkfinans
title: BK Finans
current_phase: spec
phases:
  spec:
    status: active
    epics:
      - { title: "Re-spec smal v1: starta-eget-beslutet (klarar hushållet steget?)", done: false }
      - { title: "Regelmotor-modell (transparent, ingen rådgivning) — input/output", done: false }
  mvp:
    status: todo
    epics:
      - { title: "Regelmotor (TDD) + resultat-yta", done: false }
      - { title: "CNS-söm via getDecisionModel", done: false }
  live:
    status: todo
    epics:
      - { title: "Deploy på bkfinans.se (ren ombyggnad)", done: false }
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
  - { title: "Bygga om från grunden eller refaktorera vibe-koden?", why: "v0.1 live på bkfinans.se; avgör ombyggnadens start." }
  - { title: "Smal (bara starta-eget) eller fler kontexter i v1?", why: "Separation/first-home/household-stress är förberedda — scope-grind." }
---

Ombyggnads-roadmap för BK Finans (beslutsstöd svåra ekonomiska livsbeslut, SvelteKit). v0.1 vibe-kodad
och live — detta är planen ombyggnaden drivs mot. Finslipa epics + beslut.
