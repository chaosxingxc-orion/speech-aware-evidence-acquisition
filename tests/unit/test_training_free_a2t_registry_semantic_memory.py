from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_registry_semantic_memory as v2,
)
from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_supply_memory as v1,
)
from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_registry_semantic_memory_cli as v2cli,
)


def _base_state() -> v1.RuntimeState:
    return v1.RuntimeState(
        parse_class="single",
        registry_resolution="all-known",
        declared_key_relation="exact",
        schema_arity_bucket="one",
        provided_key_bucket="one",
    )


def _base_outcome(
    sample_id: str,
    *,
    stop: int = 0,
    supply: int = 0,
    group_id: str | None = None,
) -> v1.SignedSupplyOutcome:
    return v1.SignedSupplyOutcome(
        sample_id=sample_id,
        group_id=sample_id if group_id is None else group_id,
        state=_base_state(),
        stop_exact=stop,
        supply_exact=supply,
        stop_tool_accuracy=float(stop),
        supply_tool_accuracy=float(supply),
        stop_slot_f1=float(stop),
        supply_slot_f1=float(supply),
    )


def _registry() -> tuple[dict[str, str], ...]:
    return (
        {"tool_name": "alpha", "domain": "home", "category": "search"},
        {"tool_name": "beta", "domain": "home", "category": "search"},
        {"tool_name": "gamma", "domain": "travel", "category": "booking"},
    )


def test_semantic_pairs_ignore_tool_identity_order_and_duplicates() -> None:
    alpha = v2.extract_semantic_pairs(
        '[{"name":"alpha","arguments":{}}]', _registry()
    )
    beta = v2.extract_semantic_pairs(
        '[{"name":"beta","arguments":{}}]', _registry()
    )
    assert alpha == beta == (("home", "search"),)

    forward = v2.extract_semantic_pairs(
        '[{"name":"alpha","arguments":{}},{"name":"gamma","arguments":{}},'
        '{"name":"alpha","arguments":{}}]',
        _registry(),
    )
    reverse = v2.extract_semantic_pairs(
        '[{"name":"gamma","arguments":{}},{"name":"alpha","arguments":{}}]',
        _registry(),
    )
    assert forward == reverse == (("home", "search"), ("travel", "booking"))


@pytest.mark.parametrize(
    ("response", "registry", "expected"),
    [
        ("not-json", (), (("unresolved", "unresolved"),)),
        ("[]", (), (("no-call", "no-call"),)),
        (
            '[{"name":"unknown","arguments":{}}]',
            (),
            (("unresolved", "unresolved"),),
        ),
        (
            '[{"name":"alpha","arguments":{}}]',
            ({"tool_name": "alpha", "domain": "", "category": "search"},),
            (("unresolved", "unresolved"),),
        ),
    ],
)
def test_semantic_pairs_fail_closed_on_missing_runtime_metadata(
    response: str,
    registry: tuple[dict[str, str], ...],
    expected: tuple[tuple[str, str], ...],
) -> None:
    assert v2.extract_semantic_pairs(response, registry) == expected


def test_semantic_state_appends_only_the_registered_pair_abstraction() -> None:
    state = v2.SemanticRuntimeState(_base_state(), (("home", "search"),))
    assert state.key("domain-category-coarse-v2") == (
        "single",
        "all-known",
        "exact",
        "home/search",
    )
    assert state.key("domain-category-detailed-v2") == (
        "single",
        "all-known",
        "exact",
        "one",
        "one",
        "home/search",
    )
    with pytest.raises(v1.SupplyMemoryError, match="unknown candidate"):
        state.key("invented")


def test_augmentation_preserves_every_v1_identity_and_reward() -> None:
    base = (
        _base_outcome("a", stop=0, supply=1, group_id="q"),
        _base_outcome("b", stop=1, supply=0, group_id="q"),
    )
    augmented = v2.augment_outcomes(
        base,
        direct_response_by_id={
            "a": '[{"name":"alpha","arguments":{}}]',
            "b": '[{"name":"gamma","arguments":{}}]',
        },
        registry_rows=_registry(),
    )
    assert [item.sample_id for item in augmented] == ["a", "b"]
    assert [item.group_id for item in augmented] == ["q", "q"]
    assert [item.delta for item in augmented] == [1, -1]
    assert augmented[0].state.base == base[0].state


def test_semantic_crossfit_separates_safe_and_harmful_domains() -> None:
    base = tuple(
        [_base_outcome(f"s{i:02d}", supply=1) for i in range(50)]
        + [_base_outcome(f"h{i:02d}", stop=1, supply=0) for i in range(50)]
    )
    responses = {
        item.sample_id: (
            '[{"name":"alpha","arguments":{}}]'
            if item.sample_id.startswith("s")
            else '[{"name":"gamma","arguments":{}}]'
        )
        for item in base
    }
    outcomes = v2.augment_outcomes(base, responses, _registry())
    first = v2.screen_candidates(outcomes, seed=19, n_replicates=1000)
    second = v2.screen_candidates(tuple(reversed(outcomes)), seed=19, n_replicates=1000)
    assert first == second
    assert first.promotion_passed
    assert first.selected_candidate == "domain-category-coarse-v2"
    report = first.reports["domain-category-coarse-v2"]
    assert report.metrics.saved == 50
    assert report.metrics.harmed == 0
    assert report.metrics.supplied == 50


