"""Tester för den kanoniska arbetstaxonomin (scripts/work_taxonomy.py).

Låser (1) bakåtkompat på issue-typerna efter att enkällan flyttades hit från issues_client,
och (2) referensintegritet i lager-hierarkin (ingen dinglande förälder).
"""
from __future__ import annotations

from scripts import work_taxonomy as wt


def test_issue_types_backward_compatible():
    # Exakt de historiska värdena issues_client ägde innan flytten.
    assert set(wt.VALID_ISSUE_TYPES) == {"story", "bug", "spike", "chore"}
    assert wt.DEFAULT_ISSUE_TYPE == "story"


def test_issues_client_reexports_same_values():
    # Regressionsskydd för import-flytten: issues_client ska se EN källa.
    from scripts import issues_client as ic

    assert ic.VALID_ISSUE_TYPES is wt.VALID_ISSUE_TYPES
    assert ic.DEFAULT_ISSUE_TYPE == wt.DEFAULT_ISSUE_TYPE


def test_default_issue_type_is_marked_default():
    defaults = [t.name for t in wt.ISSUE_TYPES if t.is_default]
    assert defaults == [wt.DEFAULT_ISSUE_TYPE]


def test_layer_hierarchy_reference_integrity():
    names = set(wt.layer_names())
    tops = [layer.name for layer in wt.LAYERS if layer.parent is None]
    # Exakt en toppnivå (initiative), resten pekar på ett existerande lager.
    assert tops == ["initiative"]
    for layer in wt.LAYERS:
        if layer.parent is not None:
            assert layer.parent in names, f"{layer.name} har dinglande förälder {layer.parent}"


def test_layer_order_and_lookup():
    assert wt.layer_names() == ("initiative", "epic", "story", "todo")
    assert wt.layer("epic").parent == "initiative"
    assert wt.layer("todo").parent == "story"
    assert wt.layer("saknas") is None
