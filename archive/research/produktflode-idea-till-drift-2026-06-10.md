> Återskapad ur deep-research workflow wf_4f71e0f0-a97 (körd 2026-06-10 12:47).

# Hur kategoriserar och hanterar produktbolag arbetsflödet från idé till drift?

**Forskningsfråga:** Hur kategoriserar och hanterar större produktbolag och produktorganisationer sitt arbetsflöde från idé till drift? Kartlägg fyra saker med konkreta, källbelagda exempel på vedertagna ramverk och hur ledande bolag faktiskt arbetar: (1) Faskategorisering — hur arbetet delas in i faser som discovery/definition/delivery/drift, vad varje fas innehåller, och vedertagna ramverk (dual-track agile, double diamond, Shape Up, SAFe, lean product process). (2) Hur idéer och work items kategoriseras — taxonomi som epic/story/spike/initiative, idé vs bug vs feature, hur de taggar, scorar och sorterar i triage (RICE, opportunity scoring, MoSCoW). (3) Roller och ägarskap per fas — vem äger vad (product manager, product owner, solution/technical architect, QA lead, program/delivery manager, engineering lead) och hur ansvaret växlar mellan faser. (4) Grindar mellan faser — stage-gates, definition-of-ready, definition-of-done, acceptanskriterier, och hur mogna organisationer förhindrar att ospecificerat arbete glider direkt till implementation. Fokus på hur detta tillämpas i praktiken hos mjukvaru-/produktbolag, inte bara teori.

**Verifieringsmetod:** 24 claims verifierades med adversariell 3-rösters omröstning. 23 claims godkändes (3-0); 1 claim refuterades (0-3). Resultaten nedan är enstämmigt bekräftade påståenden.

---

## Sammanfattning

Mogna produkt- och mjukvarubolag delar arbetet från idé till drift i tydliga faser (discovery/definition → leverans → drift) och använder vedertagna ramverk för att styra flödet. Dual-track agile (Cagan/Patton/SVPG) kör en discovery-spår som validerar idéer via prototyper parallellt med ett delivery-spår som bygger releasebar mjukvara; Shape Up (Basecamp) sekvenserar shaping → betting → building i fasta sex-veckorscykler; Stage-Gate (Cooper) lägger Discovery plus fem stadier med formella beslutsgrindar; och Amazons Working Backwards använder PR/FAQ som forcing function före bygge. Idéer och work items kategoriseras och prioriteras med tekniker som WSJF (SAFe), och definition-of-ready/definition-of-done samt PR/FAQ-go/no-go fungerar som grindar som hindrar ospecificerat arbete att glida direkt till implementation. Ägarskap växlar per fas: i discovery jobbar PM/designer/lead engineer sida vid sida; i SAFe äger Product Manager ART-nivån (features, WSJF) medan Product Owner äger team-nivån (stories); i Shape Up shapas arbetet av en liten senior grupp och byggs av autonoma team. Underlaget vilar tungt på primärkällor (SVPG, Basecamp Shape Up-boken, Stage-Gate.com, Working Backwards) med enstämmig 3-0-verifiering.

---

## Bekräftade fynd (11 findings, 24 claims)

### 1. Faskategorisering — Dual-Track Agile (SVPG)

**Påstående:** Dual-Track Agile delar produktarbete i två parallella spår: ett discovery-spår som producerar, testar och validerar produktidéer (validerade backlog-items), och ett delivery-spår som omvandlar dem till releasebar mjukvara. Validering sker via prototyper UNDER discovery (inte efter release som i vattenfall), och den validerade prototypen fungerar som spec för delivery.

**Konfidensgrad:** Hög | **Röster:** 3-0 (4 claims)

**Källor:**
- https://www.svpg.com/dual-track-agile/
- https://www.productboard.com/glossary/dual-track-agile/

**Belägg:** SVPG (Cagan/Patton, primärkälla, originator): "The Discovery track is all about quickly generating validated product backlog items, and the Delivery track is all about generating releasable software." Samt "we focus on prototypes and validating those prototypes in Discovery... the prototype serves as the spec for Delivery... we are validating during Discovery" (kontrast mot vattenfall där validering sker efter release). Productboard bekräftar "research and product development in parallel". Enstämmigt verifierat (claims 0,1,18,19).

> **Refuterat påstående (0-3):** Att discovery formellt "överlämnar" en detaljerad prototyp som en grind till delivery — spåren är samtidiga och kollaborativa, inte ett vattenfall-handoff.

