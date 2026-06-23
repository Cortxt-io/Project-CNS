---
slug: crusade
title: Crusade
current_phase: spec
phases:
  spec:
    status: active
    epics:
      - { title: "Definiera mätbar effektivitet (token/korrekthet) + scope för MVP-leaderboard", done: false }
      - { title: "Gateway-mätpunkt specad (vad mäts serverside = moat)", done: false }
  mvp:
    status: todo
    epics:
      - { title: "Go-gateway: reverse proxy som mäter tokens per körning", done: false }
      - { title: "Leaderboard-yta (människa+agent-team rankas)", done: false }
  live:
    status: todo
    epics:
      - { title: "Deploya gateway + leaderboard (Railway/Vercel)", done: false }
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
  - { title: "Publik yta nu eller stängd beta?", why: "Domänerna är parkerade; ingen publik yta än — avgör om MVP exponeras." }
  - { title: "Mäter vi bara token-effektivitet eller även korrekthet i v1?", why: "Scope-grind: korrekthet kräver en sanningskälla per uppgift." }
---

Ombyggnads-roadmap för Crusade (effektivitets-benchmark). Ren start från Spec — inget live att riva.
Moat = serverside token-mätning i gatewayen. Finslipa epics + beslut här.
