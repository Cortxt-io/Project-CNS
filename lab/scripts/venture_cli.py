"""``cns venture`` — ratten till fas-/grind-motorn.

Motorn (``signals`` → ``phase_derive`` → ``venture_checklist``) var byggd men hade inget
gränssnitt. Skillen ``phase-planner`` bad dig köra kommandon som inte fanns; det här är dem.

    cns venture status <slug>     var står bygget, och vilka grindar hoppades över?
    cns venture checklist <slug>  receptets steg → milestones + issues (--apply för att skriva)
    cns venture list              hela portföljen på en skärm

Rent presentationslager: all logik bor i modulerna, den här filen renderar bara.
"""
from __future__ import annotations

import sys

# Statusmarkörer — ingen färg, för att inte anta någon terminal.
MARK = {True: "[x]", False: "[ ]", None: "[?]"}
PHASE_MARK = {"passed": "[ok]", "skipped": "[!!]", "active": "[->]", "todo": "[  ]"}


def _load(slug: str):
    """Allt motorn behöver om en venture. Degraderar aldrig tyst — kastar hellre."""
    from lab.scripts import phase_derive, signals, vault_reader
    from lab.scripts.roadmap import load_recipe
    from scripts.catalog import load_catalog

    recipe = load_recipe()
    entry = load_catalog().get(slug, {})
    note = vault_reader.load_annotations().get(slug)
    sig = signals.collect(slug, catalog_entry=entry, annotation=note)
    derived = phase_derive.derive_phase(
        recipe, signals=sig, checked=signals.checked_steps(note)
    )
    return recipe, derived, note, sig


def _venture_slugs() -> list[str]:
    """Portföljens ventures = system med egen domän (allt som inte är cortxt själv)."""
    from scripts.catalog import load_catalog

    domains = {
        e.get("domain")
        for e in load_catalog().values()
        if e.get("domain") and e.get("domain") != "cortxt"
    }
    return sorted(d for d in domains if d)


def cmd_venture_status(args) -> None:
    """Var står bygget — mätt, inte påstått."""
    from lab.scripts import phase_derive, vault_reader
    from lab.scripts.roadmap import roadmap_detail

    slug = args.slug
    recipe, derived, note, _ = _load(slug)

    print(f"\n{slug} — fas: {derived['phase'].upper()}")
    if derived["gates_skipped"]:
        print(f"  SKULD: {len(derived['gates_skipped'])} grindar passerades utan att stängas "
              f"({', '.join(derived['gates_skipped'])})")
    if derived.get("gates_unknown"):
        print(f"  omätt: {', '.join(derived['gates_unknown'])}")
    print()

    detail = roadmap_detail(slug)
    for phase in (detail or {}).get("phases", []):
        print(f"{PHASE_MARK[phase['status']]} {phase['title']}")
        for step in phase["steps"]:
            done = step["done"]
            how = "" if str(step["check"]).startswith("derived") else "  (kryssas av dig)"
            print(f"      {MARK[done]} {step['title']}{how}")
        if phase["status"] in ("skipped", "active"):
            missing = [s["title"] for s in phase["steps"] if s["done"] is not True]
            if missing and phase.get("gate"):
                print(f"      GRIND: {phase['gate'].get('question', '')}")
        print()

    # Omdömet — det maskinen aldrig kan mäta.
    if note:
        tracking = vault_reader.tracking_for(slug, note, phase=derived["phase"])
        gate = tracking.get("gate_decision") or "—"
        print(f"Grindbeslut: {gate}", end="")
        if tracking.get("gate_age_days") is not None:
            print(f" ({tracking['gate_age_days']} dagar gammalt)", end="")
        print()
        if not tracking.get("kill_criteria"):
            print("  VARNING: inga kill-kriterier. Det här projektet kan aldrig dö.")
        if tracking.get("stale"):
            print(f"  VARNING: noten är {tracking['annotation_age_days']} dagar gammal "
                  f"medan bygget står i {derived['phase']}.")

        msg = phase_derive.contradiction(
            phase=derived["phase"],
            gate_decision=tracking.get("gate_decision"),
            gate_age_days=tracking.get("gate_age_days"),
        )
        if msg:
            print(f"  MOTSÄGELSE: {msg}")
    else:
        print("Ingen vault-not — allt omdöme saknas (north star, kill-kriterier, grindbeslut).")
    print()


