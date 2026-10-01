"""Budget, non-dominance, proposal isolation and immutable search history."""
import pytest

from speech_aware_evidence_acquisition.rails.system_search_archive import (
    SystemSearchArchive, pareto_frontier, proposal_input, proposal_sources,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError, SystemTextPolicyBundle
from test_system_text_policy import seed_document


def point(name, quality, intent, cost, cohort="same"):
    return {"bundle_id": name, "cohort_id": cohort, "slu_f1": quality,
            "intent": intent, "model_calls": cost, "tool_calls": 0}


def test_true_pareto_keeps_balanced_candidate_with_no_single_first():
    rows = [point("quality", .9, .9, 10), point("cheap", .5, .9, 2),
            point("balanced", .8, .9, 5), point("dominated", .7, .8, 6)]
    assert {r["bundle_id"] for r in pareto_frontier(rows)} == {"quality", "cheap", "balanced"}
    with pytest.raises(PolicyError, match="cohort"):
        pareto_frontier(rows + [point("other", .99, .99, 1, "other")])


def test_invalid_and_duplicate_proposals_consume_slots(tmp_path):
    archive = SystemSearchArchive(tmp_path / "archive")
    record = {"raw_response": "invalid json", "session_id": "isolated-1", "model_version": "GPT6-pinned",
              "input_sha256": "a" * 64, "input_tokens": None, "output_tokens": None}
    entry = archive.record_proposal(branch="B", round_index=1, slot=1, receipt=record)
    assert entry["status"] == "invalid"
    with pytest.raises(PolicyError, match="already consumed"):
        archive.record_proposal(branch="B", round_index=1, slot=1, receipt=record)
    assert len(archive.history()) == 1


def test_blind_input_has_no_feedback_and_always_uses_seed():
    seed = SystemTextPolicyBundle.from_json(seed_document())
    kwargs = dict(branch="B", round_index=2, slot=1, seed=seed, parent=seed,
                  model_version="GPT6-pinned", session_id="fresh", input_token_cap=16000, output_token_cap=4000)
    packet = proposal_input(**kwargs)
    assert packet["parent_bundle_id"] == seed.bundle_id
    assert "feedback" not in packet
    with pytest.raises(PolicyError, match="blind"):
        proposal_input(**kwargs, feedback={"scores": "leak"})
    d = seed.as_json()
    d["parent_ids"] = [seed.bundle_id]
    d["role_text"]["solver"] += "\nBe precise."
    parent = SystemTextPolicyBundle.from_json(d, parents=[seed])
    with pytest.raises(PolicyError, match="seed"):
        proposal_input(**dict(kwargs, parent=parent))


def test_frontier_rejects_missing_or_nonfinite_cost():
    with pytest.raises(PolicyError):
        pareto_frontier([point("x", .8, .9, float("nan"))])


def test_archive_round_trip_and_bounded_selection(tmp_path):
    archive = SystemSearchArchive(tmp_path)
    seed = SystemTextPolicyBundle.from_json(seed_document())
    archive.store_policy(seed)
    archive.store_policy(seed)
    assert archive.load_policy(seed.bundle_id) == seed
    rows = [point("a", .8, .9, 4), point("b", .7, .9, 2), point("c", .6, .9, 5)]
    selected = archive.retain(branch="L", cohort_id="same", measurements=rows, selected_ids=["a", "b"])
    assert selected["status"] == "search-only-not-adopted"
    with pytest.raises(PolicyError):
        archive.retain(branch="B", cohort_id="same", measurements=rows, selected_ids=["c"])


def test_prepublished_input_and_exact_response_are_bound(tmp_path):
    import json
    archive = SystemSearchArchive(tmp_path)
    seed = SystemTextPolicyBundle.from_json(seed_document())
    packet = proposal_input(branch="B", round_index=1, slot=1, seed=seed, parent=seed,
        model_version="GPT6-pinned", session_id="blind-fresh", input_token_cap=100, output_token_cap=100)
    archive.store_input(packet)
    proposal = {"schema": "saea-text-policy-update-proposal-v1", "branch": "B", "round": 1,
                "slot": 1, "parent_ids": [seed.bundle_id], "changes": {}, "rationale": "Retain the seed.",
                "hypotheses": [], "evidence": []}
    receipt = {"raw_response": json.dumps(proposal), "session_id": "blind-fresh", "model_version": "GPT6-pinned",
               "input_sha256": packet["input_sha256"], "input_tokens": 90, "output_tokens": 120}
    result = archive.import_response(branch="B", round_index=1, slot=1, receipt=receipt)
    assert result["status"] == "invalid"
    assert archive.history()[0]["status"] == "no-change"
    with pytest.raises(PolicyError):
        archive.import_response(branch="B", round_index=1, slot=1, receipt=receipt)


def test_unused_complementary_policy_and_reference_ancestry_cannot_disappear():
    seed = seed_document()
    other = seed_document()
    other["cumulative_sources"] = [{"kind": "feedback", "sha256": "f" * 64, "sample_ids": ["slurp:train:unused"]}]
    packet = {"parent_policy": seed, "complementary_policies": [other],
        "feedback": {"feedback": {"groups": [{"sample_id": "slurp:train:current"}]},
                     "reference": {"sample_ids": ["slurp:train:initial"]}}}
    sources = proposal_sources(packet, {"selected_parents": ["seed-only"]})
    assert set(sources[-1]["sample_ids"]) == {"slurp:train:900:audio-1", "slurp:train:unused",
                                              "slurp:train:current", "slurp:train:initial"}


def test_wrong_session_receipt_is_preserved_and_cannot_be_replaced(tmp_path):
    archive = SystemSearchArchive(tmp_path)
    seed = SystemTextPolicyBundle.from_json(seed_document())
    packet = proposal_input(branch="B", round_index=1, slot=1, seed=seed, parent=seed,
        model_version="GPT6-pinned", session_id="fresh", input_token_cap=100, output_token_cap=100)
    archive.store_input(packet)
    receipt = {"raw_response": "invalid", "session_id": "different-session", "model_version": "GPT6-pinned",
               "input_sha256": packet["input_sha256"], "input_tokens": 50, "output_tokens": 10}
    result = archive.import_response(branch="B", round_index=1, slot=1, receipt=receipt)
    assert result["status"] == "invalid"
    assert (tmp_path / "responses/B-1-1.json").exists()
    with pytest.raises(PolicyError, match="consumed|exists"):
        archive.import_response(branch="B", round_index=1, slot=1, receipt={**receipt, "session_id": "fresh"})


def test_learning_history_indexes_failures_without_blind_or_future_records(tmp_path):
    import json
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    archive = SystemSearchArchive(tmp_path)
    seed = seed_document()
    for branch, round_index in (("L", 1), ("B", 1), ("L", 2)):
        packet = {"branch": branch, "round": round_index, "slot": 1, "parent_policy": seed,
            "feedback": {"feedback": {"groups": [{"sample_id": "slurp:train:old"}]},
                         "reference": {"sample_ids": ["slurp:train:reference"]}}}
        packet["input_sha256"] = content_hash(packet)
        archive.store_input(packet)
        archive._write(f"responses/{branch}-{round_index}-1.json", {"raw_response": "invalid"})
        archive._write(f"imports/{branch}-{round_index}-1.json", {"status": "invalid"})
    history = archive.learning_history(before_round=2)
    assert len(history) == 1
    assert history[0]["input"]["relpath"] == "inputs/L-1-1.json"
    assert history[0]["disposition"] == "invalid"
    sources = proposal_sources({"parent_policy": seed, "learning_history": history}, {})
    assert {"slurp:train:old", "slurp:train:reference"} <= set(sources[-1]["sample_ids"])
    path = tmp_path / "inputs/L-1-1.json"
    data = json.loads(path.read_text())
    data["parent_policy"]["role_text"]["solver"] += " changed"
    path.write_text(json.dumps(data))
    with pytest.raises(PolicyError, match="history input changed"):
        archive.learning_history(before_round=2)
