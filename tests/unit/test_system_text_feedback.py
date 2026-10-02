"""Whole-system numeric feedback and all-member read gating."""
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.reward_links import SLURP_NATIVE_FIELDS
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    CompleteSystemFeedback, feedback_utility, paired_relative_returns, preflight_family,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def counts(**values):
    return dict(dict.fromkeys(SLURP_NATIVE_FIELDS, 0), **values)


def test_utility_penalizes_spurious_entities_and_keeps_empty_zero():
    assert feedback_utility(counts(), .6) == 0
    assert feedback_utility(counts(slu_f1_word_fp=1, slu_f1_char_fp=1), .6) == -1.2
    assert feedback_utility(counts(slu_f1_word_tp=2, slu_f1_char_tp=2), .6) == pytest.approx(3.2)
    assert paired_relative_returns([0, 0]) == [0, 0]
    assert paired_relative_returns([-1, 1]) == [-1, 1]


@pytest.mark.parametrize("reference", [-.1, 1.1, float("nan"), True])
def test_invalid_reference(reference):
    with pytest.raises(PolicyError):
        feedback_utility(counts(), reference)


def test_family_preflight_refuses_missing_member_before_opening_results(tmp_path):
    expected = {"a": "r-a", "b": "r-b"}
    with pytest.raises(PolicyError, match="complete family"):
        preflight_family([{"candidate_id": "a"}], expected)


