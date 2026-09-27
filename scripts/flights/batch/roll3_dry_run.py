#!/usr/bin/env python
"""The cell ROLL-3 four-row OFFLINE dry run: does the grouped form compose and walk on DEV-2000-ADDED?

Model-free by construction: zero model, tool, network, GPU, gate, transport, client, attempt and
serving-session contacts. The REAL registered smoke cell is composed from the committed fragments
and walked node by node by ``speech_aware_evidence_acquisition.analysis.native_episode_dry_run``;
only the four role answers are canned, exactly as a fake frozen core would answer.

Three proofs, in the order they can fail:

1. **FORM** -- the composed episode really is cell ROLL-2's grouped-Solver form (itself cell ROLL-1's), unchanged: policy
   ``phase-native-candidates-review-revise-samples5-v1`` with ``max_contacts`` 19, the loader's own
   bounded graph ceiling 19, Solver ``samples`` 5, no ``twin`` marker, ``decoding_overrides``
   ``{temperature: 0.7, seed_offset: 0}``, ``commit`` min_support 3 at similarity 0.8, and the
   four-node graph (perception 1 / solver 1 / reviewer 3 / planner 1, ``max_revisions`` 1, review
   loop on). ROLL-3 changes the ROSTER, never the form, so a disagreement here is the whole cell
   being wrong.
2. **IDENTITY** -- the five samples' composed request decoding params, built by the production
   ``reproduction.ojw.native_request.compose_solver_sample_decoding_params`` with the real
   ``rails.runner._solver_fragment_seed`` of this program, differ in EXACTLY one field, ``seed``,
   and every one carries ``temperature`` 0.7. That is what makes the five a sample GROUP of one
   request rather than five different requests, and it is what the sealed pool's later offline reads
   depend on.
3. **WALK** -- every one of the four smoke rows (the first four DEV-2000-ADDED rows by roster order)
   walks perception -> solver -> reviewer -> planner and delivers, with the knowledge supply
   resolved at every node boundary by the production router over the DEV-2000-ADDED artifacts. A refusal
   raised here -- a missing DEV-2000-ADDED vector line, an unresolvable packet, a store that does not open --
   is a refusal the flight would raise.

The exit status is structural: all three proofs must hold. The per-node supply counts are printed
as INFORMATION (four rows cannot decide whether a route is inert).

Usage (from a worktree, in WSL)::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src SPEECHRL_DATA_DIR=... \\
    python -B scripts/flights/batch/roll3_dry_run.py \\
      --repo-root $REPO --data-root $DATA --lock-path $LOCK
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SMOKE_EXPERIMENT = "slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1"
SMOKE_CELL = "slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1"

EXPECTED = {
    "policy": "phase-native-candidates-review-revise-samples5-v1",
    "program_max_contacts": 19,
    "graph_ceiling": 19,
    "solver_samples": 5,
    "solver_twin": None,
    "solver_temperature": 0.7,
    "solver_seed_offset": 0,
    "commit_policy": "saea-commit-plurality-support-v1",
    "commit_min_support": 3,
    "commit_similarity_threshold": 0.8,
    "max_revisions": 1,
    "review_loop": "on",
    "roles": {"perception": 1, "solver": 1, "reviewer": 3, "planner": 1},
}


#: One canned, schema-valid answer per role. The intent ids are read off the composed runtime's own
#: registered legal intent list, so nothing here invents a label.
def _answers_for(intents):
    perception = json.dumps(
        {"candidates": [{"intent_id": intent, "distinction": "Dry-run canned alternative.",
                         "evidence_refs": [], "unresolved_fields": []} for intent in intents]},
        separators=(",", ":"),
    )

    def answer(role: str, visit: int) -> str:
        if role == "perception":
            return perception
        if role == "solver":
            return "intent: %s\nentities: none" % intents[0]
        if role == "reviewer":
            return "The draft names one legal intent and no unsupported entity."
        if role == "planner":
            return "ACCEPT"
        raise AssertionError("unexpected role %r" % role)

    return answer


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--runtime-root", default=str(Path.home()))
    parser.add_argument("--cell", default=SMOKE_CELL)
    parser.add_argument("--experiment", default=SMOKE_EXPERIMENT)
    args = parser.parse_args(argv)

    from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
        NATIVE_ROLE_GRAPH_ORDER, compose_dry_run, dry_run_native_episode, legal_intent_ids,
    )
    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
    from speech_aware_evidence_acquisition.rails import controllers
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        load_native_episode_config,
    )
    from speech_aware_evidence_acquisition.rails.runner import _solver_fragment_seed
    from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (
        compose_solver_sample_decoding_params,
    )

    repo_root = Path(args.repo_root)
    fragment = json.loads((repo_root / "configs" / "experiment" /
                           ("%s.json" % args.experiment)).read_text(encoding="utf-8"))
    cell = next(item for item in fragment["cells"] if item["cell_id"] == args.cell)

    report: dict = {"cell": args.cell, "experiment": args.experiment, "ok": True}

    # ---- proof 1: FORM -------------------------------------------------------------------
    composed = compose(repo_root, model=cell["model_fragment"], dataset=cell["dataset_fragment"],
                       baseline=cell["baseline_fragment"], experiment=args.experiment)
    program = controllers.default_phase_program(composed.values["policy"])
    episode = load_native_episode_config(composed.values, program)
    solver = next(role for role in episode.roles if role.role_kind == "solver")
    measured = {
        "policy": program.program_id,
        "program_max_contacts": program.max_contacts,
        "graph_ceiling": episode.max_contacts,
        "solver_samples": solver.samples,
        "solver_twin": solver.twin,
        "solver_temperature": float(solver.decoding_overrides["temperature"]),
        "solver_seed_offset": int(solver.decoding_overrides["seed_offset"]),
        "commit_policy": solver.commit["policy"],
        "commit_min_support": int(solver.commit["min_support"]),
        "commit_similarity_threshold": float(solver.commit["similarity_threshold"]),
        "max_revisions": episode.max_revisions,
        "review_loop": composed.values["native_episode"].get("review_loop"),
        "roles": {role.role_kind: role.max_iterations for role in episode.roles},
    }
    report["form"] = {"expected": EXPECTED, "measured": measured,
                      "agrees": measured == EXPECTED,
                      "composed_config_hash": composed.config_hash,
                      "deliver_normaliser": composed.values["native_episode"].get(
                          "deliver_normaliser"),
                      "prepared_phase_supply": composed.values.get(
                          "prepared_phase_supply", "ABSENT (minted at the flip, item E16)")}
    if not report["form"]["agrees"]:
        report["ok"] = False
        report["form"]["disagreements"] = sorted(
            k for k in EXPECTED if EXPECTED[k] != measured.get(k)
        )

    # ---- proof 2: IDENTITY ---------------------------------------------------------------
    fragment_seed = _solver_fragment_seed(program.program_id)
    base = dict(composed.values.get("decoding_params") or {})
    per_sample = [
        compose_solver_sample_decoding_params(
            base, fragment_seed=fragment_seed,
            decoding_overrides=solver.decoding_overrides, sample_index=index)
        for index in range(solver.samples)
    ]
    keys = set()
    for params in per_sample:
        keys |= set(params)
    differ = sorted(
        key for key in keys
        if len({json.dumps(params.get(key), sort_keys=True) for params in per_sample}) > 1
    )
    seeds = [params.get("seed") for params in per_sample]
    report["identity"] = {
        "fragment_seed": fragment_seed,
        "base_decoding_params": base,
        "sample_decoding_params": per_sample,
        "fields_that_differ": differ,
        "seeds": seeds,
        "seeds_all_distinct": len(set(seeds)) == len(seeds),
        "all_temperatures_are_the_declared_0_7": all(
            float(params["temperature"]) == 0.7 for params in per_sample),
        "seeds_by_construction": (
            "seed = fragment_seed + seed_offset + sample_index, so the five seeds are "
            "fragment_seed .. fragment_seed + 4; at temperature 0.7 the seed is the ONLY thing "
            "that makes the five samples independent draws of one request"
        ),
    }
    if (differ != ["seed"] or not report["identity"]["all_temperatures_are_the_declared_0_7"]
            or not report["identity"]["seeds_all_distinct"]):
        report["ok"] = False
        report["identity"]["defect"] = (
            "the five samples are NOT one request drawn five times: either a field other than seed "
            "differs, a temperature is not the declared 0.7, or two seeds collide"
        )

    # ---- proof 3: WALK -------------------------------------------------------------------
    def build():
        runtime = build_flight_runtime(
            repo_root, Path(args.data_root), model=cell["model_fragment"],
            dataset=cell["dataset_fragment"], baseline=cell["baseline_fragment"],
            experiment=args.experiment, run_id=cell["run_id"], attempt_id=cell["attempt_id"],
            runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
            campaign_active=False,
        )
        return runtime, compose_dry_run(runtime, sample_limit=4)

    runtime, _binding = build()
    intents = legal_intent_ids(runtime)[:3]
    report["walk"] = {"rows": {}, "canned_candidate_intents": list(intents)}
    roster = [item.sample_id for item in runtime._samples]
    report["walk"]["roster"] = roster
    for sample_id in roster:
        runtime, _binding = build()
        result = dry_run_native_episode(runtime, answers=_answers_for(intents),
                                        sample_id=sample_id, sample_limit=4)
        walked = tuple(node.phase for node in result.nodes)
        if walked != NATIVE_ROLE_GRAPH_ORDER:
            report["ok"] = False
        report["walk"]["rows"][sample_id] = {
            "walked": list(walked),
            "delivered_phase": result.delivered_phase,
            "supplied_items_per_node": {
                node.phase: len(node.supplied_value_ids) for node in result.nodes
            },
        }

    report["what_the_verdict_is"] = (
        "ok means: the composed episode IS cell ROLL-2's registered grouped-Solver form (proof 1), "
        "the five Solver samples are one request drawn five times at the declared temperature "
        "(proof 2), and every smoke row walks the whole graph and delivers with the DEV-2000-ADDED "
        "knowledge artifacts resolving at every node boundary (proof 3). The supply counts are "
        "INFORMATION: four rows cannot decide whether a route is inert."
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
