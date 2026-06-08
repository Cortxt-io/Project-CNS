# Arkitektur -- Webhook Router

## Oversikt

Webhook Router ar en lattviktig HTTP-tjanst som fungerar som central knutpunkt for webhook-trafik inom Project Vault-portfoljen. Den tar emot inkommande webhooks, matchar mot routing-regler och vidarebefordrar till konfigurerade destinationer.

## Dataflode

```
Avsandare (t.ex. Site Change Monitor)
        |
        v
  [HTTP POST /webhook]
        |
        v
  [Routing-motor]
  Matchar event_type mot regler i routing-rules.yaml
        |
        v
  [Vidarebefordran]
  HTTP POST till destination_url
        |
   Misslyckad?
        |
        v
  [Retry-hanterare]
  Exponentiell backoff enligt regelkonfiguration
        |
        v
  [Loggning]
  Strukturerad logg av varje forsok (lyckad eller misslyckad)
```

## Komponenter

### Router (`src/router/`)
- HTTP-server som exponerar `/webhook`-endpointen
- Lasning och parsning av routing-regler fran YAML-konfiguration
- Matchning av inkommande event_type mot regler
- Vidarebefordran av payload till destination

### Retry (`src/retry/`)
- Exponentiell backoff-strategi
- Konfigurerbart antal forsok per regel
- Loggning av varje retry-forsok

### Loggning (`src/logging/`)
- Strukturerad loggning i JSON-format
- Loggar varje inkommande webhook, routing-beslut och leveransresultat
- Filbaserad loggning i MVP (ingen extern loggtjanst)

## Designbeslut

| Beslut                            | Val i MVP                           | Motivering                                     |
|-----------------------------------|-------------------------------------|-------------------------------------------------|
| Konfigurationsformat              | YAML-fil                            | Latt att lasa och redigera, inget behov av DB   |
| Matchningsstrategi                | Exakt event_type-matchning          | Enklast mojliga, tillrackligt for forsta fallet  |
| Retry-strategi                    | Exponentiell backoff                | Branschstandard, undviker overbelastning         |
| Loggformat                        | JSON till fil                       | Strukturerat, enkelt att soka i                  |
| Leveransprotokoll                 | HTTP POST                           | Universellt, tillrackligt for MVP               |

## Framtida utvidgningar (inte i MVP)

- Meddelandeko for asynkron leverans
- Wildcard/regex-matchning av event_type
- Fan-out (en webhook till flera destinationer)
- Webb-dashboard for leveransstatistik
- Persistent leveranshistorik i databas
