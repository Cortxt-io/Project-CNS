---
name: org-maintenance
description: Håll org-strukturen och bemanningsunderlaget aktuellt när agenturen växer — bemanningsmatris, bemanna-pelarna, validate_agent-kriterier. Använd vid "org-underhåll", "uppdatera bemanningsmatrisen", "bemanningsbehov", "ny avdelning behöver mall", eller som stående punkt i retro. Ägs av org-arkitekt.
department: People
---

# /org-maintenance — håll bemanningsunderlaget aktuellt

När agenturen växer (nya departments fylls, nya nivåer, roller aktiveras) driver
bemanningsunderlaget isär om ingen äger det. Detta flöde håller det synkat. **Org-arkitekten**
äger det. Governance ska sitta *utanför* agenternas exekveringsloop — det här ÄR det control plane:t.

> Princip (validerad mot extern praxis): **kontinuerliga kontroller > periodisk granskning**.
> Grindarna (`validate_org`, `validate_agent`) körs vid varje bemanning/gen; detta flöde fångar
> det grindarna flaggar + det som kräver omdöme.

## Triggers
1. **Vid behov:** när nya departments/roller läggs i manifest eller aktiveras via `/staff-role`.
2. **I retro:** stående punkt i retro-passet (granska att underlaget hänger med).

## Steg

1. **Kör täckningsgrinden:** `python scripts/validate_org.py`
   - WARN `Bemanningsmatris saknar cell '<dept>|<nivå>'` → en ny (nivå × department)-kombination
     finns utan mall. Lägg cellen i `.claude/org/bemanning_matris.json` (model, tool_families,
     guardrails, eval_focus, prompt_focus) — seat-baserat, inte personbaserat.
   - WARN `förlegad cell` → en cell utan motsvarande roll. Ta bort den.

2. **Granska bemanna-pelarna** (`.claude/skills/staff-role/SKILL.md`): stämmer de fyra pelarna och
   Gate 0 mot hur agenturen ser ut nu? Nya verktygsfamiljer, nya guardrail-behov?

3. **Granska `validate_agent.py`-kriterierna:** är de obligatoriska sektionerna + trösklarna
   fortfarande rätt? (T.ex. ny obligatorisk sektion, justerad verktygsbredd-gräns.)

4. **Fasa in en avdelning i taget** — blås inte upp matrisen till teoretiska celler; håll den till
   de kombinationer som faktiskt finns. Dokumentera vad du ändrade.

5. **Verifiera + commit:** `validate_org.py` = 0 täckningsluckor; commit ändringarna.

## Gräns
- Du formar underlaget (matris/pelare/kriterier); @people-lead bemannar enskilda roller via `/staff-role`.
- Rör inte genererade filer (`AGENTUR.md`, `agent_registry.py`) — de regenereras.

## Eval-kriterier
- Efter körning: `validate_org.py` rapporterar 0 matris-täckningsluckor
- Matrisen speglar bara verkliga (dept × nivå)-kombinationer — inga teoretiska/förlegade celler
- Ändringar är seat-baserade (roll/nivå), inte bundna till en specifik bemanning
