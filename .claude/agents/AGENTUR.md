# AGENTUR.md — org-schema (Plan A) — GENERERAD

> Genererad av `scripts/gen_agentur.py` ur agent-frontmatter. **Redigera inte för hand** —
> ändra rollerna i `.claude/agents/*.md` (aktiva) / `.claude/org/roster/*.md` (skal) och kör om.

**88 roller** i registret, varav **27 aktiva** (körbara i `.claude/agents/`).
Resten är skal i org-registret (`.claude/org/roster/`) — bemannas vid behov.

Princip: agenter = anställda, skills = kompetenser. Matris (Spotify): department +
sub_department (linjen) × squad (mission) × chapter (disciplin) × guild (skills `Gemensam`).

Aktiva rostern hålls liten (playbook: 7–10 aktiva åt gången). VD = Rikard (ej agentfil).

## Ledning

### Exec

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `operativ-chef` | Operativ chef (COO) | opus-4-8 | lead | — | aktiv |
| `produktdirektor` | Produktdirektör (CPO) | opus-4-8 | lead | — | skal |
| `stabschef` | Stabschef (Chief of Staff) | sonnet-4-6 | lead | — | aktiv |
| `strategichef` | Strategichef | opus-4-8 | lead | — | skal |
| `teknisk-direktor` | Teknisk direktör (CTO) | opus-4-8 | lead | — | aktiv |

## Produkt

### Arkitektur

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `losningsarkitekt` | Lösningsarkitekt | sonnet-4-6 | — | — | aktiv |

### PM

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `produktchef` | Produktchef | haiku-4-5 | lead | — | aktiv |
| `produktledare-core` | Produktledare CNS-core | sonnet-4-6 | — | Modellering | skal |
| `produktledare-dashboard` | Produktledare Dashboard | sonnet-4-6 | — | Insikter | skal |
| `produktledare-mcp` | Produktledare MCP-plattform | sonnet-4-6 | — | Integrationer | skal |
| `produktledare-tui` | Produktledare TUI | sonnet-4-6 | — | Överblick | skal |

### Design

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `ux-lead` | UX-lead | sonnet-4-6 | lead | — | skal |
| `interaktionsdesigner` | Interaktionsdesigner | sonnet-4-6 | — | — | skal |
| `ux-designer` | UX-designer | sonnet-4-6 | — | — | skal |
| `ux-researcher` | UX-researcher | sonnet-4-6 | — | — | skal |

### ProductOps

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `product-ops` | Product Ops | haiku-4-5 | — | — | skal |
| `produktanalytiker` | Produktanalytiker | haiku-4-5 | — | — | skal |

## R&D

### Research

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `forskningsledare` | Forskningsledare | sonnet-4-6 | lead | — | aktiv |
| `konkurrentanalytiker` | Konkurrentanalytiker | sonnet-4-6 | — | — | skal |
| `marknadsanalytiker` | Marknadsanalytiker | sonnet-4-6 | — | — | skal |
| `teknikspanare` | Teknikspanare | sonnet-4-6 | — | — | skal |
| `webbresearcher` | Webbresearcher | haiku-4-5 | — | — | skal |

### Innovation

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `innovationsledare` | Innovationsledare | sonnet-4-6 | lead | — | skal |
| `datavetare` | Datavetare | sonnet-4-6 | — | — | skal |
| `prototypare` | Prototypare | sonnet-4-6 | — | — | skal |

## Engineering

### Backend

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `backend-lead` | Backend-lead | sonnet-4-6 | lead | — | skal |
| `backend-utvecklare` | Backend-utvecklare | sonnet-4-6 | — | Integrationer | aktiv |
| `backend-utvecklare-2` | Backend-utvecklare | haiku-4-5 | — | — | skal |
| `backend-utvecklare-3` | Backend-utvecklare | haiku-4-5 | — | — | skal |
| `backend-utvecklare-4` | Backend-utvecklare | haiku-4-5 | — | — | skal |

### DevOps

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `devops-ingenjor` | DevOps-ingenjör | haiku-4-5 | — | — | aktiv |

### Frontend

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `frontend-lead` | Frontend-lead | sonnet-4-6 | lead | — | skal |
| `frontend-utvecklare` | Frontend-utvecklare | sonnet-4-6 | — | Insikter | aktiv |
| `frontend-utvecklare-2` | Frontend-utvecklare | haiku-4-5 | — | — | skal |
| `frontend-utvecklare-3` | Frontend-utvecklare | haiku-4-5 | — | — | skal |
| `terminal-utvecklare` | Terminal-UI-utvecklare | sonnet-4-6 | — | Överblick | aktiv |
| `terminal-utvecklare-2` | Terminal-UI-utvecklare | haiku-4-5 | — | Överblick | skal |

### Fullstack

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `fullstack-utvecklare` | Fullstack-utvecklare | sonnet-4-6 | — | — | aktiv |
| `fullstack-utvecklare-2` | Fullstack-utvecklare | haiku-4-5 | — | — | skal |

### Integrations

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `integrationsutvecklare` | Integrationsutvecklare | sonnet-4-6 | — | — | aktiv |
| `integrationsutvecklare-2` | Integrationsutvecklare | haiku-4-5 | — | — | skal |

