---
name: agent-studio
department: People
description: Skapa en ny agent interaktivt — guided flow som validerar mot agent-definition.schema.json, sparar agenten som en CNS-nod och genererar en .claude/agents/-fil. Triggar på /agent-studio. Använd när du vill skapa, konfigurera eller dokumentera en ny agent utan att redigera JSON manuellt.
---

# /agent-studio — skapa en agent utan JSON-redigering

Guiden tar dig igenom ett agentval steg för steg, validerar resultatet mot
`schemas/agent-definition.schema.json` och producerar två artefakter:
1. En CNS-nod (`nodes/<slug>/node.md`, `kind: component`, `part_of: agent-studio`)
2. En agentfil (`Project-CNS/.claude/agents/<slug>.md`) klar att använda i Claude Code

## Steg

### 1. Syfte
Fråga (numrerade alternativ):
1. **research** — utforskar noder, Linear-issues, wiki; skriver planning/-filer
2. **kodfokus** — genererar/granskar kod, trigger workflow_dispatch, skapar PRs
3. **orkestration** — koordinerar andra agenter, läser sessionsträd, hanterar quests
4. **annat** — beskriv fritt

### 2. Modellval
Föreslå modell baserat på syfte (motivera på substans, ej enkelhet):

| Syfte | Primär | Fallback |
|-------|--------|----------|
| research | claude-sonnet-4-6 | claude-haiku-4-5 |
| kodfokus | claude-sonnet-4-6 eller qwen2.5-coder (lokal) | claude-haiku-4-5 |
| orkestration | claude-opus-4-8 | claude-sonnet-4-6 |
| annat | claude-sonnet-4-6 | claude-haiku-4-5 |

**Auth-fallback (exakt som agent_host.py):**
`ANTHROPIC_API_KEY` → `.cns-agent-key` → Claude Code-login (ingen API-credit krävs med Claude Code-subscription)

Provider `qwen` / `glm` kräver lokal Ollama-endpoint (se `nodes/local-ai/planning/local-ai-research.md`
för att slutföra deploy-research innan du väljer dessa).

**Claw Code (beslutspunkt):** Utvärdera om Claw Code passar bättre som agent-host på Railway
*innan* du låser arkitekturen för servern. Jämför mot Claude Agent SDK och eget. Notera valet i
agentnodens `Anteckningar`-sektion.

### 3. Verktyg (MCP-tools)
Lista vilka `cortxt_*`-verktyg agenten behöver. Förslag per syfte:
- **research:** `cortxt_get_project`, `cortxt_list_linear_issues`, `cortxt_read_wiki_page`, `cortxt_write_wiki_page`, `cortxt_capture_idea`
- **kodfokus:** `cortxt_list_open_issues`, `cortxt_create_issue`, `cortxt_list_prs`, `cortxt_create_pr`, `cortxt_trigger_workflow`
- **orkestration:** `cortxt_list_sessions`, `cortxt_fork_session`, `cortxt_list_quests`, `cortxt_get_session_tree`

Lägg `read_only: true` om agenten aldrig ska mutera data.

### 4. Systemprompt
Utkast baserat på syfte (ett stycke, max 3 meningar). Håll det tätt —
fullständig prompt skrivs i agentfilen, inte i schema-JSON:en.

### 5. Eval-kriterier
Minst 2 st. Exempel:
- "Skriver inga node.md-ändringar utan att ha läst befintlig nod"
- "Frågar alltid om slug när det är otydligt"
- "Returnerar raw data, inga samtalshälsningar"

### 6. Validera
Bygg JSON-objektet och validera mot `schemas/agent-definition.schema.json`:

```python
import json, jsonschema, pathlib
schema = json.loads(pathlib.Path("schemas/agent-definition.schema.json").read_text())
instance = { "name": "...", "provider": "...", "model": "...", ... }
jsonschema.validate(instance, schema)
print("OK")
```

Om `jsonschema` saknas: granska fälten manuellt mot schemat (required: name, provider, model).

### 7. Spara artefakter
**a) CNS-nod** — skapa `nodes/<slug>/node.md`:
- `kind: component`, `part_of: agent-studio`, `stage: idea`, `status: idea`
- Fyll `summary` med agentenens syfte (en mening)
- Lägg definitionens JSON i `Anteckningar`-sektionen

**b) Agentfil** — skapa `.claude/agents/<slug>.md`:
```markdown
---
name: <slug>
description: <en rad — visas i agentlistan>
model: <model-id>
---

<system-prompt>

## Tillåtna verktyg
<lista cortxt_*-verktygen>

## Eval-kriterier
<lista>
```

**c) Verifiera att filen finns på disk** — kör Glob på `.claude/agents/<slug>.md`.
Om filen saknas: stanna här, skapa den rätt, fortsätt inte.

**d) Rapportera:** nod-slug, agentfil-sökväg, modell, verktygsantal.

### 8. Testa agenten (OBLIGATORISKT — sessionen är inte klar förrän detta steg är godkänt)

Innan `cortxt_mark_session_done` får anropas måste agenten ha körts och svarat korrekt.

**Röktest — kör detta:**
Starta agenten med ett minimalt uppdrag som matchar dess syfte:
- **research:** "Beskriv vad noden `cns-core` gör i ett mening."
- **kodfokus:** "Lista de tre senaste öppna issues."
- **orkestration:** "Visa sessionsträdet."

**Godkännandekriterier:**
1. Agenten svarar utan fel (inga tool-errors, inga auth-fel)
2. Svaret matchar minst ett av agentens eval-kriterier
3. Om agenten ska skriva (wiki, issue, idea) — verifiera att skrivningen faktiskt landade

**Om testet misslyckas:** felsök, uppdatera agentfilen, kör testet igen. Markera inte sessionen klar.

**Om testet godkänns:** uppdatera nodens `stage` från `idea` → `building` och commit.

## GitHub Agents API (undersök)
Om GitHub Agents API är stabilt vid tidpunkten: exportera agentdefinitionen
som GitHub Agent också. Undersök detta i `nodes/agent-studio/planning/` om
det är relevant för den specifika agenten.

## Relaterat
- `/new-session-profile` — skapa en session-profil som *använder* agenten
- `/new-skill` — skapa en skill som triggar agenten
- `nodes/local-ai/` — lokal AI-deploy (kräver research-steget klart)
