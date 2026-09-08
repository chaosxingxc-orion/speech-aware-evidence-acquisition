#!/usr/bin/env python3
"""The paired read of `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` against its sealed comparator.

Exposure row `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1`; this read spends no model,
GPU, tool, embedding, network or audio-decode contact and opens no Earnings-22
surface. The rule is
`docs/readiness/2026-09-07-e21-obs-speaker-turn-units-v1-preregistration.md`
(sections 4, 5 and 6, with the dated 2026-09-08 v2 addendum's counts). Section 6's
byte-level falsifier is a SEPARATE step that runs before any score file is opened
and is not repeated here.

Every statistic comes out of the same instrument the tail cell and the own-null
replicate used (`build_e21_tail2s_verdict`): the pooled ratio
`sum(numerator) / sum(denominator)`, `analysis.paired.resampled_statistic` at
10,000 replicates / seed 20260903 / CI90, clustered by CALL over 44 clusters.

Deltas are reported twice and both are labelled: `movement` is always
cell - comparator, and `improvement` is signed so that POSITIVE means the cell is
better (comparator - cell for the error rates, cell - comparator for the one
accuracy). Section 6's rule reads `improvement`.

usage:
  build_e21_obs_e1_verdict.py --score-read R --cell-attempt A --falsifier F --out-dir D
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(
    os.environ.get("SAEA_REPO_ROOT", "")
    or "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
for candidate in (Path(__file__).resolve().parent, REPO_ROOT / "scripts"):
    if (candidate / "build_e21_tail2s_verdict.py").is_file():
        sys.path.insert(0, str(candidate))
        break

import build_e21_tail2s_verdict as t2  # noqa: E402

RUN_ID = "SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1"
COMPARATOR_RUN = t2.COMPARATOR_RUN
COMPARATOR_ATTEMPT = t2.COMPARATOR_ATTEMPT
NO_PAUSE_CALL = "4366522"

PLAN = REPO_ROOT / "docs/receipts/obs/e21-speaker-turn-units-v2.json"
ROSTER = t2.ROSTER

#: The comparator's own one-pass geometry, from its sealed row.
COMPARATOR_CONTACTS = 1593
COMPARATOR_CUT_SECONDS = 141345.852687
COMPARATOR_DELIVERED_SECONDS = 141345.852687
COMPARATOR_GPU_HOURS = 0.9734

#: `SAEA-E21-FULL44-NULL-REPLICATE-V1`, section 4 of
#: `docs/readiness/2026-09-08-e21-own-null-replicate-v1-verdict.md`: the
#: Earnings-21 non-inferiority margin per metric is the half-width of that
#: cell's own call-clustered CI90. The semantic one is ADVISORY -- its null
#: interval excludes zero, so it cannot carry a "does not rise" clause.
OWN_NULL_HALF_WIDTH = {
    "corpus_wer_percent": 0.05793,
    "conec_overall_wer_percent": 0.05793,
    "conec_non_entity_wer_percent": 0.06475,
    "conec_person_wer_percent": 0.25009,
    "conec_org_wer_percent": 0.35609,
    "numeric_value_accuracy_percent": 0.15651,
    "semantic_high_impact_error_rate_percent": 0.00148,
}
ADVISORY_MARGINS = {"semantic_high_impact_error_rate_percent"}

#: Section 6's own non-inferiority margin for corpus WER, unchanged by anything
#: measured later: -0.30 points.
SECTION6_MARGIN = -0.30

#: name -> (numerator, denominator, lower_is_better, scale)
METRICS = dict(t2.POOLED)
for _entity in ("GPE", "LOC", "PRODUCT", "EVENT", "NORP", "FAC"):
    METRICS[f"conec_{_entity.lower()}_wer_percent"] = (
        f"conec_{_entity.lower()}_errors",
        f"conec_{_entity.lower()}_reference_words",
        True,
        100.0,
    )

ALL_ENTITY_TYPES = ("PERSON", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "NORP", "FAC")


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def call_rows(document: dict) -> dict[str, dict]:
    """`build_e21_tail2s_verdict.call_rows_from_score_read`, widened to carry all
    eight ConEC entity classes rather than the three that read needs."""

    rows = t2.call_rows_from_score_read(document)
    scores = document.get("scores") if "scores" in document else document
    for entry in scores["conec-entity-wer-official"]["per_sample"]:
        row = rows[str(entry["sample_id"])]
        buckets = entry["by_entity_type"]
        for entity in ALL_ENTITY_TYPES:
            bucket = buckets.get(entity) or {"errors": 0, "reference_words": 0}
            row[f"conec_{entity.lower()}_errors"] = int(bucket["errors"])
            row[f"conec_{entity.lower()}_reference_words"] = int(
                bucket["reference_words"]
            )
    return rows


def interval(left: dict, right: dict, ids, spec) -> dict:
    numerator, denominator, _lower, scale = spec
    return t2.bootstrap_delta(
        left, right, ids, numerator, denominator, scale, cluster_of=lambda i: i
    )


def metric_block(
    comparator: dict[str, dict], cell: dict[str, dict], ids, name: str
) -> dict:
    numerator, denominator, lower_is_better, scale = METRICS[name]
    comp = t2.pooled(comparator, ids, numerator, denominator, scale)
    this = t2.pooled(cell, ids, numerator, denominator, scale)
    # `improvement` is signed so positive = the cell is better.
    if lower_is_better:
        block = interval(cell, comparator, ids, METRICS[name])
    else:
        block = interval(comparator, cell, ids, METRICS[name])
    margin = OWN_NULL_HALF_WIDTH.get(name)
    out = {
        "metric": name,
        "lower_is_better": lower_is_better,
        "comparator": comp,
        "cell": this,
        "movement_cell_minus_comparator": this - comp,
        "improvement_point": block["point"],
        "improvement_ci90_low": block["ci_low"],
        "improvement_ci90_high": block["ci_high"],
        "sigma_hat": block["sigma_hat"],
        "clusters": block["n"],
        "replicates": block["replicates"],
        "seed": block["seed"],
        "ci_level": block["ci_level"],
        "equal_stratum_comparator": t2.equal_stratum(
            comparator, ids, numerator, denominator, scale
        ),
        "equal_stratum_cell": t2.equal_stratum(cell, ids, numerator, denominator, scale),
    }
    if margin is not None:
        out["own_null_half_width"] = margin
        out["own_null_margin_advisory"] = name in ADVISORY_MARGINS
        out["abs_movement_over_half_width"] = (
            abs(out["improvement_point"]) / margin if margin else None
        )
        out["non_inferior_at_own_null_margin"] = out["improvement_ci90_low"] > -margin
        out["disjoint_from_own_null"] = (
            out["improvement_ci90_low"] > margin or out["improvement_ci90_high"] < -margin
        )
    return out


def decision(person: dict, wer: dict) -> dict:
    """Section 6's rule, applied exactly as written."""

    lb_person = person["improvement_ci90_low"]
    ub_person = person["improvement_ci90_high"]
    lb_wer = wer["improvement_ci90_low"]
    ub_wer = wer["improvement_ci90_high"]

    win = lb_person > 0 and lb_wer > 0
    win_entity_only = lb_person > 0 and lb_wer > SECTION6_MARGIN
    harm = ub_person < 0 or ub_wer < SECTION6_MARGIN
    no_effect = (
        not win
        and not win_entity_only
        and lb_person <= 0 <= ub_person
        and lb_wer <= 0 <= ub_wer
    )
    if win:
        verdict, label = "WIN", "ADMITTED"
    elif win_entity_only:
        verdict, label = "WIN (entity-only)", "ADMITTED"
    elif harm:
        verdict, label = "HARM", "REJECTED"
    elif no_effect:
        verdict, label = "NO EFFECT", "NULL"
    else:
        verdict, label = "NO EFFECT (rule falls through)", "NULL"
    return {
        "rule_source": "section 6 of the preregistration, unchanged",
        "non_inferiority_margin_points": SECTION6_MARGIN,
        "delta_person_ci90": [lb_person, ub_person],
        "delta_corpus_wer_ci90": [lb_wer, ub_wer],
        "win": win,
        "win_entity_only": win_entity_only,
        "harm": harm,
        "no_effect": no_effect,
        "verdict": verdict,
        "label": label,
    }


