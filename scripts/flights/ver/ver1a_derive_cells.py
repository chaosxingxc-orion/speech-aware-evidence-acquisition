#!/usr/bin/env python3
"""Derive cell VER-1a (the five-sample greedy-first Solver pool on TRAIN Fold B) and its four-row smoke.

WHAT THE CELL IS. The review-off COMP-1b module graph exactly as the NX R5 composed arm and the R6-P1 base (lock ``v2.2``,
``agree-vote-seed`` + ``centroid-boundary-key`` ON, Reviewer loop OFF, no tool schema on any role) on TRAIN Fold B, with ONE change at
the Solver node: the visit is grouped at ``samples = 5`` -- sample 0 greedy (``decoding_overrides.greedy_first``), samples 1-4 at
temperature 0.7 -- committed by the registered plurality-support policy at ``min_support 3``. See ``ver1a_family.py`` for why the
delivered text is the unnormalised commit and v4g is applied offline.

HOW IT IS DERIVED (nothing hand-edited). The committed R6-P1 baseline is the parent (its Fold B pins, speech-query pins, centroid facet
pin and preparation receipts are the P-SV-4 / COMP-1b ones). Its ``consumption_module`` block minus the Perception template columns is
compiled by ``rails.consumption_module.compile_module`` into the R5 composed arm's policy blocks (program ``phase-native-module-v1-c2``,
ceiling 2); those blocks replace the parent's, and then exactly four things change, each asserted below: the policy id (the registered
review-off family member for ceiling 6), the removal of the module declaration (the compiler has no ``samples`` knob and the loader
verifies a declared block against its own compilation), the removal of ``deliver_normaliser`` (refused beside a grouped Solver visit),
and the Solver role's ``samples`` / ``decoding_overrides`` / ``commit``. The cell's own FIT ids, the removal of the parent's minted
``prepared_phase_supply`` (E16: the flip mints this cell's own) and the label text complete the diff; every other leaf is asserted equal
to the parent's.

CONFIG ONLY: no contact, no ledger row, no receipt, no flip. Both cells are HELD.

    python -B scripts/flights/ver/ver1a_derive_cells.py
"""

from __future__ import annotations

import copy
import io
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ver1a_family as vf  # noqa: E402

REPO_ROOT = vf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402


