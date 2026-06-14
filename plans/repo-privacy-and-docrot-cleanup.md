# Repo-privacy-split + doc-rot-städning (SPEC — granska före exekvering)

**Status:** spec fångad 2026-06-14, ej exekverad. Två sammanflätade workstreams: (A) hålla interna
specs/strategi privata medan repona förblir publika (showcase/collab), (B) rensa vilseledande docs.

## Context
Project-CNS + cortxt är **publika** (showcase för arbetsgivare + collab/forks önskat). Verifierat:
**inga hemligheter läckte** (token-scan ren) — bara strategi-/spec-prosa. Rikard vill behålla publikt
MEN inte exponera halvfärdiga specs/research/strategi. Dessutom: flera publika .md beskriver en **död
verklighet** (node.md-eran, `prompt-cns/`, generiska lager) → skadar showcase-värdet just nu.

**Låsta beslut:**
- Båda repona förblir **publika** (showcase/collab).
- **Historik-skrubb SKIPPAS** (inga hemligheter; låg risk; kan BFG:as senare).
- Interna docs → **separat privat repo** (research-rekommendation; lokal-only avråds då det bryter
  `git_ops`-agentflödet). Publika *färdiga* ADR:er = portfolio-plus.

---

## Workstream A — Privacy-split (publikt showcase + privata internals)

### A1. Nytt privat repo `Cortxt-io/cns-internal`
Privat. Speglar arbetsytan. Hit flyttas det som inte ska vara publikt:
- `plans/` (implementationsspecs, halvfärdiga)
- research-output (när sådan sparas som fil)
- strategi/roadmap/affärsprosa (om/när den finns som filer)
- ADR-**utkast** (Status ≠ Accepted)

### A2. Publikt behålls (showcase-värde)
- All kod (`scripts/`, `app/`), `catalog.yaml`, `schemas/`, tester, CI (`.github/workflows/`)
- `CLAUDE.md` (arkitektur/contributors-guide)
- `decisions/` — men **bara färdiga ADR:er** (Status: Accepted/Superseded). Utkast → privat.
  (Färdiga ADR:er publikt visar genomtänkt ingenjörskap — plus för arbetsgivare.)
- README (omskriven, se B), CONTRIBUTING/CODEOWNERS (från git-github-grund)

### A3. Gitignore + konvention
- `.gitignore` i Project-CNS: `plans/`, `research/` (+ ev. `strategy/`) så framtida specs inte
  hamnar publikt.
- **CLAUDE.md-konvention (uppdatera):** "spec-first" → specs skrivs i `cns-internal/plans/`, inte
  publika repot. När en ADR når Accepted → kopieras till `Project-CNS/decisions/` via PR (promote-flöde).
- **Agentflöde:** agenter klonar både `Project-CNS` och `cns-internal` (parallella kloner i arbetsytan),
  refererar med absoluta sökvägar. Claude Code ärver `gh`-credentials → når privata repot utan extra config.
- **Obs git_ops:** AI-skrivvägen som pushar specs måste peka på `cns-internal` (annars läcker den till publikt).

### A4. Flytt av befintliga specs (ej historik-skrubb)
- `git mv`/kopiera `plans/*` → `cns-internal`, `git rm` från Project-CNS, commit. (Historiken i publika
  repot behåller dem — medvetet accepterat; inga hemligheter.)
- `plans/taxonomy-mirror-skeleton.md` + `plans/org-bootstrap-cookbook.md` + denna fil → följer med till privat.

---

## Workstream B — Doc-rot (vilseledande publika filer)

### B1. Radera (noll/negativt värde, aktivt vilseledande)
- **`docs/ARCHITECTURE.md`** — AI-genererat generiskt skräp (Kubernetes/CDN/auth-service), beskriver
  ingenting i repot. **Radera.**
- **`system_prompt.md`** — död node.md-connector-prompt (refererar borttagna fält). **Radera/arkivera.**

### B2. Skriv om (publika, showcase-kritiska)
- **`README.md`** — beskriver node.md som sanning + döda scripts/fält. **Skriv om** mot catalog.yaml-modellen,
  aktivt CLI, MCP/dispatch-arkitektur. (Högsta showcase-prioritet.)
- **`RUNBOOK.md`** — `prompt-cns/`-sökvägar + 4 döda delprojekt. **Skriv om** (levande flöde: `cns tui`,
  `python -m scripts.dispatch`, board, MCP) eller radera.

### B3. Markera/flytta superseded
- `plans/node-schema-lock-spec.md` — riven premiss (redigera node.md) → radera el. SUPERSEDED-header (flyttas privat ändå).
- `plans/node-model-evolution-spec.md` — historisk → "HISTORISK ANALYS"-header.

### B4. Mindre status-uppdateringar (ej brådskande)
- `plans/autonom-agentur-byggordning.md` — Fas 3 klar, Fas 5 byggd-ej-default.
- `plans/integrations-field-spec.md` — reskriv intro: catalog.yaml förutsatt.
- `plans/english-naming-migration-spec.md` — uppdatera status (PR #141).
- `docs/agent-design-playbook.md` — "21 MCP-tools" → "10 feta verktyg".
- `docs/MONOREPO-MIGRATION-SPEC.md` — status-block: steg 2–7 ej utförda.
- `plans/nodmodell-teardown-spec.md` — "STATUS: GENOMFÖRD"-header.
- Spot-check `decisions/cns-core.md`, `decisions/cns-triage.md`, `.claude/skills/nod-granska.md` för node.md-rester.

---

## Föreslagen sekvens
1. **B1 (radera ARCHITECTURE.md + system_prompt.md)** — omedelbar showcase-vinst, noll risk.
2. **B2 (skriv om README + RUNBOOK)** — det publika ansiktet.
3. **A1–A4 (privacy-split)** — skapa cns-internal, flytta plans/ + utkast, gitignore, CLAUDE.md-konvention.
4. **B3–B4** — städa/markera kvarvarande specs (de flesta flyttas privat i A4 ändå).

## Verifiering
- Publikt repo: README/RUNBOOK speglar catalog.yaml-verkligheten; inga node.md/prompt-cns-referenser kvar
  (grep `node.md`, `prompt-cns`, `nodes/<slug>`).
- `plans/` borta ur publika trädet + gitignored; `decisions/` har bara Accepted/Superseded.
- `cns-internal` privat, innehåller specsen; agenter når båda repon.
- `cns validate` grön; tester gröna.

## Avgränsning
- Ingen historik-skrubb (beslutat). Det redan-publika i historiken accepteras (inga hemligheter).
- Detta är en spec — exekvering i egna PR:er per workstream.
