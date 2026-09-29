#!/usr/bin/env python3
"""Write cell W4-SV's readiness package (the W4 slot conventions as the first cell of the same-flight
supply-variant instrument; owner decision 172) from the derived fragments, the sealed-trace fit
measurement and the arm-A byte-identity proof -- config and receipt-pinned bytes only: no adapter contact,
no server, no model, tokenizer, encoder, embedder or scorer contact. It flips nothing and mints nothing.

Package ``docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1/`` and the preregistration beside it.
``--append-ledger`` writes the DRAFT exposure rows (four flight rows, the READ row, and the two model-free
rows for the fit measurement and the byte-identity proof), replacing in place on re-run. ``--check-dir``
folds the per-phase prompt-budget receipts of an already-run ``core.flight.cli check`` into the facts.

    python scripts/flights/w4sv/write_slurp_w4sv_registration.py --data-root "$SPEECHRL_DATA_DIR" \\
        --study-commit <sha> --registered-at 2026-09-28T13:00:00.000000+00:00 \\
        [--check-dir /home/chao/saea-worktrees/.w4sv-checks] [--append-ledger]
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
if str(REPO_ROOT / "scripts" / "checks") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "checks"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402
import stage3_effect_floor_check as _floor_gate  # noqa: E402

PACKAGE = "docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1"
PREREG = PACKAGE + "-preregistration.md"
LEDGER = "docs/exposure-ledger.md"
CELLS = {"arm": "slurp-native-stage3-w4sv-fold-a-v1", "smoke": "slurp-native-stage3-w4sv-fold-a-smoke-4-v1"}
PARENTS = {"arm": "slurp-native-stage3-agree-w1-fold-a-v1", "smoke": "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"}
PREFIX = {"arm": "", "smoke": "smoke-"}
AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
W4_RUN = "SAEA-SLURP-STAGE3-W4-FOLD-A-V1"
READ_RUN = "SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1"
MEASURE_ROW = "SAEA-SLURP-STAGE3-W4SV-FIT-MEASURE-V1"
PROOF_ROW = "SAEA-SLURP-STAGE3-W4SV-ARM-A-BYTE-IDENTITY-PROOF-V1"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
DECISION_ID = "slurp-stage3-w4sv-fold-a-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-w4sv-fold-a-v1/root-admission-v1.json"
AGREE_SUPPLY_OUTPUT = {"arm": "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae",
                       "smoke": "308601c52b54ec49013422349e045dd3a4d621c530bf3d2be730fdfe1fdd2fc9"}
ARMS = {"b": "b-w4", "t": "t-twin", "a": "a-agree"}
EXPECTED_EFFECT_PP = 0.79
# HISTORICAL NOTE: this cell was registered under the pre-decision-190 ROLL-AA anchor
# (200, 0.735) = 0.3163 pp at n = 1,080. Owner decision 190 (2026-09-29) re-anchored the design
# (docs/results/2026-09-29-slurp-same-flight-floor-recalibration.md and this cell's OWN read,
# docs/results/2026-09-29-slurp-w4sv-fold-a-column-read.md) to the larger of the two measured
# same-flight CONTRAST half-widths -- SLU 1.49 pp at n = 1,080 (intent 0.65, not read by ``floor_at``
# below: this cell's declaration is SLU-primary with an intent guard). ``floor_at`` now reads the
# anchor from the gate, never copied, so a future table change flows through automatically. NOT
# RE-RUN against the already-registered W4-SV package (docs/readiness/2026-09-28-slurp-stage3-w4-sv-
# fold-a-v1/): its registered-facts-v1.json keeps its original 0.3163 pp provisional floor.
ROLL_AA_ANCHOR = _floor_gate.FLOOR_TABLE["same-flight-supply-variant"].sampling_by_metric["slu"][0]
READ_ROSTER = "SLURP-EVO-FOLD-A-V2"
TUNING_ROSTERS = ["size-pool-annotated-exemplars-minus-r01", "slurp-slot-conventions-w4-support-v1"]
W4_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1"
W4_PREP_REGISTRATION = "docs/readiness/2026-09-27-slurp-slot-contracts-w4-preparation-registration-v1.json"
W4_READ = "docs/results/2026-09-28-slurp-w4-fold-a-read.md"
SPEC = "docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
FIT_MEASURE = "analysis/SAEA-SLURP-STAGE3-W4SV-FIT-MEASURE-V1/fit-measure-v1.json"
PROOF = PACKAGE + "/arm-a-byte-identity-proof-v1.json"
#: The release-swap renderer fix (merge of fable/svrender): a release-swap arm renders from its own alternate snapshot.
RENDERER_FIX = "3f6688de729f99880258e0dba4993ecf1cd88817"
#: The proof the cell was registered on (arm b-w4 INERT), kept as history once a re-run reports ARM-B-VARIES.
PRIOR_PROOF = {
    "proof_sha256": "913c5487d5c7cb37e6c323433dc55976e614f7d86676efd370ee9f669e3ea55d",
    "generated_at_utc": "2026-09-28T13:50:56.314815+00:00",
    "study_commit": "b5392755b847b43501bedeeccce78e2fd93103ad",
    "verdict": "IDENTICAL-MODULO-PROGRAM-FIELDS", "arm_b_verdict": "ARM-B-INERT", "rows": 120,
    "arm_b_bodies_equal_to_arm_a": 120, "arm_b_bodies_different_from_arm_a": 0,
    "finding": ("every arm b-w4 first-visit POST body equalled its arm a-agree body: the release swap re-selected value ids "
                "through the alternate's router, but rails.runner rendered every arm's request from the FLIGHT's composite "
                "snapshot (base_messages over the row's snapshot, with only retrieved_value_ids replaced), and "
                "slot-contracts-w4-v1 carries the SAME 54 value ids as slot-contracts-v2 with new content on 19 of them -- so "
                "arm b-w4 rendered the v2 cards and read as a second twin"),
    "where": ("rails/runner.py (the supply-variant binding rendered a non-delivering arm over the row's own composite "
              "snapshot) and core/flight/runtime.py::_supply_action_router (rebuilt only the arm's ROUTER over the alternate)"),
}
GATE ="scripts/checks/stage3_effect_floor_check.py"
SCRIPTS = {name: f"scripts/flights/w4sv/{name}" for name in (
    "derive_slurp_w4sv_cells.py", "measure_w4sv_fit.py", "w4sv_arm_a_proof.py", "write_slurp_w4sv_registration.py")}
VARIANT_PREFIXES = ("policy", "knowledge_stores.slot-contracts.alternates", "native_episode.roles.solver.supply_variants",
                    "preparation_source_receipts", "native_contact_fit.", "prepared_phase_supply", "what_this_is")


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
    elif isinstance(node, list):
        out[prefix[:-1]] = json.dumps(node, sort_keys=True)
    else:
        out[prefix[:-1]] = node
    return out


def identities() -> dict:
    out = {}
    for key, experiment in CELLS.items():
        document = json.loads(rd(f"configs/experiment/{experiment}.json"))
        cell = document["cells"][0]
        composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
        parent_doc = json.loads(rd(f"configs/experiment/{PARENTS[key]}.json"))
        pc = parent_doc["cells"][0]
        parent = compose(REPO_ROOT, pc["model_fragment"], pc["dataset_fragment"], pc["baseline_fragment"], PARENTS[key])
        experiment_keys = set(document) | set(parent_doc)
        a, b = flatten(parent.values), flatten(composed.values)
        changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
        variant = [k for k in changed if k.startswith(VARIANT_PREFIXES)]
        block = [k for k in changed if k not in variant and k.split(".", 1)[0] in experiment_keys]
        other = [k for k in changed if k not in variant and k not in block]
        if other:
            raise SystemExit(f"{key}: composed config differs from its AGREE parent beyond the declarations: {other}")
        split = document["population"]["split_identity_hash"]
        values = composed.values
        out[key] = {
            "experiment": experiment, "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"], "parent_experiment": PARENTS[key],
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "arm": values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
            "composed_config_hash": composed.config_hash, "parent_composed_config_hash": parent.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, values["arm"], split),
            "fit": dict(values["native_contact_fit"]), "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"],
            "execution_profile": document["execution_profile"], "carrier_lock_key": values["carrier_lock_key"],
            "policy": values["policy"], "supply_variants": values["native_episode"]["roles"]["solver"]["supply_variants"],
            "slot_store": values["knowledge_stores"]["slot-contracts"],
            "composed_config_diff_against_the_agree_cell": {"declared_variation": variant,
                                                            "experiment_fragment_own_block": block,
                                                            "anything_else": other},
        }
    return out


def fold_check(check_dir: str | None) -> dict:
    if not check_dir:
        return {"status": "PENDING_CHECK"}
    out = {"status": "MEASURED_BY_CHECK", "cells": {}}
    for key, cell_id in CELLS.items():
        path = Path(check_dir) / f"check-{cell_id}.json"
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            out["cells"][key] = {"status": "MISSING", "path": str(path)}
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
        out["cells"][key] = {"check_path": str(path), "check_sha256": sha_file(path), "blockers": report.get("blockers"),
                             "scientific_readiness": report.get("scientific_readiness"),
                             "config_hash": preflight.get("config_hash"), "protocol_hash": preflight.get("protocol_hash"),
                             "prompt_budget_per_phase": phases}
    return out


def floor_at(rows: int) -> float:
    floor_pp, _arithmetic = _floor_gate.floor_for("same-flight-supply-variant", rows, metric="slu")
    return round(floor_pp, 4)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/w4sv2")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-w4sv2")
    parser.add_argument("--check-dir", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    data = Path(args.data_root)

    measure = json.loads((data / FIT_MEASURE).read_text(encoding="utf-8"))
    proof = json.loads(Path(PROOF).read_text(encoding="utf-8"))
    w4_facts = json.loads(rd(W4_PACKAGE + "/registered-facts-v1.json"))
    ids = identities()
    arm, smoke = ids["arm"], ids["smoke"]
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    fit = fold_check(args.check_dir)
    floor = floor_at(arm["rows"])
    roster_audio = round(caps["repeated_speech_audio_seconds_cap"] / 13, 3)
    dataset = json.loads(rd("configs/dataset/slurp-speech-native-evo-fold-a-1080.json"))
    audio_by = {row["sample_id"]: float(row["audio_seconds"]) for row in dataset["items"]}
    arm_audio = sum(audio_by[s] for s in json.loads(rd(f"configs/experiment/{CELLS['arm']}.json"))["populations"][0]["ids"])
    smoke_audio = sum(audio_by[s] for s in json.loads(rd(f"configs/experiment/{CELLS['smoke']}.json"))["populations"][0]["ids"])
    del roster_audio
    rb = proof["request_bytes"]
    arm_b_inert = proof.get("arm_b_verdict") == "ARM-B-INERT"
    status = ("BLOCKED_ARM_B_INERT_REGISTERED_HELD" if arm_b_inert else
              "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP")

    estimand = (
        "ESTIMAND CAVEAT. The expectation is transferred from cell W4's CROSS-FLIGHT full-system read (" + W4_READ
        + ": official pooled SLU-F1 +0.79 pp CI95 [-0.56, +2.12] against the shared wave A/A). In that flight the W4 "
        "cards reached EVERY node whose request carries the slot-contract supply: the realised prompt tokens rose "
        "+1,207.8 per Solver, +1,207.4 per Reviewer and +1,201.9 per Planner contact (the registration had projected "
        "+724.5 per Solver contact). Here only arm b-w4's FIRST Solver request carries them: the Reviewer, the "
        "Planner and the Solver revisit see the AGREE v2 cards and never see an arm's output. B minus A is therefore "
        "the Solver-local first-visit effect of the W4 cards, a DIFFERENT estimand from the +0.79 pp system effect "
        "(which also includes the Reviewer and Planner reading the conventions and any revision they drive); 0.79 pp "
        "is declared only as the size to look for, not as the value this read should reproduce."
    )
    rule = (
        "Columns: the first-visit Solver answers of arm b-w4 (B), the twin t-twin (T) and the delivering arm a-agree "
        "(A), each rendered through the delivered row's deliver normaliser and projection (AT1 self-check) and scored "
        "ONCE as a complete column with slurp-slu-official-train (stage3_rollout_score.py --mode supply-variants), "
        "paired by row (sample_id), 10,000 draws, seed 20260928. THE NULL: T minus A on official pooled SLU-F1 and "
        "intent accuracy; its bar is |T - A delta| + the T - A CI95 half-width (the same law as the cross-flight in-chain "
        f"A/A), never below the provisional floor {floor} pp SLU-F1 (the owner decision 190 anchor, {ROLL_AA_ANCHOR[1]} "
        f"pp at n = {ROLL_AA_ANCHOR[0]:,} scaled to n = {arm['rows']:,}, {GATE}). INSTRUMENT FAULT (no verdict): the "
        "T - A CI95 excludes zero on either metric. "
        "NOMINATED (the claim ceiling; Q6 ruling): the B - A official pooled SLU-F1 delta exceeds the bar AND its CI95 "
        "lower bound is above zero AND the B - A intent CI95 upper bound is not below zero (the guard: no measured "
        "intent loss). HARMFUL: the B - A CI95 upper bound below zero on either metric. Otherwise NOT NOMINATED "
        "(width). A nomination only sends the composed policy to a full-system read against an in-chain A/A; it is "
        "never an admission and never a system-level claim. Every verdict carries the per-scenario table in both "
        "weightings and the per-type exact TP/FP/FN of the 19 revised types, B vs A and T vs A."
    )
    measurement = {
        arm["run_id"]: {
            "admission": "benefit", "claims_benefit": True, "claim": "nominated",
            "expected_effect_pp": EXPECTED_EFFECT_PP, "measurement_design": "same-flight-supply-variant",
            "primary_metric": "official pooled SLU-F1 of the first-visit Solver column b-w4 minus a-agree (intent accuracy the guard)",
            "rows": arm["rows"], "aa_arm_id": ARMS["t"],
            "variant_cost": {"extra_contacts_per_row": 2, "extra_audio_seconds": round(2 * arm_audio, 3)},
            "tuning_roster": TUNING_ROSTERS, "read_roster": READ_ROSTER,
            "note": ("Expected 0.79 pp from the cross-flight W4 read; provisional floor " + str(floor) + " pp at n = 1,080; "
                     "bar = the twin null. " + estimand),
        },
        smoke["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof",
            "primary_metric": "none (structural form only)", "rows": smoke["rows"],
            "tuning_roster": TUNING_ROSTERS, "read_roster": READ_ROSTER,
            "note": "Four rows prove FORM and nothing else: the alternate loads when arm b-w4 selects it, three arms fan out at the first Solver visit only, the twin's wire bytes equal the delivering arm's, every request fits, the episode seals (I7, I7n, I7v). Scored by no one, read by no one.",
        },
    }
    alternate = {
        "store_id": "slot-contracts", "primary": {"release": arm["slot_store"]["release"], "snapshot": arm["slot_store"]["snapshot"],
                                                  "what": "slot-contracts-v2, the AGREE arm's cards"},
        "alternates": arm["slot_store"]["alternates"],
        "as_cell_w4_registered_them": {"package": W4_PACKAGE, "release": w4_facts["store"]["release"],
                                        "snapshot": w4_facts["store"]["snapshot"],
                                        "equal": w4_facts["store"]["release"] == arm["slot_store"]["alternates"][0]["release"]
                                        and w4_facts["store"]["snapshot"] == arm["slot_store"]["alternates"][0]["snapshot"]},
        "store_registration": {"relpath": W4_PREP_REGISTRATION, "sha256": sha_file(W4_PREP_REGISTRATION)},
        "changed_cards": w4_facts["store"]["changed_cards"],
        "value_ids": "slot-contracts-w4-v1 carries the SAME 54 value ids as slot-contracts-v2; 19 differ in content, provenance_refs and source_sample_ids",
    }
    blocker = {
        "status": "ARM-B-INERT" if arm_b_inert else "none",
        "finding": proof.get("arm_b_reading"),
        "evidence": {"proof": PROOF, "rows": rb.get("rows"),
                     "arm_b_bodies_equal_to_arm_a": rb["comparison"]["arm_b_bodies_equal_to_arm_a"],
                     "arm_b_bodies_different_from_arm_a": rb["comparison"]["arm_b_bodies_different_from_arm_a"]},
        "where": ("rails/runner.py, the supply-variant binding: a non-delivering arm is rendered by base_messages(ctx) over "
                  "the row's own composite snapshot with ONLY query_state.retrieved_value_ids replaced by the arm's "
                  "selection; core/flight/runtime.py::_supply_action_router rebuilds the arm's ROUTER over the alternate "
                  "(selection), never the snapshot the request renders from. A release swap whose alternate keeps the "
                  "primary's value ids therefore re-selects the same ids and renders the primary's content."),
        "engineering_needed": ("render a release-swap arm's request from its own alternate binding's composite snapshot "
                               "(and bind the arm's evidence pins / snapshot hash to it in the arm receipt), with an "
                               "acceptance test that an alternate differing only in content changes the arm's wire "
                               "bytes; it touches rails/runner.py and core/flight/runtime.py (merge set B files, "
                               "identity-bound), so it lands at a coordinator-named re-pin point"),
        "consequence": ("flown as registered, arm b-w4 is a second twin and B minus A reads nothing; w4sv_flip.sh refuses "
                        "until a re-run of w4sv_arm_a_proof.py reports ARM-B-VARIES"),
    } if arm_b_inert else {
        "status": "none",
        "resolved": {
            "by": f"the release-swap renderer fix {RENDERER_FIX} (merge of fable/svrender: a release-swap arm renders from "
                  "its own alternate snapshot)",
            "proof_rerun": {"proof": PROOF, "study_commit": proof.get("study_commit"),
                            "generated_at_utc": proof.get("generated_at_utc"), "rows": rb.get("rows"),
                            "arm_b_verdict": proof.get("arm_b_verdict"),
                            "arm_b_bodies_equal_to_arm_a": rb["comparison"]["arm_b_bodies_equal_to_arm_a"],
                            "arm_b_bodies_different_from_arm_a": rb["comparison"]["arm_b_bodies_different_from_arm_a"]},
            "history": {"status_at_registration": "ARM-B-INERT", "prior_proof": PRIOR_PROOF},
        },
    }
    arm_a = {
        "tool": SCRIPTS["w4sv_arm_a_proof.py"], "proof": PROOF, "proof_sha256": sha_file(PROOF),
        "proof_study_commit": proof.get("study_commit"), "proof_generated_at_utc": proof.get("generated_at_utc"),
        "verdict": proof["verdict"], "rows": rb.get("rows"),
        "arm_b_verdict": proof.get("arm_b_verdict"),
        "arm_b": {"bodies_equal_to_arm_a": rb["comparison"]["arm_b_bodies_equal_to_arm_a"],
                  "bodies_different_from_arm_a": rb["comparison"]["arm_b_bodies_different_from_arm_a"]},
        "strict": {k: rb["comparison"][k] for k in ("paired_contacts", "arm_a_first_solver_contacts", "post_body_mismatches",
                                                    "twin_body_mismatches", "unpaired_counts")},
        "normalised": {k: rb["comparison_normalised"][k] for k in ("paired_contacts", "arm_a_first_solver_contacts",
                                                                   "post_body_mismatches", "twin_body_mismatches",
                                                                   "unpaired_counts")},
        "normalisation": rb.get("normalisation"),
        "prepared_supply_output": proof["prepared_supply"]["w4sv"]["output_sha256"],
        "prepared_supply_equal_registered_and_committed": proof["prepared_supply"]["equal_registered_and_committed"],
        "reading": ("Arm A is NOT byte-identical to the AGREE arm: every contact's POST body differs, and only in three "
                    "program-derived prompt fields the arm group necessarily moves -- the program id inside agent-state "
                    "labels, the Solver's global contact index in those labels (shifted by K - 1 = 2), and "
                    "remaining_model_contacts in the role context (13 vs 11 before the Solver visit, equal after it). "
                    "Unifying exactly those three, every paired contact is byte-identical (arm A's first Solver request "
                    "included) and every twin body equals its arm A body. A, T and B share these fields, so the column "
                    "contrasts are unaffected; the claim 'A = the AGREE arm's bytes' holds only modulo these fields."),
    }
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": f"Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block {GATE} resolves (keyed by run id).",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit, "status": status,
        "owner_decisions": {
            "172": "supply_variants re-authorised as an engineering-base INSTRUMENT; same-flight A/B reads with an in-flight twin; claim ceiling 'nominated'",
            "coordinator 2026-09-28": f"W4 NOT ADMITTED (neutral by width) and re-registered as the instrument's first cell ({W4_READ}, verdict section); the release-swap route ({SPEC}, amendment)",
            "133": "a slot-acting mechanism keeps SLU-F1 primary and intent as the guard",
            "28/86": "TRAIN Fold A numbers are development numbers, never a test claim",
        },
        "rows": arm["rows"], "stage3_measurement": measurement,
        "the_cell": {
            "base": f"the retained AGREE arm {AGREE_RUN}'s fragments (65.1575 / 85.8333 official)",
            "arms": {ARMS["b"]: "release_swap slot-contracts -> slot-contracts-w4-v1 (the W4 conventions)",
                     ARMS["t"]: f"replicate_of {ARMS['a']} (the in-flight null)",
                     ARMS["a"]: "delivering, last, no overrides: the AGREE Solver supply"},
            "arm_visits": "first", "program": arm["policy"], "ceiling": 13,
            "supply_variants": arm["supply_variants"],
        },
        "alternate": alternate,
        "blocker": blocker,
        "arm_a_byte_identity": arm_a,
        "estimand": estimand,
        "expectation": {"expected_effect_pp": EXPECTED_EFFECT_PP, "source": W4_READ,
                        "provisional_floor_pp": floor,
                        "floor_formula": f"{ROLL_AA_ANCHOR[1]} * sqrt({ROLL_AA_ANCHOR[0]} / rows) (same-flight-supply-variant, owner decision 190 anchor, provisional)",
                        "bar": "the twin null |T - A| + its CI95 half-width, never below the provisional floor"},
        "fit_estimate": {"measurement": {"relpath": FIT_MEASURE, "sha256": sha_file(data / FIT_MEASURE),
                                          "script": {"relpath": SCRIPTS["measure_w4sv_fit.py"], "sha256": sha_file(SCRIPTS["measure_w4sv_fit.py"])}},
                         "declared": arm["supply_variants"]["fit_estimate"], "prompt_limit_tokens": measure["prompt_limit_tokens"],
                         "estimated_prompt_tokens_at_max_supplied_items": measure["estimated_prompt_tokens_at_max_supplied_items"],
                         "estimate_headroom_tokens": measure["estimate_headroom_tokens"],
                         "max_supplied_items": measure["max_supplied_items"], "realised_items_max": measure["realised_items_max"],
                         "realised_solver_prompt_tokens_max": {k: v["prompt_tokens_max"] for k, v in measure["flights"].items()},
                         "method": measure["method"]},
        "fit": fit,
        "variant_cost": {"extra_contacts_per_row": 2, "extra_contacts_per_flight": 2 * arm["rows"],
                         "extra_audio_seconds": round(2 * arm_audio, 3), "smoke_extra_audio_seconds": round(2 * smoke_audio, 3),
                         "expected_contacts": 4393 + 2 * arm["rows"],
                         "note": "every extra arm re-sends the row's speech packet at the first Solver visit; the AGREE bytes realised 4,393 contacts on this roster"},
        "rosters": {"tuning_roster": TUNING_ROSTERS, "read_roster": READ_ROSTER,
                    "why": ("the W4 conventions were mined model-free from the R01-excluded TRAIN exemplar pool "
                            "size-pool-annotated-exemplars-minus-r01 (8,554 utterances) and released on the exact support "
                            "roster slurp-slot-conventions-w4-support-v1 (22,416 samples), whose prepare step refused the "
                            "forbidden rosters SLURP-EVO-FOLD-A-V2, SLURP-EVO-FOLD-B-V2 and DEV-1000 ("
                            + W4_PREP_REGISTRATION + "); no Fold A byte, flight output or score authored a value. Neither "
                            "tuning id has a receipt under docs/receipts/rosters/, so the gate reports tuning-roster-unverified (advisory)")},
        "identity": {key: {k2: v for k2, v in ids[key].items() if k2 != "composed_config_diff_against_the_agree_cell"} for key in CELLS},
        "composed_config_diff_against_the_agree_cell": {key: ids[key]["composed_config_diff_against_the_agree_cell"] for key in CELLS},
        "decision_rule": rule,
        "byte_identity_expectation": {
            "agree_first_phase_supply_output_sha256": AGREE_SUPPLY_OUTPUT,
            "claim": "neither the alternate nor the arm group is an input to the first-phase (Perception boundary) supply, so the supply the flip mints must carry the AGREE digests; the proof minted the arm's: " + proof["prepared_supply"]["w4sv"]["output_sha256"],
        },
        "budget_arithmetic": {"arm_family_budget": caps, "smoke_family_budget": smoke_caps,
                              "note": "13 contacts per row (11 + 2 arms), FIT 13 x 4 per row, speech 13 x the roster audio rounded up; run-cumulative"},
        "stage3_algorithm": "none (an instrument read; not a VAR-2 mechanism: nothing downstream depends on a non-delivering arm)",
        "prohibitions": [
            "No test-split, Fold B or DEV contact or read.", "No re-flying of the sealed AGREE or W4 arms.",
            "No second factor: no other template, knob, store, roster, geometry or session change.",
            "No paper-scale profile.", "No claim above 'nominated'.",
            "No flight while arm b-w4 is inert (w4sv_flip.sh refuses) and none before root mints the decision receipt and the cells are flipped.",
        ],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1", "protocol_id": "slurp-stage3-w4sv-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": status,
        "the_question": "At the FIRST Solver visit of the AGREE episode on TRAIN Fold A 1,080, does the Solver's official pooled SLU-F1 move when its slot-contract cards come from the W4 conventions release (arm b-w4) instead of the AGREE v2 cards (arm a-agree), beyond the in-flight twin's null?",
        "cells": {key: {k2: ids[key][k2] for k2 in ("cell", "experiment", "run_id", "attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash")}
                  | {"fit_run_id": ids[key]["fit"]["run_id"], "fit_attempt_id": ids[key]["fit"]["attempt_id"]} for key in CELLS},
        "arms": facts["the_cell"]["arms"], "decision_rule_fixed_here": rule, "estimand": estimand,
        "development_numbers_only": "Every number is a TRAIN Fold A development number (owner decisions 28 and 86), never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in CELLS:
        identity = ids[key]
        budget = identity["family_budget"]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
            plan_doc = {
                "schema": f"saea-registered-{kind}-plan-v1", "plan_kind": kind, "cell": identity["cell"],
                "experiment": identity["experiment"], "composed_config_hash": identity["composed_config_hash"],
                "registered_at_utc": args.registered_at, "status": status, "source_tree": protocol["source_tree"],
                "preparation_base_commit": args.study_commit, "expected_session_id": SESSION,
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
                    "Shared core.flight.cli campaign over configs/campaign/slurp-native-stage3-w4sv-fold-a-v1.json (this arm alone; the twin arm is the in-flight null) through scripts/flights/w4sv/batch_chain_w4sv.sh." if key == "arm" else
                    "Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored."
                ),
                "prepared_phase_supply": {"relpath": f"prepared/{identity['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
                                          "expected_output_sha256": AGREE_SUPPLY_OUTPUT[key],
                                          "note": facts["byte_identity_expectation"]["claim"]},
                "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "supply_variants": identity["supply_variants"],
                "purpose": f"{run_id}: " + ("request envelopes only; reads nothing." if is_fit else rule if key == "arm" else "structural form proof only: no score and no read."),
                "quality_read_gate": "No column read before the complete sealed manifest, the ordered outputs, the phase summary, the single complete official TRAIN score of the delivered rows and the three rendered-and-scored first-visit columns exist; the READ row must be countersigned first.",
            }
            plan_shas[run_id] = wjson(f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", plan_doc)

    column = lambda c: {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "column": c}  # noqa: E731
    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1", "recipe_id": "slurp-stage3-w4sv-fold-a-column-read-v1",
        "title": "Cell W4-SV -- the same-flight first-visit column read: b-w4 vs a-agree (gating) against the twin null t-twin vs a-agree",
        "registered_at_utc": args.registered_at, "read_run_id": READ_RUN,
        "run_ids": {"read": READ_RUN, "arm": arm["run_id"]},
        "columns": {"treatment": column(ARMS["b"]), "twin": column(ARMS["t"]), "delivering": column(ARMS["a"])},
        "passes": {"b-vs-a": {"left": ARMS["a"], "right": ARMS["b"], "role": "GATING"},
                   "t-vs-a": {"left": ARMS["a"], "right": ARMS["t"], "role": "the in-flight null (the bar)"}},
        "resampling": {"bootstrap_draws": 10000, "metrics": ["slu_f1_f1", "scenario_action_exact"], "seed": 20260928,
                       "unit": "row (paired)", "cluster_key": "sample_id"},
        "decision_rule": rule, "provisional_floor_pp": floor, "expected_effect_pp": EXPECTED_EFFECT_PP,
        "steps": [
            "1. Refuse unless the arm carries a COMPLETE sealed 1,080-row manifest (I7, I7n, I7v verified) with one successful complete official TRAIN score of the delivered rows and this package's config hash.",
            "2. Render the three first-visit columns with scripts/analysis/stage3_rollout_score.py --mode supply-variants --stage all (AT1: the delivering column reproduces the sealed delivered text on every row with no revision) into <run dir>/supply-variants/, scoring each column ONCE with slurp-slu-official-train.",
            "3. Pass t-vs-a (the null) and pass b-vs-a (gating) with scripts/analysis/stage3_paired_read.py --left-column a-agree --right-column <t-twin|b-w4>: paired row bootstrap, 10,000 draws, seed 20260928; per-scenario tables in both weightings.",
            "4. Apply the rule; the verdict word is the coordinator's (decision 139); the driver writes 'nominated' where it would write an admitting verdict (Q6).",
            "5. Mechanism read (model-free, counts only): per revised type exact TP/FP/FN, b-w4 vs a-agree and t-twin vs a-agree.",
        ],
        "read_driver": "scripts/flights/w4sv/w4sv_read.sh",
        "output": {"analysis_root": f"analysis/{READ_RUN}"},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim. No utterance text, transcript, gold label or model output is printed or persisted.",
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    eligible = [arm["run_id"], arm["fit"]["run_id"], smoke["run_id"], smoke["fit"]["run_id"]]
    draft = {
        "_draft_note": "A DRAFT for root to mint on the data root with scripts/flights/w4sv/w4sv_mint_receipt.py (status decided, recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1", "decision_id": DECISION_ID, "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None, "owner": "root", "coordinator": "Fable5.1", "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 same-flight supply-variant instrument cell (label none), claim ceiling nominated. One arm on TRAIN Fold A 1,080 with three first-visit Solver arms (b-w4, t-twin, a-agree delivering), and a four-row form smoke.",
        "decision": "Fly cell W4-SV: the retained AGREE arm with a three-arm first-visit Solver group -- b-w4 (release swap to slot-contracts-w4-v1), t-twin (replicate of a-agree), a-agree (delivering) -- read as first-visit columns b-w4 vs a-agree against the twin null.",
        "authorization_basis": f"Owner decision 172; the coordinator verdict on W4 ({W4_READ}); the release-swap amendment ({SPEC}); 133, 28/86.",
        "blocker": blocker["status"],
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "instrument_spec": {"path": SPEC, "sha256": sha_file(SPEC)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "w4_read": {"path": W4_READ, "sha256": sha_file(W4_READ)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "arm_a_proof": {"path": PROOF, "sha256": sha_file(PROOF)},
            "store_registration": {"path": W4_PREP_REGISTRATION, "sha256": sha_file(W4_PREP_REGISTRATION)},
            "base_cell": f"the retained AGREE arm {AGREE_RUN} (owner decision 161)",
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k2: caps[k2] for k2 in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No claim above 'nominated'; no superiority, generalisation, component-causal, held-out, confirmatory, system-level or paper-scale claim.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": ["any flight while arm b-w4 is inert", "any flight before the cells are flipped and the receipt is minted", "touching the resident np4 session by anyone but the coordinator", "any ASR, transcript, encoder or paid-API contact", "re-flying or re-scoring any sealed cell", "--allow-output-change on the re-pin tool"],
        "population": {"count": arm["rows"], "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS},
        "service": {"expected_session_id": SESSION, "model_fragment": arm["model_fragment"], "slots": 4, "slot_tokens": 24576, "no_child_start_stop": True},
    }
    draft_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    readme, prereg = render_docs(args, ids, facts, rule, fence, status)
    readme_sha = wr(PACKAGE + "/README.md", readme)
    prereg_sha = wr(PREREG, prereg)
    ledger = "not-requested"
    if args.append_ledger:
        ledger = append_ledger(args, ids, plan_shas, facts, data, status)
    print(json.dumps({"package": PACKAGE, "status": status, "ledger": ledger,
                      "written": {"README.md": readme_sha, "registered-facts-v1.json": facts_sha, "protocol": protocol_sha,
                                  "analysis-recipe": recipe_sha, "root-admission-draft": draft_sha, "prereg": prereg_sha, **plan_shas},
                      "identity": {key: {"run_id": ids[key]["run_id"], "composed": ids[key]["composed_config_hash"],
                                         "protocol": ids[key]["protocol_hash"]} for key in CELLS},
                      "fit": fit.get("status")}, indent=2))
    return 0


def _fit_lines(fit: dict) -> str:
    if fit.get("status") != "MEASURED_BY_CHECK":
        return "PENDING: core.flight.cli check not yet folded in."
    lines = ["| cell | phase | decision | rendered (4 B/token) | operational margin | physical margin |", "| --- | --- | --- | ---: | ---: | ---: |"]
    for key, cell in fit["cells"].items():
        for p in cell.get("prompt_budget_per_phase", []):
            lines.append(f"| {key} | {p.get('phase')} | {p.get('decision')} | {p.get('rendered_text_tokens')} | {p.get('operational_margin_tokens')} | {p.get('physical_margin_tokens')} |")
    return "\n".join(lines)


def _prereg_proof_note(blocker: dict, a: dict) -> str:
    if not blocker.get("resolved"):
        return ""
    rerun, prior = blocker["resolved"]["proof_rerun"], blocker["resolved"]["history"]["prior_proof"]
    return (f"\n\nArm-B proof: registered on {prior['arm_b_verdict']} (proof sha256 `{prior['proof_sha256']}`); re-run "
            f"{str(rerun['generated_at_utc'])[:10]} after the renderer fix `{RENDERER_FIX[:8]}` at study commit "
            f"`{str(rerun['study_commit'])[:9]}` over {rerun['rows']} rows: {rerun['arm_b_verdict']} (arm b-w4 differs from "
            f"a-agree on {rerun['arm_b_bodies_different_from_arm_a']}, equals it on {rerun['arm_b_bodies_equal_to_arm_a']}); "
            f"arm A {a['verdict']}, twin mismatches {a['normalised']['twin_body_mismatches']}; proof sha256 `{a['proof_sha256']}`.")


def render_docs(args, ids, facts, rule, fence, status):
    arm, smoke = ids["arm"], ids["smoke"]
    a = facts["arm_a_byte_identity"]
    blocker = facts["blocker"]
    fe = facts["fit_estimate"]
    vc = facts["variant_cost"]
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    blocked = ""
    if blocker["status"] != "none":
        blocked = f"""
