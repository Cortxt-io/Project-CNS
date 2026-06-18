---
type: triage
title: Triage / städning
mode: exekvering
agents: [produktchef, underhallsingenjor]
---

# Triage-session

Syfte: hålla idé-inkorgen och quest-listan ren — resolva, promota, klustra, stänga.

## Agentbeteende
- **Agera proaktivt** (CNS-bokföring sköts utan att fråga om lov): överspelade idéer → `cortxt_resolve_idea`; mogna idéer → `cortxt_promote_idea_to_issue` (under rätt quest/milestone); kluster av relaterade idéer → föreslå en quest.
- Quests där alla issues är stängda: stäng questen eller definiera nästa issue — lämna dem inte 100 %-öppna.
- Sätt slug på idéer utan nodhemvist när hemvisten är uppenbar; tvinga inte (nod-slugs kan vara uppskjutna av strukturskäl).
- Beslut med vägval presenteras med AskUserQuestion-väljaren; ren bokföring frågar inte.
- Rör inte kod — detta är ett bokföringspass.

## Avslut
- Rapport: X resolvade, Y promotade, Z kvar — och varför de är kvar.
- `cortxt_save_session` med länk till berörd nod.
