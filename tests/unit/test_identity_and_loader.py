"""E0 D1/D4 substrate: identity layers and the deterministic boundary-safe loader."""

import hashlib

import pytest

from speech_aware_evidence_acquisition.data.identity import (
    IdentityError,
    audio2tool_layers,
    earnings21_layers,
    earnings22_layers,
    conec_layers,
    relation,
    require_equal,
    slurp_layers,
)
from speech_aware_evidence_acquisition.data.loader import (
    LoaderError,
    earnings22_subset10_ids,
    load_earnings22,
    materialize,
)
from speech_aware_evidence_acquisition.data.lock import load_lock

from conftest import E21_IDS, E22_IDS, SUBSET10_IDS


class TestIdentityLayers:
    def test_layers_enumerate_same_identity(self, synthetic_world):
        e21 = earnings21_layers(synthetic_world.e21)
        assert all(layer.ids == tuple(sorted(E21_IDS)) for layer in e21.values())
        e22 = earnings22_layers(synthetic_world.e22)
        assert e22["media"].ids == tuple(sorted(E22_IDS))
        assert e22["subset10_media"].ids == tuple(sorted(SUBSET10_IDS))
        conec = conec_layers(synthetic_world.conec)
        for layer in conec.values():
            require_equal(e21["media"], layer)

    def test_missing_layer_file_breaks_identity(self, synthetic_world):
        (synthetic_world.e21 / "transcripts" / "nlp_references" / f"{E21_IDS[0]}.nlp").unlink()
        e21 = earnings21_layers(synthetic_world.e21)
        with pytest.raises(IdentityError, match="invariant violated"):
            require_equal(e21["media"], e21["nlp_references"])

    def test_stray_non_layer_file_is_visible_not_silent(self, synthetic_world):
        stray = (
            synthetic_world.conec
            / "earnings21"
            / "transcripts"
            / "timestamps"
            / "stray_aux_file.jsonl.gz"
        )
        stray.write_text("aux", encoding="utf-8")
        layers = conec_layers(synthetic_world.conec)
        assert layers["e21_timestamps"].extras == ("stray_aux_file.jsonl.gz",)
        assert layers["e21_timestamps"].ids == tuple(sorted(E21_IDS))

    def test_duplicate_metadata_id_fails_closed(self, synthetic_world):
        metadata = synthetic_world.e21 / "earnings21-file-metadata.csv"
        metadata.write_text(
            "file_id,audio_length,sample_rate\n4000001,1,16000\n4000001,2,16000\n",
            encoding="utf-8",
        )
        with pytest.raises(IdentityError, match="duplicate"):
            earnings21_layers(synthetic_world.e21)

    def test_relation_reports_direction(self, synthetic_world):
        e22 = earnings22_layers(synthetic_world.e22)
        facts = relation(e22["subset10_media"], e22["media"])
        assert facts["relation"] == "left_subset_of_right"
        assert facts["right_only_count"] == len(E22_IDS) - len(SUBSET10_IDS)


class TestLoader:
    def test_deterministic_sorted_load(self, synthetic_world):
        lock = load_lock(synthetic_world.lock_path)
        samples = load_earnings22(lock, synthetic_world.data_root)
        assert [sample.sample_id for sample in samples] == sorted(E22_IDS)
        assert samples[0].media_relpath.startswith("datasets/earnings21-22/earnings22/media/")

    def test_runtime_view_passes_boundary_and_carries_no_reference_fields(
        self, synthetic_world
    ):
        lock = load_lock(synthetic_world.lock_path)
        sample = load_earnings22(lock, synthetic_world.data_root)[0]
        view = sample.runtime_view()
        assert view["speech_ref"] == f"earnings22-original/{sample.sample_id}"
        assert not any("transcript" in key or "reference" in key for key in view)

    def test_media_metadata_drift_fails_closed(self, synthetic_world):
        (synthetic_world.e22 / "media" / f"{E22_IDS[0]}.mp3").unlink()
        lock = load_lock(synthetic_world.lock_path)
        with pytest.raises(LoaderError, match="identity drift"):
            load_earnings22(lock, synthetic_world.data_root)

    def test_subset10_is_exactly_ten(self, synthetic_world):
        lock = load_lock(synthetic_world.lock_path)
        assert earnings22_subset10_ids(lock, synthetic_world.data_root) == sorted(SUBSET10_IDS)
        (synthetic_world.e22 / "subset10" / "media" / f"{SUBSET10_IDS[0]}.mp3").unlink()
        with pytest.raises(LoaderError, match="exactly 10"):
            earnings22_subset10_ids(lock, synthetic_world.data_root)

    def test_materialize_measures_real_bytes(self, synthetic_world):
        lock = load_lock(synthetic_world.lock_path)
        sample = load_earnings22(lock, synthetic_world.data_root)[0]
        measured = materialize(sample, synthetic_world.data_root)
        media = synthetic_world.data_root / sample.media_relpath
        assert measured.media_bytes == media.stat().st_size
        assert len(measured.media_sha256) == 64


