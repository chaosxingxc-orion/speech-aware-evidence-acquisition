"""KB-BUILD v1 (work item C1): distribution-modeled TRAIN knowledge
construction -- sampler determinism/pool-order-independence, long-tail
floors, snapshot round-trip, coverage-report numbers, decontamination
refusal, registry resolution, and receipt (frozen-JSON) byte-stability.

Every test here is MODEL-FREE and filesystem-free except the small
``slurp_world`` fixture cases, which reuse the existing tiny synthetic SLURP
corpus already shared by ``tests/unit/test_data_slurp.py``.
"""

from __future__ import annotations

import json
import random

import pytest

from speech_aware_evidence_acquisition.core.base import KNOWLEDGE_BUILDERS
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.hashing import canonical_json_bytes
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    KB_BUILD_POLICY_ID,
    KbRow,
    KnowledgeBuildSpec,
    build_knowledge_snapshot,
    coverage_report,
    distribution_sample,
    freeze_slurp_split_identity,
    slurp_kb_rows,
    slurp_split_sample_ids,
)


# ---------------------------------------------------------------------------
# Synthetic corpus helpers
# ---------------------------------------------------------------------------


def _row(
    utterance_id: str,
    *,
    scenario: str,
    action: str,
    words: str,
    speaker_id: str,
    entity_types: tuple[str, ...] = (),
    entity_fillers: dict[str, tuple[str, ...]] | None = None,
) -> KbRow:
    sample_id = f"slurp:train:{utterance_id}:audio-{utterance_id}"
    return KbRow(
        utterance_id=utterance_id,
        content=words,
        scenario=scenario,
        action=action,
        intent=f"{scenario}_{action}",
        entity_types=entity_types,
        entity_fillers=entity_fillers or {},
        sample_ids=(sample_id,),
        speaker_by_sample_id={sample_id: speaker_id},
        media_relpath_by_sample_id={sample_id: f"datasets/slurp/slurp_real/audio-{utterance_id}.flac"},
    )


def _synthetic_rows() -> tuple[KbRow, ...]:
    """~150 rows: 5 common intents (20 utterances each, 4 speakers cycling,
    a shared entity type 'device' with several fillers) + 10 rare intents (5
    utterances each, one carrying a unique entity type only it has) + 3
    ultra-rare intents (exactly 1 utterance each). Every row's content text
    is distinct so bigram shingles vary."""

    rows: list[KbRow] = []
    topics = [
        "the kitchen lights", "the bedroom lamp", "the hallway light",
        "the living room brightness", "the porch light", "the garage light",
        "the office lamp", "the closet light", "the bathroom light",
        "the attic light", "the basement light", "the patio light",
        "the dining room light", "the study lamp", "the entrance light",
        "the balcony light", "the nursery light", "the workshop light",
        "the pantry light", "the laundry room light",
    ]
    common_actions = ["turnon", "turnoff", "dim", "brighten", "colour"]
    for action_index, action in enumerate(common_actions):
        for topic_index, topic in enumerate(topics):
            uid = f"c{action_index:02d}{topic_index:02d}"
            speaker = f"sp-common-{topic_index % 4}"
            entity_types: tuple[str, ...] = ()
            fillers: dict[str, tuple[str, ...]] = {}
            if topic_index % 3 == 0:
                entity_types = ("device",)
                fillers = {"device": (topic.split()[-1],)}
            rows.append(
                _row(
                    uid,
                    scenario="iot",
                    action=action,
                    words=f"please {action} {topic} now",
                    speaker_id=speaker,
                    entity_types=entity_types,
                    entity_fillers=fillers,
                )
            )

    rare_topics = [
        "flights to paris", "the stock price", "a taxi downtown",
        "my calendar for friday", "the weather tomorrow", "a pizza order",
        "the news headlines", "a reminder for noon", "the sports scores",
        "a joke about robots",
    ]
    for rare_index, topic in enumerate(rare_topics):
        for member in range(5):
            uid = f"r{rare_index:02d}{member:02d}"
            speaker = f"sp-rare-{rare_index % 3}"
            entity_types = (f"rare_type_{rare_index}",) if member == 0 else ()
            fillers = (
                {f"rare_type_{rare_index}": (f"filler-{rare_index}-{member}",)}
                if member == 0
                else {}
            )
            rows.append(
                _row(
                    uid,
                    scenario="assist",
                    action=f"rare{rare_index}",
                    words=f"tell me about {topic} variant {member}",
                    speaker_id=speaker,
                    entity_types=entity_types,
                    entity_fillers=fillers,
                )
            )

    for ultra_index in range(3):
        uid = f"u{ultra_index:02d}"
        rows.append(
            _row(
                uid,
                scenario="ultra",
                action=f"once{ultra_index}",
                words=f"this happens exactly once number {ultra_index}",
                speaker_id="sp-ultra-0",
                entity_types=(f"ultra_type_{ultra_index}",),
                entity_fillers={f"ultra_type_{ultra_index}": (f"ultra-filler-{ultra_index}",)},
            )
        )
    return tuple(rows)


