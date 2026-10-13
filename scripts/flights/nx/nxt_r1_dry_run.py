#!/usr/bin/env python3
"""The NX-T R1 four-row OFFLINE dry run: the review-off module graph with the five-arm thinking-policy column, walked node by node.

Model-free by construction: zero model, tool, network, GPU, gate, transport, client, attempt and serving-session contacts. The REAL registered smoke cell
is composed from the committed fragments over the real released stores and walked by
``speech_aware_evidence_acquisition.analysis.native_episode_dry_run`` (the harness's own contact-free per-node walk); only the two role answers (Perception,
Solver) are canned, exactly as a fake frozen core would answer. It READS the data root (released knowledge stores, packet receipts); it writes nothing.

What it proves, per row of the four-row Fold B prefix: the whole graph walks (perception -> solver -> delivery; no Reviewer or Planner visit), the Perception
node carries the five declared arms in declared order with the delivering ``both-on`` arm last, every arm renders the node's LOCKED instruction (equal
digests) over the SAME supplied evidence, each arm's per-node decoding is the one its policy declares (``node_decoding``: the delivering arm and the twin
carry the lock's budget 3,072 / cap 4,096 on both nodes, a no-think node carries ``enable_thinking`` false and ``max_tokens`` 1,024 with no budget), and the
program ceiling is the compiled one. Prints one ``NXT-R1-DRYRUN-SUMMARY`` line (ids, counts and digests only -- never an instruction text, utterance or gold)
and exits non-zero on any violation.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B scripts/flights/nx/nxt_r1_dry_run.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import nxt_r1_family as nf  # noqa: E402

ON = {"thinking_budget_tokens": nf.tsf.THINK_BUDGET_TOKENS, "chat_template_kwargs": {"enable_thinking": True}, "max_tokens": nf.tsf.THINK_MAX_TOKENS}
OFF = {"thinking_budget_tokens": None, "chat_template_kwargs": {"enable_thinking": False}, "max_tokens": nf.tsf.THINK_ANSWER_RESERVE_TOKENS}


def expected_node_decoding(arm: str) -> dict:
    policy = nf.POLICIES.get(arm, {})
    return {node: (OFF if policy.get(node, {}).get("enable_thinking") is False else ON) for node in ("perception", "solver")}


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
    locked_digest = None
    for sample in runtime._samples[:4]:
        result = dry_run_native_episode(runtime, answers=answer, sample_id=sample.sample_id, sample_limit=4, node_order=("perception", "solver"))
        walked = [node.phase for node in result.nodes]
        perception_node = next(node for node in result.nodes if node.phase == "perception")
        arms = perception_node.supply_variant_arms
        by_id = {arm.arm_id: arm for arm in arms}
        digests = {arm.arm_id: arm.instruction_sha256 for arm in arms}
        supplied = {arm.arm_id: tuple(arm.supplied_value_ids) for arm in arms}
        if walked != ["perception", "solver"]:
            problems.append(f"{sample.sample_id}: walked {walked}, expected [perception, solver]")
        if [arm.arm_id for arm in arms] != expected_order:
            problems.append(f"{sample.sample_id}: arms {[arm.arm_id for arm in arms]}, expected {expected_order}")
        if not arms or not arms[-1].deliver or sum(1 for arm in arms if arm.deliver) != 1:
            problems.append(f"{sample.sample_id}: the delivering arm is not the single last arm")
        if len(set(digests.values())) != 1:
            problems.append(f"{sample.sample_id}: arms do not all render the node's locked instruction")
        if len(set(supplied.values())) != 1:
            problems.append(f"{sample.sample_id}: arms were supplied different evidence")
        for arm_id in expected_order:
            arm = by_id.get(arm_id)
            if arm is None or arm.node_decoding is None or dict(arm.node_decoding) != expected_node_decoding(arm_id):
                problems.append(f"{sample.sample_id}: arm {arm_id!r} node decoding differs from its declared policy")
        locked_digest = digests.get(nf.DELIVERING)
        rows.append({"walked": walked, "supplied_item_count": len(next(iter(supplied.values()), ())),
                     "instruction_chars": {arm.arm_id: arm.instruction_chars for arm in arms}})
    summary = {
        "ok": not problems, "problems": problems, "rows": len(rows), "program_id": binding["program"].program_id,
        "program_max_contacts": binding["program"].max_contacts, "expected_ceiling": nf.CONTACTS_PER_ROW,
        "arm_order": expected_order, "locked_instruction_sha256": locked_digest,
        "node_decoding_by_arm": {arm: expected_node_decoding(arm) for arm in expected_order}, "per_row": rows,
    }
    if binding["program"].max_contacts != nf.CONTACTS_PER_ROW:
        summary["ok"] = False
        problems.append("program ceiling differs from the compiled one")
    print("NXT-R1-DRYRUN-SUMMARY " + json.dumps(summary, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
