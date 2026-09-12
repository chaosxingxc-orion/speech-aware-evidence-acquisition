import json

import pytest

from speech_aware_evidence_acquisition.core.preparation_speech_queries import (
    PreparationError,
    prepare_text_facet_vectors,
)
from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_vectors


_SHA = "a" * 64


def test_text_facets_are_cached_sorted_and_loader_compatible(tmp_path):
    calls = []
    result = prepare_text_facet_vectors(
        tmp_path / "set.json", facets=[{"id": "facet:b", "text": "beta"}, {"id": "facet:a", "text": "alpha"}],
        cache_root=tmp_path / "cache", encoder=lambda text: calls.append(text) or [1.0, 0.0],
        encoder_identity={"inventory_sha256": _SHA}, snapshot_sha256=_SHA,
        protocol_id="b" * 64, dimension=2,
    )
    assert calls == ["alpha", "beta"]
    rows = result["artifact"]["output"]["rows"]
    exported = b"".join(json.dumps(row, sort_keys=True).encode() + b"\n" for row in rows)
    path = tmp_path / "facets.jsonl"
    path.write_bytes(exported)
    import hashlib
    assert list(load_sealed_vectors(path, expected_sha256=hashlib.sha256(exported).hexdigest(), dimensions=("content",))) == ["facet:a", "facet:b"]
    second = prepare_text_facet_vectors(
        tmp_path / "set.json", facets=[{"id": "facet:b", "text": "beta"}, {"id": "facet:a", "text": "alpha"}],
        cache_root=tmp_path / "cache", encoder=lambda _: pytest.fail("warm cache called"),
        encoder_identity={"inventory_sha256": _SHA}, snapshot_sha256=_SHA,
        protocol_id="b" * 64, dimension=2,
    )
    assert second["accounting"]["encoder_calls"] == 0


@pytest.mark.parametrize("facets", [[], [{"id": "x", "text": ""}], [{"id": "x", "text": "a"}, {"id": "x", "text": "b"}]])
def test_text_facet_shape_refuses_before_encoder(tmp_path, facets):
    with pytest.raises(PreparationError):
        prepare_text_facet_vectors(tmp_path / "set.json", facets=facets, cache_root=tmp_path / "cache",
            encoder=lambda _: pytest.fail("encoder called"), encoder_identity={"inventory_sha256": _SHA},
            snapshot_sha256=_SHA, protocol_id="b" * 64, dimension=2)