## BLOCKED: arm b-w4 is inert

{blocker['finding']}

Evidence: `{blocker['evidence']['proof']}` over the first {blocker['evidence']['rows']} rows -- arm b-w4's first-visit
POST body equals arm a-agree's on {blocker['evidence']['arm_b_bodies_equal_to_arm_a']} rows and differs on
{blocker['evidence']['arm_b_bodies_different_from_arm_a']}. Where: {blocker['where']} Needed: {blocker['engineering_needed']}.
Consequence: {blocker['consequence']}.
"""
    elif blocker.get("resolved"):
        rerun, prior = blocker["resolved"]["proof_rerun"], blocker["resolved"]["history"]["prior_proof"]
        blocked = f"""
## Proof re-run after the renderer fix ({RENDERER_FIX[:8]}), {str(rerun['generated_at_utc'])[:10]}

`w4sv_arm_a_proof.py` re-run at study commit `{str(rerun['study_commit'])[:9]}` (which carries the release-swap renderer
fix `{RENDERER_FIX[:8]}`: a release-swap arm now renders from its own alternate snapshot) over the first {rerun['rows']} rows
reports **{rerun['arm_b_verdict']}**: arm b-w4's first-visit POST body differs from arm a-agree's on
{rerun['arm_b_bodies_different_from_arm_a']} rows and equals it on {rerun['arm_b_bodies_equal_to_arm_a']}. Arm A's verdict and
the twin are unchanged (below). The arm-B blocker is lifted; the cells stay held until root countersigns and mints.

