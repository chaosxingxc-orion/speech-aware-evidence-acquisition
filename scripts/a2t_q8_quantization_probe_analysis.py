#!/usr/bin/env python3
"""Verdict numbers for the Audio2Tool Q8_0 quantization probe.

Reads only bytes two registered runs already sealed -- this probe's
``SAEA-A2T-Q8-QUANTIZATION-PROBE-V1`` and the predecessor
``SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1`` -- and writes
``result-summary.json``. Zero model, GPU or network contact; gold enters only
through the registered scorers, exactly as it does when a flight finalizes.

What it produces, all preregistered in
``docs/readiness/2026-09-04-a2t-q8-quantization-probe-v1-preregistration.md``
section 6:

* the Q8 cell's per-tier official-scorer table with the paper row and a Wilson
  CI90 at n = 50, beside the sealed Q4_K_M cell's own figures;
* the PAIRED contrast C-q8 minus R-official-raw over the same 400 rows, per
  tier and pooled, under the official scorer and under ``a2t-toolcall-v2``:
  saves / harms / ties, exact sign test, 10,000 tier-stratified bootstrap
  replicates, seed 20260903, CI90;
* the same paired contrast pooled over the four acceptance tiers (1, 2, 5, 6),
  which is what the decision rule reads;
* per-domain tables (wearables / smart_car / smart_home) for both cells and
  the paired per-domain contrast, because every official-population verdict of
  2026-09-04 found smart_home to be the weak stratum;
* the three-outcome decision QUANTIZATION-DOMINANT / QUANTIZATION-EXCLUDED /
  PARTIAL, with the fraction of each tier's gap to the paper that Q8 closes;
* parse and multi-call statistics, throughput and memory.

Usage (WSL2, model-free)::

    python scripts/a2t_q8_quantization_probe_analysis.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Callable, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]

Q8_RUN_ID = "SAEA-A2T-Q8-QUANTIZATION-PROBE-V1"
Q8_CELL = "C-q8-official-raw"
Q4_RUN_ID = "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1"
Q4_ATTEMPT = "attempt-20260904T135250Z-rofficialraw"
Q4_CELL = "R-official-raw"

ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-calibration-400-roster"
    / "flight-roster-receipt.json"
)
OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-q8-quantization-probe-400-v1"
)
PLACEMENT_RECEIPT = OUT_DIR / "placement" / "placement-fit.json"
PROMPT_FIT_RECEIPT = OUT_DIR / "prompt-fit" / "prompt-fit.json"

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
    "tier1_direct": {"tool_accuracy": 92.4, "exact_match": 92.4},
    "tier2_parametric": {"tool_accuracy": 84.6, "exact_match": 15.6},
    "tier3_multi_intent": {"tool_accuracy": 74.7, "exact_match": 28.6},
    "tier4_implicit": {"tool_accuracy": 33.4, "exact_match": 11.3},
    "tier5_needle": {"tool_accuracy": 90.6, "exact_match": 36.0},
    "tier6_correction": {"tool_accuracy": 81.5, "exact_match": 24.8},
    "tier7_multiturn": {"tool_accuracy": 54.6, "exact_match": 16.3},
    "tier8_intent_blending": {"tool_accuracy": 41.7, "exact_match": 12.4},
}
ACCEPTANCE_TIERS = ("tier1_direct", "tier2_parametric", "tier5_needle", "tier6_correction")
# The replication preregistration's own band (section 7 of
# docs/readiness/2026-09-04-a2t-official-protocol-replication-v1-preregistration.md),
# which the Q8 preregistration's decision rule refers to by name.
REPLICATION_BAND_PP = 5.0
# The owner's later 3-point alignment standard, reported beside it, never
# substituted for it.
OWNER_BAND_PP = 3.0
Z_90 = 1.6448536269514722
BOOTSTRAP_SEED = 20260903
BOOTSTRAP_REPLICATES = 10_000
CI_LEVEL = 0.90


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
        raise SystemExit("run %s has no attempt directory" % run_id)
    return attempts[-1]


def run_dir(run_id: str, attempt: str) -> Path:
    return data_root_path() / "runs" / run_id / attempt


def load_manifest(run_id: str, attempt: str) -> Mapping[str, object]:
    return json.loads(
        (run_dir(run_id, attempt) / ("%s.run-manifest.json" % run_id)).read_text(
            encoding="utf-8"
        )
    )


def rescore(run_id: str, attempt: str, scorer: str) -> Mapping[str, object]:
    """Re-score already sealed outputs with a registered scorer. Zero contact."""

    from speech_aware_evidence_acquisition.core.base import SCORERS
    import speech_aware_evidence_acquisition.core.scorers  # noqa: F401  (registers)
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )

    outputs = run_dir(run_id, attempt) / ("%s.outputs.jsonl" % run_id)
    return SCORERS.resolve(scorer)(outputs, load_lock(umbrella_lock_path()), data_root())


def wilson(successes: int, total: int, z: float = Z_90) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, center - half), min(1.0, center + half))


def _rate_row(rows: Sequence[Mapping[str, object]], field: str) -> dict[str, object]:
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


def _mean(rows: Sequence[Mapping[str, object]], field: str) -> float:
    return sum(float(row[field]) for row in rows) / len(rows) if rows else 0.0


def score_map(per_sample: Sequence[Mapping[str, object]]) -> dict[str, dict[str, float]]:
    """Official-scorer per-sample rows -> the paired analyser's metric map."""

    return {
        str(row["sample_id"]): {
            "tool_accuracy": float(bool(row["tool_correct"])),
            "exact_match": float(bool(row["exact_match"])),
            "param_f1": float(row["param_f1"]),
            "parsed": float(bool(row["parsed"])),
        }
        for row in per_sample
    }


