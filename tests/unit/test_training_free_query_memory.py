from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis import training_free_query_memory as qmem


def _item(
    sample_id: str,
    *,
    group_id: str,
    vector: tuple[float, ...],
    direct: int = 0,
    evidence: int = 0,
) -> qmem.QueryOutcome:
    return qmem.QueryOutcome(
        sample_id=sample_id,
        group_id=group_id,
        query_vector=vector,
        direct_match=direct,
        evidence_match=evidence,
    )


def test_cosine_decision_defaults_to_acquire_without_support() -> None:
    decision = qmem.decide(
        query_vector=(1.0, 0.0),
        memory=(_item("m", group_id="g", vector=(0.0, 1.0)),),
        k=1,
        minimum_cosine=0.5,
    )

    assert decision.action == "ACQUIRE"
    assert decision.reason == "insufficient-query-support"


def test_cosine_decision_stops_only_on_unanimous_nonpositive_return() -> None:
    memory = (
        _item("m1", group_id="g1", vector=(1.0, 0.0), evidence=0),
        _item("m2", group_id="g2", vector=(0.99, 0.01), evidence=0),
        _item("m3", group_id="g3", vector=(0.98, 0.02), evidence=0),
    )
    stopped = qmem.decide(
        query_vector=(1.0, 0.0), memory=memory, k=3, minimum_cosine=0.95
    )
    assert stopped.action == "STOP"

    positive = memory[:-1] + (
        _item("m3", group_id="g3", vector=(0.98, 0.02), evidence=1),
    )
    acquired = qmem.decide(
        query_vector=(1.0, 0.0), memory=positive, k=3, minimum_cosine=0.95
    )
    assert acquired.action == "ACQUIRE"
    assert acquired.reason == "positive-return-query-neighbor"


def test_group_exclusion_removes_an_exact_query_twin() -> None:
    decision = qmem.decide(
        query_vector=(1.0, 0.0),
        memory=(
            _item("same", group_id="shared", vector=(1.0, 0.0), evidence=0),
            _item("other", group_id="other", vector=(0.0, 1.0), evidence=0),
        ),
        k=1,
        minimum_cosine=0.99,
        exclude_group_id="shared",
    )
    assert decision.action == "ACQUIRE"


def test_fit_is_order_invariant_and_passes_on_clustered_failures() -> None:
    items = tuple(
        _item(
            f"s{i:02d}",
            group_id=f"g{i:02d}",
            vector=(1.0, (i % 3) * 0.01),
            evidence=0,
        )
        for i in range(12)
    )
    grid = (
        qmem.Hyperparameters(k=1, minimum_cosine=0.9),
        qmem.Hyperparameters(k=3, minimum_cosine=0.9),
    )
    first = qmem.fit_discovery(items, grid=grid, seed=7)
    second = qmem.fit_discovery(tuple(reversed(items)), grid=grid, seed=7)

    assert first == second
    assert first.support_gate_passed
    assert first.selected == qmem.Hyperparameters(k=3, minimum_cosine=0.9)


def test_fit_fails_when_every_acquisition_is_helpful() -> None:
    items = tuple(
        _item(
            f"s{i:02d}",
            group_id=f"g{i:02d}",
            vector=(1.0, i / 20),
            evidence=1,
        )
        for i in range(12)
    )
    result = qmem.fit_discovery(
        items,
        grid=(qmem.Hyperparameters(k=1, minimum_cosine=0.5),),
        seed=7,
    )
    assert not result.support_gate_passed
    assert result.selected is None


def test_memory_digest_changes_with_query_or_reward() -> None:
    base = (_item("s", group_id="g", vector=(1.0, 0.0), evidence=0),)
    query_changed = (_item("s", group_id="g", vector=(0.0, 1.0), evidence=0),)
    reward_changed = (_item("s", group_id="g", vector=(1.0, 0.0), evidence=1),)

    assert qmem.memory_digest(base) != qmem.memory_digest(query_changed)
    assert qmem.memory_digest(base) != qmem.memory_digest(reward_changed)


def test_policy_self_hash_detects_mutation() -> None:
    artifact = qmem.with_self_hash(
        {
            "schema": qmem.POLICY_SCHEMA,
            "support_gate_passed": True,
            "selected": {"k": 3, "minimum_cosine": 0.9},
        }
    )
    qmem.assert_self_hash(artifact)
    changed = json.loads(json.dumps(artifact))
    changed["selected"]["k"] = 1
    with pytest.raises(qmem.QueryPolicyError, match="self hash"):
        qmem.assert_self_hash(changed)


def test_holdout_refuses_failed_policy() -> None:
    with pytest.raises(qmem.QueryPolicyError, match="support gate"):
        qmem.assert_policy_admits_holdout(
            {"schema": qmem.POLICY_SCHEMA, "support_gate_passed": False}
        )
