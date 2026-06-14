# Spec: Control Tower (agenturens orienteringsyta)

> Status: **granskad / låst för v1** (definition-pass 2026-06-14, session-b675c154, epic #8).
> Ersätter `orienteringsyta-spec.md`. Tidigare utkast 2026-06-11 (session-90ce28af).
> Ur `idea-7548a67a` + `idea-a7b4b7e5` (subjektsskifte) + `idea-5132a8f6` (dra-loop).
> Kanoniskt engelskt namn: **Control Tower** (ersätter sv. "kontrolltorn/orienteringsyta").
> Ägs av produktchef + lösningsarkitekt.

## Problem (varför)

CNS **lagrar** allt men **sammanställer** ingenting. Svaren på "vad gör jag härnäst", "var var jag",
"vad spelar roll" och "vad är i fokus" ligger i fyra skilda lager (recommend / sessions / issues /
aktiv-markör). Varje gång Rikard sätter sig är **han** integratorn som laddar lagren in i huvudet.
Den hopsättningskostnaden *är* desorienteringen ("tappar tråden", "blir yr av taxonomin"). Control
Tower komponerar lägesbilden åt honom i stället.

## Mål

**En läsning, ingen hopsättning** — och **systemet drar dig vidare** (dra-loop, se nedan).
Princip: **komposition av befintliga lager, inte ombyggnad.** Ingen ny datakälla, inget nytt datalager.

## Beslut (var öppna frågor i utkastet — nu avgjorda)

1. **Hemvist/trigger → landningsvy.** Control Tower blir TUI:ts **default-skärm** vid `cns tui`;
   nodträdet en tangent bort. Bygger ut `OverviewScreen` (`scripts/tui/app.py`).
   **Status: ENDA genuint öppna byggdeltat** — ytan finns men är i dag en *modal* (tangent `o`).
2. **Datakälla → hybrid.** Lokalt för snabb render + `recommend.py` TTL-cache (300 s) för quests,
   tyst degradering, **synlig färskhetsmarkör**. **Status: REDAN BYGGT** — `_freshness_label()` +
   `cockpit_state()['freshness']` i `scripts/tui/`; `recommend._cached_quests()` har TTL-cachen.
3. **Fokusmarkör → explicit.** `exports/active_session.json` bär `focus_kind`/`focus_ref`.
   **Status: REDAN BYGGT** — `session_store.set_focus/get_focus` finns; `cockpit_state()['focus']`
   renderar nod/quest + öppna issues. (Lucka: `set-focus` är inte inkopplad i `cns session`-CLI:t,
   bara nåbar via `python -m scripts.session_store` — se redundans/luckor nedan.)
4. **Omfång v1 → fyra block.** Var du slutade · Igång · Härnäst · I fokus. Avgränsa bort
   kommando-statistik, transkript-resume, kunskapslager (egna tangenter). **Status: REDAN BYGGT** —
   alla fyra block finns i `_overview_markup()`.

**Konsekvens:** v1 är till ~70 % redan implementerad. Definition-passet flyttade epicen från
"5 färska stories" till "ett litet byggdelta + en städning". Se byggordning och redundans nedan.

## Dra-lager (idea-5132a8f6) — det som gör ytan aktiv, inte bara läsbar

Control Tower visar inte bara *var du står* på de två axlarna (objekt + sessionsfas, se
`CLAUDE.md` → "Två axlar") utan **drar dig vidare**: nästa handling ska vara ETT tangenttryck —
starta den rekommenderade sessionen/fasen direkt från "Härnäst"-blocket. Detta är epicens redan
namngivna "NUDGE-lager = skillnaden statustavla vs kontrolltorn".
- Motorn finns: `recommend.recommend()` ger fas-medvetna, poängsatta rekommendationer
  (triage/definition/delivery/review/discovery).
- Deltat: göra raderna **handlingsbara** (tangent → `cortxt_session start` + `set-active` för den
  föreslagna typen), inte bara visa dem. Realiseras tvärs **#39** (handlingsbar) och **#43** (ytan).
- Föddes ur Rikards ord 2026-06-13: *"jag vill bli dragen."*

## Byggordning för epic #8 (#39–43)

- **#39** Handlingsbar statusrad + triage — **foundation**. Dataspine finns (`statusline()` komponerar
  redan typ/fokus/pass/hälsa/Rek); deltat = handlingsbarhet + triage-flöde.
- **#43** Control Tower som landningsvy — **depends_on #39**. Promota `OverviewScreen` modal →
  default-skärm + gör "Härnäst" handlingsbar (dra-loop).
- **#41** Färg/namn per sessionstyp — parallellt. **Delvis byggt** (`SESSION_COLORS`/`SESSION_ICONS`
  finns); kvar = auto-namn + flik-titel + TUI-listans färg.
- **#40** Modellval per session — ortogonal, följer efter (sessionsprofil-spår).
- **#42** Granska rekommendationer på sak — ortogonal kvalitets-skill, oberoende.

v1 = **#39 → #43 (+ #41-resten)**. #40/#42 är uppföljning.

## Konsolidering / redundans (vad blir gammalt eller redan finns)

Subjektsskiftet + att mycket redan är byggt gör att passet **stänger luckor och kollapsar dubbletter**
snarare än bygger nytt:
- **`recommend.py:statusline()` vs Control Tower** — komplementära, inte redundanta: statusraden är
  den *komprimerade* (enrads) ytan i Claude Code; `_overview_markup` den *fulla* i TUI:t. Båda läser
  samma `recommend()`/`health`/`cockpit_state`. Behåll båda; en datakälla, två renderingar.
- **Fokus dubbelspårad — KONSOLIDERA.** Två fokusnotioner finns: (a) `recommend._focus_label()` som
  *härleder* fokus ur aktiv sessions `link` ("ingen separat markör behövs"), och (b) den *explicita*
  `session_store.set_focus` + `cockpit_state['focus']`. Beslut #3 väljer den explicita. Åtgärd: låt
  `_focus_label` falla tillbaka på `get_focus()` när explicit fokus finns, annars härleda — en sanning.
- **`OverviewScreen` (modal) blir landningsvyn** — inte ny kod, samma `_overview_markup()` byter
  hemvist (modal → default-skärm). Modal-tangenten `o` kan behållas som genväg tillbaka.
- **CLI-lucka:** `set-focus`/`get-focus`/`clear-focus` finns i `session_store.__main__` men är inte
  exponerade i `cns session`-subkommandona (bara set/get/clear-active). Koppla in dem (#43 eller #39).
- **Två-axel-ASCII:n i `CLAUDE.md`** — statisk doc, kompletterar den levande ytan; ej redundant.

## Avgränsningar

- Ingen ny backend, ingen ny MCP-server. Ren TUI-komposition i `scripts/tui/` + statusrad i
  `recommend.py`. Rör inte `cns.py`-kärnan eller nodmodellen (isolationsregeln för `scripts/tui/`).
- Bygger inte agent-host/multiplex — `idea-0e52a505`s separata spår.

## Verifiering (när v1 byggd)

- `cns tui` öppnar **direkt** i Control Tower (landningsvyn), inte nodträdet; fyra block fyllda.
- "Härnäst" är handlingsbar: ett tangenttryck startar den rekommenderade sessionen (dra-loop).
- Med GitHub onåbart: ytan renderar lokalt med färskhetsmarkör — ingen hängning.
- Fokus: `cns session set-focus quest 8` speglas i "I fokus"-blocket; en enda fokussanning.
- Datafunktionerna testbara fristående (ingen textual-import), enligt `data.py`-mönstret.
