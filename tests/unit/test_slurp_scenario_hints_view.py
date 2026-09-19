"""E14: the construction-data scenario-hints view, its builder and its rule.

Model-free, tokenizer-free, encoder-free, server-free. Design:
``docs/superpowers/specs/2026-09-17-node-context-policy-design.md`` sections 16
and 16.2 (cell B8c).

The four questions this module answers:

1. does the BUILDER refuse a pool that carries an evaluated row, or a pool that
   the E12 slot-audit receipt does not recognise?
2. is the DERIVATION RULE what it says it is -- leave-one-out k-NN leakage,
   document-scoped cue frequencies, a ``+1``-prior log-odds, a count floor?
3. does the LOADER refuse a table whose pins, schema, identity or declared rule
   is not this module's?
4. does the RELEASED table carry only construction statistics and construction
   cue words -- no utterance id, no sentence, no recording, no filler and no
   gold of any evaluated row?
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
from pathlib import Path

import numpy as np
import pytest

from speech_aware_evidence_acquisition.rails.scenario_hints import (
    CUE_LIMIT,
    CUE_MIN_ROWS,
    CUE_PRIOR,
    NEIGHBOUR_K,
    NEIGHBOUR_LIMIT,
    NEIGHBOUR_MIN_LEAKAGE_SHARE,
    SCENARIO_HINTS_BUILDER_POLICY_ID,
    SCENARIO_HINTS_MAX_CANDIDATES,
    SCENARIO_HINTS_RELEASE_SCHEMA,
    SCENARIO_HINTS_VIEW_ID,
    SCENARIO_HINTS_VIEW_SCHEMA,
    STOPWORDS,
    ScenarioHintsError,
    cue_log_odds,
    hint_counts,
    is_cue_candidate,
    load_scenario_hints_table,
    render_cues,
    render_leakage,
    scenario_hints,
    scenario_hints_bounds,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILDER = REPO_ROOT / "scripts" / "build_slurp_scenario_hints_view.py"

NAMESPACE = "knowledge/slurp/semantic/scenario-hints-v1"
SNAPSHOT_RELPATH = f"{NAMESPACE}/snapshot.json"
RELEASE_RELPATH = f"{NAMESPACE}/release.json"
COMPLETION_RELPATH = f"{NAMESPACE}/completion.json"
RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-scenario-hints-v1.json"

#: The registered construction pool the 2026-09-13 exclusion leaves, pinned by
#: ``scripts/build_slurp_exemplar_pool_assets.py`` and by the E12 slot-audit
#: receipt for the same exclusion.
EXPECTED_CONSTRUCTION_UTTERANCES = 9354
EXPECTED_INTENTS = 60

_DATA_ROOT = os.environ.get("SPEECHRL_DATA_DIR", "").strip()


def _released_root() -> Path | None:
    if not _DATA_ROOT:
        return None
    root = Path(_DATA_ROOT)
    return root if (root / SNAPSHOT_RELPATH).is_file() else None


released = pytest.mark.skipif(
    _released_root() is None,
    reason="the scenario-hints view is not released under SPEECHRL_DATA_DIR",
)


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_slurp_scenario_hints_view", BUILDER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return _sha256(path.read_bytes())


def cue(word: str, rows: int = CUE_MIN_ROWS, neighbour_rows: int = 0) -> dict:
    return {
        "word": word,
        "rows": rows,
        "neighbour_rows": neighbour_rows,
        "log_odds": 1.5,
    }


def neighbour(intent: str, leaked: int, rows: int, cues=()) -> dict:
    of_neighbours = rows * NEIGHBOUR_K
    return {
        "intent": intent,
        "leaked": leaked,
        "of_neighbours": of_neighbours,
        "leakage_share": round(leaked / of_neighbours, 6),
        "cues": list(cues),
    }


def profile(intent: str, rows: int, neighbours=()) -> dict:
    return {"intent": intent, "rows": rows, "neighbours": list(neighbours)}


def write_table(
    root: Path,
    *,
    intents,
    view_id: str = SCENARIO_HINTS_VIEW_ID,
    identity: str = "c" * 64,
    policy_overrides=None,
    snapshot_overrides=None,
    release_overrides=None,
):
    """Write a synthetic release/snapshot pair and return its two pins."""

    policy = {
        "k": NEIGHBOUR_K,
        "min_leakage_share": NEIGHBOUR_MIN_LEAKAGE_SHARE,
        "max_neighbours": NEIGHBOUR_LIMIT,
        "max_cues": CUE_LIMIT,
        "cue_min_rows": CUE_MIN_ROWS,
        "cue_prior": CUE_PRIOR,
        "similarity": "cosine",
        "leave_one_out": True,
    }
    policy.update(policy_overrides or {})
    snapshot = {
        "schema": SCENARIO_HINTS_VIEW_SCHEMA,
        "view_id": view_id,
        "builder_policy_id": SCENARIO_HINTS_BUILDER_POLICY_ID,
        "source_split": "train",
        "source_split_identity_hash": identity,
        "construction_utterance_count": EXPECTED_CONSTRUCTION_UTTERANCES,
        "excluded_train_utterance_count": 2160,
        "neighbour_policy": policy,
        "intents": list(intents),
    }
    snapshot.update(snapshot_overrides or {})
    snapshot_sha256 = _write_json(root / SNAPSHOT_RELPATH, snapshot)
    release = {
        "schema": SCENARIO_HINTS_RELEASE_SCHEMA,
        "view_id": view_id,
        "builder_policy_id": SCENARIO_HINTS_BUILDER_POLICY_ID,
        "snapshot": {"relpath": SNAPSHOT_RELPATH, "root": "data"},
        "snapshot_sha256": snapshot_sha256,
        "source_split_identity_hash": identity,
    }
    release.update(release_overrides or {})
    release_sha256 = _write_json(root / RELEASE_RELPATH, release)
    return (
        {"relpath": RELEASE_RELPATH, "root": "data", "sha256": release_sha256},
        {"relpath": SNAPSHOT_RELPATH, "root": "data", "sha256": snapshot_sha256},
    )


def load(root: Path, pins):
    release_pin, snapshot_pin = pins
    return load_scenario_hints_table(
        root,
        release=release_pin,
        snapshot=snapshot_pin,
        view_id=SCENARIO_HINTS_VIEW_ID,
    )


# ---------------------------------------------------------------------------
# 1. The builder's own falsifiers
# ---------------------------------------------------------------------------


def test_refuse_evaluated_rows_refuses_a_pool_that_kept_one():
    builder = _builder()
    retained = frozenset({"slurp:train:000001", "slurp:train:000002"})
    excluded = frozenset({"slurp:train:000002"})
    with pytest.raises(SystemExit, match="survived the construction exclusion"):
        builder.refuse_evaluated_rows(retained, excluded, identity_hash="0" * 64)


def test_refuse_evaluated_rows_refuses_a_table_not_bound_to_its_pool():
    builder = _builder()
    retained = frozenset({"slurp:train:000001"})
    clean_identity = _sha256("slurp:train:000001".encode("utf-8"))
    builder.refuse_evaluated_rows(
        retained, frozenset(), identity_hash=clean_identity
    )
    with pytest.raises(SystemExit, match="not bound to the pool"):
        builder.refuse_evaluated_rows(retained, frozenset(), identity_hash="0" * 64)


def test_the_builder_binds_the_same_pool_the_e12_receipt_pins():
    """The cheapest possible proof that two independent builders mined the
    SAME construction pool: E12's receipt and this build must agree on the
    identity hash, the utterance count and the exclusion count."""

    builder = _builder()
    receipt = json.loads(
        (REPO_ROOT / builder.POOL_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    identity = receipt["source_split_identity_hash"]
    utterances = receipt["totals"]["construction_utterances"]
    excluded = receipt["decontamination"]["excluded_train_utterance_count"]
    assert utterances == EXPECTED_CONSTRUCTION_UTTERANCES
    agreement = builder.pool_receipt_agreement(
        REPO_ROOT,
        identity_hash=identity,
        utterance_count=utterances,
        excluded_count=excluded,
    )
    assert agreement["relpath"] == builder.POOL_RECEIPT_RELPATH
    assert re.fullmatch(r"[0-9a-f]{64}", agreement["sha256"])
    with pytest.raises(SystemExit, match="disagrees with the E12 receipt"):
        builder.pool_receipt_agreement(
            REPO_ROOT,
            identity_hash="0" * 64,
            utterance_count=utterances,
            excluded_count=excluded,
        )


def test_the_builder_quotes_the_same_exclusion_as_the_e12_view():
    builder = _builder()
    assert builder.EXPECTED_UTTERANCE_COUNT == EXPECTED_CONSTRUCTION_UTTERANCES
    assert builder.EXPECTED_INTENT_COUNT == EXPECTED_INTENTS
    assert builder.EXCLUDE_ROSTER_RELPATHS == (
        "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
        "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
        "docs/receipts/probe-samples/DEV-1000.json",
    )
    for relpath in builder.EXCLUDE_ROSTER_RELPATHS:
        assert (REPO_ROOT / relpath).is_file()


# ---------------------------------------------------------------------------
# 2. The derivation rule
# ---------------------------------------------------------------------------


def test_neighbour_leakage_is_leave_one_out_and_chunk_independent():
    builder = _builder()
    rows = 40
    rng = np.random.default_rng(20260919)
    matrix = rng.normal(size=(rows, 8))
    matrix /= np.linalg.norm(matrix, axis=1)[:, None]
    intents = tuple("ab"[index % 2] + "_x" for index in range(rows))
    first = builder.neighbour_leakage(matrix.copy(), intents)
    original = builder.SIMILARITY_CHUNK_ROWS
    try:
        builder.SIMILARITY_CHUNK_ROWS = 7
        second = builder.neighbour_leakage(matrix.copy(), intents)
    finally:
        builder.SIMILARITY_CHUNK_ROWS = original
    assert first == second
    # Leave-one-out: every row contributes exactly k neighbours, none itself.
    for intent, counts in first.items():
        own_rows = sum(1 for value in intents if value == intent)
        assert sum(counts.values()) <= own_rows * NEIGHBOUR_K
        assert intent not in counts


def test_a_row_is_never_its_own_neighbour_even_when_every_vector_is_equal():
    """Identical vectors are the hardest determinism case: every similarity
    ties, so the order is decided entirely by the stable sort's index rule."""

    builder = _builder()
    matrix = np.zeros((12, 4))
    matrix[:, 0] = 1.0
    intents = tuple("a_x" if index < 6 else "b_x" for index in range(12))
    leak = builder.neighbour_leakage(matrix, intents)
    assert set(leak) == {"a_x", "b_x"}
    for intent, counts in leak.items():
        assert intent not in counts
    # Every tie breaks by ascending index, so each row's k = 10 neighbours are
    # the ten lowest OTHER indices. An ``a_x`` row (index 0-5) therefore keeps
    # five ``a_x`` siblings and five ``b_x`` rows; a ``b_x`` row (index 6-11)
    # keeps all six ``a_x`` rows and four ``b_x`` siblings.
    assert leak["a_x"] == {"b_x": 6 * 5}
    assert leak["b_x"] == {"a_x": 6 * 6}
    assert builder.neighbour_leakage(matrix, intents) == leak


