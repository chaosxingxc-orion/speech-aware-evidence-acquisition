"""Unit tests for the EVO-S1 SLURP construction-capacity arithmetic.

Synthetic units only: no governed corpus, no receipt, no contact.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_evo_capacity import (
    CAPACITY_SCHEMA,
    TrainUnit,
    capacity_rows,
    census_document,
)
from speech_aware_evidence_acquisition.data.slurp import (
    SlurpIntentSlots,
    SlurpIntentSlotSchema,
)


def unit(
    utterance_id: str,
    scenario: str,
    action: str = "query",
    *,
    recordings: int = 4,
    headset: int = 2,
    speakers: tuple[str, ...] = ("S1", "S2"),
    entity_types: tuple[str, ...] = ("date",),
) -> TrainUnit:
    return TrainUnit(
        utterance_id=utterance_id,
        scenario=scenario,
        action=action,
        recordings=recordings,
        headset_recordings=headset,
        speakers=speakers,
        entity_types=entity_types,
    )


def schema(profiles: dict[str, dict[str, int]]) -> SlurpIntentSlotSchema:
    intents = {
        intent: SlurpIntentSlots(
            intent=intent,
            n=len(counts),
            mentions=sum(counts.values()),
            types=tuple(
                (entity_type, count, count / max(sum(counts.values()), 1))
                for entity_type, count in sorted(counts.items())
            ),
            fillers=MappingProxyType({}),
        )
        for intent, counts in profiles.items()
    }
    return SlurpIntentSlotSchema(
        schema_id="test-schema",
        source_split="train",
        source_identity_hash="0" * 64,
        utterance_count=sum(len(counts) for counts in profiles.values()),
        min_share=0.0,
        examples_per_type=5,
        intents=MappingProxyType(intents),
    )


def test_capacity_rows_state_the_need_and_the_headroom() -> None:
    units = [unit(f"{i:04d}", "weather") for i in range(90)]
    rows = capacity_rows(units, fold_quota=30, exemplar_quota=24)
    assert len(rows) == 1
    row = rows[0]
    assert row["required_utterances"] == 84
    assert row["headroom_utterances"] == 6
    assert row["satisfies_folds"] is True
    assert row["satisfies_exemplars"] is True


def test_a_scenario_below_the_fold_need_is_named_not_silently_dropped() -> None:
    units = [unit(f"{i:04d}", "audio") for i in range(80)]
    rows = capacity_rows(units, fold_quota=30, exemplar_quota=24)
    assert rows[0]["satisfies_folds"] is False
    assert rows[0]["headroom_utterances"] == -4


def test_entity_free_utterances_do_not_count_toward_the_exemplar_pool() -> None:
    units = [unit(f"{i:04d}", "music") for i in range(84)]
    units += [
        unit(f"9{i:03d}", "music", entity_types=()) for i in range(20)
    ]
    rows = capacity_rows(units, fold_quota=20, exemplar_quota=60)
    assert rows[0]["train_utterances"] == 104
    assert rows[0]["utterances_with_entities"] == 84
    assert rows[0]["required_utterances"] == 100
    assert rows[0]["satisfies_folds"] is True
    assert rows[0]["satisfies_exemplars"] is True
    # The exemplar quota is counted against ENTITY-BEARING utterances alone,
    # so raising it past 84 fails the exemplar test even though the raw pool
    # still has 104 blocks.
    strict = capacity_rows(units, fold_quota=10, exemplar_quota=85)
    assert strict[0]["required_utterances"] == 105
    assert strict[0]["satisfies_exemplars"] is False


def test_census_document_reports_the_mixes_and_the_verdict() -> None:
    units = [
        unit(f"a{i:03d}", "weather", "query", entity_types=("weather_descriptor",))
        for i in range(84)
    ]
    units += [
        unit(f"b{i:03d}", "music", "likeness", recordings=2, headset=1, entity_types=())
        for i in range(84)
    ]
    document = census_document(
        units,
        schema_full=schema(
            {
                "weather_query": {"weather_descriptor": 40, "place_name": 10},
                "music_likeness": {"artist_name": 3},
            }
        ),
        schema_committed={"weather_query": 2, "music_likeness": 1},
        dev_mixture={"weather": 60, "music": 51},
        dev_receipt={"split_identity_hash": "abc", "run_identity_hash": "def"},
    )
    assert document["schema"] == CAPACITY_SCHEMA
    assert document["population"]["utterances"] == 168
    assert document["population"]["recordings"] == 84 * 4 + 84 * 2
    assert document["population"]["headset_recordings"] == 84 * 2 + 84 * 1
    assert document["population"]["utterances_with_entities"] == 84
    weather = next(row for row in document["scenarios"] if row["scenario"] == "weather")
    assert weather["headset_share"] == pytest.approx(0.5)
    assert weather["zero_entity_share"] == pytest.approx(0.0)
    assert weather["entity_mentions"] == 50
    assert weather["entity_type_mention_counts"] == {
        "weather_descriptor": 40,
        "place_name": 10,
    }
    music = next(row for row in document["scenarios"] if row["scenario"] == "music")
    assert music["zero_entity_share"] == pytest.approx(1.0)
    assert document["verdict"]["capacity_wall"] is True
    assert document["verdict"]["scenarios_short_of_exemplars"] == ["music"]
    assert document["verdict"]["scenarios_short_of_folds"] == []
    assert document["dev_1000_mixture"]["scenario_allocation"] == {
        "music": 51,
        "weather": 60,
    }


def test_intent_rows_carry_their_scenario_and_the_committed_type_count() -> None:
    units = [unit(f"c{i:03d}", "weather", "query") for i in range(5)]
    document = census_document(
        units,
        schema_full=schema({"weather_query": {"weather_descriptor": 7}}),
        schema_committed={"weather_query": 1},
        dev_mixture={"weather": 60},
        dev_receipt={},
    )
    row = document["intents"][0]
    assert row["intent"] == "weather_query"
    assert row["scenario"] == "weather"
    assert row["entity_mentions"] == 7
    assert row["committed_schema_types"] == 1