def test_v1_memory_identity_gate_refuses_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = v1.LoggedSurface(
        outcomes=(_base_outcome("a", supply=1),),
        audit=v1.SurfaceAudit(1, 1, 0, 1, 1, 0, 1, 0),
    )
    digest = v2.v1_surface_memory_digest(surface)
    monkeypatch.setattr(v2, "EXPECTED_V1_MEMORY_SHA256", digest)
    v1_artifact = {"surface": {"memory_sha256": digest}}
    v2.assert_v1_surface_identity(surface, v1_artifact)

    changed = json.loads(json.dumps(v1_artifact))
    changed["surface"]["memory_sha256"] = "0" * 64
    with pytest.raises(v1.SupplyMemoryError, match="memory identity"):
        v2.assert_v1_surface_identity(surface, changed)


def test_v2_artifact_is_self_hashed_and_admission_is_fail_closed() -> None:
    base = tuple(
        [_base_outcome(f"s{i:02d}", supply=1) for i in range(20)]
        + [_base_outcome(f"h{i:02d}", stop=1, supply=0) for i in range(20)]
    )
    responses = {
        item.sample_id: (
            '[{"name":"alpha","arguments":{}}]'
            if item.sample_id.startswith("s")
            else '[{"name":"gamma","arguments":{}}]'
        )
        for item in base
    }
    outcomes = v2.augment_outcomes(base, responses, _registry())
    screen = v2.screen_candidates(outcomes, seed=7, n_replicates=100)
    artifact = v2.build_policy_artifact(outcomes, screen, offline_attempts=0)
    v1.assert_self_hash(artifact)
    selected = artifact["selected"]
    assert "full_surface_return_cells" not in selected
    assert "state_class_counts" not in selected
    assert selected["state_support_summary"]["state_class_count"] == 2
    assert selected["state_class_summary"]["live_class_count"] == 2
    assert len(selected["non_neutral_return_cells"]) == 2
    v2.assert_policy_admits_prospective(artifact)

    failed = dict(artifact)
    failed["promotion_passed"] = False
    with pytest.raises(v1.SupplyMemoryError, match="promotion screen"):
        v2.assert_policy_admits_prospective(failed)


def test_registered_runner_composes_the_committed_v1_surface(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    base = tuple(
        [_base_outcome(f"s{i:02d}", supply=1) for i in range(20)]
        + [_base_outcome(f"h{i:02d}", stop=1, supply=0) for i in range(20)]
    )
    surface = v1.LoggedSurface(
        outcomes=base,
        audit=v1.SurfaceAudit(40, 20, 20, 40, 40, 0, 40, 0),
    )
    digest = v2.v1_surface_memory_digest(surface)
    monkeypatch.setattr(v2, "EXPECTED_V1_MEMORY_SHA256", digest)
    predecessor = {"surface": {"memory_sha256": digest}}
    responses = {
        item.sample_id: (
            '[{"name":"alpha","arguments":{}}]'
            if item.sample_id.startswith("s")
            else '[{"name":"gamma","arguments":{}}]'
        )
        for item in base
    }

    monkeypatch.setattr(v2cli, "assert_registration_committed", lambda _root: None)
    monkeypatch.setattr(v2cli, "_arm_offline_guard", lambda: SimpleNamespace(count=0))
    monkeypatch.setattr(v1, "load_registered_surface", lambda **_kwargs: surface)
    monkeypatch.setattr(v2cli, "_load_v1_artifact", lambda _path: predecessor)
    monkeypatch.setattr(v2cli, "_a0_direct_responses", lambda *_args: responses)
    monkeypatch.setattr(v2cli, "_load_registry_rows", lambda *_args: _registry())
    monkeypatch.setattr(v1, "_sha256_file", lambda _path: "f" * 64)

    artifact = v2cli.run_registered_replay(
        repo_root=tmp_path,
        data_root=tmp_path,
        lock={},
        a0_attempt=tmp_path,
        headroom_supply_attempt=tmp_path,
        population_supply_attempt=tmp_path,
        headroom_path=tmp_path / "headroom.json",
        stage2_arm_plan_path=tmp_path / "arm-plan.json",
        receipt_path=tmp_path / "receipt.json",
        v1_artifact_path=tmp_path / "v1.json",
    )
    assert artifact["promotion_passed"] is True
    assert artifact["offline_guard"]["outbound_connection_attempts"] == 0
    v1.assert_self_hash(artifact)


def test_registered_cli_parser_requires_every_bound_source() -> None:
    args = v2cli._parser().parse_args(  # noqa: SLF001
        [
            "--repo-root",
            "/repo",
            "--data-root",
            "/data",
            "--lock",
            "/lock.json",
            "--a0-attempt",
            "/a0",
            "--headroom-supply-attempt",
            "/b1",
            "--population-supply-attempt",
            "/r1",
            "--headroom",
            "/headroom.json",
            "--stage2-arm-plan",
            "/plan.json",
            "--receipt",
            "/receipt.json",
            "--v1-artifact",
            "/v1.json",
        ]
    )
    assert args.repo_root == Path("/repo")
    assert args.v1_artifact == Path("/v1.json")
