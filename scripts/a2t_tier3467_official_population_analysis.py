#!/usr/bin/env python3
"""Verdict numbers for the Audio2Tool tiers-3/4/6/7 official-population flight.

Reads only bytes the registered run already sealed
(``SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1``) plus the sealed predecessor
manifest of the official-protocol replication, and writes
``result-summary.json``. Zero model, GPU or network contact; gold enters only
through the registered scorers, exactly as it does when a flight finalizes.

Sibling of ``scripts/a2t_tier258_official_population_analysis.py`` with one
tier-specific block added: tier 7's TURN RESOLUTION. The released tier-7
loader evaluates ``sorted(query_dir.glob("turn_*_user_*.wav"))[0]`` -- the
FIRST user turn -- while ``data.audio2tool._entry_media``, which bound the
frozen 400's tier-7 rows, reads ``chat_history[-1]``, the FINAL user turn.
The two tier-7 estimates are therefore not two samples of one measurement,
and the summary says so beside the number rather than in prose only.

What it produces, per tier (tier3_multi_intent, tier4_implicit,
tier6_correction, tier7_multiturn), at n = 500 each:

* official-scorer tool accuracy / exact match / parameter F1 with a Wilson
  CI90, against the published Qwen-3-Omni-30B row and against the
  Qwen-2.5-Omni-7B and weakest-published-SpeechLM floors, plus the
  preregistered three-outcome decision on the owner's 3-point alignment band;
* the same figures sliced by domain, natural mixture and equal-domain;
* the frozen 400's own 50 rows of that tier beside them, so the population
  effect is a difference rather than a replacement;
* the official scorer beside the extended ``a2t-toolcall-v2`` on the same
  outputs, with every gap wider than 3 points attributed to a named rule
  difference -- and for tier 3 specifically, the multi-intent tier, the
  official FIRST-CALL rule against v2's ORDERED rule with the count of rows
  naming more than one call and of gold rows carrying additional calls;
* parse and multi-call statistics.

Usage (WSL2, model-free)::

    python scripts/a2t_tier3467_official_population_analysis.py --write
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

RUN_ID = "SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1"
CELL = "T3467-official-pop-2000"
PRED_RUN_ID = "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1"
PRED_ATTEMPT = "attempt-20260904T135250Z-rofficialraw"
PRED_CELL = "R-official-raw"

ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-tier3467-official-population-roster"
    / "flight-roster-receipt.json"
)
FROZEN_400_ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-calibration-400-roster"
    / "flight-roster-receipt.json"
)
OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-tier3467-official-population-v1"
)

TIERS = (
    "tier3_multi_intent",
    "tier4_implicit",
    "tier6_correction",
    "tier7_multiturn",
)
PAPER = {
    "tier3_multi_intent": {"tool_accuracy": 74.7, "exact_match": 28.6, "slot_f1": 35.0},
    "tier4_implicit": {"tool_accuracy": 33.4, "exact_match": 11.3, "slot_f1": 23.4},
    "tier6_correction": {"tool_accuracy": 81.5, "exact_match": 24.8, "slot_f1": 32.4},
    "tier7_multiturn": {"tool_accuracy": 54.6, "exact_match": 16.3, "slot_f1": 26.8},
}
FLOORS = {
    "qwen2_5_omni_7b": {
        "tier3_multi_intent": 50.2,
        "tier4_implicit": 22.4,
        "tier6_correction": 68.3,
        "tier7_multiturn": 48.2,
    },
    "weakest_published_speechlm": {
        "tier3_multi_intent": 40.6,
        "tier4_implicit": 7.9,
        "tier6_correction": 44.6,
        "tier7_multiturn": 34.5,
    },
}
ALIGNMENT_BAND_PP = 3.0
Z_90 = 1.6448536269514722

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

FROZEN_400_NOTE = {
    "tier3_multi_intent": (
        "not a paired contrast: 500 first-recording rows over distinct queries against 50 "
        "rows of the frozen 400 (10 shared queries, 6 shared sample ids). Two independent "
        "estimates of the same tier under the same protocol"
    ),
    "tier4_implicit": (
        "not a paired contrast: 500 first-recording rows over distinct queries against 50 "
        "rows of the frozen 400 (13 shared queries, 7 shared sample ids). Two independent "
        "estimates of the same tier under the same protocol"
    ),
    "tier6_correction": (
        "not a paired contrast: 500 first-recording rows over distinct queries against 50 "
        "rows of the frozen 400 (12 shared queries, 5 shared sample ids). Two independent "
        "estimates of the same tier under the same protocol"
    ),
    "tier7_multiturn": (
        "NOT two estimates of the same measurement. Zero queries are shared (all 50 tier-7 "
        "queries of the frozen 400 were excluded from this population), and more "
        "importantly the two rosters bind DIFFERENT audio for a tier-7 query: the frozen "
        "400 sent chat_history[-1], the FINAL user turn that states the request, while the "
        "released loader -- and therefore this flight -- sends the FIRST user turn, with no "
        "history and no agent audio. The difference below is a protocol difference at least "
        "as much as a population difference"
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


def three_outcome(pct: float, low_pct: float, high_pct: float, paper: float) -> str:
    if pct >= paper - ALIGNMENT_BAND_PP:
        return "ALIGNED"
    if low_pct <= paper <= high_pct:
        return "CONSISTENT-WITHIN-NOISE"
    return "FAIL"


def _tier_facts() -> tuple[dict[str, str], dict[str, str]]:
    """``(domain_by_sample, category_by_sample)`` for the roster, read from
    each tier's released manifest. Identity and stratum fields only."""

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
            (public / f"{tier}_data" / f"{tier}.json").read_text(encoding="utf-8")
        )
        by_id = {int(row["id"]): row for row in manifest}
        for item in roster["items"]:
            if str(item["tier"]) != tier:
                continue
            entry = by_id[int(item["id"])]
            domain[str(item["sample_id"])] = str(entry["domain"])
            category[str(item["sample_id"])] = str(entry.get("category") or "")
    return domain, category


