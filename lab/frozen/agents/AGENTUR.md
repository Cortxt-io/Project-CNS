# AGENTUR.md — org-schema (Plan A) — GENERERAD

> Genererad av `scripts/gen_agentur.py` ur agent-frontmatter. **Redigera inte för hand** —
> ändra rollerna i `.claude/agents/*.md` (aktiva) / `.claude/org/roster/*.md` (skal) och kör om.

**88 roller** i registret, varav **27 aktiva** (körbara i `.claude/agents/`).
Resten är skal i org-registret (`.claude/org/roster/`) — bemannas vid behov.

Princip: agenter = anställda, skills = kompetenser. Matris (Spotify): department +
sub_department (linjen) × squad (mission) × chapter (disciplin) × guild (skills `Gemensam`).

Aktiva rostern hålls liten (playbook: 7–10 aktiva åt gången). VD = Rikard (ej agentfil).

## Leadership

### Exec

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `chief-of-staff` | Stabschef (Chief of Staff) | sonnet-4-6 | lead | — | aktiv |
| `coo` | Operativ chef (COO) | opus-4-8 | lead | — | aktiv |
| `cpo` | Produktdirektör (CPO) | opus-4-8 | lead | — | skal |
| `cto` | Teknisk direktör (CTO) | opus-4-8 | lead | — | aktiv |
| `strategy-lead` | Strategichef | opus-4-8 | lead | — | skal |

## Product

### PM

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `product-lead` | Produktchef | haiku-4-5 | lead | — | aktiv |
| `product-lead-core` | Produktledare CNS-core | sonnet-4-6 | — | Modellering | skal |
| `product-lead-dashboard` | Produktledare Dashboard | sonnet-4-6 | — | Insikter | skal |
| `product-lead-mcp` | Produktledare MCP-plattform | sonnet-4-6 | — | Integrationer | skal |
| `product-lead-tui` | Produktledare TUI | sonnet-4-6 | — | Överblick | skal |

### Arkitektur

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `solution-architect` | Lösningsarkitekt | sonnet-4-6 | — | — | aktiv |

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
| `product-analyst` | Produktanalytiker | haiku-4-5 | — | — | skal |
| `product-ops` | Product Ops | haiku-4-5 | — | — | skal |

## R&D

### Research

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `research-lead` | Forskningsledare | sonnet-4-6 | lead | — | aktiv |
| `competitor-analyst` | Konkurrentanalytiker | sonnet-4-6 | — | — | skal |
| `market-analyst` | Marknadsanalytiker | sonnet-4-6 | — | — | skal |
| `teknikspanare` | Teknikspanare | sonnet-4-6 | — | — | skal |
| `web-researcher` | Webbresearcher | haiku-4-5 | — | — | skal |

### Innovation

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `innovation-lead` | Innovationsledare | sonnet-4-6 | lead | — | skal |
| `datavetare` | Datavetare | sonnet-4-6 | — | — | skal |
| `prototypare` | Prototypare | sonnet-4-6 | — | — | skal |

## Engineering

### Backend

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `backend-lead` | Backend-lead | sonnet-4-6 | lead | — | skal |
| `backend-developer` | Backend-utvecklare | sonnet-4-6 | — | Integrationer | aktiv |
| `backend-developer-2` | Backend-utvecklare | haiku-4-5 | — | — | skal |
| `backend-developer-3` | Backend-utvecklare | haiku-4-5 | — | — | skal |
| `backend-developer-4` | Backend-utvecklare | haiku-4-5 | — | — | skal |

### DevOps

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `devops-engineer` | DevOps-ingenjör | haiku-4-5 | — | — | aktiv |

### Frontend

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `frontend-lead` | Frontend-lead | sonnet-4-6 | lead | — | skal |
| `frontend-developer` | Frontend-utvecklare | sonnet-4-6 | — | Insikter | aktiv |
| `frontend-developer-2` | Frontend-utvecklare | haiku-4-5 | — | — | skal |
| `frontend-developer-3` | Frontend-utvecklare | haiku-4-5 | — | — | skal |
| `terminal-developer` | Terminal-UI-utvecklare | sonnet-4-6 | — | Överblick | aktiv |
| `terminal-developer-2` | Terminal-UI-utvecklare | haiku-4-5 | — | Överblick | skal |

### Fullstack

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `fullstack-developer` | Fullstack-utvecklare | sonnet-4-6 | — | — | aktiv |
| `fullstack-developer-2` | Fullstack-utvecklare | haiku-4-5 | — | — | skal |

### Integrations

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `integration-developer` | Integrationsutvecklare | sonnet-4-6 | — | — | aktiv |
| `integration-developer-2` | Integrationsutvecklare | haiku-4-5 | — | — | skal |

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
| `data-engineer` | Data-ingenjör | sonnet-4-6 | — | — | skal |
| `data-engineer-2` | Data-ingenjör | haiku-4-5 | — | — | skal |

