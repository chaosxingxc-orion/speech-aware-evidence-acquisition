"""NX R0.4 (2026-10-09): the delivery normaliser ``saea-deliver-normalise-v4``.

Mirrors ``test_deliver_normaliser_node.py`` (v3) for the parts v4 shares, and pins the
parts it adds: the five-rule entity stage selected offline
(``docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md``), its parity
with the offline driver ``scripts/analysis/slurp_nx_postproc_v4_search.py``, and the
four pinned TRAIN-statistics tables (``scripts/build_slurp_v4_train_statistics.py``).

Sections 1-6 are model-free and offline: synthetic pool, synthetic inventory, fake scope
table; the data root is never read. Section 7 reads the data root (the pinned tables, the
sealed A2 and Fold-A delivered columns and the R0.4 v4 column copies) and is skipped when
it is absent. It compares digests and counts only, never prints a text.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.base import (
    DELIVERY_NORMALISERS,
    DeliveryNormaliserError,
)
from speech_aware_evidence_acquisition.rails import delivery_normalisers as dn
from speech_aware_evidence_acquisition.rails import slurp_projection_v3 as v3
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    SlotEntity,
    legal_intent_inventory,
    parse_slu_response,
)

_REPO = Path(__file__).resolve().parents[2]

INVENTORY = legal_intent_inventory(
    {
        "music": ("likeness", "dislikeness", "play", "query", "settings"),
        "play": ("audiobook", "game", "music", "podcasts", "radio"),
        "alarm": ("set", "remove", "query"),
        "general": ("quirky",),
    }
)


def _pool() -> dict:
    """A synthetic annotated pool in ``load_exemplar_pool``'s ``values`` shape."""
    values = {}
    k = 0

    def add(intent, utterance, fillers):
        nonlocal k
        values[f"v{k}"] = {"intent": intent, "utterance": utterance, "fillers": fillers}
        k += 1

    for _ in range(12):  # "at" precedes the time span and is never inside it -> strip (time, at)
        add("alarm_set", "wake me at six am", {"time": ["six am"]})
    for _ in range(5):  # "o'clock" follows the span and is never inside it -> strip o'clock
        add("alarm_set", "wake me at seven o'clock", {"time": ["seven"]})
    for _ in range(10):  # "the" is inside the date span -> keep (date, the)
        add("alarm_set", "set an alarm for the fifth", {"date": ["the fifth"]})
    for _ in range(20):  # an intent that never carries entities
        add("general_quirky", "tell me something funny", {})
    return values


POOL = _pool()
STATS = dn.SlurpV4Statistics.from_pool_values(POOL)
TABLE = dn.ScopeRuleTable({"please": (10, 0)}, sha256="0" * 64, floor=5)


@pytest.fixture(autouse=True)
def _synthetic_inventory(monkeypatch):
    monkeypatch.setattr(v3, "_default_legal_intent_inventory", lambda: INVENTORY)


def _answer(scenario, action, entities=()):
    return json.dumps(
        {"scenario": scenario, "action": action,
         "entities": [{"type": t, "filler": f} for t, f in entities]},
        ensure_ascii=False, sort_keys=True,
    )


def _v4(text, **kwargs):
    kwargs.setdefault("stats", STATS)
    kwargs.setdefault("table", TABLE)
    return dn.SlurpProjectionV4DeliveryNormaliser()(text, **kwargs)


def _entities(outcome):
    return list(parse_slu_response(outcome.text)[2])


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _driver():
    path = _REPO / "scripts/analysis/slurp_nx_postproc_v4_search.py"
    name = "slurp_nx_postproc_v4_search"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 1. Identity: registered (resolvable for replay), carrier-scoped, version 1.


