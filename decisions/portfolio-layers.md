# Portföljlager — substrat → fog → vertikal

## Kontext

Portföljen saknade en axel som skiljer den **delade motorn** från de **fristående
produkterna**. I dashboardens Portfolio-vy grupperades allt på `domain`, vilket lade
hela motorn (CNS Core, agentur, MCP, alla pipelines — samtliga `domain: cortxt`) i en
enda hink bredvid produkterna. "Motor och produkter blandade."

T-format-modellen (en bred horisontell bas + smala vertikala stammar) fångar
arkitekturen: en delad plattform som flera fokuserade produkter vilar på.

## Beslut

Vi inför ett **lager** med tre värden, formaliserat som en härledd axel i nodmodellen:

- **Substrat** — CNS Core: parser, validator, export. Kärnan allt annat vilar på.
- **Fog** — orkestreringen ovanpå kärnan: agentur, MCP, pipelines, stödinfra och
  plattformens egna gränssnitt. "Det delade lagret mellan bar kärna och produkt."
- **Vertikal** — produkterna: juvahem, bkfinans, crusade, orgkomp. Egna domäner, egna
  repon, egen drift. T-formens vertikala stammar.

## Härleds, lagras inte

`layer` **härleds** ur befintliga fält — precis som `kind` härleds ur `part_of`-strukturen
(se `scripts/catalog.py:derive_kind`). Vi lagrar inte det som kan beräknas; ett extra
fält i `catalog.yaml` skulle bara kunna driva ur synk. (`layer` fanns som lagrat fält
före nodmodell-teardown, epic #11, och revs då — det återinförs nu som härlett.)

Regeln (`derive_layer`, i prioritetsordning):

1. **vertical** — `domain != "cortxt"`. Sammanfaller med exportens `is_product`.
2. **substrate** — `cns-core`, eller en nod vars `part_of`-kedja bottnar i `cns-core`.
3. **fog** — allt övrigt i cortxt-domänen.

## Kantfall: gränssnitt → fog

Org-hinkarna `infrastructure`/`interface`/`cortxt` (framework-roten) och interface-
systemen (landing, dashboard, graph-view, agent-studio, tui) faller i **fog**. Det är
ett medvetet val: i tre-lagersmodellen är fog allt delat ovanpå kärnan *utom*
produkterna. Plattformens egna ytor är inte separata produkter — de exponerar motorn.

Ingen override-mekanism införs. Om ett kantfall klassas fel justeras `derive_layer`,
inte datan — felkällan rättas, inte den härledda artefakten.
