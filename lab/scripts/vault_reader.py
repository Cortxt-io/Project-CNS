"""Handlagret: Obsidian-vaulten som annoteringskälla för portföljkatalogen.

**Varför:** `catalog.yaml` handredigerades och drev därför isär från verkligheten. Lösningen är
tvådelad — infra HÄRLEDS ur verkligheten (`derive_catalog.derive`), och venture-SEMANTIK (omdöme
som ingen maskin kan härleda: `stage`, `kill_criteria`, `next_action`) bor där omdömet fattas:
i Obsidian. Den här modulen är läsaren för det handlagret. Den ersätter
`derive_catalog.load_annotations()`s läsning av `catalog.annotations.yaml` — samma interface,
nytt hem.

**Skrivytorna är disjunkta.** Vi LÄSER vaulten. Vi skriver aldrig i den. (Backstage-mönstret:
maskinen annoterar den ingested entiteten, aldrig den handförfattade filen — annars skriver ett
verktyg förr eller senare sönder någons prosa mitt i en tanke.)

**Referensintegritet är vårt jobb, inte JSON Schemas.** Schema kan säga att `node` är en sträng
som matchar ett mönster; det kan inte säga att slugen faktiskt finns i katalogen, eller att två
noter inte gör anspråk på samma. `check()` gör det.

Ren och testbar: rena funktioner tar in data, IO-skalet läser filer. Degraderar tyst — saknad
vault → tomt, aldrig en krasch (samma mönster som `roadmap.py`).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# Repo-roten: denna modul bor i lab/scripts/ → två nivåer upp.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "annotation.schema.json"

# Vaulten är ett SYSKON-repo, inte en del av detta. Default matchar arbetsytans layout.
DEFAULT_VAULT = REPO_ROOT.parent / "vault"

# Var venture-noterna bor inuti vaulten. Mappen HITTAS, den dikteras inte: layouten flyttades
# två gånger på en dag (Cortxt/Verticals → Cortxt-io/Work/Verticals), och en hårdkodad sökväg
# gjorde då läsaren tyst blind — noll ventures, noll findings, grönt. Vaulten äger sin struktur;
# koden följer den.
# Två namn: mappen döps om Verticals → Ventures (schemat säger `venture`, inte `vertical` —
# "vertical" var historia). Båda accepteras, så en pågående rename aldrig gör läsaren blind.
VENTURE_DIRS = ("Ventures", "Verticals")

# Kataloger som aldrig är innehåll.
_SKIP_DIRS = {
    ".git", ".obsidian", ".makemd", ".space", ".smart-env", ".claudian", ".claude",
    # Mallar bär `type: venture` som exempelvärde — de skulle annars räknas som en venture som
    # heter "Vertical". Understreck betyder INTE "inte innehåll": `_pipeline/` bär pre-gate-idéer,
    # och att hoppa över allt med `_` gjorde dem osynliga i exakt det ögonblick de började betyda
    # något. Namnge det som ska hoppas över; gissa inte på prefix.
    "_templates", "_dashboards", "_archive",
}

# Staleness-SLA per HÄRLEDD fas (dagar). Ju närmare verkligheten en venture är, desto snabbare
# ruttnar en ogranskad anteckning: en idé i discovery får ligga i månader, men en not om något
# som ligger i produktion och tar emot användare är färskvara.
STALENESS_SLA_DAYS = {
    "discovery": 90,
    "spec": 60,
    "mvp": 45,
    "konsolidera": 30,
    "live": 30,
    "users": 21,
    "validated": 30,
    "paying": 30,
}
# Ett dödförklarat projekt tjatar aldrig. Det är dött.
TERMINAL_DECISIONS = {"kill"}

# Noter som INTE är ventures/idéer trots att de bor bland dem (README:er, förklaringsnoter).
# De ska inte valideras som portföljposter — de gör inga anspråk.
NON_VENTURE_TYPES = {"reference", "moc", "index", "template"}

# Vad en portföljnot ÄR — en allowlist, inte en denylist.
#
# Förr räknades allt vars `type` inte stod i NON_VENTURE_TYPES som en portföljnot. Det gick så
# länge läsaren bara tittade i EN mapp. När den nu söker på innehåll i hela vaulten skulle en
# denylist svälja varje research-not, logg och skill — och rapportera dem som ventures.
# En denylist måste förutse allt som INTE är; en allowlist behöver bara veta vad som är.
VENTURE_TYPES = {"venture", "idea", "vertical"}


@dataclass(frozen=True)
class Finding:
    """En brist i handlagret. Slug + vad som är fel + vilken fil som bär felet."""
    slug: str
    message: str
    path: str = ""

    def __str__(self) -> str:  # pragma: no cover - bekvämlighet i CLI
        where = f" ({self.path})" if self.path else ""
        return f"{self.slug}: {self.message}{where}"


# -- rena funktioner ---------------------------------------------------------

def extract_pitch(body: str) -> str:
    """Första stycket under `## Pitch` — hisspitchen.

    Pitchen bor i BRÖDTEXTEN, inte i frontmatter, för att den ska kunna redigeras som text.
    Den härleds ändå: appen renderar den som ingressen på venture-kortet.
    """
    match = re.search(r"^##\s+Pitch\s*$", body, flags=re.MULTILINE | re.IGNORECASE)
    if not match:
        return ""
    rest = body[match.end():]
    for block in re.split(r"\n\s*\n", rest):
        text = block.strip()
        if text and not text.startswith("#"):
            return " ".join(text.split())
    return ""


def load_schema() -> dict:
    """annotation.schema.json. Tomt schema om filen saknas → validering degraderar till no-op."""
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def validate_annotation(frontmatter: dict, schema: dict | None = None) -> list[str]:
    """Validera en nots frontmatter mot annotation.schema.json → lista med felmeddelanden.

    Tom lista = giltig. Detta fångar typer, enums och required — men INTE referensintegritet
    (se `check`), som JSON Schema per definition inte kan uttrycka över filgränser.
    """
    schema = load_schema() if schema is None else schema
    if not schema:
        return []
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - jsonschema är en dependency
        return []

    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(frontmatter), key=lambda e: list(e.path)):
        field = ".".join(str(p) for p in err.path) or "(rot)"
        errors.append(f"{field}: {err.message}")
    return errors


def annotation_age_days(last_reviewed: str | None, today: date | None = None) -> int | None:
    """Dagar sedan noten senast granskades. None om okänt.

    Detta är staleness-klockan. Prior art (Backstage m.fl.) löser "filen försvann" — aldrig
    "filen ljuger". En not som fortfarande finns ger ingen orphan-signal, inget schemafel och
    ingen CI-fail hur gammal den än är. Den här siffran är vårt enda försvar.
    """
    if not last_reviewed:
        return None
    try:
        reviewed = date.fromisoformat(str(last_reviewed))
    except (ValueError, TypeError):
        return None
    return ((today or date.today()) - reviewed).days


def is_stale(*, phase: str | None, age_days: int | None,
             gate_decision: str | None = None) -> bool:
    """Har handlagret sannolikt ruttnat för den här noten?

    Nycklas på den HÄRLEDDA fasen — inte på ett handskrivet stadium, för det var ju just
    handskrivna fält som ruttnade. Maskinen vet var bygget står; den kan därför avgöra hur
    färsk anteckningen borde vara.

    Visas, tvingas inte: en hård grind skulle bara få en att stämpla datumet utan att tänka.
    Men det ska inte gå att INTE se att en `next_action` är tre veckor gammal medan repot
    fått fyrtio commits.
    """
    if age_days is None or gate_decision in TERMINAL_DECISIONS:
        return False
    sla = STALENESS_SLA_DAYS.get(phase or "")
    return sla is not None and age_days > sla


def _normalize_scalars(meta: dict) -> dict:
    """YAML gör `2026-07-10` till ett date-OBJEKT, inte en sträng.

    JSON Schema (`type: string, format: date`) förkastar då varenda datum i vaulten. Obsidian
    skriver datum utan citattecken och kommer alltid att göra det — så normaliseringen hör hemma
    här, i läsaren, inte som en regel människan måste minnas.
    """
    out = {}
    for key, value in meta.items():
        if value is None:
            # `url_live:` utan värde blir None i YAML. Att skicka vidare det ger
            # "None is not of type 'string'" för ett fält användaren aldrig fyllt i.
            # Frånvaro ska betyda frånvaro.
            continue
        if isinstance(value, date):        # täcker även datetime (subklass)
            out[key] = value.isoformat()[:10]
        else:
            out[key] = value
    return out


def parse_note(text: str) -> tuple[dict, str]:
    """Dela en markdown-not i (frontmatter, brödtext). Saknad frontmatter → ({}, hela texten)."""
    try:
        import frontmatter as fm_lib
    except ImportError:  # pragma: no cover - python-frontmatter är en dependency
        return {}, text
    post = fm_lib.loads(text)
    return _normalize_scalars(dict(post.metadata or {})), post.content or ""


# -- IO-skal -----------------------------------------------------------------

def vault_root(explicit: Path | str | None = None) -> Path | None:
    """Var vaulten ligger: explicit > $CORTXT_VAULT_PATH > syskonmappen ../vault. None om ingen finns.

    En EXPLICIT sökväg är strikt: pekar den på ingenting blir svaret None. Att tyst falla tillbaka
    på den riktiga vaulten vore värre än att inte hitta något — ett test mot en tom tmp-katalog
    skulle plötsligt läsa produktionsdata.
    """
    if explicit is not None:
        path = Path(explicit)
        return path if path.is_dir() else None

    # En SATT men felaktig env-var är en felkonfiguration, inte en frånvaro. Att tyst falla
    # tillbaka på standardsökvägen skulle dölja den — och i CI betyder det att jobbet läser
    # "någon vault" i stället för den man pekade ut, eller tror sig ha en när den inte har det.
    env = os.environ.get("CORTXT_VAULT_PATH")
    if env:
        path = Path(env)
        return path if path.is_dir() else None

    return DEFAULT_VAULT if DEFAULT_VAULT.is_dir() else None


def venture_root(root: Path | str | None = None) -> Path | None:
    """Hitta venture-mappen i vaulten, var den än ligger. None om den inte finns.

    Vi letar i stället för att peka: sökvägen har flyttats två gånger på en dag, och varje
    hårdkodning bygger in nästa tysta blindhet.
    """
    resolved = vault_root(root)
    if resolved is None:
        return None
    for name in VENTURE_DIRS:
        for path in sorted(resolved.rglob(name)):
            if path.is_dir() and not any(part in _SKIP_DIRS for part in path.parts):
                return path
    return None


def _note_paths(root: Path) -> list[Path]:
    """Portföljnoterna — hittade på VAD de är, inte på VAR de ligger.

    **Positionsberoendet var buggen.** Läsaren letade efter `Ventures/<venture>/<venture>.md`, exakt
    en nivå ner. Vaulten har sedan dess flyttats fyra gånger på två dygn (Verticals → Ventures →
    Products/ → Work/), grindmapparna (`G0 Problem/` … `G5 Live-Kill/`) sköts in MELLAN `Ventures/`
    och venturen, och `file-order` skrev sorteringsordningen in i mappnamnen (`2 Ventures`). Varje
    gång blev läsaren **tyst blind**: `venture_root() → None`, `load_annotations() → {}` — och
    rapporten förblev grön, eftersom CLI:t föll tillbaka på `catalog.yaml`.

    Att lära läsaren varje ny mappform är att bygga in nästa blindhet. Frågan är inte var noten
    ligger. Frågan är vad den är: en not med `type: venture` (eller en pre-gate-idé) ÄR en
    portföljnot, oavsett hur många mappar Rikard skjuter in ovanför den i morgon.
    """
    paths: list[Path] = []
    for p in sorted(root.rglob("*.md")):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        try:
            meta, _ = parse_note(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            # En not med trasig YAML får inte fälla de andra. Vi läser nu HELA vaulten, så en enda
            # felskriven frontmatter någonstans skulle annars döda hela mätningen — precis den
            # sortens totalhaveri som gör att man slutar lita på verktyget.
            continue
        if is_portfolio_note(meta, p):
            paths.append(p)
    return paths


def is_portfolio_note(meta: dict, path: Path) -> bool:
    """Gör den här noten anspråk på att vara en venture/idé — eller är den bara prosa?

    En README bland vertikalerna förklarar mappen; den är inte en portföljpost och ska inte
    mätas som en. Att validera den vore att uppfinna en brist som inte finns.
    """
    if path.stem.upper() == "README":
        return False
    return str(meta.get("type") or "").strip().lower() in VENTURE_TYPES


def load_annotations(root: Path | str | None = None) -> dict[str, dict]:
    """Handlagret: slug → annotering. Ersätter derive_catalog.load_annotations().

    Nyckeln är `node`-slugen (join-nyckeln mot katalogen). Pre-gate-idéer bär `node: none` och
    kan alltså inte nyckla på den — de nycklas på filnamnet, så de aldrig kolliderar på 'none'.

    Degraderar tyst: ingen vault → {}. En trasig not hoppas över, den fäller inte de andra.
    """
    resolved = vault_root(root)
    if resolved is None:
        return {}

    out: dict[str, dict] = {}
    for path in _note_paths(resolved):
        try:
            meta, body = parse_note(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if not meta or not is_portfolio_note(meta, path):
            continue

        node = str(meta.get("node") or "").strip()
        key = node if node and node != "none" else path.stem

        entry = dict(meta)
        entry["_path"] = str(path.relative_to(resolved))
        pitch = extract_pitch(body)
        if pitch:
            entry["pitch"] = pitch
        out[key] = entry
    return out


def check(root: Path | str | None = None, *, catalog_slugs: set[str] | None = None) -> list[Finding]:
    """Validera handlagret: schema + det JSON Schema inte kan uttrycka (referensintegritet).

    Tre klasser av fel:
      1. schemafel (fält saknas, okänd enum) — via annotation.schema.json
      2. `node:` som inte finns i katalogen — ett dinglande pekfinger
      3. två noter som gör anspråk på samma `node:` — vilken är sanningen?

    Klass 2 och 3 är precis det hål frontmatter-validering lämnar öppet, och som vi äger själva
    (ingen prior art finns för Obsidian som katalogkälla).
    """
    resolved = vault_root(root)
    if resolved is None:
        return []   # ingen vault = FRÅNVARO. Tyst är rätt.

    # Men en vault som finns och vars ventures vi inte hittar är en FELKONFIGURATION — samma
    # skillnad modulen redan gör för env-varen. Att returnera [] här vore ett kontrolltorn som
    # tittar in i en vägg och rapporterar klart väder: noll ventures i en portfölj med tio är
    # inte hälsa, det är ett brutet kontrakt.
    #
    # Vakten stod tidigare vid FEL DÖRR: den kollade att en mapp med rätt NAMN fanns. Vaulten
    # byggdes om fyra gånger på två dygn (2026-07-12/13) — grindmappar sköts in, `file-order`
    # numrerade om — och varje gång var mappen "borta" fast noterna låg kvar. Det som betyder
    # något är inte om en mapp heter Ventures. Det är om vi hittar några noter alls.
    if not _note_paths(resolved):
        return [Finding(
            "vault",
            "noll portföljnoter i vaulten — läsaren mäter ingenting (fel struktur, eller fel vault?)",
            str(resolved),
        )]

    schema = load_schema()
    findings: list[Finding] = []
    claimed: dict[str, str] = {}   # node-slug → första noten som gjorde anspråk
    seen = 0

    # Iterera NOTERNA, inte load_annotations() — den nycklar på slug och skriver därmed över
    # en dubblett med den andra. Beviset vi letar efter försvinner i just den avdubbletteringen.
    for path in _note_paths(resolved):
        try:
            meta, _ = parse_note(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if not meta or not is_portfolio_note(meta, path):
            continue

        seen += 1
        rel = str(path.relative_to(resolved))
        node = str(meta.get("node") or "").strip()
        key = node if node and node != "none" else path.stem

        for message in validate_annotation(meta, schema):
            findings.append(Finding(key, message, rel))

        if not node or node == "none":
            continue

        if catalog_slugs is not None and node not in catalog_slugs:
            findings.append(Finding(
                key, f"node: {node!r} finns inte i katalogen — dinglande referens", rel))

        if node in claimed:
            findings.append(Finding(
                key, f"duplicate: node {node!r} görs anspråk på av både "
                     f"{claimed[node]!r} och {rel!r}", rel))
        else:
            claimed[node] = rel

    # En venture-mapp utan en enda portföljnot är inte ett rent hus — det är en tom mätning.
    if seen == 0:
        findings.append(Finding(
            "vault",
            f"{VENTURE_DIRS[0]}/ innehåller inga portföljnoter — läsaren mäter ingenting",
            str(verticals.relative_to(resolved)),
        ))

    return findings


def tracking_for(slug: str, entry: dict, *, phase: str | None = None,
                 today: date | None = None) -> dict:
    """Omdömes-vyn av en annotering, med staleness pålagd — det appen renderar.

    ``phase`` kommer HÄRLEDD utifrån (``phase_derive``), inte ur noten. Handlagret bär bara
    omdöme; fasen är ett mätvärde.
    """
    age = annotation_age_days(entry.get("last_reviewed"), today=today)
    gate_decision = entry.get("gate_decision")
    return {
        "gate_decision": gate_decision,
        "gate_date": entry.get("gate_date"),
        "gate_age_days": annotation_age_days(entry.get("gate_date"), today=today),
        "next_gate": entry.get("next_gate"),
        "owner": entry.get("owner"),
        "north_star": entry.get("north_star"),
        "kill_criteria": entry.get("kill_criteria") or [],
        "next_action": entry.get("next_action"),
        "steps_done": entry.get("steps_done") or [],
        "pitch": entry.get("pitch", ""),
        "last_reviewed": entry.get("last_reviewed"),
        "annotation_age_days": age,
        "stale": is_stale(phase=phase, age_days=age, gate_decision=gate_decision),
    }
