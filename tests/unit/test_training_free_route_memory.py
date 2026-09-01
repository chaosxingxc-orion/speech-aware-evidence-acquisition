from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis import training_free_route_memory as rmem


def _item(
    sample_id: str,
    *,
    group_id: str,
    vector: tuple[float, ...],
    route: str = "direct-runner-up",
    direct: int = 0,
    evidence: int = 0,
) -> rmem.RouteOutcome:
    return rmem.RouteOutcome(
        sample_id=sample_id,
        group_id=group_id,
        query_vector=vector,
        route_class=route,
        direct_match=direct,
        evidence_match=evidence,
    )


@pytest.mark.parametrize(
    ("direct", "fused", "expected"),
    [
        (None, ("a", "b"), "direct-unresolved"),
        ("z", ("a", "b"), "direct-absent"),
        ("a", ("a", "b"), "direct-rank-1-dispatched"),
        ("b", ("a", "b"), "direct-runner-up"),
        ("c", ("a", "b", "c"), "direct-rank-3plus"),
    ],
)
def test_route_class_is_an_exact_precontact_relation(
    direct: str | None, fused: tuple[str, ...], expected: str
) -> None:
    assert rmem.classify_route(direct_target=direct, fused_targets=fused) == expected


def test_decision_rejects_a_close_neighbor_from_another_route() -> None:
    decision = rmem.decide(
        query_vector=(1.0, 0.0),
        route_class="direct-runner-up",
        memory=(
            _item(
                "m",
                group_id="g",
                vector=(1.0, 0.0),
                route="direct-absent",
            ),
        ),
        k=1,
        minimum_cosine=0.9,
    )
    assert decision.action == "ACQUIRE"
    assert decision.reason == "insufficient-route-query-support"


def test_decision_stops_only_on_same_route_nonpositive_return() -> None:
    memory = (
        _item("m1", group_id="g1", vector=(1.0, 0.0), evidence=0),
        _item("m2", group_id="g2", vector=(0.99, 0.01), evidence=0),
        _item("m3", group_id="g3", vector=(0.98, 0.02), evidence=0),
    )
    stopped = rmem.decide(
        query_vector=(1.0, 0.0),
        route_class="direct-runner-up",
        memory=memory,
        k=3,
        minimum_cosine=0.95,
    )
    assert stopped.action == "STOP"

    positive = memory[:-1] + (
        _item("m3", group_id="g3", vector=(0.98, 0.02), evidence=1),
    )
    acquired = rmem.decide(
        query_vector=(1.0, 0.0),
        route_class="direct-runner-up",
        memory=positive,
        k=3,
        minimum_cosine=0.95,
    )
    assert acquired.action == "ACQUIRE"
    assert acquired.reason == "positive-return-route-neighbor"


def test_fold_assignment_is_order_invariant_balanced_and_group_isolated() -> None:
    items = tuple(
        _item(
            f"s{i:02d}",
            group_id=f"g{i // 2:02d}",
            vector=(1.0, i / 100),
        )
        for i in range(20)
    )
    first = rmem.assign_folds(items, seed=11, n_folds=5)
    second = rmem.assign_folds(tuple(reversed(items)), seed=11, n_folds=5)

    assert first == second
    assert max(map(len, first)) - min(map(len, first)) <= 2
    for group in {item.group_id for item in items}:
        assert sum(any(item.group_id == group for item in fold) for fold in first) == 1


def test_crossfit_selects_stable_zero_harm_controller() -> None:
    items = tuple(
        _item(
            f"s{i:02d}",
            group_id=f"g{i:02d}",
            vector=(1.0, (i % 3) * 0.01),
            evidence=0,
        )
        for i in range(20)
    )
    grid = (
        rmem.Hyperparameters(k=1, minimum_cosine=0.9),
        rmem.Hyperparameters(k=3, minimum_cosine=0.9),
    )
    first = rmem.fit_crossfitted(items, grid=grid, seed=7, n_folds=5)
    second = rmem.fit_crossfitted(tuple(reversed(items)), grid=grid, seed=7, n_folds=5)

    assert first == second
    assert first.stability_screen_passed
    assert first.selected == rmem.Hyperparameters(k=3, minimum_cosine=0.9)
    assert first.crossfit_metrics.stopped == 20
    assert first.active_stop_folds == 5


