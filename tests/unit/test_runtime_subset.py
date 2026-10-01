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
