---
type: bygg
title: Bygg / implementation
mode: exekvering
agents: [operativ-chef, backend-utvecklare, frontend-utvecklare, plattformsingenjor, devops-ingenjor]
---

# Bygg-session

Syfte: exekvera definierat arbete — en quest med öppna issues.

## Agentbeteende
- **Kalla hela agenturen** via operativ-chef; Claude dirigerar, agenter kör.
- **Spec först:** granska/skriv en implementationsspec innan kod; öppna frågor ställs i specen.
- Arbeta mot questens issues: starta passet med `cortxt_start_session` (link: quest), bocka todos via `cortxt_check_todo`, stäng issues via `cortxt_close_issue`.
- Egen branch — aldrig direkt mot main; **fråga alltid före main-merge** (produktionsdeploy).
- **Merge-trigger:** när branchen är >10 commits före main ELLER alla questens issues är stängda → påminn Rikard om merge-beslutet aktivt, vänta inte på att hen frågar.
- Kedja commit+push atomiskt och verifiera mot remote (delat repo, parallella sessioner).
- Bygg inte om det som funkar; återanvänd befintliga komponenter och konstanter.

## Avslut
- Verifiera (kör koden/testen), uppdatera berörd `CLAUDE.md` i samma ändring.
- `cortxt_mark_session_done` med sammanfattning.
