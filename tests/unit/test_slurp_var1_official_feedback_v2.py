"""Synthetic post-hoc official-count feedback tests; no real result access."""

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from test_slurp_var1_variant_read import world as var1_world, ARMS, RUN_OF, ATTEMPT_OF, PACKAGE_RELPATH, ROSTER_RELPATH


SCRIPT = Path(__file__).parents[2] / "scripts" / "analysis" / "slurp_var1_official_feedback_v2.py"
SPEC = importlib.util.spec_from_file_location("slurp_var1_official_feedback_v2", SCRIPT)
reader = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reader
SPEC.loader.exec_module(reader)


def score(sid, *, tp, fp, fn, slot_tp, slot_fp, slot_fn, intent=1):
    denominator = 2 * tp + fp + fn
    return {
        "sample_id": sid, "slu_f1_word_tp": tp, "slu_f1_word_fp": fp,
        "slu_f1_word_fn": fn, "slu_f1_char_tp": 0, "slu_f1_char_fp": 0,
        "slu_f1_char_fn": 0, "scenario_action_exact": intent,
        "slot_f1_exact_tp": slot_tp, "slot_f1_exact_fp": slot_fp,
        "slot_f1_exact_fn": slot_fn,
        "slu_f1_f1": 2 * tp / denominator if denominator else 0,
    }


def arm(rows, answers):
    return SimpleNamespace(
        rows_table={row["sample_id"]: row for row in rows},
        delivered={"rows": {sid: {"parsed": True, "scenario": answer[0],
                             "action": answer[1], "entities": answer[2]}
                            for sid, answer in answers.items()}},
    )


def test_frozen_plan_f0_and_empty_gold_fp_penalty():
    ids = ("empty", "entity")
    plan_rows = [score("empty", tp=2, fp=0, fn=0, slot_tp=0, slot_fp=0, slot_fn=0),
                 score("entity", tp=3, fp=0, fn=0, slot_tp=1, slot_fp=0, slot_fn=0)]
    planr_rows = [score("empty", tp=2, fp=0, fn=0, slot_tp=0, slot_fp=0, slot_fn=0),
                  score("entity", tp=2, fp=1, fn=1, slot_tp=1, slot_fp=0, slot_fn=0)]
    variant_rows = [score("empty", tp=2, fp=1, fn=0, slot_tp=0, slot_fp=1, slot_fn=0),
                    score("entity", tp=3, fp=0, fn=0, slot_tp=1, slot_fp=0, slot_fn=0)]
    clean = {"empty": ("alarm", "set", []),
             "entity": ("alarm", "set", [{"type": "person", "filler": "Alice"}])}
    noisy = {"empty": ("alarm", "set", [{"type": "place", "filler": "X"}]),
             "entity": ("alarm", "set", [{"type": "person", "filler": "Alice"}])}
    arms = {"plan": arm(plan_rows, clean), "planr": arm(planr_rows, clean),
            "exk10": arm(variant_rows, noisy)}
    roster = {"ids": ids, "cluster": {sid: sid for sid in ids},
              "stratum": {"empty": "alarm", "entity": "weather"}}
    result = reader.analyze(arms, roster, seed=7, draws=30)
    assert result["frozen_plan_f0"] == 1.0
    assert result["arms"]["exk10"]["empty_gold_fp_total"] == 1
    assert result["paired"]["exk10"]["plan"]["utility"]["delta"] < 0
    assert result["paired"]["exk10"]["planr"]["utility"]["delta"] != result["paired"]["exk10"]["plan"]["utility"]["delta"]
    assert result["paired"]["exk10"]["plan"]["answer_disagreement_rows"] == 1
    assert "ci95_pp" in result["paired"]["exk10"]["plan"]["pooled_official_slu_f1_natural_mixture"]
    assert set(result["paired"]["exk10"]["plan"]["per_scenario"]) == {"alarm", "weather"}


def test_canonical_answer_preserves_filler_case_but_ignores_entity_order():
    left = {"parsed": True, "scenario": "alarm", "action": "set", "entities": [
        {"type": "person", "filler": "Alice"}, {"type": "place", "filler": "Home"}]}
    reordered = {"parsed": True, "scenario": "alarm", "action": "set", "entities": list(reversed(left["entities"]))}
    changed = {**reordered, "entities": [{"type": "person", "filler": "alice"}, {"type": "place", "filler": "Home"}]}
    assert reader.answer_disagreement(left, reordered) is False
    assert reader.answer_disagreement(left, changed) is True


