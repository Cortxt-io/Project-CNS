# webhook-router / decisions

## 2026-05-07: Ompositionering fran intern infra till extern produkt

**Beslut:** Webhook Router ompositioneras fran "intern infrastruktur for Project Vault" till "self-hosted webhook audit log for utvecklare."

**Varfor:**
- Tidigare framing var cirkular: bygga infra for projekt som inte finns an.
- Enda konsumenten (Site Change Monitor) ar parkerad -- exakt den risk som identifierades.
- Intern-infra-framing kan inte valideras med externa anvandare.
- En extern produkt har eget varde, egen malgrupp, och kan demo:as och valideras sjalvstandigt.

**Konsekvens:** Hela project.md omskriven. Tags andrade fran "infrastruktur" till "devtools". Inget beroende till Site Change Monitor langre.

## 2026-05-07: Self-hosted som differentiator

**Beslut:** Positionera explicit som self-hosted alternativ till Hookdeck/Convoy, inte som konkurrent pa samma plan.

**Varfor:**
- Hookdeck ar SaaS med per-event-pricing ($39/mo for team). Convoy ar enterprise/komplex (Go + Postgres + Redis).
- En binar + SQLite ar en annan kategori: ingen kostnad, ingen data som lamnar servern, ingen setup-process.
- Solo-utvecklare och sma team ar underservade av de stora aktorerna.

## 2026-05-07: Python + SQLite som teknikval

**Beslut:** Bygg i Python med SQLite. Ingen ny runtime, ingen ny stack.

**Varfor:**
- Konsistent med ovriga CNS-projekt.
- SQLite hanterar hundratals-tusentals webhooks per dag utan problem.
- Inga externa beroenden (Redis, Postgres, etc.) -- passar self-hosted-positioneringen.
- Om Go/Rust behovs for prestanda kan det overvagas efter validering, inte fore.

## 2026-05-07: Replay som killer feature

**Beslut:** Replay-funktionen ar karn-differentiator och maste finnas i MVP.

**Varfor:**
- Utan replay ar verktyget "andernu en log viewer" -- inte tillrackligt varde.
- Replay loser det konkreta problemet: "jag behover reprodusera vad som hande nar Stripe skickade den webhooken igar."
- Hookdeck har replay men bakom betalvall. Self-hosted replay ar unikt.
