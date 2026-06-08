# project-vault-dashboard / decisions

## 2026-05-27 — Byt från GitHub Pages till Cloudflare Pages

**Beslut:** Deployer React SPA via Cloudflare Pages istället för GitHub Pages.

**Skäl:** GitHub Pages tillåter bara en Pages-publicering per repo. cortxt-repot behöver två separata custom domains (cortxt.io och app.cortxt.io). Cloudflare Pages stöder detta utan extra repos.

**Konsekvens:** deploy-landing.yml i cortxt kan inaktiveras. DNS för cortxt.io flyttad från Porkbun till Cloudflare nameservers.

---

## 2026-05-27 — HashRouter istället för BrowserRouter

**Beslut:** React Router konfigurerad med HashRouter (#/).

**Skäl:** Cloudflare Pages serverar statiska filer utan server-side routing. HashRouter kräver ingen _redirects-konfiguration för klientnavigering. En public/_redirects-fil läggs till som säkerhetsnät.

---

## 2026-05-27 — Ett Cloudflare Pages-projekt, två custom domains

**Beslut:** cortxt.io (landing) och app.cortxt.io (dashboard) är ett enda Cloudflare Pages-projekt med två custom domains, inte två separata projekt.

**Skäl:** Enklare att underhålla, en deploy-pipeline, ett repo.

---

## 2026-05-27 — Family-enum dual-mapping

**Beslut:** labels.js mappar både gamla och nya family-värden parallellt.

**Gamla värden (aktiva i project.md):** developer-tools, digest-pipeline, internal-monitoring, cns-core, ideas

**Nya värden (planerade):** monitoring-pipeline, cns-platform, ideas

**Skäl:** Migration av family-fältet i alla project.md-filer sker separat. Dashboard ska inte krascha under övergångsperioden.

---

## 2026-05-27 — Ingen MCP-integration i v1

**Beslut:** Dashboard konsumerar Railway REST API direkt. Ingen MCP-server i v1.

**Skäl:** Flask API:et exponerar redan rätt data via /api/projects och /api/project/<slug>/full utan auth. MCP är planerat som separat projekt ovanpå befintlig infrastruktur.
