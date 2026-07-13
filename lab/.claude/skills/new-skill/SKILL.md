---
name: new-skill
description: "Skapa en ny skill interaktivt — guided flow som samlar namn, trigger, beteenderegler och MCP-verktyg, sedan genererar .claude/skills/<name>.md. Triggar på /new-skill. Använd när du vill koda in ett återkommande beteende (ett kommando, ett arbetsflöde, en konvention) som Claude ska följa. En skill är en portabel beteendekonvention: den beskriver vad Claude ska göra när ett visst kommando triggas, vilka regler som gäller och vilka verktyg som behövs. Guiden producerar en `.claude/skills/<name>.md`-fil klar att använda."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/new-skill.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# new-skill

## Vad den gör

Skapa en ny skill interaktivt — guided flow som samlar namn, trigger, beteenderegler och MCP-verktyg, sedan genererar .claude/skills/<name>.md.

## När den ska köras

Triggar på /new-skill. Använd när du vill koda in ett återkommande beteende (ett kommando, ett arbetsflöde, en konvention) som Claude ska följa.

En skill är en portabel beteendekonvention: den beskriver vad Claude ska göra
när ett visst kommando triggas, vilka regler som gäller och vilka verktyg som
behövs. Guiden producerar en `.claude/skills/<name>.md`-fil klar att använda.

## Steg

1. ...
2. ...

## Regler

- ...

## Relaterat

- `/agent-studio` — skapa en agent som skillen kan anropa
- `/new-session-profile` — skapa en profil som skillen aktiverar
- Befintliga skills: `.claude/skills/` och `skills/`

## Placering av skills

- **`.claude/skills/`** (versionerad i repot) — skills för portföljarbetet med Cortxt.
  Dessa synkroniseras med GitHub.
- **`skills/`** — portabla konventioner som kan delas med andra projekt (cns-flush, cns-fork, m.fl.).

Ny skill hamnar i `.claude/skills/` om inget annat angetts.
