"""Config-driven analysis of existing null score jobs; never invokes scoring."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from ..core.bundle.verify import verify_bundle
from ..data.variant_ids import published_sample_key
from .null_calibration import calibrate_null


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinned_json(binding: dict) -> dict:
    path = Path(binding["path"])
    if digest(path) != binding["sha256"]:
        raise ValueError(f"analysis source hash mismatch: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def rows_for(document: dict, scorer: str, fields: tuple[str, ...], *, view: str | None = None) -> dict:
    if document.get("verified") is not True:
        raise ValueError("unverified score job")
    # Complete finalization jobs retain the score path plus inline score_details;
    # read-only score jobs carry the same data directly under scores.
    scores = document.get("scores")
    if isinstance(scores, str):
        scores = document.get("score_details")
    if not isinstance(scores, dict):
        raise ValueError("score job has no retained per-sample score details")
    try:
        entry = scores[scorer]
    except KeyError:
        raise ValueError(f"score job has no scorer {scorer!r}") from None
    if not isinstance(entry, dict):
        raise ValueError(f"score job scorer {scorer!r} is malformed")
    if view is None:
        rows_source = entry.get("per_sample")
    else:
        if not isinstance(view, str) or not view:
            raise ValueError("score view must be a non-empty string")
        views = entry.get("views")
        if not isinstance(views, dict) or view not in views:
            raise ValueError(f"score job scorer {scorer!r} has no view {view!r}")
        selected = views[view]
        if not isinstance(selected, dict):
            raise ValueError(f"score view {view!r} is malformed")
        rows_source = selected.get("per_sample")
    if not isinstance(rows_source, list):
        location = "top-level" if view is None else f"view {view!r}"
        raise ValueError(f"score job scorer {scorer!r} has no retained {location} per-sample rows")
    rows = {}
    for row in rows_source:
        sid = published_sample_key(row["sample_id"])
        if sid in rows:
            raise ValueError("duplicate published sample ID")
        values = {**row, **row.get("normalized", {})}
        try:
            rows[sid] = {field: float(values[field]) for field in fields}
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                f"score row {sid!r} is missing or has invalid retained field"
            ) from error
    if not rows:
        raise ValueError("empty score job")
    return rows


def run(config_path: Path, output_dir: Path, *, verifier=verify_bundle) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("execution_profile") != "model-free-check":
        raise ValueError("calibration accepts only a model-free-check")
    spec = config["analysis"]
    metadata = pinned_json(spec["metadata"])["rows"]
    ids = sorted(row["id"] for row in pinned_json(spec["roster"])["items"])
    all_ids = {row["id"] for row in pinned_json(spec["full_roster"])["items"]}
    if len(ids) != len(set(ids)) or not set(ids) <= all_ids or set(metadata) != all_ids:
        raise ValueError("roster/metadata identity mismatch")
    batch_dir = Path(spec["score_batch"])
    batch_path = batch_dir / "batch-summary.json"
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    if batch.get("failed") != 0:
        raise ValueError("source score batch has failures")
    names = (spec["left_job"], spec["right_job"])
    documents, sources = {}, []
    for name in names:
        jobs = [job for job in batch["jobs"] if job["job_id"] == name]
        if len(jobs) != 1 or jobs[0]["status"] != "succeeded":
            raise ValueError("source job is not uniquely successful")
        job = jobs[0]
        score_path = batch_dir / job["result_file"]
        if score_path.resolve().parent != batch_dir.resolve():
            raise ValueError("score job escapes its batch directory")
        document = pinned_json(
            {"path": str(score_path), "sha256": job["result_sha256"]}
        )
        manifest = Path(document["manifest"])
        if str(manifest) != job["manifest"]:
            raise ValueError("score/manifest binding mismatch")
        verifier(manifest)
        documents[name] = document
        sources.append(
            {
                "job_id": name,
                "score_path": str(score_path),
                "score_sha256": digest(score_path),
                "manifest_path": str(manifest),
                "manifest_sha256": digest(manifest),
            }
        )
    fields = tuple(
        sorted(
            set(spec["metrics"])
            | {
                field
                for groups in spec["micro_metrics"].values()
                for group in groups
                for field in group
            }
        )
    )
    results = {}
    for scorer in spec["scorers"]:
        left, right = [rows_for(documents[name], scorer, fields) for name in names]
        if set(left) != all_ids or set(right) != all_ids:
            raise ValueError("source score roster does not match frozen full roster")
        results[scorer] = calibrate_null(
            left,
            right,
            sample_ids=ids,
            metrics=spec["metrics"],
            cluster_of=lambda sid: metadata[sid]["speaker"],
            strata_of=lambda sid: metadata[sid]["scenario"],
            micro_metrics=spec["micro_metrics"],
            seed=spec["seed"],
            n_replicates=spec["n_replicates"],
        )
    result = {
        "schema": "saea-null-calibration-receipt-v1",
        "experiment_id": config["experiment_id"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": {"path": str(config_path.resolve()), "sha256": digest(config_path)},
        "sources": sources,
        "score_batch_sha256": digest(batch_path),
        "roster": spec["roster"],
        "metadata": spec["metadata"],
        "implementation": [
            {"path": str(p), "sha256": digest(p)}
            for p in (
                Path(__file__),
                Path(__file__).with_name("null_calibration.py"),
                Path(__file__).with_name("paired.py"),
            )
        ],
        "model_calls": 0,
        "encoder_calls": 0,
        "tokenizer_calls": 0,
        "scorer_invocations": 0,
        "results": results,
        "historical_margins_unchanged_pp": {
            "pooled_micro": 1.1804,
            "pooled_per_row": 0.8188,
            "intent_efficacy_floor": 1.4341,
        },
    }
    # Exclusive creation refuses accidental overwriting of a frozen calibration.
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "calibration.json"
    with path.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.config, args.output_dir)
    print(
        json.dumps(
            {
                "experiment_id": result["experiment_id"],
                "results": {
                    name: {
                        metric: {
                            "delta_pp": row["delta_pp"],
                            "ci90_pp": row["ci90_pp"],
                            "margin_pp": row["margin_pp"],
                        }
                        for metric, row in item["metrics"].items()
                    }
                    for name, item in result["results"].items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
