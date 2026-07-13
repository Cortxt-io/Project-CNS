---
name: secure-secrets
description: "Skapa och lägg in tokens/secrets säkert — hemligheten passerar aldrig chatt, shell-historik eller processargument. Använd när användaren ska sätta en GitHub Actions-secret eller lokal nyckel (CLAUDE_CODE_OAUTH_TOKEN, ANTHROPIC_API_KEY, MCP-/deploy-tokens), när någon råkat klistra en hemlighet i klartext, eller när en token behöver roteras. En hemlighet ska gå **direkt från där den skapas till där den lagras**, via stdin — aldrig genom chatten, ett kommandoradsargument eller shell-historiken. Klistras en token i en delad yta (chatt, `--body \"<token>\"`, ett committat skript) är den läckt och måste roteras."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/secure-secrets.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# secure-secrets

## Vad den gör

Skapa och lägg in tokens/secrets säkert — hemligheten passerar aldrig chatt, shell-historik eller processargument.

## När den ska köras

Använd när användaren ska sätta en GitHub Actions-secret eller lokal nyckel (CLAUDE_CODE_OAUTH_TOKEN, ANTHROPIC_API_KEY, MCP-/deploy-tokens), när någon råkat klistra en hemlighet i klartext, eller när en token behöver roteras.

En hemlighet ska gå **direkt från där den skapas till där den lagras**, via stdin —
aldrig genom chatten, ett kommandoradsargument eller shell-historiken. Klistras en
token i en delad yta (chatt, `--body "<token>"`, ett committat skript) är den läckt
och måste roteras.

## Gyllene regler

1. **Aldrig i chatten.** Be aldrig användaren klistra en token i konversationen, och
   gör det aldrig själv. Om det ändå händer: behandla token:n som komprometterad → rotera.
2. **Aldrig som argument.** Inte `gh secret set NAME --body "<token>"` (syns i
   processlistan/historik). Använd stdin: `<värde> | gh secret set NAME --repo <repo>`.
3. **Dold inmatning.** Läs värdet med en dold prompt (`Read-Host -AsSecureString`),
   inte vanlig text.
4. **Rätt lagring per typ:**
   - CI-tokens (Actions) → **GitHub Actions secret**.
   - Lokala nycklar → **otrackad fil** (jfr `.cns-agent-key`, `.env` — måste vara gitignored)
     eller OS-nyckelringen.

## Verktyget

`scripts/set_secret.ps1` gör det säkra flödet i ett svep — dold prompt → stdin → `gh secret set`:

```powershell
# GitHub Actions-secret (default-repo rian010194/Project-CNS):
pwsh scripts/set_secret.ps1 -Name CLAUDE_CODE_OAUTH_TOKEN

# Lokal otrackad nyckel i .env i stället:
pwsh scripts/set_secret.ps1 -Name ANTHROPIC_API_KEY -Env .env
```

Värdet matas in i en **dold prompt** — det hamnar aldrig på skärmen, i historik eller i argument.

## Generera token (separat, interaktivt)

Generering är webbläsarbaserad och kan inte automatiseras helt:
- **Claude-prenumeration (OAuth):** `claude setup-token` i en riktig interaktiv terminal →
  slutför inloggningen → token `sk-ant-oat01-…` skrivs ut **en gång**. (Kräver Pro/Max.)
  Robustare alternativ: `/install-github-app` och välj OAuth/prenumeration — genererar token
  **och** sätter secreten åt dig.
- **API-nyckel:** console.anthropic.com → Billing/API keys.

Kopiera token:n och klistra in den i den **dolda prompten** från `set_secret.ps1` — inte i chatten.

## Rotera (när en token läckt eller går ut)

OAuth-token gäller 1 år; en som passerat en delad yta ska roteras direkt:
1. Generera ny (ovan).
2. `pwsh scripts/set_secret.ps1 -Name <SAMMA_NAMN>` → skriver över secreten.
3. Den gamla blir oanvändbar så fort den nya är aktiv. Bekräfta nästa körning går grön.

## Steg (när skillen körs)

1. **Bekräfta typ + lagringsmål** (CI-secret vs lokal nyckel) och secret-namnet.
2. **Påminn om generering** om token saknas (peka på rätt kommando ovan).
3. **Peka på `set_secret.ps1`** — låt användaren köra det själv så värdet aldrig passerar
   en agentyta. Sätt aldrig en secret åt användaren genom att ta emot värdet i klartext.
4. **Verifiera** att secreten finns: `gh secret list --repo <repo>` (visar namn + datum, inte värde).
5. **Vid läcka:** flagga rotation explicit.
