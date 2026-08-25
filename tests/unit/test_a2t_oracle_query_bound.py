"""Pure-function gates for the Audio2Tool oracle-query bound row.

No sealed bytes and no data root are touched here: these tests pin the
arithmetic the row's conclusions rest on -- what a mixing weight MEANS, which
stage is named as binding, and where the pre-registered decision bands sit --
so a later refactor cannot silently change any of them.
"""

from __future__ import annotations

import math

import pytest

from speech_aware_evidence_acquisition.analysis import (
    a2t_oracle_query_bound as oracle,
)


class TestL2Normalize:
    def test_it_returns_a_unit_vector(self) -> None:
        assert oracle.l2_normalize((3.0, 4.0)) == pytest.approx((0.6, 0.8))

    def test_it_is_scale_invariant(self) -> None:
        assert oracle.l2_normalize((3.0, 4.0)) == pytest.approx(
            oracle.l2_normalize((30.0, 40.0))
        )

    def test_a_zero_vector_is_refused_rather_than_silently_returned(self) -> None:
        with pytest.raises(oracle.OracleBoundError):
            oracle.l2_normalize((0.0, 0.0))


class TestMixDirections:
    """``lambda`` = 0 must be the flown direction EXACTLY -- that identity is
    what makes the N2 ladder's zero cell a self-check against the flight."""

    def test_weight_zero_is_the_left_direction(self) -> None:
        assert oracle.mix_directions((3.0, 4.0), (0.0, 1.0), 0.0) == pytest.approx(
            (0.6, 0.8)
        )

    def test_weight_one_is_the_right_direction(self) -> None:
        assert oracle.mix_directions((3.0, 4.0), (0.0, 5.0), 1.0) == pytest.approx(
            (0.0, 1.0)
        )

    def test_the_mixture_weights_directions_not_magnitudes(self) -> None:
        """A 1000x longer right-hand vector must not drag the midpoint: both
        sides are unit-normalised before mixing."""

        small = oracle.mix_directions((1.0, 0.0), (0.0, 1.0), 0.5)
        huge = oracle.mix_directions((1.0, 0.0), (0.0, 1000.0), 0.5)
        assert small == pytest.approx(huge)
        assert small == pytest.approx((math.sqrt(0.5), math.sqrt(0.5)))

    def test_the_result_is_always_unit_length(self) -> None:
        for weight in oracle.LAMBDA_GRID:
            mixed = oracle.mix_directions((1.0, 2.0, 3.0), (3.0, -1.0, 0.5), weight)
            assert math.sqrt(sum(v * v for v in mixed)) == pytest.approx(1.0)

    def test_a_weight_outside_the_unit_interval_is_refused(self) -> None:
        with pytest.raises(oracle.OracleBoundError):
            oracle.mix_directions((1.0, 0.0), (0.0, 1.0), 1.5)

    def test_a_dimension_mismatch_is_refused(self) -> None:
        with pytest.raises(oracle.OracleBoundError):
            oracle.mix_directions((1.0, 0.0), (0.0, 1.0, 0.0), 0.5)

    def test_the_grid_runs_from_zero_to_one_inclusive(self) -> None:
        assert oracle.LAMBDA_GRID[0] == 0.0
        assert oracle.LAMBDA_GRID[-1] == 1.0
        assert len(oracle.LAMBDA_GRID) == 11


