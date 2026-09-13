"""Full speech coverage and contact-safe reusable vector preparation."""

import hashlib

import numpy as np
import pytest
import soundfile as sf

from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_speech_queries import (
    segment_plan,
    prepare_text_facet_vectors,
    prepare_speech_query_vectors,
)


def source(tmp_path, *, name="one", frames=250, rate=2):
    path = tmp_path / (name + ".wav")
    sf.write(path, np.zeros(frames, dtype="float32"), rate, subtype="FLOAT")
    return {
        "id": name,
        "media_relpath": path.name,
        "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_frames": frames,
        "source_sample_rate_hz": rate,
    }


def prepare(tmp_path, rows, encoder, **kwargs):
    return prepare_speech_query_vectors(
        tmp_path / "prepared.json",
        rows=rows,
        data_root=tmp_path,
        cache_root=tmp_path / "vectors",
        encoder=encoder,
        encoder_identity={"id": "synthetic-pinned-encoder", "weights": "a" * 64},
        protocol_id="test-full-coverage-v1",
        dimension=2,
        **kwargs,
    )


def test_short_boundary_and_tail_keep_original_frame_coverage():
    assert [(s["start_frame"], s["end_frame"]) for s in segment_plan(240, 2)] == [
        (0, 240)
    ]
    assert [(s["start_frame"], s["end_frame"]) for s in segment_plan(250, 2)] == [
        (0, 240),
        (224, 250),
    ]
    spans = segment_plan(1309, 2)
    assert len(spans) == 6
    assert spans[-1]["end_frame"] == 1309
    assert all(
        b["start_frame"] == a["end_frame"] - 16 for a, b in zip(spans, spans[1:])
    )
    assert [
        (s["start_frame"], s["end_frame"])
        for s in segment_plan(5, 2, max_seconds=1, overlap_seconds=0)
    ] == [(0, 2), (2, 4), (4, 5)]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"frame_count": 0, "sample_rate_hz": 2},
        {"frame_count": 2, "sample_rate_hz": True},
        {"frame_count": 2, "sample_rate_hz": 2, "max_seconds": float("nan")},
        {"frame_count": 2, "sample_rate_hz": 2, "overlap_seconds": 120},
    ],
)
def test_invalid_geometry_refuses(kwargs):
    with pytest.raises(PreparationError):
        segment_plan(**kwargs)


def test_cache_hit_has_zero_encoding_and_keeps_exact_row_contract(tmp_path):
    row = source(tmp_path)
    calls = []
    first = prepare(tmp_path, [row], lambda span: calls.append(span) or [1.0, 0.0])
    assert first["accounting"]["encoder_calls"] == len(calls) == 2
    output = first["artifact"]["output"]
    assert len(output["rows"]) == 1
    assert set(output["rows"][0]) == {
        "id",
        "audio_sha256",
        "source_frames",
        "source_sample_rate_hz",
        "segments",
    }
    assert output["rows"][0]["segments"][1]["vectors"] == {"content": [1.0, 0.0]}
    again = prepare(tmp_path, [row], lambda _: pytest.fail("warm cache encoded"))
    assert again["artifact"] == first["artifact"]
    assert again["accounting"]["encoder_calls"] == 0
    assert again["accounting"]["cache_hits"] == 2


def test_equal_source_spans_deduplicate_across_sample_identities(tmp_path):
    row = source(tmp_path, frames=20)
    alias = dict(row, id="alias")
    calls = []
    result = prepare(
        tmp_path, [row, alias], lambda span: calls.append(span) or [1.0, 0.0]
    )
    rows = result["artifact"]["output"]["rows"]
    assert len(calls) == 1
    assert {r["id"] for r in rows} == {"one", "alias"}
    assert rows[0]["segments"][0]["id"] == rows[1]["segments"][0]["id"]


@pytest.mark.parametrize(
    "mutation",
    [
        lambda r: dict(r, audio_sha256="0" * 64),
        lambda r: dict(r, media_relpath="../outside.wav"),
        lambda r: dict(r, source_frames=r["source_frames"] + 1),
        lambda r: dict(r, gold="forbidden"),
    ],
)
def test_all_source_bindings_are_checked_before_any_encoder_call(tmp_path, mutation):
    one = source(tmp_path, name="one")
    two = source(tmp_path, name="two")
    with pytest.raises(PreparationError):
        prepare(
            tmp_path,
            [one, mutation(two)],
            lambda _: pytest.fail("invalid source encoded"),
        )


def test_duplicate_ids_and_empty_rosters_refuse(tmp_path):
    row = source(tmp_path)
    for rows in [[], [row, row]]:
        with pytest.raises(PreparationError):
            prepare(tmp_path, rows, lambda _: pytest.fail("invalid roster encoded"))


@pytest.mark.parametrize(
    "vector", [[0.0, 0.0], [float("nan"), 1.0], [True, 1.0], [1.0]]
)
def test_invalid_encoder_vector_never_publishes_completed_result(tmp_path, vector):
    row = source(tmp_path, frames=20)
    with pytest.raises(PreparationError):
        prepare(tmp_path, [row], lambda _: vector)
    assert not (tmp_path / "prepared.json").exists()
    with pytest.raises(PreparationError, match="registered attempt"):
        prepare(tmp_path, [row], lambda _: pytest.fail("spent segment replayed"))


def test_interrupted_segment_preserves_completed_sibling_and_refuses_replay(tmp_path):
    row = source(tmp_path)
    calls = []

    def encoder(span):
        calls.append(span["start_frame"])
        if len(calls) == 2:
            raise RuntimeError("synthetic interrupted contact")
        return [1.0, 0.0]

    with pytest.raises(RuntimeError, match="interrupted"):
        prepare(tmp_path, [row], encoder)
    with pytest.raises(PreparationError, match="registered attempt"):
        prepare(tmp_path, [row], lambda _: pytest.fail("automatic replay"))
    assert (
        len(
            [
                p
                for p in (tmp_path / "vectors").glob("*.json")
                if not p.name.endswith(".encoder-started.json")
            ]
        )
        == 1
    )


def test_text_facet_cache_binds_the_retrieval_dimension(tmp_path):
    facets = [{"id": "intent-boundary:alpha", "text": "alpha boundary"}]
    calls = []

    def encoder(text):
        calls.append(text)
        return [1.0, 0.0]

    first = prepare_text_facet_vectors(
        tmp_path / "intent-index.json",
        facets=facets,
        cache_root=tmp_path / "cache",
        encoder=encoder,
        encoder_identity={"id": "synthetic"},
        snapshot_sha256="a" * 64,
        protocol_id="b" * 64,
        dimension=2,
        facet_dimension="intent-boundary",
    )
    second = prepare_text_facet_vectors(
        tmp_path / "content-index.json",
        facets=facets,
        cache_root=tmp_path / "cache",
        encoder=encoder,
        encoder_identity={"id": "synthetic"},
        snapshot_sha256="a" * 64,
        protocol_id="b" * 64,
        dimension=2,
    )

    assert calls == ["alpha boundary", "alpha boundary"]
    assert first["artifact"]["output"]["rows"][0]["vectors"] == {
        "intent-boundary": [1.0, 0.0]
    }
    assert second["artifact"]["output"]["rows"][0]["vectors"] == {"content": [1.0, 0.0]}
