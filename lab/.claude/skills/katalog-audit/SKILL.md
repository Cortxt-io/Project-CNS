---
name: katalog-audit
description: "Granskar relationerna i `catalog.yaml` — pekar `part_of`, `feeds` och `depends_on` på verkligheten, eller på en ambition någon hade en gång? Använd vid \"städa katalogen\", \"stämmer beroendena\", \"är den här noden fortfarande med\" — och alltid efter att ett system rivits eller döpts om, för det är då relationerna tyst blir lögner."
---

<!-- GENERERAD ur vaulten — redigera INTE här.
     Källa: Ideaverse/Cortxt-io/Studio/Skills/katalog-audit.md
     Skriv om källnoten och kör `cns skill-export`. En riktning. -->

# katalog-audit

## Vad den gör

Granskar relationerna i `catalog.yaml` — pekar `part_of`, `feeds` och `depends_on` på verkligheten, eller på en ambition någon hade en gång?

## När den ska köras

Använd vid "städa katalogen", "stämmer beroendena", "är den här noden fortfarande med" — och alltid efter att ett system rivits eller döpts om, för det är då relationerna tyst blir lögner.

## Relations-audit

Tre relationer bär grafen. Granska dem var för sig:

- **`part_of`** — pekar noden på rätt system? Finns systemet? (Maskinen svarar på det andra;
  du svarar på det första.)
- **`feeds`** — flödar data faktiskt dit? Eller är det en gammal aspirationsrelation som ingen
  vågat ta bort?
- **`depends_on`** — finns beroendet kvar? Ett beroende på något rivet är inte ett beroende, det
  är ett spöke.

## Arbetsordning

1. Kör `cns validate` — den fångar referensbrott och `part_of`-cykler. Det är golvet, inte taket.
2. Läs varje relation för det system du granskar och fråga: **vad skulle det se ut som om detta
   var falskt?** Kan du inte svara har du inte granskat, du har läst.
3. Föreslå ändringarna som en PR mot `catalog.yaml`. Skriv i beskrivningen *varför* relationen var
   fel — annars återuppstår den.

## Spärrar

- **Vägrar radera ett system ur katalogen.** Att en nod ser övergiven ut är en observation, inte ett
  beslut. Lyft den; radera inte.
- Vägrar ta bort en `feeds`-relation utan att ha kollat om flödet finns i koden.
- Vägrar påstå att en relation är död för att den *ser* gammal ut. Läs källan.
