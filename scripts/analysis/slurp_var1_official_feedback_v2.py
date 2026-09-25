#!/usr/bin/env python3
"""Post-hoc VAR-1 official-count feedback from sealed artifacts only.

This reader never invokes the official scorer, a model, a tokenizer, or a service.
It reports source hashes and counts, never delivered answer or filler text.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Mapping

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from speech_aware_evidence_acquisition.analysis.official_metric_feedback import (  # noqa: E402
    FeedbackError, answers_disagree, extract_official_feedback, frozen_baseline_f1,
    pooled_f1, utility,
)
from speech_aware_evidence_acquisition.analysis.paired import paired_contrast, resampled_statistic  # noqa: E402
import slurp_var1_variant_read as var1  # noqa: E402


class FeedbackReadError(ValueError):
    """A sealed source or official count is missing or misbound."""


def _count(row: Mapping, field: str) -> float:
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise FeedbackReadError(f"official score row requires finite nonnegative {field}")
    return float(value)


def _answer(record: Mapping) -> dict:
    if not record.get("parsed"):
        return {"scenario": "<unparsed>", "action": "<unparsed>", "entities": []}
    entities = []
    for entity in record.get("entities", []):
        if isinstance(entity, Mapping):
            entities.append({"type": entity.get("type"), "filler": entity.get("filler")})
        else:
            entities.append({"type": getattr(entity, "type", None),
                             "filler": getattr(entity, "filler", None)})
    return {"scenario": record.get("scenario"), "action": record.get("action"),
            "entities": entities}


def answer_disagreement(left: Mapping, right: Mapping) -> bool:
    """Schema-aware structured comparison, including entity multiset order normalization."""
    try:
        return answers_disagree(_answer(left), _answer(right))
    except FeedbackError as exc:
        raise FeedbackReadError(str(exc)) from exc


def _exact_output_ids(path: Path, expected_ids) -> None:
    """The reused delivered loader checks missing rows; also refuse extras/duplicates."""
    seen = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            sid = json.loads(line).get("sample_id")
            if sid in seen:
                raise FeedbackReadError(f"{path.name}: duplicate delivered sample id")
            seen.add(sid)
    if seen != set(expected_ids):
        raise FeedbackReadError(f"{path.name}: delivered ids do not exactly match roster")


FALLBACK_FIELDS = ("finite_completion", "react_exhaustion", "planner_action_illegal")


def _explicit_fallback_flags(directory: Path, run_id: str, expected_ids) -> dict:
    """Read only named native dispositions; absence is recorded, never inferred."""
    phases = var1.bank.load_phase_results(directory, run_id)
    result = {}
    for item in phases["results"]:
        sid = item.get("sample_id")
        if sid in result:
            raise FeedbackReadError(f"{run_id}: repeated phase sample id")
        receipt = item.get("native_episode_receipt") or {}
        dispositions = receipt.get("dispositions") or {}
        result[sid] = {
            field: bool(receipt.get(field) or dispositions.get(field))
            for field in FALLBACK_FIELDS
        }
    if set(result) != set(expected_ids):
        raise FeedbackReadError(f"{run_id}: phase ids do not exactly match roster")
    return result


def _arm_rows(arm, ids):
    if set(arm.rows_table) != set(ids) or set(arm.delivered["rows"]) != set(ids):
        raise FeedbackReadError("sealed arm does not cover exactly the roster ids")
    feedback = {}
    empty = {}
    for sid in ids:
        row = arm.rows_table[sid]
        try:
            feedback[sid] = extract_official_feedback({**row, "sample_id": sid})
        except FeedbackError as exc:
            raise FeedbackReadError(str(exc)) from exc
        tp = _count(row, "slot_f1_exact_tp")
        fp = _count(row, "slot_f1_exact_fp")
        fn = _count(row, "slot_f1_exact_fn")
        empty[sid] = (tp == 0 and fn == 0, fp)
    return feedback, empty


def analyze(arms: Mapping, roster: Mapping, *, seed: int, draws: int) -> dict:
    """Pure aligned feedback; PLAN's F0 stays fixed for every comparison."""
    if "plan" not in arms or "planr" not in arms or len(arms) < 3:
        raise FeedbackReadError("PLAN, PLANR, and at least one variant are required")
    ids = tuple(roster["ids"])
    if (not ids or len(ids) != len(set(ids)) or set(roster["cluster"]) != set(ids)
            or set(roster["stratum"]) != set(ids)):
        raise FeedbackReadError("roster ids, clusters, or scenario bindings are incomplete")
    if not isinstance(draws, int) or draws < 2:
        raise FeedbackReadError("draws must be at least two")
    feedback = {}
    empty = {}
    for key, arm in arms.items():
        feedback[key], empty[key] = _arm_rows(arm, ids)
    for sid in ids:
        if len({empty[key][sid][0] for key in arms}) != 1:
            raise FeedbackReadError(f"empty-gold identity disagrees across sealed arms on {sid}")
    empty_ids = tuple(sid for sid in ids if empty["plan"][sid][0])
    f0 = frozen_baseline_f1([feedback["plan"][sid] for sid in ids])
    tables = {}
    utility_rows = {}
    for key in arms:
        utility_rows[key] = {sid: {"utility": utility(feedback[key][sid], f0)} for sid in ids}
        records = arms[key].delivered["rows"]
        runtime_rows = (getattr(arms[key], "runtime", {}) or {}).get("rows", {})
        fallback_rows = getattr(arms[key], "fallback_flags", {})
        row_f1 = [_count(arms[key].rows_table[sid], "slu_f1_f1") for sid in ids]
        tables[key] = {
            "pooled_official_slu_f1": pooled_f1([feedback[key][sid] for sid in ids]),
            "mean_per_row_slu_f1": sum(row_f1) / len(ids),
            "scenario_action_exact_rate": sum(feedback[key][sid].intent_exact for sid in ids) / len(ids),
            "mean_frozen_f0_utility": sum(utility_rows[key][sid]["utility"] for sid in ids) / len(ids),
            "empty_gold_rows": len(empty_ids),
            "empty_gold_fp_total": sum(empty[key][sid][1] for sid in empty_ids),
            "empty_gold_fp_rows": sum(empty[key][sid][1] > 0 for sid in empty_ids),
            "unparsed_rows": sum(not records[sid].get("parsed") for sid in ids),
            "format_normaliser_changed_rows": sum(bool(runtime_rows.get(sid, {}).get("normaliser_changed")) for sid in ids),
            "explicit_fallback_disposition_rows": {
                field: sum(bool(fallback_rows.get(sid, {}).get(field)) for sid in ids)
                for field in FALLBACK_FIELDS
            },
        }
    paired = {}
    for variant in sorted(set(arms) - {"plan", "planr"}):
        paired[variant] = {}
        for baseline in ("plan", "planr"):
            contrast_result = paired_contrast(
                utility_rows[baseline], utility_rows[variant], metrics=("utility",),
                sample_ids=ids, cluster_of=lambda sid: roster["cluster"][sid],
                seed=seed, n_replicates=draws,
            )["utility"]
            contrast = contrast_result.as_dict()
            contrast["intervals"] = var1.interval_block(
                contrast_result.bootstrap.replicates, contrast_result.delta, seed)
            left = arms[baseline].delivered["rows"]
            right = arms[variant].delivered["rows"]
            def pooled_delta(sample_ids):
                return (pooled_f1([feedback[variant][sid] for sid in sample_ids])
                        - pooled_f1([feedback[baseline][sid] for sid in sample_ids]))

            def equal_scenario_delta(sample_ids):
                by_scenario = {scenario: [] for scenario in sorted(set(roster["stratum"].values()))}
                for sid in sample_ids:
                    by_scenario[roster["stratum"][sid]].append(sid)
                return sum(pooled_delta(members) for members in by_scenario.values()) / len(by_scenario)

            cluster_of = lambda sid: roster["cluster"][sid]
            natural = resampled_statistic(sample_ids=ids, statistic=pooled_delta,
                                          cluster_of=cluster_of, seed=seed,
                                          n_replicates=draws, ci_level=0.95)
            equal = resampled_statistic(sample_ids=ids, statistic=equal_scenario_delta,
                                        cluster_of=cluster_of,
                                        strata_of=lambda sid: roster["stratum"][sid],
                                        seed=seed, n_replicates=draws, ci_level=0.95)
            scenarios = {}
            for scenario in sorted(set(roster["stratum"].values())):
                members = [sid for sid in ids if roster["stratum"][sid] == scenario]
                scenarios[scenario] = {"rows": len(members), "pooled_official_slu_f1_delta": pooled_delta(members),
                                       "empty_gold_rows": sum(sid in empty_ids for sid in members),
                                       "empty_gold_fp_delta": sum(empty[variant][sid][1] - empty[baseline][sid][1]
                                                                  for sid in members if sid in empty_ids)}
            paired[variant][baseline] = {
                "utility": contrast,
                "pooled_official_slu_f1_natural_mixture": var1.interval_block(natural.replicates, natural.point_estimate, seed),
                "pooled_official_slu_f1_equal_scenario": var1.interval_block(equal.replicates, equal.point_estimate, seed),
                "per_scenario": scenarios,
                "answer_disagreement_rows": sum(answer_disagreement(left[sid], right[sid]) for sid in ids),
                "parse_status_disagreement_rows": sum(bool(left[sid].get("parsed")) != bool(right[sid].get("parsed")) for sid in ids),
                "format_normaliser_changed_disagreement_rows": sum(
                    bool((getattr(arms[baseline], "runtime", {}) or {}).get("rows", {}).get(sid, {}).get("normaliser_changed")) !=
                    bool((getattr(arms[variant], "runtime", {}) or {}).get("rows", {}).get(sid, {}).get("normaliser_changed"))
                    for sid in ids),
                "explicit_fallback_disposition_disagreement_rows": {
                    field: sum(bool(getattr(arms[baseline], "fallback_flags", {}).get(sid, {}).get(field)) !=
                               bool(getattr(arms[variant], "fallback_flags", {}).get(sid, {}).get(field))
                               for sid in ids)
                    for field in FALLBACK_FIELDS
                },
                "empty_gold_fp_delta": sum(empty[variant][sid][1] - empty[baseline][sid][1] for sid in empty_ids),
                "empty_gold_fp_added_rows": sum(empty[baseline][sid][1] == 0 and empty[variant][sid][1] > 0 for sid in empty_ids),
                "empty_gold_fp_removed_rows": sum(empty[baseline][sid][1] > 0 and empty[variant][sid][1] == 0 for sid in empty_ids),
            }
    return {
        "schema": "saea-slurp-var1-official-feedback-v2",
        "status": "post_hoc_descriptive",
        "frozen_plan_f0": f0,
        "f0_definition": "pooled official SLU word+character F1 on sealed PLAN roster",
        "rows": len(ids),
        "empty_gold_rows": len(empty_ids),
        "arms": tables,
        "paired": paired,
        "answer_comparison": "official_metric_feedback.canonical_answer; schema and sorted entity multiset, text preserved",
    }


