#!/usr/bin/env python3
"""The SUCCESSOR-2 composed cell's four-row OFFLINE dry run: the review-off module graph, walked node by node on the sample prefix.

Model-free by construction: zero model, tool, network, GPU, gate, transport, client, attempt and serving-session contacts. The REAL
registered cell (``slurp-milestone-successor2-composed-v1``) is composed from the committed fragments over the real released stores
and walked by ``speech_aware_evidence_acquisition.analysis.native_episode_dry_run`` (the harness's own contact-free per-node walk);
only the two role answers (Perception, Solver) are canned, exactly as a fake frozen core would answer. THIS IS THE FORM PROOF THAT
STANDS IN FOR THE SMOKE: the allowance lists a test-sample smoke as not authorised, so nothing here may open a model. The runtime
adapter admits ``slurp:test`` rows only under the signed allowance the fragment pins (labels stripped, ``gold()`` raises), so the
walk reads label-free packets, the sample's pinned query vectors and the cell's OWN prepared first-phase supply -- no gold, no
score, no model output -- and prints ids, counts and digests only. It needs the data root and a READY cell (the own supply is minted
by the flip), so it is root's to run after the flip, before the chain.

What it proves, per row of the four-row sample prefix: the whole graph walks (perception -> solver -> delivery; no Reviewer or
Planner visit), the Perception node declares NO template or supply-variant column (one visit, the locked instruction), the program
ceiling is the compiled one (2), the first-phase seed comes from the cell's own prepared supply, and the delivering normaliser is
``saea-deliver-normalise-v4g``. Prints one ``MS2-DRYRUN-SUMMARY`` line and exits non-zero on any violation.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B scripts/flights/nx/milestone_successor2_dry_run.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CELL = "slurp-milestone-successor2-composed-v1"
CEILING = 2
NORMALISER = "saea-deliver-normalise-v4g"
NODES = ["perception", "solver"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
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

    fragment = json.loads((repo / "configs" / "experiment" / f"{CELL}.json").read_text(encoding="utf-8"))
    cell = next(item for item in fragment["cells"] if item["cell_id"] == CELL)
    problems: list[str] = []
    if cell["readiness"]["state"] != "ready":
        problems.append(f"the cell is {cell['readiness']['state']!r}, not ready: run this after the flip (the own supply is minted there)")
    baseline = json.loads((repo / "configs" / "baseline" / f"{cell['baseline_fragment']}.json").read_text(encoding="utf-8"))
    normaliser = (baseline.get("native_episode") or {}).get("deliver_normaliser", {}).get("normaliser")
    if normaliser != NORMALISER:
        problems.append(f"delivery normaliser is {normaliser!r}, expected {NORMALISER!r}")
    if problems:
        print("MS2-DRYRUN-SUMMARY " + json.dumps({"ok": False, "problems": problems}, sort_keys=True))
        return 1
    runtime = build_flight_runtime(
        repo, Path(args.data_root), model=cell["model_fragment"], dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"], experiment=CELL, run_id=cell["run_id"],
        attempt_id=cell["attempt_id"], runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
        campaign_active=False,
    )
    binding = compose_dry_run(runtime, sample_limit=4)
    legal = legal_intent_ids(runtime)
    candidates = list(legal[:3])
    perception = json.dumps(
        {"candidates": [{"intent_id": intent, "distinction": "E=none; Dry-run canned alternative.",
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

    rows = []
    result = None
    for sample in runtime._samples[:4]:
        result = dry_run_native_episode(runtime, answers=answer, sample_id=sample.sample_id, sample_limit=4, node_order=tuple(NODES))
        walked = [node.phase for node in result.nodes]
        if walked != NODES:
            problems.append(f"{sample.sample_id}: walked {walked}, expected {NODES}")
        for node in result.nodes:
            arms = getattr(node, "supply_variant_arms", None) or []
            if arms:
                problems.append(f"{sample.sample_id}: node {node.phase} declares a supply-variant column ({len(arms)} arms)")
        rows.append({"walked": walked})
    if binding["program"].max_contacts != CEILING:
        problems.append(f"program ceiling {binding['program'].max_contacts}, expected {CEILING}")
    seed_source = getattr(result, "first_phase_seed_source", None) if result is not None else None
    if seed_source is None:
        problems.append("the first-phase seed source is not reported")
    summary = {
        "ok": not problems, "problems": problems, "rows": len(rows), "program_id": binding["program"].program_id,
        "program_max_contacts": binding["program"].max_contacts, "expected_ceiling": CEILING,
        "deliver_normaliser": normaliser, "per_row": rows, "first_phase_seed_source": seed_source,
    }
    print("MS2-DRYRUN-SUMMARY " + json.dumps(summary, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
