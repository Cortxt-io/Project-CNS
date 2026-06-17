# agents/ — produktens agenter (Plan B)

**Plan B:** om Cortxt självt ska köra agenter åt slutanvändare bor de här, som
**produktkod** bredvid `app/` och `scripts/`. Tom tills en verklig agent kräver det
(övergeneralisera inte — samma regel som för mallar).

**Väggen (hård regel):** agenter här är produkt och får aldrig importera från `.claude/`
(det är Plan A — vår egen verktygslåda). De når CNS via samma datalager som resten av
produkten: `scripts/` och MCP-verktygen i `app/`.

När den första produktagenten ska byggas: skriv en spec först (arbetsregel i `../CLAUDE.md`),
och uppdatera `../CLAUDE.md` i samma ändring.
