#!/usr/bin/env python3
"""The NX-T R3 four-row OFFLINE dry run: the review-off module graph with the Solver template column, walked node by node.

Model-free by construction: zero model, tool, network, GPU, gate, transport, client, attempt and serving-session contacts. The REAL registered smoke cell
is composed from the committed fragments over the real released stores and walked by
``speech_aware_evidence_acquisition.analysis.native_episode_dry_run`` (the harness's own contact-free per-node walk); only the two role answers (Perception,
Solver) are canned, exactly as a fake frozen core would answer. It READS the data root (released knowledge stores, packet receipts); it writes nothing.

What it proves, per row of the four-row Fold B prefix: the whole graph walks (perception -> solver -> delivery; no Reviewer or Planner visit), the Solver node
carries the declared arms (``nxt_r3_arms.json``) in declared order with the twin ``aa`` and the delivering ``lock`` arm last, the twin renders the locked
instruction (equal digest), every candidate renders its OWN pinned template (digests distinct from each other and from lock), every arm is supplied the SAME
evidence, the delivered arm is ``lock``, EVERY arm's per-node decoding is the lock's (budget 3,072 / max_tokens 4,096 / thinking on, on both nodes), and the program
ceiling is the compiled one. Prints one ``NXT-R3-DRYRUN-SUMMARY`` line (ids, counts and digests only -- never an instruction text, utterance or gold) and exits
non-zero on any violation.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B scripts/flights/nx/nxt_r3_dry_run.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import nxt_r3_family as nf  # noqa: E402


def lock_node_decoding() -> dict:
    """The decoding every node of every arm must carry: the lock form (thinking on, the delivering budget, the delivering cap)."""

    on = {"thinking_budget_tokens": nf.DELIVERING_BUDGET, "chat_template_kwargs": {"enable_thinking": True}, "max_tokens": nf.COMPLETION_CAP}
    return {node: dict(on) for node in nf.NODES}


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

    smoke = nf.CELLS["smoke"]
    fragment = json.loads((repo / "configs" / "experiment" / f"{smoke['cell']}.json").read_text(encoding="utf-8"))
    cell = next(item for item in fragment["cells"] if item["cell_id"] == smoke["cell"])
    runtime = build_flight_runtime(
        repo, Path(args.data_root), model=cell["model_fragment"], dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"], experiment=smoke["cell"], run_id=cell["run_id"],
        attempt_id=cell["attempt_id"], runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
        campaign_active=False,
    )
    binding = compose_dry_run(runtime, sample_limit=4)
    legal = legal_intent_ids(runtime)
    candidates = list(legal[:3])
    perception = json.dumps(
        {"candidates": [{"intent_id": intent, "distinction": "Dry-run canned alternative.", "evidence_refs": [], "unresolved_fields": []}
                        for intent in candidates]}, separators=(",", ":"))
    scenario, _, action = candidates[0].partition("_")
    solver = json.dumps({"scenario": scenario, "action": action, "entities": []}, separators=(",", ":"))

    def answer(role: str, visit: int) -> str:
        if role == "perception":
            return perception
        if role == "solver":
            return solver
        raise AssertionError(f"unexpected role {role!r}: the review-off graph visits Perception and Solver only")

    problems: list[str] = []
    rows = []
    expected_order = list(nf.ARM_ORDER)
    expected_decoding = lock_node_decoding()
    locked_digest = None
    candidate_digest_by_arm: dict[str, str] = {}
    for sample in runtime._samples[:4]:
        result = dry_run_native_episode(runtime, answers=answer, sample_id=sample.sample_id, sample_limit=4, node_order=("perception", "solver"))
        walked = [node.phase for node in result.nodes]
        solver_node = next(node for node in result.nodes if node.phase == "solver")
        arms = solver_node.supply_variant_arms
        by_id = {arm.arm_id: arm for arm in arms}
        digests = {arm.arm_id: arm.instruction_sha256 for arm in arms}
        supplied = {arm.arm_id: tuple(arm.supplied_value_ids) for arm in arms}
        if walked != ["perception", "solver"]:
            problems.append(f"{sample.sample_id}: walked {walked}, expected [perception, solver]")
        if [arm.arm_id for arm in arms] != expected_order:
            problems.append(f"{sample.sample_id}: arms {[arm.arm_id for arm in arms]}, expected {expected_order}")
        if not arms or not arms[-1].deliver or sum(1 for arm in arms if arm.deliver) != 1:
            problems.append(f"{sample.sample_id}: the delivering arm is not the single last arm")
        if result.delivered_arm_id() != nf.DELIVERING:
            problems.append(f"{sample.sample_id}: delivered arm {result.delivered_arm_id()!r}")
        if digests.get(nf.TWIN) != digests.get(nf.DELIVERING):
            problems.append(f"{sample.sample_id}: the twin does not render the locked instruction")
        cand = [digests.get(a) for a in nf.CANDIDATE_ARMS]
        if len(set(cand)) != len(nf.CANDIDATE_ARMS) or digests.get(nf.DELIVERING) in cand:
            problems.append(f"{sample.sample_id}: candidate instruction digests are not distinct from each other and from lock")
        if len({supplied[a] for a in expected_order if a in supplied}) != 1:
            problems.append(f"{sample.sample_id}: arms were supplied different evidence")
        for arm_id in expected_order:
            arm = by_id.get(arm_id)
            if arm is None or arm.node_decoding is None or {k: dict(v) for k, v in arm.node_decoding.items()} != expected_decoding:
                problems.append(f"{sample.sample_id}: arm {arm_id!r} node decoding differs from the lock's thinking fields")
        candidate_digest_by_arm = {a: digests.get(a) for a in nf.CANDIDATE_ARMS}
        locked_digest = digests.get(nf.DELIVERING)
        rows.append({"walked": walked, "delivered_arm": result.delivered_arm_id(), "supplied_item_count": len(next(iter(supplied.values()), ())),
                     "instruction_chars": {arm.arm_id: arm.instruction_chars for arm in arms}})
    summary = {
        "ok": not problems, "problems": problems, "rows": len(rows), "program_id": binding["program"].program_id,
        "program_max_contacts": binding["program"].max_contacts, "expected_ceiling": nf.CONTACTS_PER_ROW,
        "arm_order": expected_order, "locked_instruction_sha256": locked_digest, "candidate_instruction_sha256": candidate_digest_by_arm,
        "node_decoding_every_arm": expected_decoding, "per_row": rows,
    }
    if binding["program"].max_contacts != nf.CONTACTS_PER_ROW:
        summary["ok"] = False
        problems.append("program ceiling differs from the compiled one")
    print("NXT-R3-DRYRUN-SUMMARY " + json.dumps(summary, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
