# Integrationsguide -- Webhook Router

Denna guide beskriver hur ett projekt i Project Vault-portfoljen kopplar in sig mot Webhook Router for att skicka webhooks.

## Oversikt

For att anvanda Webhook Router behover ditt projekt:

1. Definiera vilka handelser (event_type) som ska skickas
2. Lagga till en routing-regel i routerns konfiguration
3. Skicka HTTP POST till routerns webhook-endpoint

## Steg 1: Definiera handelser

Bestam vilka handelser ditt projekt ska skicka. Anvand namespaced event_type-namn:

| Projekt               | event_type-prefix      |
|------------------------|------------------------|
| Site Change Monitor    | `site_change.*`        |
| Dev Changelog Engine   | `changelog.*`          |
| AI Ticket Triage       | `ticket.*`             |

Exempel pa event_type-namn:
- `site_change.detected` -- en andring har detekterats
- `site_change.error` -- ett fel uppstod vid overvakning

## Steg 2: Lagg till routing-regel

Lagg till en regel i `config/routing-rules.yaml`:

```yaml
routes:
  - name: mitt-projekt-handelse
    description: Beskrivning av vad regeln gor
    event_type: site_change.detected
    destination_url: "https://min-destination.example.com/hook"
    retry:
      max_attempts: 3
      backoff_seconds: [5, 30, 120]
    timeout_seconds: 10
```

## Steg 3: Skicka webhook

Skicka en HTTP POST till routerns webhook-endpoint:

```
POST /webhook
Content-Type: application/json

{
  "event_type": "site_change.detected",
  "timestamp": "2026-05-02T10:30:00Z",
  "source": "site-change-monitor",
  "payload": {
    "url": "https://example.com",
    "change_type": "content_modified",
    "diff_summary": "Titeln andrades fran 'Gammal' till 'Ny'"
  }
}
```

### Obligatoriska falt i webhook-payload

| Falt          | Typ       | Beskrivning                                      |
|---------------|-----------|--------------------------------------------------|
| `event_type`  | string    | Handelsetyp som matchar mot routing-regler        |
| `timestamp`   | string    | ISO 8601-tidsstampel                              |
| `source`      | string    | Namn pa avsandande projekt                        |
| `payload`     | object    | Projektspecifik data (godtycklig struktur)        |

### Svar fran routern

| HTTP-status | Betydelse                                  |
|-------------|---------------------------------------------|
| `200 OK`    | Webhook mottagen och vidarebefordrad         |
| `202 Accepted` | Webhook mottagen, leverans pagar (retry) |
| `400 Bad Request` | Ogiltig payload (saknar obligatoriska falt) |
| `404 Not Found`   | Ingen matchande routing-regel              |
| `500 Internal Server Error` | Internt fel i routern          |

## Exempel: Site Change Monitor

Site Change Monitor skickar webhooks nar en overvakad sida andras:

```python
import requests
import datetime

webhook_payload = {
    "event_type": "site_change.detected",
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    "source": "site-change-monitor",
    "payload": {
        "url": "https://competitor.example.com/pricing",
        "change_type": "content_modified",
        "sections_changed": ["pricing-table", "footer"],
        "diff_lines": 12
    }
}

response = requests.post(
    "http://localhost:8080/webhook",
    json=webhook_payload
)
```