def cmd_venture_checklist(args) -> None:
    """Receptets steg → riktiga arbetsuppgifter. Torrkörning som default."""
    from lab.scripts import issues_client, venture_checklist

    slug = args.slug
    recipe, derived, _, _ = _load(slug)
    apply = bool(getattr(args, "apply", False))

    plan = venture_checklist.sync(
        slug, recipe,
        phase=derived["phase"],
        steps=derived["steps"],
        gates_skipped=derived["gates_skipped"],
        gh=issues_client,
        dry_run=not apply,
    )

    if apply:
        print(f"{slug}: {len(plan['created'])} issues skapade, "
              f"{len(plan['closed'])} stängda av verkligheten.")
        for n in plan["closed"]:
            print(f"  stängd automatiskt: #{n}")
        return

    print(f"\n{slug} [fas: {derived['phase']}] — skulle skapa "
          f"{len(plan['would_create'])} uppgifter:\n")
    for title in plan["would_create"]:
        print(f"  [ ] {title}")
    print("\n(torrkörning — kör med --apply för att skapa dem på riktigt)\n")


def cmd_venture_list(args) -> None:
    """Hela portföljen på en skärm. Det som saknades: en yta som visar sanningen."""
    from lab.scripts import vault_reader

    print(f"\n{'venture':12} {'fas':13} {'skuld':6} {'grindbeslut':12} kill-kriterier")
    print("-" * 68)
    for slug in _venture_slugs():
        try:
            _, derived, note, _ = _load(slug)
        except Exception as exc:
            # Aldrig tyst hoppa över en venture. Att den inte kan mätas ÄR information —
            # oftast betyder det att domänen saknar en katalognod med samma slug.
            print(f"{slug:12} {'(kan ej mätas)':13} {'':6} {'':12} {type(exc).__name__}")
            continue
        debt = len(derived["gates_skipped"])
        gate, kills = "—", 0
        if note:
            t = vault_reader.tracking_for(slug, note, phase=derived["phase"])
            gate = t.get("gate_decision") or "—"
            kills = len(t.get("kill_criteria") or [])
        flag = "!" * min(debt, 4)
        print(f"{slug:12} {derived['phase']:13} {debt:<2}{flag:4} {gate:12} "
              f"{kills if kills else 'INGA'}")
    print()


def cmd_reconcile(args) -> None:
    """Ställ katalogen mot verkligheten. Torrkörning som default."""
    from lab.scripts import reconcile

    report = reconcile.run(write=bool(getattr(args, "apply", False)))
    print()
    print(report.as_text())

    if getattr(args, "apply", False):
        print(f"Skrev {reconcile.GENERATED_PATH.name} "
              f"(bredvid catalog.yaml — kröner ingenting).")

    if report.is_blind:
        print("BLIND — beviskällor saknades. Siffrorna ovan säger mer om oss än om portföljen.")
        sys.exit(1)          # ett blint reconcile ska FAILA, inte tyst rapportera hälsa
    elif report.is_clean:
        print("REN — verkligheten och katalogen är överens.")
    else:
        print("EJ REN — se ovan. Flippen väntar tills detta är avgjort.")


def register(subparsers) -> None:
    """``cns venture {status|checklist|list}``."""
    sp = subparsers.add_parser("venture", help="Fas, grindar och checklistor per venture")
    sub = sp.add_subparsers(dest="venture_cmd")

    st = sub.add_parser("status", help="Var står bygget — mätt, inte påstått")
    st.add_argument("slug")
    st.set_defaults(func=cmd_venture_status)

    cl = sub.add_parser("checklist", help="Receptets steg → milestones + issues")
    cl.add_argument("slug")
    cl.add_argument("--apply", action="store_true",
                    help="Skriv på riktigt (default: torrkörning)")
    cl.set_defaults(func=cmd_venture_checklist)

    ls = sub.add_parser("list", help="Hela portföljen: fas, skuld, grindbeslut")
    ls.set_defaults(func=cmd_venture_list)

    sp.set_defaults(func=lambda a: (sp.print_help(), sys.exit(1)))

    # cns reconcile — egen toppnivå: den handlar om HELA katalogen, inte en venture.
    rc = subparsers.add_parser(
        "reconcile", help="Ställ katalogen mot verkligheten (orphans, motsägelser, diff)")
    rc.add_argument("--apply", action="store_true",
                    help="Skriv catalog.generated.yaml (kröner inget)")
    rc.set_defaults(func=cmd_reconcile)
