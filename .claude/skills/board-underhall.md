---
name: board-underhall
department: Drift
description: Hur du underhåller org-projektet "Backlog" (GitHub Projects v2) — sync, fält, vyer, scope-gotchas.
---

# Board-underhåll (GitHub Projects "Backlog")

Arbetslagret (issues/epics/initiativ) visualiseras i ett **org-ägt** GitHub Project **"Backlog"**
under `Cortxt-io`. Arkitektur/system bor INTE här — det hör till ReactFlow-dashboarden. Epic #13.

## Var sanningen bor
- **Issues/epics/initiativ** = GitHub (repot). Projektet är bara en *vy*.
- **Fält-värden** sätts av sync, inte för hand: `System` ← `node:<slug>`-label, `Type` ← `type:`-label,
  `Initiative` ← milestone-description (`Initiative: <namn>`), `Epic` ← inbyggda Milestone-fältet (auto).

## Rutinsync (säker, ingen kodändring)
```
cns project sync            # backfilla + sätt fält (idempotent)
cns project sync --dry-run  # visa utan att skriva
```
- Kräver token med **`project`-scope**: `CNS_GITHUB_TOKEN` (Railway) eller `gh auth token` efter
  `gh auth refresh -s project`. Saknas scope → scriptet säger till.
- Ägaren styrs av env **`CNS_PROJECT_OWNER=Cortxt-io`** (skild från `GITHUB_REPO`-ägaren — repot kan
  ligga kvar på ett user-konto).

## Lägga till / ändra fält
- Skapa fält: `gh project field-create <num> --owner Cortxt-io --name "<Namn>" --data-type SINGLE_SELECT --single-select-options "a,b,c"`.
- Lista fält + option-id:n: `gh project field-list <num> --owner Cortxt-io`.
- **Saknade options:** `cns project sync` rör inte issues vars värde saknar en option — den listar dem som
  "Saknade single-select-options". Lägg då optionen på fältet (kommandot ovan) och kör sync igen.

## Vyer (manuellt i UI — API skapar inte sparade vyer)
- Board per **Status** (kanban).
- Table grupperad per **Initiative → Epic (Milestone)**.
- Board per **System**.

## Gotchas
- `organization(login:)`-GraphQL reser fel mot ett user-konto → använd alltid `CNS_PROJECT_OWNER`-orgen.
- Org-projekt kan kräva **SSO-godkännande** av token mot `Cortxt-io`.
- GitHubs native "Auto-add"-workflow drar bara från repos orgen äger → fungerar först när repot flyttats
  in i `Cortxt-io`. Tills dess är `cns project sync` mekanismen som håller projektet aktuellt.

## Autonomi-gräns
Sync-*körningar* är inte kod → fria. Ändringar i `scripts/sync_gh_project.py` är feature-kod →
`classify_risk` **eskalerar** (draft-PR + människa-grind) även i Fas 5. Den här skillen + konfig
self-mergas.
