"""Prospective cohorts and budgets are metadata, never task-result dependent."""
import pytest
from speech_aware_evidence_acquisition.rails.system_search_protocol import build_protocol, stable_slice
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def rosters():
    return {
        "r01c": [f"slurp:train:r{i}:audio" for i in range(625)],
        "fold_a": [f"slurp:train:a{i}:audio" for i in range(1080)],
        "fold_b": [f"slurp:train:b{i}:audio" for i in range(1080)],
        "dev": [f"slurp:devel:d{i}:audio" for i in range(1000)],
    }


def test_exact_three_round_budget_and_disjoint_hash_order():
    data = rosters()
    p = build_protocol(data)
    assert p["trajectory_cap"] == 16800
    assert p["candidate_opportunities"] == 12
    assert [s["trajectory_cap"] for s in p["stages"]] == [800, 3200, 3200, 3200, 2400, 4000]
    assert stable_slice(data["fold_a"], 0, 400) == stable_slice(list(reversed(data["fold_a"])), 0, 400)
    assert set(p["stages"][1]["sample_ids"]).isdisjoint(p["stages"][2]["sample_ids"])
    assert len(p["stages"][-1]["sample_ids"]) == 1000


def test_recording_variant_leakage_and_short_rosters_refuse():
    r = rosters()
    r["fold_a"][0] = r["r01c"][0].replace(":audio", ":other")
    with pytest.raises(PolicyError, match="utterance"):
        build_protocol(r)
    with pytest.raises(PolicyError):
        stable_slice(["one"], 0, 400)
def test_feedback_cannot_skip_or_mix_registered_rounds():
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.rails.system_search_protocol import require_stage_feedback
    from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
    import pytest
    protocol = {"stages": [{"stage": "initial", "sample_ids": ["slurp:train:1"], "member_slots": ["seed", "seed-aa"]}]}
    value = {"summaries": {"seed": {}, "seed-aa": {}}, "feedback": {"groups": [{"sample_id": "slurp:train:1"}]}}
    feedback = SimpleNamespace(as_json=lambda: value)
    require_stage_feedback(protocol, "initial", feedback)
    value["summaries"].pop("seed-aa")
    with pytest.raises(PolicyError, match="complete preceding family"):
        require_stage_feedback(protocol, "initial", feedback)
    with pytest.raises(PolicyError, match="missing"):
        require_stage_feedback(protocol, "update-3", feedback)