def test_document_frequencies_count_utterances_not_tokens():
    builder = _builder()
    intents = ("alarm_set", "alarm_set", "calendar_query")
    tokens = (
        ("wake", "wake", "wake", "up"),
        ("wake", "up"),
        ("meeting", "tomorrow"),
    )
    frequencies, rows = builder.document_frequencies(intents, tokens)
    assert rows == {"alarm_set": 2, "calendar_query": 1}
    # "wake" occurs three times in one row and once in another: df is 2, not 4.
    assert frequencies["alarm_set"]["wake"] == 2
    # "up" is a stopword and never becomes a candidate at all.
    assert "up" in STOPWORDS
    assert "up" not in frequencies["alarm_set"]


def test_pair_cues_respect_the_count_floor_the_limit_and_the_order():
    builder = _builder()
    frequencies = {
        "alarm_set": {
            "wake": 40, "snooze": 30, "buzzer": 20, "rare": CUE_MIN_ROWS - 1,
            "shared": 25,
        },
        "alarm_remove": {"shared": 25, "cancel": 30},
    }
    rows = {"alarm_set": 100, "alarm_remove": 100}
    cues = builder.pair_cues("alarm_set", "alarm_remove", frequencies, rows)
    assert len(cues) == CUE_LIMIT
    words = [entry["word"] for entry in cues]
    assert "rare" not in words  # below the document-count floor
    assert words == ["wake", "snooze", "buzzer"]  # descending log-odds
    assert [entry["log_odds"] for entry in cues] == sorted(
        (entry["log_odds"] for entry in cues), reverse=True
    )
    assert cues[0]["neighbour_rows"] == 0


