# cns-analyst / quests

## 2026-05-27 — Förbättra riskschema med sannolikhet × påverkan

**Beskrivning:** Uppdatera CNS-schemat så att risker har `probability`, `impact`, `score` (probability × impact) och `mitigation` istället för en enkel 1-5 score. Uppdatera `project_schema.json`, `validator.py`, `md_parser.py` och `analyst.py`-prompten så Claude returnerar risker i det nya formatet. Uppdatera dashboard för att visa riskpoäng i projektdetaljsidan och Metrics-vyn.

**Impact:** Gör riskbedömningar meningsfulla och jämförbara mellan projekt. Claude kan ge skarpare riskförslag med motivering. Metrics-vyn kan visa total riskexponering per projekt. Baserat på befintlig Excel-modell (Sannolikhet × Påverkan = Riskpoäng).

**Status:** backlog

**Källa:** manuell — diskussion om risk-schema 2026-05-27

---
