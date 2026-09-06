"""Unit tests for the three EVO-S1 SLURP loop rosters.

Synthetic ``SlurpRecord`` objects only: no governed corpus, no flac, no
receipt, no contact.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
    TOUCHED_TRAIN_SOURCES,
    disjointness_proof,
    freeze_evo_rosters,
    roster_documents,
    touched_train_utterances,
    utterance_of,
)
from speech_aware_evidence_acquisition.data.slurp import SlurpRecord
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

SCENARIOS = ("weather", "social")


def record(
    utterance: int,
    scenario: str,
    channel: str,
    *,
    entities: tuple[SlotEntity, ...] = (),
    seconds: float = 2.0,
) -> SlurpRecord:
    stem = f"audio-{utterance:06d}{channel}"
    return SlurpRecord(
        sample_id=f"slurp:train:{utterance:06d}:{stem}",
        utterance_id=str(utterance),
        split="train",
        media_relpath=f"datasets/slurp/slurp_real/{stem}.flac",
        audio_seconds=seconds,
        scenario=scenario,
        action="query",
        intent=f"{scenario}_query",
        entities=entities,
    )


def corpus(per_scenario: int = 40, entity_fraction: float = 0.75) -> list[SlurpRecord]:
    """Two recordings per utterance -- one headset, one far-field."""

    records: list[SlurpRecord] = []
    utterance = 0
    for scenario in SCENARIOS:
        for index in range(per_scenario):
            entities = (
                (SlotEntity(type="date", filler="today"),)
                if index < int(per_scenario * entity_fraction)
                else ()
            )
            records.append(record(utterance, scenario, "", entities=entities))
            records.append(record(utterance, scenario, "-headset", entities=entities))
            utterance += 1
    return records


def cut(**kwargs) -> dict:
    return freeze_evo_rosters(corpus(), seed=20260906, **kwargs)


def test_every_roster_fills_its_quota_in_every_scenario() -> None:
    rosters = cut(fold_quota=10, exemplar_quota=6)
    assert len(rosters["fold_a"]["items"]) == 20
    assert len(rosters["fold_b"]["items"]) == 20
    assert len(rosters["exemplars"]["items"]) == 12
    for name, quota in (("fold_a", 10), ("fold_b", 10), ("exemplars", 6)):
        assert rosters[name]["strata_counts"] == {"social": quota, "weather": quota}
        assert rosters[name]["roster_role"] == "construction"
        assert rosters[name]["split_role"] == "discovery"


def test_the_three_rosters_are_disjoint_at_the_utterance_level() -> None:
    rosters = cut(fold_quota=10, exemplar_quota=6)
    proof = disjointness_proof(
        rosters, devel_ids=(), test_ids=(), contacted_train_utterances=()
    )
    assert set(proof.values()) == {0, 1}
    for key, value in proof.items():
        expected = 1 if key.startswith("max_recordings_per_utterance") else 0
        assert value == expected, key


def test_an_utterance_never_contributes_two_recordings() -> None:
    rosters = cut(fold_quota=10, exemplar_quota=6)
    for name in ("fold_a", "fold_b", "exemplars"):
        ids = [str(item["sample_id"]) for item in rosters[name]["items"]]
        assert len(ids) == len({utterance_of(sample_id) for sample_id in ids})


def test_the_exemplar_pool_carries_only_entity_bearing_utterances() -> None:
    records = corpus()
    entity_blocks = {
        utterance_of(item.sample_id) for item in records if item.entities
    }
    rosters = freeze_evo_rosters(records, seed=20260906, fold_quota=10, exemplar_quota=6)
    drawn = {
        utterance_of(str(item["sample_id"]))
        for item in rosters["exemplars"]["items"]
    }
    assert drawn <= entity_blocks


def test_the_proof_catches_an_evaluation_identity_planted_in_a_fold() -> None:
    rosters = cut(fold_quota=10, exemplar_quota=6)
    planted = str(rosters["fold_a"]["items"][0]["sample_id"])
    proof = disjointness_proof(
        rosters, devel_ids=(planted,), test_ids=(), contacted_train_utterances=()
    )
    assert proof["shared_with_devel_fold_a"] == 1
    assert proof["shared_with_devel_fold_b"] == 0


def test_the_proof_catches_a_contacted_train_utterance() -> None:
    rosters = cut(fold_quota=10, exemplar_quota=6)
    planted = utterance_of(str(rosters["fold_b"]["items"][0]["sample_id"]))
    proof = disjointness_proof(
        rosters, devel_ids=(), test_ids=(), contacted_train_utterances=(planted,)
    )
    assert proof["shared_with_contacted_train_fold_b"] == 1
    assert proof["shared_with_contacted_train_fold_a"] == 0


def test_roster_documents_carry_the_channel_mix_and_the_audio_total() -> None:
    rosters = cut(fold_quota=10, exemplar_quota=6)
    proof = disjointness_proof(
        rosters, devel_ids=(), test_ids=(), contacted_train_utterances=()
    )
    documents = dict(
        (stem, document)
        for stem, document in roster_documents(
            rosters, proof=proof, shared={"authority": "unit-test"}
        )
    )
    fold_a = documents["slurp-evo-fold-a-v1"]
    assert fold_a["authority"] == "unit-test"
    assert fold_a["distinct_utterances"] == 20
    assert fold_a["audio_seconds_total"] == pytest.approx(40.0)
    assert fold_a["headset_recordings"] + fold_a["far_field_recordings"] == 20
    assert fold_a["block_unit"] == "utterance id"
    assert fold_a["disjointness_proof"]["shared_utterances_fold_a_fold_b"] == 0
    assert set(documents) == {
        "slurp-evo-fold-a-v1",
        "slurp-evo-fold-b-v1",
        "slurp-evo-exemplars-v1",
    }


def test_a_scenario_that_cannot_fill_its_exemplar_quota_is_refused() -> None:
    records = corpus(per_scenario=30, entity_fraction=0.4)  # 12 entity-bearing each
    with pytest.raises(Exception):
        freeze_evo_rosters(records, seed=20260906, fold_quota=10, exemplar_quota=12)


def test_one_excluded_recording_removes_its_whole_utterance_everywhere() -> None:
    records = corpus()
    victim = records[0]  # the far-field recording of the first weather utterance
    block = utterance_of(victim.sample_id)
    rosters = freeze_evo_rosters(
        records,
        seed=20260906,
        fold_quota=10,
        exemplar_quota=6,
        exclude_sample_ids=(victim.sample_id,),
    )
    for name in ("fold_a", "fold_b", "exemplars"):
        blocks = {
            utterance_of(str(item["sample_id"])) for item in rosters[name]["items"]
        }
        assert block not in blocks
    assert rosters["fold_a"]["excluded_count"] == 2  # both recordings of that sentence


def test_the_touched_train_source_list_is_explicit_and_readable(tmp_path) -> None:
    (tmp_path / "one.json").write_text(
        '{"items": [{"id": "slurp:train:000001:audio-1"}]}', encoding="utf-8"
    )
    (tmp_path / "two.json").write_text(
        '{"items": ["slurp:train:000001:audio-2", "slurp:train:000002:audio-3"]}',
        encoding="utf-8",
    )
    union, rows = touched_train_utterances(tmp_path, ("one.json", "two.json"))
    assert union == {"slurp:train:000001", "slurp:train:000002"}
    assert [row["new_utterances"] for row in rows] == [1, 1]
    assert len(TOUCHED_TRAIN_SOURCES) == len(set(TOUCHED_TRAIN_SOURCES))


def test_assert_clean_cut_refuses_an_overlap_and_a_second_recording() -> None:
    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        RosterSourceError,
        assert_clean_cut,
    )

    assert_clean_cut(
        {
            "shared_recordings_fold_a_fold_b": 0,
            "max_recordings_per_utterance_fold_a": 1,
        }
    )
    with pytest.raises(RosterSourceError):
        assert_clean_cut(
            {
                "shared_recordings_fold_a_fold_b": 1,
                "max_recordings_per_utterance_fold_a": 1,
            }
        )
    with pytest.raises(RosterSourceError):
        assert_clean_cut(
            {
                "shared_recordings_fold_a_fold_b": 0,
                "max_recordings_per_utterance_fold_a": 2,
            }
        )


def test_pool_block_carries_the_eligible_count_after_exclusion() -> None:
    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import pool_block

    records = corpus(per_scenario=5)
    touched = {utterance_of(records[0].sample_id)}
    block = pool_block(
        records, touched=touched, excluded_recordings=2, touched_rows=[]
    )
    assert block["train_utterances"] == 10
    assert block["train_recordings"] == 20
    assert block["touched_train_utterances"] == 1
    assert block["touched_train_recordings"] == 2
    assert block["eligible_utterances"] == 9
