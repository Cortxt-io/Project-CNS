---
name: cns-sync
department: Program
description: Upptäck och flagga överlappande parallella sessioner på samma CNS-nod/quest innan du spolar ner arbete. Använd när användaren undrar om sessioner krockar/överlappar, frågar "vad har andra sessioner gjort på den här noden", "krockar det här", "syncar vi", innan en /cns-flush, eller när flera Claude Code-sessioner jobbat mot samma del och deras kontext börjar gå isär.
---

# /cns-sync — upptäck överlappande sessioner

Parallella sessioner konvergerar mot samma noder (se `/cns-flush`). Risken är att
två sessioner rör samma spår utan att veta om varandra och skriver över varandras
kontext. Den här skillen gör överlappet **synligt innan** du sparar — den läser
bara, den ändrar inget.

## När den ska köras
- **Före `/cns-flush`** — alltid, som ett gate-steg.
- När användaren misstänker att sessioner går isär eller frågar vad som gjorts på
  en nod.
- När du ska ta vid där en annan session slutade.

## Steg

1. **Bestäm spåret** att kolla: nod-slug eller quest-id (samma som `/cns-flush`
   steg 1).

2. **Hämta sessioner på spåret.** `cortxt_list_sessions(link_ref=<nod/quest>)`.
   Listan returneras nyast först och innehåller `status`, `summary`, `link`,
   `transcript_id`, `created_at`.

3. **Hitta pågående pass.** `cortxt_list_sessions(status="running")` — sessioner
   som fortfarande är `running` på samma `link_ref` är aktiv samtidighet. Då:
   - **Vänta** tills den flippar `done` innan du mergar — det är `/loop`-fallet:
     poll:a tills `status` blir `done`. (`running → done` är just den signal
     `session_store` är byggd för.)
   - Eller stäm av med användaren om de två passen ska slås ihop.

4. **Bedöm överlapp.** Flera `done`-sessioner på samma nod betyder inte
   nödvändigtvis konflikt — läs deras `summary`. Flagga bara där slutsatserna
   faktiskt rör samma beslut/yta och kan motsäga varandra.

5. **Rapportera.** Kort lägesbild:
   - Antal sessioner på spåret, varav `running`.
   - Vilka som överlappar i sak (med session-id + en rad ur summary).
   - Rekommendation: fortsätt till `/cns-flush`, vänta på ett pågående pass, eller
     förena två slutsatser först. Numrera valen.

## Förhållande till /cns-flush
`/cns-sync` är read-only och körs **före** `/cns-flush` (som skriver och pushar).
Sync hittar krocken; flush spolar ner det förenade resultatet.
