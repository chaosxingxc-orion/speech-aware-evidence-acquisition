"""LIVE (fake-transport, real graph) proof of the E4 v1 post-accept targeted
re-listen wiring (owner decision 185; ``rails.relisten`` + ``rails.runner``).

Structurally ``tests/unit/test_perception_branch_live.py``'s own twin: the
SAME ``_ActualEpisodeHarness`` fake llama-server-shaped transport, driving
the REAL ``rails.runner._invoke_native_role_episode`` graph end to end. A
relisten contact is dispatched OUTSIDE the ACCEPT/REVISE/ACQUIRE workflow
graph (design section 6's implementation table names only ``rails/
runner.py`` for this stage), so it carries no ``PhaseProgram`` phase and no
``material_for_phase`` marker; this file's own ``_arm_relisten_request_gate``
teaches the harness's fake transport to recognise a relisten contact by its
own pinned response-format name instead, and answers it through the SAME
``_output``-keyed convention every other live test in this study uses.

Zero model, real server, GPU or network contact: ``_ActualEpisodeHarness``
dials a local fake HTTP process whose every response is composed by this
test's own callback. No utterance text, transcript, gold label or model
output is printed or persisted.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import relisten as rl
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness, _review_off_config

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The SLURP answer the fake Solver delivers on every row of this file: two
#: entities, in delivery order, so the stage's own targeting ("up to
#: max_slots_per_row, in delivery order") has two real slots to visit.
_DELIVERED_ANSWER = json.dumps({
    "scenario": "alarm", "action": "set",
    "entities": [
        {"type": "time", "filler": "7 pm"},
        {"type": "place_name", "filler": "paris"},
    ],
})

_BLIND_SCHEMA_NAME = "slurp_relisten_value_v1"
_CONFIRM_SCHEMA_NAME = "slurp_relisten_confirm_v1"


def _relisten_config(max_slots_per_row: int) -> rl.RelistenConfig:
    return rl.RelistenConfig(
        policy_id=rl.RELISTEN_POLICY_ID, max_slots_per_row=max_slots_per_row,
        value_max_words=rl.MAX_VALUE_WORDS, delivery=rl.DELIVERY_MODE,
        blind_template_id=rl.BLIND_TEMPLATE_ID, confirm_template_id=rl.CONFIRM_TEMPLATE_ID,
    )


def _armed_config(*, max_slots_per_row: int):
    base_contacts = 2  # one Perception visit, one Solver visit (review-off).
    ceiling = base_contacts + rl.relisten_extra_ceiling(max_slots_per_row)
    base = _review_off_config(max_contacts=ceiling)
    return replace(
        base, relisten_json=_relisten_config(max_slots_per_row).as_json(),
    )


def _schema_name(payload: dict) -> str | None:
    response_format = (payload.get("decoding_params") or {}).get("response_format") or {}
    return (response_format.get("json_schema") or {}).get("name")


def _arm_relisten_request_gate(harness) -> None:
    """Teach the harness's fake transport to key a relisten contact by its
    own pinned response-format name (``slurp_relisten_{value,confirm}_v1``)
    rather than by a ``material_for_phase`` marker, which a relisten contact
    never carries (it is composed beside ``rails.runner.run_cleaning_
    contact``, never through ``role_input``). Every non-relisten contact
    keeps the harness's own, unmodified ``request_gate``.
    """

    original_request_gate = harness.request_gate
    kind_by_schema = {
        _BLIND_SCHEMA_NAME: "relisten-blind",
        _CONFIRM_SCHEMA_NAME: "relisten-confirm",
    }
    # This file only ever drives a single-sample harness (``sample_count=1``
    # everywhere), so the row's own sample id is read once here rather than
    # extracted from the rendered payload (whose top-level sample-identifying
    # key is query-source-specific -- ``speech_feature_sample_id`` for this
    # harness's own ``speech_features`` source -- not a plain ``sample_id``).
    assert len(harness.samples) == 1
    sample_id = harness.samples[0].sample_id

    def request_gate(prepared_request):
        payload = prepared_request.as_payload()
        kind = kind_by_schema.get(_schema_name(payload))
        if kind is None:
            return original_request_gate(prepared_request)
        rendered = harness.transport.render_request(prepared_request.payload_bytes)
        with harness.lock:
            visit = 1 + sum(
                1 for key in harness.prepared if key[0] == sample_id and key[1] == kind
            )
            key = (sample_id, kind, visit, visit)
            assert key not in harness.prepared
            harness.prepared[key] = {
                "rendered": rendered,
                "slot_id": payload["decoding_params"]["id_slot"],
            }
            harness.events.append(("fit", key))

    harness.request_gate = request_gate


def _two_entity_output(sample_id: str):
    """Entity 0 (time): the blind contact hears a genuinely different value,
    and the confirm contact is steered to CHOOSE it (an accepted replacement).
    Entity 1 (place_name): the blind contact hears nothing, and the confirm
    contact also votes "not heard" (ruling 2b's drop vote)."""

    time_order = rl.confirm_order(sample_id, "time")
    time_candidate_letter = "A" if time_order[0] == rl.CONFIRM_CANDIDATE else "B"

    def output(key):
        _sample_id, phase, visit, _turn = key
        if phase == "solver":
            return _DELIVERED_ANSWER
        if phase == "relisten-blind":
            if visit == 1:
                return json.dumps({"heard": True, "value": "eight pm"})
            return json.dumps({"heard": False, "value": ""})
        if phase == "relisten-confirm":
            if visit == 1:
                return json.dumps({"choice": time_candidate_letter})
            return json.dumps({"choice": "neither"})
        return f"{phase}-analysis:{_sample_id}:visit:{visit}"

    return output


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_config_without_relisten_is_byte_identical_to_the_pre_e4_graph(tmp_path):
    """Item 1's own proof: an unarmed config's composed graph/node list and
    contact count are exactly what they were before this branch's code --
    two contacts (Perception, Solver), no ``relisten`` key on the result,
    and no relisten-shaped response format ever rendered."""

    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=2, planner_actions=(),
    )
    harness.config = _review_off_config(max_contacts=2)
    sample_id = harness.samples[0].sample_id

    def output(key):
        _sample_id, phase, visit, _turn = key
        return _DELIVERED_ANSWER if phase == "solver" else f"{phase}-analysis:{sample_id}:visit:{visit}"

    harness._output = output
    try:
        summary = harness.run()
    finally:
        harness.close()

    result = summary.results[0]
    assert len(result.contacts) == 2
    assert result.relisten is None
    assert "relisten" not in result.as_json()
    requests = [
        payload["payload"] for channel, _record_id, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    assert len(requests) == 2
    assert all(_schema_name(request) not in (_BLIND_SCHEMA_NAME, _CONFIRM_SCHEMA_NAME)
               for request in requests)
    assert result.final_response_text == _DELIVERED_ANSWER


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_two_entities_blind_then_confirm_ordering_and_shadow_delivery(tmp_path):
    """The full mechanism on a real graph: two delivered entities, in
    delivery order, each a blind contact then (both here) a forced-choice
    confirm; the delivered answer is never mutated; the receipt is sealed
    with contact ids, hashes and flags only; and the row's own contact
    ceiling is spent exactly as the design's arithmetic predicts."""

    max_slots_per_row = 2
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0,
        max_contacts=2 + rl.relisten_extra_ceiling(max_slots_per_row), planner_actions=(),
    )
    harness.config = _armed_config(max_slots_per_row=max_slots_per_row)
    harness.repo_root = REPO_ROOT
    sample_id = harness.samples[0].sample_id
    harness._output = _two_entity_output(sample_id)
    _arm_relisten_request_gate(harness)
    try:
        summary = harness.run()
    finally:
        harness.close()

    result = summary.results[0]

    # Shadow delivery: the delivered answer is byte-identical to the
    # Solver's own raw output -- relisten never mutates it in flight.
    assert result.final_response_text == _DELIVERED_ANSWER

    # Budget counted: exactly base (Perception + Solver) plus the row's own
    # relisten spend (2 blind + 2 confirm here), which is exactly the
    # declared ceiling -- no slack, no overflow.
    requests = [
        payload["payload"] for channel, _record_id, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    assert len(requests) == 6

    # Receipts sealed: one saea-relisten-v1 receipt, two entities, in
    # delivery order, each with a blind AND a fired confirm.
    receipt = result.relisten
    assert receipt is not None
    assert receipt["schema"] == rl.RELISTEN_RECEIPT_SCHEMA
    assert receipt["triggered_count"] == 2
    assert receipt["contacts_used"] == 4
    entities = receipt["entities"]
    assert [entity["index"] for entity in entities] == [0, 1]
    assert entities[0]["slot_type"] == "time"
    assert entities[1]["slot_type"] == "place_name"
    # Entity 0: a genuine disagreement, confirm steered to accept it.
    assert entities[0]["accept"] is True
    assert entities[0]["confirm"] is not None
    # Entity 1: unheard on both contacts -- never accepted, and its shadow
    # drop vote is recorded (v1 never deletes the DELIVERED entity, only a
    # shadow column does).
    assert entities[1]["accept"] is False
    assert entities[1]["confirm_unheard_vote"] is True
    # Never the value's own bytes -- only hashes and flags.
    assert "eight pm" not in json.dumps(receipt)

    # Blind then confirm ordering, per entity, in delivery order: the trace
    # records the four relisten contacts in exactly this sequence.
    relisten_requests = [
        request for request in requests
        if _schema_name(request) in (_BLIND_SCHEMA_NAME, _CONFIRM_SCHEMA_NAME)
    ]
    assert len(relisten_requests) == 4
    assert [_schema_name(request) for request in relisten_requests] == [
        _BLIND_SCHEMA_NAME, _CONFIRM_SCHEMA_NAME, _BLIND_SCHEMA_NAME, _CONFIRM_SCHEMA_NAME,
    ]

    # No current value in the blind prompt bytes: neither delivered filler
    # ever appears in either blind contact's own rendered request.
    blind_requests = [
        request for request in requests if _schema_name(request) == _BLIND_SCHEMA_NAME
    ]
    assert len(blind_requests) == 2
    for request in blind_requests:
        rendered_text = json.dumps(request)
        assert "7 pm" not in rendered_text
        assert "paris" not in rendered_text

    # The contact ids the receipt names are real, traced contacts: the same
    # I7l custody check the bundle-verification gate applies offline.
    from speech_aware_evidence_acquisition.core.bundle.outputs import (
        _verify_relisten_trace_binding,
    )

    trace_records = {
        record_id: payload
        for channel, record_id, payload in harness.trace.records
        if channel in ("MODEL_REQUEST", "MODEL_RESPONSE")
    }
    row = {"sample_id": sample_id, "relisten": receipt}
    _verify_relisten_trace_binding(row, trace_records)
