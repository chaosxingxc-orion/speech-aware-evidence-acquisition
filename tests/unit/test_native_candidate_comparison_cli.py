from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace as NS
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import native_candidate_comparison_cli as cli

POLICY = "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
IDS = tuple(f"slurp:train:{i}:audio" for i in range(4))
LEGAL = frozenset({"weather_query", "audio_volume_up", "general_joke"})


def source():
    outputs = [
        '{"scenario":"weather","action":"query","entities":[]}',
        '{"scenario":"audio","action":"volume_up","entities":[]}',
        "",
        "invalid answer",
    ]
    return NS(
        sample_ids=IDS,
        output_rows={sid: {"sample_id": sid, "text": text}
                     for sid, text in zip(IDS, outputs, strict=True)},
        composed=NS(values={
            "phase_material": {"perception": {"fill_params": {"max_candidates": 3}}},
            "knowledge_stores": {"slots": {
                "candidate_supply": {"solver": {"projection_policy": POLICY}}
            }},
        }),
    )


def projection(monkeypatch):
    pairs = [
        NS(sample_id=IDS[0], c0=NS(candidate_ids=("weather_query",)), c1=None),
        NS(sample_id=IDS[1], c0=NS(candidate_ids=("general_joke",)), c1=None),
        NS(sample_id=IDS[2], c0=None, c1=None),
        NS(sample_id=IDS[3], c0=NS(candidate_ids=("weather_query",)), c1=None),
    ]
    monkeypatch.setattr(cli, "project_verified_native_candidate_stages",
                        lambda *a, **kw: tuple(pairs))
    return pairs


def references():
    return tuple(NS(sample_id=sid, scenario="weather", action="query",
                    intent="weather_query") for sid in IDS)


def saved_scores():
    return tuple({"sample_id": sid, "scenario_action_exact": int(i == 0)}
                 for i, sid in enumerate(IDS))


def test_projection_retains_unavailable_and_invalid_final_rows(monkeypatch):
    projection(monkeypatch)
    rows = cli.project_candidate_decision_rows(
        source(), reference_records=references(),
        official_rows=saved_scores(), legal_ids=LEGAL,
        projection_policy=POLICY,
    )
    assert [row["sample_id"] for row in rows] == list(IDS)
    assert rows[0]["gold_covered"] is True
    assert rows[0]["final_correct"] is True
    assert rows[0]["final_in_candidates"] is True
    assert rows[1]["gold_covered"] is False
    assert rows[1]["final_in_candidates"] is False
    assert rows[2] == {
        "sample_id": IDS[2], "candidate_available": False,
        "candidate_width": None, "gold_covered": False,
        "final_correct": False, "final_in_candidates": None,
    }
    assert rows[3]["candidate_available"] is True
    assert rows[3]["final_in_candidates"] is None
    assert "weather_query" not in json.dumps(rows)


def test_correct_outside_candidates_is_not_dropped(monkeypatch):
    pairs = projection(monkeypatch)
    pairs[0].c0 = NS(candidate_ids=("general_joke",))
    rows = cli.project_candidate_decision_rows(
        source(), reference_records=references(),
        official_rows=saved_scores(), legal_ids=LEGAL,
        projection_policy=POLICY,
    )
    assert rows[0]["gold_covered"] is False
    assert rows[0]["final_correct"] is True
    assert rows[0]["final_in_candidates"] is False


@pytest.mark.parametrize("mutation", ["score", "reference_order", "stage_order", "missing_output"])
def test_projection_rejects_inconsistent_source_joins(monkeypatch, mutation):
    pairs = projection(monkeypatch)
    refs, scores, src = references(), list(saved_scores()), source()
    if mutation == "score":
        scores[0]["scenario_action_exact"] = 0
    elif mutation == "reference_order":
        refs = refs[::-1]
    elif mutation == "stage_order":
        pairs.reverse()
    else:
        del src.output_rows[IDS[-1]]
    with pytest.raises(cli.NativeCandidateComparisonError):
        cli.project_candidate_decision_rows(
            src, reference_records=refs, official_rows=scores,
            legal_ids=LEGAL, projection_policy=POLICY,
        )


