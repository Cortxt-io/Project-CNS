<!--
Konsolidering: denna kontrollplan-skiss föddes i en parallell Claude-session
(transcript 18d804bc, 2026-06-11 — "vad innebär installationen / Railway-GitHub-Linear-Vercel-topologin")
och flätades in i huvudspåret (transcript b14c794b) 2026-06-11. Skissens tre öppna
byggsteg är fångade som issues: #77 (per-nod integrations-fält, foundational),
#78 (Vercel-driftsadapter, depends-on #77), #79 (modell-router). Distinktionen
GitHub=ryggrad vs ekrar lever även som minnet `integration-ryggrad-vs-ekrar`.
Tidigare löst fil i arbetsytans rot; nu GitHub-sanning i repot.
-->

# Cortxt — arkitektur-sketch (kontrollplan)

> Konceptuell helhetsbild, inte teknisk spec. Från intention (botten) till kundmöte (toppen),
> med state/compute/ekrar på rätt axlar. Uppdatera när Vercel-adaptern och modell-routern faktiskt byggs.

```
                          ╔═══════════════════════════════════════════╗
   PRODUKTYTA             ║   Shopify headless   ·   (fler källor →)   ║   ← möter kund
   (runtime, mot kund)    ║              konsumeras av                 ║
                          ║   ┌─────────────────────────────────┐     ║
                          ║   │   Vercel  (driftslager)          │     ║   storefronts KÖR här
                          ║   │   storefront-deploys per produkt │     ║
                          ║   └─────────────────────────────────┘     ║
                          ╚════════════════▲══════════════════════════╝
                                           │ deploy + status
                                           │ (CNS agerar)
   ╔═══════════════════════════════════════╪═══════════════════════════════════════╗
   ║  NAVET — kontrollplan                  │                  ▸ molnagenter         ║
   ║                                        │                    (GitHub Action,    ║
   ║         ┌──────────── COMPUTE ─────────┴──────────┐         @claude, router)   ║
   ║         │   Railway                                │                            ║
   ║         │   Flask / MCP-backend  = AKTÖREN         │ ◀── modell-router (framtid)║
   ║         └──┬───────────────────────────────────┬──┘     väljer nivå per arbete ║
   ║            │ läs/skriv                 läs/skriv │                              ║
   ║     ┌───── STATE (flyktigt) ─────┐   ┌───── STATE (durabelt) ─────┐            ║
   ║     │  Redis                     │   │  GitHub  =  SANNING         │            ║
   ║     │  leases · sessioner ·      │   │  noder · issues · PR ·      │            ║
   ║     │  eventstream · arbetsminne │   │  quests · långtidsminne     │            ║
   ║     └────────────────────────────┘   └─────────────────────────────┘            ║
   ║                                                                                  ║
   ║     Linear  ──┐ (eker: hänger av backenden, inget beror på den)                 ║
   ╚═══════════════╪══════════════════════════════════════════════════════════════════╝
                   │  intention reser uppåt-in ▲
   ┌───────────────┴──────────────────────────────────────────────────────────────┐
   │  DET LOKALA   (krymper → membran)                                              │
   │  din maskin · Claude-sessioner · CNS-repot lokalt · där du formulerar          │
   └──────────────────────────────────▲────────────────────────────────────────────┘
                                       │
   ┌───────────────────────────────────┴────────────────────────────────────────────┐
   │  JAG (Rikard)   — intention / riktning · stackens mynning, inte dess golv        │
   └──────────────────────────────────────────────────────────────────────────────────┘
```

## Två rörelser som möts i navet
- **Intention uppåt-in:** Jag → det lokala → Railway-backenden (aktören).
- **Värde uppåt-ut:** Navet → Vercel → Shopify → kund.

Navet (Railway-compute + GitHub/Redis-state) är **gångjärnet** där en människas vilja blir produkt.

## Axlarna att hålla isär

| Axel | Vad | I bilden |
|------|-----|----------|
| **Compute** | aktören som gör något | Railway-backenden (Flask/MCP) |
| **State** | minnet aktören verkar på | Redis (flyktigt) ∥ GitHub (durabelt) — syskon, ej staplade |
| **Eker** | perifert, underordnat | Linear (hänger av backenden) |
| **Drift** | var produkten kör | Vercel → Shopify ovanpå |

## Nyckeldistinktioner (varför bilden ser ut så)
- **GitHub är ryggrad, inte en eker.** Sanningen; djupt inbyggt (git_ops, issues, PR, webhook). Ska inte pressas in i ett generiskt adapter-interface.
- **Redis och GitHub är samma sorts sak — state — vid två ändar av en durabilitetsskala.** Redis = korttidsminne, GitHub = långtidsminne. Railway sitter emellan.
- **Linear är den enda genuint underordnade** av de tre — en eker, envägs, inget beror på den.
- **Vercel underligger Shopify** — Vercel är driftslager (storefronts kör där), Shopify är en datakälla storefronten konsumerar i runtime. CNS bygger en **Vercel-driftsadapter**, inte ett Shopify-integrationslager.
- **Det lokala krymper till ett membran** när molnagenter + modell-router flyttar arbetet upp i navet. Människan blir stackens mynning, inte dess golv.

## Öppna byggsteg som bilden pekar mot
1. **Per-nod `integrations`-fält** i nodmodellen — skilj **drift** (`deploy: vercel`, CNS agerar) från **källor** (`sources: [shopify:store-x]`, CNS bär bara konfig vidare). Saknas helt idag; blockerar Vercel/Shopify. → **issue #77** (foundational).
2. **Vercel-driftsadapter** (`connect / deploy / status`) — definiera adapter-formen utifrån Vercel + Linear samtidigt, inte abstrakt i förväg. Lämna GitHub-ryggraden ifred. → **issue #78** (depends-on #77).
3. **Modell-router** som backend-funktion (`route(work) → modellnivå`), deklarativ på nodens `agentur`/`work`-fält — kodifierar den manuella kostnadsgrinden (Haiku mekaniskt / Sonnet omdöme / toppmodell syntes). → **issue #79**.
