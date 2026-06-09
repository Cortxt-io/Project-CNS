---
created: '2026-06-09'
updated: '2026-06-09'
slug: research-agent
title: Research Agent
kind: component
part_of: agent-studio
stage: idea
status: idea
feeds: []
depends_on: []
summary: Research-agent som söker på webben, verifierar källor och skriver findings till CNS wiki. Kör via Anthropic API (claude-sonnet-4-6).
url_live: ''
url_repo: ''
---
## Syfte
Söka, verifiera och sammanställa faktabaserade rapporter för CNS/Cortxt-projektet. Agenten används för att besvara öppna forskningsfrågor (arkitekturval, API-stabilitet, teknologijämförelser) och skriver alltid findings till en wiki-sida innan sessionen avslutas.

## Beroenden
- Anthropic API (`ANTHROPIC_API_KEY`) — ingen lokal AI krävs
- CNS MCP-server (Railway) för wiki-verktyg

## Status
Agentfil skapad. Ej testad i produktion.

## Nästa steg
- Testa agenten mot ett konkret research-uppdrag (t.ex. Claw Code-utvärdering)
- Lägg till WebSearch/WebFetch i tillåtna verktyg när MCP-routing är klar

## Risker
- API-kostnad okontrollerad vid långa söksessioner — sätt token-budget per uppdrag
- Wiki-sidor kan bli fragmenterade om agenten skapar ny sida per körning

## Arbetslogg
- 2026-06-09: Skapad via /agent-studio

## Anteckningar
```json
{
  "name": "research-agent",
  "description": "Söker, verifierar och sammanställer faktabaserade rapporter. Skriver findings till CNS wiki.",
  "provider": "anthropic",
  "model": "claude-sonnet-4-6",
  "fallback_model": "claude-haiku-4-5",
  "prompt": "Du är research-agent i CNS/Cortxt. Sök, verifiera mot minst 2 källor, skriv findings till wiki.",
  "tools": [
    "cortxt_list_projects", "cortxt_get_project",
    "cortxt_list_quests", "cortxt_get_quest",
    "cortxt_list_open_issues", "cortxt_get_issue",
    "cortxt_list_ideas",
    "cortxt_list_wiki_pages", "cortxt_read_wiki_page", "cortxt_write_wiki_page",
    "cortxt_list_sessions", "cortxt_get_session_tree",
    "cortxt_list_prs", "cortxt_get_pr",
    "cortxt_list_linear_issues",
    "cortxt_list_workflow_runs", "cortxt_get_workflow_run",
    "cortxt_capture_idea",
    "cortxt_start_session", "cortxt_save_session", "cortxt_mark_session_done"
  ],
  "eval_criteria": [
    "Verifierar varje centralt påstående mot minst 2 oberoende källor",
    "Skriver findings till wiki-sida med källreferenser innan sessionen avslutas",
    "Frågar om scope när uppdraget är otydligt — startar inte sökning i blindo"
  ],
  "read_only": false
}
```

**Känd resurs:** Claw Code — https://github.com/ultraworkers/claw-code
Alternativ agent-host för Railway (Plan B). Utvärdera mot Claude Agent SDK innan O3-arkitektur låses.
