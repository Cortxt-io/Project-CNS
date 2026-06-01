# Runbook — CLI-kommandon for aktiva projekt

Snabbreferens for att kora de fyra aktiva projekten fran terminalen.
Alla sokvagar ar relativa till `prompt-cns/`.

---

## 1. CNS (Central Node Store)

Portfoljohanteraren. Rot: `prompt-cns/`

```bash
# Miljokontroll
python cns.py doctor

# Lista alla projekt
python cns.py list

# Visa ett projekt
python cns.py show <slug>

# Skapa nytt projekt
python cns.py new <slug>

# Uppdatera lokalt (interaktivt)
python cns.py update <slug>

# Uppdatera via API
python cns.py update <slug> --mode api --instruction "..."

# Generera connector-brief (for Perplexity/Spaces)
python cns.py prepare <slug>

# Exportera jamforelsekalkylblad
python cns.py export xlsx

# Quest-workflow (aktivt bygge)
python cns.py quest init <slug>
python cns.py quest show <slug>
python cns.py quest sync <slug>
```

---

## 2. DocsWatch

Overvakar docs/changelogs for meningsfulla forandringar. Rot: `projects/docs-watch/`

```bash
cd projects/docs-watch

# Standardkorning (hamtar, diffar, genererar sajt)
python -m src.cli

# Med annan config-fil
python -m src.cli --config my_urls.yaml

# Verbose (visa aven brusfiltrerade diffar)
python -m src.cli --verbose

# Annan datakatalog
python -m src.cli --data-dir ./store

# Regenerera statisk sajt utan ny hamtning
python -m src.cli --generate-site

# Exportera events (for changelog-engine)
python -m src.cli events-export --from 2026-05-04 --to 2026-05-11

# Markera som granskad
python -m src.cli mark-reviewed --run <run_id> --site <site-slug>

# Visa granskningsstatus
python -m src.cli review-status --run <run_id>

# Oppna rapportsajten (Windows)
start data/site/index.html
```

---

## 3. dev-changelog-engine-mini

Genererar poangberaknade veckodigest fran DocsWatch-events. Rot: `projects/dev-changelog-engine-mini/`

```bash
cd projects/dev-changelog-engine-mini

# Installera beroenden
npm install

# Auto-detect: generera alla dag/vecko/manadsrapporter fran events i en korning
npm run digest -- --source json --input ..\docs-watch\exports\events-<from>-to-<to>.json --auto-detect

# Auto-detect med AI-sammanfattningar (Ollama)
npm run digest -- --source json --input ..\docs-watch\exports\events-<from>-to-<to>.json --auto-detect --summarize

# Bara vecko- och manadsrapporter (utan dagliga)
npm run digest -- --source json --input ..\docs-watch\exports\events-<from>-to-<to>.json --auto-detect --periods week,month

# Manuellt specificerad period (gammalt satt)
npm run digest -- --period week --date 2026-W19 --source json --input ..\docs-watch\exports\events-<from>-to-<to>.json

# Bygg statisk sajt for publicering
npm run build-site

# Forhandsgranska lokalt
npx serve dist/
```

---

## 4. Project Vault Dashboard

Visuell portfoljoversikt over alla CNS-projekt. Rot: `projects/project-vault-dashboard/dashboard/`

```bash
# Uppdatera projektdata (fran prompt-cns-roten)
python cns.py export json --output projects/project-vault-dashboard/dashboard/data/projects.json

# Starta lokal server och oppna dashboarden
npx serve projects/project-vault-dashboard/dashboard -l 3000
# Oppna sedan http://localhost:3000 i webblasaren
```

OBS: Dashboarden kraver en lokal server (`file://` blockerar fetch av JSON).
Kor `export json` igen nar du andrat projekt via CNS for att synka datan.

---

## MCP Server Setup

MCP-servern (`app/mcp_server.py`) körs i två lägen: **remote Streamable HTTP**
på Railway (huvudleveransen, nåbar från telefon/web via claude.ai) och **lokal
stdio** som fallback för Claude Desktop. Samma 5 tools i båda:
`cortxt_list_active_quests`, `cortxt_get_quest`, `cortxt_complete_quest`,
`cortxt_list_projects`, `cortxt_get_project`.

### Remote (claude.ai Custom Connector) – huvudleverans

MCP-servern monteras i den befintliga appen via ASGI (`app/asgi.py`) och nås på
`https://<railway-domän>/mcp`. Den körs alltså under **samma domän** som
REST-API:t, men servern startas som ASGI (uvicorn-worker), inte sync-WSGI.

**Auth (viktigt):** claude.ai:s connector-UI stödjer **bara OAuth** — det finns
inget fält för statisk Bearer-token eller egna headers. Därför skyddas `/mcp`
med ett **OAuth-flöde**, INTE `CNS_API_TOKEN` (som fortsatt gäller för resten av
API:t). Vi använder FastMCP:s GitHub-provider, som sköter den OAuth-metadata +
Dynamic Client Registration som claude.ai kräver.