def plan_call_features() -> dict[str, dict]:
    """Per-call unit-plan features, all fixed model-free before any score existed."""

    plan = load_json(PLAN)
    out: dict[str, dict] = {}
    for block in plan["calls"]:
        units = block["units"]
        durations = [float(u["duration_seconds"]) for u in units]
        dominated = sum(
            1 for u in units if float(u["speaker_share"]) >= 0.60 and int(u["speaker_count"]) >= 1
        )
        silent = sum(1 for u in units if int(u["speaker_count"]) == 0)
        shared = len(units) - dominated - silent
        out[str(block["sample_id"])] = {
            "units": len(units),
            "cut_seconds": round(sum(durations), 6),
            "delivered_seconds": round(sum(durations) + 2.0 * len(units), 6),
            "unit_seconds_mean": round(statistics.fmean(durations), 4),
            "unit_seconds_median": round(statistics.median(durations), 4),
            "unit_seconds_min": round(min(durations), 4),
            "unit_seconds_max": round(max(durations), 4),
            "dominated_units": dominated,
            "shared_units": shared,
            "silent_units": silent,
            "dominated_share": round(dominated / len(units), 4),
            "single_speaker_units": sum(1 for u in units if int(u["speaker_count"]) == 1),
            "pause_cuts": sum(1 for u in units if u["end_cut"] == "pause"),
            "turn_boundary_cuts": sum(1 for u in units if u["end_cut"] == "turn-boundary"),
            "forced_cap_split_cuts": sum(
                1 for u in units if u["end_cut"] == "forced-cap-split"
            ),
            "pause_cut_share": round(
                sum(1 for u in units if u["end_cut"] == "pause") / len(units), 4
            ),
            "units_under_1s": sum(1 for u in units if float(u["duration_seconds"]) < 1.0),
            "units_10_to_60s": sum(
                1 for u in units if 10.0 <= float(u["duration_seconds"]) < 60.0
            ),
            "units_over_60s": sum(1 for u in units if float(u["duration_seconds"]) >= 60.0),
            "units_no_reference_word": sum(
                1
                for u in units
                if int(u["reference_word_range"][1]) - int(u["reference_word_range"][0]) == 0
            ),
            "windows": int(block["windows"]),
        }
    return out


