"""``rails.probes.pemb_flight``: the P-EMB two-run embedding flight
orchestration (docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md).
Engineering-only, ZERO live model contact -- every test here drives
``rails.embedding_client.MockEmbeddingClient``.
"""

from __future__ import annotations

import math

import pytest

from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import Audio2ToolAdapter
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.embedding_client import (
    EMBEDDING_DIM,
    EmbeddingVector,
    MockEmbeddingClient,
    deterministic_unit_vector,
)
from speech_aware_evidence_acquisition.rails.probes.pemb_flight import (
    EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
    EXPECTED_RUN_B_SPLIT_IDENTITY_HASH,
    RUN_A_AUDIO_N,
    RUN_A_ID,
    RUN_A_LABEL_N,
    RUN_A_TOTAL_N,
    RUN_B_AUDIO_N,
    RUN_B_ID,
    RUN_B_ROW_N,
    RUN_B_TOTAL_N,
    LoadedEmbeddingManifest,
    PembFlightError,
    PembRunSummary,
    _assert_this_module_never_calls_ontology_miner,
    _safe_filename,
    assert_run_a_split_identity_hash,
    assert_run_b_split_identity_hash,
    load_embedding_manifest,
    run_pemb1_flight,
    run_pemb2_flight,
    write_embedding_manifest,
)


def _slurp_adapter(world) -> SlurpAdapter:
    return SlurpAdapter(load_lock(world.lock_path), world.data_root)


def _a2t_adapter(world) -> Audio2ToolAdapter:
    return Audio2ToolAdapter(load_lock(world.lock_path), world.data_root, repo_root=world.repo_root)


# ---------------------------------------------------------------------------
# Registered constants -- the fail-closed 60+18=78 / 400+152=552 counts.
# ---------------------------------------------------------------------------


def test_registered_totals():
    assert RUN_A_AUDIO_N == 60
    assert RUN_A_LABEL_N == 18
    assert RUN_A_TOTAL_N == 78
    assert RUN_B_AUDIO_N == 400
    assert RUN_B_ROW_N == 152
    assert RUN_B_TOTAL_N == 552


# ---------------------------------------------------------------------------
# Split-identity pins.
# ---------------------------------------------------------------------------


def test_assert_run_a_split_identity_hash_accepts_the_pin():
    assert_run_a_split_identity_hash(EXPECTED_RUN_A_SPLIT_IDENTITY_HASH)  # does not raise


def test_assert_run_a_split_identity_hash_rejects_drift():
    with pytest.raises(PembFlightError, match="does not match the pinned"):
        assert_run_a_split_identity_hash("deadbeef" * 8)


def test_assert_run_b_split_identity_hash_accepts_the_pin():
    assert_run_b_split_identity_hash(EXPECTED_RUN_B_SPLIT_IDENTITY_HASH)  # does not raise


def test_assert_run_b_split_identity_hash_rejects_drift():
    with pytest.raises(PembFlightError, match="does not match the pinned"):
        assert_run_b_split_identity_hash("deadbeef" * 8)


# ---------------------------------------------------------------------------
# The ontology-miner call guard.
# ---------------------------------------------------------------------------


def test_module_never_calls_ontology_miner_on_its_own_real_source():
    _assert_this_module_never_calls_ontology_miner()  # does not raise


def test_ontology_miner_guard_trips_on_a_synthetic_reference():
    with pytest.raises(PembFlightError, match="load_slurp_ontology"):
        _assert_this_module_never_calls_ontology_miner("from ...data.slurp import load_slurp_ontology\n")


# ---------------------------------------------------------------------------
# Run A: run_pemb1_flight.
# ---------------------------------------------------------------------------


