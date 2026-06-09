---
name: new-session-profile
description: Skapa en ny session-profil interaktivt — fyller session-profile.schema.json via guided frågor, validerar och sparar under schemas/profiles/. Triggar på /new-session-profile. Använd när du vill definiera hur en ny typ av arbetspass ska se ut (vilken kontext det laddar, vilka verktyg det har, vad det producerar).
---

# /new-session-profile — skapa en session-profil utan JSON-redigering

En session-profil definierar ett standardiserat arbetspassformat: vad som laddas
vid start, vilka verktyg som är tillgängliga och vad passet ska producera.
Guiden validerar mot `schemas/session-profile.schema.json` och sparar resultatet
i `schemas/profiles/<name>.json`.

## Steg

### 1. Namn
Kebab-case slug (a-z, 0-9, bindestreck). Exempel: `code-review`, `planning`, `triage`.
Kontrollera att `schemas/profiles/<name>.json` inte redan finns.

### 2. Beskrivning
En mening som förklarar profiltypen och när den passar. Används i profillistan.

### 3. Kontext (`context`)
Vad laddas in när passet startar? Lista resurser/filter som Claude ska hämta/läsa:
- `open-ideas` — öppna idéer i idéinkorgen
- `active-quests` — milestones med öppna issues
- `open-issues` — alla öppna issues (ev. filtrerade)
- `node:<slug>` — en specifik CNS-nod och dess planning/-filer
- `linear-issues` — Linear-issues (kräver `LINEAR_API_KEY`)
- Fritext: beskriv annat kontext

Minst 1 krävs.

### 4. Kapacitet (`capacity`)
Vilka `cortxt_*`-verktyg ska vara tillgängliga? Lista de som faktiskt behövs —
inte allt. Tänk: vad muterar detta passet? Ska det kunna skriva till GitHub?

Befintliga verktyg (välj relevanta):
- **Läs:** `cortxt_list_open_issues`, `cortxt_get_issue`, `cortxt_list_quests`, `cortxt_get_project`, `cortxt_list_ideas`, `cortxt_list_sessions`, `cortxt_read_wiki_page`
- **Skriv:** `cortxt_create_issue`, `cortxt_close_issue`, `cortxt_capture_idea`, `cortxt_promote_idea_to_issue`, `cortxt_create_pr`, `cortxt_write_wiki_page`
- **Session:** `cortxt_start_session`, `cortxt_mark_session_done`, `cortxt_save_session`, `cortxt_fork_session`

### 5. Artefakttyp (`artifact_type`)
Vad producerar ett pass av den här profilen? En mening eller ett ord:
`ideas`, `code`, `node-planning-file`, `pr`, `wiki-page`, `issue-list`, m.m.

### 6. Agent (valfritt)
Ska profilen vara bunden till en specifik agent? Ange agent-slug (från `/agent-studio`)
eller hoppa över — profilen fungerar utan en bunden agent.

### 7. Validera
Kontrollera fälten mot schemat (`schemas/session-profile.schema.json`):
- `name`: kebab-case sträng ✓
- `description`: sträng ✓
- `context`: array, minst 1 element ✓
- `capacity`: array (kan vara tom) ✓
- `artifact_type`: sträng ✓

### 8. Spara
Skriv `schemas/profiles/<name>.json`. Bekräfta innehållet med användaren
**innan** du skriver filen — det är enkelt att ändra nu, svårare efteråt.

Rapportera: filsökväg, namn, kontext-items, kapacitet-antal, artefakttyp.

## Relaterat
- `/agent-studio` — skapa en agent att binda till profilen
- `/new-skill` — skapa en skill som aktiverar profilen
- Befintliga profiler: `schemas/profiles/` (brainstorm, cns-build, research)
