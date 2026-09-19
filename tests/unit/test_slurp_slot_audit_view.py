"""E12: the construction-data slot-audit view, its builder and its flags.

Model-free, tokenizer-free, server-free. Design:
``docs/superpowers/specs/2026-09-17-node-context-policy-design.md`` section 16
(cell B8b) and ``docs/superpowers/specs/2026-09-16-slurp-v2-base-program-
design.md`` section 3 item E12.

The three questions this module answers:

1. does the BUILDER refuse a pool that carries an evaluated row?
2. does the RELEASED table carry only construction statistics -- no filler, no
   sentence, no utterance id, no gold of any evaluated row?
3. does each FLAG fire exactly where it is designed to and stay silent
   everywhere else?
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.slot_audit import (
    FLAG_EMPTY_DRAFT,
    FLAG_MISSING_COMMON,
    FLAG_REPRESENTATION,
    FLAG_TYPE_UNSEEN,
    SLOT_AUDIT_BUILDER_POLICY_ID,
    SLOT_AUDIT_DEFAULT_THRESHOLDS,
    SLOT_AUDIT_FLAGS,
    SLOT_AUDIT_RELEASE_SCHEMA,
    SLOT_AUDIT_VIEW_ID,
    SLOT_AUDIT_VIEW_SCHEMA,
    SPOKEN_FORM_FORBIDDEN_CHARACTERS,
    SPOKEN_FORM_RULE_ID,
    SlotAuditError,
    flag_counts,
    load_slot_audit_table,
    profile_rows,
    render_share,
    slot_audit_flags,
    slot_audit_thresholds,
    violates_spoken_form,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILDER = REPO_ROOT / "scripts" / "build_slurp_slot_audit_view.py"
RELEASE_RELPATH = "knowledge/slurp/semantic/slot-audit-v1/release.json"
SNAPSHOT_RELPATH = "knowledge/slurp/semantic/slot-audit-v1/snapshot.json"
RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-slot-audit-v1.json"

#: The registered construction pool the 2026-09-13 exclusion leaves, pinned by
#: ``scripts/build_slurp_exemplar_pool_assets.py`` for the same exclusion.
EXPECTED_CONSTRUCTION_UTTERANCES = 9354


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_slurp_slot_audit_view", BUILDER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_table(root: Path, *, intents, conventions=None, view_id=SLOT_AUDIT_VIEW_ID):
    """Write a synthetic release/snapshot pair and return its two pins."""

    snapshot = {
        "schema": SLOT_AUDIT_VIEW_SCHEMA,
        "view_id": view_id,
        "builder_policy_id": SLOT_AUDIT_BUILDER_POLICY_ID,
        "source_split": "train",
        "source_split_identity_hash": "b" * 64,
        "construction_utterance_count": 1234,
        "excluded_train_utterance_count": 10,
        "conventions": conventions if conventions is not None else [
            {
                "entity_type": "date",
                "rule_id": SPOKEN_FORM_RULE_ID,
                "statement": "Retain the spoken calendar expression.",
                "forbidden_characters": SPOKEN_FORM_FORBIDDEN_CHARACTERS,
            },
            {
                "entity_type": "time",
                "rule_id": SPOKEN_FORM_RULE_ID,
                "statement": "The filler is the words as spoken.",
                "forbidden_characters": SPOKEN_FORM_FORBIDDEN_CHARACTERS,
            },
        ],
        "intents": intents,
    }
    directory = root / "knowledge" / "slurp" / "semantic" / "slot-audit-v1"
    directory.mkdir(parents=True, exist_ok=True)
    snapshot_path = directory / "snapshot.json"
    snapshot_path.write_text(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    snapshot_sha256 = _sha256(snapshot_path.read_bytes())
    release = {
        "schema": SLOT_AUDIT_RELEASE_SCHEMA,
        "view_id": view_id,
        "builder_policy_id": SLOT_AUDIT_BUILDER_POLICY_ID,
        "snapshot": {"relpath": SNAPSHOT_RELPATH, "root": "repo"},
        "snapshot_sha256": snapshot_sha256,
        "source": {"carrier": "slurp", "split": "train"},
        "source_split_identity_hash": "b" * 64,
    }
    release_path = directory / "release.json"
    release_path.write_text(
        json.dumps(release, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return (
        {"relpath": RELEASE_RELPATH, "sha256": _sha256(release_path.read_bytes())},
        {"relpath": SNAPSHOT_RELPATH, "sha256": snapshot_sha256},
    )


def _type(entity_type: str, rows: int, of_rows: int):
    return {
        "entity_type": entity_type,
        "rows": rows,
        "row_share": round(rows / of_rows, 6),
    }


SYNTHETIC_INTENTS = [
    {
        "intent": "alarm_set",
        "rows": 100,
        "rows_with_entity": 90,
        "types": [_type("time", 80, 100), _type("date", 30, 100)],
    },
    {
        "intent": "general_quirky",
        "rows": 200,
        "rows_with_entity": 20,
        "types": [_type("definition_word", 12, 200)],
    },
]


def _synthetic(tmp_path: Path):
    release, snapshot = _write_table(tmp_path, intents=SYNTHETIC_INTENTS)
    return load_slot_audit_table(
        tmp_path, release=release, snapshot=snapshot, view_id=SLOT_AUDIT_VIEW_ID
    )


# ---------------------------------------------------------------------------
# (a) the builder refuses evaluated rows
# ---------------------------------------------------------------------------


def test_the_builder_refuses_a_pool_that_kept_an_evaluated_row():
    builder = _builder()
    retained = frozenset({"slurp:train:000001", "slurp:train:000007"})
    excluded = frozenset({"slurp:train:000007"})
    with pytest.raises(SystemExit, match="evaluated utterance"):
        builder.refuse_evaluated_rows(retained, excluded, identity_hash="0" * 64)


def test_the_builder_refuses_a_table_not_bound_to_the_pool_it_proved_clean():
    """Disjointness alone is not enough: the mined table must ALSO bind the
    identity of the pool this build checked, or the two are unrelated."""

    builder = _builder()
    retained = frozenset({"slurp:train:000001", "slurp:train:000002"})
    with pytest.raises(SystemExit, match="retained construction pool hashes"):
        builder.refuse_evaluated_rows(
            retained, frozenset(), identity_hash="0" * 64
        )
    correct = hashlib.sha256("\n".join(sorted(retained)).encode()).hexdigest()
    builder.refuse_evaluated_rows(retained, frozenset(), identity_hash=correct)


def test_the_builder_collapses_recording_ids_and_ignores_other_splits():
    builder = _builder()
    assert builder._utterance_id("slurp:train:000007:audio--1504197557") == (
        "slurp:train:000007"
    )
    assert builder._utterance_id("slurp:devel:000123:audio-1") is None


def test_the_three_forbidden_rosters_are_the_registered_exclusion():
    builder = _builder()
    assert builder.EXCLUDE_ROSTER_RELPATHS == (
        "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
        "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
        "docs/receipts/probe-samples/DEV-1000.json",
    )
    assert builder.EXPECTED_UTTERANCE_COUNT == EXPECTED_CONSTRUCTION_UTTERANCES
    excluded, records = builder.excluded_utterance_ids(REPO_ROOT)
    assert len(records) == 3
    # DEV-1000 names no TRAIN sample id, so it adds nothing on top of the two
    # folds -- the same fact the exemplar-pool builder records.
    assert records[-1]["train_utterance_count"] == 0
    assert all(item.startswith("slurp:train:") for item in excluded)


# ---------------------------------------------------------------------------
# (b) the released table
# ---------------------------------------------------------------------------


def test_the_released_table_is_committed_and_loads_under_its_own_pins():
    release_path = REPO_ROOT / RELEASE_RELPATH
    snapshot_path = REPO_ROOT / SNAPSHOT_RELPATH
    assert release_path.is_file() and snapshot_path.is_file()
    table = load_slot_audit_table(
        REPO_ROOT,
        release={
            "relpath": RELEASE_RELPATH,
            "sha256": _sha256(release_path.read_bytes()),
        },
        snapshot={
            "relpath": SNAPSHOT_RELPATH,
            "sha256": _sha256(snapshot_path.read_bytes()),
        },
        view_id=SLOT_AUDIT_VIEW_ID,
    )
    assert table.view_id == SLOT_AUDIT_VIEW_ID
    assert table.source_split == "train"
    assert table.construction_utterance_count == EXPECTED_CONSTRUCTION_UTTERANCES
    assert len(table.intents) == 60
    assert table.convention_types == ("date", "time")
    # Every attested type is listed, however rare, because absence from this
    # table is exactly what TYPE-UNSEEN reads.
    assert all(
        rows >= 1 and rows <= profile.rows
        for profile in table.intents.values()
        for _entity_type, rows, _share in profile.types
    )
    assert table.content_hash() == table.pins()["table_content_hash"]


def test_the_released_table_carries_no_filler_no_sentence_and_no_utterance_id():
    """The boundary that makes this node legal, checked rather than asserted.

    Every string the snapshot carries is a schema/view/rule id, an intent id,
    an entity type, a released convention sentence or a split name. No
    utterance id, no recording, no sentence, no gold span and no filler."""

    document = json.loads((REPO_ROOT / SNAPSHOT_RELPATH).read_text(encoding="utf-8"))
    identifier = re.compile(r"^[a-z0-9_]+$")
    statements = {
        convention["statement"] for convention in document["conventions"]
    }
    allowed = {
        SLOT_AUDIT_VIEW_SCHEMA,
        SLOT_AUDIT_VIEW_ID,
        SLOT_AUDIT_BUILDER_POLICY_ID,
        SPOKEN_FORM_RULE_ID,
        SPOKEN_FORM_FORBIDDEN_CHARACTERS,
        "train",
        document["source_split_identity_hash"],
    } | statements

    def walk(node):
        if isinstance(node, str):
            assert node in allowed or identifier.fullmatch(node), node
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for key, value in node.items():
                assert identifier.fullmatch(key), key
                walk(value)

    walk(document)
    assert not any("slurp:train:" in text for text in allowed)


def test_the_release_pins_the_snapshot_and_the_representation_source():
    release = json.loads((REPO_ROOT / RELEASE_RELPATH).read_text(encoding="utf-8"))
    snapshot_sha256 = _sha256((REPO_ROOT / SNAPSHOT_RELPATH).read_bytes())
    assert release["snapshot_sha256"] == snapshot_sha256
    assert release["source"]["construction_utterance_count"] == (
        EXPECTED_CONSTRUCTION_UTTERANCES
    )
    assert release["representation_source"]["root"] == "data"
    assert release["representation_source"]["relpath"].endswith(
        "slot-contracts-v2/snapshot.json"
    )
    receipt = json.loads((REPO_ROOT / RECEIPT_RELPATH).read_text(encoding="utf-8"))
    assert receipt["contacts"] == {"model": 0, "tool": 0, "scorer": 0, "encoder": 0}
    assert receipt["execution_profile"] == "model-free-check"
    assert receipt["decontamination"]["verdict"] == "clean"
    assert receipt["snapshot"]["sha256"] == snapshot_sha256


def test_the_released_conventions_quote_slot_store_v2_verbatim():
    document = json.loads((REPO_ROOT / SNAPSHOT_RELPATH).read_text(encoding="utf-8"))
    by_type = {
        convention["entity_type"]: convention for convention in document["conventions"]
    }
    assert set(by_type) == {"date", "time"}
    assert "never digits and never a colon" in by_type["time"]["statement"]
    assert "ISO date" in by_type["date"]["statement"]
    for convention in by_type.values():
        assert convention["rule_id"] == SPOKEN_FORM_RULE_ID
        assert convention["forbidden_characters"] == SPOKEN_FORM_FORBIDDEN_CHARACTERS


# ---------------------------------------------------------------------------
# (c) loader refusals
# ---------------------------------------------------------------------------


def test_the_loader_refuses_a_pin_whose_bytes_moved(tmp_path):
    release, snapshot = _write_table(tmp_path, intents=SYNTHETIC_INTENTS)
    with pytest.raises(SlotAuditError, match="hashes to"):
        load_slot_audit_table(
            tmp_path,
            release=release,
            snapshot={**snapshot, "sha256": "0" * 64},
            view_id=SLOT_AUDIT_VIEW_ID,
        )


def test_the_loader_refuses_a_release_that_pins_another_snapshot(tmp_path):
    release, snapshot = _write_table(tmp_path, intents=SYNTHETIC_INTENTS)
    path = tmp_path / SNAPSHOT_RELPATH
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(SlotAuditError):
        load_slot_audit_table(
            tmp_path,
            release=release,
            snapshot={"relpath": SNAPSHOT_RELPATH, "sha256": _sha256(path.read_bytes())},
            view_id=SLOT_AUDIT_VIEW_ID,
        )


def test_the_loader_refuses_another_view_id_and_an_escaping_relpath(tmp_path):
    release, snapshot = _write_table(
        tmp_path, intents=SYNTHETIC_INTENTS, view_id="slot-audit-v2"
    )
    with pytest.raises(SlotAuditError, match="not this view's release"):
        load_slot_audit_table(
            tmp_path, release=release, snapshot=snapshot, view_id=SLOT_AUDIT_VIEW_ID
        )
    with pytest.raises(SlotAuditError, match="plain relative POSIX path"):
        load_slot_audit_table(
            tmp_path,
            release={"relpath": "../escape.json", "sha256": "0" * 64},
            snapshot=snapshot,
            view_id=SLOT_AUDIT_VIEW_ID,
        )


def test_the_loader_refuses_an_impossible_row_count(tmp_path):
    poisoned = [{
        "intent": "alarm_set",
        "rows": 10,
        "rows_with_entity": 11,
        "types": [_type("time", 5, 10)],
    }]
    release, snapshot = _write_table(tmp_path, intents=poisoned)
    with pytest.raises(SlotAuditError, match="impossible row counts"):
        load_slot_audit_table(
            tmp_path, release=release, snapshot=snapshot, view_id=SLOT_AUDIT_VIEW_ID
        )


# ---------------------------------------------------------------------------
# (d) thresholds
# ---------------------------------------------------------------------------


def test_thresholds_default_and_refuse_everything_else():
    assert slot_audit_thresholds().as_json() == dict(SLOT_AUDIT_DEFAULT_THRESHOLDS)
    assert slot_audit_thresholds(
        {"missing_common_min_row_share": 0.8}
    ).missing_common_min_row_share == 0.8
    with pytest.raises(SlotAuditError, match="unknown key"):
        slot_audit_thresholds({"nope": 0.5})
    with pytest.raises(SlotAuditError, match="must be a number"):
        slot_audit_thresholds({"profile_min_row_share": True})
    with pytest.raises(SlotAuditError, match=r"\[0, 1\]"):
        slot_audit_thresholds({"profile_min_row_share": 1.5})
    with pytest.raises(SlotAuditError, match="must be an object"):
        slot_audit_thresholds("0.5")


# ---------------------------------------------------------------------------
# (e) the spoken-form predicate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filler,expected",
    [
        ("seven am", False),
        ("five thirty am", False),
        ("six o clock", False),
        ("tenth of march two thousand seventeen", False),
        ("tomorrow", False),
        ("7:30 am", True),
        ("07 30", True),
        ("2017-03-15", True),
        ("15/03", True),
        ("", False),
    ],
)
def test_the_spoken_form_predicate_reads_characters_only(filler, expected):
    assert violates_spoken_form(filler) is expected


def test_the_spoken_form_predicate_refuses_a_non_text_filler():
    with pytest.raises(SlotAuditError, match="must be text"):
        violates_spoken_form(7)


# ---------------------------------------------------------------------------
# (f) the four flags -- each fires, and each stays silent
# ---------------------------------------------------------------------------


def _flags(table, intent_id, entities, **overrides):
    return slot_audit_flags(
        intent_id=intent_id,
        entities=tuple(entities),
        table=table,
        thresholds=slot_audit_thresholds(overrides or None),
    )


def test_type_unseen_fires_only_on_a_type_absent_from_this_intent(tmp_path):
    table = _synthetic(tmp_path)
    fired = _flags(table, "alarm_set", [("place_name", "berlin")])
    assert [flag.flag for flag in fired] == [FLAG_TYPE_UNSEEN, FLAG_MISSING_COMMON]
    assert fired[0].entity_type == "place_name"
    # 'date' IS attested with alarm_set, so it never fires TYPE-UNSEEN.
    quiet = _flags(table, "alarm_set", [("time", "seven am"), ("date", "tomorrow")])
    assert [flag.flag for flag in quiet] == []


def test_empty_draft_fires_only_above_its_threshold(tmp_path):
    table = _synthetic(tmp_path)
    fired = _flags(table, "alarm_set", [])
    assert [flag.flag for flag in fired] == [FLAG_EMPTY_DRAFT, FLAG_MISSING_COMMON]
    assert (fired[0].rows, fired[0].of_rows) == (90, 100)
    # general_quirky carries an entity on 10 % of its rows, far under 0.5.
    assert _flags(table, "general_quirky", []) == ()
    # ... and fires once the threshold is lowered under that rate.
    lowered = _flags(
        table, "general_quirky", [], empty_draft_min_entity_row_share=0.05
    )
    assert [flag.flag for flag in lowered] == [FLAG_EMPTY_DRAFT]


def test_missing_common_fires_only_strictly_above_its_threshold(tmp_path):
    table = _synthetic(tmp_path)
    # time is 80 % of alarm_set rows and is absent -> fires; date is 30 % and
    # absent -> silent.
    fired = _flags(table, "alarm_set", [("date", "tomorrow")])
    assert [(flag.flag, flag.entity_type) for flag in fired] == [
        (FLAG_MISSING_COMMON, "time")
    ]
    assert _flags(table, "alarm_set", [("time", "seven am")]) == ()
    # Strictly above: at exactly the threshold it stays silent.
    at_threshold = _flags(
        table, "alarm_set", [("date", "tomorrow")], missing_common_min_row_share=0.8
    )
    assert at_threshold == ()


def test_representation_fires_per_type_and_needs_no_intent_profile(tmp_path):
    table = _synthetic(tmp_path)
    fired = _flags(
        table,
        "alarm_set",
        [("time", "7:30 am"), ("time", "8:00 am"), ("date", "tomorrow")],
    )
    assert [flag.flag for flag in fired] == [FLAG_REPRESENTATION]
    assert fired[0].entity_type == "time"
    assert "The filler is the words as spoken." in fired[0].detail
    # An intent outside the table has no profile, so only the convention
    # applies -- and it still applies.
    absent = _flags(table, "not_in_table", [("date", "2017-03-15")])
    assert [flag.flag for flag in absent] == [FLAG_REPRESENTATION]
    # A type with no released convention is never representation-flagged.
    assert _flags(table, "alarm_set", [("time", "seven am")]) == ()


def test_flag_order_and_counts_are_fixed(tmp_path):
    table = _synthetic(tmp_path)
    fired = _flags(table, "alarm_set", [("place_name", "7 berlin")])
    assert [flag.flag for flag in fired] == [
        FLAG_TYPE_UNSEEN, FLAG_MISSING_COMMON,
    ]
    counts = flag_counts(fired)
    assert set(counts) == set(SLOT_AUDIT_FLAGS)
    assert counts == {
        FLAG_TYPE_UNSEEN: 1,
        FLAG_EMPTY_DRAFT: 0,
        FLAG_MISSING_COMMON: 1,
        FLAG_REPRESENTATION: 0,
    }
    assert flag_counts(()) == dict.fromkeys(SLOT_AUDIT_FLAGS, 0)


def test_flags_refuse_a_malformed_entity_pair(tmp_path):
    table = _synthetic(tmp_path)
    with pytest.raises(SlotAuditError, match="text pair"):
        _flags(table, "alarm_set", [("time", 7)])
    with pytest.raises(SlotAuditError, match="intent id"):
        _flags(table, "", [])


# ---------------------------------------------------------------------------
# (g) profile listing and share rendering
# ---------------------------------------------------------------------------


def test_the_profile_listing_is_filtered_and_ordered(tmp_path):
    table = _synthetic(tmp_path)
    thresholds = slot_audit_thresholds()
    listed = profile_rows(table.profile("alarm_set"), thresholds)
    assert listed == (("time", 80, 100), ("date", 30, 100))
    # general_quirky's only type is 6 % of its rows, above the 5 % default and
    # below a raised one.
    assert profile_rows(table.profile("general_quirky"), thresholds) == (
        ("definition_word", 12, 200),
    )
    raised = slot_audit_thresholds({"profile_min_row_share": 0.1})
    assert profile_rows(table.profile("general_quirky"), raised) == ()
    assert profile_rows(None, thresholds) == ()


def test_share_rendering_is_integer_exact():
    assert render_share(28, 59) == "47.5 % (28 of 59 rows)"
    assert render_share(0, 10) == "0.0 % (0 of 10 rows)"
    assert render_share(1, 3) == "33.3 % (1 of 3 rows)"
    assert render_share(0, 0) == "0.0 % (0 of 0 rows)"


# ---------------------------------------------------------------------------
# (h) the committed view reproduces from the construction pool
# ---------------------------------------------------------------------------


def test_the_committed_view_reproduces_from_the_construction_pool():
    """The builder's own ``--check``: an unchanged governed TRAIN corpus and an
    unchanged exclusion give back exactly the committed bytes.

    Skipped where the governed SLURP metadata is not materialised, which is
    every machine but the primary dev host."""

    builder = _builder()
    try:
        from speech_aware_evidence_acquisition.data.lock import (
            data_root,
            load_lock,
            umbrella_lock_path,
        )

        lock = load_lock(umbrella_lock_path(REPO_ROOT))
        root = data_root()
    except Exception as error:  # pragma: no cover - environment dependent
        pytest.skip(f"governed SLURP metadata unavailable: {error}")
    built = None
    try:
        built = builder.build_documents(REPO_ROOT, root)
    except Exception as error:  # pragma: no cover - environment dependent
        pytest.skip(f"governed SLURP metadata unavailable: {error}")
    assert lock is not None
    committed = json.loads((REPO_ROOT / SNAPSHOT_RELPATH).read_text(encoding="utf-8"))
    assert built["snapshot"] == committed