def tier7_turn_resolution() -> dict[str, object]:
    """Which conversational turn each tier-7 row actually put on the wire, and
    how the frozen 400 bound the same tier. Identity facts only."""

    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    block = roster["per_tier"]["tier7_multiturn"]
    audit = block["official_rule_audit"]
    flown: Counter = Counter()
    for item in roster["items"]:
        if str(item["tier"]) != "tier7_multiturn":
            continue
        name = str(item["media_relpath"]).rsplit("/", 1)[-1]
        flown[name.split("_")[1]] += 1

    frozen: Counter = Counter()
    frozen_ids: set[str] = set()
    if FROZEN_400_ROSTER.is_file():
        for item in json.loads(FROZEN_400_ROSTER.read_text(encoding="utf-8"))["items"]:
            if str(item["tier"]) != "tier7_multiturn":
                continue
            frozen_ids.add(str(item["sample_id"]))
            name = str(item["media_relpath"]).rsplit("/", 1)[-1]
            frozen[name.split("_")[1]] += 1

    drawn_ids = {
        str(item["sample_id"])
        for item in roster["items"]
        if str(item["tier"]) == "tier7_multiturn"
    }
    return {
        "rule": (
            "audio_benchmark/datasets/tier7_dataset.py::_get_audio_paths returns "
            "sorted(query_dir.glob('turn_*_user_*.wav')) and BenchmarkEvaluator with "
            "max_speakers_per_query 1 evaluates audio_paths[0], so the request carries the "
            "FIRST user turn only -- no chat history, no agent audio, no later user turn"
        ),
        "flown_turn_index_counts": dict(sorted(flown.items())),
        "population_first_user_turn_index_counts": audit["first_user_turn_index_counts"],
        "drawn_user_turns_per_query_counts": block["user_turns_per_query_counts"],
        "population_user_turns_per_query_counts": audit["user_turns_per_query_counts"],
        "queries_where_the_first_user_turn_is_the_only_user_turn": audit[
            "queries_where_the_first_user_turn_is_the_only_user_turn"
        ],
        "queries_with_later_user_turns": audit["queries_with_later_user_turns"],
        "frozen_400_binding": {
            "rule": (
                "data.audio2tool._entry_media reads chat_history[-1], the FINAL user turn, "
                "which is the turn that states the request"
            ),
            "turn_index_counts": dict(sorted(frozen.items())),
            "shared_sample_ids_with_this_roster": sorted(frozen_ids & drawn_ids),
        },
        "excluded_from_the_population": block["excluded_from_the_population"],
    }


