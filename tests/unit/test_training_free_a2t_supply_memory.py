from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_supply_memory as smem,
)


def _registry() -> tuple[dict[str, str], ...]:
    return (
        {
            "tool_name": "weather",
            "signature": "weather(city: str, units: str = 'metric')",
        },
        {"tool_name": "ping", "signature": "ping()"},
        {"tool_name": "lookup", "signature": "lookup(term: str)"},
    )


def _state(response: str) -> smem.RuntimeState:
    return smem.extract_runtime_state(response, _registry())


def _outcome(
    sample_id: str,
    *,
    group_id: str | None = None,
    state: smem.RuntimeState | None = None,
    stop: int = 0,
    supply: int = 0,
) -> smem.SignedSupplyOutcome:
    return smem.SignedSupplyOutcome(
        sample_id=sample_id,
        group_id=sample_id if group_id is None else group_id,
        state=_state('[{"name":"weather","arguments":{"city":"x"}}]')
        if state is None
        else state,
        stop_exact=stop,
        supply_exact=supply,
        stop_tool_accuracy=float(stop),
        supply_tool_accuracy=float(supply),
        stop_slot_f1=float(stop),
        supply_slot_f1=float(supply),
    )


@pytest.mark.parametrize(
    ("signature", "expected"),
    [
        ("weather(city: str, units: str = 'metric')", ("city", "units")),
        ("ping()", ()),
        ("lookup(term, /, *, limit: int = 1)", ("term", "limit")),
        ("not a function signature", None),
        ("broken(x:)", None),
    ],
)
def test_signature_parameter_parser_is_deterministic_and_fail_closed(
    signature: str, expected: tuple[str, ...] | None
) -> None:
    assert smem.parse_signature_parameters(signature) == expected


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (
            "not-json",
            ("invalid", "no-call", "no-call", "unresolved", "zero"),
        ),
        ("[]", ("empty", "no-call", "no-call", "unresolved", "zero")),
        (
            '[{"name":"weather","arguments":{"city":"x","units":"metric"}}]',
            ("single", "all-known", "exact", "two", "two"),
        ),
        (
            '[{"name":"weather","arguments":{"city":"x"}}]',
            ("single", "all-known", "subset", "two", "one"),
        ),
        (
            '[{"name":"weather","arguments":{"city":"x","extra":1}}]',
            ("single", "all-known", "mixed", "two", "two"),
        ),
        (
            '[{"name":"unknown","arguments":{}}]',
            ("single", "all-unknown", "unresolved", "unresolved", "zero"),
        ),
        (
            '[{"name":"ping","arguments":{}},{"name":"unknown","arguments":{}}]',
            ("multiple", "some-unknown", "mixed", "zero", "zero"),
        ),
    ],
)
def test_runtime_state_uses_only_direct_call_structure(
    response: str, expected: tuple[str, str, str, str, str]
) -> None:
    state = _state(response)
    assert (
        state.parse_class,
        state.registry_resolution,
        state.declared_key_relation,
        state.schema_arity_bucket,
        state.provided_key_bucket,
    ) == expected


def test_state_omits_tool_identity_and_is_invariant_to_reward_mutation() -> None:
    registry = (
        {"tool_name": "alpha", "signature": "alpha(value: str)"},
        {"tool_name": "beta", "signature": "beta(value: str)"},
    )
    alpha = smem.extract_runtime_state(
        '[{"name":"alpha","arguments":{"value":"x"}}]', registry
    )
    beta = smem.extract_runtime_state(
        '[{"name":"beta","arguments":{"value":"x"}}]', registry
    )
    assert alpha == beta

    original = _outcome("s", state=alpha, stop=0, supply=1)
    reward_mutated = _outcome("s", state=alpha, stop=1, supply=0)
    assert original.state == reward_mutated.state
    assert original.delta == 1
    assert reward_mutated.delta == -1


def test_candidate_keys_are_frozen_coarse_and_detailed_views() -> None:
    state = _state('[{"name":"weather","arguments":{"city":"x"}}]')
    assert state.key("coarse-v1") == ("single", "all-known", "subset")
    assert state.key("detailed-v1") == (
        "single",
        "all-known",
        "subset",
        "two",
        "one",
    )
    with pytest.raises(smem.SupplyMemoryError, match="unknown candidate"):
        state.key("invented")


def test_memory_supplies_only_with_minimum_support_saves_and_zero_harm() -> None:
    state = _state('[{"name":"weather","arguments":{"city":"x"}}]')
    safe_memory = tuple(
        _outcome(f"s{i}", state=state, supply=1 if i < 2 else 0)
        for i in range(5)
    )
    decision = smem.decide(state, safe_memory, candidate_id="coarse-v1")
    assert decision.action == "SUPPLY_STRIPPED_REGISTRY"
    assert (decision.support, decision.saves, decision.harms) == (5, 2, 0)

    too_few_saves = tuple(
        _outcome(f"f{i}", state=state, supply=1 if i == 0 else 0)
        for i in range(5)
    )
    assert smem.decide(state, too_few_saves, candidate_id="coarse-v1").action == "STOP_DIRECT"

    harmed = safe_memory[:-1] + (_outcome("harm", state=state, stop=1, supply=0),)
    assert smem.decide(state, harmed, candidate_id="coarse-v1").action == "STOP_DIRECT"

    sparse = safe_memory[:4]
    assert smem.decide(state, sparse, candidate_id="coarse-v1").action == "STOP_DIRECT"


