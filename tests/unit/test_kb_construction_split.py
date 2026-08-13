"""kb-construction split (owner decision 2026-08-13): the 34 earnings21-original
discovery calls OUTSIDE the frozen r4-e21-sub10-sample ten. Freezes identity
only -- the KB-intersection gate refusal is a separate, later task.

Mirrors tests/unit/test_probe_split.py's real-frozen-receipt check and
tests/unit/test_wave1_substrate_configs.py's real-receipt probe-split
resolution test, plus the anti-cheat invariant this split exists for: exact
disjoint complementarity with r4-e21-sub10-sample inside the frozen discovery
44.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.split_receipt import (
    SplitReceiptError,
    VerifiedSplit,
    load_verified_split,
)
from speech_aware_evidence_acquisition.data.splits import (
    prefixed,
    split_identity_hash as slash_hash,
)
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT
from speech_aware_evidence_acquisition.reproduction.probe_split import (
    load_verified_probe_split,
)
from speech_aware_evidence_acquisition.reproduction.sampling import (
    split_identity_hash as key_hash,
)

RECEIPTS_DIR = Path(REPO_ROOT) / "docs" / "receipts" / "probe-samples"
KB_RECEIPT_PATH = RECEIPTS_DIR / "kb-construction-sample.json"
R4_RECEIPT_PATH = RECEIPTS_DIR / "r4-e21-sub10-sample.json"
SPLITS_RECEIPT_PATH = Path(REPO_ROOT) / "docs" / "receipts" / "splits.json"
DATASET_FRAGMENT_PATH = Path(REPO_ROOT) / "configs" / "dataset" / "kb-construction.json"

# Pinned so a regenerated receipt that silently picks different ids fails
# loudly (same discipline as test_wave1_substrate_configs.py's pinned set).
EXPECTED_IDS = {
    "4320211", "4341191", "4344338", "4344866", "4346818", "4346923",
    "4359732", "4359971", "4360366", "4360674", "4360717", "4361631",
    "4363614", "4364366", "4366302", "4366893", "4367318", "4367535",
    "4368670", "4374910", "4375653", "4382825", "4383161", "4384198",
    "4384683", "4384744", "4385388", "4385939", "4386541", "4387332",
    "4387865", "4392809", "4394084", "4397800",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_kb_construction_receipt_identity_hash_matches_recomputation():
    """The receipt's own split_identity_hash independently recomputes from
    its item keys under the colon/key convention -- the same check
    load_verified_probe_split enforces fail-closed."""

    payload = _load(KB_RECEIPT_PATH)
    keys = [item["key"] for item in payload["items"]]
    assert key_hash(keys) == payload["split_identity_hash"]


def test_kb_construction_has_exactly_34_items():
    payload = _load(KB_RECEIPT_PATH)
    assert len(payload["items"]) == 34
    assert {item["id"] for item in payload["items"]} == EXPECTED_IDS


def test_kb_construction_is_disjoint_from_the_frozen_r4_ten():
    kb_ids = {item["id"] for item in _load(KB_RECEIPT_PATH)["items"]}
    r4_ids = {item["id"] for item in _load(R4_RECEIPT_PATH)["items"]}
    assert len(r4_ids) == 10
    assert kb_ids.isdisjoint(r4_ids)


def test_kb_construction_is_exactly_discovery_minus_the_frozen_r4_ten():
    """Membership rule, proved directly: kb-construction ids union r4's ten
    ids reconstruct the full frozen 44-id discovery split, with no overlap
    and no leftover -- not merely "disjoint from r4", but its exact
    complement inside discovery."""

    kb_ids = {item["id"] for item in _load(KB_RECEIPT_PATH)["items"]}
    r4_ids = {item["id"] for item in _load(R4_RECEIPT_PATH)["items"]}
    discovery_ids = {
        prefixed_id.split("/", 1)[1]
        for prefixed_id in _load(SPLITS_RECEIPT_PATH)["splits"]["discovery"]["ids"]
    }
    assert len(discovery_ids) == 44
    assert kb_ids | r4_ids == discovery_ids
    assert kb_ids & r4_ids == set()


def test_kb_construction_receipt_carrier_and_role():
    payload = _load(KB_RECEIPT_PATH)
    assert payload["carrier"] == "earnings21-original"
    assert payload["split_role"] == "discovery"


def test_real_frozen_kb_construction_receipt_verifies_and_derives_a_run_hash():
    """Pre-flight over the ACTUAL committed receipt (identity only, no data
    root touched): it parses, its colon-key hash re-verifies, and the
    slash-convention run hash an ExecutionPlan would carry is derivable --
    mirrors test_probe_split.py's real-r1-receipt check."""

    split = load_verified_probe_split(REPO_ROOT, "kb-construction-sample")
    assert isinstance(split, VerifiedSplit)
    assert split.carrier_lock_key == "earnings21-original"
    assert split.split_role == "discovery"
    assert len(split.ids) == 34
    assert set(split.ids) == EXPECTED_IDS
    assert split.prefixed_ids == tuple(prefixed("earnings21-original", split.ids))
    assert split.identity_hash == slash_hash(split.prefixed_ids)


def test_kb_construction_dataset_fragment_resolves_through_load_verified_split(tmp_path):
    """configs/dataset/kb-construction.json resolves through the exact same
    split<->plan<->config seam r4-e21-sub10.json does: any split name outside
    the three contract splits dispatches purely off the receipt file, so a
    dummy lock/root (never touched on this path) is enough -- mirrors
    test_probe_split.py::test_load_verified_split_dispatches_probe_names."""

    fragment = _load(DATASET_FRAGMENT_PATH)
    assert fragment == {
        "carrier_lock_key": "earnings21-original",
        "split_name": "kb-construction-sample",
    }
    split = load_verified_split(
        REPO_ROOT, fragment["split_name"], lock={}, root=tmp_path
    )
    assert split.carrier_lock_key == fragment["carrier_lock_key"]
    assert len(split.ids) == 34
    assert split.identity_hash == slash_hash(split.prefixed_ids)


def test_kb_construction_split_name_is_not_a_contract_split():
    """Sanity: 'kb-construction-sample' must dispatch through the probe-sample
    path, not silently collide with discovery/dev/confirmatory."""

    with pytest.raises(SplitReceiptError):
        load_verified_split(REPO_ROOT, "kb-construction", lock={}, root=REPO_ROOT)
