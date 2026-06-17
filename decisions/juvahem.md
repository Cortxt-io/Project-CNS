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

## Status / öppet
- ETL klar för Kolada + JobTech + transit (resumable). Pris- och pendlingsdimensioner specade
  men ej ETL:ade.
- `url_repo` rättad till `Cortxt-io/juvahem` (flyttat från `rian010194` 2026-06-16).
