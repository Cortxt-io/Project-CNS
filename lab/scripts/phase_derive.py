"""Fasen HÄRLEDS ur stegen — den handredigeras inte.

**Varför:** ``current_phase`` i ``roadmaps/<slug>.md`` var ett handfält, och handfält driver isär
från verkligheten. Men hur långt ett bygge kommit är inte en åsikt: repot vet om det finns tester,
Vercel vet om det finns en prod-deploy. **Allt som kan mätas ska mätas.**

Tre nivåer (Stage-Gates faktiska struktur — arbetsstadier åtskilda av beslutsgrindar):

    FAS    — var bygget står.      Härleds ur stegen. Denna modul.
    STEG   — arbetet i fasen.      ``derived:<signal>`` mäts; ``manual`` kryssas i vaulten.
    GRIND  — ska vi fortsätta?     Kan ALDRIG mätas. Rikard skriver go/kill/hold/recycle.

**Den bärande regeln: ett steg som inte kan avgöras är ``None``, aldrig ``False``.** En härledare
som gissar är värre än ingen härledare, för då börjar man lita på den. ``None`` betyder "vi vet
inte" — och en grind öppnas på bevis, inte på frånvaro av bevis.

Ren och transport-fri: funktionerna tar in signaler (dict) och returnerar plain data. Ingen IO,
inget nät, inga filer — anroparen samlar signalerna (``signals.py`` / reconcile) och matar hit.
"""
from __future__ import annotations

DERIVED_PREFIX = "derived:"

# En grind som legat orörd längre än så här, medan verkligheten rört sig, är sannolikt inte ett
# beslut längre — bara ett gammalt ja som ingen omprövat.
GATE_STALE_DAYS = 90


def check_step(step: dict, *, signals: dict, checked: set[str]) -> bool | None:
    """Är det här steget klart? ``True`` / ``False`` / ``None`` (kan inte avgöras).

    ``check: manual``           → kryssat i vaultens venture-not (kräver ögon, inte mätning)
    ``check: derived:<signal>`` → mäts ur verkligheten; saknas signalen är svaret ``None``

    ``None`` är inte ett fel — det är ärlighet. Ett okänt steg får aldrig öppna en grind.
    """
    check = str(step.get("check") or "").strip()
    key = str(step.get("key") or "")

    if check == "manual":
        return key in checked

    if check.startswith(DERIVED_PREFIX):
        signal = check[len(DERIVED_PREFIX):]
        if signal not in signals:
            return None                      # signalen finns inte → vi VET inte
        return bool(signals[signal])

    return None                              # okänt check-språk → okänt, inte krasch


def step_status(phase: dict, *, signals: dict, checked: set[str]) -> dict[str, bool | None]:
    """Alla steg i en fas → ``{steg-key: True|False|None}``."""
    return {
        str(s.get("key")): check_step(s, signals=signals, checked=checked)
        for s in (phase.get("steps") or [])
        if s.get("key")
    }


def blocked_by(phase: dict, status: dict[str, bool | None]) -> list[str]:
    """Vilka av grindens krav är INTE gröna? Tomt = grinden kan öppnas.

    Appen ska kunna säga *vad* som stoppar, inte bara att något gör det.
    """
    gate = phase.get("gate") or {}
    requires = gate.get("requires") or [s.get("key") for s in (phase.get("steps") or [])]
    return [key for key in requires if status.get(key) is not True]


def gate_open(phase: dict, status: dict[str, bool | None]) -> bool:
    """Är fasens grind passerbar? Bara om varje krävt steg är bevisat grönt.

    Okänt (``None``) räknas INTE som grönt. En grind öppnas på bevis.
    """
    return not blocked_by(phase, status)


