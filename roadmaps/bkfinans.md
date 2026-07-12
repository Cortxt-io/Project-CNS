---
slug: bkfinans
title: BK Finans
# current_phase BORTTAGET — härleds (lab/scripts/phase_derive.py). Det handskrivna värdet sa
# "spec" medan v0.1 legat live på bkfinans.se. `status:` per fas likaså — härleds ur stegen.
phases:
  discovery:
    epics:
      - { title: "Vem är den för: den som funderar på att starta eget, eller den som redan bestämt sig?", done: false }
      - { title: "Marknadskarta: vad gör Verksamt/banker/redovisningsbyråer redan gratis?", done: false }
      - { title: "North star: vad betyder 'den hjälpte mig fatta beslutet'?", done: false }
  spec:
    epics:
      - { title: "Re-spec smal v1: starta-eget-beslutet (klarar hushållet steget?)", done: false }
      - { title: "Regelmotor-modell (transparent, ingen rådgivning) — input/output", done: false }
      - { title: "Kill-kriterier: när är gratis-alternativen goda nog att vi lägger ner?", done: false }
  mvp:
    epics:
      - { title: "Regelmotor (TDD) + resultat-yta", done: true }
      - { title: "CNS-söm via getDecisionModel", done: true }
  konsolidera:
    epics:
      - { title: "UI på designsystemet (shadcn-svelte) — landat", done: true }
      - { title: "Typad söm regelmotor → UI: fältändring får inte tyst bryta resultatytan", done: false }
      - { title: "Extrahera regelmotorn ur UI-lagret så fler kontexter kan komponeras", done: false }
  live:
    epics:
      - { title: "Konsoliderad version ersätter vibe-v0.1 på bkfinans.se", done: false }
  users:
    epics: []
  validated:
    epics: []
  paying:
    epics: []
open_decisions:
  - { title: "Bygga om från grunden eller refaktorera vibe-koden?", why: "v0.1 live på bkfinans.se; avgör ombyggnadens start." }
  - { title: "Smal (bara starta-eget) eller fler kontexter i v1?", why: "Separation/first-home/household-stress är förberedda — scope-grind." }
---

Ombyggnads-roadmap för BK Finans (beslutsstöd för svåra ekonomiska livsbeslut, SvelteKit). **v0.1 är
vibe-kodad och live** på bkfinans.se — passerade alltså live-fasen utan att stänga en enda grind
bakom sig. Regelmotorn är TDD:ad, vilket är mer än de flesta vibe-bygg kan säga; skulden ligger i
sömmen och i att discovery aldrig gjordes.

Fasen och stegen härleds (`cns venture status bkfinans`). Denna fil bär bara epics och öppna beslut.
