"""Coherent feedback preserves full decision text and the balanced source index."""
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError, canonical
from test_system_proposer_views import learning_fixture, read_all, PROFILE
from test_system_proposer_capsule import fixture, reseal

COHERENT = "coherent-feedback-v1"


def chain_fixture(tmp_path, oversized=False):
    packet, roots = learning_fixture(tmp_path)
    for cid in ("seed", "seed-aa"):
        output = roots["data"] / f"{cid}-terminal_output.jsonl"
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        trace = []
        for i, row in enumerate(rows):
            texts = ["Initial full Solver draft.",
                     "Review evidence. " * (2000 if oversized else 40) + "CRITICISM_END",
                     "REVISE", "Complete revised Solver answer.",
                     "Final review.", "ACCEPT"]
            roles = ("solver", "reviewer", "planner", "solver", "reviewer", "planner")
            visits = []
            for j, (role, text) in enumerate(zip(roles, texts, strict=True)):
                rid = f"{cid}-{i}-{j}"
                visits.append({"role_id": role, "execution_receipt": {"contacts": [{"request_id": rid}]}})
                trace.append({"record_id": rid + "/response", "channel": "MODEL_RESPONSE",
                              "payload": {"text": text}})
            row["native_episode_receipt"]["role_visits"] = visits
            row["native_episode_receipt"]["planner_routes"] = [
                {"action": "REVISE", "role_visit_index": 2},
                {"action": "ACCEPT", "role_visit_index": 5}]
        for field, records in (("terminal_output", rows), ("trace", trace)):
            path = roots["data"] / f"{cid}-{field}.jsonl"
            path.write_text("".join(canonical(row) + "\n" for row in records))
            for group in packet["feedback"]["feedback"]["groups"]:
                for member in group["members"]:
                    if member["candidate_id"] == cid:
                        member["execution"][field]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    reseal(packet)
    return packet, roots


@pytest.mark.parametrize("paged", [False, True])
def test_complete_criticism_and_revision_are_visible_without_optional_tool_read(tmp_path, paged):
    packet, roots = chain_fixture(tmp_path)
    capsule = ProposerCapsule.from_packet(packet, roots=roots, view_profile=COHERENT,
        cache_root=tmp_path / "cache" if paged else None)
    initial = capsule.initial_input()
    chain = initial["feedback_chain"]
    assert chain["status"] == "complete-decision-chain"
    assert [r["role"] for r in chain["responses"]] == ["solver", "reviewer", "planner", "solver"]
    assert chain["responses"][1]["text"].endswith("CRITICISM_END")
    assert chain["responses"][3]["text"] == "Complete revised Solver answer."
    for r in chain["responses"]:
        a = r["source"]
        exact = json.loads(read_all(capsule, a["artifact_id"])[a["offset"]:a["offset"] + a["characters"]])
        assert exact["payload"]["text"] == r["text"]
    assert chain["omitted_role_responses"] == 2
    assert chain["omissions"] and len(canonical(chain).encode()) <= 6144
    assert set(initial["feedback_category_index"]["comparisons"]["seed-aa"]["counts"]) == {
        "correct_answer_repaired", "correct_answer_damaged", "native_counts_unchanged",
        "changed_not_resolved", "unreliable_execution"}
    assert "feedback_overview" not in initial and "feedback_examples" not in initial
    assert ProposerCapsule.from_json(capsule.as_json()).request() == capsule.request()
    assert "full decision chain" in capsule.request()["instructions"]


def test_chain_selection_is_deterministic_and_does_not_depend_on_return_magnitude(tmp_path):
    packet, roots = chain_fixture(tmp_path)
    first = ProposerCapsule.from_packet(packet, roots=roots, view_profile=COHERENT).initial_input()["feedback_chain"]
    packet["feedback"]["feedback"]["groups"].reverse()
    for g in packet["feedback"]["feedback"]["groups"]:
        for m in g["members"]:
            m["utility"] = m["relative_return"] = -987.0
    reseal(packet)
    other = ProposerCapsule.from_packet(packet, roots=roots, view_profile=COHERENT).initial_input()["feedback_chain"]
    assert (first["sample_id"], first["candidate_id"]) == (other["sample_id"], other["candidate_id"])
    assert first["responses"] == other["responses"]