def test_equal_scenario_pooled_contrast_differs_from_natural_mixture():
    ids = ("a1", "a2", "b1")
    base = [score(sid, tp=2, fp=0, fn=0, slot_tp=0, slot_fp=0, slot_fn=0) for sid in ids]
    changed = [dict(row) for row in base]
    changed[2] = score("b1", tp=1, fp=1, fn=1, slot_tp=0, slot_fp=0, slot_fn=0)
    answers = {sid: ("alarm", "set", []) for sid in ids}
    arms = {"plan": arm(base, answers), "planr": arm(base, answers),
            "exk10": arm(changed, answers)}
    roster = {"ids": ids, "cluster": {sid: sid for sid in ids},
              "stratum": {"a1": "A", "a2": "A", "b1": "B"}}
    result = reader.analyze(arms, roster, seed=5, draws=20)
    pair = result["paired"]["exk10"]["plan"]
    natural = pair["pooled_official_slu_f1_natural_mixture"]["point_estimate_pp"]
    equal = pair["pooled_official_slu_f1_equal_scenario"]["point_estimate_pp"]
    assert natural != equal
    assert equal < natural < 0


def test_explicit_two_arm_feedback_separates_empty_fp_nonempty_fn_and_intent():
    ids = ("empty", "entity")
    base = [score("empty", tp=2, fp=0, fn=0, slot_tp=0, slot_fp=0, slot_fn=0),
            score("entity", tp=3, fp=0, fn=0, slot_tp=1, slot_fp=0, slot_fn=0)]
    varied = [score("empty", tp=2, fp=1, fn=0, slot_tp=0, slot_fp=1, slot_fn=0),
              score("entity", tp=0, fp=1, fn=3, slot_tp=0, slot_fp=0, slot_fn=1, intent=0)]
    answers = {sid: ("alarm", "set", []) for sid in ids}
    arms = {"control": arm(base, answers), "variant": arm(varied, answers)}
    roster = {"ids": ids, "cluster": {sid: sid for sid in ids},
              "stratum": {"empty": "A", "entity": "B"}}
    result = reader.analyze(arms, roster, seed=3, draws=20,
                            baseline_arm="control", comparison_pairs=(("variant", "control"),),
                            extended=True)
    pair = result["paired"]["variant"]["control"]
    assert result["frozen_baseline_f0"] == 1.0
    assert pair["empty_gold_fp_delta"] == 1
    assert pair["slot_f1_exact_nonempty_gold_fn_delta"] == 1
    assert pair["slot_f1_exact_nonempty_gold_fp_delta"] == 0
    assert pair["slu_f1_word_char_empty_gold_fp_delta"] == 1
    assert pair["slu_f1_word_char_nonempty_gold_fp_delta"] == 1
    assert pair["slu_f1_word_char_nonempty_gold_fn_delta"] == 3
    assert pair["intent_exact"]["delta"] < 0
    assert "ci90_pp" in pair["intent_exact"]["intervals"]
    assert "ci95_pp" in pair["intent_exact"]["intervals"]
    assert "frozen_plan_f0" not in result


def test_missing_empty_gold_count_is_rejected():
    row = score("empty", tp=2, fp=0, fn=0, slot_tp=0, slot_fp=0, slot_fn=0)
    del row["slot_f1_exact_fn"]
    arms = {key: arm([row], {"empty": ("alarm", "set", [])}) for key in ("plan", "planr", "exk10")}
    with pytest.raises(reader.FeedbackReadError, match="slot_f1_exact_fn"):
        reader.analyze(arms, {"ids": ("empty",), "cluster": {"empty": "empty"},
                              "stratum": {"empty": "alarm"}}, seed=1, draws=10)


def _finalize_synthetic_attempts(world):
    for key in ARMS:
        path = world["data_root"] / "attempts" / RUN_OF[key] / f"{ATTEMPT_OF[key]}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"state": "FINALIZED"}), encoding="utf-8")
        run_dir = world["data_root"] / "runs" / RUN_OF[key] / ATTEMPT_OF[key]
        manifest_path = run_dir / f"{RUN_OF[key]}.run-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["outputs"] = {"sha256": reader.var1.digest(run_dir / f"{RUN_OF[key]}.outputs.jsonl")}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_reuses_sealed_var1_loaders_and_records_source_hashes(var1_world):
    _finalize_synthetic_attempts(var1_world)
    arms, roster, sources = reader.load_sources(
        var1_world["repo_root"], var1_world["data_root"], PACKAGE_RELPATH)
    assert set(arms) == set(ARMS)
    assert len(roster["ids"]) == 64
    assert sources["arms"]["plan"]["scores_sha256"] == reader.var1.digest(
        arms["plan"].directory / f"{arms['plan'].run_id}.scores.json")


