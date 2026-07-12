"""Verifiering av router-enrichment (skiva 3, scripts/router.py, #90).

Stdlib-test — unittest.mock, inga externa beroenden. Körs fristående
(``python tests/test_router_enrichment.py``) ELLER under pytest.

Acceptanskriterier (issue #90):
(1) Pass länkat till frontend-nod + bug-issue → active_routing.json speglar
    route()-utfallet (delivery-station, frontend-squad, sonnet).
(2) Inget länkat pass → router.py beter sig exakt som före (ingen regression).
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.router as router_module
from scripts.router import _agentur_enrich, _agentur_line, main  # noqa: E402


# ---------------------------------------------------------------------------
# Hjälpare
# ---------------------------------------------------------------------------

_FRONTEND_BUG_ROUTE = {
    "agentur": "produktutveckling",
    "domain": "cortxt",
    "node_type": "frontend",
    "issue_type": "bug",
    "flow": ["delivery", "review"],
    "station": "delivery",
    "discipline": "Frontend",
    "department": "Engineering",
    "squad": ["frontend-utvecklare"],
    "model": "sonnet",
}

_ACTIVE_FRONTEND_BUG = {
    "type": "delivery",
    "focus_kind": "node",
    "focus_ref": "cortxt-dashboard",
    "focus_issue_type": "bug",
}

_NODE_META_FRONTEND = {"type": "frontend", "domain": "cortxt"}


# ---------------------------------------------------------------------------
# Test (1): frontend-nod + bug-issue → delivery/frontend-squad/sonnet
# ---------------------------------------------------------------------------


def test_agentur_enrich_frontend_bug() -> None:
    """(1a) _agentur_enrich() returnerar rätt route()-utfall för frontend+bug."""
    with (
        patch("scripts.session_store.get_active", return_value=_ACTIVE_FRONTEND_BUG),
        patch("scripts.md_parser.read_node", return_value=(_NODE_META_FRONTEND, {}, "")),
        patch("scripts.agentur_routing.route", return_value=_FRONTEND_BUG_ROUTE),
    ):
        result = _agentur_enrich()

    assert result is not None, "_agentur_enrich() ska returnera ett resultat"
    assert result["station"] == "delivery", f"station={result['station']}"
    assert result["model"] == "sonnet", f"model={result['model']}"
    assert "frontend-utvecklare" in result["squad"], f"squad={result['squad']}"


def test_active_routing_json_enriched() -> None:
    """(1b) active_routing.json berikad med station/squad/modell när keyword-routing träffar."""
    with tempfile.TemporaryDirectory() as tmpdir:
        routing_file = Path(tmpdir) / "active_routing.json"

        payload = json.dumps({"prompt": "implementera ny react-komponent"})

        with (
            patch("scripts.session_store.get_active", return_value=_ACTIVE_FRONTEND_BUG),
            patch("scripts.md_parser.read_node", return_value=(_NODE_META_FRONTEND, {}, "")),
            patch("scripts.agentur_routing.route", return_value=_FRONTEND_BUG_ROUTE),
            patch.object(router_module, "ROOT", Path(tmpdir)),
            patch("sys.stdin", io.StringIO(payload)),
            patch("sys.stdout", io.StringIO()),
        ):
            (Path(tmpdir) / "exports").mkdir(parents=True, exist_ok=True)
            router_module.main()
            actual_file = Path(tmpdir) / "exports" / "active_routing.json"

        assert actual_file.exists(), "active_routing.json ska skrivas"
        data = json.loads(actual_file.read_text())
        assert data.get("station") == "delivery", f"station saknas/fel: {data}"
        assert data.get("squad") == ["frontend-utvecklare"], f"squad saknas/fel: {data}"


def test_active_routing_json_no_keyword_agent() -> None:
    """(1c) active_routing.json skrivs med agentur-data även utan keyword-routing-träff."""
    with tempfile.TemporaryDirectory() as tmpdir:
        payload = json.dumps({"prompt": "hej"})  # för kort → ingen keyword-match

        with (
            patch("scripts.session_store.get_active", return_value=_ACTIVE_FRONTEND_BUG),
            patch("scripts.md_parser.read_node", return_value=(_NODE_META_FRONTEND, {}, "")),
            patch("scripts.agentur_routing.route", return_value=_FRONTEND_BUG_ROUTE),
            patch.object(router_module, "ROOT", Path(tmpdir)),
            patch("sys.stdin", io.StringIO(payload)),
            patch("sys.stdout", io.StringIO()),
        ):
            (Path(tmpdir) / "exports").mkdir(parents=True, exist_ok=True)
            router_module.main()
            actual_file = Path(tmpdir) / "exports" / "active_routing.json"

        assert actual_file.exists(), "active_routing.json ska skrivas (enrich utan keyword-agent)"
        data = json.loads(actual_file.read_text())
        assert data.get("station") == "delivery"
        assert data.get("model") == "sonnet"


# ---------------------------------------------------------------------------
# Test (2): inget länkat pass → exakt nuvarande beteende (ingen regression)
# ---------------------------------------------------------------------------


def test_no_active_session_no_enrich() -> None:
    """(2a) _agentur_enrich() returnerar None när inget aktivt pass finns."""
    with patch("scripts.session_store.get_active", return_value=None):
        result = _agentur_enrich()
    assert result is None


def test_wrong_focus_kind_no_enrich() -> None:
    """(2b) _agentur_enrich() returnerar None om focus_kind inte är 'node'."""
    state = {"focus_kind": "issue", "focus_ref": "42"}
    with patch("scripts.session_store.get_active", return_value=state):
        result = _agentur_enrich()
    assert result is None


def test_no_regression_keyword_routing() -> None:
    """(2c) Inget aktivt pass → [ROUTING]/[MODEL] oförändrade, ingen [AGENTUR-ROUTING]."""
    with tempfile.TemporaryDirectory() as tmpdir:
        payload = json.dumps({"prompt": "implementera ny react-komponent"})
        captured = io.StringIO()

        with (
            patch("scripts.session_store.get_active", return_value=None),
            patch.object(router_module, "ROOT", Path(tmpdir)),
            patch("sys.stdin", io.StringIO(payload)),
            patch("sys.stdout", captured),
        ):
            (Path(tmpdir) / "exports").mkdir(parents=True, exist_ok=True)
            router_module.main()

        output = captured.getvalue()
        assert "[ROUTING] @frontend-" in output, "keyword-routing ska fortfarande träffa"
        assert "[MODEL:" in output, "[MODEL]-rad ska fortfarande skrivas"
        assert "[AGENTUR-ROUTING]" not in output, "ingen agentur-injection utan aktivt pass"


def test_no_regression_routing_file_deleted_without_enrich() -> None:
    """(2d) Ingen keyword-match + inget pass → routing-filen raderas (stale-bugg-skydd)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        exports = Path(tmpdir) / "exports"
        exports.mkdir()
        routing_file = exports / "active_routing.json"
        routing_file.write_text("{}", encoding="utf-8")  # pre-existing stale fil

        payload = json.dumps({"prompt": "hej"})  # för kort → ingen match

        with (
            patch("scripts.session_store.get_active", return_value=None),
            patch.object(router_module, "ROOT", Path(tmpdir)),
            patch("sys.stdin", io.StringIO(payload)),
            patch("sys.stdout", io.StringIO()),
        ):
            router_module.main()

        assert not routing_file.exists(), "stale routing-fil ska raderas"


# ---------------------------------------------------------------------------
# Hjälpfunktion _agentur_line
# ---------------------------------------------------------------------------


def test_agentur_line_format() -> None:
    """_agentur_line() formaterar raden korrekt."""
    line = _agentur_line(_FRONTEND_BUG_ROUTE)
    assert line.startswith("[AGENTUR-ROUTING]")
    assert "station=delivery" in line
    assert "@frontend-användare" in line or "Frontend" in line or "frontend" in line.lower()
    assert "modell=sonnet" in line


if __name__ == "__main__":
    test_agentur_enrich_frontend_bug()
    test_active_routing_json_enriched()
    test_active_routing_json_no_keyword_agent()
    test_no_active_session_no_enrich()
    test_wrong_focus_kind_no_enrich()
    test_no_regression_keyword_routing()
    test_no_regression_routing_file_deleted_without_enrich()
    test_agentur_line_format()
    print("OK — router enrichment skiva 3: alla acceptanskriterier gröna")
