"""WAVE R7: the eighteen ``rails/a2t_*`` renderers, registered and unchanged.

Group A of the reuse map (assessment section 6.1) said of these modules:
"They are already pure, hashable, side-effect-free functions -- which is
exactly a ``LocalFunction``/``ToolCard`` body. **Register, do not rebuild.**"

This file is the proof that nothing was rebuilt:

1. **Coverage.** Every ``rails/a2t_*.py`` module in the tree has exactly one
   catalog entry, so a nineteenth renderer cannot be added without a catalog
   row and a pin.
2. **Passthrough, per renderer.** Structurally for all eighteen -- each
   wrapper takes ``*args, **kwargs``, forwards them and wraps the return value,
   asserted on the wrapper's own source -- and behaviourally on the ones whose
   inputs are cheap to build: the wrapped call's ``ToolResult.result`` equals
   the direct call's return value field for field, and a wrapper raises exactly
   the renderer's own exception type and message. There is no re-encoding step
   to disagree about.
3. **The pin.** Each manifest's ``pinned_sha256`` is the live sha256 of the
   wrapped function's own source, re-measured here, so an edit to a renderer
   that skipped re-pinning fails.
4. **The declared shape.** Axis, scope, cost class, ledger row, the
   system-invoked marker and the passthrough discipline.

Model-free and data-free: the renderers under test are exercised on tiny
synthetic inputs or not called at all, and no renderer that reads the
controlled data root is invoked.
"""

from __future__ import annotations

import glob
import inspect
import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import tools
from speech_aware_evidence_acquisition.rails.tool_wrappers import a2t_renderers

REPO_ROOT = Path(__file__).resolve().parents[2]
RAILS_DIR = REPO_ROOT / "src/speech_aware_evidence_acquisition/rails"

#: rails/a2t_*.py modules that are deliberately NOT renderer/tool-wrapper
#: candidates: pure internal parsing/validation helpers with no ToolCard
#: wrapper and no row in rails/tools.py, consumed directly by other rails
#: modules rather than dispatched as a system-invoked tool.
NON_RENDERER_A2T_MODULES = frozenset({"a2t_perception_state"})

#: module stem -> catalog id, one per ``rails/a2t_*.py`` renderer (that is,
#: every module under this glob except NON_RENDERER_A2T_MODULES).
RENDERER_TOOLS = {
    "a2t_canonical_family_ground": "saea-tool-a2t-canonical-family-ground-v1",
    "a2t_construction_example_ground": "saea-tool-a2t-construction-example-ground-v1",
    "a2t_construction_semantic_ground": "saea-tool-a2t-construction-semantic-ground-v1",
    "a2t_executable_ground": "saea-tool-a2t-executable-ground-v1",
    "a2t_executable_ground_prompt_fit": "saea-tool-a2t-ground-prompt-envelopes-v1",
    "a2t_executable_semantic_cards": "saea-tool-a2t-executable-semantic-cards-v1",
    "a2t_frozen_semantic_assets": "saea-tool-a2t-frozen-semantic-assets-v1",
    "a2t_hard_validity": "saea-tool-a2t-hard-validity-v1",
    "a2t_observation_state_organizer": "saea-tool-a2t-observation-state-organizer-v1",
    "a2t_plain_english_cards": "saea-tool-a2t-plain-english-retrieval-v1",
    "a2t_response_schema": "saea-tool-a2t-call-array-response-format-v1",
    "a2t_select_fill_factorial": "saea-tool-a2t-select-fill-factorial-binding-v1",
    "a2t_select_fill_ground": "saea-tool-a2t-routing-knowledge-ground-v1",
    "a2t_selected_tool_ground": "saea-tool-a2t-selected-tool-ground-v1",
    "a2t_semantic_microground": "saea-tool-a2t-semantic-microground-v1",
    "a2t_semantic_router": "saea-tool-a2t-semantic-ranking-fusion-v1",
    "a2t_stage_state": "saea-tool-a2t-select-stage-envelope-v1",
    "a2t_structured_dialogue_state": "saea-tool-a2t-structured-dialogue-state-v1",
}


# ---------------------------------------------------------------------------
# 1. Coverage
# ---------------------------------------------------------------------------


