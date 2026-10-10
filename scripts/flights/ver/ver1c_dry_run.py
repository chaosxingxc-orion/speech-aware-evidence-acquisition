#!/usr/bin/env python3
"""The VER-1c four-row OFFLINE dry run: the review-off module graph with the one-candidate Solver template column, walked node by node.

Model-free by construction: zero model, tool, network, GPU, gate, transport, client, attempt and serving-session
contacts. The REAL registered smoke cell is composed from the committed fragments over the real released stores and walked
by ``speech_aware_evidence_acquisition.analysis.native_episode_dry_run`` (the harness's own contact-free per-node walk);
only the two role answers (Perception, Solver) are canned, exactly as a fake frozen core would answer.

What it proves, per row of the four-row Fold A prefix: the whole graph walks (perception -> solver -> delivery; no Reviewer
or Planner visit), the Solver node carries the declared arms (``cf.ARM_ORDER``: r1-c3, aa, lock) in declared order with the delivering ``lock`` arm last,
each candidate renders its OWN template (distinct instruction digests, equal to none of the others and to the locked
template), the twin ``aa`` and the delivering ``lock`` render the node's locked instruction (equal digests), every arm is
supplied the SAME evidence ids (the supply is unvaried), and the program ceiling is the compiled one. Prints one
``VER1C-DRYRUN-SUMMARY`` line (ids, counts and digests only -- never an instruction text, utterance or gold) and exits
non-zero on any violation.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B scripts/flights/ver/ver1c_dry_run.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ver1c_family as nf  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", default=str(nf.REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--runtime-root", default=str(Path.home()))
    args = parser.parse_args(argv)
    repo = Path(args.repo_root).resolve()
    sys.path.insert(0, str(repo / "src"))

    from speech_aware_evidence_acquisition.analysis.native_episode_dry_run import (
        compose_dry_run, dry_run_native_episode, legal_intent_ids,
    )
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime

    smoke = nf.SMOKE
    fragment = json.loads((repo / "configs" / "experiment" / f"{smoke['experiment']}.json").read_text(encoding="utf-8"))
    cell = next(item for item in fragment["cells"] if item["cell_id"] == smoke["experiment"])
    runtime = build_flight_runtime(
        repo, Path(args.data_root), model=cell["model_fragment"], dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"], experiment=smoke["experiment"], run_id=cell["run_id"],
        attempt_id=cell["attempt_id"], runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
        campaign_active=False,
    )
    binding = compose_dry_run(runtime, sample_limit=4)
    legal = legal_intent_ids(runtime)
    candidates = list(legal[:3])
    perception = json.dumps(
        {"candidates": [{"intent_id": intent, "distinction": "Dry-run canned alternative.",
                         "evidence_refs": [], "unresolved_fields": []} for intent in candidates]},
        separators=(",", ":"),
    )
    scenario, _, action = candidates[0].partition("_")
    solver = json.dumps({"scenario": scenario, "action": action, "entities": []}, separators=(",", ":"))

    def answer(role: str, visit: int) -> str:
        if role == "perception":
            return perception
        if role == "solver":
            return solver
        raise AssertionError(f"unexpected role {role!r}: the review-off graph visits Perception and Solver only")

    ok = True
    problems: list[str] = []
    rows = []
    expected_order = list(nf.ARM_ORDER)
    locked_digest = None
    for sample in runtime._samples[:4]:
        result = dry_run_native_episode(runtime, answers=answer, sample_id=sample.sample_id, sample_limit=4,
                                        node_order=("perception", "solver"))
        walked = [node.phase for node in result.nodes]
        solver_node = next(node for node in result.nodes if node.phase == "solver")
        arms = solver_node.supply_variant_arms
        arm_ids = [arm.arm_id for arm in arms]
        digests = {arm.arm_id: arm.instruction_sha256 for arm in arms}
        supplied = {arm.arm_id: tuple(arm.supplied_value_ids) for arm in arms}
        if walked != ["perception", "solver"]:
            problems.append(f"{sample.sample_id}: walked {walked}, expected [perception, solver]")
        if arm_ids != expected_order:
            problems.append(f"{sample.sample_id}: arms {arm_ids}, expected {expected_order}")
        if not arms or not arms[-1].deliver or sum(1 for arm in arms if arm.deliver) != 1:
            problems.append(f"{sample.sample_id}: the delivering arm is not the single last arm")
        if result.delivered_arm_id() != nf.DELIVERING:
            problems.append(f"{sample.sample_id}: delivered arm {result.delivered_arm_id()!r}")
        if digests.get(nf.TWIN) != digests.get(nf.DELIVERING):
            problems.append(f"{sample.sample_id}: the twin does not render the locked instruction")
        candidate_digests = [digests.get(a) for a in nf.ARMS]
        if len(set(candidate_digests)) != len(nf.ARMS) or digests.get(nf.DELIVERING) in candidate_digests:
            problems.append(f"{sample.sample_id}: candidate instruction digests are not distinct from each other and from lock")
        if len({supplied[a] for a in expected_order if a in supplied}) != 1:
            problems.append(f"{sample.sample_id}: arms were supplied different evidence")
        locked_digest = digests.get(nf.DELIVERING)
        rows.append({"walked": walked, "delivered_arm": result.delivered_arm_id(),
                     "supplied_item_count": len(next(iter(supplied.values()), ())),
                     "instruction_chars": {arm.arm_id: arm.instruction_chars for arm in arms}})
    ok = not problems
    summary = {
        "ok": ok, "problems": problems, "rows": len(rows), "program_id": binding["program"].program_id,
        "program_max_contacts": binding["program"].max_contacts, "expected_ceiling": nf.CEILING,
        "arm_order": expected_order, "locked_instruction_sha256": locked_digest,
        "arms_per_row": [list(nf.ARM_ORDER)] * len(rows), "per_row": rows,
        "first_phase_seed_source": result.first_phase_seed_source,
    }
    if binding["program"].max_contacts != nf.CEILING:
        summary["ok"] = False
        problems.append("program ceiling differs from the compiled one")
    print("VER1C-DRYRUN-SUMMARY " + json.dumps(summary, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
