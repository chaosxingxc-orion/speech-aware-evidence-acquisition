"""Split identity: convention stability, membership, and receipt generation."""

import json

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.splits import (
    SPLITS_SCHEMA,
    confirmatory_split,
    dev_split,
    discovery_split,
    freeze_splits,
    prefixed,
    split_identity_hash,
)


def test_split_identity_hash_convention_is_frozen():
    # Known vector: sha256 over LF-joined sorted ids, no trailing newline.
    # Changing the convention breaks comparability with the E0 ledger row and
    # must fail loudly here.
    assert (
        split_identity_hash(["b/2", "a/1"])
        == "8bd12b24d6eb14c9a141597ec482f69a14c9a5024036441d727b4a968e67a33f"
    )


def test_prefixed_uses_lock_key_and_slash():
    assert prefixed("earnings21-original", ["2", "1"]) == [
        "earnings21-original/1",
        "earnings21-original/2",
    ]


def test_splits_partition_the_carriers(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    root = synthetic_world.data_root
    disc = discovery_split(lock, root)
    dev = dev_split(lock, root)
    conf = confirmatory_split(lock, root)
    # Synthetic world (tests/unit/conftest.py): 3 e21 samples, 12 e22, subset10 = 10.
    assert disc.carrier_lock_key == "earnings21-original"
    assert disc.split_role == "discovery"
    assert disc.count == 3
    assert dev.split_role == "dev"
    assert dev.count == 10
    assert conf.split_role == "confirmatory"
    assert conf.count == 2
    assert all(i.startswith("earnings22-original/") for i in dev.ids + conf.ids)
    assert set(dev.ids).isdisjoint(conf.ids)
    assert disc.identity_hash == split_identity_hash(disc.ids)


def test_freeze_splits_writes_receipt(synthetic_world, tmp_path):
    lock = load_lock(synthetic_world.lock_path)
    receipts = tmp_path / "receipts"
    document = freeze_splits(lock, synthetic_world.data_root, receipts)
    on_disk = json.loads((receipts / "splits.json").read_text(encoding="utf-8"))
    assert on_disk == document
    assert document["schema"] == SPLITS_SCHEMA
    assert set(document["splits"]) == {"discovery", "dev", "confirmatory"}
    for split in document["splits"].values():
        assert split["identity_hash"] == split_identity_hash(split["ids"])
