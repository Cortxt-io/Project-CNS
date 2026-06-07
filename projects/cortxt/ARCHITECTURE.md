# Cortxt — Arkitekturmodell (fundament)

> Skapad 2026-06-06 efter en lång byggsession. Detta dokument fångar den
> tankemodell vi landat för hur Cortxt ska struktureras. Det är ett
> BESLUTSUNDERLAG, inte färdig kod. Inget schema är ännu ändrat. Läs,
> justera, godkänn — sedan migreras schemat enligt planen längst ner.

---

## Problemet vi löser

CNS kallar allt för "projekt" och använder en **produktvalideringsmall**
(Problem, Target Audience, Assumptions to Validate, Why Buy Instead of Build,
MVP Steps, ROI mot marknad). Den mallen är byggd för att svara på frågan
"ska jag bygga den här produkten och kommer någon betala?".

Men nästan inget i Cortxt är en produkt. Det är **komponenter i ett system**
som byggs för att systemet behöver dem. Att fylla i "Target Audience: mig själv"
och "Why Buy Instead of Build" för ett internt verktyg känns fel — för det ÄR fel.
Mallen passar inte saken.

Symptom på att mallen är fel:
- "MVP klar" betyder inte "färdigt verktyg" — komponenter lanseras inte, de mognar
- Marknadsrisk är meningslöst för en intern komponent
- project.md känns som ett formulär man tvingar in saker i

---

## Modellen: två ortogonala dimensioner

Varje nod i Cortxt har TVÅ oberoende egenskaper:

### Dimension 1 — Strukturell nivå (`kind`)

```
framework   toppnoden (Cortxt självt)
system      en nod som INNEHÅLLER andra noder
komponent   en atomär nod — inga egna delar på den nivå vi bryr oss om
```

**Viktig insikt:** `kind` är inte en etikett du gissar i förväg. Den
**framgår av strukturen**. Om andra noder pekar på något som sin `part_of`,
så är det ett system. Har noden inga barn, är den en komponent. Är den toppen,
är den frameworket.

Strukturen är fraktal: samma sak kan vara en komponent sedd utifrån (en svart
låda) och ett system sett inifrån (med egna delar). Var gränsen går beror på
upplösning — hur nära du tittar.

Exempel: `ai-ticket-triage` är förmodligen ett **system** när den byggs
(mottagare + klassificerare + router + vy), men just nu en enda planerad nod
eftersom den ännu inte har delar.

### Dimension 2 — Livscykelstadium (`stage`)

```
idea        planerad, ännu inte byggd
building    under aktiv konstruktion
working     fungerar och används
maturing    fungerar, fokus på underhåll och förbättring
```

"Idé" är alltså bara ett stadium — inte en egen sorts sak. Allt är komponenter
(eller system, eller frameworket); vissa är bara inte byggda än. Det finns inga
separata "produktidéer" — det finns komponenter i `stage: idea`.

En nod som visar sig värd att bygga rör sig: `idea → building → working → maturing`.
Webhook-router gjorde exakt den resan (idé → infrastruktur-komponent) tidigare idag.

---

## Relationer — det som ritar grafen

Tre relationsfält gör att frameworket kan visualiseras automatiskt:

```yaml
part_of:     <slug>          # vilken större nod denna tillhör
feeds:       [<slug>, ...]   # vilka noder denna matar data till
depends_on:  [<slug>, ...]   # vad denna behöver för att fungera
```

`part_of` bygger hierarkin (komponent → system → framework).
`feeds` + `depends_on` bygger flödet (pipelines, beroenden).

Med dessa tre fält **ritar grafen sig själv** — det var hela poängen med
graph-vyn som parkerats. Systemet vet att `cns-devwatch` är `part_of:
pipeline-intern` som är `part_of: cortxt`, och att den `feeds: cns-devlog`.

---

## Det nya komponent-schemat

Ersätter produktmallen för noder med `kind: component | system | framework`.

### Frontmatter
```yaml
title:       <namn>
slug:        <slug>
kind:        component | system | framework
stage:       idea | building | working | maturing
part_of:     <slug eller null>
feeds:       [<slug>, ...]
depends_on:  [<slug>, ...]
layer:       pipeline | infrastructure | interface   # behalls
summary:     <en mening om vad noden gor>
url_repo:    <url eller null>
url_live:    <url eller null>
created:     <datum>
updated:     <datum>
```

