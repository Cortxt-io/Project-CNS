# Spec: Konsolidera Cortxt till ett monorepo (Project-CNS som rot)

**Status:** utkast — granska och besvara kvarstående frågor innan kod.
**Skapad:** 2026-06-09. **Arbetsspråk:** svenska.

## Kontext

Cortxt bor idag i två git-repon: `Project-CNS` (Python/Flask → Railway, äger datamodellen + nodvalvet, är GitHub-sanningen) och `cortxt` (pnpm/Turborepo: dashboard + landing → Vercel). Plus tre äldre fristående verktygsrepon (`docs-watch`, `dev-changelog-engine-mini`, `webhook-router`).

**Problemet:** datamodellen är *trippel-duplicerad* — enums (status/stage/kind) och nodfält handkodas i `schemas/node_schema.json`, `scripts/validator.py` och `cortxt/apps/dashboard/src/data/labels.js` utan delad typ eller genererad klient. `project→node`-omdöpningen bevisade kostnaden: backenden bytte till `/api/node` medan dashboarden fortfarande säger "project" i state/router/`nodeTypes`, och `/api/node/{slug}/full` ser oimplementerad ut.

**Skälet att slå ihop** är inte att de pratar över HTTP (det funkar fint över repo-gränsen). Skälen är: det delade datakontraktet ska avdupliceras, Cortxts egen premiss ("utspridd kontext kostar"), preferens för färre repon ([[repo-topology-preference]]), och målet att **CNS ska kunna modifiera frontend senare**.

## Låsta beslut (med användaren)

1. **Ett monorepo med `Project-CNS` som rot.** `GITHUB_REPO` är **oförändrat** → webhook, GitHub Action-cron, Contents-API-sökvägar (`nodes/`, `exports/`) och nodvalvet rör sig **inte**. Backenden flyttar inte alls; vi nestar bara in frontenden. (Detta är lägre risk än det ursprungliga "cortxt som rot" — hela dataplanet är orört.)
2. **Frontend som `apps/` i roten** (Turborepo), inte en egen `frontend/`-katalog. Korta, förutsägbara sökvägar (`apps/dashboard/src/...`) som CNS kan skriva till.
3. **CNS-modifierar-frontend är redan upplåst av samma-repo.** `app/git_ops.py:push_file_immediately()` skriver redan vilken path som helst i `GITHUB_REPO`; idag `nodes/<slug>/node.md`, framöver `apps/dashboard/src/...` på samma sätt. Ingen ny mekanism.
4. **Frikopplat / ej i scope:** `promote_idea_to_issue` (eget spår). Quest-logiken putsas inte (ersätts av Issues). Småverktygen fold:as in lat, senare.

## Målstruktur

```
Project-CNS/                 ← monorepo-roten, GITHUB_REPO oförändrat → Railway (bygger Python i roten)
├── app/  scripts/  schemas/  cns.py  requirements.txt   ← backend, ORÖRT i roten
├── nodes/  exports/         ← nodvalvet + quests/ideas, ORÖRT i roten
├── apps/
│   ├── dashboard/           → Vercel (Root Directory = apps/dashboard, path-filter)
│   └── landing/             → Vercel (Root Directory = apps/landing)
├── packages/
│   ├── ui/
│   └── cns-schema/          ← NY: enums + nodfält (TS) genererade ur schemas/node_schema.json
├── tools/                   ← (senare, lat) docs-watch, dev-changelog-engine-mini, webhook-router
├── pnpm-workspace.yaml      ← NY
├── turbo.json               ← NY (in från cortxt)
└── package.json             ← NY rot-manifest för JS-workspacet
```

## Vassaste kanten: Railway-buildpack-detektering

Railway bygger idag `Project-CNS` som Python (uvicorn). Lägger vi `package.json` + `turbo.json` i roten kan Nixpacks tro att det är en Node-app och bryta backend-deployen. **Mitigering:** pinna Python-builden explicit (`nixpacks.toml`/`railway.toml`/`Procfile` mot uvicorn-startkommandot) och verifiera att Flask/MCP startar. Detta ersätter den tidigare "valv-sökväg"-risken (som försvinner när backenden inte flyttar).

