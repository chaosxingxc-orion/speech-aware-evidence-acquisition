#!/usr/bin/env python3
"""CLI: prove the EVO-S1 exposure rows admit round 1 (MODEL-FREE, no writes
into the loop's own artefact paths).

The loop refuses to emit a fragment whose flight would exceed its registered
row (``rails.evolution.check_ledger_budget``), and plan budgets are
RUN-CUMULATIVE across every attempt of a run id -- so the number checked is
the loop's worst case for the whole run id, not one round's. This script
charges exactly what each step will charge, against the committed exposure
ledger, and reports the answer per run id.

It also DRY-RUNS the propose step end to end in memory -- the draws, their
anchors, the rendered instruction digests and the two fragments it would
emit -- and writes none of them, so the round-1 plan is inspectable before
the roster it would freeze exists.

Zero model, GPU, tool, embedding and network contacts. The one thing it reads
from the carrier is the exemplar roster's construction rows, which the
proposer arm is licensed to read and which the A_0 closure already opened.

Run in WSL2::

    CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/verify_slurp_evo_ledger_budget.py --write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.contracts import _parse_ledger_tables  # noqa: E402
from speech_aware_evidence_acquisition.rails.evolution import (  # noqa: E402
    EvolutionState,
    LoopConfig,
    check_ledger_budget,
    run_propose_step,
)
from speech_aware_evidence_acquisition.rails.evolution_carrier import (  # noqa: E402
    load_carrier_material,
)

LOOP_CONFIG_RELPATH = "configs/knowledge/slurp-evo-s1/loop-v1.json"
CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-evo-ledger-budget"
)
PREREGISTRATION = (
    "docs/readiness/2026-09-06-slurp-evo-s1-slot-schema-evolution-v1-preregistration.md"
)
#: The read is not driven by this loop -- it is one flight after the loop
#: closes -- so its worst case is stated here rather than derived from
#: ``LoopConfig`` (preregistration section 7, read Option B).
FINAL_READ = {"run_id": "SAEA-SLURP-EVO-S1-FINAL-V2", "calls": 1000, "speech": 2884.7937}
#: Likewise the one-time intent flight and the packet promotion: both are
#: single flights over both folds, before round 1.
ONE_TIME = (
    {"run_id": "SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2", "calls": 2160},
    {"run_id": "SAEA-SLURP-EVO-FOLD-PACKETS-V2", "calls": 2160},
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", type=int, default=1)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    config = LoopConfig.from_json(
        json.loads((REPO_ROOT / LOOP_CONFIG_RELPATH).read_text(encoding="utf-8"))
    )
    ledger_rows = _parse_ledger_tables(
        (REPO_ROOT / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    )

    arms_round_one = 1 + len(config.slots_for_round(1)) + 1  # +1 deterministic F2
    # K_1 = 5 (three proposer slots, the shares-only control, the form twin),
    # so round 1 flies six arms on fold A and every later round five.
    fold_pass = config.fold_a_speech_seconds
    budgets = {
        config.proposer_run_id: None,  # measured by the dry run below
        config.fold_a_run_id: {
            "calls": arms_round_one * config.fold_a_rows * config.max_rounds,
            "speech_seconds": arms_round_one * fold_pass * config.max_rounds,
        },
        config.fold_b_run_id: {
            "calls": 2 * config.fold_b_rows * config.max_rounds,
            "speech_seconds": 2 * config.fold_b_speech_seconds * config.max_rounds,
        },
        FINAL_READ["run_id"]: {
            "calls": FINAL_READ["calls"],
            "speech_seconds": FINAL_READ["speech"],
        },
    }
    for entry in ONE_TIME:
        budgets[entry["run_id"]] = {
            "calls": entry["calls"],
            "speech_seconds": config.fold_a_speech_seconds
            + config.fold_b_speech_seconds,
        }

    verdicts: dict[str, object] = {}
    for run_id, planned in budgets.items():
        if planned is None:
            continue
        verdicts[run_id] = check_ledger_budget(
            ledger_rows,
            run_id=run_id,
            calls=planned["calls"],
            speech_seconds=planned["speech_seconds"],
        )

    # The propose step, dry: it runs its OWN check_ledger_budget against the
    # proposer row and returns the documents it would write. Nothing is
    # written here.
    carrier = load_carrier_material(REPO_ROOT, config, step="propose")
    state = EvolutionState(round=args.round - 1, incumbent_overrides={}).validate()
    result = run_propose_step(
        state, args.round, config=config, carrier=carrier, ledger_rows=ledger_rows
    )
    paths = config.round_paths(args.round)["propose"]["writes"]
    receipt = result.documents[paths[2]]
    verdicts[config.proposer_run_id] = receipt["budget"]

    contacts = receipt["contacts"]
    by_family: dict[str, int] = {}
    keys_by_target: dict[str, list[int]] = {}
    for contact in contacts:
        family = str(contact["family"])
        by_family[family] = by_family.get(family, 0) + 1
        keys_by_target.setdefault(str(contact["target_id"]), []).append(
            len(contact["artifact_keys"])
        )
    anchors = sorted({str(contact["sample_id"]) for contact in contacts})
    exemplar_slots = sum(len(contact["exemplar_ids"]) for contact in contacts)
    prompt_characters = sorted(int(contact["prompt_characters"]) for contact in contacts)

    document = {
        "schema": "saea-slurp-evo-ledger-budget-v1",
        "generated_by": "scripts/verify_slurp_evo_ledger_budget.py",
        "preregistration": PREREGISTRATION,
        "round": args.round,
        "verdict": "EVERY REGISTERED ROW ADMITS THE LOOP'S WORST CASE",
        "budget_is": (
            "run-cumulative across every attempt of a run id, so each number below is "
            "R_max x the largest per-round cost, not one round's"
        ),
        "run_ids": verdicts,
        "round_one_propose_dry_run": {
            "writes_nothing": True,
            "roster_id": receipt["roster_id"],
            "roster_split_identity_hash": receipt["roster_split_identity_hash"],
            "incumbent_state_sha256": receipt["incumbent_state_sha256"],
            "slots": receipt["slots"],
            "proposer_slots": receipt["proposer_slots"],
            "placebo_slot": receipt["placebo_slot"],
            "contacts": len(contacts),
            "contacts_by_family": dict(sorted(by_family.items())),
            "distinct_anchor_rows": len(anchors),
            "exemplar_slots_shown": exemplar_slots,
            "prompts_all_digested": all(
                len(str(contact["prompt_sha256"])) == 64 for contact in contacts
            ),
            "prompt_characters_min_max": [
                prompt_characters[0],
                prompt_characters[-1],
            ],
            # Per scenario, the number of intent blocks each of the three
            # draws asked to be rewritten. Fewer than the scenario owns means
            # the draw covered fewer intents, and every intent a draw did not
            # cover keeps its incumbent block: a candidate never rewrites a
            # block it saw no evidence for.
            "artifact_keys_asked_per_scenario": {
                target: sorted(counts) for target, counts in sorted(keys_by_target.items())
            },
            "fragments_it_would_emit": list(paths),
        },
        "contacts": {
            "model": 0,
            "gpu_hours": 0,
            "tool": 0,
            "embedding": 0,
            "network": 0,
            "paid_api_spend": 0,
        },
    }
    print(json.dumps(document, indent=2, sort_keys=True))
    if not args.write:
        return 0
    check_dir = REPO_ROOT / CHECK_DIR
    check_dir.mkdir(parents=True, exist_ok=True)
    (check_dir / "ledger-budget.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {CHECK_DIR}/ledger-budget.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
