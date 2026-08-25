"""Unit tests for the pure arithmetic of the MATCHING-versus-EXTRACTION read.

Only the data-free logic is exercised here: the four-cell partition and the
two decompositions. Everything else in that module reads sealed bytes under
``SPEECHRL_DATA_DIR`` and is covered by the read's own fail-closed fidelity
gate, which reproduces the already-landed aggregates to full float precision
before a single new number is published.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis import matching_vs_extraction_read as mve


def _toy():
    """Six samples spanning all four cells, with hand-checkable extraction."""

    ids = ("s1", "s2", "s3", "s4", "s5", "s6")
    m0_match = {"s1": 1, "s2": 1, "s3": 0, "s4": 0, "s5": 1, "s6": 0}
    blend_match = {"s1": 1, "s2": 1, "s3": 1, "s4": 0, "s5": 0, "s6": 0}
    m0_value = {"s1": 0.2, "s2": 0.4, "s3": 0.0, "s4": 0.1, "s5": 0.5, "s6": 0.3}
    blend_value = {"s1": 0.2, "s2": 0.6, "s3": 0.8, "s4": 0.3, "s5": 0.1, "s6": 0.3}
    return ids, m0_match, blend_match, m0_value, blend_value


def test_partition_is_exhaustive_and_disjoint():
    ids, m0_match, blend_match, _, _ = _toy()
    cells = mve.partition_cells(sample_ids=ids, m0_match=m0_match, blend_match=blend_match)

    assert set(cells) == set(mve.CELL_ORDER)
    assert cells["both_matched"] == ("s1", "s2")
    assert cells["blend_only_matched"] == ("s3",)
    assert cells["m0_only_matched"] == ("s5",)
    assert cells["neither_matched"] == ("s4", "s6")

    flat = [sid for name in mve.CELL_ORDER for sid in cells[name]]
    assert sorted(flat) == sorted(ids)
    assert len(flat) == len(set(flat))


def test_partition_rejects_a_non_binary_matching_outcome():
    with pytest.raises(mve.ReadError):
        mve.partition_cells(
            sample_ids=("s1",), m0_match={"s1": 2}, blend_match={"s1": 1}
        )


def test_joint_contributions_reconstruct_the_aggregate_exactly():
    ids, m0_match, blend_match, m0_value, blend_value = _toy()
    cells = mve.partition_cells(sample_ids=ids, m0_match=m0_match, blend_match=blend_match)
    block = mve.joint_cell_contributions(
        cells=cells, n_total=len(ids), m0_value=m0_value, blend_value=blend_value
    )

    expected = sum(blend_value[sid] - m0_value[sid] for sid in ids) / len(ids)
    assert block["aggregate_delta"] == pytest.approx(expected, abs=1e-12)
    assert block["reconstructed_delta"] == pytest.approx(expected, abs=1e-12)
    assert abs(block["reconstruction_residual"]) < 1e-9

    # The joint weights are shared by both arms, so a cell's contribution is
    # exactly its share times its paired delta.
    both = block["cells"]["both_matched"]
    assert both["n"] == 2
    assert both["weight"] == pytest.approx(2 / 6)
    assert both["delta"] == pytest.approx(((0.2 + 0.6) - (0.2 + 0.4)) / 2)
    assert both["contribution_to_aggregate_delta"] == pytest.approx(
        both["weight"] * both["delta"]
    )


def test_ab_split_closes_and_names_the_dominant_term():
    ids, m0_match, blend_match, m0_value, blend_value = _toy()
    cells = mve.partition_cells(sample_ids=ids, m0_match=m0_match, blend_match=blend_match)
    split = mve.joint_cell_contributions(
        cells=cells, n_total=len(ids), m0_value=m0_value, blend_value=blend_value
    )["ab_split"]

    assert split["a_cells"] == ["blend_only_matched", "m0_only_matched"]
    assert split["b_cells"] == ["both_matched", "neither_matched"]
    total = split["a_matching_attributable"] + split["b_matching_independent"]
    aggregate = sum(blend_value[sid] - m0_value[sid] for sid in ids) / len(ids)
    assert total == pytest.approx(aggregate, abs=1e-12)
    assert split["a_share_of_absolute_total"] + split["b_share_of_absolute_total"] == pytest.approx(
        1.0
    )
    dominant = (
        "(a)" if abs(split["a_matching_attributable"]) > abs(split["b_matching_independent"])
        else "(b)"
    )
    assert split["verdict"].startswith(dominant)


def test_marginal_decomposition_closes_in_both_orderings():
    ids, m0_match, blend_match, m0_value, blend_value = _toy()
    block = mve.marginal_decomposition(
        sample_ids=ids,
        m0_match=m0_match,
        blend_match=blend_match,
        m0_value=m0_value,
        blend_value=blend_value,
    )

    aggregate = block["aggregate_delta"]
    direct = sum(blend_value[sid] for sid in ids) / len(ids) - sum(
        m0_value[sid] for sid in ids
    ) / len(ids)
    assert aggregate == pytest.approx(direct, abs=1e-12)

    for ordering in ("primary_ordering", "mirror_ordering"):
        terms = block[ordering]
        assert terms["a_reweighting_from_matching_gain"] + terms[
            "b_net_within_cell_extraction"
        ] == pytest.approx(aggregate, abs=1e-12)
        assert terms["closes_exactly"] is True

    assert isinstance(block["verdict_stable_across_orderings"], bool)
    if not block["verdict_stable_across_orderings"]:
        assert block["verdict"] == "UNSTABLE ACROSS ORDERINGS"


def test_marginal_decomposition_refuses_an_empty_population():
    with pytest.raises(mve.ReadError):
        mve.marginal_decomposition(
            sample_ids=(), m0_match={}, blend_match={}, m0_value={}, blend_value={}
        )


def test_fidelity_targets_are_the_landed_aggregates():
    """The gate targets are constants, so a silent edit of them is a defect
    the suite catches rather than something a future reader has to notice."""

    assert mve.SLURP_FIDELITY_TARGETS["unexposed500"]["M0"] == {
        "scenario_action_exact": 278,
        "slot_f1_exact_mean": 0.17097619047619048,
    }
    assert mve.SLURP_FIDELITY_TARGETS["unexposed500"]["BLEND"] == {
        "scenario_action_exact": 379,
        "slot_f1_exact_mean": 0.20641428571428572,
    }
    assert mve.SLURP_FIDELITY_TARGETS["exposed500"]["M0"] == {
        "scenario_action_exact": 258,
        "slot_f1_exact_mean": 0.12224761904761905,
    }
    assert mve.SLURP_FIDELITY_TARGETS["exposed500"]["BLEND"] == {
        "scenario_action_exact": 378,
        "slot_f1_exact_mean": 0.15097142857142856,
    }
    assert mve.A2T_FIDELITY_TARGETS == {
        "M0": {"tool_accuracy_count": 62, "exact_match_count": 29, "empty_call_count": 14},
        "BLEND": {"tool_accuracy_count": 63, "exact_match_count": 29, "empty_call_count": 3},
    }


def test_bootstrap_seed_and_replicates_match_the_campaign():
    assert mve.BOOTSTRAP_SEED == 20260807
    assert mve.BOOTSTRAP_N == 10_000
