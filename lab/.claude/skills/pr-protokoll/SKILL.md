---
name: pr-protokoll
description: "PR-checklista för CNS — skapa, koppla och begär review korrekt. Använd innan en PR skapas, och när CI är röd på en öppen PR — \"öppna en PR för det här\", \"be om review\", \"varför är checken röd\". Täcker branch/issue-koppling, body-format, reviewers, och att aldrig merga eller pusha till main själv."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/pr-protokoll.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# pr-protokoll

## Vad den gör

PR-checklista för CNS — skapa, koppla och begär review korrekt.

## När den ska köras

Använd innan en PR skapas, och när CI är röd på en öppen PR — "öppna en PR för det här", "be om review", "varför är checken röd". Täcker branch/issue-koppling, body-format, reviewers, och att aldrig merga eller pusha till main själv.

## Innan du skapar en PR

- [ ] Arbetet är committat på en feature-branch (aldrig direkt på main)
- [ ] Branch-namnet speglar uppgiften: `feature/<slug>-<kort-beskrivning>`
- [ ] Det finns en öppen issue som PRen löser
- [ ] CI (GitHub Actions) är grön

## Skapa PR

```python
cortxt_create_pr(
    title="[Verb + vad]: Implementera cortxt_list_agents i app/tools/agents.py",
    body="## Vad\n[vad ändrades]\n\n## Varför\nLöser #[issue-nr]\n\n## Test\n- [ ] [hur det testades]",
    head="feature/min-branch",
    base="main"
)
```

## Koppla till issue

Lägg i PR-body: `Fixes #[issue-nr]` — GitHub stänger issuen automatiskt vid merge.

## Begär review

```python
cortxt_set_pr_reviewers(
    pr_number=42,
    reviewers=["rian010194"]
)
```

## Vad du INTE gör

- Mergar aldrig direkt — CI + Rikard beslutar
- Pushar aldrig direkt till main
- Öppnar aldrig draft-PRs utan att informera operativ-chefn
- Skapar aldrig PR utan kopplad issue

## Om CI är röd

```python
cortxt_get_workflow_run(run_id="[id]")
```

Analysera felet. Fixa på branchen. Push. CI kör om automatiskt.
Öppna inte PRen förrän CI är grön — det är en devops-ingenjor-uppgift att bevaka.
