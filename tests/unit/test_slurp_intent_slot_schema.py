"""The SLURP per-intent TRAIN slot schema (program prerequisite MF-3): what it
counts, how it renders, that it is a pure suffix of the closed-list fill, how a
sealed closed-list prediction selects one block, and that it never opens a
non-TRAIN split.

Why the counting unit matters. ``rails.knowledge_build`` already measures
``p(entity_type | intent)`` on the same TRAIN rows and renders it as a
``facet:prior`` text, but it counts UTTERANCES containing a type, so its shares
sum above 1 for 17 of the 60 TRAIN intents (up to 1.97) and its 2 % floor
leaves some intents with no listed type at all. This schema counts entity
MENTIONS, so an intent's listed shares are a partition of that intent's own
slot mass and every intent keeps at least one type. The two representations
must also not collide textually: ``rails.runner.
_assert_agent_control_excludes_knowledge_payloads`` refuses any CONTROL
instruction that embeds a frozen snapshot's facet or value payload, so a schema
phrased like a facet would be unsendable beside a knowledge snapshot.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import INSTRUCTION_FILLS
from speech_aware_evidence_acquisition.data import slurp as ds
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.loader import LoaderError
from speech_aware_evidence_acquisition.data.slurp import (
    SLURP_INTENT_SLOT_DECONTAMINATION_RECEIPTS,
    SLURP_INTENT_SLOT_SCHEMA_ID,
    load_slurp_intent_slot_schema,
    normalize_slurp_train_utterance_exclusions,
    render_slurp_closed_label_inventory,
    render_slurp_closed_label_inventory_with_slot_schema,
    render_slurp_intent_slot_schema,
    render_slurp_slot_schema_for_state,
    render_slurp_slot_schema_for_state_detail,
    slurp_intent_from_state_content,
    slurp_intent_slot_schema_receipt,
)

FILL_NAME = "slurp-intent-slot-schema"
RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-intent-slot-schema-v1.json"


# ---------------------------------------------------------------------------
# A purpose-built corpus: enough rows per intent for a 2 % floor to bite
# ---------------------------------------------------------------------------


def _tokens(*surfaces: str) -> list[dict]:
    return [
        {"surface": surface, "id": index, "lemma": surface, "pos": "NN"}
        for index, surface in enumerate(surfaces)
    ]


def _row(slurp_id: int, scenario: str, action: str, spans: list[tuple[str, str]]):
    """One metadata row whose sentence is the concatenation of its fillers, so
    the token-span join reproduces the fillers exactly."""

    surfaces: list[str] = []
    entities: list[dict] = []
    for entity_type, filler in spans:
        words = filler.split(" ")
        entities.append(
            {
                "span": list(range(len(surfaces), len(surfaces) + len(words))),
                "type": entity_type,
            }
        )
        surfaces.extend(word.upper() for word in words)
    if not surfaces:
        surfaces = ["nothing"]
    return {
        "slurp_id": slurp_id,
        "sentence": " ".join(surfaces),
        "scenario": scenario,
        "action": action,
        "intent": f"{scenario}_{action}",
        "tokens": _tokens(*surfaces),
        "entities": entities,
        "recordings": [{"file": f"audio-{slurp_id}.flac", "status": "correct"}],
    }


def _train_rows() -> list[dict]:
    rows: list[dict] = []
    # alarm_set: 100 mentions of "time" (100 rows), 3 of "date", 1 of "rare".
    # -> time 96.2 %, date 2.9 %, rare 1.0 % (dropped by the 2 % floor).
    for index in range(100):
        rows.append(_row(1000 + index, "alarm", "set", [("time", f"filler {index}")]))
    for index in range(3):
        rows.append(_row(1200 + index, "alarm", "set", [("date", "tomorrow")]))
    rows.append(_row(1300, "alarm", "set", [("rare", "once in a while")]))
    # weather_query: two rows, no entities at all.
    rows.append(_row(2000, "weather", "query", []))
    rows.append(_row(2001, "weather", "query", []))
    return rows


class SlotWorld:
    """A governed-copy layout with a rich TRAIN split and poisoned devel/test
    files: any read of the wrong split shows up as a schema that knows an
    intent it must never have seen."""

    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "slot-data"
        self.lock_path = tmp_path / "slot-lock.json"
        self.metadata_dir = self.data_root / "datasets" / "slurp" / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        (self.data_root / "datasets" / "slurp" / "slurp_real").mkdir(
            parents=True, exist_ok=True
        )
        self._write("train.jsonl", _train_rows())
        self._write("devel.jsonl", [_row(9001, "devel", "leak", [("secret", "leaked")])])
        self._write("test.jsonl", [_row(9002, "test", "leak", [("secret", "leaked")])])
        self._write(
            "train_synthetic.jsonl",
            [_row(9003, "synthetic", "leak", [("secret", "leaked")])],
        )
        self.lock_path.write_text(
            json.dumps(
                {
                    "datasets": [
                        {
                            "name": "slurp",
                            "kind": "dataset",
                            "local_subdir": "repos/slurp/scripts/audio",
                            "annotations": {"governed_copy": "datasets/slurp/metadata"},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

    def _write(self, name: str, rows: list[dict]) -> None:
        (self.metadata_dir / name).write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
        )

    @property
    def lock(self):
        return load_lock(self.lock_path)


@pytest.fixture()
def slot_world(tmp_path):
    world = SlotWorld(tmp_path)
    ds._INTENT_SLOT_SCHEMA_CACHE.clear()
    yield world
    ds._INTENT_SLOT_SCHEMA_CACHE.clear()


@pytest.fixture()
def schema(slot_world):
    return load_slurp_intent_slot_schema(slot_world.lock, slot_world.data_root)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_schema_lists_types_above_the_floor_ordered_by_count(schema):
    profile = schema.intents["alarm_set"]
    assert profile.n == 104
    assert profile.mentions == 104
    assert profile.entity_types == ("time", "date")
    assert profile.types[0] == ("time", 100, round(100 / 104, 6))
    assert profile.types[1] == ("date", 3, round(3 / 104, 6))
    # "rare" occurs once in 104 mentions -- below the 2 % floor.
    assert "rare" not in profile.entity_types
    assert "rare" not in profile.fillers


def test_schema_keeps_an_intent_that_has_no_slots_at_all(schema):
    profile = schema.intents["weather_query"]
    assert profile.n == 2
    assert profile.mentions == 0
    assert profile.types == ()
    assert profile.fillers == {}


def test_schema_shares_never_sum_above_one_per_intent(schema):
    for intent, profile in schema.intents.items():
        assert sum(count for _t, count, _s in profile.types) <= profile.mentions, intent
        slack = 10 ** -ds._INTENT_SLOT_SHARE_DIGITS * max(1, len(profile.types))
        assert sum(share for _t, _c, share in profile.types) <= 1.0 + slack, intent
        for _entity_type, count, share in profile.types:
            assert 0.0 < share <= 1.0
            assert count >= 1


def test_schema_fillers_are_lowercase_distinct_and_capped(schema):
    profile = schema.intents["alarm_set"]
    for entity_type in profile.entity_types:
        fillers = profile.fillers[entity_type]
        assert len(fillers) <= schema.examples_per_type
        assert len(set(fillers)) == len(fillers)
        for filler in fillers:
            assert filler == filler.lower()
            assert filler.strip() == filler and filler
    # the source rows spelled every surface in UPPER CASE
    assert profile.fillers["date"] == ("tomorrow",)
    assert profile.fillers["time"] == tuple(f"filler {index}" for index in range(5))


def test_schema_is_deterministic_and_content_hashable(slot_world):
    first = load_slurp_intent_slot_schema(slot_world.lock, slot_world.data_root)
    second = load_slurp_intent_slot_schema(slot_world.lock, slot_world.data_root)
    assert first.as_json() == second.as_json()
    assert first.content_hash() == second.content_hash()
    assert len(first.content_hash()) == 64
    assert first.schema_id == SLURP_INTENT_SLOT_SCHEMA_ID
    assert first.intent_ids == ("alarm_set", "weather_query")


def test_schema_identity_hash_binds_the_train_utterance_ids(schema):
    expected_ids = sorted(
        f"slurp:train:{row['slurp_id']:06d}" for row in _train_rows()
    )
    assert schema.utterance_count == len(expected_ids)
    assert schema.source_split == "train"
    assert schema.source_identity_hash == hashlib.sha256(
        "\n".join(expected_ids).encode("utf-8")
    ).hexdigest()


def test_exclusions_remove_all_sibling_recordings_before_statistics(slot_world):
    rows = _train_rows()
    rows[0]["recordings"].append(
        {"file": "audio-1000-sibling.flac", "status": "correct"}
    )
    slot_world._write("train.jsonl", rows)

    schema = load_slurp_intent_slot_schema(
        slot_world.lock,
        slot_world.data_root,
        excluded_train_utterance_ids=("slurp:train:001000",),
    )

    alarm = schema.intents["alarm_set"]
    assert alarm.n == 103
    assert alarm.mentions == 103
    assert "filler 0" not in alarm.fillers["time"]
    retained_ids = sorted(
        f"slurp:train:{row['slurp_id']:06d}" for row in rows[1:]
    )
    assert schema.source_identity_hash == hashlib.sha256(
        "\n".join(retained_ids).encode("utf-8")
    ).hexdigest()
    assert schema.excluded_train_utterance_ids == ("slurp:train:001000",)


def test_excluding_only_observations_keeps_an_empty_legal_profile(slot_world):
    schema = load_slurp_intent_slot_schema(
        slot_world.lock,
        slot_world.data_root,
        excluded_train_utterance_ids=(
            "slurp:train:002000",
            "slurp:train:002001",
        ),
    )

    assert schema.intent_ids == ("alarm_set", "weather_query")
    weather = schema.intents["weather_query"]
    assert weather.n == 0
    assert weather.mentions == 0
    assert weather.types == ()
    assert weather.fillers == {}


def test_exclusion_normalization_is_canonical_and_precedes_source_read(
    slot_world, monkeypatch
):
    assert normalize_slurp_train_utterance_exclusions(
        ["slurp:train:002001", "slurp:train:001000"]
    ) == ("slurp:train:001000", "slurp:train:002001")

    opened = False

    def unexpected_read(_path):
        nonlocal opened
        opened = True
        raise AssertionError("malformed exclusions must fail before source read")

    monkeypatch.setattr(ds, "_read_jsonl", unexpected_read)
    for malformed in (
        "slurp:train:001000",
        ["001000"],
        ["train:001000"],
        ["slurp:train:1000"],
        ["slurp:devel:001000"],
        ["slurp:train:001000", "slurp:train:001000"],
        [1000],
    ):
        with pytest.raises(LoaderError):
            load_slurp_intent_slot_schema(
                slot_world.lock,
                slot_world.data_root,
                excluded_train_utterance_ids=malformed,
            )
    assert opened is False


def test_unknown_and_fully_empty_exclusions_are_refused(slot_world):
    with pytest.raises(LoaderError, match="absent from governed TRAIN"):
        load_slurp_intent_slot_schema(
            slot_world.lock,
            slot_world.data_root,
            excluded_train_utterance_ids=("slurp:train:009999",),
        )

    all_ids = tuple(
        f"slurp:train:{row['slurp_id']:06d}" for row in _train_rows()
    )
    with pytest.raises(LoaderError, match="empty slot schema"):
        load_slurp_intent_slot_schema(
            slot_world.lock,
            slot_world.data_root,
            excluded_train_utterance_ids=all_ids,
        )


def test_a_wider_floor_and_a_smaller_example_cap_are_honoured(slot_world):
    wide = load_slurp_intent_slot_schema(
        slot_world.lock, slot_world.data_root, min_share=0.0, examples_per_type=2
    )
    profile = wide.intents["alarm_set"]
    assert profile.entity_types == ("time", "date", "rare")
    assert profile.fillers["time"] == ("filler 0", "filler 1")


def test_bad_construction_parameters_fail_closed(slot_world):
    for kwargs in (
        {"min_share": 1.5},
        {"min_share": -0.1},
        {"min_share": "0.02"},
        {"examples_per_type": -1},
        {"examples_per_type": 2.5},
    ):
        with pytest.raises(LoaderError):
            load_slurp_intent_slot_schema(
                slot_world.lock, slot_world.data_root, **kwargs
            )


def test_a_train_row_without_a_slurp_id_is_refused(slot_world):
    rows = _train_rows()
    rows[0].pop("slurp_id")
    slot_world._write("train.jsonl", rows)
    with pytest.raises(LoaderError, match="slurp_id"):
        load_slurp_intent_slot_schema(slot_world.lock, slot_world.data_root)


def test_a_missing_train_file_is_refused(slot_world):
    (slot_world.metadata_dir / "train.jsonl").unlink()
    with pytest.raises(LoaderError, match="split metadata file missing"):
        load_slurp_intent_slot_schema(slot_world.lock, slot_world.data_root)


# ---------------------------------------------------------------------------
# Split discipline
# ---------------------------------------------------------------------------


def test_no_split_but_train_is_ever_read(slot_world, monkeypatch):
    """The hard guarantee: monkeypatch the module's own jsonl reader to refuse
    every path that is not ``train.jsonl``."""

    real_read = ds._read_jsonl
    seen: list[str] = []

    def only_train(path: Path):
        seen.append(Path(path).name)
        if Path(path).name != "train.jsonl":
            raise AssertionError(f"refused non-train read of {path}")
        return real_read(path)

    monkeypatch.setattr(ds, "_read_jsonl", only_train)
    schema = load_slurp_intent_slot_schema(slot_world.lock, slot_world.data_root)
    assert seen == ["train.jsonl"]
    assert set(schema.intents) == {"alarm_set", "weather_query"}


def test_the_poisoned_devel_test_and_synthetic_rows_never_appear(schema):
    rendered = render_slurp_intent_slot_schema(schema)
    for forbidden in ("devel_leak", "test_leak", "synthetic_leak", "secret", "leaked"):
        assert forbidden not in schema.intents
        assert forbidden not in rendered


def test_the_loader_takes_no_split_or_path_argument():
    """A caller cannot point this loader at devel or test even by mistake."""

    import inspect

    parameters = inspect.signature(load_slurp_intent_slot_schema).parameters
    assert set(parameters) == {
        "lock",
        "root",
        "min_share",
        "examples_per_type",
        "excluded_train_utterance_ids",
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_render_is_one_header_plus_one_block_per_intent(schema):
    rendered = render_slurp_intent_slot_schema(schema)
    lines = rendered.split("\n")
    assert lines[0] == ds._SLOT_SCHEMA_HEADER
    blocks = [line for line in lines if line.startswith("== ")]
    assert blocks == [
        "== alarm_set == 104 TRAIN utterances, 104 slot mentions",
        "== weather_query == 2 TRAIN utterances, 0 slot mentions",
    ]
    assert "- time (96.2 percent of slot mentions): filler 0; filler 1;" in rendered
    assert "- date (2.9 percent of slot mentions): tomorrow" in rendered
    assert "no entity type reaches the 2 percent floor" in rendered


def test_render_states_the_verbatim_lowercase_filler_convention(schema):
    header = render_slurp_intent_slot_schema(schema).split("\n")[0]
    assert "exactly as it was spoken" in header
    assert "lower case" in header
    assert "TRAIN" in header


def test_render_selects_only_the_requested_intents(schema):
    rendered = render_slurp_intent_slot_schema(schema, intents=("alarm_set",))
    assert [line for line in rendered.split("\n") if line.startswith("== ")] == [
        "== alarm_set == 104 TRAIN utterances, 104 slot mentions"
    ]
    assert "alarm_set" in rendered and "weather_query" not in rendered
    assert rendered.split("\n")[0] == ds._SLOT_SCHEMA_HEADER
    assert render_slurp_intent_slot_schema(schema, intents=()) == ds._SLOT_SCHEMA_HEADER


def test_render_refuses_an_intent_it_has_no_block_for(schema):
    with pytest.raises(LoaderError, match="no block for intents"):
        render_slurp_intent_slot_schema(schema, intents=("alarm_set", "email_query"))


def test_render_is_deterministic(schema):
    assert render_slurp_intent_slot_schema(schema) == render_slurp_intent_slot_schema(
        schema
    )


def test_no_rendered_line_is_a_substring_of_a_facet_prior_text(schema):
    """The wording separation the ``rails.runner`` control-payload guard needs,
    tested against ``facet:prior`` texts built by ``rails.knowledge_build`` from
    the SAME rows (its own builder, not a copy of its format string)."""

    from speech_aware_evidence_acquisition.rails.knowledge_build import (
        KbRow,
        KnowledgeBuildSpec,
        build_knowledge_snapshot,
    )

    rows = []
    for raw in _train_rows():
        surfaces = {token["id"]: token["surface"] for token in raw["tokens"]}
        fillers: dict[str, list[str]] = {}
        for entity in raw["entities"]:
            fillers.setdefault(entity["type"], []).append(
                " ".join(surfaces[index].lower() for index in entity["span"])
            )
        sample_id = f"slurp:train:{raw['slurp_id']:06d}:audio-{raw['slurp_id']}"
        rows.append(
            KbRow(
                utterance_id=str(raw["slurp_id"]),
                content=raw["sentence"],
                scenario=raw["scenario"],
                action=raw["action"],
                intent=raw["intent"],
                entity_types=tuple(sorted(fillers)),
                entity_fillers={
                    entity_type: tuple(values) for entity_type, values in fillers.items()
                },
                sample_ids=(sample_id,),
                speaker_by_sample_id={sample_id: "speaker-a"},
                media_relpath_by_sample_id={sample_id: f"audio-{raw['slurp_id']}.flac"},
            )
        )
    snapshot = build_knowledge_snapshot(
        KnowledgeBuildSpec(carrier_lock_key="slurp", datastore_size=None, seed=20260823),
        rows=rows,
        forbidden_sample_ids=frozenset(),
    )
    priors = [
        facet.representation
        for facet in snapshot.facets
        if facet.facet_id.startswith("facet:prior:")
    ]
    assert priors, "the fixture must produce at least one facet:prior text"
    rendered = render_slurp_intent_slot_schema(schema)
    for line in rendered.split("\n"):
        for prior in priors:
            assert line not in prior, (line, prior)
    # and the same separation in the direction the runner guard reads
    for prior in priors:
        assert prior.strip().casefold() not in rendered.casefold()


# ---------------------------------------------------------------------------
# The registered fill: a pure suffix of the closed-list bytes
# ---------------------------------------------------------------------------


def test_fill_is_registered_under_its_name():
    assert FILL_NAME in INSTRUCTION_FILLS.names()
    assert (
        INSTRUCTION_FILLS.resolve(FILL_NAME)
        is render_slurp_closed_label_inventory_with_slot_schema
    )


def test_fill_is_a_pure_suffix_of_the_closed_list_fill(slot_world, schema):
    inventory = render_slurp_closed_label_inventory(
        slot_world.lock, slot_world.data_root
    )
    combined = render_slurp_closed_label_inventory_with_slot_schema(
        slot_world.lock, slot_world.data_root
    )
    assert combined.startswith(inventory)
    assert combined[len(inventory) :] == "\n\n" + render_slurp_intent_slot_schema(schema)


def test_fill_keeps_the_closed_list_fill_signature(slot_world):
    rendered = render_slurp_closed_label_inventory_with_slot_schema(
        slot_world.lock, slot_world.data_root
    )
    assert isinstance(rendered, str) and rendered.strip()


# ---------------------------------------------------------------------------
# The per-state renderer
# ---------------------------------------------------------------------------


def _sealed(scenario: str | None, action: str | None) -> str:
    return json.dumps({"scenario": scenario, "action": action, "entities": []})


def test_a_parsed_known_intent_selects_exactly_its_block(slot_world, schema):
    text, used, fallback = render_slurp_slot_schema_for_state_detail(
        slot_world.lock, slot_world.data_root, _sealed("alarm", "set")
    )
    assert used == "alarm_set"
    assert fallback is False
    assert text == render_slurp_intent_slot_schema(schema, intents=("alarm_set",))
    assert "weather_query" not in text
    assert render_slurp_slot_schema_for_state(
        slot_world.lock, slot_world.data_root, _sealed("alarm", "set")
    ) == text


def test_a_fenced_response_still_parses(slot_world):
    fenced = "sure:\n```json\n" + _sealed("alarm", "set") + "\n```\n"
    _text, used, fallback = render_slurp_slot_schema_for_state_detail(
        slot_world.lock, slot_world.data_root, fenced
    )
    assert (used, fallback) == ("alarm_set", False)


@pytest.mark.parametrize(
    "state_content",
    [
        "not json at all",
        "",
        "   ",
        None,
        123,
        json.dumps({"entities": []}),
        _sealed("alarm", None),
        _sealed(None, "set"),
        _sealed("weather", "set"),
        _sealed("unheard", "intent"),
    ],
)
def test_an_unparseable_or_unknown_intent_falls_back_to_the_full_schema(
    slot_world, schema, state_content
):
    text, used, fallback = render_slurp_slot_schema_for_state_detail(
        slot_world.lock, slot_world.data_root, state_content
    )
    assert used is None
    assert fallback is True
    assert text == render_slurp_intent_slot_schema(schema)


def test_slurp_intent_from_state_content_is_the_parser_seam():
    assert slurp_intent_from_state_content(_sealed("alarm", "set")) == "alarm_set"
    assert slurp_intent_from_state_content("nonsense") is None
    assert slurp_intent_from_state_content(None) is None


def test_a_caller_supplied_schema_bypasses_the_cache(slot_world, schema, monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("the per-state renderer must not re-mine TRAIN")

    monkeypatch.setattr(ds, "_cached_intent_slot_schema", refuse)
    text, used, fallback = render_slurp_slot_schema_for_state_detail(
        slot_world.lock, slot_world.data_root, _sealed("alarm", "set"), schema=schema
    )
    assert (used, fallback) == ("alarm_set", False)
    assert text.startswith(ds._SLOT_SCHEMA_HEADER)


def test_the_cache_mines_train_once_per_metadata_directory(slot_world, monkeypatch):
    calls: list[int] = []
    real_loader = ds.load_slurp_intent_slot_schema

    def counting(*args, **kwargs):
        calls.append(1)
        return real_loader(*args, **kwargs)

    monkeypatch.setattr(ds, "load_slurp_intent_slot_schema", counting)
    for _ in range(3):
        render_slurp_slot_schema_for_state(
            slot_world.lock, slot_world.data_root, _sealed("alarm", "set")
        )
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# The receipt
# ---------------------------------------------------------------------------


def test_receipt_document_carries_the_tables_hashes_and_decontamination(schema):
    document = slurp_intent_slot_schema_receipt(schema, generator="unit-test")
    assert document["schema"] == "saea-slurp-intent-slot-schema-v1"
    assert document["generator"] == "unit-test"
    assert document["carrier"] == "slurp"
    construction = document["construction"]
    assert construction["source_split"] == "train"
    assert construction["source_identity_hash"] == schema.source_identity_hash
    assert construction["min_share"] == 0.02
    assert construction["examples_per_type"] == 5
    assert construction["count_unit"] == "entity mention"
    assert "intents" not in construction
    assert document["content_hash"] == schema.content_hash()
    rendered = render_slurp_intent_slot_schema(schema)
    assert document["rendered_full_text"]["sha256"] == hashlib.sha256(
        rendered.encode("utf-8")
    ).hexdigest()
    assert document["rendered_full_text"]["characters"] == len(rendered)
    assert document["totals"]["intents"] == len(schema.intents)
    assert [block["intent"] for block in document["intents"]] == list(schema.intent_ids)
    alarm = document["intents"][0]
    assert alarm["types"][0]["entity_type"] == "time"
    assert alarm["types"][0]["count"] == 100
    assert alarm["types"][0]["fillers"] == ["filler %d" % index for index in range(5)]
    decontamination = document["decontamination"]
    assert decontamination["verdict"] == "clean"
    assert decontamination["cited_receipts"] == list(
        SLURP_INTENT_SLOT_DECONTAMINATION_RECEIPTS
    )
    assert "train.jsonl" in decontamination["statement"]
    # the receipt is canonical-JSON serializable exactly as written to disk
    json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)


def test_committed_receipt_matches_this_repository_rules():
    from speech_aware_evidence_acquisition.data.lock import REPO_ROOT

    document = json.loads(
        (REPO_ROOT / RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    assert document["schema"] == "saea-slurp-intent-slot-schema-v1"
    assert document["generator"] == "scripts/build_slurp_intent_slot_schema.py"
    construction = document["construction"]
    assert construction["schema_id"] == SLURP_INTENT_SLOT_SCHEMA_ID
    assert construction["source_split"] == "train"
    assert construction["min_share"] == ds._INTENT_SLOT_MIN_SHARE
    assert construction["examples_per_type"] == ds._INTENT_SLOT_EXAMPLES_PER_TYPE
    assert len(document["intents"]) == 60
    assert document["decontamination"]["cited_receipts"] == list(
        SLURP_INTENT_SLOT_DECONTAMINATION_RECEIPTS
    )
    for relpath in SLURP_INTENT_SLOT_DECONTAMINATION_RECEIPTS:
        assert (REPO_ROOT / relpath).is_file()
    text = json.dumps(document)
    assert "slurp:devel:" not in text and "slurp:test:" not in text


# ---------------------------------------------------------------------------
# The real corpus
# ---------------------------------------------------------------------------


def _real_corpus():
    from speech_aware_evidence_acquisition.data.lock import (
        data_root,
        umbrella_lock_path,
    )

    try:
        root = data_root()
        lock = load_lock(umbrella_lock_path())
    except Exception as error:  # noqa: BLE001 -- an unmaterialized asset is a skip
        pytest.skip(f"SLURP corpus unavailable: {error}")
    if not (root / "datasets" / "slurp" / "metadata" / "train.jsonl").is_file():
        pytest.skip("SLURP governed train.jsonl is not materialized")
    return lock, root


def test_real_corpus_rendering_carries_no_facet_prior_wording():
    """The cheap half of the separation check on the real corpus: none of the
    ``facet:prior`` representation's own markers survives into the schema text.
    The expensive half -- building the snapshot and comparing every text -- runs
    on the synthetic corpus above, through ``rails.knowledge_build``'s own
    builder, so the format strings under test are the real ones."""

    lock, root = _real_corpus()
    rendered = render_slurp_intent_slot_schema(load_slurp_intent_slot_schema(lock, root))
    assert "Entity-type prior for intent" not in rendered
    assert "from full TRAIN counts" not in rendered
    assert "Exemplar sentence" not in rendered
    assert "surface-form variants observed" not in rendered
    assert not re.search(r"[a-z_]+=0\.\d{4} \(\d+/\d+\)", rendered)


def test_real_corpus_schema_reproduces_the_committed_receipt():
    from speech_aware_evidence_acquisition.data.lock import REPO_ROOT

    lock, root = _real_corpus()
    schema = load_slurp_intent_slot_schema(lock, root)
    document = json.loads((REPO_ROOT / RECEIPT_RELPATH).read_text(encoding="utf-8"))
    assert schema.content_hash() == document["content_hash"]
    assert schema.utterance_count == document["construction"]["utterance_count"]
    assert len(schema.intents) == 60
    rendered = render_slurp_intent_slot_schema(schema)
    assert (
        hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        == document["rendered_full_text"]["sha256"]
    )


# ---------------------------------------------------------------------------
# The projection seam (EVO-S1, preregistration section 4)
# ---------------------------------------------------------------------------


def test_a_projection_repairs_an_illegal_sealed_label_before_the_block_is_picked(
    slot_world, schema
):
    """An illegal sealed pair falls back to the whole schema; the projection
    hands it a block instead.

    The sealed closed-list arm answers a (scenario, action) pair TRAIN never
    carries on 3.9 % of DEV-1000 rows, and every one of those rows is served
    the 26,720-character full-schema fallback. The projection is the same rule
    the re-locked comparator is SCORED through, applied one step earlier -- at
    selection -- so the row gets a per-intent block. It is off by default, so
    an already-flown cell keeps its own selection byte for byte.
    """

    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
        load_legal_intent_inventory,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        project_slu_label_v2,
    )

    inventory = load_legal_intent_inventory(slot_world.lock, slot_world.data_root)

    def project(scenario, action, *, parsed=True):
        return project_slu_label_v2(scenario, action, inventory, parsed=parsed)

    # "set" is a legal ACTION name that only `alarm` owns here, written into
    # the SCENARIO slot -- exactly the confusion v2's promote branch repairs.
    illegal = _sealed("set", "query")
    text, used, fallback = render_slurp_slot_schema_for_state_detail(
        slot_world.lock, slot_world.data_root, illegal
    )
    assert (used, fallback) == (None, True)
    assert text == render_slurp_intent_slot_schema(schema)

    text, used, fallback = render_slurp_slot_schema_for_state_detail(
        slot_world.lock, slot_world.data_root, illegal, projection=project
    )
    assert (used, fallback) == ("alarm_set", False)
    assert text == render_slurp_intent_slot_schema(schema, intents=("alarm_set",))


def test_a_projection_never_moves_a_row_whose_label_is_already_legal(slot_world):
    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (
        load_legal_intent_inventory,
    )
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
        project_slu_label_v2,
    )

    inventory = load_legal_intent_inventory(slot_world.lock, slot_world.data_root)

    def project(scenario, action, *, parsed=True):
        return project_slu_label_v2(scenario, action, inventory, parsed=parsed)

    for content in (_sealed("alarm", "set"), "not json at all", _sealed("alarm", None)):
        plain = render_slurp_slot_schema_for_state_detail(
            slot_world.lock, slot_world.data_root, content
        )
        projected = render_slurp_slot_schema_for_state_detail(
            slot_world.lock, slot_world.data_root, content, projection=project
        )
        assert plain == projected


def test_only_a_registered_projection_id_resolves():
    from speech_aware_evidence_acquisition.rails.phase_material import (
        SLURP_STATE_INTENT_PROJECTIONS,
        PhaseMaterialError,
        _slurp_intent_projection,
    )

    assert _slurp_intent_projection(None) is None
    assert SLURP_STATE_INTENT_PROJECTIONS == (
        "slurp-legal-label-projection-v1",
        "slurp-legal-label-projection-v2",
    )
    with pytest.raises(PhaseMaterialError, match="unknown SLURP intent projection"):
        _slurp_intent_projection("slurp-legal-label-projection-v3")
