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

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.slurp import load_slurp_ontology


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
