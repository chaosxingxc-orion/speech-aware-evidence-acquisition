#!/usr/bin/env python3
"""Write the readiness packages of the phase-2 Perception-branch cells P-SV-1 and P-SV-2 (owner decisions 184, 186,
188) from the derived fragments and the measured fit numbers -- config and receipt-pinned bytes only: no adapter
contact, no server, no lock, no model, tokenizer, encoder, embedder or scorer contact. Flips nothing, mints nothing.

Per cell: ``docs/readiness/2026-09-29-slurp-stage3-psvK-fold-b-v1/`` (registered facts with the CANONICAL
``stage3_measurement`` block, protocol, generation/FIT plans for the arm and its four-row smoke, the analysis recipe
naming the READ run id, the root-admission DRAFT, README) and the preregistration beside it. ``--append-ledger``
writes the DRAFT exposure rows (arm, arm FIT, smoke, smoke FIT, READ), replacing in place on re-run.
``--check-dir`` folds the per-phase prompt-budget receipts of an already-run ``core.flight.cli check``.

    python scripts/flights/psv/write_slurp_psv_registration.py --data-root "$SPEECHRL_DATA_DIR" \\
        --study-commit <sha> --registered-at 2026-09-29T00:30:00.000000+00:00 [--check-dir DIR] [--append-ledger]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

import psv_family as ff  # noqa: E402

LEDGER = "docs/exposure-ledger.md"
KINDS = ("arm", "smoke")
PREFIX = {"arm": "", "smoke": "smoke-"}
ANCHOR_N, ANCHOR_SLU = 200, 0.735
FLOOR_SLU = ANCHOR_SLU * math.sqrt(ANCHOR_N / ff.LEDGER_ROWS)
ALLOWED_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "what_this_is", "what_the_train_exemplars_store_is")
RETARGET_PREFIXES = (
    "knowledge_stores.intent-boundaries.phase_supply.perception.agreement_source.",
    "knowledge_stores.intent-boundaries.phase_supply.perception.query_source.",
    "knowledge_stores.train-exemplars.phase_supply.solver.query_source.",
    "preparation_source_receipts",
    "dataset.", "population.", "populations", "split_id", "split_identity_hash", "items", "carrier_",
    # the Fold B dataset view's own top-level identity (configs/dataset/slurp-speech-native-evo-fold-b-1080.json)
    "audio_seconds_total", "d1_manifest_sha256", "d1_media_supplement", "runtime_view_sha256",
    "source_binding_sha256", "split_name",
)
DERIVE_SCRIPT = "scripts/flights/psv/derive_slurp_psv_cells.py"
FIT_SCRIPT = "scripts/flights/psv/psv_fit_measure.py"


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> str:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(path: str, obj: object) -> str:
    return wr(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def identities(key: str) -> dict:
    out = {}
    for kind in KINDS:
        n = ff.names(key, kind)
        experiment = n["experiment"]
        document = json.loads(rd(f"configs/experiment/{experiment}.json"))
        cell = document["cells"][0]
        composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
        parent_id = ff.AGREE[kind]["experiment_id"]
        parent_doc = json.loads(rd(f"configs/experiment/{parent_id}.json"))
        parent_cell = parent_doc["cells"][0]
        parent = compose(REPO_ROOT, parent_cell["model_fragment"], parent_cell["dataset_fragment"],
                         parent_cell["baseline_fragment"], parent_id)
        experiment_keys = set(document) | set(parent_doc)
        a, b = flatten(parent.values), flatten(composed.values)
        changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
        program = [k for k in changed if k == "policy"]
        branches = [k for k in changed if k.startswith("native_episode.roles.perception.branches")]
        bookkeeping = [k for k in changed if k.startswith(ALLOWED_PREFIXES)]
        retarget = [k for k in changed if k.startswith(RETARGET_PREFIXES) and k not in bookkeeping]
        block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in bookkeeping + retarget]
        other = [k for k in changed if k not in program + branches + bookkeeping + retarget + block]
        if other:
            raise SystemExit(f"{key}/{kind}: composed config differs from its AGREE parent beyond the registered change: {other}")
        if program != ["policy"] or composed.values["policy"] != ff.NEW_PROGRAM:
            raise SystemExit(f"{key}/{kind}: the program switch is not the registered one")
        split = document["population"]["split_identity_hash"]
        out[kind] = {
            "experiment": experiment, "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"], "parent_experiment": parent_id,
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "arm": composed.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
            "roster_receipt": document["population"]["roster_receipt"],
            "composed_config_hash": composed.config_hash, "parent_composed_config_hash": parent.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values["native_contact_fit"]), "family_budget": document["family_budget"],
            "execution_profile": document["execution_profile"], "carrier_lock_key": composed.values["carrier_lock_key"],
            "program": composed.values["policy"],
            "branches": composed.values["native_episode"]["roles"]["perception"]["branches"],
            "composed_config_diff_against_the_agree_cell": {
                "program_switch": program, "branch_block": branches, "fold_b_retarget": retarget,
                "bookkeeping": bookkeeping, "experiment_fragment_own_block": block, "anything_else": other},
        }
    return out


def fold_check(key: str, check_dir: str | None, measure: dict) -> dict:
    if not check_dir:
        return {"status": "PENDING_CHECK"}
    out = {"status": "MEASURED_BY_CHECK", "cells": {}}
    contrast_tokens_4b = math.ceil(ff_contrast_chars(measure) / 4)
    for kind in KINDS:
        cell_id = ff.names(key, kind)["experiment"]
        path = Path(check_dir) / f"check-{cell_id}.json"
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            err = Path(check_dir) / f"check-{cell_id}.err"
            tail = err.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-1:] if err.is_file() else []
            out["cells"][kind] = {"status": "MISSING", "path": str(path), "error_tail": tail}
            sibling = Path(check_dir) / f"check-{ff.names('psv2', kind)['experiment']}.json"
            if key == "psv1" and sibling.is_file() and sibling.read_text(encoding="utf-8").strip():
                # P-SV-2's delivering branch A is byte-for-byte P-SV-1's (the two cells differ only in the B
                # branch row), on the same rows; its held check is the best available A-branch Perception fit.
                rows = [r for r in (json.loads(sibling.read_text(encoding="utf-8")).get("preflight") or {}).get("prompt_budget") or ()
                        if r.get("phase") == "perception"]
                if rows:
                    breakdown = rows[0].get("breakdown") if isinstance(rows[0].get("breakdown"), dict) else {}
                    margin = rows[0].get("physical_margin_tokens", breakdown.get("physical_margin_tokens"))
                    if isinstance(margin, int):
                        out["cells"][kind]["top2_contrast_branch_perception_from_psv2_a_branch"] = {
                            "source": str(sibling), "delivering_branch_physical_margin": margin,
                            "contrast_block_allowance_tokens_at_4_bytes": contrast_tokens_4b,
                            "contrast_branch_physical_margin_estimate": margin - contrast_tokens_4b,
                            "note": ("P-SV-1's own check refused at config load (the presentation registry is empty "
                                     "when the loader validates branches); this estimate uses P-SV-2's held check of the "
                                     "identical delivering branch A minus two widest boundary items at 4 bytes per token"),
                        }
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        preflight = report.get("preflight") or {}
        phases = []
        for receipt in preflight.get("prompt_budget") or ():
            entry = {"phase": receipt.get("phase"), "decision": receipt.get("decision")}
            breakdown = receipt.get("breakdown") if isinstance(receipt.get("breakdown"), dict) else {}
            for name in ("physical_margin_tokens", "operational_margin_tokens", "rendered_text_tokens",
                         "required_window_tokens", "completion_token_ceiling", "speech_feature_tokens"):
                if name in receipt:
                    entry[name] = receipt[name]
                elif name in breakdown:
                    entry[name] = breakdown[name]
            phases.append(entry)
        cell = {"check_path": str(path), "blockers": report.get("blockers"),
                "scientific_readiness": report.get("scientific_readiness"), "prompt_budget_per_phase": phases,
                "sample_count": report.get("sample_count"), "config_hash": report.get("config_hash"),
                "protocol_hash": report.get("protocol_hash")}
        perception = [p for p in phases if p.get("phase") == "perception"]
        if key == "psv1" and perception and "physical_margin_tokens" in perception[0]:
            cell["top2_contrast_branch_perception"] = {
                "delivering_branch_physical_margin": perception[0]["physical_margin_tokens"],
                "contrast_block_allowance_tokens_at_4_bytes": contrast_tokens_4b,
                "contrast_branch_physical_margin_estimate": perception[0]["physical_margin_tokens"] - contrast_tokens_4b,
                "note": ("the preflight renders the delivering branch's request only (it knows no branches, and the "
                         "top2-contrast renderer has no table yet); the contrast branch adds at most two sentences, "
                         "bounded here by two widest boundary items at the check's 4-bytes-per-token counter"),
            }
        out["cells"][kind] = cell
    return out


def ff_contrast_chars(measure: dict) -> int:
    return measure["contrast_allowance_items"] * measure["perception"]["boundary_item_chars"]["max"]


def measurement_blocks(key: str, ids: dict, measure: dict) -> dict:
    c = ff.CELLS[key]
    arm, smoke = ids["arm"], ids["smoke"]
    audio = sum(float(i["audio_seconds"]) for i in json.loads(rd(arm["roster_receipt"]))["items"])
    ceiling_rows = c["ceiling_rows"]
    if key == "psv1":
        ceiling = {
            "rows": ceiling_rows, "pp": ff.pp(ceiling_rows), "roster": ff.TUNING_ROSTER,
            "what": (f"the {ceiling_rows} wrong delivered rows with gold at Perception rank 2 on Fold A "
                     f"({ff.pp(ceiling_rows)} pp of 1,080; {ff.RANK2_ALL_ROWS} rank-2 rows overall, "
                     f"{ff.pp(ff.RANK2_ALL_ROWS)} pp level-1 top1 ceiling), {ff.NODE_LEDGER}"),
        }
        basis = ("rank-2 -> rank-1 promotion rate under a top-2 contrast is UNMEASURED; the node ledger's conversion "
                 f"of gold at Perception rank 2 is {ff.CONVERSION['rank2']} % and at rank 1 {ff.CONVERSION['rank1']} % "
                 "(row 139: no prior, so the declaration is 0.0 nominated with the ceiling beside)")
    else:
        ceiling = {
            "rows": ceiling_rows, "pp": ff.pp(ceiling_rows), "roster": ff.TUNING_ROSTER,
            "what": (f"the {ceiling_rows} wrong rows with gold in the boundary block but off Perception's list on Fold A "
                     f"({ff.pp(ceiling_rows)} pp presence ceiling); at the ledger's rank-3 conversion "
                     f"{ff.CONVERSION['rank3']} % the delivered-intent ceiling is about 6 rows (about 0.5 pp), "
                     f"{ff.NODE_LEDGER}"),
        }
        basis = ("the presence gain of a forced three-candidate list and its conversion are UNMEASURED; spec section 6 "
                 "notes only the 270 Fold A rows with lists of one (35) or two (235) can change (row 139: no prior, so "
                 "the declaration is 0.0 nominated with the ceiling beside)")
    note = (
        f"Phase-2 cell {c['label']} (level 2, K = 3). Expected effect declared from the ledger's measured numbers: "
        f"ceiling {ceiling['what']}; conversion basis: {basis}. expected_effect_pp 0.0 sits below this design's "
        f"provisional floor {FLOOR_SLU:.4f} pp (0.735 x sqrt(200 / 1080), the ROLL-AA anchor the gate registers for "
        f"{ff.MEASUREMENT_DESIGN}), so claims_benefit is false; the read's bar is the twin (T) null measured in this "
        "flight, per metric |T - A offset| + its CI95 half-width. The delivered row is branch A: delivered intent and "
        "SLU are identical by construction at the request level (reported, never contrasted). Tuning roster TRAIN "
        "Fold A (the node ledger shaped the design), read roster TRAIN Fold B (ruling O2; owner decision 186: "
        "rollout-exposed only, no branch value built from Fold B rollouts)."
    )
    return {
        arm["run_id"]: {
            "measurement_design": ff.MEASUREMENT_DESIGN, "rows": arm["rows"], "level": ff.LEVEL,
            "expected_effect_pp": 0.0, "claims_benefit": False, "claim": "nominated",
            "primary_metric": c["primary_metric"], "aa_arm_id": ff.ARM_T,
            "tuning_roster": ff.TUNING_ROSTER, "read_roster": ff.READ_ROSTER,
            "ceiling": ceiling, "conversion_basis": basis,
            "variant_cost": {
                "extra_contacts_per_row": 4, "extra_perception_contacts_per_row": 2, "extra_solver_contacts_per_row": 2,
                "extra_audio_seconds": round(4 * audio, 3), "extra_audio_seconds_per_row_mean": round(4 * audio / arm["rows"], 4),
                "note": ("K - 1 = 2 non-A branches (B and the twin T), each one Perception contact at the one Perception "
                         "visit and one Solver contact at the first Solver visit (level 2); every contact re-sends the "
                         f"row's speech packet, so 2 x row audio per branch, 4 x the Fold B total {audio} s per flight"),
            },
            "provisional_floor_pp": {"slu_f1": round(FLOOR_SLU, 4), "intent_accuracy": 0.0,
                                     "arithmetic": f"{ANCHOR_SLU} * sqrt({ANCHOR_N} / 1080) = {FLOOR_SLU:.4f} pp (ROLL-AA anchor, provisional)"},
            "read_bar": "|twin offset| + twin CI95 half-width, per metric, measured in this flight (ruling O6: one twin)",
            "note": note,
        },
        smoke["run_id"]: {
            "measurement_design": "form-proof", "rows": smoke["rows"], "expected_effect_pp": 0.0, "claims_benefit": False,
            "primary_metric": "none (structural form only)", "tuning_roster": "none", "read_roster": ff.READ_ROSTER,
            "note": ("Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the 15-ceiling "
                     "pbranch3-l2 program loads, the Perception branches fan out at the one visit and the non-A branches "
                     "take one first-visit Solver contact each, every branch fits its measured bound, the "
                     "perception-branch receipt and I7v seal, and the episode completes. Scored by no one, read by no one."),
        },
    }


def decision_rule(key: str) -> str:
    c = ff.CELLS[key]
    b = c["b_branch"]
    common = (
        f"SAME-FLIGHT PERCEPTION-BRANCH READ (owner decision 184; level 2; claim ceiling 'nominated', ruling O1). Per "
        f"branch ({ff.ARM_A} delivering, {b}, {ff.ARM_T}): the sealed branch note's candidate list gives gold's rank "
        "(1/2/3/absent), top1 and present offline (gold enters only offline); the branch's level-2 first-visit Solver "
        "answer is rendered through the delivered row's normaliser and projection and scored ONCE with "
        f"{ff.SCORER} (score_complete_derived_copy); A's column is A's own first Solver answer. Every contrast is a "
        "paired ROW bootstrap (cluster key sample_id, 10,000 draws, seed 20260929); the utterance-level number is "
        "reported beside and never gates. (1) THE TWIN NULL: T minus A per metric; the bar = |T - A offset| + its CI95 "
        f"half-width, reported beside the provisional floor {FLOOR_SLU:.4f} pp. "
    )
    if key == "psv1":
        return common + (
            f"(2) THE CONTRAST: {b} minus A on the level-2 branch Solver column's official intent accuracy (primary). "
            "NOMINATED iff the intent CI95 lower bound is above zero AND the point delta exceeds the twin's intent bar "
            "AND the SLU-F1 CI95 lower bound of the same column is not below minus the twin's SLU bar (guard). "
            "BRANCH-LOCAL HARM iff the intent CI95 upper bound is below zero and the point magnitude exceeds the twin "
            "bar. Otherwise NOT NOMINATED. Reported beside, never gating: gold-on-list and mean gold rank of the B note "
            "vs A and T, the conversion P(correct | gold rank r in the branch note) against the ledger's 97.57 / 26.98 / "
            "12.0 %, the rows where top2-contrast-v1 rendered nothing (presentation_skip_reason, ruling O5), and the "
            "delivered row (identical by construction). A nomination sends the composed policy to a full-system "
            "cross-flight read against an in-chain A/A; it admits nothing."
        )
    return common + (
        f"(2) PRESENCE: {b} minus A on gold-on-list (present) in the branch note (primary, ruling O4). NOMINATED (as a "
        "presence change) iff the present CI95 lower bound is above zero AND the point delta exceeds the twin's present "
        "bar. Reported beside, never gating: official intent accuracy and SLU-F1 of the level-2 branch Solver column "
        "(B vs A vs T), list size, gold rank, and the conversion of gold at rank 3. A presence nomination opens no "
        "system claim: it only informs a later level-2 intent cell on the same pair."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/psv")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-psv")
    parser.add_argument("--check-dir", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    parser.add_argument("--cells", default="psv1,psv2")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    data = Path(args.data_root)
    measure = json.loads((data / ff.FIT_MEASURE).read_text(encoding="utf-8"))
    summary = {}
    for key in args.cells.split(","):
        summary[key] = write_cell(key, args, data, measure)
    print(json.dumps(summary, indent=2))
    return 0


def write_cell(key: str, args, data: Path, measure: dict) -> dict:
    c = ff.CELLS[key]
    n = ff.names(key, "arm")
    package, prereg = n["package"], n["prereg"]
    ids = identities(key)
    arm, smoke = ids["arm"], ids["smoke"]
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    group = arm["branches"]
    fit = fold_check(key, args.check_dir, measure)
    rule = decision_rule(key)
    measurement = measurement_blocks(key, ids, measure)
    contrast_pin = {
        "presentation_id": "top2-contrast-v1",
        "table_relpath": ff.CONTRAST_PAIR_PLACEHOLDER, "sha256": ff.CONTRAST_PAIR_PLACEHOLDER,
        "builder": ff.CONTRAST_PAIR_BUILDER, "status": "PLACEHOLDER: the builder has not landed on fable/svphase2",
        "requirements": ("built model-free (W3a's word-gap method) over the R01-excluded TRAIN pool with its own "
                         "receipt; its pool must be proven disjoint from TRAIN Fold B by utterance identity before the "
                         "flip (phase-2 inputs README: 'Not checked here: a contrast-pair pool'); the pin enters where "
                         "the runtime reads it (merge set C item 4/6), then the cell is re-derived and re-pinned"),
    } if key == "psv1" else None
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": f"Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block {ff.GATE} and scripts/checks/flight_registration_check.py resolve (keyed by run id).",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "184": f"register {c['label']} on TRAIN Fold B at level 2, claim nominated (phase 2 of the same-flight instrument)",
            "186": "Fold B is ROLLOUT-exposed while it is the phase-2 read roster; no branch value of a cell read on Fold B is built from Fold B rollouts",
            "188": "B5 (Reviewer top-2 contrast) deferred behind P-SV-1 / P-SV-2",
            "139": "no prior: the expectation is declared from measured ledger numbers (0.0 nominated, ceiling beside)",
            "28/86": "TRAIN numbers are development numbers, never a test claim",
        },
        "rows": arm["rows"], "stage3_measurement": measurement,
        "the_cell": {
            "base": f"the retained AGREE arm {ff.AGREE_RUN} ({ff.AGREE_PACKAGE}), re-targeted Fold A -> Fold B as the filler family re-pointed it",
            "program_switch": f"policy {ff.BASE_PROGRAM} (ceiling 11) -> {ff.NEW_PROGRAM} (ceiling 15 = 11 + 2 (K - 1), K = 3, level 2; the fragments differ only in program_id and max_contacts)",
            "branch_block": group,
            "branches": {
                ff.ARM_A: "A, delivering, LAST, no axis: AGREE's Perception evidence as flown (intent-boundaries k 60, fuse 8/1/8, rank w_cos 1.0 / w_prior 0.0 / w_agree 1.0 over the Fold B agreement table); continues through Solver/Reviewer/Planner and delivers",
                c["b_branch"]: ("B, one axis: presentation_id top2-contrast-v1 (rails/perception_presentations.py) -- the same boundary ids as A plus one contrast block for the branch's rank-1/rank-2 pair from the pinned contrast-pair table; renders nothing for a pair under the pool-support floor (ruling O5)"
                                if key == "psv1" else
                                "B, one axis: response-contract min_candidates 3 (slurp-intent-hypotheses-v1; max_candidates 3) -- the same boundary ids as A, a forced three-candidate hypothesis list"),
                ff.ARM_T: f"T, replicate_of {ff.ARM_A}: no axis, A's request byte for byte in the same batch -- the read's own null (ruling O6: one twin)",
            },
            "estimand": "per branch, the Perception note (gold rank / present / top1, offline) and the level-2 branch Solver answer at the first Solver visit; never the delivered full-system answer",
            "fold_b_retarget": {
                "dataset_fragment": ff.DATASET_FRAGMENT, "split_id": ff.SPLIT_ID, "roster": ff.ROSTER["arm"]["relpath"],
                "agreement_table": {k: ff.AGREEMENT[k] for k in ("relpath", "sha256", "ledger_row")},
                "boundary_query_and_content_query": f"copied from {ff.FILLER_C01_BASELINE} (the filler family's Fold B pins)",
                "inputs_readme": ff.AGREEMENT["inputs_readme"],
            },
        },
        "contrast_pair_table": contrast_pin,
        "fit_measure": {"relpath": ff.FIT_MEASURE, "sha256": sha_file(data / ff.FIT_MEASURE), "tool": FIT_SCRIPT,
                        "summary": {k: measure[k] for k in ("chars_per_token_least_squares", "perception", "fit_estimate",
                                                            "prompt_limit_tokens", "headroom_items", "contrast_allowance_items",
                                                            "max_supplied_items", "estimates", "first_solver_visit_prompt_tokens")}},
        "fit": fit,
        "identity": {kind: {k2: v for k2, v in ids[kind].items() if k2 != "composed_config_diff_against_the_agree_cell"} for kind in KINDS},
        "composed_config_diff_against_the_agree_cell": {kind: ids[kind]["composed_config_diff_against_the_agree_cell"] for kind in KINDS},
        "decision_rule": rule,
        "budget_arithmetic": {"arm_family_budget": caps, "smoke_family_budget": smoke_caps,
                              "note": "the AGREE arithmetic at ceiling 15 with the Fold B audio: generation rows x 15, FIT rows x 15 x 4, speech ceil(audio x 15), GPU hours 12.0 x 15 / 11 = 16.4 (smoke 1.0); native task-contract calls + 4 per row; run-cumulative"},
        "prohibitions": [
            "No test-split, DEV or Fold A contact or read (Fold A is the tuning roster and is not re-flown).",
            "No re-flying of the sealed AGREE arm.", "No second factor: one axis on the B branch, none on A or T.",
            "No paper-scale profile.", "No flight before root mints the decision receipt and the cells are flipped.",
            "No branch score opened before the READ row is root countersigned.",
            "No system-level claim: a branch effect may only nominate (ruling O1).",
            "No branch value built from Fold B rollouts (owner decision 186).",
        ],
    }
    facts_sha = wjson(package + "/registered-facts-v1.json", facts)
    protocol = {
        "schema": "saea-registered-protocol-v1", "protocol_id": f"slurp-stage3-{c['slug']}-protocol-v1",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": c["question"],
        "one_factor": f"branch {c['b_branch']}: " + ", ".join(f"{k} {v}" for k, v in ff.CELLS[key]["b_axis"].items()) + f"; the Fold B re-target and the program switch to {ff.NEW_PROGRAM} are the instrument's carrier, shared by every branch",
        "cells": {kind: {k2: ids[kind][k2] for k2 in ("cell", "experiment", "run_id", "attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash")}
                  | {"fit_run_id": ids[kind]["fit"]["run_id"], "fit_attempt_id": ids[kind]["fit"]["attempt_id"]} for kind in KINDS},
        "decision_rule_fixed_here": rule,
        "development_numbers_only": "Every number is a TRAIN Fold B development number (owner decisions 28 and 86), never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(package + "/protocol-registered-v1.json", protocol)
    plan_shas: dict[str, str] = {}
    for kind in KINDS:
        identity = ids[kind]
        budget = identity["family_budget"]
        for plan in ("generation", "fit"):
            is_fit = plan == "fit"
            run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
            plan_doc = {
                "schema": f"saea-registered-{plan}-plan-v1", "plan_kind": plan, "cell": identity["cell"],
                "experiment": identity["experiment"], "composed_config_hash": identity["composed_config_hash"],
                "registered_at_utc": args.registered_at, "status": protocol["status"], "source_tree": protocol["source_tree"],
                "preparation_base_commit": args.study_commit, "expected_session_id": ff.SESSION,
                "unused_budget_is_not_attempt_authority": True,
                "execution_plan": {
                    "schema": "saea-execution-plan-v1", "study": "speech-aware-evidence-acquisition",
                    "carrier_lock_key": identity["carrier_lock_key"], "run_id": run_id,
                    "attempt_id": identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"],
                    "execution_profile": identity["execution_profile"], "split_role": "discovery",
                    "split_identity_hash": identity["split_identity_hash"], "protocol_hash": identity["protocol_hash"],
                    "planned_model_calls": budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"],
                    "planned_speech_audio_seconds": budget["repeated_speech_audio_seconds_cap"],
                    "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
                },
                "family_budget": budget,
                "execution_route": (
                    "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation." if is_fit else
                    f"Shared core.flight.cli campaign over {n['campaign']} (this arm alone; no A/A cell -- the twin branch T flies inside every row) through scripts/flights/psv/batch_chain_psv.sh and the batch driver." if kind == "arm" else
                    "Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored."
                ),
                "prepared_phase_supply": {"relpath": f"prepared/{identity['run_id']}/phase-supply-v2.json", "sha256": "MINTED_AT_THE_FLIP",
                                          "note": "the first Fold B first-phase supply at w_agree 1.0 on this roster; branch A's router must reproduce it on every row (spec section 3, AT-P6)"},
                "protocol_document": {"relpath": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "one_factor": protocol["one_factor"],
                "purpose": f"{run_id}: " + ("request envelopes only; reads nothing." if is_fit else rule if kind == "arm" else "structural form proof only: no score and no read."),
                "quality_read_gate": f"No branch column is opened before the complete sealed manifest, the ordered outputs, the phase summary and the single complete official TRAIN score of the flight exist AND the READ row {n['read_run']} is root countersigned.",
            }
            plan_shas[run_id] = wjson(f"{package}/{PREFIX[kind]}{plan}-plan-registered-v1.json", plan_doc)
    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1", "recipe_id": f"slurp-stage3-{c['slug']}-branch-analysis-v1",
        "title": f"Cell {c['label']} -- the same-flight Perception-branch read: B ({c['b_branch']}) and the twin T, each against the delivering branch A, level 2",
        "registered_at_utc": args.registered_at, "read_run_id": n["read_run"],
        "run_ids": {"read": n["read_run"], "arm": arm["run_id"], "context_comparator": ff.AGREE_RUN},
        "arms": {
            "arm": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "branch": c["b_branch"], "role": "the treatment branch"},
            "in_chain_replicate": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "branch": ff.ARM_A, "role": "the delivering branch: LEFT of both contrasts"},
            "twin": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "branch": ff.ARM_T, "role": "the in-flight twin: RIGHT of the null contrast"},
        },
        "passes": {"branch": {"left": ff.ARM_A, "right": c["b_branch"], "gating": True},
                   "twin-null": {"left": ff.ARM_A, "right": ff.ARM_T, "gating": "sets the bar"}},
        "resampling": {"bootstrap_draws": 10000, "seed": 20260929, "unit": "row (paired)", "cluster_key": "sample_id",
                       "metrics": ["scenario_action_exact", "slu_f1_f1", "present", "top1", "gold_rank"],
                       "utterance_level": "reported beside, never gating"},
        "decision_rule": rule,
        "steps": [
            f"0. Refuse unless the READ row {n['read_run']} is root countersigned.",
            "1. Refuse unless the flight carries a COMPLETE sealed 1,080-row manifest with one complete official TRAIN score, the saea-perception-branch-arms-v1 receipt on every row and I7v's Perception path verified by the bundle.",
            f"2. Level 1 (note): per branch gold rank / present / top1 from the sealed note (gold offline); {ff.READ_ANALYSIS} refuses unless branch A reproduces the ledger driver's P-node counting.",
            f"3. Level 2 (answer): render each branch's first-visit Solver answer through the delivered row's normaliser and projection and score it ONCE with {ff.SCORER} (never sharded).",
            "4. Twin null (T vs A), then B vs A under the rule; per-scenario tables in both weightings.",
        ],
        "read_driver": f"scripts/flights/psv/psv_read.sh {key} -> {ff.READ_ANALYSIS} (not yet landed at registration; merge set C item 1)",
        "output": {"analysis_root": f"analysis/{n['read_run']}"},
        "boundary": "A development read on a TRAIN fold (owner decisions 28 and 86); never a test claim; branch-local, never a system-level claim. No utterance text, transcript, gold label or model output is printed or persisted.",
    }
    recipe_sha = wjson(package + "/analysis-recipe-v1.json", recipe)
    eligible = [arm["run_id"], arm["fit"]["run_id"], smoke["run_id"], smoke["fit"]["run_id"]]
    draft = {
        "_draft_note": "A DRAFT for root to mint on the data root with scripts/flights/psv/psv_mint_receipt.py (status decided, recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1", "decision_id": n["decision_id"], "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None, "owner": "root", "coordinator": "Fable5.1", "eligible_run_ids": eligible,
        "cell_kind": f"Stage-3 same-flight Perception-branch instrument cell (phase 2, level 2, label none), claim ceiling 'nominated'. One arm on TRAIN Fold B 1,080 with three Perception branches ({c['b_branch']}, {ff.ARM_T}, {ff.ARM_A} delivering), and a four-row form smoke.",
        "decision": f"Fly cell {c['label']}: the Fold B AGREE arm under {ff.NEW_PROGRAM} with a level-2 Perception branch block; read {c['b_branch']} and {ff.ARM_T} against {ff.ARM_A} in the same flight; nominate or not at the twin bar.",
        "authorization_basis": f"Owner decisions 184, 186, 188 (and 172 for the instrument), 139, 28/86; the spec {ff.SPEC} with rulings O1-O6.",
        "antecedents": {
            "owner_decisions": {"path": ff.OWNER_DECISIONS, "sha256": sha_file(ff.OWNER_DECISIONS)},
            "spec": {"path": ff.SPEC, "sha256": sha_file(ff.SPEC)},
            "node_ledger": {"path": ff.NODE_LEDGER, "sha256": sha_file(ff.NODE_LEDGER)},
            "fold_b_inputs": {"path": ff.AGREEMENT["inputs_readme"], "sha256": sha_file(ff.AGREEMENT["inputs_readme"])},
            "preregistration": {"path": prereg, "sha256": None},
            "readiness_readme": {"path": package + "/README.md", "sha256": None},
            "protocol": {"path": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": package + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": package + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "derive_script": {"path": DERIVE_SCRIPT, "sha256": sha_file(DERIVE_SCRIPT)},
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k2: caps[k2] for k2 in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No system-level, superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; a branch read on a development fold whose ceiling is 'nominated'.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": ["any flight before the cells are flipped and the receipt is minted", "touching the resident np4 session by anyone but the coordinator", "any ASR, transcript, encoder or paid-API contact", "re-flying or re-scoring any sealed cell", "--allow-output-change on the re-pin tool", "any change beyond the registered re-target, program switch and branch block", "opening a branch column before the READ row is countersigned"]
        + (["flipping P-SV-1 while its contrast-pair table pin is the placeholder " + ff.CONTRAST_PAIR_PLACEHOLDER] if key == "psv1" else []),
        "population": {"count": arm["rows"], "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "fold_a_contact_authorized": False, "test_contact_authorized": False},
        "registered_hashes": {kind: {"composed_config": ids[kind]["composed_config_hash"], "protocol": ids[kind]["protocol_hash"]} for kind in KINDS},
        "service": {"expected_session_id": ff.SESSION, "model_fragment": arm["model_fragment"], "slots": 4, "slot_tokens": 24576, "no_child_start_stop": True},
    }
    draft_sha = wjson(package + "/root-admission-draft-v1.json", draft)
    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    readme, prereg_text = render_docs(key, args, ids, group, measure, fit, rule, fence, caps, smoke_caps, measurement)
    wr(package + "/README.md", readme)
    wr(prereg, prereg_text)
    ledger = append_ledger(key, args, ids, plan_shas, group, measurement) if args.append_ledger else "not-requested"
    return {"package": package, "ledger": ledger, "fit": fit.get("status"),
            "identity": {kind: {"run_id": ids[kind]["run_id"], "composed": ids[kind]["composed_config_hash"],
                                "protocol": ids[kind]["protocol_hash"]} for kind in KINDS},
            "facts": facts_sha, "recipe": recipe_sha, "draft": draft_sha}


def _fit_lines(fit: dict) -> str:
    if fit.get("status") != "MEASURED_BY_CHECK":
        return "PENDING: core.flight.cli check not yet folded in."
    lines = ["| cell | phase | decision | rendered (4 B/token) | operational margin | physical margin |",
             "| --- | --- | --- | ---: | ---: | ---: |"]
    for kind, cell in fit["cells"].items():
        if cell.get("status") == "MISSING":
            lines.append(f"| {kind} | check | MISSING | | | |")
            continue
        for p in cell.get("prompt_budget_per_phase", []):
            lines.append(f"| {kind} | {p.get('phase')} | {p.get('decision')} | {p.get('rendered_text_tokens')} | {p.get('operational_margin_tokens')} | {p.get('physical_margin_tokens')} |")
        lines.append(f"| {kind} | blockers | {json.dumps(cell.get('blockers'))} | | | |")
        contrast = cell.get("top2_contrast_branch_perception")
        if contrast:
            lines.append(f"| {kind} | perception, top2-contrast branch (estimate) | margin {contrast['delivering_branch_physical_margin']} - {contrast['contrast_block_allowance_tokens_at_4_bytes']} | | | {contrast['contrast_branch_physical_margin_estimate']} |")
    return "\n".join(lines)


def render_docs(key, args, ids, group, measure, fit, rule, fence, caps, smoke_caps, measurement):
    c = ff.CELLS[key]
    n = ff.names(key, "arm")
    arm, smoke = ids["arm"], ids["smoke"]
    m = measurement[arm["run_id"]]
    rows = ["| branch | order | role | axis | max_supplied_items |", "| --- | ---: | --- | --- | ---: |"]
    for index, row in enumerate(group["branches"]):
        role = "delivering (A)" if row.get("deliver") else (f"twin of `{row['replicate_of']}` (T)" if row.get("replicate_of") else "B")
        axis = ", ".join(f"`{k}` {v}" for k, v in row.items() if k in ("presentation_id", "min_candidates", "overrides", "release_swap")) or "none"
        rows.append(f"| `{row['branch_id']}` | {index} | {role} | {axis} | {row['max_supplied_items']} |")
    fe = group["fit_estimate"]
    placeholder = (
        f"\n**Depends on the merge-set-C agent.** The `top2-contrast-v1` renderer reads a pinned contrast-pair table built "
        f"by `{ff.CONTRAST_PAIR_BUILDER}`, which has not landed; the pin is registered as `{ff.CONTRAST_PAIR_PLACEHOLDER}` "
        "in `registered-facts-v1.json` (`contrast_pair_table`). The branch schema carries no table field yet, so the "
        "pin enters where the runtime reads it (merge set C items 4/6); then this cell is re-derived and re-pinned, and "
        "the table's pool is proven disjoint from Fold B. The cell must not be flipped while the placeholder stands.\n"
        if key == "psv1" else "")
    readme = f"""# Cell {c['label']}: phase-2 same-flight Perception branches on TRAIN Fold B (owner decisions 184, 186, 188)

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (branch `{args.branch}`);
both cells **held**. Nothing here authorises a flight, a flip or an admission entry. Development numbers only.

