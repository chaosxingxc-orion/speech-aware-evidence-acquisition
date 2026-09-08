"""``rails/a2t_*`` renderer bodies, as SYSTEM-invoked tool-catalog wrappers.

WAVE R7 (owner Decision 12-F, 2026-09-08). The reuse map's Group A
(``docs/readiness/2026-09-08-openjiuwen-implementation-assessment-v1.md``
section 6.1) named the eighteen ``rails/a2t_*.py`` modules as **task tools and
knowledge views in the design's own section-7 sense**, and said so on the
strength of their own docstrings: "reads no manifests, audio, evaluation
fields, model output, scorer, or network service", "performs no embedding,
model, network, scorer, or file-system contact". Its verdict was **"Register,
do not rebuild."**

That is exactly what this module does, and all it does. Every wrapper below is
a passthrough: it forwards its arguments unchanged and returns the wrapped
function's own return value in ``ToolResult.result``, byte for byte. No
renderer was moved, re-signed, re-ordered or re-encoded, and
``tests/unit/test_a2t_renderer_tools.py`` asserts the identity per renderer
against a direct call.

What registration buys, given nothing changed: each renderer now has a pinned
source hash the catalog re-measures, a declared axis (OBS / ORG / SUPPLY /
USE), a declared scope (``carrier:audio2tool``), a declared cost class and
ledger row -- and a name a Planner can read. The 2026-08-08 ruling still
holds and is enforced by ``rails.tools.build_tool_entry``: this catalog is
SYSTEM-invoked, never a tool list the frozen core is offered.
"""

from __future__ import annotations

from typing import Any

from ..a2t_canonical_family_ground import CanonicalFamilyGround
from ..a2t_construction_example_ground import build_construction_example_family_ground
from ..a2t_construction_semantic_ground import build_construction_semantic_ground
from ..a2t_executable_ground import build_executable_ground
from ..a2t_executable_ground_prompt_fit import build_ground_envelopes
from ..a2t_executable_semantic_cards import build_executable_semantic_card_corpus
from ..a2t_frozen_semantic_assets import load_frozen_semantic_runtime_assets
from ..a2t_hard_validity import validate_hard_validity
from ..a2t_observation_state_organizer import organize_sealed_observation
from ..a2t_plain_english_cards import retrieve_plain_english_packets
from ..a2t_response_schema import audio2tool_call_array_response_format
from ..a2t_select_fill_factorial import bind_factorial_predecessors
from ..a2t_select_fill_ground import build_routing_knowledge_ground
from ..a2t_selected_tool_ground import SelectedToolDecisionGround
from ..a2t_semantic_microground import route_semantic_microground
from ..a2t_semantic_router import fuse_semantic_rankings
from ..a2t_stage_state import build_select_stage_envelope
from ..a2t_structured_dialogue_state import build_structured_dialogue_state