---

### 2. Roller/ägarskap — Discovery-trio (SVPG)

**Påstående:** Discovery-arbete är kollaborativt och ägs gemensamt av product manager, designer och lead engineer som jobbar sida vid sida — inte genom att varje roll lämnar artefakter vidare till nästa steg (SVPG:s trio/product-team-modell).

**Konfidensgrad:** Hög | **Röster:** 3-0

**Källor:**
- https://www.svpg.com/dual-track-agile/

**Belägg:** SVPG: "the work flow is not characterized by each role delivering artifacts on to the next step; rather it is collaborative – the product manager, designer and lead engineer are working together, side-by-side, to create and validate backlog items." Korroborerat av Productfolio, ProductPlan, Product-frameworks.com (claim 2).

---

### 3. Faskategorisering — Shape Up (Basecamp)

**Påstående:** Shape Up (Basecamp) strukturerar arbete i tre sekventiella faser: shaping (definiera arbetet på rätt abstraktionsnivå), betting (beslutsgrind där ett team binds till en cykel), building (autonomt teamexekvering). Shaping sker FÖRE något åtagande görs. Cykler är fasta sex veckor följt av två veckors cool-down.

**Konfidensgrad:** Hög | **Röster:** 3-0 (3 claims)

**Källor:**
- https://basecamp.com/shapeup/0.3-chapter-01
- https://basecamp.com/shapeup/2.3-chapter-09

**Belägg:** Primärkälla (Singer/37signals): "Shape the work, bet on it, and give it to a team to build." "Projects are defined at the right level of abstraction: concrete enough that the teams know what to do, yet abstract enough that they have room to work out the interesting details themselves." "Six weeks is long enough to finish something meaningful and short enough to feel the deadline." Cool-down + betting table efter varje cykel bekräftat i glossary. Enstämmigt (claims 3,7,9).

---

### 4. Roller/ägarskap — Shape Up (shaping vs. building)

**Påstående:** Shaping görs av en liten senior grupp som arbetar separat (parallellt med cykel-teamen) FÖRE projektet bettas och tilldelas ett team, vilket separerar definition från leverans. Building ger sedan fullt ansvar för att definiera uppgifter och justera scope till ett litet integrerat team av designers och programmerare — till skillnad från metoder där chefer styckar upp arbetet i förväg.

**Konfidensgrad:** Hög | **Röster:** 3-0 (2 claims)

**Källor:**
- https://basecamp.com/shapeup/0.3-chapter-01

**Belägg:** "A small senior group works in parallel to the cycle teams" och "we shape the work before giving it to a team." Teamet får "full responsibility... define their own tasks, make adjustments to the scope... completely different from other methodologies, where managers chop up the work and programmers act like ticket-takers." Enstämmigt (claims 4,6).

---

### 5. Grindar — Shape Up betting table

**Påstående:** Shape Ups "betting table" är en explicit grind: senior ledning (på Basecamp: CEO, CTO, en senior programmerare, en produktstrateg) beslutar vad man jobbar på varje cykel genom att granska shapade pitches mot fem kriterier (Spelar problemet roll? Är aptiten rätt? Är lösningen attraktiv? Är tajmingen rätt? Finns rätt folk tillgängliga?). Endast shapade pitches (nya eller specifikt återupplivade) övervägs — ingen backlog-grooming, inget separat godkännande-/valideringssteg. Detta hindrar oshapat arbete att flöda in i building.

**Konfidensgrad:** Hög | **Röster:** 3-0 (4 claims)

**Källor:**
- https://basecamp.com/shapeup/0.3-chapter-01
- https://basecamp.com/shapeup/2.2-chapter-08
- https://basecamp.com/shapeup/2.3-chapter-09

**Belägg:** "The decision to commit a team to a project for one cycle with no interruptions and an expectation to finish defines a bet." De fem frågorna citerade verbatim i kap 9. Kap 8: "Our betting table at Basecamp consists of the CEO... CTO, a senior programmer, and a product strategist... There is no step two to validate the plan or get approval." "The potential bets... are either new pitches shaped during the last six weeks, or possibly one or two older pitches... there is no grooming or backlog to organize." Enstämmigt (claims 5,8,15,16).

---

### 6. Grindar — Shape Up circuit breaker (fast appetite)

