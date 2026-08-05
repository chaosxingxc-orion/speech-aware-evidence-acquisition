"""Contract: the committed splits receipt (once frozen) is internally coherent."""

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.splits import (
    SPLITS_SCHEMA,
    split_identity_hash,
)

RECEIPT = Path(__file__).resolve().parents[2] / "docs" / "receipts" / "splits.json"


@pytest.mark.skipif(not RECEIPT.is_file(), reason="splits not frozen yet")
def test_committed_splits_receipt_is_coherent():
    document = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert document["schema"] == SPLITS_SCHEMA
    splits = document["splits"]
    assert set(splits) == {"discovery", "dev", "confirmatory"}
    for name, split in splits.items():
        assert split["ids"] == sorted(split["ids"]), name
        assert split["identity_hash"] == split_identity_hash(split["ids"]), name
    assert splits["dev"]["count"] == 10
    assert set(splits["dev"]["ids"]).isdisjoint(splits["confirmatory"]["ids"])
    assert splits["discovery"]["split_role"] == "discovery"
    assert splits["confirmatory"]["split_role"] == "confirmatory"
