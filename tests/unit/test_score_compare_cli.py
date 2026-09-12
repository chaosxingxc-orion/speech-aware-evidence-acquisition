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


def test_default_analysis_finalized_scores_match_legacy_statistics(tmp_path, monkeypatch):
    import hashlib
    import json
    from pathlib import Path
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.analysis import score_compare_cli as cli

    def write(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    metadata = write("metadata.json", {"rows": {
        "a": {"speaker": "one", "scenario": "x"},
        "b": {"speaker": "two", "scenario": "y"},
    }})
    full = write("full.json", {"items": [{"id": "a"}, {"id": "b"}]})
    primary = write("primary.json", {"items": [{"id": "a"}]})
    legacy_inputs, finalized_inputs, bundles = {}, {}, {}
    for name, rows in {
        "left": [
            {"sample_id": "a", "intent": 0, "tp": 1, "fp": 1, "fn": 1},
            {"sample_id": "b", "intent": 1, "tp": 2, "fp": 0, "fn": 1},
        ],
        "right": [
            {"sample_id": "a", "intent": 1, "tp": 2, "fp": 0, "fn": 1},
            {"sample_id": "b", "intent": 1, "tp": 2, "fp": 1, "fn": 0},
        ],
    }.items():
        manifest = write(name + ".manifest.json", {})
        scores = {"official": {"per_sample": rows}}
        legacy_score = write(name + ".legacy-score.json", {
            "verified": True, "manifest": manifest["path"], "scores": scores,
        })
        attached_score = write(name + ".attached-score.json", scores)
        legacy_inputs[name] = {
            "manifest": manifest, "score": legacy_score,
            "scorers": {"official": "official"},
        }
        finalized_inputs[name] = {
            "manifest": manifest, "score_source": "finalized-bundle",
            "scorers": {"official": "official"},
        }
        bundles[Path(manifest["path"])] = SimpleNamespace(
            attempt_state="FINALIZED", manifest_path=Path(manifest["path"]),
            manifest={"status": "COMPLETED", "scores": attached_score,
                      "scorers": ["official"]},
        )

    def config(inputs):
        return {
            "execution_profile": "model-free-check", "experiment_id": "equivalent",
            "analysis": {
                "metadata": metadata, "full_roster": full, "roster": primary,
                "inputs": inputs, "metrics": ["intent"],
                "micro_metrics": {
                    "micro": {"tp": ["tp"], "fp": ["fp"], "fn": ["fn"]},
                },
                "seed": 9, "n_replicates": 20,
                "contrasts": [{
                    "name": "right_minus_left", "left": "left", "right": "right",
                    "scorers": ["official"],
                }],
            },
        }

    legacy_path = tmp_path / "legacy-config.json"
    legacy_path.write_text(json.dumps(config(legacy_inputs)))
    legacy = cli.run(legacy_path, tmp_path / "legacy-result.json", verifier=lambda _: None)

    finalized_path = tmp_path / "finalized-config.json"
    finalized_path.write_text(json.dumps(config(finalized_inputs)))
    events = []
    original_pinned_json = cli.pinned_json

    def record_read(pin):
        events.append(("read", Path(pin["path"])))
        return original_pinned_json(pin)

    def verify(path):
        events.append(("verify", path))
        return bundles[path]

    monkeypatch.setattr(cli, "pinned_json", record_read)
    finalized = cli.run(finalized_path, tmp_path / "finalized-result.json", verifier=verify)

    first_score_read = min(
        index for index, event in enumerate(events)
        if event[0] == "read" and event[1].name.endswith("attached-score.json")
    )
    for name in ("left", "right"):
        manifest_path = Path(legacy_inputs[name]["manifest"]["path"])
        assert events[:first_score_read].count(("verify", manifest_path)) == 1
    assert finalized["populations"] == legacy["populations"]
    assert finalized["results"] == legacy["results"]
    assert finalized["sources"]["left"]["score"] == bundles[
        Path(legacy_inputs["left"]["manifest"]["path"])
    ].manifest["scores"]


@pytest.mark.parametrize(
    ("source", "state", "message"),
    [
        ("finalized-bundle", "OPENED", "finalized complete"),
        ("not-a-score-source", "FINALIZED", "unknown saved score source"),
    ],
)
def test_default_analysis_rejects_invalid_explicit_score_binding(
        tmp_path, source, state, message):
    import hashlib
    import json
    from pathlib import Path
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.analysis.score_compare_cli import run

    def write(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    manifest = write("manifest.json", {})
    attached = write("attached.json", {
        "official": {"per_sample": [{"sample_id": "a", "m": 1}]},
    })
    config = {
        "execution_profile": "model-free-check", "experiment_id": "invalid",
        "analysis": {
            "metadata": write("metadata.json", {"rows": {
                "a": {"speaker": "one", "scenario": "x"},
            }}),
            "full_roster": write("full.json", {"items": [{"id": "a"}]}),
            "roster": write("primary.json", {"items": [{"id": "a"}]}),
            "inputs": {"only": {
                "manifest": manifest, "score_source": source,
                "scorers": {"official": "official"},
            }},
            "metrics": ["m"], "seed": 1, "n_replicates": 20,
            "contrasts": [{
                "name": "self", "left": "only", "right": "only",
                "scorers": ["official"],
            }],
        },
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    bundle = SimpleNamespace(
        attempt_state=state, manifest_path=Path(manifest["path"]),
        manifest={"status": "COMPLETED", "scores": attached, "scorers": ["official"]},
    )
    with pytest.raises(ValueError, match=message):
        run(config_path, tmp_path / "out.json", verifier=lambda _: bundle)


def test_default_analysis_accepts_explicit_complete_score_receipt(tmp_path, monkeypatch):
    import hashlib
    import json

    from speech_aware_evidence_acquisition.analysis import score_compare_cli as cli

    def write(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    manifest = write("manifest.json", {})
    score = write("score.json", {
        "verified": True, "manifest": manifest["path"],
        "scores": {"official": {"per_sample": [{"sample_id": "a", "m": 1}]}},
    })
    receipt = write("receipt.json", {"score_result": score})
    binding = {
        "manifest": manifest, "score_source": "complete-score-receipt",
        "score_receipt": {**receipt, "cell_id": "only"},
        "scorers": {"official": "official"},
    }
    config = {
        "execution_profile": "model-free-check", "experiment_id": "receipt",
        "analysis": {
            "metadata": write("metadata.json", {"rows": {
                "a": {"speaker": "one", "scenario": "x"},
            }}),
            "full_roster": write("full.json", {"items": [{"id": "a"}]}),
            "roster": write("primary.json", {"items": [{"id": "a"}]}),
            "inputs": {"only": binding}, "metrics": ["m"],
            "seed": 1, "n_replicates": 20,
            "contrasts": [{
                "name": "self", "left": "only", "right": "only",
                "scorers": ["official"],
            }],
        },
    }
    seen = []

    def verify_receipt(ref, bundle):
        seen.append((ref.cell_id, bundle))
        return {"score_result": score}

    monkeypatch.setattr(cli, "verify_complete_score_receipt", verify_receipt)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    result = cli.run(config_path, tmp_path / "out.json", verifier=lambda _: None)

    assert seen == [("only", None)]
    assert result["results"]["self"]["NEW500"]["official"]["m"][
        "speaker_clustered"
    ]["delta"] == 0
    assert result["sources"]["only"] == {**binding, "score": score}


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



@pytest.fixture
def generic_scores(tmp_path, monkeypatch):
    import hashlib
    import json
    from speech_aware_evidence_acquisition.analysis import score_compare_cli as cli

    def write(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value))
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

    inputs, receipts, verified = {}, {}, []
    for name, count in (("left", 1), ("right", 2)):
        manifest = write(name + ".manifest.json", {})
        score = write(name + ".score.json", {
            "verified": True, "manifest": manifest["path"], "scores": {
                "official": {"per_sample": [
                    {"sample_id": "a", "exact_match": count == 2, "f1": 2 * count / (count + 10),
                     "correct": count, "predicted": count, "gold": 10},
                    {"sample_id": "b", "exact_match": True, "f1": 18 / 19,
                     "correct": 9, "predicted": 9, "gold": 10},
                ]}}})
        receipt = write(name + ".receipt.json", {"score_result": score})
        receipts[receipt["path"]] = {"score_result": score}
        inputs[name] = {"manifest": manifest,
                        "score_receipt": {**receipt, "cell_id": name}}

    def verify_receipt(ref, bundle):
        assert bundle == ref.cell_id
        verified.append(ref)
        return receipts[str(ref.path)]

    monkeypatch.setattr(cli, "verify_complete_score_receipt", verify_receipt)
    config = {
        "execution_profile": "model-free-check", "experiment_id": "synthetic",
        "analysis": {
            "format": "generic-scores-v1", "inputs": inputs,
            "metadata": write("metadata.json", {"rows": {
                "a": {"query_idx": "shared", "tier": "A", "domain": "one"},
                "b": {"query_idx": "shared", "tier": "B", "domain": "one"}}}),
            "full_roster": write("roster.json", {"items": [{"id": "a"}, {"id": "b"}]}),
            "expected_ids_count": 2, "cluster_field": "query_idx",
            "groupings": {"tier": "tier", "domain": "domain"},
            "grouping_resampling": "whole-cluster", "seed": 77, "n_replicates": 20,
            "metrics": {
                "em": {"scorer": "official", "statistic": "mean",
                       "field": "exact_match", "direction": "higher"},
                "macro": {"scorer": "official", "statistic": "mean",
                          "field": "f1", "direction": "higher"},
                "micro": {"scorer": "official", "statistic": "ratio",
                          "numerator": {"correct": 2}, "denominator": {"predicted": 1, "gold": 1},
                          "zero_denominator": "zero", "direction": "higher"}},
            "contrasts": [
                {"name": "primary", "left": "left", "right": "right",
                 "metrics": ["em"], "ci_level": .975},
                {"name": "secondary", "left": "left", "right": "right",
                 "metrics": ["macro", "micro"], "ci_level": .9}],
        },
    }
    config_path = tmp_path / "config.json"

    def execute():
        write(config_path.name, config)
        return cli.run(config_path, tmp_path / "out.json",
                       verifier=lambda path: path.name.split(".")[0])

    return config, execute, verified, receipts


def test_generic_scores_project_official_means_and_pooled_counts(generic_scores):
    config, execute, verified, _ = generic_scores
    result = execute()
    assert len(verified) == 2
    assert result["scorer_invocations"] == 0
    assert result["populations"] == {"full_roster": 2}
    primary = result["results"]["primary"]["em"]
    assert primary["natural_mixture"]["gain_pp"] == 50.
    assert primary["sign_counts"] == {"saves": 1, "harms": 0, "ties": 1, "unavailable": 0}
    assert primary["natural_mixture"]["bootstrap"]["ci_level"] == .975
    assert primary["groupings"]["tier"]["equal_stratum"]["gain_pp"] == 50.
    secondary = result["results"]["secondary"]
    assert secondary["micro"]["natural_mixture"]["left_ratio_pct"] == pytest.approx(100 * 20 / 30)
    assert secondary["micro"]["natural_mixture"]["right_ratio_pct"] == pytest.approx(100 * 22 / 31)
    assert secondary["micro"]["natural_mixture"]["bootstrap"]["ci_level"] == .9
    assert secondary["macro"]["natural_mixture"]["left_ratio_pct"] == pytest.approx(
        100 * (2 / 11 + 18 / 19) / 2)
    assert set(result["results"]["primary"]) == {"em"}
    with pytest.raises(FileExistsError):
        execute()


def test_generic_scores_require_exact_source_roster(generic_scores):
    config, execute, _, _ = generic_scores
    config["analysis"]["expected_ids_count"] = 3
    with pytest.raises(ValueError, match="identity mismatch"):
        execute()


def test_generic_scores_refuse_absent_persisted_diagnostic(generic_scores):
    config, execute, _, _ = generic_scores
    config["analysis"]["metrics"]["em"]["field"] = "not_persisted"
    with pytest.raises(ValueError, match="missing or has invalid"):
        execute()


def test_generic_scores_recheck_receipt_score_hash(generic_scores):
    config, execute, _, receipts = generic_scores
    from pathlib import Path
    pin = receipts[config["analysis"]["inputs"]["left"]["score_receipt"]["path"]]["score_result"]
    Path(pin["path"]).write_text("{}")
    with pytest.raises(ValueError, match="hash mismatch"):
        execute()


def test_generic_scores_refuse_receipt_verification_failure(generic_scores, monkeypatch):
    from speech_aware_evidence_acquisition.analysis import score_compare_cli as cli
    _, execute, _, _ = generic_scores

    def reject(*args):
        raise ValueError("synthetic receipt mismatch")

    monkeypatch.setattr(cli, "verify_complete_score_receipt", reject)
    with pytest.raises(ValueError, match="receipt mismatch"):
        execute()


@pytest.mark.parametrize("mutation", [
    {"statistic": "unsupported"},
    {"statistic": "ratio", "numerator": {"correct": -1}, "denominator": {"gold": 1}},
    {"statistic": "ratio", "numerator": {"correct": float("nan")}, "denominator": {"gold": 1}},
])
def test_generic_scores_refuse_invalid_projection(generic_scores, mutation):
    config, execute, _, _ = generic_scores
    config["analysis"]["metrics"]["em"].update(mutation)
    with pytest.raises(ValueError):
        execute()


def test_unknown_score_format_never_uses_legacy_default(generic_scores):
    config, execute, _, _ = generic_scores
    config["analysis"]["format"] = "typo"
    with pytest.raises(ValueError, match="unknown score analysis format"):
        execute()


def test_projection_keeps_zero_counts_and_rejects_nonfinite_fields():
    from speech_aware_evidence_acquisition.analysis.score_compare_cli import _project_scores
    metric = {"m": {"scorer": "s", "statistic": "ratio",
                    "numerator": {"tp": 2}, "denominator": {"pred": 1, "gold": 1},
                    "direction": "higher"}}
    row = {"sample_id": "a", "tp": 0, "pred": 0, "gold": 0}
    document = {"verified": True, "scores": {"s": {"per_sample": [row]}}}
    assert _project_scores(document, metric, {"a"}) == {"a": {"m": {"num": 0, "den": 0}}}
    row["tp"] = float("inf")
    with pytest.raises(ValueError, match="finite nonnegative"):
        _project_scores(document, metric, {"a"})



@pytest.mark.parametrize("state", ["FINALIZED", "OPENED"])
def test_generic_scores_read_finalized_attachment_without_rescoring(
        generic_scores, tmp_path, monkeypatch, state):
    import hashlib
    import json
    from pathlib import Path
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.analysis import score_compare_cli as cli

    config, _, _, receipts = generic_scores
    bundles = {}
    for name, binding in config["analysis"]["inputs"].items():
        ref = binding.pop("score_receipt")
        saved = receipts[ref["path"]]["score_result"]
        scores = json.loads(Path(saved["path"]).read_text())["scores"]
        path = tmp_path / (name + ".attached.json")
        path.write_text(json.dumps(scores))
        pin = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        binding["score_source"] = "finalized-bundle"
        bundles[name] = SimpleNamespace(
            attempt_state=state, manifest_path=Path(binding["manifest"]["path"]),
            manifest={"status": "COMPLETED", "scores": pin, "scorers": ["official"]})

    def receipt_must_not_run(*args):
        raise AssertionError("finalized attachment must not require a new scoring operation")

    monkeypatch.setattr(cli, "verify_complete_score_receipt", receipt_must_not_run)
    config_path = tmp_path / "attached-config.json"
    config_path.write_text(json.dumps(config))
    def run():
        return cli.run(config_path, tmp_path / "attached-out.json",
                       verifier=lambda path: bundles[path.name.split(".")[0]])
    if state == "OPENED":
        with pytest.raises(ValueError, match="finalized complete"):
            run()
    else:
        result = run()
        assert result["scorer_invocations"] == 0
        assert result["results"]["primary"]["em"]["natural_mixture"]["gain_pp"] == 50.



def test_generic_scores_use_declared_native_roster_id(generic_scores):
    import hashlib
    import json
    from pathlib import Path

    config, execute, _, _ = generic_scores
    binding = config["analysis"]["full_roster"]
    path = Path(binding["path"])
    path.write_text(json.dumps({"items": [
        {"id": 3, "sample_id": "a"}, {"id": 3, "sample_id": "b"}]}))
    binding.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), id_field="sample_id")
    assert execute()["populations"] == {"full_roster": 2}
