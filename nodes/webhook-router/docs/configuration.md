# Konfiguration -- Webhook Router

## Routing-regler

Routing-regler definieras i `config/routing-rules.yaml`. Se `config/routing-rules.example.yaml` for ett komplett exempel.

### Regelstruktur

Varje routing-regel bestar av foljande falt:

| Falt                | Typ       | Obligatorisk | Beskrivning                                      |
|---------------------|-----------|--------------|--------------------------------------------------|
| `name`              | string    | Ja           | Unikt namn for regeln                            |
| `description`       | string    | Nej          | Beskrivning av regelns syfte                     |
| `event_type`        | string    | Ja           | Event-typ att matcha mot (exakt matchning)       |
| `destination_url`   | string    | Ja           | URL att vidarebefordra webhook till               |
| `retry.max_attempts`| integer   | Nej          | Max antal retry-forsok (standard: 3)             |
| `retry.backoff_seconds` | list  | Nej          | Backoff-intervall i sekunder per forsok           |
| `timeout_seconds`   | integer   | Nej          | Timeout for HTTP-anrop till destination (standard: 10) |

### Exempel

```yaml
routes:
  - name: site-change-alerts
    description: Andringshandelser fran Site Change Monitor
    event_type: site_change.detected
    destination_url: "https://hooks.example.com/site-changes"
    retry:
      max_attempts: 3
      backoff_seconds: [5, 30, 120]
    timeout_seconds: 10
```

## Standardvarden

Om retry-installningar utelamnas anvands foljande standardvarden:

| Installning         | Standardvarde   |
|---------------------|-----------------|
| `max_attempts`      | 3               |
| `backoff_seconds`   | [5, 30, 120]    |
| `timeout_seconds`   | 10              |

## Miljovariabler

| Variabel             | Beskrivning                          | Standard          |
|----------------------|--------------------------------------|-------------------|
| `ROUTER_HOST`        | Host att lyssna pa                   | `0.0.0.0`         |
| `ROUTER_PORT`        | Port att lyssna pa                   | `8080`            |
| `ROUTER_CONFIG_PATH` | Sokvag till routing-rules.yaml       | `config/routing-rules.yaml` |
| `ROUTER_LOG_PATH`    | Sokvag till loggfil                  | `logs/router.log` |
| `ROUTER_LOG_LEVEL`   | Loggniva (DEBUG, INFO, WARNING, ERROR)| `INFO`           |
