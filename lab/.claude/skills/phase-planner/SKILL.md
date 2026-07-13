---
name: phase-planner
description: "Planera en ventures faser och grindar — avvikelser från receptet, kill-kriterier, north star. Använd vid \"planera faser för X\", \"nytt venture\", \"receptet passar inte här\". Omdöme, inte beräkning. Receptet (`roadmaps/_recipe.yaml`) ger **default**-vägen: åtta faser, nitton steg, åtta grindar, samma för alla ventures. Den här skillen behövs bara när något **avviker** — och för det som receptet omöjligt kan veta: vad som får det här specifika bygget att dö."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/phase-planner.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# phase-planner

## Vad den gör

Planera en ventures faser och grindar — avvikelser från receptet, kill-kriterier, north star.

## När den ska köras

Använd vid "planera faser för X", "nytt venture", "receptet passar inte här". Omdöme, inte beräkning.

Receptet (`roadmaps/_recipe.yaml`) ger **default**-vägen: åtta faser, nitton steg, åtta grindar,
samma för alla ventures. Den här skillen behövs bara när något **avviker** — och för det som
receptet omöjligt kan veta: vad som får det här specifika bygget att dö.

> **Skiktregeln (gäller hela CNS, inte bara den här skillen):**
> **Beräkningsbart → kod. Återanvändbar process → skill. Lång, isolerad analys → subagent.**
>
> - **Kod** avgör *fakta*. Fasen (`phase_derive.py`), stegens status (`signals.py`) och
>   checklistorna (`venture_checklist.py`) är kod — deterministisk, testad, gissar aldrig.
>   Att göra om dem till skills vore en nedgradering: de får inte ha en dålig dag.
> - **Skill** väljer *vad som ska göras*. Vilka faser som gäller, vad grinden ska kräva,
>   när vi lägger ner. Det är detta dokument.
> - **Subagent** när kedjan är lång och behöver *eget arbetsminne*. Grindgranskarna nedan
>   läser hundratals filer — det ska inte in i huvudchatten.

## Innan du börjar

Läs det som redan är mätt. Planera aldrig mot en gissning:

```bash
python lab/cns_lab.py venture status <slug>     # härledd fas + steg + överhoppade grindar
```

Fasen är **bevis** (finns repo? deploy? tester?). Överhoppade grindar är **skulden** — grindar
bygget passerade utan att stänga. Tre av vertikalerna ligger live med fyra överhoppade grindar
var. Det är inte ett fel i mätningen; det är diagnosen "vibe-kodad", utskriven.

## Steg 1 — Avviker den här venturen från receptet?

Default är NEJ. Receptet är den gemensamma vägen, och en avvikelse ska vara ett **beslut**, inte
slentrian. Fråga:

- **Saknas ett steg?** T.ex. en ren datapipeline utan UI har inget `design-system`-steg.
- **Behövs ett extra steg?** T.ex. juridisk spärr (Booli-fallet), datalicens, GDPR-grind.
- **Är ett manuellt steg mätbart här?** Kan det mätas → gör det till `derived:` och slipp kryssa.

Avvikelser skrivs i `roadmaps/<slug>.md` under fasen — **inte** i receptet. Receptet ändras bara
när avvikelsen visar sig gälla alla.

## Steg 2 — Formulera grindarnas villkor

En grind vars villkor du inte kan formulera är ingen grind. Det är en förhoppning.

Varje grind ärver `requires: [...]` från receptet. Din uppgift är att avgöra om det räcker
**för just den här venturen**. Grindens fråga (`question:`) ska gå att svara ja eller nej på —
inte "är vi redo?" utan "kan vi visa X?".

Grindbeslutet är alltid ett av fyra (Stage-Gate): **go · kill · hold · recycle**.
`hold` betyder pausa, `recycle` betyder tillbaka ett steg. Att aldrig välja `kill` är hela
patologin receptet försöker bota.

## Steg 3 — Kill-kriterier (det svåraste, och det enda som faktiskt dödar något)

Skriv dem **innan** du är känslomässigt investerad. Ett kill-kriterium ska vara:

- **Mätbart** — "ingen betalande användare efter 3 månader", inte "om det känns dött"
- **Daterat** — utan datum kan det aldrig utlösas
- **Skrivet i vault-noten** (`kill_criteria:`) — det är omdöme, alltså handlagret

Reconcile mäter deras ålder. En kill-kriterium som aldrig granskats är ett du inte menade.

## Steg 4 — North star

En mening. Vad betyder "det funkar"? Om du inte kan skriva den är venturen inte redo att lämna
discovery — och det är i sig ett grindbeslut.

## Steg 5 — Skriv ner det

`roadmaps/<slug>.md`: epics per fas + `open_decisions` (det maskinen inte kan veta).
Vault-noten (`Verticals/<slug>/<slug>.md`): `north_star`, `kill_criteria`, `gate_decision`,
`next_action` — omdömet.

**Skriv aldrig `current_phase` eller fas-`status`.** De härleds. Ett fält ingen har anledning att
uppdatera blir alltid osant — det var fel i varenda vertikal innan de togs bort.

Kör sen:

```bash
python lab/cns_lab.py venture checklist <slug>   # faser → milestones + issues
```

De härledda stegen stänger sina egna issues när verkligheten hinner ikapp. Du bockar bara av det
som kräver ögon.

## Granskare per grind

En grind utan granskare är en fråga du ställer dig själv. Koppla in rätt lins:

| Grind | Granskare |
|---|---|
| discovery → spec | opportunity-evaluator |
| spec → mvp | plan-reviewer, `superpowers:writing-plans` |
| mvp → konsolidera | delivery-reviewer, acceptance-test-builder |
| konsolidera → live | architecture-auditor, test-suite-auditor, codebase-auditor |
| live → users | `verify`, seo-intel |
