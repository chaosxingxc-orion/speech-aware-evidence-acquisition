"""Model-free pooled-ratio comparisons over hash-pinned saved row artifacts."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
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


def _validate_max_workers(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PooledRatioError("analysis.max_workers must be a positive integer")
    return value


def _field(row: Mapping[str, object], path: str) -> float:
    value: object = row
    for part in path.split("."):
        if isinstance(value, Mapping) and part in value:
            value = value[part]
        elif isinstance(value, (list, tuple)) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise PooledRatioError(f"row is missing field path {path!r}")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PooledRatioError(f"field {path!r} must be a finite nonnegative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise PooledRatioError(f"field {path!r} must be a finite nonnegative number")
    return result


def _numerator(row: Mapping[str, object], fields: str | Sequence[str]) -> float:
    if isinstance(fields, str):
        return _field(row, fields)
    return sum(_field(row, field) for field in fields)


def _totals(rows, ids: Sequence[str], numerator: str | Sequence[str], denominator: str) -> tuple[float, float]:
    return (
        sum(_numerator(rows[sid], numerator) for sid in ids),
        sum(_field(rows[sid], denominator) for sid in ids),
    )


def _pooled_ratio(
    rows,
    ids: Sequence[str],
    numerator: str | Sequence[str],
    denominator: str,
    *,
    zero_denominator: str = "unavailable",
) -> float:
    num, den = _totals(rows, ids, numerator, denominator)
    if den <= 0:
        if zero_denominator == "zero":
            return 0.0
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



def _summary(left, right, ids, numerator, denominator, direction, metadata, cluster_field,
             seed, n_replicates, ci_level, strata_field=None, frozen_strata=(),
             grouping_resampling="within-stratum", zero_denominator="unavailable"):
    try:
        left_ratio = _pooled_ratio(left, ids, numerator, denominator, zero_denominator=zero_denominator)
        right_ratio = _pooled_ratio(right, ids, numerator, denominator, zero_denominator=zero_denominator)
    except _ZeroDenominator:
        return {"status": "unavailable", "reason": "zero pooled denominator"}
    result = {
        "status": "available", "n": len(ids),
        "left_ratio_pct": 100.0 * left_ratio,
        "right_ratio_pct": 100.0 * right_ratio,
        "gain_pp": 100.0 * _gain(left_ratio, right_ratio, direction),
    }
    def statistic(sample_ids):
        if strata_field is None:
            return _gain(
                _pooled_ratio(
                    left, sample_ids, numerator, denominator,
                    zero_denominator=zero_denominator,
                ),
                _pooled_ratio(
                    right, sample_ids, numerator, denominator,
                    zero_denominator=zero_denominator,
                ),
                direction,
            )
        gains = []
        for name in frozen_strata:
            members = [
                sid for sid in sample_ids
                if _group_value(metadata[sid][strata_field], strata_field) == name
            ]
            if not members:
                raise _ZeroDenominator("bootstrap draw omits a frozen stratum")
            gains.append(_gain(
                _pooled_ratio(
                    left, members, numerator, denominator,
                    zero_denominator=zero_denominator,
                ),
                _pooled_ratio(
                    right, members, numerator, denominator,
                    zero_denominator=zero_denominator,
                ),
                direction,
            ))
        return sum(gains) / len(gains)

    try:
        boot = resampled_statistic(
            sample_ids=ids, statistic=statistic, seed=seed,
            n_replicates=n_replicates, ci_level=ci_level,
            cluster_of=lambda sid: str(metadata[sid][cluster_field]),
            strata_of=(
                None
                if strata_field is None or grouping_resampling == "whole-cluster"
                else lambda sid: str(metadata[sid][strata_field])
            ),
        )
    except _ZeroDenominator:
        result["bootstrap"] = {
            "status": "unavailable",
            "reason": "at least one realized bootstrap draw has zero pooled denominator",
        }
        return result
    except PairedAnalysisError as error:
        raise PooledRatioError(str(error)) from error
    result["bootstrap"] = _bootstrap_json(boot)
    return result


def _equal_cluster_summary(left, right, ids, numerator, denominator, direction,
                           metadata, cluster_field, seed, n_replicates, ci_level,
                           zero_denominator="unavailable"):
    """Average eligible cluster rates, retaining bootstrap draw multiplicity."""
    members = {}
    for sid in ids:
        members.setdefault(metadata[sid][cluster_field], []).append(sid)
    rates, excluded = {}, []
    for cluster, cluster_ids in sorted(members.items()):
        try:
            rates[cluster] = (
                _pooled_ratio(
                    left, cluster_ids, numerator, denominator,
                    zero_denominator=zero_denominator,
                ),
                _pooled_ratio(
                    right, cluster_ids, numerator, denominator,
                    zero_denominator=zero_denominator,
                ),
            )
        except _ZeroDenominator:
            excluded.append(cluster)
    result = {
        "status": "available" if rates else "unavailable",
        "clusters": len(members),
        "eligible_clusters": len(rates),
        "excluded_zero_denominator_clusters": excluded,
        "weighting": (
            "equal per cluster with scorer-defined zero denominators"
            if zero_denominator == "zero"
            else "equal per cluster with a positive denominator in both arms"
        ),
    }
    if not rates:
        result["reason"] = "no eligible cluster rate"
        return result
    result.update({
        "left_ratio_pct": 100.0 * sum(a for a, _ in rates.values()) / len(rates),
        "right_ratio_pct": 100.0 * sum(b for _, b in rates.values()) / len(rates),
        "gain_pp": 100.0 * sum(_gain(a, b, direction) for a, b in rates.values()) / len(rates),
    })

    def statistic(drawn_clusters):
        gains = [_gain(*rates[name], direction) for name in drawn_clusters if name in rates]
        if not gains:
            raise _ZeroDenominator("draw has no eligible cluster rate")
        return sum(gains) / len(gains)

    try:
        # Sample the same complete cluster roster as the natural bootstrap.
        # A repeated cluster contributes its rate once for each occurrence.
        boot = resampled_statistic(
            sample_ids=tuple(sorted(members)), statistic=statistic, seed=seed,
            n_replicates=n_replicates, ci_level=ci_level, cluster_of=lambda name: name,
        )
    except _ZeroDenominator:
        result["bootstrap"] = {
            "status": "unavailable",
            "reason": "at least one realized bootstrap draw has no eligible cluster rate",
        }
    else:
        result["bootstrap"] = _bootstrap_json(boot)
    return result


def compare_pooled_ratios(left, right, metadata, metrics, *, groupings, seed,
                          n_replicates, ci_level, cluster_field="cluster",
                          include_equal_cluster_mean=False,
                          grouping_resampling="within-stratum"):
    """Compare exact paired rosters with pooled ratios and clustered uncertainty."""
    if not left or set(left) != set(right) or set(left) != set(metadata):
        raise PooledRatioError("left/right/metadata roster mismatch")
    if not isinstance(include_equal_cluster_mean, bool):
        raise PooledRatioError("include_equal_cluster_mean must be boolean")
    if grouping_resampling not in {"within-stratum", "whole-cluster"}:
        raise PooledRatioError(
            "grouping_resampling must be within-stratum or whole-cluster"
        )
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
        if grouping_resampling == "within-stratum":
            by_cluster = {}
            for sid in ids:
                value = _group_value(metadata[sid].get(field), field)
                cluster = metadata[sid][cluster_field]
                if cluster in by_cluster and by_cluster[cluster] != value:
                    raise PooledRatioError(
                        f"grouping {field!r} is not constant inside cluster {cluster!r}"
                    )
                by_cluster[cluster] = value

    output = {}
    for metric_name, spec in metrics.items():
        if not isinstance(metric_name, str) or not isinstance(spec, Mapping):
            raise PooledRatioError("metric declarations must be named mappings")
        numerator, denominator, direction, zero_denominator = (
            spec.get("numerator_field"),
            spec.get("denominator_field"),
            spec.get("direction"),
            spec.get("zero_denominator", "unavailable"),
        )
        numerator_valid = isinstance(numerator, str) and bool(numerator)
        if isinstance(numerator, list):
            numerator_valid = bool(numerator) and all(
                isinstance(field, str) and field for field in numerator
            )
        if (
            not numerator_valid
            or not isinstance(denominator, str)
            or not denominator
            or direction not in {"lower", "higher"}
            or zero_denominator not in {"unavailable", "zero"}
        ):
            raise PooledRatioError(
                "each metric requires numerator_field, denominator_field, "
                "lower/higher direction, and unavailable/zero denominator handling"
            )
        natural = _summary(left, right, ids, numerator, denominator, direction, metadata,
                           cluster_field, seed, n_replicates, ci_level,
                           zero_denominator=zero_denominator)
        signs = {"saves": 0, "harms": 0, "ties": 0, "unavailable": 0}
        for sid in ids:
            try:
                delta = _gain(
                    _pooled_ratio(
                        left, [sid], numerator, denominator,
                        zero_denominator=zero_denominator,
                    ),
                    _pooled_ratio(
                        right, [sid], numerator, denominator,
                        zero_denominator=zero_denominator,
                    ),
                    direction,
                )
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
                               metadata, cluster_field, seed, 1, ci_level,
                               zero_denominator=zero_denominator)
                row.pop("bootstrap", None)
                per[name] = row
                unavailable |= row["status"] != "available"
            if unavailable:
                equal = {"status": "unavailable", "reason": "one or more frozen strata has zero pooled denominator"}
            else:
                equal = _summary(left, right, ids, numerator, denominator, direction,
                                 metadata, cluster_field, seed, n_replicates, ci_level,
                                 strata_field=field, frozen_strata=strata,
                                 grouping_resampling=grouping_resampling,
                                 zero_denominator=zero_denominator)
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
        if include_equal_cluster_mean:
            output[metric_name]["equal_cluster_mean"] = _equal_cluster_summary(
                left, right, ids, numerator, denominator, direction, metadata,
                cluster_field, seed, n_replicates, ci_level,
                zero_denominator=zero_denominator,
            )
    return output


def _compare_contrast(task):
    name, left, right, metadata, metrics, options = task
    return name, compare_pooled_ratios(left, right, metadata, metrics, **options)


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
    contrasts = spec["contrasts"]
    if not isinstance(contrasts, list) or not contrasts:
        raise PooledRatioError("analysis.contrasts must be a nonempty list")
    requested_workers = _validate_max_workers(spec.get("max_workers", 1))
    effective_workers = min(requested_workers, len(contrasts))
    options = {
        "groupings": spec["groupings"],
        "seed": spec["seed"],
        "n_replicates": spec["n_replicates"],
        "ci_level": spec["ci_level"],
        "cluster_field": spec.get("cluster_field", "cluster"),
        "include_equal_cluster_mean": spec.get("include_equal_cluster_mean", False),
        "grouping_resampling": spec.get("grouping_resampling", "within-stratum"),
    }
    tasks = []
    names = set()
    for contrast in contrasts:
        name, left_name, right_name = contrast.get("name"), contrast.get("left"), contrast.get("right")
        if not isinstance(name, str) or name in names or left_name not in tables or right_name not in tables:
            raise PooledRatioError("contrasts require unique names and existing left/right inputs")
        names.add(name)
        tasks.append((name, tables[left_name], tables[right_name], metadata, spec["metrics"], options))
    if effective_workers == 1:
        completed = [_compare_contrast(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=effective_workers) as executor:
            completed = list(executor.map(_compare_contrast, tasks))
    results = dict(completed)
    source_path = Path(__file__)
    result = {"schema": SCHEMA, "execution_profile": "model-free-check",
              "provenance": {"config_path": str(config_path),
                             "config_sha256": hashlib.sha256(config_raw).hexdigest(),
                             "inputs": pins, "metadata": metadata_pin,
                             "expected_ids_count": expected,
                             "implementation": {
                                 "relpath": "src/speech_aware_evidence_acquisition/analysis/pooled_ratio_compare.py",
                                 "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                             },
                             "contacts": {"model": 0, "scorer": 0, "reference": 0}},
              "contrasts": results}
    if "max_workers" in spec:
        result["provenance"]["max_workers"] = requested_workers
        result["provenance"]["effective_workers"] = effective_workers
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
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