def test_fold_assignment_is_order_invariant_balanced_and_group_isolated() -> None:
    outcomes = tuple(
        _outcome(f"s{i:02d}", group_id=f"q{i // 2:02d}") for i in range(30)
    )
    first = smem.assign_folds(outcomes, seed=11, n_folds=5)
    second = smem.assign_folds(tuple(reversed(outcomes)), seed=11, n_folds=5)
    assert first == second
    assert max(map(len, first)) - min(map(len, first)) <= 2
    for group in {item.group_id for item in outcomes}:
        assert sum(any(item.group_id == group for item in fold) for fold in first) == 1


def test_crossfit_screen_selects_live_zero_harm_reward_memory() -> None:
    benefit_state = _state('[{"name":"weather","arguments":{"city":"x"}}]')
    danger_state = _state('[{"name":"ping","arguments":{}}]')
    outcomes = tuple(
        [_outcome(f"b{i:02d}", state=benefit_state, supply=1) for i in range(50)]
        + [_outcome(f"d{i:02d}", state=danger_state, stop=1, supply=0) for i in range(50)]
    )

    first = smem.screen_candidates(outcomes, seed=19, n_replicates=1000)
    second = smem.screen_candidates(tuple(reversed(outcomes)), seed=19, n_replicates=1000)

    assert first == second
    assert first.promotion_passed
    assert first.selected_candidate == "coarse-v1"
    report = first.reports["coarse-v1"]
    assert report.metrics.supplied == 50
    assert report.metrics.saved == 50
    assert report.metrics.harmed == 0
    assert report.metrics.net_gain == 50
    assert report.metrics.ci_low > 0
    assert all(value > 0 for value in report.metrics.fold_net_gains)


def test_crossfit_refuses_an_inert_one_class_state() -> None:
    state = _state('[{"name":"weather","arguments":{"city":"x"}}]')
    outcomes = tuple(_outcome(f"s{i:02d}", state=state, supply=1) for i in range(30))
    result = smem.screen_candidates(outcomes, seed=5, n_replicates=200)
    assert not result.promotion_passed
    assert result.selected_candidate is None
    assert not result.reports["coarse-v1"].gates["state_liveness"]


def test_crossfit_refuses_reward_cells_that_carry_harm() -> None:
    benefit_state = _state('[{"name":"weather","arguments":{"city":"x"}}]')
    other_state = _state('[{"name":"ping","arguments":{}}]')
    outcomes = tuple(
        [_outcome(f"b{i:02d}", state=benefit_state, supply=1) for i in range(10)]
        + [_outcome(f"h{i:02d}", state=benefit_state, stop=1, supply=0) for i in range(10)]
        + [_outcome(f"n{i:02d}", state=other_state, stop=1, supply=1) for i in range(20)]
    )
    result = smem.screen_candidates(outcomes, seed=7, n_replicates=200)
    assert not result.promotion_passed
    assert result.reports["coarse-v1"].metrics.supplied == 0


def test_group_bootstrap_resamples_whole_query_groups() -> None:
    state = _state('[{"name":"weather","arguments":{"city":"x"}}]')
    decisions = (
        smem.DecisionOutcome(_outcome("a1", group_id="q1", state=state, supply=1), "SUPPLY_STRIPPED_REGISTRY", 1),
        smem.DecisionOutcome(_outcome("a2", group_id="q1", state=state, supply=1), "SUPPLY_STRIPPED_REGISTRY", 1),
        smem.DecisionOutcome(_outcome("b1", group_id="q2", state=state, stop=1, supply=0), "STOP_DIRECT", 1),
    )
    result = smem.grouped_net_gain_bootstrap(decisions, seed=3, n_replicates=200)
    assert result.point_estimate == pytest.approx(2 / 3)
    assert set(result.replicates) <= {0.0, 2 / 3, 1.0}


def test_supply_renderer_identity_is_static_and_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    smem.assert_supply_renderer_identity()
    monkeypatch.setattr(smem, "POP_SUPPLY_RENDERER", lambda rows: "drift")
    with pytest.raises(smem.SupplyMemoryError, match="renderer"):
        smem.assert_supply_renderer_identity()


def test_policy_artifact_self_hash_detects_mutation() -> None:
    artifact = smem.with_self_hash(
        {
            "schema": smem.POLICY_SCHEMA,
            "promotion_passed": True,
            "selected_candidate": "coarse-v1",
        }
    )
    smem.assert_self_hash(artifact)
    changed = json.loads(json.dumps(artifact))
    changed["selected_candidate"] = "detailed-v1"
    with pytest.raises(smem.SupplyMemoryError, match="self hash"):
        smem.assert_self_hash(changed)


def test_prospective_admission_refuses_failed_or_unattributed_policy() -> None:
    with pytest.raises(smem.SupplyMemoryError, match="promotion screen"):
        smem.assert_policy_admits_prospective(
            {"schema": smem.POLICY_SCHEMA, "promotion_passed": False}
        )
    with pytest.raises(smem.SupplyMemoryError, match="both actions"):
        smem.assert_policy_admits_prospective(
            {
                "schema": smem.POLICY_SCHEMA,
                "promotion_passed": True,
                "selected": {"metrics": {"supplied": 0, "stopped": 217}},
            }
        )


def test_prospective_admission_accepts_only_live_changed_policy() -> None:
    smem.assert_policy_admits_prospective(
        {
            "schema": smem.POLICY_SCHEMA,
            "promotion_passed": True,
            "selected": {
                "metrics": {"supplied": 20, "stopped": 197},
                "state_class_counts": {"a": 100, "b": 117},
            },
        }
    )
