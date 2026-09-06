#!/usr/bin/env python3
"""Assemble ``result-summary.json`` from ``read.json`` beside it.

Reads nothing else: no corpus, no sealed bytes, no gold, no model. The single
registered read (``scripts/slurp_legal_label_projection_read.py``, copied here
as ``read.py``) already produced every number; this only selects the ones the
verdict quotes and shapes them into the machine-readable summary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = "saea-slurp-legal-label-projection-relock-result-summary-v1"

ARMS = ("CLOSED-LIST", "KU-S1C", "KU-S1C-DRAFT", "KC-S1A", "KC-S1B")
QUOTED_METRICS = ("scenario_action_exact", "action_exact", "slu_f1_f1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read", type=Path, default=HERE / "read.json")
    parser.add_argument("--out", type=Path, default=HERE / "result-summary.json")
    args = parser.parse_args()

    read = json.loads(args.read.read_text(encoding="utf-8"))
    lock = read["lock"]

    summary = {
        "schema": SCHEMA,
        "study": read["study"],
        "row_id": read["row_id"],
        "profile": "model-free-check",
        "contacts": {
            "model": 0,
            "gpu_hours": 0,
            "tool": 0,
            "embedding": 0,
            "network": 0,
            "paid_api_spend": 0,
        },
        "preregistration": (
            "docs/readiness/2026-09-06-slurp-legal-label-projection-relock-v1-preregistration.md"
        ),
        "verdict": (
            "RE-LOCKED. The closed-list direct baseline plus the legal-label projection "
            "slurp-legal-label-projection-v1 is the SLURP direct comparator: intent 71.60 "
            "(from 71.40), SLU-F1 35.80 unchanged, and 0.00 % impossible (scenario, action) "
            "pairs from 3.90 %. Every preregistered lock condition is met and no stratum is "
            "harmed on intent anywhere. The gain is protocol alignment, not accuracy: only 2 "
            "of the 39 legalised rows land on the gold intent, and the action column loses "
            "0.60 pp. The residual is named and priced -- 19 of the 39 rows put a legal "
            "ACTION name in the scenario slot, and promoting it back would have recovered 15 "
            "of them (about +1.5 pp intent), which is a SUCCESSOR rule and requires its own "
            "preregistration before it can be locked."
        ),
        "projection": read["projection"],
        "scorers": read["scorers"],
        "statistics": read["statistics"],
        "populations": read["populations"],
        "lock": lock,
        "official_table": {
            arm: {
                "unprojected": read["arms"][arm]["official_unprojected"],
                "projected": read["arms"][arm]["official_projected"],
                "projection": {
                    key: value
                    for key, value in read["arms"][arm]["projection"].items()
                    if key != "map"
                },
                "entity_side_invariant_holds": read["arms"][arm][
                    "entity_side_invariant_holds"
                ],
            }
            for arm in ARMS
        },
        "projection_map_closed_list": read["arms"]["CLOSED-LIST"]["projection"]["map"],
        "paired": {
            arm: {
                population: {
                    metric: read["arms"][arm]["paired"][population][metric]
                    for metric in QUOTED_METRICS
                }
                for population in ("pooled_1000", "old500", "new500")
            }
            for arm in ARMS
        },
        "weightings_intent_closed_list": read["arms"]["CLOSED-LIST"]["weightings_intent"],
        "impossible_pairs": read["impossible_pairs"],
        "residual_diagnostic": read["residual_swap_diagnostic"],
        "kc_s1b_fallback_rows": {
            key: value
            for key, value in read["kc_s1b_fallback_rows"].items()
            if key != "ids_made_legal"
        },
        "preregistered_properties": {
            key: value
            for key, value in read["preregistered_properties"].items()
            if key != "devel_gold_intent_rows_outside_the_train_pairs"
        },
        "identity_anchors": {
            arm: read["arms"][arm]["official_unprojected"]["identity_check_passed"]
            for arm in ARMS
        },
        "score_batch": read["score_batch"],
        "manifests": read["manifests"],
        "boundary": read["boundary"],
        "authorizes": (
            "the comparator identity every pending SLURP cell pairs against from now on, and "
            "nothing else: no admission, no promotion, no superiority claim, no "
            "generalization claim, no test contact, no Stage-3 activity. No published "
            "verdict is reopened, restated or re-scored."
        ),
    }
    args.out.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
