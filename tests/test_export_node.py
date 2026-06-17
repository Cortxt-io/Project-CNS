"""Core tests for `cns export <slug>` (Del 2.2).

Exercises the pure helpers behind the CLI command — no network, no agency.
"""

import argparse
import json

import pytest

import cns
from scripts.catalog import load_catalog, DECISIONS_DIR


def _slug_with_decision() -> str:
    for slug in load_catalog():
        if (DECISIONS_DIR / f"{slug}.md").exists():
            return slug
    pytest.skip("no node with a decision file in catalog")


def _slug_without_decision() -> str:
    for slug in load_catalog():
        if not (DECISIONS_DIR / f"{slug}.md").exists():
            return slug
    pytest.skip("every node has a decision file")


def test_payload_has_fields_and_decision():
    slug = _slug_with_decision()
    payload = cns._node_export_payload(slug)
    assert payload["slug"] == slug
    assert payload["fields"].get("title")
    assert payload["decision"]  # non-empty string


def test_markdown_has_required_sections():
    slug = _slug_with_decision()
    md = cns._render_node_markdown(cns._node_export_payload(slug))
    title = load_catalog()[slug]["title"]
    assert md.startswith(f"# {title}")
    assert "## Structure" in md
    assert "## Decision" in md


def test_markdown_marks_missing_decision():
    slug = _slug_without_decision()
    md = cns._render_node_markdown(cns._node_export_payload(slug))
    assert "No decision recorded" in md


def test_json_format_is_valid_and_complete(capsys):
    slug = _slug_with_decision()
    args = argparse.Namespace(slug=slug, format="json", with_llm=False)
    cns.cmd_export_node(args)
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["slug"] == slug
    assert "fields" in data and "decision" in data


def test_missing_slug_exits():
    args = argparse.Namespace(slug="this-slug-does-not-exist", format="md", with_llm=False)
    with pytest.raises(SystemExit):
        cns.cmd_export_node(args)
