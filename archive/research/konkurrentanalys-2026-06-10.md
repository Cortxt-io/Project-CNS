> Research körd 2026-06-10. Mellanläge: ~10 egna websökningar + 3 fokuserade research-agenter (Backlog.md, GitHub Spec Kit, Linear) + återbruk av befintlig arkitektur-research ([cns-arkitektur-branschstandard](cns-arkitektur-branschstandard-2026-06-10.md)). Komplementär till den — fyller den explicit noterade luckan "ingen verifierad källa adresserade CNS helkoncept-positionering mot Linear/Notion/Productboard/Obsidian".

# Cortxt/CNS vs konkurrenter — positionering, feature-gap & nisch-validering

**Fråga:** Var står Cortxt/CNS mot konkurrenter? Är nischen redan tagen? Vad saknar CNS, och vad är unikt?

---

## Syntes (TL;DR)

Cortxt opererar på **två lager**, och de har helt olika konkurrenssituation:

1. **Exekverings-/work-lagret** (Markdown-i-git, AI-agenter via MCP, en-task-per-session, spec-först) är **trångt och redan löst — ofta mognare än CNS**. Backlog.md och GitHub Spec Kit gör i praktiken samma sak med 5,7k★ resp. 111k★, MIT, daglig releasekadens. Här bör CNS **inte** bygga om hjulet.

2. **Portfölj-/livscykel-lagret** (en emergent **nodgraf** över hela produkten — `kind` component/system/framework ur `part_of`, icke-blockerande `feeds`-dataflöde, stages idé→building→working→maturing) har **ingen direkt motsvarighet** i någon granskad konkurrent. Det är Cortxts faktiska, försvarbara differentiering.

**Nisch-validering:** Problemet "strukturera arbete så att AI-agenter kan agera på det" är **inte** oadresserat — det är 2026 års hetaste fält (Linear Agent, Spec Kit, Backlog.md, "issue trackers as agent infrastructure"). Men ingen kombinerar *lokalt-först/GitHub=sanning* + *emergent portfölj-/systemtopologi* + *solo-grundare-med-100-agenter-ekonomi*. Den specifika korsningen är ledig. Cortxts risk är inte att nischen är tagen — det är att projektet sprider energi på det trånga work-lagret istället för det lediga portfölj-lagret.

---

## Konkurrentlandskap (4 kategorier + fynd)

