"""Official synthetic Audio2Tool scores through the shared whole-trajectory reader."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
import test_reward_links as fixtures

from speech_aware_evidence_acquisition.core.roster import read_roster
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.group_relative_feedback import (
    GroupFeedbackError, _native_quality, build_group_relative_feedback,
)
from speech_aware_evidence_acquisition.rails.reward_link_io import build_reward_link_artifact
from speech_aware_evidence_acquisition.rails.reward_links import (
    RewardLinkError, RewardProjection, _score_vector, build_reward_links,
)
from speech_aware_evidence_acquisition.rails.system_text_feedback import preflight_family
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.reproduction.a2t_scorer import score_audio2tool_outputs_official

bundled_repo = fixtures.bundled_repo
completed_source = fixtures.completed_source
IDS = ("tier1_direct:000001", "tier3_multi_intent:000004")
SCORER = "a2t-toolcall-official"


def pin(path):
    return {"path": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}


def projection():
    from speech_aware_evidence_acquisition.rails.reward_links import A2T_NATIVE_FIELDS
    return RewardProjection("synthetic-a2t-official-v1", SCORER,
                            ("samples", "tool_accuracy", "exact_match", "param_f1"), A2T_NATIVE_FIELDS)


@pytest.fixture
def a2t_pair(completed_source, audio2tool_world, tmp_path):
    lock = load_lock(audio2tool_world.lock_path)
    result = []
    for arm in range(2):
        folder = tmp_path / f"a2t-arm-{arm}"
        folder.mkdir()
        answers = {
            IDS[0]: "setLighting()" if arm else "setLighting(deviceId='unmentioned')",
            IDS[1]: "setSecurityMode(mode='Armed_Away', level=2) calibrateThermostat()",
        }
        path, ref, roster, proj, _ = fixtures._slurp_source(
            completed_source, folder, "native", carrier="audio2tool", sample_ids=IDS,
            scorer=SCORER, run_id=f"SAEA-SYNTHETIC-A2T-REWARD-{arm}",
            response_text=lambda sid, _phase, _iteration: answers[sid],
            score_function=lambda outputs: score_audio2tool_outputs_official(
                outputs, lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root),
        )
        config = {
            "schema": "saea-reward-link-artifact-config-v1", "manifest": pin(path),
            "complete_score_receipt": {**pin(ref.path), "cell_id": ref.cell_id},
            "construction_roster": pin(roster), "projection": proj.as_json(),
        }
        result.append((path, ref, roster, proj, config))
    return result


def test_official_scores_join_full_native_trajectories_without_answer_targets(a2t_pair):
    bindings = []
    original = {}
    for i, (path, ref, roster, proj, config) in enumerate(a2t_pair):
        for source in (path, ref.path, roster, path.parent / "score.json"):
            original[source] = source.read_bytes()
        links = build_reward_links(path, ref, roster, proj)
        assert len(links) == 2
        assert all(link.carrier_lock_key == "audio2tool" for link in links)
        assert all({e["axis"] for e in link.provenance["ordered_events"]}
                   >= {"MODEL_REQUEST", "MODEL_RESPONSE", "ORG", "USE"} for link in links)
        serialized = json.dumps([link.as_json() for link in links])
        assert "gold_tool" not in serialized and "setSecurityMode" not in serialized
        artifact = build_reward_link_artifact(config, path.parent / "reward-links.json")
        bindings.append({"candidate_id": f"candidate-{i}", "config": config, "artifact": artifact})
    grouped = build_group_relative_feedback(bindings)
    single = next(g for g in grouped["groups"] if g["sample_id"] == IDS[0])
    before, after = single["members"]
    assert before["native_counts"]["tool_correct"] == after["native_counts"]["tool_correct"] == 1
    assert before["native_counts"]["param_gold_keys"] == 0
    assert before["native_counts"]["param_predicted_keys"] == 1
    assert before["quality"]["exact_match"]["advantage"] == -1
    assert after["quality"]["exact_match"]["advantage"] == 1
    assert after["quality"]["tool_correct"]["advantage"] == 0
    assert "multi_tool_f1" not in after["quality"]
    multi = next(g for g in grouped["groups"] if g["sample_id"] == IDS[1])
    assert multi["members"][0]["native_counts"]["num_expected_tools"] == 3
    assert "multi_tool_f1" in multi["members"][0]["quality"]
    assert grouped["scalar_reward"] is None and grouped["cost_penalty"] is None
    assert all(p.read_bytes() == raw for p, raw in original.items())


@pytest.mark.parametrize("field", ["gold_tool", "predicted_tool", "tier", "official_call_matches", "latency"])
def test_projection_rejects_answer_strings_and_nonquality_diagnostics(field):
    p = projection()
    with pytest.raises(RewardLinkError, match="non-native"):
        RewardProjection("bad", SCORER, p.aggregate_fields, (*p.per_sample_fields, field))


def test_projection_requires_primary_parameter_and_multi_tool_fields():
    p = projection()
    for omitted in ("tool_correct", "param_predicted_keys", "is_multi_tool", "num_expected_tools"):
        with pytest.raises(RewardLinkError, match="omits"):
            RewardProjection("lossy", SCORER, p.aggregate_fields,
                             tuple(f for f in p.per_sample_fields if f != omitted))
    for wrong in ("a2t-toolcall", "a2t-toolcall-v2"):
        with pytest.raises(RewardLinkError, match="registered native"):
            RewardProjection("wrong-protocol", wrong, p.aggregate_fields, p.per_sample_fields)


@pytest.mark.parametrize("field,value", [
    ("tool_correct", .5), ("parsed", "true"), ("param_precision", 1.1),
    ("param_f1", True), ("param_recall", float("nan")),
    ("param_gold_keys", -1), ("param_predicted_keys", 1.5),
    ("param_correct_keys", True), ("num_expected_tools", 0),
    ("param_correct_keys", 2), ("is_multi_tool", True), ("exact_match", True),
])
def test_native_numeric_projection_rejects_invalid_types_and_domains(a2t_pair, tmp_path, field, value):
    document = json.loads((a2t_pair[0][0].parent / "score.json").read_text())
    document["scores"][SCORER]["per_sample"][0][field] = value
    path = tmp_path / "invalid-score.json"
    path.write_text(json.dumps(document))
    with pytest.raises(RewardLinkError):
        _score_vector({"score_result": pin(path)}, projection(), set(IDS))


def test_unparsed_empty_parameters_keep_official_semantics(audio2tool_world, tmp_path):
    path = tmp_path / "unparsed.jsonl"
    path.write_text(json.dumps({"sample_id": IDS[0], "text": "No supported answer."}) + "\n")
    result = score_audio2tool_outputs_official(path, load_lock(audio2tool_world.lock_path),
        audio2tool_world.data_root, repo_root=audio2tool_world.repo_root)
    score = tmp_path / "score.json"
    score.write_text(json.dumps({"scores": {SCORER: result}}))
    vector, _ = _score_vector({"score_result": pin(score)}, projection(), {IDS[0]})
    quality = _native_quality("audio2tool", vector["per_sample"][IDS[0]])
    assert quality["tool_correct"] == quality["exact_match"] == quality["parsed"] == 0
    assert quality["param_f1"] == 1  # Official empty/empty convention, not invented failure credit.


def test_no_evaluation_or_cross_carrier_source_is_relabelled_as_construction(a2t_pair):
    path, ref, roster, proj, _ = a2t_pair[0]
    document = read_roster(roster)
    document["roster_role"] = "evaluation"
    roster.write_text(json.dumps(document))
    with pytest.raises(RewardLinkError, match="construction"):
        build_reward_links(path, ref, roster, proj)


def test_audio2tool_requires_discovery_and_its_own_official_projection(a2t_pair):
    path, ref, roster, proj, _ = a2t_pair[0]
    wrong = RewardProjection("wrong-native", "asr-wer", ("mean_wer",),
                            ("wer", "hits", "substitutions", "deletions", "insertions"))
    with pytest.raises(RewardLinkError, match="official scorer and discovery"):
        build_reward_links(path, ref, roster, wrong)
    document = read_roster(roster)
    document["split_role"] = "final-report"
    roster.write_text(json.dumps(document))
    with pytest.raises(RewardLinkError, match="official scorer and discovery"):
        build_reward_links(path, ref, roster, proj)


@pytest.mark.parametrize("carrier", ["earnings21-original", "earnings22-original"])
def test_existing_earnings_feedback_remains_native_and_unscalarized(carrier):
    counts = {"wer": 1.5, "hits": 0, "substitutions": 1, "deletions": 1, "insertions": 1}
    assert _native_quality(carrier, counts) == {"negative_wer": -1.5}


def test_shared_support_does_not_expand_slurp_search_read_authority(a2t_pair):
    bindings = [{"candidate_id": f"candidate-{i}", "config": item[4]} for i, item in enumerate(a2t_pair)]
    expected = {b["candidate_id"]: json.loads(Path(b["config"]["manifest"]["path"]).read_text())["run_id"]
                for b in bindings}
    with pytest.raises(PolicyError, match="TRAIN"):
        preflight_family(bindings, expected)


def test_rehashed_native_vector_cannot_drop_or_falsify_required_quality(a2t_pair):
    path, ref, roster, proj, _ = a2t_pair[0]
    link = build_reward_links(path, ref, roster, proj)[0]
    counts = copy.deepcopy(link.native_score_vector["per_sample"][link.source.source_sample_id])
    for change in (lambda c: c.pop("is_multi_tool"), lambda c: c.update(tool_correct=2)):
        bad = copy.deepcopy(counts)
        change(bad)
        with pytest.raises(GroupFeedbackError):
            _native_quality("audio2tool", bad)
