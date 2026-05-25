---
cost_sek: 40000
created: 2026-05-02
mvp_stage: hypothesis
roi_percent: 200
slug: webhook-router
status: idea
tags:
- devtools
- webhooks
- self-hosted
- debugging
title: Webhook Router
updated: '2026-05-07'
current_slice: Self-hosted webhook audit log -- log, inspect, replay inkommande webhooks
summary: Self-hosted proxy som loggar, söker och replayer inkommande webhooks.
family: developer-tools
---

## Problem

Utvecklare som tar emot webhooks fran externa tjanster (Stripe, GitHub, SendGrid, Shopify, etc.) har inget enkelt satt att se exakt vad som skickades, nar, och om leveransen lyckades. Nar nagon rapporterar "betalningen gick igenom men vart system reagerade inte" borjar en manuell jakt genom applikationsloggar, tredjeparts-dashboards och gissningar. Att reproducera ett webhook-scenario i staging ar ofta omojligt eftersom payload:en ar borta.

Hookdeck och Convoy loser detta -- men som SaaS-plattformar med per-event-prissattning eller enterprise-fokus. Det finns inget latt self-hosted verktyg som bara gor: logga allt, lat mig soka, lat mig replay:a.

## Losning

En lattviktig, self-hosted webhook-proxy som sitter mellan externa tjanster och din applikation. Den tar emot webhooks, loggar varje request komplett (headers + body + timestamp), forwardar till din riktiga endpoint, och later dig soka i historiken och replay:a enskilda webhooks mot valfri destination. En binar, SQLite, inga externa beroenden.

## Target Audience

**Primar:** Solo-utvecklare och sma team (2-10 pers) som bygger mot webhook-drivna API:er (betalningar, CI/CD, e-post, e-handel) och behover kunna inspektera och replay:a webhooks utan att betala for en SaaS-plattform.

**Sekundar:** Backend-utvecklare i storre team som vill ha en lokal/staging-instans for webhook-debugging utan att ga genom organisationens procurement-process for Hookdeck/Convoy.

## Core Need

1. Se exakt vad en extern tjanst skickade -- komplett request med headers, body och metadata
2. Soka i webhook-historik efter source, endpoint, status, tidsperiod
3. Replay:a en specifik webhook mot lokal eller staging-miljo for att reproducera och felsoka
4. Kora lokalt utan molnkonto, per-event-kostnad eller extern dependency

## Why Now

- Webhook-drivna integrationer ar standard i modern SaaS-utveckling -- fler tjanster skickar webhooks an nagonsin
- Hookdeck har validerat att marknaden finns, men deras pricing ($39/mo for team) skapar utrymme for en self-hosted alternativ
- Developer tooling-trenden gar mot self-hosted och open-source (Supabase, Plausible, Umami)

## Why This Instead of Existing Tools

| Verktyg | Skillnad |
|---------|----------|
| **Hookdeck** | SaaS, per-event-pricing, konto kravs. Webhook Router ar self-hosted, gratis, ingen data lamnar din server. |
| **Convoy** | Enterprise-fokus, komplex setup (Go, Postgres, Redis). Webhook Router ar en binar + SQLite. |
| **Svix** | Fokuserar pa att *skicka* webhooks (webhook-as-a-service for SaaS-byggare). Webhook Router fokuserar pa att *ta emot och logga*. |
| **ngrok/smee** | Tunnelar for lokal utveckling, loggar inte persistent och har ingen replay. |
| **Applikationsloggar** | Kraver att du bygger loggning i varje app. Webhook Router sitter framfor appen och fangar allt. |

## Assumptions to Validate

1. Utvecklare forlorar faktiskt tid pa att felsoka webhook-leveranser och saknar en enkel metod for replay.
2. Self-hosted ar en riktig differentiator -- utvecklare valjer bort SaaS-verktyg for webhooks pa grund av kostnad, integritet eller setup-trosklar.
3. SQLite racker som lagringsbackend for den volym (hundratals till tusentals webhooks per dag) som en solo-/sma-team-setup genererar.
4. En CLI + enkel HTTP-admin-vy racker for MVP -- inget fullstandigt dashboard behover byggas.
5. Replay-funktionen ar killer feature -- utan den ar verktyget bara "en annan log viewer."