def load_sources(repo_root: Path, data_root: Path, package: str):
    """Reuse VAR-1's sealed loaders, then require full roster and registration binding."""
    package_dir = repo_root / package
    recipe_path = package_dir / "analysis-recipe-v1.json"
    facts_path = package_dir / "registered-facts-v1.json"
    recipe = var1.load_json(recipe_path)
    facts = var1.load_json(facts_path)
    specs = var1._arm_specs(recipe, var1.EXPECTED_ARMS)
    roster_relpath = (recipe.get("driver") or {}).get("roster")
    scorer = (recipe.get("scorer") or {}).get("id")
    if not roster_relpath or not scorer:
        raise FeedbackReadError("recipe lacks roster or scorer identity")
    roster = var1.load_roster(repo_root, roster_relpath, "utterance_id")
    pin = ((facts.get("pins") or {}).get("roster") or {})
    if pin.get("relpath") != roster_relpath or pin.get("sha256") != roster["sha256"]:
        raise FeedbackReadError("registered roster path or SHA disagrees")
    if roster["split_role"] != "discovery":
        raise FeedbackReadError("VAR-1 feedback requires discovery roster")
    if (facts.get("population") or {}).get("split_identity_hash") != roster["split_identity_hash"]:
        raise FeedbackReadError("registered split identity disagrees with roster")
    if (facts.get("population") or {}).get("rows") != len(roster["ids"]):
        raise FeedbackReadError("registered population count disagrees with roster")
    arms = {}
    bindings = {}
    for key, spec in specs.items():
        arm = var1.load_arm(key=key, run_id=spec["run_id"], attempt_id=spec["attempt_id"],
                            data_root=data_root, roster=roster, scorer_id=scorer)
        if arm.manifest["split_role"] != "discovery" or arm.manifest["ids"] != roster["ids"]:
            raise FeedbackReadError(f"{key}: sealed manifest roster or role disagrees")
        manifest_doc = var1.load_json(arm.directory / f"{arm.run_id}.run-manifest.json")
        if (manifest_doc.get("outputs") or {}).get("sha256") != arm.outputs_sha256:
            raise FeedbackReadError(f"{key}: run manifest output SHA disagrees with sealed outputs")
        record_path = data_root / "attempts" / arm.run_id / f"{arm.attempt_id}.json"
        if var1.load_json(record_path).get("state") != "FINALIZED":
            raise FeedbackReadError(f"{key}: attempt is not FINALIZED")
        _exact_output_ids(arm.directory / f"{arm.run_id}.outputs.jsonl", roster["ids"])
        arm.fallback_flags = _explicit_fallback_flags(arm.directory, arm.run_id, roster["ids"])
        registered = var1._check_registered_hashes(arm, spec, facts)
        arms[key] = arm
        bindings[key] = {
            "run_id": arm.run_id, "attempt_id": arm.attempt_id,
            "run_manifest_sha256": arm.manifest["sha256"],
            "generation_manifest_sha256": arm.generation_manifest_sha256,
            "scores_sha256": arm.scores["sha256"],
            "outputs_sha256": arm.outputs_sha256,
            "phases_sha256": arm.runtime["sha256"],
            "attempt_record_sha256": var1.digest(record_path),
            "score_jobs_sha256": var1.digest(arm.directory / "score-jobs.jsonl"),
            "flight_receipts_sha256": arm.flight_receipts_sha256,
            "registered": registered,
        }
    sources = {
        "analysis_recipe_sha256": var1.digest(recipe_path),
        "registered_facts_sha256": var1.digest(facts_path),
        "roster_sha256": roster["sha256"],
        "split_identity_hash": roster["split_identity_hash"],
        "scorer_id": scorer,
        "arms": bindings,
    }
    return arms, roster, sources


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--read-recipe", type=Path, required=True,
                        help="The pre-registered post-hoc derived-read recipe")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--draws", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        read_recipe = var1.load_json(args.read_recipe)
        expected_facts = args.repo_root / args.package / "registered-facts-v1.json"
        if (read_recipe.get("driver") != "scripts/analysis/slurp_var1_official_feedback_v2.py"
                or read_recipe.get("input_package_sha256") != var1.digest(expected_facts)
                or (read_recipe.get("statistics") or {}).get("seed") != args.seed
                or (read_recipe.get("statistics") or {}).get("draws") != args.draws):
            raise FeedbackReadError("derived-read preregistration, source facts, seed, or draws disagree")
        arms, roster, sources = load_sources(args.repo_root, args.data_root, args.package)
        result = analyze(arms, roster, seed=args.seed, draws=args.draws)
    except (FeedbackReadError, FeedbackError, var1.Var1ReadError) as exc:
        parser.exit(2, f"refused: {exc}\n")
    result["sources"] = sources
    result["sources"]["derived_read_recipe_sha256"] = var1.digest(args.read_recipe)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    var1.write_json(args.out, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
