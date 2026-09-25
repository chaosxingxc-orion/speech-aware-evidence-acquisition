"""Whole-episode grouped feedback, never isolated-node credit."""
import copy
import math

import pytest

from speech_aware_evidence_acquisition.analysis.system_rollout_groups import (
    RolloutGroupError, group_complete_system_sources, normalized_answer_hash,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def source(label, counts, *, intents=None, revisions=None):
    rows = []
    for i, (tp, fp, fn) in enumerate(counts):
        row = {
            "sample_id": f"s{i}", "trajectory_sha256": content_hash([label, i]),
            "input_sha256": content_hash(["speech", i]),
            "normalized_answer_sha256": content_hash([tp, fp, fn]),
            "tp": tp, "fp": fp, "fn": fn,
            "intent_exact": (intents or [1] * len(counts))[i],
            "format_ok": True, "fallback_flags": [],
            "role_visits": ["perception", "solver", "review", "planner"],
            "revision_reached": (revisions or [False] * len(counts))[i],
            "delivery_kind": "accepted", "model_contacts": 4, "tool_events": 0,
        }
        rows.append(row)
    return {
        "label": label, "run_id": label, "attempt_id": "attempt",
        "feedback_sha256": content_hash(label), "split_identity_hash": "a" * 64,
        "model_fragment": "frozen", "session_receipt_sha256": "b" * 64,
        "config_hash": content_hash(["config", label]), "feedback_role": "construction",
        "ordered_sample_ids": [r["sample_id"] for r in rows], "rows": rows,
    }


def group(*sources):
    return group_complete_system_sources(sources, f0=0.6)


def test_empty_entity_hallucination_creates_feedback_and_all_ties_remain():
    a = source("a", [(0, 0, 0), (2, 1, 1)])
    b = source("b", [(0, 2, 0), (2, 1, 1)])
    out = group(a, b)
    first, tie = out["groups"]
    assert [r["utility"] for r in first["members"]] == [0, -1.2]
    assert [r["advantage"] for r in first["members"]] == pytest.approx([1, -1])
    assert all(r["advantage"] == 0 for r in tie["members"])
    assert out["summary"]["groups"] == 2
    assert out["summary"]["utility_informative_groups"] == 1
    assert out["summary"]["utility_tied_groups"] == 1
    assert out["learning_authorized"] is False
    assert "node_credit" not in str(out)


def test_finite_and_unrevised_outcomes_are_retained_without_invented_decisions():
    a, b = source("a", [(0, 1, 0)]), source("b", [(0, 1, 0)])
    a["rows"][0].update(delivery_kind="finite", fallback_flags=["finite_completion"])
    out = group(a, b)
    row = out["groups"][0]["members"][0]
    assert row["fallback_flags"] == ["finite_completion"]
    assert row["revision_reached"] is False
    assert row["action_probability"] is None
    assert out["summary"]["episodes_without_revision"] == 2
    assert len(out["groups"][0]["members"]) == 2


def test_intent_difference_survives_equal_entity_utility():
    out = group(source("a", [(0, 0, 0)], intents=[0]), source("b", [(0, 0, 0)], intents=[1]))
    assert out["summary"]["utility_tied_groups"] == 1
    assert out["summary"]["intent_disagreement_groups"] == 1
    assert out["groups"][0]["intent_disagreement"] is True


@pytest.mark.parametrize("mutation", [
    "duplicate_source", "missing_row", "duplicate_row", "different_input",
    "different_roster", "different_session", "evaluation", "nan", "bool_count",
    "terminal_alias", "bad_intent", "source_alias",
])
def test_invalid_or_misaligned_complete_sources_refuse(mutation):
    a, b = source("a", [(1, 0, 0), (0, 1, 0)]), source("b", [(1, 0, 0), (0, 2, 0)])
    if mutation == "duplicate_source": b = copy.deepcopy(a)
    elif mutation == "missing_row": b["rows"].pop()
    elif mutation == "duplicate_row": b["rows"][1] = copy.deepcopy(b["rows"][0])
    elif mutation == "different_input": b["rows"][0]["input_sha256"] = "d" * 64
    elif mutation == "different_roster": b["split_identity_hash"] = "e" * 64
    elif mutation == "different_session": b["session_receipt_sha256"] = "e" * 64
    elif mutation == "evaluation": b["feedback_role"] = "evaluation"
    elif mutation == "nan": b["rows"][0]["fp"] = math.nan
    elif mutation == "bool_count": b["rows"][0]["tp"] = True
    elif mutation == "terminal_alias": b["rows"][0]["trajectory_sha256"] = a["rows"][0]["trajectory_sha256"]
    elif mutation == "bad_intent": b["rows"][0]["intent_exact"] = 0.4
    elif mutation == "source_alias": b["run_id"] = "a"
    with pytest.raises(ValueError):
        group(a, b)


def test_normalized_answer_ignores_json_and_entity_order_but_keeps_duplicates():
    a = '{"scenario":"x","action":"y","entities":[{"type":"t","filler":"a"},{"type":"u","filler":"b"}]}'
    b = '{"action":"y","entities":[{"filler":"b","type":"u"},{"filler":"a","type":"t"}],"scenario":"x"}'
    assert normalized_answer_hash(a) == normalized_answer_hash(b)
    assert normalized_answer_hash(a) != normalized_answer_hash(a.replace('{"type":"u","filler":"b"}', '{"type":"t","filler":"a"}'))
    assert normalized_answer_hash("invalid one") != normalized_answer_hash("invalid two")


def test_arithmetic_is_group_relative_not_global_and_does_not_mutate_sources():
    a, b = source("a", [(2, 0, 0), (0, 1, 0)]), source("b", [(1, 0, 0), (0, 2, 0)])
    original = copy.deepcopy([a, b])
    out = group(a, b)
    for row in out["groups"]:
        assert sum(m["advantage"] for m in row["members"]) == pytest.approx(0)
    assert [a, b] == original


@pytest.fixture
def pinned_source(tmp_path):
    import hashlib
    import json

    def write(name, document, *, jsonl=False):
        p = tmp_path / name
        p.write_text(json.dumps(document) + "\n")
        return {"relpath": name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}

    payload = {
        "sample_id": "s0", "carrier_lock_key": "slurp", "media_relpath": "audio.flac",
        "speech_ref": "slurp/s0", "speech_packet_sha256": "d" * 64,
        "sample_rate_hz": 16000, "audio_seconds": 2.0,
    }
    request = {"payload": payload}
    trace_pin = write("trace.jsonl", {"record_id": "r1/request", "payload": request})
    output = {"sample_id": "s0", "text": '{"scenario":"a","action":"b","entities":[]}'}
    output_pin = write("outputs.jsonl", output)
    artifact = lambda pin: {"path": str(tmp_path / pin["relpath"]), "sha256": pin["sha256"]}
    manifest = {
        "status": "COMPLETED", "run_id": "run", "plan": {"attempt_id": "attempt"},
        "config": {"config_hash": "c" * 64, "fragments": {"model": "frozen"}},
        "split": {"ids": ["s0"], "count": 1, "identity_hash": "a" * 64},
        "raw_trace": artifact(trace_pin), "outputs": artifact(output_pin),
        "session_receipt": {"sha256": "b" * 64},
    }
    manifest_pin = write("manifest.json", manifest)
    trajectory = {
        "sample_id": "s0",
        "role_visits": [
            {"stage": "perception", "contacts": [{
                "request_record_id": "r1/request",
                "request_record_sha256": content_hash(request),
                "request_payload_sha256": content_hash(payload),
            }]},
            *[{"stage": phase, "contacts": []} for phase in ("solver", "review", "planner")],
        ],
        "delivery": {"kind": "accepted"}, "tool_events": [],
        "final_output": {"record_sha256": content_hash(output)},
    }
    trajectory["trajectory_sha256"] = content_hash(trajectory)
    exported = {
        "source": {"manifest_content_sha256": content_hash(manifest), "config_hash": "c" * 64},
        "sample_ids": ["s0"], "trajectories": [trajectory],
    }
    exported["document_sha256"] = content_hash(exported)
    feedback = {
        "schema": "saea-slurp-system-feedback-v1", "feedback_role": "construction",
        "run_id": "run", "attempt_id": "attempt", "split_identity_hash": "a" * 64,
        "source_bindings": {
            "manifest": manifest_pin,
            **{k: write(k + ".json", {}) for k in ("phases", "flight_receipts", "score_jobs")},
        },
        "resolved_auxiliary_sources": {},
        "system_trajectories": exported,
        "terminal_feedback": [{
            "sample_id": "s0", "trajectory_sha256": trajectory["trajectory_sha256"],
            "delivered_output_sha256": content_hash(output),
            "tp": 0, "fp": 0, "fn": 0, "intent_exact": 1,
            "format_ok": True, "fallback_flags": [],
        }],
    }
    feedback["content_sha256"] = content_hash(feedback)
    pin = write("feedback.json", feedback)
    return tmp_path, pin, feedback, write


def test_loader_resolves_source_input_and_terminal_output_without_new_scoring(pinned_source):
    from speech_aware_evidence_acquisition.analysis.system_rollout_groups import load_group_source
    root, pin, _, _ = pinned_source
    source = load_group_source(data_root=root, feedback_pin=pin, label="one")
    assert source["ordered_sample_ids"] == ["s0"]
    assert source["rows"][0]["tp"] == source["rows"][0]["fp"] == 0
    assert source["rows"][0]["role_visits"] == ["perception", "solver", "review", "planner"]
    assert source["rows"][0]["revision_reached"] is False
    assert len(source["rows"][0]["input_sha256"]) == 64


@pytest.mark.parametrize("name", ["trace.jsonl", "outputs.jsonl", "phases.json", "feedback.json"])
def test_loader_refuses_source_bytes_changed_since_pinning(pinned_source, name):
    from speech_aware_evidence_acquisition.analysis.system_rollout_groups import load_group_source
    root, pin, _, _ = pinned_source
    p = root / name
    p.write_bytes(p.read_bytes() + b" ")
    with pytest.raises(ValueError):
        load_group_source(data_root=root, feedback_pin=pin, label="one")


def test_loader_refuses_rehashed_feedback_joined_to_another_trajectory(pinned_source):
    from speech_aware_evidence_acquisition.analysis.system_rollout_groups import load_group_source
    root, pin, document, write = pinned_source
    document["terminal_feedback"][0]["trajectory_sha256"] = "f" * 64
    document.pop("content_sha256")
    document["content_sha256"] = content_hash(document)
    pin = write("feedback.json", document)
    with pytest.raises(RolloutGroupError, match="another episode"):
        load_group_source(data_root=root, feedback_pin=pin, label="one")


@pytest.mark.parametrize("field", ["policy_supply_receipt", "policy_episode_decisions"])
def test_historical_grouping_does_not_discard_real_optimized_decisions(pinned_source, field):
    from speech_aware_evidence_acquisition.analysis.system_rollout_groups import load_group_source
    root, pin, document, write = pinned_source
    document[field] = {"recorded": "decision"}
    document.pop("content_sha256")
    document["content_sha256"] = content_hash(document)
    pin = write("feedback.json", document)
    with pytest.raises(RolloutGroupError, match="policy-credit join"):
        load_group_source(data_root=root, feedback_pin=pin, label="one")
