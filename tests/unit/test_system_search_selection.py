"""Verified same-round retention, parent custody and cumulative selection exposure."""
import copy
import json

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive, proposal_sources
from speech_aware_evidence_acquisition.rails.system_search_protocol import build_protocol, stage_for
from speech_aware_evidence_acquisition.rails.system_text_feedback import CompleteSystemFeedback
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError, SystemTextPolicyBundle, assert_roster_disjoint, canonical,
)
from test_system_search_protocol import rosters
from test_system_text_policy import seed_document


def selection_fixture(tmp_path, stage_name="update-1"):
    archive = SystemSearchArchive(tmp_path / "archive")
    seed = SystemTextPolicyBundle.from_json(seed_document())
    archive.store_policy(seed)
    protocol = build_protocol(rosters())
    protocol["seed_bundle"] = {"bundle_id": seed.bundle_id}
    protocol["proposer_exact_version"] = "GPT6-fixture-pinned"
    stage = stage_for(protocol, stage_name)
    bindings, summaries, sources = {}, {}, []
    for cid in stage["member_slots"]:
        bundle = seed
        if cid not in {"seed", "seed-aa", "L-parent", "L-parent-aa", "B-parent", "B-parent-aa"}:
            d = seed.as_json()
            d["parent_ids"] = [seed.bundle_id]
            d["role_text"]["solver"] += "\nSynthetic variant " + cid + "."
            d["cumulative_sources"].append({"kind": "proposal", "sha256": content_hash(cid),
                "sample_ids": [f"slurp:train:source-{cid}:audio"]})
            bundle = SystemTextPolicyBundle.from_json(d, parents=[seed])
            archive.store_policy(bundle)
        bindings[cid] = {"bundle_id": bundle.bundle_id, "run_id": "RUN-" + cid,
                         "config_hash": content_hash({"config": cid})}
        summaries[cid] = {"slu_f1": .7, "intent": .9, "model_calls": 2400,
                          "tool_calls": 200, "reliable_completion_rate": 1.0}
        sources.append({"candidate_id": cid, **{k: v for k, v in bindings[cid].items() if k != "bundle_id"}})
    for branch in ("L", "B"):
        first = branch + ("-candidate-1" if stage_name.startswith("update-") else "-1")
        second = branch + ("-candidate-2" if stage_name.startswith("update-") else "-2")
        summaries[first]["slu_f1"] = .8
        summaries[second].update(slu_f1=.75, model_calls=1600, tool_calls=100)
    d = {"schema": "saea-complete-system-feedback-v1", "family_id": stage_name,
        "reference": {"sample_ids": stage_for(protocol, "initial")["sample_ids"], "f1": .7},
        "summaries": summaries, "feedback": {"sources": sources, "candidate_ids": list(bindings),
            "groups": [{"sample_id": sid, "members": [{"candidate_id": cid, "utility": 0, "execution": {}}
                for cid in bindings]} for sid in stage["sample_ids"]]},
        "read_authority": {"read_run_id": "FIXTURE-READ", "recipe": {"relpath": "recipe.json", "sha256": "a" * 64},
                           "ledger_row_sha256": "b" * 64}}
    evaluation = {"schema": "saea-system-search-evaluation-binding-v1", "stage": stage_name,
                  "protocol_sha256": content_hash(protocol), "member_bindings": bindings}
    return archive, protocol, CompleteSystemFeedback(canonical(d)), evaluation


def retain(archive, protocol, feedback, evaluation, branch="L"):
    suffix = "-candidate-" if evaluation["stage"].startswith("update-") else "-"
    ids = [evaluation["member_bindings"][branch + suffix + str(i)]["bundle_id"] for i in (1, 2)]
    return archive.retain_feedback(protocol=protocol, stage_name=evaluation["stage"], feedback=feedback,
        evaluation=evaluation, branch=branch, selected_ids=ids)


def test_retention_uses_complete_feedback_preserves_frontier_and_own_branch_only(tmp_path):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path)
    record = retain(archive, protocol, feedback, evaluation)
    assert record["status"] == "search-only-not-adopted"
    assert record["feedback_sha256"] == content_hash(feedback.as_json())
    assert [r["slu_f1"] for r in record["frontier"]] == [.8, .75]
    assert all(r["candidate_id"].startswith("L-") for r in record["measurements"])
    assert "B-candidate" not in canonical(record)
    assert record["same_chain_aa"]["candidate_id"] == "L-parent-aa"
    assert record["selection_sha256"] == content_hash({k: v for k, v in record.items() if k != "selection_sha256"})
    with pytest.raises(PolicyError, match="exists|consumed"):
        retain(archive, protocol, feedback, evaluation)


