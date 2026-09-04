#!/usr/bin/env python3
"""Post-run analysis for the Audio2Tool official-protocol replication flight.

Sibling of ``scripts/a2t_calibration_analysis.py``, same discipline: reads only
artifacts a flight already sealed and produces the tables the preregistration
asks for. Zero model contact and zero server.

One thing here is NOT read from a sealed score file: the sealed calibration
cell ``A0prime-legacy-raw`` was never scored by ``a2t-toolcall-official``,
because that scorer did not exist when it flew. Its outputs JSONL is re-scored
here through the SAME registered scorer function, offline, on already-recorded
bytes -- the zero-contact re-score precedent of
``docs/readiness/2026-09-03-a2t-scorer-v2-rescore.md``. Nothing is re-run and
no scoring rule is invented.

Why both cells need care when compared. The published protocol asks for a CALL
STRING (``setLighting(state='On')``); this repository's reconstruction asked
for a JSON array (``[{"name": ..., "arguments": {...}}]``). Each scorer parses
one of those and not the other. So three readings are produced and each is
labelled:

* **official-on-both** -- the mechanical like-for-like number. It is also a
  measurement of format compatibility, not only of tool choice.
* **native-on-each** -- every cell under the scorer that can read its own
  output format. Not a like-for-like metric; it is the fair "how well did each
  cell do at its own task" reading.
* **paired** -- ``analysis.paired`` over official-on-both, tier-stratified.

Usage::

    python scripts/a2t_official_protocol_analysis.py --write
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]

RUN_ID = "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1"
ATTEMPT = "attempt-20260904T135250Z-rofficialraw"
CELL = "R-official-raw"

BASELINE_RUN_ID = "SAEA-A2T-DIRECT-CALIBRATION-V1"
BASELINE_ATTEMPT = "attempt-20260904T081627Z-a0primelegacyraw"
BASELINE_CELL = "A0prime-legacy-raw"

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

#: arXiv:2604.22821 Table 3, Qwen3-Omni-30B. Percentages. Same transcription
#: scripts/a2t_calibration_analysis.py uses.
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

#: Preregistration section 7: the tiers the paper reports above 80 %.
DECISION_TIERS = ("tier1_direct", "tier2_parametric", "tier5_needle", "tier6_correction")
TOLERANCE_PP = 5.0
CI_LEVEL = 0.90
#: Two-sided 90 % normal quantile, for the Wilson score interval.
Z_90 = 1.6448536269514722
BOOTSTRAP_SEED = 20260903
BOOTSTRAP_REPLICATES = 10_000


def run_dir(run_id: str, attempt: str) -> Path:
    from speech_aware_evidence_acquisition.data.lock import data_root

    return Path(data_root()) / "runs" / run_id / attempt


def load_scores(run_id: str, attempt: str) -> Mapping[str, object]:
    path = run_dir(run_id, attempt) / f"{run_id}.scores.json"
    return json.loads(path.read_text(encoding="utf-8"))


def load_manifest(run_id: str, attempt: str) -> Mapping[str, object]:
    path = run_dir(run_id, attempt) / f"{run_id}.run-manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def rescore_official(run_id: str, attempt: str) -> Mapping[str, object]:
    """Re-score one sealed outputs JSONL with ``a2t-toolcall-official``.

    Zero contacts: the bytes were written by a prior, separately-registered
    run and gold enters only through the registered scorer, exactly as it does
    when a flight finalizes.
    """

    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.reproduction.a2t_scorer import (
        score_audio2tool_outputs_official,
    )

    outputs = run_dir(run_id, attempt) / f"{run_id}.outputs.jsonl"
    return score_audio2tool_outputs_official(
        outputs, load_lock(umbrella_lock_path()), data_root()
    )


def format_matched_diagnostic(run_id: str, attempt: str) -> Mapping[str, object]:
    """DIAGNOSTIC ONLY: the official metric and the official gold, but with the
    prediction extracted by the JSON-array parser the cell's OWN contract asks
    for (``reproduction.toolcall_scoring.parse_tool_calls_text``, the parser
    ``a2t-toolcall``/``a2t-toolcall-v2`` already run).

    This exists to answer one question the paper-facing numbers cannot: when
    the official scorer reports 0.0 for a cell whose output format its regex
    cannot read, how much of that is FORMAT and how much is TOOL CHOICE? It is
    never a paper-facing number and never enters the decision -- the decision
    uses the dataset's standard scorer unmodified. Only the parser is swapped,
    and only for a cell that was built to emit the other contract; the gold,
    the normalization and the comparison are the official ones.
    """

    from speech_aware_evidence_acquisition.data.audio2tool import load_official_gold
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.reproduction.audio2tool_official import (
        metrics as official_metrics,
    )
    from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (
        parse_tool_calls_text,
    )

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    gold_by_id = load_official_gold(lock, root)
    outputs = run_dir(run_id, attempt) / f"{run_id}.outputs.jsonl"

    per_tier: dict[str, list[bool]] = {}
    per_sample: list[dict[str, object]] = []
    parsed_rows = 0
    for line in outputs.read_text(encoding="utf-8").split("\n"):
        if not line:
            continue
        row = json.loads(line)
        sample_id = str(row["sample_id"])
        gold = gold_by_id[sample_id]
        calls, parsed = parse_tool_calls_text(str(row["text"]))
        parsed_rows += int(bool(parsed))
        predicted = calls[0].name if calls else ""
        correct = official_metrics.compute_tool_accuracy(predicted, gold.tool_name)
        tier = sample_id.rsplit(":", 1)[0]
        per_tier.setdefault(tier, []).append(bool(correct))
        per_sample.append(
            {
                "sample_id": sample_id,
                "tier": tier,
                "predicted_tool": predicted,
                "gold_tool": gold.tool_name,
                "tool_correct": bool(correct),
                "predicted_call_count": len(calls),
                "parsed": bool(parsed),
            }
        )
    total = len(per_sample)
    return {
        "samples": total,
        "parse_rate": parsed_rows / total if total else 0.0,
        "tool_accuracy": sum(1 for row in per_sample if row["tool_correct"]) / total
        if total
        else 0.0,
        "per_tier": {
            tier: {
                "samples": len(flags),
                "tool_accuracy": sum(1 for flag in flags if flag) / len(flags),
            }
            for tier, flags in sorted(per_tier.items())
        },
        "rows_emitting_more_than_one_call": sum(
            1 for row in per_sample if int(row["predicted_call_count"]) > 1
        ),
        "per_sample": per_sample,
    }


def wilson(successes: int, total: int, z: float = Z_90) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion, as a (lo, hi) pair."""

    if total <= 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, center - half), min(1.0, center + half))