def test_oversized_chain_is_refused_before_contact_instead_of_truncating_criticism(tmp_path):
    packet, roots = chain_fixture(tmp_path, oversized=True)
    with pytest.raises(PolicyError, match="coherent.*bound"):
        ProposerCapsule.from_packet(packet, roots=roots, view_profile=COHERENT).initial_input()


def test_missing_review_stays_explicit_without_fabricating_a_chain(tmp_path):
    packet, roots = learning_fixture(tmp_path)
    initial = ProposerCapsule.from_packet(packet, roots=roots, view_profile=COHERENT).initial_input()
    assert initial["feedback_chain"]["status"] == "no-complete-decision-chain"
    assert initial["feedback_chain"]["responses"] == []
    index = initial["feedback_category_index"]["case_index"]
    c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=COHERENT)
    assert len(json.loads(read_all(c, index["artifact_id"]))["cases"]) == 5


def test_blind_request_remains_byte_identical_to_compact_profile(tmp_path):
    packet, roots = fixture(tmp_path, "B")
    new = ProposerCapsule.from_packet(packet, roots=roots, view_profile=COHERENT)
    old = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)
    assert new.request() == old.request()
    assert not any(a["kind"].startswith("feedback-") for a in new.as_json()["artifacts"])


def test_coherent_packet_keeps_one_source_page_inside_actual_metered_continuation_budget(tmp_path):
    from test_system_proposer_responses import server, reply, completed, call
    from test_system_proposer_round import runner
    from speech_aware_evidence_acquisition.rails.system_proposer_responses import ResponsesHTTP, ResponsesProposer
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposalDispatch
    packet, roots = chain_fixture(tmp_path)
    c = ProposerCapsule.from_packet(packet, roots=roots, view_profile=COHERENT)
    identity = c.initial_input()["feedback_chain"]["details_artifact_id"]
    args = {"artifact_id": identity, "offset": 0, "limit": 2048}
    reservations = []
    with server([reply(completed([call(identity, arguments=canonical(args))])), reply(completed())]) as (endpoint, requests):
        t = ResponsesProposer(c, ResponsesHTTP(endpoint, fixture_only=True), audit_dir=tmp_path / "transport",
            input_counter=runner.request_bound, before_contact=reservations.append, contact_cap=4)
        result = ProposalDispatch(tmp_path / "dispatch", c).run(t)
    assert len(requests) == len(reservations) == 2
    assert reservations[1]["input_token_bound"] + 100 <= packet["input_token_cap"]
    assert result["input_tokens"] == 200  # Synthetic measurement only.
    assert len(c.access_log) == 1


@pytest.mark.parametrize("field,value", [("record_id", "foreign/response"), ("channel", "MODEL_REQUEST")])
def test_coherent_chain_refuses_a_response_with_wrong_custody(tmp_path, field, value):
    from speech_aware_evidence_acquisition.rails.system_proposer_views import coherent_feedback_chain
    packet, roots = chain_fixture(tmp_path)
    cap = ProposerCapsule.from_packet(packet, roots=roots, view_profile=PROFILE)
    original_page = cap._page
    def tampered(artifact, offset, limit):
        raw = original_page(artifact, offset, limit)
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if isinstance(obj, dict) and obj.get("channel") == "MODEL_RESPONSE":
            obj[field] = value
            return canonical(obj)
        return raw
    with pytest.raises(PolicyError, match="coherent response differs"):
        coherent_feedback_chain(cap.initial_input()["feedback_overview"], cap._artifacts, tampered)