def test_v4_carries_its_identity_and_is_registered():
    entry = dn.SlurpProjectionV4DeliveryNormaliser()
    assert entry.id == dn.DELIVER_NORMALISE_V4 == "saea-deliver-normalise-v4"
    assert entry.version == dn.DELIVER_NORMALISE_V4_VERSION == "1"
    assert entry.carrier_lock_key == "slurp"
    assert dn.DELIVER_NORMALISE_V4 in DELIVERY_NORMALISERS.names()
    registered = DELIVERY_NORMALISERS.resolve(dn.DELIVER_NORMALISE_V4)
    assert isinstance(registered, dn.SlurpProjectionV4DeliveryNormaliser)


def test_v4_is_registered_but_armed_by_no_config():
    """Registration is for replay; which cells use v4 is a separate wiring step."""
    hits = [p for p in (_REPO / "configs").rglob("*.json")
            if f"\"{dn.DELIVER_NORMALISE_V4}\"" in p.read_text(encoding="utf-8")]  # exact id: v4g (lock v2.2) is a different normaliser
    assert hits == []


def test_v4_refuses_statistics_of_the_wrong_type():
    with pytest.raises(DeliveryNormaliserError, match="SlurpV4Statistics"):
        dn.SlurpProjectionV4DeliveryNormaliser()(_answer("alarm", "set"), stats={"x": 1}, table=TABLE)


def test_without_injected_statistics_v4_loads_the_pinned_tables_and_refuses_unpinned_ones(
    tmp_path, monkeypatch
):
    """A data root whose tables are not the pinned bytes is refused, by digest."""
    root = tmp_path / "data"
    for name, data in dn.v4_table_bytes(dn.v4_pool_counts(POOL), dn.V4_STATS_CONSTRUCTION_POOL).items():
        path = root / dn.V4_TABLE_RELPATHS[name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(root))
    monkeypatch.setattr(dn, "_DEFAULT_V4_STATISTICS", [])
    with pytest.raises(DeliveryNormaliserError, match="not the pinned"):
        dn.SlurpProjectionV4DeliveryNormaliser()(_answer("alarm", "set"), table=TABLE)


def test_the_stage_order_is_the_selected_list():
    assert dn.V4_STAGES == ("fx-article", "fx-oclock", "scope", "ti1", "ee10")


# ---------------------------------------------------------------------------
# 2. v3 first, unchanged.


def test_v3_runs_first_and_repairs_the_label():
    outcome = _v4(_answer("music", "play_music"))
    scenario, action, _e, parsed = parse_slu_response(outcome.text)
    assert parsed and (scenario, action) == ("play", "music")
    assert outcome.receipt["labels_changed"] == 1
    assert outcome.receipt["stages"][0]["normaliser_id"] == dn.DELIVER_NORMALISE_V3


def test_v3_filler_rungs_still_apply():
    outcome = _v4(_answer("alarm", "set", (("time", "6:30AM"),)))
    assert _entities(outcome) == [SlotEntity(type="time", filler="six thirty am")]
    assert outcome.receipt["fillers_changed"] == 1


# ---------------------------------------------------------------------------
# 3. The entity stage, rule by rule.


def test_fx_article_strips_a_determiner_train_annotation_excludes():
    assert ("time", "at") in STATS.article_strip
    outcome = _v4(_answer("alarm", "set", (("time", "at six am"),)))
    assert _entities(outcome) == [SlotEntity(type="time", filler="six am")]
    assert outcome.receipt["entity_stage_counts"]["fillers_rewritten"] == 1


def test_fx_article_keeps_a_determiner_train_annotation_includes():
    assert ("date", "the") not in STATS.article_strip
    outcome = _v4(_answer("alarm", "set", (("date", "the fifth"),)))
    assert _entities(outcome) == [SlotEntity(type="date", filler="the fifth")]
    assert outcome.changed is False


def test_fx_article_never_strips_a_single_token_filler():
    outcome = _v4(_answer("alarm", "set", (("time", "at"),)))
    assert _entities(outcome) == [SlotEntity(type="time", filler="at")]