def test_run_pemb1_flight_happy_path(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    # 3 samples in the synthetic world: two recordings for slurp_id 101
    # (iot) + one for slurp_id 102 (email) -- data.slurp._parse_record
    # yields one SlurpRecord per recording, not per slurp_id.
    samples = adapter.load_split("devel")
    labels = ("email", "iot")
    client = MockEmbeddingClient()

    summary = run_pemb1_flight(
        client=client,
        samples=samples,
        canonical_labels=labels,
        split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
        data_root=slurp_world.data_root,
        expected_audio_n=3,
        expected_label_n=2,
    )

    assert summary.run_id == RUN_A_ID
    assert len(summary.audio_vectors) == 3
    assert len(summary.text_vectors) == 2
    assert {v.contact_id for v in summary.audio_vectors} == {s.sample_id for s in samples}
    assert {v.contact_id for v in summary.text_vectors} == set(labels)
    assert client.marker_verified is True
    # Marker verified BEFORE any embed contact (MockEmbeddingClient refuses
    # embed_* until verify_media_marker() ran -- a successful flight is
    # itself the proof of ordering).
    assert client.calls[0][0] in ("audio", "text")


def test_run_pemb1_flight_rejects_wrong_split_identity_hash(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(PembFlightError, match="split_identity_hash"):
        run_pemb1_flight(
            client=client,
            samples=samples,
            canonical_labels=("email", "iot"),
            split_identity_hash="not-the-pin",
            data_root=slurp_world.data_root,
            expected_audio_n=3,
            expected_label_n=2,
        )
    assert client.calls == []  # refused before any contact


def test_run_pemb1_flight_rejects_wrong_audio_count(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(PembFlightError, match="60"):
        run_pemb1_flight(
            client=client,
            samples=samples,
            canonical_labels=("email", "iot"),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            # expected_audio_n left at the real default (60) -- only 2 samples given
            expected_label_n=2,
        )


def test_run_pemb1_flight_rejects_wrong_label_count(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(PembFlightError, match="canonical label"):
        run_pemb1_flight(
            client=client,
            samples=samples,
            canonical_labels=("email",),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_audio_n=3,
            expected_label_n=2,
        )


def test_run_pemb1_flight_rejects_duplicate_labels(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(PembFlightError, match="duplicate canonical label"):
        run_pemb1_flight(
            client=client,
            samples=samples,
            canonical_labels=("iot", "iot"),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_audio_n=3,
            expected_label_n=2,
        )


def test_run_pemb1_flight_rejects_a_padded_label(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(PembFlightError, match="bare"):
        run_pemb1_flight(
            client=client,
            samples=samples,
            canonical_labels=(" iot", "email"),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_audio_n=3,
            expected_label_n=2,
        )


def test_run_pemb1_flight_rejects_duplicate_sample_ids(slurp_world):
    adapter = _slurp_adapter(slurp_world)
    samples = adapter.load_split("devel")
    client = MockEmbeddingClient()
    with pytest.raises(PembFlightError, match="duplicate sample_id"):
        run_pemb1_flight(
            client=client,
            samples=[samples[0], samples[0]],
            canonical_labels=("email", "iot"),
            split_identity_hash=EXPECTED_RUN_A_SPLIT_IDENTITY_HASH,
            data_root=slurp_world.data_root,
            expected_audio_n=2,
            expected_label_n=2,
        )


# ---------------------------------------------------------------------------
# Run B: run_pemb2_flight.
# ---------------------------------------------------------------------------


def test_run_pemb2_flight_happy_path(audio2tool_world):
    adapter = _a2t_adapter(audio2tool_world)
    samples = adapter.load_split("discovery")  # 3 samples in the synthetic world
    rows = load_tool_registry(load_lock(audio2tool_world.lock_path), audio2tool_world.data_root)  # 2 rows
    client = MockEmbeddingClient()

    summary = run_pemb2_flight(
        client=client,
        samples=samples,
        registry_rows=rows,
        split_identity_hash=EXPECTED_RUN_B_SPLIT_IDENTITY_HASH,
        data_root=audio2tool_world.data_root,
        expected_audio_n=3,
        expected_row_n=2,
    )

    assert summary.run_id == RUN_B_ID
    assert len(summary.audio_vectors) == 3
    assert len(summary.text_vectors) == 2
    assert {v.contact_id for v in summary.text_vectors} == {row["tool_name"] for row in rows}
    assert client.marker_verified is True


def test_run_pemb2_flight_rejects_wrong_split_identity_hash(audio2tool_world):
    adapter = _a2t_adapter(audio2tool_world)
    samples = adapter.load_split("discovery")
    rows = load_tool_registry(load_lock(audio2tool_world.lock_path), audio2tool_world.data_root)
    client = MockEmbeddingClient()
    with pytest.raises(PembFlightError, match="split_identity_hash"):
        run_pemb2_flight(
            client=client,
            samples=samples,
            registry_rows=rows,
            split_identity_hash="not-the-pin",
            data_root=audio2tool_world.data_root,
            expected_audio_n=3,
            expected_row_n=2,
        )
    assert client.calls == []


def test_run_pemb2_flight_rejects_duplicate_tool_names(audio2tool_world):
    adapter = _a2t_adapter(audio2tool_world)
    samples = adapter.load_split("discovery")
    rows = load_tool_registry(load_lock(audio2tool_world.lock_path), audio2tool_world.data_root)
    client = MockEmbeddingClient()
    with pytest.raises(PembFlightError, match="duplicate tool_name"):
        run_pemb2_flight(
            client=client,
            samples=samples,
            registry_rows=[rows[0], rows[0]],
            split_identity_hash=EXPECTED_RUN_B_SPLIT_IDENTITY_HASH,
            data_root=audio2tool_world.data_root,
            expected_audio_n=3,
            expected_row_n=2,
        )


def test_run_pemb2_flight_rejects_wrong_audio_count(audio2tool_world):
    adapter = _a2t_adapter(audio2tool_world)
    samples = adapter.load_split("discovery")
    rows = load_tool_registry(load_lock(audio2tool_world.lock_path), audio2tool_world.data_root)
    client = MockEmbeddingClient()
    with pytest.raises(PembFlightError, match="400"):
        run_pemb2_flight(
            client=client,
            samples=samples,
            registry_rows=rows,
            split_identity_hash=EXPECTED_RUN_B_SPLIT_IDENTITY_HASH,
            data_root=audio2tool_world.data_root,
            # expected_audio_n left at the real default (400) -- only 3 samples given
            expected_row_n=2,
        )


# ---------------------------------------------------------------------------
# _safe_filename.
# ---------------------------------------------------------------------------


def test_safe_filename_sanitizes_colons_and_stays_stable():
    assert _safe_filename("slurp:devel:000101:audio-101") == "slurp_devel_000101_audio-101"
    assert _safe_filename("tier1_direct:000077") == "tier1_direct_000077"
    assert _safe_filename("setLighting") == "setLighting"


# ---------------------------------------------------------------------------
# write_embedding_manifest / load_embedding_manifest round trip.
# ---------------------------------------------------------------------------


def _summary(run_id: str) -> PembRunSummary:
    audio = (
        EmbeddingVector(contact_id="slurp:devel:000101:audio-101", kind="audio", values=deterministic_unit_vector("a1")),
        EmbeddingVector(contact_id="slurp:devel:000102:audio-102", kind="audio", values=deterministic_unit_vector("a2")),
    )
    text = (
        EmbeddingVector(contact_id="iot", kind="text", values=deterministic_unit_vector("t1")),
        EmbeddingVector(contact_id="email", kind="text", values=deterministic_unit_vector("t2")),
    )
    return PembRunSummary(run_id=run_id, audio_vectors=audio, text_vectors=text)


def test_write_and_load_embedding_manifest_round_trip(tmp_path):
    summary = _summary("SAEA-PROBE-pemb1-78")
    manifest_path = write_embedding_manifest(tmp_path, summary)
    assert manifest_path.is_file()

    loaded = load_embedding_manifest(tmp_path, "SAEA-PROBE-pemb1-78")
    assert isinstance(loaded, LoadedEmbeddingManifest)
    assert set(loaded.audio.keys()) == {v.contact_id for v in summary.audio_vectors}
    assert set(loaded.text.keys()) == {v.contact_id for v in summary.text_vectors}
    for vector in summary.audio_vectors:
        assert loaded.audio[vector.contact_id].shape == (EMBEDDING_DIM,)
        assert list(loaded.audio[vector.contact_id]) == pytest.approx(list(vector.values))


def test_write_embedding_manifest_refuses_filename_collision(tmp_path):
    # "a:b" and "a_b" both sanitize to "a_b" under the same kind.
    audio = (
        EmbeddingVector(contact_id="a:b", kind="audio", values=deterministic_unit_vector("x1")),
        EmbeddingVector(contact_id="a_b", kind="audio", values=deterministic_unit_vector("x2")),
    )
    summary = PembRunSummary(run_id="collision-test", audio_vectors=audio, text_vectors=())
    with pytest.raises(PembFlightError, match="collision"):
        write_embedding_manifest(tmp_path, summary)


def test_load_embedding_manifest_missing_directory_fails_closed(tmp_path):
    with pytest.raises(PembFlightError, match="missing"):
        load_embedding_manifest(tmp_path, "no-such-run")


def test_load_embedding_manifest_fails_closed_on_sha256_tamper(tmp_path):
    summary = _summary("tamper-test")
    write_embedding_manifest(tmp_path, summary)
    vector_path = tmp_path / "derived" / "embeddings" / "tamper-test" / "audio" / "slurp_devel_000101_audio-101.npy"
    assert vector_path.is_file()
    vector_path.write_bytes(b"corrupted-bytes-not-a-valid-npy-and-wrong-hash")
    with pytest.raises(PembFlightError, match="sha256 mismatch"):
        load_embedding_manifest(tmp_path, "tamper-test")


def test_load_embedding_manifest_fails_closed_on_schema_mismatch(tmp_path):
    summary = _summary("schema-test")
    manifest_path = write_embedding_manifest(tmp_path, summary)
    import json

    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["schema"] = "wrong-schema"
    manifest_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PembFlightError, match="schema"):
        load_embedding_manifest(tmp_path, "schema-test")


def test_load_embedding_manifest_fails_closed_on_non_finite_stored_vector(tmp_path):
    values = list(deterministic_unit_vector("nan-case"))
    values[0] = math.nan
    audio = (EmbeddingVector(contact_id="s1", kind="audio", values=tuple(values)),)
    summary = PembRunSummary(run_id="nan-test", audio_vectors=audio, text_vectors=())
    write_embedding_manifest(tmp_path, summary)
    # write_embedding_manifest itself performs no finiteness check (that is
    # EmbeddingClient's own job, at contact time) -- the LOADER re-checks
    # independently regardless of what the flight already validated.
    with pytest.raises(PembFlightError, match="non-finite"):
        load_embedding_manifest(tmp_path, "nan-test")
