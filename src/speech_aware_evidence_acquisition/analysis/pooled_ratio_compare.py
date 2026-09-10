"""Model-free pooled-ratio comparisons over hash-pinned saved row artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

from .paired import PairedAnalysisError, resampled_statistic

SCHEMA = "saea-pooled-ratio-comparison-v1"


class PooledRatioError(ValueError):
    """A comparison declaration or saved row artifact is invalid."""


class _ZeroDenominator(PooledRatioError):
    pass


def _field(row: Mapping[str, object], path: str) -> float:
    value: object = row
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise PooledRatioError(f"row is missing field path {path!r}")
        value = value[part]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PooledRatioError(f"field {path!r} must be a finite nonnegative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise PooledRatioError(f"field {path!r} must be a finite nonnegative number")
    return result


def _totals(rows, ids: Sequence[str], numerator: str, denominator: str) -> tuple[float, float]:
    return (
        sum(_field(rows[sid], numerator) for sid in ids),
        sum(_field(rows[sid], denominator) for sid in ids),
    )


def _pooled_ratio(rows, ids: Sequence[str], numerator: str, denominator: str) -> float:
    num, den = _totals(rows, ids, numerator, denominator)
    if den <= 0:
        raise _ZeroDenominator("pooled denominator is zero")
    return num / den


def _gain(left: float, right: float, direction: str) -> float:
    return left - right if direction == "lower" else right - left


def _group_value(value: object, field: str) -> str:
    if isinstance(value, str) and value:
        return value
    if not isinstance(value, bool) and isinstance(value, (int, float)):
        if math.isfinite(float(value)):
            return str(value)
    raise PooledRatioError(f"metadata field {field!r} must be nonempty text or finite number")


def _bootstrap_json(result) -> dict[str, object]:
    raw = result.as_json()
    for key in ("point_estimate", "sigma_hat", "ci_low", "ci_high"):
        raw[key] = 100.0 * float(raw[key])
    raw["units"] = "percentage-points"
    return raw


def _cluster_bootstrap_safe(rows, ids, numerator, denominator, metadata, cluster_field):
    clusters: dict[str, list[str]] = {}
    for sid in ids:
        clusters.setdefault(str(metadata[sid][cluster_field]), []).append(sid)
    return all(_totals(rows, members, numerator, denominator)[1] > 0 for members in clusters.values())


def _summary(left, right, ids, numerator, denominator, direction, metadata, cluster_field,
             seed, n_replicates, ci_level, strata_field=None, frozen_strata=()):
    try:
        left_ratio = _pooled_ratio(left, ids, numerator, denominator)
        right_ratio = _pooled_ratio(right, ids, numerator, denominator)
    except _ZeroDenominator:
        return {"status": "unavailable", "reason": "zero pooled denominator"}
    result = {
        "status": "available", "n": len(ids),
        "left_ratio_pct": 100.0 * left_ratio,
        "right_ratio_pct": 100.0 * right_ratio,
        "gain_pp": 100.0 * _gain(left_ratio, right_ratio, direction),
    }
    safe = _cluster_bootstrap_safe(left, ids, numerator, denominator, metadata, cluster_field)
    safe = safe and _cluster_bootstrap_safe(right, ids, numerator, denominator, metadata, cluster_field)
    if not safe:
        result["bootstrap"] = {"status": "unavailable", "reason": "a resampleable cluster has zero pooled denominator"}
        return result

    def statistic(sample_ids):
        if strata_field is None:
            return _gain(
                _pooled_ratio(left, sample_ids, numerator, denominator),
                _pooled_ratio(right, sample_ids, numerator, denominator), direction,
            )
        gains = []
        for name in frozen_strata:
            members = [
                sid for sid in sample_ids
                if _group_value(metadata[sid][strata_field], strata_field) == name
            ]
            gains.append(_gain(
                _pooled_ratio(left, members, numerator, denominator),
                _pooled_ratio(right, members, numerator, denominator), direction,
            ))
        return sum(gains) / len(gains)

    try:
        boot = resampled_statistic(
            sample_ids=ids, statistic=statistic, seed=seed,
            n_replicates=n_replicates, ci_level=ci_level,
            cluster_of=lambda sid: str(metadata[sid][cluster_field]),
            strata_of=(None if strata_field is None else lambda sid: str(metadata[sid][strata_field])),
        )
    except (PairedAnalysisError, PooledRatioError) as error:
        raise PooledRatioError(str(error)) from error
    result["bootstrap"] = _bootstrap_json(boot)
    return result


def compare_pooled_ratios(left, right, metadata, metrics, *, groupings, seed,
                          n_replicates, ci_level, cluster_field="cluster"):
    """Compare exact paired rosters with pooled ratios and clustered uncertainty."""
    if not left or set(left) != set(right) or set(left) != set(metadata):
        raise PooledRatioError("left/right/metadata roster mismatch")
    ids = tuple(sorted(left))
    if not isinstance(metrics, Mapping) or not metrics:
        raise PooledRatioError("metrics must be a nonempty mapping")
    if not isinstance(groupings, Mapping):
        raise PooledRatioError("groupings must be a mapping")
    for sid in ids:
        if not isinstance(left[sid], Mapping) or not isinstance(right[sid], Mapping):
            raise PooledRatioError("input rows must be mappings")
        if not isinstance(metadata[sid], Mapping) or not isinstance(metadata[sid].get(cluster_field), str):
            raise PooledRatioError(f"metadata must carry text {cluster_field!r} for every id")
    for label, field in groupings.items():
        if not isinstance(label, str) or not label or not isinstance(field, str) or not field:
            raise PooledRatioError("groupings must map names to metadata fields")
        by_cluster = {}
        for sid in ids:
            value = _group_value(metadata[sid].get(field), field)
            cluster = metadata[sid][cluster_field]
            if cluster in by_cluster and by_cluster[cluster] != value:
                raise PooledRatioError(f"grouping {field!r} is not constant inside cluster {cluster!r}")
            by_cluster[cluster] = value

    output = {}
    for metric_name, spec in metrics.items():
        if not isinstance(metric_name, str) or not isinstance(spec, Mapping):
            raise PooledRatioError("metric declarations must be named mappings")
        numerator, denominator, direction = (
            spec.get("numerator_field"), spec.get("denominator_field"), spec.get("direction")
        )
        if not isinstance(numerator, str) or not isinstance(denominator, str) or direction not in {"lower", "higher"}:
            raise PooledRatioError("each metric requires numerator_field, denominator_field and lower/higher direction")
        natural = _summary(left, right, ids, numerator, denominator, direction, metadata,
                           cluster_field, seed, n_replicates, ci_level)
        signs = {"saves": 0, "harms": 0, "ties": 0, "unavailable": 0}
        for sid in ids:
            try:
                delta = _gain(_pooled_ratio(left, [sid], numerator, denominator),
                              _pooled_ratio(right, [sid], numerator, denominator), direction)
            except _ZeroDenominator:
                signs["unavailable"] += 1
            else:
                signs["saves" if delta > 0 else "harms" if delta < 0 else "ties"] += 1
        grouped = {}
        for label, field in groupings.items():
            strata = tuple(sorted({_group_value(metadata[sid][field], field) for sid in ids}))
            per = {}
            unavailable = False
            for name in strata:
                members = [
                    sid for sid in ids
                    if _group_value(metadata[sid][field], field) == name
                ]
                row = _summary(left, right, members, numerator, denominator, direction,
                               metadata, cluster_field, seed, 1, ci_level)
                row.pop("bootstrap", None)
                per[name] = row
                unavailable |= row["status"] != "available"
            if unavailable:
                equal = {"status": "unavailable", "reason": "one or more frozen strata has zero pooled denominator"}
            else:
                equal = _summary(left, right, ids, numerator, denominator, direction,
                                 metadata, cluster_field, seed, n_replicates, ci_level,
                                 strata_field=field, frozen_strata=strata)
                equal["left_ratio_pct"] = sum(per[name]["left_ratio_pct"] for name in strata) / len(strata)
                equal["right_ratio_pct"] = sum(per[name]["right_ratio_pct"] for name in strata) / len(strata)
                equal["gain_pp"] = sum(per[name]["gain_pp"] for name in strata) / len(strata)
            grouped[label] = {
                "natural_mixture": natural,
                "per_stratum": per,
                "equal_stratum": equal,
            }
        output[metric_name] = {"direction": direction, "natural_mixture": natural,
                               "sign_counts": signs, "groupings": grouped}
    return output


def _pinned(binding):
    path, expected = Path(binding["path"]), binding["sha256"]
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise PooledRatioError(f"hash mismatch for {path}: {actual} != {expected}")
    try:
        return json.loads(raw), {"path": str(path), "sha256": actual}
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PooledRatioError(f"invalid JSON artifact {path}: {error}") from error


def _at(document, dotted):
    value = document
    if dotted:
        for part in dotted.split("."):
            if not isinstance(value, Mapping) or part not in value:
                raise PooledRatioError(f"rows_key {dotted!r} does not resolve")
            value = value[part]
    return value


def _table(value, id_field):
    result = {}
    items = value.items() if isinstance(value, Mapping) else enumerate(value) if isinstance(value, list) else ()
    for key, row in items:
        if not isinstance(row, Mapping):
            raise PooledRatioError("every table row must be a mapping")
        sid = row.get(id_field, key if isinstance(key, str) else None)
        if not isinstance(sid, str) or not sid or sid in result:
            raise PooledRatioError("table ids must be unique nonempty text")
        if isinstance(key, str) and id_field in row and row[id_field] != key:
            raise PooledRatioError("table mapping key disagrees with row id")
        result[sid] = row
    if not result:
        raise PooledRatioError("table must be a nonempty mapping or list")
    return result


def run(config_path: Path, output_path: Path):
    config_raw = Path(config_path).read_bytes()
    config = json.loads(config_raw)
    if config.get("execution_profile") != "model-free-check":
        raise PooledRatioError("execution_profile must be model-free-check")
    spec = config.get("analysis")
    if not isinstance(spec, Mapping):
        raise PooledRatioError("config requires analysis mapping")
    id_field = spec.get("id_field")
    expected = spec.get("expected_ids_count")
    if not isinstance(id_field, str) or not id_field or isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
        raise PooledRatioError("id_field and positive expected_ids_count are required")
    metadata_doc, metadata_pin = _pinned(spec["metadata"])
    metadata = _table(_at(metadata_doc, spec["metadata"].get("rows_key")), id_field)
    tables, pins = {}, {}
    for name, binding in spec["inputs"].items():
        document, pin = _pinned(binding)
        tables[name] = _table(_at(document, binding.get("rows_key")), id_field)
        pins[name] = pin
    if len(metadata) != expected or any(set(table) != set(metadata) for table in tables.values()):
        raise PooledRatioError("input/metadata roster mismatch or expected_ids_count mismatch")
    results = {}
    for contrast in spec["contrasts"]:
        name, left_name, right_name = contrast.get("name"), contrast.get("left"), contrast.get("right")
        if not isinstance(name, str) or name in results or left_name not in tables or right_name not in tables:
            raise PooledRatioError("contrasts require unique names and existing left/right inputs")
        results[name] = compare_pooled_ratios(
            tables[left_name], tables[right_name], metadata, spec["metrics"],
            groupings=spec["groupings"], seed=spec["seed"],
            n_replicates=spec["n_replicates"], ci_level=spec["ci_level"],
            cluster_field=spec.get("cluster_field", "cluster"),
        )
    result = {"schema": SCHEMA, "execution_profile": "model-free-check",
              "provenance": {"config_path": str(config_path),
                             "config_sha256": hashlib.sha256(config_raw).hexdigest(),
                             "inputs": pins, "metadata": metadata_pin,
                             "expected_ids_count": expected},
              "contrasts": results}
    with Path(output_path).open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, sort_keys=True, indent=2)
        handle.write("\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    run(args.config, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())