**The question.** {c['question']}

**The base and the three registered changes.** The retained AGREE arm (`{ff.AGREE_RUN}`) with:
(1) the Fold A -> Fold B re-target the filler family used (dataset `{ff.DATASET_FRAGMENT}`, roster
`{ff.ROSTER['arm']['relpath']}`, the two speech-query pins copied from `{ff.FILLER_C01_BASELINE}`, the agreement table
`{ff.AGREEMENT['relpath']}` (`{ff.AGREEMENT['sha256'][:8]}`, ledger row `{ff.AGREEMENT['ledger_row']}`, cited not
re-registered), the preparation receipts); (2) the program switch `{ff.BASE_PROGRAM}` (11) -> `{ff.NEW_PROGRAM}`
(15 = 11 + 2 (K - 1)); (3) the branch block `native_episode.roles.perception.branches` (level {group['level']}):

{chr(10).join(rows)}

`fit_estimate`: slot {fe['slot_tokens']}, completion {fe['completion_ceiling']}, base prompt {fe['base_prompt_tokens']},
{fe['tokens_per_supplied_item']} tokens per supplied item -- MEASURED on the sealed AGREE arm's 1,080 Perception contacts
(`{FIT_SCRIPT}`; realised Perception prompt {measure['perception']['prompt_tokens']['min']}-{measure['perception']['prompt_tokens']['max']}
tokens, {measure['perception']['items']['max']} boundary items max, widest item {measure['perception']['boundary_item_chars']['max']} characters,
{measure['chars_per_token_least_squares']} characters per token); branch estimates {json.dumps(measure['estimates'])} against the
{measure['prompt_limit_tokens']}-token prompt limit.
{placeholder}
**Measurement.** `measurement_design` `{ff.MEASUREMENT_DESIGN}` (the spelling `{ff.GATE}` and
`scripts/checks/flight_registration_check.py` register; the spec's section 4 says `same-flight-perception-branch`,
and the gate comment flags the reconciliation), level {ff.LEVEL}, claim **`nominated`**, `aa_arm_id` `{ff.ARM_T}`,
`tuning_roster` `{ff.TUNING_ROSTER}`, `read_roster` `{ff.READ_ROSTER}`. Primary: {c['primary_metric']}.
Expected effect **0.0** (nominated); ceiling {m['ceiling']['what']}. Conversion basis: {m['conversion_basis']}.
Provisional floor {FLOOR_SLU:.4f} pp; the bar is the twin null. `variant_cost`: +2 Perception and +2 Solver contacts per
row, +{m['variant_cost']['extra_audio_seconds']} speech seconds per flight (2 x row audio per non-A branch).

