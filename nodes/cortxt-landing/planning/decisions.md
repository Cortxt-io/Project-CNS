# cortxt-landing / decisions

## 2026-05-27 — React + Vite istället för statisk HTML

**Beslut:** Landningssidan byggs med React 18 + Vite + Tailwind.

**Skäl:** Reactflow kräver React. Komponentstruktur gör det enkelt att iterera på sektioner. Vite ger snabb byggtid och modern toolchain.

---

## 2026-05-27 — Cloudflare Pages istället för GitHub Pages

**Beslut:** Deploy via Cloudflare Pages till cortxt.io.

**Skäl:** GitHub Pages tillåter bara en Pages-publicering per repo. cortxt-repot behöver två custom domains (cortxt.io och app.cortxt.io). Cloudflare Pages hanterar detta från ett enda projekt.

---

## 2026-05-27 — DNS flyttad till Cloudflare

**Beslut:** cortxt.io nameservers bytta från Porkbun till Cloudflare.

**Skäl:** Cloudflare Pages custom domain-setup kräver att DNS hanteras av Cloudflare, eller att CNAME-poster läggs till manuellt. Att flytta nameservers ger också gratis DDoS-skydd och CDN.
