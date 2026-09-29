"""Post-seal checks for Perception branches (same-flight instrument phase 2, merge set C, item 3:
I7v, Perception path). Structurally ``tests/unit/test_bundle_supply_variants.py``'s own twin.
"""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _verify_outputs, _verify_outputs_trace_binding,
)

SAMPLE = "slurp:train:synthetic"
ARM = "speech-feature-query-native-tools"
BRANCH_IDS = ("B", "T", "A")


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def fixture():
    trace = {}
    contacts = []
    for index, branch_id in enumerate(BRANCH_IDS):
        rid = f"request-perception-{index}"
        answer = f"note-{branch_id}"
        contact = {
            "agent_contact_id": f"perception:{index}",
            "request_id": rid,
            "request_sha256": sha(rid),
            "response_sha256": sha("envelope-" + rid),
            "response_text_sha256": sha(answer),
        }
        contacts.append(contact)
        trace[rid + "/request"] = {
            "arm": ARM, "payload": {"sample_id": SAMPLE},
            "payload_sha256": contact["request_sha256"],
        }
        trace[rid + "/response"] = {
            "text": answer,
            "response_sha256": contact["response_sha256"],
            "response_text_sha256": contact["response_text_sha256"],
        }
    visits = [{
        "role_id": "perception", "stage": "perception",
        "execution_receipt": {"contacts": contacts, "final_contact": contacts[-1]},
    }]
    a_contact = contacts[-1]
    a_note_sha256 = a_contact["response_text_sha256"]
    branches = {
        "schema": "saea-perception-branch-arms-v1", "phase_id": "perception",
        "level": 1, "branch_count": 3, "delivered_branch_id": "A",
        "branch_visits": "first", "visit_index": 0,
        "fit_estimate": {
            "slot_tokens": 24576, "completion_ceiling": 512,
            "base_prompt_tokens": 100, "tokens_per_supplied_item": 10,
            "reserve_tokens": 3072, "prompt_limit_tokens": 20990,
        },
        "branches": [
            {
                "branch_index": 0, "branch_id": "B", "deliver": False,
                "replicate_of": None,
                "resolved_knobs": [
                    {"path": "knowledge_stores.ex.phase_supply.perception.k", "value": 30}
                ],
                "release_swap": None, "presentation_id": None, "min_candidates": None,
                "supplied_value_ids": ["v:wide"], "supplied_count": 1,
                "max_supplied_items": 5, "contact_id": contacts[0]["agent_contact_id"],
                "request_sha256": contacts[0]["request_sha256"],
                "response_text_sha256": contacts[0]["response_text_sha256"],
                "note_sha256": contacts[0]["response_text_sha256"],
                "note_parse_status": "malformed", "candidate_intent_ids": ["unparsed"],
                "presentation_skip_reason": None, "contrast_block_sha256": None,
                "min_candidates_met": None,
            },
            {
                "branch_index": 1, "branch_id": "T", "deliver": False,
                "replicate_of": "A", "resolved_knobs": [], "release_swap": None,
                "presentation_id": None, "min_candidates": None,
                "supplied_value_ids": [], "supplied_count": 0, "max_supplied_items": 5,
                "contact_id": contacts[1]["agent_contact_id"],
                "request_sha256": contacts[1]["request_sha256"],
                "response_text_sha256": contacts[1]["response_text_sha256"],
                "note_sha256": contacts[1]["response_text_sha256"],
                "note_parse_status": "malformed", "candidate_intent_ids": ["unparsed"],
                "presentation_skip_reason": None, "contrast_block_sha256": None,
                "min_candidates_met": None,
            },
            {
                "branch_index": 2, "branch_id": "A", "deliver": True,
                "replicate_of": None, "resolved_knobs": [], "release_swap": None,
                "presentation_id": None, "min_candidates": None,
                "supplied_value_ids": [], "supplied_count": 0, "max_supplied_items": 5,
                "contact_id": a_contact["agent_contact_id"],
                "request_sha256": a_contact["request_sha256"],
                "response_text_sha256": a_contact["response_text_sha256"],
                "note_sha256": a_note_sha256,
                "note_parse_status": "malformed", "candidate_intent_ids": ["unparsed"],
                "presentation_skip_reason": None, "contrast_block_sha256": None,
                "min_candidates_met": None,
            },
        ],
    }
    row = {
        "request_id": a_contact["request_id"], "sample_id": SAMPLE,
        "carrier_lock_key": "slurp", "arm": ARM,
        "text": trace[a_contact["request_id"] + "/response"]["text"],
        "admitted": True, "request_sha256": a_contact["request_sha256"],
        "response_sha256": a_contact["response_sha256"],
        "response_text_sha256": a_contact["response_text_sha256"],
        "native_episode_receipt": {
            "role_visits": visits, "perception_branches": branches,
        },
    }
    return row, trace


def check(row, trace):
    rows = _verify_outputs(
        (json.dumps(row) + "\n").encode(), frozenset({SAMPLE}), "slurp", ARM,
    )
    _verify_outputs_trace_binding(rows, trace)


def test_a_sealed_branch_group_is_trace_bound():
    row, trace = fixture()
    check(row, trace)


def test_missing_non_a_branch_response_is_refused():
    row, trace = fixture()
    del trace["request-perception-0/response"]
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_tampered_non_a_branch_response_is_refused():
    row, trace = fixture()
    trace["request-perception-1/response"]["text"] = "tampered"
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_declared_branch_contact_order_must_match_the_visit():
    row, trace = fixture()
    row["native_episode_receipt"]["perception_branches"]["branches"][0]["contact_id"] = "wrong"
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_a_note_sha256_must_equal_its_own_response_text_sha256():
    row, trace = fixture()
    row["native_episode_receipt"]["perception_branches"]["branches"][2]["note_sha256"] = "f" * 64
    with pytest.raises(BundleError, match="note_sha256"):
        check(row, trace)


def test_a_request_cannot_belong_to_another_row():
    row, trace = fixture()
    trace["request-perception-0/request"]["payload"]["sample_id"] = "other-row"
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_missing_twin_is_refused():
    row, trace = fixture()
    row["native_episode_receipt"]["perception_branches"]["branches"][1]["replicate_of"] = None
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_perception_branches_receipt_validation_failure_is_wrapped():
    row, trace = fixture()
    row["native_episode_receipt"]["perception_branches"]["level"] = 3
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_a_row_without_perception_branches_never_reaches_this_check():
    """A plain (unbranched) row never dispatches to
    ``_verify_perception_branch_trace_binding`` at all -- proven by
    deliberately leaving the row's OWN ``role_visits`` malformed
    (something the Perception-branch check would refuse by name) and
    confirming that absence, not this check, is what stays silent."""

    row, trace = fixture()
    del row["native_episode_receipt"]["perception_branches"]
    row["native_episode_receipt"]["role_visits"] = "not-a-list"
    check(row, trace)
