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


def test_the_version_argument_names_every_roster_and_every_receipt_stem() -> None:
    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        exposure_row_id,
        roster_id,
        roster_stem,
    )

    assert roster_id("fold_a") == "SLURP-EVO-FOLD-A-V1"
    assert roster_id("fold_b", "V2") == "SLURP-EVO-FOLD-B-V2"
    assert roster_stem("exemplars", "V2") == "slurp-evo-exemplars-v2"
    assert exposure_row_id("V2") == "SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V2"
    rosters = cut(fold_quota=10, exemplar_quota=6, version="V2")
    assert rosters["fold_a"]["roster_id"] == "SLURP-EVO-FOLD-A-V2"
    assert rosters["fold_b"]["roster_id"] == "SLURP-EVO-FOLD-B-V2"
    assert rosters["exemplars"]["roster_id"] == "SLURP-EVO-EXEMPLARS-V2"
    proof = disjointness_proof(
        rosters, devel_ids=(), test_ids=(), contacted_train_utterances=()
    )
    stems = {
        stem
        for stem, _document in roster_documents(
            rosters, proof=proof, shared={}, version="V2"
        )
    }
    assert stems == {
        "slurp-evo-fold-a-v2",
        "slurp-evo-fold-b-v2",
        "slurp-evo-exemplars-v2",
    }


def test_a_malformed_version_is_refused_before_anything_is_drawn() -> None:
    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        RosterSourceError,
        roster_id,
    )

    for bad in ("v2", "2", "V", "V2a", "", None):
        with pytest.raises(RosterSourceError):
            roster_id("fold_a", bad)  # type: ignore[arg-type]


def test_a_redraw_records_the_receipts_it_supersedes(tmp_path) -> None:
    import hashlib
    import json

    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        RosterSourceError,
        supersedes_block,
    )

    written: dict[str, str] = {}
    for stem, roster in (
        ("slurp-evo-fold-a-v1", "SLURP-EVO-FOLD-A-V1"),
        ("slurp-evo-fold-b-v1", "SLURP-EVO-FOLD-B-V1"),
        ("slurp-evo-exemplars-v1", "SLURP-EVO-EXEMPLARS-V1"),
    ):
        path = tmp_path / f"{stem}.json"
        path.write_text(
            json.dumps(
                {
                    "roster_id": roster,
                    "split_identity_hash": "0" * 64,
                    "items": [{"sample_id": "slurp:train:000001:audio-1"}],
                }
            ),
            encoding="utf-8",
        )
        written[roster] = hashlib.sha256(path.read_bytes()).hexdigest()

    block = supersedes_block(tmp_path, "V1", "coordinator decision 1, 2026-09-06")
    assert block["version"] == "V1"
    assert block["exposure_row"] == "SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V1"
    assert block["decision"] == "coordinator decision 1, 2026-09-06"
    assert [row["roster_id"] for row in block["rosters"]] == list(written)
    assert [row["receipt_file_sha256"] for row in block["rosters"]] == list(
        written.values()
    )
    assert all(row["recordings"] == 1 for row in block["rosters"])
    with pytest.raises(RosterSourceError):
        supersedes_block(tmp_path, "V1", "")


def test_the_shared_block_carries_the_version_and_its_exposure_row() -> None:
    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import shared_block

    identity = {
        "splits": {
            "devel": {"identity_hash": "a" * 64, "count": 8690},
            "test": {"identity_hash": "b" * 64, "count": 13078},
        }
    }
    block = shared_block(
        corpus(per_scenario=5),
        touched=set(),
        touched_rows=[],
        excluded_recordings=0,
        split_identity=identity,
        version="V2",
        offline_guard={"outbound_connection_attempts": 0},
        supersedes={"version": "V1"},
    )
    assert block["roster_version"] == "V2"
    assert block["exposure_row"] == "SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V2"
    assert block["supersedes"] == {"version": "V1"}
    assert block["split_identity_receipt"]["devel_ids"] == 8690
    assert block["pool"]["train_utterances"] == 10
    assert "supersedes" not in shared_block(
        corpus(per_scenario=5),
        touched=set(),
        touched_rows=[],
        excluded_recordings=0,
        split_identity=identity,
        version="V1",
        offline_guard={},
    )


