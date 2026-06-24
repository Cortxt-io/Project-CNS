# Juvahem — beslut & anteckningar

## Vad
Beslutsstöd för par/familjer som ska flytta: rankar Sveriges 290 kommuner mot parets
**kombinerade** profil (båda partnernas jobbmatch, kommunalskatt, boende, pendling, skola,
energipris-zon). Eget venture, eget repo (`Cortxt-io/juvahem`), egen Vercel, live på juvahem.se
via GitHub auto-deploy. Modellerad i CNS som `domain: juvahem`.

## Beslut
- **Moat = personalisering per pars profil, inte generiska "bästa orter"-listor.** Två inkomster +
  två yrken + hushåll matchas samtidigt — det är det konkurrenterna inte gör.
- **Gratis-/öppen-data-MVP (Tier 1):** Kolada (skatt/befolkning), JobTech (jobbannonser per
  yrkesfält × kommun), SCB PxWeb. Deterministisk klient-scoring (`src/lib/score.js`),
  renormaliserar bort saknade dimensioner. Ingen egen backend.
- **Affiliate förkastad** som intäktsmodell i v1 — för svagt och grumlar oberoendet.
- **Booli/Lantmäteriet (huspriser) = Tier 3, juridisk/kostnadsspärr** — vilande dimension,
  UI visar "Coming soon" tills en fri/laglig källa finns.
- **Datadriven, inte innehållsdriven:** värdet ligger i modellen + 290 förrenderade SEO-sidor,
  inte i redaktionellt innehåll.

## Stack: SvelteKit (vs React) — rationale (2026-06-24)
Valet var odokumenterat (konstaterat i NOTES/UI-SPEC, aldrig jämfört). Spikas här i efterhand som
ett **medvetet behållet** val (jfr refaktor-beslutet nedan).

**Fördelar (passar juvahems form):**
- Kompilerar bort runtime → mindre bundle → snabbare laddning + bättre Core Web Vitals (rankingfaktor
  för en publik, sök-driven sajt).
- SvelteKit ger SSR/prerender per route out of the box: landing prerenderad, `/kommun/[slug]` statiska
  SEO-sidor m. canonical, `/jamfor` interaktiv (`ssr=false`). React kräver Next.js för motsvarande.
- Mindre boilerplate (Svelte 5 runes) → snabbt att bygga solo.

**Nackdelar (= React-fördelar):**
- Mindre ekosystem, mindre AI-träningsdata, mindre talangpool.
- **Designsystem-divergens:** `@cortxt/ui` + övriga vertikaler lutar React/shadcn; juvahem-UI måste gå
  via shadcn-svelte (separat port). Det är per-stack-priset (jfr [[per-stack-arketyp-beslut]]).

**Motivering:** juvahem är SEO-statisk + sök-driven med EN interaktiv vy — exakt formen SvelteKit är
bäst på. Konsekvent med per-stack/polyglott-valet (bästa verktyg per jobb + lärande). Konsekvens för
arketyperna: juvahems UI-arketyp-referens blir **Svelte**, inte React.

## Bygga om från grunden vs rädda vibe-koden? (2026-06-24)
**Beslut: REFAKTORERA, inte bygg om.** En kodgranskning (Explore, hela juvahem/etl + src, 34 filer)
mot faktisk kod reviderar "vibe-kodad, bygg om allt"-premissen — juvahem är inte en röra. Det svåra
är redan rent och bevisat; det rörigaste är presentationen + avsaknad av tester.

| Lager | Dom | Varför |
|-------|-----|--------|
| ETL (`etl/`) | KEEP | Provenance per värde, typad Pydantic-modell, isolerade källklienter — distillerad till CNS ETL-arketyp-referens (`archetypes/etl-python/`) |
| Scoring (`src/lib/score.js`) | KEEP | Ren WSM-funktion, dual-career via harmoniskt medel, transparent |
| Explain (`src/lib/explain.js`) | KEEP | Deterministisk, tröskelberoende, centraliserad config |
| Data-koppling (`communes.js`/`presets.js`) | KEEP | Statisk, hårt Pydantic-kontrakt, robust slug-mappning |
| UI (Svelte) | REFACTOR | Bra komponentseparation, men två rankings-dataflöden + Explanation-dubblett |
| Sömmar ETL→UI | REFACTOR | Starkt kontrakt men ingen runtime-validering → ETL-fältändring kan tyst bryta UI |
| Tester | SAKNAS (kritiskt) | Ingen test av scoring/explain mot faktisk data |

Att bygga om från noll skulle sänka beprövad, ren kod (inkl. ETL:n som blev arketyp-referens) utan
vinst. Arbetet är **Konsolidera-fasen**: tester + härda sömmen + UI-refaktor (shadcn-svelte). Se
`roadmaps/juvahem.md` (current_phase: konsolidera).

## Status / öppet
- ETL klar för Kolada + JobTech + transit (resumable). Pris- och pendlingsdimensioner specade
  men ej ETL:ade.
- `url_repo` rättad till `Cortxt-io/juvahem` (flyttat från `rian010194` 2026-06-16).