## Migrationsordning (systemet lever hela vägen)

1. **För-arbete (säkert, värdefullt oavsett) — KLART utom drift:** `packages/cns-schema` skapat och genereras ur `schemas/enums.json` (enkälla, läses även av `validator.py`); dashboarden importerar det via `labels.js`. `/api/node/{slug}/full` verifierad (finns). **Kvar:** rename-driften ("project"→"node" i ~34 filer, kosmetisk, ingen funktionsbugg — uppskjuten till merget).
2. **Graft:a in `cortxt`** i `Project-CNS` med `git subtree` (bevarar historik) → `apps/` + `packages/`. Lägg `pnpm-workspace.yaml`, rot-`package.json`, flytta in `turbo.json`.
3. **Pinna Railway till Python** (vassaste kanten); verifiera backend-deploy.
4. **Koppla om Vercel:** två projekt med Root Directory `apps/dashboard` resp. `apps/landing` + path-filter så backend-pushar inte triggar frontend-deploy. `vercel.json`-proxyn till Railway oförändrad.
5. **Cutover + verifiera** (nedan).
6. **Avveckla/arkivera `cortxt`-repot.** Uppdatera `CLAUDE.md` (workspace + Project-CNS) och `RUNBOOK.md` (stale `prompt-cns/`-sökvägar = samma repo, äldre namn — städas här).
7. **(Lat, senare):** fold:a in småverktyg i `tools/`; lös `webhook-router`-dubbletten (kod i både eget repo och `nodes/webhook-router/src/`) först.

## Kritiska filer / återanvändning

- `app/git_ops.py` — `push_file_immediately()` + `REPO_ROOT`. Roten oförändrad → ingen ändring; samma motor låter CNS skriva `apps/...`.
- `app/server.py:1686-1712` — webhook-slug-utvinning. Oförändrad (sökvägar rör sig inte).
- `schemas/node_schema.json` — auktoritativ källa för `packages/cns-schema`-generatorn.
- `cortxt/apps/dashboard/src/data/labels.js` — slutar handkoda enums, importerar `@cortxt/cns-schema`.
- `cortxt/apps/dashboard/vercel.json` — proxy `/api/*` → Railway, oförändrad.
- Frontend-drift: `App.jsx`, `GraphCanvas.jsx`, `hooks/useProject*.js`.

## Verifiering (efter cutover, steg 5)

- `GET /api/nodes` → 200 `{nodes:[...]}` (backend-deploy överlevde Railway-pinningen).
- Dashboarden laddar grafen; inga "project"-referenser som bryter; enums från `@cortxt/cns-schema`.
- `/mcp` svarar; MCP-round-trip `cortxt_capture_idea → list_ideas → promote_idea_to_quest` pushar till repot.
- Webhook-round-trip: push som rör `nodes/<slug>/` auto-completar quest (bekräftar oförändrad valv-sökväg + `GITHUB_REPO`).
- Vercel: frontend-only-push deployar frontend men **inte** Railway; backend-only-push tvärtom.

## Designval för senare (inte hinder för layouten)

- **CNS pushar frontend via PR, inte rakt på main.** Skriver CNS frontend-kod direkt till `main` via Contents API kringgås JS-build/tester/Vercel-preview. Grinda senare: CNS skriver till en branch / öppnar PR för frontend-ändringar.

## Kvarstående småfrågor (lösas under utförande)

1. **LÖST:** Enkälla = `schemas/enums.json`, läst av både `validator.py` (Python, som `set`) och `cns-schema` (JS, genererad via `packages/cns-schema/generate.mjs`). Återstår: koppla generatorn till ett pre-commit/CI-steg så den inte glöms, och kör ett Python-smoke-test på `validator.py`-ändringen (ej körbar lokalt — ingen Python). Layer/pipeline/family medvetet uteslutna (legacy/ovaliderade).
2. `git subtree` med `--prefix=.` vs per-katalog-graft (historik-granularitet).
3. Cutover-fönster: kort omkopplingsfönster för webhook/deploy accepteras, annars branch-baserad parallellkörning.
