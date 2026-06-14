# Git/GitHub-grund — repo-topologi, branchstandard, org

**Status:** beslutad 2026-06-14 · **Gäller:** alla Cortxt-repon (Project-CNS, cortxt, webhook-router)

Detta dokument låser hur vi använder git och GitHub över hela Cortxt. Det skrevs när org:en sattes upp och
osäkerhet fanns kring repo-uppdelning och branch-hygien. Beslut nedan är normen; avvikelser motiveras här.

## Beslut 1 — Repo-topologi: polyrepo, splittra inte Project-CNS
Behåll separata repon: **Project-CNS** (kärnan — CLI + Flask-backend + MCP + catalog, en kohesiv Railway-deploy),
**cortxt** (frontend-monorepo på Vercel), **webhook-router** (egen tjänst).

`Project-CNS` splittras **inte** nu: MCP och backend är *samma* ASGI-deploy (`app/asgi.py`), CLI deployar inte alls,
och allt binder ihop via `scripts/`-kärnan. Att splittra skulle ge versionsskew + paketunderhåll utan vinst.
"Svårt att överblicka" löses med tydligare modulgränser + arkitekturkarta, inte med fler repon (split gör cross-cutting
överblick värre). Framtida split-punkt finns redan inritad: noden `mcp-gateway` byggs när Plan B-agenter kräver det.

**Kriterier för framtida split** (när NÅGOT gäller): egen deploy-takt, egen runtime/språk, egen ägare/team, eller
för stort att överblicka. `catalog.yaml:url_repo` modellerar redan multi-repo — håll uppdaterat.

## Beslut 1b — Org = logisk enhet, inte fysisk monorepo
Org:en motiveras av **kapabilitet** (cross-repo Projects v2 + Linear-webhooks), inte av öppenhet. **Privat org, bara
Rikard nu** — publikt/licens uppskjutet. Repona förblir separata under org-paraplyet; org-Projects ger "allt på ett
ställe" utan att blanda Python (Railway) och JS (Vercel) i en fysisk monorepo.

cortxt är redan en Turborepo-monorepo (`apps/dashboard` + `apps/landing`) och dess GitHub-remote är aktuell.

## Beslut 2 — Branchstandard: trunk-based
`main` är **enda långlivade branchen** per repo; allt annat kortlivat (långlivad *komponent* ≠ långlivad *branch*).
Skäl: kontinuerlig deploy (Railway/Vercel vid push till main), en live-version, många små agentur-PR:er — git-flows
långlivade brancher skulle ge merge-skuld och sen riskupptäckt.

**Namnschema** (ett, ersätter dagens blandning):
- `feat/<kort>` · `fix/<kort>` · `chore/<kort>` · `docs/<kort>`
- Agenturen: `dispatch/issue-<n>` (skrivande pass), `claude/issue-<n>` (Claude Code). Avvikare standardiseras
  (`dispatch-loop-59` → `dispatch/issue-59`).

**Squash-merge** (en commit/PR på main), **radera branch efter merge**. Commit-meddelanden + PR-titel/beskrivning på
engelska (artefakt-språkpolicy). Conventional commits (`feat:`/`fix:`/`chore:`) rekommenderas, tvingas inte.

## Beslut 3 — Kollaborations-dugligt skydd (branch protection på main, alla repon)
Samma regler för människa, agent och ev. extern bidragsgivare — det är vad som gör repot tryggt att öppna för forks.
- **Strikt för alla + admin-ventil:** PR + grön CI krävs för allt, ingen direkt-push till main (även Rikard);
  admin-bypass behålls för nödfall.
- Squash-merge, linjär historik, radera head-branch automatiskt, required reviewer (matchar dispatch-loopens
  draft-PR + reviewer-flöde; lågrisk self-merge enligt befintlig policy).
- **Fork/PR-flöde + scaffolding:** `CONTRIBUTING.md`, `CODEOWNERS`, PR-/issue-mallar. `LICENSE` uppskjuten tills
  något blir publikt (utan licens får ingen juridiskt återanvända koden).

## Beslut 4 — Org-migrering (körschema, minimal nedtid)
Webhooks + repo-secrets ÖVERLEVER transfer. Railway- och Vercel-auto-deploy BRYTS och kräver manuell reconnect.

**Förbered (ingen nedtid):**
1. Skapa org:en.
2. Installera Railway GitHub App på org:en (github.com/settings/installations → inkludera org-repos).
3. Installera Vercel GitHub App på org:en. **Vercel-kontot måste vara Team/Pro** — Hobby kan inte deploya privat
   org-repo (hård blockering).

**Transfer (~15–30 min fönster):**
4. Transferera i ordning: `webhook-router` → `Project-CNS` → `cortxt`.
5. Uppdatera lokala remotes: `git remote set-url origin https://github.com/<ORG>/<repo>` (alla kloner + cns-tui-worktree).
6. **Återanvänd ALDRIG gamla adressen** (`rian010194/<repo>`) — dödar redirecten permanent.

**Reconnect + verifiera:**
7. Railway: projekt → Settings → Source → disconnect → reconnect (full app-reinstall om stale `installation_id`).
8. Vercel: projekt → Settings → Git → disconnect → reconnect (eller transferera Vercel-projektet till Team).
9. Webhooks: repo → Settings → Webhooks → Recent Deliveries gröna.
10. Push-test till main i varje repo → bekräfta Railway-redeploy + Vercel-deploy.
11. Ersätt person-scopade fine-grained PAT:ar med org-PAT (`repo`, `read:org`, `project`); uppdatera Railway/Vercel/
    MCP-secrets; `.mcp.json` `GITHUB_PAT` satt + org-scoped.
12. Uppdatera `catalog.yaml:url_repo` till org-URL:er. Verifiera/återskapa branch protection.
13. (Governance, ej akut) Överför MCP-serverns OAuth-app till org-ägo.

## Omedelbar städning (oberoende av migreringen)
- `cortxt`: radera remote `master` (behåll `main`); bekräfta default branch = `main`.
- `cortxt`: synka lokal klon (`git checkout main && git pull` — lokalt ligger efter mergad PR #3).
- Rensa mergade/stale brancher (båda repon, lokalt + remote) efter verifiering att de landat.
- Sätt branch protection på `main` i båda repona enligt Beslut 3.

## Relaterat
- Spegel-/projektion-skelettet (kanonisk taxonomi → org-Projects/Linear/Vercel) är parkerat tills detta fundament
  sitter: `plans/taxonomy-mirror-skeleton.md`.