## Decision rule (fixed here)

{rule}

## Fit (core.flight.cli check, held)

{_fit_lines(fit)}

The first Solver visit's realised prompt on the AGREE arm was {measure['first_solver_visit_prompt_tokens']['min']}-{measure['first_solver_visit_prompt_tokens']['max']} tokens;
a branch Solver contact carries a branch note of the same shape in place of A's.

## Sequence

(1) Root countersigns the four DRAFT flight rows (the READ row `{n['read_run']}` stays draft until the seal) and mints
`{n['decision_relpath']}` with `scripts/flights/psv/psv_mint_receipt.py {key}`. (2) `bash scripts/flights/psv/psv_flip.sh`
(loop form, both P-SV cells, one HEAD). (3) `bash scripts/flights/psv/batch_chain_psv.sh` on slurp-np4 through the batch
driver (P-SV-1 then P-SV-2, each smoke first). (4) `bash scripts/flights/psv/psv_read.sh {key}`.

**Budgets.** Arm {caps['generation_calls_cap']:,} generation contacts (1,080 x 15), {caps['fit_endpoint_calls_cap']:,} FIT
endpoints, {caps['repeated_speech_audio_seconds_cap']:,} speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours; smoke
{smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} / {smoke_caps['gpu_hours_fit_inclusive']}.
Expected spend about 8.06 contacts per row (AGREE's 4.06 + 4).
"""
    prereg = f"""# Cell {c['label']} (phase-2 Perception branches, level 2): preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the retained AGREE
arm fragments by script (decision 58) under owner decisions 184, 186 and 188. Development numbers only.

| item | value |
| --- | --- |
| base | the AGREE arm `{ff.AGREE_RUN}` re-targeted to TRAIN Fold B |
| program | `{ff.NEW_PROGRAM}` (ceiling 15, level 2, K = 3) |
| branches | `{c['b_branch']}` ({', '.join(f'{k} {v}' for k, v in c['b_axis'].items())}), `{ff.ARM_T}` (twin), `{ff.ARM_A}` (delivering) |
| design / claim | `{ff.MEASUREMENT_DESIGN}` / `nominated` |
| primary | {c['primary_metric']} |
| expected effect | 0.0 pp, `claims_benefit` false; ceiling {m['ceiling']['rows']} rows = {m['ceiling']['pp']} pp on Fold A |
| rosters | tuning `{ff.TUNING_ROSTER}`; read `{ff.READ_ROSTER}` |
| runs | `{arm['run_id']}` / `{arm['fit']['run_id']}`; `{smoke['run_id']}` / `{smoke['fit']['run_id']}`; read `{n['read_run']}` |
| composed config hashes | arm `{arm['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |
| protocol hashes | arm `{arm['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |
| split identity | arm `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |

## Decision rule (fixed here)

{rule}

## The measurement declaration

```json
{fence}
```
"""
    return readme, prereg


MODEL_TOOL = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any role; "
              "prompt bytes the retained AGREE arm's re-targeted to Fold B; three Perception branches at the one Perception visit, level 2")
INHERITED = ("TRAIN Fold B discovery rows already exposed by SAEA-SLURP-EVO-FOLD-PACKETS-V2, SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2, the EVO-S1 "
             "confirmation fold SAEA-SLURP-EVO-S1-FOLD-B-V2 (8,640 contacts, 2026-09-06), the encoder pass SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1 "
             "and the model-free W2 offline guard read against Fold B gold; the filler family is registered on these rows (rollout-exposed only, owner decision 186). "
             "This cell opens no split. Prior exposure is inherited in full.")


def append_ledger(key, args, ids, plan_shas, group, measurement) -> str:
    c = ff.CELLS[key]
    n = ff.names(key, "arm")
    text = rd(LEDGER)
    eligible = [ids["arm"]["run_id"], ids["arm"]["fit"]["run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit"]["run_id"]]
    branches = "; ".join(f"{r['branch_id']} max_supplied_items {r['max_supplied_items']}" for r in group["branches"])
    m = measurement[ids["arm"]["run_id"]]

    def notes(kind: str, plan: str) -> str:
        identity = ids[kind]
        run_id = identity["fit"]["run_id"] if plan == "fit" else identity["run_id"]
        attempt = identity["fit"]["attempt_id"] if plan == "fit" else identity["attempt_id"]
        declaration = (f"measurement_design {ff.MEASUREMENT_DESIGN}, level 2, claim nominated, claims_benefit false, expected_effect_pp 0.0 "
                       f"(ceiling {m['ceiling']['rows']} rows = {m['ceiling']['pp']} pp on Fold A), provisional floor {FLOOR_SLU:.4f} pp, bar = the twin null, "
                       f"aa_arm_id {ff.ARM_T}, tuning_roster {ff.TUNING_ROSTER}, read_roster {ff.READ_ROSTER}, variant_cost +2 Perception and +2 Solver contacts per row, rows 1080"
                       if kind == "arm" else f"measurement_design form-proof, claims_benefit false, expected_effect_pp 0.0, rows 4, tuning_roster none, read_roster {ff.READ_ROSTER}")
        placeholder = (f" P-SV-1's top2-contrast-v1 branch waits for its contrast-pair table ({ff.CONTRAST_PAIR_BUILDER}; pin {ff.CONTRAST_PAIR_PLACEHOLDER}); no flip before it is pinned." if key == "psv1" else "")
        return (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit} by the P-SV "
            f"registration agent (worktree {args.worktree}, branch {args.branch}). This registration performs no contact and authorises none. Plan SHA256 "
            f"{plan_shas[run_id]}; attempt {attempt}. Protocol hash {identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected "
            f"session {ff.SESSION} (attach only). READINESS HELD: root mints {n['decision_relpath']} (decision id {n['decision_id']}) with the four eligible run ids "
            f"{', '.join(eligible)}, then scripts/flights/psv/psv_flip.sh re-pins with scripts/flights/repin_cell.py --set-ready, minting each cell's own first-phase "
            f"supply (item E16); --allow-output-change must never be passed. Every hash in this row moves at the flip. OWNER DECISIONS 184, 186, 188: cell {c['label']}, the "
            f"AGREE arm re-targeted to TRAIN Fold B (agreement table {ff.AGREEMENT['ledger_row']}, cited), program {ff.NEW_PROGRAM} (ceiling 15) and a level-2 "
            f"Perception branch block, branches in order {branches}. Measurement declaration ({ff.GATE}): {declaration} -- canonical in {n['package']}/registered-facts-v1.json."
            f"{placeholder} Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. No test-split, DEV or Fold A contact."
        )

    def flight_row(kind: str, plan: str) -> str:
        identity = ids[kind]
        budget = identity["family_budget"]
        run_id = identity["fit"]["run_id"] if plan == "fit" else identity["run_id"]
        scope = ((f"Cell {c['label']} (phase-2 Perception branches, level 2)" if kind == "arm" else f"Four-row form smoke of cell {c['label']}")
                 + (" -- FIT spend identity, request envelopes only, no generation" if plan == "fit" else "")
                 + f": the AGREE arm on TRAIN Fold B under the 15-ceiling pbranch3-l2 program with three Perception branches ({c['b_branch']}, {ff.ARM_T}, {ff.ARM_A} delivering)"
                 + (", B and T read as branch columns against A in the same flight" if kind == "arm" else ", structural form only, never scored"))
        cells = ["", args.registered_at, run_id, "bounded-discovery-probe", scope, MODEL_TOOL, f"slurp TRAIN Fold B {identity['rows']}", "discovery",
                 identity["split_identity_hash"], "no", str(budget["fit_endpoint_calls_cap"] if plan == "fit" else budget["generation_calls_cap"]),
                 str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED,
                 f"{n['package']}/{PREFIX[kind]}{plan}-plan-registered-v1.json", notes(kind, plan), ""]
        return " | ".join(cells).strip()

    read_row = " | ".join(["", args.registered_at[:10], n["read_run"], "model-free-check",
        (f"The same-flight Perception-branch read of cell {c['label']}: per branch ({ff.ARM_A}, {c['b_branch']}, {ff.ARM_T}) gold rank, present and top1 from the sealed "
         f"branch note (gold offline) and the level-2 branch Solver answer rendered through the delivered row's normaliser and projection and scored ONCE with {ff.SCORER} "
         f"(three derived-copy scorings, never sharded); paired row bootstrap of {c['b_branch']} vs {ff.ARM_A} and {ff.ARM_T} vs {ff.ARM_A} (the bar), by the recipe "
         f"{n['package']}/analysis-recipe-v1.json through scripts/flights/psv/psv_read.sh -> {ff.READ_ANALYSIS}. Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
        "no model or tool contact; read of sealed bytes and three official column scorings", f"slurp TRAIN Fold B 1080, the sealed {c['label']} flight's branch columns (after the seal)", "discovery",
        ids["arm"]["split_identity_hash"], "no", "0", "0", "0", "No new speech exposure; reads sealed outputs and scores derived copies only. Prior exposure inherited in full.",
        f"{n['package']}/analysis-recipe-v1.json",
        (f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; countersigned after the seal and before any branch column is opened) {args.registered_at[:10]} "
         f"at study commit {args.study_commit}. Recipe slurp-stage3-{c['slug']}-branch-analysis-v1; output analysis/{n['read_run']}. One READ row covers both contrasts. "
         "Its ceiling is a nomination; it admits nothing."),
        ""]).strip()

    fresh = {}
    for kind in KINDS:
        for plan in ("generation", "fit"):
            run_id = ids[kind]["fit"]["run_id"] if plan == "fit" else ids[kind]["run_id"]
            fresh[run_id] = flight_row(kind, plan)
    fresh[n["read_run"]] = read_row
    for run_id, line in fresh.items():
        if len(line.split("|")) != 17:
            raise SystemExit(f"ledger row {run_id} does not have exactly fifteen cells; a literal '|' slipped into a cell")
    order = list(fresh)
    lines = text.split("\n")
    replaced = 0
    for index, line in enumerate(lines):
        if line.startswith("|") and len(line.split("|")) > 3 and line.split("|")[2].strip() in fresh:
            lines[index] = fresh.pop(line.split("|")[2].strip())
            replaced += 1
    if replaced and fresh:
        raise SystemExit(f"the ledger carries some but not all {c['label']} rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    header = (f"\n## Cell {c['label']}: phase-2 same-flight Perception branches on TRAIN Fold B (owner decisions 184, 186, 188) -- the arm, its four-row smoke and the READ row "
              "(DRAFT, root countersignature pending)\n\nFour unconsumed flight rows and one READ row registered with the flight. No A/A cell: the twin branch flies "
              "inside every row. The Fold B agreement table row SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1 is cited, not re-registered. None of these rows is "
              "countersigned and none authorises a contact.\n\n"
              "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(fresh[r] for r in order) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