## Platform

### Infra

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `platform-lead` | Plattformschef | sonnet-4-6 | lead | — | aktiv |
| `platform-engineer` | Plattformsingenjör | sonnet-4-6 | — | — | aktiv |
| `platform-engineer-2` | Plattformsingenjör | haiku-4-5 | — | — | skal |

### DevEx

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `build-engineer` | Build-ingenjör | haiku-4-5 | — | — | skal |
| `devex-engineer` | Developer-Experience-ingenjör | sonnet-4-6 | — | — | skal |

### DevOps

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `devops-engineer-2` | DevOps-ingenjör | haiku-4-5 | — | — | skal |

## People

### L&D

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `learning-developer` | Kompetensutvecklare (L&D) | sonnet-4-6 | — | — | aktiv |
| `learning-developer-2` | Kompetensutvecklare | sonnet-4-6 | — | — | skal |

### Org Design

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `org-architect` | Organisationsarkitekt | sonnet-4-6 | lead | — | aktiv |

### Talent

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `people-lead` | HR-chef (CHRO) | sonnet-4-6 | lead | — | aktiv |
| `rekryterare` | Rekryterare | sonnet-4-6 | — | — | skal |
| `rekryterare-2` | Rekryterare | haiku-4-5 | — | — | skal |

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
| `program-lead` | Programledare | sonnet-4-6 | lead | — | aktiv |
| `scrum-master` | Scrum Master | haiku-4-5 | — | — | skal |
| `scrum-master-2` | Scrum Master | haiku-4-5 | — | — | skal |

### Coordination

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `session-coordinator` | Sessionskoordinator | haiku-4-5 | — | — | aktiv |
| `session-coordinator-2` | Sessionskoordinator | haiku-4-5 | — | — | skal |

### Release

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `delivery-lead` | Leveranschef | sonnet-4-6 | lead | — | skal |
| `release-coordinator` | Release-koordinator | haiku-4-5 | — | — | skal |

## Operations

### Maintenance

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `maintenance-engineer` | Underhållsingenjör | sonnet-4-6 | — | — | aktiv |
| `maintenance-engineer-2` | Underhållsingenjör | haiku-4-5 | — | — | skal |

### SRE

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `operations-lead` | Driftchef | sonnet-4-6 | lead | — | aktiv |
| `sre-engineer` | SRE-ingenjör | sonnet-4-6 | — | — | skal |
| `sre-engineer-2` | SRE-ingenjör | haiku-4-5 | — | — | skal |

### Monitoring

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `monitoring-analyst` | Övervakningsanalytiker | haiku-4-5 | — | — | skal |
| `situation-analyst` | Lägesanalytiker | haiku-4-5 | — | — | aktiv |

### Incident

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `incident-lead` | Incidentledare | sonnet-4-6 | lead | — | skal |

## Finance

### Controlling

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `finance-lead` | Ekonomichef (CFO) | haiku-4-5 | lead | — | aktiv |
| `controller` | Controller | haiku-4-5 | — | — | skal |

### FinOps

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `faktureringsansvarig` | Faktureringsansvarig | haiku-4-5 | — | — | skal |
| `finops-analyst` | FinOps-analytiker | haiku-4-5 | — | — | skal |
| `inkop` | Inköpsansvarig | haiku-4-5 | — | — | skal |

## Communications

### Docs

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `communications-lead` | Kommunikationschef | sonnet-4-6 | lead | — | aktiv |
| `technical-writer` | Teknisk skribent | sonnet-4-6 | — | — | aktiv |
| `technical-writer-2` | Teknisk skribent | haiku-4-5 | — | — | skal |

### DevRel

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `community-ansvarig` | Community-ansvarig | haiku-4-5 | — | — | skal |
| `devrel-ansvarig` | DevRel-ansvarig | sonnet-4-6 | — | — | skal |

### Marketing

| slug | titel | modell | roll | squad | status |
|------|-------|--------|------|-------|--------|
| `innehallsskapare` | Innehållsskapare | haiku-4-5 | — | — | skal |
| `marketer` | Marknadsförare | sonnet-4-6 | — | — | skal |

## Squads (tvärfunktionella mission-team)

Ortogonalt mot avdelning: *vad* vi bygger (produktområde), tvärfunktionellt bemannat.

| squad | medlemmar |
|-------|-----------|
| **Insikter** | `frontend-developer`, `product-lead-dashboard` |
| **Integrationer** | `backend-developer`, `product-lead-mcp` |
| **Modellering** | `product-lead-core` |
| **Överblick** | `terminal-developer`, `terminal-developer-2`, `product-lead-tui` |
