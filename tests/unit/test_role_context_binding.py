"""Role-context config and runtime schema binding use registered shared seams."""
import json
from copy import deepcopy
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
from speech_aware_evidence_acquisition.rails.role_context_binding import (
    build_role_context_binding, validate_role_context_config,
)
from test_native_episode_config import config, program

DRAFT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["scenario", "action", "entities"],
    "properties": {
        "scenario": {"type": "string"}, "action": {"type": "string"},
        "entities": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["type", "filler"],
            "properties": {"type": {"type": "string"}, "filler": {"type": "string"}},
        }},
    },
}


def context_spec():
    return {
        "policy_id": "typed-slurp-role-context-v1",
        "params": {
            "max_candidates": 3,
            "projection_policy": "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1",
            "draft_response_schema": deepcopy(DRAFT_SCHEMA),
        },
    }


def perception_format():
    return {"type": "json_schema", "json_schema": {"schema": {
        "properties": {"candidates": {"maxItems": 3, "items": {
            "properties": {"intent_id": {"enum": ["alarm_set", "alarm_remove", "calendar_query"]}},
        }}},
    }}}


def context_program():
    base = program()
    return replace(base, phases=tuple(
        replace(phase, response_format_id="slurp-intent-hypotheses-v1")
        if phase.name == "perception" else phase for phase in base.phases
    ))


def test_default_context_is_absent_and_explicit_spec_is_immutable_json():
    assert load_native_episode_config(config(), program()).role_context_json is None
    values = config()
    values["native_episode"]["role_context"] = context_spec()
    parsed = load_native_episode_config(values, context_program())
    saved = parsed.role_context_json
    values["native_episode"]["role_context"]["params"]["max_candidates"] = 1
    assert json.loads(saved)["params"]["max_candidates"] == 3
    assert parsed.role_context_json == saved


@pytest.mark.parametrize("change", ["unknown_policy", "unknown_key", "missing_entities", "bad_width", "bool_width", "external_ref"])
def test_invalid_context_spec_is_rejected(change):
    spec = context_spec()
    if change == "unknown_policy":
        spec["policy_id"] = "unregistered"
    elif change == "unknown_key":
        spec["params"]["inferred_gold"] = "alarm_set"
    elif change == "missing_entities":
        spec["params"]["draft_response_schema"]["required"].remove("entities")
    elif change == "bad_width":
        spec["params"]["max_candidates"] = 0
    elif change == "bool_width":
        spec["params"]["max_candidates"] = True
    else:
        spec["params"]["draft_response_schema"]["properties"]["scenario"]["$ref"] = "https://example.invalid/schema"
    with pytest.raises(ValueError):
        validate_role_context_config(spec)


def test_incompatible_raw_history_filter_or_untyped_source_is_rejected():
    values = config()
    values["native_episode"]["role_context"] = context_spec()
    with pytest.raises(ValueError, match="Perception"):
        load_native_episode_config(values, program())
    values["native_episode"]["roles"]["reviewer"]["history_scope"] = "latest-solver-and-local-tools"
    with pytest.raises(ValueError, match="history"):
        load_native_episode_config(values, context_program())


def test_binding_uses_actual_candidate_schema_and_rejects_width_drift():
    spec_json = validate_role_context_config(context_spec())
    response = perception_format()
    binding = build_role_context_binding(spec_json, response)
    assert binding.draft_response_schema == DRAFT_SCHEMA
    assert len(binding.source_format_sha256) == 64
    changed = deepcopy(response)
    changed["json_schema"]["schema"]["properties"]["candidates"]["maxItems"] = 2
    with pytest.raises(ValueError, match="candidate"):
        build_role_context_binding(spec_json, changed)
    with pytest.raises(ValueError, match="Perception"):
        build_role_context_binding(spec_json, None)