def score_map_v2(per_sample: Sequence[Mapping[str, object]]) -> dict[str, dict[str, float]]:
    """``a2t-toolcall-v2`` rows carry different field names from the official
    scorer's -- ordered ``tool_accuracy`` rather than ``tool_correct``, and
    ``slot_f1`` rather than ``param_f1`` -- because the two answer different
    questions. Mapping them here keeps the paired analyser metric-name-agnostic."""

    return {
        str(row["sample_id"]): {
            "tool_accuracy": float(row["tool_accuracy"]),
            "tool_accuracy_multiset": float(row["tool_accuracy_multiset"]),
            "exact_match": float(row["exact_match"]),
            "slot_f1": float(row["slot_f1"]),
            "parsed": float(bool(row["parsed"])),
        }
        for row in per_sample
    }


V2_METRICS = ("tool_accuracy", "tool_accuracy_multiset", "exact_match", "slot_f1")


def tier_facts() -> tuple[dict[str, str], dict[str, str]]:
    """``(domain_by_sample, category_by_sample)`` from each tier's released
    manifest. Identity and stratum fields only -- no gold, no task text."""

    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        load_lock,
        umbrella_lock_path,
    )

    lock = load_lock(umbrella_lock_path())
    public = asset_dir(lock, "audio2tool", data_root_path()) / "public"
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    domain: dict[str, str] = {}
    category: dict[str, str] = {}
    for tier in TIERS:
        manifest = json.loads(
            (public / ("%s_data" % tier) / ("%s.json" % tier)).read_text(encoding="utf-8")
        )
        by_id = {int(row["id"]): row for row in manifest}
        for item in roster["items"]:
            if str(item["tier"]) != tier:
                continue
            entry = by_id[int(item["id"])]
            domain[str(item["sample_id"])] = str(entry["domain"])
            category[str(item["sample_id"])] = str(entry.get("category") or "")
    return domain, category