**Påstående:** Shape Up upprätthåller en fast aptit via en "circuit breaker": om ett team inte blir klart inom det bettade tidsboxen får projektet som standard ingen förlängning (en missad ship-date signalerar ett shaping-problem som ska reshapas för en framtida cykel).

**Konfidensgrad:** Hög | **Röster:** 3-0

**Källor:**
- https://basecamp.com/shapeup/2.2-chapter-08

**Belägg:** "Teams have to ship the work within the amount of time that we bet. If they do not finish, by default the project does not get an extension." Appetite definieras som "the amount of time we want to spend... as opposed to an estimate." (claim 17).

---

### 7. Faskategorisering & grindar — Stage-Gate (Cooper)

**Påstående:** Stage-Gate-modellen (Cooper) strukturerar innovationsarbete i Discovery/Ideation plus fem sekventiella stadier: Concept, Build the Business Case, Development, Testing and Validation, Launch. Mellan varje stadium sitter en Gate — en explicit beslutspunkt där verksamheten väljer om och hur den ska fortsätta investera (Go/Kill/Hold/Recycle), vilket fungerar som governance/grind.

**Konfidensgrad:** Hög | **Röster:** 3-0 (2 claims)

**Källor:**
- https://www.stage-gate.com/blog/the-stage-gate-model-an-overview/

**Belägg:** Primärkälla (Coopers organisation): "Discovery and Ideation" plus Stage 1 Concept, 2 Build the Business Case, 3 Development, 4 Testing and Validation, 5 Launch. "Preceding each Stage is a Gate – an explicit decision point where the business must choose whether and how to continue investing." Notera: sekundärlitteratur kallar ofta Stage 1 "Scoping" istället för "Concept" (etikettvariant, ej motsägelse). Enstämmigt (claims 10,11).

---

### 8. Grindar (mekanik) — Stage-Gate gate-komponenter

**Påstående:** Varje Stage-Gate utvärderar tre komponenter: Deliverables (definierade outputs från föregående stadium), Criteria (project readiness OCH project value), och Outputs (ett tydligt beslut och en överenskommen plan). Med förspecificerade deliverables och must-meet-kriterier hindrar grinden ospecificerat arbete från att avancera.

**Konfidensgrad:** Hög | **Röster:** 3-0

**Källor:**
- https://www.stage-gate.com/blog/the-stage-gate-model-an-overview/

**Belägg:** "Gate deliverables: Defined outputs from the previous Stage... Gate criteria... include both project readiness and project value... Gate outputs: A clear decision and an agreed plan. Typical outcomes are Go, Kill, Hold, or Recycle." Korroborerat av Wellspring, OCM Solution m.fl. (claim 12).

---

### 9. Grindar — Amazons PR/FAQ (Working Backwards)

**Påstående:** Amazons PR/FAQ (Working Backwards) är en forcing function i definitions-/discoveryfasen som tvingar idéupphovet att definiera produkten från kunden och bakåt INNAN bygge. Dokumentet itereras tills tillräckligt komplett, varpå ett explicit go/no-go-beslut fattas — vilket hindrar ospecificerat arbete att glida in i build (att de flesta PR/FAQs inte godkänns är "a feature, not a bug").

**Konfidensgrad:** Hög | **Röster:** 3-0 (2 claims)

**Källor:**
- https://workingbackwards.com/concepts/working-backwards-pr-faq-process/

**Belägg:** Bryar & Carr (ex-Amazon, författare till Working Backwards): "Writing a press release is a forcing function to ensure that the creator of the new product idea is focused on the customer." "At some point, a level of completion of the PR/FAQ document is reached, and a go, no-go decision can be made." Mötet avgör om idén behöver mer undersökning, är värd att bygga, eller ska läggas åt sidan — utan att binda mjukvaruresurser. Enstämmigt (claims 13,14).

---

### 10. Roller/ägarskap & prioritering — SAFe (PM vs. PO)

**Påstående:** I SAFe opererar Product Manager på Agile Release Train (ART)-nivå och ansvarar för att ART:en levererar lösningar som möter kund-, marknads- och affärsbehov; PM definierar och prioriterar features med Weighted Shortest Job First (WSJF). Product Owner arbetar på team-nivå med user stories och requirements (Team Backlog). Ansvaret är tudelat på två nivåer.

**Konfidensgrad:** Hög | **Röster:** 3-0 (2 claims)

**Källor:**
- https://www.aha.io/roadmapping/guide/product-development-methodologies/what-is-the-role-of-pm-in-safe