def test_cue_log_odds_is_the_declared_plus_one_prior_formula():
    measured = cue_log_odds(40, 100, 10, 100)
    expected = math.log((40 + CUE_PRIOR) / (60 + CUE_PRIOR)) - math.log(
        (10 + CUE_PRIOR) / (90 + CUE_PRIOR)
    )
    assert measured == pytest.approx(expected)
    # Symmetry: swapping the two sides negates the score.
    assert cue_log_odds(10, 100, 40, 100) == pytest.approx(-expected)
    with pytest.raises(ScenarioHintsError):
        cue_log_odds(200, 100, 0, 100)
    with pytest.raises(ScenarioHintsError):
        cue_log_odds(True, 100, 0, 100)


@pytest.mark.parametrize(
    "word, accepted",
    [
        ("wake", True),
        ("o'clock", True),
        ("the", False),      # a stopword
        ("a", False),        # below the length floor and a stopword
        ("7am", False),      # carries a digit
        ("", False),
        ("Wake", False),     # never upper-case: the builder lower-cases first
    ],
)
def test_is_cue_candidate_is_characters_and_a_closed_list(word, accepted):
    assert is_cue_candidate(word) is accepted


# ---------------------------------------------------------------------------
# 3. The loader's refusals, over synthetic tables
# ---------------------------------------------------------------------------


