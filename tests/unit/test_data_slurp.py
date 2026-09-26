"""``data.slurp.load_slurp_ontology``'s ``include_synthetic`` flag (2026-08-17
fix): the shipped ontology miner used to fold ``train_synthetic.jsonl`` into
every roster unconditionally, which is ceiling-tier for a devel-split probe
(64.8% verbatim devel overlap, measured on the real corpus and recorded in
``configs/probes/g0-binding/pslu-rosters-train-only.json``'s own
``train_synthetic_refused`` block). This module asserts the DEFAULT excludes
``train_synthetic`` and that ``include_synthetic=True`` remains an available,
explicit opt-in.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.slurp import (
    _missing_media_paths,
    _prefetch_audio_seconds,
    load_slurp_ontology,
    load_slurp_split,
    load_slurp_train_material,
)


def test_media_existence_validation_uses_a_bounded_parallel_worker_pool():
    lock = threading.Lock()
    active = 0
    peak = 0

    def probe(_path):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return True

    missing = _missing_media_paths(
        tuple(Path(f"audio-{index}.flac") for index in range(8)),
        workers=4,
        probe=probe,
    )
    assert missing == ()
    assert 2 <= peak <= 4


def test_default_excludes_train_synthetic(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    ontology = load_slurp_ontology(lock, slurp_world.data_root)
    # The fixture's only train_synthetic record is scenario="alarm",
    # action="set", entity type="time"/filler="six" -- absent from train.jsonl.
    assert "alarm" not in ontology.scenarios
    assert "time" not in ontology.entity_types
    # train.jsonl's own facts are still present.
    assert "iot" in ontology.scenarios
    assert "weather" in ontology.scenarios
    assert "house_place" in ontology.entity_types
    assert ontology.entity_types["house_place"] == ("kitchen",)


def test_include_synthetic_true_folds_train_synthetic_back_in(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    ontology = load_slurp_ontology(lock, slurp_world.data_root, include_synthetic=True)
    assert "alarm" in ontology.scenarios
    assert "time" in ontology.entity_types
    assert "six" in ontology.entity_types["time"]
    # train.jsonl's own facts are still present alongside the synthetic ones.
    assert "iot" in ontology.scenarios
    assert "house_place" in ontology.entity_types


def test_default_and_explicit_false_agree(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    default_ontology = load_slurp_ontology(lock, slurp_world.data_root)
    explicit_ontology = load_slurp_ontology(lock, slurp_world.data_root, include_synthetic=False)
    assert default_ontology == explicit_ontology


def test_train_material_exposes_auditable_text_audio_and_speaker_provenance(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    material = load_slurp_train_material(lock, slurp_world.data_root)
    assert [entry.scenario for entry in material] == ["iot", "weather"]
    assert material[0].sentence == "dim the lights in the kitchen"
    assert material[0].entity_types == ("house_place",)
    assert material[1].entity_types == ()
    assert material[0].recordings[0].sample_id == "slurp:train:000301:audio-301"
    assert material[0].recordings[0].speaker_id == "speaker-train-a"
    assert material[0].recordings[0].media_relpath.endswith("/slurp_real/audio-301.flac")


def test_train_material_refuses_missing_speaker_identity(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    metadata_path = slurp_world.metadata_dir / "metadata.json"
    metadata_path.write_text("{}", encoding="utf-8")
    with pytest.raises(Exception, match="speaker identity"):
        load_slurp_train_material(lock, slurp_world.data_root)


def test_train_material_refuses_a_malformed_entity_type(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    metadata_path = slurp_world.metadata_dir / "train.jsonl"
    rows = [
        json.loads(line)
        for line in metadata_path.read_text(encoding="utf-8").splitlines()
    ]
    rows[0]["entities"] = [{"span": [5], "type": ""}]
    metadata_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="entity type"):
        load_slurp_train_material(lock, slurp_world.data_root)


# ---------------------------------------------------------------------------
# The flac-header prefetch (2026-09-26). load_slurp_split re-verifies EVERY
# recording against its flac header -- 50,628 files for the real ``train``, all
# of it waiting on the filesystem -- so the probe is now a bounded thread pool.
# What it must never change: the records, their durations, or any refusal.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("workers", [1, 2, 4, 8])
def test_load_slurp_split_is_worker_count_invariant(slurp_world, workers):
    lock = load_lock(slurp_world.lock_path)
    reference = load_slurp_split(lock, slurp_world.data_root, "devel", workers=1)
    measured = load_slurp_split(lock, slurp_world.data_root, "devel", workers=workers)
    assert measured == reference
    assert [record.sample_id for record in measured] == [
        record.sample_id for record in reference
    ]
    assert [record.audio_seconds for record in measured] == [
        record.audio_seconds for record in reference
    ]


def test_prefetch_returns_the_same_durations_as_the_serial_probe(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    serial = {
        Path(record.media_relpath).name: record.audio_seconds
        for record in load_slurp_split(lock, slurp_world.data_root, "devel", workers=1)
    }
    rows = [
        json.loads(line)
        for line in (slurp_world.metadata_dir / "devel.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    prefetched = _prefetch_audio_seconds(
        rows, slurp_world.audio_root / "slurp_real", workers=4
    )
    assert prefetched, "the prefetch resolved nothing"
    for path, seconds in prefetched.items():
        if path.name in serial:
            assert seconds == serial[path.name], path


def test_prefetch_is_best_effort_and_never_raises(tmp_path):
    """A missing or unreadable file is simply left out, so the serial parse
    still raises the real LoaderError itself, for the same file, in order."""

    rows = [{"recordings": [{"file": "does-not-exist.flac"},
                            {"file": "also-missing.flac"}]}]
    assert _prefetch_audio_seconds(rows, tmp_path, workers=4) == {}


@pytest.mark.parametrize("workers", [1, 4])
def test_a_missing_recording_still_refuses_identically(slurp_world, workers):
    """The prefetch swallows its own failures, so the SERIAL parse is still
    what raises -- at both worker counts, with the same message."""

    lock = load_lock(slurp_world.lock_path)
    records = load_slurp_split(lock, slurp_world.data_root, "devel", workers=1)
    victim = slurp_world.data_root / records[0].media_relpath
    assert victim.is_file()
    victim.unlink()
    with pytest.raises(Exception, match="media missing"):
        load_slurp_split(lock, slurp_world.data_root, "devel", workers=workers)


def test_prefetch_skips_malformed_recording_entries(tmp_path):
    rows = [
        {"recordings": "not-a-list"},
        {"recordings": ["not-an-object"]},
        {"recordings": [{"file": 7}, {"file": "no-extension"}]},
        {},
    ]
    assert _prefetch_audio_seconds(rows, tmp_path, workers=4) == {}


def test_prefetch_stays_serial_below_two_candidates(tmp_path):
    rows = [{"recordings": [{"file": "one.flac"}]}]
    assert _prefetch_audio_seconds(rows, tmp_path, workers=4) == {}
