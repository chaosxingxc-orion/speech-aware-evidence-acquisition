"""Synthetic post-hoc official-count feedback tests; no real result access."""

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from test_slurp_var1_variant_read import world as var1_world, ARMS, RUN_OF, ATTEMPT_OF, PACKAGE_RELPATH


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