def test_projection_policy_must_match_actual_supply(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("do not project against a different policy")
    monkeypatch.setattr(cli, "project_verified_native_candidate_stages", forbidden)
    with pytest.raises(cli.NativeCandidateComparisonError, match="projection"):
        cli.project_candidate_decision_rows(
            source(), reference_records=references(), official_rows=saved_scores(),
            legal_ids=LEGAL, projection_policy="invented",
        )


def pin(path, value):
    path.write_text(json.dumps(value))
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def test_release_mismatch_rejects_before_source_or_reference_reads(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("unreleased source must not be read")
    monkeypatch.setattr(cli, "verify_native_episode_source", forbidden)
    monkeypatch.setattr(cli, "load_verified_slurp_reference_records", forbidden)
    release = pin(tmp_path / "release.json", {
        "schema": cli.RELEASE_SCHEMA,
        "status": "COMPLETE_SOURCES_RELEASED_FOR_REGISTERED_ANALYSIS",
        "manifests": {"left": {"path": "/wrong", "sha256": "b" * 64},
                      "right": {"path": "/right", "sha256": "c" * 64}},
    })
    cfg = {
        "schema": cli.CONFIG_SCHEMA, "execution_profile": "model-free-check",
        "quality_release": release,
        "arms": {
            side: {"manifest": {"path": f"/{side}", "sha256": char * 64},
                   "phase_artifact": {"path": f"/{side}.phases", "sha256": "d" * 64},
                   "source_repo_root": "/source", "projection_policy": POLICY,
                   "complete_score_receipt": {"path": "/score", "sha256": "e" * 64}}
            for side, char in (("left", "a"), ("right", "c"))
        },
        "reference_source": {}, "metadata": {"path": "/metadata", "sha256": "f" * 64},
        "bootstrap": {"seed": 3, "n_replicates": 10, "ci_level": 0.9},
    }
    cfgpin = pin(tmp_path / "config.json", cfg)
    with pytest.raises(cli.NativeCandidateComparisonError, match="release"):
        cli.run(
            Path(cfgpin["path"]), expected_config_sha256=cfgpin["sha256"],
            output_path=tmp_path / "out.json",
        )
    assert not (tmp_path / "out.json").exists()


def test_partial_manifest_is_rejected_before_bundle_or_reference_reads(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("partial source must not be consumed")
    monkeypatch.setattr(cli, "verify_native_episode_source", forbidden)
    monkeypatch.setattr(cli, "load_verified_slurp_reference_records", forbidden)
    manifest = pin(tmp_path / "manifest.json", {"status": "RUNNING"})
    with pytest.raises(cli.NativeCandidateComparisonError, match="complete manifests"):
        cli._load_arm({"manifest": manifest}, {})


def complete_fixture(tmp_path, monkeypatch):
    projection(monkeypatch)
    src = source()
    src.plan = NS(
        carrier_lock_key="slurp", split_role="discovery", attempt_id="attempt",
        run_id="run", protocol_hash="a" * 64, split_identity_hash="b" * 64,
    )
    src.composed.config_hash = "c" * 64
    src.bundle = object()
    scorepin = pin(tmp_path / "score.json", {
        "scores": {"slurp-slu-official-train": {"per_sample": list(saved_scores())}},
    })
    def source_verifier(**kwargs):
        return src
    def receipt_verifier(receipt_ref, bundle):
        assert bundle is src.bundle
        assert receipt_ref.cell_id == "attempt"
        return {"score_result": scorepin}
    monkeypatch.setattr(cli, "verify_native_episode_source", source_verifier)
    monkeypatch.setattr(cli, "verify_complete_score_receipt", receipt_verifier)
    monkeypatch.setattr(cli, "load_verified_slurp_reference_records",
                        lambda *a, **kw: references())
    monkeypatch.setattr(cli, "load_authoritative_slurp_candidate_ids",
                        lambda *a, **kw: LEGAL)
    manifests = {
        side: pin(tmp_path / f"{side}.json", {"status": "COMPLETED", "arm": side})
        for side in ("left", "right")
    }
    release = pin(tmp_path / "release.json", {
        "schema": cli.RELEASE_SCHEMA,
        "status": "COMPLETE_SOURCES_RELEASED_FOR_REGISTERED_ANALYSIS",
        "manifests": manifests,
    })
    metadata = pin(tmp_path / "metadata.json", {"rows": [
        {"sample_id": sid, "scenario": "weather" if i < 2 else "audio",
         "speaker": f"speaker-{i % 2}"}
        for i, sid in enumerate(IDS)
    ]})
    cfg = {
        "schema": cli.CONFIG_SCHEMA, "execution_profile": "model-free-check",
        "quality_release": release,
        "arms": {
            side: {"manifest": manifests[side],
                   "phase_artifact": {"path": "/phases", "sha256": "d" * 64},
                   "source_repo_root": "/source", "projection_policy": POLICY,
                   "complete_score_receipt": {"path": "/receipt", "sha256": "e" * 64}}
            for side in ("left", "right")
        },
        "reference_source": {"source_scope": "synthetic"},
        "metadata": metadata,
        "bootstrap": {"seed": 3, "n_replicates": 10, "ci_level": 0.9},
    }
    return src, cfg


def test_shared_pipeline_persists_all_rows_and_clustered_ratio_diagnostics(tmp_path, monkeypatch):
    _, cfg = complete_fixture(tmp_path, monkeypatch)
    cfgpin = pin(tmp_path / "config.json", cfg)
    out = tmp_path / "comparison.json"
    cli.run(Path(cfgpin["path"]), expected_config_sha256=cfgpin["sha256"], output_path=out)
    envelope = json.loads(out.read_text())
    assert envelope["contact_class"] == "model-free"
    document = envelope["output"]
    assert envelope["output_sha256"] == cli.content_hash(document)
    comparison = document["comparison"]
    assert comparison["roster_count"] == 4
    assert set(comparison["ratio_rows"]["left"]) == set(IDS)
    full = comparison["full_cohort"]["left"]
    assert full["candidate_availability"]["unavailable"] == 1
    assert full["candidate_width"]["histogram"] == {"1": 3}
    assert full["final_membership"]["outside_candidates"] == 1
    assert full["final_membership"]["unavailable_or_invalid"] == 2
    assert full["coverage"] == {"numerator": 2, "denominator": 4, "ratio": 0.5}
    assert full["common_covered_final_accuracy"]["denominator"] == 2
    assert set(comparison["by_scenario"]) == {"audio", "weather"}
    assert document["bootstrap"]["grouping_resampling"] == "whole-cluster"
    assert document["bootstrap"]["cluster_field"] == "speaker"
    assert document["semantics"]["new_model_tool_scorer_contacts"] == 0
    uncertainty = document["uncertainty"]["coverage"]
    assert uncertainty["natural_mixture"]["gain_pp"] == 0.0
    assert uncertainty["groupings"]["scenario"]["equal_stratum"]["gain_pp"] == 0.0
    assert uncertainty["natural_mixture"]["bootstrap"]["n_replicates"] == 10
    assert "weather_query" not in out.read_text()
    assert "invalid answer" not in out.read_text()


@pytest.mark.parametrize("problem", ["wrong_score", "duplicate_metadata", "confirmatory", "wrong_ids"])
def test_complete_pipeline_rejects_bad_bindings(tmp_path, monkeypatch, problem):
    src, cfg = complete_fixture(tmp_path, monkeypatch)
    if problem == "wrong_score":
        score_path = tmp_path / "score.json"
        doc = json.loads(score_path.read_text())
        doc["scores"]["slurp-slu-official-train"]["per_sample"][0]["scenario_action_exact"] = 0
        updated = pin(score_path, doc)
        monkeypatch.setattr(cli, "verify_complete_score_receipt",
                            lambda *a, **kw: {"score_result": updated})
    elif problem == "duplicate_metadata":
        meta_path = Path(cfg["metadata"]["path"])
        doc = json.loads(meta_path.read_text())
        doc["rows"][-1] = doc["rows"][0]
        cfg["metadata"] = pin(meta_path, doc)
    elif problem == "confirmatory":
        src.plan.split_role = "confirmatory"
    else:
        rows = list(saved_scores())
        rows[-1]["sample_id"] = "foreign"
        updated = pin(tmp_path / "score.json", {
            "scores": {"slurp-slu-official-train": {"per_sample": rows}},
        })
        monkeypatch.setattr(cli, "verify_complete_score_receipt",
                            lambda *a, **kw: {"score_result": updated})
    cfgpin = pin(tmp_path / "config.json", cfg)
    out = tmp_path / "comparison.json"
    with pytest.raises(cli.NativeCandidateComparisonError):
        cli.run(Path(cfgpin["path"]), expected_config_sha256=cfgpin["sha256"], output_path=out)
    assert not out.exists()
