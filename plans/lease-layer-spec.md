# Spec: Lease-lager för issue-koordination (work-model §6/§7 steg 6)

**Status:** IMPLEMENTERAD design — kod additiv och fail-open. Krockscenariot (§1) är
**förväntat, ej empiriskt bekräftat** och kräver Rikards verifiering innan lagret görs
till en hård grind i agentflödet.
**Datum:** 2026-06-10 · **Nod:** `agentur` · **Förälder-spec:** `work-model-taxonomy-spec.md` (Beslut 4)

---

## 1. Krockscenario (FÖRVÄNTAT — kräver bekräftelse)

> **Ärlighetsnot:** Mätningen i förälder-specen (§2, 2026-06-10) visade att arbetet idag är
> **koncentrerat** (7/8 öppna issues på nod `agentur`), inte parallellt. Det finns alltså
> ännu inget *empiriskt* krockscenario. Lagret byggs på Beslut 4 (bygg nu, parallellt) och
> dimensioneras mot det **förväntade** scenariot nedan. Innan lease görs obligatoriskt i
> agentflödet: bekräfta att verkliga samtidiga claims uppstår.

**Förväntat scenario (målbild 100+ agenter):** När `depends_on`-DAG:en (steg 2) väl delar
upp arbetet i oberoende slices, kan flera agent-runs samtidigt plocka samma öppna issue —
särskilt på heta noder (`agentur`). Utan koordination dubbelarbetar de eller skriver över
varandras resultat. Lease ger en atomisk "jag tar denna" så bara en run äger en issue i taget.

**Granularitet:** per issue-nummer (en lease per issue). Issue förblir den synliga artefakten
på GitHub; den efemära live-claimen lever bara i Redis.

## 2. Lease-semantik
- **TTL:** 300 s (5 min). En övergiven run (kraschad agent) släpper automatiskt sin claim.
- **Heartbeat:** ägaren förnyar TTL var ~60 s medan arbetet pågår (`heartbeat`).
- **TTL-utgång:** lease försvinner ur Redis → issue är fri att claimas igen (reclaim).
- **Reclaim-policy:** ingen forcerad stöld — först när TTL gått ut kan en annan run ta över.
- **Ägaridentitet:** GitHub-login från OAuth-token (`get_access_token().claims["login"]`),
  samma källa som allowlisten i `mcp_server.py`.

## 3. GitHub = sanning
Issue (open/closed, labels, body) är oförändrad sanning på GitHub. Lease är **inte** en
body-PATCH (undviker skriv-storm och historik-brus) utan ett separat efemärt Redis-lager.
Dashboarden behöver inte känna till leases; en valfri framtida `list_leases`-vy kan visa
vem som äger vad just nu.

## 4. Failure modes — FAIL-OPEN
Redis nere eller `REDIS_URL` osatt → alla lease-operationer returnerar `False`/tomt **utan
exception**. Agenter koordinerar då som idag (degraderat men funktionellt). Fail-**closed**
vore en tillgänglighetsregression: en nere-Redis skulle blockera allt arbete. Samma
fail-open-mönster som `eventstream.py` redan använder.

## 5. Redis-nyckeldesign
- Nyckel: `lease:issue:<number>` (separat namespace från `eventstream:recent`).
- Värde: JSON `{"owner": <login>, "claimed_at": <iso>, "heartbeat_at": <iso>, "ttl": <sek>}`.
- **Atomisk claim:** `SET lease:issue:<n> <payload> NX EX <ttl>` — `NX` = bara om nyckeln inte
  finns. Falsy retur = redan tagen. Detta är spec-skissens "optimistiska claim" (`UPDATE WHERE
  open → 0 rader = redan tagen`), uttryckt i Redis.
- **Release:** DEL bara om owner matchar (Lua-script eller WATCH/MULTI) — annars kan en run
  råka släppa en annans förnyade lease.
- **Heartbeat:** verifiera owner, förnya TTL (`SET ... XX EX <ttl>` eller `EXPIRE`).
- **List:** `SCAN MATCH lease:issue:*` (inte `KEYS`, som blockerar).

## 6. Verktygskontrakt (MCP, `app/tools/leases.py`)
- `cortxt_claim_issue(number)` → `{claimed: bool, owner, ...}`; `claimed=False` om redan tagen.
- `cortxt_release_issue(number)` → `{released: bool}`.
- `cortxt_heartbeat_issue(number)` → `{renewed: bool}`.
- `cortxt_list_leases()` → lista aktiva leases.
Owner härleds server-side från OAuth-login — agenten anger den inte själv.

## 7. Berörda filer
- `scripts/lease_store.py` (nytt, rent datalager — återanvänder `eventstream._get_redis()`-mönstret).
- `app/tools/leases.py` (nytt, MCP-wrapper).
- `app/mcp_server.py` (registrera `leases.register(mcp)` + katalog-docstring).

## 8. Verifiering
- Två claim mot samma issue → första `claimed=True`, andra `claimed=False`.
- Release av icke-owner → `released=False`; av owner → `True`.
- Heartbeat förnyar TTL (lease lever vidare efter ursprunglig TTL skulle gått ut).
- `REDIS_URL` osatt → alla operationer returnerar False/tomt utan exception (fail-open).
