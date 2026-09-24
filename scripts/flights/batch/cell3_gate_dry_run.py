#!/usr/bin/env python
"""The ITERATION-3 four-row OFFLINE dry run: which nodes the scenario gate withholds.

Model-free by construction: zero model, tool, network, GPU, gate, transport, client,
attempt and serving-session contacts. The REAL derived gated baseline fragment is
composed over the REAL released version-2 stores and walked node by node by
``speech_aware_evidence_acquisition.analysis.native_episode_dry_run``; only the four
role answers are canned, exactly as a fake frozen core would answer.

It is ``scripts/flights/batch/cell2_dry_run.py``'s recipe, on the same four rows -- the
CELL-2 smoke population is "the first four rows of TRAIN Fold A in the roster's own
order", so this driver walks the CELL-2 cell truncated to four rows with the baseline
fragment swapped for the gated one, and imports that driver's own traced candidate ids
and canned answers rather than restating them.

Three walks, every one of them a decision the gate has to get right:

1. the TRACED walk, all four rows, on the Perception candidate ids the flight itself
   produced. Rows 1 and 3 have majority scenario ``audio`` (not gated) and rows 2 and 4
   have ``iot`` (gated), so one roster shows both outcomes;
2. the TIE walk on row 1, two candidates from two different scenarios, the gated one
   second -- the first-listed tie-break must leave the gate OPEN;
3. the same tie REVERSED, the gated scenario first -- the gate must CLOSE.

The exit status is structural: every row walks the whole graph and delivers, every
node that the gate closed supplied nothing, every node the gate left open supplied
exactly what the ungated route would have, and the two tie walks disagree. No claim
about effectiveness is made or possible here: this is a wiring proof.

Usage (from a worktree, in WSL):

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src SPEECHRL_DATA_DIR=... \
    python -B scripts/flights/batch/cell3_gate_dry_run.py \
      --repo-root $REPO --data-root $DATA --lock-path $LOCK
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cell2_dry_run import TRACE_CANDIDATES, _answers_for, _deltas  # noqa: E402

#: The CELL-2 cell itself, truncated to four rows -- NOT the smoke cell, whose baseline
#: carries its own speech-feature identity ids. The gated fragment is derived from the
#: CELL-2 baseline, so this is the composition it belongs to, and the CELL-2 experiment's
#: first four rows ARE the smoke population (that experiment's own population note).
EXPERIMENT = "slurp-native-stage3-delta-cell-r02-v1"
CELL = "slurp-native-stage3-delta-cell-r02-v1"
GATED_BASELINE = "slurp-native-stage3-delta-cell-r03-gate-baseline-v1"
DELTA_STORE = "stage3-deltas"
ROWS = 4


def _gate_table(result):
    return {
        item.node: {
            "majority_scenario": item.majority_scenario,
            "candidate_count": item.candidate_count,
            "closed": item.closed,
        }
        for item in result.scenario_gate_decisions
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--runtime-root", default=str(Path.home()))
    parser.add_argument("--experiment", default=EXPERIMENT)
    parser.add_argument("--cell", default=CELL)
    parser.add_argument("--baseline", default=GATED_BASELINE,
                        help="the baseline fragment to compose INSTEAD of the cell's own")
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
        NATIVE_ROLE_GRAPH_ORDER, compose_dry_run, dry_run_native_episode,
    )
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime

    repo_root = Path(args.repo_root)
    fragment = json.loads((repo_root / "configs" / "experiment" /
                           ("%s.json" % args.experiment)).read_text(encoding="utf-8"))
    cell = next(item for item in fragment["cells"] if item["cell_id"] == args.cell)

    def compose():
        runtime = build_flight_runtime(
            repo_root, Path(args.data_root), model=cell["model_fragment"],
            dataset=cell["dataset_fragment"], baseline=args.baseline,
            experiment=args.experiment, run_id=cell["run_id"], attempt_id=cell["attempt_id"],
            runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
            campaign_active=False,
        )
        return runtime, compose_dry_run(runtime, sample_limit=ROWS)

    baseline = json.loads((repo_root / "configs" / "baseline" /
                           ("%s.json" % args.baseline)).read_text(encoding="utf-8"))
    store = baseline["knowledge_stores"][DELTA_STORE]
    routes = store["context_supply"]
    report = {
        "experiment": args.experiment, "cell": args.cell, "baseline": args.baseline,
        "store_pins": {"release": store["release"], "snapshot": store["snapshot"]},
        "gated_routes": {
            node: spec.get("scenario_gate") for node, spec in sorted(routes.items())
        },
        "traced_walk": {}, "tie_walk": {}, "tie_reversed_walk": {},
    }

    ok = True
    runtime, binding = compose()
    report["roster"] = [item.sample_id for item in runtime._samples]
    if sorted(report["roster"]) != sorted(TRACE_CANDIDATES):
        ok = False
        report["roster_defect"] = (
            "the walked rows are not the four rows the traced candidate ids belong to"
        )
    for sample_id, candidates in TRACE_CANDIDATES.items():
        result = dry_run_native_episode(runtime, answers=_answers_for(candidates),
                                        sample_id=sample_id, sample_limit=ROWS)
        gates = _gate_table(result)
        supplied = {node.phase: len(_deltas(node.supplied_value_ids)) for node in result.nodes}
        if tuple(node.phase for node in result.nodes) != NATIVE_ROLE_GRAPH_ORDER:
            ok = False
        for node, decision in gates.items():
            # A closed gate must take NO supply step at that node.
            if decision["closed"] and supplied.get(node):
                ok = False
                report.setdefault("defects", []).append(
                    "%s:%s closed gate still supplied %d" % (sample_id, node, supplied[node])
                )
        report["traced_walk"][sample_id] = {
            "candidates": list(candidates),
            "majority_scenario": next(
                (item["majority_scenario"] for item in gates.values()), None
            ),
            "gates": gates,
            "supplied": supplied,
            "delivered_phase": result.delivered_phase,
        }

    row1, cands1 = next(iter(TRACE_CANDIDATES.items()))
    # A 1-1 tie between one gated and one ungated scenario. The first-listed
    # candidate decides, so the two orders must disagree.
    ungated_first = (cands1[0], "iot_hue_lighton")
    gated_first = ("iot_hue_lighton", cands1[0])
    for key, order in (("tie_walk", ungated_first), ("tie_reversed_walk", gated_first)):
        runtime, _binding = compose()
        result = dry_run_native_episode(runtime, answers=_answers_for(order),
                                        sample_id=row1, sample_limit=ROWS)
        report[key] = {
            "sample_id": row1, "candidates": list(order), "gates": _gate_table(result),
            "supplied": {
                node.phase: len(_deltas(node.supplied_value_ids)) for node in result.nodes
            },
        }
    tie_closed = {node: item["closed"] for node, item in report["tie_walk"]["gates"].items()}
    tie_rev_closed = {
        node: item["closed"] for node, item in report["tie_reversed_walk"]["gates"].items()
    }
    if not tie_closed or any(tie_closed.values()):
        ok = False
        report.setdefault("defects", []).append(
            "the ungated-first tie closed a gate; the first-listed tie-break is wrong"
        )
    if not tie_rev_closed or not all(tie_rev_closed.values()):
        ok = False
        report.setdefault("defects", []).append(
            "the gated-first tie left a gate open; the first-listed tie-break is wrong"
        )

    report["what_the_verdict_is"] = (
        "ok means: every row walked the whole graph and delivered, every node whose gate "
        "CLOSED supplied nothing at that node, and the two tie walks -- the same two "
        "candidates in the two orders -- disagreed, which is the first-listed tie-break "
        "doing its job. It says NOTHING about whether gating helps; that is a flight."
    )
    report["ok"] = ok
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
