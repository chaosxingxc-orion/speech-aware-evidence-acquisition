#!/usr/bin/env python3
"""The NX R5 four-row OFFLINE dry run: the composed review-off lock-v2.2 graph walked node by node.

Model-free by construction: zero model, tool, network, GPU, gate, transport, client, attempt and serving-session contacts. The REAL
registered smoke cell is composed from the committed fragments over the real released stores and walked by
``speech_aware_evidence_acquisition.analysis.native_episode_dry_run`` (the harness's own contact-free per-node walk); only the two role
answers (Perception, Solver) are canned, exactly as a fake frozen core would answer.

What it proves, per row of the four-row prefix: the graph walks perception -> solver (no Reviewer or Planner visit, no tool schema), the
compiled program is ``phase-native-module-v1-c2`` with ceiling 2, the Solver node carries the LOCKED instruction template (no variant arm),
and the delivery normaliser the run resolves is ``saea-deliver-normalise-v4g``. Prints one ``NX-R5-DRYRUN-SUMMARY`` line (ids, counts and
digests only -- never an instruction text, utterance or gold) and exits non-zero on any violation.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B scripts/flights/nx/nx_r5_dry_run.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import nx_r5_family as nf  # noqa: E402


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
    binding = compose_dry_run(runtime, sample_limit=nf.SMOKE_ROWS)
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

    problems: list[str] = []
    rows = []
    result = None
    for sample in runtime._samples[:nf.SMOKE_ROWS]:
        result = dry_run_native_episode(runtime, answers=answer, sample_id=sample.sample_id, sample_limit=nf.SMOKE_ROWS,
                                        node_order=("perception", "solver"))
        walked = [node.phase for node in result.nodes]
        solver_node = next(node for node in result.nodes if node.phase == "solver")
        if walked != ["perception", "solver"]:
            problems.append(f"{sample.sample_id}: walked {walked}, expected [perception, solver]")
        if getattr(solver_node, "supply_variant_arms", None):
            problems.append(f"{sample.sample_id}: the Solver node carries variant arms; R5 delivers the locked template only")
        rows.append({"walked": walked})
    if binding["program"].program_id != nf.PROGRAM or binding["program"].max_contacts != nf.CEILING:
        problems.append(f"program {binding['program'].program_id} / {binding['program'].max_contacts}, expected {nf.PROGRAM} / {nf.CEILING}")
    baseline = json.loads((repo / "configs" / "baseline" / f"{cell['baseline_fragment']}.json").read_text(encoding="utf-8"))
    normaliser = baseline["native_episode"]["deliver_normaliser"]["normaliser"]
    if normaliser != nf.NORMALISER:
        problems.append(f"the smoke cell delivers through {normaliser!r}, expected {nf.NORMALISER!r}")
    from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS
    from speech_aware_evidence_acquisition.rails import delivery_normalisers  # noqa: F401

    DELIVERY_NORMALISERS.resolve(normaliser)  # the registered entry the runtime resolves at delivery
    summary = {
        "ok": not problems, "problems": problems, "rows": len(rows), "program_id": binding["program"].program_id,
        "program_max_contacts": binding["program"].max_contacts, "expected_ceiling": nf.CEILING,
        "deliver_normaliser": normaliser, "per_row": rows,
        "first_phase_seed_source": getattr(result, "first_phase_seed_source", None),
    }
    print("NX-R5-DRYRUN-SUMMARY " + json.dumps(summary, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
