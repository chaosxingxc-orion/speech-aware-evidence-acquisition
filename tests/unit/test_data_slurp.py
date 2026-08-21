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

import threading
import time
from pathlib import Path

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.slurp import (
    _missing_media_paths,
    load_slurp_ontology,
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
    assert material[0].recordings[0].sample_id == "slurp:train:000301:audio-301"
    assert material[0].recordings[0].speaker_id == "speaker-train-a"
    assert material[0].recordings[0].media_relpath.endswith("/slurp_real/audio-301.flac")


def test_train_material_refuses_missing_speaker_identity(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    metadata_path = slurp_world.metadata_dir / "metadata.json"
    metadata_path.write_text("{}", encoding="utf-8")
    import pytest

    with pytest.raises(Exception, match="speaker identity"):
        load_slurp_train_material(lock, slurp_world.data_root)
