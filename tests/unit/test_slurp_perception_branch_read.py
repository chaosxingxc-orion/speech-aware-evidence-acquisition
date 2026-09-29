"""``scripts/analysis/slurp_perception_branch_read.py`` (same-flight instrument phase 2, merge
set C, item 4): pure, model-free, gold-free-at-import tests of the level-1 read -- gold rank,
paired top1/present bootstrap reads, the twin null bar, the utterance-level read beside it, and
the ledger-reproduction refusal. Every "gold label" here is a synthetic, made-up intent id string
passed directly by the test, never read from a real dataset file.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS_ANALYSIS = _REPO / "scripts" / "analysis"
if str(_SCRIPTS_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ANALYSIS))

import slurp_perception_branch_read as spbr  # noqa: E402


def _branches_receipt(candidates_by_branch: dict[str, tuple[str, ...]]) -> dict:
    return {
        "schema": "saea-perception-branch-arms-v1", "phase_id": "perception",
        "level": 1, "delivered_branch_id": "A",
        "branches": [
            {"branch_id": branch_id, "candidate_intent_ids": list(candidates)}
            for branch_id, candidates in candidates_by_branch.items()
        ],
    }


def _row(sample_id: str, candidates_by_branch: dict[str, tuple[str, ...]]) -> dict:
    return {
        "sample_id": sample_id,
        "native_episode_receipt": {"perception_branches": _branches_receipt(candidates_by_branch)},
    }


def test_branch_gold_rank_finds_gold_at_its_position():
    assert spbr.branch_gold_rank(("a", "b", "c"), "b") == 2
    assert spbr.branch_gold_rank(("a", "b", "c"), "a") == 1


def test_branch_gold_rank_is_none_when_gold_is_off_the_list():
    assert spbr.branch_gold_rank(("a", "b"), "z") is None


def test_branch_row_outcome_top1_present_and_rank_agree():
    outcome = spbr.branch_row_outcome(("gold", "other"), "gold")
    assert outcome == {"rank": 1, "present": True, "top1": True}
    outcome = spbr.branch_row_outcome(("other", "gold"), "gold")
    assert outcome == {"rank": 2, "present": True, "top1": False}
    outcome = spbr.branch_row_outcome(("other",), "gold")
    assert outcome == {"rank": None, "present": False, "top1": False}


def test_level1_row_outcomes_covers_every_declared_branch():
    row = _row("s1", {"B": ("x", "gold"), "T": ("gold",), "A": ("gold",)})
    outcomes = spbr.level1_row_outcomes(row, "gold")
    assert outcomes["B"]["rank"] == 2
    assert outcomes["T"]["top1"] is True
    assert outcomes["A"]["top1"] is True


def test_level1_row_outcomes_refuses_a_row_with_no_receipt():
    with pytest.raises(spbr.PerceptionBranchReadError, match="no perception_branches"):
        spbr.level1_row_outcomes({"sample_id": "s1", "native_episode_receipt": {}}, "gold")


def _rows_for_paired_read(n_promoted: int, n_total: int) -> list[dict]:
    """``n_promoted`` rows where B ranks gold 1st and A does not (B beats A); the rest agree."""

    rows = []
    for index in range(n_total):
        sample_id = f"slurp:train:s{index:04d}:0"
        if index < n_promoted:
            rows.append(_row(sample_id, {"B": ("gold", "other"), "T": ("other", "gold"), "A": ("other", "gold")}))
        else:
            rows.append(_row(sample_id, {"B": ("other", "gold"), "T": ("other", "gold"), "A": ("other", "gold")}))
    return rows


def test_paired_top1_read_finds_the_promoted_rows():
    rows = _rows_for_paired_read(n_promoted=20, n_total=100)
    gold = {row["sample_id"]: "gold" for row in rows}
    result = spbr.paired_top1_read(rows, gold, branch_id="B", against="A")
    assert result["n"] == 100
    assert result["discordant"] == 20
    assert result["point_pp"] == pytest.approx(20.0, abs=0.01)
    assert result["ci95"][0] < result["point_pp"] < result["ci95"][1]


def test_paired_top1_read_is_deterministic():
    rows = _rows_for_paired_read(n_promoted=15, n_total=80)
    gold = {row["sample_id"]: "gold" for row in rows}
    first = spbr.paired_top1_read(rows, gold, branch_id="B", against="A")
    second = spbr.paired_top1_read(rows, gold, branch_id="B", against="A")
    assert first == second


def test_paired_top1_read_ignores_rows_without_a_gold_label():
    rows = _rows_for_paired_read(n_promoted=5, n_total=10)
    gold = {rows[0]["sample_id"]: "gold"}
    result = spbr.paired_top1_read(rows, gold, branch_id="B", against="A")
    assert result["n"] == 1


def test_paired_top1_read_refuses_when_nothing_qualifies():
    with pytest.raises(spbr.PerceptionBranchReadError, match="no row"):
        spbr.paired_top1_read([], {}, branch_id="B", against="A")


def test_paired_present_read_uses_the_present_metric():
    rows = [
        _row("s1", {"B": ("gold",), "A": ()}),
        _row("s2", {"B": (), "A": ("gold",)}),
    ]
    gold = {"s1": "gold", "s2": "gold"}
    result = spbr.paired_present_read(rows, gold, branch_id="B", against="A")
    assert result["metric"] == "present"
    # +1 on s1 (B present, A absent), -1 on s2 (B absent, A present): net 0.
    assert result["point_pp"] == pytest.approx(0.0, abs=0.01)


def test_twin_null_bar_is_zero_when_t_and_a_always_agree():
    rows = [_row(f"s{i}", {"T": ("gold",), "A": ("gold",)}) for i in range(30)]
    gold = {row["sample_id"]: "gold" for row in rows}
    result = spbr.twin_null_bar(rows, gold)
    assert result["point_pp"] == pytest.approx(0.0, abs=0.01)
    assert result["abs_point_pp"] == pytest.approx(0.0, abs=0.01)
    assert result["half_width_pp"] >= 0.0


def test_utterance_id_groups_by_the_first_three_segments():
    assert spbr.utterance_id("slurp:train:s1:0") == "slurp:train:s1"
    assert spbr.utterance_id("slurp:train:s1:1") == "slurp:train:s1"
    assert spbr.utterance_id("slurp:train:s2:0") == "slurp:train:s2"


def test_utterance_level_read_clusters_multiple_rows_of_one_utterance():
    # Two rows of the SAME utterance ("s1"), one promoted and one not: averaged to 0.5 before
    # bootstrapping, unlike the row-level read which would see two independent 1.0/0.0 rows.
    rows = [
        _row("slurp:train:s1:0", {"B": ("gold", "other"), "A": ("other", "gold")}),
        _row("slurp:train:s1:1", {"B": ("other", "gold"), "A": ("other", "gold")}),
        _row("slurp:train:s2:0", {"B": ("other", "gold"), "A": ("other", "gold")}),
    ]
    gold = {row["sample_id"]: "gold" for row in rows}
    result = spbr.utterance_level_top1_read(rows, gold, branch_id="B", against="A")
    assert result["clustering"] == "utterance"
    assert result["n"] == 2  # two distinct utterances, not three rows


def test_assert_a_reproduces_ledger_counts_passes_within_tolerance():
    # 60 rank-1, 30 rank-2, 10 rank-3 out of 100 -> 60/30/10 %.
    rows = []
    for index in range(100):
        if index < 60:
            candidates = ("gold", "x", "y")
        elif index < 90:
            candidates = ("x", "gold", "y")
        else:
            candidates = ("x", "y", "gold")
        rows.append(_row(f"s{index}", {"A": candidates}))
    gold = {row["sample_id"]: "gold" for row in rows}
    result = spbr.assert_a_reproduces_ledger_counts(
        rows, gold, expected_rank1_pct=60.0, expected_rank2_pct=30.0, expected_rank3_pct=10.0,
    )
    assert result["total"] == 100
    assert result["observed_pct"][1] == pytest.approx(60.0)


def test_assert_a_reproduces_ledger_counts_refuses_a_drifted_a():
    rows = [_row(f"s{i}", {"A": ("x", "y", "gold")}) for i in range(50)]  # all rank 3
    gold = {row["sample_id"]: "gold" for row in rows}
    with pytest.raises(spbr.PerceptionBranchReadError, match="disagrees with the node ledger"):
        spbr.assert_a_reproduces_ledger_counts(
            rows, gold, expected_rank1_pct=97.57, expected_rank2_pct=26.98, expected_rank3_pct=12.0,
        )


def test_assert_a_reproduces_ledger_counts_refuses_with_no_gold_rows():
    with pytest.raises(spbr.PerceptionBranchReadError, match="no row carried a gold label"):
        spbr.assert_a_reproduces_ledger_counts(
            [], {}, expected_rank1_pct=1.0, expected_rank2_pct=1.0, expected_rank3_pct=1.0,
        )
