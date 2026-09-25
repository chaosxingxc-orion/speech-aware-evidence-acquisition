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
import re
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


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _sha(value, name):
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise FeedbackReadError(f"{name} requires a full SHA-256 binding")
    return value


def _repo_path(repo_root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise FeedbackReadError("registered source path must be repository-relative")
    root = repo_root.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise FeedbackReadError("registered source path leaves repository")
    return path


def _id(value, name):
    if not isinstance(value, str) or not value or value in (".", "..") or "/" in value or "\\" in value:
        raise FeedbackReadError(f"{name} must be one path component")
    return value


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


FALLBACK_FIELDS = ("finite_completion", "react_exhaustion", "planner_action_illegal", "revision_limit")


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
        terminal_reason = (receipt.get("terminal_disposition") or {}).get("reason")
        result[sid] = {
            field: bool(receipt.get(field) or dispositions.get(field) or terminal_reason == field)
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
        empty[sid] = (tp == 0 and fn == 0, fp, fn)
    return feedback, empty


def analyze(arms: Mapping, roster: Mapping, *, seed: int, draws: int,
            baseline_arm: str = "plan", comparison_pairs=None, extended: bool = False) -> dict:
    """Pure aligned feedback; one left-arm F0 stays fixed within a read."""
    legacy = comparison_pairs is None
    if legacy and ("plan" not in arms or "planr" not in arms or len(arms) < 3):
        raise FeedbackReadError("PLAN, PLANR, and at least one variant are required")
    if baseline_arm not in arms:
        raise FeedbackReadError("frozen baseline arm is absent")
    pairs = (tuple((variant, baseline) for variant in sorted(set(arms) - {"plan", "planr"})
                   for baseline in ("plan", "planr")) if legacy else tuple(comparison_pairs))
    if not pairs or any(variant not in arms or baseline not in arms or variant == baseline
                        for variant, baseline in pairs):
        raise FeedbackReadError("comparison pairs must name distinct loaded arms")
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
    empty_ids = tuple(sid for sid in ids if empty[baseline_arm][sid][0])
    nonempty_ids = tuple(sid for sid in ids if sid not in set(empty_ids))
    f0 = frozen_baseline_f1([feedback[baseline_arm][sid] for sid in ids])
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
        if extended:
            tables[key]["nonempty_gold_rows"] = len(nonempty_ids)
            tables[key]["slot_f1_exact_empty_gold_fp_total"] = tables[key]["empty_gold_fp_total"]
            tables[key]["slot_f1_exact_nonempty_gold_fp_total"] = sum(empty[key][sid][1] for sid in nonempty_ids)
            tables[key]["slot_f1_exact_nonempty_gold_fn_total"] = sum(empty[key][sid][2] for sid in nonempty_ids)
            for group, members in (("empty", empty_ids), ("nonempty", nonempty_ids)):
                tables[key][f"slu_f1_word_char_{group}_gold_fp_total"] = sum(feedback[key][sid].fp for sid in members)
                tables[key][f"slu_f1_word_char_{group}_gold_fn_total"] = sum(feedback[key][sid].fn for sid in members)
            cost = getattr(arms[key], "generation_cost", {}) or {}
            tables[key]["available_generation_cost"] = {
                name: cost[name] for name in (
                    "calls_used", "prompt_tokens_total", "completion_tokens_total",
                    "audio_seconds_used", "tool_calls", "latency_seconds_total",
                ) if isinstance(cost.get(name), (int, float)) and not isinstance(cost[name], bool)
            }
    paired = {}
    for variant, baseline in pairs:
        paired.setdefault(variant, {})
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
        if extended:
            intent_left = {sid: {"intent": feedback[baseline][sid].intent_exact} for sid in ids}
            intent_right = {sid: {"intent": feedback[variant][sid].intent_exact} for sid in ids}
            intent = paired_contrast(
                intent_left, intent_right, metrics=("intent",), sample_ids=ids,
                cluster_of=cluster_of, seed=seed, n_replicates=draws,
            )["intent"]
            intent_block = intent.as_dict()
            intent_block["intervals"] = var1.interval_block(
                intent.bootstrap.replicates, intent.delta, seed)
            def equal_intent_delta(sample_ids):
                by_scenario = {scenario: [] for scenario in sorted(set(roster["stratum"].values()))}
                for sid in sample_ids:
                    by_scenario[roster["stratum"][sid]].append(sid)
                return sum(sum(feedback[variant][sid].intent_exact - feedback[baseline][sid].intent_exact
                               for sid in members) / len(members)
                           for members in by_scenario.values()) / len(by_scenario)
            equal_intent = resampled_statistic(
                sample_ids=ids, statistic=equal_intent_delta,
                cluster_of=cluster_of, strata_of=lambda sid: roster["stratum"][sid],
                seed=seed, n_replicates=draws, ci_level=0.95)
            paired[variant][baseline]["intent_exact"] = intent_block
            paired[variant][baseline]["intent_exact_equal_scenario"] = var1.interval_block(
                equal_intent.replicates, equal_intent.point_estimate, seed)
            paired[variant][baseline]["slot_f1_exact_empty_gold_fp_delta"] = paired[variant][baseline]["empty_gold_fp_delta"]
            paired[variant][baseline]["slot_f1_exact_nonempty_gold_fp_delta"] = sum(
                empty[variant][sid][1] - empty[baseline][sid][1] for sid in nonempty_ids)
            paired[variant][baseline]["slot_f1_exact_nonempty_gold_fn_delta"] = sum(
                empty[variant][sid][2] - empty[baseline][sid][2] for sid in nonempty_ids)
            for group, members in (("empty", empty_ids), ("nonempty", nonempty_ids)):
                paired[variant][baseline][f"slu_f1_word_char_{group}_gold_fp_delta"] = sum(
                    feedback[variant][sid].fp - feedback[baseline][sid].fp for sid in members)
                paired[variant][baseline][f"slu_f1_word_char_{group}_gold_fn_delta"] = sum(
                    feedback[variant][sid].fn - feedback[baseline][sid].fn for sid in members)
            for scenario, entry in scenarios.items():
                members = [sid for sid in ids if roster["stratum"][sid] == scenario]
                nonempty_members = [sid for sid in members if sid in nonempty_ids]
                entry["slot_f1_exact_empty_gold_fp_delta"] = entry["empty_gold_fp_delta"]
                entry["intent_exact_delta"] = sum(
                    feedback[variant][sid].intent_exact - feedback[baseline][sid].intent_exact
                    for sid in members) / len(members)
                entry["nonempty_gold_rows"] = len(nonempty_members)
                entry["slot_f1_exact_nonempty_gold_fp_delta"] = sum(
                    empty[variant][sid][1] - empty[baseline][sid][1] for sid in nonempty_members)
                entry["slot_f1_exact_nonempty_gold_fn_delta"] = sum(
                    empty[variant][sid][2] - empty[baseline][sid][2] for sid in nonempty_members)
                for group, group_members in (("empty", [sid for sid in members if sid in empty_ids]),
                                             ("nonempty", nonempty_members)):
                    entry[f"slu_f1_word_char_{group}_gold_fp_delta"] = sum(
                        feedback[variant][sid].fp - feedback[baseline][sid].fp for sid in group_members)
                    entry[f"slu_f1_word_char_{group}_gold_fn_delta"] = sum(
                        feedback[variant][sid].fn - feedback[baseline][sid].fn for sid in group_members)
    result = {
        "schema": "saea-slurp-var1-official-feedback-v2",
        "status": "post_hoc_descriptive",
        "frozen_plan_f0" if legacy else "frozen_baseline_f0": f0,
        "f0_definition": ("pooled official SLU word+character F1 on sealed PLAN roster" if legacy
                          else f"descriptive pooled official SLU word+character F1 on sealed {baseline_arm} roster"),
        "rows": len(ids),
        "empty_gold_rows": len(empty_ids),
        "arms": tables,
        "paired": paired,
        "answer_comparison": "official_metric_feedback.canonical_answer; schema and sorted entity multiset, text preserved",
    }
    if extended:
        result["schema"] = "saea-sealed-official-count-comparison-read-v1"
        result["status"] = "descriptive_registered_comparison"
        result["baseline_arm"] = baseline_arm
        result["nonempty_gold_rows"] = len(nonempty_ids)
        result["entity_error_count_definition"] = "slot_f1_exact_fp/fn from sealed official per-row scores"
        result["slu_error_count_definition"] = "combined slu_f1_word and slu_f1_char FP/FN from sealed official per-row scores"
    return result


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
        arm, binding = _load_sealed_arm(key=key, spec=spec, data_root=data_root,
                                        roster=roster, scorer=scorer, split_role="discovery")
        registered = var1._check_registered_hashes(arm, spec, facts)
        arms[key] = arm
        bindings[key] = {**binding, "registered": registered}
    sources = {
        "analysis_recipe_sha256": var1.digest(recipe_path),
        "registered_facts_sha256": var1.digest(facts_path),
        "roster_sha256": roster["sha256"],
        "split_identity_hash": roster["split_identity_hash"],
        "scorer_id": scorer,
        "arms": bindings,
    }
    return arms, roster, sources


def _load_sealed_arm(*, key, spec, data_root, roster, scorer, split_role):
    arm = var1.load_arm(key=key, run_id=spec["run_id"], attempt_id=spec["attempt_id"],
                        data_root=data_root, roster=roster, scorer_id=scorer)
    if arm.manifest["split_role"] != split_role or arm.manifest["ids"] != roster["ids"]:
        raise FeedbackReadError(f"{key}: sealed manifest roster or role disagrees")
    manifest_doc = var1.load_json(arm.directory / f"{arm.run_id}.run-manifest.json")
    if (manifest_doc.get("outputs") or {}).get("sha256") != arm.outputs_sha256:
        raise FeedbackReadError(f"{key}: run manifest output SHA disagrees with sealed outputs")
    record_path = data_root / "attempts" / arm.run_id / f"{arm.attempt_id}.json"
    if var1.load_json(record_path).get("state") != "FINALIZED":
        raise FeedbackReadError(f"{key}: attempt is not FINALIZED")
    _exact_output_ids(arm.directory / f"{arm.run_id}.outputs.jsonl", roster["ids"])
    arm.fallback_flags = _explicit_fallback_flags(arm.directory, arm.run_id, roster["ids"])
    binding = {
        "run_id": arm.run_id, "attempt_id": arm.attempt_id,
        "run_manifest_sha256": arm.manifest["sha256"],
        "generation_manifest_sha256": arm.generation_manifest_sha256,
        "scores_sha256": arm.scores["sha256"],
        "outputs_sha256": arm.outputs_sha256,
        "phases_sha256": arm.runtime["sha256"],
        "attempt_record_sha256": var1.digest(record_path),
        "score_jobs_sha256": var1.digest(arm.directory / "score-jobs.jsonl"),
        "flight_receipts_sha256": arm.flight_receipts_sha256,
    }
    return arm, binding


def load_comparison_sources(repo_root: Path, data_root: Path, recipe_path: Path):
    """Load two declared sealed arms after checking their raw source hashes."""
    recipe_path = Path(recipe_path)
    if not recipe_path.is_absolute():
        recipe_path = _repo_path(repo_root, str(recipe_path))
    recipe = var1.load_json(recipe_path)
    if recipe.get("schema") != "saea-sealed-official-count-comparison-v1":
        raise FeedbackReadError("comparison recipe has the wrong schema")
    registration = recipe.get("registration")
    registration_sha = None
    if registration is not None:
        if not isinstance(registration, Mapping):
            raise FeedbackReadError("registration binding must be an object")
        registration_path = _repo_path(repo_root, registration.get("path"))
        registration_sha = _sha(registration.get("sha256"), "registration sha256")
        if var1.digest(registration_path) != registration_sha:
            raise FeedbackReadError("prospective registration SHA disagrees")
    roster_spec = recipe.get("roster") or {}
    roster_path = _repo_path(repo_root, roster_spec.get("relpath"))
    roster_sha = _sha(roster_spec.get("sha256"), "roster sha256")
    if var1.digest(roster_path) != roster_sha:
        raise FeedbackReadError("comparison roster SHA disagrees")
    split_role = roster_spec.get("split_role")
    if split_role != "discovery":
        raise FeedbackReadError("comparison read requires a discovery roster")
    cluster_key = recipe.get("cluster_key")
    if not isinstance(cluster_key, str) or not cluster_key:
        raise FeedbackReadError("comparison cluster key is missing")
    roster = var1.load_roster(repo_root, roster_spec["relpath"], cluster_key)
    if (roster["split_identity_hash"] != roster_spec.get("split_identity_hash")
            or roster["split_role"] != split_role or len(roster["ids"]) != roster_spec.get("rows")):
        raise FeedbackReadError("comparison roster identity, role, or count disagrees")
    specs = recipe.get("arms")
    if not isinstance(specs, Mapping) or len(specs) != 2:
        raise FeedbackReadError("comparison recipe must declare exactly two arms")
    comparisons = recipe.get("comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != 1 or not isinstance(comparisons[0], Mapping):
        raise FeedbackReadError("comparison recipe must declare one comparator pair")
    left, right = comparisons[0].get("left"), comparisons[0].get("right")
    if left == right or set((left, right)) != set(specs):
        raise FeedbackReadError("comparator pair must name the two distinct declared arms")
    stats = recipe.get("statistics") or {}
    seed, draws = stats.get("seed"), stats.get("draws")
    if isinstance(seed, bool) or not isinstance(seed, int) or isinstance(draws, bool) or not isinstance(draws, int) or draws < 2:
        raise FeedbackReadError("comparison seed or draws is invalid")
    arms, bindings = {}, {}
    scorers = set()
    # Establish every source pin before opening either arm's scores or answers.
    for key, spec in specs.items():
        _id(key, "arm id")
        if not isinstance(spec, Mapping):
            raise FeedbackReadError(f"{key}: arm must be an object")
        run = _id(spec.get("run_id"), f"{key} run_id")
        attempt = _id(spec.get("attempt_id"), f"{key} attempt_id")
        scorer = spec.get("scorer_id")
        if not isinstance(scorer, str) or not scorer:
            raise FeedbackReadError(f"{key}: scorer_id is missing")
        scorers.add(scorer)
        declared = spec.get("source_sha256") or {}
        directory = data_root / "runs" / run / attempt
        for name, path in (
            ("run_manifest", directory / f"{run}.run-manifest.json"),
            ("scores", directory / f"{run}.scores.json"),
            ("outputs", directory / f"{run}.outputs.jsonl"),
        ):
            expected = _sha(declared.get(name), f"{key} {name} sha256")
            if not path.is_file() or var1.digest(path) != expected:
                raise FeedbackReadError(f"{key}: {name} source SHA disagrees or file is missing")
        manifest = var1._load_run_manifest(directory, run, roster["split_identity_hash"])
        if manifest["split_role"] != split_role or manifest["ids"] != roster["ids"]:
            raise FeedbackReadError(f"{key}: sealed manifest roster or role disagrees")
        if (var1.load_json(directory / f"{run}.run-manifest.json").get("outputs") or {}).get("sha256") != declared["outputs"]:
            raise FeedbackReadError(f"{key}: run manifest output SHA disagrees")
        attempt_record = data_root / "attempts" / run / f"{attempt}.json"
        if not attempt_record.is_file() or var1.load_json(attempt_record).get("state") != "FINALIZED":
            raise FeedbackReadError(f"{key}: attempt is not FINALIZED")
    if len(scorers) != 1:
        raise FeedbackReadError("paired arms must use the same official scorer id")
    for key, spec in specs.items():
        scorer = spec["scorer_id"]
        arm, binding = _load_sealed_arm(key=key, spec=spec, data_root=data_root,
                                        roster=roster, scorer=scorer, split_role=split_role)
        arms[key], bindings[key] = arm, binding
    sources = {
        "comparison_recipe_sha256": var1.digest(recipe_path),
        "registration_sha256": registration_sha,
        "roster_sha256": roster_sha,
        "split_identity_hash": roster["split_identity_hash"],
        "scorer_id": next(iter(scorers)), "arms": bindings,
    }
    return arms, roster, sources, ((right, left),), (seed, draws)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--package")
    parser.add_argument("--comparison-recipe", type=Path,
                        help="A registered two-arm sealed-source comparison recipe")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--read-recipe", type=Path,
                        help="The pre-registered post-hoc derived-read recipe")
    parser.add_argument("--seed", type=int)
    parser.add_argument("--draws", type=int)
    args = parser.parse_args(argv)
    try:
        if args.comparison_recipe is not None:
            if any(value is not None for value in (args.package, args.read_recipe, args.seed, args.draws)):
                raise FeedbackReadError("comparison recipe mode cannot mix legacy package or statistics arguments")
            arms, roster, sources, pairs, (seed, draws) = load_comparison_sources(
                args.repo_root, args.data_root, args.comparison_recipe)
            result = analyze(arms, roster, seed=seed, draws=draws,
                             baseline_arm=pairs[0][1], comparison_pairs=pairs, extended=True)
        else:
            if args.package is None or args.read_recipe is None or args.seed is None or args.draws is None:
                raise FeedbackReadError("legacy mode requires package, read recipe, seed, and draws")
            read_recipe = var1.load_json(args.read_recipe)
            expected_facts = args.repo_root / args.package / "registered-facts-v1.json"
            if (read_recipe.get("driver") != "scripts/analysis/slurp_var1_official_feedback_v2.py"
                    or read_recipe.get("input_package_sha256") != var1.digest(expected_facts)
                    or (read_recipe.get("statistics") or {}).get("seed") != args.seed
                    or (read_recipe.get("statistics") or {}).get("draws") != args.draws):
                raise FeedbackReadError("derived-read preregistration, source facts, seed, or draws disagree")
            arms, roster, sources = load_sources(args.repo_root, args.data_root, args.package)
            result = analyze(arms, roster, seed=args.seed, draws=args.draws)
            sources["derived_read_recipe_sha256"] = var1.digest(args.read_recipe)
    except (FeedbackReadError, FeedbackError, var1.Var1ReadError) as exc:
        parser.exit(2, f"refused: {exc}\n")
    result["sources"] = sources
    args.out.parent.mkdir(parents=True, exist_ok=True)
    var1.write_json(args.out, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
