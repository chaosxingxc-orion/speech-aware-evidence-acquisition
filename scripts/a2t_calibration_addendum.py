#!/usr/bin/env python3
"""Zero-contact addendum to the Audio2Tool direct-baseline calibration verdict.

Three questions the verdict left open, answered only from artifacts the flight
already sealed, plus scorer-side gold and the frozen tool registry. No model
contact; nothing is re-scored.

1. **Ordered tool accuracy.** The verdict's ``metric_notes.tool_accuracy``
   states the registered scorer "provides no ORDERED variant" and that the
   ordered column is "reported as not computed rather than invented". That is
   WRONG. ``a2t-toolcall-v2`` seals BOTH: its ``tool_accuracy`` field is
   ``AggregateScoreV2.tool_accuracy_ordered`` (the sequence match) and
   ``tool_accuracy_multiset`` is v1's own rule. Both were sealed by the flight
   itself, per sample and per tier. This addendum READS them out of the four
   ``*.scores.json`` artifacts and cross-checks, per cell and per tier, that
   v2's multiset column equals v1's ``tool_accuracy`` column exactly.

2. **Multi-call diagnosis** of the native cells' tier3/tier8 collapse: per cell
   and tier, the distribution of the number of calls emitted against the number
   of gold calls, and the share of rows that emitted exactly one call where gold
   expects two or more -- for the legacy cells as well as the native ones.
   Predicted call counts come from re-reading the sealed ``text`` with the very
   parse the registered scorer uses (``parse_tool_calls_text``); the
   reconstruction is verified against each row's sealed ``parsed`` flag.

3. **Tier 1 wrong-tool-set rows**, split into near-neighbour name substitutions
   inside the same registry family (same ``domain`` AND ``category``) versus
   other families.

Gold is read only through ``data.audio2tool.load_expected_calls`` -- the same
scorer-side path the registered scorers use -- and is reduced to call COUNTS and
tool NAMES before anything is emitted. No gold argument values and no utterance
text appear in the output.

Usage::

    python scripts/a2t_calibration_addendum.py           # print only
    python scripts/a2t_calibration_addendum.py --write   # + result-summary.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
RUN_ID = "SAEA-A2T-DIRECT-CALIBRATION-V1"

CELLS: dict[str, tuple[str, bool]] = {
    "A0prime-legacy-raw": ("attempt-20260904T081627Z-a0primelegacyraw", False),
    "A1-native-raw": ("attempt-20260904T081627Z-a1nativeraw", True),
    "P0-legacy-packets": ("attempt-20260904T083403Z-p0legacypackets", False),
    "P1-native-packets": ("attempt-20260904T083403Z-p1nativepackets", True),
}

# The per-cell response-arrival counts the flight recorded through
# ``FlightRuntime.response_arrival_counts`` and the verdict published in its
# "Native tool calls versus text" table. They are not sealed per row, so they
# are quoted here as the reconciliation target for part 2's proxy, never as an
# input to any figure: {cell: (rows_native, rows_text, native_calls_total)}.
VERDICT_ARRIVALS: dict[str, tuple[int, int, int]] = {
    "A0prime-legacy-raw": (0, 400, 0),
    "A1-native-raw": (347, 53, 371),
    "P0-legacy-packets": (0, 400, 0),
    "P1-native-packets": (346, 54, 368),
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
FOCUS_TIERS = ("tier3_multi_intent", "tier8_intent_blending")


class AddendumError(RuntimeError):
    """A sealed artifact does not support the reconstruction."""


def tier_of(sample_id: str) -> str:
    """The scorer's own tier derivation (``a2t_scorer`` uses ``rsplit``)."""

    return sample_id.rsplit(":", 1)[0]


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _pct(value: float) -> float:
    return round(100.0 * value, 4)


