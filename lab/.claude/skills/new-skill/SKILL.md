---
name: new-skill
description: "Skapar en ny skill — som en källnot i vaultens `Studio/Skills/`, aldrig som en handskriven fil i `.claude/skills/`. Använd vid \"gör en skill av det här\", \"det där gör vi varje gång\", \"koda in det beteendet\" — alltså när ett återkommande arbetsmoment ska få en form. Använd den INTE för något som är deterministiskt och verifierbart; det hör i kod."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/new-skill.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# new-skill

## Vad den gör

Skapar en ny skill — som en källnot i vaultens `Studio/Skills/`, aldrig som en handskriven fil i `.claude/skills/`.

## När den ska köras

Använd vid "gör en skill av det här", "det där gör vi varje gång", "koda in det beteendet" — alltså när ett återkommande arbetsmoment ska få en form. Använd den INTE för något som är deterministiskt och verifierbart; det hör i kod.

## Grinden — förtjänar det att bli en skill?

Fråga i den här ordningen, och stanna vid första ja:

| Fråga | Ja → |
|---|---|
| Är utfallet **deterministiskt och verifierbart**? | **Kod.** Ett buntat skript som skillen kör. Skriptets kod hamnar aldrig i kontexten, bara dess output — billigare och pålitligare än att låta modellen skriva om den varje gång. |
| Har **reglerna stelnat** helt? | Då är det ingen skill utan en **regel**. Skriv den i [[Rules|Studio/Rules]]. |
| Är kedjan **lång och behöver eget arbetsminne**? | **Subagent**, inte skill. |
| Är det **omdöme som återkommer**? | **Skill.** Fortsätt nedan. |

## Steg

1. **Skriv källnoten** — `Studio/Skills/<slug>.md`, från mallen [[Skill]]. Har skillen
   buntade filer blir den en mapp-not istället: `Studio/Skills/<slug>/<slug>.md` med `references/`
   och `scripts/` bredvid. Buntarna följer med ut i exporten.
2. **Fyll `## Vad den gör` och `## När den ska köras`.** Båda krävs, och det är inte formalia: de
   blir skillens `description`, och **descriptionen ÄR triggern**. Bara namn och beskrivning
   förladdas — en skill som bara säger *vad* den gör aktiveras aldrig. Åtta av tolv skills i den här
   vaulten led av precis det.
3. **Sätt `target:`** — `cns` (skillen arbetar i Project-CNS) eller `vault` (skillen arbetar på
   vault-noter, som grindskillsen).
4. **Skriv spärrarna.** Vad ska skillen VÄGRA göra? En skill utan spärr är en rekommendation.
5. **Exportera:** `python lab/cns_lab.py skill-export`.

## Spärrar

- **Vägrar skriva i `.claude/skills/`.** Det är en härledd artefakt. Redigerar du den glider den
  från källan, och då har du två sanningar som tyst säger olika saker — samma fel som ruttnade
  agentur-lagret. `skill-export --check` faller på det.
- Vägrar skapa en skill utan `## När den ska köras`. En otriggbar skill är en fil ingen kommer att
  köra.
- Vägrar göra en skill av något deterministiskt. Det hör i kod, och kod får inte ha en dålig dag.