@pytest.mark.parametrize("fault", ["family", "cohort", "missing", "run", "config", "protocol", "aa", "seed", "authority"])
def test_retention_refuses_mixed_or_unbound_measurements_before_record(tmp_path, fault):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path)
    d = feedback.as_json()
    if fault == "family": d["family_id"] = "update-2"
    elif fault == "cohort": d["feedback"]["groups"].reverse()
    elif fault == "missing": d["summaries"].pop("B-candidate-2")
    elif fault == "run": evaluation["member_bindings"]["B-candidate-1"]["run_id"] = "OTHER-RUN"
    elif fault == "config": evaluation["member_bindings"]["L-candidate-1"]["config_hash"] = "f" * 64
    elif fault == "protocol": evaluation["protocol_sha256"] = "f" * 64
    elif fault == "aa": evaluation["member_bindings"]["L-parent-aa"]["bundle_id"] = evaluation["member_bindings"]["L-candidate-1"]["bundle_id"]
    elif fault == "seed": evaluation["member_bindings"]["B-parent"]["bundle_id"] = evaluation["member_bindings"]["B-candidate-1"]["bundle_id"]
    else: d.pop("read_authority")
    with pytest.raises(PolicyError):
        retain(archive, protocol, CompleteSystemFeedback(canonical(d)), evaluation)
    assert not (archive.root / "retentions").exists()


def test_selection_exposure_covers_losing_candidates_and_reaches_later_proposals(tmp_path):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path)
    record = retain(archive, protocol, feedback, evaluation)
    parent = archive.load_policy(record["active_ids"][0])
    proposal_record = {"new": "actual proposal identity"}
    packet = {"parent_policy": parent.as_json(), "selection": record,
              "learning_history": [{"cumulative_sources": [], "earlier": "not the current proposal"}]}
    sources = proposal_sources(packet, proposal_record)
    assert sources[-1]["sha256"] == content_hash(proposal_record)
    ids = {sid for source in sources for sid in source["sample_ids"]}
    assert "slurp:train:source-L-candidate-2:audio" in ids
    assert set(stage_for(protocol, "update-1")["sample_ids"]) <= ids
    assert not any("source-B-" in sid for sid in ids)
    variant = stage_for(protocol, "update-1")["sample_ids"][0].rsplit(":", 1)[0] + ":other-recording"
    with pytest.raises(PolicyError, match="overlaps"):
        assert_roster_disjoint(sources, [variant])
    assert_roster_disjoint(sources, stage_for(protocol, "update-2")["sample_ids"])


def test_later_learning_parent_and_complementary_must_match_recorded_retention(tmp_path):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path)
    record = retain(archive, protocol, feedback, evaluation)
    kwargs = dict(protocol=protocol, round_index=2, feedback=feedback,
                  parent_id=record["active_ids"][0], complementary_ids=record["active_ids"][1:])
    assert archive.learning_selection(**kwargs) == record
    with pytest.raises(PolicyError, match="parent"):
        archive.learning_selection(**{**kwargs, "parent_id": protocol["seed_bundle"]["bundle_id"]})
    with pytest.raises(PolicyError, match="complementary"):
        archive.learning_selection(**{**kwargs, "complementary_ids": [evaluation["member_bindings"]["B-candidate-1"]["bundle_id"]]})
    d = feedback.as_json()
    d["summaries"]["L-candidate-1"]["slu_f1"] = .99
    with pytest.raises(PolicyError, match="feedback"):
        archive.learning_selection(**{**kwargs, "feedback": CompleteSystemFeedback(canonical(d))})
    path = archive.root / "retentions/update-1/L.json"
    changed = copy.deepcopy(record)
    changed["active_ids"].reverse()
    path.write_text(json.dumps(changed))
    with pytest.raises(PolicyError, match="identity"):
        archive.learning_selection(**kwargs)


def test_first_learning_round_uses_unselected_seed(tmp_path):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path)
    seed_id = protocol["seed_bundle"]["bundle_id"]
    kwargs = dict(protocol=protocol, round_index=1, feedback=feedback, parent_id=seed_id, complementary_ids=[])
    assert archive.learning_selection(**kwargs) is None
    with pytest.raises(PolicyError, match="seed"):
        archive.learning_selection(**{**kwargs, "parent_id": evaluation["member_bindings"]["L-candidate-1"]["bundle_id"]})


def test_common_selection_retains_separate_finalists_without_dev_feedback(tmp_path):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path, "selection")
    left = retain(archive, protocol, feedback, evaluation, "L")
    right = retain(archive, protocol, feedback, evaluation, "B")
    frozen = archive.freeze_finalists(protocol=protocol, feedback=feedback)
    assert frozen["members"] == {"seed": protocol["seed_bundle"]["bundle_id"],
        "seed-aa": protocol["seed_bundle"]["bundle_id"], "L-frozen": left["active_ids"][0],
        "B-frozen": right["active_ids"][0]}
    assert frozen["status"] == "frozen-for-dev-not-adopted"
    assert all(source["kind"] != "test" for source in frozen["cumulative_sources"])
    with pytest.raises(PolicyError):
        archive.freeze_finalists(protocol=protocol, feedback=feedback)


