"""Prospective capacity omits inactive roles and reserves a real final answer."""
from copy import deepcopy
import json

import pytest

from speech_aware_evidence_acquisition.analysis import native_graph_capacity as cap
from speech_aware_evidence_acquisition.analysis import native_graph_rehearsal as graph
from test_solver_tool_access import solver_values


def values(tool=True):
    v = solver_values()
    v["policy"] = "phase-native-module-v1-c3" if tool else "phase-native-module-v1-c2"
    v["native_graph_capacity_profile"] = "review-off-v1"
    if not tool:
        v["native_episode"].pop("solver_tool_access")
        v["native_episode"]["roles"]["solver"]["max_iterations"] = 1
        v["phase_tools"] = {}
    return v


def payload(sample, role):
    return {"sample_id": sample, "history": [{"role": "control", "contact_id": f"native:{role}:0:{sample}"}]}


@pytest.mark.parametrize("tool", [False, True])
def test_review_off_profile_and_budget_are_pure_and_omit_inactive_roles(tool):
    v = values(tool)
    before = deepcopy(v)
    parsed = graph.rehearsal_profile(v, "review-off-v1")
    assert parsed.max_contacts == (3 if tool else 2)
    budget = cap.native_graph_capacity_budget(v, slot_value_count=10, intent_value_count=5,
                                             profile="review-off-v1")
    assert budget["captured_requests"] == (22 if tool else 8)
    assert budget["request_measurement_endpoints"] == budget["captured_requests"] * 3
    assert budget["padding_tokenizer_endpoints"] == (60 if tool else 18)
    assert budget["contact_cap"] == (142 if tool else 58)
    assert v == before


def test_opt_in_cannot_bypass_review_off_or_budget_validation():
    for mutate in (lambda v: v["native_episode"]["roles"]["planner"].update(max_iterations=1),
                   lambda v: v["native_episode"]["roles"]["solver"].update(max_iterations=4)):
        v = values()
        mutate(v)
        with pytest.raises(ValueError):
            graph.rehearsal_profile(v, "review-off-v1")
    with pytest.raises(ValueError):
        graph.rehearsal_profile(values(), "unknown")
    for counts in ((True, 5), (-1, 5), (10, 0)):
        with pytest.raises(ValueError):
            cap.native_graph_capacity_budget(values(), slot_value_count=counts[0], intent_value_count=counts[1],
                                             profile="review-off-v1")


def test_four_solver_paths_cover_decline_empty_rejection_and_maximum_lookup():
    responder = graph.ReviewOffResponder(list("abcd"), ["person", "place"],
                                        texts={"perception": "candidate", "solver": "final"},
                                        lookup=True, distinction="e" * 512)
    assert responder(payload("a", "solver"))["content"] == "final"
    empty = responder(payload("b", "solver"))
    assert json.loads(empty["tool_calls"][0]["function"]["arguments"])["candidate_ids"] == ["synthetic_absent_slot_type"]
    rejected = responder(payload("c", "solver"))
    assert len(json.loads(rejected["tool_calls"][0]["function"]["arguments"])["candidate_ids"]) == 3
    legal = responder(payload("d", "solver"))
    assert json.loads(legal["tool_calls"][0]["function"]["arguments"])["candidate_ids"] == ["person", "place"]
    for sample in "bcd":
        assert responder(payload(sample, "solver")) == {"role": "assistant", "content": "final"}
    with pytest.raises(ValueError, match="inactive"):
        responder(payload("a", "reviewer"))


