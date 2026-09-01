from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis import training_free_acquisition_memory as tfrl


def _item(
    sample_id: str,
    *,
    group_id: str,
    value: float,
    direct: int = 0,
    evidence: int = 0,
) -> tfrl.Outcome:
    return tfrl.Outcome(
        sample_id=sample_id,
        group_id=group_id,
        state=(value,) * len(tfrl.FEATURE_NAMES),
        direct_match=direct,
        evidence_match=evidence,
    )


def test_decide_defaults_to_acquire_without_support() -> None:
    memory = (_item("m1", group_id="g1", value=0.1),)

    decision = tfrl.decide(
        state=(0.9,) * len(tfrl.FEATURE_NAMES),
        memory=memory,
        k=1,
        radius=0.1,
    )

    assert decision.action == "ACQUIRE"
    assert decision.reason == "insufficient-local-support"


def test_decide_stops_only_when_local_returns_are_unanimously_nonpositive() -> None:
    memory = (
        _item("m1", group_id="g1", value=0.10, evidence=0),
        _item("m2", group_id="g2", value=0.11, evidence=0),
        _item("m3", group_id="g3", value=0.12, evidence=0),
    )
    query = (0.11,) * len(tfrl.FEATURE_NAMES)

    stopped = tfrl.decide(state=query, memory=memory, k=3, radius=0.05)
    assert stopped.action == "STOP"
    assert stopped.neighbor_ids == ("m2", "m1", "m3")

    with_positive = memory[:-1] + (_item("m3", group_id="g3", value=0.12, evidence=1),)
    acquired = tfrl.decide(state=query, memory=with_positive, k=3, radius=0.05)
    assert acquired.action == "ACQUIRE"
    assert acquired.reason == "positive-return-neighbor"


def test_group_exclusion_prevents_same_utterance_leakage() -> None:
    memory = (
        _item("same", group_id="shared", value=0.10, evidence=0),
        _item("other", group_id="other", value=0.40, evidence=0),
    )

    decision = tfrl.decide(
        state=(0.10,) * len(tfrl.FEATURE_NAMES),
        memory=memory,
        k=1,
        radius=0.05,
        exclude_group_id="shared",
    )

    assert decision.action == "ACQUIRE"
    assert decision.neighbor_ids == ()


def test_select_candidate_is_deterministic_and_uses_group_holdout() -> None:
    items = tuple(
        _item(
            f"s{i:02d}",
            group_id=f"g{i:02d}",
            value=0.10 + (i % 3) * 0.01,
            evidence=0,
        )
        for i in range(12)
    )
    grid = (
        tfrl.Hyperparameters(k=1, radius=0.05),
        tfrl.Hyperparameters(k=3, radius=0.05),
    )

    first = tfrl.fit_discovery(items, grid=grid, seed=7)
    second = tfrl.fit_discovery(tuple(reversed(items)), grid=grid, seed=7)

    assert first == second
    assert first.support_gate_passed
    assert first.selected == tfrl.Hyperparameters(k=3, radius=0.05)
    assert first.gate_metrics.harmful_stops == 0


def test_support_gate_fails_when_policy_never_saves_a_contact() -> None:
    items = tuple(
        _item(
            f"s{i:02d}",
            group_id=f"g{i:02d}",
            value=i / 12,
            evidence=1,
        )
        for i in range(12)
    )

    result = tfrl.fit_discovery(
        items,
        grid=(tfrl.Hyperparameters(k=1, radius=0.01),),
        seed=7,
    )

    assert not result.support_gate_passed
    assert result.selected is None


def test_evaluate_reports_harm_and_contact_savings_exactly() -> None:
    memory = (
        _item("m1", group_id="m1", value=0.1, evidence=0),
        _item("m2", group_id="m2", value=0.1, evidence=0),
        _item("m3", group_id="m3", value=0.1, evidence=0),
    )
    holdout = (
        _item("neutral", group_id="h1", value=0.1, direct=0, evidence=0),
        _item("harm", group_id="h2", value=0.1, direct=0, evidence=1),
        _item("acquire", group_id="h3", value=0.9, direct=0, evidence=1),
    )

    metrics = tfrl.evaluate(
        holdout,
        memory=memory,
        params=tfrl.Hyperparameters(k=3, radius=0.05),
    )

    assert metrics.stopped == 2
    assert metrics.acquired == 1
    assert metrics.contacts_saved == 2
    assert metrics.harmful_stops == 1
    assert metrics.policy_correct == 1
    assert metrics.baseline_correct == 2


def test_policy_artifact_self_hash_detects_mutation() -> None:
    payload = {
        "schema": tfrl.POLICY_SCHEMA,
        "policy_id": "fixture",
        "support_gate_passed": True,
        "selected": {"k": 3, "radius": 0.1},
        "memory_digest": "0" * 64,
    }
    artifact = tfrl.with_self_hash(payload)

    tfrl.assert_self_hash(artifact)
    mutated = json.loads(json.dumps(artifact))
    mutated["selected"]["k"] = 1
    with pytest.raises(tfrl.PolicyError, match="self hash"):
        tfrl.assert_self_hash(mutated)


def test_holdout_refuses_a_policy_without_a_passed_support_gate() -> None:
    with pytest.raises(tfrl.PolicyError, match="support gate"):
        tfrl.assert_policy_admits_holdout(
            {
                "schema": tfrl.POLICY_SCHEMA,
                "support_gate_passed": False,
            }
        )
