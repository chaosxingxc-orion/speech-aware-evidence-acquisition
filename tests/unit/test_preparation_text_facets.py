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
        tmp_path / "set.json",
        facets=[{"id": "facet:b", "text": "beta"}, {"id": "facet:a", "text": "alpha"}],
        cache_root=tmp_path / "cache",
        encoder=lambda text: calls.append(text) or [1.0, 0.0],
        encoder_identity={"inventory_sha256": _SHA},
        snapshot_sha256=_SHA,
        protocol_id="b" * 64,
        dimension=2,
    )
    assert calls == ["alpha", "beta"]
    rows = result["artifact"]["output"]["rows"]
    exported = b"".join(
        json.dumps(row, sort_keys=True).encode() + b"\n" for row in rows
    )
    path = tmp_path / "facets.jsonl"
    path.write_bytes(exported)
    import hashlib

    assert list(
        load_sealed_vectors(
            path,
            expected_sha256=hashlib.sha256(exported).hexdigest(),
            dimensions=("content",),
        )
    ) == ["facet:a", "facet:b"]
    second = prepare_text_facet_vectors(
        tmp_path / "set.json",
        facets=[{"id": "facet:b", "text": "beta"}, {"id": "facet:a", "text": "alpha"}],
        cache_root=tmp_path / "cache",
        encoder=lambda _: pytest.fail("warm cache called"),
        encoder_identity={"inventory_sha256": _SHA},
        snapshot_sha256=_SHA,
        protocol_id="b" * 64,
        dimension=2,
    )
    assert second["accounting"]["encoder_calls"] == 0


@pytest.mark.parametrize(
    "facets",
    [
        [],
        [{"id": "x", "text": ""}],
        [{"id": "x", "text": "a"}, {"id": "x", "text": "b"}],
    ],
)
def test_text_facet_shape_refuses_before_encoder(tmp_path, facets):
    with pytest.raises(PreparationError):
        prepare_text_facet_vectors(
            tmp_path / "set.json",
            facets=facets,
            cache_root=tmp_path / "cache",
            encoder=lambda _: pytest.fail("encoder called"),
            encoder_identity={"inventory_sha256": _SHA},
            snapshot_sha256=_SHA,
            protocol_id="b" * 64,
            dimension=2,
        )


def test_passage_backend_uses_no_audio_and_emits_processor_forward_hooks(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core import (
        speech_preparation_runtime as runtime,
    )

    events, rendered, calls = [], [], []
    (tmp_path / "model").mkdir()
    monkeypatch.setattr(
        runtime,
        "load_stack",
        lambda *_args, **_kwargs: ("processor", "model", "template"),
    )
    monkeypatch.setattr(
        runtime, "render", lambda _p, _t, content: rendered.append(content) or "wire"
    )

    def fake_encode(_p, _m, texts, audio, **kwargs):
        calls.append((texts, audio, kwargs))
        kwargs["forward_event"]("encoder_forward_started")
        kwargs["forward_event"]("encoder_forward_finished")
        return [[1.0, 0.0]]

    monkeypatch.setattr(runtime, "encode", fake_encode)
    backend = runtime.NemotronPassageEncoder(
        {"model_dir_relpath": "model"},
        {"passage_prompt": "passage: ", "max_sequence_tokens": 8192},
        tmp_path,
        events.append,
    )
    assert backend("facet text") == [1.0, 0.0]
    assert rendered == [[{"type": "text", "text": "passage: facet text"}]]
    assert calls == [
        (["wire"], None, {"max_sequence_tokens": 8192, "forward_event": events.append})
    ]
    assert events == [
        "model_load_started",
        "model_load_finished",
        "processor_started",
        "encoder_forward_started",
        "encoder_forward_finished",
    ]


@pytest.mark.parametrize("bad_vector", [[0.0, 0.0], [float("nan"), 1.0], [1.0]])
def test_bad_encoded_vectors_remain_spent_and_unpublished(tmp_path, bad_vector):
    with pytest.raises(PreparationError):
        prepare_text_facet_vectors(
            tmp_path / "set.json",
            facets=[{"id": "facet", "text": "positive evidence"}],
            cache_root=tmp_path / "cache",
            encoder=lambda _: bad_vector,
            encoder_identity={"inventory_sha256": _SHA},
            snapshot_sha256=_SHA,
            protocol_id="b" * 64,
            dimension=2,
        )
    assert not (tmp_path / "set.json").exists()
    assert len(list((tmp_path / "cache").glob("*.encoder-started.json"))) == 1


def test_changed_text_cannot_reuse_the_previous_sealed_set(tmp_path):
    args = dict(
        path=tmp_path / "set.json",
        cache_root=tmp_path / "cache",
        encoder_identity={"inventory_sha256": _SHA},
        snapshot_sha256=_SHA,
        protocol_id="b" * 64,
        dimension=2,
    )
    prepare_text_facet_vectors(
        **args,
        facets=[{"id": "facet", "text": "original evidence"}],
        encoder=lambda _: [1.0, 0.0],
    )
    with pytest.raises(PreparationError, match="identity"):
        prepare_text_facet_vectors(
            **args,
            facets=[{"id": "facet", "text": "changed evidence"}],
            encoder=lambda _: pytest.fail("mismatched set reached encoder"),
        )