### Sektioner (ersätter produktsektionerna)
```
## Syfte           vad noden gor i systemet
## Beroenden       vad den matar / matas av (prosa som komplement till feeds/depends_on)
## Status          var i bygget den ar, vad som fungerar
## Nasta steg      vad som ska goras harnast
## Risker          tekniska/operationella (probability x impact), INTE marknadsrisk
## Arbetslogg      handelser — pa sikt automatiskt matad av eventstream
## Anteckningar    fritt
```

### Vad som FÖRSVINNER från komponenter
- Target Audience (komponenten tjänar systemet)
- Why Buy Instead of Build (du bygger den per definition)
- ROI / cost_sek / value_sek mot marknad (ingen extern marknad)
- MVP Steps som lanseringsstege (ersätts av `stage`)

---

## System-schemat

Ett system koordinerar komponenter — det gör inte EN sak, det binder ihop flera.
Dess md-fil ska INTE upprepa komponenternas innehåll, utan beskriva helheten.

### Frontmatter
Samma som komponent, med `kind: system`. `part_of` pekar uppåt (oftast `cortxt`).
`feeds`/`depends_on` på systemnivå beskriver flöden mellan system.

### Sektioner
```
## Syfte/mal             vad systemet astadkommer som komponenterna inte gor var for sig
## Ingaende komponenter  GENERERAS automatiskt fran noder med part_of: <detta system>
## Dataflode             hur data ror sig mellan komponenterna (A->B->C), bygger pa feeds
## Halsa                 ar alla ingaende komponenter working? var skaver det?
## Systemrisker          risker som uppstar av samspelet, inte i enskild komponent
## Arbetslogg            handelser (eventstream)
## Anteckningar          fritt
```

Nyckeln: "Ingaende komponenter" och "Dataflode" ar VYER av relationsfalten, inte
handunderhallen text. Nar en komponent far `part_of: pipeline-intern` dyker den
upp i pipeline-interns systemfil automatiskt.

---

## Framework-schemat

Frameworket ar toppnoden (Cortxt). Dess md-fil ar vision och karta, inte bygge.
Det finns bara en framework-nod.

### Frontmatter
`kind: framework`, `part_of: null`. Inga `feeds`/`depends_on` (inget ovanfor).

### Sektioner
```
## Vision            vad Cortxt ar och varfor det finns
## Ingaende system   GENERERAS fran noder med part_of: cortxt
## Karta             oversikt av hela tradet (alla system + komponenter)
## Riktning          roadmap pa frameworkniva — vart ar det pa vag
## Principer         designprinciper (CNS-first, human-in-the-loop, GitHub som
                     source of truth, komponenter inte produkter, osv)
## Arbetslogg        handelser (eventstream)
## Anteckningar      fritt
```

---

## Varianter — medvetet INTE skapade ännu

Vi övervägde undertyper (pipeline-system vs samexisterande system, interface som
egen sort, extern-produkt-nod). Beslut: **skapa inga varianter på spekulation.**

Det var precis så produktmallen blev fel — en mall designad innan den mötte
verkligheten. Regel: en variant skapas först den dag en konkret nod skaver mot
sin grundmall, och då vet vi exakt vilket fält som fattas. Testet `pipeline-intern`
mot system-mallen ovan passade utan att skava → ingen variant behövs nu.

Möjliga framtida varianter att vara uppmärksam på:
- **Pipeline** (system där komponenter är seriellt kopplade) — om `feeds`-ordning
  och flödesvy behöver mer än vanligt system ger
- **Interface** (konsumerar systemet, producerar inte i pipeline) — kanske
  `consumes`- istället för `feeds`-relation
- **Extern produkt** — om något FAKTISKT ska säljas externt återkommer
  produktmallen (Target Audience, ROI mot marknad) för just den noden

---

## Vad händer med risk-frågan

Det förbättrade risk-schemat (probability × impact × score + mitigation,
baserat på MVP_comparison.xlsx-modellen) är **rätt för komponenter** — det
mäter teknisk och operationell risk, vilket är vad som faktiskt gäller när du
bygger en komponent.

Marknadsrisk hör bara hemma på noder som genuint övervägs som externa produkter
— och vi har konstaterat att du i praktiken inte har några sådana kvar. Allt är
komponenter i olika stadier. Så risk = teknisk/operationell, överallt.

Detta gör risk-quest:et i backloggen (`cns-analyst/planning/quests.md`)
meningsfullt och välriktat.

---

## Beslut: filnamn förblir `project.md` (typ bärs av `kind`)