# ---------------------------------------------------------------------------
# distribution_sample
# ---------------------------------------------------------------------------


def test_distribution_sample_is_deterministic_and_pool_order_independent():
    rows = _synthetic_rows()
    shuffled = list(rows)
    random.Random("shuffle").shuffle(shuffled)

    first = distribution_sample(rows, 60, seed=1)
    second = distribution_sample(tuple(shuffled), 60, seed=1)
    assert first == second
    ids = [row.utterance_id for row in first]
    assert ids == sorted(ids)


def test_distribution_sample_covers_every_intent_and_every_entity_type():
    rows = _synthetic_rows()
    all_intents = {row.intent for row in rows}
    all_entity_types = {et for row in rows for et in row.entity_types}

    selected = distribution_sample(rows, 40, seed=20260823)
    selected_intents = {row.intent for row in selected}
    selected_entity_types = {et for row in selected for et in row.entity_types}

    assert selected_intents == all_intents
    assert selected_entity_types == all_entity_types


def test_distribution_sample_floor_can_exceed_requested_size():
    rows = _synthetic_rows()
    n_intents = len({row.intent for row in rows})
    # Requesting fewer than the number of intents forces the floor set to be
    # larger than the request -- floors are hard, size is best-effort.
    selected = distribution_sample(rows, 5, seed=1)
    assert len(selected) >= n_intents


def test_distribution_sample_returns_full_pool_for_none_or_oversized_request():
    rows = _synthetic_rows()
    all_ids = tuple(sorted(row.utterance_id for row in rows))

    none_selected = distribution_sample(rows, None, seed=1)
    assert tuple(row.utterance_id for row in none_selected) == all_ids

    oversized_selected = distribution_sample(rows, len(rows) + 100, seed=1)
    assert tuple(row.utterance_id for row in oversized_selected) == all_ids


def test_distribution_sample_respects_speaker_cap_where_feasible():
    rows = _synthetic_rows()
    # The 5 common intents each have 4 distinct speakers cycling evenly over
    # 20 rows; request enough of one intent that the 10% cap should bind.
    selected = distribution_sample(rows, 120, seed=20260823)
    by_speaker_in_common_intent: dict[str, int] = {}
    common_selected = [row for row in selected if row.scenario == "iot" and row.action == "turnon"]
    for row in common_selected:
        by_speaker_in_common_intent[row.primary_speaker_id] = (
            by_speaker_in_common_intent.get(row.primary_speaker_id, 0) + 1
        )
    if common_selected:
        max_share = max(by_speaker_in_common_intent.values()) / len(common_selected)
        # Soft cap: allow some slack for small strata, but a single speaker
        # should not dominate an intent stratum of meaningful size.
        if len(common_selected) >= 10:
            assert max_share <= 0.5


def test_distribution_sample_rejects_empty_or_invalid_input():
    with pytest.raises(RailsError):
        distribution_sample((), 10, seed=1)
    with pytest.raises(RailsError):
        distribution_sample(_synthetic_rows(), 0, seed=1)
    with pytest.raises(RailsError):
        distribution_sample(_synthetic_rows(), True, seed=1)  # bool is not a legal size


# ---------------------------------------------------------------------------
# KnowledgeBuildSpec validation
# ---------------------------------------------------------------------------