def test_a_synthetic_table_round_trips(tmp_path):
    pins = write_table(tmp_path, intents=[
        profile("alarm_set", 100, [
            neighbour("alarm_remove", 120, 100, [cue("wake", 40, 3)]),
        ]),
        profile("calendar_query", 50),
    ])
    table = load(tmp_path, pins)
    assert table.view_id == SCENARIO_HINTS_VIEW_ID
    assert table.intent_ids == ("alarm_set", "calendar_query")
    assert table.neighbour_k == NEIGHBOUR_K
    assert table.min_leakage_share == NEIGHBOUR_MIN_LEAKAGE_SHARE
    entry = table.profile("alarm_set").neighbours[0]
    assert entry.intent == "alarm_remove"
    assert entry.leakage_share == round(120 / 1000, 6)
    assert [item.word for item in entry.cues] == ["wake"]
    assert table.profile("calendar_query").neighbours == ()
    assert table.profile("absent_intent") is None
    assert re.fullmatch(r"[0-9a-f]{64}", table.content_hash())
    assert set(table.pins()) == {
        "release_sha256", "snapshot_sha256", "table_content_hash",
    }


def test_a_tampered_snapshot_is_refused(tmp_path):
    pins = write_table(tmp_path, intents=[profile("alarm_set", 10)])
    path = tmp_path / SNAPSHOT_RELPATH
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ScenarioHintsError, match="hashes to"):
        load(tmp_path, pins)


