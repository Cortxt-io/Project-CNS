# Spec: Orienteringsytan (cockpit / hemvy)

> Status: **utkast för granskning** (spec-pass 2026-06-11, session-90ce28af). Spec-först — ingen kod
> förrän öppna frågor 1–4 är besvarade. Ägs av produktchef + lösningsarkitekt.
> Ur `idea-7548a67a`. Initiativ-kandidat: ny epic under **Agentur** (ev. omramning av #8 Sessions-UX).

## Problem (varför)

CNS **lagrar** allt men **sammanställer** ingenting. Svaren på "vad gör jag härnäst", "var var jag",
"vad spelar roll" och "vad är i fokus" ligger i fyra skilda lager:

| Fråga | Lager idag |
|-------|-----------|
| Vad härnäst? | `scripts/recommend.py` (`recommend()` / `statusline()`) |
| Var var jag? | `scripts/session_store.py` (`list_sessions`, transkript via `sources.list_transcripts`) |
| Vad spelar roll? | `scripts/issues_client.py` (quests/issues) |
| Vad är i fokus? | `exports/active_session.json` (`{type, session_id}` — saknar nod/quest) |

Varje gång Rikard sätter sig är **han** integratorn som laddar fyra lager in i huvudet. Den
hopsättningskostnaden *är* desorienteringen ("tappar tråden"). Ironin: CNS löste utspridd kontext för
**maskinen** (node.md) men återskapade den för **användaren**. Backloggens kluster C (issues #39–43)
är upprepade onamngivna försök att bygga just denna yta.

## Mål

**En läsning, ingen hopsättning.** En yta som vid öppning komponerar lägesbilden åt Rikard. Princip:
**komposition av befintliga lager, inte ombyggnad.** Ingen ny datakälla, inget nytt datalager.

## Vad finns redan (återanvänds — inget nybygge)

- `scripts/tui/app.py` → **`OverviewScreen`** (tangent `o`) komponerar redan git-spår + senaste
  sessioner + öppna idéer via `_overview_markup()`. **Detta är prototypen att bygga ut.**
- `scripts/recommend.py` → `recommend(state)` ger rangordnade rek; `gather_state()` läser idéer +
  quests (TTL-cache) + running sessions; `statusline()` finns redan.
- `scripts/session_store.py` → `list_sessions(status="running")`, `get_active()`.
- `scripts/tui/sources.py` → `list_transcripts`, `load_ideas`, `open_issues_for_slug` (grindad, tyst degradering).
- `scripts/tui/data.py` → rena, testbara datafunktioner (mönstret att följa: ingen textual-import i datalagret).

## Föreslagen v1 (fyra block)

En **landnings-/hemvy** som visar:

1. **Var du slutade** — senaste `session_store`-posten (`done`), dess länk (nod/quest/issue) och summary-rad.
2. **Igång** — `list_sessions(status="running")` + aktiv sessionstyp (`get_active()`), med ikon/färg per typ (jfr #41).
3. **Härnäst** — `recommend()` topp-3, samma motor som statusraden.
4. **I fokus** — fokusmarkören (nod/quest) + dess öppna issues (`open_issues_for_slug`).

Allt annat (kunskap, agent-host, full nodträd) når man som idag via tangentbindningarna.

## Öppna frågor (MÅSTE besvaras före kod)

1. **Hemvist/trigger.** Bygga ut `OverviewScreen` (modal, tangent `o`) → eller göra ytan till TUI:ts
   **landningsvy** (det första `cns tui` visar, före nodträdet)? Brainstorm pekar på "vid öppning".
   → *Rek: landningsvy som default-skärm; nodträdet en tangent bort.*
2. **Datakälla (kärnspänningen, jfr issue #39).** Läsa **live** (`issues_client`/GitHub-sanning, kan
   hänga / kräver token) eller **lokalt** (snabbt, men `exports/` driver isär från GitHub)? 
   → *Rek: hybrid — lokalt för snabb render + `recommend.py`:s TTL-cache för quests, tyst degradering,
   och en synlig **färskhetsmarkör** ("lokal · 3 min") så drift aldrig är osynlig. Löser #39 i samma drag.*
3. **Fokusmarkör.** Utöka `active_session.json` från `{type, session_id}` till att även bära
   `{focus_kind, focus_ref}` (nod/quest/issue man jobbar på) — eller härleda fokus ur senaste
   sessionens länk? → *Rek: explicit markör (utöka filen); härledning gissar fel när flera spår löper.*
4. **Omfång v1.** Räcker de fyra blocken, eller ska något in/ut? (Avgränsa bort: kommando-statistik,
   transkript-resume, kunskapslager — de finns redan på egna tangenter.)

## Avgränsningar

- Ingen ny backend, ingen ny MCP-server. Ren TUI-komposition i `scripts/tui/`.
- Rör inte `cns.py` eller nodmodellen (samma isolationsregel som resten av `scripts/tui/`).
- Bygger inte agent-host eller multiplex — det är `idea-0e52a505`s separata, svårare spår.

## Verifiering (när byggd)

- `cns tui` öppnar direkt i hemvyn; fyra block fyllda från live-datat.
- Med GitHub onåbart: ytan renderar ändå (lokalt) med färskhetsmarkör — ingen hängning.
- Fokusmarkören uppdateras när man sätter aktivt spår; "I fokus"-blocket speglar den.
- Datafunktionerna testbara fristående (ingen textual-import), enligt `data.py`-mönstret.