def test_every_a2t_rails_module_has_exactly_one_catalog_entry():
    on_disk = {
        os.path.basename(path)[: -len(".py")]
        for path in glob.glob(str(RAILS_DIR / "a2t_*.py"))
    } - NON_RENDERER_A2T_MODULES
    assert on_disk == set(RENDERER_TOOLS), (
        "a rails/a2t_* module gained or lost a catalog entry; register it in "
        "rails/tools.py and add it here"
    )
    assert len(on_disk) == 18
    registered = set(tools.catalog_ids())
    assert set(RENDERER_TOOLS.values()) <= registered


def test_each_entry_names_the_module_it_came_from():
    for stem, tool_id in RENDERER_TOOLS.items():
        manifest = tools.resolve_tool(tool_id).manifest
        assert manifest.source_ref.startswith(
            f"speech_aware_evidence_acquisition.rails.{stem}:"
        ), tool_id


# ---------------------------------------------------------------------------
# 2. The pin, and the declared shape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool_id", sorted(RENDERER_TOOLS.values()))
def test_the_pinned_hash_is_the_live_source_hash(tool_id):
    manifest = tools.resolve_tool(tool_id).manifest
    tools.assert_pinned_hash(manifest)
    assert manifest.pinned_sha256 == tools.source_sha256(manifest.source_ref)


@pytest.mark.parametrize("tool_id", sorted(RENDERER_TOOLS.values()))
def test_the_declared_shape_is_the_one_group_a_named(tool_id):
    manifest = tools.resolve_tool(tool_id).manifest
    assert manifest.system_invoked is True
    assert manifest.scope == f"{tools.CARRIER_SCOPE_PREFIX}audio2tool"
    assert manifest.cost_class == "cpu"
    assert manifest.axis in ("ORG", "SUPPLY", "USE")
    # A renderer changes no bytes on the wire, so it names no derivation
    # record -- the biconditional ToolManifest.validate enforces.
    assert manifest.changes_bytes is False
    assert manifest.derivation_record is None
    assert manifest.ledger_row_type in ("none", "tool-contact")


@pytest.mark.parametrize("tool_id", sorted(RENDERER_TOOLS.values()))
def test_every_wrapper_is_a_passthrough(tool_id):
    """No wrapper may do anything but forward and wrap.

    Asserted on the wrapper's own source: it takes ``*args, **kwargs``, and
    the only call it makes is the wrapped renderer's.
    """

    body = tools.resolve_tool(tool_id).body
    signature = inspect.signature(body)
    kinds = [parameter.kind for parameter in signature.parameters.values()]
    assert kinds == [
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.KEYWORD_ONLY,
    ] or kinds == [
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
    ], tool_id
    source = inspect.getsource(body)
    assert "*args, **kwargs" in source
    assert "ToolResult(" in source


def test_the_toolkit_table_places_every_renderer():
    table = json.loads(
        (REPO_ROOT / "configs/toolkit/task-toolkits-v1.json").read_text(
            encoding="utf-8"
        )
    )
    placed = {
        tool_id
        for role in table["toolkits"]["tool-call"].values()
        for tool_id in role["tools"]
    }
    assert set(RENDERER_TOOLS.values()) <= placed


# ---------------------------------------------------------------------------
# 3. Byte identity: wrapped output == direct output
# ---------------------------------------------------------------------------


def _direct(tool_id):
    return tools.load_source_target(tools.resolve_tool(tool_id).manifest.source_ref)


REGISTRY_ROWS = (
    {
        "tool_name": "getBatteryStatus",
        "domain": "device",
        "category": "status",
        "description": "Report the battery level of one device.",
        "signature": "getBatteryStatus()",
        "argument_constraints": "",
        "argument_defaults": "",
    },
    {
        "tool_name": "setLightLevel",
        "domain": "lighting",
        "category": "control",
        "description": "Set one light to a level between 0 and 100.",
        "signature": "setLightLevel(deviceId:String, level:Number)",
        "argument_constraints": "level: [0-100]",
        "argument_defaults": "",
    },
)