def test_no_finalists_without_both_common_cohort_selections(tmp_path):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path, "selection")
    retain(archive, protocol, feedback, evaluation, "L")
    with pytest.raises(PolicyError, match="selection"):
        archive.freeze_finalists(protocol=protocol, feedback=feedback)


def test_explicit_no_qualified_candidate_fallback_preserves_dominated_parent(tmp_path):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path)
    parent = protocol["seed_bundle"]["bundle_id"]
    kwargs = dict(protocol=protocol, stage_name="update-1", feedback=feedback, evaluation=evaluation,
                  branch="L", selected_ids=[parent])
    with pytest.raises(PolicyError, match="non-dominated"):
        archive.retain_feedback(**kwargs)
    record = archive.retain_feedback(**kwargs, retain_parent=True)
    assert record["parent_fallback"] and record["active_ids"] == [parent]
    assert parent not in {r["bundle_id"] for r in record["frontier"]}


def test_common_cohort_repeated_seed_is_not_a_lucky_selectable_version(tmp_path):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path, "selection")
    evaluation["member_bindings"]["L-1"]["bundle_id"] = protocol["seed_bundle"]["bundle_id"]
    d = feedback.as_json()
    d["summaries"]["L-1"]["slu_f1"] = .99
    feedback = CompleteSystemFeedback(canonical(d))
    record = archive.retain_feedback(protocol=protocol, stage_name="selection", feedback=feedback,
        evaluation=evaluation, branch="L", selected_ids=[evaluation["member_bindings"]["L-2"]["bundle_id"]])
    assert next(r for r in record["measurements"] if r["candidate_id"] == "seed")["slu_f1"] == .7
    assert record["duplicate_bundle_replicates"][0]["candidate_id"] == "L-1"
    assert all(r["slu_f1"] != .99 for r in record["frontier"])


@pytest.mark.parametrize("fault", ["dominated", "too-many", "foreign", "bad-fallback", "overlap", "missing-policy"])
def test_invalid_retention_never_partially_publishes(tmp_path, fault):
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path)
    ids = [evaluation["member_bindings"]["L-candidate-1"]["bundle_id"]]
    fallback = False
    if fault == "dominated": ids = [protocol["seed_bundle"]["bundle_id"]]
    elif fault == "too-many": ids = list({b["bundle_id"] for b in evaluation["member_bindings"].values()})
    elif fault == "foreign": ids = [evaluation["member_bindings"]["B-candidate-1"]["bundle_id"]]
    elif fault == "bad-fallback": fallback = True
    elif fault == "missing-policy":
        # Delete only this synthetic fixture's copy, never a repository artifact.
        (archive.root / f"policies/{ids[0]}.json").unlink()
    else:
        bundle = archive.load_policy(ids[0])
        d = bundle.as_json()
        d["cumulative_sources"].append({"kind": "feedback", "sha256": "f" * 64,
            "sample_ids": [stage_for(protocol, "update-1")["sample_ids"][0]]})
        replacement = SystemTextPolicyBundle.from_json(d, parents=[archive.load_policy(d["parent_ids"][0])])
        archive.store_policy(replacement)
        evaluation["member_bindings"]["L-candidate-1"]["bundle_id"] = replacement.bundle_id
    with pytest.raises((PolicyError, FileNotFoundError)):
        archive.retain_feedback(protocol=protocol, stage_name="update-1", feedback=feedback,
            evaluation=evaluation, branch="L", selected_ids=ids, retain_parent=fallback)
    assert not (archive.root / "retentions").exists()


def test_learning_capsule_accepts_own_selection_and_refuses_rehashed_blind_fields(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_search_archive import proposal_input
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import input_references
    archive, protocol, feedback, evaluation = selection_fixture(tmp_path)
    record = retain(archive, protocol, feedback, evaluation)
    packet = proposal_input(branch="L", round_index=2, slot=1,
        seed=archive.load_policy(protocol["seed_bundle"]["bundle_id"]),
        parent=archive.load_policy(record["active_ids"][0]), model_version="GPT6-fixture-pinned",
        session_id="fresh", input_token_cap=32768, output_token_cap=4096,
        feedback=feedback.learning_view([cid for cid in feedback.as_json()["summaries"] if cid.startswith("L-")]))
    packet["selection"] = record
    packet["protocol_sha256"] = content_hash(protocol)
    packet["input_sha256"] = content_hash({k: v for k, v in packet.items() if k != "input_sha256"})
    assert input_references(packet)
    record["member_bindings"]["B-illicit"] = record["member_bindings"]["L-parent"]
    record["selection_sha256"] = content_hash({k: v for k, v in record.items() if k != "selection_sha256"})
    packet["input_sha256"] = content_hash({k: v for k, v in packet.items() if k != "input_sha256"})
    with pytest.raises(PolicyError, match="another branch"):
        input_references(packet)
