---
slug: cns-mcp
spec_started: '2026-06-09'
spec_updated: '2026-06-09'
status: draft
---

# Spec: `cortxt_route_session` — flytta en sessions delar in i rätt mål

## Problem
Ett AI-arbetspass (`session_store`-session) producerar lösa delar — fångade
idéer, `/btw`-asides, beslut. När passet landar vill man **dirigera** de
delarna till rätt hemvist: en quest, en issue, en idé eller en nod. I dag finns
ingen sådan operation; delarna blir kvar löst kopplade (eller helt okopplade).

## Vad finns redan (bygg på, bygg inte om)
- `scripts/session_store.py` — passet som objekt (`session-xxxx`), **en** länk
  `(kind, ref)`, `kind ∈ {quest, issue, idea, node}`, plus `transcript_id`
  (pekar på Claude Code-`.jsonl`).
- `scripts/btw_log.py` — asides grupperade per **Claude Code-session-id**
  (`exports/btw/<session-id>.json`), redan mjukt länkbara via
  `link_session(session_id, quest_id, idea_id)`.
- `scripts/idea_inbox.py` — idéer med `slug` (nodlänk) och status open/promoted.
  **Saknar sessionsfält.**
- `scripts/quest_manager.py` — `create_quest(slug, …)`.
- MCP-mönster (`app/mcp_server.py`): `scripts/`-lagret är rent, **pushen ligger
  i wrappern** (`push_file_immediately` / `_push_session`).

## Blockerare (måste lösas först)
**En sessions "delar" går inte att räkna upp fullständigt än.**
- `/btw`-asides ÄR nåbara: `session_store.transcript_id` → `btw_log.get_session(transcript_id)`.
- **Fångade idéer är INTE nåbara** — `idea` saknar `session_id`. Detta är exakt
  prerekvisiten i idea-337b37ff. Utan den kan verktyget bara flytta btw-delar
  + själva sessionslänken, inte de idéer passet fött.

Minimal additiv åtgärd (följer "additiv migrering"): lägg valfritt
`session_id` på idén i `idea_inbox.capture_idea` (default `None`), och
`list_ideas(session_id=…)`. Inget gammalt bryts.

## Föreslaget verktyg (efter att blockeraren lösts)
Två operationer, delade för att kunna inspektera före commit ("spec först"):

```
cortxt_list_session_parts(session_id) -> {session, ideas[], asides[], current_link}
    # läser; visar vad som skulle flyttas

cortxt_route_session(
    session_id: str,
    target_kind: "quest" | "issue" | "idea" | "node",
    target_ref: str,                  # måste peka på ett BEFINTLIGT mål (beslut 3)
    parts: list[str] | None = None,   # part-id:n; None = alla
) -> {session, routed: [...], skipped: [...]}
```

Beteende:
- Sätter sessionens `link` till `(target_kind, target_ref)`.
- För varje idé-del: länkar idén till målet (sätt `slug` vid nod-mål; spegla
  promote-mönstret om målet är en quest).
- För varje btw-aside: `btw_log.link_session(transcript_id, quest_id/idea_id)`.
- Push i wrappern per ändrad fil; `scripts/`-lagret förblir rent.
- Bor i `app/tools/` som domänmodul (per CLAUDE.md: nya verktyg skalar där,
  inte som fler dekoratörer i `mcp_server.py`).

## Beslut (avgjorda 2026-06-09)
1. **Flytt vs kopia → behåll + statusflagga.** Route konsumerar inte delen:
   idén får status `routed` och länken behålls för spårbarhet, precis som
   promote behåller källan.
2. **"Del" → idéer + btw-asides (MVP).** Beslut/anteckningar utan eget datalager
   ingår inte än.
3. **Quest-mål utan nod → peka på befintlig.** Route *skapar* inte quests;
   skapande sker via promote. (Slipper nod-slug-kravet i route.)
4. **Delvis dirigering → ett mål per anrop.** Urval styrs med `parts`-filtret;
   olika delar till olika mål görs med flera anrop.

## Inte nu
- Auto-klassning (gissa rätt mål åt användaren).
- Semantisk matchning av delar mot befintliga noder.
- Ångra/återställ av en dirigering.