Frågan uppstod om noder borde ha olika filnamn (`component.md`, `system.md`,
`framework.md`) nu när de har olika typer. Beslut: **NEJ — behåll `project.md`
för alla nodtyper. `kind` i frontmatter bär typen.**

Motivering:
1. **All kod globbar `*/project.md`** — `project_path()`, `list_project_files()`,
   post-commit-hooken, json_exporter, devwatch, MCP-servern, dashboarden. Olika
   filnamn = varje sådan plats måste hantera flera mönster = stor buggyta för
   en kosmetisk vinst.
2. **`kind` kan ändras, filnamn vill man inte byta.** En nod kan röra sig
   (ai-ticket-triage: komponent → system). Sitter typen i filnamnet måste filen
   döpas om → bryter git-historik och alla referenser. Sitter den i frontmatter
   ändras ett fält. Mjukt och spårbart.
3. **Strukturen bär redan typen** (via `part_of`). Filnamnet skulle duplicera
   information som redan finns — och duplicerad sanning blir motstridig sanning.

Tre olika filnamn vore det sämsta alternativet: migreringsjobbet PLUS pågående
komplexitet av flera mönster överallt.

**Möjlig framtida ISOLERAD övning (inte nu, inte i arkitektur-quest:et):** om
ordet "project" fortsätter skava efter att systemet använts ett tag, byt ALLA
till ett neutralt `node.md` i ett eget rename-quest. Allt är noder — det vore
konceptuellt korrekt. Men det blandas INTE in i den additiva migreringen; det
är en separat sak som annars ökar risken i allt annat.

---

## Migreringsstrategi: ADDITIV, inte hård

16 befintliga project.md har produktmallen. Vi skriver INTE om alla på en gång.

1. **Lägg till** `kind`, `stage`, `part_of`, `feeds`, `depends_on` i validator
   som valfria fält (gamla fält behålls, inget bryts).
2. **Migrera en nod i taget** när du ändå rör den — lägg till de nya fälten,
   fasa ut produktfälten gradvis.
3. **Dashboarden** läser nya fält om de finns, faller tillbaka på gamla annars.
4. **Behåll** `layer`/`pipeline` (de fungerar och stämmer med modellen).
5. När alla noder migrerats — ta bort produktfälten ur schemat.

Detta bevarar kontroll och översikt. Ingen stor omskrivning, ingen risk att
allt bryts samtidigt.

---

## Konsekvens för befintliga noder (utkast — justeras vid migrering)

```
cortxt                  framework  · working   · part_of: null
  pipeline-intern       system     · working   · part_of: cortxt
    cns-devwatch        component  · working    · part_of: pipeline-intern · feeds: [cns-devlog]
    cns-devlog          component  · working    · part_of: pipeline-intern · feeds: [cns-brief]
    cns-brief           component  · working    · part_of: pipeline-intern
  pipeline-review       system     · working   · part_of: cortxt
    cns-analyst         component  · working    · part_of: pipeline-review
  pipeline-extern       system     · idea/building · part_of: cortxt
    docs-watch          component  · working    · part_of: pipeline-extern · feeds: [dev-changelog-engine-mini]
    dev-changelog-engine-mini  component · working · part_of: pipeline-extern
    scoring-studio      component  · idea       · part_of: pipeline-extern
  infrastructure        system     · working   · part_of: cortxt
    cns-hosting-infra   component  · working    · part_of: infrastructure
    webhook-router      component  · building   · part_of: infrastructure
    cns-vault-app       component  · working    · part_of: infrastructure (MCP-server bor har)
    cortxt-eventstream  component  · idea       · part_of: infrastructure
  interface             system     · working   · part_of: cortxt
    cortxt-dashboard-app component · working    · part_of: interface
    cortxt-landing      component  · working    · part_of: interface
    cortxt-graph-view   component  · idea       · part_of: interface
  (oplacerade / oklara)
    ai-ticket-triage    system?    · idea       · part_of: null (beslutas nar den byggs)
    dev-changelog-engine component · idea
    site-change-monitor component  · shelved
```

---

## Nästa steg (när du sätter dig fräsch)

1. Läs och justera detta dokument.
2. Quest: additiv schema-migrering (validator + md_parser + nytt komponent-template).
3. Quest: dashboarden läser nya fält, faller tillbaka på gamla.
4. Quest: depends_on/feeds → graph-vyn ritar sig själv.
5. DÄREFTER: eventstream, som matar Arbetslogg-sektionen automatiskt.

Bygg inget förrän detta fundament känns rätt. Det är grunden allt annat vilar på.