## MVP Scope

Vad forsta versionen ska gora:

- **Proxy-mode:** Ta emot webhooks pa konfigurerade paths, logga komplett request, forwarda till riktig endpoint
- **Loggning:** Spara varje webhook i SQLite med headers, body, source path, timestamp, forward-status
- **CLI inspect:** `hooklog list` -- visa senaste webhooks. `hooklog show <id>` -- visa detaljer for en specifik webhook
- **CLI replay:** `hooklog replay <id> --to http://localhost:8000/webhook` -- skicka om en webhook till valfri endpoint
- **Config:** YAML-fil som definierar routes (source path -> forward destination)
- **Self-contained:** En Python-process, SQLite-fil, inga externa beroenden utover stdlib + en HTTP-server

## Not in MVP

- Inget webb-dashboard (CLI racker for MVP)
- Ingen autentisering av inkommande webhooks (signature verification)
- Ingen retry-logik (forwarding ar fire-and-forget i MVP)
- Inga transformationer eller payload-manipulation
- Ingen rate limiting
- Ingen multi-tenant-support
- Inga notifikationer (Slack, e-post)
- Ingen Docker-image (kors direkt med Python)
- Inget plugin-system
- Inget stod for utgaende webhooks -- enbart inkommande

## Risks

- **Marknad** (score 2/5): Utvecklare kanske inte betalar for detta som produkt -- manga accepterar att webhook-debugging ar jobbigt utan att aktivt soka verktyg.
- **Teknik** (score 2/5): Proxy-logik och SQLite-lagring ar okomplicerat. Storsta tekniska risken ar att hantera concurrent requests korrekt.
- **Positionering** (score 3/5): Risk att forvanxlas med Hookdeck/Convoy trots att det ar en annan kategori. Messaging maste vara tydlig: "inte en webhook-plattform, utan en lokal audit log."
- **Adoption** (score 3/5): Self-hosted verktyg kraver att anvandaren sjalv driftar -- hogre trempel an SaaS.

## Suggested First Build

1. Enkel HTTP-server i Python (Flask eller bara http.server) som tar emot webhooks pa konfigurerade routes
2. Loggar varje request till SQLite
3. Forwardar till konfigurerad destination
4. CLI med `list`, `show`, `replay` kommandon
5. Testa med en riktig webhook-kalla (t.ex. GitHub webhook for ett test-repo)

## Cost Estimate

Uppskattat 40 000 SEK forsta aret. Lagen kostnad eftersom det ar en relativt smal implementation -- en HTTP-proxy med SQLite-lagring och CLI. Ingen infrastrukturkostnad (self-hosted hos anvandaren).

## Value Estimate

Uppskattat 120 000 SEK forsta aret genom sparad felsoknings- och utvecklingstid for utvecklare som integrerar mot webhook-drivna API:er. Replay-funktionen ensam kan spara timmar per incident.

## ROI

Uppskattat ROI: 200%, baserat pa 120 000 SEK i varde och 40 000 SEK i kostnad.

## Timeline

- **Vecka 1-2:** Bygg proxy-server, SQLite-loggning och basic forwarding. Testa med curl.
- **Vecka 3-4:** Bygg CLI (list, show, replay). Testa med riktig webhook-kalla (GitHub).
- **Vecka 5-6:** Kor i eget dev-flode. Utvardera: ar replay anvandbart? Ar loggningen tillracklig?
- **Vecka 7-8:** Visa for 2-3 andra utvecklare. Fraga: "Skulle du kora detta lokalt?"

## Notes

Projektet ar ompositionerat fran den ursprungliga framingen som intern infrastruktur for Project Vault-portfoljen. Den framingen var problematisk: cirkular vardelogik (bygga infra for projekt som inte finns an), enda konsumenten (Site Change Monitor) parkerad, och inte validerbar med externa anvandare.

Ny riktning: self-hosted webhook audit log for utvecklare. Eget varde, egen malgrupp, validerbar utan att andra projekt maste finnas.

Teknikval: Python, SQLite, YAML-config. Samma stack som ovriga CNS-projekt. Inga nya runtime-beroenden.
