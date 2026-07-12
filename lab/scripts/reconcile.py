"""Reconcile — ställ katalogen mot verkligheten, varje natt, och gör lögnen synlig.

**Varför ett schemalagt jobb och inte en CI-lint:** CI triggar på commits. Men Vercel, Railway
och repona driver på sin egen klocka — en katalog som bara regenereras vid push ljuger mellan
pushar. Prior art (Backstage) kör en kontinuerlig processing-loop av exakt det skälet.

Vad den gör, i ordning:

  1. **Härleder** verkligheten (MCP-servrar, repo-struktur, syskonrepon)
  2. **Läser omdömet** ur vaulten (det maskinen aldrig kan veta)
  3. **Mergar** → ``catalog.generated.yaml``
  4. **Diffar** mot den handskrivna ``catalog.yaml`` — *diffen är driftloggen*
  5. **Flaggar orphans** — noder utan backing OCH utan not. Tystnad är buggen.
  6. **Flaggar motsägelser** — härledd fas säger live, men grindbeslutet är fyra månader gammalt

**Den kröner ingenting.** Den genererade filen skrivs bredvid, inte över. Flippen (att
``load_catalog`` läser den genererade) görs först när diffen granskats och är ren — det var felet
2026-07-11: att kröna en ställning innan den bevisats bära.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATED_PATH = REPO_ROOT / "catalog.generated.yaml"


@dataclass
class Report:
    """Vad reconcile såg. Allt som är tyst här är en bugg."""

    derived: int = 0
    annotated: int = 0
    merged: int = 0

    only_in_reality: list[str] = field(default_factory=list)   # verkligt, saknas i katalogen
    orphans: list[str] = field(default_factory=list)           # i katalogen, ingen backing alls
    unbacked: list[str] = field(default_factory=list)          # ingen repo-backing (kandidater)
    contradictions: list[str] = field(default_factory=list)    # härlett ≠ deklarerat
    vault_findings: list[str] = field(default_factory=list)    # handlagret brister

    def as_text(self) -> str:
        lines = [
            "# Reconcile — katalogen mot verkligheten",
            "",
            f"härlett: {self.derived}  ·  annoterat (vault): {self.annotated}  ·  "
            f"sammanslaget: {self.merged}",
            "",
        ]

        def block(title: str, rows: list[str], hint: str = "") -> None:
            lines.append(f"## {title}: {len(rows)}")
            if hint and rows:
                lines.append(f"_{hint}_")
            lines.extend(f"  - {r}" for r in rows)
            lines.append("")

        block("Verkligt men saknas i katalogen", self.only_in_reality,
              "Något kör som katalogen inte känner till.")
        block("Orphans", self.orphans,
              "I katalogen, men ingen kod och ingen not backar dem. Gravsten eller gissning?")
        block("Utan repo-backing (kandidater, ej dom)", self.unbacked,
              "Heuristik — flaggar, dömer inte. Kan vara planerade, kan vara döda rester.")
        block("Motsägelser (härlett vs deklarerat)", self.contradictions,
              "Verkligheten och omdömet säger emot varandra.")
        block("Handlagret (vault)", self.vault_findings)
        return "\n".join(lines)

    @property
    def is_clean(self) -> bool:
        """Ren = inget som kräver ett beslut. Utan-backing är kandidater, inte fel."""
        return not (self.only_in_reality or self.orphans or self.contradictions)


def run(*, write: bool = False) -> Report:
    """Kör hela reconcile. ``write=True`` skriver catalog.generated.yaml."""
    import yaml

    from scripts import derive_catalog
    from scripts.catalog import load_catalog

    from . import phase_derive, signals, vault_reader
    from .roadmap import load_recipe

    report = Report()

    # 1 — verkligheten
    derived = derive_catalog.derive_from_disk()
    classified = derive_catalog.verify_from_disk()
    report.derived = len(derived)

    # 2 — omdömet
    catalog = load_catalog()
    annotations = vault_reader.load_annotations()
    report.annotated = len(annotations)
    report.vault_findings = [
        str(f) for f in vault_reader.check(catalog_slugs=set(catalog))
    ]

    # 3 — merge. Katalogen är annoteringslagret för INFRA (tills härledarna täcker allt);
    #     vaulten är det för VENTURES. Härlett bär existens, annotering bär semantik.
    merged = derive_catalog.merge(derived, catalog)
    report.merged = len(merged)

    # 4 — diff mot verkligheten
    diff = derive_catalog.diff_against_catalog(derived, catalog)
    report.only_in_reality = diff.only_in_reality

    # 5 — orphans: ingen kod OCH ingen not. En nod ingen kan peka på.
    #     Grupperingsnoder undantas — de ÄR abstraktioner, inte kod.
    for slug, (status, why) in sorted(classified.items()):
        if status == "grouping":
            continue
        if status == "aspirational":
            has_note = slug in annotations or (catalog.get(slug, {}).get("domain") in annotations)
            if has_note:
                report.unbacked.append(f"{slug} — {why} (men har en not)")
            else:
                report.orphans.append(f"{slug} — {why}, ingen not heller")

    # 6 — motsägelser: verkligheten mot omdömet, per venture
    recipe = load_recipe()
    for slug, note in sorted(annotations.items()):
        entry = catalog.get(slug, {})
        sig = signals.collect(slug, catalog_entry=entry, annotation=note)
        derived_phase = phase_derive.derive_phase(
            recipe, signals=sig, checked=signals.checked_steps(note)
        )
        tracking = vault_reader.tracking_for(slug, note, phase=derived_phase["phase"])

        msg = phase_derive.contradiction(
            phase=derived_phase["phase"],
            gate_decision=tracking.get("gate_decision"),
            gate_age_days=tracking.get("gate_age_days"),
        )
        if msg:
            report.contradictions.append(f"{slug}: {msg}")

        if derived_phase["gates_skipped"] and not tracking.get("kill_criteria"):
            report.contradictions.append(
                f"{slug}: står i '{derived_phase['phase']}' med "
                f"{len(derived_phase['gates_skipped'])} överhoppade grindar och INGA "
                f"kill-kriterier — det här projektet kan aldrig dö."
            )

    # 7 — skriv den genererade katalogen (bredvid, aldrig över)
    if write:
        header = (
            "# GENERERAD av lab/scripts/reconcile.py — redigera INTE för hand.\n"
            "# Härledd verklighet + annoterat omdöme. Konsumenterna läser ÄNNU catalog.yaml;\n"
            "# detta är kandidaten inför flippen. Kröna den först när diffen är ren.\n\n"
        )
        body = yaml.safe_dump(
            {"systems": {k: merged[k] for k in sorted(merged)}},
            allow_unicode=True, sort_keys=False,
        )
        GENERATED_PATH.write_text(header + body, encoding="utf-8")

    return report
