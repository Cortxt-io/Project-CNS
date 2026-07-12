---
slug: crusade
title: Crusade
# current_phase BORTTAGET — härleds (lab/scripts/phase_derive.py). `status:` per fas likaså.
phases:
  discovery:
    epics:
      - { title: "Vem bryr sig om token-effektivitet nog för att titta på en leaderboard?", done: false }
      - { title: "Marknadskarta: finns benchmarken redan (SWE-bench, HumanEval, Aider)?", done: false }
      - { title: "North star: vad betyder 'den funkar' för en benchmark?", done: false }
  spec:
    epics:
      - { title: "Definiera mätbar effektivitet (token/korrekthet) + scope för MVP-leaderboard", done: false }
      - { title: "Gateway-mätpunkt specad (vad mäts serverside = moat)", done: false }
      - { title: "Kill-kriterier: kostnadsexponeringen är make-or-break — vid vilken kostnad dör den?", done: false }
  mvp:
    epics:
      - { title: "Go-gateway: reverse proxy som mäter tokens per körning", done: false }
      - { title: "Leaderboard-yta (människa + agent-team rankas)", done: false }
  konsolidera:
    epics:
      - { title: "UI på designsystemet från start (ingen vibe-skuld att betala)", done: false }
      - { title: "Typad söm mellan gateway-mätning och leaderboard", done: false }
  live:
    epics:
      - { title: "Deploya gateway + leaderboard (Railway/Vercel)", done: false }
  users:
    epics: []
  validated:
    epics: []
  paying:
    epics: []
open_decisions:
  - { title: "Publik yta nu eller stängd beta?", why: "Domänerna är parkerade; ingen publik yta än — avgör om MVP exponeras." }
  - { title: "Mäter vi bara token-effektivitet eller även korrekthet i v1?", why: "Scope-grind: korrekthet kräver en sanningskälla per uppgift." }
---

Ombyggnads-roadmap för Crusade (effektivitets-benchmark, repo Cortxt-io/crusade). **Ren start** — inget
live att riva, och därför den enda vertikalen som kan passera grindarna i rätt ordning. Använd den som
bevis på att receptet fungerar när det följs.

Moat = serverside token-mätning i gatewayen. Kostnadsexponeringen är make-or-break — därför är
kill-kriteriet i spec-fasen inte en formalitet.

Fasen och stegen härleds (`cns venture status crusade`). Denna fil bär bara epics och öppna beslut.
