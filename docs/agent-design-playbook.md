# AI-agentur-mönster — Agent Design Playbook

> Senast verifierad: 2026-06-09. Baserad på research mot 22 oberoende källor.
> Flytta till GitHub Wiki när den är initierad: `wiki/Agent-Design-Playbook`

## Syfte

Referenskontext för HR-chefen (ny agent designas), Tränaren (agents prompt diagnostiseras) och Teamleadern (koordinationsstrategin väljs). Läs innan du designar ett agentteam.

---

## Sammanfattning

Multi-agent-system domineras 2026 av tre kommunikationsprotokollar (MCP, A2A, ACP) som löser olika lager av koordination, och de starkaste produktionsarkitekturerna konvergerar mot supervisor-topologin med en nivå delegering. Forskning på 1 642 exekveringsspår (MAST-studien) visar att 36,9 % av alla agentfel beror på koordinationsproblem, inte kapabilitetsproblem — vilket bekräftar att roller och gränser är viktigare än råkapacitet. CNS:s nuvarande design med Teamleader som orchestrator, MCP-tools för koordination och isolerade specialistroller är i linje med bästa praxis, men saknar explicit retry-logik, rollvalidering och tydliga handoff-kontrakt.

---

## Kommunikationsmönster

| Mönster | Beskrivning | Fördelar | Nackdelar | Passar CNS |
|---------|-------------|----------|-----------|------------|
| **Direkt meddelande** | Agent A anropar Agent B synkront | Enkelt, deterministiskt | Tätt kopplat, bryter om mottagaren är nere | Nej — agenter är sessionsisolerade |
| **Delat tillstånd** | Agenter läser/skriver till gemensamt lager | Löst kopplat, asynkront, persistent | Konflikter vid parallella skrivningar | **Ja** — session-store + idea-inbox i CNS |
| **Meddelandeköer** | Agenter producerar/konsumerar events | Skalbar, retrybar, audit-trail | Kräver infrastruktur | Delvis — GitHub Issues fungerar som kö |
| **MCP** | Standardlager mot tools/data, agent→server | Universal tooling, vendor-agnostisk, Linux Foundation | Löser inte agent-till-agent | **Ja** — CNS har 21 MCP-tools |
| **A2A** | Google-protokoll för cross-agent delegation, Apache 2.0 | Öppen standard, OAuth2+JWT, 50+ partners | Overkill inom samma runtime | Framtida — relevant om CNS agenter exponeras externt |
| **ACP** | IBM Research, REST-nativt | Framework-agnostisk | Lägre momentum än A2A | Nej — för tungt |

**CNS-slutsats:** MCP + delat tillstånd är rätt lager idag. A2A är relevant om CNS exponerar agenter mot externa system.

---

## Frameworks-jämförelse

| Framework | Arkitektur | Styrka | Svaghet | CNS-relevans |
|-----------|-----------|--------|---------|--------------|
| **LangGraph** | StateGraph — noder + kanter, delat state | Stateful, checkpointing, human-in-the-loop | Lärandetröskel, verbose | Medium — bra referens för state-design |
| **CrewAI** | Roll-baserat team, crews = projekt | Snabbast setup, intuitiv rollmodell | Begränsad kontroll av ordning | **Hög** — CNS-roller liknar CrewAI konceptuellt |
| **AutoGen** | Konversationsbaserat, agents chatar | Flexibelt, dynamisk rollfördelning | Svårare att förutsäga, hög token-kostnad | Låg — CNS behöver deterministiska flöden |
| **OpenAI Swarm** | Lightweight, handoffs-baserat | Enkelt att förstå | Experimentellt, ingen state-persistence | Låg — läs koden för inspiration |
| **CAMEL** | Roll-par: assistant + user agent | #1 på GAIA-benchmark | Akademisk, smal produktionshistorik | Låg — referens för rolldesign |
| **Claude Code Subagents** | `.claude/agents/*.md`, supervisor→subagent | Native i CNS-runtime, isolerad context | Max 1 delegationsnivå rekommenderas | **Hög** — CNS körs redan i detta system |

**2026-konsensus:** Supervisor-topologin är produktionsdefault. CNS:s design är korrekt.

---

## Anti-patterns att undvika

**1. Okontrollerad rekursiv spawn**
Agent A misslyckas → triggar B → anropar A → oändlig loop. MAST: koordinationsfel = 36,9 % av alla fel.
*Fix:* Max 3 retries, exponential backoff, GitHub Issue `agent/stuck` som dead-letter-kö.

**2. Rollkonfusion**
En "planner"-agent som börjar skriva kod. Frekvens: 41,77 % av spec-problemen i MAST.
*Fix:* Varje agent deklarerar sina avsedda åtgärder innan exekvering. Teamleader kontrollerar.

**3. Kontextexplosion**
En session kan växa från 15k till 156k tokens. Multi-agent-system konsumerar upp till 15× fler tokens än enkel chatt.
*Fix:* Orchestratorn skickar minimal, uppgiftsspecifik kontext — aldrig full historik.

**4. Parallellism som kontextkringgång**
Dela inte upp ett jobb bara för att det "är för stort".
*Fix:* Parallellism motiverat när uppgifterna är genuint oberoende OCH tidsbesparing väger tyngre.

