---
name: bemanna
description: Aktivera en skal-roll ur org-registret till en körbar agent. Använd vid "bemanna <roll>", "aktivera <slug>", "rekrytera in X", "fyll rollen Y". Ägs av hr-chef + org-arkitekt.
department: People
---

# /bemanna — aktivera en roster-roll till körbar agent

Org-registret (`.claude/org/roster/`) håller definierade men obemannade roller. Detta flöde
bemannar en roll: fyller dess kropp och gör den körbar i `.claude/agents/`. Onboarding/rekrytering.

**Gräns:** @hr-chef validerar att individen behövs + dess verktyg/eval; @org-arkitekt att
strukturen stämmer. Den mekaniska flytten gör `scripts/bemanna.py`.

## Steg

1. **Hitta rollen.** Bekräfta att `<slug>` finns i `.claude/org/roster/<slug>.md` (annars: är
   den redan aktiv, eller behöver den läggas i `manifest.json` + scaffoldas först?).

2. **@hr-chef validerar (inventeringschecklistan):**
   - Behövs rollen aktiv NU, eller räcker den som skal? (Håll aktiva rostern ~7–10.)
   - Vilka MCP-verktyg täcker dess kärnuppgifter? Saknas något verktyg?
   - Vilket konkret testkriterie visar att den gör sitt jobb?

3. **Fyll skelettets kropp** med Edit — ersätt TODO-sektionerna i roster-filen INNAN aktivering:
   - `## Roll` — kärnuppgift (1 mening) + 3–5 konkreta uppgifter
   - `## Tillåtna verktyg` — de MCP-verktyg hr-chef identifierade
   - `## Eval-kriterier` — testkriteriet, mätbart
   - Lägg ev. `## Session-protokoll` (start/done) som övriga agenter har

4. **Kör motorn:** `python scripts/bemanna.py <slug>`
   - Flyttar filen roster→agents, sätter `status: active`, flippar manifest-flaggan, regenererar
     registret (`agent_registry.py` + `AGENTUR.md`)

5. **Routing (om rollen ska nås automatiskt):** lägg en `ROUTING_RULE` i `scripts/router.py`
   med ett domän-regex → `<slug>`. (Kan inte autogenereras — kräver omdöme om rollens triggers.)

6. **Verifiera:** `python scripts/validate_org.py` = 0 error (active-flagga matchar filplats);
   `echo '{}' | python scripts/router.py` exit 0.

7. **Commit + push.** Uppdatera ev. CLAUDE.md routing-tabell om en routad agent tillkom.

## Viktigt
- Fyll kroppen FÖRE `bemanna.py` — motorn varnar om TODO/Skal-markörer kvarstår.
- Nya agenter blir anropbara som `subagent_type` först efter att Claude Code laddat om.
- Inversen (aktiv → roster, för att hålla rostern liten) finns inte än — håll därför aktiva
  rostern medvetet liten; bemanna bara det som faktiskt ska köras.