def test_fx_oclock_strips_a_trailing_oclock_from_a_time_filler():
    assert STATS.oclock_strip is True
    outcome = _v4(_answer("alarm", "set", (("time", "seven o'clock"),)))
    assert _entities(outcome) == [SlotEntity(type="time", filler="seven")]


def test_scope_drops_what_the_registered_stage_drops():
    outcome = _v4(_answer("alarm", "set", (("time", "six am"), ("time", "please"))))
    assert _entities(outcome) == [SlotEntity(type="time", filler="six am")]
    assert outcome.receipt["entity_stage_counts"]["dropped_scope"] == 1


def test_ti1_drops_a_type_the_intent_never_carries_in_train():
    outcome = _v4(_answer("alarm", "set", (("time", "six am"), ("person", "bob"))))
    assert _entities(outcome) == [SlotEntity(type="time", filler="six am")]
    assert outcome.receipt["entity_stage_counts"]["dropped_ti1"] == 1


def test_an_intent_absent_from_train_is_left_alone_by_ti1_and_ee10():
    outcome = _v4(_answer("alarm", "query", (("person", "bob"),)))
    assert _entities(outcome) == [SlotEntity(type="person", filler="bob")]


def test_ee10_empties_a_row_whose_intent_carries_no_entities_in_train():
    outcome = _v4(_answer("general", "quirky", (("person", "bob"),)))
    assert _entities(outcome) == []
    assert outcome.receipt["entity_stage_counts"]["dropped_ti1"] == 1  # ti1 runs first


def test_an_empty_entity_list_is_never_filled():
    raw = _answer("general", "quirky")
    outcome = _v4(raw)
    assert _entities(outcome) == []
    assert outcome.text == raw


def test_the_stage_never_changes_a_label():
    for raw in (_answer("general", "quirky", (("person", "bob"),)),
                _answer("alarm", "set", (("time", "at six am"), ("person", "x")))):
        before = parse_slu_response(raw)[:2]
        assert parse_slu_response(_v4(raw).text)[:2] == before


# ---------------------------------------------------------------------------
# 4. Custody: no-op, idempotence, pass-through, receipt.


def test_an_already_normal_answer_is_a_byte_identical_no_op():
    raw = _answer("alarm", "set", (("time", "six am"),))
    outcome = _v4(raw)
    assert outcome.text == raw
    assert outcome.changed is False
    assert outcome.receipt["applied"] is True


@pytest.mark.parametrize("raw", (
    _answer("alarm", "set", (("time", "At 6:30AM"), ("person", "bob"), ("time", "please"))),
    _answer("music", "play_music", (("time", "seven o'clock"),)),
    _answer("general", "quirky", (("date", "today"),)),
))
def test_the_normaliser_is_idempotent(raw):
    once = _v4(raw)
    twice = _v4(once.text)
    assert twice.text == once.text
    assert twice.changed is False


def test_an_unparsed_answer_is_delivered_unchanged_with_a_reason():
    raw = "not a SLURP answer"
    outcome = _v4(raw)
    assert outcome.text == raw
    assert outcome.changed is False
    assert outcome.receipt["applied"] is False
    assert outcome.receipt["reason"] == "unparsed"


def test_the_receipt_binds_digests_statistics_and_table_and_no_text():
    raw = _answer("alarm", "set", (("time", "at six am"), ("person", "bob")))
    outcome = _v4(raw)
    r = outcome.receipt
    assert r["normaliser_id"] == dn.DELIVER_NORMALISE_V4
    assert r["rule_id"] == dn.V4_RULE_ID
    assert r["input_sha256"] == _sha(raw)
    assert r["output_sha256"] == _sha(outcome.text)
    assert r["stats_sha256"] == STATS.sha256
    assert r["table_sha256"] == TABLE.sha256
    assert r["entity_stage"] == list(dn.V4_STAGES)
    flat = json.dumps(r)
    assert "six am" not in flat and "bob" not in flat


