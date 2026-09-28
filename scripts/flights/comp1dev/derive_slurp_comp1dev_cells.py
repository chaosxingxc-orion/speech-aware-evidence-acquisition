#!/usr/bin/env python3
"""Derive the three COMP-1 DEV-2000-ADDED cells -- the replication of the first
composed Stage-3 arm on the fresh evaluation roster (owner decision 161: AGREE enters
COMP-1 pending the DEV replication; docs/results/2026-09-27-verdict-reclassification.md:
the COMP-1 DEV-2000-ADDED round settles AGREE's KEEP-PROVISIONAL) -- from the SEALED
DEV-2000-ADDED plan arm's own fragments (decision 58: script-derived registrations).

WHAT THIS IS. Exactly COMP-1's plan bytes as the Fold A package
``docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1`` registers them (the locked
v2.0 plan + the agreement term w_agree 1.0 / recall k 60 / delivered 8-1-8 + the
centroid boundary key + the citation contract, and nothing else), with ONLY the roster
moved. The roster move is taken from the sealed DEV-2000-ADDED plan arm
``SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1`` (cell B6, replicated by PLANr-DEV2000),
whose fragments are the locked PLAN fragments with every roster-bound pin re-pointed:
the two speech query sources, the packet promotion receipt, the FIT cap, the scorer
(``slurp-slu-official``, the DEV sibling -- never the ``-train`` one), the split role
``dev`` and the population. ROLL-3 re-pointed the same keys the same way.

The four composed changes, each read from its registered source rather than restated:

  1. the AGREEMENT TERM exactly as the AGREE arm carries it (rank weights, recall k 60,
     delivered 8-1-8), with ONE roster-bound pin moved: the agreement table is the
     DEV-2000-ADDED table ``SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1``,
     built model-free by ``scripts/build_slurp_intent_exemplar_agreement.py`` against the
     sealed DEV comparator cell with the same builder, vote store, vote phase and
     target store the Fold A table used (the table is a function of the roster's own
     sealed speech vectors, so it cannot be carried over from Fold A);
  2. the CENTROID BOUNDARY KEY exactly as KPROBE pins it, byte for byte (roster-free:
     arithmetic over the R01-excluded construction-TRAIN pool);
  3. the CITATION CONTRACT exactly as COMP-1 Fold A arms it (four keys, one arming);
  4. nothing else.

THREE CELLS: the arm on DEV-2000-ADDED 1,000; its four-row form smoke (the roster's
first four rows by roster order, the rows and split identity cell ROLL-3's smoke
registered); and the IN-CHAIN A/A -- the DEV plan arm's own bytes at recall k 60 (a
proven no-op at pure cosine), whose own prepared supply must reproduce the sealed DEV
comparator's output digest ``d57ee9d6...``.

Every cell drops ``prepared_phase_supply`` so the flip mints each cell's OWN supply
(item E16); ``--allow-output-change`` must never be passed. This script writes CONFIG
ONLY. Two passes, converging in two: pass 1 at placeholder supply digests, then
``core.flight.cli prepare-supply`` per cell, then pass 2 with the measured digests.

    python scripts/flights/comp1dev/derive_slurp_comp1dev_cells.py --date 2026-09-27 \\
        --data-root "$SPEECHRL_DATA_DIR" \\
        [--arm-supply-sha256 <64 hex> --aa-supply-sha256 <64 hex> --smoke-supply-sha256 <64 hex>]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DEV_ARM_BASELINE = "configs/baseline/slurp-native-default-plan-dev2000-added-baseline-v1.json"
DEV_ARM_EXPERIMENT = "configs/experiment/slurp-native-default-plan-dev2000-added-v1.json"

#: The three registered factor sources, read rather than restated.
COMP1_FOLD_A_BASELINE = "configs/baseline/slurp-native-stage3-comp1-fold-a-baseline-v1.json"
AGREE_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
KPROBE_BASELINE = "configs/baseline/slurp-native-stage3-kprobe-fold-a-55-baseline-v1.json"
#: The smoke's four rows and their split identity, exactly as cell ROLL-3's smoke registered them.
ROLL3_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1.json"
DATASET_FRAGMENT = "configs/dataset/slurp-speech-native-dev2000-added.json"
ROSTER_RECEIPT = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"

DEV_PLAN_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1"
#: The sealed DEV plan preparation's OUTPUT digest (999 rows seeded, 7,970 ids). The
#: A/A cell's own prepared supply must reproduce it exactly.
DEV_PLAN_SUPPLY_OUTPUT_SHA = "d57ee9d6212bd3dc10762f84ec6ff1e8368b0b1a1e80fed9f9fbc81147fc5a19"
DEV_SPLIT = "ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67"
WRITTEN_KEY_SHA = "76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2"

#: The DEV-2000-ADDED agreement table (built model-free in this registration).
AGREEMENT_ARTIFACT = "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1"
AGREEMENT_RELPATH = f"prepared/{AGREEMENT_ARTIFACT}/agreement.jsonl"
AGREEMENT_RECEIPT_RELPATH = f"prepared/{AGREEMENT_ARTIFACT}/receipt.json"
FOLD_A_AGREEMENT_RECEIPT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/receipt.json"
CENTROID_ARTIFACT = "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1"
CENTROID_FACETS_RELPATH = f"prepared/{CENTROID_ARTIFACT}/facets.jsonl"
CENTROID_RECEIPT_RELPATH = f"prepared/{CENTROID_ARTIFACT}/receipt.json"

CITED_POLICY = "phase-native-candidates-review-revise-cited-v1"
CITED_RESPONSE_FORMAT = "saea-solver-cited-answer-v1"
CITED_SOLVER_TEMPLATE = "probes/slurp_native_role_solver_cited_v1.txt"
CITED_NORMALISER = "saea-deliver-cited-answer-normalise-v3-v1"
PLAN_POLICY = "phase-native-candidates-review-revise-v1"
PLAN_SOLVER_TEMPLATE = "probes/slurp_native_role_solver_v2.txt"
PLAN_NORMALISER = "saea-deliver-normalise-v3"

TAG = "COMP1"
ROSTER_TAG = "DEV2000-ADDED"
ROSTER_SLUG = "dev2000-added"
CEILING_PER_ROW = 11

THE_COMPOSITION = (
    "COMP-1 DEV-2000-ADDED is cell COMP-1's composed plan (docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1) "
    "with only the roster moved to the fresh evaluation roster DEV-2000-ADDED 1,000, exactly as the sealed "
    "DEV-2000-ADDED plan arm (cell B6) re-pointed the locked plan. (1) The agreement term as cell AGREE carries it: "
    "the intent-boundary Perception channel ranks with w_agree 1.0 over the pre-computed exemplar-intent vote, "
    "w_cos 1.0, w_prior 0.0, recall k 60, delivered width 8 (fuse_coverage m 8 / c 1 / top_l 8); the vote table "
    "is this roster's own (SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1: the same builder, vote store, "
    "vote phase and target store as the Fold A table, over this roster's own sealed speech vectors). (2) The "
    "centroid boundary key as cell KPROBE pins it, byte for byte. (3) The citation contract as COMP-1 arms it "
    "(saea-solver-cited-answer-v1, the cited Solver instruction, saea-deliver-cited-answer-normalise-v3-v1). "
    "(4) Nothing else: the geometry, the session, the phase program's 11-contact ceiling, the three stores' "
    "snapshots and releases, the exemplar k of 20, the role graph, the Perception / Reviewer / Planner templates "
    "and the DEV scorer are the sealed DEV plan arm's, byte for byte."
)

ARM_ALGORITHM_NOTE = (
    "The DEV-2000-ADDED replication of the first instance of sealed-credit-system-policy-v1 (owner decisions 138, "
    "152 and 161): the same three typed consumption actions COMP-1 composes on TRAIN Fold A -- a rank weight "
    "over a pre-computed vote, a retrieval key file, and the Solver's answer contract -- re-executed on the "
    "evaluation roster beside its in-chain replicate. Operator context_application; no rollout, no per-sample "
    "scoring, no credit assignment and no update of its own."
)
AA_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is the locked plan's own form on "
    "DEV-2000-ADDED re-flown in the same chain as the in-chain null and instrument of the COMP-1 DEV-2000-ADDED "
    "arm -- w_agree 0.0, no agreement_source, the written boundary key, the un-armed citation default. Its "
    "prepared first-phase supply reproduces the sealed DEV plan arm's output digest exactly."
)
SMOKE_ALGORITHM_NOTE = (
    "The four-row structural form smoke of the COMP-1 DEV-2000-ADDED arm: the same three composed actions on the "
    "first four rows of the unchanged DEV-2000-ADDED roster, labelled as the arm is because it flies the arm's "
    "form; scored by no one and read by no one."
)


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + (
        "\n" if raw.endswith("\n") else ""
    )


def substitutions(tag: str, slug: str, *, smoke: bool) -> list[tuple[str, str]]:
    """Longest-first id rewrites from the DEV plan fragment to this cell's own."""

    suffix = "-SMOKE-4" if smoke else ""
    slug_suffix = "-smoke-4" if smoke else ""
    return [
        ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-FIT-V1", f"SAEA-SLURP-STAGE3-{tag}-{ROSTER_TAG}{suffix}-FIT-V1"),
        ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1", f"SAEA-SLURP-STAGE3-{tag}-{ROSTER_TAG}{suffix}-V1"),
        ("attempt-slurp-native-default-plan-dev2000-added-generation-v1", f"attempt-slurp-native-stage3-{slug}-{ROSTER_SLUG}{slug_suffix}-generation-v1"),
        ("attempt-slurp-native-default-plan-dev2000-added-fit-v1", f"attempt-slurp-native-stage3-{slug}-{ROSTER_SLUG}{slug_suffix}-fit-v1"),
        ("slurp-native-default-plan-dev2000-added-baseline-v1", f"slurp-native-stage3-{slug}-{ROSTER_SLUG}{slug_suffix}-baseline-v1"),
        ("slurp-native-default-plan-dev2000-added-v1", f"slurp-native-stage3-{slug}-{ROSTER_SLUG}{slug_suffix}-v1"),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def registered_factors(data_root: Path) -> tuple[dict, dict, dict, dict]:
    """``(agreement_source, agreement receipt entry, facet_source, centroid receipt entry)``.

    The agreement term's rank weights, k and fuse width come from the AGREE baseline and
    must equal COMP-1 Fold A's; the agreement PIN is this roster's own table, verified on
    the data root against its receipt (rows 1,000, the DEV comparator cell, the DEV split
    identity, the same vote/target store and snapshots as the Fold A table's receipt).
    The centroid key and its receipt are KPROBE's, byte for byte.
    """

    agree = json.loads(rd(AGREE_BASELINE))
    agree_p = agree["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    comp1 = json.loads(rd(COMP1_FOLD_A_BASELINE))
    comp1_p = comp1["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if agree_p["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0} or agree_p["k"] != 60:
        raise SystemExit("the AGREE baseline is not at w_agree 1.0 / k 60 as registered")
    if agree_p["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8}:
        raise SystemExit("the AGREE baseline's delivered width is not 8-1-8")
    for key in ("rank_weights", "k", "fuse_coverage", "tau", "rank_policy", "fuse_policy", "facet_source"):
        if key != "facet_source" and comp1_p[key] != agree_p[key]:
            raise SystemExit(f"COMP-1 Fold A's {key} is not AGREE's")

    receipt_path = data_root / AGREEMENT_RECEIPT_RELPATH
    artifact_path = data_root / AGREEMENT_RELPATH
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    fold_a_receipt = json.loads((data_root / FOLD_A_AGREEMENT_RECEIPT_RELPATH).read_text(encoding="utf-8"))
    derived = receipt["derived_from"]
    if receipt["artifact"]["sha256"] != sha_file(artifact_path) or receipt["artifact"]["rows"] != 1000:
        raise SystemExit("the DEV agreement table does not hash to its receipt or is not 1,000 rows")
    if derived["run_id"] != DEV_PLAN_RUN or derived["split_identity_hash"] != DEV_SPLIT:
        raise SystemExit("the DEV agreement table was not derived from the sealed DEV plan cell on DEV-2000-ADDED")
    for key in ("vote_store", "vote_phase", "vote_key", "target_store", "target_facet_template",
                "target_snapshot_sha256", "vote_snapshot_sha256", "program_id"):
        if derived[key] != fold_a_receipt["derived_from"][key]:
            raise SystemExit(f"the DEV agreement table's {key} differs from the Fold A table's")
    measured = receipt["measured"]
    if measured["rows_with_no_vote"] != 0 or measured["pool_values_without_a_build_time_target"] != 0:
        raise SystemExit("the DEV agreement table carries rows with no vote or untargeted pool values")

    agreement_source = dict(agree_p["agreement_source"])
    agreement_source["relpath"] = AGREEMENT_RELPATH
    agreement_source["sha256"] = receipt["artifact"]["sha256"]
    agreement_source["tool_contact_ledger_row"] = AGREEMENT_ARTIFACT
    agreement_receipt = {"relpath": AGREEMENT_RECEIPT_RELPATH, "root": "data", "sha256": sha_file(receipt_path)}

    kprobe = json.loads(rd(KPROBE_BASELINE))
    kprobe_p = kprobe["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    facet_source = dict(kprobe_p["facet_source"])
    if facet_source["relpath"] != CENTROID_FACETS_RELPATH or facet_source["kind"] != "sealed-vectors":
        raise SystemExit("the KPROBE baseline's facet_source is not the centroid key pin")
    if facet_source != comp1_p["facet_source"]:
        raise SystemExit("COMP-1 Fold A's facet_source is not KPROBE's pin")
    centroid_receipt = next(
        dict(r) for r in kprobe["preparation_source_receipts"] if r["relpath"] == CENTROID_RECEIPT_RELPATH
    )
    return agreement_source, agreement_receipt, facet_source, centroid_receipt


def derive_baseline(parent_path, out_path, pairs, *, composed, factors, what_this_is, smoke_fit_cap=None) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document.pop("prepared_phase_supply", None)
    document["what_this_is"] = what_this_is
    if smoke_fit_cap is not None:
        document["native_contact_fit"]["contact_cap"] = smoke_fit_cap
    if document["scorers"] != ["slurp-slu-official", "cost"]:
        raise SystemExit("the DEV parent does not score with the DEV sibling slurp-slu-official")
    perception = document["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if perception["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0}:
        raise SystemExit("the parent's boundary rank weights are not the flown identity")
    if perception["k"] != 8 or perception["tau"] != 0.0:
        raise SystemExit("the parent's boundary k/tau are not the flown 8 / 0.0")
    if perception["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8}:
        raise SystemExit("the parent's boundary fuse coverage is not the flown 8/1/8")
    if perception["facet_source"]["sha256"] != WRITTEN_KEY_SHA:
        raise SystemExit("the parent's boundary facet_source is not the flown written-key pin")
    if "agreement_source" in perception:
        raise SystemExit("the parent declares an agreement_source; refusing")
    if document["policy"] != PLAN_POLICY:
        raise SystemExit("the parent's policy is not the locked phase program")
    solver = document["phase_material"]["solver"]
    if solver["instruction_template"] != PLAN_SOLVER_TEMPLATE or solver["response_format_id"] is not None:
        raise SystemExit("the parent's Solver material is not the locked plan's")
    if document["native_episode"]["deliver_normaliser"] != {"normaliser": PLAN_NORMALISER}:
        raise SystemExit("the parent's deliver_normaliser is not the locked v3 projection")
    # The recall width on BOTH arms (see the Fold A derivation): k 60 is a proven no-op at
    # pure cosine and the A/A must prove it again by digest.
    perception["k"] = 60
    if composed:
        agreement_source, agreement_receipt, facet_source, centroid_receipt = factors
        perception["rank_weights"] = {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0}
        perception["agreement_source"] = dict(agreement_source)
        perception["facet_source"] = dict(facet_source)
        receipts = document.setdefault("preparation_source_receipts", [])
        for entry in (agreement_receipt, centroid_receipt):
            if any(r["relpath"] == entry["relpath"] for r in receipts):
                raise SystemExit(f"the parent already pins {entry['relpath']}")
            receipts.append(dict(entry))
        document["preparation_source_receipts"] = sorted(receipts, key=lambda e: (e["root"], e["relpath"]))
        document["policy"] = CITED_POLICY
        solver["instruction_template"] = CITED_SOLVER_TEMPLATE
        solver["response_format_id"] = CITED_RESPONSE_FORMAT
        document["native_episode"]["deliver_normaliser"] = {"normaliser": CITED_NORMALISER}
    wr(out_path, dump_like(raw, document))


def smoke_population() -> tuple[list[str], str, float]:
    """The four rows, their split identity and audio seconds, exactly as cell ROLL-3's smoke
    registered them, re-verified against the roster order and the dataset fragment."""

    roll3 = json.loads(rd(ROLL3_SMOKE_EXPERIMENT))
    ids = list(roll3["populations"][0]["ids"])
    split = roll3["population"]["split_identity_hash"]
    roster = json.loads(rd(ROSTER_RECEIPT))
    items = roster["items"]
    first = [item["sample_id"] if isinstance(item, dict) else item for item in items[:4]]
    if first != ids:
        raise SystemExit("ROLL-3's smoke rows are not the roster's first four rows")
    dataset = json.loads(rd(DATASET_FRAGMENT))
    seconds = {item["sample_id"]: item["audio_seconds"] for item in dataset["items"]}
    return ids, split, sum(seconds[i] for i in ids)


def derive_experiment(parent_path, out_path, pairs, args, *, purpose, readiness_reason, preparation_requirements,
                      campaign, algorithm, smoke=None) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    cell = document["cells"][0]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": preparation_requirements, "state": "held"}
    document["failure_policy"] = document["failure_policy"].replace("closes this flight", "closes this cell")
    document["stage3_algorithm"] = algorithm
    document["population"]["roster_receipt"] = ROSTER_RECEIPT
    if smoke is not None:
        ids, split, seconds = smoke
        rows = len(ids)
        audio_cap = math.ceil(seconds * CEILING_PER_ROW)
        document["fragment_kind"] = "saea-slurp-native-stage3-comp1-dev2000-added-smoke-4-v1"
        document["population"] = {
            "count": rows,
            "dataset_fragment": document["population"]["dataset_fragment"],
            "decision_population": (
                f"The first {rows} rows, by roster order, of the unchanged DEV-2000-ADDED roster {ROSTER_RECEIPT}: "
                + ", ".join(ids)
                + f" ({seconds} s of audio), split identity {split} -- exactly the rows and split identity cell "
                "ROLL-3's four-row smoke registered (configs/experiment/slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1.json), "
                "re-verified here against the roster order. Structural form proof only: no score and no read."
            ),
            "split_identity_hash": split,
        }
        document["populations"] = [{"dataset_fragment": document["population"]["dataset_fragment"], "ids": ids}]
        document["family_budget"].update({
            "fit_endpoint_calls_cap": rows * CEILING_PER_ROW * 4,
            "generation_calls_cap": rows * CEILING_PER_ROW,
            "gpu_hours_fit_inclusive": 1.0,
            "native_task_contract_calls_cap": rows * 6,
            "official_complete_scoring_jobs": 0,
            "repeated_speech_audio_seconds_cap": audio_cap,
        })
        document["execution_plan"].update({
            "planned_gpu_hours": 1.0,
            "planned_model_calls": rows * CEILING_PER_ROW,
            "planned_speech_audio_seconds": audio_cap,
        })
        document["generation_budget"] = {
            "cap": rows * CEILING_PER_ROW,
            "definition": (
                f"{rows} rows x {CEILING_PER_ROW}, the locked phase program's own ceiling (perception 1, solver 1, "
                "reviewer 3, planner 1, max_revisions 1 -> 1 + 2 * (3 + 1 + 1)); the citation contract adds tokens "
                f"per Solver contact, never contacts. Speech: ceil({seconds} s x {CEILING_PER_ROW}) = {audio_cap} s."
            ),
            "target": rows * 5,
        }
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. "
            "A failed smoke stops cell COMP-1 DEV-2000-ADDED and the arm does not open. The resume-recovery clause "
            "of owner decision 22 applies to the arm, not to a four-row form smoke, which is re-flown whole if it is "
            "re-flown at all."
        )
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--data-root", required=True)
    for name in ("arm", "smoke", "aa"):
        parser.add_argument(f"--{name}-supply-sha256", default="0" * 64)
    args = parser.parse_args(argv)
    for value in (args.arm_supply_sha256, args.smoke_supply_sha256, args.aa_supply_sha256):
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise SystemExit("every supply digest must be a lowercase sha256")

    factors = registered_factors(Path(args.data_root))
    agreement_source = factors[0]
    smoke = smoke_population()
    written: list[str] = []

    agreement_requirement = {
        "kind": "preparation",
        "reason": (
            "The pre-computed exemplar-intent AGREEMENT table this cell's boundary channel ranks with: THIS "
            "roster's own table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1, built model-free by "
            "scripts/build_slurp_intent_exemplar_agreement.py against the sealed DEV-2000-ADDED plan cell with the "
            "builder, vote store, vote phase and target store of the Fold A table cell AGREE registered, from the "
            "pinned exemplar snapshot, the pinned pool key vectors and this roster's own pinned speech query "
            "vectors -- zero model, server, encoder, embedder, scorer, network and GPU contacts. Measured: 1,000 "
            "rows, every row 20 votes, 0 self-excluded exemplars (the TRAIN-built pool shares no utterance with "
            "the roster), 0 rows with no vote, 59 distinct boundary facets ever voted for. The centroid key file is "
            "deliberately NOT a readiness requirement: it is pinned where the loader verifies it "
            "(facet_source.sha256) and its receipt in preparation_source_receipts, as cell KPROBE registered it."
        ),
        "relpath": agreement_source["relpath"],
        "sha256": agreement_source["sha256"],
    }
    supply_reason_composed = (
        "This cell's OWN prepared first-phase Perception supply, built model-free under this cell's own run id with "
        "core.flight.cli prepare-supply from the sealed DEV-2000-ADDED speech-query segment vectors, the CENTROID key "
        "file SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and this roster's sealed agreement table, with zero model, "
        "tokenizer, encoder, scorer or server contacts. E16: this cell pins its own. --allow-output-change must "
        "never be passed."
    )
    supply_reason_aa = (
        "This cell's OWN prepared first-phase Perception supply, built model-free under this cell's own run id with "
        "core.flight.cli prepare-supply from the same sealed DEV-2000-ADDED speech-query segment vectors and the same "
        "sealed written-key facet vectors the sealed DEV plan arm used, with zero model, tokenizer, encoder, scorer "
        "or server contacts. Its output digest must equal the sealed DEV plan preparation's "
        + DEV_PLAN_SUPPLY_OUTPUT_SHA
        + " (the byte-identity proof that the A/A flies the locked plan's own bytes on this roster). E16: this cell "
        "pins its own. --allow-output-change must never be passed."
    )
    held_tail = (
        " HELD: the coordinator declares expected_effect_pp from the COMP-1 Fold A read (owner decision 139), root "
        "countersigns the exposure rows, mints the admission receipt and re-pins with scripts/flights/repin_cell.py "
        "--set-ready (scripts/flights/comp1dev/comp1dev_flip.sh), which also mints this cell's own first-phase supply "
        "under its own run id (item E16). --allow-output-change must never be passed. Nothing here authorises a "
        "flight, a readiness flip or an admission entry."
    )

    # ---- the arm -------------------------------------------------------------
    arm_pairs = substitutions(TAG, "comp1", smoke=False)
    base = f"configs/baseline/slurp-native-stage3-comp1-{ROSTER_SLUG}-baseline-v1.json"
    derive_baseline(DEV_ARM_BASELINE, base, arm_pairs, composed=True, factors=factors, what_this_is=(
        "Cell COMP-1 on DEV-2000-ADDED: the replication of the first composed Stage-3 arm on the fresh evaluation "
        "roster (owner decisions 138, 152 and 161). " + THE_COMPOSITION))
    written.append(base)
    exp = f"configs/experiment/slurp-native-stage3-comp1-{ROSTER_SLUG}-v1.json"
    derive_experiment(DEV_ARM_EXPERIMENT, exp, arm_pairs, args, purpose=(
        "Cell COMP-1 on DEV-2000-ADDED 1,000 (owner decision 161: AGREE enters COMP-1 pending this DEV "
        "replication; docs/results/2026-09-27-verdict-reclassification.md: this round settles AGREE's "
        "KEEP-PROVISIONAL): does the composition of the agreement term, the centroid boundary key and the citation "
        "contract raise intent-recognition accuracy (primary, owner decision 133) on the evaluation roster, read "
        "at the in-chain A/A null flown beside it, with official pooled SLU-F1 (slurp-slu-official, the DEV "
        "sibling) the non-inferiority guard? " + THE_COMPOSITION + " The declared expected effect is set by the "
        "coordinator from the COMP-1 Fold A read (owner decision 139: no if-then on unread results); until it is "
        "declared the effect-floor gate refuses this cell, which is intended. Development numbers only (owner "
        "decisions 28 and 86); never a test claim."),
        readiness_reason=(
            "Cell COMP-1 DEV-2000-ADDED registered before contact on " + args.date + " from the sealed DEV-2000-ADDED "
            "plan arm fragments by script (decision 58) with COMP-1's three composed factors. Comparator: the sealed "
            "DEV plan arm " + DEV_PLAN_RUN + ", never re-flown, read at the in-chain A/A "
            "SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1 flown in the same campaign chain." + held_tail),
        preparation_requirements=[agreement_requirement, {
            "kind": "preparation", "reason": supply_reason_composed,
            "relpath": f"prepared/SAEA-SLURP-STAGE3-{TAG}-{ROSTER_TAG}-V1/phase-supply-v1.json",
            "sha256": args.arm_supply_sha256}],
        campaign=True,
        algorithm={"id": "sealed-credit-system-policy-v1", "operators_used": ["context_application"], "note": ARM_ALGORITHM_NOTE},
    )
    written.append(exp)

    # ---- the four-row smoke ---------------------------------------------------
    smoke_pairs = substitutions(TAG, "comp1", smoke=True)
    base = f"configs/baseline/slurp-native-stage3-comp1-{ROSTER_SLUG}-smoke-4-baseline-v1.json"
    derive_baseline(DEV_ARM_BASELINE, base, smoke_pairs, composed=True, factors=factors,
                    smoke_fit_cap=len(smoke[0]) * CEILING_PER_ROW * 4, what_this_is=(
                        "Four-row structural form smoke of cell COMP-1 DEV-2000-ADDED: the same three composed actions "
                        "on the first four rows of the unchanged DEV-2000-ADDED roster. " + THE_COMPOSITION))
    written.append(base)
    exp = f"configs/experiment/slurp-native-stage3-comp1-{ROSTER_SLUG}-smoke-4-v1.json"
    derive_experiment(DEV_ARM_EXPERIMENT, exp, smoke_pairs, args, purpose=(
        "Four-row structural form smoke of cell COMP-1 DEV-2000-ADDED: that this roster's agreement table and the "
        "centroid key file load and hash-verify, that the boundary channel still delivers, that the Solver answers "
        "under the cited-answer contract and the unwrapping normaliser delivers the answer's own bytes, that every "
        "request fits and that the episode completes. Scored by no one and read by no one. " + THE_COMPOSITION),
        readiness_reason=(
            "Four-row form smoke of cell COMP-1 DEV-2000-ADDED, registered before contact on " + args.date
            + " from the sealed DEV plan arm fragments by script (decision 58). Structural form proof only: no score, "
            "no read, no claim." + held_tail),
        preparation_requirements=[agreement_requirement, {
            "kind": "preparation", "reason": supply_reason_composed,
            "relpath": f"prepared/SAEA-SLURP-STAGE3-{TAG}-{ROSTER_TAG}-SMOKE-4-V1/phase-supply-v1.json",
            "sha256": args.smoke_supply_sha256}],
        campaign=False,
        algorithm={"id": "sealed-credit-system-policy-v1", "operators_used": ["context_application"], "note": SMOKE_ALGORITHM_NOTE},
        smoke=smoke,
    )
    written.append(exp)

    # ---- the in-chain A/A -------------------------------------------------------
    aa_pairs = substitutions(f"{TAG}-AA", "comp1-aa", smoke=False)
    base = f"configs/baseline/slurp-native-stage3-comp1-aa-{ROSTER_SLUG}-baseline-v1.json"
    derive_baseline(DEV_ARM_BASELINE, base, aa_pairs, composed=False, factors=factors, what_this_is=(
        "The IN-CHAIN A/A REPLICATE and control of cell COMP-1 DEV-2000-ADDED: the sealed DEV-2000-ADDED plan arm's "
        "own bytes -- w_agree 0.0 with no agreement_source, the WRITTEN boundary key, the un-armed citation default "
        "-- carrying the same widened recall (k 60, delivered width 8) as the arm so the two differ in the three "
        "composed factors alone, re-flown in the same campaign chain (measurement instrument rules 3 and 4). Its "
        "own prepared first-phase supply must reproduce the sealed DEV plan preparation's output digest "
        + DEV_PLAN_SUPPLY_OUTPUT_SHA + " exactly."))
    written.append(base)
    exp = f"configs/experiment/slurp-native-stage3-comp1-aa-{ROSTER_SLUG}-v1.json"
    derive_experiment(DEV_ARM_EXPERIMENT, exp, aa_pairs, args, purpose=(
        "The in-chain A/A replicate of cell COMP-1 DEV-2000-ADDED: the locked plan's own form on DEV-2000-ADDED, "
        "unchanged, re-flown in the same campaign chain, to supply the within-chain null the composed delta is read "
        "at. It makes no claim of its own and admits nothing. Development numbers only (owner decisions 28 and 86)."),
        readiness_reason=(
            "The in-chain A/A replicate of cell COMP-1 DEV-2000-ADDED, registered before contact on " + args.date
            + " from the sealed DEV plan arm fragments by script (decision 58): the same baseline bytes at k 60, "
            "w_agree 0.0, the written key, the un-armed citation default, its own run, attempt and fit ids. Its "
            "prepared supply must reproduce the sealed DEV plan output digest " + DEV_PLAN_SUPPLY_OUTPUT_SHA + "."
            + held_tail),
        preparation_requirements=[{
            "kind": "preparation", "reason": supply_reason_aa,
            "relpath": f"prepared/SAEA-SLURP-STAGE3-{TAG}-AA-{ROSTER_TAG}-V1/phase-supply-v1.json",
            "sha256": args.aa_supply_sha256}],
        campaign=True,
        algorithm={"id": "none", "operators_used": [], "note": AA_ALGORITHM_NOTE},
    )
    written.append(exp)

    plan = {
        "cells": [
            {"cell": f"slurp-native-stage3-comp1-aa-{ROSTER_SLUG}-v1", "experiment": f"slurp-native-stage3-comp1-aa-{ROSTER_SLUG}-v1"},
            {"cell": f"slurp-native-stage3-comp1-{ROSTER_SLUG}-v1", "experiment": f"slurp-native-stage3-comp1-{ROSTER_SLUG}-v1"},
        ],
        "schema": "saea-campaign-plan-v1",
    }
    campaign = f"configs/campaign/slurp-native-stage3-comp1-{ROSTER_SLUG}-v1.json"
    wr(campaign, json.dumps(plan, indent=2, sort_keys=True) + "\n")
    written.append(campaign)
    print(json.dumps({"written": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
