---
name: agent-routing
department: Gemensam
description: Komplett routing-karta för agenturen — vilken agent hanterar vad och när du ska kalla på vem.
---

# Agent-routing: vem gör vad

Använd den här kartan när du vet att en uppgift borde delegeras. Kalla alltid på **operativ-chefn** om du är osäker — det är hans jobb att matcha.

## Routing-matris

| Uppgift | Primär | Sekundär |
|---------|--------|---------|
| Vilka agenter finns? Vad pågår? | lagesanalytiker | — |
| Koordinera flera agenter | operativ-chef | — |
| Ny agent behöver skapas | hr-chef | kompetensutvecklare (validering) |
| Förbättra en befintlig agents prompt | kompetensutvecklare | hr-chef |
| Token-/kreditförbrukning, effektivitet | ekonomichef | — |
| Teknisk research, externa jämförelser | forskningsledare | — |
| Gamla noder, stale wiki, städning | underhallsingenjor | — |
| PR-status, CI, GitHub-issues | devops-ingenjor | — |
| Idéer som dyker upp under arbete | produktchef | — |
| Arkitekturdokumentation, wiki | teknisk-skribent | — |
| Flask, FastMCP, MCP-verktyg, Railway | backend-utvecklare | fullstack-utvecklare |
| React, Vite, dashboard, Tailwind | frontend-utvecklare | fullstack-utvecklare |
| Feature som spänner backend + frontend | fullstack-utvecklare | — |
| CLI, TUI, Rich, scripts/, session-mgmt | plattformsingenjor | — |
| Eskalering till Rikard | operativ-chef → Rikard | — |

## Hur du kallar på en agent

I din output — skriv tydligt vem du lämnar till:

```
DELEGERAR TILL: [agent-namn]
UPPGIFT: [konkret vad de ska göra]
FÖRVÄNTAT RESULTAT: [vad som ska levereras tillbaka]
BEROENDE: [om din fortsättning beror på deras output]
```

## Parallellt vs sekventiellt

- **Parallellt** om output från A inte behövs som input till B
- **Sekventiellt** om B beror på A:s resultat
- Markera alltid: `ORDNING: parallell | sekventiell`

## Eskaleringskedja

```
Agent → Teamleader → Rikard
```

Hoppa aldrig direkt till Rikard utan att gå via Teamleadern, utom:
- Aktiv produktionsstopp
- Säkerhetsbeslut
- Budgetbeslut över 1M tokens/dag
