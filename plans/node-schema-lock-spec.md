# Spec (LÅST): Schema-tillägg för nodmodellens evolution — steg 1 (datastruktur)

> Spec-pass 2026-06-11 (session-840ec8bb). Bygger på `plans/node-model-evolution-spec.md` (research).
> **Granskningsutkast — ingen kod än.** Beslut tagna med Rikard (se nedan). Spec-först:
> en öppen designfråga (Plan A/B-väggen) MÅSTE besvaras innan agent-entitetsdelen byggs.

## Beslut (Rikard 2026-06-11)
1. **domain:** JA — inför som valfri toppnivå.
2. **Ägarskap:** FULL grafentitet — agenter blir förstklassiga entiteter med owns/contributes-kanter.
3. **c4_level:** PARKERAD — härleds ur `part_of`-djup när zoom-vyn byggs; inget fält nu.
4. **Levande lager** (beräknade fält + scorecards): PARKERAT till viz-/webbapp-passet.

Detta pass låser alltså **bara datastrukturen**. Visualisering + färskhetsrobot kommer separat.

## Del 1 — node.md frontmatter (additivt, valfritt, fallback på gamla)

Nya fält, alla valfria (gamla noder bryts ej; dashboarden fallbackar):

| Fält | Typ | Innebörd |
|------|-----|----------|
| `type` | string (enum `types`) | Precisering under `kind` — *vad* noden är (frontend/service/pipeline…). |
| `domain` | string (enum `domains`) | Affärskontext-grupp ovanför system. |
| `owner_agent` | string (agent-slug) | Primär ägare → `owns`-kant till AGENT. |
| `contributing_agents` | list[string] | Bidragande agenter → `contributes_to`-kanter. |

## Del 2 — enums.json (enkälla; konsumeras av validator.py + JS cns-schema)

Tillägg (ordning semantisk, förslag — justeras i granskning):

```json
"types":   ["frontend", "service", "mcp-server", "pipeline", "cli",
            "tool", "agent", "infra", "library", "dataset", "ai-model"],
"domains": ["cortxt", "shopify-venture"]
```

`types` härledd ur de 31 befintliga noderna (dashboard/landing=frontend, cns-mcp=mcp-server,
cns-brief/devlog/analyst=pipeline, cns-core=cli, agent-studio=tool, research-agent=agent,
local-ai=ai-model osv). `domains` = nuvarande två affärskontext. Båda växbara additivt.

## Del 3 — validator.py
- Validera `type` mot `types`, `domain` mot `domains` (mjukt: WARN om okänt, ej ERROR — additivt).
- `owner_agent`/`contributing_agents`: WARN om slug inte matchar en känd agent (se Del 4-väggen).
- Alla fyra fälten valfria — en nod utan dem validerar fortfarande.

## Del 4 — AGENT som förstklassig grafentitet ⚠️ ÖPPEN DESIGNFRÅGA (Plan A/B-väggen)

**Konflikten:** Agenturen (88 roller) bor i `.claude/agents/*.md` = **Plan A** (verktygsladan).
`CLAUDE.md` slår fast: *"produktkod importerar aldrig från `.claude/`, och `.claude/` är aldrig
ett produktberoende."* Men `owns`-kanter + agent-noder i `nodes.json` skulle få **dashboarden
(produkt) att bero på Plan A-data**. Det bryter väggen om `json_exporter.py` läser `.claude/` direkt.

**Tre vägar (beslut krävs innan bygge):**
- **A. Projektion via Plan A-generator (REK).** Utöka `gen_agentur.py` (Plan A, läser redan
  `.claude/agents/`) att emittera en *committad produkt-rymd-artefakt* — `exports/agents.json`
  (slug, title, department, squad, status, model, owns[], contributes_to[]). `json_exporter.py`
  läser den artefakten, aldrig `.claude/` direkt. Väggen hålls: riktningen `.claude → produkt`
  går via en genererad fil, inte ett kodberoende.
- **B. Agenter som riktiga node.md.** Modellera varje agent som en nod (`kind: agent`) i `nodes/`.
  Enhetlig graf, men blandar org-lager in i system-lagret och dubbellagrar mot `.claude/agents/`.
- **C. Separat agent-graf.** Dashboarden hämtar agenter från en egen endpoint, helt skild från
  nodgrafen. Renast vägg, men ingen *korsad* graf (org↔system syns inte tillsammans).

→ **BESLUTAT (Rikard 2026-06-11): väg A.** Research-grundad (spår 4: agenter som ägar-entiteter)
och hedrar Plan A/B-väggen (CLAUDE.md). `gen_agentur.py` utökas att emittera `exports/agents.json`;
`json_exporter.py` läser den, aldrig `.claude/` direkt.

## Del 5 — Arbets-kanter (härledda, inget i node.md)
QUEST/ISSUE bär redan `node:<slug>`-labels. Exportera dem som kanter:
- `QUEST --targets--> NODE`, `ISSUE --addresses--> NODE`, `ISSUE --assigned_to--> AGENT`.
- Härleds vid export (ny modul, läser `issues_client`), lagras ej i node.md. Ingen GitHub-skrivning.

## Del 6 — json_exporter.py → nodes.json (version 3.0)
Utöka payloaden additivt:
```
{ "version": "3.0",
  "nodes":  [ {... + type, domain, owner_agent, contributing_agents } ],
  "agents": [ {slug, title, department, squad, status, owns[], contributes_to[]} ],  # via väg A
  "edges":  [ {from, to, type: owns|contributes_to|targets|addresses|assigned_to} ] }
```
`cortxt/packages/cns-schema` regenereras ur enums.json (nya enums propagerar till JS).

## Migreringsväg (additiv, en bit i taget — bryt inte dashboarden)
1. enums.json: lägg `types` + `domains`.
2. validator.py: mjuk validering av de nya fälten.
3. Backfill `type`/`domain` på de 31 noderna (en PR el. gradvis).
4. **Beslut Del 4** → bygg agent-projektionen (väg A: utöka gen_agentur.py).
5. Backfill `owner_agent` på noder; exportera agenter + owns-kanter.
6. Arbets-kant-härledning ur `node:`-labels.
7. (Parkerat) c4_level-härledning + levande lager när viz byggs.

## Avgränsning
- Ingen visualisering, ingen färskhetsrobot, ingen `c4_level` i detta steg.
- Allt additivt med fallback — dashboarden får inte brytas av en nod utan de nya fälten.
- Nodmodellen rivs inte (se minne `nodmodell-evolution`); den växer.

## Verifiering (när byggd)
- En gammal node.md utan nya fält validerar och renderas oförändrat.
- `cns validate <slug>` WARN:ar (ej ERROR) på okänt `type`/`domain`.
- `nodes.json` v3.0 innehåller `agents` + `edges`; dashboarden kan rita owns-kanter.
- Inget i `app/`/`json_exporter.py` importerar eller läser `.claude/` direkt (väggen intakt).
