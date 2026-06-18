---
type: review
title: Review / konvergens
mode: granskning
agents: [devops-ingenjor, underhallsingenjor]
---

# Review-session

Syfte: granska och förena — PRs, branches och parallella sessioners slutsatser.

## Agentbeteende
- Kör `cns-sync`-mönstret först: `cortxt_list_sessions(link_ref=…)` för överlappsdetektering innan något mergas.
- Granska öppna PRs/branches (`cortxt_list_prs`, branch-läget); merga slutsatser ner i `node.md` — merga aldrig transkript.
- **Fråga alltid före merge till main** — det är en produktionsdeploy; ett kort "ja" räcker inte, varna tydligt.
- Stäng questar vars arbete bevisligen landat; flagga branches som driver isär.
- Read-first: ändra inget förrän helhetsbilden är klar.

## Avslut
- Konvergensrapport: vad förenades, vad väntar, vad blockerar.
- `cortxt_save_session` (eller `cns-flush`-skillen) med slutsatsen.
