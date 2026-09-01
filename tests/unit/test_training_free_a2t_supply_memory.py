from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_supply_memory as smem,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall


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


def _a0_row(sample_id: str, response: str, *, arm: str = "zero-supply") -> SimpleNamespace:
    return SimpleNamespace(arm=arm, sample_id=sample_id, response_text=response)


def _supply_row(
    arm: str, sample_id: str, supplied_tool: str, response: str
) -> SimpleNamespace:
    return SimpleNamespace(
        arm=arm,
        sample_id=sample_id,
        supplied_tool=supplied_tool,
        response=response,
    )


def _synthetic_surface_inputs() -> dict[str, object]:
    return {
        "a0_rows": (
            _a0_row(
                "tier1_direct:000001",
                '[{"name":"weather","arguments":{"city":"wrong"}}]',
            ),
            _a0_row("tier1_direct:000002", '[{"name":"ping","arguments":{}}]'),
        ),
        "headroom_supply_rows": (
            _supply_row(
                "B1",
                "tier1_direct:000001",
                "weather",
                '[{"name":"weather","arguments":{"city":"right"}}]',
            ),
        ),
        "population_supply_rows": (
            _supply_row("R1", "tier1_direct:000002", "ping", "[]"),
        ),
        "headroom_ids": ("tier1_direct:000001",),
        "query_group_by_id": {
            "tier1_direct:000001": "q-1",
            "tier1_direct:000002": "q-2",
        },
        "registry_rows": (
            {"tool_name": "weather", "signature": "weather(city: str)"},
            {"tool_name": "ping", "signature": "ping()"},
        ),
        "expected_by_id": {
            "tier1_direct:000001": (ToolCall("weather", {"city": "right"}),),
            "tier1_direct:000002": (ToolCall("ping", {}),),
        },
        "expected_a0_n": 2,
        "expected_headroom_n": 1,
        "expected_population_n": 1,
    }


def test_logged_surface_recomputes_paired_rewards_and_state() -> None:
    surface = smem.build_logged_surface(**_synthetic_surface_inputs())
    assert len(surface.outcomes) == 2
    by_id = {item.sample_id: item for item in surface.outcomes}
    assert by_id["tier1_direct:000001"].delta == 1
    assert by_id["tier1_direct:000002"].delta == -1
    assert by_id["tier1_direct:000001"].group_id == "q-1"
    assert surface.audit == smem.SurfaceAudit(
        a0_rows=2,
        headroom_rows=1,
        population_rows=1,
        eligible_rows=2,
        distinct_query_groups=2,
        repeated_query_groups=0,
        supplied_tool_label_matches=2,
        unresolved_registry_signatures=0,
    )
    cells = smem.state_return_cells(surface.outcomes, candidate_id="coarse-v1")
    assert sum(cell["n"] for cell in cells.values()) == 2
    assert sum(cell["saves"] for cell in cells.values()) == 1
    assert sum(cell["harms"] for cell in cells.values()) == 1


def test_logged_surface_refuses_a_supplied_tool_not_selected_by_a0() -> None:
    inputs = _synthetic_surface_inputs()
    inputs["headroom_supply_rows"] = (
        _supply_row(
            "B1",
            "tier1_direct:000001",
            "ping",
            '[{"name":"weather","arguments":{"city":"right"}}]',
        ),
    )
    with pytest.raises(smem.SupplyMemoryError, match="supplied tool label"):
        smem.build_logged_surface(**inputs)


def test_logged_surface_refuses_gold_strata_that_do_not_match_the_frozen_definition() -> None:
    inputs = _synthetic_surface_inputs()
    expected = dict(inputs["expected_by_id"])
    expected["tier1_direct:000002"] = (ToolCall("weather", {"city": "right"}),)
    inputs["expected_by_id"] = expected
    with pytest.raises(smem.SupplyMemoryError, match="population stratum"):
        smem.build_logged_surface(**inputs)


def test_logged_surface_refuses_missing_query_group_or_duplicate_a0_row() -> None:
    missing_group = _synthetic_surface_inputs()
    missing_group["query_group_by_id"] = {"tier1_direct:000001": "q-1"}
    with pytest.raises(smem.SupplyMemoryError, match="query group"):
        smem.build_logged_surface(**missing_group)

    duplicate = _synthetic_surface_inputs()
    duplicate["a0_rows"] = (
        duplicate["a0_rows"][0],
        duplicate["a0_rows"][0],
    )
    with pytest.raises(smem.SupplyMemoryError, match="duplicate"):
        smem.build_logged_surface(**duplicate)


