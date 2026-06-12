# Autonom agentur — byggordning

**Status:** levande karta (tunn). Kodifierar den fas-ordning som redan styr arbetet
i quest #10 och ger issues #57–#61 en gemensam ryggrad. Detta är INTE en ny
ceremoni — det gör en implicit sekvens explicit så att parallella sessioner inte
driver isär i sin tolkning av "Fas 3" / "Fas 5".

Syster-spec (mekanik, inte ordning): `plans/agentur-routing-spec.md`.

## Princip

**Tillit före autonomi.** En agentur som plockar arbete och muterar repo:t på egen
hand är bara försvarbar om vi FÖRST kan (a) bedöma om ett pass gjorde rätt (eval),
(b) se vad det förbrukade (observabilitet) och (c) stoppa runaway (guardrails). Att
bygga dispatch-loopen innan dessa finns vore att automatisera oövervakat — fel
ordning. Därför kommer transport (Fas 3) efter fundamentet, och full autonomi
(Fas 5) sist, grindat av track record.

**Komponera, bygg inte om.** Varje fas byggs PÅ befintliga primitiver
(`agentur_routing`, `agent_roles`, `agent_host`, `agent_guardrails`, `agent_eval`,
`session_store`, `issues_client`/`lease_store`), inte ny parallell infrastruktur.

## Faser

| Fas | Namn | Vad den ger | Issue(s) | Status |
|-----|------|-------------|----------|--------|
| 0 | Routing + roll-medveten exekvering | `route()` → station/squad/modell; `role_for_node` → kör passet SOM rätt agent | #90 (PR #93) | klar |
| 1 | Eval-grind | bedöm en sessions OUTPUT mot agentens eval-kriterier (LLM-domare) före `mark_done` | #57 | klar |
| 2 | Observabilitet | metrics per pass (tool_calls/tokens/artifacts), `is_phantom`, `running→done` som pollbar signal | #58 | klar |
| 3 | **Dispatch-loop (bounded, human-in-loop)** | loopen: välj lämplig issue → claim → route → kör ETT pass → draft-PR. En issue i taget, människa godkänner varje muterande steg (crawl) | **#59** | bygges |
| 4 | Guardrails wirade | turn/token-tak + upprepat-anrop + cns-sync-överlapp, inkopplat i `agent_host` | #60, #69 | klar |
| 5 | Lossa till exception-only | när track record finns: släpp human-in-loop-grinden från varje-steg till undantag; öka parallellism | #61 | väntar |

> Fas 4 (guardrails) listas efter Fas 3 i numrering men landade tekniskt redan
> (#69) — den är en förutsättning som Fas 3 wirar mot, inte ett senare steg. Ordningen
> är logisk (guardrails finns innan loopen kör), inte kronologisk.

## Fas 3 — dispatch-loop (det aktiva steget)

**Crawl-form:** övervakad, en issue i taget, ingen fan-out. Människa godkänner varje
muterande åtgärd (push/PR/close). Aldrig auto-merge.

Loop v1:
1. **Lämplighetsbedömning** — öppen, claimbar, `depends_on` uppfyllda, typ lämplig
   (hoppa diffusa/feature-tunga). Föreslå-sen-utför.
2. **Claim → route → kör** — `claim_issue` (lease_store) → `route()`/`role_for_node`
   → ETT pass via `agent_host` som rätt roll, under `Guardrails` + cns-sync-koll.
3. **Människa-in-loop** — varje muterande steg kräver godkännande.
4. **Draft-PR + bokför** — öppna draft-PR (required reviewer som hård grind);
   `session_store` `running→done` + metrics. Stanna för människa.

Hårda krav: kill-switch + orphan-cleanup vid timeout; kostnadstak (Guardrails);
worktree-isolering om passet skriver; eval-grind (#57) före done.

**Transportval:** lokal `agent_host`-loop (roll-medvetenheten finns redan där) framför
@claude-molntransport (molnet kör generisk Claude — ej roll-medvetet än). Claude
GitHub App utvärderas som färdig dispatch-yta men ersätter INTE #57/#58/#60
(transport ≠ tillit/mätning) och är ett utåtriktat steg (app-install, repo-secret,
API-fakturering → Ekonomichefens grind).

## Underhåll

Håll filen tunn. När en fas byter status eller en issue stängs — uppdatera tabellen
i samma ändring. Detaljerad mekanik hör hemma i respektive modul-docstring och i
`agentur-routing-spec.md`, inte här.
