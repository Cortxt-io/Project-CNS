# Org-bootstrap + cookbook (PLANERAD — bygg senare)

**Status:** spec fångad 2026-06-14, ej byggd. Prioritet: efter att taxonomi-skelettets återstod
(forward-wiring, Fas 2) känns klar — detta är återanvändnings-payoff, inte blockerande.

## Context / mål
Idag sattes CNS:s GitHub-projektion upp **manuellt** (org-Project, Initiative-fält + options,
Status-options, `CNS_PROJECT_URL`-variabel, token-permissions). Det var f-igt och odokumenterat.
Mål: göra uppsättningen **återanvändbar** — Rikard (eller någon som forkar CNS och vill köra eget,
ev. med annat arbetssätt) ska kunna resa hela GitHub-projektionen i en ny org med ~ett kommando +
en kort checklista, istället för att klicka/gissa. Detta är payoffen av att kärnan hölls tunn och
projektionen deklarativ (`scripts/projections.py`).

**Princip (jfr [[inte-jira-klon]]):** bootstrap sätter upp GitHubs egna ytor (Project/fält/Actions).
Den bygger ingen CNS-board. "Arbeta annorlunda" = ändra config, inte kod.

## Deliverables
1. **`scripts/bootstrap_org_project.py`** — idempotent. Kodifierar dagens manuella GraphQL:
   - skapa org-Project v2 (om saknas; annars hitta på titel/number)
   - skapa/normalisera **Initiative** single-select-fält + options
   - normalisera **Status**-options till CNS-flödet (Backlog/Definition/Delivery/Review/Done)
   - sätt Actions-variabeln `CNS_PROJECT_URL`
   - **Idempotent-krav:** läs befintliga fält/options FÖRST; lägg bara till saknade. Skriv ALDRIG
     blint `updateProjectV2Field` (replace-semantik nollställer items värden — den fällan vi mötte).
   - Input: org-login + token (env). Återanvänder `gh_project_sync`/`gh_project_core`-mönstren.
2. **`config/project_schema.yaml`** — deklarativ fält/options/vy-definition (kunde-vara-mall).
   Bootstrap läser denna. **Detta är fork-sömmen:** en fork ändrar schemat (andra initiativ, andra
   status-stationer) utan att röra kod. Hänger ihop med `projections.py`.
3. **`docs/SETUP.md`** (cookbook) — stegen vi snubblade på, dokumenterade en gång:
   - skapa GitHub-org
   - skapa fine-grained PAT: **resource owner = org**, Organization→Projects: Read and write
     (+ repo-perms Contents/Issues/PRs/Metadata för runtime). Vanligaste fällan: token ägd av
     personligt konto kan aldrig få org-Project-write.
   - kör `bootstrap_org_project.py`
   - sätt secret `CNS_GITHUB_TOKEN` (org-token) + variabeln `CNS_PROJECT_URL`
   - Actions-automationen är redan kod (`.github/workflows/project-*.yml`) — fork ärver den
   - bygg vyerna i UI (Flow/Portfolio/All) eller klona en mall via `copyProjectV2`

## Kända begränsningar (att dokumentera i cookbooken)
- **Vyer + inbyggda Project-workflows kan inte skapas via API** (UI-only). Automation görs som
  **GitHub Actions** istället (redan byggt: `project-add-to-project.yml`, `project-status-done.yml`).
  Vyer: UI eller `copyProjectV2` från en mall-projekt.
- `updateProjectV2Field` ersätter HELA options-listan → bootstrap måste vara additiv/idempotent.
- Node-IDs är opaka → resolva på namn (som `gh_project_sync` redan gör).

## Verifiering
- Kör bootstrap mot en TOM testorg → org-Project med rätt fält/options + variabel satt.
- Kör igen → idempotent (inga dubbletter, inga nollställda värden).
- Öppna en testissue → auto-add-workflow lägger den; stäng → status→Done.

## Relaterat
- `plans/taxonomy-mirror-skeleton.md` (projektionen som bootstrappen reser)
- `scripts/projections.py`, `scripts/gh_project_sync.py` (återanvänds)
- `.github/workflows/project-add-to-project.yml`, `project-status-done.yml` (redan byggd automation)
