---
name: pr-protokoll
description: "PR-checklista — skapa, koppla och begär review korrekt, via `gh` CLI. Använd innan en PR skapas, och när CI är röd på en öppen PR — \"öppna en PR för det här\", \"be om review\", \"varför är checken röd\". Använd den INTE för att skapa eller stänga issues — det är issue-lifecycle."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/pr-protokoll.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# pr-protokoll

## Vad den gör

PR-checklista — skapa, koppla och begär review korrekt, via `gh` CLI.

## När den ska köras

Använd innan en PR skapas, och när CI är röd på en öppen PR — "öppna en PR för det här", "be om review", "varför är checken röd". Använd den INTE för att skapa eller stänga issues — det är [[issue-lifecycle]].

## Verktyget

**`gh` CLI.** MCP-verktygen `cortxt_pr` och `cortxt_action` är borttagna (revs 2026-07-13 — 53 exponerade verktyg, noll anrop). Interaktiva flaggor fungerar inte här.

## Innan du skapar en PR

- [ ] Arbetet är committat på en egen branch — **aldrig direkt på main**
- [ ] Branchnamnet följer [[git-github-grund]]: `feat/`, `fix/`, `chore/` eller `docs/` + kort beskrivning
- [ ] Det finns en öppen issue som PR:en löser
- [ ] Testerna är gröna lokalt

> [!warning] Branchprefix
> `feature/` är fel och har stått fel i den här skillen. Regeln är `feat/` — trunk-based, squash-merge, radera branchen efter merge. Regeln går före skillen.

## Skapa PR

```bash
gh pr create \
  --title "Verb + vad" \
  --body "## Vad
[vad ändrades]

## Varför

Fixes #<issue-nr>

## Test

- [ ] [hur det testades]" \
  --base main \
  --head feat/min-branch
```

Lägg till `--draft` när arbetet inte är klart för review.

## Koppla till issue

`Fixes #<nr>` i bodyn — GitHub stänger issuen automatiskt vid merge. En PR utan kopplad issue skapas inte.

## Begär review

```bash
gh pr edit <nr> --add-reviewer rian010194
```

## Om CI är röd

```bash
gh pr checks <nr>                 # vilka checkar failar
gh run view <run-id> --log-failed # bara de rader som föll
```

Analysera felet. Fixa på branchen. Push — CI kör om automatiskt. Begär inte review förrän CI är grön.

## Vad du INTE gör

- Mergar aldrig direkt — CI + Rikard beslutar
- Pushar aldrig till main
- Skapar aldrig PR utan kopplad issue
- Kringgår aldrig hooks (`--no-verify`) eller signering
