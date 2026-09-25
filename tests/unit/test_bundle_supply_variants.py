"""Post-seal checks for Solver supply alternatives."""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _verify_outputs, _verify_outputs_trace_binding,
)


SAMPLE = "slurp:train:synthetic"
ARM = "speech-feature-query-native-tools"


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def fixture(revisions=0):
    trace, visits = {}, []
    for visit in range(revisions + 1):
        contacts = []
        for index in range(2):
            rid = f"request-{visit}-{index}"
            answer = f"answer-{visit}-{index}"
            contact = {
                "agent_contact_id": f"solver:{visit}:{index}",
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
        visits.append({
            "role_id": "solver", "stage": "solver",
            "execution_receipt": {"contacts": contacts, "final_contact": contacts[-1]},
        })
    trace["synthetic/org"] = {"org_final_query_state": {
        "query_sample_id": SAMPLE,
        "retrieved_value_ids": ["v:plan", "v:later"],
    }}
    last = contacts[-1]
    variant = {
        "schema": "saea-supply-variant-arms-v1", "phase_id": "solver",
        "arm_count": 2, "delivered_arm_id": "plan",
        "fit_estimate": {
            "slot_tokens": 24576, "completion_ceiling": 512,
            "base_prompt_tokens": 100, "tokens_per_supplied_item": 10,
            "reserve_tokens": 3072, "prompt_limit_tokens": 20990,
        },
        "arms": [
            {"arm_index": 0, "arm_id": "wide", "deliver": False,
             "contact_id": contacts[0]["agent_contact_id"],
             "resolved_knobs": [{"path": "knowledge_stores.ex.phase_supply.solver.k", "value": 30}],
             "supplied_value_ids": ["v:wide"], "supplied_item_count": 1,
             "max_supplied_items": 5},
            {"arm_index": 1, "arm_id": "plan", "deliver": True,
             "contact_id": last["agent_contact_id"], "resolved_knobs": [],
             "supplied_value_ids": ["v:plan"], "supplied_item_count": 1,
             "max_supplied_items": 5},
        ],
    }
    row = {
        "request_id": last["request_id"], "sample_id": SAMPLE,
        "carrier_lock_key": "slurp", "arm": ARM,
        "text": trace[last["request_id"] + "/response"]["text"],
        "admitted": True, "request_sha256": last["request_sha256"],
        "response_sha256": last["response_sha256"],
        "response_text_sha256": last["response_text_sha256"],
        "native_episode_receipt": {"role_visits": visits},
        "supply_variants": variant,
    }
    return row, trace


def check(row, trace):
    rows = _verify_outputs(
        (json.dumps(row) + "\n").encode(), frozenset({SAMPLE}), "slurp", ARM,
    )
    _verify_outputs_trace_binding(rows, trace)


@pytest.mark.parametrize("revisions", [0, 1])
def test_all_solver_visits_are_trace_bound(revisions):
    row, trace = fixture(revisions)
    check(row, trace)


def test_missing_non_delivering_response_is_refused():
    row, trace = fixture()
    del trace["request-0-0/response"]
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_tampered_prior_revision_response_is_refused():
    row, trace = fixture(1)
    trace["request-0-0/response"]["text"] = "tampered"
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_wrong_final_arm_contact_is_refused():
    row, trace = fixture()
    row["supply_variants"]["arms"][0]["contact_id"] = "wrong"
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_delivering_ids_must_match_final_state():
    row, trace = fixture()
    row["supply_variants"]["arms"][1]["supplied_value_ids"] = ["v:wrong"]
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_prior_revision_must_have_all_arm_contacts():
    row, trace = fixture(1)
    row["native_episode_receipt"]["role_visits"][1]["execution_receipt"]["contacts"].pop(0)
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_arm_request_cannot_belong_to_another_row():
    row, trace = fixture()
    trace["request-0-0/request"]["payload"]["sample_id"] = "other-row"
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)


def test_final_state_source_is_required():
    row, trace = fixture()
    del trace["synthetic/org"]
    with pytest.raises(BundleError, match="I7v"):
        check(row, trace)
