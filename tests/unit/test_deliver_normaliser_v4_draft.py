"""NX R0.4 (2026-10-09): the DRAFT delivery normaliser ``saea-deliver-normalise-v4``.

Mirrors ``test_deliver_normaliser_node.py`` (v3) for the parts v4 shares, and pins the
parts it adds: the five-rule entity stage selected offline
(``docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md``) and its parity
with the offline driver ``scripts/analysis/slurp_nx_postproc_v4_search.py``.

Model-free and offline: synthetic pool, synthetic inventory, fake scope table; the data
root is never read.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
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
# 1. Identity: a draft, deliberately unregistered, that refuses unpinned statistics.


def test_the_draft_carries_its_identity_and_is_not_registered():
    entry = dn.SlurpProjectionV4DeliveryNormaliser()
    assert entry.id == dn.DELIVER_NORMALISE_V4 == "saea-deliver-normalise-v4"
    assert entry.version == dn.DELIVER_NORMALISE_V4_VERSION
    assert entry.carrier_lock_key == "slurp"
    assert dn.DELIVER_NORMALISE_V4 not in DELIVERY_NORMALISERS.names()


def test_the_draft_refuses_to_run_without_injected_statistics():
    with pytest.raises(DeliveryNormaliserError, match="draft"):
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
