#!/usr/bin/env python3
"""Write the readiness packages of the phase-2 Perception-branch cells P-SV-1, P-SV-2, P-SV-3 (owner decisions
184, 186, 188, 190) and P-SV-4 (2026-09-30, the key_source axis; written with --cells psv4) from the derived fragments and the measured fit numbers -- config and receipt-pinned bytes
only: no adapter contact, no server, no lock, no model, tokenizer, encoder, embedder or scorer contact. Flips
nothing, mints nothing.

Per cell: ``docs/readiness/2026-09-29-slurp-stage3-psvK-fold-b-v1/`` (registered facts with the CANONICAL
``stage3_measurement`` block, protocol, generation/FIT plans for the arm and its four-row smoke, the analysis recipe
naming the READ run id, the root-admission DRAFT, README) and the preregistration beside it. ``--append-ledger``
writes the DRAFT exposure rows (arm, arm FIT, smoke, smoke FIT, READ), replacing in place on re-run.
``--check-dir`` folds the per-phase prompt-budget receipts of an already-run ``core.flight.cli check``. ``--cells``
(default ``psv1,psv2``) scopes which cells this run touches; P-SV-3 is written with ``--cells psv3`` so an
already-registered cell's package is never re-rendered under a fresh timestamp/commit by the same invocation.

    python scripts/flights/psv/write_slurp_psv_registration.py --data-root "$SPEECHRL_DATA_DIR" \\
        --study-commit <sha> --registered-at 2026-09-29T00:30:00.000000+00:00 [--check-dir DIR] [--append-ledger] \\
        [--cells psv1,psv2,psv3]
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402
import stage3_effect_floor_check as _floor_gate  # noqa: E402

import psv_family as ff  # noqa: E402

LEDGER = "docs/exposure-ledger.md"
KINDS = ("arm", "smoke")
PREFIX = {"arm": "", "smoke": "smoke-"}
# Owner decision 190 (2026-09-29) put a per-metric floor on ff.MEASUREMENT_DESIGN
# (same-flight-perception-variant): P-SV-1's primary is intent (FLOOR_INTENT), P-SV-2's is
# gold-on-list presence, which carries no numeric floor at all (FLOOR_SLU is reported beside,
# never as P-SV-2's own floor). Read from the gate, never copied, so a future table change
# flows through automatically.
#
# HISTORICAL NOTE: these cells were registered under the pre-decision-190 ROLL-AA anchor
# (200, 0.735) = 0.3163 pp at n = 1,080, metric-blind. NOT RE-RUN against the already-
# registered P-SV-1 / P-SV-2 packages (docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1/,
# .../psv2-fold-b-v1/): their registered-facts-v1.json keep their original 0.3163 pp floor.
# Both declare claims_benefit false, so no effect-below-floor comparison is live either way.
ANCHOR_N, ANCHOR_SLU = _floor_gate.FLOOR_TABLE[ff.MEASUREMENT_DESIGN].sampling_by_metric["slu"][0]
_ANCHOR_N_INTENT, ANCHOR_INTENT = _floor_gate.FLOOR_TABLE[ff.MEASUREMENT_DESIGN].sampling_by_metric["intent"][0]
FLOOR_SLU, _ = _floor_gate.floor_for(ff.MEASUREMENT_DESIGN, ff.LEDGER_ROWS, metric="slu")
FLOOR_INTENT, _ = _floor_gate.floor_for(ff.MEASUREMENT_DESIGN, ff.LEDGER_ROWS, metric="intent")
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


def declared(key: str) -> dict:
    """A cell's declared expectation: P-SV-1..3 0.0 nominated (claims_benefit false); P-SV-4 1.1 pp intent
    (claims_benefit true, the recall note's implied intent on Fold B)."""

    c = ff.CELLS[key]
    return {
        "expected_effect_pp": c.get("expected_effect_pp", 0.0),
        "claims_benefit": c.get("claims_benefit", False),
        "primary_metric_key": c.get("primary_metric_key", "intent" if key == "psv1" else "present"),
    }


def intent_primary(key: str) -> bool:
    return declared(key)["primary_metric_key"] == "intent"


def receipt_schema(key: str) -> str:
    return "saea-perception-branch-arms-v3" if key == "psv4" else "saea-perception-branch-arms-v1"


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


def registered_supply(identity: dict) -> dict:
    """The prepared first-phase supply a registered plan declares. Before the flip: the placeholder. After the
    flip the cell baseline fragment carries the minted pin, and ``registered-supply-binding``
    (scripts/checks/flight_registration_check.py, 2026-10-03) requires the plan to declare EXACTLY that, so it is
    copied verbatim (same rule as scripts/flights/nx/write_slurp_nx_r1_registration.py)."""

    supply = {
        "relpath": f"prepared/{identity['run_id']}/phase-supply-v2.json", "sha256": "MINTED_AT_THE_FLIP",
        "note": "the first Fold B first-phase supply at w_agree 1.0 on this roster; branch A's router must reproduce it on every row (spec section 3, AT-P6)",
    }
    baseline_path = REPO_ROOT / "configs" / "baseline" / f"{identity['baseline_fragment']}.json"
    if baseline_path.is_file():
        pinned = json.loads(baseline_path.read_text(encoding="utf-8")).get("prepared_phase_supply")
        if isinstance(pinned, dict) and pinned.get("sha256") not in (None, "", "MINTED_AT_THE_FLIP"):
            supply = dict(pinned)
    return supply


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
    elif key == "psv2":
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
    elif key == "psv4":
        proof = ff.K6P_PROOF
        ceiling = {
            "rows": ceiling_rows, "pp": ff.pp(ceiling_rows), "roster": ff.READ_ROSTER,
            "what": (f"the +{ceiling_rows} net Fold B rows K6p lifts to boundary-block rank 1 over the centroid + "
                     f"agreement key ({proof['fold_b']['rank1_k6p']} vs {proof['fold_b']['rank1_cent_agree']} of 1,080; "
                     f"Fold A +22, {proof['fold_a']['rank1_k6p']} vs {proof['fold_a']['rank1_cent_agree']}), an offline "
                     f"model-free read of sealed vectors ({ff.K6P_NOTE}), reproduced from the two pinned artifacts by "
                     f"{proof['script']} (proof.json sha256 {proof['sha256'][:8]})"),
        }
        basis = (f"implied intent +{c['implied_intent_rows_fold_b']} rows of 1,080 on Fold B (+11.5 on Fold A; +5.0 to "
                 "+6.6 in each of the four utterance halves), the note's analogue: rows lifted to block rank 1 are "
                 "assumed to convert like today's rank-1 rows (P-SV-1 a-agree's rank-conditional conversions on Fold B). "
                 f"expected_effect_pp {c['expected_effect_pp']} = {c['implied_intent_rows_fold_b']} / 1,080 rounded. "
                 "Presence cost -0.7 / +0.2 pp (Fold A / Fold B); against the description key the P-SV cells fly as A, "
                 "the presence change is 0 / +14 rows, so the flown A is a stricter comparator than cent_agree on rank "
                 "and a looser one on presence. Rows lifted may be harder than today's rank-1 rows: the declaration "
                 "is a registered expectation, never a claim. DISCLOSURE: the key family was chosen offline over the sealed "
                 "vectors of BOTH folds (15 families compared; K6p carries no tuned parameter beyond the flown weights, and "
                 "its centring statistics come from the Fold-B-disjoint R01C roster), so TRAIN Fold B is not a clean held-out "
                 "roster for the key CHOICE; the registered tuning roster stays Fold A, and Fold B is read only through this "
                 "flight's own same-flight columns")
    else:
        # psv3: 83 = 49 (in block) + 34 (out of block) wrong rows with gold off Perception's list entirely on Fold A
        # (docs/results/2026-09-28-slurp-node-information-gain-ledger.md section 1.4 and section 5 item 1). This
        # ceiling covers BOTH sub-populations because raising the boundary-supply depth can, in principle, reach
        # either: the 34 by literally retrieving gold into the (now wider) block, the 49 as a side effect of the
        # wider note. No conversion is claimed for either: this axis changes only what Perception is SHOWN
        # (fuse_coverage.m/top_l), never the response contract or the presentation it renders from that supply.
        assert ceiling_rows == ff.IN_BLOCK_DROPPED_ROWS + ff.OUT_OF_BLOCK_DROPPED_ROWS
        ceiling = {
            "rows": ceiling_rows, "pp": ff.pp(ceiling_rows), "roster": ff.TUNING_ROSTER,
            "what": (f"the {ceiling_rows} wrong rows with gold off Perception's list on Fold A entirely "
                     f"({ff.pp(ceiling_rows)} pp presence ceiling): {ff.IN_BLOCK_DROPPED_ROWS} of them still inside "
                     f"the retrieved boundary block but off the rendered list, {ff.OUT_OF_BLOCK_DROPPED_ROWS} "
                     f"outside the block entirely, {ff.NODE_LEDGER}"),
        }
        basis = ("no conversion is claimed: raising the boundary-supply depth (fuse_coverage.m and fuse_coverage.top_l "
                 "together, 8 -> 12, c unchanged) only changes what Perception is SHOWN, never the response contract "
                 "or the presentation it renders from that supply; whether a newly shown item reaches top-1, appears "
                 "on the note's candidate list, or changes the level-2 Solver's answer is UNMEASURED (row 139: no "
                 "prior, so the declaration is 0.0 nominated with the ceiling beside)")
    if intent_primary(key):
        floor_note = (
            f"provisional intent floor {FLOOR_INTENT:.4f} pp ({ANCHOR_INTENT:g} x sqrt({_ANCHOR_N_INTENT} / "
            f"{ff.LEDGER_ROWS}), owner decision 190 anchor for {ff.MEASUREMENT_DESIGN})"
        )
    else:
        floor_note = (
            "primary_metric_key 'present': gold-on-list carries no numeric floor under owner decision 190 (or the "
            "table it superseded); reported, never checked against a bound"
        )
    d = declared(key)
    if d["claims_benefit"]:
        verdict = (f"expected_effect_pp {d['expected_effect_pp']} sits ABOVE this design's {floor_note} (a same-flight "
                   "column, so the cross-flight floor does not apply), so claims_benefit is true -- at about 1.7 x the "
                   "floor, knowingly near it (the note's own caveat)")
    else:
        verdict = (f"expected_effect_pp 0.0 sits below this design's {floor_note}, so claims_benefit is false")
    note = (
        f"Phase-2 cell {c['label']} (level 2, K = 3). Expected effect declared from "
        f"{'the recall note' if key == 'psv4' else 'the ledger'}'s measured numbers: "
        f"ceiling {ceiling['what']}; conversion basis: {basis}. {verdict}; the read's bar is the twin (T) null measured in this "
        "flight, per metric |T - A offset| + its CI95 half-width. The delivered row is branch A: delivered intent and "
        "SLU are identical by construction at the request level (reported, never contrasted). Tuning roster TRAIN "
        "Fold A (the node ledger shaped the design), read roster TRAIN Fold B (ruling O2; owner decision 186: "
        "rollout-exposed only, no branch value built from Fold B rollouts)."
    )
    provisional_floor_pp = (
        {"intent_accuracy": round(FLOOR_INTENT, 4), "slu_f1": round(FLOOR_SLU, 4),
         "arithmetic": f"intent {ANCHOR_INTENT:g} * sqrt({_ANCHOR_N_INTENT} / 1080) = {FLOOR_INTENT:.4f} pp "
                       f"(primary; owner decision 190 anchor), SLU {ANCHOR_SLU:g} * sqrt({ANCHOR_N} / 1080) = "
                       f"{FLOOR_SLU:.4f} pp (guard reference)"}
        if intent_primary(key) else
        {"present": None, "intent_accuracy": round(FLOOR_INTENT, 4), "slu_f1": round(FLOOR_SLU, 4),
         "arithmetic": "primary_metric_key 'present' (gold-on-list) carries no numeric floor under owner "
                       "decision 190; intent and SLU are reported beside, never gating this cell"}
    )
    return {
        arm["run_id"]: {
            "measurement_design": ff.MEASUREMENT_DESIGN, "rows": arm["rows"], "level": ff.LEVEL,
            "expected_effect_pp": d["expected_effect_pp"], "claims_benefit": d["claims_benefit"], "claim": "nominated",
            "primary_metric": c["primary_metric"],
            "primary_metric_key": d["primary_metric_key"],
            "aa_arm_id": ff.ARM_T,
            "tuning_roster": ff.TUNING_ROSTER, "read_roster": ff.READ_ROSTER,
            "ceiling": ceiling, "conversion_basis": basis,
            "variant_cost": {
                "extra_contacts_per_row": 4, "extra_perception_contacts_per_row": 2, "extra_solver_contacts_per_row": 2,
                "extra_audio_seconds": round(4 * audio, 3), "extra_audio_seconds_per_row_mean": round(4 * audio / arm["rows"], 4),
                "note": ("K - 1 = 2 non-A branches (B and the twin T), each one Perception contact at the one Perception "
                         "visit and one Solver contact at the first Solver visit (level 2); every contact re-sends the "
                         f"row's speech packet, so 2 x row audio per branch, 4 x the Fold B total {audio} s per flight"),
            },
            "provisional_floor_pp": provisional_floor_pp,
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
        "half-width, reported beside the design's own provisional floor per metric (owner decision 190; "
        "stage3_measurement.provisional_floor_pp -- intent {:.4f} pp, SLU {:.4f} pp). ".format(FLOOR_INTENT, FLOOR_SLU)
    )
    if key == "psv4":
        # P-SV-1's rule, copied with the axis named (the key_source swap in place of the top-2 contrast block).
        return common + (
            f"(2) THE CONTRAST: {b} (key_source K6p: the centred centroid key and the centred Fold B speech queries, "
            "agreement unchanged) minus A on the level-2 branch Solver column's official intent accuracy (primary). "
            "NOMINATED iff the intent CI95 lower bound is above zero AND the point delta exceeds the twin's intent bar "
            "AND the SLU-F1 CI95 lower bound of the same column is not below minus the twin's SLU bar (guard). "
            "BRANCH-LOCAL HARM iff the intent CI95 upper bound is below zero and the point magnitude exceeds the twin "
            "bar. Otherwise NOT NOMINATED. Reported beside, never gating: gold-on-list (present) and mean gold rank of "
            "the B note vs A and T, gold at supplied-block rank 1 (the note's mechanism: +26 rows expected on Fold B), "
            "the conversion P(correct | gold rank r in the branch note) against the ledger's 97.57 / 26.98 / 12.0 %, "
            "and the delivered row (identical by construction). A nomination sends the composed policy to a "
            "full-system cross-flight read against an in-chain A/A; it admits nothing."
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
    # each cell reads its OWN fit measure (P-SV-4 on: the v2 file carrying the key_source bound)
    measure = json.loads((data / ff.fit_measure_relpath(key)).read_text(encoding="utf-8"))
    n = ff.names(key, "arm")
    package, prereg = n["package"], n["prereg"]
    ids = identities(key)
    arm, smoke = ids["arm"], ids["smoke"]
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    group = arm["branches"]
    fit = fold_check(key, args.check_dir, measure)
    rule = decision_rule(key)
    measurement = measurement_blocks(key, ids, measure)
    ct, v1, cov = ff.CONTRAST_PAIR_TABLE, ff.CONTRAST_PAIR_TABLE_V1, ff.CONTRAST_PAIR_COVERAGE
    contrast_pin = {
        "presentation_id": "top2-contrast-v1",
        "table_relpath": ct["table_relpath"], "sha256": ct["sha256"],
        "builder": f"{ff.CONTRAST_PAIR_BUILDER} {ff.CONTRAST_PAIR_BUILDER_ARGS}",
        "coverage": cov,
        "status": (
            f"RE-PINNED {ct['pinned_date']} to V2 ({ff.CONTRAST_PAIR_RULING} ruling): the nearest-rival V1 table "
            f"({v1['pairs_written']} pairs, pinned {v1['pinned_date']}) covered only {cov['v1_nearest_rival']['rows_hit']} of "
            f"{cov['rows_total']:,} P-SV-1 b-top2contrast rows (38.5%; {cov['coverage_script']}), "
            f"{cov['v1_nearest_rival']['rows_no_table_row']} rows naming a rank-1/rank-2 pair the table never built. V2 is "
            "EVERY unordered pair of distinct SLURP intents above the same pool-support floor (min_pair_pool_support 5), "
            f"roster-agnostic, from the SAME R01/Fold-A/Fold-B-excluded TRAIN pool: {ct['pairs_written']:,} pairs written / "
            f"{ct['pairs_skipped']} skipped of {ct['pairs_considered']:,} considered (C(60,2)), skip reason "
            f"insufficient-pool-support. Coverage against this seed rises to {cov['v2_all_pairs']['rows_hit']:,}/"
            f"{cov['rows_total']:,} (96.0%); the residual {cov['v2_all_pairs']['rows_no_table_row']} rows land on the 2 "
            "pairs still below the floor (cooking_query/cooking_recipe, iot_hue_lightoff/iot_hue_lighton -- the same 2 of "
            f"60 V1 skipped). V1 itself is untouched and unchanged: {ff.CONTRAST_PAIR_BUILDER} --check confirms its content "
            f"(schema, artifact_id, builder_id, min_pair_pool_support, rows) is still the pinned {v1['pairs_written']}-pair "
            f"table, sha256 {v1['sha256']}. The table pin sits on the b-top2contrast branch (contrast_pairs: relpath "
            f"{ct['table_relpath']}, sha256 {ct['sha256']}), emitted by {DERIVE_SCRIPT} from "
            "scripts/flights/psv/psv_family.py, and the runtime loads it once per flight, verifies the file's bytes against "
            "that sha256, and hands the top2-contrast-v1 renderer the table as a mapping; the table document's own schema "
            "field is unchanged (saea-slurp-perception-contrast-pairs-v1). The cell was re-derived against this pin "
            "(composed config and protocol hashes in identity); root's flip re-pins the prepared branch seed against the "
            "widened branch identity."
        ),
        "receipt": {
            "relpath": ct["receipt_relpath"], "sha256": ct["receipt_sha256"], "artifact_id": ct["artifact_id"],
            "exposure_ledger_row": ct["exposure_ledger_row"], "pairs_considered": ct["pairs_considered"],
            "pairs_written": ct["pairs_written"], "pairs_skipped": ct["pairs_skipped"],
        },
        "requirements": ("built model-free (W3a's word-gap method) over the SAME R01-excluded TRAIN pool as V1, "
                         f"roster-agnostic ({ff.CONTRAST_PAIR_RULING} ruling, {ff.SPEC}: every unordered pair of distinct "
                         "intents above the pool-support floor, never selected from a roster's seeds); its pool must be "
                         "proven disjoint from TRAIN Fold B by utterance identity before the flip (phase-2 inputs README: "
                         "'Not checked here: a contrast-pair pool'); the pin enters where the runtime reads it (merge set C "
                         "item 4/6), then the cell is re-derived and re-pinned"),
    } if key == "psv1" else None
    key_source_pin = {
        "axis": "key_source (rails/supply_variants.py PerceptionBranchKeySource; refusals 19-20; receipt schema v3)",
        "block": ff.k6p_key_source(),
        "key": ff.K6P_KEY, "queries_fold_b": ff.K6P_QUERIES_FOLD_B, "proof": ff.K6P_PROOF, "note": ff.K6P_NOTE,
        "status": ("PINNED 2026-09-30: both artifacts built model-free (ledger rows "
                   f"{ff.K6P_KEY['ledger_row']} and {ff.K6P_QUERIES_FOLD_B['ledger_row']}, DRAFT) and proven to reproduce "
                   "the note's K6p block on both folds (1,080 / 1,080 blocks identical; rank-1 lift +22 / +26). The runtime "
                   "re-verifies each file's bytes against its sha256 at seed preparation (FlightRuntime._apply_key_source) "
                   "and flight_registration_check's key-source-unpinned finding checks them at registration. The swap is "
                   "rendering-only: the branch's seed is built by its own router at prepare-branch-seeds; A and T never "
                   "see it; the store, its release and snapshot and every delivered body are unchanged."),
    } if key == "psv4" else None
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": f"Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block {ff.GATE} and scripts/checks/flight_registration_check.py resolve (keyed by run id).",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "184": f"register {c['label']} on TRAIN Fold B at level 2, claim nominated (phase 2 of the same-flight instrument)",
            "186": "Fold B is ROLLOUT-exposed while it is the phase-2 read roster; no branch value of a cell read on Fold B is built from Fold B rollouts",
            "188": "B5 (Reviewer top-2 contrast) deferred behind P-SV-1 / P-SV-2",
            "139": ("no prior: the expectation is declared from measured numbers (P-SV-4: the recall note's offline implied intent, 1.1 pp, claims_benefit true)"
                    if key == "psv4" else "no prior: the expectation is declared from measured ledger numbers (0.0 nominated, ceiling beside)"),
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
                                "B, one axis: key_source K6p -- the branch's own router recalls the intent-boundaries store with the centred centroid key (facet_source) and the centred Fold B speech queries (query_source), agreement unchanged, w_cos / w_agree 1 / 1 and fuse 8/1/8 as flown; the same store, release, snapshot and delivered bodies as A, a different ranking of which boundary items are shown"
                                if key == "psv4" else
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
        **({"key_source": key_source_pin} if key_source_pin is not None else {}),
        "fit_measure": {"relpath": ff.fit_measure_relpath(key), "sha256": sha_file(data / ff.fit_measure_relpath(key)), "tool": FIT_SCRIPT,
                        "summary": {k: measure[k] for k in ("chars_per_token_least_squares", "perception", "fit_estimate",
                                                            "prompt_limit_tokens", "headroom_items", "contrast_allowance_items",
                                                            "max_supplied_items", "estimates", "first_solver_visit_prompt_tokens")}},
        "fit": fit,
        "identity": {kind: {k2: v for k2, v in ids[kind].items() if k2 != "composed_config_diff_against_the_agree_cell"} for kind in KINDS},
        "composed_config_diff_against_the_agree_cell": {kind: ids[kind]["composed_config_diff_against_the_agree_cell"] for kind in KINDS},
        "decision_rule": rule,
        "budget_arithmetic": {"arm_family_budget": caps, "smoke_family_budget": smoke_caps,
                              "note": "the AGREE arithmetic at ceiling 15 with the Fold B audio: generation rows x 15, FIT rows x 15 x 4, speech ceil(audio x 15), GPU hours 12.0 x 15 / 11 = 16.4 (smoke 1.0); native task-contract calls + 4 per row; run-cumulative"},
        **({"registration_basis": (
            "coordinator brief 2026-09-30 acting on the recall note's recommendation 2 (register K6p as a rank-quality "
            "candidate; build the two zero-contact artifacts; a key_source Perception-branch axis for a level-2 same-flight "
            "column). HELD: the owner / root admission is still required; nothing here authorises a flip or a flight.")}
           if key == "psv4" else {}),
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
                "prepared_phase_supply": registered_supply(identity),
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
            f"1. Refuse unless the flight carries a COMPLETE sealed 1,080-row manifest with one complete official TRAIN score, the {receipt_schema(key)} receipt on every row and I7v's Perception path verified by the bundle.",
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
        + ([f"flipping P-SV-1 with a b-top2contrast contrast_pairs pin other than the registered V2 table ({ff.CONTRAST_PAIR_TABLE['table_relpath']}, sha256 {ff.CONTRAST_PAIR_TABLE['sha256']}; {ff.CONTRAST_PAIR_RULING} ruling)"] if key == "psv1" else []),
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
        if row.get("key_source"):
            swapped = [f for f in ("facet_source", "query_source", "agreement_source") if row["key_source"].get(f)]
            axis = "`key_source` K6p (" + ", ".join(f"`{f}` {row['key_source'][f]['relpath']} (`{row['key_source'][f]['sha256'][:8]}`)" for f in swapped) + "; agreement unchanged)"
        rows.append(f"| `{row['branch_id']}` | {index} | {role} | {axis} | {row['max_supplied_items']} |")
    fe = group["fit_estimate"]
    ct, v1, cov = ff.CONTRAST_PAIR_TABLE, ff.CONTRAST_PAIR_TABLE_V1, ff.CONTRAST_PAIR_COVERAGE
    placeholder = (
        f"\n**Contrast-pair table pinned (V2, {ct['pinned_date']}, ruling {ff.CONTRAST_PAIR_RULING}).** The `top2-contrast-v1` "
        f"renderer reads the model-free contrast-pair table built by `{ff.CONTRAST_PAIR_BUILDER} {ff.CONTRAST_PAIR_BUILDER_ARGS}`: "
        f"`{ct['table_relpath']}` (data root), sha256 `{ct['sha256']}`, receipt `{ct['receipt_relpath']}` (sha256 "
        f"`{ct['receipt_sha256']}`; {ct['pairs_written']:,} pairs written / {ct['pairs_skipped']} skipped of "
        f"{ct['pairs_considered']:,}, insufficient pool support; every unordered pair of distinct intents above the floor, "
        "roster-agnostic, from the R01/Fold-A/Fold-B-excluded TRAIN pool). The pin sits on the branch "
        "(`b-top2contrast.contrast_pairs`) and the runtime verifies the file's bytes against it before any contact. It "
        f"replaces the nearest-rival V1 pin (`{v1['sha256'][:8]}`, {v1['pairs_written']} pairs), which covered "
        f"{cov['v1_nearest_rival']['coverage_fraction']} of this seed's rows against V2's "
        f"{cov['v2_all_pairs']['coverage_fraction']} (`{cov['coverage_script']}`). Registered in `registered-facts-v1.json` "
        "(`contrast_pair_table`).\n"
        if key == "psv1" else "")
    b_branch_row = next(row for row in group["branches"] if row["branch_id"] == c["b_branch"])
    if "prepared_seed" in b_branch_row:
        # This coverage count was measured once the seed existed (P-SV-1 / P-SV-2, disclosed 2026-09-29) and is
        # never recomputed here; a cell whose B branch has NOT been through prepare-branch-seeds yet (no
        # `prepared_seed` key at all -- e.g. P-SV-3 at first registration) carries no seed to disclose coverage of.
        placeholder += (
            "\n**Branch-seed coverage (disclosed before countersigning, 2026-09-29).** The B branch's pinned `prepared_seed` "
            f"(`{ff.branch_seed_relpath(key, 'arm')}`) carries seeds for 1,078 of the 1,080 Fold B rows: the two remaining "
            "Fold B rows have zero boundary recall for every column (A, B and T alike), a property of the data rather than "
            "of the branch.\n"
        )
    else:
        placeholder += (
            "\n**Branch-seed not yet prepared.** The B branch carries no `prepared_seed` pin: `core.flight.cli "
            "prepare-branch-seeds` has not run for this cell (left to root at the flip, per the readiness gate's "
            "`branch-seed-unpinned` finding).\n"
        )
    purpose_180 = (
        "\n**Purpose (coordinator, decision 180 consumption thesis; node-gain ledger).** Intent is decided at "
        "Perception's shortlist. Of the 153 wrong rows on Fold A, gold was off Perception's list on 83 (49 still "
        "inside the retrieved boundary block, 34 outside it). P-SV-2 (forced three candidates) tests whether the "
        "note can carry more of the in-block gold; P-SV-3 measures the boundary-supply DEPTH itself (how many "
        "boundary items Perception is shown) as a same-flight Perception-branch column: B is the same AGREE "
        "Perception supply with the boundary-supply depth raised one step (fuse_coverage.m and fuse_coverage.top_l, "
        "8 -> 12, c unchanged), read primarily on `present` (gold on the branch's list), with official intent "
        f"beside ({ff.NODE_LEDGER}, section 1.4 and section 5 item 1).\n"
        if key == "psv3" else
        "\n**Purpose (the retrieval-key recall read, 2026-09-30).** No key built from pinned vectors reaches +4 pp "
        "presence; one key changes rank QUALITY: K6p, the centred centroid + agreement key under production admission, "
        "lifts gold to boundary-block rank 1 on +22 (Fold A) / +26 (Fold B) rows over the centroid + agreement key, "
        f"about +1.1 pp implied intent on both folds ({ff.K6P_NOTE}). This cell reads that effect as a same-flight "
        "level-2 Solver column (the note: a note-only level-1 branch would not show a rank-1 conversion effect), "
        "through the new key_source Perception-branch axis: B re-keys the boundary retrieval with the two pinned K6p "
        "artifacts, everything else as A. The same-flight intent floor (0.65 pp at n = 1,080, owner decision 190) makes a "
        "~1.1 pp effect readable as a column; the cross-flight floor (2.5 pp) would not.\n"
        if key == "psv4" else ""
    )
    readme = f"""# Cell {c['label']}: phase-2 same-flight Perception branches on TRAIN Fold B (owner decisions 184, 186, 188)

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (branch `{args.branch}`);
this cell **held**. Nothing here authorises a flight, a flip or an admission entry. Development numbers only.
{purpose_180}
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
Expected effect **{m['expected_effect_pp']}** (nominated; `claims_benefit` {str(m['claims_benefit']).lower()}); ceiling {m['ceiling']['what']}. Conversion basis: {m['conversion_basis']}.
Provisional floor {(FLOOR_INTENT if intent_primary(key) else FLOOR_SLU):.4f} pp ({"intent, primary" if intent_primary(key) else "SLU, reference only -- primary_metric_key 'present' has no floor"}, owner decision 190); the bar is the twin null. `variant_cost`: +2 Perception and +2 Solver contacts per
row, +{m['variant_cost']['extra_audio_seconds']} speech seconds per flight (2 x row audio per non-A branch).

## Decision rule (fixed here)

{rule}

## Fit (core.flight.cli check, held)

{_fit_lines(fit)}

The first Solver visit's realised prompt on the AGREE arm was {measure['first_solver_visit_prompt_tokens']['min']}-{measure['first_solver_visit_prompt_tokens']['max']} tokens;
a branch Solver contact carries a branch note of the same shape in place of A's.

## Sequence

(1) Root countersigns the four DRAFT flight rows (the READ row `{n['read_run']}` stays draft until the seal) and mints
`{n['decision_relpath']}` with `scripts/flights/psv/psv_mint_receipt.py {key}`. (2) `bash scripts/flights/psv/psv_flip.sh {key}`
(loop form, converges at one HEAD; naming {key} explicitly leaves any sibling P-SV cell's own flip untouched). (3)
`bash scripts/flights/psv/batch_chain_psv.sh {key}` on slurp-np4 through the batch driver (smoke first, then the
one-cell arm campaign). (4) `bash scripts/flights/psv/psv_read.sh {key}`.

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
| expected effect | {m['expected_effect_pp']} pp, `claims_benefit` {str(m['claims_benefit']).lower()}; ceiling {m['ceiling']['rows']} rows = {m['ceiling']['pp']} pp on {m['ceiling']['roster']} |
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
        declaration = (f"measurement_design {ff.MEASUREMENT_DESIGN}, level 2, claim nominated, claims_benefit {str(m['claims_benefit']).lower()}, expected_effect_pp {m['expected_effect_pp']} "
                       f"(ceiling {m['ceiling']['rows']} rows = {m['ceiling']['pp']} pp on {m['ceiling']['roster']}), primary_metric_key {m['primary_metric_key']}, "
                       f"provisional floor {(FLOOR_INTENT if intent_primary(key) else FLOOR_SLU):.4f} pp ({'intent, primary' if intent_primary(key) else 'SLU, reference only -- present has no floor'}, owner decision 190), bar = the twin null, "
                       f"aa_arm_id {ff.ARM_T}, tuning_roster {ff.TUNING_ROSTER}, read_roster {ff.READ_ROSTER}, variant_cost +2 Perception and +2 Solver contacts per row, rows 1080"
                       if kind == "arm" else f"measurement_design form-proof, claims_benefit false, expected_effect_pp 0.0, rows 4, tuning_roster none, read_roster {ff.READ_ROSTER}")
        placeholder = (
            f" P-SV-1's top2-contrast-v1 branch reads its pinned contrast-pair table ({ff.CONTRAST_PAIR_BUILDER} "
            f"{ff.CONTRAST_PAIR_BUILDER_ARGS}; {ff.CONTRAST_PAIR_TABLE['table_relpath']} sha256 {ff.CONTRAST_PAIR_TABLE['sha256']}, "
            f"ruling {ff.CONTRAST_PAIR_RULING}) through b-top2contrast.contrast_pairs; the runtime verifies its bytes before any contact."
            if key == "psv1" else
            (f" P-SV-4's b-k6p branch carries key_source (facet_source {ff.K6P_KEY['relpath']} sha256 {ff.K6P_KEY['sha256']}; "
             f"query_source {ff.K6P_QUERIES_FOLD_B['relpath']} sha256 {ff.K6P_QUERIES_FOLD_B['sha256']}; agreement unchanged), "
             f"built model-free under {ff.K6P_KEY['ledger_row']} and {ff.K6P_QUERIES_FOLD_B['ledger_row']}; the runtime verifies both "
             "files' bytes at seed preparation. The b-k6p prepared_seed is minted by prepare-branch-seeds at the flip."
             if key == "psv4" else "")
        )
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
