> Deep-research wf_fa957667-ef0, körd 2026-06-10. 24 källor, 25/25 claims bekräftade 3-0, 9 findings efter syntes.

# CNS-arkitektur vs branschstandard — jämförande landskapsanalys

**Fråga:** Var avviker CNS (Central Node Store / Cortxt) från etablerad branschstandard, och vilka beprövade mönster/verktyg kan informera nästa steg? Fyra dimensioner: datamodell, repo/datalager, agentur (multi-agent), hela konceptet.

## Syntes (TL;DR)
CNS ligger nära branschstandard på det mesta men avviker tydligast på **emergent kind**, där Backstage (`apiVersion` + `kind` + `spec.type`) och C4 i stället kräver explicit deklarerad typ. På datamodell-, fil- och grafnivå gör CNS i stort sett samma sak som Backstage software catalog: docs-as-code YAML-frontmatter-filer (`node.md` ≈ `catalog-info.yaml`), graf med entiteter som noder och relationer som kanter, och nästan identisk relationsvokabulär (`part_of`/`depends_on` ≈ `partOf`/`dependsOn`) — så CNS uppfinner inte hjulet här. Multi-agent-delen avviker mest från state-of-the-art: mogna system (Anthropic, LangGraph) använder LLM-driven orchestrator-worker-delegering medan CNS `router.py` är regelbaserad regex-keyword-routing. Samtidigt är CNS fil-som-agent (Markdown + YAML) och modell-tier-routing/kostnadsgrindning väl i linje med vendor-praxis och Anthropics kostnadsvarningar (multi-agent ~15× dyrare), och sessioner med fork-träd har direkt motsvarighet i LangGraphs checkpoints/threads/forking.

## Caveats
Tidskänslighet: multi-agent-fältet rör sig snabbt; "~15× tokens" och "90,2 %-förbättringen" gäller en **bredd-först-research-eval med dynamisk LLM-lead/Sonnet-topologi**, INTE generellt "fler agenter vinner" och inte CNS keyword-router-design. Källkvalitet: ett claim (subagents-as-tools) fick *medium* för att exakt citat inte kunde verifieras ordagrant i den citerade PDF:en, men konceptet stöds av andra primära Anthropic-källor. Jämförelser mot CNS är analogier för inspiration, inte teknisk ekvivalens (C4 fyra fasta nivåer vs CNS fraktala djup; LangGraph grafexekveringsträd vs CNS sessionsträd). Notabelt gap: ingen verifierad källa adresserade direkt CNS helkoncept-positionering mot Linear/Notion/Productboard/Obsidian-PKM; Backstage var enda nära jämförbara namngivna produkt som faktiskt verifierades.

## Findings (9 st, alla 3-0-verifierade)

### 1. Emergent kind är den tydligaste avvikelsen — branschen deklarerar typ explicit
**Confidence:** high · **Vote:** 3-0
Backstage identifierar entitetstyp via obligatoriskt `kind`-fält + `spec.type` (required för Component/Resource) och stödjer custom kinds via namespacad `apiVersion` (`my-company.net/v1`) — explicit deklaration + versionerad namespacing, inte strukturell emergens. C4-notationen säger ordagrant: "The type of every element should be explicitly specified". Ingen ledande modell använder emergent typ → genuin CNS-avvikelse (inte nödvändigtvis fel, men ovanlig).
**Källor:** backstage.io/docs/features/software-catalog/extending-the-model · descriptor-format · c4model.com/diagrams/notation · c4model.com

### 2. På datamodell-/fil-/grafnivå följer CNS branschstandard ~1:1 — uppfinner inte hjulet
**Confidence:** high · **Vote:** 3-0
Backstage definierar entiteter i YAML-filer (`catalog-info.yaml`) med envelope `apiVersion/kind/metadata/spec` — direkt jämförbart med `node.md` + YAML-frontmatter. Katalogen byggs som "a graph using descriptors as nodes and relations as edges". Relationsnamnen praktiskt identiska: `partOf`/`hasPart`, `dependsOn`/`dependencyOf` mot CNS `part_of`/`depends_on` (bara camelCase vs snake_case skiljer).
**Källor:** backstage.io descriptor-format · creating-the-catalog-graph · github.com/backstage

### 3. C4:s zoombara nestning ≈ CNS part_of-nesting, men C4 är fast på fyra nivåer
**Confidence:** high · **Vote:** 3-0
C4 = "A set of hierarchical diagrams — system context, containers, components, code" med zoom-metafor. Båda uttrycker containment/nesting. Skillnad: C4 är preskriptivt fast på fyra nivåer; CNS fraktala modell är friare men saknar C4:s standardiserade abstraktionsnivåer och publikanpassning.
**Källor:** c4model.com · c4model.com/diagrams/notation

