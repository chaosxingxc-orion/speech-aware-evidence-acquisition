"""scripts/analysis/slurp_perception_block_depth_recall.py -- pure parts on fakes.

All synthetic: no sealed run, no gold, no utterance or model text. Placeholder intent ids
(``i-a`` ...) and placeholder sample ids only. Covers rank lookup, id stripping, dedupe, the AUC,
the utterance half split, rank buckets, the two variable-depth rules, the depth table, the
note-given-block-rank table, the sweeps and both cross-fits, entry counts, net rows, the paired
bootstrap and the Solver pick classes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_perception_block_depth_recall.py"

_spec = importlib.util.spec_from_file_location("slurp_perception_block_depth_recall", DRIVER_PATH)
M = importlib.util.module_from_spec(_spec)
sys.modules["slurp_perception_block_depth_recall"] = M
_spec.loader.exec_module(M)


def test_rank_of_dedupe_and_strip():
    assert M.rank_of(["i-a", "i-b", "i-c"], "i-b") == 2
    assert M.rank_of(["i-a"], "i-z") is None
    assert M.dedupe(["i-a", "i-b", "i-a", "", None]) == ["i-a", "i-b"]
    assert M.strip_value("intent-boundaries::intent-boundary:i-a") == "i-a"
    assert M.strip_value("intent-boundary:i-b") == "i-b"


def test_auc_direction_ties_and_degenerate():
    assert M.auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == pytest.approx(1.0)
    assert M.auc([0.1, 0.2, 0.8, 0.9], [1, 1, 0, 0]) == pytest.approx(0.0)
    assert M.auc([0.1, 0.5, 0.5], [0, 0, 1]) == pytest.approx(0.75)
    assert M.auc([0.3, 0.4], [1, 1]) is None


def test_split_half_is_deterministic_binary():
    halves = {M.split_half(f"utt-{i}") for i in range(50)}
    assert halves == {0, 1}
    assert M.split_half("utt-7") == M.split_half("utt-7")


def test_bucket():
    assert [M.bucket(r) for r in (1, 8, 9, 12, 13, 20, 21, 60, None)] == [
        "1-8", "1-8", "9-12", "9-12", "13-20", "13-20", "21-60", "21-60", "not recalled"]


def test_variable_depth_gap_and_cliff():
    scores = [1.0, 0.95, 0.9, 0.5, 0.45, 0.1]
    assert M.variable_depth(scores, "gap", 0.1) == 3
    assert M.variable_depth(scores, "gap", 0.0) == 1
    assert M.variable_depth(scores, "gap", 5.0, cap=4) == 4
    # first drop >= 0.3 is after position 3 (0.9 -> 0.5)
    assert M.variable_depth(scores, "cliff", 0.3) == 3
    # no drop that large: cap / list length
    assert M.variable_depth(scores, "cliff", 2.0, cap=12) == 6
    assert M.variable_depth([], "gap", 0.1) == 0
    with pytest.raises(ValueError):
        M.variable_depth(scores, "other", 0.1)


def _pool():
    # rank = fused gold rank; target = intent-wrong, gold off note, gold in the depth-8 block
    return {
        "s1": {"rank": 1, "block_rank": 1, "on_note": True, "correct": True, "target": False},
        "s2": {"rank": 4, "block_rank": 4, "on_note": True, "correct": True, "target": False},
        "s3": {"rank": 6, "block_rank": 6, "on_note": False, "correct": False, "target": True},
        "s4": {"rank": 10, "block_rank": None, "on_note": False, "correct": False, "target": False},
        "s5": {"rank": None, "block_rank": None, "on_note": False, "correct": False, "target": False},
    }


def test_depth_rows_counts_losses_and_gains():
    rows = {x["d"]: x for x in M.depth_rows(_pool(), depths=(3, 5, 8, 12))}
    assert rows[8]["gold_in_block"] == 3 and rows[8]["targets_in_block"] == 1 and rows[8]["targets_total"] == 1
    assert rows[3]["gold_in_block"] == 1 and rows[3]["lost_vs_ref"] == 2
    assert rows[3]["lost_vs_ref_note_had_gold"] == 1 and rows[3]["lost_vs_ref_delivered_correct"] == 1
    assert rows[5]["lost_vs_ref"] == 1 and rows[5]["targets_in_block"] == 0
    assert rows[12]["gained_vs_ref"] == 1 and rows[12]["gained_vs_ref_intent_wrong"] == 1
    assert rows[5]["rank_hist"] == {"1": 1, "4": 1}


def test_note_given_block_rank():
    t = M.note_given_block_rank(_pool(), 6)
    assert t["1"] == {"rows": 1, "on_note": 1, "pct": 100.0}
    assert t["6"] == {"rows": 1, "on_note": 0, "pct": 0.0}
    assert t["off"]["rows"] == 2 and t["2"]["pct"] is None


def test_sweeps_and_crossfits():
    ids = [f"s{i}" for i in range(8)]
    # gold always at position 2 with a small gap; position 3+ far below
    scores = {s: [1.0, 0.95, 0.2, 0.1] for s in ids}
    rank = {s: 2 for s in ids}
    half = {s: i % 2 for i, s in enumerate(ids)}
    sweep = M.variable_sweep(scores, rank, set(ids[:2]), "gap", [0.01, 0.1])
    assert sweep[0]["gold_in_block"] == 0 and sweep[1]["gold_in_block"] == 8 and sweep[1]["mean_depth"] == 2.0
    assert sweep[1]["targets_in_block"] == 2
    cf = M.crossfit_variable(scores, rank, half, "gap", [0.01, 0.1, 0.9])
    assert cf["delta_chosen_on_half"] == {"0": 0.1, "1": 0.1}
    assert cf["out_of_half_mean_depth"] == 2.0 and cf["out_of_half_gold_in_block"] == 8 == cf["fixed_ref_gold_in_block"]
    budget = M.crossfit_budget(scores, rank, half, "gap", [0.01, 0.1, 0.9], 2.0)
    assert budget["out_of_half_gold_in_block"] == 8 and budget["fixed_depth"] == 2
    none = M.crossfit_budget(scores, rank, half, "gap", [0.9], 1.5)
    assert none["delta_chosen_on_half"] == {"0": None, "1": None} and none["out_of_half_mean_depth"] == 1.0


def test_entry_counts_and_net_rows():
    ranks = {"s1": 3, "s2": 10, "s3": 25, "s4": None}
    e = M.entry_counts(ranks, ranks)
    assert e["top8"] == 1 and e["top12"] == 2 and e["top20"] == 2 and e["rows"] == 4
    assert e["buckets"] == {"1-8": 1, "21-60": 1, "9-12": 1, "not recalled": 1}
    base = {"s1": 3, "s2": 10, "s3": 7}
    alt = {"s1": 3, "s2": 5, "s3": 9}
    flags = {"s1": {"correct": True, "on_note": True}, "s2": {"correct": False, "on_note": False},
             "s3": {"correct": True, "on_note": True}}
    n = M.net_rows(base, alt, flags)
    assert (n["enters"], n["leaves"], n["net"]) == (1, 1, 0)
    assert n["enters_intent_wrong"] == 1 and n["leaves_delivered_correct"] == 1 and n["leaves_note_had_gold"] == 1


def test_paired_boot_and_pick_class():
    lo, hi = M.paired_boot([1, 0, 0, -1, 1, 0] * 10)
    assert lo <= 1 / 6 <= hi
    assert M.paired_boot([]) == [None, None]
    note = ["i-a", "i-b", "i-c"]
    assert M.pick_class("i-b", note, "i-b") == "gold"
    assert M.pick_class("i-a", note, "i-b") == "note rank 1 (not gold)"
    assert M.pick_class("i-c", note, "i-b") == "other note candidate"
    assert M.pick_class("i-z", note, "i-b") == "off the note"
    assert M.pick_class(None, note, "i-b") == "unparsed"
