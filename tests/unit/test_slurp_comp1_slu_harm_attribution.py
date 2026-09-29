"""``scripts/analysis/slurp_comp1_slu_harm_attribution.py``: pure, model-free tests on fakes -- no data
root, no gold corpus, no server, no GPU. Mirrors the import pattern other ``scripts/analysis`` tests use
for a module with no package ``__init__.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_ANALYSIS = _REPO / "scripts" / "analysis"
if str(_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS))

import slurp_comp1_slu_harm_attribution as attr  # noqa: E402

from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (  # noqa: E402
    SlotEntity,
    _exact_counts,
    score_slu,
)


def _counts(tp, fp, fn):
    # split evenly across word and char so the summed ingredients equal (tp, fp, fn)
    return {"slu_f1_word_tp": tp / 2, "slu_f1_char_tp": tp / 2, "slu_f1_word_fp": fp / 2,
            "slu_f1_char_fp": fp / 2, "slu_f1_word_fn": fn / 2, "slu_f1_char_fn": fn / 2}


def test_exact_items_matches_the_official_exact_counter_and_types_the_errors():
    gold = [("date", "a"), ("time", "b"), ("time", "c")]
    pred = [("date", "a"), ("time", "x"), ("device_type", "y"), ("device_type", "y")]
    item = attr.exact_items(gold, pred)
    tp, fp, fn = _exact_counts([SlotEntity(*g) for g in gold], [SlotEntity(*p) for p in pred])
    assert (item["tp"], item["fp"], item["fn"]) == (tp, fp, fn) == (1, 3, 2)
    assert sorted(item["fp_types"]) == ["device_type", "device_type", "time"]
    assert item["fp_gold_type"] == 1 and item["fp_new_type"] == 2
    assert item["emitted"] == 4


def test_exact_items_zero_gold_row_charges_every_emission_as_fp():
    item = attr.exact_items([], [("device_type", "h1"), ("change_amount", "h2")])
    assert (item["tp"], item["fp"], item["fn"], item["fp_new_type"]) == (0, 2, 0, 2)


def test_pooled_f1_and_row_swap():
    rows = {"r1": _counts(4, 2, 2), "r2": _counts(0, 2, 0)}
    base = {"r1": _counts(4, 2, 2), "r2": _counts(0, 0, 0)}
    assert attr.f1(*attr.slu_totals(rows, ["r1", "r2"])) == pytest.approx(100 * 8 / (8 + 4 + 2))
    swapped = attr.slu_totals(rows, ["r1", "r2"], base, {"r2"})
    assert attr.f1(*swapped) == pytest.approx(100 * 8 / (8 + 2 + 2))
    assert attr.f1(0, 0, 0) == 0.0


def test_marginal_pp_equals_the_finite_difference_of_one_new_type_fp():
    gold = [SlotEntity("date", "monday")]
    pred = [SlotEntity("date", "monday")]
    spurious = pred + [SlotEntity("device_type", "lights")]
    one = score_slu(gold_scenario="s", gold_action="a", gold_entities=gold, predicted_scenario="s",
                    predicted_action="a", predicted_entities=spurious)
    none = score_slu(gold_scenario="s", gold_action="a", gold_entities=gold, predicted_scenario="s",
                     predicted_action="a", predicted_entities=pred)
    # the official distance matcher charges exactly 1.0 word FP and 1.0 char FP
    assert one.slu_f1_word_fp - none.slu_f1_word_fp == 1.0
    assert one.slu_f1_char_fp - none.slu_f1_char_fp == 1.0
    tp, fp, fn = 1448.0, 1096.6, 680.6
    finite = attr.f1(tp, fp + 2.0, fn) - attr.f1(tp, fp, fn)
    assert attr.marginal_pp_per_exact_fp(tp, fp, fn) == pytest.approx(finite, rel=1e-3)


def test_raw_vs_delivered_detects_an_added_entity_and_a_filler_only_change():
    same = attr.raw_vs_delivered([("date", "h1")], [("date", "h2")])
    assert same["count_equal"] == 1 and same["type_multiset_equal"] == 1
    assert same["entity_multiset_equal"] == 0 and same["delivered_types_not_in_raw"] == 0
    added = attr.raw_vs_delivered([], [("device_type", "h")])
    assert added["count_equal"] == 0 and added["delivered_types_not_in_raw"] == 1
    assert attr.raw_vs_delivered(None, []) == {"raw_missing": 1}


def test_cited_unwrap_delivers_exactly_the_answer_entities():
    """Channel (a) on a fake envelope: the registered unwrap cannot add an entity."""

    from speech_aware_evidence_acquisition.rails.delivery_normalisers import CitedAnswerUnwrapDeliveryNormaliser
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    answer = {"scenario": "audio", "action": "volume_up", "entities": []}
    envelope = json.dumps({"schema": "saea-solver-cited-answer-v1", "answer": answer,
                           "citations": {"intent": ["train-exemplars::value:1"],
                                         "entities": [{"type": "device_type",
                                                       "evidence_ids": ["train-exemplars::value:1"]}]}})
    result = CitedAnswerUnwrapDeliveryNormaliser()(envelope)
    assert result.changed and result.receipt["applied"]
    scenario, action, entities, ok = parse_slu_response(result.text)
    assert ok and (scenario, action) == ("audio", "volume_up")
    # the citation names an entity type the answer does not carry; the delivered answer has none
    assert entities == []


def test_contrast_and_bootstrap_are_deterministic():
    left = {"a": {"tp": 1, "fp": 2, "fn": 0, "emitted": 3}, "b": {"tp": 0, "fp": 0, "fn": 1, "emitted": 0}}
    right = {"a": {"tp": 1, "fp": 0, "fn": 0, "emitted": 1}, "b": {"tp": 0, "fp": 1, "fn": 1, "emitted": 1}}
    c = attr.contrast(left, right, ["a", "b"])
    assert c == {"rows": 2, "d_tp": 0, "d_fp": 1, "d_fn": 0, "d_emitted": 1,
                 "rows_more_entities": 1, "rows_fewer_entities": 1}
    ci = attr.paired_boot([2, -1, 0, 0], draws=500, seed=7)
    assert ci == attr.paired_boot([2, -1, 0, 0], draws=500, seed=7)
    assert ci[0] <= 1 <= ci[1]