def tertiles(values: dict[str, float]) -> dict[str, str]:
    """Split 44 calls into LOW / MID / HIGH tertiles of a plan-derived feature.
    The feature and the cut points are model-free by construction (the plan was
    fixed before any score existed), so this is a report, never a knob."""

    ordered = sorted(values.items(), key=lambda item: item[1])
    n = len(ordered)
    labels: dict[str, str] = {}
    for position, (sample_id, _value) in enumerate(ordered):
        if position < n // 3:
            labels[sample_id] = "LOW"
        elif position < (2 * n) // 3:
            labels[sample_id] = "MID"
        else:
            labels[sample_id] = "HIGH"
    return labels


def stratum_table(
    comparator: dict[str, dict],
    cell: dict[str, dict],
    ids,
    labels: dict[str, str],
    names: list[str],
) -> list[dict]:
    rows: list[dict] = []
    for label in sorted({labels[i] for i in ids}):
        subset = [i for i in ids if labels[i] == label]
        row: dict = {"stratum": label, "calls": len(subset)}
        for name in names:
            numerator, denominator, lower, scale = METRICS[name]
            comp = t2.pooled(comparator, subset, numerator, denominator, scale)
            this = t2.pooled(cell, subset, numerator, denominator, scale)
            improvement = (comp - this) if lower else (this - comp)
            block = (
                interval(cell, comparator, subset, METRICS[name])
                if lower
                else interval(comparator, cell, subset, METRICS[name])
            )
            row[name] = {
                "comparator_natural": comp,
                "cell_natural": this,
                "improvement_natural": improvement,
                "improvement_ci90": [block["ci_low"], block["ci_high"]],
                "comparator_equal_stratum": t2.equal_stratum(
                    comparator, subset, numerator, denominator, scale
                ),
                "cell_equal_stratum": t2.equal_stratum(
                    cell, subset, numerator, denominator, scale
                ),
            }
        rows.append(row)
    return rows


