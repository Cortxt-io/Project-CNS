---
name: cns-flush
description: Spola ner en sessions slutsats i CNS så parallella sessioner konvergerar mot samma noder (GitHub = sanning). Använd vid sessionsslut, eller när användaren säger "bokför sessionen", "spara det här i CNS", "flush", "spola ner", "avsluta sessionen", "konvergera sessionerna", eller efter en längre diskussion som landat i beslut/öppna frågor som inte får tappas mellan sessioner.
---

# /cns-flush — spola ner en session i CNS

Flera parallella Claude Code-sessioner kan inte mergas tekniskt — de är isolerade
kontexter. Lösningen är att **konvergera mot en gemensam sanning**: varje session
spolar ner sina slutsatser i CNS (noder/quests/idéer på GitHub). Då blir överlapp
synligt som vanliga diffar i stället för utspridd kontext i flera chattfönster.

Detta är skillen som gör nedspolningen. Den **muterar och pushar till GitHub**
(via `git_ops` Contents API, branch `main`) — samma datasanningsväg som idéer och
quests. Det är inte en kod-merge till main; det är en dataskrivning.

## När den ska köras
- I slutet av ett arbetspass som landat i beslut, ändringar eller öppna frågor.
- När användaren ber dig bokföra/spara sessionen.
- Proaktivt: enligt arbetsregeln sköts CNS-bokföring utan att fråga om lov — men
  **bekräfta sammanfattningen** med användaren innan du pushar (det går inte att
  ångra efter push).

## Steg

1. **Identifiera spåret.** Vilken nod eller quest rörde sessionen? Vid oklarhet:
   `cortxt_list_projects` för att hitta rätt slug, eller `cortxt_list_active_quests`
   om arbetet hör till ett quest. Fråga användaren om det fortfarande är otydligt
   (numrera alternativen).

2. **Kolla överlapp först.** Kör `/cns-sync` (eller `cortxt_list_sessions` med
   `link_ref=<nod/quest>`) för att se om en annan session redan rört samma spår.
   Finns överlapp — förena slutsatserna innan du sparar, så de inte skriver över
   varandras kontext.

3. **Sammanfatta passet.** Tre delar i `summary`:
   - **Beslut** som fattades.
   - **Vad som gjordes / ändrades.**
   - **Öppna frågor** som nästa session måste ta vid.
   Håll det tätt och högsignalerat — detta är kontexten en framtida session läser
   i stället för att läsa om hela chatten.

4. **Spara sessionen.** `cortxt_save_session`:
   - `summary` — sammanfattningen från steg 3.
   - `link_kind` — `node` eller `quest` (även `idea`/`issue` finns).
   - `link_ref` — nod-slug eller quest-id.
   - `transcript_id` — Claude Code-sessionens id, för spårbarhet bakåt till `.jsonl`.

   Långt pass? Öppna det i stället med `cortxt_start_session` vid start och avsluta
   med `cortxt_mark_session_done` — då blir `running → done` en pollbar signal som
   en parallell session kan `/loop`:a på innan den mergar sitt arbete.

5. **Fånga kvarvarande idéer.** Sidospår som inte hör till sammanfattningen men är
   värda att behålla: `cortxt_capture_idea(text=..., slug=<nod>)` — en per distinkt
   idé. Är någon redan en konkret uppgift: `cortxt_promote_idea_to_quest`
   (bekräfta med användaren först).

6. **Rapportera.** Lista kort vad som bokfördes: session-id, länkat spår, fångade
   idéer/quests.

## Push-läge (samma varning som cortxt-quests)
Pushen kräver att GitHub-credentials är satta (`CNS_GITHUB_TOKEN` + `GITHUB_REPO`,
eller OAuth-env i en remote-session). I en lokal stdio-session utan dem skrivs
sessionen till disk men pushen misslyckas. Händer det: säg till användaren att
sessionen sparades lokalt men inte nådde GitHub, och att den behöver pushas manuellt
eller att env-varen behöver sättas.

## Relaterat
- `/cns-sync` — överlappsdetektering före flush.
- `cortxt-quests` — quest-livscykeln som ett spår kan länkas till.