def test_refuses_duplicate_sealed_output_row(var1_world):
    _finalize_synthetic_attempts(var1_world)
    path = var1_world["data_root"] / "runs" / RUN_OF["plan"] / ATTEMPT_OF["plan"] / f"{RUN_OF['plan']}.outputs.jsonl"
    first = path.read_text(encoding="utf-8").splitlines()[0]
    with path.open("a", encoding="utf-8") as handle:
        handle.write(first + "\n")
    manifest_path = path.with_name(f"{RUN_OF['plan']}.run-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["outputs"]["sha256"] = reader.var1.digest(path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(reader.FeedbackReadError, match="duplicate delivered"):
        reader.load_sources(var1_world["repo_root"], var1_world["data_root"], PACKAGE_RELPATH)


def test_refuses_unsealed_manifest(var1_world):
    _finalize_synthetic_attempts(var1_world)
    path = var1_world["data_root"] / "runs" / RUN_OF["plan"] / ATTEMPT_OF["plan"] / f"{RUN_OF['plan']}.run-manifest.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["status"] = "RUNNING"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(reader.var1.Var1ReadError, match="not COMPLETED"):
        reader.load_sources(var1_world["repo_root"], var1_world["data_root"], PACKAGE_RELPATH)


def test_cli_binds_preregistered_facts_and_writes_no_answer_text(var1_world, tmp_path):
    _finalize_synthetic_attempts(var1_world)
    facts = var1_world["repo_root"] / PACKAGE_RELPATH / "registered-facts-v1.json"
    recipe = tmp_path / "read-recipe.json"
    recipe.write_text(json.dumps({
        "driver": "scripts/analysis/slurp_var1_official_feedback_v2.py",
        "input_package_sha256": reader.var1.digest(facts),
        "statistics": {"seed": 9, "draws": 2},
    }), encoding="utf-8")
    out = tmp_path / "feedback.json"
    assert reader.main([
        "--repo-root", str(var1_world["repo_root"]), "--data-root", str(var1_world["data_root"]),
        "--package", PACKAGE_RELPATH, "--read-recipe", str(recipe),
        "--out", str(out), "--seed", "9", "--draws", "2",
    ]) == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["sources"]["registered_facts_sha256"] == reader.var1.digest(facts)
    assert result["status"] == "post_hoc_descriptive"
    assert "f0-date" not in out.read_text(encoding="utf-8")


def test_refuses_output_manifest_hash_mismatch(var1_world):
    _finalize_synthetic_attempts(var1_world)
    path = var1_world["data_root"] / "runs" / RUN_OF["plan"] / ATTEMPT_OF["plan"] / f"{RUN_OF['plan']}.run-manifest.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["outputs"]["sha256"] = "0" * 64
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(reader.FeedbackReadError, match="output SHA"):
        reader.load_sources(var1_world["repo_root"], var1_world["data_root"], PACKAGE_RELPATH)


def test_cli_refuses_mismatched_preregistration_before_loading_arms(var1_world, tmp_path):
    recipe = tmp_path / "read-recipe.json"
    recipe.write_text(json.dumps({"driver": "other", "statistics": {"seed": 9, "draws": 2}}), encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        reader.main(["--repo-root", str(var1_world["repo_root"]),
                     "--data-root", str(var1_world["data_root"]), "--package", PACKAGE_RELPATH,
                     "--read-recipe", str(recipe), "--out", str(tmp_path / "out.json"),
                     "--seed", "9", "--draws", "2"])
    assert error.value.code == 2


def _comparison_recipe(world, tmp_path):
    _finalize_synthetic_attempts(world)
    registration = world["repo_root"] / "docs" / "readiness" / "registered-comparison.json"
    registration.parent.mkdir(parents=True, exist_ok=True)
    registration.write_text(json.dumps({"purpose": "synthetic comparison"}), encoding="utf-8")
    roster = world["roster_path"]
    arms = {}
    for name in ("plan", "exdiv"):
        run, attempt = RUN_OF[name], ATTEMPT_OF[name]
        directory = world["data_root"] / "runs" / run / attempt
        arms[name] = {"run_id": run, "attempt_id": attempt,
                      "scorer_id": "slurp-slu-official-train",
                      "source_sha256": {
                          "run_manifest": reader.var1.digest(directory / f"{run}.run-manifest.json"),
                          "scores": reader.var1.digest(directory / f"{run}.scores.json"),
                          "outputs": reader.var1.digest(directory / f"{run}.outputs.jsonl"),
                      }}
    payload = {
        "schema": "saea-sealed-official-count-comparison-v1",
        "registration": {"path": "docs/readiness/registered-comparison.json",
                         "sha256": reader.var1.digest(registration)},
        "roster": {"relpath": ROSTER_RELPATH, "sha256": reader.var1.digest(roster),
                   "split_identity_hash": world["split_identity_hash"],
                   "split_role": "discovery", "rows": 64},
        "cluster_key": "utterance_id", "arms": arms,
        "comparisons": [{"left": "plan", "right": "exdiv"}],
        "statistics": {"seed": 9, "draws": 2},
    }
    path = tmp_path / "comparison.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


def test_two_arm_recipe_loads_exact_bound_sources(var1_world, tmp_path):
    recipe, _ = _comparison_recipe(var1_world, tmp_path)
    arms, roster, sources, pairs, stats = reader.load_comparison_sources(
        var1_world["repo_root"], var1_world["data_root"], recipe)
    assert set(arms) == {"plan", "exdiv"}
    assert pairs == (("exdiv", "plan"),)
    assert stats == (9, 2)
    assert sources["registration_sha256"] == reader.var1.digest(
        var1_world["repo_root"] / "docs/readiness/registered-comparison.json")
    assert len(roster["ids"]) == 64


def test_two_arm_recipe_refuses_bad_source_hash(var1_world, tmp_path):
    recipe, payload = _comparison_recipe(var1_world, tmp_path)
    payload["arms"]["exdiv"]["source_sha256"]["outputs"] = "0" * 64
    recipe.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(reader.FeedbackReadError, match="outputs"):
        reader.load_comparison_sources(var1_world["repo_root"], var1_world["data_root"], recipe)


def test_two_arm_recipe_refuses_missing_hash(var1_world, tmp_path):
    recipe, payload = _comparison_recipe(var1_world, tmp_path)
    del payload["arms"]["plan"]["source_sha256"]["scores"]
    recipe.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(reader.FeedbackReadError, match="scores"):
        reader.load_comparison_sources(var1_world["repo_root"], var1_world["data_root"], recipe)


def test_two_arm_cli_writes_bound_feedback_and_preserves_legacy_fields(var1_world, tmp_path):
    recipe, _ = _comparison_recipe(var1_world, tmp_path)
    out = tmp_path / "two-arm.json"
    assert reader.main([
        "--repo-root", str(var1_world["repo_root"]),
        "--data-root", str(var1_world["data_root"]),
        "--comparison-recipe", str(recipe), "--out", str(out),
    ]) == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["schema"] == "saea-sealed-official-count-comparison-read-v1"
    assert result["sources"]["comparison_recipe_sha256"] == reader.var1.digest(recipe)
    assert result["baseline_arm"] == "plan"
    assert result["status"] == "descriptive_registered_comparison"
    assert "frozen_plan_f0" not in result
    assert "ci90_pp" in result["paired"]["exdiv"]["plan"]["intent_exact"]["intervals"]


def test_two_arm_recipe_refuses_changed_registration(var1_world, tmp_path):
    recipe, payload = _comparison_recipe(var1_world, tmp_path)
    payload["registration"]["sha256"] = "0" * 64
    recipe.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(reader.FeedbackReadError, match="registration SHA"):
        reader.load_comparison_sources(var1_world["repo_root"], var1_world["data_root"], recipe)


def test_two_arm_recipe_refuses_nonfinal_attempt_before_any_arm_load(var1_world, tmp_path, monkeypatch):
    recipe, _ = _comparison_recipe(var1_world, tmp_path)
    attempt = var1_world["data_root"] / "attempts" / RUN_OF["exdiv"] / f"{ATTEMPT_OF['exdiv']}.json"
    attempt.write_text(json.dumps({"state": "RUNNING"}), encoding="utf-8")
    loaded = []
    monkeypatch.setattr(reader.var1, "load_arm", lambda **kwargs: loaded.append(kwargs))
    with pytest.raises(reader.FeedbackReadError, match="FINALIZED"):
        reader.load_comparison_sources(var1_world["repo_root"], var1_world["data_root"], recipe)
    assert loaded == []


def test_fallback_flags_include_recorded_terminal_reasons(monkeypatch, tmp_path):
    phases = {"results": [
        {"sample_id": "finite", "native_episode_receipt": {
            "terminal_disposition": {"reason": "finite_completion"}}},
        {"sample_id": "limit", "native_episode_receipt": {
            "terminal_disposition": {"reason": "revision_limit"}}},
        {"sample_id": "ok", "native_episode_receipt": {}},
    ]}
    monkeypatch.setattr(reader.var1.bank, "load_phase_results", lambda *_: phases)
    flags = reader._explicit_fallback_flags(tmp_path, "run", ["finite", "limit", "ok"])
    assert flags["finite"]["finite_completion"]
    assert flags["limit"]["revision_limit"]
    assert not any(flags["ok"].values())
