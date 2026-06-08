---
quest_started: '2026-05-07'
quest_updated: '2026-05-07'
slug: webhook-router
---

## Current Slice

Self-hosted webhook audit log -- log, inspect, replay inkommande webhooks.

- HTTP-proxy som tar emot webhooks pa konfigurerade routes
- Loggar komplett request (headers + body + timestamp) till SQLite
- Forwardar till konfigurerad destination
- CLI: `list`, `show`, `replay` kommandon
- YAML-config for route-definitioner
- Testa med riktig webhook-kalla (GitHub)

## Next Steps

1. **Bygg proxy + loggning:** Minimal HTTP-server som tar emot, loggar och forwardar.
2. **Bygg CLI:** `list`, `show`, `replay` mot SQLite-databasen.
3. **Test med GitHub webhook:** Satt upp en riktig webhook fran ett test-repo, verifiera hela flodet.
4. **Utvardera:** Ar replay anvandbart i praktiken? Ar loggningen tillracklig for debugging?

## Not Now

- Webb-dashboard eller admin-UI
- Retry-logik (fire-and-forget i MVP)
- Signature verification for inkommande webhooks
- Payload-transformationer
- Multi-tenant-support
- Docker-image
- Rate limiting
- Notifikationer (Slack, e-post)
- Plugin-system
- Utgaende webhooks
- Hookdeck/Convoy-kompatibla API:er