### A. Kommersiella issue-trackers som blir agent-infrastruktur — **Linear** (+ Jira, GitHub Projects)
Linear lanserade **Linear Agent** (public beta, mars 2026): delegera issues end-to-end, Triage Intelligence, hostad remote **MCP-server**, one-click code-agent-integrationer (Codex/Cursor/Copilot/Devin). OpenAI **Symphony** kör en Linear-board som agent-control-plane. Tesen "issue trackers *är* agent-infrastruktur" (persistent state + ownership + scope + queryable history) validerar CNS:s grundpremiss — men antar att substratet är en **central SaaS**, inte git. ([Linear Agent](https://linear.app/changelog/2026-03-24-introducing-linear-agent), [Linear MCP](https://linear.app/docs/mcp), [MindStudio: issue trackers as agent infra](https://www.mindstudio.ai/blog/issue-trackers-ai-agent-infrastructure-jira-linear))
- **Slår CNS på:** agent-mognad, färdiga integrationer, UX-driven datakvalitet, bevisad produktion (Symphony).
- **CNS slår Linear på:** lokalt-först/GitHub=sanning (ingen vendor-lock-in, git-historik = immutable agent-log), portfölj-/systemmodell (inte bara software-issues), och **ekonomin för solo + 100 agenter** — Linears per-seat-moln ($10–16/user/mån) är direkt fientligt mot 100 agent-"seats". ([pricing](https://linear.app/pricing))

### B. Markdown/git-native AI-task-verktyg — **Backlog.md** (närmaste konkurrenten)
"Project collaboration between humans and AI Agents in a git ecosystem." En `.md`-fil per task med YAML-frontmatter, kanban (terminal + web), **MCP-connector** för Claude Code/Codex/Gemini/Kiro/Cursor, 100% offline, MIT, **5,7k★ / 188 releaser** (senaste 2026-06-07). En-task-per-session, en-PR-per-task. ([github.com/MrLesk/Backlog.md](https://github.com/MrLesk/Backlog.md), [AGENTS.md](https://github.com/MrLesk/Backlog.md/blob/main/AGENTS.md))
- **Överlappar ≈70% av CNS work-modell** och är mognare där. Relationer: `dependencies` (blocking, cykelvaliderat) + `parent`/subtask + `milestone`.
- **Saknar helt:** portfölj-/system-/`kind`-nivå och icke-blockerande dataflöde (`feeds`). Modellerar *arbete*, inte *produktstruktur*. → Detta är exakt Cortxts differentiering.

### C. Spec-driven AI-orkestrering — **GitHub Spec Kit**
Spec→Plan→Tasks→Implement med artefakter (constitution.md, spec.md, plan.md, tasks.md). Tasks numreras `T001…` med `[P]`-parallellmarkörer och `[Story]`-etiketter. MIT, GitHub-ägt, **~111k★**, release 2026-06-09, 30+ agent-integrationer. ([github/spec-kit](https://github.com/github/spec-kit), [spec-driven.md](https://github.com/github/spec-kit/blob/main/spec-driven.md))
- **Komplement, inte konkurrent:** per-*feature* spec→kod-verktyg; ansvar slutar vid genererad kod. Ingen portfölj/graf/stage/drift. CNS sitter *ovanför* (livscykel).
- **Lärdom CNS kan låna:** Spec Kit:s beroenden är *implicita* (fasordning) — öppen [issue #1934](https://github.com/github/spec-kit/issues/1934) efterfrågar explicit `depends on` + DAG/wave, exakt det CNS designar för 100-agent-skala. CNS kan **leda** här. Återanvändbart: artefakt-kedjan constitution→spec→plan→tasks och task-formatet `T001 [P] [Story]` med exakt filväg.

### D. Lokalt-först kunskaps-/PKM-verktyg — **Obsidian** (+ TechDocs/Backstage)
Obsidian + plugins (Tasks, Kanban, obsidian-pm) ger lokalt-först Markdown-PM med grafvy och bidirektionella länkar, men det är **personlig kunskap/uppgifter**, inte en agent-styrd produktportfölj med typad topologi. Branschsignal från developer-portal-fältet: Backstage-YAML **"blir stale inom veckor för utvecklare uppdaterar inte filerna"** ([Cortex/Backstage-alt 2026](https://www.cortex.io/post/backstage-alternatives-what-engineering-leaders-need-to-know-in-2026)) — det är precis problemet CNS:s AI-underhållna `node.md` + GitHub=sanning svarar på. (Backstage-jämförelsen i detalj: se [cns-arkitektur-branschstandard](cns-arkitektur-branschstandard-2026-06-10.md).)

---

## Positioneringskarta (två axlar)

```
                 PORTFÖLJ-/SYSTEMTOPOLOGI (idé→drift, typad graf)
                              ▲
                              │   ● Backstage (men: deklarerad kind, blir stale)
                  ● Cortxt/CNS │
   (emergent kind, feeds,      │
    GitHub=sanning, 100 agenter)│
                              │
  LOKALT-FÖRST ───────────────┼─────────────────── CENTRAL SaaS
   (git = sanning)            │
              ● Backlog.md     │   ● Linear (Agent, Symphony)
              ● Obsidian-PM    │   ● Jira / GitHub Projects
              ● Spec Kit       │
                              │
                              ▼
                 PER-TASK / PER-FEATURE EXEKVERING
```
Övre vänstra kvadranten (portföljtopologi **+** lokalt-först) är gles — där bor Cortxt nästan ensamt. Backstage är närmast men sitter på central infra och brottas med stale YAML.

---

## Feature-gap-tabell

| Dimension | Linear | Backlog.md | Spec Kit | **Cortxt/CNS** |
|---|---|---|---|---|
| Lokalt-först / git=sanning | ✗ moln-SaaS | ✓ | ✓ | ✓ |
| AI-agent / MCP-integration | ✓✓ moget, brett | ✓ MCP, 5 agenter | ✓✓ 30+ agenter | ✓ MCP, egen agentur |
| Spec-först-flöde | delvis | ✓ | ✓✓ artefakt-pipeline | princip, ej verktygskedjat |
| Task-/dependency-modell | blocked/blocking + sub | blocking + parent + milestone | `T001`+`[P]`, implicit | designar explicit task-`depends_on` |
| **Portfölj-/systemnivå (kind)** | software-issues | ✗ | ✗ | **✓✓ emergent ur `part_of`** |
| **Icke-blockerande dataflöde (`feeds`)** | ✗ | ✗ | ✗ | **✓✓ unikt** |
| Livscykel/stages idé→drift | initiative→project | task→milestone | slutar vid kod | **✓✓ idea→maturing** |
| Persistent kunskapsgraf | moln-DB | ✗ (platt) | ✗ (isolerade specs) | **✓ ReactFlow-graf, GitHub** |
| Solo + 100 agenter-ekonomi | ✗ per-seat | ✓ (men platt) | ✓ (men per-feature) | **✓✓ designmål** |
| Mognad / community | hög, kommersiell | 5,7k★ MIT | 111k★ MIT | tidigt/internt |

(✓✓ = unik/ledande styrka; ✗ = saknas)

---

## Nisch-bedömning: är problemet redan löst?

- **Work-/exekveringslagret: JA, av mognare verktyg.** Backlog.md + Spec Kit löser markdown-i-git + MCP-agenter + spec-driven bättre och med community CNS inte har. Att tävla här är att förlora mot 111k★.
- **Portfölj-/livscykel-lagret: NEJ.** Ingen granskad konkurrent modellerar en *emergent, typad produkttopologi* (kind ur struktur, `feeds`-dataflöde) lokalt-först. Backstage är närmast men deklarerar typ explicit och lider av stale-YAML — vilket CNS:s AI-underhåll adresserar.
- **Korsningen lokalt-först × portföljtopologi × solo-100-agent-ekonomi är ledig.**

---

## Rekommendationer (3–5)

1. **Koncentrera värdet till nodgrafen, inte work-modellen.** Differentieringen är `kind`-emergens + `feeds` + idé→drift-livscykel. Work-taxonomin (ideas/issues/quests/projects/sessions) ger ingen försvarbar fördel mot Backlog.md — håll den minimal och låna mogna mönster i stället för att bygga om.
2. **Adoptera Spec Kit:s artefakt-format som quest-spec.** Återanvänd constitution→spec→plan→tasks och `T001 [P] [Story]`-formatet för CNS quest-engine i stället för egen uppfinning. Lågt risk, hög mognad.
3. **Led på explicit task-`depends_on` + DAG** där Spec Kit (#1934) och Backlog.md (bara blocking) släpar. Det är CNS:s 100-agent-tes och ett genuint försprång om det byggs.
4. **Gör "AI-underhållen, aldrig-stale topologi" till huvudbudskapet.** Branschen vittnar att docs-as-code-kataloger ruttnar (Backstage). CNS:s GitHub=sanning + agent-underhåll av `node.md` är ett konkret svar — positionera där, inte på "ännu en markdown-task-app".
5. **Konkurrera inte med Linear på integrationsbredd.** Linear vinner ekosystemet. CNS:s berättelse är *ägandeskap + portföljmodell + solo-agent-ekonomi* — låna deras mönster (status=handoff, comment=bus, history=context) men realisera dem i git.

---

## Kunskapsluckor / caveats
- Räknas Linear-agenter som betalda seats? Avgörande för solo-ekonomi-argumentet; ej verifierat mot Linears billing-docs.
- Backlog.md roadmap mot systemnivå (issue #237 antyder djupare spec, ej portföljmodell) ej fullt granskad.
- Symphony "+500% PR" är sekundärkälla (MindStudio), ej OpenAI-primärdata.
- CNS-sidan beskrevs utifrån projektkontext, inte verifierad mot live-backend i denna körning.

## Sources
- [Linear Agent (changelog)](https://linear.app/changelog/2026-03-24-introducing-linear-agent) · [Linear MCP](https://linear.app/docs/mcp) · [Linear conceptual model](https://linear.app/docs/conceptual-model) · [Linear pricing](https://linear.app/pricing)
- [MindStudio: issue trackers as AI agent infrastructure](https://www.mindstudio.ai/blog/issue-trackers-ai-agent-infrastructure-jira-linear) · [OpenAI Symphony on Linear](https://www.mindstudio.ai/blog/openai-symphony-spec-linear-agent-control-plane-500-percent-pr-increase)
- [Backlog.md (repo)](https://github.com/MrLesk/Backlog.md) · [Backlog.md AGENTS.md](https://github.com/MrLesk/Backlog.md/blob/main/AGENTS.md)
- [GitHub Spec Kit (repo)](https://github.com/github/spec-kit) · [spec-driven.md](https://github.com/github/spec-kit/blob/main/spec-driven.md) · [Spec Kit issue #1934 (explicit task deps)](https://github.com/github/spec-kit/issues/1934)
- [Obsidian](https://obsidian.md/) · [obsidian-pm](https://github.com/StepanKropachev/obsidian-pm)
- [Cortex: Backstage alternatives 2026 (stale-YAML)](https://www.cortex.io/post/backstage-alternatives-what-engineering-leaders-need-to-know-in-2026)
- Internt: [cns-arkitektur-branschstandard-2026-06-10.md](cns-arkitektur-branschstandard-2026-06-10.md)
