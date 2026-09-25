"""Synthetic full episodes reach the TF-GRPO summary field without gold text."""
import copy
import json

import pytest

from test_system_trajectory import _source
from test_native_episode_diagnostics import _finite_fixture
from speech_aware_evidence_acquisition.analysis.system_semantic_trajectory import (
    SemanticTrajectoryError, materialize_semantic_trajectories, tfgrpo_summary_fields,
)


def source(fixture=None):
    value = _source() if fixture is None else _source(fixture)
    value.plan.split_role = "discovery"
    value.plan.split_identity_hash = "d"*64
    first = value.bundle.trace_records["request-perception-1/request"]["payload"]
    first.update(carrier_lock_key="slurp", media_relpath="audio/one.wav",
                 speech_ref="recording-one", speech_packet_sha256="e"*64,
                 sample_rate_hz=16000, audio_seconds=1.0,
                 task_instruction="Identify the spoken intent and entities.")
    return value


def materialize(value=None):
    return materialize_semantic_trajectories(value or source(), round_id="construction-round-1")


def test_every_role_contact_and_tool_event_reaches_one_upstream_trajectory():
    document = materialize()
    episode = document["episodes"][0]
    fields = tfgrpo_summary_fields(episode)
    upstream = json.loads(fields["trajectories"])
    assert len(upstream) == 1
    visible = json.loads(upstream[0]["trajectory"])
    assert [v["stage"] for v in visible["trajectory"]["role_visits"]] == [
        "perception", "solver", "review", "planner"]
    assert len(visible["contacts"]) == 5
    assert len(visible["tool_records"]) == 2
    assert len(visible["timeline_record_ids"]) == len(set(visible["timeline_record_ids"]))
    assert "tool call" in json.dumps(visible)
    assert "ACCEPT" in json.dumps(visible)
    assert fields["correct_answer"] == "" and fields["reasoning"] == ""
    assert "reward" not in fields
    assert document["learning_authorized"] is False and document["model_contacts_added"] == 0


def test_request_payloads_are_losslessly_resolvable_and_repeated_content_is_shared():
    value = source()
    repeated = [{"state_kind": "tool-result", "content": "A supported correction."}]
    for name in ("request-reviewer-1", "request-reviewer-2"):
        value.bundle.trace_records[name+"/request"]["payload"]["history"] = copy.deepcopy(repeated)
    before = copy.deepcopy(value.bundle.trace_records)
    episode = materialize(value)["episodes"][0]
    pool = episode["content_pool"]
    for contact in episode["contacts"]:
        actual = value.bundle.trace_records[contact["request_record_id"]]["payload"]
        restored = {key: pool[ref] for key, ref in contact["request_field_refs"].items()}
        assert restored == actual
        assert pool[contact["response_record_ref"]] == value.bundle.trace_records[contact["response_record_id"]]
    review = [c for c in episode["contacts"] if c["role_id"] == "reviewer"]
    assert review[0]["request_field_refs"]["history"] == review[1]["request_field_refs"]["history"]
    assert value.bundle.trace_records == before


@pytest.mark.parametrize("with_solver", [True, False])
def test_interrupted_and_abstention_episodes_preserve_raw_response_and_delivery(with_solver):
    value = source(lambda: _finite_fixture(with_solver=with_solver))
    episode = materialize(value)["episodes"][0]
    assert episode["trajectory"]["role_visits"][-1]["interrupted"]
    assert episode["delivered_text"] == value.output_rows["s1"]["text"]
    if not with_solver:
        assert episode["delivered_text"] == ""
        assert episode["trajectory"]["delivery"]["kind"] == "abstention"
    wires = [c["wire_response"] for c in episode["contacts"] if c["wire_response"] is not None]
    assert wires
    assert any('"finish_reason": "length"' in episode["content_pool"][w["body_utf8_ref"]] for w in wires)


def test_group_identity_binds_recording_split_and_round_not_instruction_or_run():
    original = source()
    first = materialize(original)["episodes"][0]
    changed = source()
    changed.plan.run_id = "another-run"
    changed.bundle.trace_records["request-perception-1/request"]["payload"]["task_instruction"] = "Different policy text."
    repeat = materialize(changed)["episodes"][0]
    assert tfgrpo_summary_fields(first)["raw_question"] == tfgrpo_summary_fields(repeat)["raw_question"]
    assert first["content_sha256"] != repeat["content_sha256"]
    changed.bundle.trace_records["request-perception-1/request"]["payload"]["speech_packet_sha256"] = "f"*64
    assert materialize(changed)["episodes"][0]["input_group_sha256"] != first["input_group_sha256"]
    changed = source()
    changed.plan.split_identity_hash = "a"*64
    assert materialize(changed)["episodes"][0]["input_group_sha256"] != first["input_group_sha256"]
    assert materialize_semantic_trajectories(source(), round_id="round-2")["episodes"][0]["input_group_sha256"] != first["input_group_sha256"]


def test_reference_answers_scores_and_posthoc_content_do_not_enter_summary():
    value = source()
    value.bundle.manifest["scores"] = {"reference_answer": "GOLD-SENTINEL", "reward": "OFFLINE-REWARD-SENTINEL"}
    value.phase_results["s1"]["private_annotation"] = "GOLD-SENTINEL"
    value.phase_results["s1"]["native_episode_receipt"]["offline_feedback"] = {"reference_answer": "GOLD-SENTINEL"}
    value.bundle.trace_records["s1/private-feedback"] = {"sample_id": "s1", "gold": "GOLD-SENTINEL"}
    episode = materialize(value)["episodes"][0]
    text = json.dumps(tfgrpo_summary_fields(episode))
    assert "GOLD-SENTINEL" not in text
    assert "OFFLINE-REWARD-SENTINEL" not in text
    assert "reference_answer" not in text


@pytest.mark.parametrize("mutation", ["missing-response", "missing-speech", "evaluation", "empty-round"])
def test_invalid_sources_are_refused_without_partial_output(mutation):
    value = source()
    round_id = "round-1"
    if mutation == "missing-response":
        del value.bundle.trace_records["request-reviewer-2/response"]
    elif mutation == "missing-speech":
        del value.bundle.trace_records["request-perception-1/request"]["payload"]["speech_packet_sha256"]
    elif mutation == "evaluation":
        value.plan.split_role = "confirmatory"
    else:
        round_id = ""
    with pytest.raises(ValueError):
        materialize_semantic_trajectories(value, round_id=round_id)


def test_summary_adapter_rejects_changed_materialization_and_does_not_invent_feedback():
    episode = materialize()["episodes"][0]
    changed = copy.deepcopy(episode)
    changed["delivered_text"] = "Changed after preparation."
    with pytest.raises(SemanticTrajectoryError):
        tfgrpo_summary_fields(changed)
    fields = tfgrpo_summary_fields(episode)
    assert set(fields) == {"raw_question", "trajectories", "correct_answer", "reasoning"}
    assert json.loads(json.loads(fields["trajectories"])[0]["trajectory"]) == episode
