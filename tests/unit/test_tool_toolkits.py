"""The per-task-type toolkit table (WAVE W3, 2026-09-08).

Follows the framework's ``core/controller/modules/intent_toolkits`` pattern --
a table of tool schemas plus a subset selector -- with the subset FAIL-CLOSED
and chosen by task type and agent role from ``configs/toolkit/``, never by a
model. The framework's own ``get_openai_tool_schemas`` ignores its ``choices``
argument and returns everything; the last test here pins that ours does not.

Zero model contacts, zero GPU.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.rails import tools
from speech_aware_evidence_acquisition.rails.tools import (
    TASK_TYPE_CARRIERS,
    TASK_TYPES,
    TOOLKIT_CONFIG_RELPATH,
    TOOLKIT_ROLES,
    TOOLKIT_SCHEMA,
    ToolCatalogError,
    default_toolkit_table,
    load_toolkit_table,
    parse_toolkit_table,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available


def _document(**overrides) -> dict:
    base = {
        "schema": TOOLKIT_SCHEMA,
        "toolkits": {
            "meeting": {
                "planner": {"tools": ["saea-tool-prompt-fit-tokens-v1"]},
                "observer": {"tools": ["saea-tool-speaker-turn-units-v2"]},
                "reviewer": {"tools": []},
            },
            "command": {
                "planner": {"tools": []},
                "observer": {"tools": ["saea-tool-slice-encode-v1"]},
                "reviewer": {"tools": ["saea-tool-legal-label-projection-v2"]},
            },
            "tool-call": {
                "planner": {"tools": []},
                "observer": {"tools": []},
                "reviewer": {"tools": []},
            },
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# The committed table.
# ---------------------------------------------------------------------------


def test_the_committed_table_loads_and_covers_every_task_type():
    table = default_toolkit_table()
    assert table.schema == TOOLKIT_SCHEMA
    assert sorted(table.toolkits) == sorted(TASK_TYPES)
    for task_type in TASK_TYPES:
        toolkit = table.for_task(task_type)
        assert sorted(toolkit.tools_by_role) == sorted(TOOLKIT_ROLES)


def test_every_id_in_the_committed_table_resolves_in_the_catalog():
    table = default_toolkit_table()
    for task_type in TASK_TYPES:
        toolkit = table.for_task(task_type)
        for role in TOOLKIT_ROLES:
            for entry in toolkit.entries_for(role):
                assert entry.manifest.system_invoked is True


def test_every_catalog_tool_is_offered_to_at_least_one_task_type():
    """A registered tool nothing may call is either a mistake in the table or
    a tool that should not be registered yet."""

    # New capabilities live in versioned opt-in tables; the default stays frozen.
    tables = [
        load_toolkit_table(path)
        for path in sorted((tools.REPO_ROOT / "configs" / "toolkit").glob("*.json"))
    ]
    offered = {
        tool_id
        for table in tables
        for task_type in TASK_TYPES
        for role in TOOLKIT_ROLES
        for tool_id in table.for_task(task_type).tools_for(role)
    }
    assert offered == set(tools.catalog_ids())


def test_the_committed_table_places_the_carrier_scoped_tools_correctly():
    table = default_toolkit_table()
    meeting = table.for_task("meeting")
    command = table.for_task("command")

    assert meeting.may_call("observer", "saea-tool-speaker-turn-units-v2")
    assert not command.may_call("observer", "saea-tool-speaker-turn-units-v2")
    assert command.may_call("reviewer", "saea-tool-legal-label-projection-v2")
    assert not meeting.may_call("reviewer", "saea-tool-legal-label-projection-v2")


def test_the_planner_owns_the_tokenizer_everywhere():
    """Budget and tokenization is the Planner's family (design note section
    7), so the tokenizer is in every task type's planner row and in no
    other."""

    table = default_toolkit_table()
    for task_type in TASK_TYPES:
        toolkit = table.for_task(task_type)
        assert toolkit.may_call("planner", "saea-tool-prompt-fit-tokens-v1")
        assert not toolkit.may_call("observer", "saea-tool-prompt-fit-tokens-v1")
        assert not toolkit.may_call("reviewer", "saea-tool-prompt-fit-tokens-v1")


def test_no_toolkit_offers_a_tool_to_a_solver_row():
    """The Solver is the frozen core and calls no tool, so there is no such
    role to declare."""

    assert "solver" not in TOOLKIT_ROLES
    document = json.loads(
        (tools.REPO_ROOT / TOOLKIT_CONFIG_RELPATH).read_text(encoding="utf-8")
    )
    for roles in document["toolkits"].values():
        assert "solver" not in roles


# ---------------------------------------------------------------------------
# Fail-closed.
# ---------------------------------------------------------------------------


def test_an_unknown_tool_id_refuses():
    document = _document()
    document["toolkits"]["meeting"]["observer"]["tools"] = ["saea-tool-invented-v1"]
    with pytest.raises(Exception):
        parse_toolkit_table(document)


def test_an_unknown_task_type_refuses():
    document = _document()
    document["toolkits"]["dictation"] = {
        "planner": {"tools": []},
        "observer": {"tools": []},
        "reviewer": {"tools": []},
    }
    with pytest.raises(ToolCatalogError) as excinfo:
        parse_toolkit_table(document)
    assert "dictation" in str(excinfo.value)


def test_a_missing_task_type_refuses():
    document = _document()
    del document["toolkits"]["tool-call"]
    with pytest.raises(ToolCatalogError):
        parse_toolkit_table(document)


def test_an_unknown_role_refuses():
    document = _document()
    document["toolkits"]["meeting"]["solver"] = {"tools": []}
    with pytest.raises(ToolCatalogError) as excinfo:
        parse_toolkit_table(document)
    assert "solver" in str(excinfo.value)


def test_a_missing_role_refuses():
    document = _document()
    del document["toolkits"]["meeting"]["reviewer"]
    with pytest.raises(ToolCatalogError):
        parse_toolkit_table(document)


def test_a_carrier_scoped_tool_in_the_wrong_task_type_refuses():
    document = _document()
    document["toolkits"]["command"]["observer"]["tools"] = [
        "saea-tool-speaker-turn-units-v2"
    ]
    with pytest.raises(ToolCatalogError) as excinfo:
        parse_toolkit_table(document)
    assert "earnings21" in str(excinfo.value)
    assert TASK_TYPE_CARRIERS["command"] == ("slurp",)


def test_a_repeated_tool_id_refuses():
    document = _document()
    document["toolkits"]["command"]["observer"]["tools"] = [
        "saea-tool-slice-encode-v1",
        "saea-tool-slice-encode-v1",
    ]
    with pytest.raises(ToolCatalogError):
        parse_toolkit_table(document)


@pytest.mark.parametrize(
    "broken",
    [
        {"schema": "something-else"},
        {"toolkits": {}},
        {"toolkits": []},
    ],
)
def test_a_malformed_table_refuses(broken):
    with pytest.raises(ToolCatalogError):
        parse_toolkit_table(_document(**broken))


def test_a_role_without_a_tools_list_refuses():
    document = _document()
    document["toolkits"]["meeting"]["observer"] = {"names": []}
    with pytest.raises(ToolCatalogError):
        parse_toolkit_table(document)
    document["toolkits"]["meeting"]["observer"] = ["saea-tool-slice-encode-v1"]
    with pytest.raises(ToolCatalogError):
        parse_toolkit_table(document)


def test_a_non_object_document_refuses():
    with pytest.raises(ToolCatalogError):
        parse_toolkit_table(["not", "an", "object"])


def test_an_unreadable_file_refuses(tmp_path):
    with pytest.raises(ToolCatalogError):
        load_toolkit_table(tmp_path / "missing.json")
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(ToolCatalogError):
        load_toolkit_table(broken)


def test_an_unknown_role_lookup_refuses():
    toolkit = default_toolkit_table().for_task("meeting")
    with pytest.raises(ToolCatalogError):
        toolkit.tools_for("solver")


def test_an_unknown_task_lookup_refuses():
    with pytest.raises(ToolCatalogError):
        default_toolkit_table().for_task("dictation")


# ---------------------------------------------------------------------------
# The framework pattern, with the subset actually applied.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not openjiuwen_available(), reason="needs the pinned openjiuwen runtime"
)
def test_cards_for_returns_the_subset_and_not_the_whole_catalog():
    """The framework's own ``IntentToolkits.get_openai_tool_schemas`` returns
    every schema whatever ``choices`` says; a toolkit whose selector does not
    select is not a toolkit."""

    table = default_toolkit_table()
    cards = table.cards_for("command", "reviewer")
    assert [card.id for card in cards] == ["saea-tool-legal-label-projection-v2"]
    assert len(cards) < len(tools.catalog_ids())
    assert all(card.properties["system_invoked"] is True for card in cards)

    # WAVE R7 (2026-09-08): the tool-call reviewer row is no longer empty --
    # it carries the hard-validity check that used to be a private branch
    # inside the retired A2T repair controller.
    reviewer_cards = table.cards_for("tool-call", "reviewer")
    assert [card.id for card in reviewer_cards] == ["saea-tool-a2t-hard-validity-v1"]
    assert len(reviewer_cards) < len(tools.catalog_ids())
