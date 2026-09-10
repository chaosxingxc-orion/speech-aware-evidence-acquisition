"""Compare verified existing score artifacts using the shared paired analysis."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ..core.bundle.verify import verify_bundle
from .null_calibration_cli import digest, pinned_json, rows_for
from .null_calibration import pooled_f1
from .paired import paired_contrast, resampled_statistic


def _pooled_f1_family(left, right, *, ids, metadata, fields, grouping, seed,
                      n_replicates):
    """Return one pooled-count F1 estimate and its requested bootstrap family."""
    if grouping == "scenario":
        def strata_of(sid):
            return metadata[sid]["scenario"]
        cluster_of = None
    elif grouping == "speaker":
        strata_of = None
        def cluster_of(sid):
            return metadata[sid]["speaker"]
    else:
        raise ValueError("unknown pooled-F1 grouping")
    def statistic(sample_ids):
        return pooled_f1(right, sample_ids, fields) - pooled_f1(
            left, sample_ids, fields
        )
    bootstrap = resampled_statistic(
        sample_ids=ids, statistic=statistic, strata_of=strata_of,
        cluster_of=cluster_of, seed=seed, n_replicates=n_replicates,
        ci_level=0.90,
    ).as_json()
    # Descriptive rows and equal-stratum weighting are always scenario based;
    # speaker clustering changes only the bootstrap draws.
    strata_names = sorted({metadata[sid]["scenario"] for sid in ids})
    per_stratum = {}
    for stratum in strata_names:
        members = [sid for sid in ids if metadata[sid]["scenario"] == stratum]
        left_value = pooled_f1(left, members, fields)
        right_value = pooled_f1(right, members, fields)
        per_stratum[stratum] = {
            "n": len(members), "left_pct": 100 * left_value,
            "right_pct": 100 * right_value,
            "delta_pp": 100 * (right_value - left_value),
        }
    left_value = pooled_f1(left, ids, fields)
    right_value = pooled_f1(right, ids, fields)
    return {
        "left_pct": 100 * left_value, "right_pct": 100 * right_value,
        "delta_pp": 100 * (right_value - left_value),
        "ci90_pp": [100 * bootstrap["ci_low"], 100 * bootstrap["ci_high"]],
        "bootstrap": bootstrap, "per_stratum": per_stratum,
        "equal_stratum_delta_pp": sum(
            row["delta_pp"] for row in per_stratum.values()
        ) / len(per_stratum),
    }


def _micro_compare(left, right, *, ids, metadata, fields, seed, n_replicates):
    """Compare one declared pooled-count F1 identity."""
    return {
        "estimand": "pooled-count-f1",
        "fields": {name: list(group) for name, group in
                   zip(("tp", "fp", "fn"), fields)},
        "scenario_stratified": _pooled_f1_family(
            left, right, ids=ids, metadata=metadata, fields=fields,
            grouping="scenario", seed=seed, n_replicates=n_replicates,
        ),
        "speaker_clustered": _pooled_f1_family(
            left, right, ids=ids, metadata=metadata, fields=fields,
            grouping="speaker", seed=seed, n_replicates=n_replicates,
        ),
    }


def _micro_field_groups(raw):
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("analysis.micro_metrics must be a mapping")
    result = {}
    for name, groups in raw.items():
        claimed_fields = set()
        if not isinstance(name, str) or not name:
            raise ValueError("micro metric names must be non-empty strings")
        if isinstance(groups, dict):
            if set(groups) != {"tp", "fp", "fn"}:
                raise ValueError("micro metric groups must name exactly tp, fp, fn")
            groups = (groups["tp"], groups["fp"], groups["fn"])
        if not isinstance(groups, (list, tuple)) or len(groups) != 3:
            raise ValueError("micro metric groups must contain tp, fp, fn groups")
        normalized = []
        for group in groups:
            if isinstance(group, str) or not isinstance(group, (list, tuple)) or not group:
                raise ValueError("each micro count group must be a nonempty list")
            if any(not isinstance(field, str) or not field for field in group):
                raise ValueError("micro count fields must be nonempty strings")
            if len(set(group)) != len(group) or set(group) & claimed_fields:
                raise ValueError("micro count fields must be unique and non-overlapping")
            claimed_fields.update(group)
            normalized.append(tuple(group))
        result[name] = tuple(normalized)
    return result


def compare(left, right, *, ids, metadata, metric, seed, n_replicates):
    """Retain the historical stratified estimate and the clustered sensitivity."""
    if set(left) != set(right) or not set(ids) <= set(left):
        raise ValueError("source population mismatch")
    common = dict(metrics=[metric], sample_ids=ids, seed=seed,
                  n_replicates=n_replicates, ci_level=0.90)
    stratified = paired_contrast(left, right, strata_of=lambda sid: metadata[sid]["scenario"],
                                 **common)[metric].as_dict()
    clustered = paired_contrast(left, right, cluster_of=lambda sid: metadata[sid]["speaker"],
                                **common)[metric].as_dict()
    strata = stratified["per_stratum"]
    return {"scenario_stratified": stratified, "speaker_clustered": clustered,
            "equal_stratum_delta": sum(row["delta"] for row in strata.values()) / len(strata)}


def run(config_path: Path, output: Path, *, verifier=verify_bundle):
    """Read only hash-pinned, complete, verified score jobs; never call a scorer."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("execution_profile") != "model-free-check":
        raise ValueError("analysis requires model-free-check")
    spec = config["analysis"]
    metadata = pinned_json(spec["metadata"])["rows"]
    full = [row["id"] for row in pinned_json(spec["full_roster"])["items"]]
    primary = [row["id"] for row in pinned_json(spec["roster"])["items"]]
    if (len(set(full)) != len(full) or len(set(primary)) != len(primary)
            or set(metadata) != set(full) or not set(primary) <= set(full)):
        raise ValueError("roster/metadata identity mismatch")
    populations = {"NEW500": sorted(primary), "DEV1000": sorted(full)}
    remainder = sorted(set(full) - set(primary))
    if remainder:
        populations["OLD500"] = remainder
    for name, binding in spec.get("additional_populations", {}).items():
        ids = pinned_json(binding)["sample_ids"]
        if name in populations or len(ids) != len(set(ids)) or not set(ids) <= set(primary):
            raise ValueError("invalid additional population")
        populations[name] = sorted(ids)
    micro_metrics = _micro_field_groups(spec.get("micro_metrics"))
    requested_fields = list(spec["metrics"])
    for groups in micro_metrics.values():
        for group in groups:
            requested_fields.extend(group)
    requested_fields = tuple(dict.fromkeys(requested_fields))
    tables, sources = {}, {}
    for name, binding in spec["inputs"].items():
        document = pinned_json(binding["score"])
        pinned_json(binding["manifest"])
        manifest = Path(binding["manifest"]["path"])
        if Path(document["manifest"]).resolve() != manifest.resolve():
            raise ValueError("score/manifest identity mismatch")
        verifier(manifest)
        tables[name] = {}
        for alias, scorer_binding in binding["scorers"].items():
            if isinstance(scorer_binding, str):
                scorer, view = scorer_binding, None
            elif isinstance(scorer_binding, dict):
                if set(scorer_binding) - {"scorer", "view"}:
                    raise ValueError("invalid scorer alias binding")
                scorer = scorer_binding.get("scorer")
                view = scorer_binding.get("view")
            else:
                raise ValueError("scorer alias binding must be a scorer id or object")
            if not isinstance(scorer, str) or not scorer:
                raise ValueError("scorer alias binding has no scorer id")
            rows = rows_for(document, scorer, requested_fields, view=view)
            if set(rows) != set(full):
                raise ValueError("score roster mismatch")
            tables[name][alias] = rows
        sources[name] = binding
    results = {}
    for contrast in spec["contrasts"]:
        name = contrast["name"]
        if name in results:
            raise ValueError("duplicate contrast")
        results[name] = {}
        selected = contrast.get("populations", list(populations))
        if not selected or len(selected) != len(set(selected)) or not set(selected) <= set(populations):
            raise ValueError("contrast population selection is invalid")
        for population in selected:
            ids = populations[population]
            results[name][population] = {}
            for scorer in contrast["scorers"]:
                metric_results = {
                    metric: compare(
                        tables[contrast["left"]][scorer], tables[contrast["right"]][scorer],
                        ids=ids, metadata=metadata, metric=metric,
                        seed=spec["seed"] + offset, n_replicates=spec["n_replicates"])
                    for offset, metric in enumerate(spec["metrics"])
                }
                for micro_name, fields in micro_metrics.items():
                    if micro_name in metric_results:
                        raise ValueError("micro metric collides with mean metric")
                    metric_results[micro_name] = _micro_compare(
                        tables[contrast["left"]][scorer],
                        tables[contrast["right"]][scorer],
                        ids=ids, metadata=metadata, fields=fields,
                        seed=spec["seed"],
                        n_replicates=spec["n_replicates"])
                results[name][population][scorer] = metric_results
    result = {
        "schema": "saea-existing-score-contrasts-v1",
        "experiment_id": config["experiment_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.resolve()), "sha256": digest(config_path)},
        "sources": sources, "metadata": spec["metadata"],
        "populations": {name: len(ids) for name, ids in populations.items()},
        "population_bindings": {key: spec[key] for key in
                               ("roster", "full_roster", "additional_populations") if key in spec},
        "implementation": [{"path": str(path), "sha256": digest(path)} for path in
                           tuple(
                               [Path(__file__), Path(__file__).with_name("paired.py")]
                               + ([Path(__file__).with_name("null_calibration.py")]
                                  if micro_metrics else [])
                               + ([Path(__file__).with_name("null_calibration_cli.py")]
                                  if any(
                                      isinstance(binding.get("scorers"), dict)
                                      and any(isinstance(value, dict) and value.get("view") is not None
                                              for value in binding["scorers"].values())
                                      for binding in spec["inputs"].values()
                                  ) else [])
                           )],
        "model_calls": 0, "encoder_calls": 0, "tokenizer_calls": 0,
        "scorer_invocations": 0, "results": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.config, args.output)
    print(json.dumps({"experiment_id": result["experiment_id"],
                      "populations": result["populations"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
