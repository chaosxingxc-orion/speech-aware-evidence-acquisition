"""E0 D1/D4 substrate: identity layers and the deterministic boundary-safe loader."""

import pytest

from speech_aware_evidence_acquisition.data.identity import (
    IdentityError,
    earnings21_layers,
    earnings22_layers,
    conec_layers,
    relation,
    require_equal,
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
