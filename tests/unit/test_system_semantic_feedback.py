"""Join complete actor episodes to signed official construction feedback."""
import copy
import json

import pytest

from test_system_semantic_trajectory import source, materialize
from test_native_episode_diagnostics import _finite_fixture
from speech_aware_evidence_acquisition.analysis.system_rollout_groups import (
    group_complete_system_sources, normalized_answer_hash,
)
from speech_aware_evidence_acquisition.analysis.system_semantic_feedback import (
    SemanticFeedbackError, prepare_semantic_feedback_groups,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def rehash(value, field="content_sha256"):
    value.pop(field, None)
    value[field] = content_hash(value)


def inputs(counts=((0, 0, 0), (0, 2, 0)), *, intents=(1, 1), formats=(True, True),
           finite=False, round_ids=None):
    reports, sources = [], []
    for index, (tp, fp, fn) in enumerate(counts):
        fixture = (lambda: _finite_fixture(with_solver=False)) if finite and index == 1 else None
        actor = source(fixture)
        actor.plan.run_id = "run-" + str(index)
        report = materialize(actor)
        episode = report["episodes"][0]
        if round_ids is not None:
            episode["round_id"] = round_ids[index]
            episode["input_group_sha256"] = content_hash({
                "round_id": episode["round_id"], "split_identity_hash": episode["split_identity_hash"],
                "input_sha256": episode["input_sha256"],
            })
            rehash(episode)
            rehash(report)
        trajectory = episode["trajectory"]
        visits = trajectory["role_visits"]
        reports.append(report)
        sources.append({
            "label": "arm-" + str(index), "run_id": actor.plan.run_id, "attempt_id": actor.plan.attempt_id,
            "feedback_sha256": content_hash(["synthetic-feedback", index]),
            "split_identity_hash": actor.plan.split_identity_hash,
            "model_fragment": "frozen", "session_receipt_sha256": "a" * 64,
            "config_hash": actor.composed.config_hash, "feedback_role": "construction",
            "ordered_sample_ids": ["s1"],
            "rows": [{
                "sample_id": "s1", "trajectory_sha256": trajectory["trajectory_sha256"],
                "input_sha256": episode["input_sha256"],
                "normalized_answer_sha256": normalized_answer_hash(episode["delivered_text"]),
                "tp": tp, "fp": fp, "fn": fn, "intent_exact": intents[index],
                "format_ok": formats[index], "fallback_flags": [],
                "role_visits": [v["stage"] for v in visits],
                "revision_reached": sum(v["stage"] == "solver" for v in visits) > 1,
                "delivery_kind": trajectory["delivery"]["kind"],
                "model_contacts": sum(len(v["contacts"]) for v in visits),
                "tool_events": len(trajectory["tool_events"]),
            }],
        })
    return group_complete_system_sources(sources, f0=0.5), reports


def prepare(*args, **kwargs):
    grouped, reports = inputs(*args, **kwargs)
    return prepare_semantic_feedback_groups(grouped, reports)


def test_empty_entity_error_retains_signed_feedback_without_reference_text():
    grouped, reports = inputs()
    grouped["sources"][0]["private_reference_answer"] = "OFFLINE-GOLD-SENTINEL"
    grouped["groups"][0]["members"][0]["critique"] = "OFFLINE-GOLD-SENTINEL"
    rehash(grouped)
    before = copy.deepcopy((grouped, reports))
    out = prepare_semantic_feedback_groups(grouped, reports)
    group = out["groups"][0]
    feedback = group["comparison_feedback"]
    assert [m["utility"] for m in feedback["members"]] == [0, -1]
    assert [m["fp"] for m in feedback["members"]] == [0, 2]
    assert feedback["eligibility"]["eligible"] is True
    assert feedback["eligibility"]["differing_fields"] == ["fp"]
    assert "OFFLINE-GOLD-SENTINEL" not in json.dumps(out)
    assert "advantage" not in feedback["members"][0]
    assert out["learning_authorized"] is False
    assert out["model_contacts_added"] == out["scorer_contacts_added"] == 0
    for member in group["summary_inputs"]:
        fields = member["fields"]
        assert "reward" not in fields
        assert fields["correct_answer"] == fields["reasoning"] == ""
        episode = json.loads(json.loads(fields["trajectories"])[0]["trajectory"])
        assert len(episode["trajectory"]["role_visits"]) == 4
        assert len(episode["contacts"]) == 5
        assert len(episode["tool_records"]) == 2
    assert before == (grouped, reports)


@pytest.mark.parametrize("counts", [
    ((0, 4, 0), (0, 2, 0)),  # Both utilities negative.
    ((2, 0, 0), (3, 0, 0)),  # Both utilities above one.
    ((1, 1, 0), (1, 0, 1)),  # Equal utility, different FP/FN.
])
def test_signed_or_utility_tied_count_differences_remain_eligible(counts):
    group = prepare(counts)["groups"][0]
    assert group["comparison_feedback"]["eligibility"]["eligible"] is True


@pytest.mark.parametrize("field", ["intent", "format"])
def test_nonentity_outcome_differences_survive_tied_utility(field):
    kwargs = {"intents": (0, 1)} if field == "intent" else {"formats": (False, True)}
    group = prepare(((0, 0, 0), (0, 0, 0)), **kwargs)["groups"][0]
    feedback = group["comparison_feedback"]
    assert [m["utility"] for m in feedback["members"]] == [0, 0]
    assert feedback["eligibility"]["differing_fields"] == [
        "intent_exact" if field == "intent" else "format_ok"]


def test_all_ties_remain_in_population_with_explicit_no_update_disposition():
    out = prepare(((0, 0, 0), (0, 0, 0)))
    assert len(out["groups"]) == 1
    group = out["groups"][0]
    assert len(group["summary_inputs"]) == 2
    eligibility = group["comparison_feedback"]["eligibility"]
    assert eligibility == {
        "rule_id": "terminal-outcome-vector-disagreement-v1",
        "eligible": False, "reason": "identical-terminal-outcome-vector", "differing_fields": [],
    }
    assert out["summary"]["eligible_groups"] == 0
    assert out["summary"]["ineligible_groups"] == 1
    assert out["update_disposition"] == "no-informative-terminal-groups"


def test_finite_abstention_stays_in_complete_episode_and_feedback():
    out = prepare(finite=True)
    group = out["groups"][0]
    fields = group["summary_inputs"][1]["fields"]
    episode = json.loads(json.loads(fields["trajectories"])[0]["trajectory"])
    assert episode["delivered_text"] == ""
    assert episode["trajectory"]["delivery"]["kind"] == "abstention"
    assert len(group["comparison_feedback"]["members"]) == 2


@pytest.mark.parametrize("change", [
    "group-fingerprint", "report-fingerprint", "episode-fingerprint", "trajectory-fingerprint",
    "missing-source", "duplicate-source", "extra-episode", "wrong-run", "wrong-config",
    "wrong-input", "wrong-answer", "wrong-trajectory", "mixed-round", "evaluation",
    "bad-utility", "bad-count", "bad-intent", "bad-format",
])
def test_misbound_or_invalid_inputs_are_rejected(change):
    grouped, reports = inputs()
    group = grouped["groups"][0]
    member = group["members"][0]
    if change == "group-fingerprint": grouped["group_size"] += 1
    elif change == "report-fingerprint": reports[0]["sample_ids"].append("other")
    elif change == "episode-fingerprint": reports[0]["episodes"][0]["round_id"] = "other"
    elif change == "trajectory-fingerprint":
        reports[0]["episodes"][0]["trajectory"]["delivery"]["kind"] = "other"
        rehash(reports[0]["episodes"][0])
        rehash(reports[0])
    elif change == "missing-source": reports.pop()
    elif change == "duplicate-source": reports[1] = copy.deepcopy(reports[0])
    elif change == "extra-episode":
        reports[0]["episodes"].append(copy.deepcopy(reports[0]["episodes"][0]))
        rehash(reports[0])
    elif change in ("wrong-run", "wrong-config"):
        reports[0]["source"]["run_id" if change == "wrong-run" else "config_hash"] = "wrong"
        rehash(reports[0])
    elif change == "wrong-input":
        member["input_sha256"] = "f" * 64
        rehash(grouped)
    elif change == "wrong-answer":
        member["normalized_answer_sha256"] = "f" * 64
        rehash(grouped)
    elif change == "wrong-trajectory":
        member["trajectory_sha256"] = "f" * 64
        rehash(grouped)
    elif change == "mixed-round":
        grouped, reports = inputs(round_ids=("round-1", "round-2"))
    elif change == "evaluation":
        grouped["sources"][0]["feedback_role"] = "evaluation"
        rehash(grouped)
    else:
        field, value = {
            "bad-utility": ("utility", 100),
            "bad-count": ("fp", -1),
            "bad-intent": ("intent_exact", 0.2),
            "bad-format": ("format_ok", "yes"),
        }[change]
        member[field] = value
        rehash(grouped)
    with pytest.raises((SemanticFeedbackError, ValueError)):
        prepare_semantic_feedback_groups(grouped, reports)


def test_source_input_order_is_resolved_by_identity_not_list_position():
    grouped, reports = inputs()
    expected = prepare_semantic_feedback_groups(grouped, reports)
    assert prepare_semantic_feedback_groups(grouped, list(reversed(reports))) == expected


def test_different_answers_without_terminal_feedback_difference_do_not_invent_signal():
    out = prepare(((0, 0, 0), (0, 0, 0)), finite=True)
    group = out["groups"][0]
    episodes = [
        json.loads(json.loads(member["fields"]["trajectories"])[0]["trajectory"])
        for member in group["summary_inputs"]
    ]
    assert episodes[0]["delivered_text"] != episodes[1]["delivered_text"]
    assert group["comparison_feedback"]["eligibility"]["eligible"] is False
    assert len(group["summary_inputs"]) == 2


def test_rehashed_delivery_text_cannot_replace_exact_actor_bytes():
    grouped, reports = inputs()
    episode = reports[0]["episodes"][0]
    episode["delivered_text"] += " "
    grouped["groups"][0]["members"][0]["normalized_answer_sha256"] = normalized_answer_hash(
        episode["delivered_text"])
    rehash(episode)
    rehash(reports[0])
    rehash(grouped)
    with pytest.raises(SemanticFeedbackError, match="delivered bytes"):
        prepare_semantic_feedback_groups(grouped, reports)