def unit_grain_table(unit_rows: dict[str, dict], plan_units: dict[str, dict]) -> dict:
    """The cell's OWN per-unit error decomposition on section 4's unit-grain
    strata. There is no comparator counterpart -- the comparator has no units --
    so this is a distribution, never a contrast, and it is labelled as one."""

    def bucket_length(seconds: float) -> str:
        if seconds < 1.0:
            return "<1s"
        if seconds < 10.0:
            return "1-10s"
        if seconds < 60.0:
            return "10-60s"
        return ">=60s"

    strata: dict[str, dict[str, list[str]]] = {
        "dominance": {},
        "speaker_count": {},
        "unit_length": {},
        "cut_kind": {},
        "reference_word_presence": {},
    }
    for unit_id, unit in plan_units.items():
        if unit_id not in unit_rows:
            continue
        share = float(unit["speaker_share"])
        count = int(unit["speaker_count"])
        if count == 0:
            dominance = "silent"
        elif share >= 0.60:
            dominance = "dominated"
        else:
            dominance = "shared"
        strata["dominance"].setdefault(dominance, []).append(unit_id)
        strata["speaker_count"].setdefault(
            "speakers=0" if count == 0 else ("speakers>=3" if count >= 3 else f"speakers={count}"),
            [],
        ).append(unit_id)
        strata["unit_length"].setdefault(
            bucket_length(float(unit["duration_seconds"])), []
        ).append(unit_id)
        strata["cut_kind"].setdefault(str(unit["end_cut"]), []).append(unit_id)
        words = int(unit["reference_word_range"][1]) - int(unit["reference_word_range"][0])
        strata["reference_word_presence"].setdefault(
            "no-reference-word" if words == 0 else "has-reference-word", []
        ).append(unit_id)

    out: dict[str, list[dict]] = {}
    for stratum, groups in strata.items():
        table = []
        for label in sorted(groups):
            members = groups[label]
            errors = sum(unit_rows[u]["__wer_errors"] for u in members)
            words = sum(unit_rows[u]["reference_words"] for u in members)
            per_unit = [
                100.0 * unit_rows[u]["__wer_errors"] / unit_rows[u]["reference_words"]
                for u in members
                if unit_rows[u]["reference_words"]
            ]
            table.append(
                {
                    "stratum": label,
                    "units": len(members),
                    "reference_words": words,
                    "errors": errors,
                    "wer_percent_natural_mixture": (100.0 * errors / words) if words else None,
                    "wer_percent_equal_stratum": (
                        round(statistics.fmean(per_unit), 4) if per_unit else None
                    ),
                }
            )
        out[stratum] = table
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-read", type=Path, required=True)
    parser.add_argument("--cell-attempt", type=Path, required=True)
    parser.add_argument("--falsifier", type=Path, required=True)
    parser.add_argument("--unit-rows", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    comparator = call_rows(load_json(t2.AGENTIC_BASELINE))
    t2.attach_sealed_semantic(comparator)
    comparator = {k: t2.derived(v) for k, v in comparator.items()}
    cell = {k: t2.derived(v) for k, v in call_rows(load_json(args.score_read)).items()}

    ids = sorted(set(comparator) & set(cell))
    if len(ids) != 44 or set(ids) != set(comparator) or set(ids) != set(cell):
        raise SystemExit(
            f"roster mismatch: {len(ids)} paired of {len(comparator)} comparator and "
            f"{len(cell)} cell calls"
        )

    # ---- identity anchor: the comparator must reproduce its sealed numbers.
    anchors = {}
    for name, expected in (
        ("corpus_wer_percent", t2.SEALED_ANCHORS["corpus_wer_percent"]),
        ("conec_overall_wer_percent", t2.SEALED_ANCHORS["conec_overall_wer_percent"]),
        ("conec_non_entity_wer_percent", t2.SEALED_ANCHORS["conec_non_entity_wer_percent"]),
        (
            "numeric_value_accuracy_percent",
            t2.SEALED_ANCHORS["numeric_value_accuracy_percent"],
        ),
        (
            "semantic_high_impact_error_rate_percent",
            t2.SEALED_ANCHORS["semantic_high_impact_error_rate_percent"],
        ),
    ):
        numerator, denominator, _lower, scale = METRICS[name]
        actual = t2.pooled(comparator, ids, numerator, denominator, scale)
        anchors[name] = {
            "sealed": expected,
            "recomputed": actual,
            "agrees": abs(actual - expected) <= 5e-4,
        }
    person_numerator, person_denominator, _l, person_scale = METRICS["conec_person_wer_percent"]
    anchors["conec_person_wer_percent"] = {
        "sealed": 22.5,
        "recomputed": t2.pooled(
            comparator, ids, person_numerator, person_denominator, person_scale
        ),
        "agrees": abs(
            t2.pooled(comparator, ids, person_numerator, person_denominator, person_scale)
            - 22.48886
        )
        <= 5e-4,
    }
    anchor_ok = all(block["agrees"] for block in anchors.values())

    # ---- primary metrics
    metrics = {name: metric_block(comparator, cell, ids, name) for name in METRICS}
    verdict = decision(metrics["conec_person_wer_percent"], metrics["corpus_wer_percent"])

    # ---- the first table: contacts and delivered audio per arm
    falsifier = load_json(args.falsifier)
    features = plan_call_features()
    manifest = load_json(
        args.cell_attempt / f"{RUN_ID}.run-manifest.json"
    )
    cost = manifest.get("cost") or {}
    contact_table = {
        "comparator": {
            "run_id": COMPARATOR_RUN,
            "attempt_id": COMPARATOR_ATTEMPT,
            "transport_unit": "fixed 90-second window",
            "contacts": COMPARATOR_CONTACTS,
            "cut_audio_seconds": COMPARATOR_CUT_SECONDS,
            "delivered_audio_seconds": COMPARATOR_DELIVERED_SECONDS,
            "mean_unit_seconds": round(COMPARATOR_CUT_SECONDS / COMPARATOR_CONTACTS, 4),
            "gpu_hours": COMPARATOR_GPU_HOURS,
        },
        "cell": {
            "run_id": RUN_ID,
            "attempt_id": manifest.get("attempt_id"),
            "transport_unit": "speaker-turn unit (v2 plan)",
            "contacts": falsifier["units"],
            "cut_audio_seconds": falsifier["cut_seconds"],
            "delivered_audio_seconds": falsifier["delivered_seconds"],
            "mean_unit_seconds": round(
                falsifier["cut_seconds"] / falsifier["units"], 4
            ),
            "gpu_hours": cost.get("gpu_hours"),
        },
        "equal_contact_statement": (
            "A contact-matched control is IMPOSSIBLE BY CONSTRUCTION and was declared so "
            "before the flight (section 5): a call cut at its speaker turns yields 5,122 "
            "pieces and there is no way to cut it into speaker-turn units AND into 1,593 "
            "of them. The contrast is the TRANSPORT UNIT AS A WHOLE and it confounds "
            "boundary placement (11.0 % of unit cuts land mid-speech against 65.5 % of "
            "window cuts), speaker purity (76.1 % single-speaker units against 40.5 %) "
            "and contact count/length (5,122 x 27.60 s against 1,593 x 88.73 s). The "
            "control that WOULD separate contact count -- a fixed-window arm at "
            "obs_buffer_seconds 27.60, OBS-E1b -- is named as the follow-up and is "
            "deliberately not registered."
        ),
    }

    # ---- per-call table
    per_call = []
    for sample_id in ids:
        row = {"sample_id": sample_id}
        row.update(features[sample_id])
        for name, spec in METRICS.items():
            numerator, denominator, lower, scale = spec
            comp_den = comparator[sample_id][denominator]
            cell_den = cell[sample_id][denominator]
            comp_value = (
                scale * comparator[sample_id][numerator] / comp_den if comp_den else None
            )
            cell_value = scale * cell[sample_id][numerator] / cell_den if cell_den else None
            if comp_value is None or cell_value is None:
                row[name] = {
                    "comparator": comp_value,
                    "cell": cell_value,
                    "improvement": None,
                    "reference_words": comp_den,
                }
                continue
            row[name] = {
                "comparator": comp_value,
                "cell": cell_value,
                "improvement": (comp_value - cell_value) if lower else (cell_value - comp_value),
                "reference_words": comp_den,
            }
        per_call.append(row)

    # ---- strata (paired, at the paired grain)
    roster = {str(c["sample_id"]): c for c in load_json(ROSTER)["calls"]}
    headline = ["corpus_wer_percent", "conec_person_wer_percent", "conec_org_wer_percent"]
    strata: dict = {}
    strata["sector"] = stratum_table(
        comparator, cell, ids, {i: str(roster[i]["sector"]) for i in ids}, headline
    )
    strata["sample_rate_hz"] = stratum_table(
        comparator, cell, ids, {i: str(roster[i]["sample_rate_hz"]) for i in ids}, headline
    )
    strata["dominated_share_tertile"] = stratum_table(
        comparator,
        cell,
        ids,
        tertiles({i: features[i]["dominated_share"] for i in ids}),
        headline,
    )
    strata["mean_unit_seconds_tertile"] = stratum_table(
        comparator,
        cell,
        ids,
        tertiles({i: features[i]["unit_seconds_mean"] for i in ids}),
        headline,
    )
    strata["pause_cut_share_tertile"] = stratum_table(
        comparator,
        cell,
        ids,
        tertiles({i: features[i]["pause_cut_share"] for i in ids}),
        headline,
    )
    strata["units_per_call_tertile"] = stratum_table(
        comparator, cell, ids, tertiles({i: float(features[i]["units"]) for i in ids}), headline
    )

    # ---- the no-pause call, apart
    no_pause = {
        "sample_id": NO_PAUSE_CALL,
        "why_apart": (
            "zero detected pauses of 300 ms or more over 1,817.7 s; every one of its "
            "units ends on an active frame, so it is the one call where the transport "
            "unit cannot buy a silent boundary"
        ),
        "features": features[NO_PAUSE_CALL],
        "metrics": {
            name: {
                "comparator": row[name]["comparator"],
                "cell": row[name]["cell"],
                "improvement": row[name]["improvement"],
            }
            for row in per_call
            if row["sample_id"] == NO_PAUSE_CALL
            for name in METRICS
        },
        "never_pooled_away": True,
    }

    # ---- saves / harms / ties at the CALL grain (the paired grain)
    def saves_harms(name: str) -> dict:
        wins = losses = ties = 0
        for row in per_call:
            value = row[name]["improvement"]
            if value is None:
                continue
            if value > 1e-12:
                wins += 1
            elif value < -1e-12:
                losses += 1
            else:
                ties += 1
        return {"saves": wins, "harms": losses, "ties": ties, "n": wins + losses + ties}

    document = {
        "schema": "saea-e21-obs-e1-verdict-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID,
        "exposure_row": RUN_ID,
        "preregistration": (
            "docs/readiness/2026-09-07-e21-obs-speaker-turn-units-v1-preregistration.md"
        ),
        "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT},
        "identity_anchor": {"anchors": anchors, "result": "PASS" if anchor_ok else "FAIL"},
        "falsifier": {
            "result": falsifier["result"],
            "calls": falsifier["calls"],
            "units": falsifier["units"],
            "failures": falsifier["failures"][:20],
        },
        "pairing": {
            "unit": "the CALL",
            "clusters": len(ids),
            "seed": t2.SEED,
            "replicates": t2.REPLICATES,
            "ci_level": t2.CI_LEVEL,
            "power_limitation": (
                "n = 44 clusters is BELOW the program's n >= 400 rule for a paired "
                "effectiveness claim. This cell reports an interval and a direction and "
                "makes NO paper-facing effectiveness claim."
            ),
        },
        "contacts_and_audio": contact_table,
        "metrics": metrics,
        "decision": verdict,
        "own_null_margins": {
            "source": "SAEA-E21-FULL44-NULL-REPLICATE-V1",
            "note": (
                "the per-metric Earnings-21 non-inferiority margin is the half-width of "
                "that cell's own call-clustered CI90; the semantic one is ADVISORY "
                "because that null's interval excludes zero"
            ),
            "half_widths": OWN_NULL_HALF_WIDTH,
            "advisory": sorted(ADVISORY_MARGINS),
        },
        "saves_harms_ties_by_call": {
            name: saves_harms(name)
            for name in ("corpus_wer_percent", "conec_person_wer_percent", "conec_org_wer_percent")
        },
        "per_call": per_call,
        "strata": strata,
        "no_pause_call": no_pause,
        "plan_properties": {
            "units_under_1s": sum(features[i]["units_under_1s"] for i in ids),
            "units_no_reference_word": sum(features[i]["units_no_reference_word"] for i in ids),
            "units": sum(features[i]["units"] for i in ids),
        },
        "claim_surface": (
            "Discovery data. No superiority, generality, published-comparison or Stage-3 "
            "claim, and no paper-facing effectiveness claim at all. No knob tuned on the "
            "evaluation ten: the plan's rules were fixed model-free before any score "
            "existed. No Earnings-22 contact, no fstalign install, no diarizer re-run, no "
            "speaker naming, no OBS-E1b contact-matched control."
        ),
    }

    if args.unit_rows and Path(args.unit_rows).is_file():
        unit_rows = load_json(args.unit_rows)
        plan_units = {
            str(u["unit_id"]): u
            for block in load_json(PLAN)["calls"]
            for u in block["units"]
        }
        # window_rows keys units by "<call>#w<NNNN>"; the plan keys them "#u<NNNN>".
        renamed = {
            key.replace("#w", "#u"): value for key, value in unit_rows.items()
        }
        document["unit_grain_distribution"] = unit_grain_table(renamed, plan_units)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "result-summary.json"
    target.write_text(
        json.dumps(document, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("wrote", target)
    print(
        json.dumps(
            {
                "identity_anchor": document["identity_anchor"]["result"],
                "falsifier": document["falsifier"]["result"],
                "verdict": verdict["verdict"],
                "label": verdict["label"],
                "corpus_wer": {
                    k: metrics["corpus_wer_percent"][k]
                    for k in (
                        "comparator",
                        "cell",
                        "improvement_point",
                        "improvement_ci90_low",
                        "improvement_ci90_high",
                    )
                },
                "person": {
                    k: metrics["conec_person_wer_percent"][k]
                    for k in (
                        "comparator",
                        "cell",
                        "improvement_point",
                        "improvement_ci90_low",
                        "improvement_ci90_high",
                    )
                },
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
