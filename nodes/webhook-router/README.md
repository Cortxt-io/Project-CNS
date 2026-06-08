# Webhook Router

Intern webhook-router for Project Vault-portfoljen. Tar emot inkommande webhooks, matchar mot konfigurerbara routing-regler och vidarebefordrar till ratt destination med automatisk retry och strukturerad loggning.

## Status

**MVP-steg:** Hypothesis
**Primar konsument:** Site Change Monitor

## Projektstruktur

```
webhook-router/
├── project.md                          # Projektspecifikation
├── README.md                           # Denna fil
├── docs/
│   ├── architecture.md                 # Arkitekturbeskrivning
│   ├── configuration.md                # Konfigurationsguide
│   └── integration-guide.md            # Integrationsguide for konsumenter
├── src/
│   ├── router/                         # Routing-motor och regelhantering
│   ├── retry/                          # Retry-logik med exponentiell backoff
│   └── logging/                        # Strukturerad loggning
└── config/
    └── routing-rules.example.yaml      # Exempelkonfiguration
```

## Snabbstart

1. Kopiera `config/routing-rules.example.yaml` till `config/routing-rules.yaml`
2. Anpassa routing-regler for din miljo
3. Starta routern (instruktioner tillaggs nar implementationen ar klar)

## Dokumentation

- [Arkitektur](docs/architecture.md) -- overgripande design och dataflode
- [Konfiguration](docs/configuration.md) -- routing-regler och installningar
- [Integrationsguide](docs/integration-guide.md) -- hur konsumerande projekt kopplar in sig

## Beroenden i portfoljen

- **Site Change Monitor** -- forsta konsumenten, skickar andringshandelser via webhooks
- **Dev Changelog Engine** -- potentiell framtida konsument
- **AI Ticket Triage** -- potentiell framtida konsument