def test_crossfit_fails_when_every_acquisition_is_helpful() -> None:
    items = tuple(
        _item(
            f"s{i:02d}",
            group_id=f"g{i:02d}",
            vector=(1.0, i / 100),
            evidence=1,
        )
        for i in range(20)
    )
    result = rmem.fit_crossfitted(
        items,
        grid=(rmem.Hyperparameters(k=1, minimum_cosine=0.5),),
        seed=7,
        n_folds=5,
    )
    assert not result.stability_screen_passed
    assert result.selected is None


def test_memory_digest_changes_with_route_or_reward() -> None:
    base = (_item("s", group_id="g", vector=(1.0, 0.0), evidence=0),)
    route_changed = (
        _item(
            "s",
            group_id="g",
            vector=(1.0, 0.0),
            route="direct-absent",
            evidence=0,
        ),
    )
    reward_changed = (_item("s", group_id="g", vector=(1.0, 0.0), evidence=1),)

    assert rmem.memory_digest(base) != rmem.memory_digest(route_changed)
    assert rmem.memory_digest(base) != rmem.memory_digest(reward_changed)


def test_policy_self_hash_detects_mutation() -> None:
    artifact = rmem.with_self_hash(
        {
            "schema": rmem.POLICY_SCHEMA,
            "stability_screen_passed": True,
            "selected": {"k": 3, "minimum_cosine": 0.9},
        }
    )
    rmem.assert_self_hash(artifact)
    changed = json.loads(json.dumps(artifact))
    changed["selected"]["k"] = 1
    with pytest.raises(rmem.RoutePolicyError, match="self hash"):
        rmem.assert_self_hash(changed)


def test_holdout_refuses_failed_policy() -> None:
    with pytest.raises(rmem.RoutePolicyError, match="stability screen"):
        rmem.assert_policy_admits_holdout(
            {"schema": rmem.POLICY_SCHEMA, "stability_screen_passed": False}
        )


def test_holdout_refuses_a_degenerate_route_state() -> None:
    with pytest.raises(rmem.RoutePolicyError, match="route state is degenerate"):
        rmem.assert_policy_admits_holdout(
            {
                "schema": rmem.POLICY_SCHEMA,
                "stability_screen_passed": True,
                "discovery": {"route_class_counts": {"direct-unresolved": 37}},
                "crossfit": {"stopped_ids": ["a"]},
                "fixed_v2_comparator": {"crossfit": {"stopped_ids": ["b"]}},
            }
        )


def test_holdout_refuses_route_conditioning_that_changes_no_decision() -> None:
    with pytest.raises(rmem.RoutePolicyError, match="does not change cross-fitted decisions"):
        rmem.assert_policy_admits_holdout(
            {
                "schema": rmem.POLICY_SCHEMA,
                "stability_screen_passed": True,
                "discovery": {
                    "route_class_counts": {
                        "direct-absent": 20,
                        "direct-runner-up": 17,
                    }
                },
                "crossfit": {"stopped_ids": ["a", "b"]},
                "fixed_v2_comparator": {"crossfit": {"stopped_ids": ["a", "b"]}},
            }
        )


def test_holdout_accepts_a_live_route_policy_with_changed_decisions() -> None:
    rmem.assert_policy_admits_holdout(
        {
            "schema": rmem.POLICY_SCHEMA,
            "stability_screen_passed": True,
            "discovery": {
                "route_class_counts": {
                    "direct-absent": 20,
                    "direct-runner-up": 17,
                }
            },
            "crossfit": {"stopped_ids": ["a"]},
            "fixed_v2_comparator": {"crossfit": {"stopped_ids": ["b"]}},
        }
    )
