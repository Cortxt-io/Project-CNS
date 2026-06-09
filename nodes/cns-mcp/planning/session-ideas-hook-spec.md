---
slug: cns-mcp
spec_started: '2026-06-09'
spec_updated: '2026-06-09'
status: draft
---

# Spec: väck sessionens öppna idéer vid nästa prompt (idea-337b37ff)

## Problem
Idéer som föds mitt i ett arbetspass (`capture_idea`, `/btw`) försvinner ur
sikte så fort fokus byter. Användaren måste själv minnas att en tidigare tanke
kanske går att lösa nu. Vi vill att passets **öppna** idéer automatiskt dyker
upp igen när de blir relevanta — utan att användaren ber om det.

## Vad finns redan (bygg på, bygg inte om)
- **Datalagret är klart (2026-06-09):** `idea_inbox.capture_idea(..., session_id=None)`
  taggar idén med passet; `list_ideas(session_id=…)` hämtar passets idéer.
  Speglat i MCP (`cortxt_capture_idea` / `cortxt_list_ideas`). Detta var
  prerekvisiten — den är löst.
- `btw_log` grupperar redan asides per Claude Code-session-id.
- Claude Code-hooks: `UserPromptSubmit` kör *innan* prompten når modellen och
  kan **injicera kontext** i sessionen. Den får `session_id` + `transcript_path`
  på stdin.

## Föreslagen lösning
En lokal `UserPromptSubmit`-hook (skript i repo, registrerad i `settings.json`):

1. Läs `session_id` från hookens stdin-payload.
2. Hämta passets öppna idéer: `list_ideas(status="open", session_id=<id>)`.
   (Lokalt anrop mot `scripts/idea_inbox`, inte via remote-MCP — hooken kör på
   användarens maskin.)
3. Om träffar finns: injicera en kort kontextblob före prompten, t.ex.
   > "Öppna idéer från det här passet: [id + en rad var]. Kolla om någon går att
   > implementera i ljuset av användarens prompt; annars ignorera tyst."
4. Inga träffar → injicera inget (hooken är tyst).

## Blockerare / öppna frågor (besvara innan kod)
1. **Gemensam sessionsnyckel.** Hooken får Claude Code:s `session_id` på stdin.
   Men `capture_idea` tar emot `session_id` som *argument* — vem fyller det vid
   fångst? Om idén fångas via remote-MCP känner servern inte till Claude Code:s
   session. **Måste lösas:** antingen (a) en lokal fångst-väg som stämplar
   `session_id` själv, (b) hooken matar in aktuellt `session_id` i kontext så
   agenten skickar med det, eller (c) härled nyckeln ur `transcript_path`.
   Utan en stabil delad nyckel matchar inte fångst och uppväckning.
2. **Brusfilter.** Bara öppna idéer (klart). Ska vi dessutom semantiskt matcha
   idé mot prompt för att inte väcka *alla* varje gång? → MVP-förslag: väck alla
   öppna (oftast få per pass); semantisk matchning är "inte nu".
3. **Snooze.** Behövs ett sätt att tysta en idé för resten av passet så den
   slutar dyka upp? → MVP-förslag: nej; lägg till `snoozed`-status vid behov.
4. **Lokalt datalager i hook-miljön.** Hooken kör lokalt och måste nå
   `exports/ideas/`. Funkar i repo-checkout; odefinierat om idéer bara bor på
   Railway/GitHub. → Antagande: lokal checkout är källan vid hook-körning,
   annars läs via `read_file_from_github`.

## Inte nu
- Semantisk relevansrankning av idé mot prompt.
- Väcka idéer på tvärs av sessioner.
- Route-session-integration (egen spec: `route-session-spec.md`) — den
  konsumerar samma `session_id`-fält men är ett separat verktyg.
