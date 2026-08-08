"""Probe-sample splits through the T1 split seam (P1 scaffold).

A probe split name (any name outside the three contract splits) resolves via
``docs/receipts/probe-samples/<name>.json``: strict parse, receipt-hash
recomputation under the receipt's own colon-key convention
(``reproduction.sampling.split_identity_hash``), and a DERIVED run-identity
hash under the E0 slash convention (``data.splits``) — the value an
``ExecutionPlan``/run manifest carries, and the one ``core.bundle.verify_bundle``
independently recomputes from the manifest's carrier + bare ids.
"""

import json

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
from speech_aware_evidence_acquisition.reproduction.probe_split import (
    load_verified_probe_split,
)

A2T_RECEIPT_NAME = "r1-a2t-test"  # matches tests/unit/conftest.py's Audio2ToolWorld


def test_probe_split_resolves_to_a_verified_split(audio2tool_world):
    split = load_verified_probe_split(audio2tool_world.repo_root, A2T_RECEIPT_NAME)
    assert isinstance(split, VerifiedSplit)
    assert split.name == A2T_RECEIPT_NAME
    assert split.carrier_lock_key == "audio2tool"
    assert split.split_role == "discovery"
    assert split.ids == (
        "tier1_direct:000001",
        "tier3_multi_intent:000004",
        "tier7_multiturn:000009",
    )
    # prefixed ids and identity hash follow the E0 slash convention, so the
    # bundle verifier's independent recomputation matches byte-for-byte.
    assert split.prefixed_ids == tuple(prefixed("audio2tool", split.ids))
    assert split.identity_hash == slash_hash(split.prefixed_ids)


def test_load_verified_split_dispatches_probe_names(audio2tool_world):
    split = load_verified_split(
        audio2tool_world.repo_root, A2T_RECEIPT_NAME, lock={}, root=audio2tool_world.data_root
    )
    assert split.carrier_lock_key == "audio2tool"
    assert split.identity_hash == slash_hash(split.prefixed_ids)


def test_missing_probe_receipt_fails_closed(audio2tool_world):
    with pytest.raises(SplitReceiptError, match="no-such-probe"):
        load_verified_probe_split(audio2tool_world.repo_root, "no-such-probe")


def test_path_traversal_split_name_is_refused(audio2tool_world):
    with pytest.raises(SplitReceiptError, match="split name"):
        load_verified_probe_split(audio2tool_world.repo_root, "../evil")


def test_tampered_receipt_items_fail_closed(audio2tool_world):
    items = audio2tool_world.receipt_items()
    items[0]["key"] = "audio2tool:tier1_direct:000002"
    items[0]["id"] = 2
    # keep the OLD hash on disk: item tampering must trip the recomputation
    payload = json.loads(audio2tool_world.receipt_path.read_text(encoding="utf-8"))
    audio2tool_world.write_receipt(
        items=items, split_identity_hash=payload["split_identity_hash"]
    )
    with pytest.raises(SplitReceiptError, match="split_identity_hash"):
        load_verified_probe_split(audio2tool_world.repo_root, A2T_RECEIPT_NAME)


def test_confirmatory_probe_role_is_refused(audio2tool_world):
    audio2tool_world.write_receipt(split_role="confirmatory")
    with pytest.raises(SplitReceiptError, match="split_role"):
        load_verified_probe_split(audio2tool_world.repo_root, A2T_RECEIPT_NAME)


def test_unprefixed_item_key_is_refused(audio2tool_world):
    items = audio2tool_world.receipt_items()
    items[0]["key"] = "elsewhere:tier1_direct:000001"
    audio2tool_world.write_receipt(items=items)
    with pytest.raises(SplitReceiptError, match="prefixed"):
        load_verified_probe_split(audio2tool_world.repo_root, A2T_RECEIPT_NAME)


def test_real_frozen_r1_receipt_verifies_and_derives_a_run_hash():
    """Pre-flight over the ACTUAL committed 400-item receipt (identity only,
    no data root touched): it parses, its colon-key hash re-verifies, and the
    slash-convention run hash an ExecutionPlan will carry is derivable."""

    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    split = load_verified_probe_split(REPO_ROOT, "r1-audio2tool-sample")
    assert split.carrier_lock_key == "audio2tool"
    assert split.split_role == "discovery"
    assert len(split.ids) == 400
    assert all(":" in sample_id for sample_id in split.ids)
    assert split.identity_hash == slash_hash(split.prefixed_ids)


def test_contract_split_names_still_use_the_frozen_receipt_path(tmp_path):
    """The three contract splits never reach the probe path: with no
    docs/receipts/splits.json present they fail with the splits-receipt
    error, exactly as before this dispatch existed."""

    with pytest.raises(SplitReceiptError, match="splits receipt missing"):
        load_verified_split(tmp_path, "dev", lock={}, root=tmp_path)