def test_the_exemplar_target_yields_to_capacity_and_the_cap_is_recorded() -> None:
    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        candidates,
        exemplar_quotas,
    )

    # 'weather' keeps 30 entity-bearing utterances, 'social' only 10, so a
    # target of 24 is met by one scenario and capped for the other.
    records = [
        *[record(i, "weather", "", entities=(SlotEntity(type="date", filler="x"),))
          for i in range(30)],
        *[record(100 + i, "social", "", entities=(SlotEntity(type="date", filler="x"),))
          for i in range(10)],
    ]
    items, groups = candidates(records)
    quotas, policy = exemplar_quotas(
        items, spent=set(), groups=groups, target=24, floor=8
    )
    assert quotas == {"social": 10, "weather": 24}
    assert policy["target_per_scenario"] == 24
    assert policy["capped_scenarios"] == {"social": 10}
    assert policy["realized_per_scenario"] == quotas


def test_an_exemplar_pool_below_the_floor_is_refused_not_weakened() -> None:
    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        RosterSourceError,
        candidates,
        exemplar_quotas,
    )

    records = [
        record(i, "weather", "", entities=(SlotEntity(type="date", filler="x"),))
        for i in range(5)
    ]
    items, groups = candidates(records)
    with pytest.raises(RosterSourceError):
        exemplar_quotas(items, spent=set(), groups=groups, target=24, floor=8)


def test_the_exemplar_quota_policy_lands_in_the_exemplar_receipt() -> None:
    rosters = cut(fold_quota=10, exemplar_quota=6)
    policy = rosters["exemplars"]["exemplar_quota_policy"]
    assert policy["target_per_scenario"] == 6
    assert policy["capped_scenarios"] == {}
    assert set(policy["realized_per_scenario"]) == set(SCENARIOS)


# ---------------------------------------------------------------------------
# Stage-one power: the arithmetic that justified the 60-per-scenario re-draw.
# ---------------------------------------------------------------------------

KC_S1B_TRANSPORT = {"n": 60, "saves": 12, "harms": 2}
KC_S1B_QA = {"n": 60, "saves": 4, "harms": 0}
KC_S1B_DATETIME = {"n": 61, "saves": 4, "harms": 0}


def test_the_gate_prices_measured_rates_at_the_fold_size() -> None:
    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        stage_one_power,
    )

    (row,) = stage_one_power({"qa": KC_S1B_QA}, 60)
    assert row["expected_saves"] == 4.0
    assert row["expected_harms"] == 0.0
    assert row["clears_gate"] is True
    (half,) = stage_one_power({"qa": KC_S1B_QA}, 30)
    assert half["expected_saves"] == 2.0
    assert half["clears_gate"] is False


def test_the_absolute_harms_bound_makes_the_gate_not_scale_free() -> None:
    """``transport`` clears at 30 rows and is refused at 60: saves double, the
    harms bound does not. This is the finding the power receipt records."""

    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        stage_one_power,
    )

    (at30,) = stage_one_power({"transport": KC_S1B_TRANSPORT}, 30)
    (at60,) = stage_one_power({"transport": KC_S1B_TRANSPORT}, 60)
    assert (at30["expected_saves"], at30["expected_harms"]) == (6.0, 1.0)
    assert at30["clears_gate"] is True
    assert (at60["expected_saves"], at60["expected_harms"]) == (12.0, 2.0)
    assert at60["clears_gate"] is False


def test_expected_counts_are_never_rounded_into_the_gate() -> None:
    """``datetime`` prices at 3.93 saves on a 60-row fold. Rounding would admit
    it; the preregistered gate is an absolute count and does not round."""

    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        stage_one_power,
    )

    (row,) = stage_one_power({"datetime": KC_S1B_DATETIME}, 60)
    assert row["expected_saves"] == pytest.approx(3.9344, abs=1e-4)
    assert row["clears_gate"] is False


def test_the_power_summary_counts_and_names_the_clearing_scenarios() -> None:
    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        stage_one_power,
        stage_one_power_summary,
    )

    table = stage_one_power(
        {"qa": KC_S1B_QA, "transport": KC_S1B_TRANSPORT, "datetime": KC_S1B_DATETIME},
        60,
    )
    summary = stage_one_power_summary(table)
    assert summary == {"clears": 1, "scenarios": 3, "clearing_scenarios": ["qa"]}


def test_a_stratum_with_no_measured_rows_is_refused() -> None:
    from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (
        stage_one_power,
    )

    with pytest.raises(ValueError):
        stage_one_power({"ghost": {"n": 0, "saves": 0, "harms": 0}}, 60)
    with pytest.raises(ValueError):
        stage_one_power({"qa": KC_S1B_QA}, 0)
