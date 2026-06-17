# .claude/ — verktygslådan (Plan A)

Detta är **Plan A**: hur *vi* driver Cortxt-portföljen med Claude Code. Det är **inte** produktkod.

**Väggen (hård regel):** produktkod (`app/`, `scripts/`, `agents/`, `nodes/`) importerar
aldrig något härifrån, och inget här är ett produktberoende. Produktens egna agenter
bor i `Project-CNS/agents/` (Plan B), inte här.

## Innehåll
- `agents/` — subagent-definitioner (`.md` med `name`/`description`-frontmatter).
- `skills/` — egna skills för portföljarbetet. (Produktens/portabla skills bor i `Project-CNS/skills/`.)
- `commands/` — slash-kommandon.
- `settings.json` — delade, versionerade permissions. Maskinlokala overrides hör hemma i
  `settings.local.json` (versioneras inte).

## Versionering
Detta repo är källan till sanning för verktygslådan. Arbetsytans `.claude/`
(`CNS projekt/.claude/`) är **maskinlokal och oversionerad** — lägg inget varaktigt
där utom den btw-Stop-hook som redan bor i arbetsytans `settings.json`.

Se `../CLAUDE.md` → "Agenter, verktygslåda & minne (två plan)" för helheten.
