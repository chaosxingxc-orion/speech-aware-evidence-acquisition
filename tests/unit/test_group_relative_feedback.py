"""Native group-relative feedback tests; all source bundles are synthetic."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
import test_reward_links as fixtures

from speech_aware_evidence_acquisition.core.bundle.verify import verify_bundle
from speech_aware_evidence_acquisition.core.scoring_receipt import (
    capture_score_source, write_complete_score_receipt,
)
from speech_aware_evidence_acquisition.rails.group_relative_feedback import (
    GroupFeedbackError, _advantages, _native_quality, build_group_relative_feedback,
    prepare_group_relative_feedback,
)
from speech_aware_evidence_acquisition.rails.reward_link_io import build_reward_link_artifact
from speech_aware_evidence_acquisition.rails.reward_links import SLURP_NATIVE_FIELDS

pytest_plugins = ("test_bundle",)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_group_centering_preserves_conflicting_quality_dimensions():
    result = _advantages([{"intent": 1.0, "entity": 0.2},
                          {"intent": 0.0, "entity": 0.8}])
    assert result[0]["intent"] == {"value": 1.0, "mean": 0.5, "std": 0.5,
                                   "centered": 0.5, "advantage": 1.0}
    assert result[0]["entity"]["advantage"] == pytest.approx(-1)
    assert result[1]["entity"]["advantage"] == pytest.approx(1)


def test_equal_rewards_have_zero_advantage_without_nan():
    result = _advantages([{"quality": 0.0}] * 3)
    assert all(row["quality"]["advantage"] == 0.0 for row in result)


def test_native_slurp_count_reward_is_not_row_mean_or_cohort_micro():
    counts = {name: 0.0 for name in SLURP_NATIVE_FIELDS}
    counts.update(scenario_action_exact=1, scenario_exact=1, action_exact=1,
                  slu_f1_word_tp=2, slu_f1_word_fp=1, slu_f1_char_tp=1,
                  slu_f1_char_fn=3)
    quality = _native_quality("slurp", counts)
    assert quality["sample_word_char_f1"] == pytest.approx(6 / 10)
    assert quality["scenario_action_exact"] == 1
    assert quality["sample_slu_f1_word"] == pytest.approx(4 / 5)
    assert quality["sample_slu_f1_char"] == pytest.approx(2 / 5)
    assert quality["sample_slot_f1_exact"] == 0
    assert _native_quality("slurp", dict.fromkeys(counts, 0))["sample_word_char_f1"] == 0


def test_native_asr_direction_preserves_insertion_penalty_in_wer_only():
    quality = _native_quality("earnings21-original",
                              {"wer": 1.25, "hits": 0, "substitutions": 0,
                               "deletions": 1, "insertions": 4})
    assert quality == {"negative_wer": -1.25}




def _enrich_trace_with_supplied_evidence_and_failed_contact(manifest_path):
    """Keep a fully verified fixture while exercising real request payload shapes."""
    from speech_aware_evidence_acquisition.contracts import TraceRecord
    from speech_aware_evidence_acquisition.rails.hashing import content_hash

    manifest = json.loads(Path(manifest_path).read_text())
    trace_path = Path(manifest["raw_trace"]["path"])
    documents = [json.loads(line) for line in trace_path.read_text().splitlines() if line]
    inserted_failed = False
    enriched = []
    for row in documents:
        if row["channel"] == "MODEL_REQUEST":
            payload = row["payload"]["payload"]
            request_id = payload["request_id"]
            if request_id.endswith(("-solve", "-revise")):
                sid = payload["sample_id"]
                payload["supplied_evidence"] = [{
                    "content": "independent observation",
                    "knowledge_role": "observation",
                    "evidence_id": "private-evidence:" + sid,
                    "source_uri": "/private/cache/" + sid + ".json",
                }]
                row["payload"]["payload_sha256"] = content_hash(payload)
            if not inserted_failed and request_id.endswith("-plan"):
                failed = copy.deepcopy(row)
                sid = payload["sample_id"]
                failed["record_id"] = "opaque-failed/request"
                failed_payload = failed["payload"]["payload"]
                failed_payload["request_id"] = "opaque-failed"
                failed_payload["history"] = [{
                    "role": "control",
                    "contact_id": "synthetic-program:failed:" + sid,
                    "content": "Inspect the available evidence.",
                }]
                failed["payload"]["payload_sha256"] = content_hash(failed_payload)
                enriched.append(failed)
                inserted_failed = True
        enriched.append(row)
    records = [TraceRecord(row["channel"], row["record_id"], row["payload"]) for row in enriched]
    trace_path.write_text("".join(record.serialize() + "\n" for record in records))
    trace_manifest = Path(manifest["trace_manifest"]["path"])
    trace_manifest.write_text(json.dumps({
        "records": {record.record_id: record.content_hash() for record in records}
    }))
    manifest["raw_trace"]["sha256"] = _sha(trace_path)
    manifest["trace_manifest"]["sha256"] = _sha(trace_manifest)
    request_hashes = {
        row["payload"]["payload"]["request_id"]: row["payload"]["payload_sha256"]
        for row in enriched if row["channel"] == "MODEL_REQUEST"
    }
    outputs_path = Path(manifest["outputs"]["path"])
    outputs = [json.loads(line) for line in outputs_path.read_text().splitlines() if line]
    for row in outputs:
        row["request_sha256"] = request_hashes[row["request_id"]]
    outputs_path.write_text("".join(json.dumps(row) + "\n" for row in outputs))
    manifest["outputs"]["sha256"] = _sha(outputs_path)
    manifest["cost"]["calls_used"] += 1
    Path(manifest_path).write_text(json.dumps(manifest))

def _source_pair(synthetic_world, bundled_repo, tmp_path, *, native=False, native_framework=False):
    base = fixtures.completed_source.__wrapped__(synthetic_world, bundled_repo, tmp_path)
    bindings = []
    for arm in range(2):
        folder = tmp_path / f"arm-{arm}"
        folder.mkdir()
        path, _, roster, projection, _ = fixtures._slurp_source(
            base, folder, "native" if native else "continuous",
            native_framework=native_framework,
        )
        if not native:
            _enrich_trace_with_supplied_evidence_and_failed_contact(path)
        manifest = json.loads(path.read_text())
        run = f"SAEA-SYNTHETIC-GROUP-{arm}"
        manifest["run_id"] = manifest["exposure_run_id"] = run
        manifest["plan"]["run_id"] = run
        manifest["attempt"]["run_id"] = run
        state = Path(manifest["attempt"]["state_path"])
        attempt = json.loads(state.read_text())
        attempt["run_id"] = run
        state.write_text(json.dumps(attempt))
        path.write_text(json.dumps(manifest))
        bundle = verify_bundle(path)
        score_path = path.parent / "score.json"
        score = json.loads(score_path.read_text())
        if arm:
            row = score["scores"][projection.scorer]["per_sample"][0]
            row.update(scenario_action_exact=1, slu_f1_word_tp=4, slu_f1_char_tp=4)
        score_path.write_text(json.dumps(score))
        receipt = write_complete_score_receipt(
            path.parent / "group-score-receipt.json", job_id=f"group-score-{arm}",
            result_path=score_path, source=capture_score_source(bundle),
            verified_bundle=bundle,
        )
        config = {
            "schema": "saea-reward-link-artifact-config-v1",
            "manifest": {"path": str(path), "sha256": _sha(path)},
            "complete_score_receipt": {"path": str(receipt.path),
                                       "sha256": receipt.sha256, "cell_id": receipt.cell_id},
            "construction_roster": {"path": str(roster), "sha256": _sha(roster)},
            "projection": projection.as_json(),
        }
        pin = build_reward_link_artifact(config, path.parent / "reward-links.json")
        bindings.append({"candidate_id": f"candidate-{arm}", "config": config, "artifact": pin})
    return bindings



@pytest.fixture
def source_pair(synthetic_world, bundled_repo, tmp_path):
    return _source_pair(synthetic_world, bundled_repo, tmp_path)


@pytest.fixture
def native_source_pair(synthetic_world, bundled_repo, tmp_path):
    return _source_pair(synthetic_world, bundled_repo, tmp_path, native=True)


@pytest.fixture
def native_training_source_pair(synthetic_world, bundled_repo, tmp_path):
    """Opt-in pair with source-bound framework history for proposal projection."""
    return _source_pair(
        synthetic_world, bundled_repo, tmp_path,
        native=True, native_framework=True,
    )


def test_complete_verified_sources_form_exact_groups_and_preserve_counts(source_pair):
    result = build_group_relative_feedback(source_pair)
    assert len(result["groups"]) == 2
    group = next(row for row in result["groups"] if row["sample_id"] == "slurp:train:1")
    assert group["members"][0]["quality"]["scenario_action_exact"]["advantage"] == -1
    assert group["members"][1]["quality"]["scenario_action_exact"]["advantage"] == 1
    assert group["members"][1]["native_counts"]["slu_f1_word_tp"] == 4
    assert len(group["members"][0]["reward_link_sha256"]) == 64
    assert result["candidate_ids"] == ["candidate-0", "candidate-1"]
    assert result["scalar_reward"] is None
    assert all(s["attempt_state"]["state"] == "FINALIZED" for s in result["sources"])
    assert all(len(s["attempt_state"]["sha256"]) == 64 for s in result["sources"])
    serialized = json.dumps(result)
    assert "synthetic-answer" not in serialized
    assert "reference_text" not in serialized


def test_native_training_pair_preserves_upstream_finalized_reward_custody(
    native_training_source_pair,
):
    result = build_group_relative_feedback(native_training_source_pair)
    assert result["candidate_ids"] == ["candidate-0", "candidate-1"]
    assert all(source["attempt_state"]["state"] == "FINALIZED" for source in result["sources"])


def test_group_artifact_uses_shared_preparation_and_reverifies_warm_sources(source_pair, tmp_path):
    output = tmp_path / "group-feedback.json"
    first = prepare_group_relative_feedback(source_pair, output)
    before = output.read_bytes()
    second = prepare_group_relative_feedback(source_pair, output)
    assert first["sha256"] == second["sha256"]
    assert output.read_bytes() == before
    Path(source_pair[0]["artifact"]["path"]).write_text("{}")
    with pytest.raises(GroupFeedbackError):
        prepare_group_relative_feedback(source_pair, output)


@pytest.mark.parametrize("case", ["one", "duplicate_id", "duplicate_source",
                                   "unknown", "wrong_pin", "rehashed_tamper"])
def test_group_refuses_ineligible_or_changed_sources(source_pair, case):
    bindings = copy.deepcopy(source_pair)
    if case == "one":
        bindings = bindings[:1]
    elif case == "duplicate_id":
        bindings[1]["candidate_id"] = bindings[0]["candidate_id"]
    elif case == "duplicate_source":
        bindings[1] = {**bindings[0], "candidate_id": "another"}
    elif case == "unknown":
        bindings[0]["extra"] = "forbidden"
    elif case == "wrong_pin":
        bindings[0]["artifact"]["sha256"] = "f" * 64
    else:
        p = Path(bindings[0]["artifact"]["path"])
        doc = json.loads(p.read_text())
        doc["links"][0]["native_score_vector"]["aggregate"]["port_micro.samples"] += 1
        p.write_text(json.dumps(doc))
        bindings[0]["artifact"]["sha256"] = _sha(p)
    with pytest.raises(GroupFeedbackError):
        build_group_relative_feedback(bindings)


@pytest.mark.parametrize("values", [
    [{"x": float("nan")}, {"x": 0.0}],
    [{"x": True}, {"x": 0.0}],
    [{"x": 1.0}, {"y": 1.0}],
    [{"x": 1.0}],
])
def test_invalid_group_numbers_or_members_are_rejected(values):
    with pytest.raises(GroupFeedbackError):
        _advantages(values)


@pytest.mark.parametrize("case", ["construction", "projection"])
def test_individually_valid_but_differently_bound_cohorts_cannot_be_grouped(source_pair, case):
    binding = source_pair[1]
    config = binding["config"]
    if case == "construction":
        roster = Path(config["construction_roster"]["path"])
        document = json.loads(roster.read_text())
        document["roster_id"] = "another-construction-purpose"
        roster.write_text(json.dumps(document))
        config["construction_roster"]["sha256"] = _sha(roster)
    else:
        config["projection"]["reward_rule_id"] = "another-reward-projection"
    new_path = Path(binding["artifact"]["path"]).with_name("rebound-links.json")
    binding["artifact"] = build_reward_link_artifact(config, new_path)
    with pytest.raises(GroupFeedbackError, match="construction, projection"):
        build_group_relative_feedback(source_pair)


def test_all_native_sufficient_statistics_survive_feedback(source_pair):
    result = build_group_relative_feedback(source_pair)
    for group in result["groups"]:
        for member in group["members"]:
            assert set(member["native_counts"]) == set(SLURP_NATIVE_FIELDS)
            assert set(member["quality"]) == {
                "scenario_action_exact", "scenario_exact", "action_exact",
                "sample_word_char_f1", "sample_slot_f1_exact",
                "sample_slu_f1_word", "sample_slu_f1_char",
            }
            assert "cost" not in member["quality"]


@pytest.mark.parametrize("carrier,counts", [
    ("audio2tool", {"tool": 1}),
    ("slurp", {"scenario_action_exact": 1}),
    ("earnings21-original", {"wer": 1}),
    ("earnings21-original", {"wer": -1, "hits": 0, "substitutions": 0,
                             "deletions": 0, "insertions": 0}),
    ("slurp", {**dict.fromkeys(SLURP_NATIVE_FIELDS, 0), "scenario_action_exact": 2}),
    ("slurp", {**dict.fromkeys(SLURP_NATIVE_FIELDS, 0), "slu_f1_char_tp": -1}),
])
def test_native_quality_refuses_unavailable_or_invalid_task_projections(carrier, counts):
    with pytest.raises(GroupFeedbackError):
        _native_quality(carrier, counts)