def test_load_earnings21_returns_identity_checked_samples(synthetic_world):
    from speech_aware_evidence_acquisition.data.loader import load_earnings21
    from speech_aware_evidence_acquisition.data.lock import load_lock

    lock = load_lock(synthetic_world.lock_path)
    samples = load_earnings21(lock, synthetic_world.data_root)
    assert [s.sample_id for s in samples] == sorted(s.sample_id for s in samples)
    assert len(samples) == 3
    first = samples[0]
    assert first.carrier_lock_key == "earnings21-original"
    assert first.media_relpath.endswith(f"media/{first.sample_id}.mp3")
    assert first.audio_seconds == 100.5
    assert first.sample_rate_hz == 16000
    assert first.runtime_view()["speech_ref"] == f"earnings21-original/{first.sample_id}"


def test_load_earnings21_fails_closed_on_identity_drift(synthetic_world):
    import pytest

    from speech_aware_evidence_acquisition.data.loader import LoaderError, load_earnings21
    from speech_aware_evidence_acquisition.data.lock import load_lock

    (synthetic_world.e21 / "media" / "9999999.mp3").write_text("orphan", encoding="utf-8")
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(LoaderError, match="identity drift"):
        load_earnings21(lock, synthetic_world.data_root)


class TestBoundedDiscoveryProbeMediaLayers:
    """SLURP/Audio2Tool D1 media-identity layers (2026-08-15 owner amendment):
    single-layer, fresh on-disk re-hash only -- see ``data.identity`` module
    docstring and ``slurp_layers``/``audio2tool_layers`` own docstrings for
    the scope this deliberately narrows to (vs. the three core carriers'
    multi-layer cross-check)."""

    def test_slurp_layers_cover_devel_in_full(self, slurp_world):
        lock = load_lock(slurp_world.lock_path)
        layers = slurp_layers(lock, slurp_world.data_root)
        assert set(layers) == {"media"}
        assert layers["media"].ids == (
            "slurp:devel:000101:audio-101",
            "slurp:devel:000101:audio-101-headset",
            "slurp:devel:000102:audio-102",
        )
        for fact in layers["media"].files.values():
            assert fact.bytes > 0
            assert len(fact.sha256) == 64

    def test_slurp_layers_hash_matches_real_bytes_on_disk(self, slurp_world):
        lock = load_lock(slurp_world.lock_path)
        layers = slurp_layers(lock, slurp_world.data_root)
        sample_id = "slurp:devel:000102:audio-102"
        media_path = slurp_world.audio_root / "slurp_real" / "audio-102.flac"
        fact = layers["media"].files[sample_id]
        assert fact.bytes == media_path.stat().st_size
        assert fact.sha256 == hashlib.sha256(media_path.read_bytes()).hexdigest()

    def test_slurp_layers_fails_closed_on_missing_flac(self, slurp_world):
        from speech_aware_evidence_acquisition.data.loader import LoaderError

        (slurp_world.audio_root / "slurp_real" / "audio-102.flac").unlink()
        lock = load_lock(slurp_world.lock_path)
        with pytest.raises(LoaderError, match="media missing"):
            slurp_layers(lock, slurp_world.data_root)

    def test_slurp_layers_other_split_ids_are_addressable_too(self, slurp_world):
        lock = load_lock(slurp_world.lock_path)
        layers = slurp_layers(lock, slurp_world.data_root, split_id="train")
        assert layers["media"].ids == (
            "slurp:train:000301:audio-301",
            "slurp:train:000302:audio-302",
        )

    def test_audio2tool_layers_cover_exactly_the_frozen_receipt(self, audio2tool_world):
        lock = load_lock(audio2tool_world.lock_path)
        layers = audio2tool_layers(
            lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )
        assert set(layers) == {"media"}
        assert layers["media"].ids == (
            "tier1_direct:000001",
            "tier3_multi_intent:000004",
            "tier7_multiturn:000009",
        )

    def test_audio2tool_layers_hash_matches_real_bytes_on_disk(self, audio2tool_world):
        lock = load_lock(audio2tool_world.lock_path)
        layers = audio2tool_layers(
            lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
        )
        media_path = audio2tool_world.public / "tier1_direct_audios" / "query_00001" / "turn.wav"
        fact = layers["media"].files["tier1_direct:000001"]
        assert fact.bytes == media_path.stat().st_size
        assert fact.sha256 == hashlib.sha256(media_path.read_bytes()).hexdigest()

    def test_audio2tool_layers_fails_closed_on_missing_wav(self, audio2tool_world):
        (
            audio2tool_world.public / "tier1_direct_audios" / "query_00001" / "turn.wav"
        ).unlink()
        lock = load_lock(audio2tool_world.lock_path)
        with pytest.raises(Exception, match="tier1_direct:000001"):
            audio2tool_layers(
                lock, audio2tool_world.data_root, repo_root=audio2tool_world.repo_root
            )
