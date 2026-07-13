---
name: idea-session
description: "Starta en strukturerad idésession — Claude lyssnar, klusterar och skriver ner varje idé som en rånot i vaultens inkorg. Använd när användaren vill brainstorma, dumpa tankar eller samla idéer i ett pass. Triggar på /idea-session. En idésession är ett avgränsat arbetspass för fri tankedumpning. Passet **slutar när idéerna är fångade** — bedömningen (behåll/promota/radera) ägs av `idea-triage`, inte av den här skillen."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/idea-session.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# idea-session

## Vad den gör

Starta en strukturerad idésession — Claude lyssnar, klusterar och skriver ner varje idé som en
rånot i vaultens inkorg.

## När den ska köras

Använd när användaren vill brainstorma, dumpa tankar eller samla idéer i ett pass. Triggar på /idea-session.

En idésession är ett avgränsat arbetspass för fri tankedumpning. Passet **slutar när idéerna är
fångade** — bedömningen (behåll/promota/radera) ägs av `idea-triage`, inte av den här skillen.

## Var idéerna hamnar

Inkorgen är vaultens `Ideaverse/CNS/Products/Raw/` — **en rånot per idé**. Se [[Inkorgsregeln]]:
en rånot är material, inte prosa, den bär ingen `prose:`-art, och den ska ut ur inkorgen igen.
Därför får fångst vara billig och slarvig. (Kodens `exports/ideas/`-inkorg är ersatt av regeln —
skriv inte dit.)

## Steg

1. **Starta sessionen.**
   `cortxt_session(action="start", source="chat", summary="Idésession")` → spara `session_id`.
   Meddela användaren: "Idésession startad (`<session_id>`). Dumpa fritt — jag lyssnar."

2. **Lyssna-läge.**
   Inga avbrott, inga frågor. Låt användaren dumpa fritt. Bekräfta med korta ord
   ("ok", "noterat") utan att styra innehållet.

3. **Klustrera** (per 3–5 idéer, eller när användaren pausar/avslutar).
   Gruppera tematiskt, föreslå ett klusternamn. Fråga **inte** om godkännande —
   presentera klustret och gå direkt till nedskrivningen. Säg om du avviker från
   gruppningen.

4. **Skriv en rånot per distinkt idé** i `Ideaverse/CNS/Products/Raw/<kort-titel>.md`:

   ```markdown
   ---
   type: raw
   status: untriaged
   created: <YYYY-MM-DD>
   source: idea-session/<session_id>
   tags: [raw]
   ---

   # <Kort titel>

   <Idén i användarens egna ord — inte tvättad, inte bedömd.>
   ```

   Ingen `prose:`-art: noten påstår ingenting ännu. Nämn klustret i brödtexten om det bär mening.

5. **Avsluta sessionen.**
   `cortxt_session(action="done", session_id=<id>, summary=<kluster-sammanfattning>)`
   Sammanfattning = ett kluster per rad: "Kluster A: idé1, idé2. Kluster B: idé3."
   Rapportera: antal skrivna rånoter, session-id, kluster.

## Regler

- **Aldrig avbryta lyssna-läget** med frågor om noder, epics eller struktur.
  Det löses när idéerna skrivs ner.
- Klustrera på **substans**, inte på formalia. Om en idé inte passar ett kluster
  skrivs den ensam.
- **Döm inte mitt i dumpen.** Verkar en idé mogen för ett issue: notera det i rånoten och lämna
  det till triagen. Den här skillen promotar ingenting.

## Relaterat

- `idea-triage` — nästa pass: bedömer rånoterna, ger dem art eller raderar dem.
- `/cns-flush` — spola ner en sessions slutsatser om passet handlar om kod/beslut.
- `cortxt_session(action="fork")` — bokför en fork om en idé växer till ett eget spår.
