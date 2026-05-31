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

## API-nycklar

CNS läser API-nycklar från miljön (via `python-dotenv`) — de finns aldrig i koden.

| Nyckel | Driver | Krävs för |
|--------|--------|-----------|
| `ANTHROPIC_API_KEY` | Anthropic Claude | `cns analyze` (CNS Analyst), devlog AI-sammanfattningar |
| `PERPLEXITY_API_KEY` | Perplexity | `cns update --mode api` (lokalt/connector-läge kräver ingen nyckel) |

### Lokalt
```bash
cp .env.example .env
# Fyll i nycklarna i .env (filen är gitignorad — läcker aldrig till repot)
```

### Railway (produktion)
Service → fliken **Variables** → lägg till `ANTHROPIC_API_KEY=...` (samma ställe som `CNS_WEBHOOK_SECRET`).

### Claude Code on the web
Moln-ikonen (miljönamnet) → **Edit environment** (eller **Add environment** om ingen finns) →
fältet **Environment variables**. Format: `.env`, en `KEY=value` per rad, **inga citattecken**:
```
ANTHROPIC_API_KEY=...
```
- `api.anthropic.com` ligger redan på default-allowlistan (**Trusted**), så ingen extra
  network-config behövs.
- **OBS:** web-miljöns env-variabler är inte en säker secret-store — de lagras i klartext,
  synliga för alla som kan redigera miljön. Använd helst en nyckel med begränsad budget/scope.
- Görs i webbläsaren (claude.ai/code), inte i mobilappen.

Verifiera med `python cns.py doctor`.

---

## MCP Server Setup

### Lokal användning (Claude Desktop / Qoder)

1. Installera dependencies: `pip install -r requirements.txt`
2. Lägg till i Claude Desktop config (~/.claude/claude_desktop_config.json):
```json
{
  "mcpServers": {
    "cortxt": {
      "command": "python",
      "args": ["C:/Users/rikar/OneDrive/prompt-cns/app/mcp_server.py"]
    }
  }
}
```
3. Starta om Claude Desktop
4. Tools tillgängliga: cortxt_list_active_quests, cortxt_get_quest, cortxt_complete_quest, cortxt_list_projects, cortxt_get_project

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