**History (the registration's finding, superseded).** At registration the proof (study commit
`{prior['study_commit'][:9]}`, sha256 `{prior['proof_sha256']}`) read {prior['arm_b_verdict']} over the first
{prior['rows']} rows -- arm b-w4's body equal to arm a-agree's on {prior['arm_b_bodies_equal_to_arm_a']} rows, different on
{prior['arm_b_bodies_different_from_arm_a']}: {prior['finding']}. Where: {prior['where']}. The cell was registered held
with status `BLOCKED_ARM_B_INERT_REGISTERED_HELD` until the fix landed.
"""
    readme = f"""# Cell W4-SV: the W4 slot conventions as a same-flight supply-variant column read (owner decision 172)

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}`; both cells **held**; status
`{status}`. Nothing here authorises a flight, a flip or an admission entry. Development numbers only (owner decisions
28 and 86).
{blocked}
**What W4-SV is.** The retained AGREE arm (`{AGREE_RUN}`) with a three-arm Solver supply-variant group fanned out at
the FIRST Solver visit only (`arm_visits: "first"`, program `{arm['policy']}`, ceiling 13 = 11 + 2):

| arm | declaration | what its first Solver request carries |
| --- | --- | --- |
| `b-w4` | `release_swap: {{store_id: slot-contracts, release: knowledge/slurp/semantic/slot-contracts-w4-v1/release.json}}` | the W4 conventions release (19 of 54 cards extended), the declared ONE alternate of `slot-contracts` |
| `t-twin` | `replicate_of: a-agree` | the delivering arm's request, byte for byte (AT2) -- the in-flight null |
| `a-agree` | `deliver: true`, last, no overrides | the AGREE Solver supply (slot-contracts-v2) |

Only the delivering arm's answer reaches the Reviewer, the Planner and the delivered text; every revisit contacts
`a-agree` alone. The alternate is pinned exactly as cell W4 registered it (`{W4_PACKAGE}`): equal =
{facts['alternate']['as_cell_w4_registered_them']['equal']}.

**Measurement.** `same-flight-supply-variant`; primary official pooled SLU-F1 of the first-visit column b-w4 minus
a-agree, intent accuracy the guard; expected effect {EXPECTED_EFFECT_PP} pp (cell W4's cross-flight read); provisional
floor {facts['expectation']['provisional_floor_pp']} pp at n = 1,080 ({ROLL_AA_ANCHOR[1]} x sqrt({ROLL_AA_ANCHOR[0]} / 1,080), owner decision 190 anchor); bar = the twin null;
claim `nominated`; `aa_arm_id` `t-twin`; variant cost +{vc['extra_contacts_per_row']} Solver contacts per row
(+{vc['extra_contacts_per_flight']:,} per flight, +{vc['extra_audio_seconds']:,} speech seconds); tuning roster
{', '.join('`' + r + '`' for r in TUNING_ROSTERS)}; read roster `{READ_ROSTER}`.

**Estimand.** {facts['estimand']}

## Arm A against the AGREE arm (`arm-a-byte-identity-proof-v1.json`, the wave shared-A/A proof shape)

Verdict **{a['verdict']}** over the first {a['rows']} rows. Strict POST-body comparison: {a['strict']['post_body_mismatches']}
of {a['strict']['paired_contacts']} paired contacts differ; twin mismatches {a['strict']['twin_body_mismatches']}.
Normalised: {a['normalised']['post_body_mismatches']} of {a['normalised']['paired_contacts']} differ
({a['normalised']['arm_a_first_solver_contacts']} arm-A first Solver contacts included); twin mismatches
{a['normalised']['twin_body_mismatches']}. Prepared first-phase supply output `{a['prepared_supply_output']}` (equal to the
registered and committed AGREE digest: {a['prepared_supply_equal_registered_and_committed']}).

{a['reading']}

## Fit

`supply_variants.fit_estimate` {json.dumps(fe['declared'], sort_keys=True)}, measured from the sealed wave A/A and W4
Solver requests (`{FIT_MEASURE}`): per-item ratio envelope; estimate at `max_supplied_items` {fe['max_supplied_items']}
(the structural sum of the supply caps; realised max {fe['realised_items_max']}) is
{fe['estimated_prompt_tokens_at_max_supplied_items']:,} tokens against the {fe['prompt_limit_tokens']:,}-token limit
(headroom {fe['estimate_headroom_tokens']:,}). Realised Solver prompt maxima: AGREE bytes
{fe['realised_solver_prompt_tokens_max']['agree_bytes']:,}, W4 {fe['realised_solver_prompt_tokens_max']['w4']:,}.

{_fit_lines(facts['fit'])}

The check composes the delivering path; arm b-w4's widest request is cell W4's first Solver request, whose preflight
physical margin at 24,576 was 826 tokens (`{W4_PACKAGE}/registered-facts-v1.json`, `fit`), COMPACT_REQUIRED under the
armed compact-or-abstain policy with a non-negative physical margin.

## Decision rule (fixed here)

{rule}

## Files

| file | what it holds |
| --- | --- |
| `../{Path(PREREG).name}` | the preregistration, with the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact; the CANONICAL `stage3_measurement` |
| `arm-a-byte-identity-proof-v1.json` | the arm-A / twin / arm-B byte proof |
| `protocol-registered-v1.json` | identities, hashes, the rule |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the column read; `read_run_id` = `{READ_RUN}` |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/w4sv/w4sv_mint_receipt.py` |

