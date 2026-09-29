"""Row-state extraction on synthetic sealed pools (no real utterances).

Covers both pool kinds the design spec names (single-sample-arm, grouped-multi-
sample), and the item-state classification (note_state / gold_item_states /
entity_items) the shared ``entity_states`` module now carries.
"""

from __future__ import annotations

import json

from speech_aware_evidence_acquisition.analysis.sealed_credit import row_states as rs
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity


class FakeGold:
    def __init__(self, intent, entities):
        self.intent = intent
        self.entities = entities


def _write_phases(path, results):
    path.write_text(json.dumps({
        "schema": "saea-flight-phase-summaries-v1",
        "phases": [{"results": results}],
    }), encoding="utf-8")


def _perception_state(candidate_ids, distinctions=None):
    distinctions = distinctions or ["" for _ in candidate_ids]
    payload = {"candidates": [
        {"intent_id": cid, "distinction": dist, "unresolved_fields": []}
        for cid, dist in zip(candidate_ids, distinctions)
    ]}
    return {"state_kind": "phase:perception", "content": json.dumps(payload)}


def _solver_state(text):
    return {"state_kind": "phase:solver", "content": text}


def _slu_text(intent, entities):
    scenario, action = intent.split("_", 1)
    return json.dumps({
        "scenario": scenario, "action": action,
        "entities": [{"type": e.type, "filler": e.filler} for e in entities],
    })


def _write_scores(path, run_id, per_sample):
    path.write_text(json.dumps({
        "cost": {},
        "slurp-slu-official-train": {"aggregate": {}, "per_sample": per_sample},
    }), encoding="utf-8")


