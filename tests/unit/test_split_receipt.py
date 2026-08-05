"""Split receipt authenticity (R0 repair T1, invariant I1, regression probe P2).

`docs/receipts/splits.json` is an external, editable artifact. These tests
prove that a tampered receipt is refused before any model-facing code can
consume it: strict internal parsing (schema, exact key set, per-split shape,
sorted/unique/carrier-prefixed ids, identity_hash recomputed from ids,
same-carrier splits pairwise disjoint) AND live recomputation against the
current carrier loader, byte-for-byte.

Each probe tampers exactly one property of an otherwise-valid, freshly-frozen
receipt so it demonstrates that specific guard is load-bearing.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.split_receipt import (
    SplitReceiptError,
    VerifiedSplit,
    load_verified_split,
    verify_receipt_document,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.splits import (
    SPLITS_RECEIPT_NAME,
    split_identity_hash,
    freeze_splits,
)


def _frozen_world(synthetic_world, tmp_path):
    lock = load_lock(synthetic_world.lock_path)
    repo_root = tmp_path / "repo"
    receipts = repo_root / "docs" / "receipts"
    document = freeze_splits(lock, synthetic_world.data_root, receipts)
    return lock, synthetic_world.data_root, repo_root, document


def _receipt_path(repo_root: Path) -> Path:
    return repo_root / "docs" / "receipts" / SPLITS_RECEIPT_NAME


def _write(repo_root: Path, document: dict) -> None:
    _receipt_path(repo_root).write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def _resort(document: dict, split_name: str) -> None:
    """Re-derive count/identity_hash for a split whose ids list was tampered,
    so the only violation left is the one the probe targets."""

    split = document["splits"][split_name]
    ids = sorted(split["ids"])
    split["ids"] = ids
    split["count"] = len(ids)
    split["identity_hash"] = split_identity_hash(ids)


# ---------------------------------------------------------------------------
# Happy path: a freshly frozen receipt verifies and matches live recomputation.
# ---------------------------------------------------------------------------


def test_verify_receipt_document_accepts_a_freshly_frozen_receipt(synthetic_world, tmp_path):
    lock, root, repo_root, document = _frozen_world(synthetic_world, tmp_path)
    verified = verify_receipt_document(document)
    assert set(verified) == {"discovery", "dev", "confirmatory"}
    assert isinstance(verified["dev"], VerifiedSplit)
    assert len(verified["dev"].ids) == 10
    assert len(verified["confirmatory"].ids) == 2


def test_load_verified_split_matches_live_recomputation(synthetic_world, tmp_path):
    lock, root, repo_root, _document = _frozen_world(synthetic_world, tmp_path)
    verified = load_verified_split(repo_root, "dev", lock, root)
    assert verified.split_role == "dev"
    assert len(verified.ids) == 10
    assert all(sample_id.startswith("50000") for sample_id in verified.ids)


# ---------------------------------------------------------------------------
# Probe 1: dev ids swapped for real same-carrier (confirmatory) ids, stored
# hash kept. The old downstream "ids missing from loaded samples" check could
# NOT catch this — the substituted ids are real, loadable earnings22 ids.
# ---------------------------------------------------------------------------


def test_probe1_dev_ids_swapped_for_real_confirmatory_ids_is_refused(synthetic_world, tmp_path):
    lock, root, repo_root, document = _frozen_world(synthetic_world, tmp_path)
    tampered = copy.deepcopy(document)
    dev = tampered["splits"]["dev"]
    confirmatory = tampered["splits"]["confirmatory"]
    borrowed = confirmatory["ids"][:2]
    assert len(borrowed) == 2

    new_dev_ids = sorted(dev["ids"][2:] + borrowed)
    assert len(new_dev_ids) == dev["count"]  # same count, real same-carrier ids
    dev["ids"] = new_dev_ids
    # stored hash and count are deliberately left untouched (the attack).
    _write(repo_root, tampered)

    with pytest.raises(SplitReceiptError, match="dev"):
        load_verified_split(repo_root, "dev", lock, root)
    with pytest.raises(SplitReceiptError, match="dev"):
        verify_receipt_document(tampered)


# ---------------------------------------------------------------------------
# Probe 2: generic stale hash — ids edited (one id replaced by a fabricated
# id), stored hash kept unchanged.
# ---------------------------------------------------------------------------


def test_probe2_stale_hash_after_id_edit_is_refused(synthetic_world, tmp_path):
    lock, root, repo_root, document = _frozen_world(synthetic_world, tmp_path)
    tampered = copy.deepcopy(document)
    discovery = tampered["splits"]["discovery"]
    ids = discovery["ids"][1:] + ["earnings21-original/9999999"]
    discovery["ids"] = sorted(ids)
    # count still matches (len unchanged); identity_hash deliberately stale.
    _write(repo_root, tampered)

    with pytest.raises(SplitReceiptError, match="discovery"):
        verify_receipt_document(tampered)
    with pytest.raises(SplitReceiptError, match="discovery"):
        load_verified_split(repo_root, "discovery", lock, root)


# ---------------------------------------------------------------------------
# Probe 3: wrong carrier prefix inside an earnings22 split.
# ---------------------------------------------------------------------------


def test_probe3_wrong_prefix_inside_earnings22_split_is_refused(synthetic_world, tmp_path):
    lock, root, repo_root, document = _frozen_world(synthetic_world, tmp_path)
    tampered = copy.deepcopy(document)
    dev = tampered["splits"]["dev"]
    victim = dev["ids"][0]
    bare = victim.split("/", 1)[1]
    dev["ids"] = [f"conec/{bare}" if pid == victim else pid for pid in dev["ids"]]
    _resort(tampered, "dev")  # hash/count/order otherwise internally consistent
    _write(repo_root, tampered)

    with pytest.raises(SplitReceiptError, match="dev"):
        verify_receipt_document(tampered)
    with pytest.raises(SplitReceiptError, match="dev"):
        load_verified_split(repo_root, "dev", lock, root)


# ---------------------------------------------------------------------------
# Probe 4: duplicate id within one split.
# ---------------------------------------------------------------------------


def test_probe4_duplicate_id_is_refused(synthetic_world, tmp_path):
    lock, root, repo_root, document = _frozen_world(synthetic_world, tmp_path)
    tampered = copy.deepcopy(document)
    dev = tampered["splits"]["dev"]
    dev["ids"] = sorted(dev["ids"] + [dev["ids"][0]])  # a real id, duplicated
    dev["count"] = len(dev["ids"])
    dev["identity_hash"] = split_identity_hash(dev["ids"])
    _write(repo_root, tampered)

    with pytest.raises(SplitReceiptError, match="dev"):
        verify_receipt_document(tampered)
    with pytest.raises(SplitReceiptError, match="dev"):
        load_verified_split(repo_root, "dev", lock, root)


# ---------------------------------------------------------------------------
# Probe 5: count field mismatch (ids/hash otherwise correct).
# ---------------------------------------------------------------------------


def test_probe5_count_mismatch_is_refused(synthetic_world, tmp_path):
    lock, root, repo_root, document = _frozen_world(synthetic_world, tmp_path)
    tampered = copy.deepcopy(document)
    tampered["splits"]["dev"]["count"] = tampered["splits"]["dev"]["count"] - 1
    _write(repo_root, tampered)

    with pytest.raises(SplitReceiptError, match="dev"):
        verify_receipt_document(tampered)
    with pytest.raises(SplitReceiptError, match="dev"):
        load_verified_split(repo_root, "dev", lock, root)


# ---------------------------------------------------------------------------
# Probe 6: wrong schema tag.
# ---------------------------------------------------------------------------


def test_probe6_wrong_schema_tag_is_refused(synthetic_world, tmp_path):
    lock, root, repo_root, document = _frozen_world(synthetic_world, tmp_path)
    tampered = copy.deepcopy(document)
    tampered["schema"] = "saea-splits-v0-legacy"
    _write(repo_root, tampered)

    with pytest.raises(SplitReceiptError, match="schema"):
        verify_receipt_document(tampered)
    with pytest.raises(SplitReceiptError, match="schema"):
        load_verified_split(repo_root, "dev", lock, root)


# ---------------------------------------------------------------------------
# Probe 7: live-recomputation drift — the receipt is fully internally
# consistent (passes verify_receipt_document) but its ids do not match what
# the current carrier loader actually enumerates from disk. This is the
# "self-certifying artifact treated as verified artifact" failure mode: a
# receipt can be perfectly self-consistent and still be a lie.
# ---------------------------------------------------------------------------


def test_probe7_internally_consistent_but_live_recomputation_drift_is_refused(
    synthetic_world, tmp_path
):
    lock, root, repo_root, document = _frozen_world(synthetic_world, tmp_path)
    tampered = copy.deepcopy(document)
    discovery = tampered["splits"]["discovery"]
    ids = discovery["ids"][1:] + ["earnings21-original/9999999"]  # no such media file
    discovery["ids"] = sorted(ids)
    discovery["count"] = len(discovery["ids"])
    discovery["identity_hash"] = split_identity_hash(discovery["ids"])
    _write(repo_root, tampered)

    # Fully self-consistent: the pure structural verifier accepts it.
    verified = verify_receipt_document(tampered)
    assert verified["discovery"].identity_hash == discovery["identity_hash"]

    # Live recomputation against the real (synthetic) media directory refuses it.
    with pytest.raises(SplitReceiptError, match="discovery"):
        load_verified_split(repo_root, "discovery", lock, root)


# ---------------------------------------------------------------------------
# Probe 8 (coverage fix, T1 review): same-carrier disjointness must be the
# check that fires, in isolation. `dev` and `confirmatory` both carry
# earnings22-original ids; an attacker who adds one real confirmatory id into
# dev (without removing anything, so dev's own count/identity_hash are
# re-derived and internally correct, and confirmatory is left untouched and
# already internally correct) produces a document where every per-split
# structural check passes for BOTH splits — role, carrier prefix, sorted,
# unique, count==len(ids), identity_hash-recomputed-from-ids all hold. The
# *only* thing wrong is that the two same-carrier splits now overlap. This
# isolates the disjointness guard as load-bearing: deleting it would let this
# exact probe through `verify_receipt_document` with zero errors (verified
# below by temporarily removing the guard — see the report).
# ---------------------------------------------------------------------------


def test_probe8_same_carrier_overlap_with_all_other_checks_passing_is_refused(
    synthetic_world, tmp_path
):
    lock, root, repo_root, document = _frozen_world(synthetic_world, tmp_path)
    tampered = copy.deepcopy(document)
    dev = tampered["splits"]["dev"]
    confirmatory = tampered["splits"]["confirmatory"]

    borrowed = confirmatory["ids"][0]  # a real, untouched confirmatory id
    assert borrowed not in dev["ids"]

    # dev gains the id (not a swap: nothing is removed from dev), then dev's
    # own count/identity_hash are correctly re-derived from its new id set.
    dev["ids"] = sorted(dev["ids"] + [borrowed])
    dev["count"] = len(dev["ids"])
    dev["identity_hash"] = split_identity_hash(dev["ids"])
    # confirmatory is left completely untouched: still internally correct.
    _write(repo_root, tampered)

    # Every per-split structural check independently passes for both splits.
    assert dev["count"] == len(dev["ids"]) == len(set(dev["ids"]))
    assert dev["identity_hash"] == split_identity_hash(dev["ids"])
    assert confirmatory["count"] == len(confirmatory["ids"])
    assert confirmatory["identity_hash"] == split_identity_hash(confirmatory["ids"])

    # verify_receipt_document alone (layer 1, no live loader involved) must
    # refuse this — the disjointness guard, not live recomputation, is what
    # catches it.
    with pytest.raises(SplitReceiptError, match="disjoint"):
        verify_receipt_document(tampered)