def test_knowledge_build_spec_validation():
    KnowledgeBuildSpec(carrier_lock_key="slurp").validate()
    with pytest.raises(RailsError):
        KnowledgeBuildSpec(carrier_lock_key="").validate()
    with pytest.raises(RailsError):
        KnowledgeBuildSpec(carrier_lock_key="slurp", datastore_size=0).validate()
    with pytest.raises(RailsError):
        KnowledgeBuildSpec(carrier_lock_key="slurp", datastore_size=-5).validate()
    with pytest.raises(RailsError):
        KnowledgeBuildSpec(carrier_lock_key="slurp", dimensions=()).validate()
    with pytest.raises(RailsError):
        KnowledgeBuildSpec(carrier_lock_key="slurp", dimensions=("content", "content")).validate()
    with pytest.raises(RailsError):
        KnowledgeBuildSpec(carrier_lock_key="slurp", dimensions=("bogus",)).validate()
    with pytest.raises(RailsError):
        KnowledgeBuildSpec(carrier_lock_key="slurp", dimensions=("speaker", "prior")).validate()


# ---------------------------------------------------------------------------
# build_knowledge_snapshot / round trip / coverage_report
# ---------------------------------------------------------------------------


def _build(size, *, dims=None, seed=20260823) -> tuple[KnowledgeSnapshot, tuple[KbRow, ...]]:
    rows = _synthetic_rows()
    spec = KnowledgeBuildSpec(
        carrier_lock_key="slurp",
        datastore_size=size,
        seed=seed,
        dimensions=dims or ("content", "label", "speaker", "prior"),
    )
    snapshot = build_knowledge_snapshot(spec, rows=rows, forbidden_sample_ids=frozenset())
    return snapshot, rows


def test_snapshot_round_trips_via_from_frozen_json():
    snapshot, _rows = _build(40)
    frozen = snapshot.frozen_json()
    restored = KnowledgeSnapshot.from_frozen_json(frozen)
    assert restored.content_hash() == snapshot.content_hash()
    assert restored.snapshot_id == snapshot.snapshot_id
    assert len(restored.facets) == len(snapshot.facets)
    assert len(restored.values) == len(snapshot.values)


def test_registry_resolution():
    resolved = KNOWLEDGE_BUILDERS.resolve(KB_BUILD_POLICY_ID)
    assert resolved is build_knowledge_snapshot


def test_coverage_report_numbers_on_synthetic_corpus():
    snapshot, rows = _build(40)
    report = coverage_report(snapshot, rows)

    all_intents = {row.intent for row in rows}
    all_entity_types = {et for row in rows for et in row.entity_types}
    assert report["intent_coverage"] == 1.0
    assert report["entity_type_coverage"] == 1.0
    assert report["datastore_size_actual"] == len(snapshot.values)
    assert report["counts"]["train_intents"] == len(all_intents)
    assert report["counts"]["train_entity_types"] == len(all_entity_types)
    assert report["kl_selected_given_train_over_intent"] >= 0.0
    # The 3 ultra-rare intents have exactly 1 train utterance (< 5) -> long
    # tail; the 10 "rare" intents have exactly 5 (not < 5) so they don't count.
    assert report["long_tail_coverage"]["intent"]["train_long_tail_count"] == 3
    assert report["long_tail_coverage"]["intent"]["coverage"] == 1.0
    assert 0.0 <= report["cluster_coverage_proxy"] <= 1.0
    assert report["speaker_histogram_summary"]["distinct_speakers"] > 0


def test_coverage_report_full_build_has_perfect_coverage_and_zero_kl():
    snapshot, rows = _build(None)
    report = coverage_report(snapshot, rows)
    assert report["intent_coverage"] == 1.0
    assert report["entity_type_coverage"] == 1.0
    assert report["scenario_coverage"] == 1.0
    assert report["action_coverage"] == 1.0
    assert report["kl_selected_given_train_over_intent"] == pytest.approx(0.0, abs=1e-9)
    assert report["datastore_size_actual"] == len(rows)


