---
slug: orgkomp
title: Orgkomp
# current_phase BORTTAGET — det HÄRLEDS nu (lab/scripts/phase_derive.py). Det handskrivna
# värdet sa "spec" medan orgkomp legat live på orgkomp.com i veckor. Ett fält ingen har
# anledning att uppdatera blir alltid osant.
# `status:` per fas är också borta — den härleds ur stegens signaler.
phases:
  discovery:
    epics:
      - { title: "Vision: vem är verktyget för när det INTE är en JumpYard-leverans?", done: false }
      - { title: "Marknads-/konkurrentkarta (org-chart-verktyg: vad saknas hos dem?)", done: false }
  spec:
    epics:
      - { title: "Re-spec: redigerbar org-/ansvars-/beroende-utforskare (roller-först typad graf)", done: false }
      - { title: "Datamodell: reports_to / depends_on + lagring/export", done: false }
      - { title: "Kill-kriterier: vad får oss att lägga ner om JumpYard inte förlänger?", done: false }
  mvp:
    epics:
      - { title: "Graf-editor + roll-modell", done: true }
      - { title: "Import/export (JSON/Excel) + localStorage", done: true }
  konsolidera:
    epics:
      - { title: "UI på designsystemet (shadcn) — landat", done: true }
      - { title: "Grafstacken konsoliderad: ELK + ReactFlow ersatte handkodad SVG", done: true }
      - { title: "Typad API-söm: UI anropar aldrig fetch direkt", done: false }
      - { title: "Extrahera kärnan ur UI-lagret (model.ts-lib påbörjad i OrgChart-refaktorn)", done: false }
  live:
    epics:
      - { title: "Konsoliderad version ersätter vibe-v1 på orgkomp.com", done: false }
  users:
    epics: []
  validated:
    epics: []
  paying:
    epics: []
open_decisions:
  - { title: "JumpYard-specifik leverans eller generell produkt?", why: "Byggd som kundleverans åt JumpYard; avgör om ombyggnaden generaliseras." }
  - { title: "Bygga om från grunden eller behålla Next-basen?", why: "Live på orgkomp.com; avgör ombyggnadens start." }
---

Ombyggnads-roadmap för Orgkomp (org-/ansvars-utforskare, Next.js). **Live på orgkomp.com** (JumpYard-
leverans) — men live utan att ha stängt en enda grind bakom sig. Det är vad ombyggnaden handlar om:
inte att bygga något nytt, utan att betala tillbaka de grindar bygget passerade i farten.

Fasen och stegen härleds (`cns venture status orgkomp`). Denna fil bär bara det maskinen inte kan
veta: vilka epics som är venture-specifika, och vilka beslut som är öppna.
