#!/usr/bin/env python3
"""The VER-1b four-row OFFLINE dry run: does the grouped greedy-first review-off form compose and walk on Fold A?

Model-free by construction: zero model, tool, network, GPU, gate, transport, client, attempt and serving-session contacts. The REAL
registered smoke cell is composed from the committed fragments and walked node by node by
``speech_aware_evidence_acquisition.analysis.native_episode_dry_run`` (Perception then Solver; the Reviewer and Planner are never
visited); only the two role answers are canned, exactly as a fake frozen core would answer. It needs the data root (released stores,
roster) and therefore is root's to run after the flip; it prints ids, counts and digests only.

Three proofs, in the order they can fail:

1. **FORM** -- the composed episode is the registered cell: the policy ``vf.PROGRAM`` (``phase-native-module-v1-c4``) with ``max_contacts``
   ``vf.CEILING``, the loader's own graph ceiling, Solver ``samples`` ``vf.SAMPLES`` (3) with ``decoding_overrides`` ``vf.SOLVER_OVERRIDES``
   (temperature 0.7, seed_offset 0, greedy_first true) and the plurality-support commit ``vf.SOLVER_COMMIT`` (``min_support 2``,
   similarity 0.8), no ``twin``, no ``deliver_normaliser``, review loop off,
   ``max_revisions`` 0 and roles perception 1 / solver 1 / reviewer 0 / planner 0.
2. **IDENTITY** -- the ``vf.SAMPLES`` samples' composed request decoding params, built by the production
   ``compose_solver_sample_decoding_params`` with the real ``rails.runner._solver_fragment_seed`` of this program, differ in EXACTLY
   ``seed`` and ``temperature``: sample 0 carries the fragment's own temperature (0) and differs from the fragment's block only by the
   pinned seed, the other samples carry ``vf.SAMPLE_TEMPERATURE``, and the seeds are distinct and consecutive.
3. **WALK** -- every one of the four smoke rows walks perception -> solver and delivers, with the Fold A knowledge artifacts resolving
   at the Perception boundary. A refusal raised here is a refusal the flight would raise.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B scripts/flights/ver/ver1b_dry_run.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ver1b_family as vf  # noqa: E402

EXPECTED = {
    "policy": vf.PROGRAM,
    "program_max_contacts": vf.CEILING,
    "graph_ceiling": vf.CEILING,
    "solver_samples": vf.SAMPLES,
    "solver_twin": None,
    "solver_decoding_overrides": dict(vf.SOLVER_OVERRIDES),
    "commit": dict(vf.SOLVER_COMMIT),
    "max_revisions": 0,
    "review_loop": "off",
    "deliver_normaliser": None,
    "roles": {"perception": 1, "solver": 1, "reviewer": 0, "planner": 0},
}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", default=str(vf.REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--runtime-root", default=str(Path.home()))
    args = parser.parse_args(argv)
    repo = Path(args.repo_root).resolve()
    sys.path.insert(0, str(repo / "src"))

    from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
        compose_dry_run, dry_run_native_episode, legal_intent_ids,
    )
    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
    from speech_aware_evidence_acquisition.rails import controllers
    from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
    from speech_aware_evidence_acquisition.rails.runner import _solver_fragment_seed
    from speech_aware_evidence_acquisition.reproduction.ojw.native_request import compose_solver_sample_decoding_params

    smoke = vf.SMOKE
    fragment = json.loads((repo / "configs" / "experiment" / f"{smoke['experiment']}.json").read_text(encoding="utf-8"))
    cell = next(item for item in fragment["cells"] if item["cell_id"] == smoke["experiment"])
    report: dict = {"cell": smoke["experiment"], "ok": True}

    # ---- proof 1: FORM
    composed = compose(repo, model=cell["model_fragment"], dataset=cell["dataset_fragment"],
                       baseline=cell["baseline_fragment"], experiment=smoke["experiment"])
    program = controllers.default_phase_program(composed.values["policy"])
    episode = load_native_episode_config(composed.values, program)
    solver = next(role for role in episode.roles if role.role_kind == "solver")
    measured = {
        "policy": program.program_id, "program_max_contacts": program.max_contacts, "graph_ceiling": episode.max_contacts,
        "solver_samples": solver.samples, "solver_twin": solver.twin,
        "solver_decoding_overrides": dict(solver.decoding_overrides), "commit": dict(solver.commit),
        "max_revisions": episode.max_revisions, "review_loop": composed.values["native_episode"].get("review_loop"),
        "deliver_normaliser": composed.values["native_episode"].get("deliver_normaliser"),
        "roles": {role.role_kind: role.max_iterations for role in episode.roles},
    }
    report["form"] = {"expected": EXPECTED, "measured": measured, "agrees": measured == EXPECTED,
                      "composed_config_hash": composed.config_hash}
    if not report["form"]["agrees"]:
        report["ok"] = False
        report["form"]["disagreements"] = sorted(k for k in EXPECTED if EXPECTED[k] != measured.get(k))

    # ---- proof 2: IDENTITY
    fragment_seed = _solver_fragment_seed(program.program_id)
    base = dict(composed.values.get("decoding_params") or {})
    per_sample = [
        compose_solver_sample_decoding_params(base, fragment_seed=fragment_seed,
                                              decoding_overrides=solver.decoding_overrides, sample_index=index)
        for index in range(solver.samples)
    ]
    seeds = [params.get("seed") for params in per_sample]
    temperatures = [params.get("temperature") for params in per_sample]
    differ = sorted(key for key in set().union(*per_sample)
                    if len({json.dumps(params.get(key), sort_keys=True) for params in per_sample}) > 1)
    sample0_vs_base = sorted(key for key in set(base) | set(per_sample[0])
                             if json.dumps(base.get(key), sort_keys=True) != json.dumps(per_sample[0].get(key), sort_keys=True))
    report["identity"] = {
        "fragment_seed": fragment_seed, "base_decoding_params": base, "sample_decoding_params": per_sample,
        "fields_that_differ_across_samples": differ, "temperatures": temperatures, "seeds": seeds,
        "sample0_fields_that_differ_from_the_fragment_block": sample0_vs_base,
    }
    identity_ok = (
        differ == ["seed", "temperature"] and temperatures == [base.get("temperature")] + [vf.SAMPLE_TEMPERATURE] * (vf.SAMPLES - 1)
        and seeds == [fragment_seed + index for index in range(vf.SAMPLES)] and sample0_vs_base == ["seed"]
    )
    report["identity"]["agrees"] = identity_ok
    if not identity_ok:
        report["ok"] = False

    # ---- proof 3: WALK
    def build():
        runtime = build_flight_runtime(
            repo, Path(args.data_root), model=cell["model_fragment"], dataset=cell["dataset_fragment"],
            baseline=cell["baseline_fragment"], experiment=smoke["experiment"], run_id=cell["run_id"],
            attempt_id=cell["attempt_id"], runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
            campaign_active=False,
        )
        return runtime, compose_dry_run(runtime, sample_limit=4)

    runtime, _binding = build()
    legal = legal_intent_ids(runtime)
    candidates = list(legal[:3])
    perception = json.dumps(
        {"candidates": [{"intent_id": intent, "distinction": "Dry-run canned alternative.", "evidence_refs": [],
                         "unresolved_fields": []} for intent in candidates]}, separators=(",", ":"))
    scenario, _, action = candidates[0].partition("_")
    solver_answer = json.dumps({"scenario": scenario, "action": action, "entities": []}, separators=(",", ":"))

    def answer(role: str, visit: int) -> str:
        if role == "perception":
            return perception
        if role == "solver":
            return solver_answer
        raise AssertionError(f"unexpected role {role!r}: the review-off graph visits Perception and Solver only")

    report["walk"] = {"rows": {}}
    for sample in [item.sample_id for item in runtime._samples][:4]:
        runtime, _binding = build()
        result = dry_run_native_episode(runtime, answers=answer, sample_id=sample, sample_limit=4,
                                        node_order=("perception", "solver"))
        walked = [node.phase for node in result.nodes]
        if walked != ["perception", "solver"]:
            report["ok"] = False
        report["walk"]["rows"][sample] = {
            "walked": walked, "delivered_phase": result.delivered_phase,
            "supplied_items_per_node": {node.phase: len(node.supplied_value_ids) for node in result.nodes},
        }
    report["what_the_verdict_is"] = (
        f"ok means: the composed episode IS the registered {vf.CELL_LABEL} form (proof 1), the {vf.SAMPLES} Solver samples are one request drawn {vf.SAMPLES} "
        f"times with the greedy first sample and {vf.SAMPLES - 1} temperature-{vf.SAMPLE_TEMPERATURE:g} draws (proof 2), and every smoke row walks Perception then Solver and "
        f"delivers with the {vf.FOLD_TITLE} knowledge artifacts resolving at the Perception boundary (proof 3). The supply counts are INFORMATION."
    )
    print("VER1B-DRYRUN-SUMMARY " + json.dumps({"ok": report["ok"], "form": report["form"]["agrees"],
                                                "identity": report["identity"]["agrees"],
                                                "rows": len(report["walk"]["rows"])}, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
