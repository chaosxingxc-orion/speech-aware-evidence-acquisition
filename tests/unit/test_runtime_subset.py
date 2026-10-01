import json
from pathlib import Path

import pytest
from speech_aware_evidence_acquisition.data.runtime_subset import build_runtime_subset
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def parent():
    p = {"count": 5, "items": [{"sample_id": f"x:{i}", "audio_seconds": 1} for i in range(5)],
         "carrier_lock_key": "fixture", "split_name": "parent", "split_role": "discovery", "seed": 1}
    return {**p, "runtime_view_sha256": content_hash(p)}


def test_seeded_subset_is_order_independent_and_preserves_rows():
    p = parent()
    view, receipt = build_runtime_subset(p, seed=20261001, count=4, name="child")
    q = {k:v for k,v in p.items() if k != "runtime_view_sha256"}
    q["items"] = list(reversed(q["items"]))
    q["runtime_view_sha256"] = content_hash(q)
    other, _ = build_runtime_subset(q, seed=20261001, count=4, name="child")
    assert view["items"] == other["items"]
    assert view["count"] == 4 and len({x["sample_id"] for x in view["items"]}) == 4
    assert view["source_binding_sha256"] == content_hash(receipt)
    assert all(row in p["items"] for row in view["items"])


def test_parent_mutation_and_invalid_count_refused():
    p = parent(); p["items"][0]["audio_seconds"] = 2
    with pytest.raises(ValueError, match="hash"):
        build_runtime_subset(p, seed=1, count=4, name="child")
    for count in [True, 0, 6]:
        with pytest.raises(ValueError):
            build_runtime_subset(parent(), seed=1, count=count, name="child")


def test_nonzero_slice_preserves_registered_hash_order_and_source_rows():
    p = parent()
    full, _ = build_runtime_subset(p, seed=20261001, count=5, name="whole")
    view, receipt = build_runtime_subset(p, seed=20261001, start=2, count=2, name="later")
    assert view["items"] == full["items"][2:4]
    assert receipt["schema"] == "saea-runtime-subset-receipt-v2"
    assert receipt["slice_start"] == 2
    assert receipt["sample_ids"] == [i["sample_id"] for i in full["items"][2:4]]
    assert view["source_binding_sha256"] == content_hash(receipt)
    assert view["audio_seconds_total"] == 2


def test_explicit_zero_start_keeps_historical_identity():
    old = build_runtime_subset(parent(), seed=20261001, count=2, name="child")
    assert build_runtime_subset(parent(), seed=20261001, start=0, count=2, name="child") == old
    assert old[1]["schema"] == "saea-runtime-subset-receipt-v1"
    assert "slice_start" not in old[1]


@pytest.mark.parametrize("start", [True, -1, 1.0, "1", 4, 5])
def test_invalid_slice_offset_refused(start):
    with pytest.raises(ValueError, match="slice"):
        build_runtime_subset(parent(), seed=1, start=start, count=2, name="child")


def test_default_retains_existing_registered_view_and_receipt():
    root = Path(__file__).resolve().parents[2]
    p = json.loads((root / "configs/dataset/slurp-speech-native-stage3-construction-r01c.json").read_text())
    expected = json.loads((root / "configs/dataset/slurp-speech-native-knowledge-opportunity-r01c400-v1.json").read_text())
    receipt = json.loads((root / "docs/receipts/rosters/slurp-knowledge-opportunity-r01c400-v1.json").read_text())
    assert build_runtime_subset(p, seed=20261001, count=400, name=expected["split_name"]) == (expected, receipt)