class TestClassifyBindingStage:
    """The stages must be named in PIPELINE order, so the FIRST obstruction is
    reported rather than the last one a reader happens to notice."""

    @staticmethod
    def _call(**overrides: object) -> dict[str, object]:
        base: dict[str, object] = {
            "gold_supplied": False,
            "has_vectored_gold_facet": True,
            "best_gold_cosine": 0.90,
            "gold_facet_position": 1,
            "gold_facet_in_admitted_window": True,
            "gold_target_rank_among_tau_passing": 1,
        }
        base.update(overrides)
        return oracle.classify_binding_stage(**base)  # type: ignore[arg-type]

    def test_a_supplied_trajectory_has_no_binding_stage(self) -> None:
        result = self._call(gold_supplied=True)
        assert result["stage"] == "supplied"
        assert result["kind"] is None

    def test_missing_kb_coverage_is_a_data_property(self) -> None:
        result = self._call(has_vectored_gold_facet=False)
        assert result["stage"] == "kb_coverage"
        assert result["kind"] == "data"

    def test_a_cosine_below_tau_binds_before_the_window(self) -> None:
        """The landed 0.5653-0.6356 band: below tau, and the window is then
        irrelevant at every depth."""

        result = self._call(best_gold_cosine=0.6054, gold_facet_position=999)
        assert result["stage"] == "tau_gate"
        assert result["kind"] == "data-against-a-knob"

    def test_a_facet_outside_the_locked_window_binds_on_the_window(self) -> None:
        result = self._call(best_gold_cosine=0.80, gold_facet_position=14)
        assert result["stage"] == "recall_depth_k"
        assert result["kind"] == "knob"

    def test_a_target_outside_top_l_binds_on_the_target_budget(self) -> None:
        result = self._call(gold_target_rank_among_tau_passing=8)
        assert result["stage"] == "top_l_target_budget"
        assert result["kind"] == "knob"

    def test_an_unranked_target_is_treated_as_outside_top_l(self) -> None:
        result = self._call(gold_target_rank_among_tau_passing=None)
        assert result["stage"] == "top_l_target_budget"

    def test_an_unexplained_absence_is_reported_not_attributed(self) -> None:
        """Every named stage passes and the gold value is still absent. That
        must surface as `unclassified` rather than be blamed on a stage."""

        result = self._call()
        assert result["stage"] == "unclassified"
        assert result["kind"] is None


class TestDecisionRule:
    """The bands were fixed in the registration before any number was seen and
    are pinned here so no later edit can quietly move them."""

    def test_the_registered_bands(self) -> None:
        assert oracle.REFUTED_AT_OR_BELOW == 1
        assert oracle.SURVIVES_AT_OR_ABOVE == 8

    @pytest.mark.parametrize("supplied", [0, 1])
    def test_zero_or_one_refutes(self, supplied: int) -> None:
        assert oracle.decision_rule(supplied, 11)["outcome"] == "REFUTED"

    @pytest.mark.parametrize("supplied", [2, 5, 7])
    def test_the_middle_band_is_inconclusive(self, supplied: int) -> None:
        assert oracle.decision_rule(supplied, 11)["outcome"] == "INCONCLUSIVE"

    @pytest.mark.parametrize("supplied", [8, 11])
    def test_a_substantial_majority_survives(self, supplied: int) -> None:
        assert oracle.decision_rule(supplied, 11)["outcome"] == "SURVIVES"

    def test_surviving_says_out_loud_that_it_authorizes_nothing(self) -> None:
        verdict = str(oracle.decision_rule(11, 11)["verdict"])
        assert "AUTHORIZES NOTHING" in verdict
        assert "upper bound" in verdict
        assert "K3" in verdict

    def test_the_bands_travel_with_every_verdict(self) -> None:
        bands = oracle.decision_rule(6, 11)["bands_fixed_in_the_registration"]
        assert bands["refuted_at_or_below"] == 1
        assert bands["survives_at_or_above"] == 8
        assert bands["inconclusive_between"] == [2, 7]


class TestFrozenCellIsNotDrifted:
    """This row replays the LOCKED cell. If any of these move, the row is no
    longer a bound on the locked cell and must not be cited as one."""

    def test_the_locked_knobs(self) -> None:
        assert oracle.FROZEN_FUSE.tau == pytest.approx(0.65)
        assert oracle.FROZEN_FUSE.m == 5
        assert oracle.FROZEN_FUSE.c == 2
        assert oracle.FROZEN_FUSE.top_l == 3
        assert oracle.FROZEN_TOP_K == 5
        assert oracle.FROZEN_ALPHA == pytest.approx(0.45)

    def test_the_landed_band_and_split_the_gate_must_reproduce(self) -> None:
        assert oracle.LANDED_TAU_BAND == (0.565332, 0.635625)
        assert oracle.LANDED_DISPATCHED_N == 15
        assert oracle.LANDED_GOLD_BEARING_N == 4
        assert oracle.LANDED_GOLD_ABSENT_N == 11