**5. Saknat verifieringssteg**
Agenten som utför arbetet kan inte granska sitt eget resultat.
*Fix:* Separat antagonistiskt verifieringsanrop som försöker motbevisa resultatet.

**6. Flat team utan orchestrator**
Alla agenter på samma nivå — ingen tar ansvar ("orchestration void").
*Fix:* Alltid orchestrator + specialister.

**7. Agent-bloat**
Fler agenter = fler koordinationspunkter = fler felkällor. 2–5 väldefinierade agenter slår ofta 20 smala.
*Fix:* Om två agenter aldrig kommunicerar direkt och gör liknande saker — slå ihop dem.

---

## Google A2A-protokollet

Google lanserade A2A (Agent2Agent) april 2025, donerade till Linux Foundation juni 2025 (Apache 2.0). Löser cross-vendor agent-koordination via Agent Cards (capability-manifest), standardiserade Task-objekt och OAuth 2.0 + JWT.

MCP = vertikal integration (agent → tools). A2A = horisontell integration (agent ↔ agent, cross-vendor). Komplement, inte konkurrenter.

**CNS nu:** Inte akut. **CNS framtid:** Relevant om Cortxt exponerar agenter externt.

---

## Rekommendationer för CNS

| # | Rekommendation | Prioritet |
|---|---------------|-----------|
| R1 | Behåll supervisor-topologin — Teamleader (Opus) som orchestrator | Klar ✓ |
| R2 | Inför retry-logic: max 3 försök, backoff, `agent/stuck` issue som dead-letter | Hög |
| R3 | Minimera kontext-payload per subagent — aldrig full sessionshistorik | Hög |
| R4 | Parallellism med kostnadskalkyl — forskningsledare + teknisk-skribent OK, backend + scripts på samma fil NEJ | Medium |
| R5 | Agent Card-format: lägg till `capabilities:` i varje `.claude/agents/*.md` | Medium |
| R6 | Adversarial verification för research och specs — self-check: "3 ways this could be wrong" | Medium |
| R7 | Håll aktiva agenter vid 7–10 — kärna: Teamleader + 6 specialister, stödroller vid behov | Låg |

---

## Onboarding-pelarna (bemanning av en ny agent)

När en roll bemannas (`/bemanna`-skillen) gäller fyra pelare, grindade av `scripts/validate_agent.py`:

1. **Systemprompt = DNA.** Numrerat task-flow (viktigast), skarpa gränser, "verifiera X innan
   nästa steg", rollkonfusionsskydd (deklarera åtgärder före exekvering). Lägg ej manualer i
   prompten; övergeneralisera/överspecificera inte.
2. **Verktyg = least privilege (Zero Trust).** Minsta nödvändiga MCP-verktyg, read-first,
   destruktiv-op-skydd, minimal kontext-payload.
3. **Eval + red-team.** Ett konkret mätbart testuppdrag; adversariell self-check; red-team mot
   prompt-injection / instruction-override / rollöverskridande före aktivering.
4. **Gate 0 (anti-bloat):** behövs rollen ENS aktiv? 2–5 vassa slår 20 smala; håll aktiva 7–10.

## Källor

- [A2A Protocol — Zylos Research](https://zylos.ai/research/2026-05-16-agent-to-agent-communication-protocols-a2a-mcp/)
- [ACP vs MCP vs A2A — Neosalpha](https://neosalpha.com/blogs/ai-agent-protocols-acp-vs-mcp-vs-a2a/)
- [Google A2A Protocol — Atlan](https://atlan.com/know/google-a2a-protocol/)
- [Anti-Patterns in Multi-Agent Gen AI — Medium](https://medium.com/@armankamran/anti-patterns-in-multi-agent-gen-ai-solutions-enterprise-pitfalls-and-best-practices-ea39118f3b70)
- [Why Multi-Agent Systems Fail — Galileo](https://galileo.ai/blog/why-multi-agent-systems-fail)
- [Claude Code Subagents: Best Practices — ClaudeFast](https://claudefa.st/blog/guide/agents/sub-agent-best-practices)
- [LangGraph vs AutoGen vs CrewAI 2025 — Latenode](https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langgraph-vs-autogen-vs-crewai-complete-ai-agent-framework-comparison-architecture-analysis-2025)
- [Multi-Agent Orchestration: 5 Patterns — Digital Applied](https://www.digitalapplied.com/blog/multi-agent-orchestration-5-patterns-that-work)
- [Survey of Agent Interoperability Protocols — arXiv](https://arxiv.org/html/2505.02279v1)
- [CAMEL Framework — GitHub](https://github.com/camel-ai/camel)
- [OpenAI Swarm — GitHub](https://github.com/openai/swarm)
- [System Prompts shaping AI agents — Maxim](https://www.getmaxim.ai/articles/the-importance-of-system-prompts-in-shaping-ai-agent-responses/)
- [Least Privilege for LLM Agents — Medium](https://medium.com/@michael.hannecke/least-privilege-for-llm-agents-applying-security-principles-to-model-selection-57760accb041)
- [LLM Guardrails Best Practices — Datadog](https://www.datadoghq.com/blog/llm-guardrails-best-practices/)
- [Evaluation and Benchmarking of LLM Agents: A Survey — arXiv](https://arxiv.org/html/2507.21504v1)