def test_plain_responder_and_bounded_padding_make_no_hidden_lookup():
    texts, counts = cap.bounded_response_texts(lambda s: len(s) // 4 + 1,
        targets=["person", "place"], intents=list("xyz"), roles=("perception", "solver"))
    assert set(texts) == set(counts) == {"perception", "solver"}
    responder = graph.ReviewOffResponder(list("abcd"), [], texts=texts, lookup=False)
    assert all("tool_calls" not in responder(payload(s, "solver")) for s in "abcd")
    distinction, count = cap.bounded_lookup_distinction(lambda s: len(s) // 2 + 1, targets=["person", "place"])
    assert 0 < len(distinction) <= 512 and count <= 512


def test_requested_profile_must_match_the_config_declaration():
    v = values()
    with pytest.raises(ValueError, match="profile"):
        graph.rehearsal_profile(v, graph.LEGACY_PROFILE)
    v.pop("native_graph_capacity_profile")
    with pytest.raises(ValueError, match="profile"):
        graph.rehearsal_profile(v, "review-off-v1")


def captured_proof(lookup=True):
    import hashlib
    records, paths, receipts = [], [], []
    for sample in "abcd":
        turns = ("perception", "solver", "solver") if lookup and sample != "a" else ("perception", "solver")
        for index, role in enumerate(turns):
            request = {"messages": [], "max_tokens": 512}
            if index == 2:
                request.update(tool_choice="none")
                request["messages"] = [{"role": "tool", "tool_call_id": "call", "content": "{}"}]
            response = {"role": "assistant", "content": "final"}
            if lookup and sample != "a" and index == 1:
                response = {"role": "assistant", "content": None, "tool_calls": [{"id": "call"}]}
                if sample in "bd":
                    receipts.append({"sample_id": sample, "source_authority_role": "solver",
                                     "source_request_sha256": sample + str(index)})
            records.append({"sample_id": sample, "payload": payload(sample, role), "request": request,
                            "synthetic_response": response, "prepared_request_sha256": sample + str(index)})
        paths.append({"sample_id": sample, "role_visits": ["perception", "solver"], "planner_routes": [],
                      "accepted_solver_receipt": {"final_contact": {"request_sha256": sample + str(len(turns) - 1),
                       "response_text_sha256": hashlib.sha256(b"final").hexdigest()}}})
    return {"sample_ids": list("abcd"), "terminal_paths": paths, "tool_receipts": receipts}, records


@pytest.mark.parametrize("lookup", [False, True])
def test_capture_proves_post_tool_final_reserve_and_custody(lookup):
    proof, records = captured_proof(lookup)
    checked = cap.validate_review_off_capture(proof, records, lookup=lookup)
    assert checked["post_tool_final_requests"] == (3 if lookup else 0)
    assert len(checked["accepted_final_request_sha256"]) == 4


@pytest.mark.parametrize("mutate", [
    lambda p, r: p["terminal_paths"][0]["role_visits"].append("reviewer"),
    lambda p, r: p["terminal_paths"][0]["planner_routes"].append("ACCEPT"),
    lambda p, r: p["terminal_paths"][0]["accepted_solver_receipt"]["final_contact"].update(request_sha256="unbound"),
    lambda p, r: r[4]["request"].update(tool_choice="auto"),
    lambda p, r: r[4]["request"].update(tools=[{"name": "lookup"}]),
    lambda p, r: p["tool_receipts"][0].update(source_authority_role="planner"),
    lambda p, r: p["terminal_paths"].reverse(),
    lambda p, r: r.append(deepcopy(r[0])),
    lambda p, r: r[1]["request"]["messages"].append({"role": "tool", "content": "hidden"}),
    lambda p, r: p["tool_receipts"].pop(),
])
def test_capture_refuses_inactive_paths_unbound_final_or_lost_tool_reserve(mutate):
    proof, records = captured_proof()
    mutate(proof, records)
    with pytest.raises(ValueError):
        cap.validate_review_off_capture(proof, records, lookup=True)


def test_dense_tool_call_padding_shrinks_and_impossible_minimum_fails():
    text, count = cap.bounded_lookup_distinction(len, targets=["person", "place"])
    assert len(text) < 512 and count <= 512
    with pytest.raises(ValueError, match="Minimal"):
        cap.bounded_lookup_distinction(lambda _: 513, targets=["person", "place"])


@pytest.mark.parametrize("rows,targets,distinction", [
    (list("aabc"), ["person", "place"], "check"),
    (list("abcd"), ["person", "person"], "check"),
    (list("abcd"), ["person", "place"], ""),
])
def test_responder_refuses_ambiguous_proof_identities(rows, targets, distinction):
    with pytest.raises(ValueError):
        graph.ReviewOffResponder(rows, targets, texts={}, lookup=True, distinction=distinction)


def test_padding_preserves_an_original_solver_tool_message(monkeypatch):
    message = {"role": "assistant", "content": None, "tool_calls": [{"id": "real-synthetic-call"}]}
    monkeypatch.setattr(graph.FourPathResponder, "__call__", lambda *_: message)
    responder = cap.CapacityResponder(list("abcd"), ["person", "place"], {"solver": "padded text"})
    assert responder(payload("d", "solver")) is message
