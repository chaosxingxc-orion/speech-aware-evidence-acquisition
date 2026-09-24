#!/usr/bin/env python
"""The CELL-3 four-row OFFLINE dry run on DEV-2000-ADDED: what the gate withholds.

Model-free by construction: zero model, tool, network, GPU, gate, transport, client,
attempt and serving-session contacts. The REAL registered smoke cells are composed from
the committed fragments over the REAL released version-2 stores and walked node by node
by ``speech_aware_evidence_acquisition.analysis.native_episode_dry_run``; only the four
role answers are canned, exactly as a fake frozen core would answer.

It is ``scripts/flights/batch/cell3_gate_dry_run.py``'s recipe moved to this cell's own
venue: that driver walks the TRAIN Fold A CELL-2 cell with the gated fragment swapped
in, this one walks the two REGISTERED DEV-2000-ADDED smoke cells (arm and twin) on the
four rows the package selected. Its gate table helper and ``cell2_dry_run``'s canned
answers and delta filter are IMPORTED rather than restated.

Three walks per form, every one of them a decision the gate has to get right:

1. the TRACED walk, all four rows, on the Perception candidate ids the SEALED comparator
   itself produced (``SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1``; labels only, no
   utterance text, no gold). Rows 1 and 2 have majority scenario ``iot`` (gated) and rows
   3 and 4 have ``weather`` (not gated), so one roster shows both outcomes;
2. the TIE walk on row 3, two candidates from two different scenarios with the ungated one
   first -- the first-listed tie-break must leave the gate OPEN;
3. the same tie REVERSED, the gated scenario first -- the gate must CLOSE.

The exit status is structural: every row walks the whole graph and delivers, every node
the gate closed supplied nothing, the gate published one decision per candidate-bound
node per row, and the two tie walks disagree. Byte-identity of an OPEN gate against the
ungated route is not re-proved here -- it is the unit test
``tests/unit/test_stage3_scenario_gate.py::test_an_open_gate_is_byte_identical_to_the_ungated_route``.
No claim about effectiveness is made or possible here: this is a wiring proof.

Usage (from a worktree, in WSL):

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src SPEECHRL_DATA_DIR=... \
    python -B scripts/flights/batch/cell3_dry_run.py \
      --repo-root $REPO --data-root $DATA --lock-path $LOCK [--cell <twin smoke cell>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cell2_dry_run import _answers_for, _deltas  # noqa: E402
from cell3_gate_dry_run import _gate_table  # noqa: E402

EXPERIMENT = "slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1"
SMOKE_CELL = "slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1"
TWIN_SMOKE_CELL = "slurp-native-stage3-delta-cell-r03-gate-smoke-4-twin-v1"
DELTA_STORE = "stage3-deltas"
ROWS = 4

#: The Perception candidate ids the SEALED DEV-2000-ADDED comparator itself produced on
#: these four rows, read off its own sealed ``phases.json`` agent states (intent ids only,
#: after the route's own bounded first-occurrence projection at max 3) and reduced by
#: ``rails.stage3_delta_supply.majority_candidate_scenario``. Labels only; no utterance
#: text, transcript, gold or distinction string is carried here.
TRACE_CANDIDATES = {
    "slurp:devel:000017:audio-1501773854-headset":
        ("iot_hue_lightdim", "iot_hue_lighton", "iot_hue_lightoff"),
    "slurp:devel:000024:audio-1490195864-headset":
        ("iot_hue_lightdim", "iot_hue_lighton", "iot_hue_lightchange"),
    "slurp:devel:000099:audio-1501754782":
        ("weather_query",),
    "slurp:devel:000217:audio-1490367363":
        ("weather_query", "transport_traffic", "datetime_query"),
}
#: The registered expectation, from the same sealed labels.
EXPECTED_MAJORITY = {
    "slurp:devel:000017:audio-1501773854-headset": ("iot", True),
    "slurp:devel:000024:audio-1490195864-headset": ("iot", True),
    "slurp:devel:000099:audio-1501754782": ("weather", False),
    "slurp:devel:000217:audio-1490367363": ("weather", False),
}
#: The row the two tie walks use, and the gated intent they tie an ungated one against.
TIE_ROW = "slurp:devel:000099:audio-1501754782"
TIE_UNGATED = "weather_query"
TIE_GATED = "iot_hue_lighton"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--runtime-root", default=str(Path.home()))
    parser.add_argument("--experiment", default=EXPERIMENT)
    parser.add_argument("--cell", default=SMOKE_CELL,
                        help="the smoke cell to walk (the twin smoke is %s)" % TWIN_SMOKE_CELL)
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
            dataset=cell["dataset_fragment"], baseline=cell["baseline_fragment"],
            experiment=args.experiment, run_id=cell["run_id"], attempt_id=cell["attempt_id"],
            runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
            campaign_active=False,
        )
        return runtime, compose_dry_run(runtime, sample_limit=ROWS)

    baseline = json.loads((repo_root / "configs" / "baseline" /
                           ("%s.json" % cell["baseline_fragment"])).read_text(encoding="utf-8"))
    store = baseline["knowledge_stores"][DELTA_STORE]
    routes = store["context_supply"]
    report = {
        "experiment": args.experiment, "cell": args.cell,
        "baseline": cell["baseline_fragment"],
        "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
        "store_pins": {"release": store["release"], "snapshot": store["snapshot"]},
        "gated_routes": {node: spec.get("scenario_gate") for node, spec in sorted(routes.items())},
        "traced_walk": {}, "tie_walk": {}, "tie_reversed_walk": {},
    }

    ok = True
    runtime, _binding = compose()
    report["roster"] = [item.sample_id for item in runtime._samples]
    if sorted(report["roster"]) != sorted(TRACE_CANDIDATES):
        ok = False
        report.setdefault("defects", []).append(
            "the walked rows are not the four rows the traced candidate ids belong to"
        )
    for sample_id, candidates in TRACE_CANDIDATES.items():
        result = dry_run_native_episode(runtime, answers=_answers_for(candidates),
                                        sample_id=sample_id, sample_limit=ROWS)
        gates = _gate_table(result)
        supplied = {node.phase: len(_deltas(node.supplied_value_ids)) for node in result.nodes}
        if tuple(node.phase for node in result.nodes) != NATIVE_ROLE_GRAPH_ORDER:
            ok = False
            report.setdefault("defects", []).append("%s did not walk the whole graph" % sample_id)
        expected_scenario, expected_closed = EXPECTED_MAJORITY[sample_id]
        for node, decision in gates.items():
            if decision["majority_scenario"] != expected_scenario:
                ok = False
                report.setdefault("defects", []).append(
                    "%s:%s majority %r, registered %r"
                    % (sample_id, node, decision["majority_scenario"], expected_scenario)
                )
            if decision["closed"] != expected_closed:
                ok = False
                report.setdefault("defects", []).append(
                    "%s:%s closed=%s, registered %s"
                    % (sample_id, node, decision["closed"], expected_closed)
                )
            if decision["closed"] and supplied.get(node):
                ok = False
                report.setdefault("defects", []).append(
                    "%s:%s closed gate still supplied %d" % (sample_id, node, supplied[node])
                )
        # One decision per candidate-bound node: the Perception route is REMOVED in this
        # cell, so the gate publishes exactly three decisions per row.
        if len(gates) != len([spec for spec in routes.values() if spec.get("scenario_gate")]):
            ok = False
            report.setdefault("defects", []).append(
                "%s published %d gate decisions, expected one per gated route"
                % (sample_id, len(gates))
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

    for key, order in (("tie_walk", (TIE_UNGATED, TIE_GATED)),
                       ("tie_reversed_walk", (TIE_GATED, TIE_UNGATED))):
        runtime, _binding = compose()
        result = dry_run_native_episode(runtime, answers=_answers_for(order),
                                        sample_id=TIE_ROW, sample_limit=ROWS)
        report[key] = {
            "sample_id": TIE_ROW, "candidates": list(order), "gates": _gate_table(result),
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

    per_node = {}
    rows_closed = {}
    for walk in report["traced_walk"].values():
        for phase, count in walk["supplied"].items():
            per_node[phase] = per_node.get(phase, 0) + count
        for node, decision in walk["gates"].items():
            rows_closed[node] = rows_closed.get(node, 0) + (1 if decision["closed"] else 0)
    report["totals"] = {"items_per_node": per_node, "rows_gate_closed_per_node": rows_closed}
    report["what_the_verdict_is"] = (
        "ok means: every row walked the whole graph and delivered, every node whose gate "
        "CLOSED supplied nothing at that node, every realised gate decision equalled the "
        "registered one, the gate published one decision per gated route per row, and the "
        "two tie walks -- the same two candidates in the two orders -- disagreed. It says "
        "NOTHING about whether gating helps; that is a flight."
    )
    report["ok"] = ok
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
