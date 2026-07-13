---
type: skill
prose: description
status: active
skill_name: idea-triage
department: Produkt
serves_gate:
routing: skill
reads: Ideaverse/CNS/Work/Raw/
writes: register, beskrivningar, GitHub-issues
decays_to: "inget — domen är omdöme, och omdöme blir aldrig kod"
exported: true
created: 2026-07-12
updated: 2026-07-13
tags: [skill]
---

# idea-triage

## Vad den gör
Tömmer inkorgen. Varje rånot i `Raw/` får en dom: bli register, bli beskrivning, bli issue — eller raderas.

## När den ska köras
Använd när inkorgen ska tömmas — "triagera idéerna", "vad ligger i inkorgen", "gå igenom Raw/" — och när en rånot är äldre än sju dagar, för då är den synlig skuld.

## Routningen — varför är detta en skill och inte kod?

Grupperingen *gick* att koda, och gjordes det (`scripts/triage.group_ideas`). Men **domen** —
är det här värt att bygga? — är omdöme, och omdöme får inte bli en poängformel som låtsas vara ett
beslut. `decays_to:` är därför tomt: den här skillen blir aldrig kod.

> **Omskriven 2026-07-13.** Den tidigare versionen drev kod-inkorgen (`exports/ideas/`,
> `cortxt_idea(action="capture")`, `cns triage`). Den inkorgen är **tom**, och
> [[Inkorgsregeln]] (en *regel*, `status: decided`) har flyttat inkorgen till vaultens `Raw/`.
> En regel är överordnad en skill. Mekaniken byttes; omdömeslagret nedan överlevde oförändrat.

## Steg 1: Fånga

En tanke som dyker upp skrivs som en **rånot i `Raw/`**. Inget mer. En rånot bär medvetet ingen
`prose:`-art — **arten sätts vid triage, inte vid skrivning.** Det är därför fångst får vara
slarvig: ingen förlitar sig på en rånot.

> **Ingen annan not får citera en rånot.** Citeras den har den slutat vara rå, och måste
> triageras först. ([[Inkorgsregeln]])

## Steg 2: Döm varje not mot matrisen

| Värde | Effort | Brådska | Åtgärd |
|-------|--------|---------|--------|
| Hög | Låg | Hög | Promote direkt |
| Hög | Låg | Låg | Promote till backlog |
| Hög | Hög | Hög | Promote, flagga |
| Hög | Hög | Låg | Behåll, ta upp vid planering |
| Låg | * | * | **Radera** — promota ej |

## Steg 3: Ge den en utgång

En rånot har **fyra** utgångar, och den ska ta en av dem. En mapp utan utgång blir en soptipp.

| Utgång | När | Vad du gör |
|--------|-----|------------|
| **Register** (`prose: record`) | den registrerar ett vägval som gjordes | flytta till rätt Log/, sätt `prose: record` — redigeras sedan aldrig |
| **Beskrivning** (`prose: description`) | den påstår något om vad som är sant nu | flytta till den effort/vertikal den tillhör, sätt `prose: description` |
| **Issue** | den är konkret arbete som ska göras | skapa GitHub-issue (se kriterierna nedan), radera rånoten |
| **Raderad** | den var brus, eller är överspelad | **radera.** Det är ett fullgott utfall, inte ett misslyckande |

## Promote-kriterier (en rånot blir issue ENBART om)

- [ ] Titeln beskriver en konkret leverans (verb + substantiv)
- [ ] Det finns en rimlig nod (`slug`) och ev. epic att länka till
- [ ] Effort är inte "omöjlig att estimera"

## Vad du INTE promotar

- Vaga idéer ("förbättra agenturen", "gör det snabbare"). Radera, eller låt mogna i `Raw/`.
- Idéer som kräver ett arkitekturbeslut som inte tagits — lyft det beslutet först.

## Spärrar

- Vägrar promota en rånot som inte klarar alla tre promote-kriterier.
- Vägrar lämna en not otriagerad förbi sju dagar utan att flagga den som skuld.
- Vägrar sätta `prose:`-art på en not utan att en dom faktiskt fattats — arten *är* domen.
