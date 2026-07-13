# CLAUDE.md — Project-CNS

CNS-kärnan och backenden. Läs detta först varje session. Arbetsspråk: **svenska**.

> **Rivning 2026-07-13.** Agentur-lagret (fryst 2026-07-12) är **borttaget**, tillsammans med allt
> annat som inte hade en konsument: MCP-servern (10 feta verktyg + 43 alias — **noll anrop** i
> samtliga transkript), sessionslagret (**noll sessioner** på en månad), idé-inkorgen, btw-lagret,
> 36 av 40 HTTP-endpoints, `archive/` (171 filer) och `lab/frozen/`. Repot gick från 525 till ~165
> spårade filer. **Git är minnet** — inget är arkiverat till en finare adress.
>
> Agentur-kommandona (tui, status, dispatch, agent-ask, agent-tools, mcp-servers) är **borttagna ur
> CLI:t**. De avvisar inte längre med exit 2 — de existerar inte.

## Vad det är

CNS (Central Node Store): en katalog över portföljen, och en läs-API som matar **app.cortxt.io**.
Varje system är en post i **`catalog.yaml`** (graf + routing) plus en valfri `decisions/<slug>.md`
(ADR-prosa). **GitHub är källan till sanning** för arbete (issues, PR:er) — CNS speglar det inte.

## Kontraktet — det enda som får gå sönder på riktigt

Frontendens söm — cns.js i cortxt-repot (apps/app/src/lib/) — har **exakt fyra funktioner**. De
motsvarar de fyra endpoints som är kvar:

| Endpoint | Läses av |
|---|---|
| `/api/command-center` | Cockpit + Sidebar (`useCommandCenter.js`) |
| `/api/vertical/<slug>` | `pages/Vertical.jsx` |
| `/api/nodes?domain=` | grafen i `pages/Vertical.jsx` (rått — behöver `part_of`/`feeds`/`depends_on`/`kind`) |
| `/api/cookbook/<slug>` | `pages/Vertical.jsx` |

`tests/test_api_contract.py` pinnar formen mot inspelade svar i `tests/golden/`. Spela in på nytt med
`python scripts/record_golden.py` före och efter en ändring — samma fält ⇒ appen överlever.

## Nodmodellen

**`catalog.yaml` (repo-rot) är enda strukturerade källan.** 44 poster under `systems:`, handredigerad.
Varje post: `title`, `summary`, `type`, `domain`, `feeds`, `depends_on`, valfritt `part_of`,
`url_repo`, `url_live`, `owner_agent`, `integrations`.

- `kind` (component | system | framework) **härleds ur `part_of`, lagras inte** (`catalog.derive_kind`).
- `layer` härleds i `catalog.derive_layer` — **den implementerar fortfarande den ersatta
  tre-lagersmodellen**, inte `portfolio-lager-v2` (vaulten). Rör den inte förrän den regeln är prövad.
- Hälsa härleds vid läsning (`scripts/health.py`), deklareras aldrig.
- Livscykel/status/stage bor **inte** i katalogen — de delegeras till GitHub.

Läsning går via `scripts/catalog.py:load_catalog()`. `md_parser.read_node`/`read_all_nodes` är tunna
wrappers ovanpå den; skriv-vägen är pensionerad (redigera `catalog.yaml` för hand).

## Repo-layout

- `cns.py` — Core-CLI: `new`, `validate`, `export`. Importerar bara root-`scripts/`.
- `lab/cns_lab.py` — Lab-CLI: allt övrigt (`venture`, `deploy`, `project`, `quest`, `cookbook`,
  `health`, `pr`, `skill-export`, `memory-export`, `skill-usage`, `selftest`, …).
- `scripts/` (Core) och `lab/scripts/` (Lab) är **ett PEP 420 namespace-paket**. Core importerar
  aldrig Lab; Lab får importera Core.
- `scripts/catalog.py` — katalog-läsaren. `scripts/validator.py` — `cns validate`.
- `scripts/prose_check.py` — **ärlighetsgrinden**. Kontrollerar backtickade sökvägar, `cns`-kommandon
  och pensionerade fält i all prosa. Kör i CI på varje PR. En `prose: record`-fil checkas aldrig.
- `lab/scripts/command_center.py` — kompositören bakom `/api/command-center`.
- `lab/scripts/roadmap.py` — per-vertikal roadmap (`roadmaps/_recipe.yaml` + `roadmaps/<slug>.md`).
- `lab/scripts/health.py` — härledd hälso-scorecard (nod, issue, milestone, initiative).
- `lab/scripts/issues_client.py` / `prs_client.py` — GitHub REST, ingen `git`-subprocess.
- `lab/scripts/skill_export.py` — **vaulten äger skills**; `.claude/skills/` är en härledd artefakt.
  Tre mål: `workspace` (laddas från första prompten), `cns` (lazy), `vault`. En riktning.
- `lab/scripts/memory_export.py` — samma för minnen (`Studio/Memory/` → `~/.claude/.../memory/`).
- `lab/app/server.py` — Flask. `lab/app/asgi.py` — ASGI-entrypoint (Starlette runt Flask).

## Deploy

Railway, från repo-roten. `railway.json` är enkälla; start:
`gunicorn app.asgi:asgi_app -k uvicorn.workers.UvicornWorker`. **Railway redeployar vid push till
main** — syns inte en ändring i appen, kolla Deployments-loggen.

Dashboarden (`cortxt`-repot, Vercel) proxar `/api/*` hit via sin `vercel.json`.

## Enums

Enkälla: `schemas/enums.json` — läses av `scripts/validator.py` och av `cortxt/packages/cns-schema`
(genererad). Lägg inte tillbaka `layer`/`pipeline`/`family`.

## Arbetsregler

- **Git/GitHub-grund:** trunk-based, `feat/`/`fix/`/`chore/`/`docs/`, squash-merge. Låst i
  `decisions/git-github-grund.md`.
- **Issues och PR:er går genom `gh` CLI.** MCP-verktygen är borta. Skillsen `issue-lifecycle` och
  `pr-protokoll` (vaulten) beskriver hur.
- **Spec först.** Specar bor i **vaulten**, under den effort de tjänar — inte i `docs/` här.
- Validera (`cns validate`) innan commit.
- **Prosa som beskriver koden måste ändras i samma PR som koden.** Det är vad grinden mäter.

## Underhåll av denna fil

Läses varje session. **Uppdatera den i samma ändring som du ändrar något den beskriver.** Låter du
den driva börjar varje framtida session från felaktiga antaganden — och det var precis det som gjorde
rivningen ovan nödvändig.