def per_tier_table(aggregate: Mapping[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for tier in TIERS:
        block = aggregate["per_tier"].get(tier)
        if block is None:
            continue
        total = int(block["samples"])
        accuracy = float(block["tool_accuracy"])
        successes = int(round(accuracy * total))
        low, high = wilson(successes, total)
        paper = PAPER[tier]["tool_accuracy"]
        pct = accuracy * 100.0
        rows.append(
            {
                "tier": tier,
                "samples": total,
                "tool_accuracy_pct": pct,
                "ci90_low_pct": low * 100.0,
                "ci90_high_pct": high * 100.0,
                "paper_tool_accuracy_pct": paper,
                "delta_pp": pct - paper,
                "within_replication_band_5pp": abs(pct - paper) <= REPLICATION_BAND_PP,
                "within_owner_band_3pp": pct >= paper - OWNER_BAND_PP,
                "paper_inside_ci90": low * 100.0 <= paper <= high * 100.0,
                "exact_match_pct": float(block["exact_match"]) * 100.0,
                "paper_exact_match_pct": PAPER[tier]["exact_match"],
                "param_f1_macro_pct": float(block["param_f1"]) * 100.0,
                "param_f1_micro_pct": float(block["param_f1_micro"]) * 100.0,
                "parse_rate_pct": float(block["parse_rate"]) * 100.0,
                "multi_tool_samples": int(block["multi_tool_samples"]),
                "rows_with_multiple_call_matches": int(
                    block["rows_with_multiple_call_matches"]
                ),
            }
        )
    return rows


def rank_order(rows: Sequence[Mapping[str, object]]) -> list[str]:
    return [
        str(row["tier"])
        for row in sorted(rows, key=lambda r: (-float(r["tool_accuracy_pct"]), str(r["tier"])))
    ]


PAPER_RANK_ORDER = [
    tier
    for tier in sorted(TIERS, key=lambda t: (-PAPER[t]["tool_accuracy"], t))
]


def replication_outcome(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """PASS / CONSISTENT-WITHIN-NOISE / FAIL under the REPLICATION
    preregistration's own definitions, which the Q8 decision rule cites."""

    by_tier = {str(row["tier"]): row for row in rows}
    acceptance = [by_tier[tier] for tier in ACCEPTANCE_TIERS if tier in by_tier]
    all_within = all(bool(row["within_replication_band_5pp"]) for row in acceptance)
    order = rank_order(rows)
    order_preserved = order == PAPER_RANK_ORDER
    all_in_ci = all(bool(row["paper_inside_ci90"]) for row in acceptance)
    if all_within and order_preserved:
        outcome = "PASS"
    elif all_in_ci:
        outcome = "CONSISTENT-WITHIN-NOISE"
    else:
        outcome = "FAIL"
    return {
        "outcome": outcome,
        "rule": (
            "PASS = per-tier official tool accuracy within 5 pp of the paper row on tiers "
            "1, 2, 5 and 6 with the tier rank order preserved; CONSISTENT-WITHIN-NOISE = "
            "the paper value inside the tier's Wilson CI90 (n = 50) on all four but at "
            "least one outside 5 pp; FAIL = neither. These are the official-protocol "
            "replication preregistration's own definitions, cited by name in the Q8 "
            "preregistration's decision rule"
        ),
        "acceptance_tiers": list(ACCEPTANCE_TIERS),
        "all_acceptance_tiers_within_5pp": all_within,
        "rank_order": order,
        "paper_rank_order": PAPER_RANK_ORDER,
        "rank_order_preserved": order_preserved,
        "all_acceptance_tiers_paper_inside_ci90": all_in_ci,
    }


def domain_slices(
    rows: Sequence[Mapping[str, object]], domain_by_sample: Mapping[str, str]
) -> dict[str, object]:
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        grouped.setdefault(domain_by_sample[str(row["sample_id"])], []).append(row)
    per_domain = {
        domain: {
            "tool_accuracy": _rate_row(bucket, "tool_correct"),
            "exact_match": _rate_row(bucket, "exact_match"),
            "param_f1_macro_pct": 100.0 * _mean(bucket, "param_f1"),
        }
        for domain, bucket in sorted(grouped.items())
    }
    natural = 100.0 * sum(1 for row in rows if row["tool_correct"]) / len(rows)
    equal = sum(block["tool_accuracy"]["pct"] for block in per_domain.values()) / len(
        per_domain
    )
    return {
        "per_domain": per_domain,
        "tool_accuracy_natural_mixture_pct": natural,
        "tool_accuracy_equal_domain_pct": equal,
        "counts": {name: block["tool_accuracy"]["samples"] for name, block in per_domain.items()},
    }


def paired_block(
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    *,
    strata_of: Callable[[str], str],
    sample_ids: Sequence[str] | None = None,
    metrics: Sequence[str] = ("tool_accuracy", "exact_match", "param_f1"),
) -> dict[str, object]:
    from speech_aware_evidence_acquisition.analysis.paired import paired_contrast

    contrasts = paired_contrast(
        left,
        right,
        metrics=list(metrics),
        sample_ids=list(sample_ids) if sample_ids is not None else None,
        strata_of=strata_of,
        seed=BOOTSTRAP_SEED,
        n_replicates=BOOTSTRAP_REPLICATES,
        ci_level=CI_LEVEL,
    )
    return {name: contrast.as_dict() for name, contrast in contrasts.items()}


def cell_block(
    *,
    run_id: str,
    attempt: str,
    cell_id: str,
    domain_by_sample: Mapping[str, str],
) -> dict[str, object]:
    official = rescore(run_id, attempt, "a2t-toolcall-official")
    v2 = rescore(run_id, attempt, "a2t-toolcall-v2")
    rows = official["per_sample"]
    aggregate = official["aggregate"]
    manifest = load_manifest(run_id, attempt)
    cost = manifest["cost"]
    calls = int(cost["calls_used"])
    table = per_tier_table(aggregate)
    return {
        "run_id": run_id,
        "attempt_id": attempt,
        "cell_id": cell_id,
        "study_commit": manifest["study_commit"],
        "status": manifest["status"],
        "manifest_sha256": sha256_file(
            run_dir(run_id, attempt) / ("%s.run-manifest.json" % run_id)
        ),
        "protocol_hash": manifest["protocol_hash"],
        "config_hash": manifest["config"]["config_hash"],
        "model_fragment": manifest["config"]["fragments"]["model"],
        "samples": int(aggregate["samples"]),
        "official": {
            "tool_accuracy": _rate_row(rows, "tool_correct"),
            "exact_match": _rate_row(rows, "exact_match"),
            "param_f1_macro_pct": 100.0 * float(aggregate["param_f1"]),
            "param_f1_micro_pct": 100.0 * float(aggregate["param_f1_micro"]),
            "parse_rate_pct": 100.0 * float(aggregate["parse_rate"]),
            "parse_failures": int(aggregate["parse_failures"]),
            "rows_with_multiple_call_matches": int(
                aggregate["rows_with_multiple_call_matches"]
            ),
            "per_tier": table,
            "summed_absolute_per_tier_gap_pp": sum(
                abs(float(row["delta_pp"])) for row in table
            ),
        },
        "v2": {
            "tool_accuracy_ordered_pct": 100.0 * float(v2["aggregate"]["tool_accuracy"]),
            "tool_accuracy_multiset_pct": 100.0
            * float(v2["aggregate"]["tool_accuracy_multiset"]),
            "exact_match_pct": 100.0 * float(v2["aggregate"]["exact_match"]),
            "slot_f1_pct": 100.0 * float(v2["aggregate"]["slot_f1"]),
            "parse_failures": int(v2["aggregate"]["parse_failures"]),
        },
        "replication_outcome_vs_paper": replication_outcome(table),
        "domain_slices": domain_slices(rows, domain_by_sample),
        "throughput": {
            "calls": calls,
            "audio_seconds_used": float(cost["audio_seconds_used"]),
            "prompt_tokens_total": int(cost["prompt_tokens_total"]),
            "completion_tokens_total": int(cost["completion_tokens_total"]),
            "latency_seconds_total": float(cost["latency_seconds_total"]),
            "mean_latency_seconds_per_call": float(cost["latency_seconds_total"]) / calls,
            "prompt_tokens_per_call": int(cost["prompt_tokens_total"]) / calls,
            "completion_tokens_per_call": int(cost["completion_tokens_total"]) / calls,
        },
        "_official_rows": rows,
        "_official_scores": score_map(rows),
        "_v2_scores": score_map_v2(v2["per_sample"]),
        "_scorer_versions": {
            "official": aggregate["scorer_version"],
            "official_commit": aggregate["official_commit"],
            "official_gold": aggregate["gold_version"],
            "v2": v2["aggregate"]["scorer_version"],
            "v2_gold": v2["aggregate"]["gold_version"],
            "parse": v2["aggregate"]["parse_version"],
        },
    }


def gap_closure(
    q8_table: Sequence[Mapping[str, object]], q4_table: Sequence[Mapping[str, object]]
) -> list[dict[str, object]]:
    """How much of each tier's Q4-to-paper gap the Q8 decoder closes."""

    q4_by_tier = {str(row["tier"]): row for row in q4_table}
    out: list[dict[str, object]] = []
    for row in q8_table:
        tier = str(row["tier"])
        q4 = q4_by_tier[tier]
        paper = float(row["paper_tool_accuracy_pct"])
        q4_pct = float(q4["tool_accuracy_pct"])
        q8_pct = float(row["tool_accuracy_pct"])
        gap = paper - q4_pct
        out.append(
            {
                "tier": tier,
                "q4_pct": q4_pct,
                "q8_pct": q8_pct,
                "paper_pct": paper,
                "q8_minus_q4_pp": q8_pct - q4_pct,
                "q4_gap_to_paper_pp": gap,
                "fraction_of_gap_closed": ((q8_pct - q4_pct) / gap) if gap > 0 else None,
                "gap_closure_defined": gap > 0,
            }
        )
    return out


def decide(
    *,
    pooled_acceptance: Mapping[str, object],
    q8_outcome: Mapping[str, object],
) -> dict[str, object]:
    bootstrap = pooled_acceptance["tool_accuracy"]["bootstrap"]
    ci_low = float(bootstrap["ci_low"])
    ci_high = float(bootstrap["ci_high"])
    paper_ok = str(q8_outcome["outcome"]) in {"PASS", "CONSISTENT-WITHIN-NOISE"}
    if ci_low > 0.0 and paper_ok:
        outcome = "QUANTIZATION-DOMINANT"
    elif ci_low <= 0.0 <= ci_high:
        outcome = "QUANTIZATION-EXCLUDED"
    else:
        outcome = "PARTIAL"
    return {
        "outcome": outcome,
        "rule": (
            "QUANTIZATION-DOMINANT: the pooled Q8-minus-Q4 tool-accuracy CI90 lower bound "
            "over the four acceptance tiers (1, 2, 5, 6) is above 0 AND C-q8 is PASS or "
            "CONSISTENT-WITHIN-NOISE against the paper on those tiers. "
            "QUANTIZATION-EXCLUDED: the pooled CI90 includes 0. PARTIAL: otherwise "
            "(preregistration section 6)"
        ),
        "pooled_acceptance_tiers": list(ACCEPTANCE_TIERS),
        "pooled_delta": float(pooled_acceptance["tool_accuracy"]["delta"]),
        "pooled_ci90_low": ci_low,
        "pooled_ci90_high": ci_high,
        "pooled_ci90_excludes_zero_above": ci_low > 0.0,
        "pooled_ci90_includes_zero": ci_low <= 0.0 <= ci_high,
        "q8_vs_paper_outcome": q8_outcome["outcome"],
        "q8_vs_paper_is_pass_or_consistent": paper_ok,
        "consequence": (
            "No outcome changes the operating core by itself, tunes any knob, or opens any "
            "test data. Whether Q8_0 with expert offload becomes the Audio2Tool operating "
            "core is a separate owner decision informed by the throughput recorded here."
        ),
    }


def build(*, q8_attempt: str, q8_run_id: str = Q8_RUN_ID) -> dict[str, object]:
    domain_by_sample, _ = tier_facts()
    q8 = cell_block(
        run_id=q8_run_id,
        attempt=q8_attempt,
        cell_id=Q8_CELL,
        domain_by_sample=domain_by_sample,
    )
    q4 = cell_block(
        run_id=Q4_RUN_ID,
        attempt=Q4_ATTEMPT,
        cell_id=Q4_CELL,
        domain_by_sample=domain_by_sample,
    )
    tier_of = {
        str(row["sample_id"]): str(row["tier"]) for row in q8["_official_rows"]
    }
    shared = sorted(set(q8["_official_scores"]) & set(q4["_official_scores"]))
    if len(shared) != 400:
        raise SystemExit(
            "the two cells share %d sample ids, not the frozen 400" % len(shared)
        )
    acceptance_ids = [sid for sid in shared if tier_of[sid] in ACCEPTANCE_TIERS]

    paired_official = paired_block(
        q4["_official_scores"],
        q8["_official_scores"],
        strata_of=lambda sid: tier_of[sid],
        sample_ids=shared,
    )
    paired_official_acceptance = paired_block(
        q4["_official_scores"],
        q8["_official_scores"],
        strata_of=lambda sid: tier_of[sid],
        sample_ids=acceptance_ids,
    )
    paired_official_domain = paired_block(
        q4["_official_scores"],
        q8["_official_scores"],
        strata_of=lambda sid: domain_by_sample[sid],
        sample_ids=shared,
    )
    paired_v2 = paired_block(
        q4["_v2_scores"],
        q8["_v2_scores"],
        strata_of=lambda sid: tier_of[sid],
        sample_ids=shared,
        metrics=V2_METRICS,
    )
    paired_v2_acceptance = paired_block(
        q4["_v2_scores"],
        q8["_v2_scores"],
        strata_of=lambda sid: tier_of[sid],
        sample_ids=acceptance_ids,
        metrics=V2_METRICS,
    )
    paired_v2_domain = paired_block(
        q4["_v2_scores"],
        q8["_v2_scores"],
        strata_of=lambda sid: domain_by_sample[sid],
        sample_ids=shared,
        metrics=V2_METRICS,
    )

    decision = decide(
        pooled_acceptance=paired_official_acceptance,
        q8_outcome=q8["replication_outcome_vs_paper"],
    )

    placement = json.loads(PLACEMENT_RECEIPT.read_text(encoding="utf-8"))
    prompt_fit = json.loads(PROMPT_FIT_RECEIPT.read_text(encoding="utf-8"))
    q8_manifest = load_manifest(q8_run_id, q8_attempt)

    document = {
        "schema": "saea-a2t-q8-quantization-probe-result-v1",
        "study": "speech-aware-evidence-acquisition",
        "preregistration": (
            "docs/readiness/2026-09-04-a2t-q8-quantization-probe-v1-preregistration.md"
        ),
        "boundary": (
            "zero model, GPU or network contact. Every number is computed from outputs "
            "JSONL files two separately registered runs already sealed; gold enters only "
            "through the registered scorers"
        ),
        "population": {
            "carrier": "audio2tool",
            "split_name": "A2T-CALIBRATION-400",
            "split_role": "discovery",
            "count": len(shared),
            "flight_split_identity_hash": (
                "11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b"
            ),
            "roster_receipt": str(ROSTER.relative_to(REPO)),
            "roster_receipt_sha256": sha256_file(ROSTER),
        },
        "cells": {
            "C-q8-official-raw": {k: v for k, v in q8.items() if not k.startswith("_")},
            "R-official-raw": {k: v for k, v in q4.items() if not k.startswith("_")},
        },
        "paired_official_by_tier": paired_official,
        "paired_official_acceptance_tiers": paired_official_acceptance,
        "paired_official_by_domain": paired_official_domain,
        "paired_v2_by_tier": paired_v2,
        "paired_v2_acceptance_tiers": paired_v2_acceptance,
        "paired_v2_by_domain": paired_v2_domain,
        "paired_basis": {
            "delta": "right minus left, i.e. C-q8 minus R-official-raw",
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "ci_level": CI_LEVEL,
            "stratification": "tier for the tier blocks, domain for the domain blocks",
            "same_rows": "the identical frozen 400, one contact each, same gold, same scorer",
        },
        "gap_closure_by_tier": gap_closure(
            q8["official"]["per_tier"], q4["official"]["per_tier"]
        ),
        "decision": decision,
        "scorer_versions": {
            "C-q8-official-raw": q8["_scorer_versions"],
            "R-official-raw": q4["_scorer_versions"],
        },
        "placement": {
            "receipt": str(PLACEMENT_RECEIPT.relative_to(REPO)),
            "receipt_sha256": sha256_file(PLACEMENT_RECEIPT),
            "chosen": placement["chosen"],
            "ladder": [
                {
                    "label": trial["label"],
                    "free_mib": trial["free_mib"],
                    "used_mib": trial["device_memory_resident_mib"]["used_mib"],
                    "server_rss_mib": trial["server_rss_mib"],
                    "meets_min_free": trial["meets_min_free"],
                }
                for trial in placement["trials"]
            ],
            "min_free_mib": placement["min_free_mib"],
            "gpu_power_limit_watts": placement["gpu_power_limit_watts"],
        },
        "prompt_fit": {
            "receipt": str(PROMPT_FIT_RECEIPT.relative_to(REPO)),
            "receipt_sha256": sha256_file(PROMPT_FIT_RECEIPT),
            "system_text_sha256": prompt_fit["cells"][0]["system_text_sha256"],
            "text_prompt_tokens": prompt_fit["cells"][0]["text_prompt_tokens"],
            "rendered_prompt_chars": prompt_fit["cells"][0]["rendered_prompt_chars"],
            "rendered_prompt_sha256_with_reference_marker": prompt_fit["cells"][0].get(
                "rendered_prompt_sha256_with_reference_marker"
            ),
            "sealed_q4_rendered_prompt_sha256": (
                "430c075bbb923d487ca959dc86ca7d7ade6372660001abab0223bdabcb53f231"
            ),
            "prompt_is_byte_identical_apart_from_the_media_marker_nonce": (
                prompt_fit["cells"][0].get("rendered_prompt_sha256_with_reference_marker")
                == "430c075bbb923d487ca959dc86ca7d7ade6372660001abab0223bdabcb53f231"
            ),
            "chat_template_sha256": prompt_fit["server"]["chat_template_sha256"],
            "worst_required_window_tokens": prompt_fit["cells"][0][
                "worst_required_window_tokens"
            ],
        },
        "runtime": {
            "q8_runtime_receipt": "docs/receipts/runtime-q8-featcache-04ccc72a.json",
            "q8_runtime_receipt_sha256": sha256_file(
                REPO / "docs/receipts/runtime-q8-featcache-04ccc72a.json"
            ),
            "q4_runtime_receipt": "docs/receipts/runtime-q4km-featcache-04ccc72a.json",
            "q4_runtime_receipt_sha256": sha256_file(
                REPO / "docs/receipts/runtime-q4km-featcache-04ccc72a.json"
            ),
            "build_commit": "04ccc72a2207347ca76161b93fd9d846dd0a8675",
            "q8_plan": q8_manifest["plan"],
        },
        "throughput_comparison": {
            "q8": q8["throughput"],
            "q4": q4["throughput"],
            "q8_over_q4_mean_latency": (
                q8["throughput"]["mean_latency_seconds_per_call"]
                / q4["throughput"]["mean_latency_seconds_per_call"]
            ),
        },
    }
    return document


def render(document: Mapping[str, object]) -> None:
    q8 = document["cells"]["C-q8-official-raw"]
    q4 = document["cells"]["R-official-raw"]
    print("=== per tier, official scorer (tool accuracy %) ===")
    print("%-24s %8s %8s %8s %8s %8s" % ("tier", "Q4", "Q8", "delta", "paper", "Q8-paper"))
    q4_by_tier = {row["tier"]: row for row in q4["official"]["per_tier"]}
    for row in q8["official"]["per_tier"]:
        other = q4_by_tier[row["tier"]]
        print(
            "%-24s %8.2f %8.2f %8.2f %8.1f %8.2f"
            % (
                row["tier"],
                other["tool_accuracy_pct"],
                row["tool_accuracy_pct"],
                row["tool_accuracy_pct"] - other["tool_accuracy_pct"],
                row["paper_tool_accuracy_pct"],
                row["delta_pp"],
            )
        )
    print(
        "%-24s %8.2f %8.2f %8.2f"
        % (
            "OVERALL",
            q4["official"]["tool_accuracy"]["pct"],
            q8["official"]["tool_accuracy"]["pct"],
            q8["official"]["tool_accuracy"]["pct"] - q4["official"]["tool_accuracy"]["pct"],
        )
    )
    print()
    print("=== paired, official scorer, tier-stratified ===")
    for name, block in sorted(document["paired_official_by_tier"].items()):
        boot = block["bootstrap"]
        print(
            "%-14s delta %+0.4f  saves %3d harms %3d ties %3d  sign p %.4f  CI90 [%+.4f, %+.4f]"
            % (
                name,
                block["delta"],
                block["saves"],
                block["harms"],
                block["ties"],
                block["sign_test_p"],
                boot["ci_low"],
                boot["ci_high"],
            )
        )
    print()
    print("=== paired on the four acceptance tiers (the decision block) ===")
    for name, block in sorted(document["paired_official_acceptance_tiers"].items()):
        boot = block["bootstrap"]
        print(
            "%-14s delta %+0.4f  saves %3d harms %3d ties %3d  sign p %.4f  CI90 [%+.4f, %+.4f]"
            % (
                name,
                block["delta"],
                block["saves"],
                block["harms"],
                block["ties"],
                block["sign_test_p"],
                boot["ci_low"],
                boot["ci_high"],
            )
        )
    print()
    print("=== per domain (tool accuracy %) ===")
    for cell_id in ("R-official-raw", "C-q8-official-raw"):
        block = document["cells"][cell_id]["domain_slices"]
        print(cell_id)
        for domain, cell in block["per_domain"].items():
            print(
                "   %-12s n=%3d  %6.2f  CI90 [%5.2f, %5.2f]"
                % (
                    domain,
                    cell["tool_accuracy"]["samples"],
                    cell["tool_accuracy"]["pct"],
                    cell["tool_accuracy"]["ci90_low_pct"],
                    cell["tool_accuracy"]["ci90_high_pct"],
                )
            )
        print(
            "   natural %6.2f   equal-domain %6.2f"
            % (
                block["tool_accuracy_natural_mixture_pct"],
                block["tool_accuracy_equal_domain_pct"],
            )
        )
    print()
    print("=== paired by domain, official tool accuracy ===")
    for name, row in sorted(
        document["paired_official_by_domain"]["tool_accuracy"]["per_stratum"].items()
    ):
        print(
            "   %-12s n=%3d  Q4 %6.4f  Q8 %6.4f  delta %+0.4f  saves %2d harms %2d ties %3d"
            % (
                name,
                row["n"],
                row["left_mean"],
                row["right_mean"],
                row["delta"],
                row["saves"],
                row["harms"],
                row["ties"],
            )
        )
    print()
    print("=== decision ===")
    print(json.dumps(document["decision"], indent=2, sort_keys=True))
    print()
    print("=== throughput ===")
    print(json.dumps(document["throughput_comparison"], indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--q8-attempt", default=None)
    parser.add_argument(
        "--q8-run-id",
        default=Q8_RUN_ID,
        help=(
            "the probe run whose sealed outputs are the RIGHT side of every contrast; "
            "overridable so a recovery re-registration under a second run id can be read "
            "with the same code, and so this script can be dry-run against an already "
            "sealed run before the probe exists"
        ),
    )
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    q8_attempt = args.q8_attempt or latest_attempt(args.q8_run_id)
    document = build(q8_attempt=q8_attempt, q8_run_id=args.q8_run_id)
    render(document)
    if args.write:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "result-summary.json"
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print("\nwrote %s (sha256 %s)" % (path, sha256_file(path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
