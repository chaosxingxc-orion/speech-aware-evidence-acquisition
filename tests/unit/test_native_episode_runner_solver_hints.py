"""E14: the Solver scenario-hints block through the PRODUCTION render path.

Every episode here runs the real OpenJiuwen role graph, the real
``rails.runner`` and the real ``LlamaServerTransport.render_request`` over the
shared fake transport, against a synthetic-but-released scenario-hints view
under a temporary data root. No model, no tokenizer, no encoder, no server, no
run directory, and -- the point of the module -- no contact of any kind added
by the block.

The request-channel falsifier: with the hints armed, every contact of every
role BUT the Solver renders bytes identical to the same policy's own, and every
Solver contact differs in exactly the appended block.

Design: ``docs/superpowers/specs/2026-09-17-node-context-policy-design.md``
sections 16 and 16.2 (cell B8c).
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.node_context_binding import (
    validate_node_context_policy_config,
    validate_solver_hints_config,
)
from speech_aware_evidence_acquisition.rails.node_context_policy import (
    SOLVER_HINTS_BOUNDARY,
    SOLVER_HINTS_TEMPLATE,
)
from speech_aware_evidence_acquisition.rails.scenario_hints import (
    SCENARIO_HINTS_RECEIPT_SCHEMA,
    SCENARIO_HINTS_VIEW_ID,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness
from test_node_context_policy_runner import (
    REPO_ROOT,
    _anchor_outputs,
    _policy_document,
    _request_digests,
)
from test_role_context_binding import perception_format
from test_slurp_scenario_hints_view import cue, neighbour, profile, write_table

#: The Solver contacts of the harness episode; every other key is a contact
#: whose bytes the block may not move.
SOLVER_KEYS = ("solver/1/1", "solver/2/1")

#: The episode's Perception output offers ``alarm_set`` and ``alarm_remove``;
#: the bound schema's legal inventory adds ``calendar_query``.
INTENTS = [
    profile("alarm_set", 100, [
        neighbour("alarm_remove", 120, 100, [
            cue("wake", 40, 3), cue("snooze", 30, 2),
        ]),
    ]),
    profile("alarm_remove", 80, [
        neighbour("alarm_set", 110, 80, [cue("cancel", 25, 0)]),
    ]),
    profile("calendar_query", 50),
]


def _solver_hints_document(root, **overrides) -> dict[str, object]:
    release_pin, snapshot_pin = write_table(root, intents=INTENTS)
    document: dict[str, object] = {
        "view": SCENARIO_HINTS_VIEW_ID,
        "release": release_pin,
        "snapshot": snapshot_pin,
    }
    document.update(overrides)
    return document


def _episode(tmp_path, *, policy, solver_hints=None, hints_root=None):
    """The same production harness E8a's runner proofs use, with the E14 key.

    Copied in shape from ``test_node_context_policy_runner._episode`` rather
    than parameterised into it, so that module's own pins stay a function of
    exactly what it declares.
    """

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    harness._output = _anchor_outputs(harness)
    harness.repo_root = REPO_ROOT
    harness.solver_hints_data_root = hints_root
    harness.config = replace(
        harness.config,
        context_policy_json=validate_node_context_policy_config(policy),
        solver_hints_json=(
            None if solver_hints is None
            else validate_solver_hints_config(solver_hints)
        ),
    )
    harness.program = replace(
        harness.program,
        phases=tuple(
            replace(phase, response_format_id="slurp-intent-hypotheses-v1")
            if phase.name == "perception" else phase
            for phase in harness.program.phases
        ),
    ).validate()
    original = harness.material_for_phase

    def material_for_phase(phase, context, sealed):
        material = original(phase, context, sealed)
        if phase == "perception":
            return replace(material, response_format=perception_format()).validate()
        return material

    harness.material_for_phase = material_for_phase
    try:
        summary = harness.run()
    finally:
        harness.close()
    return harness, summary


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_armed_block_moves_only_the_solver_contacts(tmp_path):
    view_root = tmp_path / "view"
    document = _solver_hints_document(view_root)
    off_harness, off_summary = _episode(tmp_path / "off", policy=_policy_document())
    on_harness, on_summary = _episode(
        tmp_path / "on",
        policy=_policy_document(),
        solver_hints=document,
        hints_root=view_root,
    )
    off_digests = _request_digests(off_harness)
    on_digests = _request_digests(on_harness)
    assert set(off_digests) == set(on_digests)
    moved = sorted(key for key in off_digests if off_digests[key] != on_digests[key])
    assert moved == sorted(SOLVER_KEYS)
    # The episode graph is unchanged: the same contacts, the same transitions
    # outside the Solver's own, and no added contact.
    assert len(on_summary.results[0].contacts) == len(off_summary.results[0].contacts)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_solver_request_gains_exactly_the_appended_block(tmp_path):
    view_root = tmp_path / "view"
    document = _solver_hints_document(view_root)
    off_harness, _off = _episode(tmp_path / "off", policy=_policy_document())
    on_harness, on_summary = _episode(
        tmp_path / "on",
        policy=_policy_document(),
        solver_hints=document,
        hints_root=view_root,
    )

    def wire(harness, key):
        return json.dumps(
            harness.prepared[key]["rendered"], sort_keys=True, ensure_ascii=False
        )

    key = ("s1", "solver", 1, 1)
    off_text = wire(off_harness, key)
    on_text = wire(on_harness, key)
    assert "SCENARIO HINTS" not in off_text
    assert f"SCENARIO HINTS ({SCENARIO_HINTS_VIEW_ID};" in on_text
    assert len(on_text) > len(off_text)
    # Exactly once per Solver contact, never twice and never elsewhere.
    assert on_text.count("SCENARIO HINTS") == 1
    for reviewer_key in (("s1", "reviewer", 1, 2), ("s1", "planner", 1, 1)):
        assert "SCENARIO HINTS" not in wire(on_harness, reviewer_key)

    receipt = on_summary.results[0].native_episode_receipt
    rows = [
        row
        for record in receipt["node_context_policy_compilations"]
        for row in record["compilation"]["boundaries"]
        if (
            row["boundary"]["consumer_role_kind"] == SOLVER_HINTS_BOUNDARY[0]
            and row["boundary"]["semantic_class"] == SOLVER_HINTS_BOUNDARY[1]
        )
    ]
    assert rows
    for row in rows:
        hints = row["solver_hints"]
        assert hints["schema"] == SCENARIO_HINTS_RECEIPT_SCHEMA
        assert hints["applied"] is True
        assert hints["view_id"] == SCENARIO_HINTS_VIEW_ID
        assert hints["template_id"] == SOLVER_HINTS_TEMPLATE
        assert hints["candidate_ids"] == ["alarm_set", "alarm_remove"]
        assert hints["counts"]["candidates"] == 2
        assert hints["block_chars"] > 0
    # Every OTHER boundary row is untouched by the hints.
    other = [
        row
        for record in receipt["node_context_policy_compilations"]
        for row in record["compilation"]["boundaries"]
        if "solver_hints" not in row
    ]
    assert other


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_block_pins_its_three_assets_in_every_compilation_record(tmp_path):
    view_root = tmp_path / "view"
    document = _solver_hints_document(view_root)
    _harness, summary = _episode(
        tmp_path,
        policy=_policy_document(),
        solver_hints=document,
        hints_root=view_root,
    )
    spelling = f"{SOLVER_HINTS_BOUNDARY[0]}:{SOLVER_HINTS_BOUNDARY[1]}"
    for record in summary.results[0].native_episode_receipt[
        "node_context_policy_compilations"
    ]:
        pins = record["template_sha256s"]
        assert pins[f"{spelling}:scenario-hints-release"] == (
            document["release"]["sha256"]
        )
        assert pins[f"{spelling}:scenario-hints-snapshot"] == (
            document["snapshot"]["sha256"]
        )
        assert f"{spelling}:scenario-hints" in pins


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_off_arm_is_the_keys_absence_down_to_the_byte(tmp_path):
    """``solver_hints_json`` None renders exactly what the pre-E14 tree
    rendered for the same policy -- the same bytes, the same receipt fields."""

    first_harness, first_summary = _episode(tmp_path / "a", policy=_policy_document())
    second_harness, _second = _episode(tmp_path / "b", policy=_policy_document())
    assert _request_digests(first_harness) == _request_digests(second_harness)
    for record in first_summary.results[0].native_episode_receipt[
        "node_context_policy_compilations"
    ]:
        assert all(
            "solver_hints" not in row for row in record["compilation"]["boundaries"]
        )
        assert not any("scenario-hints" in key for key in record["template_sha256s"])
