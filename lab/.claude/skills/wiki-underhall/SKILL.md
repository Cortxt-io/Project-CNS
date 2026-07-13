---
name: wiki-underhall
description: "När och hur du uppdaterar CNS-wikin — memory card-format, stale-termer, vad som hör var. Använd när ett beslut eller ett systemmönster ska skrivas ner i GitHub-wikin — \"dokumentera hur X fungerar\", \"uppdatera wiki-sidan\", \"den här sidan är gammal\" — och alltid när en sida bär döda termer (nodes/, node.md, quest_manager.py, stage/status som nodfält)."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/wiki-underhall.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# wiki-underhall

## Vad den gör

När och hur du uppdaterar CNS-wikin — memory card-format, stale-termer, vad som hör var.

## När den ska köras

Använd när ett beslut eller ett systemmönster ska skrivas ner i GitHub-wikin — "dokumentera hur X fungerar", "uppdatera wiki-sidan", "den här sidan är gammal" — och alltid när en sida bär döda termer (nodes/, node.md, quest_manager.py, stage/status som nodfält).

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

Kolumnen "Gammalt" skrivs utan backticks med flit: backticks är ett anspråk om **levande** kod, och
de här termerna är döda. Skriver du dem som kod fäller färskhetschecken dig — med rätta.

| Gammalt | Rätt |
|---------|------|
| projects/, nodes/ | `catalog.yaml` — enda strukturerade källan |
| project.md, node.md | `catalog.yaml` (fält) + `decisions/<slug>.md` (prosa). Nodmodellen revs 2026-06-12. |
| quest_manager.py | `issues_client` + GitHub Milestones |
| stage, status (som nodfält) | Finns inte. Livscykel och arbete bor på **boarden** (GitHub Projects/Linear). |
| "quest som JSON" | "quest = GitHub Milestone" |

## Vad du INTE skriver i wikin

- Implementationsdetaljer som framgår av koden
- Spekulativ arkitektur ("om vi någon gång skulle...")
- Personliga sessionsnoteringar
- Duplicat av node.md-innehåll
