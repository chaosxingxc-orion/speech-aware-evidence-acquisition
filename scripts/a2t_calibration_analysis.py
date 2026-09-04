#!/usr/bin/env python3
"""Post-run analysis for the Audio2Tool direct-baseline calibration flight.

Reads only artifacts the flight already sealed -- each cell's
``<run_id>.scores.json`` (the registered ``a2t-toolcall`` / ``a2t-toolcall-v2``
/ ``cost`` scorers' own output) and its run manifest -- and produces the
tables preregistration section 6 asks for:

* per cell, per tier: tool accuracy, exact match under v1 and v2, slot F1,
  parse rate, with the published arXiv:2604.22821 Table 3 row beside it;
* the four paired contrasts (Factor A within each audio path, Factor D
  within each output contract) and the A x D interaction, tier-stratified,
  through ``analysis.paired``;
* the acceptance rule, evaluated per cell.

Zero model contact: no server, no scorer re-run, no gold read by this file --
gold entered only through the registered scorers when the flight finalized.

Usage::

    python scripts/a2t_calibration_analysis.py --write
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
RUN_ID = "SAEA-A2T-DIRECT-CALIBRATION-V1"

CELLS = {
    "A0prime-legacy-raw": "attempt-20260904T081627Z-a0primelegacyraw",
    "A1-native-raw": "attempt-20260904T081627Z-a1nativeraw",
    "P0-legacy-packets": "attempt-20260904T083403Z-p0legacypackets",
    "P1-native-packets": "attempt-20260904T083403Z-p1nativepackets",
}

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

#: arXiv:2604.22821 Table 3, as transcribed in this preregistration's own
#: section 1 table. Percentages.
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

#: Section 6: the tiers the paper reports above 80 %.
ACCEPTANCE_TIERS = ("tier1_direct", "tier2_parametric", "tier5_needle", "tier6_correction")
ACCEPTANCE_TOLERANCE_PP = 5.0

BOOTSTRAP_SEED = 20260903
BOOTSTRAP_REPLICATES = 10_000
CI_LEVEL = 0.90


def data_root() -> Path:
    import os

    value = os.environ.get("SPEECHRL_DATA_DIR")
    if not value:
        raise SystemExit("SPEECHRL_DATA_DIR is required")
    return Path(value)


def load_cell(root: Path, attempt_id: str) -> dict[str, object]:
    run_dir = root / "runs" / RUN_ID / attempt_id
    scores = json.loads((run_dir / f"{RUN_ID}.scores.json").read_text(encoding="utf-8"))
    manifest = json.loads(
        (run_dir / f"{RUN_ID}.run-manifest.json").read_text(encoding="utf-8")
    )
    return {"scores": scores, "manifest": manifest, "run_dir": run_dir}


def per_sample(scores: Mapping[str, object], scorer: str) -> dict[str, Mapping[str, object]]:
    rows = scores[scorer]["per_sample"]
    return {str(row["sample_id"]): row for row in rows}


def tier_of(sample_id: str) -> str:
    return sample_id.split(":", 1)[0]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def cell_tables(cell: Mapping[str, object]) -> dict[str, object]:
    v1 = per_sample(cell["scores"], "a2t-toolcall")
    v2 = per_sample(cell["scores"], "a2t-toolcall-v2")
    cost = cell["scores"]["cost"]["aggregate"]
    per_tier: dict[str, dict[str, float]] = {}
    for tier in TIERS:
        ids = [sid for sid in v1 if tier_of(sid) == tier]
        per_tier[tier] = {
            "n": len(ids),
            "tool_accuracy_multiset": 100.0 * _mean([v1[i]["tool_accuracy"] for i in ids]),
            "exact_match_v1": 100.0 * _mean([v1[i]["exact_match"] for i in ids]),
            "exact_match_v2": 100.0 * _mean([v2[i]["exact_match"] for i in ids]),
            "slot_f1_v1": 100.0 * _mean([v1[i]["slot_f1"] for i in ids]),
            "parse_rate": 100.0 * _mean([1.0 if v1[i]["parsed"] else 0.0 for i in ids]),
            "paper_tool_accuracy": PAPER[tier]["tool_accuracy"],
            "paper_exact_match": PAPER[tier]["exact_match"],
            "tool_accuracy_delta_pp": (
                100.0 * _mean([v1[i]["tool_accuracy"] for i in ids])
                - PAPER[tier]["tool_accuracy"]
            ),
        }
    overall = {
        "n": len(v1),
        "tool_accuracy_multiset": 100.0 * _mean([r["tool_accuracy"] for r in v1.values()]),
        "exact_match_v1": 100.0 * _mean([r["exact_match"] for r in v1.values()]),
        "exact_match_v2": 100.0 * _mean([r["exact_match"] for r in v2.values()]),
        "slot_f1_v1": 100.0 * _mean([r["slot_f1"] for r in v1.values()]),
        "parse_rate": 100.0 * _mean([1.0 if r["parsed"] else 0.0 for r in v1.values()]),
    }
    calls = int(cost.get("calls_used") or 0)
    latency = float(cost.get("latency_seconds_total") or 0.0)
    return {
        "per_tier": per_tier,
        "overall": overall,
        "cost": {
            "calls_used": calls,
            "audio_seconds_used": cost.get("audio_seconds_used"),
            "prompt_tokens_total": cost.get("prompt_tokens_total"),
            "completion_tokens_total": cost.get("completion_tokens_total"),
            "latency_seconds_total": latency,
            "mean_latency_seconds": latency / calls if calls else 0.0,
            "prompt_tokens_per_call": (
                (cost.get("prompt_tokens_total") or 0) / calls if calls else 0.0
            ),
            "completion_tokens_per_second": (
                (cost.get("completion_tokens_total") or 0) / latency if latency else 0.0
            ),
            "tool_calls_counter": cost.get("tool_calls"),
        },
    }


def acceptance(cell_id: str, tables: Mapping[str, object]) -> dict[str, object]:
    """Section 6: at least one cell reaches per-tier tool-accuracy
    |delta| <= 5 pp against the paper row on tiers 1, 2, 5 and 6, with the
    tier rank order preserved."""

    per_tier = tables["per_tier"]
    within = {
        tier: abs(per_tier[tier]["tool_accuracy_delta_pp"]) <= ACCEPTANCE_TOLERANCE_PP
        for tier in ACCEPTANCE_TIERS
    }
    ours = [per_tier[tier]["tool_accuracy_multiset"] for tier in TIERS]
    paper = [PAPER[tier]["tool_accuracy"] for tier in TIERS]
    ours_rank = [sorted(ours, reverse=True).index(value) for value in ours]
    paper_rank = [sorted(paper, reverse=True).index(value) for value in paper]
    rank_preserved = ours_rank == paper_rank
    return {
        "cell_id": cell_id,
        "tiers_within_5pp": within,
        "all_four_tiers_within_5pp": all(within.values()),
        "tier_rank_order_preserved": rank_preserved,
        "accepted": all(within.values()) and rank_preserved,
        "rule": (
            "per-tier tool-accuracy |delta| <= 5 pp against the paper row on tiers 1, 2, "
            "5 and 6, with the tier rank order preserved"
        ),
    }


def build(root: Path) -> dict[str, object]:
    from speech_aware_evidence_acquisition.analysis.paired import (
        paired_contrast,
        render_markdown,
    )

    loaded = {name: load_cell(root, attempt) for name, attempt in CELLS.items()}
    tables = {name: cell_tables(cell) for name, cell in loaded.items()}

    def metric_map(name: str, scorer: str, metric: str) -> dict[str, dict[str, float]]:
        rows = per_sample(loaded[name]["scores"], scorer)
        return {sid: {metric: float(row[metric])} for sid, row in rows.items()}

    def contrast(left: str, right: str, label: str) -> dict[str, object]:
        out: dict[str, object] = {}
        for scorer, metric in (
            ("a2t-toolcall", "tool_accuracy"),
            ("a2t-toolcall", "exact_match"),
            ("a2t-toolcall-v2", "exact_match"),
        ):
            key = f"{label}::{scorer}::{metric}"
            result = paired_contrast(
                metric_map(left, scorer, metric),
                metric_map(right, scorer, metric),
                metrics=[metric],
                strata_of=tier_of,
                seed=BOOTSTRAP_SEED,
                n_replicates=BOOTSTRAP_REPLICATES,
                ci_level=CI_LEVEL,
            )
            out[key] = result[metric]
        return out

    contrasts: dict[str, object] = {}
    contrasts.update(contrast("A0prime-legacy-raw", "A1-native-raw", "A_within_raw"))
    contrasts.update(contrast("P0-legacy-packets", "P1-native-packets", "A_within_packets"))
    contrasts.update(contrast("A0prime-legacy-raw", "P0-legacy-packets", "D_within_legacy"))
    contrasts.update(contrast("A1-native-raw", "P1-native-packets", "D_within_native"))

    # A x D interaction on the paired 400: (A within packets) - (A within raw)
    interaction = {}
    for scorer, metric in (
        ("a2t-toolcall", "tool_accuracy"),
        ("a2t-toolcall", "exact_match"),
        ("a2t-toolcall-v2", "exact_match"),
    ):
        raw_a = contrasts[f"A_within_raw::{scorer}::{metric}"]
        pkt_a = contrasts[f"A_within_packets::{scorer}::{metric}"]
        interaction[f"{scorer}::{metric}"] = {
            "a_within_raw_delta": raw_a.delta,
            "a_within_packets_delta": pkt_a.delta,
            "interaction_delta": pkt_a.delta - raw_a.delta,
            "basis": (
                "difference of the two Factor-A deltas on the same paired 400; the "
                "bootstrap CI of a difference of differences is not computed here "
                "because analysis.paired contrasts two score maps, not two contrasts"
            ),
        }

    verdicts = {name: acceptance(name, tables[name]) for name in CELLS}
    accepted = [name for name, v in verdicts.items() if v["accepted"]]

    def summed_abs_delta(name: str, tiers: Sequence[str]) -> float:
        return sum(
            abs(tables[name]["per_tier"][tier]["tool_accuracy_delta_pp"]) for tier in tiers
        )

    # Two different senses of "closest to the paper", reported separately
    # because they disagree here and picking one silently would hide that.
    best_acceptance_tiers = min(CELLS, key=lambda n: summed_abs_delta(n, ACCEPTANCE_TIERS))
    best_all_tiers = min(CELLS, key=lambda n: summed_abs_delta(n, TIERS))
    best_overall_accuracy = max(
        CELLS, key=lambda n: tables[n]["overall"]["tool_accuracy_multiset"]
    )
    closeness = {
        name: {
            "summed_abs_delta_acceptance_tiers_pp": summed_abs_delta(name, ACCEPTANCE_TIERS),
            "summed_abs_delta_all_tiers_pp": summed_abs_delta(name, TIERS),
            "overall_tool_accuracy": tables[name]["overall"]["tool_accuracy_multiset"],
        }
        for name in CELLS
    }
    best = best_all_tiers
    return {
        "schema": "saea-a2t-calibration-result-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "cells": {name: {"attempt_id": CELLS[name], **tables[name]} for name in CELLS},
        "paper_row": PAPER,
        "paper_source": "arXiv:2604.22821 Table 3, as transcribed in the preregistration",
        "acceptance": {
            "rule": (
                "at least one cell reaches per-tier tool-accuracy |delta| <= 5 pp against "
                "the paper row on tiers 1, 2, 5 and 6, with the tier rank order preserved"
            ),
            "per_cell": verdicts,
            "accepted_cells": accepted,
            "any_cell_accepted": bool(accepted),
            "closeness_to_the_paper_row": closeness,
            "closest_cell_on_the_acceptance_tiers": best_acceptance_tiers,
            "closest_cell_on_all_eight_tiers": best_all_tiers,
            "highest_overall_tool_accuracy_cell": best_overall_accuracy,
            "best_cell_for_reporting": best_all_tiers,
            "best_cell_basis": (
                "smallest summed absolute per-tier tool-accuracy gap to the paper row "
                "across all eight tiers; the four-tier acceptance subset picks a "
                "different cell, and both are recorded because they disagree"
            ),
        },
        "contrasts": {name: c.as_dict() for name, c in contrasts.items()},
        "interaction": interaction,
        "bootstrap": {
            "replicates": BOOTSTRAP_REPLICATES,
            "seed": BOOTSTRAP_SEED,
            "ci_level": CI_LEVEL,
            "stratification": "tier",
        },
        "metric_notes": {
            "tool_accuracy": (
                "the registered a2t-toolcall scorer compares expected and predicted tool "
                "NAME MULTISETS (Counter == Counter), so this is the multiset figure. The "
                "registered scorer provides no ORDERED variant; preregistration section 6 "
                "asks for both, and the ordered column is therefore reported as not "
                "computed rather than invented here -- adding a scoring rule after the "
                "flight would make the paper-facing number something other than the "
                "dataset's standard scorer"
            ),
            "exact_match_v1_vs_v2": (
                "a2t-toolcall is a2t-scorer-v1; a2t-toolcall-v2 is the registered v2 rule "
                "that credits omitted registry-default arguments"
            ),
        },
        "markdown": render_markdown(contrasts),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            REPO
            / "docs/checks/speech-aware-evidence-acquisition"
            / "2026-09-04-a2t-direct-calibration-400-v1"
            / "result-summary.json"
        ),
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    document = build(data_root())
    payload = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "accepted_cells": document["acceptance"]["accepted_cells"],
                "closest_on_acceptance_tiers": document["acceptance"]["closest_cell_on_the_acceptance_tiers"],
                "closest_on_all_tiers": document["acceptance"]["closest_cell_on_all_eight_tiers"],
                "highest_overall": document["acceptance"]["highest_overall_tool_accuracy_cell"],
                "output": str(args.output),
                "written": bool(args.write),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
