# cns-analyst / quests

## 2026-05-27 — Förbättra riskschema med sannolikhet × påverkan

**Beskrivning:** Uppdatera CNS-schemat så att risker har `probability`, `impact`, `score` (probability × impact) och `mitigation` istället för en enkel 1-5 score. Uppdatera `project_schema.json`, `validator.py`, `md_parser.py` och `analyst.py`-prompten så Claude returnerar risker i det nya formatet. Uppdatera dashboard för att visa riskpoäng i projektdetaljsidan och Metrics-vyn.

**Impact:** Gör riskbedömningar meningsfulla och jämförbara mellan projekt. Claude kan ge skarpare riskförslag med motivering. Metrics-vyn kan visa total riskexponering per projekt. Baserat på befintlig Excel-modell (Sannolikhet × Påverkan = Riskpoäng).

**Status:** backlog

**Källa:** manuell — diskussion om risk-schema 2026-05-27

---

## 2026-05-27 — Validera CNS Analyst bulk-analys med 20 pending förslag

**Beskrivning:** Kör `cns analyze` mot scoring-studio (9 förslag), ai-ticket-triage (6 förslag) och cns-devwatch (5 förslag). Dokumentera precision, false positives och eventuella buggar i bulk-hanteringen. Detta validerar gårdagens implementation i verklig användning.

**Impact:** Validerar kärnfunktionalitet för CNS Analyst (ROI 400%) och låser upp godkännande av 20 förslag över tre projekt. Första riktiga användningstestet av ny bulk-analysfunktion.

**Status:** föreslagen

**Källa:** portfolio-brief

---

## 2026-05-31 — Implementera nytt riskschema i CNS Analyst

**Beskrivning:** Uppgradera riskvärdering från 1-5-skala till sannolikhet × påverkan-matris med mitigation-plan. Uppdatera schema/project-schema.ts, validators, parser och Claude-prompt enligt gårdagens quest-spec.

**Impact:** Direkt förbättring av analysverktyget som används aktivt (mvp-stage). Etablerar bättre riskbedömning för hela portföljen (400% ROI). Kan genomföras idag eftersom spec redan är definierad i gårdagens quest.

**Status:** föreslagen

**Källa:** portfolio-brief

---
