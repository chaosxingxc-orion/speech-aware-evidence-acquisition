"""``rails.evolution``: targets, portfolios, the two-stage decision, the
stop rule, the round receipt and its model-free replay.

Every per-sample score table here is hand-built, so each admission,
tie-break and confirmation verdict is recountable by eye from the numbers in
the test itself rather than from a fixture nobody reads. The replay test
writes real ``<job_id>.score.json`` files in the shape
``core.scoring_batch.run_score_batch`` produces and recomputes the whole
round from them.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.evolution import (
    BACKGROUND_TOLERANCE_PP,
    INCUMBENT_KEY,
    MAX_ROUNDS,
    SENTINEL_SCHEMA,
    AdmissionGates,
    EvolutionError,
    EvolutionState,
    LoopConfig,
    Portfolio,
    RoundOutcome,
    Target,
    assemble_portfolio,
    assert_disjoint_targets,
    confirm_assembly,
    ledger_budget,
    prompt_noise_floor,
    question_sha256,
    replay_selection,
    select_per_target,
    selection_record,
    sentinel_harms,
    should_stop,
    write_candidate_fragments,
    write_round_receipt,
)
from speech_aware_evidence_acquisition.rails.proposer import (
    ProposerError,
    proposer_candidate,
)

METRIC = "tool_correct"
SCORER = "a2t-toolcall-official"
PROMPT_SHA = "c" * 64

TARGET_A = Target(target_id="pair-a", tools=("toolA0", "toolA1"))
TARGET_B = Target(target_id="pair-b", tools=("toolB0", "toolB1"))


def candidate(target: Target, k: int, *, round: int = 1, text: str = "x") -> object:
    return proposer_candidate(
        f"cue {k}",
        {tool: f"{text} for {tool} at slot {k}" for tool in target.tools},
        target_id=target.target_id,
        round=round,
        k=k,
        proposer_prompt_sha256=PROMPT_SHA,
        exemplar_ids=(f"tier1_direct:00010{k}",),
    )


def rows(prefix: str, count: int) -> list[str]:
    return [f"{prefix}:{index:06d}" for index in range(count)]


def scores(sample_ids, values) -> dict[str, dict[str, float]]:
    """``{sample_id: {metric: value}}`` from parallel sequences."""

    assert len(sample_ids) == len(values)
    return {sid: {METRIC: float(value)} for sid, value in zip(sample_ids, values)}


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------


def test_targets_must_be_disjoint_and_uniquely_named():
    assert assert_disjoint_targets([TARGET_A, TARGET_B]) == (TARGET_A, TARGET_B)
    with pytest.raises(EvolutionError, match="must be disjoint"):
        assert_disjoint_targets(
            [TARGET_A, Target(target_id="pair-c", tools=("toolA1", "toolC0"))]
        )
    with pytest.raises(EvolutionError, match="duplicate target_id"):
        assert_disjoint_targets(
            [TARGET_A, Target(target_id="pair-a", tools=("toolC0", "toolC1"))]
        )


def test_a_target_of_one_tool_is_refused():
    with pytest.raises(EvolutionError, match="at least two tools"):
        Target(target_id="lonely", tools=("toolA0",)).validate()


# ---------------------------------------------------------------------------
# Portfolios
# ---------------------------------------------------------------------------


def test_assemble_portfolio_merges_over_the_incumbent():
    portfolio = assemble_portfolio(
        {"toolZ": "an earlier round's override"},
        {"pair-a": candidate(TARGET_A, 1), "pair-b": candidate(TARGET_B, 1)},
    )
    assert portfolio.round == 1
    assert portfolio.k == 1
    assert set(portfolio.overrides) == {"toolZ", "toolA0", "toolA1", "toolB0", "toolB1"}
    assert portfolio.overrides["toolZ"] == "an earlier round's override"
    assert set(portfolio.candidate_ids) == {"pair-a", "pair-b"}
    assert len(portfolio.portfolio_sha256) == 64
    assert json.dumps(portfolio.as_json())


def test_assemble_portfolio_is_content_addressed():
    first = assemble_portfolio({}, {"pair-a": candidate(TARGET_A, 1)})
    same = assemble_portfolio({}, {"pair-a": candidate(TARGET_A, 1)})
    other = assemble_portfolio({}, {"pair-a": candidate(TARGET_A, 2)})
    assert first.portfolio_sha256 == same.portfolio_sha256
    assert first.portfolio_sha256 != other.portfolio_sha256


def test_assemble_portfolio_marks_a_mixed_slot_assembly_with_k_none():
    portfolio = assemble_portfolio(
        {}, {"pair-a": candidate(TARGET_A, 1), "pair-b": candidate(TARGET_B, 3)}
    )
    assert portfolio.k is None
    assert portfolio.round == 1


def test_assemble_portfolio_refuses_mixed_rounds_and_overlapping_tools():
    with pytest.raises(EvolutionError, match="span rounds"):
        assemble_portfolio(
            {},
            {
                "pair-a": candidate(TARGET_A, 1, round=1),
                "pair-b": candidate(TARGET_B, 1, round=2),
            },
        )
    shared = Target(target_id="pair-c", tools=("toolA1", "toolC0"))
    with pytest.raises(EvolutionError, match="must be disjoint"):
        assemble_portfolio(
            {}, {"pair-a": candidate(TARGET_A, 1), "pair-c": candidate(shared, 1)}
        )


def test_assemble_portfolio_refuses_a_mislabelled_candidate():
    with pytest.raises(EvolutionError, match="carries target_id"):
        assemble_portfolio({}, {"pair-b": candidate(TARGET_A, 1)})


# ---------------------------------------------------------------------------
# Fragment writer
# ---------------------------------------------------------------------------


BASE_FRAGMENT = {
    "arm": "bare-core",
    "policy": "fixed",
    "evidence_source": "none",
    "scorers": [SCORER],
    "task_instruction_template": "probes/r1_audio2tool_official.txt",
    "task_instruction_template_active": True,
}


def test_write_candidate_fragments_emits_the_artifact_and_the_two_keys(tmp_path):
    portfolios = [
        assemble_portfolio({}, {"pair-a": candidate(TARGET_A, k)}) for k in (0, 1)
    ]
    written = write_candidate_fragments(
        portfolios,
        base_fragment=BASE_FRAGMENT,
        out_dir=tmp_path / "configs",
        artifact_dir=tmp_path / "artifacts",
    )
    assert [path.name for path in written] == [
        f"evolved-artifact-{portfolio.portfolio_sha256[:16]}.json"
        for portfolio in portfolios
    ]
    fragment = json.loads(written[0].read_text(encoding="utf-8"))
    # The base fragment survives untouched beside the two keys this writer owns.
    for key, value in BASE_FRAGMENT.items():
        assert fragment[key] == value
    assert fragment["task_instruction_fill"] == "evolved-artifact-v1"
    params = fragment["task_instruction_fill_params"]
    assert params["artifact_relpath"] == (
        f"evolved-registry-{portfolios[0].portfolio_sha256[:16]}.json"
    )
    assert params["portfolio_sha256"] == portfolios[0].portfolio_sha256
    assert params["round"] == 1 and params["k"] == 0

    artifact = tmp_path / "artifacts" / params["artifact_relpath"]
    assert json.loads(artifact.read_text(encoding="utf-8")) == dict(
        portfolios[0].overrides
    )
    assert (
        hashlib.sha256(artifact.read_bytes()).hexdigest() == params["artifact_sha256"]
    )


def test_write_candidate_fragments_is_deterministic_and_relpath_bases(tmp_path):
    portfolio = assemble_portfolio({}, {"pair-a": candidate(TARGET_A, 0)})
    first = write_candidate_fragments(
        [portfolio],
        base_fragment=BASE_FRAGMENT,
        out_dir=tmp_path / "configs",
        artifact_dir=tmp_path / "root" / "artifacts",
        artifact_relpath_base=tmp_path / "root",
    )
    before = first[0].read_bytes()
    second = write_candidate_fragments(
        [portfolio],
        base_fragment=BASE_FRAGMENT,
        out_dir=tmp_path / "configs",
        artifact_dir=tmp_path / "root" / "artifacts",
        artifact_relpath_base=tmp_path / "root",
    )
    assert second == first
    assert second[0].read_bytes() == before
    params = json.loads(before)["task_instruction_fill_params"]
    assert params["artifact_relpath"].startswith("artifacts/")


def test_write_candidate_fragments_refuses_a_base_that_already_sets_the_fill(tmp_path):
    with pytest.raises(EvolutionError, match="owns that key"):
        write_candidate_fragments(
            [assemble_portfolio({}, {"pair-a": candidate(TARGET_A, 0)})],
            base_fragment={**BASE_FRAGMENT, "task_instruction_fill": "something-else"},
            out_dir=tmp_path / "configs",
            artifact_dir=tmp_path / "artifacts",
        )


# ---------------------------------------------------------------------------
# Stage one
# ---------------------------------------------------------------------------

ROWS_A = rows("tier1_direct", 20)
ROWS_B = rows("tier2_slot", 20)
ALL_ROWS = ROWS_A + ROWS_B
ROWS_OF_TARGET = {"pair-a": ROWS_A, "pair-b": ROWS_B}


def arm_from_flips(*, saves: int, harms: int, target_rows, incumbent_values):
    """An arm that flips exactly ``saves`` zeros up and ``harms`` ones down."""

    values = dict(zip(target_rows, incumbent_values))
    zeros = [sid for sid in target_rows if values[sid] == 0.0]
    ones = [sid for sid in target_rows if values[sid] == 1.0]
    assert saves <= len(zeros) and harms <= len(ones)
    out = dict(values)
    for sid in zeros[:saves]:
        out[sid] = 1.0
    for sid in ones[:harms]:
        out[sid] = 0.0
    return out


# 10 zeros then 10 ones on each target's own rows.
INCUMBENT_PATTERN = [0.0] * 10 + [1.0] * 10
INCUMBENT_SCORES = {
    **scores(ROWS_A, INCUMBENT_PATTERN),
    **scores(ROWS_B, INCUMBENT_PATTERN),
}


def arm(pair_a: tuple[int, int], pair_b: tuple[int, int]):
    table = {}
    for target_rows_, counts in ((ROWS_A, pair_a), (ROWS_B, pair_b)):
        flipped = arm_from_flips(
            saves=counts[0],
            harms=counts[1],
            target_rows=target_rows_,
            incumbent_values=INCUMBENT_PATTERN,
        )
        table.update({sid: {METRIC: value} for sid, value in flipped.items()})
    return table


def test_select_per_target_admits_only_what_clears_all_three_gates():
    portfolio_scores = {
        0: arm((5, 1), (3, 0)),  # a: saves 5 harms 1 net 4 -> admitted
        1: arm((4, 2), (0, 0)),  # a: harms 2 -> refused on harms
        2: arm((3, 0), (0, 0)),  # a: saves 3 -> refused on saves
    }
    decisions = select_per_target(
        INCUMBENT_SCORES,
        portfolio_scores,
        targets=[TARGET_A, TARGET_B],
        rows_of_target=ROWS_OF_TARGET,
        metric=METRIC,
    )
    outcomes = {o.k: o for o in decisions["pair-a"].outcomes}
    assert (outcomes[0].saves, outcomes[0].harms, outcomes[0].net) == (5, 1, 4)
    assert [o.admitted for o in decisions["pair-a"].outcomes] == [True, False, False]
    assert decisions["pair-a"].winner_k == 0
    assert decisions["pair-a"].n_rows == 20
    # pair-b: no arm reaches saves >= 4, so the incumbent is kept there.
    assert [o.admitted for o in decisions["pair-b"].outcomes] == [False, False, False]
    assert decisions["pair-b"].winner_k is None


def test_select_per_target_breaks_a_net_tie_on_harms_then_bytes_then_k():
    # Every arm nets 4 on pair-a; k=0 harms twice, k=1 and k=2 harm once.
    portfolio_scores = {0: arm((6, 2), (0, 0)), 1: arm((5, 1), (0, 0)), 2: arm((5, 1), (0, 0))}
    long_text = "a considerably longer replacement description"
    candidates = {
        "pair-a": {
            0: candidate(TARGET_A, 0),
            1: candidate(TARGET_A, 1, text=long_text),
            2: candidate(TARGET_A, 2),
        }
    }
    decisions = select_per_target(
        INCUMBENT_SCORES,
        portfolio_scores,
        targets=[TARGET_A],
        rows_of_target=ROWS_OF_TARGET,
        metric=METRIC,
        candidates=candidates,
    )
    outcomes = {o.k: o for o in decisions["pair-a"].outcomes}
    assert outcomes[0].net == outcomes[1].net == outcomes[2].net == 4
    assert (outcomes[0].harms, outcomes[1].harms, outcomes[2].harms) == (2, 1, 1)
    assert outcomes[1].bytes > outcomes[2].bytes
    # Harms eliminates k=0; bytes -- not the lower k -- then picks k=2.
    assert decisions["pair-a"].winner_k == 2
    assert decisions["pair-a"].winner is candidates["pair-a"][2]
    assert decisions["pair-a"].winner_candidate_id == candidates["pair-a"][2].candidate_id


def test_select_per_target_falls_back_to_the_lowest_k_when_bytes_tie():
    portfolio_scores = {1: arm((5, 1), (0, 0)), 2: arm((5, 1), (0, 0))}
    candidates = {"pair-a": {1: candidate(TARGET_A, 1), 2: candidate(TARGET_A, 2)}}
    decisions = select_per_target(
        INCUMBENT_SCORES,
        portfolio_scores,
        targets=[TARGET_A],
        rows_of_target=ROWS_OF_TARGET,
        metric=METRIC,
        candidates=candidates,
    )
    outcomes = {o.k: o for o in decisions["pair-a"].outcomes}
    assert outcomes[1].bytes == outcomes[2].bytes
    assert decisions["pair-a"].winner_k == 1


def test_select_per_target_reads_only_the_targets_own_rows():
    # pair-b's rows are wrecked; pair-a's decision must be unaffected.
    wrecked = arm((5, 1), (0, 10))
    decisions = select_per_target(
        INCUMBENT_SCORES,
        {0: wrecked},
        targets=[TARGET_A, TARGET_B],
        rows_of_target=ROWS_OF_TARGET,
        metric=METRIC,
    )
    assert decisions["pair-a"].winner_k == 0
    assert decisions["pair-b"].outcomes[0].harms == 10
    assert decisions["pair-b"].winner_k is None


def test_select_per_target_accepts_a_callable_row_lookup():
    decisions = select_per_target(
        INCUMBENT_SCORES,
        {0: arm((5, 1), (0, 0))},
        targets=[TARGET_A],
        rows_of_target=lambda target_id: ROWS_OF_TARGET[target_id],
        metric=METRIC,
    )
    assert decisions["pair-a"].winner_k == 0


def test_admission_gates_are_the_preregistered_constants():
    gates = AdmissionGates()
    assert (gates.saves, gates.harms, gates.net) == (4, 1, 3)
    assert gates.admits(saves=4, harms=1) is True
    assert gates.admits(saves=4, harms=2) is False
    assert gates.admits(saves=3, harms=0) is False


# ---------------------------------------------------------------------------
# Stage two
# ---------------------------------------------------------------------------

FOLD_B_TARGETED = rows("foldb_target", 120)
FOLD_B_BACKGROUND = rows("foldb_bg", 120)


def test_confirm_assembly_accepts_a_clean_targeted_gain():
    incumbent = {
        **scores(FOLD_B_TARGETED, [0.0] * 120),
        **scores(FOLD_B_BACKGROUND, [1.0] * 120),
    }
    assembly = {
        **scores(FOLD_B_TARGETED, [1.0] * 40 + [0.0] * 80),
        **scores(FOLD_B_BACKGROUND, [1.0] * 120),
    }
    decision = confirm_assembly(
        incumbent,
        assembly,
        targeted_rows=FOLD_B_TARGETED,
        background_rows=FOLD_B_BACKGROUND,
        metric=METRIC,
        seed=20260903,
        n_replicates=200,
    )
    assert decision.accepted is True
    assert decision.targeted.bootstrap.ci_low > 0.0
    assert decision.background_gain_pp == 0.0
    assert "background lower bound" in decision.reason
    assert json.dumps(decision.as_json())


def test_confirm_assembly_rejects_background_harm_even_with_a_targeted_gain():
    incumbent = {
        **scores(FOLD_B_TARGETED, [0.0] * 120),
        **scores(FOLD_B_BACKGROUND, [1.0] * 120),
    }
    # 40 targeted saves, but 12 of 120 background rows broken: -10.0 pp, far
    # past the -1.0 pp tolerance.
    assembly = {
        **scores(FOLD_B_TARGETED, [1.0] * 40 + [0.0] * 80),
        **scores(FOLD_B_BACKGROUND, [0.0] * 12 + [1.0] * 108),
    }
    decision = confirm_assembly(
        incumbent,
        assembly,
        targeted_rows=FOLD_B_TARGETED,
        background_rows=FOLD_B_BACKGROUND,
        metric=METRIC,
        seed=20260903,
        n_replicates=200,
    )
    assert decision.accepted is False
    assert decision.targeted.bootstrap.ci_low > 0.0
    assert decision.background_gain_pp == pytest.approx(-10.0)
    assert "below the -1.000 pp tolerance" in decision.reason
    assert decision.background_tolerance_pp == BACKGROUND_TOLERANCE_PP


def test_confirm_assembly_rejects_a_targeted_bound_that_includes_zero():
    incumbent = {
        **scores(FOLD_B_TARGETED, [0.0] * 60 + [1.0] * 60),
        **scores(FOLD_B_BACKGROUND, [1.0] * 120),
    }
    # One save and one harm: a delta of zero, so the bound cannot clear 0.
    assembly = {
        **scores(FOLD_B_TARGETED, [1.0] + [0.0] * 59 + [0.0] + [1.0] * 59),
        **scores(FOLD_B_BACKGROUND, [1.0] * 120),
    }
    decision = confirm_assembly(
        incumbent,
        assembly,
        targeted_rows=FOLD_B_TARGETED,
        background_rows=FOLD_B_BACKGROUND,
        metric=METRIC,
        seed=20260903,
        n_replicates=200,
    )
    assert decision.accepted is False
    assert "not above 0" in decision.reason


def test_confirm_assembly_refuses_overlapping_populations():
    incumbent = scores(FOLD_B_TARGETED, [0.0] * 120)
    with pytest.raises(EvolutionError, match="both the targeted and the background"):
        confirm_assembly(
            incumbent,
            incumbent,
            targeted_rows=FOLD_B_TARGETED,
            background_rows=FOLD_B_TARGETED[:10],
            metric=METRIC,
            n_replicates=10,
        )


def test_confirm_assembly_tolerance_is_percentage_points_not_a_fraction():
    """A -1.0 pp tolerance must reject a 2 pp background loss.

    If the tolerance were compared against the raw fractional delta, -1.0
    would be below every possible bound and the background gate would be
    silently inert -- which is the whole failure this parameter's unit
    handling exists to prevent.
    """

    incumbent = {
        **scores(FOLD_B_TARGETED, [0.0] * 120),
        **scores(FOLD_B_BACKGROUND, [1.0] * 120),
    }
    assembly = {
        **scores(FOLD_B_TARGETED, [1.0] * 40 + [0.0] * 80),
        **scores(FOLD_B_BACKGROUND, [0.0] * 3 + [1.0] * 117),
    }
    decision = confirm_assembly(
        incumbent,
        assembly,
        targeted_rows=FOLD_B_TARGETED,
        background_rows=FOLD_B_BACKGROUND,
        metric=METRIC,
        seed=20260903,
        n_replicates=200,
    )
    assert decision.background_gain_pp == pytest.approx(-2.5)
    # The targeted half is fine; only the background bound refuses it.
    assert decision.targeted.bootstrap.ci_low > 0.0
    assert decision.background.bootstrap.ci_low < BACKGROUND_TOLERANCE_PP / 100.0
    assert decision.accepted is False
    assert "below the -1.000 pp tolerance" in decision.reason


# ---------------------------------------------------------------------------
# State and stopping
# ---------------------------------------------------------------------------


def outcome(round_: int, accepted: bool, gain_pp: float) -> RoundOutcome:
    return RoundOutcome(
        round=round_, accepted=accepted, gain_pp=gain_pp, reason="test"
    )


def test_should_stop_on_two_consecutive_rejects():
    stop, reason = should_stop([outcome(1, False, 0.0), outcome(2, False, -0.2)])
    assert stop is True
    assert "two consecutive rejects" in reason


def test_should_stop_on_an_accepted_gain_below_the_minimum():
    stop, reason = should_stop([outcome(1, True, 0.4)])
    assert stop is True
    assert "below the 0.500 pp minimum" in reason
    assert should_stop([outcome(1, True, 0.6)]) == (False, "continue")


def test_should_stop_on_the_round_cap():
    history = [outcome(index, True, 2.0) for index in range(1, MAX_ROUNDS + 1)]
    stop, reason = should_stop(history)
    assert stop is True
    assert "round cap" in reason
    assert should_stop(history[:-1])[0] is False


def test_should_stop_says_nothing_has_happened_on_an_empty_history():
    assert should_stop([]) == (False, "no round has completed yet")


def test_state_keeps_the_incumbent_on_a_rejected_round():
    state = EvolutionState(round=0, incumbent_overrides={}).validate()
    accepted = state.with_outcome(outcome(1, True, 2.0), overrides={"toolA0": "new"})
    assert accepted.incumbent_overrides == {"toolA0": "new"}
    rejected = accepted.with_outcome(outcome(2, False, -0.5))
    assert rejected.incumbent_overrides == {"toolA0": "new"}
    assert [entry.round for entry in rejected.history] == [1, 2]
    assert rejected.state_sha256() != accepted.state_sha256()
    assert json.dumps(rejected.as_json())


def test_state_refuses_a_history_that_goes_backwards():
    with pytest.raises(EvolutionError, match="strictly increasing"):
        EvolutionState(
            round=2,
            incumbent_overrides={},
            history=(outcome(2, True, 1.0), outcome(1, True, 1.0)),
        ).validate()


def test_evolution_state_defines_no_controller_shape():
    # The engineering-base rule reserves `initial_contact` + `advance` to the
    # one controller; this state object must not half-grow into a second one.
    assert not hasattr(EvolutionState, "advance")
    assert not hasattr(EvolutionState, "initial_contact")
    assert hasattr(EvolutionState, "with_outcome")


# ---------------------------------------------------------------------------
# Receipt and replay
# ---------------------------------------------------------------------------


def write_score_file(path, table):
    document = {
        "manifest": str(path.with_suffix(".manifest.json")),
        "verified": True,
        "scores": {
            SCORER: {
                "aggregate": {
                    "samples": len(table),
                    "tool_accuracy": sum(row[METRIC] for row in table.values())
                    / len(table),
                },
                "per_sample": [
                    {"sample_id": sid, METRIC: bool(row[METRIC])}
                    for sid, row in sorted(table.items())
                ],
            }
        },
    }
    path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    return path


def landed_round(tmp_path):
    portfolio_scores = {0: arm((5, 1), (3, 0)), 1: arm((4, 2), (6, 0))}
    decisions = select_per_target(
        INCUMBENT_SCORES,
        portfolio_scores,
        targets=[TARGET_A, TARGET_B],
        rows_of_target=ROWS_OF_TARGET,
        metric=METRIC,
    )
    record = selection_record(
        decisions,
        metric=METRIC,
        scorer_id=SCORER,
        gates=AdmissionGates(),
        rows_of_target=ROWS_OF_TARGET,
        targets=[TARGET_A, TARGET_B],
    )
    state = EvolutionState(round=0, incumbent_overrides={}).with_outcome(
        outcome(1, True, 1.5)
    )
    receipt_path, digest = write_round_receipt(
        state, out_dir=tmp_path / "receipt", extra={"selection": record}
    )
    files = {
        INCUMBENT_KEY: write_score_file(
            tmp_path / "incumbent.score.json", INCUMBENT_SCORES
        )
    }
    for slot, table in portfolio_scores.items():
        files[str(slot)] = write_score_file(tmp_path / f"k{slot}.score.json", table)
    return receipt_path, digest, files, decisions


def test_round_receipt_digest_is_over_the_written_bytes(tmp_path):
    receipt_path, digest, _files, _decisions = landed_round(tmp_path)
    assert receipt_path.name == "evolution-round-01.json"
    assert hashlib.sha256(receipt_path.read_bytes()).hexdigest() == digest
    document = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert document["schema"] == "saea-evolution-round-receipt-v1"
    assert document["extra"]["selection"]["schema"] == "saea-evolution-selection-v1"


def test_replay_recomputes_every_decision_from_the_score_files(tmp_path):
    receipt_path, _digest, files, decisions = landed_round(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    result = replay_selection(receipt, files)
    assert result.matches is True
    assert result.mismatches == ()
    assert {t: d.winner_k for t, d in result.recomputed.items()} == {
        t: d.winner_k for t, d in decisions.items()
    }
    assert json.dumps(result.as_json())


def test_replay_reports_a_receipt_that_disagrees_with_the_scores(tmp_path):
    receipt_path, _digest, files, _decisions = landed_round(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    tampered = receipt["extra"]["selection"]["decisions"]["pair-a"]
    tampered["outcomes"][0]["saves"] += 3
    tampered["winner_k"] = 1
    result = replay_selection(receipt, files)
    assert result.matches is False
    assert any("pair-a.k0.saves" in item for item in result.mismatches)
    assert any("pair-a.winner_k" in item for item in result.mismatches)


def test_replay_accepts_the_selection_record_on_its_own(tmp_path):
    receipt_path, _digest, files, _decisions = landed_round(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert replay_selection(receipt["extra"]["selection"], files).matches is True


def test_replay_refuses_a_document_with_no_selection_record(tmp_path):
    _receipt_path, _digest, files, _decisions = landed_round(tmp_path)
    with pytest.raises(EvolutionError, match="no selection record"):
        replay_selection({"schema": "something-else"}, files)


def test_replay_refuses_missing_score_files(tmp_path):
    receipt_path, _digest, files, _decisions = landed_round(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    del files["1"]
    with pytest.raises(EvolutionError, match="no entry for portfolio k=1"):
        replay_selection(receipt, files)


# ---------------------------------------------------------------------------
# Budget
# ---------------------------------------------------------------------------


def test_ledger_budget_follows_the_documented_formula():
    budget = ledger_budget(
        4,
        roster_rows=600,
        k=4,
        proposer_calls_per_round=36,
        speech_seconds_per_pass=18_000.0,
        seconds_per_call=0.75,
    )
    # R * (K + 1) * rows = 4 * 5 * 600 = 12,000; plus R * proposer = 144.
    assert budget["calls"] == 12_144.0
    assert budget["speech_seconds"] == 4 * 5 * 18_000.0
    assert budget["gpu_hours"] == pytest.approx(12_144 * 0.75 / 3600.0)


def test_ledger_budget_charges_the_proposer_no_audio():
    with_proposer = ledger_budget(
        1,
        roster_rows=10,
        k=1,
        proposer_calls_per_round=100,
        speech_seconds_per_pass=60.0,
        seconds_per_call=1.0,
    )
    without = ledger_budget(
        1,
        roster_rows=10,
        k=1,
        proposer_calls_per_round=0,
        speech_seconds_per_pass=60.0,
        seconds_per_call=1.0,
    )
    assert with_proposer["calls"] - without["calls"] == 100
    assert with_proposer["speech_seconds"] == without["speech_seconds"] == 120.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"roster_rows": 0},
        {"k": 0},
        {"proposer_calls_per_round": -1},
        {"speech_seconds_per_pass": -1.0},
        {"seconds_per_call": -1.0},
    ],
)
def test_ledger_budget_refuses_impossible_inputs(kwargs):
    arguments = {
        "roster_rows": 10,
        "k": 1,
        "proposer_calls_per_round": 1,
        "speech_seconds_per_pass": 1.0,
        "seconds_per_call": 1.0,
    }
    arguments.update(kwargs)
    with pytest.raises(EvolutionError):
        ledger_budget(1, **arguments)


# ---------------------------------------------------------------------------
# Cross-module guard
# ---------------------------------------------------------------------------


def test_a_portfolio_refuses_an_invalid_candidate():
    good = candidate(TARGET_A, 0)
    broken = type(good)(
        candidate_id="0" * 64,
        family=good.family,
        target_id=good.target_id,
        round=good.round,
        k=good.k,
        descriptions=good.descriptions,
        cue=good.cue,
        proposer_prompt_sha256=good.proposer_prompt_sha256,
        exemplar_ids=good.exemplar_ids,
    )
    with pytest.raises(ProposerError):
        broken.validate()
    with pytest.raises(EvolutionError, match="not a valid candidate"):
        assemble_portfolio({}, {"pair-a": broken})


def test_portfolio_is_a_plain_frozen_record():
    portfolio = assemble_portfolio({}, {"pair-a": candidate(TARGET_A, 0)})
    assert isinstance(portfolio, Portfolio)
    with pytest.raises(Exception):
        portfolio.round = 9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# The sentinel-harms line (owner decision, 2026-09-06)
# ---------------------------------------------------------------------------

SENTINEL_ROWS = {"pair-a": {"thin": ["s:000000", "s:000001", "s:000002"]}}


def test_sentinel_harms_names_every_harmed_row_and_its_tool():
    incumbent = scores(SENTINEL_ROWS["pair-a"]["thin"], [1.0, 1.0, 0.0])
    arm_scores = {1: scores(SENTINEL_ROWS["pair-a"]["thin"], [0.0, 1.0, 1.0])}
    line = sentinel_harms(
        incumbent, arm_scores, sentinel_rows=SENTINEL_ROWS, metric=METRIC
    )
    block = line["by_target"]["pair-a"]["by_k"]["1"]
    assert (block["n"], block["saves"], block["harms"], block["ties"], block["net"]) == (
        3,
        1,
        1,
        1,
        0,
    )
    assert block["harmed"] == [{"sample_id": "s:000000", "tool": "thin"}]
    assert block["saved"] == [{"sample_id": "s:000002", "tool": "thin"}]
    assert line["by_target"]["pair-a"]["tools"] == ["thin"]
    assert line["schema"] == SENTINEL_SCHEMA


def test_sentinel_harms_refuses_an_arm_that_never_scored_a_sentinel_row():
    incumbent = scores(SENTINEL_ROWS["pair-a"]["thin"], [1.0, 1.0, 1.0])
    partial = {1: scores(SENTINEL_ROWS["pair-a"]["thin"][:2], [1.0, 1.0])}
    with pytest.raises(EvolutionError, match="no 'tool_correct' score for sentinel row"):
        sentinel_harms(incumbent, partial, sentinel_rows=SENTINEL_ROWS, metric=METRIC)


def loop_document(**overrides):
    document = {
        "schema": "saea-evolution-loop-config-v1",
        "carrier_lock_key": "audio2tool",
        "targets": {"lighting": ["setLighting", "setAmbientLighting"]},
        "sentinel_tools": {"lighting": ["setAmbientLighting"]},
        "proposer_run_id": "P",
        "fold_a_run_id": "A",
        "fold_b_run_id": "B",
        "base_fragment": "base",
        "model_fragment": "model",
        "fold_a_dataset_fragment": "fold-a",
        "fold_b_dataset_fragment": "fold-b",
        "metric": METRIC,
        "scorer_id": "a2t-toolcall-official",
    }
    document.update(overrides)
    return document


def test_loop_config_reads_sentinels_and_derives_the_reward_tools():
    config = LoopConfig.from_json(loop_document())
    assert config.sentinel_tools == {"lighting": ("setAmbientLighting",)}
    assert config.reward_tools("lighting") == ("setLighting",)
    assert config.fold_a_roster_relpath.endswith("a2t-evo-fold-a-v2.json")


def test_loop_config_refuses_a_sentinel_that_is_not_in_its_own_target():
    with pytest.raises(EvolutionError, match="does not.*carry"):
        LoopConfig.from_json(
            loop_document(sentinel_tools={"lighting": ["setColorTemperature"]})
        )


def test_loop_config_refuses_a_target_that_is_all_sentinels():
    with pytest.raises(EvolutionError, match="all sentinels"):
        LoopConfig.from_json(
            loop_document(
                sentinel_tools={"lighting": ["setLighting", "setAmbientLighting"]}
            )
        )


def test_loop_config_refuses_sentinels_for_an_unknown_target():
    with pytest.raises(EvolutionError, match="not a target"):
        LoopConfig.from_json(loop_document(sentinel_tools={"nope": ["setLighting"]}))


# ---------------------------------------------------------------------------
# The question digest the noise floor is computed on (track E3e, 2026-09-07)
# ---------------------------------------------------------------------------


def _payload(**overrides) -> dict:
    payload = {
        "sample_id": "slurp:train:000006:audio-1",
        "history": [{"content": "Extract the entities of this command."}],
        "task_instruction": "You are given spoken audio.",
        "speech_packet_sha256": "b" * 64,
        "decoding_params": {"id_slot": 0, "max_tokens": 64, "temperature": 0},
        "request_id": "cell-0001",
    }
    payload.update(overrides)
    return payload


def test_a_question_digest_ignores_the_transport_envelope():
    """``request_id`` is an ordinal and ``id_slot`` is which server slot the
    scheduler happened to hand the request. Counting either as part of the
    question is what makes an instrument useless: on EVO-S1 round 1, 820 of
    1,080 rows differ in ``id_slot`` alone and 62 in ``request_id``, against 61
    that differ in the rendered prompt."""

    asked = _payload()
    same_question_other_envelope = _payload(
        request_id="cell-0997",
        decoding_params={"id_slot": 3, "max_tokens": 64, "temperature": 0},
    )
    assert question_sha256(asked) == question_sha256(same_question_other_envelope)


def test_a_question_digest_moves_on_anything_it_does_not_know_to_be_transport():
    """A denylist, on purpose: a payload field this module has never heard of
    is CONTENT until someone proves it is scheduling."""

    asked = _payload()
    assert question_sha256(asked) != question_sha256(
        _payload(history=[{"content": "Extract the entities of this other command."}])
    )
    assert question_sha256(asked) != question_sha256(
        _payload(decoding_params={"id_slot": 0, "max_tokens": 96, "temperature": 0})
    )
    assert question_sha256(asked) != question_sha256(_payload(some_new_field=["x"]))
    with pytest.raises(EvolutionError, match="mapping"):
        question_sha256("not a payload")


def test_the_noise_floor_counts_split_moves_by_the_question_test():
    """Four rows: one asked differently and saved, one asked identically and
    saved, one asked identically and harmed, one asked identically, answered
    differently and moved nothing. Recountable by eye."""

    incumbent_digests = {row: ("q-same", f"a-{row}") for row in ("r1", "r2", "r3", "r4")}
    arm_digests = {
        "r1": ("q-changed", "a-r1-new"),
        "r2": ("q-same", "a-r2-new"),
        "r3": ("q-same", "a-r3-new"),
        "r4": ("q-same", "a-r4-new"),
    }
    incumbent_scores = {row: {METRIC: 0.0} for row in ("r1", "r2", "r4")}
    incumbent_scores["r3"] = {METRIC: 1.0}
    arm_scores = {row: {METRIC: 1.0} for row in ("r1", "r2")}
    arm_scores["r3"] = {METRIC: 0.0}
    arm_scores["r4"] = {METRIC: 0.0}

    report = prompt_noise_floor(
        incumbent_digests,
        arm_digests,
        incumbent_scores,
        arm_scores,
        metric=METRIC,
        rows=("r1", "r2", "r3", "r4"),
        rows_of_target={"only": ("r2", "r3")},
    )
    assert report["rows"] == 4
    assert report["changed_prompt_rows"] == 1
    assert report["unchanged_prompt_rows"] == 3
    assert report["unchanged_prompt_flips"] == 3
    assert report["changed_prompt"] == {"saves": 1, "harms": 0}
    assert report["unchanged_prompt"] == {"saves": 1, "harms": 1}
    assert report["by_target"]["only"]["unchanged_prompt"] == {"saves": 1, "harms": 1}
    assert report["by_target"]["only"]["rows"] == 2
    # A row missing from one side is not counted rather than guessed at.
    assert (
        prompt_noise_floor(
            incumbent_digests,
            arm_digests,
            incumbent_scores,
            arm_scores,
            metric=METRIC,
            rows=("r1", "absent"),
        )["rows"]
        == 1
    )
