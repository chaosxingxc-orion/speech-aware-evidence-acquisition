"""Synthetic terminal-count proofs, not task efficacy or a runtime optimizer."""
from fractions import Fraction
import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[2] / "scripts/analysis/audit_system_ratio_objective.py"
spec = importlib.util.spec_from_file_location("ratio_objective_audit", path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_fixed_reference_reward_can_reverse_true_pooled_f1_ranking():
    states = [[(5, 0, 5), (10, 11, 0)]]
    weights = [Fraction(1)]
    assert all(tp + fn == 10 for tp, fp, fn in states[0])
    assert audit.choose_residual(states, Fraction(3, 5)) == (1,)
    result, trace = audit.solve_ratio(states, weights, initial=Fraction(3, 5))
    assert result == (0,)
    assert audit.pooled(states, weights, result) == Fraction(2, 3)
    assert audit.pooled(states, weights, (1,)) == Fraction(20, 31)
    assert trace[-1]["residual"] == "0"


def test_locally_best_f1_can_lose_to_joint_pooled_policy():
    states = [[(5, 0, 5), (10, 11, 0)], [(0, 0, 2), (0, 1, 2)]]
    weights = [Fraction(1, 2), Fraction(1, 2)]
    local = (0, 0)
    result, _ = audit.solve_ratio(states, weights, initial=Fraction(3, 5))
    assert result == (1, 0)
    assert audit.pooled(states, weights, local) == Fraction(10, 17)
    assert audit.pooled(states, weights, result) == Fraction(20, 33)


def test_empty_target_error_is_preserved_when_full_population_denominator_is_positive():
    states = [[(0, 0, 0), (0, 2, 0)], [(2, 0, 0), (2, 0, 0)]]
    result, _ = audit.solve_ratio(states, [Fraction(1, 2)]*2, initial=Fraction(3, 5))
    assert result == (0, 0)
    assert audit.pooled(states, [Fraction(1, 2)]*2, result) == 1


def test_zero_population_denominator_is_not_a_convergence_certificate():
    with pytest.raises(ValueError, match="positive"):
        audit.solve_ratio([[(0, 0, 0), (0, 1, 0)]], [Fraction(1)], initial=Fraction(3, 5))


def test_synthetic_matrix_sweep_matches_exhaustive_policy_search():
    result = audit.run_audit()
    assert result["source"] == "synthetic terminal count tables only"
    assert result["sweep"]["tables"] == 192
    assert result["sweep"]["all_ratio_optima_matched"]
    assert result["runtime_application_authorized"] is False
    assert result["model_contacts_added"] == result["scorer_contacts_added"] == 0


def test_equal_weighted_group_advantages_can_disagree_with_pooled_task_quality():
    result = audit.group_normalization_example()
    assert result["mean_advantage_selected_action"] == 1
    assert result["pooled_f1_selected_action"] == 0
    assert result["policies"][0]["pooled_f1"] > result["policies"][1]["pooled_f1"]
    assert result["policies"][1]["summed_raw_utility"] < result["policies"][0]["summed_raw_utility"]