def test_the_statistics_digest_is_deterministic_and_content_bound():
    again = dn.SlurpV4Statistics.from_pool_values(_pool())
    assert again.sha256 == STATS.sha256
    smaller = dict(list(_pool().items())[:-1])
    assert dn.SlurpV4Statistics.from_pool_values(smaller).sha256 != STATS.sha256


# ---------------------------------------------------------------------------
# 5. Parity with the offline driver that selected and confirmed the rule.


def test_statistics_match_the_offline_driver():
    driver = _driver()
    offline = driver.TrainStats(POOL)
    assert STATS.article_strip == offline.article_strip
    assert STATS.oclock_strip == offline.oclock["strip"]
    assert STATS.intent_n == dict(offline.intent_n)
    assert STATS.intent_with_entities == dict(offline.intent_with_entities)
    assert STATS.intent_type == {i: dict(t) for i, t in offline.intent_type.items()}


@pytest.mark.parametrize("scenario, action, entities", (
    ("alarm", "set", (("time", "at six am"), ("person", "bob"), ("time", "please"), ("date", "the fifth"))),
    ("alarm", "set", (("time", "seven o'clock"), ("date", "at noon"))),
    ("general", "quirky", (("person", "bob"),)),
    ("alarm", "query", (("person", "bob"), ("time", "please"))),
    ("alarm", "set", ()),
))
def test_the_entity_stage_matches_the_offline_driver(scenario, action, entities):
    driver = _driver()
    ents = [SlotEntity(type=t, filler=f) for t, f in entities]
    mine, _counts = dn.v4_entity_stage(scenario, action, ents, STATS, TABLE)
    offline_stats = driver.TrainStats(POOL)
    ctx = driver.RowContext(f"{scenario}_{action}", None, None)
    env = {"SlotEntity": SlotEntity, "scope_table": TABLE}
    theirs = [e for _i, e in driver.apply_rules(list(dn.V4_STAGES), ents, ctx, offline_stats, env)]
    assert mine == theirs



# ---------------------------------------------------------------------------
# 6. The pinned-table form: round trip, consistency refusals, receipt binding.


def _tables(pool=None):
    return dn.v4_table_bytes(dn.v4_pool_counts(pool or POOL), dn.V4_STATS_CONSTRUCTION_POOL)


def _mutate(name, edit):
    blobs = _tables()
    document = json.loads(blobs[name].decode("utf-8"))
    edit(document)
    blobs[name] = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    return blobs


def test_the_tables_round_trip_to_the_same_statistics():
    blobs = _tables()
    assert set(blobs) == set(dn.V4_TABLES)
    loaded = dn.SlurpV4Statistics.from_table_bytes(blobs, expected_sha256=None)
    assert loaded.sha256 == STATS.sha256
    pins = {n: hashlib.sha256(b).hexdigest() for n, b in blobs.items()}
    assert loaded.tables == pins
    assert dn.SlurpV4Statistics.from_table_bytes(blobs, expected_sha256=pins).sha256 == STATS.sha256


def test_the_tables_are_deterministic_bytes_and_carry_no_text():
    assert _tables() == _tables()
    flat = b"".join(_tables().values()).decode("utf-8")
    for text in ("wake me", "six am", "funny", "the fifth"):
        assert text not in flat


def test_a_table_that_is_not_its_pin_is_refused():
    blobs = _tables()
    pins = {n: hashlib.sha256(b).hexdigest() for n, b in blobs.items()}
    pins["oclock"] = "0" * 64
    with pytest.raises(DeliveryNormaliserError, match="oclock table hashes"):
        dn.SlurpV4Statistics.from_table_bytes(blobs, expected_sha256=pins)


