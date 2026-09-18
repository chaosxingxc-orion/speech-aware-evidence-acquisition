"""Cell B5e config-switch proof: the early combination of modules M1 and M4b.

Cell B5e (owner decision 19 of 2026-09-18) is the first cell of the SLURP v2
base program that turns on **two** admitted modules at once:

* **M1** -- the named knowledge store ``train-exemplars`` (speech-keyed
  annotated TRAIN exemplars supplied to the Solver), admitted by cell B1 and
  its derangement twin;
* **M4b** -- the ``slot-contracts`` store re-pinned from release/snapshot v1
  to v2 (the date/time slot-contract revision), admitted by cell B4b.

A combination cell is only interpretable if each module is *the same module*
it was when it was admitted alone. These tests pin exactly that, on the
committed baseline fragments and without composing a runtime:

1. against the sealed dual-store anchor, cell B5e moves ``knowledge_stores``
   and bookkeeping only -- no ``phase_material``, ``phase_tools``,
   ``native_episode``, ``policy``, template, scorer or geometry key;
2. inside ``knowledge_stores`` exactly two store ids move: ``train-exemplars``
   is ADDED and ``slot-contracts`` is re-pinned in exactly two leaves
   (``release`` and ``snapshot``), while ``intent-boundaries`` is untouched;
3. the added ``train-exemplars`` block is **byte-for-byte** the block the B1
   recovery arm flew, and the re-pinned ``slot-contracts`` block is
   **byte-for-byte** the block cell B4b flew;
4. removing ``train-exemplars`` and restoring the v1 slot-contract pins
   reconstructs the anchor's own ``knowledge_stores`` block exactly -- the OFF
   arm of both modules together is the base, not a third cell identity;
5. the four-row smoke baseline is the arm baseline apart from its own FIT
   identity (the 4 x 11 x 4 = 176 endpoint ceiling), its own two
   speech-feature identity ids, its own prepared-supply pin and its note.

Model-free: it reads committed JSON and nothing else.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "configs" / "baseline"

ANCHOR = "slurp-native-dual-store-train-fold-a-anchor-v1.json"
B1_ARM = "slurp-native-anchor-exemplars-k20-train-fold-a-recovery-v2.json"
B4B_ARM = "slurp-native-anchor-slot-store-v2-train-fold-a-v2.json"
B5E_ARM = "slurp-native-anchor-b5e-exemplars-k20-slot-store-v2-train-fold-a-v1.json"
B5E_SMOKE = "slurp-native-anchor-b5e-exemplars-k20-slot-store-v2-smoke-4-v1.json"

# Bookkeeping-only top-level keys: run/attempt identity, provenance receipts,
# the prepared-artifact pin and free-English notes. None of them shapes a
# rendered request; every one of them must differ between two distinct run
# identities.
BOOKKEEPING_KEYS = frozenset(
    {
        "native_contact_fit",
        "prepared_phase_supply",
        "preparation_source_receipts",
        "speech_feature_key_representation_id",
        "speech_feature_matcher_policy_id",
        "what_this_is",
        "what_the_train_exemplars_store_is",
    }
)


def _load(name: str) -> dict:
    return json.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))


def test_b5e_differs_from_the_anchor_by_knowledge_stores_and_bookkeeping_only():
    anchor = _load(ANCHOR)
    b5e = _load(B5E_ARM)

    non_bookkeeping_keys = (set(anchor) | set(b5e)) - BOOKKEEPING_KEYS
    differing = sorted(
        key for key in non_bookkeeping_keys if anchor.get(key) != b5e.get(key)
    )
    assert differing == ["knowledge_stores"]


def test_b5e_moves_exactly_two_store_ids_against_the_anchor():
    anchor_stores = _load(ANCHOR)["knowledge_stores"]
    b5e_stores = _load(B5E_ARM)["knowledge_stores"]

    assert set(b5e_stores) - set(anchor_stores) == {"train-exemplars"}
    moved = sorted(
        store_id
        for store_id in anchor_stores
        if anchor_stores[store_id] != b5e_stores[store_id]
    )
    assert moved == ["slot-contracts"]
    assert b5e_stores["intent-boundaries"] == anchor_stores["intent-boundaries"]

    anchor_slots = anchor_stores["slot-contracts"]
    b5e_slots = b5e_stores["slot-contracts"]
    differing_leaves = sorted(
        leaf
        for leaf in set(anchor_slots) | set(b5e_slots)
        if anchor_slots.get(leaf) != b5e_slots.get(leaf)
    )
    assert differing_leaves == ["release", "snapshot"]
    assert b5e_slots["candidate_supply"] == anchor_slots["candidate_supply"]
    assert b5e_slots["store_role"] == anchor_slots["store_role"]
    assert "slot-contracts-v2" in b5e_slots["release"]["relpath"]
    assert "slot-contracts-v2" in b5e_slots["snapshot"]["relpath"]


def test_each_module_block_is_byte_identical_to_the_cell_that_admitted_it():
    b5e_stores = _load(B5E_ARM)["knowledge_stores"]
    b1_stores = _load(B1_ARM)["knowledge_stores"]
    b4b_stores = _load(B4B_ARM)["knowledge_stores"]

    # M1, exactly as the B1 recovery arm flew it.
    assert b5e_stores["train-exemplars"] == b1_stores["train-exemplars"]
    solver = b5e_stores["train-exemplars"]["phase_supply"]["solver"]
    assert solver["k"] == 20
    assert solver["fuse_policy"] == "saea-fuse-supplyfilter-v1"
    assert solver["fuse_coverage"] == {"m": 20, "c": 20, "top_l": 20}
    assert solver["rank_policy"] == "saea-rank-wcos-prior-agree-v1"
    assert solver["rank_weights"] == {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0}
    assert solver["tau"] == 0.0

    # M4b, exactly as cell B4b flew it.
    assert b5e_stores["slot-contracts"] == b4b_stores["slot-contracts"]


def test_turning_both_modules_off_reconstructs_the_anchor_store_block():
    anchor_stores = _load(ANCHOR)["knowledge_stores"]
    b5e_stores = _load(B5E_ARM)["knowledge_stores"]

    off = copy.deepcopy(b5e_stores)
    del off["train-exemplars"]
    off["slot-contracts"]["release"] = copy.deepcopy(
        anchor_stores["slot-contracts"]["release"]
    )
    off["slot-contracts"]["snapshot"] = copy.deepcopy(
        anchor_stores["slot-contracts"]["snapshot"]
    )
    assert off == anchor_stores


def test_the_smoke_baseline_is_the_arm_baseline_apart_from_its_own_identities():
    arm = _load(B5E_ARM)
    smoke = _load(B5E_SMOKE)

    differing = sorted(key for key in set(arm) | set(smoke) if arm.get(key) != smoke.get(key))
    assert differing == [
        "native_contact_fit",
        "prepared_phase_supply",
        "speech_feature_key_representation_id",
        "speech_feature_matcher_policy_id",
        "what_this_is",
    ]
    assert smoke["knowledge_stores"] == arm["knowledge_stores"]
    assert arm["native_contact_fit"]["contact_cap"] == 47520
    assert smoke["native_contact_fit"]["contact_cap"] == 176


def test_the_preparation_receipts_carry_the_v2_slot_contract_provenance():
    b5e = _load(B5E_ARM)
    relpaths = [row["relpath"] for row in b5e["preparation_source_receipts"]]
    assert not any("slot-contracts-v1" in relpath for relpath in relpaths)
    assert sum("slot-contracts-v2" in relpath for relpath in relpaths) == 2
    assert any("size-pool-annotated-exemplars" in relpath for relpath in relpaths)

    b4b_rows = {
        row["relpath"]: row
        for row in _load(B4B_ARM)["preparation_source_receipts"]
        if "slot-contracts-v2" in row["relpath"]
    }
    for row in b5e["preparation_source_receipts"]:
        if "slot-contracts-v2" in row["relpath"]:
            assert row == b4b_rows[row["relpath"]]
