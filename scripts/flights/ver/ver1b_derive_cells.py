#!/usr/bin/env python3
"""Derive cell VER-1b (the three-sample greedy-first Solver pool on TRAIN Fold A, the confirmation pool) and its four-row smoke.

WHAT THE CELL IS. The review-off COMP-1b module graph exactly as the NX R5 composed arm, the R6-P1 base and the VER-1a base (lock
``v2.2``, ``agree-vote-seed`` + ``centroid-boundary-key`` ON, Reviewer loop OFF, no tool schema on any role) on TRAIN Fold A, with ONE
change at the Solver node: the visit is grouped at ``samples = vf.SAMPLES`` -- sample 0 greedy (``decoding_overrides.greedy_first``), the
rest at temperature 0.7 -- committed by the registered plurality-support policy at ``min_support = vf.MIN_SUPPORT``. See
``ver1b_family.py`` for why the delivered text is the unnormalised commit and v4g is applied offline.

HOW IT IS DERIVED (nothing hand-edited). The committed COMP-1b Fold A baselines (arm / smoke) are the parent: their Fold A pins (the
agreement table, both speech-query pins, the centroid facet pin, the preparation receipts) are the ones the COMP-1b / A2 cells flew.
The module block is the VER-1a / R6-P1 one (the same two components ON, ``admitted_by`` the A2 read, review loop off, lock v2.2) with
the agreement and facet sources taken from the parent; it is compiled by ``rails.consumption_module.compile_module`` into the R5
composed arm's policy blocks (program ``phase-native-module-v1-c2``, ceiling 2), which replace the parent's policy-owned keys on the
parent's roster pins. Then exactly four things change, each asserted below: the policy id (the registered review-off family member for
this ceiling), the absence of a module declaration (the compiler has no ``samples`` knob and the loader verifies a declared block
against its own compilation), the absence of ``deliver_normaliser`` (refused beside a grouped Solver visit), and the Solver role's
``samples`` / ``decoding_overrides`` / ``commit``. The cell's own FIT ids, the removal of the parent's minted ``prepared_phase_supply``
(E16: the flip mints this cell's own) and the label text complete the diff. The structural twin test
(tests/unit/test_ver1b_cell_registration.py) proves the result equals the committed VER-1a Fold B fragment except the Fold A pins and
the sample parameters.

CONFIG ONLY: no contact, no ledger row, no receipt, no flip. Both cells are HELD.

    python -B scripts/flights/ver/ver1b_derive_cells.py
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

import ver1b_family as vf  # noqa: E402

REPO_ROOT = vf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    DECISION_SUPPLY_PATH, carrier_module_hooks,
)

A2_READ = "docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md"


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


#: Longest-first id rewrites from the COMP-1b Fold A fragments to this cell's own.
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


def _node(document: dict, path) -> dict:
    for key in path:
        document = document[key]
    return document


def module_block(parent: dict) -> dict:
    """The base module block: COMP-1b's two components ON (the parent's own Fold A agreement table and centroid facet), lock v2.2,
    review loop OFF; no columns, no template frame (the base is compiled for the R5 composed arm's blocks only)."""

    seed = _node(parent, DECISION_SUPPLY_PATH)
    if vf.FOLD_TOKEN not in seed["agreement_source"]["relpath"]:
        raise SystemExit(f"the parent does not pin the {vf.FOLD_TOKEN} agreement table")
    armed = {
        cm.AGREE_VOTE_SEED: {
            "component_id": cm.AGREE_VOTE_SEED, "state": "on", "admitted_by": A2_READ, "record": A2_READ,
            "params": {"w_agree": seed["rank_weights"]["w_agree"], "k": seed["k"],
                       "agreement_source": copy.deepcopy(seed["agreement_source"])},
        },
        cm.CENTROID_BOUNDARY_KEY: {
            "component_id": cm.CENTROID_BOUNDARY_KEY, "state": "on", "admitted_by": A2_READ, "record": A2_READ,
            "params": {"facet_source": copy.deepcopy(seed["facet_source"])},
        },
    }
    return {
        "module_id": cm.CONSUMPTION_MODULE_ID,
        "profile": "slurp",
        "lock": vf.LOCK,
        "review_loop": "off",
        "components": [armed.get(spec.component_id, {"component_id": spec.component_id, "state": "off"})
                       for spec in cm.COMPONENT_CATALOGUE],
    }


WHAT_THIS_IS = (
    f"{vf.CELL_LABEL} (owner decision 257, 2026-10-10; decision 258 option A: the Fold A confirmation of the verification layer of the "
    f"training-free RL round): the SAMPLE POOL on which the VER-1 rule FIXED on {vf.TUNING_TITLE} (the support filter at n = {vf.RULE_N}, "
    f"s = {vf.RULE_S}, the c3 verdict gated by N1 >= {vf.RULE_THETA:g}, delivered through v4g) is confirmed. THE BASE is the NX R5 composed "
    "arm / the R6-P1 and VER-1a base -- the COMP-1b composition (agree-vote-seed w_agree 1.0, k 60 over the Fold A vote table "
    f"SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-{vf.FOLD_TOKEN}-V1, and centroid-boundary-key SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) as a "
    f"consumption-module block on lock {vf.LOCK}, Reviewer loop OFF (Perception then Solver; no Reviewer or Planner visit; no tool "
    f"schema on any role) -- on {vf.FOLD_TITLE} {vf.ROWS:,}. THE ONE CHANGE: the Solver visit is grouped at samples = {vf.SAMPLES}: sample 0 "
    "GREEDY (decoding_overrides.greedy_first: the fragment's own temperature 0, the answer the lock's single-sample delivery makes) and "
    f"{vf.DRAWN_TEXT} at temperature {vf.SAMPLE_TEMPERATURE:g} (seeds {vf.SEEDS_TEXT}), all over the SAME state and evidence, committed by "
    f"saea-commit-plurality-support-v1 at min_support {vf.MIN_SUPPORT} (intent: plurality, ties to the lowest sample index, i.e. the "
    f"greedy sample; entities: same-type clusters kept at support >= {vf.MIN_SUPPORT}). The delivered text is the unnormalised commit (the "
    "loader refuses deliver_normaliser beside a grouped visit; ROLL-2's precedent); v4g, the lock's delivery rule, is applied OFFLINE to "
    f"every custodied raw sample and to the replayed commit. The program is {vf.PROGRAM} (ceiling {vf.CEILING} = 1 + 1 x {vf.SAMPLES}), a "
    "registered member of the review-off module program family; the fragment declares no consumption_module block because the module "
    "compiler has no samples knob and the loader verifies a declared block against its own compilation. This is a POOL cell: it claims no "
    f"benefit; the pool is read offline with the c3 column of cell VER-1c on the same {vf.FOLD_TITLE} rows, under the rule fixed on {vf.TUNING_TITLE}."
)

STAGE3_ALGORITHM_NOTE = (
    f"{vf.CELL_LABEL} seals the sampled-answer pool on which the inference-time verification family (owner decision 257: scoring and "
    f"selection operators over the frozen core's own sampled answers) is CONFIRMED on {vf.FOLD_TITLE}; no rule is wired or flown here and "
    f"none is tuned on this roster (the rule was fixed on {vf.TUNING_TITLE}). The cell itself delivers the registered deterministic "
    "plurality commit; the scoring and selection operators are applied offline over the custodied raw samples "
    f"({vf.COMPOSER}, scripts/analysis/slurp_sample_aggregation_offline_read.py, slurp_candidate_support_read.py)."
)

HELD = (
    " HELD: root countersigns the DRAFT rows, mints the admission receipt "
    f"(scripts/flights/ver/{vf.SHORT}_mint_receipt.py) and re-pins with scripts/flights/repin_cell.py --set-ready "
    f"(through scripts/flights/ver/{vf.SHORT}_flip.sh), which also mints this cell's own first-phase supply under its own "
    f"run id (item E16; the {vf.FOLD_TITLE} supply at w_agree 1.0 with the centroid key is the COMP-1b / A2 cells' own, so the output digest is "
    "expected to equal COMP-1b's and a different digest means the knowledge channel moved -- stop and report); "
    "--allow-output-change must never be passed. Nothing here authorises a flight, a readiness flip or an admission entry."
)


def derive_baseline(kind: str) -> str:
    parent_name = vf.parent_names(kind)["baseline"]
    raw = rd(f"configs/baseline/{parent_name}.json")
    parent = json.loads(raw)
    block = module_block(parent)
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
    text = dump_like(raw, document)
    if re.search(r"comp1b|COMP1B", json.dumps(document.get("native_contact_fit", {}))):
        raise SystemExit("the FIT block still names the parent cell")
    out = f"configs/baseline/{names['baseline']}.json"
    wr(out, text)
    return out


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
    rows = vf.SMOKE_ROWS if kind == "smoke" else vf.ROWS
    document["date"] = vf.DATE
    document["family_budget"], document["execution_plan"] = budgets(kind)
    document["stage3_algorithm"] = {"id": "inference-time-verification-v1", "note": STAGE3_ALGORITHM_NOTE,
                                    "operators_used": ["scoring", "selection"]}
    population = document["population"]
    if population["count"] != rows or population["dataset_fragment"] != "slurp-speech-native-evo-fold-a-1080":
        raise SystemExit("the parent population is not the Fold A roster")
    population["decision_population"] = (
        f"{vf.FOLD_TITLE}, the rule-confirmation roster ({vf.ROWS:,} rows of {vf.ROSTER['arm']}, {vf.READ_ROSTER}; the unchanged "
        "roster the sealed COMP-1b / A2 Fold A cells flew, so the pool is paired row for row with the Fold A c3 column of cell VER-1c): "
        + (f"{vf.SMOKE_ROWS} rows, the first {vf.SMOKE_ROWS} Fold A rows (the COMP-1b Fold A smoke fragment's own prefix); structural form "
           "proof only, no score and no read." if kind == "smoke" else
           f"the rule (n = {vf.RULE_N}, s = {vf.RULE_S}, theta {vf.RULE_THETA:g}) was FIXED on {vf.TUNING_ROSTER} and nothing is chosen "
           "on this roster."))
    if kind == "arm":
        population["roster_receipt"] = vf.ROSTER["arm"]
    if "generation_budget" in document:
        document["generation_budget"] = {
            "cap": rows * vf.CEILING,
            "definition": (
                f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) with the Solver visit "
                f"grouped at samples {vf.SAMPLES} under program {vf.PROGRAM}: rails.native_episode_config ceiling = perception 1 + "
                f"(max_revisions 0 + 1) x (solver 1 x samples {vf.SAMPLES}) = {vf.CEILING} contacts per row, so {rows:,} x {vf.CEILING} = "
                f"{rows * vf.CEILING:,} is the exact program maximum and the expected spend (one Perception and {vf.SAMPLES_WORD} Solver "
                "contacts per row; no early exit). The budget is RUN-CUMULATIVE across every attempt of this run id."
            ),
            "target": rows * vf.CEILING,
        }
    cell = document["cells"][0]
    if cell["cell_id"] != names["experiment"] or cell["run_id"] != names["run_id"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r}")
    cell["attempt_id"] = names["attempt_id"]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if kind == "arm" else [])
    agreement = next(r for r in cell["readiness"]["requirements"]
                     if r["relpath"].endswith(f"{vf.FOLD_TOKEN}-V1/agreement.jsonl"))
    supply = {
        "kind": "preparation",
        "reason": (
            "This cell's OWN prepared first-phase Perception supply, built model-free under its own run id with "
            f"core.flight.cli prepare-supply at the flip from the sealed {vf.FOLD_TITLE} speech-query segment vectors, the "
            f"centroid key file SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and the {vf.FOLD_TITLE} agreement table, with zero "
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
            f"script (decision 58) from the committed COMP-1b {vf.FOLD_TITLE} fragments and the module compiler: the R5 composed arm (COMP-1b on "
            f"lock {vf.LOCK}, Reviewer loop off) with the Solver visit grouped at samples {vf.SAMPLES} ({vf.SCORING_TEXT}; owner decision 257; "
            f"decision 258 option A, the {vf.FOLD_TITLE} confirmation pool)." + HELD
        ),
        "requirements": [decision, agreement, supply],
        "state": "held",
    }
    if kind == "smoke":
        document["purpose"] = (
            f"Four-row structural form smoke of {vf.CELL_LABEL}: that {vf.PROGRAM} (ceiling {vf.CEILING}) loads, that the Solver visit "
            f"fans out to {vf.SAMPLES} custodied samples with sample 0 at the fragment's temperature 0 and {vf.DRAWN_TEXT} at "
            f"{vf.SAMPLE_TEMPERATURE:g} with the pinned seeds, that the plurality-support commit at min_support {vf.MIN_SUPPORT} seals and its "
            "replay holds, that every request fits, and that the episode completes. Scored by no one and read by no one: four rows are never "
            "evidence of benefit or harm."
        )
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed smoke stops "
            f"cell {vf.CELL_LABEL} and the arm does not open. A form smoke is re-flown whole if it is re-flown at all, under at most "
            "one root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run."
        )
    else:
        document["purpose"] = (
            f"{vf.CELL_LABEL} on {vf.FOLD_TITLE} {vf.ROWS:,} (owner decision 257, decision 258 option A: the Fold A confirmation of the "
            f"verification layer): seal a {vf.SAMPLES_WORD}-sample pool of the lock {vf.LOCK} Solver whose sample 0 is the greedy "
            f"single-sample answer and whose {vf.DRAWN_TEXT} are temperature-{vf.SAMPLE_TEMPERATURE:g} draws over the SAME state and "
            f"evidence, so that the VER-1 rule FIXED on {vf.TUNING_TITLE} (the support filter n = {vf.RULE_N}, s = {vf.RULE_S}, the c3 verdict "
            f"x N1 >= {vf.RULE_THETA:g} gate, v4g at delivery) can be CONFIRMED OFFLINE over sealed bytes, together with the c3 column of "
            f"cell VER-1c on this roster, at the {vf.FLOOR_SLU_PP} pp floor of the offline sealed-pool instrument. The cell is a POOL cell: it "
            f"claims no benefit and its in-flight delivered text is the unnormalised plurality commit at min_support {vf.MIN_SUPPORT}; "
            "nothing is selected or tuned on this roster. Development numbers only (owner decisions 28 and 86); never a test claim. Nothing "
            "here authorises a flight, a readiness flip or an admission entry."
        )
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact; at most one root-diagnosed recovery re-registration; a second failure "
            "closes the cell and the fix is proven on a four-row dry run. No retry, no partial quality read."
        )
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
        if re.search(r"comp1b-fold-a|COMP1B-FOLD-A", rd(path)):
            raise SystemExit(f"{path}: carries inherited COMP-1b Fold A identity text")
    print(json.dumps({"written": written, "program": vf.PROGRAM, "ceiling": vf.CEILING}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