def domain_slices(
    rows: Sequence[Mapping[str, object]], domain_by_sample: Mapping[str, str]
) -> dict[str, object]:
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        grouped.setdefault(domain_by_sample[str(row["sample_id"])], []).append(row)
    per_domain = {
        name: {
            "tool_accuracy": _rate_row(block, "tool_correct"),
            "exact_match": _rate_row(block, "exact_match"),
            "param_f1_macro_pct": 100.0 * _mean(block, "param_f1"),
        }
        for name, block in sorted(grouped.items())
    }
    natural = 100.0 * _mean(
        [{"v": float(bool(row["tool_correct"]))} for row in rows], "v"
    )
    equal = sum(block["tool_accuracy"]["pct"] for block in per_domain.values()) / len(
        per_domain
    )
    return {
        "per_domain": per_domain,
        "tool_accuracy_natural_mixture_pct": natural,
        "tool_accuracy_equal_domain_pct": equal,
        "counts": {name: block["tool_accuracy"]["samples"] for name, block in per_domain.items()},
    }


def tool_confusion(
    rows: Sequence[Mapping[str, object]], domain_by_sample: Mapping[str, str]
) -> dict[str, object]:
    """Where a tier's misses go -- a DIAGNOSTIC, not a metric."""

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

    counts: Counter = Counter()
    misses: Counter = Counter()
    for row in rows:
        sample_id = str(row["sample_id"])
        domain = domain_by_sample[sample_id]
        counts["samples"] += 1
        if row["tool_correct"]:
            counts["correct"] += 1
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
        misses[(str(row["gold_tool"]), predicted)] += 1

    top = [
        {
            "gold_tool": gold,
            "predicted_tool": predicted,
            "rows": count,
            "gold_domain_category": (
                [by_name[gold]["domain"], by_name[gold]["category"]] if gold in by_name else None
            ),
            "predicted_domain_category": (
                [by_name[predicted]["domain"], by_name[predicted]["category"]]
                if predicted in by_name
                else None
            ),
        }
        for (gold, predicted), count in misses.most_common(10)
    ]
    return {
        "note": (
            "diagnostic only; no number here enters a decision. It asks what the wrong "
            "answers are, in the same shape the tier-1 verdict used"
        ),
        "counts": dict(sorted(counts.items())),
        "top_confusions": top,
    }


