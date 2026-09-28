#!/usr/bin/env python3
"""Derive cell W5 -- knowledge-wave item W5, slot-side retrieval (owner decision 170) -- from the
RETAINED AGREE arm fragments (decision 58: script-derived registrations).

THE ONE CHANGE. ONE store is ADDED: ``knowledge_stores.slot-exemplars``, a second speech-keyed
exemplar route delivered to the SOLVER (the node that fills slots), and nothing else moves.
  * store: the ALREADY RELEASED R01-excluded TRAIN exemplar pool
    (``size-pool-annotated-exemplars-minus-r01``, 8,554 utterances, snapshot content ``6eaa03ae...``)
    bound under the new store id by the release ``slot-exemplars-w5-v1`` (the pool's own release
    fields with ``store_id`` renamed; no snapshot copied or rebuilt);
  * route: ``phase_supply.solver`` with the M1 route's own speech query vectors and TRAIN key
    vectors, recall k 300, ranked by ``saea-rank-wcos-prior-agree-v1`` at w_cos 0 / w_prior 0 /
    w_agree 1 over the pinned per-row order ``SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1``, fused by
    ``saea-fuse-associated-values-v1`` (m 300, c 1, top_l 9): nine slot-bearing TRAIN exemplars per
    row, three per intent of the row's retrieval shortlist (the first three entries of the AGREE
    Perception boundary ranking), never one M1 already delivers on that row;
  * bookkeeping: the release and the scope-table receipt appended to
    ``preparation_source_receipts``; the scope table added as a readiness ``preparation``
    requirement beside the AGREE agreement table.
The M1 route (``train-exemplars``), the intent-boundary channel and its agreement term, the
slot-contract cards and their candidate supply, the roster, geometry, session, program and its
11-contact ceiling, every template, the deliver normaliser and the scorers are the AGREE arm's,
byte for byte.

TWO CELLS: the arm on TRAIN Fold A 1,080 and its four-row form smoke. The in-chain A/A is NOT
derived here: the knowledge wave shares ONE A/A, ``SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1``.

Both cells drop ``prepared_phase_supply`` so the flip mints each cell's OWN first-phase supply
(item E16). The added store serves the Solver only, never the first phase, so the minted
Perception supply must reproduce the AGREE arm's output digest -- the flip's byte-identity check.

This script writes CONFIG ONLY. It performs no contact, writes no ledger row, mints no receipt and
flips nothing.

    python scripts/flights/w5/derive_slurp_w5_cells.py --date 2026-09-27
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

AGREE_ARM_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
AGREE_SMOKE_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1.json"
AGREE_ARM_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json"
AGREE_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-smoke-4-v1.json"
AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
SHARED_AA_RUN = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
AGREEMENT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"

NEW_STORE_ID = "slot-exemplars"
SCOPE_ID = "SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1"
SCOPE = {"relpath": f"prepared/{SCOPE_ID}/agreement.jsonl",
         "sha256": "f12540f19730d713594c4f63ce7b68c66ef508b8bb2dbb897ae9541087aceb96"}
SCOPE_RECEIPT = {"relpath": f"prepared/{SCOPE_ID}/receipt.json", "root": "data",
                 "sha256": "40cfd8bbfa5aa2c49e9670a2d7849b76c132fe8a657784ee13f8e3b255ba0f6c"}
RELEASE = {"relpath": "knowledge/slurp/saea-kb-distmodel-v1/slot-exemplars-w5-v1/release.json",
           "sha256": "83f175704a09e1721e4d61666979925133a25ea80fc4918fc68a56e527a122a3"}
SNAPSHOT = {"relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json",
            "sha256": "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63"}
RECALL_K, TOP_L = 300, 9
EMBEDDED_SIGNAL = (
    "derived: a strictly decreasing per-row ORDER over this store's recalled facets, pre-computed "
    "model-free by scripts/build_slurp_slot_exemplar_scope_w5.py: the nearest slot-bearing exemplars "
    "(by the row's own sealed speech vector) of each of the first three intents of the row's AGREE "
    "intent-boundary ranking (written-key cosine + 1.0 x the pinned self-excluded exemplar-intent vote), "
    "round-robin, never an utterance the row's M1 exemplar route already delivers, then the nearest other "
    "slot-bearing exemplars as fill; shares (L - j) / sum. Speech-keyed and gold-free: no label, "
    "transcript, flight output or future turn of the evaluated row enters it. The reserved agreement "
    "dimension is reused as the ranker's one pre-computed per-row signal slot."
)
NEW_RECEIPTS = [dict(RELEASE, root="data"), dict(SCOPE_RECEIPT)]

ONE_CHANGE = (
    "ONE change against the retained AGREE arm: ONE store is ADDED, knowledge_stores.slot-exemplars -- a "
    "second speech-keyed TRAIN exemplar route delivered to the Solver (the node that fills slots). It binds "
    "the already released R01-excluded TRAIN exemplar pool (size-pool-annotated-exemplars-minus-r01, 8,554 "
    "utterances, snapshot content " + SNAPSHOT["sha256"] + ") under the release slot-exemplars-w5-v1 (sha256 "
    + RELEASE["sha256"] + "), and serves phase_supply.solver with the M1 route's own speech query vectors and "
    "TRAIN key vectors: recall k " + str(RECALL_K) + ", ranked by saea-rank-wcos-prior-agree-v1 at w_cos 0 / w_prior "
    "0 / w_agree 1 over the pinned per-row order " + SCOPE_ID + " (sha256 " + SCOPE["sha256"] + "), fused by "
    "saea-fuse-associated-values-v1 (m " + str(RECALL_K) + ", c 1, top_l " + str(TOP_L) + "): nine slot-bearing TRAIN "
    "exemplars per row, three per intent of the row's retrieval shortlist (the first three entries of the AGREE "
    "Perception boundary ranking, speech plus the pinned exemplar vote), nearest first by the row's own speech, "
    "never an utterance the M1 route already delivers on that row, filled by the nearest other slot-bearing "
    "exemplars where a shortlist intent has fewer than three inside the recall. Built model-free by "
    "scripts/build_slurp_slot_exemplar_scope_w5.py (no Fold A gold, no flight output). The release and the "
    "scope receipt are appended to preparation_source_receipts. Nothing else moves: the M1 route "
    "(train-exemplars), the intent-boundary channel and its agreement term (w_agree 1.0, k 60, fuse 8-1-8), the "
    "slot-contract cards and their candidate supply, roster, geometry, session, program and its 11-contact "
    "ceiling, every template, the deliver normaliser and the scorers are the AGREE arm's, byte for byte."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a one-store knowledge "
    "retrieval change -- a second speech-keyed exemplar route, scoped by the row's retrieval shortlist and "
    "ordered by a model-free pre-computed table -- with no rollout, no per-sample scoring, no credit "
    "assignment, no update operator and no evolving store."
)


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


def substitutions(*, smoke: bool) -> list[tuple[str, str]]:
    if smoke:
        return [
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-FIT-V1", "SAEA-SLURP-STAGE3-W5-FOLD-A-SMOKE-4-FIT-V1"),
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-W5-FOLD-A-SMOKE-4-V1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-generation-v1", "attempt-slurp-native-stage3-w5-fold-a-smoke-4-generation-v1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-fit-v1", "attempt-slurp-native-stage3-w5-fold-a-smoke-4-fit-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1", "slurp-native-stage3-w5-fold-a-smoke-4-baseline-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", "slurp-native-stage3-w5-fold-a-smoke-4-v1"),
            ("saea-slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", "saea-slurp-native-stage3-w5-fold-a-smoke-4-v1"),
        ]
    return [
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1", "SAEA-SLURP-STAGE3-W5-FOLD-A-FIT-V1"),
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "SAEA-SLURP-STAGE3-W5-FOLD-A-V1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", "attempt-slurp-native-stage3-w5-fold-a-generation-v1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-fit-v1", "attempt-slurp-native-stage3-w5-fold-a-fit-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-baseline-v1", "slurp-native-stage3-w5-fold-a-baseline-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-v1", "slurp-native-stage3-w5-fold-a-v1"),
        ("saea-slurp-native-stage3-agree-w1-fold-a-v1", "saea-slurp-native-stage3-w5-fold-a-v1"),
    ]


def substitute(text: str, pairs) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def new_store(m1_solver: dict) -> dict:
    spec = {
        "agreement_source": {"embedded_signal": EMBEDDED_SIGNAL, "kind": "sealed-agreement",
                             "relpath": SCOPE["relpath"], "sha256": SCOPE["sha256"],
                             "tool_contact_ledger_row": SCOPE_ID},
        "dimensions": list(m1_solver["dimensions"]), "expose_facets": False,
        "facet_source": copy.deepcopy(m1_solver["facet_source"]),
        "fuse_coverage": {"c": 1, "m": RECALL_K, "top_l": TOP_L},
        "fuse_policy": "saea-fuse-associated-values-v1", "k": RECALL_K, "provider": "kb-facet-v1",
        "query_source": copy.deepcopy(m1_solver["query_source"]),
        "rank_policy": "saea-rank-wcos-prior-agree-v1",
        "rank_weights": {"w_agree": 1.0, "w_cos": 0.0, "w_prior": 0.0}, "tau": 0.0,
    }
    return {"phase_supply": {"solver": spec}, "release": dict(RELEASE), "snapshot": dict(SNAPSHOT),
            "store_role": "train-exemplars"}


def derive_baseline(parent: str, out: str, pairs, *, what_this_is: str) -> None:
    raw = rd(parent)
    parent_doc = json.loads(raw)
    document = json.loads(substitute(raw, pairs))
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own
    stores = document["knowledge_stores"]
    if NEW_STORE_ID in stores:
        raise SystemExit("the AGREE parent already declares a slot-exemplars store; refusing")
    if set(stores) != {"intent-boundaries", "slot-contracts", "train-exemplars"}:
        raise SystemExit(f"unexpected AGREE stores {sorted(stores)}; refusing")
    stores[NEW_STORE_ID] = new_store(stores["train-exemplars"]["phase_supply"]["solver"])  # THE ONE CHANGE
    receipts = list(document["preparation_source_receipts"])
    if any(r["relpath"] in {x["relpath"] for x in NEW_RECEIPTS} for r in receipts):
        raise SystemExit("the parent already carries a W5 receipt")
    document["preparation_source_receipts"] = receipts + [dict(r) for r in NEW_RECEIPTS]
    document["what_this_is"] = what_this_is
    for key in parent_doc:
        if key in ("preparation_source_receipts", "prepared_phase_supply", "what_this_is", "native_contact_fit"):
            continue
        if key == "knowledge_stores":
            for store_id, store in parent_doc[key].items():
                if json.dumps(store, sort_keys=True) != json.dumps(document[key][store_id], sort_keys=True):
                    raise SystemExit(f"store {store_id!r} moved beyond the one added store")
            continue
        if json.dumps(parent_doc[key], sort_keys=True) != json.dumps(document[key], sort_keys=True):
            raise SystemExit(f"baseline key {key!r} moved beyond the one added store")
    wr(out, dump_like(raw, document))


def derive_experiment(parent: str, out: str, pairs, args, *, purpose: str, readiness_reason: str,
                      campaign: bool, failure_policy: str | None = None) -> None:
    raw = rd(parent)
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    if failure_policy is not None:
        document["failure_policy"] = failure_policy
    else:
        document["failure_policy"] = document["failure_policy"].replace(
            "closes cell PLAN", "closes this cell").replace("stops cell PLAN", "stops this cell")
    cell = document["cells"][0]
    agreement = [r for r in cell["readiness"]["requirements"]
                 if r.get("kind") == "preparation" and r.get("relpath") == AGREEMENT_RELPATH]
    if len(agreement) != 1:
        raise SystemExit("the AGREE parent does not carry exactly one agreement-table requirement")
    scope = {
        "kind": "preparation", "relpath": SCOPE["relpath"], "sha256": SCOPE["sha256"],
        "reason": (
            "The pre-computed per-row ORDER the added slot-exemplars route ranks with, built model-free by "
            "scripts/build_slurp_slot_exemplar_scope_w5.py from the AGREE arm's own composed config (roster, "
            "packets, the flown boundary and M1 channel specs), the pinned speech query vectors, the pinned TRAIN "
            "key vectors, the pinned agreement table and the released R01-excluded pool snapshot, through the "
            "flight's own build_supply_for_phase / KbFacetProvider recall, ranker and fuser -- zero model, server, "
            "tokenizer, encoder, embedder, scorer, network and GPU contacts. Measured: 1,080 rows, nine listed "
            "exemplars delivered per row (85.94 % from the shortlist tier), the replayed boundary order reproduces "
            "the delivered eight on 1,080 of 1,080 rows, and the route as it will fly reproduces the intended "
            "selection on 1,080 of 1,080 rows; no Fold A utterance is in the pool (roster exclusion proof in the "
            "receipt " + SCOPE_RECEIPT["relpath"] + ")."),
    }
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": agreement + [scope], "state": "held"}
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    wr(out, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR"))
    args = parser.parse_args(argv)
    if args.data_root:
        for pin in (RELEASE, SCOPE, SCOPE_RECEIPT):
            path = os.path.join(args.data_root, pin["relpath"])
            if hashlib.sha256(io.open(path, "rb").read()).hexdigest() != pin["sha256"]:
                raise SystemExit(f"{pin['relpath']} does not hash to its pin")

    held = (
        " HELD: root mints the admission receipt and re-pins with scripts/flights/repin_cell.py --set-ready "
        "(through scripts/flights/w5/w5_flip.sh), which also mints this cell's own first-phase supply under its "
        "own run id (item E16); --allow-output-change must never be passed, and the minted supply must reproduce "
        "the AGREE arm's own first-phase output digest (the added store serves the Solver only). Nothing here "
        "authorises a flight, a readiness flip or an admission entry."
    )
    written = []
    arm_pairs = substitutions(smoke=False)
    derive_baseline(AGREE_ARM_BASELINE, "configs/baseline/slurp-native-stage3-w5-fold-a-baseline-v1.json", arm_pairs,
                    what_this_is="Cell W5 (knowledge wave, owner decision 170): the retained AGREE arm with a slot-side "
                                 "retrieval route added for the Solver. " + ONE_CHANGE)
    written.append("configs/baseline/slurp-native-stage3-w5-fold-a-baseline-v1.json")
    derive_experiment(
        AGREE_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-w5-fold-a-v1.json", arm_pairs, args,
        purpose=(
            "Cell W5 on TRAIN Fold A 1,080 (knowledge wave, owner decision 170): with a second speech-keyed TRAIN "
            "exemplar route delivered to the Solver -- nine slot-bearing exemplars per row, three per intent of the "
            "row's retrieval shortlist, never one the M1 route already delivers -- does the official pooled SLU-F1 "
            "(primary: the mechanism acts on slots; W5 is the one wave cell with SLU primary) stay within -- or rise "
            "above -- the retained AGREE form, read at the knowledge wave's shared in-chain A/A " + SHARED_AA_RUN
            + ", with intent accuracy the non-inferiority guard? " + ONE_CHANGE + " Development numbers only (owner "
            "decisions 28 and 86); never a test claim. Nothing here authorises a flight, a readiness flip or an "
            "admission entry."
        ),
        readiness_reason=(
            "Cell W5 registered before contact on " + args.date + " from the retained AGREE arm fragments by script "
            "(decision 58) with one store added (owner decision 170). Comparator: the sealed AGREE arm " + AGREE_RUN
            + ", never re-flown, read at the knowledge wave's shared in-chain A/A replicate " + SHARED_AA_RUN
            + " (registered by the coordinator) flown in the same campaign chain." + held
        ),
        campaign=True,
    )
    written.append("configs/experiment/slurp-native-stage3-w5-fold-a-v1.json")

    smoke_pairs = substitutions(smoke=True)
    derive_baseline(AGREE_SMOKE_BASELINE, "configs/baseline/slurp-native-stage3-w5-fold-a-smoke-4-baseline-v1.json",
                    smoke_pairs,
                    what_this_is="Four-row structural form smoke of cell W5: the same added store on the first four rows "
                                 "of the unchanged TRAIN Fold A roster. " + ONE_CHANGE)
    written.append("configs/baseline/slurp-native-stage3-w5-fold-a-smoke-4-baseline-v1.json")
    derive_experiment(
        AGREE_SMOKE_EXPERIMENT, "configs/experiment/slurp-native-stage3-w5-fold-a-smoke-4-v1.json", smoke_pairs, args,
        purpose=(
            "Four-row structural form smoke of cell W5: that the slot-exemplars store loads by its pins, that the "
            "scope table loads and the Solver receives nine W5 exemplars beside the M1 twenty, that every request "
            "fits and that the episode completes. It is scored by no one and read by no one: four rows can never be "
            "evidence of benefit or of harm. " + ONE_CHANGE
        ),
        readiness_reason=(
            "Four-row form smoke of cell W5, registered before contact on " + args.date + " from the AGREE smoke "
            "fragments by script (decision 58). Structural form proof only: no score, no read, no claim." + held
        ),
        campaign=False,
        failure_policy=(
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. "
            "A failed smoke stops cell W5 and the arm does not open. The resume-recovery clause of owner decision 22 "
            "applies to the arm, not to a four-row form smoke, which is re-flown whole if it is re-flown at all."
        ),
    )
    written.append("configs/experiment/slurp-native-stage3-w5-fold-a-smoke-4-v1.json")
    campaign = {"cells": [{"cell": "slurp-native-stage3-w5-fold-a-v1", "experiment": "slurp-native-stage3-w5-fold-a-v1"}],
                "schema": "saea-campaign-plan-v1"}
    wr("configs/campaign/slurp-native-stage3-w5-fold-a-v1.json", json.dumps(campaign, indent=2, sort_keys=True) + "\n")
    written.append("configs/campaign/slurp-native-stage3-w5-fold-a-v1.json")
    print(json.dumps({"written": written, "store": NEW_STORE_ID, "release": RELEASE, "scope": SCOPE}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
