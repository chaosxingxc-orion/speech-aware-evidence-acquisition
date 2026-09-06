#!/usr/bin/env python3
"""Verdict numbers for N Audio2Tool arms on the union 4,000 roster.

Reads only bytes that are already sealed -- each arm's own manifest and the
three 2026-09-04 official-population manifests whose 4,000 rows every arm is
paired against -- and writes ``result-summary.json``. Zero model, GPU or
network contact; gold enters only through the registered scorers, exactly as
it does when a flight finalizes.

2026-09-05 (KC-A1): the script was written for the single ORG-1 arm and is
now N-arm rather than forked. ``--arm cell_id=run_id[:attempt]`` is
repeatable; every arm is paired against the SAME sealed baseline rows (read
once), and each arm after the first is additionally paired against the first,
which is what separates a treatment from its same-length control. ``--rule``
selects the preregistered decision rule (``org1``, the default, or ``kc-a1``,
whose admission clause is the MF-1 TARGET-pair share of the gain). The per-arm
block is the ORG-1 computation with ``org1`` renamed ``arm``, so the sealed
2026-09-05 ORG-1 summary (schema ...-v1) stays as sealed while a re-run of
that arm reproduces its numbers under the v2 key names.

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
    python a2t_org1_domain_grouped_analysis.py --rule kc-a1         --arm KC-A1-contrast-raw=SAEA-A2T-KC-A1-CONTRAST-NOTES-V1         --arm KC-A1c-category-raw=SAEA-A2T-KC-A1C-CATEGORY-ONLY-V1         --out-dir docs/checks/speech-aware-evidence-acquisition/2026-09-05-a2t-kc-a1-contrast-notes-4000-v1 --write
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

#: The repository this file belongs to, whichever checkout that is. It was a
#: hard-coded main-checkout path; deriving it from the file's own location is
#: the SAME path there and additionally lets a prep worktree run the analysis
#: against its own configs and receipts.
REPO = Path(__file__).resolve().parents[1]

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

#: MF-1's own receipt: the five disjoint TARGET tool sets KC-A1's decision
#: rule counts corrected rows against. Read, never restated here.
TARGETS_RECEIPT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-a2t-query-cue-audit"
    / "summary.json"
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
        "arm_pct": 100.0 * contrast.right_mean,
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


def target_map() -> tuple[dict[str, str], dict[str, object]]:
    """``(tool -> MF-1 target id, provenance)`` from the audit receipt.

    KC-A1's decision rule asks how many corrected rows were TARGET-pair
    misses, which is a property of the MF-1 receipt and not of this run, so
    the map is READ from that receipt with its hash recorded rather than
    restated here. A tree without the receipt yields an empty map and every
    target statistic is then reported as ``null``.
    """

    if not TARGETS_RECEIPT.is_file():
        return {}, {"receipt": None, "targets": 0}
    document = json.loads(TARGETS_RECEIPT.read_text(encoding="utf-8"))
    targets = document["primary_population"]["targets"]["targets"]
    by_tool = {
        str(tool): str(entry["target_id"]) for entry in targets for tool in entry["tools"]
    }
    return by_tool, {
        "receipt": str(TARGETS_RECEIPT.relative_to(REPO)).replace("\\", "/"),
        "receipt_sha256": sha256_file(TARGETS_RECEIPT),
        "targets": len(targets),
        "tools": len(by_tool),
        "definition": (
            "a miss is a TARGET-PAIR miss when the gold tool and the predicted tool sit "
            "inside the SAME MF-1 target -- the component definition of the audit's own "
            "table, resolved from the receipt and never asserted here"
        ),
    }


def target_pair_miss(row: Mapping[str, object], targets: Mapping[str, str]) -> str | None:
    """The target id a miss sits inside, or ``None``."""

    if row["tool_correct"] or not targets:
        return None
    gold, predicted = str(row["gold_tool"]), str(row["predicted_tool"] or "")
    if gold in targets and predicted in targets and targets[gold] == targets[predicted]:
        return targets[gold]
    return None


def build_arm(
    cell_id: str,
    run_id: str,
    attempt: str,
    *,
    roster_ids: Sequence[str],
    domains: Mapping[str, str],
    registry: Mapping[str, Mapping[str, str]],
    left: Mapping[str, Mapping[str, float]],
    base_rows: Mapping[str, Mapping[str, object]],
    targets: Mapping[str, str],
    rule: str,
) -> tuple[dict[str, object], dict[str, dict[str, float]], dict[str, Mapping[str, object]]]:
    """One arm's whole paired summary against the sealed baseline.

    Returns the summary plus this arm's per-sample score and official-row maps,
    so a caller can pair two ARMS against each other without rescoring.
    """

    from speech_aware_evidence_acquisition.analysis.paired import (
        paired_contrast,
        per_stratum_table,
    )

    official = rescore(run_id, attempt, "a2t-toolcall-official")
    v2 = rescore(run_id, attempt, "a2t-toolcall-v2")
    right, arm_rows = arm_scores(official, v2)
    missing = [sample_id for sample_id in roster_ids if sample_id not in right]
    if missing:
        raise SystemExit(
            "%s: %d roster rows missing (first: %s)" % (cell_id, len(missing), missing[:3])
        )
    right = {sample_id: right[sample_id] for sample_id in roster_ids}
    arm_rows = {sample_id: arm_rows[sample_id] for sample_id in roster_ids}

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
        strata_of=lambda sample_id: domains[sample_id],
        seed=SEED,
        n_replicates=REPLICATES,
        ci_level=CI_LEVEL,
    )

    # ---- per tier, with the paper column -------------------------------
    per_tier: dict[str, object] = {}
    for tier in TIERS:
        ids = [sample_id for sample_id in roster_ids if tier_of(sample_id) == tier]
        base_tier = [base_rows[sample_id] for sample_id in ids]
        arm_tier = [arm_rows[sample_id] for sample_id in ids]
        base_ta = rate(base_tier, "tool_correct")
        arm_ta = rate(arm_tier, "tool_correct")
        per_domain: dict[str, object] = {}
        for domain in sorted({domains[sample_id] for sample_id in ids}):
            members = [sample_id for sample_id in ids if domains[sample_id] == domain]
            per_domain[domain] = {
                "n": len(members),
                "baseline_pct": 100.0
                * sum(left[s]["tool_accuracy"] for s in members)
                / len(members),
                "arm_pct": 100.0
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
            "arm": {
                "tool_accuracy": arm_ta,
                "exact_match": rate(arm_tier, "exact_match"),
                "param_f1_macro_pct": 100.0 * mean(arm_tier, "param_f1"),
                "param_f1_micro_pct": 100.0 * micro_param_f1(arm_tier),
                "parse_rate_pct": 100.0 * mean(arm_tier, "parsed"),
            },
            "paper": PAPER[tier],
            "delta_pp": {
                "tool_accuracy": arm_ta["pct"] - base_ta["pct"],
                "exact_match": rate(arm_tier, "exact_match")["pct"]
                - rate(base_tier, "exact_match")["pct"],
            },
            "arm_minus_paper_pp": arm_ta["pct"] - PAPER[tier]["tool_accuracy"],
            "baseline_minus_paper_pp": base_ta["pct"] - PAPER[tier]["tool_accuracy"],
            "per_domain": per_domain,
        }

    # ---- per domain ------------------------------------------------------
    per_domain_overall: dict[str, object] = {}
    for domain in sorted(set(domains[sample_id] for sample_id in roster_ids)):
        ids = [sample_id for sample_id in roster_ids if domains[sample_id] == domain]
        base_dom = [base_rows[sample_id] for sample_id in ids]
        arm_dom = [arm_rows[sample_id] for sample_id in ids]
        per_domain_overall[domain] = {
            "n": len(ids),
            "baseline": {
                "tool_accuracy": rate(base_dom, "tool_correct"),
                "exact_match": rate(base_dom, "exact_match"),
            },
            "arm": {
                "tool_accuracy": rate(arm_dom, "tool_correct"),
                "exact_match": rate(arm_dom, "exact_match"),
            },
            "delta_pp": {
                "tool_accuracy": rate(arm_dom, "tool_correct")["pct"]
                - rate(base_dom, "tool_correct")["pct"],
                "exact_match": rate(arm_dom, "exact_match")["pct"]
                - rate(base_dom, "exact_match")["pct"],
            },
            "saves": sum(
                1 for s in ids if right[s]["tool_accuracy"] > left[s]["tool_accuracy"]
            ),
            "harms": sum(
                1 for s in ids if right[s]["tool_accuracy"] < left[s]["tool_accuracy"]
            ),
        }

    # ---- confusion, before and after ------------------------------------
    before = confusion_block(base_rows, domains, registry)
    after = confusion_block(arm_rows, domains, registry)
    twins = named_twin_table(before.pop("_pairs"), after.pop("_pairs"), registry)

    # ---- gain decomposition, including the MF-1 target pairs -------------
    corrected = [
        s for s in roster_ids if not base_rows[s]["tool_correct"] and arm_rows[s]["tool_correct"]
    ]
    broken = [
        s for s in roster_ids if base_rows[s]["tool_correct"] and not arm_rows[s]["tool_correct"]
    ]
    corrected_classes = Counter(
        classify_miss(base_rows[s], domains[s], registry) for s in corrected
    )
    broken_classes = Counter(
        classify_miss(arm_rows[s], domains[s], registry) for s in broken
    )
    cross_share = (
        corrected_classes["cross_domain_twin"] / len(corrected) if corrected else None
    )
    target_before = Counter(
        target_pair_miss(row, targets)
        for row in base_rows.values()
        if target_pair_miss(row, targets)
    )
    target_after = Counter(
        target_pair_miss(row, targets)
        for row in arm_rows.values()
        if target_pair_miss(row, targets)
    )
    corrected_on_targets = [s for s in corrected if target_pair_miss(base_rows[s], targets)]
    target_share = (
        len(corrected_on_targets) / len(corrected) if corrected and targets else None
    )

    # ---- decision --------------------------------------------------------
    primary = contrasts["tool_accuracy"]
    low = 100.0 * primary.bootstrap.ci_low
    high = 100.0 * primary.bootstrap.ci_high
    equal_domain = equal_domain_delta(roster_ids, left, right, domains)
    weightings_agree = (100.0 * primary.delta) * equal_domain["delta_pp"] > 0
    if rule == "kc-a1":
        admitted = bool(
            low > 0.0
            and weightings_agree
            and equal_domain["delta_pp"] > 0
            and target_share is not None
            and target_share >= 0.5
        )
        rule_text = (
            "ADMITTED = pooled CI90 lower bound above 0, both weightings agreeing in sign, "
            "and at least half of the corrected rows carrying a baseline miss whose gold "
            "AND predicted tool sit inside one MF-1 target; HARMFUL = CI90 upper bound "
            "below 0; NULL otherwise. A gain is credited as CONTENT only if the "
            "same-length control does not reach a comparable delta (cross_arm below)."
        )
    else:
        smart_home = per_domain_overall.get("smart_home", {})
        smart_home_delta = smart_home["delta_pp"]["tool_accuracy"] if smart_home else 0.0
        other_deltas = [
            block["delta_pp"]["tool_accuracy"]
            for name, block in per_domain_overall.items()
            if name != "smart_home"
        ]
        admitted = bool(
            low > 0.0
            and smart_home_delta > 0
            and (not other_deltas or smart_home_delta >= max(other_deltas))
            and (cross_share is not None and cross_share >= 0.5)
        )
        rule_text = (
            "ADMITTED = pooled CI90 lower bound above 0 AND the gain concentrated on "
            "smart_home cross-domain twins (smart_home delta positive and at least as "
            "large as every other domain's, and the cross-domain share of the gain at "
            "least 0.50); NULL = CI90 includes 0, or the CI90 is positive but the gain is "
            "not so concentrated; HARMFUL = CI90 upper bound below 0"
        )
    if low > 0.0 and admitted:
        outcome = "ADMITTED"
    elif high < 0.0:
        outcome = "HARMFUL"
    else:
        outcome = "NULL"

    manifest = load_manifest(run_id, attempt)
    summary = {
        "cell_id": cell_id,
        "run_id": run_id,
        "attempt_id": attempt,
        "manifest_sha256": sha256_file(run_dir(run_id, attempt) / f"{run_id}.run-manifest.json"),
        "study_commit": manifest["study_commit"],
        "protocol_hash": manifest["protocol_hash"],
        "primary": {
            "metric": "official tool accuracy (a2t-toolcall-official)",
            "natural_mixture": contrast_as_dict(primary),
            "equal_domain": equal_domain,
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
            "arm_macro_pct": 100.0 * mean(list(arm_rows.values()), "param_f1"),
            "baseline_micro_pct": 100.0 * micro_param_f1(list(base_rows.values())),
            "arm_micro_pct": 100.0 * micro_param_f1(list(arm_rows.values())),
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
            "broken_by_arm_miss_class": dict(sorted(broken_classes.items())),
            "cross_domain_share_of_the_gain": cross_share,
            "cross_domain_share_definition": (
                "(baseline misses corrected whose baseline prediction was a real registry "
                "tool in ANOTHER domain) / (all baseline misses corrected)"
            ),
            "corrected_on_target_pairs": len(corrected_on_targets),
            "target_pair_share_of_the_gain": target_share,
        },
        "mf1_targets": {
            "miss_mass_before": dict(sorted(target_before.items())),
            "miss_mass_after": dict(sorted(target_after.items())),
            "miss_mass_before_total": sum(target_before.values()),
            "miss_mass_after_total": sum(target_after.values()),
        },
        "decision": {
            "rule_id": rule,
            "outcome": outcome,
            "rule": rule_text,
            "ci90_low_pp": low,
            "ci90_high_pp": high,
            "weightings_agree_in_sign": weightings_agree,
            "target_pair_share_of_the_gain": target_share,
            "cross_domain_share_of_the_gain": cross_share,
            "baseline_unchanged": (
                "no outcome changes the direct baseline: the official-protocol cell stays "
                "the comparator every mechanism is paired against"
            ),
        },
        "scorer_versions": {
            "official": official["aggregate"]["scorer_version"],
            "official_commit": official["aggregate"]["official_commit"],
            "official_gold": official["aggregate"]["gold_version"],
            "official_metrics_blob_sha1": official["aggregate"]["official_metrics_blob_sha1"],
            "v2": v2["aggregate"]["scorer_version"],
            "v2_gold": v2["aggregate"]["gold_version"],
            "parse": v2["aggregate"]["parse_version"],
        },
        "overall": {
            "samples": len(roster_ids),
            "baseline_tool_accuracy_pct": 100.0 * primary.left_mean,
            "arm_tool_accuracy_pct": 100.0 * primary.right_mean,
            "baseline_parse_rate_pct": 100.0 * mean(list(base_rows.values()), "parsed"),
            "arm_parse_rate_pct": 100.0 * mean(list(arm_rows.values()), "parsed"),
            "arm_parse_failures": int(official["aggregate"]["parse_failures"]),
            "baseline_rows_with_multiple_call_matches": sum(
                1 for row in base_rows.values() if int(row["official_call_matches"]) > 1
            ),
            "arm_rows_with_multiple_call_matches": sum(
                1 for row in arm_rows.values() if int(row["official_call_matches"]) > 1
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
    return summary, right, arm_rows


def build(*, arms: Sequence[tuple[str, str, str]], rule: str) -> dict[str, object]:
    """Every requested arm, each paired against the SAME sealed baseline rows,
    plus each later arm paired against the first one.

    The baselines are read once: the three official-population manifests are
    the comparator for every arm on this roster, so N arms cost N rescorings
    and not 4N, and every delta in the document is over one identical row set.
    """

    from speech_aware_evidence_acquisition.analysis.paired import paired_contrast

    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    domains = domain_by_sample(roster)
    registry = registry_rows()
    roster_ids = sorted(str(item["sample_id"]) for item in roster["items"])
    targets, target_provenance = target_map()

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
        baseline_sources.append(
            {
                "run_id": run_id,
                "cell_id": cell,
                "attempt_id": base_attempt,
                "rows": len(scores),
                "manifest_sha256": sha256_file(
                    run_dir(run_id, base_attempt) / f"{run_id}.run-manifest.json"
                ),
                "study_commit": str(load_manifest(run_id, base_attempt)["study_commit"]),
            }
        )
    missing = [s for s in roster_ids if s not in left]
    if missing:
        raise SystemExit("baseline is missing %d roster rows (first: %s)" % (len(missing), missing[:3]))
    left = {s: left[s] for s in roster_ids}
    base_rows = {s: base_rows[s] for s in roster_ids}

    summaries: dict[str, object] = {}
    scores_by_arm: dict[str, dict[str, dict[str, float]]] = {}
    for cell_id, run_id, attempt in arms:
        summary, right, _ = build_arm(
            cell_id,
            run_id,
            attempt,
            roster_ids=roster_ids,
            domains=domains,
            registry=registry,
            left=left,
            base_rows=base_rows,
            targets=targets,
            rule=rule,
        )
        summaries[cell_id] = summary
        scores_by_arm[cell_id] = right

    cross_arm = []
    first = arms[0][0]
    for cell_id, _, _ in arms[1:]:
        contrast = paired_contrast(
            scores_by_arm[cell_id],
            scores_by_arm[first],
            metrics=("tool_accuracy",),
            sample_ids=roster_ids,
            strata_of=lambda sample_id: sample_id.rsplit(":", 1)[0],
            seed=SEED,
            n_replicates=REPLICATES,
            ci_level=CI_LEVEL,
        )["tool_accuracy"]
        block = contrast_as_dict(contrast)
        block.update(
            {
                "left_cell_id": cell_id,
                "right_cell_id": first,
                "delta_definition": f"{first} minus {cell_id} on the same 4,000 rows",
                "content_effect_credited": 100.0 * contrast.bootstrap.ci_low > 0.0,
                "rule": (
                    "a gain is credited as CONTENT only when this contrast's CI90 lower "
                    "bound is above 0; a control reaching a comparable delta attributes the "
                    "gain to prompt FORM instead"
                ),
            }
        )
        cross_arm.append(block)

    return {
        "schema": "saea-a2t-paired-arms-result-summary-v2",
        "study": "speech-aware-evidence-acquisition",
        "schema_note": (
            "v2 generalizes the single-arm ORG-1 summary (schema saea-a2t-org1-domain-"
            "grouped-result-summary-v1, sealed 2026-09-05) to N arms: the per-arm block is "
            "the same computation with 'org1' renamed 'arm', and the sealed v1 file stays "
            "as sealed. Re-running the ORG-1 arm here reproduces its numbers exactly"
        ),
        "arms_requested": [
            {"cell_id": cell_id, "run_id": run_id, "attempt_id": attempt}
            for cell_id, run_id, attempt in arms
        ],
        "decision_rule_id": rule,
        "paper_source": "arXiv:2604.22821 Table 3, Qwen-3-Omni-30B",
        "paper_column_note": (
            "reported beside every tier as a CEILING reference. No gate in this run is set "
            "relative to it: every decision is a paired delta against the sealed "
            "official-protocol cells and, for a control, against the treatment arm"
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
        "mf1_target_provenance": target_provenance,
        "pairing": (
            "every one of the 4,000 rows is paired with its OWN sealed official-protocol "
            "output; nothing was re-flown on the baseline side. Arm-versus-arm contrasts "
            "pair the same rows between two flown arms"
        ),
        "arms": summaries,
        "cross_arm": cross_arm,
    }


def parse_arm(value: str) -> tuple[str, str, str]:
    """``cell_id=run_id[:attempt_id]``; the attempt defaults to the latest."""

    cell_id, _, rest = value.partition("=")
    if not cell_id or not rest:
        raise SystemExit(f"--arm wants cell_id=run_id[:attempt_id], got {value!r}")
    run_id, _, attempt = rest.partition(":")
    return cell_id, run_id, attempt or latest_attempt(run_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--arm",
        action="append",
        default=None,
        help=(
            "cell_id=run_id[:attempt_id], repeatable. Every arm is paired against the same "
            "sealed baseline rows, and each arm after the first is also paired against the "
            "first (the treatment/control contrast). Default: the ORG-1 arm"
        ),
    )
    parser.add_argument("--rule", default="org1", choices=("org1", "kc-a1"))
    parser.add_argument("--attempt", default=None, help="attempt for the DEFAULT arm")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    arms = (
        [parse_arm(value) for value in args.arm]
        if args.arm
        else [(CELL, RUN_ID, args.attempt or latest_attempt(RUN_ID))]
    )
    document = build(arms=arms, rule=args.rule)
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "result-summary.json"
        out_path.write_text(payload, encoding="utf-8", newline="\n")
        print("written: %s (sha256 %s)" % (out_path, sha256_file(out_path)))

    for cell_id, block in document["arms"].items():
        primary = block["primary"]["natural_mixture"]
        equal = block["primary"]["equal_domain"]
        print()
        print("%s attempt %s  n=%d" % (cell_id, block["attempt_id"], block["overall"]["samples"]))
        print(
            "POOLED official tool accuracy: baseline %.2f -> arm %.2f  delta %+.2f pp "
            "CI90 [%+.2f, %+.2f]  saves %d harms %d ties %d  sign p=%.4f"
            % (
                primary["baseline_pct"],
                primary["arm_pct"],
                primary["delta_pp"],
                primary["ci90_low_pp"],
                primary["ci90_high_pp"],
                primary["saves"],
                primary["harms"],
                primary["ties"],
                primary["sign_test_p"],
            )
        )
        print(
            "EQUAL-DOMAIN: baseline %.2f -> arm %.2f  delta %+.2f pp CI90 [%+.2f, %+.2f]"
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
            % ("tier", "base", "arm", "delta", "paper", "vs paper", "saves", "harms")
        )
        for row in block["primary"]["per_tier_table"]:
            tier = row["stratum"]
            tier_block = block["per_tier"][tier]
            print(
                "%-24s %8.2f %8.2f %+8.2f %8.1f %+8.2f %6d %6d"
                % (
                    tier,
                    100.0 * row["left_mean"],
                    100.0 * row["right_mean"],
                    100.0 * row["delta"],
                    tier_block["paper"]["tool_accuracy"],
                    tier_block["arm_minus_paper_pp"],
                    row["saves"],
                    row["harms"],
                )
            )
        print()
        print("by domain:")
        for domain, domain_block in block["per_domain"].items():
            print(
                "  %-12s n=%-5d base %6.2f -> arm %6.2f  delta %+6.2f  saves %d harms %d"
                % (
                    domain,
                    domain_block["n"],
                    domain_block["baseline"]["tool_accuracy"]["pct"],
                    domain_block["arm"]["tool_accuracy"]["pct"],
                    domain_block["delta_pp"]["tool_accuracy"],
                    domain_block["saves"],
                    domain_block["harms"],
                )
            )
        print()
        print("secondary:")
        for metric, metric_block in block["secondary"].items():
            print(
                "  %-18s base %7.3f -> arm %7.3f  delta %+6.3f pp CI90 [%+6.3f, %+6.3f] "
                "saves %4d harms %4d p=%.4f"
                % (
                    metric,
                    metric_block["baseline_pct"],
                    metric_block["arm_pct"],
                    metric_block["delta_pp"],
                    metric_block["ci90_low_pp"],
                    metric_block["ci90_high_pp"],
                    metric_block["saves"],
                    metric_block["harms"],
                    metric_block["sign_test_p"],
                )
            )
        print()
        gain = block["gain_decomposition"]
        print(
            "gain: corrected %d, broken %d, net %+d; cross-domain share %s; MF-1 target-pair share %s"
            % (
                gain["rows_corrected"],
                gain["rows_broken"],
                gain["net"],
                (
                    "%.3f" % gain["cross_domain_share_of_the_gain"]
                    if gain["cross_domain_share_of_the_gain"] is not None
                    else "n/a"
                ),
                (
                    "%.3f" % gain["target_pair_share_of_the_gain"]
                    if gain["target_pair_share_of_the_gain"] is not None
                    else "n/a"
                ),
            )
        )
        print("  corrected by baseline miss class: %s" % gain["corrected_by_baseline_miss_class"])
        print("  broken by arm miss class:         %s" % gain["broken_by_arm_miss_class"])
        print(
            "  MF-1 target miss mass: %d -> %d  %s"
            % (
                block["mf1_targets"]["miss_mass_before_total"],
                block["mf1_targets"]["miss_mass_after_total"],
                block["mf1_targets"]["miss_mass_after"],
            )
        )
        print()
        print("miss classes before: %s" % block["confusion"]["before"]["miss_classes"])
        print("miss classes after:  %s" % block["confusion"]["after"]["miss_classes"])
        print()
        print(
            "%-26s -> %-26s %-13s %7s %7s %7s"
            % ("gold", "predicted", "class", "before", "after", "delta")
        )
        for row in block["confusion"]["named_twins"]:
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
        print("DECISION (%s): %s" % (block["decision"]["rule_id"], block["decision"]["outcome"]))

    for block in document["cross_arm"]:
        print()
        print(
            "ARM vs ARM: %s minus %s  delta %+.2f pp CI90 [%+.2f, %+.2f]  saves %d harms %d "
            "-> content credited: %s"
            % (
                block["right_cell_id"],
                block["left_cell_id"],
                block["delta_pp"],
                block["ci90_low_pp"],
                block["ci90_high_pp"],
                block["saves"],
                block["harms"],
                block["content_effect_credited"],
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