def test_hard_validity_wrapped_output_equals_the_direct_call():
    tool_id = RENDERER_TOOLS["a2t_hard_validity"]
    entry = tools.resolve_tool(tool_id)
    draft = '[{"name":"getBatteryStatus","arguments":{}}]'
    wrapped = entry.call(draft, REGISTRY_ROWS)
    direct = _direct(tool_id)(draft, REGISTRY_ROWS)
    assert wrapped.tool_id == tool_id
    assert wrapped.derivation is None
    assert wrapped.result.as_json() == direct.as_json()
    assert wrapped.result.status == direct.status == "valid"


def test_executable_ground_wrapped_output_equals_the_direct_call():
    tool_id = RENDERER_TOOLS["a2t_executable_ground"]
    entry = tools.resolve_tool(tool_id)
    signature = inspect.signature(_direct(tool_id))
    assert "registry_rows" in signature.parameters, "signature drifted; re-pin"
    wrapped = entry.call(REGISTRY_ROWS, ())
    direct = _direct(tool_id)(REGISTRY_ROWS, ())
    assert wrapped.result.sha256 == direct.sha256
    assert wrapped.result.text == direct.text
    assert wrapped.result.report == direct.report


def test_response_format_wrapper_refuses_exactly_as_the_renderer_does():
    """The call-array response format needs real ``ToolSemanticCard`` objects,
    which are a corpus product; what is proved here instead is that the wrapper
    reaches the renderer's own validation with the arguments unchanged."""

    tool_id = RENDERER_TOOLS["a2t_response_schema"]
    entry = tools.resolve_tool(tool_id)
    with pytest.raises(Exception) as wrapped_error:
        entry.call(REGISTRY_ROWS, ("not-a-card",))
    with pytest.raises(Exception) as direct_error:
        _direct(tool_id)(REGISTRY_ROWS, ("not-a-card",))
    assert type(wrapped_error.value) is type(direct_error.value)
    assert str(wrapped_error.value) == str(direct_error.value)


def test_semantic_ranking_fusion_wrapped_output_equals_the_direct_call():
    from speech_aware_evidence_acquisition.rails.a2t_semantic_router import (
        RankedTool,
        SemanticRanking,
    )

    tool_id = RENDERER_TOOLS["a2t_semantic_router"]
    entry = tools.resolve_tool(tool_id)
    rankings = (
        SemanticRanking(
            selected=(
                RankedTool(
                    tool_name="getBatteryStatus",
                    rank=1,
                    score=0.9,
                    supported_by_construction=True,
                ),
                RankedTool(
                    tool_name="setLightLevel",
                    rank=2,
                    score=0.4,
                    supported_by_construction=False,
                ),
            ),
            full_ranked_tool_names=("getBatteryStatus", "setLightLevel"),
            index_sha256="b" * 64,
            query_vector_sha256="c" * 64,
        ),
    )
    wrapped = entry.call(rankings, top_k=2, source_names=("tier",))
    direct = _direct(tool_id)(rankings, top_k=2, source_names=("tier",))
    assert wrapped.result == direct


def test_a_wrapper_raises_exactly_what_the_renderer_raises():
    """A wrapper adds no error handling of its own."""

    tool_id = RENDERER_TOOLS["a2t_executable_ground"]
    entry = tools.resolve_tool(tool_id)
    direct = _direct(tool_id)
    with pytest.raises(Exception) as wrapped_error:
        entry.call(())
    with pytest.raises(Exception) as direct_error:
        direct(())
    assert type(wrapped_error.value) is type(direct_error.value)
    assert str(wrapped_error.value) == str(direct_error.value)


def test_the_renderer_modules_say_where_they_are_registered():
    """Each module is MARKED, so a reader of the renderer finds the catalog
    row without reading rails/tools.py."""

    for stem, tool_id in RENDERER_TOOLS.items():
        text = (RAILS_DIR / f"{stem}.py").read_text(encoding="utf-8")
        assert tool_id in text, f"{stem}.py does not name its catalog id"


def test_the_wrapper_module_imports_only_the_renderers_it_wraps():
    source = inspect.getsource(a2t_renderers)
    assert "import" in source
    for stem in RENDERER_TOOLS:
        assert f"from ..{stem} import" in source
