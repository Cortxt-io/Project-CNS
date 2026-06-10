---
type: verktygsladan
title: Verktygslådan
mode: underhåll
agents: [hr-chef, kompetensutvecklare, plattformsingenjor, programledare]
---

# Verktygslådan-session

Syfte: bygga ut och underhålla `.claude/`-verktygslådan — agenter, skills, hooks, session-profiler.

## Agentbeteende

- **Kalla @hr-chef** innan ny agentfil skrivs — validerar modell, verktyg, roll.
- **Kalla @tränaren** för att förbättra befintliga agentprompter och systemprompter.
- **Kalla @plattformsingenjor** för hooks, automation och `session_store.py`-ändringar.
- **Kalla @programledare** om sessionen kräver ett session-träd för att koordinera arbetet.
- Inga produktionsdeploys härifrån — verktygslådan är `.claude/`, inte `app/` eller `scripts/` (undantag: hooks i `scripts/`).

## Typiska uppgifter

- Skapa eller uppdatera `.claude/agents/*.md`
- Skapa eller uppdatera `.claude/skills/*.md`
- Lägga till routing-regler i `scripts/router.py`
- Bygga eller felsöka Stop/UserPromptSubmit-hooks
- Lägga till nya session-profiler i `sessions/profiles/`

## Avslut

- Verifiera att nya agentfiler är kompletta (eval-kriterier, tillåtna verktyg, session-protokoll).
- Commit och push till rätt branch.
- `cortxt_mark_session_done` med lista över vad som skapades/ändrades.