### QA

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `qa-lead` | QA-lead | sonnet-4-6 | lead | — | aktiv |
| `testautomatiserare` | Testautomatiserare | haiku-4-5 | — | — | skal |
| `testautomatiserare-2` | Testautomatiserare | haiku-4-5 | — | — | skal |
| `testautomatiserare-3` | Testautomatiserare | haiku-4-5 | — | — | skal |

### Data

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `data-ingenjor` | Data-ingenjör | sonnet-4-6 | — | — | skal |
| `data-ingenjor-2` | Data-ingenjör | haiku-4-5 | — | — | skal |

## Platform

### Infra

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `plattformschef` | Plattformschef | sonnet-4-6 | lead | — | aktiv |
| `plattformsingenjor` | Plattformsingenjör | sonnet-4-6 | — | — | aktiv |
| `plattformsingenjor-2` | Plattformsingenjör | haiku-4-5 | — | — | skal |

### DevEx

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `build-ingenjor` | Build-ingenjör | haiku-4-5 | — | — | skal |
| `devex-ingenjor` | Developer-Experience-ingenjör | sonnet-4-6 | — | — | skal |

### DevOps

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `devops-ingenjor-2` | DevOps-ingenjör | haiku-4-5 | — | — | skal |

## People

### Talent

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `hr-chef` | HR-chef (CHRO) | sonnet-4-6 | lead | — | aktiv |
| `rekryterare` | Rekryterare | sonnet-4-6 | — | — | skal |
| `rekryterare-2` | Rekryterare | haiku-4-5 | — | — | skal |

### L&D

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `kompetensutvecklare` | Kompetensutvecklare (L&D) | sonnet-4-6 | — | — | aktiv |
| `kompetensutvecklare-2` | Kompetensutvecklare | sonnet-4-6 | — | — | skal |

### Org Design

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `org-arkitekt` | Organisationsarkitekt | sonnet-4-6 | lead | — | aktiv |

### Culture

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `kulturansvarig` | Kulturansvarig | sonnet-4-6 | — | — | skal |

## Program

### Coaching

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `agile-coach` | Agile Coach | sonnet-4-6 | — | — | aktiv |

### Delivery

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `programledare` | Programledare | sonnet-4-6 | lead | — | aktiv |
| `scrum-master` | Scrum Master | haiku-4-5 | — | — | skal |
| `scrum-master-2` | Scrum Master | haiku-4-5 | — | — | skal |

### Coordination

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `sessionskoordinator` | Sessionskoordinator | haiku-4-5 | — | — | aktiv |
| `sessionskoordinator-2` | Sessionskoordinator | haiku-4-5 | — | — | skal |

### Release

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `leveranschef` | Leveranschef | sonnet-4-6 | lead | — | skal |
| `release-koordinator` | Release-koordinator | haiku-4-5 | — | — | skal |

## Drift

### SRE

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `driftchef` | Driftchef | sonnet-4-6 | lead | — | aktiv |
| `sre-ingenjor` | SRE-ingenjör | sonnet-4-6 | — | — | skal |
| `sre-ingenjor-2` | SRE-ingenjör | haiku-4-5 | — | — | skal |

### Monitoring

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `lagesanalytiker` | Lägesanalytiker | haiku-4-5 | — | — | aktiv |
| `overvakningsanalytiker` | Övervakningsanalytiker | haiku-4-5 | — | — | skal |

### Maintenance

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `underhallsingenjor` | Underhållsingenjör | sonnet-4-6 | — | — | aktiv |
| `underhallsingenjor-2` | Underhållsingenjör | haiku-4-5 | — | — | skal |

### Incident

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `incidentledare` | Incidentledare | sonnet-4-6 | lead | — | skal |

## Ekonomi

### Controlling

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `ekonomichef` | Ekonomichef (CFO) | haiku-4-5 | lead | — | aktiv |
| `controller` | Controller | haiku-4-5 | — | — | skal |

### FinOps

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `faktureringsansvarig` | Faktureringsansvarig | haiku-4-5 | — | — | skal |
| `finops-analytiker` | FinOps-analytiker | haiku-4-5 | — | — | skal |
| `inkop` | Inköpsansvarig | haiku-4-5 | — | — | skal |

## Kommunikation

### Docs

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `kommunikationschef` | Kommunikationschef | sonnet-4-6 | lead | — | aktiv |
| `teknisk-skribent` | Teknisk skribent | sonnet-4-6 | — | — | aktiv |
| `teknisk-skribent-2` | Teknisk skribent | haiku-4-5 | — | — | skal |

### DevRel

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `community-ansvarig` | Community-ansvarig | haiku-4-5 | — | — | skal |
| `devrel-ansvarig` | DevRel-ansvarig | sonnet-4-6 | — | — | skal |

### Marketing

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `innehallsskapare` | Innehållsskapare | haiku-4-5 | — | — | skal |
| `marknadsforare` | Marknadsförare | sonnet-4-6 | — | — | skal |

## Squads (tvärfunktionella mission-team)

Ortogonalt mot avdelning: *vad* vi bygger (produktområde), tvärfunktionellt bemannat.

| squad | medlemmar |
|-------|-----------|
| **Insikter** | `frontend-utvecklare`, `produktledare-dashboard` |
| **Integrationer** | `backend-utvecklare`, `produktledare-mcp` |
| **Modellering** | `produktledare-core` |
| **Överblick** | `terminal-utvecklare`, `terminal-utvecklare-2`, `produktledare-tui` |
