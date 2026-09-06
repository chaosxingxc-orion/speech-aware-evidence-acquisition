#!/usr/bin/env python3
"""Assemble ``result-summary.json`` from ``read.json`` beside it.

Reads nothing else: no corpus, no sealed bytes, no gold, no model. The single
registered read (``scripts/slurp_legal_label_projection_v2_read.py``, copied
here as ``read.py``) already produced every number; this only selects the ones
the verdict quotes and shapes them into the machine-readable summary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = "saea-slurp-legal-label-projection-v2-result-summary-v1"

ARMS = ("CLOSED-LIST", "KU-S1C", "KU-S1C-DRAFT", "KC-S1A", "KC-S1B")
VIEWS = ("unprojected", "v1", "v2")
CONTRASTS = ("v2_minus_v1", "v2_minus_unprojected", "v1_minus_unprojected")
POPULATIONS = ("pooled_1000", "old500", "new500")
QUOTED_METRICS = ("scenario_action_exact", "scenario_exact", "action_exact", "slu_f1_f1")

VERDICT = (
    "RE-LOCKED. The closed-list direct baseline plus the SUCCESSOR legal-label projection "
    "slurp-legal-label-projection-v2 is the SLURP direct comparator: intent 73.10 against "
    "v1's locked 71.60 and the unprojected 71.40, scenario 82.60 from 81.00, action 74.60 "
    "from v1's 73.30 and back above the unprojected 73.90, SLU-F1 35.80 and every other "
    "entity-side number unchanged to the last decimal on every arm, impossible "
    "(scenario, action) pairs 3.90 percent to 0.00 percent. Every preregistered lock "
    "condition is met in BOTH contrasts: intent +1.50 pp over the locked comparator "
    "(15 saves, 0 harms, CI90 [1.0, 2.1], p 6.1e-05) and +1.70 pp over the raw sealed "
    "labels (17 saves, 0 harms, CI90 [1.1, 2.3], p 1.5e-05), non-negative on OLD500 and "
    "NEW500 in both, and not one gold-scenario stratum harmed on intent anywhere in either. "
    "The promote branch is the entire difference: 19 of the 39 changed rows, 15 of them "
    "landing on the gold intent, against 2 of 39 for v1's edit distance. Two honest "
    "caveats: the whole intent gain is ONE stratum -- recommendation, 46.67 to 71.67 on 60 "
    "rows, with 17 of 18 strata flat against v1 -- and the multi-owner half of the "
    "tie-break never fires on this roster, so it is exercised only by unit tests. This is "
    "still a repair of the baseline's own output rather than a mechanism: the points belong "
    "to the comparator, and every pending SLURP cell now has to beat 73.10."
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read", type=Path, default=HERE / "read.json")
    parser.add_argument("--out", type=Path, default=HERE / "result-summary.json")
    args = parser.parse_args()

    read = json.loads(args.read.read_text(encoding="utf-8"))

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
            "docs/readiness/2026-09-06-slurp-legal-label-projection-v2-preregistration.md"
        ),
        "verdict": VERDICT,
        "projection": {
            key: value
            for key, value in read["projection"].items()
            if key != "actions_by_scenario"
        },
        "scorers": read["scorers"],
        "statistics": read["statistics"],
        "populations": read["populations"],
        "lock": read["lock"],
        "official_table": {
            arm: {
                "views": {view: read["arms"][arm]["official"][view] for view in VIEWS},
                "projection": {
                    view: {
                        key: value
                        for key, value in read["arms"][arm]["projection"][view].items()
                        if key not in ("map", "map_by_branch")
                    }
                    for view in ("v1", "v2")
                },
                "entity_side_invariant_holds": read["arms"][arm][
                    "entity_side_invariant_holds"
                ],
            }
            for arm in ARMS
        },
        "projection_map_closed_list": {
            view: {
                "map": read["arms"]["CLOSED-LIST"]["projection"][view]["map"],
                "map_by_branch": read["arms"]["CLOSED-LIST"]["projection"][view][
                    "map_by_branch"
                ],
            }
            for view in ("v1", "v2")
        },
        # The per-stratum table of every metric of every contrast lives in
        # ``read.json``; carrying all 3,240 of those blocks here would bury the
        # summary in its own detail, so only the CLOSED-LIST intent strata (the
        # ones the lock rule reads) are quoted below.
        "paired": {
            arm: {
                contrast: {
                    population: {
                        metric: {
                            key: value
                            for key, value in read["arms"][arm]["paired"][contrast][
                                population
                            ][metric].items()
                            if key != "per_stratum"
                        }
                        for metric in QUOTED_METRICS
                    }
                    for population in POPULATIONS
                }
                for contrast in CONTRASTS
            }
            for arm in ARMS
        },
        "per_stratum_intent_closed_list": {
            contrast: read["arms"]["CLOSED-LIST"]["paired"][contrast]["pooled_1000"][
                "scenario_action_exact"
            ]["per_stratum"]
            for contrast in CONTRASTS
        },
        "weightings_intent_closed_list": read["arms"]["CLOSED-LIST"]["weightings_intent"],
        "impossible_pairs": read["impossible_pairs"],
        "residual_after_v2": read["residual_after_v2"],
        "kc_s1b_fallback_rows": read["kc_s1b_fallback_rows"],
        "preregistered_properties": {
            key: value
            for key, value in read["preregistered_properties"].items()
            if key != "devel_gold_intent_rows_outside_the_train_pairs"
        },
        "published_identity_anchors": {
            arm: {view: block["matches"] for view, block in views.items()}
            for arm, views in read["published_identity_anchors"].items()
        },
        "identity_check_passed": {
            arm: {
                view: read["arms"][arm]["official"][view]["identity_check_passed"]
                for view in VIEWS
            }
            for arm in ARMS
        },
        "score_batch": read["score_batch"],
        "manifests": read["manifests"],
        "boundary": read["boundary"],
        "authorizes": (
            "the comparator identity every pending SLURP cell pairs against from now on, and "
            "nothing else: no admission, no promotion, no superiority claim, no "
            "generalization claim, no test contact, no Stage-3 activity. No published "
            "verdict is reopened, restated or re-scored, and v1 stays a registered, "
            "resolvable scorer."
        ),
    }
    args.out.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
