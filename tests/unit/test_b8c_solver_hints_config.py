"""E14: ``native_episode.solver_hints`` as one loaded episode-class key.

Cell B8c is NOT registered by this item: no readiness package, no exposure row,
no committed arm, no owner decision. What is proved here is that the KEY exists,
that it parses through the real ``load_native_episode_config``, that its OFF arm
is the key's own absence down to the composed configuration, and that every
unusable arm is refused BY NAME before any contact could be made.

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
sections 16 and 16.2 (cell B8c).
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.config_tables import (
    EPISODE_LEVEL_SWITCH_KEYS,
    is_episode_null_arm,
    resolve_episode_switch_key,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeRunBinding,
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.node_context_binding import (
    build_node_context_policy_binding,
    validate_solver_hints_config,
)
from speech_aware_evidence_acquisition.rails.node_context_policy import (
    SOLVER_HINTS_BOUNDARY,
)
from speech_aware_evidence_acquisition.rails.scenario_hints import (
    SCENARIO_HINTS_VIEW_ID,
)

from test_native_episode_config import config, program
from test_node_context_policy import DRAFT_SCHEMA, REPO_ROOT
from test_role_context_binding import context_program, perception_format
from test_slurp_scenario_hints_view import cue, neighbour, profile, write_table

SWITCH_KEY = "native_episode.solver_hints"
SPELLING = f"{SOLVER_HINTS_BOUNDARY[0]}:{SOLVER_HINTS_BOUNDARY[1]}"

LEGAL_INTENTS = ("alarm_set", "alarm_remove", "calendar_query")
INTENTS = [
    profile("alarm_set", 100, [
        neighbour("alarm_remove", 120, 100, [cue("wake", 40, 3)]),
    ]),
    profile("alarm_remove", 80),
    profile("calendar_query", 50),
]

PARAMS = {
    "max_candidates": 3,
    "projection_policy": (
        "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
    ),
    "draft_response_schema": json.loads(json.dumps(DRAFT_SCHEMA)),
    "legal_entity_types": ["time", "date", "event_name"],
}


def _policy_document(boundaries=None) -> dict[str, object]:
    document: dict[str, object] = {
        "level": "structured",
        "policy_id": "typed-slurp-node-context-v1",
        "params": json.loads(json.dumps(PARAMS)),
    }
    if boundaries is not None:
        document["boundaries"] = boundaries
    return document


def _armed(root: Path, **overrides) -> dict[str, object]:
    release_pin, snapshot_pin = write_table(root, intents=INTENTS)
    document: dict[str, object] = {
        "view": SCENARIO_HINTS_VIEW_ID,
        "release": release_pin,
        "snapshot": snapshot_pin,
    }
    document.update(overrides)
    return document


def _values(*, solver_hints=None, carrier="slurp", boundaries=None):
    """The registered four-role episode fixture, plus the declared policy."""

    values = config()
    values["carrier_lock_key"] = carrier
    values["native_episode"]["context_policy"] = _policy_document(boundaries)
    if solver_hints is not None:
        values["native_episode"]["solver_hints"] = solver_hints
    return values


def _load(values):
    # ``context_program`` is the registered fixture whose Perception phase
    # declares the hypothesis response format a declared context policy
    # binds against; ``program`` is imported so the fixture pair stays one.
    assert program().program_id == context_program().program_id
    return load_native_episode_config(values, context_program())


# ---------------------------------------------------------------------------
# 1. The key
# ---------------------------------------------------------------------------


def test_solver_hints_is_one_episode_class_key(tmp_path):
    assert SWITCH_KEY in EPISODE_LEVEL_SWITCH_KEYS
    assert resolve_episode_switch_key(SWITCH_KEY) == SWITCH_KEY
    # OFF: the key absent. There is no third shape.
    assert is_episode_null_arm(SWITCH_KEY, None) is True
    assert is_episode_null_arm(SWITCH_KEY, _armed(tmp_path)) is False
    assert is_episode_null_arm(
        SWITCH_KEY, _armed(tmp_path, max_cues=0)
    ) is False


def test_the_off_arm_is_the_keys_absence_in_the_loaded_config(tmp_path):
    off = _load(_values())
    on = _load(_values(solver_hints=_armed(tmp_path)))
    assert off.solver_hints_json is None
    assert on.solver_hints_json is not None
    # Every other loaded field is identical: the key is ONE factor.
    assert replace(on, solver_hints_json=None) == off


def test_the_loaded_text_is_the_canonical_bound_representation(tmp_path):
    document = _armed(tmp_path)
    parsed = _load(_values(solver_hints=document))
    assert parsed.solver_hints_json == validate_solver_hints_config(document)
    assert json.loads(parsed.solver_hints_json) == document


# ---------------------------------------------------------------------------
# 2. The refusals, all before contact
# ---------------------------------------------------------------------------


def test_another_carrier_is_refused_by_name(tmp_path):
    with pytest.raises(ValueError, match="defined for carrier 'slurp'"):
        _load(_values(solver_hints=_armed(tmp_path), carrier="audio2tool"))


def test_a_boundary_that_is_not_at_l1_is_refused_by_name(tmp_path):
    with pytest.raises(ValueError, match="at level 'structured'"):
        _load(
            _values(
                solver_hints=_armed(tmp_path),
                boundaries={SPELLING: {"level": "raw"}},
            )
        )


def test_an_unknown_field_of_the_episode_block_is_still_refused(tmp_path):
    values = _values(solver_hints=_armed(tmp_path))
    values["native_episode"]["solver_hint"] = {}
    with pytest.raises(ValueError):
        _load(values)


def test_the_binding_refuses_an_armed_block_with_no_data_root(tmp_path):
    parsed = _load(_values(solver_hints=_armed(tmp_path)))
    with pytest.raises(ValueError, match="requires the controlled data root"):
        build_node_context_policy_binding(
            parsed.context_policy_json,
            perception_format(),
            REPO_ROOT,
            None,
            parsed.solver_hints_json,
            None,
        )


def test_the_binding_pins_the_three_assets_the_block_is_composed_from(tmp_path):
    parsed = _load(_values(solver_hints=_armed(tmp_path)))
    binding = build_node_context_policy_binding(
        parsed.context_policy_json,
        perception_format(),
        REPO_ROOT,
        None,
        parsed.solver_hints_json,
        tmp_path,
    )
    pins = binding.template_sha256s
    assert f"{SPELLING}:scenario-hints" in pins
    assert f"{SPELLING}:scenario-hints-release" in pins
    assert f"{SPELLING}:scenario-hints-snapshot" in pins
    assert pins[f"{SPELLING}:scenario-hints-snapshot"] == json.loads(
        parsed.solver_hints_json
    )["snapshot"]["sha256"]
    # The boundary's own L1 template pin is still there and unchanged.
    assert SPELLING in pins


def test_the_run_binding_carries_the_data_root_and_defaults_to_none():
    binding = NativeEpisodeRunBinding(
        config=None, program=None, material_for_phase=lambda *a: None,
        render_request=lambda *a: None, request_gate=lambda *a: None,
    )
    assert binding.repo_root is None
    assert binding.data_root is None
    assert replace(binding, data_root=Path(".")).data_root == Path(".")