def score_map(per_sample: Sequence[Mapping[str, object]]) -> dict[str, dict[str, float]]:
    """``analysis.paired``'s ``{sample_id: {metric: value}}`` shape."""

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
        block = aggregate["per_tier"][tier]
        total = int(block["samples"])
        accuracy = float(block["tool_accuracy"])
        successes = int(round(accuracy * total))
        low, high = wilson(successes, total)
        paper = PAPER[tier]["tool_accuracy"]
        rows.append(
            {
                "tier": tier,
                "samples": total,
                "tool_accuracy_pct": accuracy * 100.0,
                "tool_accuracy_successes": successes,
                "ci90_low_pct": low * 100.0,
                "ci90_high_pct": high * 100.0,
                "paper_tool_accuracy_pct": paper,
                "delta_pp": accuracy * 100.0 - paper,
                "abs_delta_pp": abs(accuracy * 100.0 - paper),
                "within_tolerance": abs(accuracy * 100.0 - paper) <= TOLERANCE_PP,
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


def v2_per_tier_table(aggregate: Mapping[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for tier in TIERS:
        block = aggregate["per_tier"].get(tier)
        if block is None:
            continue
        rows.append(
            {
                "tier": tier,
                "samples": int(block["samples"]),
                "tool_accuracy_ordered_pct": float(block["tool_accuracy"]) * 100.0,
                "tool_accuracy_multiset_pct": float(block["tool_accuracy_multiset"]) * 100.0,
                "exact_match_pct": float(block["exact_match"]) * 100.0,
                "slot_f1_pct": float(block["slot_f1"]) * 100.0,
                "paper_tool_accuracy_pct": PAPER[tier]["tool_accuracy"],
            }
        )
    return rows


def rank_order(values: Sequence[float]) -> list[int]:
    ordered = sorted(values, reverse=True)
    return [ordered.index(value) for value in values]


def decide(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """The preregistered three-outcome rule (section 7)."""

    by_tier = {row["tier"]: row for row in rows}
    decision_rows = [by_tier[tier] for tier in DECISION_TIERS]
    within = all(bool(row["within_tolerance"]) for row in decision_rows)
    ours = [float(by_tier[tier]["tool_accuracy_pct"]) for tier in TIERS]
    paper = [PAPER[tier]["tool_accuracy"] for tier in TIERS]
    order_preserved = rank_order(ours) == rank_order(paper)
    inside_ci = all(bool(row["paper_inside_ci90"]) for row in decision_rows)

    if within and order_preserved:
        outcome = "PASS"
    elif inside_ci:
        outcome = "CONSISTENT-WITHIN-NOISE"
    else:
        outcome = "FAIL"

    return {
        "outcome": outcome,
        "rule": (
            "PASS = per-tier official tool accuracy |delta| <= 5 pp against the paper row "
            "on tiers 1, 2, 5 and 6 AND the tier rank order preserved across all eight "
            "tiers; CONSISTENT-WITHIN-NOISE = not PASS but the paper value inside every "
            "decision tier's Wilson CI90 at n = 50; FAIL = neither"
        ),
        "decision_tiers": list(DECISION_TIERS),
        "tolerance_pp": TOLERANCE_PP,
        "all_decision_tiers_within_tolerance": within,
        "tier_rank_order_preserved": order_preserved,
        "all_decision_tiers_contain_the_paper_value_in_ci90": inside_ci,
        "per_decision_tier": {
            str(row["tier"]): {
                "tool_accuracy_pct": row["tool_accuracy_pct"],
                "paper_pct": row["paper_tool_accuracy_pct"],
                "delta_pp": row["delta_pp"],
                "within_tolerance": row["within_tolerance"],
                "ci90_pct": [row["ci90_low_pct"], row["ci90_high_pct"]],
                "paper_inside_ci90": row["paper_inside_ci90"],
            }
            for row in decision_rows
        },
        "our_rank_order": [
            tier for tier, _ in sorted(
                ((tier, by_tier[tier]["tool_accuracy_pct"]) for tier in TIERS),
                key=lambda item: -float(item[1]),
            )
        ],
        "paper_rank_order": [
            tier for tier, _ in sorted(
                ((tier, PAPER[tier]["tool_accuracy"]) for tier in TIERS),
                key=lambda item: -float(item[1]),
            )
        ],
    }


def build(write: bool) -> Mapping[str, object]:
    from speech_aware_evidence_acquisition.analysis.paired import (
        paired_contrast,
        per_stratum_table,
    )

    ours = load_scores(RUN_ID, ATTEMPT)
    ours_official = ours["a2t-toolcall-official"]
    ours_v2 = ours["a2t-toolcall-v2"]
    ours_v1 = ours["a2t-toolcall"]
    manifest = load_manifest(RUN_ID, ATTEMPT)

    baseline_scores = load_scores(BASELINE_RUN_ID, BASELINE_ATTEMPT)
    baseline_official = rescore_official(BASELINE_RUN_ID, BASELINE_ATTEMPT)

    rows = per_tier_table(ours_official["aggregate"])
    decision = decide(rows)

    left = score_map(baseline_official["per_sample"])
    right = score_map(ours_official["per_sample"])
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

    paired_out = {}
    for metric, contrast in contrasts.items():
        paired_out[metric] = {
            "left_cell": BASELINE_CELL,
            "right_cell": CELL,
            "left_mean": contrast.left_mean,
            "right_mean": contrast.right_mean,
            "delta": contrast.delta,
            "saves": contrast.saves,
            "harms": contrast.harms,
            "ties": contrast.ties,
            "sign_test_p": contrast.sign_test_p,
            "ci_low": contrast.bootstrap.ci_low if contrast.bootstrap else None,
            "ci_high": contrast.bootstrap.ci_high if contrast.bootstrap else None,
            "bootstrap_sigma_hat": (
                contrast.bootstrap.sigma_hat if contrast.bootstrap else None
            ),
            "per_stratum": per_stratum_table(contrast),
        }

    baseline_official_tiers = per_tier_table(baseline_official["aggregate"])

    # The like-for-like protocol effect: same official metric, same official
    # gold, each cell parsed by the contract it was built to emit.
    diagnostic = format_matched_diagnostic(BASELINE_RUN_ID, BASELINE_ATTEMPT)
    diagnostic_left = {
        str(row["sample_id"]): {"tool_accuracy": float(bool(row["tool_correct"]))}
        for row in diagnostic["per_sample"]
    }
    diagnostic_shared = sorted(set(diagnostic_left) & set(right))
    diagnostic_contrasts = paired_contrast(
        diagnostic_left,
        {sid: {"tool_accuracy": right[sid]["tool_accuracy"]} for sid in diagnostic_shared},
        metrics=("tool_accuracy",),
        sample_ids=diagnostic_shared,
        strata_of=lambda sid: sid.rsplit(":", 1)[0],
        seed=BOOTSTRAP_SEED,
        n_replicates=BOOTSTRAP_REPLICATES,
        ci_level=CI_LEVEL,
    )
    diagnostic_paired = {
        metric: {
            "left_cell": BASELINE_CELL + " (JSON-array parse)",
            "right_cell": CELL + " (official parse)",
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
        for metric, contrast in diagnostic_contrasts.items()
    }

    document = {
        "schema": "saea-a2t-official-protocol-replication-summary-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "attempt_id": ATTEMPT,
        "cell": CELL,
        "model_contacts_by_this_analysis": 0,
        "boundary": (
            "zero model contact and zero server. Every number is read from sealed "
            "artifacts, except the A0prime-legacy-raw official column, which re-scores "
            "that cell's already-recorded outputs JSONL through the SAME registered "
            "a2t-toolcall-official function. No scoring rule was added after the flight."
        ),
        "official_code_pin": ours_official["aggregate"]["official_commit"],
        "official_metrics_blob_sha1": ours_official["aggregate"]["official_metrics_blob_sha1"],
        "paper_row": PAPER,
        "paper_source": "arXiv:2604.22821 Table 3, as transcribed in the preregistration",
        "official": {
            "overall": {
                key: ours_official["aggregate"][key]
                for key in (
                    "samples",
                    "tool_accuracy",
                    "exact_match",
                    "param_exact_match",
                    "param_precision",
                    "param_recall",
                    "param_f1",
                    "param_precision_micro",
                    "param_recall_micro",
                    "param_f1_micro",
                    "parse_rate",
                    "parse_failures",
                    "rows_with_multiple_call_matches",
                    "multi_tool_samples",
                    "multi_tool_all_match",
                    "multi_tool_recall",
                    "scorer_version",
                    "gold_version",
                )
            },
            "per_tier": rows,
        },
        "repo_scorers_on_this_cell": {
            "note": (
                "The published protocol asks for a CALL STRING; a2t-toolcall and "
                "a2t-toolcall-v2 parse this repository's reconstructed JSON-array "
                "contract and cannot read one. These columns measure FORMAT "
                "COMPATIBILITY, not tool choice, and are reported for completeness "
                "only -- they are not a result about the model."
            ),
            "a2t_toolcall_v1_overall": {
                key: ours_v1["aggregate"][key]
                for key in ("samples", "tool_accuracy", "exact_match", "parse_failures")
            },
            "a2t_toolcall_v2_overall": {
                key: ours_v2["aggregate"][key]
                for key in (
                    "samples",
                    "tool_accuracy",
                    "tool_accuracy_multiset",
                    "exact_match",
                    "parse_failures",
                )
            },
            "a2t_toolcall_v2_per_tier": v2_per_tier_table(ours_v2["aggregate"]),
        },
        "baseline_comparison": {
            "baseline_run_id": BASELINE_RUN_ID,
            "baseline_attempt_id": BASELINE_ATTEMPT,
            "baseline_cell": BASELINE_CELL,
            "official_on_both": {
                "note": (
                    "the mechanical like-for-like number: the official scorer applied to "
                    "both cells. It is simultaneously a measurement of whether each "
                    "cell's OUTPUT FORMAT is one the official parser can read"
                ),
                "baseline_overall": {
                    key: baseline_official["aggregate"][key]
                    for key in (
                        "samples",
                        "tool_accuracy",
                        "exact_match",
                        "param_f1",
                        "param_f1_micro",
                        "parse_rate",
                        "parse_failures",
                    )
                },
                "baseline_per_tier": baseline_official_tiers,
            },
            "native_on_each": {
                "note": (
                    "each cell under the scorer that can read its own output format. NOT "
                    "a like-for-like metric: different scorers, different gold "
                    "interpretation. Reported so neither cell is judged by a parser "
                    "built for the other's contract."
                ),
                "official_protocol_cell_under_official": ours_official["aggregate"][
                    "tool_accuracy"
                ],
                "baseline_cell_under_v1_multiset": baseline_scores["a2t-toolcall"][
                    "aggregate"
                ]["tool_accuracy"],
                "baseline_cell_under_v2_ordered": baseline_scores["a2t-toolcall-v2"][
                    "aggregate"
                ]["tool_accuracy"],
            },
            "format_matched_diagnostic": {
                "note": (
                    "DIAGNOSTIC, never a paper-facing number and never part of the "
                    "decision: the OFFICIAL metric and the OFFICIAL gold, with the "
                    "prediction taken by the JSON-array parser the baseline cell's own "
                    "contract asks for. It separates format from tool choice, which "
                    "neither of the two readings above can do. The official-protocol "
                    "cell's own official number is repeated beside it for reference; its "
                    "output format already matches the official parser, so no swap "
                    "applies to it."
                ),
                "baseline_cell": {
                    key: value
                    for key, value in diagnostic.items()
                    if key != "per_sample"
                },
                "official_protocol_cell_official_number": ours_official["aggregate"][
                    "tool_accuracy"
                ],
                "per_tier_versus_ours_and_the_paper": [
                    {
                        "tier": tier,
                        "baseline_format_matched_pct": diagnostic["per_tier"][tier][
                            "tool_accuracy"
                        ]
                        * 100.0,
                        "official_protocol_pct": float(
                            ours_official["aggregate"]["per_tier"][tier]["tool_accuracy"]
                        )
                        * 100.0,
                        "paper_pct": PAPER[tier]["tool_accuracy"],
                        "protocol_effect_pp": (
                            float(
                                ours_official["aggregate"]["per_tier"][tier][
                                    "tool_accuracy"
                                ]
                            )
                            - diagnostic["per_tier"][tier]["tool_accuracy"]
                        )
                        * 100.0,
                    }
                    for tier in TIERS
                ],
                "summed_absolute_gap_to_the_paper_pp": {
                    "official_protocol_cell": sum(
                        abs(
                            float(
                                ours_official["aggregate"]["per_tier"][tier][
                                    "tool_accuracy"
                                ]
                            )
                            * 100.0
                            - PAPER[tier]["tool_accuracy"]
                        )
                        for tier in TIERS
                    ),
                    "baseline_cell_format_matched": sum(
                        abs(
                            diagnostic["per_tier"][tier]["tool_accuracy"] * 100.0
                            - PAPER[tier]["tool_accuracy"]
                        )
                        for tier in TIERS
                    ),
                },
                "paired": {
                    "basis": (
                        "analysis.paired on the SAME official metric and gold, with each "
                        "cell's prediction taken by the parser its own output contract "
                        "asks for. This is the like-for-like protocol effect; the "
                        "official-on-both contrast above is dominated by format."
                    ),
                    "n_shared_samples": len(diagnostic_shared),
                    "replicates": BOOTSTRAP_REPLICATES,
                    "seed": BOOTSTRAP_SEED,
                    "ci_level": CI_LEVEL,
                    "contrasts": diagnostic_paired,
                },
            },
            "paired": {
                "basis": (
                    "analysis.paired over the official scorer applied to both cells, on "
                    "the shared sample ids, tier-stratified"
                ),
                "n_shared_samples": len(shared),
                "replicates": BOOTSTRAP_REPLICATES,
                "seed": BOOTSTRAP_SEED,
                "ci_level": CI_LEVEL,
                "contrasts": paired_out,
            },
        },
        "decision": decision,
        "throughput": {
            "calls_used": manifest.get("cost", {}).get("calls_used"),
            "audio_seconds_used": manifest.get("cost", {}).get("audio_seconds_used"),
            "prompt_tokens_total": manifest.get("cost", {}).get("prompt_tokens_total"),
            "completion_tokens_total": manifest.get("cost", {}).get("completion_tokens_total"),
            "latency_seconds_total": manifest.get("cost", {}).get("latency_seconds_total"),
        },
    }

    if write:
        out_dir = (
            REPO
            / "docs/checks/speech-aware-evidence-acquisition"
            / "2026-09-04-a2t-official-protocol-replication-400-v1"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "result-summary.json"
        path.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"wrote {path}")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    document = build(args.write)

    print("\n=== official per tier: ours / paper (delta) with CI90 ===")
    for row in document["official"]["per_tier"]:
        print(
            "  %-24s %6.2f  paper %5.1f  d %+7.2f  CI90 [%5.1f, %5.1f]  paper_in_ci=%s"
            % (
                row["tier"],
                row["tool_accuracy_pct"],
                row["paper_tool_accuracy_pct"],
                row["delta_pp"],
                row["ci90_low_pct"],
                row["ci90_high_pct"],
                row["paper_inside_ci90"],
            )
        )
    decision = document["decision"]
    print("\nDECISION: %s" % decision["outcome"])
    print("  within tolerance on all decision tiers: %s" % decision["all_decision_tiers_within_tolerance"])
    print("  tier rank order preserved: %s" % decision["tier_rank_order_preserved"])
    print("  paper inside CI90 on all decision tiers: %s" % decision["all_decision_tiers_contain_the_paper_value_in_ci90"])
    diag = document["baseline_comparison"]["format_matched_diagnostic"]
    print("\n=== format-matched diagnostic: protocol effect on tool choice ===")
    for row in diag["per_tier_versus_ours_and_the_paper"]:
        print(
            "  %-24s A0prime %6.2f  official %6.2f  paper %5.1f  protocol effect %+6.2f"
            % (
                row["tier"],
                row["baseline_format_matched_pct"],
                row["official_protocol_pct"],
                row["paper_pct"],
                row["protocol_effect_pp"],
            )
        )
    print(
        "  summed |gap| to the paper: official-protocol %.1f pp, A0prime %.1f pp"
        % (
            diag["summed_absolute_gap_to_the_paper_pp"]["official_protocol_cell"],
            diag["summed_absolute_gap_to_the_paper_pp"]["baseline_cell_format_matched"],
        )
    )
    for metric, block in diag["paired"]["contrasts"].items():
        print(
            "  paired %-14s left %.4f right %.4f delta %+.4f saves %d harms %d ties %d "
            "p %.4f CI90 [%+.4f, %+.4f]"
            % (
                metric,
                block["left_mean"],
                block["right_mean"],
                block["delta"],
                block["saves"],
                block["harms"],
                block["ties"],
                block["sign_test_p"],
                block["ci_low"],
                block["ci_high"],
            )
        )
    print("\n=== paired vs %s, official scorer on both ===" % BASELINE_CELL)
    for metric, block in document["baseline_comparison"]["paired"]["contrasts"].items():
        print(
            "  %-14s left %.4f right %.4f delta %+.4f saves %d harms %d ties %d p %.4f CI90 [%+.4f, %+.4f]"
            % (
                metric,
                block["left_mean"],
                block["right_mean"],
                block["delta"],
                block["saves"],
                block["harms"],
                block["ties"],
                block["sign_test_p"],
                block["ci_low"] if block["ci_low"] is not None else float("nan"),
                block["ci_high"] if block["ci_high"] is not None else float("nan"),
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
