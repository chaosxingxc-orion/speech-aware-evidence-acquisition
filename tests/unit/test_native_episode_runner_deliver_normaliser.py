"""E11 (owner directive 26, 2026-09-18): the delivery-time normaliser node
through the ACTUAL shared ``rails.runner`` episode invocation -- no network
and no model.

Complements ``test_deliver_normaliser_node.py`` (the pure rule, its registry
and its switch) with the live-wiring proof this item owes:

* the node runs INSIDE the episode, once, after the Planner ACCEPTs, and the
  delivered ``final_response_text`` is its output;
* it changes NO request byte -- every rendered MODEL_REQUEST of the ON arm is
  byte-identical to the OFF arm's, because the node runs after the last
  contact of the episode is already spent;
* the episode receipt carries the ``deliver_normaliser`` block, naming the
  rule and binding its input and output digests;
* the OFF arm is byte-identical to the pre-E11 shape, delivered text
  included.

Run through the SAME ``_ActualEpisodeHarness`` fake transport
``test_native_episode_runner.py`` and the grouped-Solver proof already use.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails import slurp_projection_v3 as v3
from speech_aware_evidence_acquisition.rails.delivery_normalisers import (
    DELIVER_NORMALISE_V3,
    DELIVER_NORMALISER_RECEIPT_SCHEMA,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    legal_intent_inventory,
    parse_slu_response,
)

# pytest module-scoped autouse fixture (spawns the fake llama-server-shaped
# process the transport dials): must be IMPORTED into this module's own
# namespace, exactly as test_native_episode_runner.py itself does, or
# _base_url() reads an empty _live dict. Not called directly here.
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness

INVENTORY = legal_intent_inventory(
    {
        "music": ("likeness", "dislikeness", "play", "query", "settings"),
        "play": ("audiobook", "game", "music", "podcasts", "radio"),
        "alarm": ("set", "remove", "query"),
    }
)

#: What the Solver answers: an ILLEGAL (music, play_music) pair with an
#: unnormalised time filler, so the node changes both halves and the
#: delivered text equals no model response's own bytes.
RAW_ANSWER = json.dumps(
    {
        "scenario": "music",
        "action": "play_music",
        "entities": [{"type": "time", "filler": "6:30AM"}],
    },
    ensure_ascii=False,
    sort_keys=True,
)


@pytest.fixture(autouse=True)
def _synthetic_inventory(monkeypatch):
    """No test here reads the data root for the legal label space."""

    monkeypatch.setattr(v3, "_default_legal_intent_inventory", lambda: INVENTORY)


def _slurp_output(key):
    """Solver visits answer a real SLURP answer; every other phase keeps
    ``_ActualEpisodeHarness``'s own scripted shape."""

    sample_id, phase, visit, _turn = key
    if phase == "solver":
        return RAW_ANSWER
    if phase == "planner":
        return "ACCEPT"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run(tmp_path, *, armed: bool):
    """One four-contact episode (Perception, Solver, Reviewer, Planner
    ACCEPT), with the delivery node armed or absent. Returns the summary and
    the rendered request bodies, in dispatch order."""

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
        arm="speech-feature-query",
    )
    if armed:
        harness.config = dataclasses.replace(
            harness.config, deliver_normaliser_id=DELIVER_NORMALISE_V3
        )
    harness._output = _slurp_output
    try:
        summary = harness.run()
    finally:
        harness.close()
    requests = [
        json.dumps(harness.prepared[key]["rendered"], sort_keys=True)
        for _event, key in harness.events
        if _event == "dispatch"
    ]
    return summary, requests


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_the_node_rewrites_only_what_is_delivered_and_no_request_byte(tmp_path):
    off_summary, off_requests = _run(tmp_path / "off", armed=False)
    on_summary, on_requests = _run(tmp_path / "on", armed=True)

    # 1. Every MODEL_REQUEST byte is identical with and without the node: it
    #    runs after the last contact of the episode is already spent.
    assert len(on_requests) == 4
    assert on_requests == off_requests

    off_result = off_summary.results[0]
    on_result = on_summary.results[0]

    # 2. The OFF arm is the pre-E11 shape, delivered text included.
    assert off_result.final_response_text == RAW_ANSWER
    assert "deliver_normaliser" not in off_result.native_episode_receipt

    # 3. The ON arm delivers the rule's output, which is neither the model's
    #    own answer nor anything the model was asked for.
    assert on_result.final_response_text != RAW_ANSWER
    scenario, action, entities, parsed = parse_slu_response(
        on_result.final_response_text
    )
    assert parsed is True
    assert (scenario, action) == ("play", "music")
    assert [entity.filler for entity in entities] == ["six thirty am"]

    # 4. The receipt is the custody the seal and the bundle re-derive from.
    block = on_result.native_episode_receipt["deliver_normaliser"]
    assert block["schema"] == DELIVER_NORMALISER_RECEIPT_SCHEMA
    assert block["normaliser_id"] == DELIVER_NORMALISE_V3
    assert block["rule_id"] == "slurp-use-projection-v3"
    assert block["applied"] is True
    assert block["changed"] is True
    assert block["labels_changed"] == 1
    assert block["label_branch"] == "r-action"
    assert block["fillers_changed"] == 1
    assert block["input_sha256"] == _sha(RAW_ANSWER)
    assert block["output_sha256"] == _sha(on_result.final_response_text)

    # 5. The node's INPUT is the accepted Solver contact's own recorded
    #    response text -- what the seal checks and I7n re-derives from.
    accepted = on_result.native_episode_receipt["accepted_solver_receipt"]
    assert accepted["final_contact"]["response_text_sha256"] == block["input_sha256"]

    # 6. Everything else about the episode is unchanged: same contact count,
    #    same role visits, same Planner routes.
    assert len(on_result.contacts) == len(off_result.contacts) == 4
    assert on_result.native_episode_receipt["role_visits"] == (
        off_result.native_episode_receipt["role_visits"]
    )
    assert on_result.native_episode_receipt["planner_routes"] == (
        off_result.native_episode_receipt["planner_routes"]
    )
    assert on_result.solver_group is None


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_an_already_normal_answer_leaves_the_delivered_bytes_untouched(
    tmp_path, monkeypatch
):
    """The node is a no-op on an answer that already satisfies the rule: the
    delivered bytes are the model's own, and the receipt says ``changed:
    false`` rather than being absent."""

    normal = json.dumps(
        {
            "scenario": "play",
            "action": "music",
            "entities": [{"type": "time", "filler": "six thirty am"}],
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    def _normal_output(key):
        _sample_id, phase, visit, _turn = key
        if phase == "solver":
            return normal
        if phase == "planner":
            return "ACCEPT"
        return f"{phase}-analysis:{_sample_id}:visit:{visit}"

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
        arm="speech-feature-query",
    )
    harness.config = dataclasses.replace(
        harness.config, deliver_normaliser_id=DELIVER_NORMALISE_V3
    )
    harness._output = _normal_output
    try:
        summary = harness.run()
    finally:
        harness.close()

    result = summary.results[0]
    assert result.final_response_text == normal
    block = result.native_episode_receipt["deliver_normaliser"]
    assert block["changed"] is False
    assert block["applied"] is True
    assert block["input_sha256"] == block["output_sha256"] == _sha(normal)