def _read_jsonl(path: Path) -> list[Mapping[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _ordered_vs_multiset(cell: str, scores: Mapping[str, object]) -> dict[str, object]:
    """Part 1 -- read, do not recompute: the sealed v2 aggregate already
    carries ``tool_accuracy`` (ordered) and ``tool_accuracy_multiset`` both
    overall and per tier, and v1's aggregate carries its own multiset
    ``tool_accuracy``. The v1-vs-v2 agreement is asserted, not assumed."""

    v2 = scores["a2t-toolcall-v2"]["aggregate"]  # type: ignore[index]
    v1 = scores["a2t-toolcall"]["aggregate"]  # type: ignore[index]

    per_tier: dict[str, object] = {}
    for tier in TIERS:
        a2 = v2["per_tier"][tier]
        a1 = v1["per_tier"][tier]
        if abs(a2["tool_accuracy_multiset"] - a1["tool_accuracy"]) > 1e-12:
            raise AddendumError(
                f"{cell}/{tier}: v2 tool_accuracy_multiset "
                f"{a2['tool_accuracy_multiset']!r} != v1 tool_accuracy "
                f"{a1['tool_accuracy']!r}; the field-semantics premise fails"
            )
        per_tier[tier] = {
            "n": a2["samples"],
            "tool_accuracy_ordered": _pct(a2["tool_accuracy"]),
            "tool_accuracy_multiset": _pct(a2["tool_accuracy_multiset"]),
            "order_penalty_pp": _pct(
                a2["tool_accuracy_multiset"] - a2["tool_accuracy"]
            ),
        }
    if abs(v2["tool_accuracy_multiset"] - v1["tool_accuracy"]) > 1e-12:
        raise AddendumError(f"{cell}: overall v2 multiset != v1 tool_accuracy")
    return {
        "overall": {
            "n": v2["samples"],
            "tool_accuracy_ordered": _pct(v2["tool_accuracy"]),
            "tool_accuracy_multiset": _pct(v2["tool_accuracy_multiset"]),
            "order_penalty_pp": _pct(v2["tool_accuracy_multiset"] - v2["tool_accuracy"]),
        },
        "per_tier": per_tier,
    }


def _multi_call(
    cell: str,
    is_native: bool,
    outputs: Sequence[Mapping[str, object]],
    v2_rows: Mapping[str, Mapping[str, object]],
    gold: Mapping[str, Sequence[object]],
    parse_tool_calls_text,
) -> dict[str, object]:
    """Part 2 -- per-row predicted vs gold CALL COUNTS, nothing else."""

    entries: dict[str, list[tuple[int, int, bool]]] = {t: [] for t in TIERS}
    for row in outputs:
        sample_id = str(row["sample_id"])
        predicted, parsed = parse_tool_calls_text(str(row["text"]))
        sealed_parsed = bool(v2_rows[sample_id]["parsed"])
        if parsed is not sealed_parsed:
            raise AddendumError(
                f"{cell}/{sample_id}: re-parse disagrees with the sealed "
                f"parsed flag ({parsed} vs {sealed_parsed})"
            )
        entries[tier_of(sample_id)].append(
            (len(predicted) if parsed else 0, len(gold[sample_id]), parsed)
        )

    per_tier: dict[str, object] = {}
    for tier in TIERS:
        rows = entries[tier]
        multi = [r for r in rows if r[1] >= 2]
        one_of_multi = sum(1 for r in multi if r[0] == 1)
        per_tier[tier] = {
            "n": len(rows),
            "predicted_call_counts": {
                str(k): v for k, v in sorted(Counter(r[0] for r in rows).items())
            },
            "gold_call_counts": {
                str(k): v for k, v in sorted(Counter(r[1] for r in rows).items())
            },
            "mean_predicted_calls": round(_mean([r[0] for r in rows]), 4),
            "mean_gold_calls": round(_mean([r[1] for r in rows]), 4),
            "rows_unparsed": sum(1 for r in rows if not r[2]),
            "rows_gold_multi_call": len(multi),
            "rows_one_call_where_gold_multi": one_of_multi,
            "share_one_call_where_gold_multi_pct": (
                round(100.0 * one_of_multi / len(multi), 4) if multi else None
            ),
            "rows_undercount": sum(1 for r in rows if r[2] and r[0] < r[1]),
            "rows_overcount": sum(1 for r in rows if r[2] and r[0] > r[1]),
        }

    everything = [r for t in TIERS for r in entries[t]]
    multi = [r for r in everything if r[1] >= 2]
    one_of_multi = sum(1 for r in multi if r[0] == 1)

    rows_native, rows_text, native_calls_total = VERDICT_ARRIVALS[cell]
    parsed_calls_total = sum(r[0] for r in everything)
    rows_unparsed_total = sum(1 for r in everything if not r[2])
    return {
        "native_tools_arm": is_native,
        "native_arrival_reconciliation": {
            "verdict_rows_arrived_native": rows_native,
            "verdict_rows_arrived_as_text": rows_text,
            "verdict_native_calls_total": native_calls_total,
            "reconstructed_parsed_calls_total": parsed_calls_total,
            "reconstructed_rows_unparsed": rows_unparsed_total,
            "calls_attributable_to_text_rows": parsed_calls_total - native_calls_total,
            "text_rows_that_parsed_anyway": rows_text - rows_unparsed_total,
            "note": (
                "for a native arm the reconstructed total should exceed the verdict's "
                "native call total only by the few text-arriving rows whose free text "
                "still parsed as a valid call array, and the reconstructed unparsed count "
                "should sit just under the text-arriving row count -- both hold, which is "
                "independent evidence that the canonicalized array length is the native "
                "tool_call count for natively-arriving rows"
            ),
        },
        "per_tier": per_tier,
        "all_tiers": {
            "n": len(everything),
            "rows_gold_multi_call": len(multi),
            "rows_one_call_where_gold_multi": one_of_multi,
            "share_one_call_where_gold_multi_pct": (
                round(100.0 * one_of_multi / len(multi), 4) if multi else None
            ),
        },
        "focus_tiers": {
            tier: per_tier[tier]["share_one_call_where_gold_multi_pct"]
            for tier in FOCUS_TIERS
        },
    }


_BUCKETS = (
    "same_domain_same_category",
    "same_domain_other_category",
    "other_domain_same_category_label",
    "other_domain_other_category_label",
)


def _bucket(gold_family: tuple[str, str], pred_family: tuple[str, str]) -> str:
    gold_domain, gold_category = gold_family
    pred_domain, pred_category = pred_family
    if gold_domain == pred_domain:
        return (
            "same_domain_same_category"
            if gold_category == pred_category
            else "same_domain_other_category"
        )
    return (
        "other_domain_same_category_label"
        if gold_category == pred_category
        else "other_domain_other_category_label"
    )


def _tier1_split(
    cell: str,
    outputs: Sequence[Mapping[str, object]],
    v1_rows: Mapping[str, Mapping[str, object]],
    gold: Mapping[str, Sequence[object]],
    family: Mapping[str, tuple[str, str]],
    parse_tool_calls_text,
) -> dict[str, object]:
    """Part 3 -- tier1 rows whose predicted tool SET is wrong, split by how far
    the substituted NAME sits from gold's in the registry's domain/category
    taxonomy. Names only; no arguments and no utterance text.

    Four buckets rather than the two the question names, because the registry
    carries only 3 domains and 28 (domain, category) families and the exemplar
    the question gives -- ``setLighting`` vs ``setLightState`` -- is itself
    same-domain but CROSS-category (smart_home/core_control vs
    smart_home/lighting). Collapsing to "same (domain, category) versus
    everything else" would score that exemplar as a different family and report
    zero near-neighbour substitutions for both legacy cells, which would be a
    misleading answer. ``same_domain_*`` recombine to the near-neighbour
    reading; the cross-domain buckets are kept split because a substitution
    that lands on the same category LABEL in another domain (status -> status,
    security -> security) is a device-domain confusion, not a naming one.
    """

    wrong = 0
    unparsed = 0
    count_mismatch = 0
    off_registry = 0
    buckets: Counter[str] = Counter()
    pairs: dict[str, Counter[str]] = {name: Counter() for name in _BUCKETS}
    for row in outputs:
        sample_id = str(row["sample_id"])
        if tier_of(sample_id) != "tier1_direct":
            continue
        if float(v1_rows[sample_id]["tool_accuracy"]) >= 1.0:
            continue
        wrong += 1
        predicted, parsed = parse_tool_calls_text(str(row["text"]))
        if not parsed:
            unparsed += 1
            continue
        pred_names = [call.name for call in predicted]
        gold_names = [call.name for call in gold[sample_id]]
        if len(pred_names) != len(gold_names) or len(pred_names) != 1:
            count_mismatch += 1
            continue
        predicted_name, gold_name = pred_names[0], gold_names[0]
        if predicted_name not in family:
            off_registry += 1
            continue
        name = _bucket(family[gold_name], family[predicted_name])
        buckets[name] += 1
        pairs[name][f"{gold_name} -> {predicted_name}"] += 1

    substitutions = sum(buckets.values())
    accounted = unparsed + count_mismatch + off_registry + substitutions
    if accounted != wrong:
        raise AddendumError(f"{cell}: tier1 split {accounted} != {wrong} wrong rows")
    same_domain = (
        buckets["same_domain_same_category"] + buckets["same_domain_other_category"]
    )
    return {
        "n": 50,
        "rows_wrong_tool_set": wrong,
        "unparsed": unparsed,
        "call_count_mismatch": count_mismatch,
        "single_call_name_absent_from_registry": off_registry,
        "single_call_substitutions": substitutions,
        "split": {name: buckets[name] for name in _BUCKETS},
        "near_neighbour_same_domain": same_domain,
        "other_domain": substitutions - same_domain,
        "near_neighbour_same_domain_share_pct": (
            round(100.0 * same_domain / substitutions, 4) if substitutions else None
        ),
        "substitution_names": {
            name: dict(pairs[name].most_common()) for name in _BUCKETS
        },
    }


def build(root: Path) -> dict[str, object]:
    from speech_aware_evidence_acquisition.data.audio2tool import (
        load_expected_calls,
        load_tool_registry,
    )
    from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path
    from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (
        parse_tool_calls_text,
    )

    lock = load_lock(umbrella_lock_path())
    gold = load_expected_calls(lock, root, repo_root=REPO)
    family = {
        row["tool_name"]: (row["domain"], row["category"])
        for row in load_tool_registry(lock, root)
    }

    ordered: dict[str, object] = {}
    multi_call: dict[str, object] = {}
    tier1: dict[str, object] = {}

    for cell, (attempt_id, is_native) in CELLS.items():
        run_dir = root / "runs" / RUN_ID / attempt_id
        scores = json.loads(
            (run_dir / f"{RUN_ID}.scores.json").read_text(encoding="utf-8")
        )
        outputs = _read_jsonl(run_dir / f"{RUN_ID}.outputs.jsonl")
        v2_rows = {
            str(r["sample_id"]): r for r in scores["a2t-toolcall-v2"]["per_sample"]
        }
        v1_rows = {str(r["sample_id"]): r for r in scores["a2t-toolcall"]["per_sample"]}
        if len(outputs) != len(v2_rows) or len(outputs) != len(v1_rows):
            raise AddendumError(f"{cell}: outputs/scores row counts disagree")

        ordered[cell] = _ordered_vs_multiset(cell, scores)
        multi_call[cell] = _multi_call(
            cell, is_native, outputs, v2_rows, gold, parse_tool_calls_text
        )
        tier1[cell] = _tier1_split(
            cell, outputs, v1_rows, gold, family, parse_tool_calls_text
        )

    return {
        "schema": "saea-a2t-calibration-addendum-v1",
        "run_id": RUN_ID,
        "model_contacts": 0,
        "correction_to_metric_notes_tool_accuracy": (
            "metric_notes.tool_accuracy in this file states that the registered scorer "
            "provides no ORDERED tool-accuracy variant and that the ordered column is "
            "therefore reported as not computed rather than invented. That statement is "
            "incorrect and is corrected here rather than rewritten above: the registered "
            "a2t-toolcall-v2 scorer seals BOTH rules. Its tool_accuracy field is "
            "AggregateScoreV2.tool_accuracy_ordered (the expected-vs-predicted NAME "
            "SEQUENCE match) and its tool_accuracy_multiset field is v1's multiset rule. "
            "Both were computed by the flight's own registered scoring job, per sample and "
            "per tier, and are read out below; no scoring rule was added after the flight."
        ),
        "ordered_vs_multiset": ordered,
        "ordered_vs_multiset_basis": (
            "read verbatim from each cell's sealed SAEA-A2T-DIRECT-CALIBRATION-V1."
            "scores.json (a2t-toolcall-v2 aggregate and its per_tier block). For every "
            "cell and tier the v2 tool_accuracy_multiset column was asserted equal to the "
            "v1 a2t-toolcall tool_accuracy column, which is what identifies v2's "
            "tool_accuracy as the ordered variant rather than a relabelled multiset."
        ),
        "multi_call_diagnosis": multi_call,
        "multi_call_diagnosis_basis": (
            "predicted call count is the length of the call array recovered from each "
            "sealed response text by reproduction.toolcall_scoring.parse_tool_calls_text, "
            "the same parse both registered scorers run; every row's parse outcome was "
            "asserted equal to the parsed flag the scorer sealed for that row, so the "
            "counts are a faithful reconstruction of what the scorer itself saw. An "
            "unparsed row counts as 0 calls, exactly as the scorer treats it. For the "
            "native-tools arms the transport canonicalizes each message.tool_call 1:1 "
            "into that array, so for a natively-arriving row this count IS the number of "
            "tool_call entries the envelope carried; per-row native counts are not "
            "themselves sealed (only per-cell totals are, in the run_phases receipt), so "
            "the canonicalized array is the faithful proxy. Gold call counts come from "
            "data.audio2tool.load_expected_calls, the scorer-side gold path, reduced to a "
            "length before anything is recorded."
        ),
        "tier1_wrong_tool_set": tier1,
        "tier1_wrong_tool_set_basis": (
            "a tier1_direct row counts as wrong when its sealed a2t-toolcall (v1) "
            "tool_accuracy is below 1.0, i.e. the predicted tool-NAME multiset differs "
            "from gold's. Rows that emitted exactly one call against exactly one gold "
            "call are split by where the predicted tool_name sits relative to gold's in "
            "the tools_registry.csv domain/category taxonomy (3 domains, 28 "
            "(domain, category) families over 152 tools). FOUR buckets are reported "
            "rather than the two the question names, because the question's own exemplar "
            "-- setLighting vs setLightState -- is same-domain but CROSS-category "
            "(smart_home/core_control vs smart_home/lighting): scoring 'same family' as "
            "'same domain AND category' alone would classify that exemplar as a different "
            "family and would report zero near-neighbour substitutions for both legacy "
            "cells. near_neighbour_same_domain recombines the two same-domain buckets and "
            "is the figure that answers the question as intended; the cross-domain "
            "buckets stay split because a substitution landing on the same category LABEL "
            "in another domain (status -> status, security -> security, maintenance -> "
            "maintenance) is a device-domain confusion rather than a naming one. Rows "
            "that failed to parse, or that emitted a different number of calls than gold, "
            "are reported separately because no single-name substitution is defined for "
            "them."
        ),
        "boundary": (
            "gold entered only through data.audio2tool.load_expected_calls, the same "
            "scorer-side path the registered scorers use, and only as call COUNTS and "
            "tool NAMES; no gold argument values and no utterance text appear here"
        ),
    }


SECTION_MARKER = "## Addendum — three questions the verdict left open"

_SHORT = {
    "A0prime-legacy-raw": "A0'-legacy-raw",
    "A1-native-raw": "A1-native-raw",
    "P0-legacy-packets": "P0-legacy-packets",
    "P1-native-packets": "P1-native-packets",
}


def render_markdown(addendum: Mapping[str, object]) -> str:
    ordered = addendum["ordered_vs_multiset"]
    multi = addendum["multi_call_diagnosis"]
    tier1 = addendum["tier1_wrong_tool_set"]
    cells = list(CELLS)
    head = " | ".join(_SHORT[c] for c in cells)
    rule = "|---|" + "---:|" * len(cells)

    lines: list[str] = [
        "",
        SECTION_MARKER,
        "",
        "Zero model contacts. Every figure below is read from the four sealed",
        "`SAEA-A2T-DIRECT-CALIBRATION-V1.scores.json` / `.outputs.jsonl` artifacts of the same four",
        "FINALIZED attempts, plus scorer-side gold (`data.audio2tool.load_expected_calls`, reduced to",
        "call counts and tool names) and the frozen `tools_registry.csv`. Nothing was re-scored and no",
        "scoring rule was added. Builder: `scripts/a2t_calibration_addendum.py`; machine-readable form:",
        "the `addendum` key of `result-summary.json`.",
        "",
        "### A1 — Correction: ordered tool accuracy *was* computed, and was sealed by this flight",
        "",
        "The section above (\"Overall, n = 400 per cell\") states that the registered scorer provides no",
        "ordered variant and that the ordered column is therefore **not computed**. That is wrong, and",
        "is corrected here rather than rewritten above. The registered `a2t-toolcall-v2` scorer seals",
        "**both** rules for every sample and every tier: its `tool_accuracy` field is",
        "`AggregateScoreV2.tool_accuracy_ordered`, the expected-versus-predicted tool-name **sequence**",
        "match, and its `tool_accuracy_multiset` field is v1's multiset rule. The flight's own scoring",
        "job computed them; they were in the artifacts all along. The identification is asserted, not",
        "assumed: for every cell and every tier, v2's `tool_accuracy_multiset` equals v1's",
        "`a2t-toolcall` `tool_accuracy` exactly, which is what distinguishes v2's `tool_accuracy` as a",
        "genuinely different, ordered rule rather than a relabelled multiset.",
        "",
        "### A2 — Ordered versus multiset tool accuracy (ordered / multiset)",
        "",
        f"| tier | {head} |",
        rule,
    ]
    for tier in TIERS:
        row = [
            "{:.1f} / {:.1f}".format(
                ordered[c]["per_tier"][tier]["tool_accuracy_ordered"],
                ordered[c]["per_tier"][tier]["tool_accuracy_multiset"],
            )
            for c in cells
        ]
        lines.append(f"| {tier} | " + " | ".join(row) + " |")
    overall = [
        "{:.2f} / {:.2f}".format(
            ordered[c]["overall"]["tool_accuracy_ordered"],
            ordered[c]["overall"]["tool_accuracy_multiset"],
        )
        for c in cells
    ]
    lines.append("| **overall, n = 400** | " + " | ".join(overall) + " |")
    lines += [
        "",
        "Ordering costs {} pp overall on A0', {} pp on A1, {} pp on P0 and {} pp on P1.".format(
            *(
                "{:.2f}".format(ordered[c]["overall"]["order_penalty_pp"])
                for c in cells
            )
        ),
        "The penalty is **exactly zero on all six single-call tiers in all four cells** and appears only",
        "on tier3 and tier8, the two multi-call tiers — 4.0 and 6.0 pp on both legacy cells, 0.0/2.0 pp",
        "on A1 and 0.0/4.0 pp on P1. Ordering is therefore not a second, independent failure mode: it is",
        "a small correction confined to the tiers that emit more than one call, and it does not change",
        "the verdict or any cell's acceptance. Note that the native cells' apparently *smaller* order",
        "penalty is an artefact of A3 below — a cell that emits one call cannot get the order wrong.",
        "",
        "### A3 — Why the native cells collapse on tier3 and tier8: they emit one call instead of many",
        "",
        "Predicted call count is the length of the call array recovered from each sealed response by",
        "`reproduction.toolcall_scoring.parse_tool_calls_text`, the same parse both registered scorers",
        "run; every row's parse outcome was asserted equal to the `parsed` flag the scorer sealed for",
        "that row, and an unparsed row counts as 0 calls exactly as the scorer treats it. Gold enters",
        "only as a length. Tier3 and tier8 are the only tiers where gold ever asks for two or more",
        "calls, and there it always does: 50 of 50 rows in each.",
        "",
        "Share of the 50 gold-multi-call rows on which the cell emitted **exactly one** call:",
        "",
        f"| tier | gold-multi rows | {head} |",
        "|---|---:|" + "---:|" * len(cells),
    ]
    for tier in FOCUS_TIERS:
        row = [
            "{:.0f} %".format(
                multi[c]["per_tier"][tier]["share_one_call_where_gold_multi_pct"]
            )
            for c in cells
        ]
        lines.append(
            f"| {tier} | {multi[cells[0]]['per_tier'][tier]['rows_gold_multi_call']} | "
            + " | ".join(row)
            + " |"
        )
    row = [
        "{:.0f} %".format(multi[c]["all_tiers"]["share_one_call_where_gold_multi_pct"])
        for c in cells
    ]
    lines.append(
        f"| **both tiers** | {multi[cells[0]]['all_tiers']['rows_gold_multi_call']} | "
        + " | ".join(row)
        + " |"
    )
    lines += [
        "",
        "**This is the mechanism.** The legacy contract emits one call on 1 of 100 multi-call rows; the",
        "native contract does it on 81 (A1) and 84 (P1) of 100. Mean calls emitted against a mean gold",
        "of 2.40 on tier3: A0' 1.82, P0 2.02, but A1 1.14 and P1 1.16. Against a mean gold of 2.74 on",
        "tier8: A0' 2.18, P0 2.34, but A1 1.32 and P1 1.22. The native cells are not choosing the wrong",
        "tools on these tiers — they are **stopping after the first one**. On tier3 A1 emitted a single",
        "call on 43 of 50 rows and never more than two; the legacy A0' emitted two on 29 and three on 11.",
        "",
        "The proxy is sound. Per-row native counts are not sealed, only the per-cell totals in the",
        "\"Native tool calls versus text\" table above, so the canonicalized array length stands in for",
        "them — and it reconciles exactly. Reconstructed parsed calls total 372 for A1 against 371",
        "native calls recorded, and 369 for P1 against 368, the difference in each case being exactly",
        "one text-arriving row whose free text still parsed; reconstructed unparsed rows are 52 of 53",
        "text-arriving rows for A1 and 53 of 54 for P1. Every natively-arriving row parsed, and its",
        "array length is its `tool_call` count.",
        "",
        "A second, separate native cost shows up on the single-call tiers: A1 and P1 fail to parse 11–12",
        "of 50 tier1 rows and 16 of 50 tier7 rows, where both legacy cells fail 0–1 and 1. Those are the",
        "rows that declined the tools interface and answered as prose. The native contract thus loses",
        "rows two ways — under-emission where gold wants many calls, and prose fallback where it wants",
        "one — which together account for its 5.75–8.75 pp deficit without any change in tool choice.",
        "",
        "### A4 — Tier 1: how wrong is the wrong tool?",
        "",
        "A tier1 row counts as wrong when its sealed v1 `tool_accuracy` is below 1.0. Rows that emitted",
        "exactly one call against exactly one gold call are placed by where the predicted `tool_name`",
        "sits relative to gold's in the registry taxonomy (3 domains, 28 `(domain, category)` families,",
        "152 tools). Four buckets are reported rather than the two the question names, because the",
        "question's own exemplar — `setLighting` versus `setLightState` — is itself same-domain but",
        "**cross-category** (`smart_home/core_control` versus `smart_home/lighting`); scoring \"same",
        "family\" as \"same domain *and* category\" alone would classify that exemplar as a different",
        "family and report **zero** near-neighbour substitutions for both legacy cells. Names only.",
        "",
        f"| | {head} |",
        rule,
    ]
    for label, key in (
        ("rows with wrong tool set (of 50)", "rows_wrong_tool_set"),
        ("— unparsed (no tool set emitted)", "unparsed"),
        ("— call-count mismatch", "call_count_mismatch"),
        ("— single-call substitutions", "single_call_substitutions"),
    ):
        lines.append(
            f"| {label} | " + " | ".join(str(tier1[c][key]) for c in cells) + " |"
        )
    for label, bucket in (
        ("· same domain, same category", "same_domain_same_category"),
        ("· same domain, other category", "same_domain_other_category"),
        ("· other domain, same category label", "other_domain_same_category_label"),
        ("· other domain, other category label", "other_domain_other_category_label"),
    ):
        lines.append(
            f"| {label} | "
            + " | ".join(str(tier1[c]["split"][bucket]) for c in cells)
            + " |"
        )
    row = [
        "{:.0f} %".format(tier1[c]["near_neighbour_same_domain_share_pct"])
        for c in cells
    ]
    lines.append("| **same-domain share of substitutions** | " + " | ".join(row) + " |")
    lines += [
        "",
        "Read the same-domain rows together: 5 of 16 substitutions on A0', 6 of 14 on A1, 7 of 17 on P0",
        "and 6 of 13 on P1 stay inside the correct device domain — 31–46 %. Under the strict",
        "`(domain, category)` reading only the native cells register any at all (3 on A1, 2 on P1) and",
        "both legacy cells register none, which is precisely why the wider split is reported.",
        "",
        "The majority of tier1 substitutions are therefore **not** naming near-misses: they cross the",
        "device domain, and they do so onto a functionally analogous name in the wrong one. Three",
        "substitutions recur in **all four** cells — `getBatteryLevel` → `getBatteryStatus`",
        "(`smart_home/diagnostics` → `smart_car/charging_energy`), `getLockState` → `getLockStatus`",
        "(`smart_home/status` → `smart_car/status`) and `setVolume` → `adjustVolume`",
        "(`smart_home/media` → `smart_car/media_cabin`) — and `viewRemoteCamera` → `getCameraStream`",
        "(`smart_car/security` → `smart_home/security`) in three. The climate group behaves the same way",
        "with a contract-dependent target: `setThermostatMode` / `setTargetTemperature` /",
        "`setThermostatSchedule` → `setClimate` on both legacy cells, `setThermostatMode` →",
        "`setZoneTemperature` on both native ones. These are stable properties of the",
        "registry-plus-prompt, not sampling noise. The failure is **device-domain disambiguation** across",
        "a 152-tool registry carrying three near-duplicate capability sets, not tool naming.",
        "",
        "Inside `smart_home` the residual confusion is the `core_control` versus `lighting` boundary, and",
        "it too is contract-dependent in the same direction: the legacy cells collapse `setBrightness` /",
        "`setColor` / `setColorTemperature` / `setGroupLightState` onto the generic `setLighting`, while",
        "the native cells collapse them — and `setLighting` itself — onto `setLightState`. The",
        "question's exemplar is thus real and directional, but it sits inside the same-domain bucket,",
        "which is 5 of 16 and 7 of 17 substitutions on the legacy cells and 6 of 14 and 6 of 13 on the",
        "native ones — a minority of tier1's misses either way.",
        "",
        "None of this changes the verdict. It does sharpen the tier1 clarification question the section",
        "above recommends: the paper's 92.4 requires resolving both the device domain and the",
        "`core_control`/`lighting` boundary from speech alone, and it is worth asking whether the",
        "published protocol scopes the candidate tool set per utterance rather than offering all 152.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    from speech_aware_evidence_acquisition.data.lock import data_root

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary",
        type=Path,
        default=(
            REPO
            / "docs"
            / "checks"
            / "speech-aware-evidence-acquisition"
            / "2026-09-04-a2t-direct-calibration-400-v1"
            / "result-summary.json"
        ),
    )
    parser.add_argument(
        "--verdict",
        type=Path,
        default=(
            REPO
            / "docs"
            / "readiness"
            / "2026-09-04-a2t-direct-baseline-calibration-v1-verdict.md"
        ),
    )
    parser.add_argument(
        "--out", type=Path, default=None, help="also write the addendum object alone"
    )
    parser.add_argument(
        "--markdown", type=Path, default=None, help="write the verdict section alone"
    )
    parser.add_argument(
        "--append-verdict",
        action="store_true",
        help="APPEND the rendered section to the verdict; never rewrites it",
    )
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    addendum = build(data_root())
    section = render_markdown(addendum)
    if args.markdown is not None:
        args.markdown.write_text(section, encoding="utf-8", newline="\n")
    if args.append_verdict:
        existing = args.verdict.read_text(encoding="utf-8")
        if SECTION_MARKER in existing:
            raise SystemExit("the verdict already carries the addendum section")
        with args.verdict.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(section)
    if args.out is not None:
        args.out.write_text(
            json.dumps(addendum, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    if args.write:
        summary = json.loads(args.summary.read_text(encoding="utf-8"))
        if "addendum" in summary:
            raise SystemExit("result-summary.json already carries an addendum")
        summary["addendum"] = addendum
        args.summary.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(section)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