def derive_phase(recipe: dict, *, signals: dict, checked: set[str]) -> dict:
    """Var står bygget, och vilka grindar hoppades över på vägen?

    **Fasen är BEVIS, inte kryss.** Har en venture en live-URL så ÄR den live — även om du aldrig
    kryssade "marknadskarta". Att låta ett okryssat discovery-steg pinna fast något som ligger i
    produktion vore tekniskt korrekt och praktiskt värdelöst.

    Varje fas deklarerar ``reached_when: <signal>`` — beviset på att bygget nått hit. Fasen är den
    längst gångna vars bevis finns.

    **Överhoppade grindar är inte en bugg — de är diagnosen.** En venture som är live men vars
    spec-grind aldrig stängdes är exakt vad "vibe-kodad" betyder, uttryckt i data. Systemet ska
    säga det rakt ut, inte dölja det bakom en påhittad fas.

    Returnerar:
        {phase, title, steps, gate: {…, blocked_by}, gates_skipped: [fas-keys]}
    """
    phases = recipe.get("phases") or []
    if not phases:
        return {"phase": "unknown", "title": "", "steps": {},
                "gate": {}, "gates_skipped": []}

    all_steps: dict[str, bool | None] = {}
    statuses: dict[str, dict] = {}
    for phase in phases:
        status = step_status(phase, signals=signals, checked=checked)
        statuses[str(phase.get("key"))] = status
        all_steps.update(status)

    # Fasen: längst gångna vars BEVIS finns. Ingen bevisad → första fasen (inget byggt än).
    current = phases[0]
    for phase in phases:
        proof = str(phase.get("reached_when") or "").strip()
        if proof and signals.get(proof):
            current = phase

    current_key = str(current.get("key") or "unknown")
    current_index = phases.index(current)

    # Skulden bakom oss — men bara den vi kan BEVISA. Att beskylla någon för att ha hoppat över
    # en grind vi aldrig mätte vore samma lögn som att gissa ett steg. Röd = bevisat ogjort;
    # okänd = vi vet inte, och det säger vi.
    gates_skipped, gates_unknown = [], []
    for p in phases[:current_index]:
        key = str(p.get("key"))
        missing = blocked_by(p, statuses[key])
        if not missing:
            continue
        if any(statuses[key].get(m) is False for m in missing):
            gates_skipped.append(key)        # minst ett krav är bevisat ogjort
        else:
            gates_unknown.append(key)        # allt som fattas är omätt

    gate = current.get("gate") or {}
    return {
        "phase": current_key,
        "title": str(current.get("title") or ""),
        "steps": all_steps,
        "gate": {
            "phase": current_key,
            "title": str(gate.get("title") or ""),
            "question": str(gate.get("question") or ""),
            "blocked_by": blocked_by(current, statuses[current_key]),
        },
        "gates_skipped": gates_skipped,
        "gates_unknown": gates_unknown,
    }


def contradiction(*, phase: str, gate_decision: str | None, gate_age_days: int | None) -> str | None:
    """Säger verkligheten och omdömet emot varandra? Returnerar vad som skaver, annars None.

    Detta är luckan ingen prior art löser: reconcile upptäcker att en fil *försvann*, aldrig att
    den *ljuger*. En not som fortfarande finns ger ingen orphan-signal, inget schemafel, ingen
    CI-fail — hur gammal den än är. Så här mäter vi den ändå, genom att ställa det HÄRLEDDA mot
    det DEKLARERADE.

    Visas, tvingas inte. En hård grind skulle bara få en att stämpla datumet utan att tänka.
    """
    if gate_decision == "kill":
        # Grinden sa kill — men verkligheten fortsätter leverera. Något stämmer inte,
        # och det är inte koden. Antingen är beslutet inte genomfört, eller inte menat.
        return (f"Grindbeslutet är 'kill', men bygget står i '{phase}' och rör sig. "
                f"Antingen är beslutet inte genomfört — eller inte längre sant.")

    if gate_age_days is not None and gate_age_days > GATE_STALE_DAYS:
        return (f"Grindbeslutet ({gate_decision or 'inget'}) är {gate_age_days} dagar gammalt "
                f"medan bygget står i '{phase}'. Det är sannolikt inte ett beslut längre, "
                f"bara ett gammalt ja.")

    return None
