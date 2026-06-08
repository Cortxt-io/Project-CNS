# Project Vault Dashboard -- anteckningar

## Designideer

- Mörkt tema som default (matchar terminal-estetik, signalerar "developer portfolio").
- Varje projekt visas som ett kort med statusfärg (gron = live, gul = early_mvp, gra = idea, rod = shelved).
- ROI-stapel intill varje kort -- snabb visuell jamforelse.
- Responsivt: kortlayout pa mobil, tabell pa desktop.
- Ingen JavaScript-framework -- vanilla JS + CSS custom properties for tema.

## Mojliga grafer

1. **ROI per projekt** -- horisontell bar chart, sorterad fallande.
2. **Statusfordelning** -- enkel donut/pie (idea vs early_mvp vs mvp vs live vs shelved).
3. **Kostnad vs. Varde** -- scatter plot med projektnamn som labels.
4. **Tidslinje** -- simpel timeline med `created`-datum per projekt.

## Datakalla

- `projects.json` genereras av `cns export --format json`.
- Filen kopieras till `public/data/projects.json` vid build/deploy.
- Dashboarden laser filen via `fetch()` -- ingen server behoves.

## Inspirationskallor

- Linear's changelog (ren, tydlig, snabb).
- GitHub's contribution graph (visuell densitet).
- Stripe's docs sidebar (navigering).

## Oppen fraga

- Ska dashboarden ha filter/sok? I MVP: nej. Projekten ar fa nog att oversikten racker.
- Ska den visa quest-data (current_slice)? Ja, om projektet har quest state -- visa som badge/tag.