def test_family_preflight_refuses_test_partition_and_duplicate_scoring(tmp_path):
    def binding(cid):
        run = "r-" + cid
        folder = tmp_path / cid
        folder.mkdir()
        state = folder / "attempt.json"
        state.write_text(json.dumps({"state": "FINALIZED", "run_id": run, "attempt_id": "attempt"}))
        manifest = folder / "run.json"
        manifest.write_text(json.dumps({"status": "COMPLETED", "run_id": run,
            "plan": {"split_role": "discovery"},
            "attempt": {"state_path": str(state), "attempt_id": "attempt"}}))
        roster = folder / "roster.json"
        roster.write_text(json.dumps({"items": [{"sample_id": "slurp:train:1"}]}))
        jobs = folder / "score-jobs.jsonl"
        jobs.write_text(json.dumps({"job_id": "one", "manifest": str(manifest)}) + "\n")
        import hashlib
        def pin(p):
            return {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        return {"candidate_id": cid, "config": {"manifest": pin(manifest), "construction_roster": pin(roster)}}
    bindings = [binding("a"), binding("b")]
    assert len(preflight_family(bindings, {"a": "r-a", "b": "r-b"})) == 2
    jobs = tmp_path / "b" / "score-jobs.jsonl"
    jobs.write_text(jobs.read_text() * 2)
    with pytest.raises(PolicyError, match="one official"):
        preflight_family(bindings, {"a": "r-a", "b": "r-b"})
    jobs.write_text(jobs.read_text().splitlines()[0] + "\n")
    roster = Path(bindings[1]["config"]["construction_roster"]["path"])
    roster.write_text('{"items":[{"sample_id":"slurp:test:1"}]}')
    import hashlib
    bindings[1]["config"]["construction_roster"]["sha256"] = hashlib.sha256(roster.read_bytes()).hexdigest()
    with pytest.raises(PolicyError, match="TRAIN"):
        preflight_family(bindings, {"a": "r-a", "b": "r-b"})


def test_feedback_cannot_be_constructed_by_unverified_summary():
    assert hasattr(CompleteSystemFeedback, "from_family")


def test_learning_view_recomputes_relative_return_without_blind_scores():
    from speech_aware_evidence_acquisition.rails.system_text_policy import canonical
    d = {"schema": "saea-complete-system-feedback-v1", "family_id": "round1",
         "reference": {"f1": .6}, "summaries": {cid: {} for cid in ("L-parent", "L-child", "B-child")},
         "feedback": {"candidate_ids": ["L-parent", "L-child", "B-child"],
             "sources": [{"candidate_id": cid} for cid in ("L-parent", "L-child", "B-child")],
             "groups": [{"sample_id": "slurp:train:1", "members": [
                 {"candidate_id": "L-parent", "utility": 0, "relative_return": -1},
                 {"candidate_id": "L-child", "utility": 0, "relative_return": -1},
                 {"candidate_id": "B-child", "utility": 20, "relative_return": 2}]}]}}
    view = CompleteSystemFeedback(canonical(d)).learning_view(["L-parent", "L-child"]).as_json()
    assert "B-child" not in json.dumps(view)
    assert all(m["relative_return"] == 0 for m in view["feedback"]["groups"][0]["members"])


def test_actual_role_tool_and_terminal_records_determine_cost(tmp_path):
    import hashlib
    from test_native_episode_diagnostics import _fixture
    from speech_aware_evidence_acquisition.rails.system_text_feedback import _row_cost_and_terminal
    _, _, output, trace = _fixture()
    records = []
    for key, value in trace.items():
        channel = "MODEL_REQUEST" if key.endswith("/request") else "MODEL_RESPONSE" if key.endswith("/response") else "USE"
        records.append({"channel": channel, "record_id": key, "payload": value})
    raw_path, out_path = tmp_path / "trace.jsonl", tmp_path / "outputs.jsonl"
    raw_path.write_text("\n".join(json.dumps(r) for r in records))
    out_path.write_text(json.dumps(output) + "\n")
    def pin(p):
        return {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    manifest = {"raw_trace": pin(raw_path), "outputs": pin(out_path)}
    result = _row_cost_and_terminal(manifest)[output["sample_id"]]
    assert result["model_calls"] == 5
    assert result["tool_calls"] == 1
    assert result["role_contacts"]["reviewer"] == 2
    assert result["delivery_kind"] == "accepted"
    assert result["reliable_completion"]
    assert result["prompt_tokens"] is None
    out_path.write_text("{}")
    with pytest.raises(PolicyError, match="terminal bytes"):
        _row_cost_and_terminal(manifest)


def _cost_fixture(tmp_path, mutate=None):
    import hashlib
    from test_native_episode_diagnostics import _fixture
    _, _, output, trace = _fixture()
    records = []
    for key, value in trace.items():
        channel = "MODEL_REQUEST" if key.endswith("/request") else "MODEL_RESPONSE" if key.endswith("/response") else "USE"
        if channel == "MODEL_RESPONSE":
            value["usage"] = {"prompt_tokens": 11, "completion_tokens": 3}
            assert "request_id" not in value  # The production adapter uses record_id.
        records.append({"channel": channel, "record_id": key, "payload": value})
    outputs = [output]
    if mutate:
        mutate(records, outputs)
    def save(name, rows):
        path = tmp_path / name
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return {"raw_trace": save("trace.jsonl", records), "outputs": save("outputs.jsonl", outputs)}, output["sample_id"]


def test_cost_joins_production_response_record_ids_even_out_of_order(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.rails.system_text_feedback import _row_cost_and_terminal
    manifest, sid = _cost_fixture(tmp_path, lambda records, _outputs: records.reverse())
    def refuse_bulk(_path):
        pytest.fail("Complete trace/output files must be streamed.")
    monkeypatch.setattr(Path, "read_bytes", refuse_bulk)
    row = _row_cost_and_terminal(manifest)[sid]
    assert row["model_calls"] == 5
    assert row["prompt_tokens"] == 55 and row["completion_tokens"] == 15
    assert row["missing_model_responses"] == 0
    assert row["tool_events"] == {"attempt": 1, "result": 1, "failed": 0, "rejected": 0}


def test_failed_contacts_remain_counted_and_usage_unknown(tmp_path):
    from speech_aware_evidence_acquisition.rails.system_text_feedback import _row_cost_and_terminal
    def mutate(records, outputs):
        records.append({"channel": "MODEL_REQUEST", "record_id": "failed/request", "payload": {
            "payload": {"request_id": "failed", "sample_id": outputs[0]["sample_id"]}}})
        records.append({"channel": "USE", "record_id": "s1/native-policy/reviewer/tool-failed/failed",
                        "payload": {"use_sample_id": outputs[0]["sample_id"]}})
    manifest, sid = _cost_fixture(tmp_path, mutate)
    row = _row_cost_and_terminal(manifest)[sid]
    assert row["model_calls"] == 6 and row["missing_model_responses"] == 1
    assert row["prompt_tokens"] is None and row["completion_tokens"] is None
    assert row["tool_events"]["failed"] == 1


@pytest.mark.parametrize("kind", ["output", "request", "response"])
def test_duplicate_cost_identity_is_not_silently_collapsed(tmp_path, kind):
    from speech_aware_evidence_acquisition.rails.system_text_feedback import _row_cost_and_terminal
    def mutate(records, outputs):
        if kind == "output":
            outputs.append(outputs[0])
        else:
            records.append(next(r for r in records if r["channel"] == "MODEL_" + kind.upper()))
    manifest, _ = _cost_fixture(tmp_path, mutate)
    with pytest.raises(PolicyError, match="duplicate"):
        _row_cost_and_terminal(manifest)


def test_full_family_pools_official_feedback_and_freezes_reference(monkeypatch, tmp_path):
    import hashlib
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.rails import system_text_feedback as sf
    from speech_aware_evidence_acquisition.core.bundle import verify as bv
    ids = [f"slurp:train:{i}" for i in range(400)]
    bindings, metadata = [], []
    def pin(p):
        return {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    for cid in ("seed", "seed-aa"):
        score = tmp_path / (cid + "-score.json")
        score.write_text(json.dumps({"scores": {"slurp-slu-official-train": {"aggregate": {
            "official": {"slu_f1": .6}, "port_micro": {"intent_accuracy": .8}, "identity_check": {"passed": True}}}}}))
        receipt = tmp_path / (cid + "-receipt.json")
        receipt.write_text(json.dumps({"job_id": cid, "score_result": pin(score)}))
        bindings.append({"candidate_id": cid, "config": {"manifest": {"path": "/fake/" + cid},
            "projection": {"scorer": "slurp-slu-official-train"}, "complete_score_receipt": pin(receipt)}})
        metadata.append(({"split": {"count": 400}}, {"job_id": cid}))
    def grouped(_):
        return {"carrier_lock_key": "slurp", "sources": [{"candidate_id": b["candidate_id"]} for b in bindings],
                "groups": [{"sample_id": sid, "members": [{"candidate_id": cid,
                    "native_counts": counts(slu_f1_word_fp=1)} for cid in ("seed", "seed-aa")]} for sid in ids]}
    monkeypatch.setattr(sf, "preflight_family", lambda *a: metadata)
    monkeypatch.setattr(bv, "verify_bundle", lambda *a: SimpleNamespace(attempt_state="FINALIZED"))
    monkeypatch.setattr(sf, "build_group_relative_feedback", grouped)
    monkeypatch.setattr(sf, "_row_cost_and_terminal", lambda *a: {sid: {"model_calls": 4, "tool_calls": 0,
        "reliable_completion": i % 2 == 0, "abstained": i % 2 != 0} for i, sid in enumerate(ids)})
    feedback = sf.CompleteSystemFeedback.from_family(bindings, expected_members={}, family_id="initial", initial_reference_member="seed")
    d = feedback.as_json()
    assert d["summaries"]["seed"]["model_calls"] == 1600
    assert d["summaries"]["seed"]["reliable_completion_rate"] == .5
    assert d["feedback"]["groups"][0]["members"][0]["utility"] == -.6
    assert d["feedback"]["groups"][0]["members"][0]["relative_return"] == 0
    later = sf.CompleteSystemFeedback.from_family(bindings, expected_members={}, family_id="later", reference=feedback)
    assert later.as_json()["reference"] == d["reference"]
    with pytest.raises(PolicyError, match="freeze"):
        sf.CompleteSystemFeedback.from_family(bindings, expected_members={}, family_id="later", reference={"f1": .7})
    def invalid_seal(*a):
        raise PolicyError("bad seal")
    monkeypatch.setattr(bv, "verify_bundle", invalid_seal)
    monkeypatch.setattr(sf, "build_group_relative_feedback", lambda *a: pytest.fail("read before all seals verified"))
    with pytest.raises(PolicyError, match="bad seal"):
        sf.CompleteSystemFeedback.from_family(bindings, expected_members={}, family_id="initial", initial_reference_member="seed")


def test_search_reader_rejects_tiny_family_before_any_quality(monkeypatch):
    from speech_aware_evidence_acquisition.rails import system_text_feedback as sf
    monkeypatch.setattr(sf, "preflight_family", lambda *a: [({"split": {"count": 20}}, {})])
    monkeypatch.setattr(sf, "build_group_relative_feedback", lambda *a: pytest.fail("tiny quality read"))
    with pytest.raises(PolicyError, match="before any task-result"):
        sf.CompleteSystemFeedback.from_family([], expected_members={}, family_id="initial")