def rd(path: str) -> str:
    return io.open(REPO_ROOT / path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    target = REPO_ROOT / path
    os.makedirs(target.parent, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


#: Longest-first id rewrites from the R6-P1 fragments to this cell's own.
def substitution_pairs() -> list[tuple[str, str]]:
    return [
        (f"slurp-stage3-{vf.PARENT_SLUG}", f"slurp-stage3-{vf.SLUG}"),
        (vf.PARENT_SLUG.upper(), vf.SLUG.upper()),
        (vf.PARENT_SLUG, vf.SLUG),
    ]


def substitute(text: str) -> str:
    for old, new in substitution_pairs():
        text = text.replace(old, new)
    return text


def _leaves(node: object, prefix: str = "") -> dict[str, object]:
    if isinstance(node, dict) and node:
        out: dict[str, object] = {}
        for key, value in node.items():
            out.update(_leaves(value, f"{prefix}.{key}" if prefix else str(key)))
        return out
    return {prefix: node}


#: The leaf-path prefixes allowed to differ from the R6-P1 parent (everything else is asserted equal).
ALLOWED_DIFFS = (
    "policy",
    "native_episode.consumption_module",                       # the declaration is dropped (see the module docstring)
    "native_episode.deliver_normaliser",                       # refused beside a grouped Solver visit
    "native_episode.roles.perception.template_variants",       # the template column is not part of this cell
    "native_episode.roles.solver.samples",
    "native_episode.roles.solver.decoding_overrides",
    "native_episode.roles.solver.commit",
    "native_contact_fit",
    "prepared_phase_supply",
    "what_this_is",
)


def derive_baseline(kind: str) -> str:
    parent_name = vf.parent_names(kind)["baseline"]
    raw = rd(f"configs/baseline/{parent_name}.json")
    parent = json.loads(raw)
    block = copy.deepcopy(parent["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY])
    block.pop("columns")
    block.pop("template_frame")                                # the base module block: review-off, lock v2.2, COMP-1b components
    if (block.get("lock"), block.get("review_loop")) != (vf.LOCK, "off"):
        raise SystemExit(f"the parent's module block is not review-off lock {vf.LOCK}")
    composed = cm.compile_module(block, carrier_module_hooks(repo_root=REPO_ROOT), repo_root=REPO_ROOT)
    if (composed.program_id, composed.program_ceiling) != ("phase-native-module-v1-c2", vf.BASE_CONTACTS):
        raise SystemExit(f"the base compiled to {composed.program_id} / {composed.program_ceiling}, expected the R5 arm's c2 / 2")
    document = composed.apply_to(parent)                       # the R5 composed arm's policy blocks on the parent's roster pins
    document["policy"] = vf.PROGRAM
    episode = document["native_episode"]
    episode.pop(cm.CONSUMPTION_MODULE_CONFIG_KEY, None)
    if episode.pop("deliver_normaliser", None) != {"normaliser": "saea-deliver-normalise-v4g"}:
        raise SystemExit("the base does not deliver through the v4g normaliser")
    solver = episode["roles"]["solver"]
    solver.update(samples=vf.SAMPLES, decoding_overrides=copy.deepcopy(vf.SOLVER_OVERRIDES), commit=copy.deepcopy(vf.SOLVER_COMMIT))
    document.pop("prepared_phase_supply", None)                # E16: the flip mints this cell's own
    rows = vf.SMOKE_ROWS if kind == "smoke" else vf.ROWS
    names = vf.names(kind)
    document["native_contact_fit"] = {**parent["native_contact_fit"], "run_id": names["fit_run_id"],
                                      "attempt_id": names["fit_attempt_id"], "contact_cap": vf.fit_contact_cap(rows)}
    document["what_this_is"] = ("Four-row form smoke of cell " if kind == "smoke" else "Cell ") + vf.CELL_LABEL + ". " + WHAT_THIS_IS
    if episode.get("finite_completion_policy") != "deliver-latest-or-abstain" or episode.get("react_exhaustion_policy") != "continue-without-answer":
        raise SystemExit("the native_episode finite-completion / ReAct-exhaustion policies are not the registered ones")
    if (episode["review_loop"], episode["max_revisions"], document.get("phase_tools")) != ("off", 0, {}):
        raise SystemExit("the review-off leaves are not as expected")
    # Every leaf outside the allowed diff list is the parent's own.
    left, right = _leaves(parent), _leaves(document)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    stray = [k for k in moved if not any(k == p or k.startswith(p + ".") for p in ALLOWED_DIFFS)]
    if stray:
        raise SystemExit(f"leaves moved beyond the registered diff: {stray[:12]}")
    out = f"configs/baseline/{names['baseline']}.json"
    wr(out, dump_like(raw, document))
    return out


WHAT_THIS_IS = (
    "VER-1a (owner decision 257, 2026-10-10; the verification layer of the training-free RL round): the SAMPLE POOL the VER-1 "
    "selection rule is read on. THE BASE is the NX R5 composed arm / the R6-P1 base -- the COMP-1b composition (agree-vote-seed w_agree "
    "1.0, k 60 over the Fold B vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1, and centroid-boundary-key "
    "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) as a consumption-module block on lock v2.2, Reviewer loop OFF (Perception then Solver; "
    "no Reviewer or Planner visit; no tool schema on any role) -- on TRAIN Fold B 1,080. THE ONE CHANGE: the Solver visit is grouped at "
    f"samples = {vf.SAMPLES}: sample 0 GREEDY (decoding_overrides.greedy_first: the fragment's own temperature 0, the answer the lock's "
    "single-sample delivery makes) and samples 1-4 at temperature 0.7 (seeds fragment_seed + seed_offset + index), all five over the "
    "SAME state and evidence, committed by saea-commit-plurality-support-v1 at min_support 3 (intent: plurality, ties to the lowest sample "
    "index, i.e. the greedy sample; entities: same-type clusters kept at support >= 3). The delivered text is the unnormalised commit (the "
    "loader refuses deliver_normaliser beside a grouped visit; ROLL-2's precedent); v4g, lock v2.2's delivery rule, is applied OFFLINE to "
    f"every custodied raw sample and to the replayed commit. The program is {vf.PROGRAM} (ceiling {vf.CEILING} = 1 + 1 x {vf.SAMPLES}), a "
    "registered member of the review-off module program family; the fragment declares no consumption_module block because the module "
    "compiler has no samples knob and the loader verifies a declared block against its own compilation. This is a POOL cell: it claims no "
    "benefit; the pool is read offline with the existing c3 verdict columns on the same roster."
)

STAGE3_ALGORITHM_NOTE = (
    "VER-1a seals the sampled-answer pool that the inference-time verification family (owner decision 257: scoring and selection "
    "operators over the frozen core's own sampled answers) selects its rule on; no rule is wired or flown here. The cell itself delivers "
    "the registered deterministic plurality commit; the scoring and selection operators are read offline over the custodied raw samples "
    "(scripts/analysis/slurp_sample_aggregation_offline_read.py, slurp_candidate_support_read.py, group_system_rollouts.py)."
)

HELD = (
    " HELD: root countersigns the DRAFT rows, mints the admission receipt "
    "(scripts/flights/ver/ver1a_mint_receipt.py) and re-pins with scripts/flights/repin_cell.py --set-ready "
    "(through scripts/flights/ver/ver1a_flip.sh), which also mints this cell's own first-phase supply under its own "
    "run id (item E16; the first Fold B supply at w_agree 1.0 with the centroid key is the NX R1 / R6 cells' own, so the output digest is "
    "expected to equal theirs and a different digest means the knowledge channel moved -- stop and report); "
    "--allow-output-change must never be passed. Nothing here authorises a flight, a readiness flip or an admission entry."
)


def budgets(kind: str) -> tuple[dict, dict]:
    rows = vf.SMOKE_ROWS if kind == "smoke" else vf.ROWS
    calls = rows * vf.CEILING
    audio = vf.audio_cap(kind)
    gpu = vf.PLANNED_GPU_HOURS_SMOKE if kind == "smoke" else vf.PLANNED_GPU_HOURS_ARM
    fam = {
        "asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0,
        "fit_endpoint_calls_cap": vf.fit_contact_cap(rows),
        "generation_calls_cap": calls,
        "gpu_hours_fit_inclusive": gpu,
        "native_task_contract_calls_cap": calls,
        "official_complete_scoring_jobs": 0 if kind == "smoke" else 1,
        "repeated_speech_audio_seconds_cap": audio,
    }
    plan = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": gpu, "planned_model_calls": calls,
            "planned_speech_audio_seconds": audio, "split_role": "discovery"}
    return fam, plan


def derive_experiment(kind: str) -> str:
    parent = vf.parent_names(kind)["experiment"]
    raw = rd(f"configs/experiment/{parent}.json")
    document = json.loads(substitute(raw))
    names = vf.names(kind)
    document["date"] = vf.DATE
    document["family_budget"], document["execution_plan"] = budgets(kind)
    document["stage3_algorithm"] = {"id": "inference-time-verification-v1", "note": STAGE3_ALGORITHM_NOTE,
                                    "operators_used": ["scoring", "selection"]}
    rows = vf.SMOKE_ROWS if kind == "smoke" else vf.ROWS
    if "generation_budget" in document:
        document["generation_budget"] = {
            "cap": rows * vf.CEILING,
            "definition": (
                f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) with the Solver visit "
                f"grouped at samples {vf.SAMPLES} under program {vf.PROGRAM}: rails.native_episode_config ceiling = perception 1 + "
                f"(max_revisions 0 + 1) x (solver 1 x samples {vf.SAMPLES}) = {vf.CEILING} contacts per row, so {rows:,} x {vf.CEILING} = "
                f"{rows * vf.CEILING:,} is the exact program maximum and the expected spend (one Perception and five Solver contacts per "
                "row; no early exit). The budget is RUN-CUMULATIVE across every attempt of this run id."
            ),
            "target": rows * vf.CEILING,
        }
    cell = document["cells"][0]
    if cell["cell_id"] != names["experiment"] or cell["run_id"] != names["run_id"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r}")
    cell["attempt_id"] = names["attempt_id"]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if kind == "arm" else [])
    agreement = next(r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("FOLD-B-V1/agreement.jsonl"))
    supply = {
        "kind": "preparation",
        "reason": (
            "This cell's OWN prepared first-phase Perception supply, built model-free under its own run id with "
            "core.flight.cli prepare-supply at the flip from the sealed TRAIN Fold B speech-query segment vectors, the "
            "centroid key file SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and the Fold B agreement table, with zero "
            "model, tokenizer, encoder, scorer or server contacts. E16: this cell pins its own. --allow-output-change "
            "must never be passed."
        ),
        "relpath": f"prepared/{names['run_id']}/phase-supply-v1.json",
        "sha256": "0" * 64,
    }
    decision = {
        "kind": "decision", "expected_decision_id": vf.DECISION_ID, "relpath": vf.DECISION_RELPATH, "sha256": "0" * 64,
        "reason": f"Decision {vf.DECISION_ID} pinned by scripts/flights/repin_cell.py.",
    }
    cell["readiness"] = {
        "reason": (
            f"{'Four-row form smoke of cell' if kind == 'smoke' else 'Cell'} {vf.CELL_LABEL} registered before contact on {vf.DATE} by "
            f"script (decision 58) from the committed R6-P1 Fold B fragments and the module compiler: the R5 composed arm (COMP-1b on "
            f"lock v2.2, Reviewer loop off) with the Solver visit grouped at samples {vf.SAMPLES} (sample 0 greedy, samples 1-4 at "
            "temperature 0.7; owner decision 257; five samples per the coordinator ruling after the offline composer read)." + HELD
        ),
        "requirements": [decision, agreement, supply],
        "state": "held",
    }
    if kind == "smoke":
        document["purpose"] = (
            f"Four-row structural form smoke of {vf.CELL_LABEL}: that {vf.PROGRAM} (ceiling {vf.CEILING}) loads, that the Solver visit "
            f"fans out to {vf.SAMPLES} custodied samples with sample 0 at the fragment's temperature 0 and samples 1-4 at 0.7 with the "
            "pinned seeds, that the plurality-support commit at min_support 3 seals and its replay holds, that every request fits, and "
            "that the episode completes. Scored by no one and read by no one: four rows are never evidence of benefit or harm."
        )
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed smoke stops "
            f"cell {vf.CELL_LABEL} and the arm does not open. A form smoke is re-flown whole if it is re-flown at all, under at most "
            "one root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run."
        )
    else:
        document["purpose"] = (
            f"{vf.CELL_LABEL} on TRAIN Fold B 1,080 (owner decision 257: the verification layer of the training-free RL round): seal a "
            "five-sample pool of the lock v2.2 Solver whose sample 0 is the greedy single-sample answer and whose samples 1-4 are "
            "temperature-0.7 draws over the SAME state and evidence, so that VER-1 verification rules (scoring of the sampled answers, "
            "selection among them) can be computed OFFLINE over sealed bytes, together with the existing c3 verdict columns of the NX R1 "
            "and R6 flights on this roster, at the 0.67 pp floor of the offline sealed-pool instrument. The cell is a POOL cell: it "
            "claims no benefit and its in-flight delivered text is the unnormalised plurality commit at min_support 3; the VER-1 rule is "
            "selected in the READ row's offline read and flown, if nominated, under its own registration. Development numbers only "
            "(owner decisions 28 and 86); never a test claim. Nothing here authorises a flight, a readiness flip or an admission entry."
        )
        document["failure_policy"] = document["failure_policy"].replace("NX-R6-PERCEPTION", vf.CELL_LABEL)
    out = f"configs/experiment/{names['experiment']}.json"
    wr(out, dump_like(raw, document))
    return out


def main(argv=None) -> int:
    written = []
    for kind in ("arm", "smoke"):
        written.append(derive_baseline(kind))
        written.append(derive_experiment(kind))
    plan = {"cells": [{"cell": vf.ARM["experiment"], "experiment": vf.ARM["experiment"]}], "schema": "saea-campaign-plan-v1"}
    wr(vf.CAMPAIGN, json.dumps(plan, indent=2) + "\n")
    written.append(vf.CAMPAIGN)
    for path in written:                                       # no inherited identity text may survive the rewrite
        if re.search(r"nx-r6|NX-R6|NX_R6", rd(path)) and not path.startswith("configs/baseline/"):
            raise SystemExit(f"{path}: carries inherited R6 identity text")
    print(json.dumps({"written": written, "program": vf.PROGRAM, "ceiling": vf.CEILING}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
