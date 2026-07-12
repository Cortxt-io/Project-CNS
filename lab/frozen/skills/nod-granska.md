---
name: nod-granska
department: Produkt
description: Revidera noder — zombie-kriterier, stage-transitioner, relations-audit.
---

# Nod-granskning

## Zombie-kriterier (3+ av 5 = zombie)

1. `stage: working` eller `stage: maturing` men inga öppna issues
2. Senast uppdaterad >90 dagar sedan
3. Inga beroenden — inget pekar på noden via `part_of` eller `feeds`
4. Sammanfattning nämner "utforska", "undersök", "kanske" — aldrig levererat
5. Slug nämns aldrig i sessions-data

**En `stage: idea`-nod är INTE en zombie** — den är korrekt klassificerad.

## Stage-transitioner

| Från | Till | Krav |
|------|------|------|
| idea | building | Minst en öppen issue kopplad |
| building | working | Minst en closed issue, MVP körbart |
| working | maturing | Stabilt, inga kritiska issues |
| * | idea | Zombie-audit eller explicit beslut |

Sätt aldrig `stage: working` utan ett bevis på att det faktiskt funkar.

## Relations-audit

- `part_of`: pekar noden på rätt system? Finns systemet?
- `feeds`: flödar data faktiskt dit? Eller är det en gammal aspirationsrelation?
- `depends_on`: beroenden som inte längre finns kvar?

## Arbetsordning

1. Lista alla noder: `cortxt_list_projects`
2. Hämta detaljer per nod: `cortxt_get_project`
3. Kör zombie-kriteriet (3+ av 5)
4. Rapportera lista INNAN du gör ändringar
5. Vänta på godkännande för >3 noder
6. Utför — en i taget

## Vad du ALDRIG gör utan explicit order

- Tar bort noder (sätt `stage: idea` istället)
- Ändrar `part_of`-relationer
- Slår ihop noder
