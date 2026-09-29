"""LIVE (fake-transport, real graph) proof that a Perception branch's own
``top2-contrast-v1`` presentation and ``min_candidates`` response-contract
sentence actually reach the wire (design docs/superpowers/specs/2026-09-28-
same-flight-instrument-phase2-perception-variants-design.md section 3,
"What to build" items 2 and 3), while A's and T's own requests stay
byte-identical (AT-P1/AT-P2, restated for this defect fix).

Structurally ``tests/unit/test_perception_branch_live.py``'s own twin, with a
custom knowledge snapshot carrying intent-boundary-shaped value ids (the
shared ``_knowledge_snapshot()`` fixture's one plain ``value:dim-light`` id
has no intent to derive) and a K = 4 branch group (two B branches: one per
axis this defect fix wires).

Zero model, real server, GPU or network contact.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.rails import KeyFacet, KnowledgeSnapshot, ValueBundle
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeConfig,
    NativeEpisodeRole,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_perception_branch_receipt,
)
from speech_aware_evidence_acquisition.rails.perception_presentations import (
    TOP2_CONTRAST_PRESENTATION_ID,
)
from speech_aware_evidence_acquisition.rails.supply_variants import parse_perception_branches
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import ACTIONS, PHASES, _ActualEpisodeHarness

FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 640,
    "base_prompt_tokens": 9600,
    "tokens_per_supplied_item": 120,
}
STORE = "train-exemplars"
INTENT_X = "general_quirky"
INTENT_Y = "play_music"
VALUE_X = f"{STORE}::intent-boundary:{INTENT_X}"
VALUE_Y = f"{STORE}::intent-boundary:{INTENT_Y}"
CONTRAST_TABLE = {
    frozenset({INTENT_X, INTENT_Y}): {
        "activation_sentence": "Pick general_quirky when the utterance names an odd request.",
        "exclusion_sentence": "Pick play_music when it names a song or artist.",
    },
}


def _intent_snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="fake-intent-boundary-contrast-v1",
        source_split_identity_hash="b" * 64,
        source_sample_ids=("train:t1",),
        builder_policy_id="coverage-builder-v1",
        facets=(
            KeyFacet(
                facet_id="operation:dim", dimension="operation",
                representation_kind="text",
                representation="Decrease the brightness of a light.",
                source_sample_ids=("train:t1",),
            ),
        ),
        values=(
            ValueBundle(
                value_id=VALUE_X, content="general_quirky boundary text.",
                associated_facet_ids=("operation:dim",), source_sample_ids=("train:t1",),
                provenance_refs=("train:t1",), task_target=INTENT_X,
            ),
            ValueBundle(
                value_id=VALUE_Y, content="play_music boundary text.",
                associated_facet_ids=("operation:dim",), source_sample_ids=("train:t1",),
                provenance_refs=("train:t1",), task_target=INTENT_Y,
            ),
        ),
    ).validate()


def _group():
    return parse_perception_branches(
        {
            "level": 1,
            "fit_estimate": dict(FIT),
            "branches": [
                {
                    "branch_id": "b-top2contrast", "max_supplied_items": 4,
                    "presentation_id": TOP2_CONTRAST_PRESENTATION_ID,
                    "contrast_pairs": {
                        "relpath": "prepared/SAEA-TEST-PERCEPTION-CONTRAST-PAIRS-V1/table.json",
                        "sha256": "a" * 64,
                    },
                },
                {"branch_id": "b-mincand", "max_supplied_items": 4, "min_candidates": 2},
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 4},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 4},
            ],
        },
        first_phase_id="perception", declared_stores=(STORE,),
        registered_presentation_ids=(TOP2_CONTRAST_PRESENTATION_ID, "rank-visible-v1"),
        max_candidates_ceiling=3,
        top2_contrast_presentation_id=TOP2_CONTRAST_PRESENTATION_ID,
    )


def _perception_live_config(*, group, max_contacts):
    return NativeEpisodeConfig(
        episode_id="native-role-runner-perception-branch-presentation-proof-v1",
        max_revisions=0,
        actions=ACTIONS,
        roles=tuple(
            NativeEpisodeRole(
                phase_id=phase,
                role_kind=phase,
                max_iterations=0 if phase in {"reviewer", "planner"} else 1,
                tool_names=(),
                perception_branches=(group if phase == "perception" else None),
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
    )


def _branch_output(key):
    sample_id, phase, _visit, turn = key
    if phase == "perception":
        return f"perception-branch-turn-{turn}:{sample_id}"
    return f"{phase}-analysis:{sample_id}:visit:{turn}"


def _supplied_evidence(request):
    items = request.get("supplied_evidence")
    return items if isinstance(items, list) else []


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_contrast_branch_renders_exactly_one_extra_item_and_a_t_are_unchanged(tmp_path):
    group = _group()
    # Perception (4 branches) + Solver 1 visit = 5.
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=5, planner_actions=(),
    )
    harness.config = _perception_live_config(group=group, max_contacts=5)
    sample_id = harness.samples[0].sample_id
    harness.perception_branch_seeds = {
        "b-top2contrast": {sample_id: (VALUE_X, VALUE_Y)},
        "b-mincand": {sample_id: (VALUE_X,)},
    }
    harness.perception_contrast_pairs = {"b-top2contrast": CONTRAST_TABLE}
    harness._output = _branch_output
    try:
        summary = harness.run(snapshot=_intent_snapshot())
    finally:
        harness.close()

    result = summary.results[0]
    assert len(result.contacts) == 5

    receipt = result.native_episode_receipt["perception_branches"]
    validate_perception_branch_receipt(
        receipt, branch_ids=group.branch_ids,
        delivered_branch_id=group.delivering_branch.branch_id,
        twin_branch_id=group.twin_branch.branch_id, phase_id="perception",
        level=group.level,
    )
    rows = {row["branch_id"]: row for row in receipt["branches"]}
    assert rows["b-top2contrast"]["contrast_block_sha256"] is not None
    assert rows["b-top2contrast"]["presentation_skip_reason"] is None
    assert rows["b-mincand"]["min_candidates_met"] is False  # note text has no candidates list
    assert rows["A"]["contrast_block_sha256"] is None
    assert rows["A"]["min_candidates_met"] is None
    assert rows["T"]["contrast_block_sha256"] is None
    assert rows["T"]["min_candidates_met"] is None

    requests = [
        payload["payload"]
        for channel, _record_id, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    # Branch order: b-top2contrast, b-mincand, T, A, then the Solver.
    assert len(requests) == 5
    contrast_request, mincand_request, t_request, a_request, _solver_request = requests

    contrast_evidence = _supplied_evidence(contrast_request)
    contrast_items = [
        item for item in contrast_evidence
        if item.get("evidence_id") == "perception-branch-presentation:b-top2contrast"
    ]
    assert len(contrast_items) == 1
    assert contrast_items[0]["knowledge_role"] == "value"
    assert contrast_items[0]["content"] == (
        "Pick general_quirky when the utterance names an odd request.\n"
        "Pick play_music when it names a song or artist."
    )
    # Exactly the two real values plus the one presentation block -- no other
    # extra item snuck in.
    assert len(contrast_evidence) == 3

    mincand_evidence = _supplied_evidence(mincand_request)
    contract_items = [
        item for item in mincand_evidence
        if item.get("evidence_id") == "perception-branch-contract:b-mincand"
    ]
    assert len(contract_items) == 1
    assert "at least 2" in contract_items[0]["content"]
    assert "at most 3" in contract_items[0]["content"]

    # AT-P1/AT-P2: A is override-free and T repeats it byte for byte on every
    # field the phase-1 AT2 proof already compares (excluding the one turn
    # naming each contact's own transport identity).
    for field in (
        "decoding_params", "task_instruction", "tool_schemas",
        "speech_feature_parts", "speech_packet_sha256", "query_source",
        "key_representation_id", "matcher_policy_id", "carrier_lock_key",
        "media_relpath", "audio_seconds", "sample_rate_hz", "sample_id",
        "supplied_evidence", "evidence_provenance",
    ):
        assert t_request[field] == a_request[field], field
    # Neither A nor T ever carries either branch's own presentation/contract
    # block.
    a_evidence_ids = {item.get("evidence_id") for item in _supplied_evidence(a_request)}
    assert "perception-branch-presentation:b-top2contrast" not in a_evidence_ids
    assert "perception-branch-contract:b-mincand" not in a_evidence_ids


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_contrast_branch_skips_when_the_table_has_no_row_for_the_pair(tmp_path):
    group = _group()
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=5, planner_actions=(),
    )
    harness.config = _perception_live_config(group=group, max_contacts=5)
    sample_id = harness.samples[0].sample_id
    harness.perception_branch_seeds = {
        "b-top2contrast": {sample_id: (VALUE_X, VALUE_Y)},
        "b-mincand": {sample_id: (VALUE_X,)},
    }
    # No table entry for this pair -- must render nothing (O5, no fallback).
    harness.perception_contrast_pairs = {"b-top2contrast": {}}
    harness._output = _branch_output
    try:
        summary = harness.run(snapshot=_intent_snapshot())
    finally:
        harness.close()

    result = summary.results[0]
    receipt = result.native_episode_receipt["perception_branches"]
    rows = {row["branch_id"]: row for row in receipt["branches"]}
    assert rows["b-top2contrast"]["contrast_block_sha256"] is None
    assert rows["b-top2contrast"]["presentation_skip_reason"] == "insufficient-pool-support"

    requests = [
        payload["payload"]
        for channel, _record_id, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    contrast_evidence = _supplied_evidence(requests[0])
    assert not any(
        item.get("evidence_id") == "perception-branch-presentation:b-top2contrast"
        for item in contrast_evidence
    )
