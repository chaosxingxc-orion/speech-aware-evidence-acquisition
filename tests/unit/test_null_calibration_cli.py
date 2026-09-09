"""Config/receipt integration tests over synthetic already-scored rows."""

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.analysis.null_calibration_cli import (
    run,
    rows_for,
)


def write(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def calibration_config(tmp_path):
    metadata = write(
        tmp_path / "metadata.json",
        {
            "rows": {
                "a": {"speaker": "s1", "scenario": "x"},
                "b": {"speaker": "s2", "scenario": "y"},
            }
        },
    )
    roster = write(tmp_path / "roster.json", {"items": [{"id": "a"}, {"id": "b"}]})
    jobs = []
    for name, values in (("left", [0, 1]), ("right", [1, 1])):
        manifest = tmp_path / (name + ".manifest.json")
        write(manifest, {"source": name})
        result = write(
            tmp_path / (name + ".score.json"),
            {
                "verified": True,
                "manifest": str(manifest),
                "scores": {
                    "standard": {
                        "per_sample": [
                            {
                                "sample_id": sid,
                                "m": value,
                                "tp": value,
                                "fp": 1 - value,
                                "fn": 1 - value,
                            }
                            for sid, value in zip(("a", "b"), values)
                        ]
                    }
                },
            },
        )
        jobs.append(
            {
                "job_id": name,
                "status": "succeeded",
                "manifest": str(manifest),
                "result_file": name + ".score.json",
                "result_sha256": result["sha256"],
            }
        )
    write(tmp_path / "batch-summary.json", {"failed": 0, "jobs": jobs})
    config = {
        "execution_profile": "model-free-check",
        "experiment_id": "synthetic-calibration",
        "analysis": {
            "metadata": metadata,
            "roster": roster,
            "full_roster": roster,
            "score_batch": str(tmp_path),
            "left_job": "left",
            "right_job": "right",
            "scorers": ["standard"],
            "metrics": ["m"],
            "micro_metrics": {"micro": [["tp"], ["fp"], ["fn"]]},
            "seed": 123,
            "n_replicates": 20,
        },
    }
    path = tmp_path / "config.json"
    write(path, config)
    return path


def test_verified_read_records_provenance_and_refuses_overwrite(
    calibration_config, tmp_path
):
    verified = []
    result = run(calibration_config, tmp_path / "out", verifier=verified.append)
    assert len(verified) == 2
    assert result["results"]["standard"]["metrics"]["m"]["delta_pp"] == 50
    assert result["model_calls"] == result["scorer_invocations"] == 0
    assert len(result["sources"]) == 2
    with pytest.raises(FileExistsError):
        run(calibration_config, tmp_path / "out", verifier=lambda _: None)


def test_tampered_score_refuses_before_manifest_read(calibration_config, tmp_path):
    (tmp_path / "left.score.json").write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        run(
            calibration_config,
            tmp_path / "out",
            verifier=lambda _: pytest.fail("must not verify"),
        )
    assert not (tmp_path / "out").exists()


def test_missing_population_member_refuses(calibration_config, tmp_path):
    config = json.loads(calibration_config.read_text())
    config["analysis"]["roster"] = write(
        tmp_path / "extra.json", {"items": [{"id": "missing"}]}
    )
    write(calibration_config, config)
    with pytest.raises(ValueError, match="roster"):
        run(calibration_config, tmp_path / "out", verifier=lambda _: None)


@pytest.mark.parametrize("change", ["failed", "duplicate", "manifest", "profile"])
def test_invalid_binding_refuses(calibration_config, tmp_path, change):
    config = json.loads(calibration_config.read_text())
    batch = json.loads((tmp_path / "batch-summary.json").read_text())
    if change == "failed":
        batch["failed"] = 1
    if change == "duplicate":
        batch["jobs"].append(batch["jobs"][0])
    if change == "manifest":
        batch["jobs"][0]["manifest"] = "other"
    if change == "profile":
        config["execution_profile"] = "bounded-discovery-probe"
    write(calibration_config, config)
    write(tmp_path / "batch-summary.json", batch)
    with pytest.raises(ValueError):
        run(calibration_config, tmp_path / "out", verifier=lambda _: None)


def test_normalized_rows_and_duplicate_refusal():
    document = {
        "verified": True,
        "scores": {
            "s": {
                "per_sample": [{"sample_id": "a", "m": 0.0, "normalized": {"m": 1.0}}]
            }
        },
    }
    assert rows_for(document, "s", ("m",))["a"]["m"] == 1
    document["scores"]["s"]["per_sample"] *= 2
    with pytest.raises(ValueError):
        rows_for(document, "s", ("m",))


def test_rows_for_consumes_finalization_retained_statistics():
    from speech_aware_evidence_acquisition.analysis.null_calibration_cli import rows_for
    statistics = {"official": {"per_sample": [{"sample_id": "s", "f1": 0.5}]}}
    inline = {"verified": True, "scores": statistics}
    finalized = {"verified": True, "scores": "/sealed/run.scores.json", "score_details": statistics}
    assert rows_for(inline, "official", ("f1",)) == rows_for(finalized, "official", ("f1",))


def test_rows_for_does_not_treat_a_score_path_as_statistics():
    from speech_aware_evidence_acquisition.analysis.null_calibration_cli import rows_for
    with pytest.raises(ValueError, match="retained per-sample"):
        rows_for({"verified": True, "scores": "/sealed/run.scores.json"}, "official", ("f1",))