def test_a_pin_outside_the_namespace_or_root_is_refused(tmp_path):
    release_pin, snapshot_pin = write_table(
        tmp_path, intents=[profile("alarm_set", 10)]
    )
    with pytest.raises(ScenarioHintsError, match="must be a plain relative"):
        load_scenario_hints_table(
            tmp_path,
            release={**release_pin, "relpath": "elsewhere/release.json"},
            snapshot=snapshot_pin,
            view_id=SCENARIO_HINTS_VIEW_ID,
        )
    with pytest.raises(ScenarioHintsError, match="root must be"):
        load_scenario_hints_table(
            tmp_path,
            release={**release_pin, "root": "repo"},
            snapshot=snapshot_pin,
            view_id=SCENARIO_HINTS_VIEW_ID,
        )
    with pytest.raises(ScenarioHintsError, match="exactly relpath, root and sha256"):
        load_scenario_hints_table(
            tmp_path,
            release={"relpath": RELEASE_RELPATH, "sha256": release_pin["sha256"]},
            snapshot=snapshot_pin,
            view_id=SCENARIO_HINTS_VIEW_ID,
        )


def test_another_view_id_or_an_unpinned_snapshot_is_refused(tmp_path):
    pins = write_table(
        tmp_path, intents=[profile("alarm_set", 10)], view_id="scenario-hints-v2",
    )
    with pytest.raises(ScenarioHintsError, match="is not this view's release"):
        load(tmp_path, pins)
    pins = write_table(
        tmp_path,
        intents=[profile("alarm_set", 10)],
        release_overrides={"snapshot_sha256": "0" * 64},
    )
    with pytest.raises(ScenarioHintsError, match="does not pin the declared snapshot"):
        load(tmp_path, pins)


def test_a_release_and_snapshot_that_disagree_on_identity_are_refused(tmp_path):
    pins = write_table(
        tmp_path,
        intents=[profile("alarm_set", 10)],
        release_overrides={"source_split_identity_hash": "d" * 64},
    )
    with pytest.raises(ScenarioHintsError, match="disagree on the construction identity"):
        load(tmp_path, pins)


@pytest.mark.parametrize(
    "override",
    [
        {"k": NEIGHBOUR_K + 1},
        {"min_leakage_share": 0.2},
        {"max_neighbours": NEIGHBOUR_LIMIT + 1},
        {"max_cues": CUE_LIMIT + 1},
        {"cue_min_rows": CUE_MIN_ROWS + 1},
        {"cue_prior": CUE_PRIOR + 1},
    ],
)
def test_a_table_built_by_another_rule_is_refused(tmp_path, override):
    """The derivation rule is the view's IDENTITY: a table built with another
    k, another floor or another prior is another analysis."""

    pins = write_table(
        tmp_path, intents=[profile("alarm_set", 10)], policy_overrides=override,
    )
    with pytest.raises(ScenarioHintsError):
        load(tmp_path, pins)


def test_a_neighbour_below_the_floor_or_pointing_at_itself_is_refused(tmp_path):
    pins = write_table(tmp_path, intents=[
        profile("alarm_set", 100, [neighbour("alarm_remove", 10, 100)]),
    ])
    with pytest.raises(ScenarioHintsError, match="below the declared leakage floor"):
        load(tmp_path, pins)
    pins = write_table(tmp_path, intents=[
        profile("alarm_set", 100, [neighbour("alarm_set", 120, 100)]),
    ])
    with pytest.raises(ScenarioHintsError, match="neighbour row is invalid"):
        load(tmp_path, pins)


def test_more_neighbours_or_cues_than_the_rule_allows_are_refused(tmp_path):
    pins = write_table(tmp_path, intents=[
        profile("alarm_set", 100, [
            neighbour(f"other_{index}", 120, 100)
            for index in range(NEIGHBOUR_LIMIT + 1)
        ]),
    ])
    with pytest.raises(ScenarioHintsError, match="more than 3 neighbours"):
        load(tmp_path, pins)
    pins = write_table(tmp_path, intents=[
        profile("alarm_set", 100, [
            neighbour(
                "alarm_remove", 120, 100,
                [cue(f"word{index}") for index in range(CUE_LIMIT + 1)],
            ),
        ]),
    ])
    with pytest.raises(ScenarioHintsError, match="more than 3 cues"):
        load(tmp_path, pins)


