# API Schema -- projects.json

Skiss pa JSON-schemat som `cns export --format json` ska producera.

## Toppniva

```json
{
  "exported_at": "2026-05-11T14:00:00Z",
  "version": "1.0",
  "project_count": 8,
  "projects": [ ... ]
}
```

## Projektobjekt

```json
{
  "slug": "project-vault-dashboard",
  "title": "Project Vault Dashboard",
  "status": "idea",
  "mvp_stage": "hypothesis",
  "cost_sek": 4500,
  "value_sek": 20000,
  "roi_percent": 344,
  "tags": ["portfolio", "dashboard", "static-site", "dataviz", "cns"],
  "created": "2026-05-11",
  "updated": "2026-05-11",
  "current_slice": null,
  "sections": {
    "problem": "CNS och Project Vault lever i Markdown...",
    "solution": "En statisk HTML-dashboard...",
    "target_audience": "Framtida arbetsgivare...",
    "mvp_steps": ["Ta fram JSON-export...", "Bygga skal..."],
    "risks": [
      {"category": "market", "score": 2, "description": "..."},
      {"category": "technical", "score": 2, "description": "..."}
    ]
  }
}
```

## Faltbeskrivningar

| Falt | Typ | Beskrivning |
|------|-----|-------------|
| `slug` | string | Unik identifierare, matchar katalognamn |
| `title` | string | Lasbart projektnamn |
| `status` | enum | `idea`, `early_mvp`, `mvp`, `live`, `shelved` |
| `mvp_stage` | enum | `hypothesis`, `problem_interviews`, `solution_test`, `demand_test`, `launch` |
| `cost_sek` | number | Total uppskattad kostnad i SEK |
| `value_sek` | number | Total uppskattat varde i SEK |
| `roi_percent` | number | ROI i procent: `(value - cost) / cost * 100` |
| `tags` | string[] | Kategoriseringstaggar |
| `created` | date | Skapandedatum (ISO 8601) |
| `updated` | date | Senast uppdaterad (ISO 8601) |
| `current_slice` | string\|null | Aktiv quest-slice (om projektet har quest state) |
| `sections` | object | Parsade markdown-sektioner (valfritt i MVP) |

## Anmarkningar

- `sections` ar valfritt i MVP -- dashboarden kan klara sig pa enbart frontmatter-data.
- Om `sections` inkluderas ska `mvp_steps` vara en array av steg, inte ratt markdown.
- `risks` bor vara en array av objekt for att kunna renderas som visuella indikatorer.
- Versionsfaltet (`version`) mojliggor framtida schemandring utan att bryta dashboarden.
