---
name: wiki-underhall
description: När och hur du uppdaterar CNS-wikin — memory card-format, stale-termer, vad som hör var.
---

# Wiki-underhåll

## Vad hör i wikin (vs node.md vs sessions)

| Kunskap | Hemvist |
|---------|---------|
| Hur systemet fungerar, dataflöde, beslut | **GitHub Wiki** |
| Vad en specifik nod/komponent är | `nodes/*/node.md` |
| Vad som gjordes i ett arbetspass | `exports/sessions/`, `exports/btw/` |

**Regel:** Spekulativ arkitektur → idé-inkorgen. Personliga anteckningar → btw. Beslut och mönster → wiki.

## Memory card-format (för agenter och beslut)

```markdown
## Syfte
[Vad detta är och varför det finns — en mening]

## Nyckelinformation
- [Viktigaste faktum 1]
- [Viktigaste faktum 2]
- [Viktigaste faktum 3]

## Kontext
[Bakgrund: varför beslutades detta, vad ersatte det]

## Senast verifierad
[Datum]
```

## Arbetsflöde — alltid

1. `cortxt_read_wiki_page` — läs befintlig sida om den finns
2. Kolla relevanta noder för korrekt fakta
3. Skriv nytt innehåll
4. `cortxt_write_wiki_page` — spara

## Stale-termer att alltid uppdatera

| Gammalt | Rätt |
|---------|------|
| `projects/` | `nodes/` |
| `project.md` | `node.md` |
| `quest_manager.py` | `issues_client` + GitHub Milestones |
| `status` (primärt fält) | `stage` |
| "quest som JSON" | "quest = GitHub Milestone" |

## Vad du INTE skriver i wikin

- Implementationsdetaljer som framgår av koden
- Spekulativ arkitektur ("om vi någon gång skulle...")
- Personliga sessionsnoteringar
- Duplicat av node.md-innehåll
