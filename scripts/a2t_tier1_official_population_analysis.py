#!/usr/bin/env python3
"""Verdict numbers for the Audio2Tool tier-1 official-population flight.

Reads only bytes the two registered runs already sealed
(``SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1`` and
``SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-V1``) plus the sealed
predecessor manifest, and writes ``result-summary.json``. Zero model, GPU or
network contact; gold enters only through the registered scorers, exactly as
it does when a flight finalizes.

What it produces:

* the T1 cell's official-scorer tool accuracy / exact match / parameter F1 at
  n = 500 with a Wilson CI90, against the published 92.4 / 92.4, and the
  preregistered three-outcome decision on the owner's 3-point alignment band;
* the same figures sliced by domain (natural mixture and equal-domain), and
  the frozen 400's own 50 tier-1 rows beside them so the roster effect is a
  difference rather than a replacement;
* the whitespace cell's per-tier table with the paper row and a Wilson CI90,
  its own three-outcome decision, and the paired contrast against the sealed
  ``R-official-raw`` manifest over the same 400 rows;
* the official scorer beside the extended ``a2t-toolcall-v2`` on both cells'
  own outputs, per tier, with every gap wider than 3 points attributed to a
  named rule difference;
* parse and multi-call statistics for both cells.

Usage (WSL2, model-free)::

    python scripts/a2t_tier1_official_population_analysis.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]

T1_RUN_ID = "SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1"
T1_CELL = "T1-official-pop-500"
W_RUN_ID = "SAEA-A2T-TIER1-OFFICIAL-POPULATION-WHITESPACE-V1"
W_CELL = "W-official-raw-yaml"
PRED_RUN_ID = "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1"
PRED_ATTEMPT = "attempt-20260904T135250Z-rofficialraw"
PRED_CELL = "R-official-raw"

ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-tier1-official-population-roster"
    / "flight-roster-receipt.json"
)
OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-tier1-official-population-v1"
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
    "tier1_direct": {"tool_accuracy": 92.4, "exact_match": 92.4},
    "tier2_parametric": {"tool_accuracy": 84.6, "exact_match": 15.6},
    "tier3_multi_intent": {"tool_accuracy": 74.7, "exact_match": 28.6},
    "tier4_implicit": {"tool_accuracy": 33.4, "exact_match": 11.3},
    "tier5_needle": {"tool_accuracy": 90.6, "exact_match": 36.0},
    "tier6_correction": {"tool_accuracy": 81.5, "exact_match": 24.8},
    "tier7_multiturn": {"tool_accuracy": 54.6, "exact_match": 16.3},
    "tier8_intent_blending": {"tool_accuracy": 41.7, "exact_match": 12.4},
}
DECISION_TIERS = ("tier1_direct", "tier2_parametric", "tier5_needle", "tier6_correction")
ALIGNMENT_BAND_PP = 3.0
CI_LEVEL = 0.90
Z_90 = 1.6448536269514722
BOOTSTRAP_SEED = 20260903
BOOTSTRAP_REPLICATES = 10_000

SCORER_RULE_DIFFERENCES = {
    "first_call_only_vs_ordered_sequence": (
        "the official HF path never populates all_tool_calls, so the official scorer reads "
        "only the FIRST parsed call against the PRIMARY gold tool, while a2t-toolcall-v2 "
        "compares the whole ordered predicted sequence with the whole expected sequence"
    ),
    "primary_gold_tool_vs_full_expected_sequence": (
        "official gold is the release's QuerySample (primary tool_name + verbatim "
        "extracted_params); v2 gold is a2t-gold-v1, which builds the full expected call "
        "sequence and may take primary arguments from the expected_tool_call call string"
    ),
    "default_argument_credit": (
        "v2 rule V2b drops a predicted argument key absent from every same-tool gold call "
        "when its value equals that tool's registry default; the official scorer counts "
        "every extra key as a parameter error and therefore as an exact-match failure"
    ),
    "numeric_and_boolean_coercion": (
        "v2 rule V2d compares a numeric-looking string to its numeric value and "
        "'true'/'false' to the matching boolean; the official normalize_parameters reaches "
        "a similar place by a different route, so this rule rarely separates the two alone"
    ),
    "parameter_f1_definition": (
        "the official parameter F1 is a macro average of per-sample key P/R/F1 while v2's "
        "slot F1 is micro over (tool, key, value) triples, so the two answer different "
        "questions and are reported side by side rather than differenced"
    ),
}


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


def load_scores(run_id: str, attempt: str) -> Mapping[str, object]:
    return json.loads(
        (run_dir(run_id, attempt) / f"{run_id}.scores.json").read_text(encoding="utf-8")
    )


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
    return {
        str(row["sample_id"]): {
            "tool_accuracy": float(bool(row["tool_correct"])),
            "exact_match": float(bool(row["exact_match"])),
            "param_f1": float(row["param_f1"]),
            "parsed": float(bool(row["parsed"])),
        }
        for row in per_sample
    }


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
                "aligned": (pct >= paper - ALIGNMENT_BAND_PP),
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


def three_outcome(pct: float, low_pct: float, high_pct: float, paper: float) -> str:
    if pct >= paper - ALIGNMENT_BAND_PP:
        return "ALIGNED"
    if low_pct <= paper <= high_pct:
        return "CONSISTENT-WITHIN-NOISE"
    return "FAIL"


def alignment_table(run_id: str, attempt: str) -> dict[str, object]:
    official = rescore(run_id, attempt, "a2t-toolcall-official")
    v2 = rescore(run_id, attempt, "a2t-toolcall-v2")
    rows: list[dict[str, object]] = []
    for tier in TIERS:
        o = official["aggregate"]["per_tier"].get(tier)
        if o is None:
            continue
        v = v2["aggregate"]["per_tier"][tier]
        tool_delta = 100.0 * (float(v["tool_accuracy"]) - float(o["tool_accuracy"]))
        em_delta = 100.0 * (float(v["exact_match"]) - float(o["exact_match"]))
        named: list[str] = []
        if abs(tool_delta) > ALIGNMENT_BAND_PP:
            named.append("first_call_only_vs_ordered_sequence")
            if int(o["multi_tool_samples"]) > 0:
                named.append("primary_gold_tool_vs_full_expected_sequence")
        if abs(em_delta) > ALIGNMENT_BAND_PP:
            for name in (
                "default_argument_credit",
                "primary_gold_tool_vs_full_expected_sequence",
            ):
                if name not in named:
                    named.append(name)
        rows.append(
            {
                "tier": tier,
                "samples": int(o["samples"]),
                "official_tool_accuracy_pct": 100.0 * float(o["tool_accuracy"]),
                "v2_tool_accuracy_ordered_pct": 100.0 * float(v["tool_accuracy"]),
                "v2_tool_accuracy_multiset_pct": 100.0 * float(v["tool_accuracy_multiset"]),
                "tool_accuracy_delta_pp": tool_delta,
                "tool_accuracy_within_band": abs(tool_delta) <= ALIGNMENT_BAND_PP,
                "official_exact_match_pct": 100.0 * float(o["exact_match"]),
                "v2_exact_match_pct": 100.0 * float(v["exact_match"]),
                "exact_match_delta_pp": em_delta,
                "exact_match_within_band": abs(em_delta) <= ALIGNMENT_BAND_PP,
                "official_param_f1_macro_pct": 100.0 * float(o["param_f1"]),
                "official_param_f1_micro_pct": 100.0 * float(o["param_f1_micro"]),
                "v2_slot_f1_pct": 100.0 * float(v["slot_f1"]),
                "rules_that_can_explain_a_gap": named,
            }
        )
    oa, va = official["aggregate"], v2["aggregate"]
    return {
        "per_tier": rows,
        "overall": {
            "samples": int(oa["samples"]),
            "official_tool_accuracy_pct": 100.0 * float(oa["tool_accuracy"]),
            "v2_tool_accuracy_ordered_pct": 100.0 * float(va["tool_accuracy"]),
            "v2_tool_accuracy_multiset_pct": 100.0 * float(va["tool_accuracy_multiset"]),
            "tool_accuracy_delta_pp": 100.0
            * (float(va["tool_accuracy"]) - float(oa["tool_accuracy"])),
            "official_exact_match_pct": 100.0 * float(oa["exact_match"]),
            "v2_exact_match_pct": 100.0 * float(va["exact_match"]),
            "exact_match_delta_pp": 100.0
            * (float(va["exact_match"]) - float(oa["exact_match"])),
            "official_param_f1_macro_pct": 100.0 * float(oa["param_f1"]),
            "official_param_f1_micro_pct": 100.0 * float(oa["param_f1_micro"]),
            "v2_slot_f1_pct": 100.0 * float(va["slot_f1"]),
            "official_parse_rate_pct": 100.0 * float(oa["parse_rate"]),
            "v2_parse_failures": int(va["parse_failures"]),
            "official_rows_with_multiple_call_matches": int(
                oa["rows_with_multiple_call_matches"]
            ),
            "v2_extra_keys_stripped": int(va["extra_keys_stripped"]),
        },
        "scorer_versions": {
            "official": oa["scorer_version"],
            "official_commit": oa["official_commit"],
            "official_gold": oa["gold_version"],
            "v2": va["scorer_version"],
            "v2_gold": va["gold_version"],
            "parse": va["parse_version"],
        },
    }


def domain_slices(per_sample: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """T1 rows sliced by the release's own domain field, natural and equal-weighted."""

    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        load_lock,
        umbrella_lock_path,
    )

    lock = load_lock(umbrella_lock_path())
    public = asset_dir(lock, "audio2tool", data_root_path()) / "public"
    manifest = json.loads(
        (public / "tier1_direct_data" / "tier1_direct.json").read_text(encoding="utf-8")
    )
    domain_by_id = {int(row["id"]): str(row["domain"]) for row in manifest}
    domain_by_sample = {
        str(item["sample_id"]): domain_by_id[int(item["id"])] for item in roster["items"]
    }
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for row in per_sample:
        grouped.setdefault(domain_by_sample[str(row["sample_id"])], []).append(row)
    per_domain = {
        domain: {
            "tool_accuracy": _rate_row(rows, "tool_correct"),
            "exact_match": _rate_row(rows, "exact_match"),
            "param_f1_macro_pct": 100.0 * _mean(rows, "param_f1"),
        }
        for domain, rows in sorted(grouped.items())
    }
    natural = 100.0 * _mean(
        [{"v": float(bool(row["tool_correct"]))} for row in per_sample], "v"
    )
    equal = sum(
        block["tool_accuracy"]["pct"] for block in per_domain.values()
    ) / len(per_domain)
    return {
        "per_domain": per_domain,
        "tool_accuracy_natural_mixture_pct": natural,
        "tool_accuracy_equal_domain_pct": equal,
        "counts": dict(sorted(Counter(domain_by_sample.values()).items())),
    }


