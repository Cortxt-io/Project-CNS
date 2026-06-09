---
name: new-skill
description: Skapa en ny skill interaktivt — guided flow som samlar namn, trigger, beteenderegler och MCP-verktyg, sedan genererar .claude/skills/<name>.md. Triggar på /new-skill. Använd när du vill koda in ett återkommande beteende (ett kommando, ett arbetsflöde, en konvention) som Claude ska följa.
---

# /new-skill — skapa en skill utan manuell filredigering

En skill är en portabel beteendekonvention: den beskriver vad Claude ska göra
när ett visst kommando triggas, vilka regler som gäller och vilka verktyg som
behövs. Guiden producerar en `.claude/skills/<name>.md`-fil klar att använda.

## Steg

### 1. Namn och trigger
- **Slug** (kebab-case): det du skriver som `/namn` i Claude Code. Exempel: `daily-brief`, `validate-nodes`, `sync-linear`.
- Kontrollera att `.claude/skills/<slug>.md` inte redan finns.

### 2. Beskrivning (frontmatter)
En mening som:
1. Förklarar vad skillen gör
2. Listar exempel på fraser som triggar den ("Använd när användaren säger X")

Beskrivningen visas i skillistan och används av Claude för att avgöra när
skillen är relevant — skriv den som om du förklarar för en ny Claude-instans.

### 3. Beteenderegler
Kärninnehållet. Specificera:
- **Triggersituation:** exakt när skillen ska köras (fraser, kontextsignaler)
- **Steg:** numrerad lista med konkreta handlingar (verktygsanrop, beslut, output)
- **Regler:** vad som aldrig får göras (no-ops, farliga operationer, antaganden)
- **Rapportering:** vad som ska bekräftas till användaren och när

Inspirationskälla: se befintliga skills i `skills/` (cns-flush, cns-fork, cns-sync)
för mönster — de är välgenomtänkta mallar.

### 4. MCP-verktyg att pre-allowlista
Lista vilka `cortxt_*`-verktyg skillen använder. Dessa läggs i kommentaren i
skillens frontmatter som en referens (Claude Code allowlist hanteras separat
i `settings.json` — informera användaren om det om relevanta verktyg saknas).

### 5. Relaterade skills
Vilka befintliga skills kompletterar eller föregår denna? Exempel:
`/cns-sync` körs naturligt före `/cns-flush`. Lista relationer i en `## Relaterat`-sektion.

### 6. Generera och bekräfta
Bygg skillens markdown-innehåll:

```markdown
---
name: <slug>
description: <en rad — trigger-fraser ingår>
---

# /<slug> — <kort titel>

<introduktion: vad skillens syfte är>

## Steg
1. ...
2. ...

## Regler
- ...

## Relaterat
- ...
```

Visa utkastet för användaren. Bekräfta innan du skriver filen.

### 7. Spara
Skriv `.claude/skills/<slug>.md`. Rapportera sökväg och vilka verktyg
användaren behöver lägga till i `settings.json` om de saknas.

## Placering av skills
- **`.claude/skills/`** (versionerad i repot) — skills för portföljarbetet med Cortxt.
  Dessa synkroniseras med GitHub.
- **`skills/`** — portabla konventioner som kan delas med andra projekt (cns-flush, cns-fork, m.fl.).

Ny skill hamnar i `.claude/skills/` om inget annat angetts.

## Relaterat
- `/agent-studio` — skapa en agent som skillen kan anropa
- `/new-session-profile` — skapa en profil som skillen aktiverar
- Befintliga skills: `.claude/skills/` och `skills/`
