#!/usr/bin/env python
"""The CELL-2 four-row OFFLINE dry run: what each node is supplied at store version 2.

Model-free by construction: zero model, tool, network, GPU, gate, transport, client,
attempt and serving-session contacts. The REAL registered smoke cell is composed from
the committed fragments over the REAL released version-2 stores and walked node by node
by ``speech_aware_evidence_acquisition.analysis.native_episode_dry_run``; only the four
role answers are canned, exactly as a fake frozen core would answer.

Three walks, all four rows:

1. the ACCEPT path on the Perception candidate ids the flight itself produced (read off
   the retired CELL-1 v2 smoke attempt's own trace, ids only) -- the walk that catches an
   inert node slice, which is what version 2's retention makes worth measuring: 10 of 14
   Planner values and 55 of 95 Reviewer values are retired;
2. a REVISE verdict on row 1, which revisits the Solver, the Reviewer and the Planner and
   must acquire nothing the second time;
3. a DUPLICATE-candidate Perception answer (n=3, distinct=1 -- the shape that aborted the
   CELL-1 arm after 304 metered contacts) on row 1, which must walk instead of raising.

The exit status is structural: every row walks the whole graph and delivers, a REVISE revisit
acquires nothing it already holds, and the duplicate row walks. The per-node counts it prints
are the registered structural rule for the smoke -- the flight's realised counts must equal
them -- and a node that selects nothing on these four rows is reported, not failed: four rows
cannot decide whether a candidate-bound route is inert, and the Perception route is seeded
before the walk rather than supplied at a node boundary.

Each walk group composes its OWN runtime: the plan's slot-contracts candidate route audits
its selection per (phase, sample, query state) and refuses a selection that changed within
one query, which is exactly what a second walk of the same row with different candidates
would look like to it.

Usage (from a worktree, in WSL):

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src SPEECHRL_DATA_DIR=... \
    python -B scripts/flights/batch/cell2_dry_run.py \
      --repo-root $REPO --data-root $DATA --lock-path $LOCK [--cell <smoke cell>]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SMOKE_EXPERIMENT = "slurp-native-stage3-delta-cell-r02-smoke-4-v1"
SMOKE_CELL = "slurp-native-stage3-delta-cell-r02-smoke-4-v1"
TWIN_SMOKE_CELL = "slurp-native-stage3-delta-cell-r02-smoke-4-twin-v1"
DELTA_STORE = "stage3-deltas"

#: The Perception candidate ids the flight itself produced on these four rows, read off
#: the retired CELL-1 v2 smoke attempt's own trace (MODEL_RESPONSE records, ids only).
TRACE_CANDIDATES = {
    "slurp:train:000007:audio--1504197557": ("audio_volume_up", "audio_volume_mute", "play_audiobook"),
    "slurp:train:000009:audio-1497557594-headset": ("iot_hue_lightchange", "iot_hue_lightup", "iot_hue_lighton"),
    "slurp:train:000015:audio-1488524781": ("audio_volume_up", "play_radio", "audio_volume_mute"),
    "slurp:train:000023:audio-1490956038": ("iot_hue_lightdim", "iot_hue_lighton", "iot_hue_lightoff"),
}


def _answers_for(candidates, *, revise_on_first_visit=False):
    perception = json.dumps(
        {"candidates": [{"intent_id": intent, "distinction": "Dry-run canned alternative.",
                         "evidence_refs": [], "unresolved_fields": []} for intent in candidates]},
        separators=(",", ":"),
    )

    def answer(role: str, visit: int) -> str:
        if role == "perception":
            return perception
        if role == "solver":
            return "intent: %s\nentities: none" % candidates[0]
        if role == "reviewer":
            return "The draft names one legal intent and no unsupported entity."
        if role == "planner":
            return "REVISE" if (revise_on_first_visit and visit == 1) else "ACCEPT"
        raise AssertionError("unexpected role %r" % role)

    return answer


def _deltas(value_ids):
    return [item for item in value_ids if item.startswith("%s::" % DELTA_STORE)]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--runtime-root", default=str(Path.home()))
    parser.add_argument("--cell", default=SMOKE_CELL,
                        help="the smoke cell to walk (the twin smoke is %s)" % TWIN_SMOKE_CELL)
    parser.add_argument("--experiment", default=SMOKE_EXPERIMENT,
                        help="the experiment fragment the cell is declared in; a CELL-1 smoke "
                             "fragment makes this driver the version-1r CONTROL of the same walk")
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
        NATIVE_ROLE_GRAPH_ORDER, compose_dry_run, dry_run_native_episode,
    )
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime

    repo_root = Path(args.repo_root)
    experiment = args.experiment
    fragment = json.loads((repo_root / "configs" / "experiment" /
                           ("%s.json" % experiment)).read_text(encoding="utf-8"))
    cell = next(item for item in fragment["cells"] if item["cell_id"] == args.cell)

    def compose():
        runtime = build_flight_runtime(
            repo_root, Path(args.data_root), model=cell["model_fragment"],
            dataset=cell["dataset_fragment"], baseline=cell["baseline_fragment"],
            experiment=experiment, run_id=cell["run_id"], attempt_id=cell["attempt_id"],
            runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
            campaign_active=False,
        )
        return runtime, compose_dry_run(runtime, sample_limit=4)

    baseline = json.loads((repo_root / "configs" / "baseline" /
                           ("%s.json" % cell["baseline_fragment"])).read_text(encoding="utf-8"))
    pins = baseline["knowledge_stores"][DELTA_STORE]
    report = {"cell": args.cell, "experiment": experiment,
              "store_pins": {"release": pins["release"], "snapshot": pins["snapshot"]},
              "accept_walk": {}, "revise_walk": {}, "duplicate_walk": {}}

    ok = True
    runtime, binding = compose()
    report["roster"] = [item.sample_id for item in runtime._samples]
    for sample_id, candidates in TRACE_CANDIDATES.items():
        result = dry_run_native_episode(runtime, answers=_answers_for(candidates),
                                        sample_id=sample_id, sample_limit=4)
        walked = tuple(node.phase for node in result.nodes)
        if walked != NATIVE_ROLE_GRAPH_ORDER:
            ok = False
        report["accept_walk"][sample_id] = {
            "candidates": list(candidates),
            "walked": list(walked),
            "delivered_phase": result.delivered_phase,
            "supplied": {node.phase: len(_deltas(node.supplied_value_ids)) for node in result.nodes},
            "supplied_value_ids": {node.phase: _deltas(node.supplied_value_ids)
                                   for node in result.nodes},
        }
    router = binding["phase_binding"].get("supply_for_store")
    audits = (getattr(router, "receipt", {}) or {}).get("delta_supply", {}) if router else {}
    report["declined_routes"] = sorted(
        "%s:%s" % (entry["phase"], entry["sample_id"])
        for entry in audits.values() if entry.get("selected") == 0
    )

    row1, cands1 = next(iter(TRACE_CANDIDATES.items()))
    runtime, _binding = compose()
    revise = dry_run_native_episode(
        runtime, answers=_answers_for(cands1, revise_on_first_visit=True), sample_id=row1,
        sample_limit=4, node_order=NATIVE_ROLE_GRAPH_ORDER + ("solver", "reviewer", "planner"))
    report["revise_walk"] = {
        "sample_id": row1,
        "walked": [[node.phase, node.visit] for node in revise.nodes],
        "supplied": {"%s#%d" % (node.phase, node.visit): len(_deltas(node.supplied_value_ids))
                     for node in revise.nodes},
    }
    if any(_deltas(node.supplied_value_ids) for node in revise.nodes[4:]):
        ok = False
        report["revise_walk"]["defect"] = "a second visit acquired a value the episode already held"

    duplicate = (cands1[0], cands1[0], cands1[0])
    runtime, binding = compose()
    dup = dry_run_native_episode(runtime, answers=_answers_for(duplicate), sample_id=row1,
                                 sample_limit=4)
    report["duplicate_walk"] = {
        "sample_id": row1, "candidates": list(duplicate),
        "walked": [node.phase for node in dup.nodes],
        "supplied": {node.phase: len(_deltas(node.supplied_value_ids)) for node in dup.nodes},
    }
    if tuple(node.phase for node in dup.nodes) != NATIVE_ROLE_GRAPH_ORDER:
        ok = False
    router = binding["phase_binding"].get("supply_for_store")
    projections = (getattr(router, "receipt", {}) or {}).get("delta_candidate_projection", {}) if router else {}
    report["duplicate_walk"]["candidate_projections_recorded"] = len(projections)

    per_node = {phase: 0 for phase in NATIVE_ROLE_GRAPH_ORDER}
    rows_supplied = {phase: 0 for phase in NATIVE_ROLE_GRAPH_ORDER}
    for walk in report["accept_walk"].values():
        for phase, count in walk["supplied"].items():
            per_node[phase] += count
            rows_supplied[phase] += 1 if count else 0
    report["totals"] = {"items_per_node": per_node, "rows_supplied_per_node": rows_supplied}
    # INFORMATION, never the verdict: four rows cannot decide whether a candidate-bound
    # route is inert -- the 1,080-row arm's own delta-consumption table decides that -- and
    # the Perception route is SEEDED before the walk, so it is never a node supply step here.
    report["zero_on_this_roster"] = sorted(
        phase for phase, count in per_node.items()
        if count == 0 and phase != "perception"
    )
    report["what_the_verdict_is"] = (
        "ok means: every row walked the whole graph and delivered, the REVISE revisit "
        "acquired nothing it already held, and the duplicate-candidate row walked instead "
        "of raising. The per-node counts are the registered structural rule for the smoke: "
        "the flight's realised counts must EQUAL them."
    )
    report["ok"] = ok
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
