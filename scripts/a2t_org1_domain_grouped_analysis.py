#!/usr/bin/env python3
"""Verdict numbers for A2T-ORG-1, the domain-grouped Audio2Tool tool registry.

Reads only bytes that are already sealed -- this run's own manifest
(``SAEA-A2T-ORG1-DOMAIN-GROUPED-V1``) and the three 2026-09-04
official-population manifests its 4,000 rows are paired against -- and writes
``result-summary.json``. Zero model, GPU or network contact; gold enters only
through the registered scorers, exactly as it does when a flight finalizes.

Section 6 of ``docs/readiness/2026-09-05-a2t-org1-domain-grouped-registry-v1-
preregistration.md``, fixed before takeoff, is what this computes:

* PRIMARY -- pooled official tool accuracy, ORG-1 minus baseline, paired over
  the 4,000 rows through ``analysis.paired`` (saves / harms / ties, exact sign
  test, 10,000 replicates stratified by tier, seed 20260903, CI90);
* the same delta on the NATURAL MIXTURE (which is the pooled figure) and on
  EQUAL-DOMAIN weighting, the latter with its own domain-stratified bootstrap
  at the same seed and replicate count;
* per tier, with the published Qwen-3-Omni-30B column beside every tier;
* per domain, and per tier x domain;
* SECONDARY -- exact match, parameter F1 (macro and micro), ``a2t-toolcall-v2``
  and parse rate, each as a paired delta;
* the CONFUSION-PAIR table before and after -- the named cross-domain and
  same-domain twins the three official-population verdicts reported -- with
  each pair's class taken from the registry rather than asserted;
* the CROSS-DOMAIN SHARE of the gain = (baseline cross-domain-twin misses
  corrected) / (all misses corrected);
* the three-outcome decision ADMITTED / NULL / HARMFUL.

Usage (WSL2, model-free)::

    python a2t_org1_domain_grouped_analysis.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)

RUN_ID = "SAEA-A2T-ORG1-DOMAIN-GROUPED-V1"
CELL = "ORG1-grouped-raw"

#: The sealed official-protocol comparators, one per parent draw.
BASELINES: tuple[tuple[str, str, str], ...] = (
    (
        "SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1",
        "attempt-20260904T172609Z-t1officialpop500",
        "T1-official-pop-500",
    ),
    (
        "SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1",
        "attempt-20260904T193726Z-t258officialpop1500",
        "T258-official-pop-1500",
    ),
    (
        "SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1",
        "attempt-20260904T211040Z-t3467officialpop2000",
        "T3467-official-pop-2000",
    ),
)

ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-a2t-org1-domain-grouped-roster"
    / "flight-roster-receipt.json"
)
OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-a2t-org1-domain-grouped-4000-v1"
)

TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)

PAPER = {
    "tier1_direct": {"tool_accuracy": 92.4, "exact_match": 92.4, "slot_f1": None},
    "tier2_parametric": {"tool_accuracy": 84.6, "exact_match": 15.6, "slot_f1": 21.7},
    "tier3_multi_intent": {"tool_accuracy": 74.7, "exact_match": 28.6, "slot_f1": 35.0},
    "tier4_implicit": {"tool_accuracy": 33.4, "exact_match": 11.3, "slot_f1": 23.4},
    "tier5_needle": {"tool_accuracy": 90.6, "exact_match": 36.0, "slot_f1": 41.6},
    "tier6_correction": {"tool_accuracy": 81.5, "exact_match": 24.8, "slot_f1": 32.4},
    "tier7_multiturn": {"tool_accuracy": 54.6, "exact_match": 16.3, "slot_f1": 26.8},
    "tier8_intent_blending": {"tool_accuracy": 41.7, "exact_match": 12.4, "slot_f1": 19.9},
}

#: Every (gold, predicted) pair the three 2026-09-04 official-population
#: verdicts named in a top-confusion table. Whether a pair is CROSS-domain or
#: SAME-domain is not asserted here -- it is resolved from the registry.
NAMED_TWINS: tuple[tuple[str, str], ...] = (
    ("rebootDevice", "restartDevice"),
    ("setSecurityMode", "armSecuritySystem"),
    ("activateScene", "activateRoutine"),
    ("setColor", "setAmbientLighting"),
    ("setColorTemperature", "setAmbientLighting"),
    ("setLighting", "setAmbientLighting"),
    ("setLighting", "setLightState"),
    ("setColor", "setLighting"),
    ("getAirQuality", "getAirQuality_diag"),
    ("setGroupLightState", "setLighting"),
    ("setGarageDoor", "setGarageOpener"),
    ("setFanMode", "setFanSpeed"),
    ("getApplianceState", "getApplianceStatus"),
    ("setLockState", "setLockState_home"),
    ("getBiometricData", "startWorkout"),
    ("findMyDevice", "findPairedPhone"),
    ("setVolume", "adjustVolume"),
    ("getNetworkHealth", "runNetworkSpeedTest"),
)

SEED = 20260903
REPLICATES = 10_000
CI_LEVEL = 0.90
Z_90 = 1.6448536269514722

METRICS = (
    "tool_accuracy",
    "exact_match",
    "param_f1",
    "parse_rate",
    "v2_tool_accuracy",
    "v2_exact_match",
)


# ---------------------------------------------------------------------------
# Sealed-byte plumbing (identical in shape to the three official-population
# analyses; only the run ids differ)
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def data_root_path() -> Path:
    from speech_aware_evidence_acquisition.data.lock import data_root

    return Path(data_root())


def latest_attempt(run_id: str) -> str:
    directory = data_root_path() / "runs" / run_id
    attempts = sorted(p.name for p in directory.iterdir() if p.name.startswith("attempt-"))
    if not attempts:
        raise SystemExit(f"run {run_id} has no attempt directory")
    return attempts[-1]


def run_dir(run_id: str, attempt: str) -> Path:
    return data_root_path() / "runs" / run_id / attempt


def load_manifest(run_id: str, attempt: str) -> Mapping[str, object]:
    return json.loads(
        (run_dir(run_id, attempt) / f"{run_id}.run-manifest.json").read_text(encoding="utf-8")
    )


def rescore(run_id: str, attempt: str, scorer: str) -> Mapping[str, object]:
    from speech_aware_evidence_acquisition.core.base import SCORERS
    import speech_aware_evidence_acquisition.core.scorers  # noqa: F401  (registers)
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )

    outputs = run_dir(run_id, attempt) / f"{run_id}.outputs.jsonl"
    return SCORERS.resolve(scorer)(outputs, load_lock(umbrella_lock_path(REPO)), data_root())


def wilson(successes: int, total: int, z: float = Z_90) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, center - half), min(1.0, center + half))


# ---------------------------------------------------------------------------
# Stratum and registry facts (identity metadata only)
# ---------------------------------------------------------------------------


def registry_rows() -> dict[str, Mapping[str, str]]:
    from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry
    from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path

    lock = load_lock(umbrella_lock_path(REPO))
    return {
        str(row["tool_name"]): row
        for row in load_tool_registry(lock, data_root_path())
    }


def domain_by_sample(roster: Mapping[str, object]) -> dict[str, str]:
    """Each roster row's domain, read from its tier's released manifest.

    Stratum metadata only, resolved at ANALYSIS time exactly as the three
    official-population analyses resolved it.
    """

    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        load_lock,
        umbrella_lock_path,
    )

    lock = load_lock(umbrella_lock_path(REPO))
    public = asset_dir(lock, "audio2tool", data_root_path()) / "public"
    by_tier: dict[str, list[Mapping[str, object]]] = {}
    for item in roster["items"]:
        by_tier.setdefault(str(item["tier"]), []).append(item)
    out: dict[str, str] = {}
    for tier, items in by_tier.items():
        manifest = json.loads(
            (public / f"{tier}_data" / f"{tier}.json").read_text(encoding="utf-8")
        )
        domains = {int(row["id"]): str(row["domain"]) for row in manifest}
        for item in items:
            out[str(item["sample_id"])] = domains[int(item["id"])]
    return out


# ---------------------------------------------------------------------------
# Score assembly
# ---------------------------------------------------------------------------


def arm_scores(
    official: Mapping[str, object], v2: Mapping[str, object]
) -> tuple[dict[str, dict[str, float]], dict[str, Mapping[str, object]]]:
    """``(metric map, official row map)`` keyed by sample id."""

    rows = {str(row["sample_id"]): row for row in official["per_sample"]}
    v2_rows = {str(row["sample_id"]): row for row in v2["per_sample"]}
    scores: dict[str, dict[str, float]] = {}
    for sample_id, row in rows.items():
        v2_row = v2_rows[sample_id]
        scores[sample_id] = {
            "tool_accuracy": 1.0 if row["tool_correct"] else 0.0,
            "exact_match": 1.0 if row["exact_match"] else 0.0,
            "param_f1": float(row["param_f1"]),
            "parse_rate": 1.0 if row["parsed"] else 0.0,
            "v2_tool_accuracy": float(v2_row["tool_accuracy"]),
            "v2_exact_match": float(v2_row["exact_match"]),
        }
    return scores, rows


def rate(rows: Sequence[Mapping[str, object]], field: str) -> dict[str, object]:
    total = len(rows)
    successes = sum(1 for row in rows if bool(row[field]))
    low, high = wilson(successes, total)
    return {
        "samples": total,
        "successes": successes,
        "pct": 100.0 * successes / total if total else 0.0,
        "ci90_low_pct": low * 100.0,
        "ci90_high_pct": high * 100.0,
    }


def mean(rows: Sequence[Mapping[str, object]], field: str) -> float:
    return sum(float(row[field]) for row in rows) / len(rows) if rows else 0.0


def micro_param_f1(rows: Sequence[Mapping[str, object]]) -> float:
    correct = sum(int(row["param_correct_keys"]) for row in rows)
    predicted = sum(int(row["param_predicted_keys"]) for row in rows)
    gold = sum(int(row["param_gold_keys"]) for row in rows)
    if predicted == 0 or gold == 0:
        return 0.0
    precision = correct / predicted
    recall = correct / gold
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# Miss classification and the confusion-pair table
# ---------------------------------------------------------------------------


def classify_miss(
    row: Mapping[str, object], domain: str, registry: Mapping[str, Mapping[str, str]]
) -> str:
    if row["tool_correct"]:
        return "correct"
    predicted = row["predicted_tool"]
    if not predicted:
        return "unparsed"
    entry = registry.get(str(predicted))
    if entry is None:
        return "invented_name"
    return "cross_domain_twin" if entry["domain"] != domain else "same_domain_twin"


def confusion_block(
    rows: Mapping[str, Mapping[str, object]],
    domains: Mapping[str, str],
    registry: Mapping[str, Mapping[str, str]],
) -> dict[str, object]:
    classes: Counter = Counter()
    pairs: Counter = Counter()
    for sample_id, row in rows.items():
        label = classify_miss(row, domains[sample_id], registry)
        classes[label] += 1
        if label != "correct":
            pairs[(str(row["gold_tool"]), str(row["predicted_tool"] or ""))] += 1
    return {
        "miss_classes": dict(sorted(classes.items())),
        "top_confusions": [
            {
                "gold_tool": gold,
                "predicted_tool": predicted,
                "rows": count,
                "gold_domain": registry[gold]["domain"] if gold in registry else None,
                "predicted_domain": (
                    registry[predicted]["domain"] if predicted in registry else None
                ),
            }
            for (gold, predicted), count in pairs.most_common(15)
        ],
        "_pairs": pairs,
    }


def named_twin_table(
    before: Counter,
    after: Counter,
    registry: Mapping[str, Mapping[str, str]],
) -> list[dict[str, object]]:
    table: list[dict[str, object]] = []
    for gold, predicted in NAMED_TWINS:
        gold_entry = registry.get(gold)
        predicted_entry = registry.get(predicted)
        if gold_entry is None or predicted_entry is None:
            klass = "unresolvable"
        elif gold_entry["domain"] != predicted_entry["domain"]:
            klass = "cross_domain"
        else:
            klass = "same_domain"
        table.append(
            {
                "gold_tool": gold,
                "predicted_tool": predicted,
                "class": klass,
                "gold_domain": gold_entry["domain"] if gold_entry else None,
                "predicted_domain": predicted_entry["domain"] if predicted_entry else None,
                "rows_before": int(before.get((gold, predicted), 0)),
                "rows_after": int(after.get((gold, predicted), 0)),
                "delta": int(after.get((gold, predicted), 0))
                - int(before.get((gold, predicted), 0)),
            }
        )
    return sorted(table, key=lambda row: (-row["rows_before"], row["gold_tool"]))


# ---------------------------------------------------------------------------
# The equal-domain delta and its own bootstrap
# ---------------------------------------------------------------------------


def equal_domain_delta(
    ids: Sequence[str],
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    domains: Mapping[str, str],
    metric: str = "tool_accuracy",
) -> dict[str, object]:
    """Unweighted mean over domains of each arm's per-domain rate, and the
    delta, with a domain-stratified paired bootstrap at the same seed and
    replicate count the primary contrast uses."""

    by_domain: dict[str, list[str]] = {}
    for sample_id in ids:
        by_domain.setdefault(domains[sample_id], []).append(sample_id)
    ordered = {name: tuple(members) for name, members in sorted(by_domain.items())}

    def statistic(sample_ids: Sequence[str]) -> float:
        grouped: dict[str, list[str]] = {}
        for sample_id in sample_ids:
            grouped.setdefault(domains[sample_id], []).append(sample_id)
        deltas = []
        for members in grouped.values():
            deltas.append(
                sum(right[s][metric] - left[s][metric] for s in members) / len(members)
            )
        return sum(deltas) / len(deltas)

    point = statistic(tuple(ids))
    rng = random.Random(SEED)
    replicates: list[float] = []
    for _ in range(REPLICATES):
        resampled: list[str] = []
        for members in ordered.values():
            resampled.extend(members[rng.randrange(len(members))] for _ in members)
        replicates.append(statistic(tuple(resampled)))
    replicates.sort()
    tail = (1.0 - CI_LEVEL) / 2.0

    def percentile(fraction: float) -> float:
        index = min(len(replicates) - 1, max(0, int(round(fraction * (len(replicates) - 1)))))
        return replicates[index]

    return {
        "metric": metric,
        "left_pct": 100.0
        * sum(
            sum(left[s][metric] for s in members) / len(members)
            for members in ordered.values()
        )
        / len(ordered),
        "right_pct": 100.0
        * sum(
            sum(right[s][metric] for s in members) / len(members)
            for members in ordered.values()
        )
        / len(ordered),
        "delta_pp": 100.0 * point,
        "ci90_low_pp": 100.0 * percentile(tail),
        "ci90_high_pp": 100.0 * percentile(1.0 - tail),
        "n_replicates": REPLICATES,
        "seed": SEED,
        "basis": (
            "unweighted mean over the three domains of each arm's per-domain rate; the "
            "bootstrap resamples WITHIN each domain (domain-stratified) at the same seed "
            "and replicate count as the primary tier-stratified contrast"
        ),
    }


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def contrast_as_dict(contrast) -> dict[str, object]:
    return {
        "metric": contrast.metric,
        "n": contrast.n,
        "baseline_pct": 100.0 * contrast.left_mean,
        "org1_pct": 100.0 * contrast.right_mean,
        "delta_pp": 100.0 * contrast.delta,
        "saves": contrast.saves,
        "harms": contrast.harms,
        "ties": contrast.ties,
        "sign_test_p": contrast.sign_test_p,
        "ci90_low_pp": 100.0 * contrast.bootstrap.ci_low,
        "ci90_high_pp": 100.0 * contrast.bootstrap.ci_high,
        "sigma_hat_pp": 100.0 * contrast.bootstrap.sigma_hat,
        "n_replicates": contrast.bootstrap.n_replicates,
        "seed": contrast.bootstrap.seed,
    }


def build(*, attempt: str) -> dict[str, object]:
    from speech_aware_evidence_acquisition.analysis.paired import (
        paired_contrast,
        per_stratum_table,
    )

    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    domains = domain_by_sample(roster)
    registry = registry_rows()
    roster_ids = sorted(str(item["sample_id"]) for item in roster["items"])

    org_official = rescore(RUN_ID, attempt, "a2t-toolcall-official")
    org_v2 = rescore(RUN_ID, attempt, "a2t-toolcall-v2")
    right, org_rows = arm_scores(org_official, org_v2)

    left: dict[str, dict[str, float]] = {}
    base_rows: dict[str, Mapping[str, object]] = {}
    baseline_sources = []
    for run_id, base_attempt, cell in BASELINES:
        official = rescore(run_id, base_attempt, "a2t-toolcall-official")
        v2 = rescore(run_id, base_attempt, "a2t-toolcall-v2")
        scores, rows = arm_scores(official, v2)
        overlap = set(scores) & set(left)
        if overlap:
            raise SystemExit(f"baseline runs overlap on {sorted(overlap)[:5]}")
        left.update(scores)
        base_rows.update(rows)
        manifest_path = (
            run_dir(run_id, base_attempt) / f"{run_id}.run-manifest.json"
        )
        baseline_sources.append(
            {
                "run_id": run_id,
                "cell_id": cell,
                "attempt_id": base_attempt,
                "rows": len(scores),
                "manifest_sha256": sha256_file(manifest_path),
                "study_commit": str(load_manifest(run_id, base_attempt)["study_commit"]),
            }
        )

    missing_left = [s for s in roster_ids if s not in left]
    missing_right = [s for s in roster_ids if s not in right]
    if missing_left or missing_right:
        raise SystemExit(
            "roster rows missing: baseline %d, org1 %d (first: %s / %s)"
            % (
                len(missing_left),
                len(missing_right),
                missing_left[:3],
                missing_right[:3],
            )
        )
    left = {s: left[s] for s in roster_ids}
    right = {s: right[s] for s in roster_ids}
    base_rows = {s: base_rows[s] for s in roster_ids}
    org_rows = {s: org_rows[s] for s in roster_ids}

    def tier_of(sample_id: str) -> str:
        return sample_id.rsplit(":", 1)[0]

    contrasts = paired_contrast(
        left,
        right,
        metrics=METRICS,
        sample_ids=roster_ids,
        strata_of=tier_of,
        seed=SEED,
        n_replicates=REPLICATES,
        ci_level=CI_LEVEL,
    )
    domain_contrasts = paired_contrast(
        left,
        right,
        metrics=("tool_accuracy", "exact_match"),
        sample_ids=roster_ids,
        strata_of=lambda s: domains[s],
        seed=SEED,
        n_replicates=REPLICATES,
        ci_level=CI_LEVEL,
    )

    # ---- per tier, with the paper column -------------------------------
    per_tier: dict[str, object] = {}
    for tier in TIERS:
        ids = [s for s in roster_ids if tier_of(s) == tier]
        base_tier = [base_rows[s] for s in ids]
        org_tier = [org_rows[s] for s in ids]
        base_ta = rate(base_tier, "tool_correct")
        org_ta = rate(org_tier, "tool_correct")
        per_domain: dict[str, object] = {}
        for domain in sorted({domains[s] for s in ids}):
            members = [s for s in ids if domains[s] == domain]
            per_domain[domain] = {
                "n": len(members),
                "baseline_pct": 100.0
                * sum(left[s]["tool_accuracy"] for s in members)
                / len(members),
                "org1_pct": 100.0
                * sum(right[s]["tool_accuracy"] for s in members)
                / len(members),
                "delta_pp": 100.0
                * sum(
                    right[s]["tool_accuracy"] - left[s]["tool_accuracy"] for s in members
                )
                / len(members),
            }
        per_tier[tier] = {
            "samples": len(ids),
            "baseline": {
                "tool_accuracy": base_ta,
                "exact_match": rate(base_tier, "exact_match"),
                "param_f1_macro_pct": 100.0 * mean(base_tier, "param_f1"),
                "param_f1_micro_pct": 100.0 * micro_param_f1(base_tier),
                "parse_rate_pct": 100.0 * mean(base_tier, "parsed"),
            },
            "org1": {
                "tool_accuracy": org_ta,
                "exact_match": rate(org_tier, "exact_match"),
                "param_f1_macro_pct": 100.0 * mean(org_tier, "param_f1"),
                "param_f1_micro_pct": 100.0 * micro_param_f1(org_tier),
                "parse_rate_pct": 100.0 * mean(org_tier, "parsed"),
            },
            "paper": PAPER[tier],
            "delta_pp": {
                "tool_accuracy": org_ta["pct"] - base_ta["pct"],
                "exact_match": rate(org_tier, "exact_match")["pct"]
                - rate(base_tier, "exact_match")["pct"],
            },
            "org1_minus_paper_pp": org_ta["pct"] - PAPER[tier]["tool_accuracy"],
            "baseline_minus_paper_pp": base_ta["pct"] - PAPER[tier]["tool_accuracy"],
            "per_domain": per_domain,
        }

    # ---- per domain ------------------------------------------------------
    per_domain_overall: dict[str, object] = {}
    for domain in sorted(set(domains[s] for s in roster_ids)):
        ids = [s for s in roster_ids if domains[s] == domain]
        base_dom = [base_rows[s] for s in ids]
        org_dom = [org_rows[s] for s in ids]
        per_domain_overall[domain] = {
            "n": len(ids),
            "baseline": {
                "tool_accuracy": rate(base_dom, "tool_correct"),
                "exact_match": rate(base_dom, "exact_match"),
            },
            "org1": {
                "tool_accuracy": rate(org_dom, "tool_correct"),
                "exact_match": rate(org_dom, "exact_match"),
            },
            "delta_pp": {
                "tool_accuracy": rate(org_dom, "tool_correct")["pct"]
                - rate(base_dom, "tool_correct")["pct"],
                "exact_match": rate(org_dom, "exact_match")["pct"]
                - rate(base_dom, "exact_match")["pct"],
            },
            "saves": sum(
                1
                for s in ids
                if right[s]["tool_accuracy"] > left[s]["tool_accuracy"]
            ),
            "harms": sum(
                1
                for s in ids
                if right[s]["tool_accuracy"] < left[s]["tool_accuracy"]
            ),
        }

    # ---- confusion, before and after ------------------------------------
    before = confusion_block(base_rows, domains, registry)
    after = confusion_block(org_rows, domains, registry)
    twins = named_twin_table(before.pop("_pairs"), after.pop("_pairs"), registry)

    # ---- cross-domain share of the gain ---------------------------------
    corrected = [
        s
        for s in roster_ids
        if not base_rows[s]["tool_correct"] and org_rows[s]["tool_correct"]
    ]
    broken = [
        s
        for s in roster_ids
        if base_rows[s]["tool_correct"] and not org_rows[s]["tool_correct"]
    ]
    corrected_classes = Counter(
        classify_miss(base_rows[s], domains[s], registry) for s in corrected
    )
    broken_classes = Counter(
        classify_miss(org_rows[s], domains[s], registry) for s in broken
    )
    cross_share = (
        corrected_classes["cross_domain_twin"] / len(corrected) if corrected else None
    )

    # ---- decision --------------------------------------------------------
    primary = contrasts["tool_accuracy"]
    low = 100.0 * primary.bootstrap.ci_low
    high = 100.0 * primary.bootstrap.ci_high
    smart_home = per_domain_overall.get("smart_home", {})
    smart_home_delta = (
        smart_home["delta_pp"]["tool_accuracy"] if smart_home else 0.0
    )
    other_deltas = [
        block["delta_pp"]["tool_accuracy"]
        for name, block in per_domain_overall.items()
        if name != "smart_home"
    ]
    concentrated = bool(
        smart_home_delta > 0
        and (not other_deltas or smart_home_delta >= max(other_deltas))
        and (cross_share is not None and cross_share >= 0.5)
    )
    if low > 0.0 and concentrated:
        outcome = "ADMITTED"
    elif low > 0.0:
        outcome = "NULL"
    elif high < 0.0:
        outcome = "HARMFUL"
    else:
        outcome = "NULL"

    manifest = load_manifest(RUN_ID, attempt)
    return {
        "schema": "saea-a2t-org1-domain-grouped-result-summary-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "cell_id": CELL,
        "attempt_id": attempt,
        "manifest_sha256": sha256_file(
            run_dir(RUN_ID, attempt) / f"{RUN_ID}.run-manifest.json"
        ),
        "study_commit": manifest["study_commit"],
        "protocol_hash": manifest["protocol_hash"],
        "preregistration": (
            "docs/readiness/2026-09-05-a2t-org1-domain-grouped-registry-v1-preregistration.md"
        ),
        "paper_source": "arXiv:2604.22821 Table 3, Qwen-3-Omni-30B",
        "paper_column_note": (
            "reported beside every tier as a CEILING reference. No gate in this run is set "
            "relative to it: the decision is a paired delta against the sealed "
            "official-protocol cells"
        ),
        "roster": {
            "receipt": str(ROSTER.relative_to(REPO)).replace("\\", "/"),
            "receipt_sha256": sha256_file(ROSTER),
            "count": int(roster["count"]),
            "split_identity_hash": str(roster["split_identity_hash"]),
            "flight_split_identity_hash": str(roster["flight_split_identity_hash"]),
            "tier_counts": dict(roster["tier_counts"]),
            "domain_counts": dict(roster["domain_counts"]),
        },
        "baseline_sources": baseline_sources,
        "pairing": (
            "every one of the 4,000 rows is paired with its OWN sealed official-protocol "
            "output; nothing was re-flown on the baseline side"
        ),
        "primary": {
            "metric": "official tool accuracy (a2t-toolcall-official)",
            "natural_mixture": contrast_as_dict(primary),
            "equal_domain": equal_domain_delta(roster_ids, left, right, domains),
            "per_tier_table": per_stratum_table(primary),
            "per_domain_table": per_stratum_table(domain_contrasts["tool_accuracy"]),
        },
        "secondary": {
            metric: contrast_as_dict(contrasts[metric])
            for metric in METRICS
            if metric != "tool_accuracy"
        },
        "param_f1": {
            "baseline_macro_pct": 100.0 * mean(list(base_rows.values()), "param_f1"),
            "org1_macro_pct": 100.0 * mean(list(org_rows.values()), "param_f1"),
            "baseline_micro_pct": 100.0 * micro_param_f1(list(base_rows.values())),
            "org1_micro_pct": 100.0 * micro_param_f1(list(org_rows.values())),
            "note": (
                "the official parameter F1 is a macro average of per-sample key P/R/F1; the "
                "micro figure pools keys across samples and is reported beside it"
            ),
        },
        "per_tier": per_tier,
        "per_domain": per_domain_overall,
        "confusion": {
            "note": (
                "diagnostic; the miss classes are resolved from tools_registry.csv (the "
                "predicted tool's domain against the gold tool's), never asserted"
            ),
            "before": before,
            "after": after,
            "named_twins": twins,
            "named_twins_cross_domain_before": sum(
                row["rows_before"] for row in twins if row["class"] == "cross_domain"
            ),
            "named_twins_cross_domain_after": sum(
                row["rows_after"] for row in twins if row["class"] == "cross_domain"
            ),
            "named_twins_same_domain_before": sum(
                row["rows_before"] for row in twins if row["class"] == "same_domain"
            ),
            "named_twins_same_domain_after": sum(
                row["rows_after"] for row in twins if row["class"] == "same_domain"
            ),
        },
        "gain_decomposition": {
            "rows_corrected": len(corrected),
            "rows_broken": len(broken),
            "net": len(corrected) - len(broken),
            "corrected_by_baseline_miss_class": dict(sorted(corrected_classes.items())),
            "broken_by_org1_miss_class": dict(sorted(broken_classes.items())),
            "cross_domain_share_of_the_gain": cross_share,
            "cross_domain_share_definition": (
                "(baseline misses corrected whose baseline prediction was a real registry "
                "tool in ANOTHER domain) / (all baseline misses corrected)"
            ),
        },
        "decision": {
            "outcome": outcome,
            "rule": (
                "ADMITTED = pooled CI90 lower bound above 0 AND the gain concentrated on "
                "smart_home cross-domain twins (smart_home delta positive and at least as "
                "large as every other domain's, and the cross-domain share of the gain at "
                "least 0.50); NULL = CI90 includes 0, or the CI90 is positive but the gain "
                "is not so concentrated; HARMFUL = CI90 upper bound below 0"
            ),
            "ci90_low_pp": low,
            "ci90_high_pp": high,
            "concentrated_on_smart_home_cross_domain_twins": concentrated,
            "smart_home_delta_pp": smart_home_delta,
            "other_domain_deltas_pp": other_deltas,
            "baseline_unchanged": (
                "no outcome changes the direct baseline: the official-protocol cell stays "
                "the comparator every mechanism is paired against"
            ),
        },
        "scorer_versions": {
            "official": org_official["aggregate"]["scorer_version"],
            "official_commit": org_official["aggregate"]["official_commit"],
            "official_gold": org_official["aggregate"]["gold_version"],
            "official_metrics_blob_sha1": org_official["aggregate"][
                "official_metrics_blob_sha1"
            ],
            "v2": org_v2["aggregate"]["scorer_version"],
            "v2_gold": org_v2["aggregate"]["gold_version"],
            "parse": org_v2["aggregate"]["parse_version"],
        },
        "overall": {
            "samples": len(roster_ids),
            "baseline_tool_accuracy_pct": 100.0 * primary.left_mean,
            "org1_tool_accuracy_pct": 100.0 * primary.right_mean,
            "baseline_parse_rate_pct": 100.0 * mean(list(base_rows.values()), "parsed"),
            "org1_parse_rate_pct": 100.0 * mean(list(org_rows.values()), "parsed"),
            "org1_parse_failures": int(org_official["aggregate"]["parse_failures"]),
            "baseline_rows_with_multiple_call_matches": sum(
                1 for row in base_rows.values() if int(row["official_call_matches"]) > 1
            ),
            "org1_rows_with_multiple_call_matches": sum(
                1 for row in org_rows.values() if int(row["official_call_matches"]) > 1
            ),
        },
        "throughput": {
            "planned_model_calls": manifest["plan"]["planned_model_calls"],
            "planned_speech_audio_seconds": manifest["plan"]["planned_speech_audio_seconds"],
            "planned_gpu_hours": manifest["plan"]["planned_gpu_hours"],
            "calls_used": manifest["cost"]["calls_used"],
            "audio_seconds_used": manifest["cost"]["audio_seconds_used"],
            "prompt_tokens_total": manifest["cost"]["prompt_tokens_total"],
            "prompt_tokens_per_call": (
                manifest["cost"]["prompt_tokens_total"] / manifest["cost"]["calls_used"]
            ),
            "completion_tokens_total": manifest["cost"]["completion_tokens_total"],
            "completion_tokens_per_call": (
                manifest["cost"]["completion_tokens_total"] / manifest["cost"]["calls_used"]
            ),
            "latency_seconds_total": manifest["cost"]["latency_seconds_total"],
            "mean_per_call_latency_seconds": (
                manifest["cost"]["latency_seconds_total"] / manifest["cost"]["calls_used"]
            ),
            "status": manifest["status"],
            "study_repo_dirt": manifest["study_repo_dirt"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", default=None)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    document = build(attempt=args.attempt or latest_attempt(RUN_ID))
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "result-summary.json"
        out_path.write_text(payload, encoding="utf-8", newline="\n")
        print("written: %s (sha256 %s)" % (out_path, sha256_file(out_path)))

    primary = document["primary"]["natural_mixture"]
    print()
    print(
        "%s attempt %s  n=%d"
        % (document["cell_id"], document["attempt_id"], document["overall"]["samples"])
    )
    print(
        "POOLED official tool accuracy: baseline %.2f -> ORG-1 %.2f  delta %+.2f pp "
        "CI90 [%+.2f, %+.2f]  saves %d harms %d ties %d  sign p=%.4f"
        % (
            primary["baseline_pct"],
            primary["org1_pct"],
            primary["delta_pp"],
            primary["ci90_low_pp"],
            primary["ci90_high_pp"],
            primary["saves"],
            primary["harms"],
            primary["ties"],
            primary["sign_test_p"],
        )
    )
    equal = document["primary"]["equal_domain"]
    print(
        "EQUAL-DOMAIN: baseline %.2f -> ORG-1 %.2f  delta %+.2f pp CI90 [%+.2f, %+.2f]"
        % (
            equal["left_pct"],
            equal["right_pct"],
            equal["delta_pp"],
            equal["ci90_low_pp"],
            equal["ci90_high_pp"],
        )
    )
    print()
    print(
        "%-24s %8s %8s %8s %8s %8s %6s %6s"
        % ("tier", "base", "ORG-1", "delta", "paper", "vs paper", "saves", "harms")
    )
    for row in document["primary"]["per_tier_table"]:
        tier = row["stratum"]
        block = document["per_tier"][tier]
        print(
            "%-24s %8.2f %8.2f %+8.2f %8.1f %+8.2f %6d %6d"
            % (
                tier,
                100.0 * row["left_mean"],
                100.0 * row["right_mean"],
                100.0 * row["delta"],
                block["paper"]["tool_accuracy"],
                block["org1_minus_paper_pp"],
                row["saves"],
                row["harms"],
            )
        )
    print()
    print("by domain:")
    for domain, block in document["per_domain"].items():
        print(
            "  %-12s n=%-5d base %6.2f -> ORG-1 %6.2f  delta %+6.2f  saves %d harms %d"
            % (
                domain,
                block["n"],
                block["baseline"]["tool_accuracy"]["pct"],
                block["org1"]["tool_accuracy"]["pct"],
                block["delta_pp"]["tool_accuracy"],
                block["saves"],
                block["harms"],
            )
        )
    print()
    print("secondary:")
    for metric, block in document["secondary"].items():
        print(
            "  %-18s base %7.3f -> ORG-1 %7.3f  delta %+6.3f pp CI90 [%+6.3f, %+6.3f] "
            "saves %4d harms %4d p=%.4f"
            % (
                metric,
                block["baseline_pct"],
                block["org1_pct"],
                block["delta_pp"],
                block["ci90_low_pp"],
                block["ci90_high_pp"],
                block["saves"],
                block["harms"],
                block["sign_test_p"],
            )
        )
    print()
    gain = document["gain_decomposition"]
    print(
        "gain: corrected %d, broken %d, net %+d; cross-domain share of the gain %s"
        % (
            gain["rows_corrected"],
            gain["rows_broken"],
            gain["net"],
            (
                "%.3f" % gain["cross_domain_share_of_the_gain"]
                if gain["cross_domain_share_of_the_gain"] is not None
                else "n/a"
            ),
        )
    )
    print("  corrected by baseline miss class: %s" % gain["corrected_by_baseline_miss_class"])
    print("  broken by ORG-1 miss class:      %s" % gain["broken_by_org1_miss_class"])
    print()
    print("miss classes before: %s" % document["confusion"]["before"]["miss_classes"])
    print("miss classes after:  %s" % document["confusion"]["after"]["miss_classes"])
    print()
    print("%-26s -> %-26s %-13s %7s %7s %7s" % ("gold", "predicted", "class", "before", "after", "delta"))
    for row in document["confusion"]["named_twins"]:
        print(
            "%-26s -> %-26s %-13s %7d %7d %+7d"
            % (
                row["gold_tool"],
                row["predicted_tool"],
                row["class"],
                row["rows_before"],
                row["rows_after"],
                row["delta"],
            )
        )
    print()
    print("DECISION: %s" % document["decision"]["outcome"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