def _write_outputs(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def test_single_sample_arm_row_state(tmp_path):
    sid = "slurp:train:000001:audio-1"
    boundary = [f"intent-boundaries::intent-boundary:{i}" for i in ("weather_query", "alarm_set", "calendar_query")]
    result = {
        "sample_id": sid,
        "initial_query_state": {"retrieved_value_ids": boundary},
        "agent_states": [
            _perception_state(["alarm_set", "weather_query"]),
            _solver_state(_slu_text("alarm_set", [SlotEntity("time", "five pm")])),
            {"state_kind": "phase:reviewer", "content": "revise"},
            _solver_state(_slu_text("weather_query", [SlotEntity("time", "five pm")])),
        ],
        "native_episode_receipt": {
            "planner_routes": [{"action": "REVISE"}],
            "deliver_normaliser": {"changed": True, "labels_changed": False},
        },
    }
    _write_phases(tmp_path / "RUN.phases.json", [result])
    _write_scores(tmp_path / "RUN.scores.json", "RUN", [{
        "sample_id": sid, "scenario_action_exact": 1.0, "slu_f1_f1": 1.0,
        "slu_f1_word_tp": 1.0, "slu_f1_word_fp": 0.0, "slu_f1_word_fn": 0.0,
        "slu_f1_char_tp": 1.0, "slu_f1_char_fp": 0.0, "slu_f1_char_fn": 0.0,
    }])
    _write_outputs(tmp_path / "RUN.outputs.jsonl", [
        {"sample_id": sid, "text": _slu_text("weather_query", [SlotEntity("time", "five pm")])},
    ])

    phases = rs.load_phases(tmp_path, "RUN")
    scores = rs.load_scores(tmp_path, "RUN", "slurp-slu-official-train")
    outputs = rs.load_outputs(tmp_path, "RUN")
    gold = {sid: FakeGold("weather_query", (SlotEntity("time", "five pm"),))}
    derived = rs.derive_rows("single-sample-arm", gold, phases["rows"], scores["rows"], outputs["rows"], [sid])

    row = derived["rows"][sid]
    assert row["block_pos"] == 1  # weather_query is boundary[0]
    assert row["perc_rank"] == 2  # weather_query is perc[1]
    assert row["perc_rank_bucket"] == "2"
    assert row["s1_ok"] is False  # first solver said alarm_set
    assert row["s_last_ok"] is True  # revised solver said weather_query
    assert row["revised"] is True
    assert row["reviewer_visited"] is True
    assert row["normaliser_changed"] is True
    assert row["d_ok"] is True
    assert row["samples_n"] == 2

    assert len(derived["items"]) == 1
    item = derived["items"][0]
    assert item["type"] == "time"
    assert item["d"] == "EXACT"


def test_grouped_multi_sample_row_state(tmp_path):
    sid = "slurp:train:000002:audio-2"
    boundary = [f"intent-boundaries::intent-boundary:{i}" for i in ("alarm_set", "weather_query")]
    result = {
        "sample_id": sid,
        "initial_query_state": {"retrieved_value_ids": boundary},
        "agent_states": [
            _perception_state(["weather_query"]),
            _solver_state(_slu_text("weather_query", [])),
            {"state_kind": "phase:reviewer", "content": "accept"},
            {"state_kind": "phase:planner", "content": "ACCEPT"},
        ],
        "native_episode_receipt": {"planner_routes": [{"action": "ACCEPT"}]},
        "solver_group": {"samples": ["s0", "s1", "s2", "s3", "s4"], "delivered": "s2",
                         "commit_policy_id": "majority-vote-v1", "commit_params": {}},
    }
    _write_phases(tmp_path / "RUN.phases.json", [result])
    _write_scores(tmp_path / "RUN.scores.json", "RUN", [{
        "sample_id": sid, "scenario_action_exact": 1.0, "slu_f1_f1": 1.0,
        "slu_f1_word_tp": 0.0, "slu_f1_word_fp": 0.0, "slu_f1_word_fn": 0.0,
        "slu_f1_char_tp": 0.0, "slu_f1_char_fp": 0.0, "slu_f1_char_fn": 0.0,
    }])
    _write_outputs(tmp_path / "RUN.outputs.jsonl", [
        {"sample_id": sid, "text": _slu_text("weather_query", [])},
    ])

    phases = rs.load_phases(tmp_path, "RUN")
    scores = rs.load_scores(tmp_path, "RUN", "slurp-slu-official-train")
    outputs = rs.load_outputs(tmp_path, "RUN")
    gold = {sid: FakeGold("weather_query", ())}
    derived = rs.derive_rows("grouped-multi-sample", gold, phases["rows"], scores["rows"], outputs["rows"], [sid])

    row = derived["rows"][sid]
    assert row["perc_rank"] == 1
    assert row["d_ok"] is True
    # grouped pools carry no Reviewer/normaliser node (design spec section 2b)
    assert row["reviewer_visited"] is False
    assert row["normaliser_changed"] is None
    assert row["revised"] is False


def test_note_state_and_entity_items_reused_from_entity_states():
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import (
        canonical,
        entity_items,
        gold_item_states,
        note_state,
    )

    gold = (SlotEntity("time", "five pm"),)
    pred_exact = (SlotEntity("time", "five pm"),)
    pred_wrong = (SlotEntity("time", "six pm"),)
    states, _ = gold_item_states(gold, pred_exact)
    assert states == ["EXACT"]
    states, _ = gold_item_states(gold, pred_wrong)
    assert states[0] in ("NEAR", "WRONG-VALUE", "FORMAT", "BOUNDARY")
    perc_tokens = canonical("at five pm today").split()
    assert note_state("five pm", perc_tokens) == "CONTIGUOUS"
    assert note_state("five pm", ["nothing", "here"]) == "ABSENT"
    assert entity_items(gold, pred_exact) == []


def test_extract_pool_reads_phases_from_a_separate_directory(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.analysis.sealed_credit import row_states as rs_mod

    seen = {}
    monkeypatch.setattr(rs_mod, "load_phases", lambda d, r: seen.setdefault("phases", d) and {"rows": {}, "sha256": "0", "relpath": "p"})
    monkeypatch.setattr(rs_mod, "load_scores", lambda d, r, s: seen.setdefault("scores", d) and {"rows": {}, "sha256": "0", "relpath": "s"})
    monkeypatch.setattr(rs_mod, "load_outputs", lambda d, r: seen.setdefault("outputs", d) and {"rows": {}, "sha256": "0", "relpath": "o"})
    pool = {"label": "x", "run_id": "R", "kind": "single-sample-arm", "roster": "F", "use": "tuning", "scorer": "s"}
    out = rs_mod.extract_pool(pool, tmp_path, {}, tmp_path / "seal-only", tmp_path / "generation")
    assert seen == {"phases": tmp_path / "generation", "scores": tmp_path / "seal-only", "outputs": tmp_path / "seal-only"}
    assert out["row_count"] == 0
