"""R4 (SAEA-E-002) context-dose three-arm comparison: model-free, read-only.

Compares the three ``r4-e21-sub10`` arms -- ``nocontext`` (``bare-core-ojw``),
``matched`` (``fixed-legal-context-ojw``, each sample's own ConEC context),
``mismatched`` (``mismatched-evidence-ojw``, another sample's context) -- on
per-sample WER, over the SAME ten paired samples. See
``docs/readiness/2026-08-09-r4-analysis-plan.md`` for the pre-registered
statistics (Wilcoxon signed-rank, bootstrap CI, exact-p floor at n=10) this
module implements.

This module never opens a model session, spawns a process, or mutates run
state: it reads already-written ``<run_id>.run-manifest.json``/
``<run_id>.outputs.jsonl`` files under a stable ``run_dir`` (each attempt in
its own ``attempt-*/`` subdirectory -- ``core.driver.smoke.fresh_attempt_id``'s
convention) and scores them through the SAME frozen scoring stack every other
scorer in this study uses (``core.scorers.score_asr_outputs`` ->
``scoring.normalize.normalize_text_v1``/``scoring.wer.align``). It
deliberately does NOT go through ``core.bundle.score_bundle``/
``verify_bundle``: those additionally require a git tree whose load-bearing
surface is clean (``core.bundle.git_commit.
require_clean_load_bearing_surface``) and re-verify the E0/D3 freeze on
every call, which is right for a formal audit record but wrong for an
analysis tool a reviewer wants to re-run against a dirty working tree. In
exchange this module does its own light integrity check (outputs.jsonl bytes
re-hashed against the manifest's recorded sha256 before scoring) and its own
config-identity re-derivation (see :func:`assert_comparable`) -- narrower
than I7, but real.

The single most important behaviour here (module brief, near-verbatim): a
silently incomparable three-arm table is worse than no table. Every
comparability check below raises :class:`ComparisonError` naming exactly
which field differs, and :func:`build_report` never scores past that point.
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
import statistics
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..core.bundle import STATUS_ABORTED, STATUS_COMPLETED
from ..core.config import ConfigError, compose
from ..core.scorers import score_asr_outputs
from ..e0.artifacts import sha256_file, write_json_artifact

ARM_NAMES = ("nocontext", "matched", "mismatched")

# Contrasts to report: (name, condition_arm, reference_arm). diff = wer(condition) -
# wer(reference); negative means the condition arm is BETTER (lower WER).
CONTRASTS = (
    ("matched_vs_nocontext", "matched", "nocontext"),
    ("mismatched_vs_nocontext", "mismatched", "nocontext"),
    ("matched_vs_mismatched", "matched", "mismatched"),
)

# docs/readiness/2026-08-09-r4-analysis-plan.md: "bootstrap 95% CI (10,000
# resamples over calls, fixed seed 20260807)" -- the SAME seed convention
# scripts/build_probe_samples.py already uses for this study's sampling.
BOOTSTRAP_RESAMPLES_DEFAULT = 10_000
BOOTSTRAP_SEED_DEFAULT = 20260807
BOOTSTRAP_CONFIDENCE_DEFAULT = 0.95

REPORT_SCHEMA = "saea-r4-context-dose-comparison-v1"


class ComparisonError(RuntimeError):
    """No usable COMPLETED attempt exists, or the three arms are not
    comparable; refuse to emit a comparison rather than report a silently
    incomparable table."""


def _get_path(document: Mapping[str, object], path: tuple[str, ...]) -> object:
    node: object = document
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            raise ComparisonError(
                f"manifest is missing required field {'.'.join(path)!r}"
            )
        node = node[key]
    return node


# ---------------------------------------------------------------------------
# Step 1: locate, per arm, the attempt-*/ directory that actually COMPLETED.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkippedAttempt:
    manifest_path: Path
    status: str | None
    reason: str | None


@dataclass(frozen=True)
class AttemptSelection:
    run_dir: Path
    manifest_path: Path
    manifest: Mapping[str, object]
    skipped: tuple[SkippedAttempt, ...]
    # Any OTHER COMPLETED manifest under this run_dir that was not chosen
    # (kept for transparency in the report; build_report never averages
    # these in -- exactly one attempt per arm is ever scored).
    other_completed: tuple[Path, ...]


def find_completed_attempt(run_dir: Path) -> AttemptSelection:
    """Pick the COMPLETED attempt under ``run_dir`` (a stable parent whose
    children are ``attempt-*/`` subdirectories, each holding one attempt's
    own ``<run_id>.run-manifest.json``).

    An ABORTED attempt (a manifest with ``"status": "ABORTED"``) is real and
    common here -- it is recorded in :attr:`AttemptSelection.skipped` and
    never silently averaged in. If more than one COMPLETED attempt exists
    (a rerun under the same run_dir), the most recently created one is
    chosen and the rest are recorded in :attr:`AttemptSelection.other_completed`,
    never merged.
    """

    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise ComparisonError(f"run directory does not exist: {run_dir}")
    attempt_dirs = sorted(
        path for path in run_dir.iterdir() if path.is_dir() and path.name.startswith("attempt-")
    )
    if not attempt_dirs:
        raise ComparisonError(
            f"no attempt-* subdirectories found under {run_dir}; nothing to compare"
        )

    skipped: list[SkippedAttempt] = []
    completed: list[tuple[Path, Mapping[str, object]]] = []
    for attempt_dir in attempt_dirs:
        manifest_paths = sorted(attempt_dir.glob("*.run-manifest.json"))
        if not manifest_paths:
            skipped.append(
                SkippedAttempt(attempt_dir, None, "no *.run-manifest.json in this attempt directory")
            )
            continue
        for manifest_path in manifest_paths:
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                skipped.append(SkippedAttempt(manifest_path, None, f"unreadable manifest: {error}"))
                continue
            status = manifest.get("status") if isinstance(manifest, Mapping) else None
            if status == STATUS_ABORTED:
                reason = manifest.get("failure_reason") or "<no failure_reason recorded>"
                skipped.append(SkippedAttempt(manifest_path, STATUS_ABORTED, str(reason)))
                continue
            if status != STATUS_COMPLETED:
                skipped.append(
                    SkippedAttempt(manifest_path, status, "status is neither COMPLETED nor ABORTED")
                )
                continue
            completed.append((manifest_path, manifest))

    if not completed:
        detail = "; ".join(
            f"{item.manifest_path.name}: {item.status or 'unreadable'} ({item.reason})"
            for item in skipped
        )
        raise ComparisonError(
            f"no COMPLETED attempt found under {run_dir} ({len(attempt_dirs)} attempt "
            f"director{'y' if len(attempt_dirs) == 1 else 'ies'} inspected); refusing to "
            f"report a comparison. {detail or 'no manifests were readable at all.'}"
        )
    completed.sort(key=lambda pair: str(pair[1].get("created_at", "")))
    chosen_path, chosen_manifest = completed[-1]
    other_completed = tuple(path for path, _ in completed[:-1])
    return AttemptSelection(run_dir, chosen_path, chosen_manifest, tuple(skipped), other_completed)


# ---------------------------------------------------------------------------
# Step 2: refuse unless the three arms are actually comparable.
# ---------------------------------------------------------------------------


def assert_comparable(selections: Mapping[str, AttemptSelection], *, repo_root: Path) -> None:
    """Refuse (:class:`ComparisonError`, naming the exact differing field)
    unless: the same ``split.identity_hash``; the same ten ``split.ids``; the
    same ``config.fragments`` for model/dataset/experiment (byte-identical,
    re-verified by recomputing ``config_hash`` from the COMMITTED fragment
    files -- catches a stale/hand-edited manifest or fragment drift since the
    attempt ran); and a pairwise-distinct ``baseline`` fragment per arm (the
    ONE thing that is supposed to differ)."""

    missing = sorted(set(ARM_NAMES) - set(selections))
    if missing:
        raise ComparisonError(f"missing arm(s) {missing}; expected exactly {ARM_NAMES}")
    manifests = {arm: selections[arm].manifest for arm in ARM_NAMES}

    identity_hashes = {arm: _get_path(manifests[arm], ("split", "identity_hash")) for arm in ARM_NAMES}
    if len(set(identity_hashes.values())) != 1:
        raise ComparisonError(
            "split.identity_hash differs across arms: "
            + ", ".join(f"{arm}={value!r}" for arm, value in identity_hashes.items())
        )

    id_sets = {
        arm: tuple(sorted(str(sample_id) for sample_id in (_get_path(manifests[arm], ("split", "ids")) or [])))
        for arm in ARM_NAMES
    }
    if len(set(id_sets.values())) != 1:
        raise ComparisonError(
            "split.ids differ across arms: "
            + ", ".join(f"{arm}={list(ids)}" for arm, ids in id_sets.items())
        )

    fragments = {
        arm: dict(_get_path(manifests[arm], ("config", "fragments")) or {}) for arm in ARM_NAMES
    }
    for kind in ("model", "dataset", "experiment"):
        values = {arm: fragments[arm].get(kind) for arm in ARM_NAMES}
        if len(set(values.values())) != 1:
            raise ComparisonError(
                f"config.fragments[{kind!r}] differs across arms: "
                + ", ".join(f"{arm}={value!r}" for arm, value in values.items())
            )
    baseline_values = {arm: fragments[arm].get("baseline") for arm in ARM_NAMES}
    if len(set(baseline_values.values())) != len(ARM_NAMES):
        raise ComparisonError(
            "config.fragments['baseline'] must be pairwise distinct across the three arms "
            "(otherwise two arms are not actually testing different evidence conditions): "
            + ", ".join(f"{arm}={value!r}" for arm, value in baseline_values.items())
        )

    for arm in ARM_NAMES:
        recorded_hash = _get_path(manifests[arm], ("config", "config_hash"))
        try:
            composed = compose(
                repo_root,
                str(fragments[arm]["model"]),
                str(fragments[arm]["dataset"]),
                str(fragments[arm]["baseline"]),
                str(fragments[arm]["experiment"]),
            )
        except ConfigError as error:
            raise ComparisonError(
                f"cannot recompute config for arm {arm!r} from the committed config fragments: {error}"
            ) from error
        if composed.config_hash != recorded_hash:
            raise ComparisonError(
                f"arm {arm!r} manifest config.config_hash {recorded_hash!r} does not match "
                f"what the committed config fragments produce now ({composed.config_hash!r}); "
                "the manifest may be stale/hand-edited, or a fragment file changed since this "
                "attempt ran"
            )


# ---------------------------------------------------------------------------
# Step 3: score each arm's chosen attempt through the frozen scoring stack.
# ---------------------------------------------------------------------------


def _resolve_outputs_path(manifest: Mapping[str, object], manifest_path: Path) -> Path:
    outputs_meta = manifest.get("outputs")
    if not isinstance(outputs_meta, Mapping) or not outputs_meta.get("path"):
        raise ComparisonError(f"manifest {manifest_path} carries no outputs artifact to score")
    outputs_path = Path(str(outputs_meta["path"]))
    if not outputs_path.is_file():
        raise ComparisonError(
            f"outputs artifact recorded in {manifest_path} does not exist: {outputs_path}"
        )
    recorded_sha256 = outputs_meta.get("sha256")
    if isinstance(recorded_sha256, str) and recorded_sha256:
        actual_sha256 = sha256_file(outputs_path)
        if actual_sha256 != recorded_sha256:
            raise ComparisonError(
                f"outputs artifact {outputs_path} sha256 {actual_sha256} does not match the "
                f"manifest's recorded {recorded_sha256}; refusing to score a mismatched artifact"
            )
    return outputs_path


def _reference_length(entry: Mapping[str, object]) -> int:
    return len(entry["ref_hit_mask"])


def _errors(entry: Mapping[str, object]) -> int:
    return int(entry["substitutions"]) + int(entry["deletions"]) + int(entry["insertions"])


def score_arm(
    selection: AttemptSelection, lock: Mapping[str, object], root: Path
) -> dict[str, Mapping[str, object]]:
    """Score one arm's chosen attempt via ``core.scorers.score_asr_outputs``
    (the asr-wer scorer entry point) directly on the outputs.jsonl it
    produced -- the same normalizer/aligner (``scoring.normalize_text_v1``,
    ``scoring.align``) every other WER number in this study goes through.
    Returns ``{sample_id: per_sample_entry}``."""

    outputs_path = _resolve_outputs_path(selection.manifest, selection.manifest_path)
    scores = score_asr_outputs(outputs_path, lock, root)
    per_sample = {str(entry["sample_id"]): entry for entry in scores["per_sample"]}
    expected_ids = {str(sample_id) for sample_id in (_get_path(selection.manifest, ("split", "ids")) or [])}
    if set(per_sample) != expected_ids:
        raise ComparisonError(
            f"scored sample ids {sorted(per_sample)} do not match the manifest's split.ids "
            f"{sorted(expected_ids)} for {selection.manifest_path}"
        )
    return per_sample


def corpus_wer(per_sample: Mapping[str, Mapping[str, object]]) -> float:
    """Total errors / total reference words -- weights long samples more."""

    total_errors = sum(_errors(entry) for entry in per_sample.values())
    total_reference = sum(_reference_length(entry) for entry in per_sample.values())
    if total_reference == 0:
        return 0.0 if total_errors == 0 else float(total_errors)
    return total_errors / total_reference


def macro_wer(per_sample: Mapping[str, Mapping[str, object]]) -> float:
    """Mean of per-sample WER -- weights every sample equally regardless of length."""

    values = [float(entry["wer"]) for entry in per_sample.values()]
    if not values:
        raise ComparisonError("cannot compute macro WER over zero samples")
    return statistics.fmean(values)


# ---------------------------------------------------------------------------
# Step 4: paired statistics -- exact Wilcoxon signed-rank + bootstrap CI.
# ---------------------------------------------------------------------------


def _rank_with_ties(values: Sequence[float]) -> list[float]:
    """1-based ranks, ties given the average of the ranks they span
    (standard Wilcoxon tie handling)."""

    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average_rank = (i + 1 + j + 1) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = average_rank
        i = j + 1
    return ranks


@dataclass(frozen=True)
class WilcoxonResult:
    n_pairs: int
    n_effective: int
    statistic: float
    pvalue: float
    min_two_sided_p: float


def wilcoxon_signed_rank_exact(diffs: Sequence[float]) -> WilcoxonResult:
    """Exact two-sided Wilcoxon signed-rank test (zero differences dropped,
    the standard "Wilcoxon" zero-method) via full enumeration of the
    ``2 ** n_effective`` equally-likely sign assignments -- exact, not an
    asymptotic normal approximation, which is what a small paired n needs.

    At n_effective=10 (this study's n) the smallest possible two-sided
    p-value is ``2 / 2 ** 10 = 0.001953125`` -- see
    :attr:`WilcoxonResult.min_two_sided_p`, always reported alongside the
    p-value so a caller can never mistake a small p at small n for strong
    evidence.

    Verified 2026-08-09 against ``scipy.stats.wilcoxon(method="exact")`` over
    300 random tie-free, zero-free inputs at n in {4,5,6,8,10}: **0
    mismatches**. On inputs WITH ties the two disagree, and this
    implementation is the correct one -- scipy's exact mode assumes no ties
    and evaluates against the untied rank-sum null, whereas the enumeration
    above is the conditional sign-flip permutation test over the OBSERVED
    tie-averaged ranks, which is what conditioning on |d| actually gives you.
    An independent from-scratch brute force reproduced this implementation's
    values, not scipy's, on every tied case checked. Ties are not exotic here:
    per-sample WER differences at n=10 tie often, and exact zeros (a sample the
    arm did not change at all) are common. **Do not "fix" this toward scipy.**
    """

    n_pairs = len(diffs)
    nonzero = [value for value in diffs if value != 0]
    n = len(nonzero)
    if n == 0:
        return WilcoxonResult(n_pairs=n_pairs, n_effective=0, statistic=0.0, pvalue=1.0, min_two_sided_p=1.0)

    ranks = _rank_with_ties([abs(value) for value in nonzero])
    observed = sum(rank for rank, value in zip(ranks, nonzero) if value > 0)

    total = 2**n
    count_le = 0
    count_ge = 0
    for signs in itertools.product((1, -1), repeat=n):
        statistic = sum(rank for rank, sign in zip(ranks, signs) if sign > 0)
        if statistic <= observed:
            count_le += 1
        if statistic >= observed:
            count_ge += 1
    p_two_sided = min(1.0, 2 * min(count_le, count_ge) / total)
    return WilcoxonResult(
        n_pairs=n_pairs, n_effective=n, statistic=observed, pvalue=p_two_sided, min_two_sided_p=2 / total
    )


@dataclass(frozen=True)
class BootstrapCI:
    point_estimate: float
    ci_low: float
    ci_high: float
    resamples: int
    seed: int
    confidence: float


def bootstrap_ci(
    diffs: Sequence[float],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES_DEFAULT,
    seed: int = BOOTSTRAP_SEED_DEFAULT,
    confidence: float = BOOTSTRAP_CONFIDENCE_DEFAULT,
    stat_fn: Callable[[Sequence[float]], float] = statistics.fmean,
) -> BootstrapCI:
    """Percentile bootstrap CI for ``stat_fn`` over paired differences,
    resampling calls (not scores) with replacement -- ``docs/readiness/
    2026-08-09-r4-analysis-plan.md``'s "10,000 resamples over calls, fixed
    seed 20260807"."""

    n = len(diffs)
    if n == 0:
        raise ComparisonError("cannot bootstrap a CI over zero paired samples")
    if resamples <= 0:
        raise ComparisonError("bootstrap resamples must be a positive integer")
    rng = random.Random(seed)
    values = list(diffs)
    stats = sorted(stat_fn([values[rng.randrange(n)] for _ in range(n)]) for _ in range(resamples))
    alpha = (1.0 - confidence) / 2.0
    low_index = max(0, min(resamples - 1, round(alpha * (resamples - 1))))
    high_index = max(0, min(resamples - 1, round((1.0 - alpha) * (resamples - 1))))
    return BootstrapCI(
        point_estimate=stat_fn(values),
        ci_low=stats[low_index],
        ci_high=stats[high_index],
        resamples=resamples,
        seed=seed,
        confidence=confidence,
    )


@dataclass(frozen=True)
class Contrast:
    name: str
    condition_arm: str
    reference_arm: str
    sample_ids: tuple[str, ...]
    diffs: tuple[float, ...]
    wilcoxon: WilcoxonResult
    bootstrap_mean: BootstrapCI
    bootstrap_median: BootstrapCI


def build_contrast(
    name: str,
    condition_arm: str,
    reference_arm: str,
    per_sample: Mapping[str, Mapping[str, Mapping[str, object]]],
    *,
    resamples: int,
    seed: int,
) -> Contrast:
    condition = per_sample[condition_arm]
    reference = per_sample[reference_arm]
    sample_ids = tuple(sorted(set(condition) & set(reference)))
    if set(condition) != set(reference):
        raise ComparisonError(
            f"contrast {name!r} cannot pair {condition_arm!r} against {reference_arm!r}: "
            f"sample ids differ ({sorted(set(condition) ^ set(reference))})"
        )
    diffs = tuple(
        float(condition[sample_id]["wer"]) - float(reference[sample_id]["wer"]) for sample_id in sample_ids
    )
    wilcoxon = wilcoxon_signed_rank_exact(diffs)
    bootstrap_mean = bootstrap_ci(diffs, resamples=resamples, seed=seed, stat_fn=statistics.fmean)
    bootstrap_median = bootstrap_ci(diffs, resamples=resamples, seed=seed, stat_fn=statistics.median)
    return Contrast(
        name=name,
        condition_arm=condition_arm,
        reference_arm=reference_arm,
        sample_ids=sample_ids,
        diffs=diffs,
        wilcoxon=wilcoxon,
        bootstrap_mean=bootstrap_mean,
        bootstrap_median=bootstrap_median,
    )


# ---------------------------------------------------------------------------
# Step 5: assemble the full report.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparisonReport:
    generated_at: str
    arms: Mapping[str, AttemptSelection]
    per_sample: Mapping[str, Mapping[str, Mapping[str, object]]]
    aggregate: Mapping[str, Mapping[str, object]]
    contrasts: Mapping[str, Contrast]
    bootstrap_resamples: int
    bootstrap_seed: int


def build_report(
    run_dirs: Mapping[str, Path],
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    resamples: int = BOOTSTRAP_RESAMPLES_DEFAULT,
    seed: int = BOOTSTRAP_SEED_DEFAULT,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> ComparisonReport:
    """Locate each arm's COMPLETED attempt, refuse unless all three are
    comparable, score them through the frozen stack, and compute the
    pre-registered contrasts. Raises :class:`ComparisonError` (never returns
    a partial report) if any step fails."""

    if set(run_dirs) != set(ARM_NAMES):
        raise ComparisonError(f"expected exactly the arms {ARM_NAMES}, got {sorted(run_dirs)}")

    selections = {arm: find_completed_attempt(Path(path)) for arm, path in run_dirs.items()}
    assert_comparable(selections, repo_root=repo_root)

    per_sample = {arm: score_arm(selection, lock, root) for arm, selection in selections.items()}
    aggregate = {
        arm: {
            "corpus_wer": corpus_wer(rows),
            "macro_wer": macro_wer(rows),
            "n": len(rows),
            "total_errors": sum(_errors(entry) for entry in rows.values()),
            "total_reference_words": sum(_reference_length(entry) for entry in rows.values()),
        }
        for arm, rows in per_sample.items()
    }
    contrasts = {
        name: build_contrast(name, condition_arm, reference_arm, per_sample, resamples=resamples, seed=seed)
        for name, condition_arm, reference_arm in CONTRASTS
    }
    return ComparisonReport(
        generated_at=now().astimezone(timezone.utc).isoformat(),
        arms=selections,
        per_sample=per_sample,
        aggregate=aggregate,
        contrasts=contrasts,
        bootstrap_resamples=resamples,
        bootstrap_seed=seed,
    )


# ---------------------------------------------------------------------------
# Rendering: machine-readable JSON + human-readable table.
# ---------------------------------------------------------------------------


def report_to_json(report: ComparisonReport) -> dict[str, object]:
    sample_ids = sorted({sample_id for rows in report.per_sample.values() for sample_id in rows})
    identity_hash = _get_path(next(iter(report.arms.values())).manifest, ("split", "identity_hash"))
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": report.generated_at,
        "bootstrap": {"resamples": report.bootstrap_resamples, "seed": report.bootstrap_seed},
        "arms": {
            arm: {
                "run_dir": str(selection.run_dir),
                "manifest_path": str(selection.manifest_path),
                "run_id": selection.manifest.get("run_id"),
                "attempt_id": _get_path(selection.manifest, ("attempt", "attempt_id")),
                "baseline_fragment": _get_path(selection.manifest, ("config", "fragments", "baseline")),
                "config_hash": _get_path(selection.manifest, ("config", "config_hash")),
                "skipped_attempts": [
                    {
                        "manifest_path": str(skipped.manifest_path),
                        "status": skipped.status,
                        "reason": skipped.reason,
                    }
                    for skipped in selection.skipped
                ],
                "other_completed_attempts_not_used": [str(path) for path in selection.other_completed],
            }
            for arm, selection in report.arms.items()
        },
        "comparability": {
            "ok": True,
            "split_identity_hash": identity_hash,
            "sample_ids": sample_ids,
            "n_samples": len(sample_ids),
        },
        "per_sample": {
            sample_id: {
                arm: {
                    "wer": rows[sample_id]["wer"],
                    "hits": rows[sample_id]["hits"],
                    "substitutions": rows[sample_id]["substitutions"],
                    "deletions": rows[sample_id]["deletions"],
                    "insertions": rows[sample_id]["insertions"],
                    "reference_length": _reference_length(rows[sample_id]),
                }
                for arm, rows in report.per_sample.items()
            }
            for sample_id in sample_ids
        },
        "aggregate": dict(report.aggregate),
        "contrasts": {
            name: {
                "condition_arm": contrast.condition_arm,
                "reference_arm": contrast.reference_arm,
                "diff_convention": (
                    f"wer({contrast.condition_arm}) - wer({contrast.reference_arm}); "
                    f"negative = {contrast.condition_arm} better"
                ),
                "sample_ids": list(contrast.sample_ids),
                "diffs": list(contrast.diffs),
                "wilcoxon": {
                    "statistic_w_plus": contrast.wilcoxon.statistic,
                    "n_pairs": contrast.wilcoxon.n_pairs,
                    "n_effective_nonzero": contrast.wilcoxon.n_effective,
                    "pvalue_two_sided_exact": contrast.wilcoxon.pvalue,
                    "min_achievable_two_sided_p": contrast.wilcoxon.min_two_sided_p,
                    "note": (
                        f"exact two-sided Wilcoxon signed-rank test over "
                        f"{contrast.wilcoxon.n_effective} nonzero paired difference(s); the "
                        f"smallest p-value this test can ever report at this n is "
                        f"{contrast.wilcoxon.min_two_sided_p:.6g} -- do not read a p-value near "
                        "this floor as strong evidence"
                    ),
                },
                "bootstrap": {
                    "resamples": report.bootstrap_resamples,
                    "seed": report.bootstrap_seed,
                    "mean": {
                        "point_estimate": contrast.bootstrap_mean.point_estimate,
                        "ci95": [contrast.bootstrap_mean.ci_low, contrast.bootstrap_mean.ci_high],
                    },
                    "median": {
                        "point_estimate": contrast.bootstrap_median.point_estimate,
                        "ci95": [contrast.bootstrap_median.ci_low, contrast.bootstrap_median.ci_high],
                    },
                },
            }
            for name, contrast in report.contrasts.items()
        },
    }


def render_table(report: ComparisonReport) -> str:
    lines: list[str] = []
    lines.append("R4 context-dose comparison (SAEA-E-002)")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Arms:")
    for arm in ARM_NAMES:
        selection = report.arms[arm]
        baseline = _get_path(selection.manifest, ("config", "fragments", "baseline"))
        run_id = selection.manifest.get("run_id")
        attempt_id = _get_path(selection.manifest, ("attempt", "attempt_id"))
        lines.append(f"  {arm:<11} run_id={run_id}  attempt={attempt_id}  baseline={baseline}")
        for skipped in selection.skipped:
            lines.append(f"      skipped {skipped.manifest_path.name}: {skipped.status} ({skipped.reason})")
    lines.append("")

    sample_ids = sorted({sample_id for rows in report.per_sample.values() for sample_id in rows})
    identity_hash = _get_path(next(iter(report.arms.values())).manifest, ("split", "identity_hash"))
    lines.append(f"Comparability: OK  split.identity_hash={identity_hash}  n={len(sample_ids)} samples")
    lines.append("")

    lines.append("Per-sample WER")
    lines.append(f"  {'sample_id':<12}" + "".join(f"{arm:>14}" for arm in ARM_NAMES))
    for sample_id in sample_ids:
        row = f"  {sample_id:<12}" + "".join(
            f"{report.per_sample[arm][sample_id]['wer']:>14.4f}" for arm in ARM_NAMES
        )
        lines.append(row)
    lines.append("")

    lines.append("Aggregate WER")
    lines.append(f"  {'arm':<11}{'corpus_wer':>14}{'macro_wer':>14}{'n':>6}")
    for arm in ARM_NAMES:
        agg = report.aggregate[arm]
        lines.append(f"  {arm:<11}{agg['corpus_wer']:>14.4f}{agg['macro_wer']:>14.4f}{agg['n']:>6}")
    lines.append("")

    lines.append("Paired contrasts (diff = wer(condition) - wer(reference); negative = condition better)")
    for name, contrast in report.contrasts.items():
        wilcoxon = contrast.wilcoxon
        mean_ci = contrast.bootstrap_mean
        lines.append(
            f"  {name:<24} mean_diff={mean_ci.point_estimate:+.4f} "
            f"[95% CI {mean_ci.ci_low:+.4f}, {mean_ci.ci_high:+.4f}]  "
            f"wilcoxon W+={wilcoxon.statistic:g} p={wilcoxon.pvalue:.4g} "
            f"(n={wilcoxon.n_effective}, exact)"
        )
    lines.append("")

    floor = max(contrast.wilcoxon.min_two_sided_p for contrast in report.contrasts.values())
    n_pairs = max(contrast.wilcoxon.n_pairs for contrast in report.contrasts.values())
    lines.append(
        f"NOTE: n={n_pairs} paired samples. The exact two-sided Wilcoxon test's minimum "
        f"achievable p-value at this n is {floor:.6g} -- do not over-read a p-value near this "
        "floor as strong evidence. See docs/readiness/2026-08-09-r4-analysis-plan.md for the "
        "pre-registered statistics and what this design can/cannot show."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point (scripts/compare_context_dose.py is a thin wrapper).
# ---------------------------------------------------------------------------


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compare-context-dose",
        description=(
            "R4 (SAEA-E-002) context-dose three-arm WER comparison: model-free, reads "
            "already-produced run bundles only. See docs/readiness/"
            "2026-08-09-r4-analysis-plan.md for the pre-registered statistics."
        ),
    )
    parser.add_argument(
        "--nocontext-run-dir", required=True, type=Path,
        help="stable run_dir for SAEA-E-002-r4-nocontext (parent of attempt-*/ subdirectories)",
    )
    parser.add_argument(
        "--matched-run-dir", required=True, type=Path,
        help="stable run_dir for SAEA-E-002-r4-matched",
    )
    parser.add_argument(
        "--mismatched-run-dir", required=True, type=Path,
        help="stable run_dir for SAEA-E-002-r4-mismatched",
    )
    parser.add_argument("--output", required=True, type=Path, help="path to write the machine-readable JSON summary")
    parser.add_argument("--bootstrap-resamples", type=int, default=BOOTSTRAP_RESAMPLES_DEFAULT)
    parser.add_argument("--bootstrap-seed", type=int, default=BOOTSTRAP_SEED_DEFAULT)
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="TEST-ONLY override of the study repo root used to re-derive config_hash",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    lock = load_lock(umbrella_lock_path(repo_root))
    root = data_root()
    run_dirs = {
        "nocontext": args.nocontext_run_dir,
        "matched": args.matched_run_dir,
        "mismatched": args.mismatched_run_dir,
    }
    try:
        report = build_report(
            run_dirs, lock, root, repo_root=repo_root,
            resamples=args.bootstrap_resamples, seed=args.bootstrap_seed,
        )
    except ComparisonError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    document = report_to_json(report)
    write_json_artifact(args.output, document)
    print(render_table(report))
    print(f"\nwrote machine-readable summary to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
