"""The harm bound is a RATE, on both carriers and at both stages.

Owner decision, 2026-09-06. Stage one admits a candidate with at most
``harms`` harms per ``harms_per_rows`` fold rows, and stage three tolerates
``harms - saves`` up to the same rate on an admitted scenario's own fold-B
rows -- never below the base count, so a small fold is not held to a looser
bound than a large one. The two live loop configs are the two cases: EVO-A1
draws 20 rows per targeted tool and keeps reading "at most 1" without
declaring the field at all, while EVO-S1's V2 draw of 60 rows per scenario
reads "at most 2".

Every score table here is hand-built, so each verdict is recountable by eye.
Zero model contacts, zero carrier reads.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.paired import PairedAnalysisError
from speech_aware_evidence_acquisition.rails.evolution import (
    HARMS_PER_ROWS,
    AdmissionGates,
    EvolutionError,
    LoopConfig,
    PerTargetHarmBound,
    Target,
    confirm_assembly,
    harm_allowance,
    select_per_target,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
A2T_LOOP_CONFIG = REPO_ROOT / "configs" / "knowledge" / "a2t-evo-a1" / "loop-v1.json"
SLURP_LOOP_CONFIG = REPO_ROOT / "configs" / "knowledge" / "slurp-evo-s1" / "loop-v1.json"

#: The two fold quotas the rate has to serve: a tool target on EVO-A1 and a
#: scenario target on EVO-S1's V2 draw.
A2T_ROWS_PER_TARGET = 20
SLURP_ROWS_PER_TARGET = 60

METRIC = "tool_correct"


def rows(prefix: str, count: int) -> list[str]:
    return [f"{prefix}:{index:06d}" for index in range(count)]


def scores(sample_ids, values) -> dict[str, dict[str, float]]:
    assert len(sample_ids) == len(values)
    return {sid: {METRIC: float(value)} for sid, value in zip(sample_ids, values)}


def contrast_arm(n: int, *, saves: int, harms: int):
    """An incumbent/arm pair over ``n`` rows with exactly these counts.

    The incumbent is wrong on the first ``saves`` rows and right on the next
    ``harms``; the arm swaps both. Every remaining row ties at 1.0, so nothing
    but the two counts moves.
    """

    assert saves + harms <= n
    ids = rows("row", n)
    ties = n - saves - harms
    incumbent = scores(ids, [0.0] * saves + [1.0] * harms + [1.0] * ties)
    arm = scores(ids, [1.0] * saves + [0.0] * harms + [1.0] * ties)
    return ids, incumbent, arm


# ---------------------------------------------------------------------------
# The rate itself
# ---------------------------------------------------------------------------


def test_harm_allowance_is_one_per_thirty_rows_floored_at_the_base():
    assert harm_allowance(1, n_rows=20, per_rows=30) == 1
    assert harm_allowance(1, n_rows=29, per_rows=30) == 1
    assert harm_allowance(1, n_rows=30, per_rows=30) == 1
    assert harm_allowance(1, n_rows=59, per_rows=30) == 1
    assert harm_allowance(1, n_rows=60, per_rows=30) == 2
    assert harm_allowance(1, n_rows=90, per_rows=30) == 3
    # A base of 2 is two harms per 30 rows, not two harms in total.
    assert harm_allowance(2, n_rows=60, per_rows=30) == 4


def test_harm_allowance_without_a_denominator_is_the_unscaled_base():
    assert harm_allowance(1, n_rows=None, per_rows=30) == 1
    assert harm_allowance(3, n_rows=None, per_rows=30) == 3


def test_harm_allowance_refuses_a_nonsense_rate():
    with pytest.raises(EvolutionError, match="positive integer"):
        harm_allowance(1, n_rows=60, per_rows=0)
    with pytest.raises(EvolutionError, match="positive integer"):
        harm_allowance(1, n_rows=60, per_rows=True)
    with pytest.raises(EvolutionError, match="nonnegative integer"):
        harm_allowance(-1, n_rows=60, per_rows=30)
    with pytest.raises(EvolutionError, match="n_rows"):
        harm_allowance(1, n_rows=-5, per_rows=30)


# ---------------------------------------------------------------------------
# Stage one, both carriers
# ---------------------------------------------------------------------------


def test_admission_gates_scale_the_harm_half_only():
    gates = AdmissionGates()
    assert (gates.saves, gates.harms, gates.net, gates.harms_per_rows) == (
        4,
        1,
        3,
        HARMS_PER_ROWS,
    )
    # A2T: 20 rows, so the rate reproduces the absolute rule exactly.
    assert gates.allowed_harms(A2T_ROWS_PER_TARGET) == 1
    assert gates.admits(saves=4, harms=1, n_rows=A2T_ROWS_PER_TARGET) is True
    assert gates.admits(saves=6, harms=2, n_rows=A2T_ROWS_PER_TARGET) is False
    # SLURP: 60 rows, so two harms are inside the bound.
    assert gates.allowed_harms(SLURP_ROWS_PER_TARGET) == 2
    assert gates.admits(saves=6, harms=2, n_rows=SLURP_ROWS_PER_TARGET) is True
    assert gates.admits(saves=6, harms=3, n_rows=SLURP_ROWS_PER_TARGET) is False
    # saves and net stay absolute counts at every n.
    assert gates.admits(saves=3, harms=0, n_rows=SLURP_ROWS_PER_TARGET) is False
    assert gates.admits(saves=4, harms=2, n_rows=SLURP_ROWS_PER_TARGET) is False


def test_admission_gates_without_a_row_count_stay_at_the_base():
    gates = AdmissionGates()
    assert gates.allowed_harms(None) == 1
    assert gates.admits(saves=6, harms=2) is False


def test_stage_one_admits_two_harms_on_a_sixty_row_scenario_target():
    ids, incumbent, arm = contrast_arm(SLURP_ROWS_PER_TARGET, saves=6, harms=2)
    decisions = select_per_target(
        incumbent,
        {1: arm},
        targets=[Target(target_id="alarm", tools=("alarm",), kind="scenario")],
        rows_of_target={"alarm": ids},
        metric=METRIC,
    )
    outcome = decisions["alarm"].outcomes[0]
    assert (outcome.n, outcome.saves, outcome.harms) == (SLURP_ROWS_PER_TARGET, 6, 2)
    assert outcome.harms_allowed == 2
    assert outcome.admitted is True
    assert decisions["alarm"].winner_k == 1


def test_stage_one_refuses_the_same_counts_on_a_twenty_row_tool_target():
    ids, incumbent, arm = contrast_arm(A2T_ROWS_PER_TARGET, saves=6, harms=2)
    decisions = select_per_target(
        incumbent,
        {1: arm},
        targets=[Target(target_id="pair-a", tools=("toolA0", "toolA1"))],
        rows_of_target={"pair-a": ids},
        metric=METRIC,
    )
    outcome = decisions["pair-a"].outcomes[0]
    assert (outcome.n, outcome.saves, outcome.harms) == (A2T_ROWS_PER_TARGET, 6, 2)
    assert outcome.harms_allowed == 1
    assert outcome.admitted is False
    assert decisions["pair-a"].winner_k is None


def test_stage_one_still_refuses_three_harms_on_a_sixty_row_target():
    ids, incumbent, arm = contrast_arm(SLURP_ROWS_PER_TARGET, saves=9, harms=3)
    decisions = select_per_target(
        incumbent,
        {1: arm},
        targets=[Target(target_id="alarm", tools=("alarm",), kind="scenario")],
        rows_of_target={"alarm": ids},
        metric=METRIC,
    )
    outcome = decisions["alarm"].outcomes[0]
    assert (outcome.harms, outcome.harms_allowed, outcome.admitted) == (3, 2, False)


def test_the_allowance_follows_the_paired_n_of_this_target_alone():
    """A thinner target reads a smaller allowance in the same round.

    The denominator is the contrast's own paired ``n``, so a scenario that
    drew 45 rows is held to one harm while a 60-row scenario beside it is
    allowed two -- the gate object is shared, the reading is not.
    """

    wide_ids, wide_inc, wide_arm = contrast_arm(SLURP_ROWS_PER_TARGET, saves=6, harms=2)
    thin_ids = rows("thin", 45)
    thin_inc = scores(thin_ids, [0.0] * 6 + [1.0] * 2 + [1.0] * 37)
    thin_arm = scores(thin_ids, [1.0] * 6 + [0.0] * 2 + [1.0] * 37)
    decisions = select_per_target(
        {**wide_inc, **thin_inc},
        {1: {**wide_arm, **thin_arm}},
        targets=[
            Target(target_id="alarm", tools=("alarm",), kind="scenario"),
            Target(target_id="news", tools=("news",), kind="scenario"),
        ],
        rows_of_target={"alarm": wide_ids, "news": thin_ids},
        metric=METRIC,
    )
    wide = decisions["alarm"].outcomes[0]
    thin = decisions["news"].outcomes[0]
    assert (wide.n, wide.harms, wide.harms_allowed, wide.admitted) == (60, 2, 2, True)
    assert (thin.n, thin.harms, thin.harms_allowed, thin.admitted) == (45, 2, 1, False)


def test_a_row_missing_from_a_score_file_is_refused_not_reweighted():
    """The allowance can never be widened by a hole in the evidence."""

    ids, incumbent, arm = contrast_arm(SLURP_ROWS_PER_TARGET, saves=6, harms=2)
    thin = {sid: value for sid, value in arm.items() if sid != ids[-1]}
    with pytest.raises(PairedAnalysisError, match="absent from"):
        select_per_target(
            incumbent,
            {1: thin},
            targets=[Target(target_id="alarm", tools=("alarm",), kind="scenario")],
            rows_of_target={"alarm": ids},
            metric=METRIC,
        )


def test_the_receipt_carries_the_allowance_beside_the_raw_counts():
    ids, incumbent, arm = contrast_arm(SLURP_ROWS_PER_TARGET, saves=6, harms=2)
    decisions = select_per_target(
        incumbent,
        {1: arm},
        targets=[Target(target_id="alarm", tools=("alarm",), kind="scenario")],
        rows_of_target={"alarm": ids},
        metric=METRIC,
    )
    document = decisions["alarm"].as_json()
    assert json.dumps(document)
    entry = document["outcomes"][0]
    assert entry["harms"] == 2
    assert entry["harms_allowed"] == 2
    assert entry["n"] == SLURP_ROWS_PER_TARGET
    assert AdmissionGates().as_json()["harms_per_rows"] == HARMS_PER_ROWS


# ---------------------------------------------------------------------------
# Stage three, the per-scenario bound
# ---------------------------------------------------------------------------


def bound_case(net_harm_rows: int, n_rows: int) -> tuple[dict, dict, list[str]]:
    """One admitted scenario whose fold-B rows net exactly ``net_harm_rows``.

    Two saves are always present, so the case is a genuine mixture rather than
    harms alone, and the pooled targeted gain is supplied separately by a
    clean second scenario.
    """

    ids = rows("scenario", n_rows)
    saves = 2
    harms = saves + net_harm_rows
    ties = n_rows - saves - harms
    assert ties >= 0
    incumbent = scores(ids, [0.0] * saves + [1.0] * harms + [1.0] * ties)
    assembly = scores(ids, [1.0] * saves + [0.0] * harms + [1.0] * ties)
    return incumbent, assembly, ids


def clean_gain(prefix: str, n_rows: int) -> tuple[dict, dict, list[str]]:
    """A second admitted scenario that only saves, so the pooled CI90 clears."""

    ids = rows(prefix, n_rows)
    incumbent = scores(ids, [0.0] * n_rows)
    assembly = scores(ids, [1.0] * n_rows)
    return incumbent, assembly, ids


def confirm(net_harm_rows: int, n_rows: int):
    harmed_inc, harmed_asm, harmed_ids = bound_case(net_harm_rows, n_rows)
    clean_inc, clean_asm, clean_ids = clean_gain("clean", n_rows)
    return confirm_assembly(
        {**harmed_inc, **clean_inc},
        {**harmed_asm, **clean_asm},
        targeted_rows=[*harmed_ids, *clean_ids],
        metric=METRIC,
        harm_bound=PerTargetHarmBound(),
        rows_of_target={"harmed": harmed_ids, "clean": clean_ids},
        admitted_targets=["harmed", "clean"],
        seed=20260903,
        n_replicates=200,
    )


def test_the_bound_tolerates_two_net_harm_rows_at_sixty_and_not_three():
    accepted = confirm(2, SLURP_ROWS_PER_TARGET)
    assert accepted.accepted is True
    assert "harms - saves <= 1 per 30 rows" in accepted.reason
    harmed = next(
        record for record in accepted.per_target if record["target_id"] == "harmed"
    )
    assert harmed["net_harm_rows"] == 2
    assert harmed["net_harm_rows_allowed"] == 2
    assert harmed["within_harm_bound"] is True

    rejected = confirm(3, SLURP_ROWS_PER_TARGET)
    assert rejected.accepted is False
    assert "harmed (harms - saves = 3 over 2 allowed at n = 60)" in rejected.reason


def test_the_bound_still_tolerates_only_one_net_harm_row_at_twenty():
    accepted = confirm(1, A2T_ROWS_PER_TARGET)
    assert accepted.accepted is True
    harmed = next(
        record for record in accepted.per_target if record["target_id"] == "harmed"
    )
    assert harmed["net_harm_rows_allowed"] == 1

    rejected = confirm(2, A2T_ROWS_PER_TARGET)
    assert rejected.accepted is False
    assert "harms - saves = 2 over 1 allowed at n = 20" in rejected.reason


def test_the_bound_reports_the_rate_it_used():
    decision = confirm(2, SLURP_ROWS_PER_TARGET)
    document = decision.as_json()
    assert json.dumps(document)
    assert document["harm_bound"] == {
        "max_net_harm_rows": 1,
        "unadmitted_tolerance_pp": -1.0,
        "harms_per_rows": HARMS_PER_ROWS,
    }
    assert PerTargetHarmBound().allowed_net_harm_rows(None) == 1


def test_the_bound_refuses_a_nonsense_rate():
    with pytest.raises(EvolutionError, match="harms_per_rows must be a positive"):
        PerTargetHarmBound(harms_per_rows=0).validate()


# ---------------------------------------------------------------------------
# The two live loop configs
# ---------------------------------------------------------------------------


def test_the_a2t_loop_config_reads_one_harm_without_declaring_the_field():
    document = json.loads(A2T_LOOP_CONFIG.read_text(encoding="utf-8"))
    assert "harms_per_rows" not in document
    config = LoopConfig.from_json(document)
    assert config.harms_per_rows == HARMS_PER_ROWS
    assert config.gates.harms_per_rows == HARMS_PER_ROWS
    assert config.gates.allowed_harms(A2T_ROWS_PER_TARGET) == 1
    assert config.gates.admits(saves=6, harms=2, n_rows=A2T_ROWS_PER_TARGET) is False
    assert config.harm_bound is None


def test_the_slurp_loop_config_reads_two_harms_on_its_sixty_row_scenarios():
    document = json.loads(SLURP_LOOP_CONFIG.read_text(encoding="utf-8"))
    assert document["harms_per_rows"] == HARMS_PER_ROWS
    config = LoopConfig.from_json(document)
    assert config.harms_per_rows == HARMS_PER_ROWS
    assert config.gates.allowed_harms(SLURP_ROWS_PER_TARGET) == 2
    assert config.gates.admits(saves=6, harms=2, n_rows=SLURP_ROWS_PER_TARGET) is True
    assert config.harm_bound is not None
    assert config.harm_bound.harms_per_rows == HARMS_PER_ROWS
    assert config.harm_bound.allowed_net_harm_rows(SLURP_ROWS_PER_TARGET) == 2
    assert config.harm_bound.unadmitted_tolerance_pp == -1.0


def test_the_rate_has_exactly_one_spelling_in_a_loop_config():
    document = json.loads(SLURP_LOOP_CONFIG.read_text(encoding="utf-8"))
    document["harms_per_rows"] = 20
    assert LoopConfig.from_json(document).gates.harms_per_rows == 20

    hidden_in_gates = json.loads(SLURP_LOOP_CONFIG.read_text(encoding="utf-8"))
    hidden_in_gates["gates"] = {**hidden_in_gates["gates"], "harms_per_rows": 20}
    with pytest.raises(EvolutionError, match="gates carries unknown key"):
        LoopConfig.from_json(hidden_in_gates)

    hidden_in_bound = json.loads(SLURP_LOOP_CONFIG.read_text(encoding="utf-8"))
    hidden_in_bound["harm_bound"] = {
        **hidden_in_bound["harm_bound"],
        "harms_per_rows": 20,
    }
    with pytest.raises(EvolutionError, match="harm_bound carries unknown key"):
        LoopConfig.from_json(hidden_in_bound)

    nonsense = json.loads(SLURP_LOOP_CONFIG.read_text(encoding="utf-8"))
    nonsense["harms_per_rows"] = 0
    with pytest.raises(EvolutionError, match="harms_per_rows must be a positive"):
        LoopConfig.from_json(nonsense)