@pytest.mark.parametrize("name, edit, match", (
    ("article-strip", lambda d: d["strip"].append(["date", "the"]), "does not follow from its counts"),
    ("article-strip", lambda d: d.update(min_opportunities=5), "thresholds"),
    ("oclock", lambda d: d.update(strip=False), "does not follow from its counts"),
    ("type-by-intent", lambda d: d.update(min_share=0.02), "1 % threshold"),
    ("intent-entity-rate", lambda d: d["intent_n"].update(alarm_set=1), "disagree"),
    ("intent-entity-rate", lambda d: d.update(construction_pool={"relpath": "x", "content_sha256": "y"}),
     "one construction pool"),
    ("type-by-intent", lambda d: d.update(schema="other"), "schema"),
))
def test_an_inconsistent_table_is_refused(name, edit, match):
    with pytest.raises(DeliveryNormaliserError, match=match):
        dn.SlurpV4Statistics.from_table_bytes(_mutate(name, edit), expected_sha256=None)


def test_a_missing_table_is_refused():
    blobs = _tables()
    del blobs["oclock"]
    with pytest.raises(DeliveryNormaliserError, match="exactly the tables"):
        dn.SlurpV4Statistics.from_table_bytes(blobs, expected_sha256=None)


def test_loaded_statistics_behave_exactly_as_injected_ones():
    loaded = dn.SlurpV4Statistics.from_table_bytes(_tables(), expected_sha256=None)
    for raw in (_answer("alarm", "set", (("time", "at six am"), ("person", "bob"), ("time", "please"))),
                _answer("alarm", "set", (("time", "seven o'clock"),)),
                _answer("general", "quirky", (("date", "today"),))):
        assert _v4(raw, stats=loaded).text == _v4(raw).text


def test_the_receipt_names_the_tables_it_loaded():
    loaded = dn.SlurpV4Statistics.from_table_bytes(_tables(), expected_sha256=None)
    assert _v4(_answer("alarm", "set"), stats=loaded).receipt["stats_tables"] == loaded.tables
    assert _v4(_answer("alarm", "set")).receipt["stats_tables"] == {}


def test_the_pins_agree_with_the_build_receipt():
    assert set(dn.V4_TABLE_SHA256) == set(dn.V4_TABLES) == set(dn.V4_TABLE_RELPATHS)
    for digest in (*dn.V4_TABLE_SHA256.values(), dn.V4_STATS_SHA256):
        assert len(digest) == 64 and int(digest, 16) >= 0
    receipt = json.loads((_REPO / "docs/receipts/knowledge/slurp-v4-train-statistics-v1.json").read_text(
        encoding="utf-8"))
    assert {n: receipt["outputs"][n]["sha256"] for n in dn.V4_TABLES} == dn.V4_TABLE_SHA256
    assert {n: receipt["outputs"][n]["relpath"] for n in dn.V4_TABLES} == dn.V4_TABLE_RELPATHS
    assert receipt["statistics_sha256"] == dn.V4_STATS_SHA256
    assert receipt["inputs"]["construction_pool"]["content_sha256"] == \
        dn.V4_STATS_CONSTRUCTION_POOL["content_sha256"]
    assert receipt["counts"]["article_strip_pairs"] == 73


# ---------------------------------------------------------------------------
# 7. The data root: the pinned path reproduces the sealed R0.4 v4 columns byte for byte.

_DATA = Path(os.environ.get("SPEECHRL_DATA_DIR", "") or "/nonexistent")
_FALLBACK_LOCK = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
_SEARCH = "analysis/SAEA-SLURP-NX-POSTPROC-V4-SEARCH-V1"
#: The R0.4 column copies (the registered-scorer identity proofs), their recorded digests, the
#: roster size and the number of rows v4 edits (R0.4 read: 124 on A2, 130 on Fold A).
_COLUMNS = {
    "a2": ("SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1",
           "attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1",
           f"{_SEARCH}/select-a2/v4-column-outputs.jsonl",
           "2104239a2aa51ee949036a20295f4754ca12793202dcda362374adf8758b14d6", 1000, 124),
    "fold-a": ("SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1",
               "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1",
               f"{_SEARCH}/confirm-fold-a/v4-column-outputs.jsonl",
               "68de69759d6c85942354852c151ee3f707638c48463c28996e67318cde52b4be", 1080, 130),
}


