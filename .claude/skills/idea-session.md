---
name: idea-session
department: Produkt
description: Starta en strukturerad idésession — Claude lyssnar, klusterar och bokför idéer i CNS. Använd när användaren vill brainstorma, dumpa tankar eller samla idéer i ett pass. Triggar på /idea-session.
---

# /idea-session — strukturerad idésession

En idésession är ett avgränsat arbetspass för fri tankedumpning. Claude lyssnar,
klusterar och bokför allt i CNS så inget tappas mellan sessioner.

## Steg

1. **Starta sessionen.**
   `cortxt_start_session(source="chat", summary="Idésession")` → spara `session_id`.
   Meddela användaren: "Idésession startad (`<session_id>`). Dumpa fritt — jag lyssnar."

2. **Lyssna-läge.**
   Inga avbrott, inga frågor. Låt användaren dumpa fritt. Bekräfta med korta ord
   ("ok", "noterat") utan att styra innehållet.

3. **Klustrera** (per 3–5 idéer, eller när användaren pausar/avslutar).
   Gruppera tematiskt, föreslå ett klusternamn. Fråga **inte** om godkännande —
   presentera klustret och gå direkt till bokföringen. Säg om du avviker från
   gruppningen.

4. **Bokför varje idé.**
   `cortxt_capture_idea(text=<idé>, session_id=<id>)` — en per distinkt idé.
   Länka till en nod om det är uppenbart (`slug=<nod>`), annars lämna tomt.

5. **Avsluta sessionen.**
   `cortxt_mark_session_done(session_id=<id>, summary=<kluster-sammanfattning>)`
   Sammanfattning = ett kluster per rad: "Kluster A: idé1, idé2. Kluster B: idé3."
   Rapportera: antal bokförda idéer, session-id, kluster.

## Regler

- **Aldrig avbryta lyssna-läget** med frågor om noder, quests eller struktur.
  Det löses i bokföringsfasen.
- Klustrera på **substans**, inte på formalia. Om en idé inte passar ett kluster
  bokförs den ensam.
- Om en idé är tillräckligt konkret för ett issue: notera det men **fråga** innan
  `cortxt_promote_idea_to_issue` — promote muterar GitHub.
- Hooken (`idea_prompt_hook.py`) injicerar öppna idéer från sessionens pass i
  varje ny prompt — Claude ska läsa dem som kontext, inte repetera dem.

## Relaterat

- `/cns-flush` — spola ner en sessions slutsatser om passet handlar om kod/beslut.
- `/cns-sync` — överlappsdetektering om parallella sessioner är igång på samma nod.
- `cortxt_fork_session` — bokför en fork om en idé växer till ett eget spår.
