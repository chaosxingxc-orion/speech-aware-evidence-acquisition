"""The tool catalog's own contract (WAVE W3, 2026-09-08).

Manifest completeness, the system-invoked marker enforced AT REGISTRATION,
and the pinned-hash rule -- all over locally built objects, so this module
holds whether or not any wrapper is registered yet. The catalog-wide
assertions (every REGISTERED manifest complete and pinned, the framework
``ToolCard`` over a real entry) live beside the wrappers in
``tests/unit/test_tool_wrappers.py``.

Zero model contacts, zero GPU, no ``openjiuwen`` import.
"""

from __future__ import annotations

import inspect

import pytest

from speech_aware_evidence_acquisition.rails import tools
from speech_aware_evidence_acquisition.rails.tools import (
    COST_CLASSES,
    GENERAL_SCOPE,
    INVOCATION,
    LEDGER_ROW_TYPES,
    TOOL_AXES,
    DerivationRecord,
    ToolCatalogError,
    ToolManifest,
    ToolResult,
    build_tool_entry,
    source_sha256,
    tool_input_params,
)

_PINNED_TARGET = "speech_aware_evidence_acquisition.core.replay_signals:flag_spans"


def _sample_body(value: int) -> ToolResult:
    return ToolResult(tool_id="saea-tool-sample-v1", result=value)


def _manifest(**overrides: object) -> ToolManifest:
    base = dict(
        tool_id="saea-tool-sample-v1",
        description="A sample manifest used only by this test module.",
        source_ref=_PINNED_TARGET,
        pinned_sha256=source_sha256(_PINNED_TARGET),
        inputs={"value": "int"},
        outputs={"result": "int"},
        changes_bytes=False,
        derivation_record=None,
        cost_class="cpu",
        axis="OBS",
        scope=GENERAL_SCOPE,
        ledger_row_type="none",
    )
    base.update(overrides)
    return ToolManifest(**base)  # type: ignore[arg-type]


def test_a_complete_manifest_validates_and_normalizes():
    manifest = _manifest(pinned_sha256=source_sha256(_PINNED_TARGET).upper()).validate()
    assert manifest.pinned_sha256 == source_sha256(_PINNED_TARGET)
    assert manifest.system_invoked is True
    assert dict(manifest.inputs) == {"value": "int"}


@pytest.mark.parametrize(
    "overrides",
    [
        {"tool_id": ""},
        {"tool_id": "diarization-v1"},  # no saea-tool- prefix
        {"description": "  "},
        {"source_ref": "no-colon"},
        {"source_ref": "a:b:c"},
        {"pinned_sha256": "abc"},
        {"pinned_sha256": "z" * 64},
        {"inputs": {}},
        {"outputs": {}},
        {"cost_class": "tpu"},
        {"axis": "OTHER"},
        {"scope": "carrier:librispeech"},
        {"scope": "carrier"},
        {"ledger_row_type": "model-contact"},
        {"changes_bytes": True, "derivation_record": None},
        {"changes_bytes": False, "derivation_record": "saea-slice-derivation-v1"},
        {"cost_class": "contact", "ledger_row_type": "none"},
        {"system_invoked": "yes"},
    ],
)
def test_an_incomplete_or_contradictory_manifest_refuses(overrides):
    with pytest.raises(ToolCatalogError):
        _manifest(**overrides).validate()


def test_the_frozen_core_can_never_be_a_tool_ledger_row_type():
    """There is deliberately no ``model-contact`` ledger row: the core is
    reached through the single door and is never a catalog entry."""

    assert "model-contact" not in LEDGER_ROW_TYPES
    assert set(LEDGER_ROW_TYPES) == {"none", "tool-contact", "service-contact"}
    assert set(TOOL_AXES) == {"OBS", "ORG", "SUPPLY", "USE"}
    assert set(COST_CLASSES) == {"cpu", "gpu", "contact"}


def test_entry_construction_refuses_a_manifest_without_the_system_invoked_marker():
    """The 2026-08-08 ruling enforced in code: a framework tool base is
    reserved for a MODEL-invoked arm, so a manifest that does not claim
    system invocation cannot enter this catalog."""

    with pytest.raises(ToolCatalogError) as excinfo:
        build_tool_entry(_manifest(system_invoked=False), _sample_body)
    assert "system_invoked" in str(excinfo.value)
    assert "saea-tool-sample-v1" not in tools.catalog_ids()


def test_entry_construction_refuses_a_non_callable_body():
    with pytest.raises(ToolCatalogError):
        build_tool_entry(_manifest(), "not callable")  # type: ignore[arg-type]


def test_entry_construction_refuses_a_non_manifest():
    with pytest.raises(ToolCatalogError):
        build_tool_entry({"tool_id": "saea-tool-x-v1"}, _sample_body)  # type: ignore[arg-type]


def test_a_stale_pin_is_refused():
    with pytest.raises(ToolCatalogError) as excinfo:
        tools.assert_pinned_hash(_manifest(pinned_sha256="0" * 64))
    assert "re-pinned" in str(excinfo.value)


def test_source_sha256_refuses_an_unresolvable_reference():
    with pytest.raises(ToolCatalogError):
        source_sha256("speech_aware_evidence_acquisition.core.replay_signals:nope")
    with pytest.raises(ToolCatalogError):
        source_sha256("speech_aware_evidence_acquisition.no_such_module:thing")


def test_manifest_as_dict_carries_every_design_note_field():
    document = _manifest().validate().as_dict()
    for field in (
        "tool_id",
        "pinned_sha256",
        "inputs",
        "outputs",
        "changes_bytes",
        "derivation_record",
        "cost_class",
        "axis",
        "scope",
        "ledger_row_type",
        "system_invoked",
    ):
        assert field in document
    assert document["invocation"] == INVOCATION == "system"


def test_input_params_declare_python_types_and_system_invocation():
    schema = tool_input_params(_manifest().validate())
    assert schema["type"] == "object"
    assert schema["properties"] == {"value": {"python_type": "int"}}
    assert schema["required"] == ["value"]
    assert schema["x-invocation"] == "system"


def test_derivation_record_is_json_safe():
    record = DerivationRecord(
        tool_id="saea-tool-sample-v1",
        transforms=("rms-norm",),
        pre_sha256="a" * 64,
        post_sha256="b" * 64,
    )
    assert record.as_dict() == {
        "tool_id": "saea-tool-sample-v1",
        "transforms": ["rms-norm"],
        "pre_sha256": "a" * 64,
        "post_sha256": "b" * 64,
    }


def test_resolve_refuses_an_unknown_id():
    with pytest.raises(Exception):
        tools.resolve_tool("saea-tool-does-not-exist-v1")


def test_the_module_imports_no_framework_client_at_module_level():
    """D2 zero-dependency gate: ``rails.tools`` imports with ``openjiuwen``
    absent, so no framework symbol may be bound at import time."""

    module_level = [
        line
        for line in inspect.getsource(tools).splitlines()
        if line.startswith("import ") or line.startswith("from ")
    ]
    assert module_level
    assert not any("openjiuwen" in line for line in module_level)