def build(*, attempt: str) -> dict[str, object]:
    domain_by_sample, _ = _tier_facts()
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))

    official = load_scores(RUN_ID, attempt)["a2t-toolcall-official"]
    v2 = rescore(RUN_ID, attempt, "a2t-toolcall-v2")
    rows = official["per_sample"]
    aggregate = official["aggregate"]
    by_tier: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        by_tier.setdefault(str(row["tier"]), []).append(row)
    if sorted(by_tier) != sorted(TIERS):
        raise SystemExit(f"sealed rows cover {sorted(by_tier)}, expected {sorted(TIERS)}")

    # The frozen 400's own 50 rows of each tier, re-scored under the same scorer.
    predecessor = rescore(PRED_RUN_ID, PRED_ATTEMPT, "a2t-toolcall-official")
    pred_by_tier: dict[str, list[Mapping[str, object]]] = {}
    for row in predecessor["per_sample"]:
        pred_by_tier.setdefault(str(row["tier"]), []).append(row)

    tiers: dict[str, object] = {}
    for tier in TIERS:
        tier_rows = by_tier[tier]
        block = aggregate["per_tier"][tier]
        v2_block = v2["aggregate"]["per_tier"][tier]
        tool = _rate_row(tier_rows, "tool_correct")
        exact = _rate_row(tier_rows, "exact_match")
        paper = PAPER[tier]
        outcome = three_outcome(
            tool["pct"], tool["ci90_low_pct"], tool["ci90_high_pct"], paper["tool_accuracy"]
        )
        pred_rows = pred_by_tier.get(tier, [])
        pred_pct = (
            100.0 * sum(1 for row in pred_rows if row["tool_correct"]) / len(pred_rows)
            if pred_rows
            else None
        )
        tool_delta = 100.0 * (
            float(v2_block["tool_accuracy"]) - float(block["tool_accuracy"])
        )
        em_delta = 100.0 * (float(v2_block["exact_match"]) - float(block["exact_match"]))
        named: list[str] = []
        if abs(tool_delta) > ALIGNMENT_BAND_PP:
            named.append("first_call_only_vs_ordered_sequence")
            if int(block["multi_tool_samples"]) > 0:
                named.append("primary_gold_tool_vs_full_expected_sequence")
        if abs(em_delta) > ALIGNMENT_BAND_PP:
            for name in ("default_argument_credit", "primary_gold_tool_vs_full_expected_sequence"):
                if name not in named:
                    named.append(name)
        tiers[tier] = {
            "samples": int(block["samples"]),
            "official": {
                "tool_accuracy": tool,
                "exact_match": exact,
                "param_f1_macro_pct": 100.0 * float(block["param_f1"]),
                "param_f1_micro_pct": 100.0 * float(block["param_f1_micro"]),
                "param_precision_macro_pct": 100.0 * float(block["param_precision"]),
                "param_recall_macro_pct": 100.0 * float(block["param_recall"]),
                "parse_rate_pct": 100.0 * float(block["parse_rate"]),
                "parse_failures": int(block["parse_failures"]),
                "rows_with_multiple_call_matches": int(block["rows_with_multiple_call_matches"]),
                "multi_tool_gold_samples": int(block["multi_tool_samples"]),
            },
            "paper": paper,
            "delta_pp": {
                "tool_accuracy": tool["pct"] - paper["tool_accuracy"],
                "exact_match": exact["pct"] - paper["exact_match"],
            },
            "floors": {
                "qwen2_5_omni_7b_pct": FLOORS["qwen2_5_omni_7b"][tier],
                "weakest_published_speechlm_pct": FLOORS["weakest_published_speechlm"][tier],
                "above_qwen2_5_omni_7b": tool["pct"] >= FLOORS["qwen2_5_omni_7b"][tier],
                "above_weakest_published_speechlm": (
                    tool["pct"] >= FLOORS["weakest_published_speechlm"][tier]
                ),
                "delta_vs_qwen2_5_omni_7b_pp": tool["pct"] - FLOORS["qwen2_5_omni_7b"][tier],
                "delta_vs_weakest_published_speechlm_pp": (
                    tool["pct"] - FLOORS["weakest_published_speechlm"][tier]
                ),
            },
            "decision": {
                "outcome": outcome,
                "rule": (
                    f"ALIGNED = official tool accuracy >= {paper['tool_accuracy'] - ALIGNMENT_BAND_PP:.1f} "
                    f"(within 3 pp of the paper's {paper['tool_accuracy']}, or better); "
                    "CONSISTENT-WITHIN-NOISE = not ALIGNED but the paper value inside the "
                    "Wilson CI90 at n = 500; FAIL = neither"
                ),
                "aligned_threshold_pct": paper["tool_accuracy"] - ALIGNMENT_BAND_PP,
                "paper_inside_ci90": (
                    tool["ci90_low_pct"] <= paper["tool_accuracy"] <= tool["ci90_high_pct"]
                ),
            },
            "official_versus_v2": {
                "official_tool_accuracy_pct": 100.0 * float(block["tool_accuracy"]),
                "v2_tool_accuracy_ordered_pct": 100.0 * float(v2_block["tool_accuracy"]),
                "v2_tool_accuracy_multiset_pct": 100.0
                * float(v2_block["tool_accuracy_multiset"]),
                "tool_accuracy_delta_pp": tool_delta,
                "tool_accuracy_within_band": abs(tool_delta) <= ALIGNMENT_BAND_PP,
                "official_exact_match_pct": 100.0 * float(block["exact_match"]),
                "v2_exact_match_pct": 100.0 * float(v2_block["exact_match"]),
                "exact_match_delta_pp": em_delta,
                "official_param_f1_macro_pct": 100.0 * float(block["param_f1"]),
                "official_param_f1_micro_pct": 100.0 * float(block["param_f1_micro"]),
                "v2_slot_f1_pct": 100.0 * float(v2_block["slot_f1"]),
                "paper_slot_f1_pct": paper["slot_f1"],
                "rules_that_can_explain_a_gap": named,
            },
            "domain_slices": domain_slices(tier_rows, domain_by_sample),
            "tool_confusion_diagnostic": tool_confusion(tier_rows, domain_by_sample),
            "frozen_400_comparison": {
                "cell_id": PRED_CELL,
                "samples": len(pred_rows),
                "tool_accuracy": _rate_row(pred_rows, "tool_correct") if pred_rows else None,
                "exact_match": _rate_row(pred_rows, "exact_match") if pred_rows else None,
                "population_effect_pp": (tool["pct"] - pred_pct) if pred_pct is not None else None,
                "note": FROZEN_400_NOTE[tier],
            },
        }
        if tier == "tier7_multiturn":
            tiers[tier]["turn_resolution"] = tier7_turn_resolution()

    manifest = load_manifest(RUN_ID, attempt)
    return {
        "schema": "saea-a2t-tier3467-official-population-result-summary-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "cell_id": CELL,
        "attempt_id": attempt,
        "manifest_sha256": sha256_file(
            run_dir(RUN_ID, attempt) / f"{RUN_ID}.run-manifest.json"
        ),
        "study_commit": manifest["study_commit"],
        "protocol_hash": manifest["protocol_hash"],
        "roster": {
            "receipt": str(ROSTER.relative_to(REPO)).replace("\\", "/"),
            "receipt_sha256": sha256_file(ROSTER),
            "count": int(roster["count"]),
            "split_identity_hash": str(roster["split_identity_hash"]),
            "flight_split_identity_hash": str(roster["flight_split_identity_hash"]),
        },
        "preregistration": (
            "docs/readiness/2026-09-04-a2t-tier3467-official-population-v1-preregistration.md"
        ),
        "paper_source": "arXiv:2604.22821 Table 3, Qwen-3-Omni-30B",
        "alignment_band_pp": ALIGNMENT_BAND_PP,
        "confidence_interval": "Wilson score CI90",
        "overall": {
            "samples": int(aggregate["samples"]),
            "official_tool_accuracy_pct": 100.0 * float(aggregate["tool_accuracy"]),
            "official_exact_match_pct": 100.0 * float(aggregate["exact_match"]),
            "official_param_f1_macro_pct": 100.0 * float(aggregate["param_f1"]),
            "official_param_f1_micro_pct": 100.0 * float(aggregate["param_f1_micro"]),
            "official_parse_rate_pct": 100.0 * float(aggregate["parse_rate"]),
            "official_parse_failures": int(aggregate["parse_failures"]),
            "rows_with_multiple_call_matches": int(
                aggregate["rows_with_multiple_call_matches"]
            ),
            "v2_tool_accuracy_ordered_pct": 100.0 * float(v2["aggregate"]["tool_accuracy"]),
            "v2_exact_match_pct": 100.0 * float(v2["aggregate"]["exact_match"]),
            "v2_parse_failures": int(v2["aggregate"]["parse_failures"]),
        },
        "scorer_versions": {
            "official": aggregate["scorer_version"],
            "official_commit": aggregate["official_commit"],
            "official_gold": aggregate["gold_version"],
            "official_metrics_blob_sha1": aggregate["official_metrics_blob_sha1"],
            "v2": v2["aggregate"]["scorer_version"],
            "v2_gold": v2["aggregate"]["gold_version"],
            "parse": v2["aggregate"]["parse_version"],
        },
        "scorer_rule_differences": SCORER_RULE_DIFFERENCES,
        "tiers": tiers,
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

    print()
    print("%s  attempt %s  n=%d" % (CELL, document["attempt_id"], document["overall"]["samples"]))
    print(
        "%-24s %7s %-18s %7s %8s %9s %8s %8s"
        % ("tier", "ours", "CI90", "paper", "delta", "outcome", "EM", "paperEM")
    )
    for tier in TIERS:
        block = document["tiers"][tier]
        tool = block["official"]["tool_accuracy"]
        print(
            "%-24s %7.2f [%6.2f,%6.2f] %7.1f %+8.2f %9s %8.2f %8.1f"
            % (
                tier,
                tool["pct"],
                tool["ci90_low_pct"],
                tool["ci90_high_pct"],
                block["paper"]["tool_accuracy"],
                block["delta_pp"]["tool_accuracy"],
                block["decision"]["outcome"],
                block["official"]["exact_match"]["pct"],
                block["paper"]["exact_match"],
            )
        )
    print()
    print("floors (tool accuracy):")
    for tier in TIERS:
        floors = document["tiers"][tier]["floors"]
        print(
            "  %-24s vs Qwen2.5-Omni-7B %5.1f -> %+6.2f (%s) | vs weakest SpeechLM %5.1f -> %+6.2f (%s)"
            % (
                tier,
                floors["qwen2_5_omni_7b_pct"],
                floors["delta_vs_qwen2_5_omni_7b_pp"],
                "above" if floors["above_qwen2_5_omni_7b"] else "BELOW",
                floors["weakest_published_speechlm_pct"],
                floors["delta_vs_weakest_published_speechlm_pp"],
                "above" if floors["above_weakest_published_speechlm"] else "BELOW",
            )
        )
    print()
    print("official vs v2, parse and multi-call:")
    for tier in TIERS:
        block = document["tiers"][tier]
        contrast = block["official_versus_v2"]
        print(
            "  %-24s TA off %6.2f / v2 %6.2f (%+6.2f)  EM off %6.2f / v2 %6.2f (%+6.2f)  "
            "F1 %5.2f macro / %5.2f micro / v2 slot %5.2f (paper %4.1f)  parse %6.2f%%  "
            "multi-call rows %3d  multi-tool gold %3d"
            % (
                tier,
                contrast["official_tool_accuracy_pct"],
                contrast["v2_tool_accuracy_ordered_pct"],
                contrast["tool_accuracy_delta_pp"],
                contrast["official_exact_match_pct"],
                contrast["v2_exact_match_pct"],
                contrast["exact_match_delta_pp"],
                contrast["official_param_f1_macro_pct"],
                contrast["official_param_f1_micro_pct"],
                contrast["v2_slot_f1_pct"],
                contrast["paper_slot_f1_pct"],
                block["official"]["parse_rate_pct"],
                block["official"]["rows_with_multiple_call_matches"],
                block["official"]["multi_tool_gold_samples"],
            )
        )
    print()
    print("by domain:")
    for tier in TIERS:
        block = document["tiers"][tier]["domain_slices"]
        print("  %s" % tier)
        for domain, cell in block["per_domain"].items():
            print(
                "    %-12s n=%-4d tool %6.2f%% CI90 [%6.2f, %6.2f]  EM %6.2f%%"
                % (
                    domain,
                    cell["tool_accuracy"]["samples"],
                    cell["tool_accuracy"]["pct"],
                    cell["tool_accuracy"]["ci90_low_pct"],
                    cell["tool_accuracy"]["ci90_high_pct"],
                    cell["exact_match"]["pct"],
                )
            )
        print(
            "    natural %6.2f%%   equal-domain %6.2f%%"
            % (
                block["tool_accuracy_natural_mixture_pct"],
                block["tool_accuracy_equal_domain_pct"],
            )
        )
    print()
    print("against the frozen 400's own 50 rows per tier:")
    for tier in TIERS:
        block = document["tiers"][tier]["frozen_400_comparison"]
        print(
            "  %-24s frozen-400 %6.2f%% (n=%d) -> official population %+6.2f pp"
            % (
                tier,
                block["tool_accuracy"]["pct"],
                block["samples"],
                block["population_effect_pp"],
            )
        )
    turn = document["tiers"]["tier7_multiturn"]["turn_resolution"]
    print()
    print("tier 7 turn resolution:")
    print("  flown turn index counts:      %s" % turn["flown_turn_index_counts"])
    print("  drawn user turns per query:   %s" % turn["drawn_user_turns_per_query_counts"])
    print(
        "  only-user-turn / later turns: %d / %d (population)"
        % (
            turn["queries_where_the_first_user_turn_is_the_only_user_turn"],
            turn["queries_with_later_user_turns"],
        )
    )
    print(
        "  frozen 400 bound turn index:  %s (shared sample ids: %d)"
        % (
            turn["frozen_400_binding"]["turn_index_counts"],
            len(turn["frozen_400_binding"]["shared_sample_ids_with_this_roster"]),
        )
    )
    print()
    for tier in TIERS:
        confusion = document["tiers"][tier]["tool_confusion_diagnostic"]
        print("%s misses: %s" % (tier, confusion["counts"]))
        for row in confusion["top_confusions"][:5]:
            print(
                "    %3d  %-26s -> %-26s %s"
                % (
                    row["rows"],
                    row["gold_tool"],
                    row["predicted_tool"],
                    row["predicted_domain_category"],
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