def test_a_cue_below_the_count_floor_or_not_a_word_is_refused(tmp_path):
    pins = write_table(tmp_path, intents=[
        profile("alarm_set", 100, [
            neighbour("alarm_remove", 120, 100, [cue("wake", CUE_MIN_ROWS - 1)]),
        ]),
    ])
    with pytest.raises(ScenarioHintsError, match="cue of"):
        load(tmp_path, pins)
    pins = write_table(tmp_path, intents=[
        profile("alarm_set", 100, [
            neighbour("alarm_remove", 120, 100, [cue("the")]),
        ]),
    ])
    with pytest.raises(ScenarioHintsError, match="cue of"):
        load(tmp_path, pins)


def test_a_devel_snapshot_is_refused(tmp_path):
    pins = write_table(
        tmp_path,
        intents=[profile("alarm_set", 10)],
        snapshot_overrides={"source_split": "devel"},
    )
    with pytest.raises(ScenarioHintsError, match="TRAIN construction pool"):
        load(tmp_path, pins)


# ---------------------------------------------------------------------------
# 4. Bounds and selection
# ---------------------------------------------------------------------------


def test_bounds_default_to_the_table_and_may_only_narrow():
    assert scenario_hints_bounds().as_json() == {
        "max_candidates": SCENARIO_HINTS_MAX_CANDIDATES,
        "max_cues": CUE_LIMIT,
        "max_neighbours": NEIGHBOUR_LIMIT,
    }
    assert scenario_hints_bounds({"max_cues": 0}).max_cues == 0
    for declared, message in (
        ({"max_cues": CUE_LIMIT + 1}, "must lie in"),
        ({"max_neighbours": -1}, "must lie in"),
        ({"max_cues": True}, "must be an integer"),
        ({"max_cues": 1.5}, "must be an integer"),
        ({"max_candidates": 1}, "unknown bound"),
        ("three", "must be an object"),
    ):
        with pytest.raises(ScenarioHintsError, match=message):
            scenario_hints_bounds(declared)


def test_selection_is_bounded_ordered_and_skips_what_the_table_lacks(tmp_path):
    letters = "abcdefghij"
    pins = write_table(tmp_path, intents=[
        profile(f"intent_{index}", 100, [
            neighbour(f"other_{index}_{step}", 120 - step, 100, [
                cue(f"cue{letters[index]}{letters[step]}{letters[rank]}")
                for rank in range(CUE_LIMIT)
            ])
            for step in range(NEIGHBOUR_LIMIT)
        ])
        for index in range(5)
    ])
    table = load(tmp_path, pins)
    bounds = scenario_hints_bounds()
    candidates = [f"intent_{index}" for index in range(5)]
    hints = scenario_hints(
        candidate_ids=[*candidates, "absent_intent"], table=table, bounds=bounds,
    )
    assert [hint.intent for hint in hints] == candidates[:SCENARIO_HINTS_MAX_CANDIDATES]
    assert hint_counts(hints) == {
        "candidates": 3,
        "neighbours": 3 * NEIGHBOUR_LIMIT,
        "cues": 3 * NEIGHBOUR_LIMIT * CUE_LIMIT,
    }
    # A repeated candidate is rendered once; an absent one is skipped silently.
    repeated = scenario_hints(
        candidate_ids=["intent_0", "intent_0", "absent_intent", "intent_1"],
        table=table,
        bounds=bounds,
    )
    assert [hint.intent for hint in repeated] == ["intent_0", "intent_1"]
    # Narrowed bounds narrow the block and nothing else.
    narrowed = scenario_hints(
        candidate_ids=candidates,
        table=table,
        bounds=scenario_hints_bounds({"max_neighbours": 1, "max_cues": 1}),
    )
    assert hint_counts(narrowed) == {"candidates": 3, "neighbours": 3, "cues": 3}


def test_render_helpers_are_integer_exact_and_closed(tmp_path):
    assert render_leakage(60, 940) == "6.4 % (60 of 940 nearest neighbours)"
    assert render_leakage(0, 0) == "0.0 % (0 of 0 nearest neighbours)"
    assert render_cues(["wake", "snooze"]) == "wake, snooze"
    assert render_cues([]).startswith("(")


