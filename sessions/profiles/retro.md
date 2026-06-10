---
type: retro
title: Retrospektiv
mode: granskning
agents: [hr-chef, ekonomichef, kompetensutvecklare, operativ-chef]
---

# Retro-session

Syfte: granska hur **agenturen själv** presterade — inte produkten. Den agila retron:
vad fungerade, vad kostade för mycket, vilka agenter behöver tränas eller omstruktureras.

Skiljer sig från `review` (som granskar produktkod/PR) — retro granskar arbetssättet.

## Agentbeteende

- **Kalla @ekonomichef** för förbrukningsanalys: läs `exports/ekonom_stats.json`, identifiera
  dyraste agenter, onödig parallellism, hängande sessioner senaste perioden.
- **Kalla @hr-chef** för bemanningsanalys: vilka agenter användes mest/minst, saknas en roll,
  är någon agent överlastad eller överflödig.
- **Kalla @kompetensutvecklare** för kvalitetsanalys: vilka agenter presterade svagt, vilka
  prompter behöver finslipas (lämnar patch-förslag, implementerar inte här).
- **Read-first:** retron muterar inte kod. Den producerar slutsatser och åtgärdsförslag.
- Konkreta åtgärder fångas som idéer (`cortxt_capture_idea`) eller issues — inte löst prat.

## Underlag att läsa

- `exports/ekonom_stats.json` — kumulativ per-agent-förbrukning
- `cortxt_list_sessions` — passvolym, hängande/stale, parallellitetsmönster
- `cortxt_get_session_tree` — kedjor som bröts eller aldrig flushades

## Output-format

```
[RETRO] Period: <vad som granskas>

GICK BRA: <2–3 punkter>
KOSTADE: <ekonomichefens observation — dyraste agenter/mönster>
BEMANNING: <hr-chefens observation — luckor/överlast>
KVALITET: <kompetensutvecklarens observation — svaga prompter>

ÅTGÄRDER: <konkreta nästa steg, fångade som idéer/issues>
```

## Avslut

- Åtgärdsförslagen är fångade som idéer/issues (inte bara i chatten).
- `cortxt_mark_session_done` med de viktigaste slutsatserna.
