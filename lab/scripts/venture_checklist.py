"""Receptets steg → riktiga arbetsuppgifter. Grinden → en milestone.

**Varför inte en fjärde lista:** CNS har redan ett arbetsuppgiftslager — GitHub issues under
milestones, med todos som checkboxar och acceptanskriterier (``issues_client.py``). Checklistorna
hör hemma där arbetet redan bor, inte i ännu en yta som ska hållas i synk.

**Poängen — härledda steg stänger sina egna issues.** Du bockar aldrig av "tester finns";
verkligheten gör det åt dig när testerna finns. Bara det som kräver ögon ("pratat med fem kunder")
kräver din hand. Nio av nitton steg i receptet är manuella — resten sköter sig själva.

Två regler maskinen aldrig bryter:
  1. **Ett manuellt steg stängs aldrig bakom din rygg.** Maskinen får inte påstå att du pratat
     med fem kunder. Den äger inte den sanningen.
  2. **Okänt stänger ingenting.** Vi stänger på bevis, aldrig på frånvaro av bevis.

Ren och injicerbar: ``gh`` är en duck-typad klient (``issues_client`` i drift, en fejk i test),
så modulen kan testas utan GitHub, utan nät och utan tokens.
"""
from __future__ import annotations

from dataclasses import dataclass

# Markören som binder en issue till sitt recept-steg. Ligger i bodyn, inte i titeln — titlar
# redigeras, och en checklista som tappar sin koppling när någon förbättrar en formulering
# är värdelös.
STEP_MARKER = "Recipe-step:"


@dataclass(frozen=True)
class _Step:
    key: str
    title: str
    check: str

    @property
    def is_manual(self) -> bool:
        return self.check == "manual"


def _steps_of(recipe: dict, phase: str) -> list[_Step]:
    for p in recipe.get("phases") or []:
        if str(p.get("key")) == phase:
            return [
                _Step(str(s.get("key")), str(s.get("title") or s.get("key")),
                      str(s.get("check") or ""))
                for s in (p.get("steps") or []) if s.get("key")
            ]
    return []


def _gate_of(recipe: dict, phase: str) -> dict:
    for p in recipe.get("phases") or []:
        if str(p.get("key")) == phase:
            return p.get("gate") or {}
    return {}


def step_key_of(issue: dict) -> str | None:
    """Vilket recept-steg hör den här issuen till? None om den inte är vår."""
    for line in str(issue.get("body") or "").splitlines():
        if line.strip().startswith(STEP_MARKER):
            return line.split(STEP_MARKER, 1)[1].strip().strip("`")
    return None


def milestone_title(slug: str, gate: dict, phase: str) -> str:
    return f"{slug}: {gate.get('title') or phase}"


def issue_body(slug: str, step: _Step, gate: dict) -> str:
    """Bodyn bär kopplingen till steget — och vad som mäter det.

    Ett härlett steg säger rakt ut att det stänger sig självt. Annars sitter man och bockar av
    saker maskinen redan vet, vilket är precis den handredigering vi byggt bort.
    """
    how = ("**Stängs automatiskt** när verkligheten säger så "
           f"(signal: `{step.check.split(':', 1)[-1]}`). Du behöver inte bocka av den."
           if not step.is_manual else
           "**Kräver ögon** — bara du kan avgöra den här. Stäng issuen när den är sann.")

    question = gate.get("question") or ""
    return (
        f"{STEP_MARKER} `{step.key}`\n\n"
        f"{how}\n\n"
        f"## Grinden detta steg öppnar\n\n"
        f"**{gate.get('title') or ''}** — {question}\n"
    )


def sync(
    slug: str,
    recipe: dict,
    *,
    phase: str,
    steps: dict[str, bool | None],
    gh,
    gates_skipped: list[str] | None = None,
    dry_run: bool = False,
) -> dict:
    """Håll venturens checklista i takt med verkligheten.

    Täcker TVÅ saker:
      1. **Fasen du står i** — vad som återstår för att passera nästa grind.
      2. **Skulden bakom dig** (``gates_skipped``) — stegen i de grindar du aldrig stängde.

    Punkt 2 är hela poängen för en vibe-kodad portfölj: orgkomp ligger i produktion, så dess
    live-fas har nästan inget kvar — men discovery, spec, mvp och konsolidera passerades aldrig.
    Att bara lista live-fasens rest vore att låtsas att skulden inte finns. Det är exakt det
    arbete "bygga om vertikalerna mot receptet" består av.

    Stänger de härledda issues vars signal blivit sann. Idempotent — kör den i en cron utan
    att den spammar dig.
    """
    # Skulden först: den är äldre, och den blockerar allt annat från att betyda något.
    phases = [*(gates_skipped or []), phase]

    # ALLA tillstånd, inte bara öppna: en stängd issue för ett steg som återfaller till rött
    # ska inte skapas på nytt. Verkligheten svänger; historiken gör det inte.
    try:
        existing_issues = gh.list_issues(node_slug=slug, state="all") or []
    except Exception:
        # En TORRKÖRNING ska aldrig kräva en token. Att fråga nätverket för att visa vad man
        # SKULLE göra är fel — då kan man inte ens planera offline. Utan GitHub antar vi att
        # inget finns; värsta utfallet är att torrkörningen listar något som redan finns.
        if not dry_run:
            raise
        existing_issues = []

    by_step = {k: i for i in existing_issues if (k := step_key_of(i))}

    would_create, created, closed = [], [], []

    for phase_key in phases:
        plan_steps = _steps_of(recipe, phase_key)
        gate = _gate_of(recipe, phase_key)

        for step in plan_steps:
            status = steps.get(step.key)
            existing = by_step.get(step.key)

            if existing is None:
                if status is True:
                    continue                 # redan gjort — skapa inte arbete som är klart
                would_create.append(step.title)
                if not dry_run:
                    milestone = _ensure_milestone(gh, slug, gate, phase_key, dry_run=dry_run)
                    issue = gh.create_issue(
                        node_slug=slug,
                        title=step.title,
                        body=issue_body(slug, step, gate),
                        milestone=(milestone or {}).get("number"),
                    )
                    created.append(issue)
                    by_step[step.key] = issue      # samma steg skapas aldrig två gånger
                continue

            # Issuen finns. Får verkligheten stänga den?
            #   - manuellt steg  → aldrig. Maskinen äger inte den sanningen.
            #   - okänt (None)   → aldrig. Vi stänger på bevis, inte på tystnad.
            if step.is_manual or status is not True:
                continue
            if str(existing.get("state") or "open") == "closed":
                continue
            if not dry_run:
                gh.close_issue(existing["number"])
            closed.append(existing["number"])

    return {"created": created, "closed": closed, "would_create": would_create}


def _ensure_milestone(gh, slug: str, gate: dict, phase: str, *, dry_run: bool) -> dict | None:
    """Grindens milestone — en per fas och venture. Skapas bara om den saknas."""
    title = milestone_title(slug, gate, phase)
    for ms in gh.list_milestones() or []:
        if str(ms.get("title")) == title:
            return ms
    if dry_run:
        return None
    return gh.create_milestone(
        title=title,
        description=(gate.get("question") or "").strip(),
    )