def _data_ready() -> bool:
    if not _DATA.is_dir():
        return False
    needed = [_DATA / dn.V4_TABLE_RELPATHS[n] for n in dn.V4_TABLES]
    needed.append(_DATA / dn.SCOPE_RULE_TABLE_RELPATH)
    for run_id, attempt, copy, *_rest in _COLUMNS.values():
        needed += [_DATA / "runs" / run_id / attempt / f"{run_id}.outputs.jsonl", _DATA / copy]
    return all(p.is_file() for p in needed)


needs_data = pytest.mark.skipif(not _data_ready(), reason="SPEECHRL_DATA_DIR with the pinned v4 tables absent")


def _real_inventory():
    from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path
    from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import load_legal_intent_inventory

    try:
        lock_path = umbrella_lock_path()
    except Exception:  # noqa: BLE001 - a worktree outside the umbrella layout
        lock_path = _FALLBACK_LOCK
    if not Path(lock_path).is_file():
        pytest.skip("umbrella datasets lock not found")
    return load_legal_intent_inventory(load_lock(lock_path), _DATA)


def _jsonl(path: Path) -> dict:
    out = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                out[str(record["sample_id"])] = record.get("text") or ""
    return out


@needs_data
def test_the_pinned_tables_load_with_the_reads_statistics(monkeypatch):
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(_DATA))
    monkeypatch.setattr(dn, "_DEFAULT_V4_STATISTICS", [])
    stats = dn.default_v4_statistics()
    assert stats.sha256 == dn.V4_STATS_SHA256
    assert stats.tables == dn.V4_TABLE_SHA256
    assert len(stats.article_strip) == 73
    assert stats.oclock_strip is True
    assert len(stats.intent_n) == 59 and sum(stats.intent_n.values()) == 8554
    assert sum(len(t) for t in stats.intent_type.values()) == 360
    assert sum(1 for i in stats.intent_n if stats.entity_rate(i) < dn.V4_EE_MIN_ENTITY_RATE) == 4


@needs_data
@pytest.mark.parametrize("pool", sorted(_COLUMNS))
def test_the_pinned_path_reproduces_the_sealed_v4_column_byte_for_byte(pool, monkeypatch):
    """The REGISTERED entry, with no injected statistics or scope table, over each sealed delivered
    answer, gives exactly the R0.4 v4 column copy (digests and counts compared, no text shown)."""
    run_id, attempt, copy, copy_sha, rows, edited = _COLUMNS[pool]
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(_DATA))
    monkeypatch.setattr(dn, "_DEFAULT_V4_STATISTICS", [])
    monkeypatch.setattr(dn, "_DEFAULT_SCOPE_RULE_TABLE", [])
    assert hashlib.sha256((_DATA / copy).read_bytes()).hexdigest() == copy_sha
    sealed = _jsonl(_DATA / "runs" / run_id / attempt / f"{run_id}.outputs.jsonl")
    expected = _jsonl(_DATA / copy)
    assert len(sealed) == rows and set(sealed) == set(expected)
    inventory = _real_inventory()
    normaliser = DELIVERY_NORMALISERS.resolve(dn.DELIVER_NORMALISE_V4)
    mismatches = changed = 0
    for sid in sorted(sealed):
        outcome = normaliser(sealed[sid], inventory=inventory)
        mismatches += int(outcome.text.encode("utf-8") != expected[sid].encode("utf-8"))
        changed += int(outcome.changed)
        assert outcome.receipt["stats_sha256"] == dn.V4_STATS_SHA256
        assert outcome.receipt["stats_tables"] == dn.V4_TABLE_SHA256
        assert outcome.receipt["table_sha256"] == dn.SCOPE_RULE_TABLE_SHA256
    assert mismatches == 0
    assert changed == edited