# ---------------------------------------------------------------------------
# 5. The released table
# ---------------------------------------------------------------------------


@released
def test_the_released_view_loads_and_binds_the_registered_pool():
    root = _released_root()
    pins = (
        {
            "relpath": RELEASE_RELPATH, "root": "data",
            "sha256": _sha256((root / RELEASE_RELPATH).read_bytes()),
        },
        {
            "relpath": SNAPSHOT_RELPATH, "root": "data",
            "sha256": _sha256((root / SNAPSHOT_RELPATH).read_bytes()),
        },
    )
    table = load(root, pins)
    assert table.view_id == SCENARIO_HINTS_VIEW_ID
    assert table.builder_policy_id == SCENARIO_HINTS_BUILDER_POLICY_ID
    assert table.source_split == "train"
    assert table.construction_utterance_count == EXPECTED_CONSTRUCTION_UTTERANCES
    assert len(table.intent_ids) == EXPECTED_INTENTS
    receipt = json.loads(
        (REPO_ROOT / RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    assert receipt["source_split_identity_hash"] == table.source_split_identity_hash
    assert receipt["contacts"] == {
        "encoder": 0, "model": 0, "scorer": 0, "tool": 0,
    }
    assert receipt["outputs"]["snapshot"]["sha256"] == pins[1]["sha256"]
    assert receipt["outputs"]["release"]["sha256"] == pins[0]["sha256"]
    completion = json.loads(
        (root / COMPLETION_RELPATH).read_text(encoding="utf-8")
    )
    assert completion["snapshot"]["sha256"] == pins[1]["sha256"]
    assert completion["release"]["sha256"] == pins[0]["sha256"]
    assert completion["contacts"] == {
        "encoder": 0, "model": 0, "scorer": 0, "tool": 0,
    }


@released
def test_the_released_table_carries_no_identifier_and_no_sentence():
    """The content audit. Every leaf of the released snapshot is an intent id,
    a count, a share, a log-odds or a single cue WORD -- never an utterance id,
    a recording, a sentence or an entity filler."""

    root = _released_root()
    snapshot = json.loads((root / SNAPSHOT_RELPATH).read_text(encoding="utf-8"))
    text = json.dumps(snapshot, ensure_ascii=False)
    assert "slurp:train:" not in text
    assert ".flac" not in text
    assert "facet:content:" not in text.replace(
        '"relpath": "vectors/slurp-kus3/facet-vectors.jsonl"', ""
    )
    for entry in snapshot["intents"]:
        assert re.fullmatch(r"[a-z0-9_]+", entry["intent"])
        for row in entry["neighbours"]:
            assert re.fullmatch(r"[a-z0-9_]+", row["intent"])
            assert row["intent"] != entry["intent"]
            assert row["leaked"] / row["of_neighbours"] >= NEIGHBOUR_MIN_LEAKAGE_SHARE
            assert row["of_neighbours"] == entry["rows"] * NEIGHBOUR_K
            assert row["leakage_share"] == round(
                row["leaked"] / row["of_neighbours"], 6
            )
            assert len(row["cues"]) <= CUE_LIMIT
            for item in row["cues"]:
                # One WORD, never a phrase and never a filler: no whitespace.
                assert " " not in item["word"]
                assert is_cue_candidate(item["word"])
                assert item["rows"] >= CUE_MIN_ROWS
                assert item["rows"] <= entry["rows"]
        assert len(entry["neighbours"]) <= NEIGHBOUR_LIMIT


@released
def test_the_released_neighbours_are_ordered_and_the_cues_scored():
    root = _released_root()
    snapshot = json.loads((root / SNAPSHOT_RELPATH).read_text(encoding="utf-8"))
    for entry in snapshot["intents"]:
        keys = [(-row["leaked"], row["intent"]) for row in entry["neighbours"]]
        assert keys == sorted(keys)
        for row in entry["neighbours"]:
            scores = [
                (-item["log_odds"], item["word"]) for item in row["cues"]
            ]
            assert scores == sorted(scores)
