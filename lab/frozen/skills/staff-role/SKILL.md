---
name: staff-role
description: Rigorös onboarding av en roster-roll till körbar agent — fyra pelare (systemprompt, verktyg/guardrails, eval/red-team, aktivering) med mekanisk kvalitetsgrind. Använd vid "bemanna <roll>", "aktivera <slug>", "rekrytera in X", "fyll rollen Y". Ägs av hr-chef + org-arkitekt + kompetensutvecklare.
department: People
---

# /staff-role — rigorös agent-onboarding

Org-registret (`.claude/org/roster/`) håller definierade men obemannade roller. Detta är
agenturens **rekrytering + onboarding**: att fylla en roll så väl att den blir en pålitlig,
körbar agent — inte bara flytta en fil. En halvfärdig agent gör mer skada än nytta
(rollkonfusion = 41,77 % av spec-fel; agent-bloat ökar koordinationsfel).

**Gräns:** @people-lead äger behovet + verktygen, @learning-developer promptkvaliteten,
@org-architect att strukturen stämmer. Mekaniken: `scripts/bemanna.py` (grindad av
`scripts/validate_agent.py`).

> Grundad i `archive/docs/agent-design-playbook.md` (arkiverad, men fortfarande grunden) +
> onboarding-research (systemprompt = agentens DNA; Zero Trust least-privilege;
> reliability > tillfällig framgång).

---

## Baslinje — slå upp bemanningsmatrisen FÖRST

Bemanningsbehovet skiljer sig per **nivå × department**. Slå upp rollens cell i
`.claude/org/bemanning_matris.json` innan du fyller kroppen:
- **Nivå:** exec (department Ledning) · lead (`lead: true`) · ic (övriga). Cell-nyckel `"<Department>|<nivå>"`.
- Cellen ger baslinje: `model`, `tool_families`, `guardrails`, `eval_focus`, `prompt_focus`.
- **Använd cellen som utgångspunkt i Pelare 1–3.** Avvik bara med uttalad motivering.
- Saknas cellen (ny dept/nivå)? Kör `/org-maintenance` (org-arkitekt) som lägger den först.

## Gate 0 — Behövs rollen ENS aktiv? (anti-bloat)

Innan något annat, svara ärligt:
- Finns en aktiv agent som redan täcker uppgiften? → **slå ihop/återanvänd, bemanna INTE**.
- Skulle den nya agenten aldrig prata direkt med någon annan OCH göra liknande saker som en
  befintlig? → en agent, inte två.
- Är aktiva rostern redan ~10? → bemanna bara om något annat kan vila (registret är gratis,
  aktiva agenter kostar kontext varje session). 2–5 vassa slår 20 smala.

Passerar inte Gate 0 → stoppa. Lämna rollen som skal.

---

## Pelare 1 — Systemprompt-design (@people-lead + @learning-developer)

Systemprompten är agentens **DNA** — vem den är, hur den tänker, vad den vägrar. Skriv kroppen:

- **Identitet & gränser:** "Du är X. Du äger Y. Du gör INTE Z." Skarpa gränser mot grannroller.
- **Numrerat task-flow** (viktigaste sektionen): stegen agenten följer, med villkor som
  *"verifiera X innan nästa steg"* — det stoppar skippade steg och hallucinationer.
- **Rollkonfusionsskydd:** agenten deklarerar sina avsedda åtgärder innan den exekverar.
- **Anti-mönster att undvika:** prompt som eftertanke; dumpa manualer/kunskapsbaser i prompten
  (peka på datalagret istället); övergeneralisera så den blir vag, eller överspecificera så den
  bara klarar ett smalt fall. Håll den bred nog att generalisera.
- **Output-format** om agenten rapporterar (ge en mall).

## Pelare 2 — Verktygsval + guardrails (least privilege / Zero Trust)

- **Minsta nödvändiga verktyg.** Lista bara de MCP-verktyg kärnuppgifterna kräver — motivera
  varje. En ren analys-/planerarroll kan behöva 0 muterande verktyg.
- **Read-first:** läsning/överblick är default; muterande verktyg bara där rollen verkligen skriver.
- **Destruktiv-op-skydd:** delete/overwrite/deploy/merge kräver explicit bekräftelse i prompten.
- **Minimal kontext:** rollen begär aldrig full historik — bara det uppgiften kräver.
- Bred verktygsyta (>12) = gul flagga; motivera eller dela rollen.

## Pelare 3 — Eval + red-teaming

- **Ett konkret mätbart testuppdrag** — "Analysera Q2-förbrukning och ge 3 åtgärder", inte
  "fungerar korrekt". Det är agentens acceptanstest.
- **Adversariell self-check inbyggd:** agenten ombeds hitta "3 sätt detta blir fel" innan den
  levererar (reliability > tillfällig framgång).
- **Red-team-pass innan aktivering** — testa agenten mot:
  - *Prompt-injection:* en uppgift med inbäddad "ignorera dina instruktioner".
  - *Instruction-override:* be den göra något utanför sitt mandat — den ska vägra/eskalera.
  - *Rollöverskridande:* be den göra grannrollens jobb — den ska delegera.
  Dokumentera utfallet i ett kort red-team-stycke; fixa prompten tills den håller.

## Pelare 4 — Onboarding-checklista + aktivering

1. `python scripts/validate_agent.py <slug>` → **0 error** (grinden: komplett frontmatter,
   inga skelettmarkörer, sektionerna Roll/Verktyg/Eval/Session-protokoll finns).
2. `python scripts/bemanna.py <slug>` — kör grinden igen och **blockerar vid error** (annars
   `--force`). Flyttar roster→agents, sätter `status: active`, flippar manifest, regenererar.
3. **Routing** (om agenten ska nås via [ROUTING]): lägg en `ROUTING_RULE` i `scripts/router.py`
   med ett domän-regex → `<slug>`. Uppdatera CLAUDE.md routing-tabell om den ska synas där.
4. `python scripts/validate_org.py` = 0 error; `echo '{}' | python scripts/router.py` exit 0.
5. **Commit + push.**

---

## Viktigt
- Fyll ALLA fyra pelarna i kroppen FÖRE steg 4.1 — grinden blockerar annars (det är meningen).
- Nya agenter blir anropbara som `subagent_type` först efter att Claude Code laddat om.
- Håll aktiva rostern medvetet liten — bemanna bara det som faktiskt ska köras nu.
