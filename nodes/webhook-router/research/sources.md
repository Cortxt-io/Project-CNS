# webhook-router / research

## Konkurrentlandskap

### Hookdeck
- **Typ:** SaaS event gateway
- **Pricing:** Free (10k events, 3 dagars retention), $39/mo (team), $499/mo (growth)
- **Styrkor:** Fullstandig plattform, retry, routing, transformation, monitoring
- **Svaghet for oss:** Per-event-pricing, konto kravs, data hos tredje part
- **URL:** https://hookdeck.com

### Convoy
- **Typ:** Open-source webhook gateway (Go)
- **Fokus:** Enterprise, bade skicka och ta emot
- **Krav:** Go, Postgres, Redis -- komplex setup
- **Styrkor:** SOC2/GDPR, rolling secrets, advanced endpoint management
- **Svaghet for oss:** For tungt for solo-dev/sma team
- **URL:** https://www.getconvoy.io / https://github.com/frain-dev/convoy

### Svix
- **Typ:** Webhook-sending-as-a-service
- **Fokus:** SaaS-byggare som vill skicka webhooks till sina kunder
- **Relevans:** Annan riktning -- vi fokuserar pa att *ta emot*, inte skicka
- **URL:** https://www.svix.com

### Hook0
- **Typ:** Open-source webhooks-as-a-service
- **Fokus:** Liknande Svix, utgaende webhooks
- **URL:** https://www.hook0.com

### ngrok / smee.io
- **Typ:** Tunnel for lokal utveckling
- **Relevans:** Exponerar lokal port, men loggar inte persistent och har ingen replay
- **Svaghet:** Inte tankt for audit/debugging, enbart for att ta emot under utveckling

## Var positionering

**Inte** en webhook-plattform. **Inte** en gateway. En **self-hosted audit log** for inkommande webhooks.

Nyckelskillnader:
1. Self-hosted -- ingen SaaS, ingen per-event-kostnad
2. En binar + SQLite -- ingen komplex setup
3. Replay -- reproducera exakt vad som skickades
4. Fokus pa inkommande webhooks -- inte outbound/sending

## Potentiella forsta anvandare

- Solo-utvecklare som bygger Stripe/GitHub/SendGrid-integrationer
- Sma team (2-10) med webhook-tunga applikationer
- Backend-utvecklare i storre team som vill ha lokal webhook-debugging