**Sequence.** (1) The arm-B blocker is fixed and `w4sv_arm_a_proof.py` re-run reports ARM-B-VARIES (the flip refuses
otherwise){' -- DONE: ' + blocker['resolved']['proof_rerun']['arm_b_verdict'] + ' at ' + str(blocker['resolved']['proof_rerun']['study_commit'])[:9] if blocker.get('resolved') else ''}. (2) Root countersigns the DRAFT rows (four flight rows and the two model-free rows; the READ row stays
draft until the seal) and mints `{DECISION_RELPATH}`. (3) `scripts/flights/w4sv/w4sv_flip.sh` (smoke, then arm; minted
supplies must reproduce the AGREE digests). (4) `scripts/flights/w4sv/batch_chain_w4sv.sh` on slurp-np4 through the
batch driver. (5) `scripts/flights/w4sv/w4sv_read.sh`.

**Budgets.** Arm {caps['generation_calls_cap']:,} generation contacts, {caps['fit_endpoint_calls_cap']:,} FIT endpoints,
{caps['repeated_speech_audio_seconds_cap']:,} speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours; smoke
{smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} / {smoke_caps['gpu_hours_fit_inclusive']}.
"""
    prereg = f"""# Cell W4-SV (same-flight supply-variant read of the W4 slot conventions): preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the retained AGREE
