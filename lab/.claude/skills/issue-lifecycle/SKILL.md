---
name: issue-lifecycle
description: "Skapa, uppdatera och stäng GitHub-issues korrekt — via `gh` CLI. Använd när en GitHub-issue ska skapas, få todos eller stängas — \"skapa en issue för X\", \"stäng #42\", \"lägg till delsteg\". Och innan du stänger något: kontrollera acceptanskriterierna, inte bara att arbetet är gjort. Använd den INTE för PR:er — det är pr-protokoll."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/issue-lifecycle.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# issue-lifecycle

## Vad den gör

Skapa, uppdatera och stäng GitHub-issues korrekt — via `gh` CLI.

## När den ska köras

Använd när en GitHub-issue ska skapas, få todos eller stängas — "skapa en issue för X", "stäng #42", "lägg till delsteg". Och innan du stänger något: kontrollera acceptanskriterierna, inte bara att arbetet är gjort. Använd den INTE för PR:er — det är [[pr-protokoll]].

## Verktyget

**`gh` CLI. Inget annat.** MCP-verktygen `cortxt_issue(action=…)` som den här skillen tidigare byggde på är borttagna (53 exponerade verktyg, noll anrop — de revs 2026-07-13). Använd aldrig `git`-subprocess för issue-arbete; `gh` talar med API:t direkt.

Interaktiva flaggor (`-i`) fungerar inte i den här miljön. Allt nedan är icke-interaktivt.

## Modellen — tre nivåer, ingen sidokopia

Sanningen lever på GitHub. Ingenting speglas lokalt.

- **nod** — label `node:<slug>`, kopplar issuen till en post i `catalog.yaml`
- **quest** = **milestone** — progress räknas av GitHub, inte av oss
- **issue** = uppgiften. Under den: **todos** = `- [ ]`-checkboxar i bodyn
- **typ** — label `type:story|bug|spike|chore` (default `story`)

## Skapa en issue

```bash
gh issue create \
  --title "Verb + substantiv" \
  --body "## Bakgrund
[varför]

## Acceptanskriterier

Given/When/Then under rubriken `## Acceptanskriterier`. De är agentens definition of done och är **skilda från delstegen** — delsteg är hur, acceptans är vad.

Lägga till i efterhand: läs bodyn, lägg till raden, skriv tillbaka.

```bash
gh issue view 42 --json body -q .body
gh issue edit 42 --body "<hela den nya bodyn>"
```

## Delsteg

- [ ] [konkret delsteg]" \
  --label "node:<slug>,type:story" \
  --milestone "<quest>"
```

**Titeln måste vara:** verb + substantiv, max 10 ord. Inga vaga ord som "förbättra" eller "kolla".

`--milestone` utelämnas om issuen saknar quest. `--label node:<slug>` är inte valfri — en issue utan nod hör ingenstans.

## Todos (delsteg)

Checkboxar under `## Delsteg`. Samma väg: `gh issue view --json body` → redigera → `gh issue edit --body`. Bocka av genom att byta `- [ ]` mot `- [x]`.

## Stänga en issue

```bash
gh issue close 42 --comment "Klart: [vad som levererades]"
```

**Stäng bara om acceptanskriterierna är uppfyllda** — inte bara för att arbetet känns gjort. Läs dem först:

```bash
gh issue view 42
```

## Prioriteringsordning

1. Issues kopplade till en aktiv quest (milestone) — högst
2. Orphan-issues (utan quest) — lägst

## Vad du INTE gör

- Skapar aldrig issues utan tydliga acceptanskriterier
- Stänger aldrig issues utan att dokumentera vad som levererades
- Kopplar aldrig en issue till mer än en quest
- Speglar aldrig issue-data i en lokal fil — GitHub är sanningen