**Belägg:** Aha! (i linje med primärkällan Scaled Agile): PM "responsible for ensuring an ART delivers solutions that meet customer, market, and business demands"; "Product Owners work at the team level handling user stories and requirements, while product managers operate at the ART level." "Backlog Management – defining/prioritizing features using weighted shortest job first (WSJF) analysis." WSJF = Cost of Delay / Job Size (scaledagile.com). Matchar SAFe 6.0. Enstämmigt (claims 20,21).

---

### 11. Grindar — Definition of Ready & Definition of Done (Scrum)

**Påstående:** Definition of Ready (DoR) är en grind som anger kriterier ett product backlog item måste uppfylla innan teamet tar in det i en sprint, vilket hindrar oförberett arbete från att gå in i implementation. Definition of Done (DoD) är en delad teamförståelse för vad som gör ett item klart och fungerar som en kvalitetsgrind på output (om ett item inte möter DoD kan det inte släppas).

**Konfidensgrad:** Hög | **Röster:** 3-0 (2 claims)

**Källor:**
- https://resources.scrumalliance.org/Article/definition-vs-ready

**Belägg:** Scrum Alliance: DoR "outlines the criteria for a product backlog item to even be considered by the team for bringing into their sprint"; korroborerat av ScrumPLoP ("Ready gate"), Scrum.org, Mountain Goat. DoD "is a shared understanding among scrum team members of what it means for a PBI to be considered complete"; Scrum Guide: "describes the quality standards for the Increment." Enstämmigt (claims 22,23).

> **Caveat:** DoR är INTE i 2020 Scrum Guide (valfri/komplementär praktik, kan bli antimönster om den weaponiseras till vattenfall); DoD gäller strikt Increment men PBI-nivå-framing är vedertagen operativ användning.

---

## Källkvalitet och kaveater

**Källtyngd:** De flesta fynd vilar på auktoritativa PRIMÄRKÄLLOR (SVPG/Cagan, Basecamp Shape Up-boken av Singer, Stage-Gate.com/Cooper, Working Backwards av Bryar & Carr). SAFe- och Scrum-DoR/DoD-fynden vilar på SEKUNDÄRKÄLLOR (Aha!, Scrum Alliance) men matchar primärdoktrin (Scaled Agile, Scrum Guide).

**Tekniska noteringar:**
- WebFetch av svpg.com gav HTTP 403 — verifiering av dual-track-citaten skedde via WebSearch-utdrag plus korroborerande sekundärkällor, inte live-läsning av primärsidan.
- Etikettvariant: Stage-Gates Stage 1 kallas "Concept" i primärkällan men oftast "Scoping" i sekundärlitteraturen.

**Scope:** Basecamps betting-table-sammansättning (CEO/CTO/programmerare/strateg) och "inget grooming" är Basecamp-SPECIFIKT, inte branschuniversellt.

**Begränsning i underlaget:** Verifierade påståenden täcker Dual-Track Agile, Shape Up, Stage-Gate, Working Backwards, SAFe-roller/WSJF och DoR/DoD väl, men forskningsfrågans uttryckligen efterfrågade ramverk **Double Diamond** och **Lean Product Process**, samt taxonomierna epic/story/spike/initiative och prioriteringsteknikerna RICE/opportunity scoring/MoSCoW, fick **inga verifierade påståenden** — de bör behandlas som otäckta, inte motbevisade.

**Tidskänslighet:** Ramverken är stabila/kanoniska; SAFe-referensen matchar 6.0 (kontrollera mot senaste SAFe-version).

---

## Öppna frågor (ej täckta av detta underlag)

1. Hur ser den faktiska faskategoriseringen ut i Double Diamond (Discover/Define/Develop/Deliver) och Lean Product Process — inga verifierade påståenden samlades för dessa två uttryckligen efterfrågade ramverk.
2. Hur kategoriserar bolag work items i taxonomin epic/story/spike/initiative och idé vs bug vs feature i praktiken (t.ex. Jira/Linear-konventioner) — ej verifierat i detta underlag.
3. Hur tillämpas prioriterings-/scoringtekniker som RICE, opportunity scoring och MoSCoW i triage hos ledande bolag (utöver SAFe:s WSJF som täcktes)?
4. Hur ser drift-/operationsfasen (det fjärde steget "till drift") ut konkret — överlämning till operations, SRE/on-call, runbooks — utöver Stage-Gates Launch och Shape Ups building? Underlaget tunt på post-launch/drift.