arm fragments by script (decision 58) under owner decision 172 and the coordinator's W4 verdict. Status `{status}`.
Development numbers only.{_prereg_proof_note(blocker, a)}

## The cell

| item | value |
| --- | --- |
| base | the retained AGREE arm `{AGREE_RUN}` (65.1575 / 85.8333) |
| arms (first Solver visit) | `b-w4` release swap to slot-contracts-w4-v1; `t-twin` replicate of a-agree; `a-agree` delivering |
| design / claim | `same-flight-supply-variant` / `nominated` |
| primary / guard | official pooled SLU-F1 of the b-w4 minus a-agree column / intent accuracy |
| expected effect / floor / bar | {EXPECTED_EFFECT_PP} pp / {facts['expectation']['provisional_floor_pp']} pp provisional / the twin null |
| runs | `{arm['run_id']}` / `{arm['fit']['run_id']}`; `{smoke['run_id']}` / `{smoke['fit']['run_id']}`; read `{READ_RUN}` |
| composed config hashes | arm `{arm['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |
| protocol hashes | arm `{arm['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |
| split identity | arm `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |

## Estimand

{facts['estimand']}

## Decision rule (fixed here)

{rule}

## The measurement declaration

```json
{fence}
```

## Prohibitions

No test-split, Fold B or DEV contact; no re-flying of a sealed cell; no second factor; no paper-scale profile; no claim
above `nominated`; no flight while arm b-w4 is inert; `--allow-output-change` never passed.
"""
    return readme, prereg


MODEL_TOOL = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any role; "
              "prompt bytes the retained AGREE arm's except arm b-w4's first Solver request (slot-contracts-w4-v1 cards via the release-swap route) and the program-derived fields of the 13-contact program")
INHERITED = ("TRAIN Fold A discovery rows already exposed by the sealed anchors and every Stage-2/3 Fold A cell (B-series, PLAN, PLANr, ROLL-2, CONV, "
             "the AGREE family, KPROBE, COMP-1, G5, the knowledge wave W1/W3a/W4 and REV-TFRL-1, flown or in flight at registration); this cell adds no new row to the fold and opens no split. Prior exposure is inherited in full.")


def append_ledger(args, ids, plan_shas, facts, data, status) -> str:
    text = rd(LEDGER)
    eligible = [ids["arm"]["run_id"], ids["arm"]["fit"]["run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit"]["run_id"]]
    blocked = (" BLOCKED: arm b-w4 is inert at registration (its first-visit POST body equals arm a-agree's on every proof row; "
               "the runner renders a release-swap arm from the flight's own composite snapshot) -- root must not countersign "
               "or flip until the engineering fix lands and w4sv_arm_a_proof.py reports ARM-B-VARIES.") if facts["blocker"]["status"] != "none" else ""

    def flight_notes(key: str, kind: str) -> str:
        identity = ids[key]
        run_id = identity["fit"]["run_id"] if kind == "fit" else identity["run_id"]
        attempt = identity["fit"]["attempt_id"] if kind == "fit" else identity["attempt_id"]
        m = facts["stage3_measurement"][ids["arm"]["run_id"]]
        declaration = (f"measurement_design same-flight-supply-variant, expected_effect_pp {EXPECTED_EFFECT_PP}, claims_benefit true, claim nominated, "
                       f"aa_arm_id t-twin, variant_cost +2 Solver contacts per row / +{m['variant_cost']['extra_audio_seconds']} speech s, "
                       f"columns b-w4 (treatment), t-twin (null), a-agree (delivering), rows 1080, provisional floor {facts['expectation']['provisional_floor_pp']} pp, bar the twin null"
                       if key == "arm" else "measurement_design form-proof, claims_benefit false, expected_effect_pp 0.0, rows 4")
        return (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit} by the W4-SV "
            f"registration agent (worktree {args.worktree}, branch {args.branch}). This registration performs no contact and authorises none.{blocked} Plan SHA256 "
            f"{plan_shas[run_id]}; attempt {attempt}. Protocol hash {identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected "
            f"session {SESSION} (attach only). READINESS HELD: root mints {DECISION_RELPATH} (decision id {DECISION_ID}) with the four eligible run ids "
            f"{', '.join(eligible)}, then scripts/flights/w4sv/w4sv_flip.sh re-pins with scripts/flights/repin_cell.py --set-ready, minting each cell's own "
            f"first-phase supply (item E16; expected output digest {AGREE_SUPPLY_OUTPUT[key]}, the AGREE {key}'s); --allow-output-change must never be "
            f"passed. Every hash in this row moves at the flip. The AGREE arm with a three-arm first-visit Solver supply-variant group (owner decision 172): "
            f"b-w4 release_swap slot-contracts -> slot-contracts-w4-v1, t-twin replicate_of a-agree, a-agree delivering; program "
            f"phase-native-candidates-review-revise-variants3first-v1 (ceiling 13). Measurement declaration ({GATE}): {declaration} -- canonical in "
            f"{PACKAGE}/registered-facts-v1.json. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. "
            f"No test-split, Fold B or DEV contact, no re-flight of a sealed cell."
        )

    def flight_row(key: str, kind: str) -> str:
        identity = ids[key]
        budget = identity["family_budget"]
        run_id = identity["fit"]["run_id"] if kind == "fit" else identity["run_id"]
        scope = (("Cell W4-SV (same-flight supply-variant read of the W4 slot conventions)" if key == "arm" else "Four-row form smoke of cell W4-SV")
                 + (" -- FIT spend identity, request envelopes only, no generation" if kind == "fit" else "")
                 + ": the retained AGREE arm with three first-visit Solver arms (b-w4 W4 cards, t-twin, a-agree delivering)"
                 + (", read as first-visit columns b-w4 vs a-agree against the twin null, claim ceiling nominated" if key == "arm" else ", structural form only, never scored"))
        cells = ["", args.registered_at, run_id, "bounded-discovery-probe", scope, MODEL_TOOL, f"slurp TRAIN Fold A {identity['rows']}", "discovery",
                 identity["split_identity_hash"], "no", str(budget["fit_endpoint_calls_cap"] if kind == "fit" else budget["generation_calls_cap"]),
                 str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED,
                 f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", flight_notes(key, kind), ""]
        return " | ".join(cells).strip()

    read_row = " | ".join(["", args.registered_at[:10], READ_RUN, "model-free-check",
        f"The first-visit column read of cell W4-SV: render and score (once each, slurp-slu-official-train) the three Solver columns b-w4, t-twin and a-agree of the sealed arm, then the paired row bootstrap b-w4 vs a-agree (gating) and t-twin vs a-agree (the null), by the recipe {PACKAGE}/analysis-recipe-v1.json through scripts/flights/w4sv/w4sv_read.sh. Zero model, server, encoder, embedder, tokenizer and GPU contacts; three official column scorings.",
        "no model or tool contact; read of sealed bytes and three official column scorings only", "slurp TRAIN Fold A 1080, the sealed W4-SV arm's three first-visit columns (after the seal)", "discovery",
        ids["arm"]["split_identity_hash"], "no", "0", "0", "0", "No new speech exposure; reads sealed outputs and official scores only. Prior exposure inherited in full.",
        f"{PACKAGE}/analysis-recipe-v1.json",
        f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; countersigned after the seal and before any column score is opened) {args.registered_at[:10]} at study commit {args.study_commit}. Recipe slurp-stage3-w4sv-fold-a-column-read-v1; output analysis/{READ_RUN}. It nominates at most; it admits nothing.{blocked}",
        ""]).strip()
    measure_sha = sha_file(data / FIT_MEASURE)
    measure_row = " | ".join(["", args.registered_at[:10], MEASURE_ROW, "model-free-check",
        "Measure cell W4-SV's supply_variants.fit_estimate from sealed bytes: per Solver contact of the sealed wave A/A (the AGREE bytes) and the sealed W4 arm, the request's supplied item count and the paired response's realised prompt tokens; the per-item ratio envelope and the structural item bound. Zero model, tokenizer, encoder, embedder, scorer, server, network and GPU contacts.",
        "no model or tool contact; read-only sealed traces (counts and token numbers only)", "slurp TRAIN Fold A 1080 (sealed wave A/A and W4 arm traces)", "discovery",
        ids["arm"]["split_identity_hash"], "no", "0", "0", "0", "No new speech exposure: sealed bytes already exposed. Prior exposure inherited in full.",
        FIT_MEASURE,
        f"MODEL-FREE READ OF SEALED BYTES, RUN BEFORE THIS ROW WAS WRITTEN (disclosed; DRAFT, root countersignature pending) {args.registered_at[:10]}; script scripts/flights/w4sv/measure_w4sv_fit.py; output sha256 {measure_sha}. It authorises nothing.",
        ""]).strip()
    a = facts["arm_a_byte_identity"]
    rerun_note = ""
    if facts["blocker"].get("resolved"):
        rerun, prior = facts["blocker"]["resolved"]["proof_rerun"], facts["blocker"]["resolved"]["history"]["prior_proof"]
        rerun_note = (f" RE-RUN {str(rerun['generated_at_utc'])[:10]} after the renderer fix {RENDERER_FIX[:8]} at study commit "
                      f"{str(rerun['study_commit'])[:9]}, {rerun['rows']} rows: arm b-w4 differs from a-agree on "
                      f"{rerun['arm_b_bodies_different_from_arm_a']}, equals it on {rerun['arm_b_bodies_equal_to_arm_a']}; the "
                      f"registration proof (sha256 {prior['proof_sha256']}) read {prior['arm_b_verdict']} "
                      f"({prior['arm_b_bodies_equal_to_arm_a']} of {prior['rows']} equal) and is superseded.")
    proof_row =" | ".join(["", args.registered_at[:10], PROOF_ROW, "model-free-check",
        f"The arm-A byte-identity proof of cell W4-SV (the wave shared-A/A proof shape): composed-config diff against the AGREE arm, a scratch prepare-supply of the W4-SV arm's first-phase supply, and each cell's real dispatch against the real transport with a fake POST (canned completions, serial, one slot) over the first {a['rows']} rows, pairing contacts by (sample, role, AGREE index). Zero model, server, tokenizer, encoder, scorer and GPU contacts.",
        "no model or tool contact; fake POST, canned completions; model-free prepare-supply into a scratch directory", f"slurp TRAIN Fold A first {a['rows']} rows (request composition only)", "discovery",
        ids["arm"]["split_identity_hash"], "no", "0", "0", "0", "No speech exposure: requests are composed and hashed, never sent to a model. Prior exposure inherited in full.",
        PROOF,
        f"MODEL-FREE PROOF, RUN BEFORE THIS ROW WAS WRITTEN (disclosed; DRAFT, root countersignature pending) {args.registered_at[:10]}; script scripts/flights/w4sv/w4sv_arm_a_proof.py; verdict {a['verdict']}; arm B {facts['blocker']['status'] if facts['blocker']['status'] != 'none' else 'ARM-B-VARIES'}; proof sha256 {a['proof_sha256']}.{rerun_note} It authorises nothing.",
        ""]).strip()

    fresh = {}
    for key in ("arm", "smoke"):
        for kind in ("generation", "fit"):
            run_id = ids[key]["fit"]["run_id"] if kind == "fit" else ids[key]["run_id"]
            fresh[run_id] = flight_row(key, kind)
    fresh[READ_RUN] = read_row
    fresh[MEASURE_ROW] = measure_row
    fresh[PROOF_ROW] = proof_row
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
        raise SystemExit("the ledger carries some but not all W4-SV rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    header = ("\n## Cell W4-SV: the W4 slot conventions as a same-flight supply-variant column read (owner decision 172) -- the arm, its "
              "four-row smoke, the READ row, the fit measurement and the arm-A byte-identity proof (DRAFT, root countersignature pending)\n\n"
              "Four unconsumed flight rows, one READ row registered with the flight, and two model-free rows. The null is the in-flight twin "
              f"arm t-twin. Status {status}. None of these rows is countersigned and none authorises a contact.\n\n"
              "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(fresh[r] for r in order) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
