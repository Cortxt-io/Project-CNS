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