def test_artifact_payload_keeps_hashed_identities_and_excludes_raw_responses() -> None:
    surface = smem.build_logged_surface(**_synthetic_surface_inputs())
    screen = smem.screen_candidates(surface.outcomes, seed=3, n_folds=2, n_replicates=20)
    artifact = smem.build_policy_artifact(surface, screen, offline_attempts=0)
    smem.assert_self_hash(artifact)
    encoded = json.dumps(artifact, sort_keys=True)
    assert "wrong" not in encoded
    assert "right" not in encoded
    assert artifact["surface"]["eligible_rows"] == 2
    assert len(artifact["surface"]["sample_identity_sha256"]) == 64


def test_receipt_group_loader_uses_query_idx_and_refuses_duplicates(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "carrier": "audio2tool",
                "split_identity_hash": "split-hash",
                "items": [
                    {"tier": "tier1_direct", "id": 1, "query_idx": 9},
                    {"tier": "tier1_direct", "id": 2, "query_idx": 9},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert smem.load_query_groups_from_receipt(
        receipt, expected_split_identity_hash="split-hash"
    ) == {
        "tier1_direct:000001": "9",
        "tier1_direct:000002": "9",
    }

    document = json.loads(receipt.read_text(encoding="utf-8"))
    document["items"].append(document["items"][0])
    receipt.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(smem.SupplyMemoryError, match="duplicate"):
        smem.load_query_groups_from_receipt(
            receipt, expected_split_identity_hash="split-hash"
        )


def test_receipt_group_loader_refuses_wrong_carrier_hash_or_missing_query_idx(
    tmp_path: Path,
) -> None:
    receipt = tmp_path / "receipt.json"
    base = {
        "carrier": "other",
        "split_identity_hash": "split-hash",
        "items": [{"tier": "tier1_direct", "id": 1, "query_idx": 9}],
    }
    receipt.write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(smem.SupplyMemoryError, match="carrier"):
        smem.load_query_groups_from_receipt(
            receipt, expected_split_identity_hash="split-hash"
        )

    base["carrier"] = "audio2tool"
    receipt.write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(smem.SupplyMemoryError, match="split identity"):
        smem.load_query_groups_from_receipt(
            receipt, expected_split_identity_hash="different"
        )

    del base["items"][0]["query_idx"]
    receipt.write_text(json.dumps(base), encoding="utf-8")
    with pytest.raises(smem.SupplyMemoryError, match="query_idx"):
        smem.load_query_groups_from_receipt(
            receipt, expected_split_identity_hash="split-hash"
        )


def test_source_hash_reads_complete_file(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"signed-supply-source")
    assert smem._sha256_file(source) == hashlib.sha256(  # noqa: SLF001
        b"signed-supply-source"
    ).hexdigest()


def test_fast_a0_validation_reuses_structural_checks_without_scoring(tmp_path: Path) -> None:
    rows = (_a0_row("tier1_direct:000001", "[]"),)
    calls: list[str] = []

    fake_reader = SimpleNamespace(
        load_attempt_rows=lambda _path: (rows, ()),
        load_flight_receipt=lambda _path: {"status": "COMPLETED"},
        _load_split_receipt=lambda _repo, _role: {
            "split_identity_hash": "hash",
            "items": [{"tier": "tier1_direct", "id": 1}],
        },
        expected_sample_ids=lambda _receipt: ("tier1_direct:000001",),
        _harness_defect_reasons=lambda **_kwargs: calls.append("checked") or (),
    )
    assert smem._validated_a0_rows(  # noqa: SLF001
        fake_reader,
        attempt_dir=tmp_path,
        repo_root=tmp_path,
    ) == rows
    assert calls == ["checked"]

    fake_reader._harness_defect_reasons = lambda **_kwargs: ("drift",)
    with pytest.raises(smem.SupplyMemoryError, match="drift"):
        smem._validated_a0_rows(  # noqa: SLF001
            fake_reader,
            attempt_dir=tmp_path,
            repo_root=tmp_path,
        )
