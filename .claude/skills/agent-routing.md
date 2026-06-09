---
name: agent-routing
description: Komplett routing-karta för agenturen — vilken agent hanterar vad och när du ska kalla på vem.
---

# Agent-routing: vem gör vad

Använd den här kartan när du vet att en uppgift borde delegeras. Kalla alltid på **teamleadern** om du är osäker — det är hans jobb att matcha.

## Routing-matris

| Uppgift | Primär | Sekundär |
|---------|--------|---------|
| Vilka agenter finns? Vad pågår? | kontext-agent | — |
| Koordinera flera agenter | teamleader | — |
| Ny agent behöver skapas | hr-chefen | tranaren (validering) |
| Förbättra en befintlig agents prompt | tranaren | hr-chefen |
| Token-/kreditförbrukning, effektivitet | ekonomen | — |
| Teknisk research, externa jämförelser | research-agent | — |
| Gamla noder, stale wiki, städning | stadaren | — |
| PR-status, CI, GitHub-issues | github-agent | — |
| Idéer som dyker upp under arbete | ide-agent | — |
| Arkitekturdokumentation, wiki | wiki-skribent | — |
| Flask, FastMCP, MCP-verktyg, Railway | backend-agent | fullstack-agent |
| React, Vite, dashboard, Tailwind | frontend-agent | fullstack-agent |
| Feature som spänner backend + frontend | fullstack-agent | — |
| CLI, TUI, Rich, scripts/, session-mgmt | scripts-agent | — |
| Eskalering till Rikard | teamleader → Rikard | — |

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