def tool_confusion(per_sample: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Where the tier-1 misses go, by domain -- a DIAGNOSTIC, not a metric.

    The domain slice makes the tier-1 gap look like a smart_home phenomenon.
    This asks what the wrong answers actually are, and the answer is that they
    are overwhelmingly OTHER REAL TOOLS of the 152-row registry whose names
    are near-synonyms of the gold one, sometimes inside smart_home and
    sometimes the same idea's twin in smart_car. Nothing here enters a
    decision; it names a component so the next question is a bounded one.
    """

    import csv

    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        load_lock,
        umbrella_lock_path,
    )

    lock = load_lock(umbrella_lock_path())
    carrier = asset_dir(lock, "audio2tool", data_root_path())
    with (carrier / "tools_registry.csv").open(newline="", encoding="utf-8") as handle:
        registry = list(csv.DictReader(handle))
    by_name = {row["tool_name"]: row for row in registry}
    tools_per_domain = dict(sorted(Counter(row["domain"] for row in registry).items()))

    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    public = carrier / "public"
    manifest = json.loads(
        (public / "tier1_direct_data" / "tier1_direct.json").read_text(encoding="utf-8")
    )
    domain_of_id = {int(row["id"]): str(row["domain"]) for row in manifest}
    category_of_id = {int(row["id"]): str(row["category"]) for row in manifest}
    domain_of = {
        str(item["sample_id"]): domain_of_id[int(item["id"])] for item in roster["items"]
    }
    category_of = {
        str(item["sample_id"]): category_of_id[int(item["id"])] for item in roster["items"]
    }

    per_domain: dict[str, Counter] = {}
    misses: Counter = Counter()
    category_hits: dict[str, list[int]] = {}
    for row in per_sample:
        sample_id = str(row["sample_id"])
        domain = domain_of[sample_id]
        counts = per_domain.setdefault(domain, Counter())
        counts["samples"] += 1
        bucket = category_hits.setdefault(f"{domain}/{category_of[sample_id]}", [0, 0])
        bucket[1] += 1
        if row["tool_correct"]:
            counts["correct"] += 1
            bucket[0] += 1
            continue
        counts["misses"] += 1
        predicted = str(row["predicted_tool"])
        entry = by_name.get(predicted)
        if entry is None:
            counts["miss_predicted_name_absent_from_registry"] += 1
        else:
            counts["miss_predicted_name_is_a_real_registry_tool"] += 1
            if entry["domain"] == domain:
                counts["miss_predicted_tool_same_domain"] += 1
            else:
                counts["miss_predicted_tool_other_domain"] += 1
        if domain == "smart_home":
            misses[(str(row["gold_tool"]), predicted)] += 1

    top = [
        {
            "gold_tool": gold,
            "predicted_tool": predicted,
            "rows": count,
            "gold_domain_category": (
                [by_name[gold]["domain"], by_name[gold]["category"]]
                if gold in by_name
                else None
            ),
            "predicted_domain_category": (
                [by_name[predicted]["domain"], by_name[predicted]["category"]]
                if predicted in by_name
                else None
            ),
        }
        for (gold, predicted), count in misses.most_common(15)
    ]
    return {
        "note": (
            "diagnostic only; no number here enters a decision. It exists because the "
            "domain slice turns the tier-1 gap into a smart_home question and this says "
            "what the smart_home wrong answers are"
        ),
        "registry_tools_per_domain": tools_per_domain,
        "per_domain": {
            domain: dict(sorted(counts.items())) for domain, counts in sorted(per_domain.items())
        },
        "smart_home_top_confusions": top,
        "per_domain_category_accuracy": {
            name: {
                "correct": hits[0],
                "samples": hits[1],
                "pct": 100.0 * hits[0] / hits[1] if hits[1] else 0.0,
            }
            for name, hits in sorted(category_hits.items())
        },
    }


def build(*, t1_attempt: str, w_attempt: str) -> dict[str, object]:
    from speech_aware_evidence_acquisition.analysis.paired import (
        paired_contrast,
        per_stratum_table,
    )

    # ---- T1 cell ---------------------------------------------------------
    t1_official = load_scores(T1_RUN_ID, t1_attempt)["a2t-toolcall-official"]
    t1_rows = t1_official["per_sample"]
    t1_agg = t1_official["aggregate"]
    tool = _rate_row(t1_rows, "tool_correct")
    exact = _rate_row(t1_rows, "exact_match")
    t1_outcome = three_outcome(
        tool["pct"], tool["ci90_low_pct"], tool["ci90_high_pct"], PAPER["tier1_direct"]["tool_accuracy"]
    )

    # The frozen 400's own 50 tier-1 rows, re-scored under the same scorer.
    pred_official = rescore(PRED_RUN_ID, PRED_ATTEMPT, "a2t-toolcall-official")
    pred_tier1_rows = [
        row for row in pred_official["per_sample"] if row["tier"] == "tier1_direct"
    ]

    t1_block = {
        "run_id": T1_RUN_ID,
        "attempt_id": t1_attempt,
        "cell_id": T1_CELL,
        "manifest_sha256": sha256_file(
            run_dir(T1_RUN_ID, t1_attempt) / f"{T1_RUN_ID}.run-manifest.json"
        ),
        "study_commit": load_manifest(T1_RUN_ID, t1_attempt)["study_commit"],
        "samples": int(t1_agg["samples"]),
        "official": {
            "tool_accuracy": tool,
            "exact_match": exact,
            "param_f1_macro_pct": 100.0 * float(t1_agg["param_f1"]),
            "param_f1_micro_pct": 100.0 * float(t1_agg["param_f1_micro"]),
            "parse_rate_pct": 100.0 * float(t1_agg["parse_rate"]),
            "parse_failures": int(t1_agg["parse_failures"]),
            "rows_with_multiple_call_matches": int(
                t1_agg["rows_with_multiple_call_matches"]
            ),
        },
        "paper": PAPER["tier1_direct"],
        "delta_pp": {
            "tool_accuracy": tool["pct"] - PAPER["tier1_direct"]["tool_accuracy"],
            "exact_match": exact["pct"] - PAPER["tier1_direct"]["exact_match"],
        },
        "decision": {
            "outcome": t1_outcome,
            "rule": (
                "ALIGNED = official tier-1 tool accuracy >= 89.4 (within 3 pp of the "
                "paper's 92.4, or better); CONSISTENT-WITHIN-NOISE = not ALIGNED but 92.4 "
                "inside the Wilson CI90 at n = 500; FAIL = neither"
            ),
            "alignment_band_pp": ALIGNMENT_BAND_PP,
            "aligned_threshold_pct": PAPER["tier1_direct"]["tool_accuracy"] - ALIGNMENT_BAND_PP,
            "paper_inside_ci90": (
                tool["ci90_low_pct"]
                <= PAPER["tier1_direct"]["tool_accuracy"]
                <= tool["ci90_high_pct"]
            ),
            "extension_contingency_fires": t1_outcome == "ALIGNED",
        },
        "domain_slices": domain_slices(t1_rows),
        "tool_confusion_diagnostic": tool_confusion(t1_rows),
        "frozen_400_tier1_comparison": {
            "cell_id": PRED_CELL,
            "samples": len(pred_tier1_rows),
            "tool_accuracy": _rate_row(pred_tier1_rows, "tool_correct"),
            "exact_match": _rate_row(pred_tier1_rows, "exact_match"),
            "roster_effect_pp": tool["pct"]
            - (100.0 * sum(1 for r in pred_tier1_rows if r["tool_correct"]) / len(pred_tier1_rows)),
            "note": (
                "not a paired contrast: the two rosters are different populations (500 "
                "first-speaker rows over distinct queries against 50 mixed-speaker rows "
                "over 50 queries, 12 of which overlap). Reported as two independent "
                "estimates of the same tier under the same protocol"
            ),
        },
        "alignment_official_vs_v2": alignment_table(T1_RUN_ID, t1_attempt),
    }

    # ---- W cell ----------------------------------------------------------
    w_official = load_scores(W_RUN_ID, w_attempt)["a2t-toolcall-official"]
    w_rows = per_tier_table(w_official["aggregate"])
    w_decision_rows = [row for row in w_rows if row["tier"] in DECISION_TIERS]
    w_aligned = all(bool(row["aligned"]) for row in w_decision_rows)
    w_inside = all(bool(row["paper_inside_ci90"]) for row in w_decision_rows)
    w_outcome = "ALIGNED" if w_aligned else ("CONSISTENT-WITHIN-NOISE" if w_inside else "FAIL")

    left = score_map(pred_official["per_sample"])
    right = score_map(w_official["per_sample"])
    shared = sorted(set(left) & set(right))
    contrasts = paired_contrast(
        left,
        right,
        metrics=("tool_accuracy", "exact_match", "param_f1", "parsed"),
        sample_ids=shared,
        strata_of=lambda sid: sid.rsplit(":", 1)[0],
        seed=BOOTSTRAP_SEED,
        n_replicates=BOOTSTRAP_REPLICATES,
        ci_level=CI_LEVEL,
    )
    paired_out = {
        metric: {
            "left_cell": PRED_CELL,
            "right_cell": W_CELL,
            "left_mean": contrast.left_mean,
            "right_mean": contrast.right_mean,
            "delta": contrast.delta,
            "saves": contrast.saves,
            "harms": contrast.harms,
            "ties": contrast.ties,
            "sign_test_p": contrast.sign_test_p,
            "ci_low": contrast.bootstrap.ci_low if contrast.bootstrap else None,
            "ci_high": contrast.bootstrap.ci_high if contrast.bootstrap else None,
            "per_stratum": per_stratum_table(contrast),
        }
        for metric, contrast in contrasts.items()
    }
    w_agg = w_official["aggregate"]
    w_block = {
        "run_id": W_RUN_ID,
        "attempt_id": w_attempt,
        "cell_id": W_CELL,
        "manifest_sha256": sha256_file(
            run_dir(W_RUN_ID, w_attempt) / f"{W_RUN_ID}.run-manifest.json"
        ),
        "study_commit": load_manifest(W_RUN_ID, w_attempt)["study_commit"],
        "samples": int(w_agg["samples"]),
        "per_tier": w_rows,
        "overall": {
            "tool_accuracy_pct": 100.0 * float(w_agg["tool_accuracy"]),
            "exact_match_pct": 100.0 * float(w_agg["exact_match"]),
            "param_f1_macro_pct": 100.0 * float(w_agg["param_f1"]),
            "param_f1_micro_pct": 100.0 * float(w_agg["param_f1_micro"]),
            "parse_rate_pct": 100.0 * float(w_agg["parse_rate"]),
            "rows_with_multiple_call_matches": int(w_agg["rows_with_multiple_call_matches"]),
        },
        "decision": {
            "outcome": w_outcome,
            "rule": (
                "ALIGNED = per-tier official tool accuracy within 3 pp of the paper row or "
                "better on tiers 1, 2, 5 and 6; CONSISTENT-WITHIN-NOISE = not ALIGNED but "
                "the paper value inside the tier's Wilson CI90 (n = 50) on all four; FAIL "
                "= neither"
            ),
            "decision_tiers": list(DECISION_TIERS),
            "all_decision_tiers_aligned": w_aligned,
            "all_decision_tiers_contain_the_paper_value_in_ci90": w_inside,
        },
        "paired_against_the_sealed_in_code_default_cell": {
            "left": {
                "cell_id": PRED_CELL,
                "run_id": PRED_RUN_ID,
                "attempt_id": PRED_ATTEMPT,
                "system_prompt_variant": "in-code-default",
                "system_prompt_sha256": (
                    "1c52cd2ebca6e4737b706ccc231b01f008d35276a2153000d74ec9500018258a"
                ),
            },
            "right": {
                "cell_id": W_CELL,
                "run_id": W_RUN_ID,
                "attempt_id": w_attempt,
                "system_prompt_variant": "example-config-yaml",
                "system_prompt_sha256": (
                    "aa2e344ee52c59019b938926f37498e0dc9c80bd01f6521eba5c3d81309a491d"
                ),
            },
            "shared_samples": len(shared),
            "bootstrap": {
                "replicates": BOOTSTRAP_REPLICATES,
                "seed": BOOTSTRAP_SEED,
                "stratification": "tier",
                "ci_level": CI_LEVEL,
            },
            "contrasts": paired_out,
        },
        "alignment_official_vs_v2": alignment_table(W_RUN_ID, w_attempt),
    }

    return {
        "schema": "saea-a2t-tier1-official-population-result-summary-v1",
        "study": "speech-aware-evidence-acquisition",
        "preregistration": (
            "docs/readiness/2026-09-04-a2t-tier1-official-population-v1-preregistration.md"
        ),
        "paper_row": PAPER,
        "paper_facing_scorer": "a2t-toolcall-official",
        "alignment_standard": (
            "owner, 2026-09-04: aligned means within 3 points of the official number; being "
            "better than the official number by more than 3 points is also acceptable"
        ),
        "scorer_rule_differences": SCORER_RULE_DIFFERENCES,
        "boundary": (
            "zero model, GPU and network contact: every number is computed from outputs "
            "JSONL files the two registered runs and their sealed predecessor already "
            "wrote, and gold enters only through the registered scorers"
        ),
        "cells": {"T1-official-pop-500": t1_block, "W-official-raw-yaml": w_block},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--t1-attempt", default=None)
    parser.add_argument("--w-attempt", default=None)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    document = build(
        t1_attempt=args.t1_attempt or latest_attempt(T1_RUN_ID),
        w_attempt=args.w_attempt or latest_attempt(W_RUN_ID),
    )
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "result-summary.json"
        out_path.write_text(payload, encoding="utf-8", newline="\n")
        print("written: %s (sha256 %s)" % (out_path, sha256_file(out_path)))

    t1 = document["cells"]["T1-official-pop-500"]
    print()
    print("T1-official-pop-500  n=%d  attempt %s" % (t1["samples"], t1["attempt_id"]))
    tool = t1["official"]["tool_accuracy"]
    exact = t1["official"]["exact_match"]
    print(
        "  tool accuracy %.2f%% CI90 [%.2f, %.2f]  paper 92.4  delta %+.2f pp -> %s"
        % (
            tool["pct"],
            tool["ci90_low_pct"],
            tool["ci90_high_pct"],
            t1["delta_pp"]["tool_accuracy"],
            t1["decision"]["outcome"],
        )
    )
    print(
        "  exact match   %.2f%% CI90 [%.2f, %.2f]  paper 92.4  delta %+.2f pp"
        % (
            exact["pct"],
            exact["ci90_low_pct"],
            exact["ci90_high_pct"],
            t1["delta_pp"]["exact_match"],
        )
    )
    print(
        "  param F1 %.2f macro / %.2f micro   parse rate %.2f%%   frozen-400 tier1 %.2f%%"
        % (
            t1["official"]["param_f1_macro_pct"],
            t1["official"]["param_f1_micro_pct"],
            t1["official"]["parse_rate_pct"],
            t1["frozen_400_tier1_comparison"]["tool_accuracy"]["pct"],
        )
    )
    for domain, block in t1["domain_slices"]["per_domain"].items():
        print(
            "    %-12s n=%-4d tool %.2f%% CI90 [%.2f, %.2f]  EM %.2f%%"
            % (
                domain,
                block["tool_accuracy"]["samples"],
                block["tool_accuracy"]["pct"],
                block["tool_accuracy"]["ci90_low_pct"],
                block["tool_accuracy"]["ci90_high_pct"],
                block["exact_match"]["pct"],
            )
        )
    print(
        "  natural mixture %.2f%%   equal-domain %.2f%%"
        % (
            t1["domain_slices"]["tool_accuracy_natural_mixture_pct"],
            t1["domain_slices"]["tool_accuracy_equal_domain_pct"],
        )
    )
    confusion = t1["tool_confusion_diagnostic"]
    print("  registry tools per domain: %s" % confusion["registry_tools_per_domain"])
    for domain, counts in confusion["per_domain"].items():
        print("    %-12s %s" % (domain, counts))
    print("  top smart_home confusions:")
    for row in confusion["smart_home_top_confusions"][:8]:
        print(
            "    %3d  %-24s %-26s -> %-24s %s"
            % (
                row["rows"],
                row["gold_tool"],
                row["gold_domain_category"],
                row["predicted_tool"],
                row["predicted_domain_category"],
            )
        )

    w = document["cells"]["W-official-raw-yaml"]
    print()
    print("W-official-raw-yaml  n=%d  attempt %s -> %s" % (w["samples"], w["attempt_id"], w["decision"]["outcome"]))
    print("%-24s %8s %8s %8s %10s" % ("tier", "ours", "paper", "delta", "in CI90"))
    for row in w["per_tier"]:
        print(
            "%-24s %8.1f %8.1f %+8.1f %10s"
            % (
                row["tier"],
                row["tool_accuracy_pct"],
                row["paper_tool_accuracy_pct"],
                row["delta_pp"],
                row["paper_inside_ci90"],
            )
        )
    print("%-24s %8.2f" % ("overall", w["overall"]["tool_accuracy_pct"]))
    contrast = w["paired_against_the_sealed_in_code_default_cell"]["contrasts"]["tool_accuracy"]
    print(
        "  paired vs R-official-raw: %.4f -> %.4f  delta %+0.4f  saves %d harms %d ties %d "
        "sign p %.4f  CI90 [%+0.4f, %+0.4f]"
        % (
            contrast["left_mean"],
            contrast["right_mean"],
            contrast["delta"],
            contrast["saves"],
            contrast["harms"],
            contrast["ties"],
            contrast["sign_test_p"],
            contrast["ci_low"],
            contrast["ci_high"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