**Engångssetup – GitHub OAuth-app:**
1. GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
   - **Homepage URL:** `https://<railway-domän>`
   - **Authorization callback URL:** `https://<railway-domän>/auth/callback`
2. Sätt env-vars i Railway (service → Variables):
   ```
   MCP_GITHUB_CLIENT_ID=<client id>
   MCP_GITHUB_CLIENT_SECRET=<client secret>
   MCP_BASE_URL=https://<railway-domän>
   ```
   Saknas dessa startar servern **utan auth** (endast avsett för lokal dev).
3. Deploya. Verifiera att `https://<railway-domän>/mcp` svarar `401` med en
   `WWW-Authenticate`-header (pekar på OAuth-metadata) innan inloggning.

**Lägg till i claude.ai:**
1. Settings → Connectors → **Add custom connector**
2. URL: `https://<railway-domän>/mcp`
3. Genomför GitHub-inloggningen (OAuth). De 5 verktygen ska nu listas.
4. Testa från en konversation (även på telefon): "lista mina CNS-projekt" →
   `cortxt_list_projects`.

> **⚠️ Härda innan du litar på den:** GitHub-providern släpper in *vilken*
> GitHub-användare som helst som loggar in — och `cortxt_complete_quest`
> muterar data och pushar till GitHub. Innan servern exponeras på riktigt,
> begränsa åtkomsten till din egen GitHub-användare (t.ex. en
> allowlist-middleware på `mcp` som matchar inloggat användarnamn).

### Lokal användning (Claude Desktop, stdio-fallback)

1. Installera dependencies: `pip install -r requirements.txt`
2. Lägg till i Claude Desktop config (~/.claude/claude_desktop_config.json):
```json
{
  "mcpServers": {
    "cortxt": {
      "command": "python",
      "args": ["<absolut sökväg>/app/mcp_server.py"]
    }
  }
}
```
   (Utan OAuth-env-vars kör `mcp_server.py` stdio-transporten oförändrad.)
3. Starta om Claude Desktop.

---

## GitHub Webhook Setup

CNS-servern tar emot GitHub-webhooks på `POST /api/webhook/github` och uppdaterar
quests automatiskt utifrån vad som händer i kopplade repos.

### Setup

1. Sätt env-var i Railway:
   ```
   CNS_WEBHOOK_SECRET=<din hemlighet>
   ```
2. GitHub → repo → Settings → Webhooks → Add webhook:
   - **Payload URL:** `https://project-cns-production.up.railway.app/api/webhook/github`
   - **Content type:** `application/json`
   - **Secret:** samma som `CNS_WEBHOOK_SECRET`
   - **Which events?** → "Let me select individual events" och bocka i:
     - **Push** – auto-completar quests vars projektfiler ändrats
     - **Pull requests** – startar/avslutar quests vid PR-händelser
     - **Workflow runs** – sätter CI-status (grön/röd) på quests

### Hanterade events

| Event | Trigger | Effekt på quest |
|-------|---------|-----------------|
| `push` | Commits pushade | Filer under `projects/<slug>/` → matchande `in_progress`-quests blir `completed` |
| `pull_request` (opened/reopened) | PR öppnad | `active`-quests vars slug nämns i PR-titel/body/branch → `in_progress` |
| `pull_request` (closed + merged) | PR merge:ad | Matchande `in_progress`-quests → `completed` |
| `workflow_run` (completed) | CI-körning klar | `ci_status` sätts till `passing`/`failing` på matchande `in_progress`-quests |

**Slug-matchning:** `push` matchar via filsökväg (`projects/<slug>/...`). `pull_request`
och `workflow_run` saknar fillista i sin payload — de matchar istället quests vars
`slug` nämns som text i PR-titel/body/branch respektive workflow-titel/branch.

---

## Typiskt arbetsflode (alla fyra)

```bash
# 1. Kor DocsWatch for att hamta senaste andringar
cd projects/docs-watch
python -m src.cli

# 2. Exportera events for veckan
python -m src.cli events-export --from 2026-05-05 --to 2026-05-11

# 3. Generera alla digests automatiskt med Engine
cd ../dev-changelog-engine-mini
npm run digest -- --source json --input ..\docs-watch\exports\events-2026-05-05-to-2026-05-14.json --auto-detect

# 4. Bygg statisk sajt
npm run build-site

# 5. Uppdatera dashboard-datan
cd ../..
python cns.py export json --output projects/project-vault-dashboard/dashboard/data/projects.json

# 6. Starta dashboard-server
npx serve projects/project-vault-dashboard/dashboard -l 3000
# Oppna http://localhost:3000
```
