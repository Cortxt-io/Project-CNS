# Dashboard Views -- planerade vyer

## 1. Portfolio Overview (startsida)

**Syfte:** Ge besokaren en omedelbar bild av vad som byggts och vad som pagar.

**Innehall:**
- Sammanfattande siffror langst upp: antal projekt, total investerad tid/SEK, genomsnittligt ROI.
- Projektkort i grid-layout, sorterade efter `updated` (senast uppdaterade forst).
- Varje kort visar: titel, status (fargkodad badge), MVP-steg, ROI-procent.
- Klick pa kort -> detaljvy.

**Design:**
- Morkt tema, minimalistiskt.
- Max 3-4 kolumner pa desktop, 1 kolumn pa mobil.

---

## 2. ROI & Metrics (analysvyn)

**Syfte:** Visa aggregerad data -- hur mycket har jag investerat totalt, vad ar totalt varde, vilka projekt levererar bast ROI?

**Innehall:**
- ROI bar chart (horisontell, sorterad fallande).
- Kostnad vs. varde scatter plot.
- Statusfordelning (pie/donut).
- Topplista: "Basta ROI", "Hogsta varde", "Lagsta kostnad".

**Design:**
- Grafer renderade med Canvas API eller enkel SVG (ingen Chart.js i MVP for att halla zero-dependency).
- Alternativ: om zero-dep ar for tidskravande, tillat en liten lib (t.ex. Chart.js via CDN).

---

## 3. Project Detail (detaljvy)

**Syfte:** Visa fullstandig information om ett enskilt projekt.

**Innehall:**
- Titel + status + MVP-steg langst upp.
- Problemformulering och losning.
- Kostnads- och vardetabell.
- ROI-formel visuellt.
- Risker med fargkodade badges (gron/gul/rod baserat pa score).
- Tidslinje om tillganglig.
- Quest-state om aktivt (current_slice, next_steps).
- Lank tillbaka till oversikten.

**Design:**
- Enkel enspaltig layout.
- Lasbar typografi, god kontrast.

---

## 4. Status Filter (eventuell MVP+)

**Syfte:** Filtrera projekt baserat pa status eller tags.

**Innehall:**
- Filterrad langst upp med klickbara badges: All, Idea, Early MVP, MVP, Live, Shelved.
- Alternativt: enkel textfiltrering.

**Beslut:** Inte i MVP. Projekten ar tillrackligt fa for att oversikten racker. Lagg till nar det finns 15+ projekt.

---

## Navigationsstruktur

```
/ (Portfolio Overview)
/metrics (ROI & Metrics)
/project/:slug (Project Detail)
```

Implementeras med enkel hash-routing (`window.location.hash`) -- ingen router-lib behovs.
