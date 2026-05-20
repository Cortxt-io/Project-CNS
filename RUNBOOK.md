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
