# CLAUDE.md — Project-CNS

CNS-kärnan och backenden. Läs detta först varje session. Arbetsspråk: **svenska**.

## Vad det är
CNS (Central Node Store): ett lokalt-först system för att modellera och driva ett produktsystem från idé till drift. Varje system är en post i **`catalog.yaml`** (graf + routing) plus en valfri **`decisions/<slug>.md`** (ADR-prosa). **GitHub är källan till sanning.**

## Nodmodellen (viktigast) — teardown 2026-06-12, epic #11
**`catalog.yaml` (repo-rot) är enda strukturerade källan.** Ersatte 31× `nodes/<slug>/node.md`-blanketten (den var en stilla hand-underhållen parallellkopia av verkligheten). Spec: `plans/nodmodell-teardown-spec.md`.

Varje system under `systems:` bär: `title`, `summary`, `part_of`, `feeds`, `depends_on`, `type`, `domain`, `owner_agent`, valfritt `url_repo`/`contributing_agents`/`integrations`.
- `kind` (component | system | framework): **härleds ur `part_of`-strukturen, lagras inte** — system om andra pekar på den via `part_of`, component om inga gör det, framework om toppnivå. Fraktal. Se `catalog.derive_kind()`.
- Tre relationer driver grafen: `part_of` (nesting), `feeds` (dataflöde), `depends_on` (beroende).
- **`stage`/`status`/risk/arbete delegeras till board** (GitHub Projects/Linear), inte CNS — de bor inte i katalogen. (`stage`-enumet finns kvar i `enums.json` tills board-integrationen wirar tillbaka det, steg 5/#102.)

ADR-prosa (varaktig beslutskunskap, t.ex. teknikval) bor i `decisions/<slug>.md` — **bara där sådan finns**, ingen tom mall per system.

**Läsning går via katalogen:** `md_parser.read_node`/`read_all_nodes` är tunna wrappers ovanpå `scripts/catalog.py:load_catalog()` (returnerar samma `(meta, sections)`-form; `sections` är tomt — prosan ligger i `decisions/`). Konsumenter (json_exporter, tui, projects, analyst, recommend, `role_for_node`) är därför oförändrade. **Skriv-vägen (`write_node`) är pensionerad** — redigera `catalog.yaml`/`decisions/` för hand; web/analyst/quest/local_editor-redigering rewiras i uppföljnings-issue.

## Repo-layout
- `cns.py` — CLI-entrypoint
- `catalog.yaml` (repo-rot) — **enda strukturerade källan** för nodmodellen (systemkatalog + graf + routing). `decisions/<slug>.md` = glesa ADR-noter. Genererades av `scripts/migrate_to_catalog.py` (engångs), redigeras sedan för hand.
- `scripts/catalog.py` — **katalog-läsaren**: `load_catalog()`, `derive_kind()` (fraktal kind ur part_of), `catalog_to_meta()`. Nodmodellens nya seam.
- `scripts/md_parser.py` — **tunna wrappers** (`read_node`/`read_all_nodes`) ovanpå `catalog.py`. `write_node` pensionerad (teardown #101). Kvarvarande mallar/`node_dir` är döda rester tills skriv-ytorna rewiras.
- `scripts/validator.py` — katalog-validering (`cns validate` = hela `catalog.yaml`; `<slug>` = ett system): referensintegritet + part_of-cykelkoll + mjuk type/domain/owner_agent
- `scripts/json_exporter.py` — exporterar katalogen till nodes.json (schema oförändrat; `stage`/`status` tomma efter delegering)
- `scripts/analyst.py` — AI-analys (anropar Claude via ANTHROPIC_API_KEY)
- `scripts/portfolio_brief.py` — daglig portföljbrief
- `scripts/issues_client.py` — **arbetsuppgiftslagret** (GitHub REST, ingen `git`-subprocess). Tre nivåer: nod (label `node:<slug>`) ← **quest = GitHub Milestone** (progress beräknas av GitHub) ← **issue = uppgift** (open/closed). Under issue: **todos = task-list-checkboxar** i issue-body — sanningen lever på GitHub. Verktygen i `app/tools/{issues,quests}.py`. **Dekompositionsprimitiver på issues** (härleds i `_normalize` med tomma defaults — gamla issues/dashboarden bryts ej): `type` (label `type:<value>`, story|bug|spike|chore, default story; enkälla `VALID_ISSUE_TYPES`), `depends_on` (body-rad `Depends-on: #12, #34`), `acceptance_criteria` (Given/When/Then-checkboxar under `## Acceptanskriterier`, sektionsmedvetet skilda från todos = agent-DoD). **`initiative`** = valfri toppnivå över quest, `Initiative: <namn>` i milestone-description. Spec: `plans/work-model-taxonomy-spec.md`.
- `scripts/idea_inbox.py` — idé-inkorg (lättviktig fångst; `exports/ideas/<id>.json`, glob `idea-*.json`; valfritt `session_id`). Promote → `issues_client.create_issue` (`cortxt_promote_idea_to_issue`, ev. under en quest/milestone).
- `scripts/btw_log.py` — btw-sessionslogg. **Personlig logg, ej produktdata:** `/btw`-asides (Claude Code-forkkommandot) grupperade per session i `exports/btw/<session-id>.json`, mjukt länkbara till quest/idé via `link_session`. Rent datalager — pushar inte själv. **Isolerat:** rör inte nodmodellen eller `cns.py`. Fångas av `scripts/btw_capture.py` (hook-entry: läser ett transkripts `/btw`-kommandon idempotent på `src_uuid`, äger pushen). Körs av en **Stop-hook** i arbetsytans `.claude/settings.json` (inte i något repo). Inkopplad som `cns btw {list|show|link}` (lokalt datalager, ingen push) och som MCP-verktyg.
- `scripts/session_store.py` — sessioner (AI-arbetspass) som förstklassiga objekt; en post per fil i `exports/sessions/session-*.json`, länkbar till quest/issue/idea/node och till Claude Code-transkriptet. **`running → done` är en pollbar signal** (en parallell session kan `/loop`:a tills en annan flippar `done` innan merge). **Rent datalager — pushar inte själv;** pushen ligger i MCP-wrappern (`app/tools/sessions.py`), samma split som idéer/btw. Överlappsfrågan = flera sessioner på samma nod ⇒ arbete att förena. **Sessionsträd** via valfritt `parent_id` (forks-under-forks, ortogonalt mot link). **Sessionstyp** (brainstorm | spec | bygg | triage | review | verktygsladan | retro; `spec` = definitionssteget mellan triage och bygg, ägt av produktchef + losningsarkitekt, ingen kod) + lokal aktiv-typ-markör `exports/active_session.json` som `router.py`-hooken läser för att injicera `[SESSION: <typ>]` per prompt. **Markören följer arbetet automatiskt:** hooken `_detect_type` härleder typ ur promptens arbetsspråk (`TYPE_SIGNALS`-regex) och **auto-sätter** markören (`set_active`) vid tydlig signal — vanlig/konversationell chatt lämnar typen orörd (ingen tjafs-växling). Manuellt `/session <typ>` funkar fortfarande men behövs inte (beslut Rikard 2026-06-11: "vill inte ändra session manuellt" — tidigare flaggades bara `[SESSION-SKIFTE?]`, nu växlas tyst eftersom en kvarglömd markör visade sig vara värre än auto). Markören är en sidofil (inte en session-post) för att hooken behöver omedelbar lokal synlighet medan kanonisk bokföring går via GitHub. Inkopplad som `cns session {list|show|fork|tree|set-active|get-active|clear-active}` (lokalt datalager, ingen push).
- `scripts/dispatch.py` — **dispatch-loop** (#59, Fas 3): agenturens puls i **övervakad crawl**. Plockar EN lämplig issue (`assess_suitability` hoppar diffusa/feature-tunga/ouppfyllda-`depends_on`) → `lease_store.claim` → `agent_roles.role_for_node` → kör ETT pass via `agent_host.run_turn` → eval-grind (#57) → bokför session (#58) → gatead draft-PR. **Crawl:** varje muterande steg passerar en injicerad `approve(action, ctx)`-callback (default `deny_all`); lease + worktree släpps alltid (orphan-cleanup); `should_abort` = kill-switch. **Ärlighetsgrindar (efter #95-felsöket):** routar `role_fn` ingen roll → `blocked` (kör inget meningslöst generiskt pass); ett pass med tom output rapporteras som "tomt pass" och markeras **inte** `done`. **Dispatch känner medvetet INTE nodmodellens filform** — den litar på `role_for_node`-seamet, så CNS kan byggas om utan att röra loopen. **Två pass-lägen styrt av `worktree_fn`:** default `None` = **read-first**-förslag (passet skriver inget); satt = **skriv-läge** — passet kör med skrivrätt i en isolerad git-worktree (`scripts/worktree.py`: `dispatch/issue-<n>`-branch), ändringarna committas, och `open_pr_fn` öppnar en **draft**-PR + required reviewer (`scripts/prs_client.py`). Skriv-läget passerar **skrivtröskeln** men **inte** autonomitröskeln. **Fas 5 (autonomi, #61 + #60 merge-policy):** `autonomy=True` (CLI `--autonomy`, kräver `--write`) låter loopen self-merga — men **bara LÅGRISK** via `classify_risk` (positiv allowlist: docs/deps/tooling/tester); feature-kod (scripts/app), schema/connector (`schemas/`, `app/tools/`, `enums.json`), produktion, eval-fall och tomma pass **eskaleras** (status `escalated`, draft lämnas). Av som default = crawl orört. CLI: `python -m scripts.dispatch [--write] [--autonomy] [--yes]`. Komponerar bara befintliga primitiver. Ren/injicerbar — testad utan GitHub/Redis/LLM/SDK/git i `tests/test_dispatch.py` (+ `tests/test_worktree.py` mot riktigt git). Designval: lokal `agent_host` framför @claude-molntransport (roll-medvetenhet finns lokalt). Spec: `plans/autonom-agentur-byggordning.md` (Fas 3).
- `scripts/prs_client.py` — **PR-klient** (plain REST, samma split som `issues_client` ↔ `app/tools/issues.py`): `list_prs`/`get_pr`/`create_pr(draft=…)`/`set_reviewers`. Logiken lyftes hit ur `app/tools/prs.py` (som nu är tunna wrappers som delegerar) så dispatch-loopen kan öppna draft-PR utan MCP-servern. Connector-namnen `cortxt_*` oförändrade.
- `scripts/worktree.py` — **git-worktree-isolering** för skrivande dispatch-pass (#59): `prepare`/`commit_all`/`push`/`cleanup` (subprocess runt `git worktree`). Worktrees bor som syskon till repo-roten (`../.cns-dispatch-worktrees/`, ej nästlat). `cleanup` tar bort worktree:t men behåller branchen (committat arbete överlever). Degraderar via `WorktreeError` om git/remote saknas.
- `scripts/recommend.py` — **sessionsrekommendationer**: regelbaserat lager ovanpå datalagret. Ger `--json` (för `/sessions`-skillen) och `--statusline` (Claude Codes statusrad). Rekommenderar en av de **standardiserade sessionstyperna** i `sessions/profiles/<typ>.md` (brainstorm | spec | bygg | triage | review — profil per typ; `/session <typ>` läser profilen och ställer om beteendet, bokför via `cortxt_start_session`). Rent datalager-konsument, pushar inget.
- `scripts/git_ops.py` — direkt GitHub API-push
- `app/server.py` — Flask-backend (Railway)
- `app/mcp_server.py` — MCP-server (FastMCP, GitHub OAuth, Redis token-store). Äger auth + allowlist + `mcp`-instansen; verktygen själva bor i `app/tools/` (`issues`/`quests`/`ideas`/`projects`/`sessions`, var sin `register(mcp)`).
- `app/asgi.py` — ASGI-entrypoint. **FastMCP är yttersta appen** och äger `/mcp` + OAuth-routes (`/.well-known/...`, `/authorize`, `/token`); Flask monteras *inuti* via `a2wsgi` som fallthrough (WSGI kan inte hålla ASGI, därför denna riktning). Kör med uvicorn-worker, inte sync-gunicorn. `/mcp` exponeras bara när OAuth är konfigurerat (annars 503) — annars vore en data-muterande endpoint öppen.
- `schemas/catalog_schema.json` — strukturschema för `catalog.yaml`. (`node_schema.json` = död rest från node.md-eran, kvar tills AI-redigeringsvägen rewiras.)
- `skills/` — portabla konventioner: `cortxt-quests` (quest/issue-arbetsflöde), `cns-flush` (spola ner en sessions slutsats i CNS via `cortxt_save_session`), `cns-sync` (read-only överlappsdetektering av parallella sessioner via `cortxt_list_sessions(link_ref=…)`, körs före flush), `cns-fork` (bokför en fork i sessionsträdet via `cortxt_fork_session`).
- `scripts/tui/` — interaktiv terminal-överblick (textual). **Isolerad:** konsumerar bara datalagret (`read_all_nodes`), rör inte `cns.py`. Körs via `python -m scripts.tui` eller `cns tui` (lazy import — `textual` laddas inte vid varje `cns`-anrop). Beroende: `textual>=0.79,<1.0`.
  - `scripts/tui/agent_host.py` — **agent-host** (tangent `c` i TUI:t): driver Claude lokalt via **Claude Agent SDK** (`claude-agent-sdk`, valfritt extra i `requirements-agent.txt`), exponerar datalagret som in-process MCP-verktyg (`create_sdk_mcp_server` + `@tool`), read-first (`can_use_tool` nekar Write/Edit/Bash). Auth: env `ANTHROPIC_API_KEY` → otrackad `.cns-agent-key` → annars Claude Code-login. Rör inte `app/mcp_server.py`.
- `.mcp.json` — MCP-router (config), se "Agenter, verktygslåda & minne" nedan.
- `.claude/` — verktygslådan (Plan A), versionerad. Egen `README.md`.
- `agents/` — produktens agenter (Plan B), tom tills en verklig agent kräver det.

## Agenter, verktygslåda & minne (två plan)
Två skilda plan med **hård vägg emellan** — produktkod importerar aldrig från `.claude/`, och `.claude/` är aldrig ett produktberoende.
- **Plan A — verktygslådan (`.claude/`, versionerad här):** subagenter (`.claude/agents/`), egna skills (`.claude/skills/`), slash-kommandon (`.claude/commands/`), delade permissions (`.claude/settings.json`). Detta är hur *vi* driver portföljen, inte produkten. Arbetsytans `.claude/` är maskinlokal och oversionerad — lägg inget varaktigt där utom btw-Stop-hooken som redan bor i arbetsytans `settings.json`.
- **Plan B — produktens agenter (`agents/`):** om Cortxt själv ska köra agenter åt slutanvändare bor de här som produktkod, bredvid `app/` och `scripts/`. Tom tills en verklig agent kräver det.
- **MCP-router:** `.mcp.json` (versionerad) listar MCP-servrarna agenterna når — i dag bara `project-cns`. Detta *är* routern nu (config-router). En separat gateway-process är inritad som idé-noden `mcp-gateway` (`depends_on: cns-mcp`) och byggs först när Plan B-agenter når många servrar.
- **MCP-verktyg bor i `app/tools/`:** en domänmodul per område, var och en med `register(mcp)`. `app/mcp_server.py` äger bara auth, allowlist-middleware och `mcp`-instansen och anropar varje moduls `register`. Nya verktyg läggs som en `@mcp.tool` i rätt modul (eller en ny modul), mot `scripts/`-datalagret — **inte** som fler dekoratörer i `mcp_server.py`. Verktygsnamnen är connector-kontrakt mot claude.ai och måste vara stabila vid flytt mellan moduler.
  - CNS-data: `issues` / `quests` / `ideas` / `projects` (noder) / `sessions`
  - GitHub-ytor: `prs` (Pull Requests) / `gh_projects` (Projects v2 GraphQL) / `actions` (workflow_dispatch + run-status) / `wiki` (Contents API mot `{repo}.wiki`)
  - Extern integration: `linear` (Linear REST+GraphQL, kräver `LINEAR_API_KEY`)

### Fyra minneslager (förväxla inte)
- **Claude-minne** (`~/.claude/projects/.../memory/`) — hur Claude ska jobba med dig. Personligt, Plan A.
- **Sessionsminne** — `exports/btw/` (btw-asides per session) **och** `exports/sessions/` (`session_store.py`, AI-arbetspass som förstklassiga objekt). Arbetstillstånd, ej kunskap.
- **Kunskap/wiki** (`catalog.yaml` + `decisions/<slug>.md`) — varaktig portföljkunskap, produktens sanning. `.qoder/repowiki/` är verktygsgenererat och räknas inte.
En agent som lär sig något *bestående om portföljens struktur* uppdaterar `catalog.yaml`; en *varaktig beslutskunskap* → `decisions/<slug>.md`; något *om sessionen/arbetspasset* → btw/sessions; något *om hur Claude ska bete sig* → Claude-minnet.

## Deploy & dataflöde
- GitHub = sanning. AI-genererat innehåll pushas via **direkt GitHub API** (`git_ops.py`), inte till Railways efemära disk.
- Backend på Railway: `https://project-cns-production.up.railway.app`. `/api/nodes` kör `export_json()` mot den kod/de noder som checkades ut **vid deploy-tillfället**. OBS: `git_pull()` i `app/git_ops.py` är en **no-op** (`return True, "ok"`) — backenden pullar *inte* vid runtime. Färskheten beror helt på att **Railway auto-redeployar** vid push till main. Syns inte en ändring i dashboarden trots att den ligger på main ⇒ Railway har inte redeployat (kolla Deployments-loggen).
- Dashboarden (separat `cortxt`-repo på Vercel) proxar `/api/*` hit via sin `vercel.json`.
- **Ett system är inte "tillagt" förrän `catalog.yaml` är committad, pushad OCH exporterad.** Nya filer (t.ex. `decisions/<slug>.md`) måste `git add`:as explicit — `git commit -am` missar otrackade filer.

## GitHub-interaktion
Tre kanaler, lätta att förväxla: inkommande webhooks (GitHub → Flask, quest-transitioner), utgående skrivningar (Contents API via `git_ops.py`, **inte** `git`-subprocess), pollande läsning (`eventstream.py`) och GitHub Actions (`export-dashboard.yml`). **Detaljer + sekvensdiagram:** `.claude/rules/github-interaction.md` (path-scopad, laddas on-demand när du rör `app/`, `git_ops.py`, `eventstream.py` eller `.github/workflows/`).

## Enums
**Enkälla: `schemas/enums.json`** — läses av `scripts/validator.py` (Python, som `set`; därifrån importerar analyst.py/server.py) och av `cortxt/packages/cns-schema` (JS, genererad via dess `generate.mjs`). Ändra värden där, inte handkodat. Lägg INTE in layer/pipeline/family (legacy, ovaliderade — kvar som referens i validator.py).
- kind: component | system | framework — **härleds ur `part_of`, lagras inte** (se `catalog.derive_kind`)
- type: frontend | service | mcp-server | pipeline | cli | tool | agent | infra | library | dataset | ai-model — driver agent-routing
- domain: cortxt | shopify-venture
- **delegerade till board (ej i katalogen):** status, stage, mvp_stage, risk_category. Enum-värdena ligger kvar i `enums.json` som referens tills board-integrationen (#102) landar; de validerar inget i katalogen.

## Begreppsmodell (branschstandard-mappning)
CNS-termerna mappar mot branschstandard (granskad spec: `plans/work-model-taxonomy-spec.md`). Standardtermen är vokabulär i dok/prompter; **MCP-verktygsnamn (`cortxt_*`) är connector-kontrakt och behålls oförändrade** — ny standardterm exponeras vid behov som alias, inte som hård rename.

### Ordlista — EN kanonisk term per koncept

| CNS-term | Kanonisk term | Alias / synonymer |
|----------|---------------|-------------------|
| system (`catalog.yaml`-post) | **component** | nod, node, project |
| idé | **opportunity** | idea |
| quest | **epic** | GitHub Milestone, milestone |
| issue | **story** | bug, spike, chore (via `type`-fält) |
| todo | **sub-task** | task-list-checkbox |
| session | **run** | arbetspass |

Valfri toppnivå **initiative** över epic. `issue_type`-enkälla: `VALID_ISSUE_TYPES` i `issues_client.py` (inte `enums.json` — issues schemavalideras inte).

### CNS · cortxt · Cortxt — tre distinkta begrepp
- **CNS** = hjärnan/datalagret — repo `Project-CNS`, Python-backend, nodmodellen.
- **cortxt** = ansiktet/dashboarden — repo `cortxt`, React-frontend på Vercel.
- **Cortxt** = produkten som helhet (båda repona tillsammans).

### Nummer-konvention
GitHub delar EN räknare för issues och PR:er — samma siffra kan vara en issue eller en PR. Skriv **alltid** typen före numret: `issue #39`, `PR #50`, `epic #8`. Aldrig bara `#39`.

## Automatisk agent-routing
Routing sker via hooken `scripts/router.py` (UserPromptSubmit): den injicerar `[ROUTING] @agent → reason` + `[MODEL: X]` per prompt ur `ROUTING_RULES` (nyckelordsmatchning) och den genererade `agent_registry` (modellnivå/avdelning ur agent-frontmatter). **Regel: när `[ROUTING]` syns, delegera direkt — anropa Agent-verktyget med `subagent_type="<agent-slug>"`, `model="X"` (från `[MODEL: X]`) och hela originaluppgiften; fråga inte Rikard.** Konversationella frågor och prompts utan träff hanteras direkt.

Agenturens fulla roster: `.claude/agents/AGENTUR.md` (**genererad** av `gen_agentur.py` ur frontmatter — redigera inte för hand). **Lägg/ändra routing i `router.py`, inte här** — en handhållen tabell driver isär från hooken.

## Arbetsregler
- **Spec först:** skriv/granska en implementationsspec innan kod. Vid osäkerhet — ställ frågan i specen så den måste besvaras.
- **Additiv migrering:** nya fält är valfria; migrera en nod i taget; behåll fallback på gamla fält så dashboarden inte bryts.
- **Övergeneralisera inte mallar:** inga mallvarianter förrän en verklig nod kräver det.
- Validera (`cns validate <slug>`) innan commit — särskilt handskrivna noder.
- AI-funktioner (analyze, suggest-quest, brief, devlog) kräver `ANTHROPIC_API_KEY` satt på Railway.
- **`cortxt_mark_session_done` kräver explicit done-checklista:** (1) ursprungsuppgiften är levererad, (2) kod är committad och pushad om kodändringar gjordes, (3) öppna delfrågor är fångade som idéer/todos. Anropa aldrig done om någon av dessa inte stämmer.

## Underhåll av denna fil
Denna fil läses in varje session och är din primära kontext. **Uppdatera den i samma ändring som du ändrar något den beskriver** — arkitektur, dataflöde, repo-layout, konventioner, nya/omdöpta noder, eller en gotcha du snubblat på. Håll den koncis och högsignalerad: det här är inte fullständig dokumentation, utan det du behöver för att inte göra fel. Låter du den driva börjar varje framtida session från felaktiga antaganden.
