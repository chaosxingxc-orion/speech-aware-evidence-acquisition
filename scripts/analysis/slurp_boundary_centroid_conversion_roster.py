#!/usr/bin/env python3
"""Derive the centroid-key CONVERSION PROBE's roster -- the TRAIN Fold A rows
whose gold intent's boundary entry the centroid key NEWLY delivers -- and prove,
before a single id is taken, that (1) the arithmetic reproduces the committed
diagnostic's own delivery numbers, (2) the pinned key FILE reproduces them
through the production recall, and (3) the production constructor's fused
selection agrees with both.

WHY THIS EXISTS. ``docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md``
measured DELIVERY, never correctness: a centroid boundary key puts the gold
intent inside the delivered eight on 71.2 / 64.7 / 66.8 % of the intent-wrong
rows (Fold A / ROLL-1 / DEV-2000, held-out pools) against 45.0 / 44.6 / 35.8 %
for the written key. Whether the Solver then answers correctly with the entry
present is the missing quantity -- the conversion from delivery to correctness
-- and owner decision 145 registers a CONV-style probe to measure it on exactly
the rows the delivery gain lands on. Those rows are derived here.

THREE PROOFS, IN ORDER.

  A. The diagnostic's arithmetic, reproduced. The committed diagnostic module
     ``scripts/analysis/slurp_boundary_key_construction_diagnostic.py`` is
     imported BYTE-UNCHANGED and its own functions are called with its own
     parameters on all three rosters; the written-key recall is validated
     against every sealed delivered set (100 % on every row, as the diagnostic
     reports) and the ``written`` / ``centroid`` delivery cells are compared,
     to the precision the committed note prints, against the numbers that
     note committed (its sha256 is recorded).

  B. The pinned FILE, through the production recall. The treatment file
     ``prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl`` is
     read through ``rails.phase_supply.load_sealed_vectors`` (the flight's own
     loader, sha256-verified), its 60 vectors are compared to the diagnostic's
     own R01-excluded ``centroid`` construction (the pool this file is built
     from) and to the written key on the fallback intent, and the roster's
     speech vectors are run against it through
     ``rails.kb_policy.multidim_segment_recall`` at the flown width. On ROLL-1
     -- the roster the diagnostic read under this same pool -- the delivery
     cells must equal the note's exactly; on Fold A and DEV-2000 the note
     reports the full-pool construction, so the treatment file's numbers are
     reported beside them (Fold A's is what the flight will deliver).

  C. The population, through the production constructor. The sealed PLAN
     arm's own channels are built the way a flight builds them (the agreement
     replication recipe's ``arm_channels``, imported byte-unchanged), the
     boundary decision is taken through ``provider.candidates`` + ``provider.fuse``
     at the flown ``k`` 8 / ``fuse_coverage`` 8-1-8 twice -- once with the
     flown written key (its fused set must equal the sealed delivered set on
     every row) and once with the spec's ``facet_source`` replaced by the
     treatment pin -- and the roster is exactly the bad-case-bank
     intent-wrong rows (bank classes ``INTENT-UNCOVERED`` and ``INTENT-COVERED``,
     both intent-wrong in the sealed comparator) whose gold intent's boundary
     value id is in the treatment fusion and not in the written fusion. That id set must equal
     the set proof B derives through the recall, or the derivation refuses.

THE ROSTER IS SELECTED USING GOLD, OFFLINE. The bad-case bank's ``plan_class``
and each row's gold intent are read on the scoring side only, here, before any
flight exists. That is legitimate for a CONDITIONAL estimate on a TRAIN roster
and for nothing else: NO POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE FROM THE
CELL THIS ROSTER DEFINES, because its population was chosen by the mechanism's
own effect. Gold reaches no query, no key, no weight, no selector and no runtime.
The key itself is built from a store property (each pool value's frozen
build-time ``task_target``); proof A's centroid used the diagnostic's TRAIN-split
labelling, and the two are shown to yield the same vectors.

TEXT DISCIPLINE. Sample ids, facet ids, counts, rates and hashes only. No
utterance text, transcript, gold label string, knowledge body, key description
or model output is printed or persisted.

ZERO model, server, encoder, embedder, scorer, tokenizer, network, GPU and
paid-API contacts: arithmetic over receipt-pinned vector files and frozen
snapshots, each verified against its configured sha256 by this repository's own
loaders.

    PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python \\
        scripts/analysis/slurp_boundary_centroid_conversion_roster.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" \\
        --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \\
        --output docs/readiness/<package>/roster-derivation-v1.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)
from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: E402
    multidim_segment_recall,
)
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_vectors,
)

DERIVATION_ID = "SAEA-SLURP-STAGE3-KPROBE-FOLD-A-ROSTER-V1"
SCHEMA = "saea-centroid-key-conversion-roster-v1"

DIAGNOSTIC_RECIPE = Path("scripts/analysis/slurp_boundary_key_construction_diagnostic.py")
DIAGNOSTIC_NOTE = Path("docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md")
REPLICATION_RECIPE = Path("scripts/analysis/slurp_intent_agreement_production_replication.py")

ARTIFACT_ID = "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1"
TREATMENT_RELPATH = f"prepared/{ARTIFACT_ID}/facets.jsonl"
TREATMENT_RECEIPT_RELPATH = f"prepared/{ARTIFACT_ID}/receipt.json"
TREATMENT_LEDGER_ROW = ARTIFACT_ID
TREATMENT_SIGNAL = (
    "text: the intent's unit-normalised MEAN construction-TRAIN utterance vector (R01-excluded "
    "pool, one centroid per released intent-boundary facet; the one intent with no pool member "
    "keeps the flown written key), arithmetic over the pinned pool key vectors at zero encoder "
    "contacts; the key side is knowledge, the delivered body is unchanged."
)

FLOWN_K = 8
RECALL_WIDTH = 60
WRONG_CLASS = "INTENT-WRONG"
#: The bank's two intent-error classes, both intent-WRONG in the sealed comparator.
PLAN_CLASSES = ("INTENT-UNCOVERED", "INTENT-COVERED")
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-a-1080"
CARRIER_LOCK_KEY = "slurp"
WORKERS = 4

#: The committed note's own cells, as it prints them (one decimal), for the
#: two constructions this derivation depends on. Section 2 of the note.
NOTE_CELLS = {
    "train-fold-a-plan": {
        "rows": 1080, "wrong": 191, "correct": 480,
        "written": {"rank1_all": 65.6, "rank1_wrong": 4.7, "deliv_all": 87.7,
                    "deliv_wrong": 45.0, "deliv_correct": 97.3},
        "centroid": {"rank1_all": 65.7, "rank1_wrong": 23.0, "deliv_all": 94.0,
                     "deliv_wrong": 71.2, "deliv_correct": 99.0},
    },
    "roll1": {
        "rows": 625, "wrong": 184, "correct": 163,
        "written": {"rank1_all": 47.0, "rank1_wrong": 3.3, "deliv_all": 79.2,
                    "deliv_wrong": 44.6, "deliv_correct": 95.1},
        "centroid": {"rank1_all": 54.1, "rank1_wrong": 14.7, "deliv_all": 87.8,
                     "deliv_wrong": 64.7, "deliv_correct": 95.7},
    },
    "dev2000-added-plan": {
        "rows": 1000, "wrong": 232, "correct": 398,
        "written": {"rank1_all": 56.4, "rank1_wrong": 3.9, "deliv_all": 81.5,
                    "deliv_wrong": 35.8, "deliv_correct": 94.5},
        "centroid": {"rank1_all": 62.5, "rank1_wrong": 17.2, "deliv_all": 90.6,
                     "deliv_wrong": 66.8, "deliv_correct": 98.2},
    },
}
#: The note's R01-excluded centroid geometry (section 3).
NOTE_R01_EXCLUDED_CENTROID_GEOMETRY = {"cos_mean": 0.9326, "cos_max": 0.993}

#: The registered per-row headroom of the class the gain lands on, from the
#: agreement package's own expected_effect_derivation (INTENT-UNCOVERED:
#: 5.41 pp SLU-F1 and 12.04 pp intent accuracy over 130 rows), reported so the
#: re-declaration rule is arithmetic on this receipt and not a second source.
HEADROOM_SLU_PP_PER_ROW = 5.41 / 130.0
HEADROOM_INTENT_PP_PER_ROW = 12.04 / 130.0
ARM_ROWS = 1080
ARM_ADMISSION_BAR_PP = 2.5


class DeriveError(RuntimeError):
    """Refuse a derivation that cannot be proven against committed bytes."""


def digest_file(path: Path) -> str:
    measured = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            measured.update(chunk)
    return measured.hexdigest()


def import_module(repo: Path, relpath: Path, name: str):
    path = repo / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DeriveError(f"cannot import {relpath}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, digest_file(path)


def pct(num: float, den: float) -> float:
    return 100.0 * num / den if den else 0.0


def cells_of(summary: dict) -> dict:
    return {
        "rank1_all": round(pct(summary["all"]["rank1"], summary["all"]["rows"]), 1),
        "rank1_wrong": round(pct(summary["wrong"]["rank1"], summary["wrong"]["rows"]), 1),
        "deliv_all": round(pct(summary["all"]["delivered"], summary["all"]["rows"]), 1),
        "deliv_wrong": round(pct(summary["wrong"]["delivered"], summary["wrong"]["rows"]), 1),
        "deliv_correct": round(pct(summary["correct"]["delivered"], summary["correct"]["rows"]), 1),
    }


def counts_of(summary: dict) -> dict:
    return {
        "rows": summary["all"]["rows"],
        "wrong_rows": summary["wrong"]["rows"],
        "correct_rows": summary["correct"]["rows"],
        "rank1_all": summary["all"]["rank1"],
        "rank1_wrong": summary["wrong"]["rank1"],
        "delivered_all": summary["all"]["delivered"],
        "delivered_wrong": summary["wrong"]["delivered"],
        "delivered_correct": summary["correct"]["delivered"],
        "unrankable_all": summary["all"]["unrankable"],
    }


def compare(label: str, expected: object, observed: object, diffs: list[str]) -> None:
    if expected != observed:
        diffs.append(f"{label}: expected {expected!r}, observed {observed!r}")


# ---------------------------------------------------------------------------
# proof A: the diagnostic's own arithmetic, on all three rosters


def proof_a(diag, root: Path, lock: dict) -> dict:
    train = diag.load_train(lock, root)
    bank, store = diag.load_bank(root), diag.load_boundary(root)
    pools = {relpath: diag.load_pool(root, relpath, sha)
             for relpath, sha in ((diag.POOL, diag.POOL_SHA), (diag.POOL_M, diag.POOL_M_SHA))}
    if not set(pools[diag.POOL_M]["facets"]) < set(pools[diag.POOL]["facets"]):
        raise DeriveError("the minus-R01 pool is not a strict subset of the full pool")
    vectors = diag.load_pool_vectors(root, set(pools[diag.POOL]["facets"]))
    keysets = {relpath: diag.build_keysets(store, pool, vectors, train)
               for relpath, pool in pools.items()}
    diffs: list[str] = []
    arms: dict[str, dict] = {}
    for arm in diag.ARMS:
        label = arm["label"]
        rows, sealed = diag.load_rows(root, arm, bank, train), diag.load_sealed(root, arm)
        ids = sorted(s for s, r in rows["rows"].items() if r.get("gold_intent"))
        queries = diag.load_queries(root, arm, ids)
        repo_order = diag.repo_orders(store, queries)
        triples = [(s, rows["rows"][s]["gold_intent"], rows["rows"][s]["class"])
                   for s in queries["ids"]]
        own = {diag.own_key(s) for s in queries["ids"]} - {None}
        membership = {relpath: len(own & set(pool["keyed"].values()))
                      for relpath, pool in pools.items()}
        if membership[arm["pool"]]:
            raise DeriveError(f"{label}: an evaluated row is in its own construction pool")
        validation = diag.validate(queries, keysets[arm["pool"]]["written"], sealed["rows"], repo_order)
        for key in ("repo_top_matches_sealed", "numpy_top_matches_sealed", "numpy_order_equals_repo"):
            compare(f"{label}.validation.{key}", validation["rows"], validation[key], diffs)
        reads = {}
        for name in ("written", "centroid"):
            summary = diag.summarise(diag.evaluate(queries["matrix"], keysets[arm["pool"]][name], triples))
            reads[name] = {"cells": cells_of(summary), "counts": counts_of(summary)}
            compare(f"{label}.{name}.cells", NOTE_CELLS[label][name], reads[name]["cells"], diffs)
        compare(f"{label}.rows", NOTE_CELLS[label]["rows"], len(triples), diffs)
        compare(f"{label}.wrong", NOTE_CELLS[label]["wrong"], reads["written"]["counts"]["wrong_rows"], diffs)
        compare(f"{label}.correct", NOTE_CELLS[label]["correct"], reads["written"]["counts"]["correct_rows"], diffs)
        arms[label] = {
            "rows": len(triples), "pool": arm["pool"], "own_rows_in_pool": membership,
            "query_relpath": arm["query"], "query_sha256": arm["query_sha"],
            "phases_relpath": sealed["relpath"], "phases_sha256": sealed["sha256"],
            "population_source": rows["source"], "population_source_sha256": rows["source_sha256"],
            "validation": validation, "reads": reads,
            # kept for proofs B and C; dropped before the receipt is written
            "_queries": queries, "_triples": triples, "_repo_order": repo_order,
            "_sealed": sealed["rows"],
        }
    geometry = diag.key_geometry(keysets[diag.POOL_M]["centroid"])
    compare("r01_excluded_centroid.cos_mean", NOTE_R01_EXCLUDED_CENTROID_GEOMETRY["cos_mean"], geometry["cos_mean"], diffs)
    compare("r01_excluded_centroid.cos_max", NOTE_R01_EXCLUDED_CENTROID_GEOMETRY["cos_max"], geometry["cos_max"], diffs)
    return {
        "store": store, "pools": pools, "keysets": keysets, "bank": bank, "train": train,
        "arms": arms, "differences": diffs,
        "r01_excluded_centroid_geometry": {k: geometry[k] for k in ("cos_mean", "cos_max", "keys", "fallback")},
    }


# ---------------------------------------------------------------------------
# proof B: the pinned file, through the production recall


def proof_b(diag, root: Path, a: dict, treatment_sha: str) -> dict:
    store = a["store"]
    path = root / TREATMENT_RELPATH
    facets = load_sealed_vectors(path, expected_sha256=treatment_sha, dimensions=(diag.IB_DIM,))
    if set(facets) != set(store["facet_vectors"]):
        raise DeriveError("the treatment file does not cover the released store's facet ids exactly")
    intents = store["intents"]
    by_intent = {store["to_intent"][fid]: fid for fid in store["facet_vectors"]}
    expected = a["keysets"][diag.POOL_M]["centroid"]
    fallback = set(expected["fallback"])
    matrix = np.asarray([facets[by_intent[i]][diag.IB_DIM] for i in intents], dtype=np.float64)
    per_row = np.abs(matrix - expected["matrix"]).max(axis=1)
    is_fallback = np.asarray([i in fallback for i in intents])
    # A centroid row must be the diagnostic's bitwise (float64 noise only). The
    # fallback row is the FLOWN written key byte for byte, which the diagnostic's
    # keyset carries re-normalised through unit_rows (the encoder's float32 unit
    # vectors are not exactly unit in float64), so it is compared to the flown
    # bytes exactly and its distance to the re-normalised copy is reported.
    diff = per_row[~is_fallback]
    fallback_exact = all(
        tuple(facets[by_intent[i]][diag.IB_DIM]) == tuple(store["facet_vectors"][by_intent[i]][diag.IB_DIM])
        for i in fallback
    )
    norms = np.linalg.norm(matrix, axis=1)
    if float(diff.max()) > 1e-12:
        raise DeriveError(f"the treatment file's centroid rows differ from the diagnostic's R01-excluded centroid by up to {float(diff.max())}")
    if not fallback_exact:
        raise DeriveError("the fallback intent's key is not the flown written key byte for byte")
    keyset = {**expected, "matrix": matrix}
    treated_store = dict(store, facet_vectors=facets)
    diffs: list[str] = []
    arms = {}
    for label, arm in a["arms"].items():
        queries, triples = arm["_queries"], arm["_triples"]
        order = diag.repo_orders(treated_store, queries)
        vectorised = diag.intent_orders(queries["matrix"], keyset)
        same_order = sum(int(mine == order[s]) for mine, s in zip(vectorised, queries["ids"]))
        # the flown width, through the same recall, must be the 60-way order's head
        width8_agree = 0
        for sample_id in queries["ids"]:
            recalled = multidim_segment_recall(
                store["snapshot"], queries["segments"][sample_id].segments,
                lambda f: facets.get(f, {}), FLOWN_K,
            )
            top = sorted((store["to_intent"][f] for f in recalled), key=lambda i: i)
            width8_agree += int(top == sorted(order[sample_id][:FLOWN_K]))
        summary = diag.summarise(diag.evaluate(queries["matrix"], keyset, triples))
        cells, counts = cells_of(summary), counts_of(summary)
        delivered_by_class = Counter()
        newly = {"delivered": [], "lost": []}
        written_order = arm["_repo_order"]
        for sample_id, gold, klass in triples:
            before = gold in written_order[sample_id][:FLOWN_K]
            after = gold in order[sample_id][:FLOWN_K]
            delivered_by_class[(klass, "before")] += int(before)
            delivered_by_class[(klass, "after")] += int(after)
            delivered_by_class[(klass, "rows")] += 1
            if after and not before:
                newly["delivered"].append((sample_id, klass))
            if before and not after:
                newly["lost"].append((sample_id, klass))
        per_class = {}
        for klass in sorted({k for k, _ in delivered_by_class}):
            per_class[klass] = {
                "rows": delivered_by_class[(klass, "rows")],
                "delivered_written": delivered_by_class[(klass, "before")],
                "delivered_centroid": delivered_by_class[(klass, "after")],
                "newly_delivered": sum(1 for _, k in newly["delivered"] if k == klass),
                "newly_lost": sum(1 for _, k in newly["lost"] if k == klass),
            }
        block = {
            "rows": len(triples),
            "production_recall_order_equals_vectorised_order": same_order,
            "production_recall_width8_equals_order_head": width8_agree,
            "cells": cells, "counts": counts, "per_class": per_class,
            "_newly_delivered": newly["delivered"], "_newly_lost": newly["lost"],
        }
        compare(f"{label}.width8", len(triples), width8_agree, diffs)
        compare(f"{label}.same_order", len(triples), same_order, diffs)
        if label == "roll1":
            compare("roll1.treatment_file.cells", NOTE_CELLS["roll1"]["centroid"], cells, diffs)
            block["note_comparison"] = "the note read ROLL-1 under this same R01-excluded pool; the treatment file must reproduce its centroid cells exactly"
        else:
            block["note_comparison"] = (
                "the note read this roster under the FULL pool (reproduced in proof A); the treatment "
                "file is the R01-excluded construction, so its cells are reported beside the note's, not equated"
            )
            block["note_full_pool_cells"] = NOTE_CELLS[label]["centroid"]
        arms[label] = block
    return {
        "relpath": TREATMENT_RELPATH, "sha256": treatment_sha,
        "max_abs_diff_to_diagnostic_r01_excluded_centroid": float(diff.max()),
        "fallback_facet_ids": sorted(by_intent[i] for i in fallback),
        "fallback_equals_written_key_exactly": fallback_exact,
        "fallback_max_abs_diff_to_the_renormalised_written_key": float(per_row[is_fallback].max()) if is_fallback.any() else 0.0,
        "fallback_note": (
            "the diagnostic's keyset carries the written key re-normalised in float64; the file carries "
            "the FLOWN bytes. Cosine ranking is scale-invariant, so the two order identically (proven "
            "per row below); the distance is the encoder's float32 unit-norm residue"
        ),
        "l2_norm_min": float(norms.min()), "l2_norm_max": float(norms.max()),
        "arms": arms, "differences": diffs,
    }


# ---------------------------------------------------------------------------
# proof C: the population, through the production constructor


def treatment_pin(sha256: str) -> dict:
    return {
        "kind": "sealed-vectors",
        "relpath": TREATMENT_RELPATH,
        "sha256": sha256,
        "tool_contact_ledger_row": TREATMENT_LEDGER_ROW,
        "embedded_signal": TREATMENT_SIGNAL,
    }


def proof_c(recipe, repo: Path, root: Path, lock_path: Path, lock: dict, treatment_sha: str, b: dict) -> dict:
    arm = next(a for a in recipe.ARMS if a["label"] == "train-fold-a-plan")
    bank = recipe.load_bank(root)
    train_gold = recipe.load_train_gold(lock, root)
    channels = recipe.arm_channels(repo, root, lock_path, arm)
    population = recipe.load_population(root, arm, bank, train_gold)
    sealed = recipe.load_sealed(root, arm["run_id"], channels["attempt_id"])
    spec = channels["specs"][recipe.BOUNDARY_STORE]
    if spec.k != FLOWN_K or dict(spec.fuse_coverage or {}) != {"m": 8, "c": 1, "top_l": 8}:
        raise DeriveError("the sealed PLAN arm's boundary channel is not the flown k 8 / 8-1-8")
    if dict(spec.rank_weights or {}).get("w_agree", 0.0) != 0.0:
        raise DeriveError("the sealed PLAN arm's boundary channel is not at w_agree 0.0")
    base = recipe.boundary_decisions(root, arm, channels, None, 0.0, FLOWN_K)
    treated = dict(channels)
    treated["specs"] = dict(channels["specs"])
    treated["specs"][recipe.BOUNDARY_STORE] = replace(spec, facet_source=treatment_pin(treatment_sha))
    treat = recipe.boundary_decisions(root, arm, treated, None, 0.0, FLOWN_K)
    delivery = recipe.tally(population, sealed, base, treat)
    agree = delivery["sealed_boundary_agreement"]
    if agree.get("baseline_fusion_equals_sealed") != agree.get("rows"):
        raise DeriveError("the written-key production fusion does not reproduce the sealed delivered set on every row")
    if delivery["fusion_vs_rank_disagreements"]:
        raise DeriveError("the fused selection disagrees with the ranked top-8 somewhere")

    newly_delivered: list[str] = []
    newly_lost_wrong: list[str] = []
    lost_by_class: Counter = Counter()
    wrong_rows = 0
    by_plan_class: Counter = Counter()
    for sample_id, verdict in sorted(population["rows"].items()):
        gold = verdict.get("gold_intent")
        if gold is None or sample_id not in base["rows"] or sample_id not in treat["rows"]:
            continue
        if sealed["rows"].get(sample_id) is None:
            continue
        gold_id = f"{recipe.BOUNDARY_DIM}:{gold}"
        before = gold_id in base["rows"][sample_id]["fused"]
        after = gold_id in treat["rows"][sample_id]["fused"]
        if before and not after:
            lost_by_class[verdict["class"]] += 1
        if verdict["class"] != WRONG_CLASS:
            continue
        wrong_rows += 1
        by_plan_class[(verdict["plan_class"], "rows")] += 1
        if after and not before:
            newly_delivered.append(sample_id)
            by_plan_class[(verdict["plan_class"], "newly_delivered")] += 1
        if before and not after:
            newly_lost_wrong.append(sample_id)
            by_plan_class[(verdict["plan_class"], "newly_lost")] += 1

    # cross-check against proof B's recall-derived set on the intent-wrong rows
    recall_set = sorted(s for s, klass in b["arms"]["train-fold-a-plan"]["_newly_delivered"] if klass == WRONG_CLASS)
    if recall_set != sorted(newly_delivered):
        raise DeriveError(
            f"the production constructor derives {len(newly_delivered)} newly delivered intent-wrong rows, "
            f"the production recall {len(recall_set)}; the two paths disagree"
        )
    split = delivery["plan_class_split"]
    if sum(split[k].get("newly_delivered", 0) for k in PLAN_CLASSES) != len(newly_delivered):
        raise DeriveError("the tally's plan-class split does not match the derived set")
    if sum(split[k].get("rows", 0) for k in PLAN_CLASSES) != wrong_rows:
        raise DeriveError("the tally's plan-class rows do not match the intent-wrong count")
    return {
        "recipe_functions_used": ["load_bank", "load_train_gold", "arm_channels", "load_population",
                                  "load_sealed", "boundary_decisions", "tally"],
        "comparator": {"run_id": arm["run_id"], "attempt_id": channels["attempt_id"],
                       "experiment": arm["experiment"], "cell_id": channels["cell_id"],
                       "baseline_fragment": channels["baseline_fragment"],
                       "split_identity_hash": channels["split_identity_hash"],
                       "roster_rows": len(channels["packets"])},
        "sealed_phase_artefact": {"relpath": sealed["relpath"], "sha256": sealed["sha256"]},
        "bad_case_bank_sha256": bank["sha256"],
        "bank_raw_classes": population["raw_classes"],
        "written_boundary_channel": base["pins"],
        "treatment_boundary_channel": treat["pins"],
        "delivery": delivery,
        "wrong_rows": wrong_rows,
        "population_by_plan_class": {
            klass: {
                "rows": by_plan_class[(klass, "rows")],
                "newly_delivered": by_plan_class[(klass, "newly_delivered")],
                "newly_lost": by_plan_class[(klass, "newly_lost")],
            }
            for klass in PLAN_CLASSES
        },
        "newly_lost_by_class_all_rows": dict(sorted(lost_by_class.items())),
        "newly_lost_wrong_ids": newly_lost_wrong,
        "production_constructor_equals_production_recall_on_the_population": True,
        "_ids": sorted(newly_delivered),
    }


# ---------------------------------------------------------------------------


def strip_private(node):
    if isinstance(node, dict):
        return {k: strip_private(v) for k, v in node.items() if not str(k).startswith("_")}
    if isinstance(node, list):
        return [strip_private(v) for v in node]
    if isinstance(node, tuple):
        return [strip_private(v) for v in node]
    if isinstance(node, frozenset):
        return sorted(node)
    if isinstance(node, (np.floating, np.integer)):
        return node.item()
    return node


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--treatment-sha256", default=None,
                        help="the treatment file's sha256; defaults to its receipt's artifact.sha256")
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        print(json.dumps({"error": "PYTHONDONTWRITEBYTECODE=1 is required"}), file=sys.stderr)
        return 1
    repo = Path(args.repo_root).resolve()
    root = Path(args.data_root).resolve()
    lock_path = Path(args.lock_path).resolve()

    receipt_path = root / TREATMENT_RECEIPT_RELPATH
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != "saea-centroid-key-receipt-v1" or receipt.get("artifact_id") != ARTIFACT_ID:
        raise DeriveError("the treatment receipt is not the centroid-key receipt")
    treatment_sha = args.treatment_sha256 or str(receipt["artifact"]["sha256"])
    measured = digest_file(root / TREATMENT_RELPATH)
    if measured != treatment_sha or receipt["artifact"]["sha256"] != measured:
        raise DeriveError("the treatment file does not hash to its receipt's pin")

    diag, diag_sha = import_module(repo, DIAGNOSTIC_RECIPE, "_saea_boundary_key_diagnostic")
    recipe, recipe_sha = import_module(repo, REPLICATION_RECIPE, "_saea_agreement_replication")
    note_sha = digest_file(repo / DIAGNOSTIC_NOTE)
    lock = load_lock(lock_path)

    a = proof_a(diag, root, lock)
    if a["differences"]:
        raise DeriveError("proof A: the diagnostic's arithmetic does not reproduce its note: " + "; ".join(a["differences"]))
    b = proof_b(diag, root, a, treatment_sha)
    if b["differences"]:
        raise DeriveError("proof B: the treatment file does not reproduce through the production recall: " + "; ".join(b["differences"]))
    c = proof_c(recipe, repo, root, lock_path, lock, treatment_sha, b)

    ids = c["_ids"]
    m = len(ids)
    id_list_sha256 = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    probe_split_identity = split_identity_hash(prefixed(CARRIER_LOCK_KEY, ids))
    manifest = json.loads((repo / "configs" / "dataset" / f"{DATASET_FRAGMENT}.json").read_text(encoding="utf-8"))
    by_id = {str(item["sample_id"]): item for item in manifest["items"]}
    missing = [s for s in ids if s not in by_id]
    if missing:
        raise DeriveError(f"{len(missing)} derived ids are not in the roster manifest")
    audio_seconds = sum(float(by_id[s]["audio_seconds"]) for s in ids)
    fold_a = b["arms"]["train-fold-a-plan"]
    wrong = fold_a["per_class"]["INTENT-WRONG"]

    report = {
        "schema": SCHEMA,
        "derivation_id": DERIVATION_ID,
        "contact_class": "model-free",
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0,
                     "tokenizer": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "workers": WORKERS,
        "flown_k": FLOWN_K,
        "recall_width_for_orders": RECALL_WIDTH,
        "why": (
            "The committed diagnostic measured DELIVERY on whole rosters and named the centroid key; "
            "the probe that measures conversion flies exactly the TRAIN Fold A rows whose gold intent's "
            "boundary entry the centroid key NEWLY delivers, and that set is derived here from the "
            "pinned key FILE through the production path, after three proofs: the diagnostic's own "
            "arithmetic reproduces its committed note, the pinned file reproduces the diagnostic's "
            "R01-excluded centroid through the production recall, and the production constructor's "
            "fused selection agrees with the recall on every population row."
        ),
        "authority": {
            "diagnostic_note": {"relpath": str(DIAGNOSTIC_NOTE).replace("\\", "/"), "sha256": note_sha},
            "diagnostic_recipe": {"relpath": str(DIAGNOSTIC_RECIPE).replace("\\", "/"), "sha256": diag_sha,
                                  "imported_unchanged": True},
            "replication_recipe": {"relpath": str(REPLICATION_RECIPE).replace("\\", "/"), "sha256": recipe_sha,
                                   "imported_unchanged": True},
        },
        "treatment": {
            "artifact_id": ARTIFACT_ID,
            "relpath": TREATMENT_RELPATH,
            "sha256": treatment_sha,
            "receipt_relpath": TREATMENT_RECEIPT_RELPATH,
            "receipt_sha256": digest_file(receipt_path),
            "receipt_kind": receipt.get("kind"),
            "construction_pool": receipt["inputs"]["construction_pool_snapshot"],
            "pool_facet_vectors": receipt["inputs"]["pool_facet_vectors"],
            "written_fallback_ids": receipt["measured"]["written_fallback_ids"],
            "facet_source_pin": treatment_pin(treatment_sha),
        },
        "proof_a_diagnostic_reproduced": {
            "note_cells_compared": NOTE_CELLS,
            "differences": a["differences"],
            "r01_excluded_centroid_geometry": a["r01_excluded_centroid_geometry"],
            "arms": {label: {k: v for k, v in arm.items() if not k.startswith("_")} for label, arm in a["arms"].items()},
        },
        "proof_b_treatment_file_through_production_recall": {k: v for k, v in b.items() if k != "arms"} | {
            "arms": {label: {k: v for k, v in arm.items() if not k.startswith("_")} for label, arm in b["arms"].items()},
        },
        "proof_c_population_through_production_constructor": {k: v for k, v in c.items() if not k.startswith("_")},
        "gold_use": (
            "THE ROSTER IS SELECTED USING GOLD, OFFLINE. The bad-case bank's plan_class and each row's "
            "gold intent are read on the scoring side only, in this derivation, before the cell exists. "
            "That is legitimate for a CONDITIONAL estimate on a TRAIN roster and for nothing else: NO "
            "POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE FROM THE CELL THIS ROSTER DEFINES, because "
            "its population was chosen by the mechanism's own effect. Gold reaches no query, no key, "
            "no weight, no selector and no runtime; the key is built from each pool value's frozen "
            "build-time task_target, a store property."
        ),
        "population": {
            "source": c["comparator"] | {"bank_roster": "train-fold-a"},
            "bank_sha256": c["bad_case_bank_sha256"],
            "comparator_class": WRONG_CLASS,
            "bank_plan_classes_collapsed": list(PLAN_CLASSES),
            "class_rows": c["wrong_rows"],
            "by_plan_class": c["population_by_plan_class"],
            "predicate": (
                "the row is intent-WRONG in the sealed comparator (bad-case bank plan_class INTENT-UNCOVERED or "
                "INTENT-COVERED) and the row's own gold intent's intent-boundary value id "
                "is in the fused Perception selection under the centroid key file and NOT under the flown "
                "written key file, both at the flown k 8 / fuse_coverage m 8 / c 1 / top_l 8 / w_agree 0.0 "
                "through provider.candidates + provider.fuse"
            ),
            "expected_order_of_magnitude": {
                "note": "191 intent-wrong rows x (0.712 - 0.450) is about 50 under the FULL-pool centroid the note reports; the treatment file is the R01-excluded centroid",
                "intent_wrong_rows": wrong["rows"],
                "delivered_written": wrong["delivered_written"],
                "delivered_centroid": wrong["delivered_centroid"],
                "newly_delivered": wrong["newly_delivered"],
                "newly_lost": wrong["newly_lost"],
            },
            "what_the_flight_cannot_see": (
                "rows that LOSE their gold entry under the centroid key, and rows the comparator already "
                "answers correctly: both lie outside this roster and remain a construction cell's question"
            ),
            "newly_lost_by_class_all_rows": c["newly_lost_by_class_all_rows"],
        },
        "roster": {
            "dataset_fragment": DATASET_FRAGMENT,
            "carrier_lock_key": CARRIER_LOCK_KEY,
            "count": m,
            "ids": ids,
            "id_list_sha256": id_list_sha256,
            "id_list_convention": "sha256 over the LF-joined sorted sample ids, UTF-8, no trailing newline",
            "split_identity_hash": probe_split_identity,
            "split_identity_convention": (
                "data.splits.split_identity_hash over the LF-joined sorted carrier-prefixed ids f'slurp/{sample_id}'"
            ),
            "audio_seconds_total": round(audio_seconds, 7),
            "newly_lost_wrong_ids": c["newly_lost_wrong_ids"],
        },
        "the_quantity_this_roster_measures": {
            "name": "P(correct | newly delivered)",
            "what_it_is": (
                "the conversion from delivery to correctness for the centroid boundary key: of the rows "
                "whose gold intent's boundary entry the key newly puts in front of the Solver, the share "
                "that move from a wrong intent to the gold intent. Every row is intent WRONG in the sealed "
                "comparator, so the forward count is the whole estimate and the reverse count is zero by "
                "construction."
            ),
            "headroom_slu_pp_per_row": round(HEADROOM_SLU_PP_PER_ROW, 6),
            "headroom_intent_pp_per_row": round(HEADROOM_INTENT_PP_PER_ROW, 6),
            "re_declared_expectation_rule": (
                "a later 1,080-row construction cell's expected_effect_pp = (rows of this roster that move "
                f"from a wrong intent to the gold intent) x {HEADROOM_INTENT_PP_PER_ROW:.6f} pp intent "
                f"accuracy (primary under owner decision 133), and x {HEADROOM_SLU_PP_PER_ROW:.6f} pp "
                "SLU-F1 for the guard."
            ),
            "rows_needed_to_clear_the_2_5_pp_intent_bar": math.ceil(ARM_ADMISSION_BAR_PP / HEADROOM_INTENT_PP_PER_ROW),
            "ceiling_intent_pp_at_perfect_conversion": round(m * HEADROOM_INTENT_PP_PER_ROW, 4),
            "ceiling_slu_pp_at_perfect_conversion": round(m * HEADROOM_SLU_PP_PER_ROW, 4),
            "arm_admission_bar_pp": ARM_ADMISSION_BAR_PP,
            "arm_rows": ARM_ROWS,
            "the_only_directly_observable_prior": (
                "86 of the 191 intent-wrong Fold A rows already RECEIVE the gold intent's boundary entry "
                "under the written key and are wrong anyway; the CONV probe measured 32 of 70 newly "
                "delivered rows converting under the agreement term. Neither is a prediction for this key."
            ),
        },
        "boundary": (
            "ZERO model, server, encoder, embedder, scorer, tokenizer, network, GPU and paid-API contacts: no "
            "server was started, stopped or probed, no waveform decoded and no text encoded. Every number "
            "is arithmetic over receipt-pinned vector files and frozen snapshots, each verified against its "
            "configured sha256 by this repository's own loaders through its own rails.phase_supply / "
            "rails.knowledge_provider / rails.kb_policy seams. A DERIVATION, never a gate: it registers no "
            "cell by itself, admits no mechanism, releases or rebuilds no store, authorises no flight and "
            "states no effectiveness, superiority or generalisation claim. Every roster is a discovery or "
            "dev roster and every number is a development number (owner decisions 28 and 86). Every number "
            "here is DELIVERY, never correctness. No utterance text, transcript, gold label, knowledge body "
            "or delivered answer is printed or persisted: every cell is an id, a count, a rate or a hash."
        ),
    }
    report = strip_private(report)
    out = repo / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print(json.dumps({
        "derived_rows": m,
        "id_list_sha256": id_list_sha256,
        "split_identity_hash": probe_split_identity,
        "audio_seconds_total": round(audio_seconds, 7),
        "fold_a_intent_wrong": wrong,
        "fold_a_treatment_cells": fold_a["cells"],
        "roll1_treatment_cells": b["arms"]["roll1"]["cells"],
        "dev2000_treatment_cells": b["arms"]["dev2000-added-plan"]["cells"],
        "proof_a_differences": a["differences"],
        "proof_b_differences": b["differences"],
        "newly_lost_by_class_all_rows": c["newly_lost_by_class_all_rows"],
        "output": str(out.relative_to(repo)).replace("\\", "/") if out.is_relative_to(repo) else str(out),
        "output_sha256": digest_file(out),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
