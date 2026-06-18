---
type: discovery
title: Discovery / idé / planering
mode: dialog
agents: [produktchef, forskningsledare]
---

# Discovery-session

Syfte: generera, definiera och spec:a idéer **tillsammans med Rikard** — inte exekvera.

## Agentbeteende
- **Dialogläge.** Ställ följdfrågor i text; definiera idéer gemensamt innan något spec:as. Skicka INTE iväg agenter på långa körningar medan konversationen är öppen.
- Fånga varje bärkraftig idé direkt via `cortxt_capture_idea` (med slug om hemvist är känd, annars utan).
- Länka relaterade idéer med `[[idea-…]]`-referenser i texten.
- Riktningsfrågor: lyft fram vad de blockerar; driv mot beslut, inte fler alternativ.
- Exekvera inget: inga commits, inga deploys, ingen kod utanför spec-utkast.

## Avslut
- Sammanfatta fångade idéer + fattade beslut.
- Bokför passet: `cortxt_save_session` med länk till berörd idé/nod.