### 4. GitHub-som-databas är välunderbyggt — Dolt är moget alternativ vid flaskhals
**Confidence:** high · **Vote:** 3-0
GitHubs dokumentation bekräftar att man "could technically do just about anything that Git can do without having Git installed" via raw-objekt + branch-refs — validerar CNS skrivning förbi Railways efemära disk. Dolt versionerar tabeller i stället för filer ("Git versions files. Dolt versions tables") med fork/clone/branch/merge. Riskerna för CNS handlar om **rate limits, latens och query-förmåga** — inte om mönstret är osunt.
**Källor:** docs.github.com/rest git-database-api · github.com/dolthub/dolt

### 5. Regex-keyword-routing är största avvikelsen i multi-agent-delen
**Confidence:** high · **Vote:** 3-0 (medium på exakt citat för subagents-as-tools)
Anthropic: lead-agenten "analyzes, develops a strategy, and spawns subagents" och "uses reasoning to decompose queries". Mogna hierarkiska system behandlar subagenter som verktyg via tool-calling — LLM bestämmer routing on the fly, motsatsen till regex-keyword. CNS regelbaserade router är billigare och deterministisk men mindre adaptiv.
**Källor:** anthropic.com/engineering/multi-agent-research-system · Building Effective AI Agents (PDF)

### 6. Fil-som-agent (Markdown + YAML + modell-tier) är etablerat vendor-mönster
**Confidence:** high · **Vote:** 3-0
Claude Codes officiella dok: "Subagents are defined in Markdown files with YAML frontmatter" med fält som name/description/model — direkt parallellt med CNS per-agent-Markdownfiler med Haiku/Sonnet/Opus-tier i frontmatter.
**Källor:** code.claude.com/docs/en/sub-agents

### 7. Modell-tier-routing & kostnadsgrind ligger i linje med Anthropics rekommendationer
**Confidence:** high · **Vote:** 3-0
Anthropic: agenter ~4× mer tokens än chat, multi-agent ~15×; "simple queries shouldn't trigger expensive multi-agent workflows". Multi-agent slog single-agent med 90,2 % men ENBART på bredd-först-research med Opus-lead/Sonnet-subagenter, och hjälper INTE när agenter delar kontext. Validerar CNS kostnadsgrind + tiers — men inte automatiskt 22 agenter.
**Källor:** anthropic.com/engineering/multi-agent-research-system · Building Effective AI Agents (PDF)

### 8. Sessioner-som-förstklassiga-objekt med fork-träd ≈ LangGraph checkpoints/threads
**Confidence:** high · **Vote:** 3-0
LangGraph sparar "a snapshot of the graph state at every step", organiserat i threads, och stödjer "fork the graph state at arbitrary checkpoints" via prior `checkpoint_id`. Samma mönster som CNS pollbara running→done-signal och fork-träd — ett moget, branschvaliderat sätt att göra tillstånd/sessioner persistenta och förgreningsbara.
**Källor:** docs.langchain.com/oss/python/langgraph/persistence

### 9. Anthropics agent-loop + subagent-motivering är referensmönster att mäta agenturen mot
**Confidence:** high · **Vote:** 3-0
Anthropic anger "gather context, take action, verify work, repeat" som agent-loopens kärna och motiverar subagenter med två skäl: parallellisering + kontexthantering (isolerade context windows, skickar bara relevant info tillbaka). **Verify-steget** framhålls för tillförlitlighet — något en regelbaserad router inte i sig ger.
**Källor:** anthropic.com/engineering/building-agents-with-the-claude-agent-sdk

## Öppna frågor (researchen lämnade dessa)
1. Finns ett namngivet etablerat mönster för emergent/strukturhärledd typ (RDF/property-graphs, ECS), eller är CNS emergent kind genuint ovanligt? Materialet visar bara att de ledande verktygen INTE gör det.
2. Vad är CNS unika positionering mot Linear/Notion/Productboard och Obsidian-baserade PKM-workflows? Endast Backstage verifierades som nära jämförelse.
3. Var går CNS reella skalgräns för GitHub-API-som-databas (rate limits, latens, query-behov) innan en riktig DB eller Dolt-liknande lösning behövs?
4. Skulle en hybrid-router (regex-prefilter + LLM-fallback för tvetydiga prompts) ge bättre träffsäkerhet än ren keyword-routing utan att förlora determinism och kostnadskontroll?

## Statistik
5 sökvinklar · 24 källor hämtade · 111 claims extraherade · 25 verifierade · 25 bekräftade · 0 dödade · 9 findings efter syntes · 106 agentanrop.

## Källor (urval, primära)
- Backstage software catalog: descriptor-format, extending-the-model, creating-the-catalog-graph
- C4: c4model.com, /diagrams/notation
- GitHub Git Database API; github.com/dolthub/dolt
- Anthropic: multi-agent-research-system, building-agents-with-the-claude-agent-sdk, "Building Effective AI Agents" (PDF)
- LangGraph persistence; code.claude.com/docs/en/sub-agents