def test_receipt_and_report_are_byte_stable_across_rebuilds():
    snapshot_a, rows_a = _build(50)
    snapshot_b, _rows_b = _build(50)
    assert canonical_json_bytes(snapshot_a.frozen_json()) == canonical_json_bytes(
        snapshot_b.frozen_json()
    )
    report_a = coverage_report(snapshot_a, rows_a)
    report_b = coverage_report(snapshot_b, rows_a)
    assert json.dumps(report_a, sort_keys=True) == json.dumps(report_b, sort_keys=True)


def test_build_knowledge_snapshot_respects_dimension_gating():
    snapshot, _rows = _build(30, dims=("content",))
    dimensions = {facet.dimension for facet in snapshot.facets}
    assert dimensions == {"content"}
    for value in snapshot.values:
        assert value.prior_score is not None


def test_build_knowledge_snapshot_rejects_non_slurp_carrier():
    rows = _synthetic_rows()
    spec = KnowledgeBuildSpec(carrier_lock_key="not-slurp")
    with pytest.raises(RailsError):
        build_knowledge_snapshot(spec, rows=rows, forbidden_sample_ids=frozenset())


# ---------------------------------------------------------------------------
# Decontamination
# ---------------------------------------------------------------------------


def test_build_knowledge_snapshot_refuses_a_planted_devel_id():
    rows = _synthetic_rows()
    planted_sample_id = rows[0].sample_ids[0]
    spec = KnowledgeBuildSpec(carrier_lock_key="slurp", datastore_size=None)
    with pytest.raises(RailsError, match="decontamination"):
        build_knowledge_snapshot(
            spec, rows=rows, forbidden_sample_ids=frozenset({planted_sample_id})
        )


def test_build_knowledge_snapshot_succeeds_when_forbidden_set_is_disjoint():
    rows = _synthetic_rows()
    spec = KnowledgeBuildSpec(carrier_lock_key="slurp", datastore_size=None)
    snapshot = build_knowledge_snapshot(
        spec, rows=rows, forbidden_sample_ids=frozenset({"slurp:devel:999999:audio-x"})
    )
    assert snapshot.source_sample_ids


# ---------------------------------------------------------------------------
# slurp_kb_rows / slurp_split_sample_ids / freeze_slurp_split_identity
# (real (tiny) SLURP fixture from tests/unit/conftest.py)
# ---------------------------------------------------------------------------


def test_slurp_kb_rows_recovers_entity_fillers_absent_from_train_material(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    rows = slurp_kb_rows(lock, slurp_world.data_root)
    assert [row.scenario for row in rows] == ["iot", "weather"]
    assert rows[0].entity_types == ("house_place",)
    assert rows[0].entity_fillers == {"house_place": ("kitchen",)}
    assert rows[0].intent == "iot_hue_lightdim"
    assert rows[1].entity_fillers == {}


def test_slurp_split_sample_ids_is_identity_only(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    devel_ids = slurp_split_sample_ids(lock, slurp_world.data_root, "devel")
    test_ids = slurp_split_sample_ids(lock, slurp_world.data_root, "test")
    # devel fixture: slurp_id 101 has 2 recordings, 102 has 1 -> 3 ids.
    assert len(devel_ids) == 3
    assert all(sid.startswith("slurp:devel:") for sid in devel_ids)
    assert len(test_ids) == 1
    assert test_ids[0].startswith("slurp:test:")
    assert devel_ids == tuple(sorted(devel_ids))


def test_slurp_split_sample_ids_rejects_unknown_split(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    with pytest.raises(RailsError):
        slurp_split_sample_ids(lock, slurp_world.data_root, "bogus")


def test_freeze_slurp_split_identity_document_shape(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    document = freeze_slurp_split_identity(lock, slurp_world.data_root)
    assert document["schema"] == "saea-kb-split-identity-v1"
    assert document["carrier"] == "slurp"
    assert document["splits"]["devel"]["count"] == 3
    assert document["splits"]["test"]["count"] == 1
    devel_ids = document["splits"]["devel"]["ids"]
    assert devel_ids == sorted(devel_ids)
    import hashlib

    expected_hash = hashlib.sha256("\n".join(sorted(devel_ids)).encode("utf-8")).hexdigest()
    assert document["splits"]["devel"]["identity_hash"] == expected_hash