def render_family_tool(*args: Any, **kwargs: Any):
    """Render the value-safe canonical Audio2Tool ground for ONE action family.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_canonical_family_ground.CanonicalFamilyGround.render_family(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-canonical-family-ground-v1', result=CanonicalFamilyGround.render_family(*args, **kwargs))


def build_construction_example_family_ground_tool(*args: Any, **kwargs: Any):
    """Build the query-independent construction-example family ground.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_construction_example_ground.build_construction_example_family_ground(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-construction-example-ground-v1', result=build_construction_example_family_ground(*args, **kwargs))


def build_construction_semantic_ground_tool(*args: Any, **kwargs: Any):
    """Build construction-conditioned Audio2Tool semantics without source text.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_construction_semantic_ground.build_construction_semantic_ground(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-construction-semantic-ground-v1', result=build_construction_semantic_ground(*args, **kwargs))


def build_executable_ground_tool(*args: Any, **kwargs: Any):
    """Build the compact, task-wide, values-stripped executable handbook.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_executable_ground.build_executable_ground(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-executable-ground-v1', result=build_executable_ground(*args, **kwargs))


def build_ground_envelopes_tool(*args: Any, **kwargs: Any):
    """Build the exact prompt envelopes the executable ground must fit inside.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_executable_ground_prompt_fit.build_ground_envelopes(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-ground-prompt-envelopes-v1', result=build_ground_envelopes(*args, **kwargs))


def build_executable_semantic_card_corpus_tool(*args: Any, **kwargs: Any):
    """Build the deterministic, label-free executable semantic card corpus.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_executable_semantic_cards.build_executable_semantic_card_corpus(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-executable-semantic-cards-v1', result=build_executable_semantic_card_corpus(*args, **kwargs))


def load_frozen_semantic_runtime_assets_tool(*args: Any, **kwargs: Any):
    """Load the frozen, label-free semantic runtime assets at their pinned hashes.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_frozen_semantic_assets.load_frozen_semantic_runtime_assets(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-frozen-semantic-assets-v1', result=load_frozen_semantic_runtime_assets(*args, **kwargs))


def validate_hard_validity_tool(*args: Any, **kwargs: Any):
    """Check a tool-call draft for deterministic, deployment-visible invalidity.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_hard_validity.validate_hard_validity(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-hard-validity-v1', result=validate_hard_validity(*args, **kwargs))


def organize_sealed_observation_tool(*args: Any, **kwargs: Any):
    """Organize sealed ASCII OBS into task-blind structured dialogue state.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_observation_state_organizer.organize_sealed_observation(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-observation-state-organizer-v1', result=organize_sealed_observation(*args, **kwargs))


def retrieve_plain_english_packets_tool(*args: Any, **kwargs: Any):
    """Retrieve the hierarchical plain-English knowledge packets for one observation.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_plain_english_cards.retrieve_plain_english_packets(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-plain-english-retrieval-v1', result=retrieve_plain_english_packets(*args, **kwargs))


def audio2tool_call_array_response_format_tool(*args: Any, **kwargs: Any):
    """Render the strict JSON-Schema response format for a routed tool subset.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_response_schema.audio2tool_call_array_response_format(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-call-array-response-format-v1', result=audio2tool_call_array_response_format(*args, **kwargs))


def bind_factorial_predecessors_tool(*args: Any, **kwargs: Any):
    """Bind the SELECT/FILL factorial cell's predecessor selector states.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_select_fill_factorial.bind_factorial_predecessors(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-select-fill-factorial-binding-v1', result=bind_factorial_predecessors(*args, **kwargs))


def build_routing_knowledge_ground_tool(*args: Any, **kwargs: Any):
    """Build the selection-scoped routing knowledge ground.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_select_fill_ground.build_routing_knowledge_ground(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-routing-knowledge-ground-v1', result=build_routing_knowledge_ground(*args, **kwargs))


def build_tool(*args: Any, **kwargs: Any):
    """Render the compact, value-safe decision cards for the selected tools.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_selected_tool_ground.SelectedToolDecisionGround.build(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-selected-tool-ground-v1', result=SelectedToolDecisionGround.build(*args, **kwargs))


def route_semantic_microground_tool(*args: Any, **kwargs: Any):
    """Route bounded executable semantic cards without gold or learned control.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_semantic_microground.route_semantic_microground(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-semantic-microground-v1', result=route_semantic_microground(*args, **kwargs))


def fuse_semantic_rankings_tool(*args: Any, **kwargs: Any):
    """Fuse the frozen tool-tier semantic rankings by reciprocal rank.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_semantic_router.fuse_semantic_rankings(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-semantic-ranking-fusion-v1', result=fuse_semantic_rankings(*args, **kwargs))


def build_select_stage_envelope_tool(*args: Any, **kwargs: Any):
    """Build the canonical, hash-bound SELECT stage-state envelope.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_stage_state.build_select_stage_envelope(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-select-stage-envelope-v1', result=build_select_stage_envelope(*args, **kwargs))


def build_structured_dialogue_state_tool(*args: Any, **kwargs: Any):
    """Derive strict, task-blind dialogue state from sealed Audio2Tool OBS.

    Passthrough: ``ToolResult.result`` IS
    ``a2t_structured_dialogue_state.build_structured_dialogue_state(*args, **kwargs)``'s own return value.
    """

    from ..tools import ToolResult

    return ToolResult(tool_id='saea-tool-a2t-structured-dialogue-state-v1', result=build_structured_dialogue_state(*args, **kwargs))
