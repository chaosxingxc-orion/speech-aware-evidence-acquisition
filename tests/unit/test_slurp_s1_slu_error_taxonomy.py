"""scripts/analysis/slurp_s1_slu_error_taxonomy.py -- the ``--arms`` flag and the pure parts on fakes.

All synthetic: no sealed run, no gold, no utterance or model text. Placeholder sample ids, placeholder
slot types and placeholder fillers (``tok-a`` ...) only.
"""

from __future__ import annotations

import importlib.util
import sys
from collections import namedtuple
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_s1_slu_error_taxonomy.py"

_spec = importlib.util.spec_from_file_location("slurp_s1_slu_error_taxonomy", DRIVER_PATH)
S1 = importlib.util.module_from_spec(_spec)
sys.modules["slurp_s1_slu_error_taxonomy"] = S1
_spec.loader.exec_module(S1)

E = namedtuple("E", "type filler")


# --- the --arms flag --------------------------------------------------------------------------------


def test_arms_flag_defaults_to_every_arm_in_table_order():
    assert S1.parse_arms(None) == [a["label"] for a in S1.ARMS]
    assert S1.parse_arms("") == [a["label"] for a in S1.ARMS]


def test_arms_flag_keeps_the_given_order_and_strips_blanks():
    assert S1.parse_arms(" agree , a2 ,", known=("a2", "agree", "x")) == ["agree", "a2"]


def test_arms_flag_refuses_unknown_and_repeated_labels():
    with pytest.raises(S1.ReadError):
        S1.parse_arms("a2,nope", known=("a2",))
    with pytest.raises(S1.ReadError):
        S1.parse_arms("a2,a2", known=("a2",))


def test_arm_table_reads_no_test_split_and_carries_the_control():
    assert {a["split"] for a in S1.ARMS} <= {"train", "devel"}
    assert S1.CONTROL in {a["label"] for a in S1.ARMS}
    assert len({a["label"] for a in S1.ARMS}) == len(S1.ARMS)


def test_gold_loader_refuses_the_test_split():
    with pytest.raises(S1.ReadError):
        S1.load_gold_split(lock={}, data_root=Path("."), split="test", ES=None)


# --- class / origin mapping -------------------------------------------------------------------------


def test_origin_short_maps_every_ledger_origin_string():
    assert S1.origin_short("consumption: broken at delivery normaliser") == "consumption"
    assert S1.origin_short("consumption: note carries the gold span, Solver first answer wrong") == "consumption"
    assert S1.origin_short("hearing/span: note carries a near form") == "hearing_visible"
    assert S1.origin_short("undetermined: note silent (value absent from the note)") == "undetermined"
    with pytest.raises(S1.ReadError):
        S1.origin_short("something else")


def test_supply_class_keeps_e1_to_e3_and_folds_the_rest():
    assert S1.supply_class("E1 exemplars print the gold (type, value)") == "E1"
    assert S1.supply_class("E3 a delivered slot-contract card names the value") == "E3"
    assert S1.supply_class("E4 not supplied; in TRAIN's own value list for the type") == "none"
    assert S1.supply_class("E5 nowhere but the audio") == "none"


def test_class_counts_reports_every_class_including_zeros():
    items = [{"kind": "MISSING"}, {"kind": "MISSING"}, {"kind": "SPURIOUS"}]
    counts = S1.class_counts(items)
    assert list(counts) == list(S1.CLASSES)
    assert counts["MISSING"] == 2 and counts["SPURIOUS"] == 1 and counts["FORMAT"] == 0


# --- empty-gold split (decision 199) ----------------------------------------------------------------


def test_empty_gold_split_on_a_four_row_fake():
    gold = {"r1": (), "r2": (), "r3": (E("t1", "tok-a"),), "r4": (E("t1", "tok-b"), E("t2", "tok-c"))}
    pred = {"r1": (), "r2": (E("t1", "tok-x"), E("t2", "tok-y")), "r3": (E("t1", "tok-a"),), "r4": ()}
    ok = {"r1": True, "r2": True, "r3": False, "r4": True}
    out = S1.empty_gold_split(gold, pred, ok, ["r1", "r2", "r3", "r4"])
    assert out["zero_gold_rows"] == 2
    assert out["correctly_empty"] == 1 and out["spurious_filled"] == 1
    assert out["spurious_entities_on_zero_gold_rows"] == 2
    assert out["spurious_filled_intent_right"] == 1
    assert out["gold_rows"] == 2 and out["gold_rows_delivered_empty"] == 1
    assert out["gold_items_on_gold_rows_delivered_empty"] == 2


# --- N1 none-share gate -----------------------------------------------------------------------------


def test_none_share_skips_unresolved_keys_and_returns_none_when_nothing_resolves():
    fillers = {"k1": {}, "k2": {"t1": ["tok-a"]}, "k3": {}}
    assert S1.none_share(["k1", "k2", "k3", "zz"], fillers) == pytest.approx(2 / 3)
    assert S1.none_share(["zz"], fillers) is None
    assert S1.none_share([], fillers) is None


def test_n1_gate_changes_only_gated_emitting_rows():
    shares = {"r1": 0.9, "r2": 0.6, "r3": 0.59, "r4": None, "r5": 0.7}
    pred = {"r1": (E("t1", "tok-a"),), "r2": (), "r3": (E("t1", "tok-b"),), "r4": (E("t1", "tok-c"),),
            "r5": (E("t2", "tok-d"),)}
    gold = {"r1": (), "r2": (), "r3": (), "r4": (), "r5": (E("t2", "tok-d"),)}
    g = S1.n1_gate(shares, pred, gold, 0.6)
    assert sorted(g["gated"]) == ["r1", "r2", "r5"]
    assert g["change"] == {"r1": [], "r5": []}
    assert g["rows_gated_zero_gold"] == 2 and g["rows_gated_gold"] == 1


def test_expected_is_oracle_times_rate_rounded():
    assert S1.expected(2.0, 0.2471) == pytest.approx(0.4942)
    assert S1.RATES["m1"]["rate"] == pytest.approx(0.2471, abs=1e-4)
    assert S1.RATES["w4_list"]["rate"] == pytest.approx(0.0515, abs=1e-4)
    assert S1.E5_CONTAINMENT["rate"] == pytest.approx(0.7513, abs=1e-4)
    assert all(v["source"] for v in S1.RATES.values())
