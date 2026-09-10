"""Scientific contrasts preserve both fixed resampling families."""
import pytest
from speech_aware_evidence_acquisition.analysis.score_compare_cli import compare


def test_compare_keeps_scientific_families_and_equal_weighting():
    left = {str(i): {"m": 0.} for i in range(4)}
    right = {str(i): {"m": float(i == 3)} for i in range(4)}
    metadata = {str(i): {"speaker": str(i // 2), "scenario": "a" if i < 3 else "b"} for i in range(4)}
    result = compare(left, right, ids=list(left), metadata=metadata, metric="m", seed=1, n_replicates=20)
    assert result["scenario_stratified"]["delta"] == .25
    assert result["equal_stratum_delta"] == .5
    assert result["speaker_clustered"]["bootstrap"]["ci_level"] == .9


def test_compare_refuses_population_loss():
    with pytest.raises(ValueError):
        compare({"a": {"m": 0.}}, {"b": {"m": 1.}}, ids=["a"], metadata={"a": {}},
                metric="m", seed=1, n_replicates=20)


def test_analysis_verifies_inputs_and_keeps_source_hashes(tmp_path):
    import json
    import hashlib
    from speech_aware_evidence_acquisition.analysis.score_compare_cli import run

    def write(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    inputs = {}
    for name, value in (("left", 0), ("right", 1)):
        manifest = write(name + ".manifest.json", {})
        score = write(name + ".score.json", {"verified": True, "manifest": manifest["path"],
                       "scores": {"standard": {"per_sample": [
                           {"sample_id": sid, "m": value} for sid in ("a", "b")]}}})
        inputs[name] = {"score": score, "manifest": manifest, "scorers": {"official": "standard"}}
    config = {"execution_profile": "model-free-check", "experiment_id": "synthetic",
              "analysis": {
                  "metadata": write("metadata.json", {"rows": {
                      sid: {"speaker": sid, "scenario": sid} for sid in ("a", "b")}}),
                  "full_roster": write("full.json", {"items": [{"id": "a"}, {"id": "b"}]}),
                  "roster": write("primary.json", {"items": [{"id": "a"}]}),
                  "inputs": inputs, "metrics": ["m"], "seed": 1, "n_replicates": 20,
                  "contrasts": [{"name": "right_minus_left", "left": "left", "right": "right",
                                 "scorers": ["official"]}]}}
    path = tmp_path / "config.json"
    write(path.name, config)
    verified = []
    result = run(path, tmp_path / "out.json", verifier=verified.append)
    assert len(verified) == 2
    assert result["populations"] == {"NEW500": 1, "DEV1000": 2, "OLD500": 1}
    assert result["scorer_invocations"] == 0
    assert result["sources"] == inputs
    assert result["results"]["right_minus_left"]["NEW500"]["official"]["m"]["scenario_stratified"]["delta"] == 1
    with pytest.raises(FileExistsError):
        run(path, tmp_path / "out.json", verifier=lambda _: None)
    config["analysis"]["contrasts"][0]["populations"] = ["NEW500"]
    write(path.name, config)
    selected = run(path, tmp_path / "selected.json", verifier=lambda _: None)
    assert set(selected["results"]["right_minus_left"]) == {"NEW500"}
    config["analysis"]["inputs"]["left"]["manifest"] = inputs["right"]["manifest"]
    write(path.name, config)
    with pytest.raises(ValueError, match="identity mismatch"):
        run(path, tmp_path / "bad.json", verifier=lambda _: None)


def test_cli_uses_shared_reader(monkeypatch, tmp_path, capsys):
    from speech_aware_evidence_acquisition.analysis import score_compare_cli as cli
    seen = []
    monkeypatch.setattr(cli, "run", lambda config, output: seen.append((config, output)) or
                        {"experiment_id": "synthetic", "populations": {"NEW500": 2}})
    monkeypatch.setattr("sys.argv", ["score-compare", "--config", str(tmp_path / "config"),
                                    "--output", str(tmp_path / "output")])
    assert cli.main() == 0
    assert seen == [(tmp_path / "config", tmp_path / "output")]
    assert "NEW500" in capsys.readouterr().out


def test_analysis_refuses_model_contact_profile(tmp_path):
    from speech_aware_evidence_acquisition.analysis.score_compare_cli import run
    path = tmp_path / "config.json"
    path.write_text('{"execution_profile":"bounded-discovery-probe"}')
    with pytest.raises(ValueError, match="model-free"):
        run(path, tmp_path / "output")


def test_micro_f1_is_pooled_and_differs_from_mean_per_row(tmp_path):
    import hashlib
    import json
    from speech_aware_evidence_acquisition.analysis.score_compare_cli import run

    def write(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    rows = {
        "left": [{"sample_id": "a", "m": 2 / 11, "tp": 1, "fp": 0, "fn": 9},
                 {"sample_id": "b", "m": 18 / 19, "tp": 9, "fp": 0, "fn": 1}],
        "right": [{"sample_id": "a", "m": 1 / 3, "tp": 2, "fp": 0, "fn": 8},
                  {"sample_id": "b", "m": 18 / 19, "tp": 9, "fp": 0, "fn": 1}],
    }
    inputs = {}
    for name in ("left", "right"):
        manifest = write(name + ".manifest.json", {})
        score = write(name + ".score.json", {
            "verified": True, "manifest": manifest["path"],
            "scores": {"standard": {"per_sample": rows[name]}}
        })
        inputs[name] = {"score": score, "manifest": manifest,
                        "scorers": {"official": "standard"}}
    config = {"execution_profile": "model-free-check", "experiment_id": "micro",
              "analysis": {
                  "metadata": write("metadata.json", {"rows": {
                      "a": {"speaker": "s1", "scenario": "x"},
                      "b": {"speaker": "s2", "scenario": "x"}}}),
                  "full_roster": write("full.json", {"items": [{"id": "a"}, {"id": "b"}]}),
                  "roster": write("primary.json", {"items": [{"id": "a"}, {"id": "b"}]}),
                  "inputs": inputs, "metrics": ["m"],
                  "micro_metrics": {"entity_f1": {"tp": ["tp"], "fp": ["fp"], "fn": ["fn"]}},
                  "seed": 7, "n_replicates": 20,
                  "contrasts": [{"name": "c", "left": "left", "right": "right",
                                 "scorers": ["official"]}]}}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    result = run(path, tmp_path / "out.json", verifier=lambda _: None)
    metrics = result["results"]["c"]["DEV1000"]["official"]
    assert metrics["entity_f1"]["estimand"] == "pooled-count-f1"
    assert metrics["entity_f1"]["scenario_stratified"]["delta_pp"] == pytest.approx(
        100 * (22 / 31 - 20 / 30)
    )
    assert metrics["entity_f1"]["scenario_stratified"]["delta_pp"] != pytest.approx(
        metrics["m"]["scenario_stratified"]["delta"] * 100
    )
    assert metrics["entity_f1"]["scenario_stratified"]["equal_stratum_delta_pp"] == pytest.approx(
        100 * (22 / 31 - 20 / 30)
    )
    assert metrics["entity_f1"]["scenario_stratified"]["ci90_pp"] == (
        metrics["entity_f1"]["speaker_clustered"]["ci90_pp"]
    )
    assert metrics["entity_f1"]["scenario_stratified"]["bootstrap"]["seed"] == 7
    assert metrics["entity_f1"]["speaker_clustered"]["bootstrap"]["seed"] == 7


def test_micro_bootstrap_preserves_repeated_cluster_multiplicity(monkeypatch):
    from speech_aware_evidence_acquisition.analysis import score_compare_cli as cli

    seen = []
    seeds = []
    original = cli.resampled_statistic

    def wrapped(**kwargs):
        seeds.append(kwargs["seed"])
        statistic = kwargs["statistic"]

        def capture(ids):
            seen.append(tuple(ids))
            return statistic(ids)

        kwargs["statistic"] = capture
        return original(**kwargs)

    monkeypatch.setattr(cli, "resampled_statistic", wrapped)
    rows = {
        "a": {"tp": 1, "fp": 0, "fn": 0},
        "b": {"tp": 0, "fp": 1, "fn": 0},
    }
    cli._micro_compare(
        rows, rows, ids=["a", "b"],
        metadata={"a": {"speaker": "s2", "scenario": "x"},
                  "b": {"speaker": "s1", "scenario": "y"}},
         fields=(("tp",), ("fp",), ("fn",)), seed=3, n_replicates=8,
    )
    assert any(ids.count("a") > 1 or ids.count("b") > 1 for ids in seen)
    assert seeds == [3, 3]
    result = cli._micro_compare(
        rows, rows, ids=["a", "b"],
        metadata={"a": {"speaker": "s1", "scenario": "x"},
                  "b": {"speaker": "s1", "scenario": "y"}},
        fields=(("tp",), ("fp",), ("fn",)), seed=3, n_replicates=8,
    )
    assert result["scenario_stratified"]["per_stratum"] == result["speaker_clustered"]["per_stratum"]


def test_micro_fields_reject_duplicates_but_allow_shared_fields():
    from speech_aware_evidence_acquisition.analysis.score_compare_cli import _micro_field_groups

    with pytest.raises(ValueError, match="unique and non-overlapping"):
        _micro_field_groups({"x": {"tp": ["n"], "fp": ["n"], "fn": ["z"]}})
    assert _micro_field_groups({
        "word_f1": {"tp": ["tp"], "fp": ["fp"], "fn": ["fn"]},
        "slu_f1": {"tp": ["tp"], "fp": ["fp"], "fn": ["fn"]},
    })["slu_f1"] == (("tp",), ("fp",), ("fn",))


def test_micro_source_missing_count_refuses():
    from speech_aware_evidence_acquisition.analysis.null_calibration_cli import rows_for

    document = {
        "verified": True,
        "scores": {"s": {"per_sample": [{"sample_id": "a", "tp": 1, "fp": 0}]}}
    }
    with pytest.raises(ValueError, match="missing or has invalid"):
        rows_for(document, "s", ("tp", "fp", "fn"))


def test_rows_for_explicit_view_and_legacy_top_level():
    from speech_aware_evidence_acquisition.analysis.null_calibration_cli import rows_for

    document = {
        "verified": True,
        "scores": {
            "s": {
                "per_sample": [{"sample_id": "a", "tp": 1}],
                "views": {"normalized": {"per_sample": [{"sample_id": "a", "tp": 2}]}}
            }
        },
    }
    assert rows_for(document, "s", ("tp",))["a"]["tp"] == 1
    assert rows_for(document, "s", ("tp",), view="normalized")["a"]["tp"] == 2
    with pytest.raises(ValueError, match="no view"):
        rows_for(document, "s", ("tp",), view="missing")
