# Beslut — Cortxt Dashboard App

## 2026-05-27 — HashRouter istället för BrowserRouter

**Beslut:** React Router konfigurerad med HashRouter (#/).

**Skäl:** Cloudflare Pages serverar statiska filer utan server-side routing. HashRouter kräver ingen server-config. En public/_redirects-fil läggs till som säkerhetsnät.

---

## 2026-05-27 — Railway REST API som datakälla, ingen MCP i v1

**Beslut:** Appen konsumerar Railway Flask API direkt. Ingen MCP-server i v1.

**Skäl:** Flask API:et exponerar redan rätt data utan auth. MCP planeras som separat projekt ovanpå befintlig infrastruktur.

---

## 2026-05-27 — Family-enum dual-mapping

**Beslut:** labels.js mappar både gamla och nya family-värden parallellt.

**Gamla värden:** developer-tools, digest-pipeline, internal-monitoring, cns-core, ideas
**Nya värden:** monitoring-pipeline, cns-platform, ideas

**Skäl:** Migration av family-fältet i project.md-filer sker separat. Appen ska inte krascha under övergången.

---

## 2026-05-27 — Inga edges i Reactflow graph v1

**Beslut:** Graph-vyn visar noder grupperade per family utan edges.

**Skäl:** Beroendekartan kräver maskinläsbar edge-data i project.md som inte finns än. Edges läggs till i v2.

---

## Cloudflare Pages-byte

**Beslut:** Deployer React SPA via Cloudflare Pages istället för GitHub Pages.

**Skäl:** GitHub Pages tillåter bara en Pages-publicering per repo. cortxt-repot behöver två separata custom domains (cortxt.io och app.cortxt.io). Cloudflare Pages stöder detta utan extra repos.

**Konsekvens:** deploy-landing.yml i cortxt kan inaktiveras. DNS för cortxt.io flyttad från Porkbun till Cloudflare nameservers.

---

## DNS-flytt: Porkbun → Cloudflare

**Beslut:** cortxt.io (landing) och app.cortxt.io (dashboard) är ett enda Cloudflare Pages-projekt med två custom domains, inte två separata projekt. DNS hanteras av Cloudflare (nameservers bytta från Porkbun 2026-05-27).

**Skäl:** Enklare att underhålla, en deploy-pipeline, ett repo. Cloudflare ger global CDN, HTTPS och noll driftkostnad.
