"""Compare verified existing score artifacts using the shared paired analysis."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ..core.bundle.verify import verify_bundle
from .null_calibration_cli import digest, pinned_json, rows_for
from .paired import paired_contrast


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
    tables, sources = {}, {}
    for name, binding in spec["inputs"].items():
        document = pinned_json(binding["score"])
        pinned_json(binding["manifest"])
        manifest = Path(binding["manifest"]["path"])
        if Path(document["manifest"]).resolve() != manifest.resolve():
            raise ValueError("score/manifest identity mismatch")
        verifier(manifest)
        tables[name] = {}
        for alias, scorer in binding["scorers"].items():
            rows = rows_for(document, scorer, tuple(spec["metrics"]))
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
            results[name][population] = {
                scorer: {
                    metric: compare(
                        tables[contrast["left"]][scorer], tables[contrast["right"]][scorer],
                        ids=ids, metadata=metadata, metric=metric,
                        seed=spec["seed"] + offset, n_replicates=spec["n_replicates"])
                    for offset, metric in enumerate(spec["metrics"])}
                for scorer in contrast["scorers"]}
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
                           (Path(__file__), Path(__file__).with_name("paired.py"))],
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
