"""Focused model-free tests for the G6 exhaustive family-sweep core."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.probes.a2t_g6_family_sweep import (
    FAMILY_COUNT,
    OPERATIONAL_HEADROOM_TOKENS,
    PER_SLOT_CONTEXT_TOKENS,
    ArgumentSpec,
    FamilyScanReport,
    FamilyBundle,
    G6FamilySweep,
    G6FamilySweepError,
    ToolContract,
    build_trace_documents,
    measure_prompt_envelope,
)


def _contract(index: int) -> ToolContract:
    return ToolContract(
        contract_id=f"contract-{index:02d}",
        family_tag=f"family-{index:02d}",
        tool_name=f"tool{index:02d}",
        arguments=(
            ArgumentSpec("target", required=True),
            ArgumentSpec("count", required=False, canonicalizer_ids=("to-int",)),
        ),
        content=f"Use tool{index:02d} with a required target and optional count.",
        legal_key_skeletons=(("target",), ("target", "count")),
    )


def _sweep(*, max_final_calls: int = 4) -> G6FamilySweep:
    contracts = tuple(_contract(index) for index in range(FAMILY_COUNT))
    return G6FamilySweep(
        family_bundles=tuple(
            FamilyBundle(contract.family_tag, (contract,)) for contract in contracts
        ),
        max_final_calls=max_final_calls,
        canonicalizers={"to-int": lambda value: int(value)},
    )


def _scan_json(
    index: int,
    *,
    tool_name: str | None = None,
    argument_key: str = "target",
    value: object = "Alice",
    unresolved: list[str] | None = None,
) -> str:
    span = str(value)
    return json.dumps(
        {
            "applicable": True,
            "candidates": [
                {
                    "tool_name": tool_name or f"tool{index:02d}",
                    "speech_spans": [span],
                    "argument_bindings": [
                        {"key": argument_key, "value": value, "speech_span": span}
                    ],
                    "unresolved_required_arguments": unresolved or [],
                }
            ],
            "correction_evidence": [],
            "turn_evidence": ["current"],
            "role_evidence": ["user"],
            "ordering_evidence": [],
        },
        separators=(",", ":"),
    )


def _responses(*, nominated: tuple[int, ...] = (0,)) -> dict[str, str]:
    rows: dict[str, str] = {}
    for index in range(FAMILY_COUNT):
        rows[f"family-{index:02d}"] = (
            _scan_json(index)
            if index in nominated
            else '{"applicable":false,"candidates":[],"correction_evidence":[],'
            '"turn_evidence":[],"role_evidence":[],"ordering_evidence":[]}'
        )
    return rows


def test_builds_exactly_28_independent_scan_contexts() -> None:
    contexts = _sweep().build_scan_contexts(
        speech_packet_id="speech-1",
        speech_packet_sha256="a" * 64,
        task_contract="Use only the original human speech.",
    )

    assert len(contexts) == FAMILY_COUNT == 28
    assert len({context.contact_id for context in contexts}) == FAMILY_COUNT
    assert all(context.stage == "SCAN" for context in contexts)
    assert all(context.report_jsons == () for context in contexts)
    assert all(context.causal_dependency_contact_ids == () for context in contexts)
    assert all(context.attempt_limit == 1 for context in contexts)
    assert all(len(context.contracts) == 1 for context in contexts)
    assert all(
        context.contracts[0].family_tag == context.family_tag for context in contexts
    )
    assert all(context.speech_packet_sha256 == "a" * 64 for context in contexts)
    assert "reference-only" in contexts[0].instruction.casefold()
    assert "no final calls" in contexts[0].instruction.casefold()


def test_valid_scan_preserves_compact_ordered_evidence() -> None:
    sweep = _sweep()
    report = sweep.parse_scan_response("family-00", _scan_json(0))

    assert report.valid is True
    assert report.applicable is True
    assert report.candidates[0].tool_name == "tool00"
    assert report.candidates[0].speech_spans == ("Alice",)
    assert report.candidates[0].argument_bindings[0].key == "target"
    assert len(report.canonical_json.encode("ascii")) <= 2_048


@pytest.mark.parametrize(
    "raw",
    [
        "not-json",
        _scan_json(0, tool_name="tool01"),
        _scan_json(0, argument_key="illegal"),
        _scan_json(0, unresolved=["target"]),
        _scan_json(0).replace('"speech_spans":["Alice"]', '"speech_spans":[]'),
        _scan_json(0) + " trailing",
        "x" * 4_097,
    ],
)
def test_invalid_scan_becomes_empty_for_only_its_family(raw: str) -> None:
    sweep = _sweep()
    responses = _responses(nominated=(1,))
    responses["family-00"] = raw

    reports = sweep.parse_scan_responses(responses)

    assert len(reports) == FAMILY_COUNT
    assert reports[0].family_tag == "family-00"
    assert reports[0].valid is False
    assert reports[0].applicable is False
    assert reports[0].candidates == ()
    assert raw not in reports[0].canonical_json
    assert reports[1].valid is True
    assert reports[1].candidates[0].tool_name == "tool01"


def test_scan_response_surface_must_cover_each_family_once() -> None:
    sweep = _sweep()
    missing = _responses()
    missing.pop("family-27")

    with pytest.raises(G6FamilySweepError, match="exactly the 28 families"):
        sweep.parse_scan_responses(missing)


def test_resolve_context_sees_all_reports_and_only_nominated_exact_contracts() -> None:
    sweep = _sweep()
    reports = sweep.parse_scan_responses(_responses(nominated=(0, 17)))

    context = sweep.build_resolve_context(
        speech_packet_id="speech-1",
        speech_packet_sha256="a" * 64,
        task_contract="Use only the original human speech.",
        reports=reports,
    )

    assert context.stage == "RESOLVE"
    assert len(context.report_jsons) == FAMILY_COUNT
    assert len(context.causal_dependency_contact_ids) == FAMILY_COUNT
    assert context.attempt_limit == 1
    assert tuple(contract.tool_name for contract in context.contracts) == (
        "tool00",
        "tool17",
    )
    assert "tool01" not in context.render_control_text()
    assert "sole final" in context.instruction.casefold()
    assert context.speech_packet_sha256 == "a" * 64


def test_final_resolution_accepts_evidence_copy_and_permitted_canonicalizer() -> None:
    sweep = _sweep(max_final_calls=2)
    responses = _responses(nominated=(0,))
    responses["family-00"] = _scan_json(
        0, argument_key="count", value="3", unresolved=["target"]
    )
    # Add a second binding for the required key without changing the evidence surface.
    responses["family-00"] = (
        responses["family-00"]
        .replace(
            '"argument_bindings":[',
            '"argument_bindings":[{"key":"target","value":"Alice",'
            '"speech_span":"Alice"},',
        )
        .replace('"speech_spans":["3"]', '"speech_spans":["Alice","3"]')
        .replace(
            '"unresolved_required_arguments":["target"]',
            '"unresolved_required_arguments":[]',
        )
    )
    reports = sweep.parse_scan_responses(responses)

    parsed = sweep.parse_resolve_response(
        '[{"name":"tool00","arguments":{"target":"Alice","count":3}}]',
        reports=reports,
    )

    assert parsed.valid is True
    assert parsed.calls[0].arguments == {"target": "Alice", "count": 3}


def test_final_resolution_requires_exact_legal_key_skeleton_membership() -> None:
    sweep = _sweep(max_final_calls=1)
    reports = sweep.parse_scan_responses(_responses(nominated=(0,)))

    legal = sweep.parse_resolve_response(
        '[{"name":"tool00","arguments":{"target":"Alice"}}]',
        reports=reports,
    )
    illegal_order = sweep.parse_resolve_response(
        '[{"name":"tool00","arguments":{"count":3,"target":"Alice"}}]',
        reports=reports,
    )

    assert legal.valid is True
    assert illegal_order.valid is False


@pytest.mark.parametrize(
    "raw",
    [
        "not-json",
        "[]",
        '[{"name":"tool01","arguments":{"target":"Alice"}}]',
        '[{"name":"tool00","arguments":{"illegal":"Alice"}}]',
        '[{"name":"tool00","arguments":{"target":"unspoken"}}]',
        '[{"name":"tool00","arguments":{"target":"Alice"}},'
        '{"name":"tool00","arguments":{"target":"Alice"}}]',
    ],
)
def test_invalid_final_is_sealed_empty_without_repair_or_retry(raw: str) -> None:
    sweep = _sweep(max_final_calls=2)
    reports = sweep.parse_scan_responses(_responses(nominated=(0,)))

    parsed = sweep.parse_resolve_response(raw, reports=reports)

    assert parsed.valid is False
    assert parsed.calls == ()
    assert parsed.canonical_json == "[]"


def test_final_call_count_is_bounded_by_frozen_construction_maximum() -> None:
    sweep = _sweep(max_final_calls=1)
    reports = sweep.parse_scan_responses(_responses(nominated=(0, 1)))
    raw = json.dumps(
        [
            {"name": "tool00", "arguments": {"target": "Alice"}},
            {"name": "tool01", "arguments": {"target": "Alice"}},
        ],
        separators=(",", ":"),
    )

    assert sweep.parse_resolve_response(raw, reports=reports).valid is False


def test_context_measurement_requires_8192_tokens_of_actual_request_headroom() -> None:
    envelope = measure_prompt_envelope(
        contact_id="g6-scan-family-00",
        rendered_request="fully rendered request",
        token_counter=lambda _: 20_000,
        speech_feature_tokens=2_000,
        special_token_reserve=512,
        completion_token_ceiling=1_024,
    )

    assert envelope.total_tokens == 23_536
    assert envelope.remaining_tokens == PER_SLOT_CONTEXT_TOKENS - 23_536
    assert envelope.rendered_request_sha256
    context = _sweep().build_scan_contexts(
        speech_packet_id="speech-1",
        speech_packet_sha256="a" * 64,
        task_contract="Use only original speech.",
    )[0]
    assert (
        context.measure_exact_request(
            "exact rendered request",
            token_counter=lambda _: 1_000,
            speech_feature_tokens=2_000,
        ).completion_token_ceiling
        == 512
    )

    with pytest.raises(G6FamilySweepError, match="operational headroom"):
        measure_prompt_envelope(
            contact_id="g6-resolve",
            rendered_request="exact request",
            token_counter=lambda _: 21_100,
            speech_feature_tokens=2_000,
            special_token_reserve=512,
            completion_token_ceiling=1_024,
        )
    assert OPERATIONAL_HEADROOM_TOKENS == 8_192


def test_trace_documents_keep_obs_org_supply_and_use_separate() -> None:
    sweep = _sweep()
    reports = sweep.parse_scan_responses(_responses(nominated=(0,)))
    context = sweep.build_resolve_context(
        speech_packet_id="speech-1",
        speech_packet_sha256="a" * 64,
        task_contract="Use only the original human speech.",
        reports=reports,
    )
    resolution = sweep.parse_resolve_response(
        '[{"name":"tool00","arguments":{"target":"Alice"}}]',
        reports=reports,
    )

    documents = build_trace_documents(
        scan_contact_ids=tuple(f"g6-scan-family-{index:02d}" for index in range(28)),
        resolve_context=context,
        reports=reports,
        resolution=resolution,
        final_response_text='[{"name":"tool00","arguments":{"target":"Alice"}}]',
    )

    assert tuple(documents) == ("OBS", "ORG", "SUPPLY", "USE")
    assert set(documents["OBS"]) == {"speech_packet_id", "speech_packet_sha256"}
    assert len(documents["ORG"]["scan_reports"]) == FAMILY_COUNT
    assert documents["SUPPLY"]["selected_contract_ids"] == ["contract-00"]
    assert documents["USE"]["resolution_valid"] is True
    assert "selected_contract_ids" not in documents["ORG"]
    assert "scan_reports" not in documents["USE"]


def test_protocol_rejects_wrong_family_count_duplicate_registry_and_unknown_canonicalizer() -> (
    None
):
    contracts = tuple(_contract(index) for index in range(FAMILY_COUNT))
    with pytest.raises(G6FamilySweepError, match="exactly 28"):
        G6FamilySweep(
            family_bundles=tuple(
                FamilyBundle(contract.family_tag, (contract,))
                for contract in contracts[:-1]
            ),
            max_final_calls=1,
        )

    duplicate = ToolContract(
        contract_id="duplicate-id",
        family_tag="family-01",
        tool_name="tool00",
        arguments=(ArgumentSpec("target", required=True),),
        content="Duplicate registered name.",
        legal_key_skeletons=(("target",),),
    )
    bundles = [FamilyBundle(contract.family_tag, (contract,)) for contract in contracts]
    bundles[1] = FamilyBundle("family-01", (duplicate,))
    with pytest.raises(G6FamilySweepError, match="registered tool names"):
        G6FamilySweep(family_bundles=tuple(bundles), max_final_calls=1)

    with pytest.raises(G6FamilySweepError, match="canonicalizer"):
        G6FamilySweep(
            family_bundles=tuple(
                FamilyBundle(contract.family_tag, (contract,)) for contract in contracts
            ),
            max_final_calls=1,
        )


def test_contract_and_family_setup_rejects_malformed_closed_surfaces() -> None:
    with pytest.raises(G6FamilySweepError):
        ArgumentSpec("", required=True).validate()
    with pytest.raises(G6FamilySweepError, match="boolean"):
        ArgumentSpec("key", required=1).validate()  # type: ignore[arg-type]
    with pytest.raises(G6FamilySweepError, match="duplicates"):
        ArgumentSpec("key", required=True, canonicalizer_ids=("x", "x")).validate()

    contract = _contract(0)
    with pytest.raises(G6FamilySweepError, match="must be a tuple"):
        replace(contract, arguments=[]).validate()  # type: ignore[arg-type]
    with pytest.raises(G6FamilySweepError, match="argument keys"):
        replace(
            contract,
            arguments=(ArgumentSpec("x", True), ArgumentSpec("x", False)),
        ).validate()
    with pytest.raises(G6FamilySweepError, match="legal key skeleton"):
        replace(contract, legal_key_skeletons=(("target", "unknown"),)).validate()
    with pytest.raises(G6FamilySweepError, match="ToolContract"):
        FamilyBundle("family-00", (object(),)).validate()  # type: ignore[arg-type]
    with pytest.raises(G6FamilySweepError, match="belong"):
        FamilyBundle("other-family", (contract,)).validate()
    with pytest.raises(G6FamilySweepError, match="identities"):
        FamilyBundle("family-00", (contract, contract)).validate()
    with pytest.raises(G6FamilySweepError, match="byte cap"):
        FamilyBundle(
            "family-00",
            (replace(contract, content="x" * 12_289),),
        ).validate()


def test_protocol_setup_and_context_identity_are_fail_closed() -> None:
    contracts = tuple(_contract(index) for index in range(FAMILY_COUNT))
    bundles = tuple(
        FamilyBundle(contract.family_tag, (contract,)) for contract in contracts
    )
    duplicated_tag = list(bundles)
    duplicated_tag[1] = FamilyBundle(
        "family-00", (replace(contracts[1], family_tag="family-00"),)
    )
    with pytest.raises(G6FamilySweepError, match="family tags"):
        G6FamilySweep(family_bundles=duplicated_tag, max_final_calls=1)
    duplicated_id = list(bundles)
    duplicated_id[1] = FamilyBundle(
        "family-01", (replace(contracts[1], contract_id="contract-00"),)
    )
    with pytest.raises(G6FamilySweepError, match="contract ids"):
        G6FamilySweep(family_bundles=duplicated_id, max_final_calls=1)
    with pytest.raises(G6FamilySweepError, match="positive integer"):
        G6FamilySweep(family_bundles=bundles, max_final_calls=True)
    with pytest.raises(G6FamilySweepError, match="map ASCII"):
        G6FamilySweep(
            family_bundles=bundles,
            max_final_calls=1,
            canonicalizers={"to-int": object()},  # type: ignore[dict-item]
        )

    sweep = _sweep()
    with pytest.raises(G6FamilySweepError, match="SHA-256"):
        sweep.build_scan_contexts(
            speech_packet_id="speech", speech_packet_sha256="bad", task_contract="task"
        )
    with pytest.raises(G6FamilySweepError, match="ASCII"):
        sweep.build_scan_contexts(
            speech_packet_id="speech",
            speech_packet_sha256="a" * 64,
            task_contract="t\N{LATIN SMALL LETTER A WITH CIRCUMFLEX}sk",
        )


@pytest.mark.parametrize(
    "document",
    [
        {
            "applicable": False,
            "candidates": [],
            "correction_evidence": [],
            "turn_evidence": [],
            "role_evidence": [],
            "ordering_evidence": [],
            "gold": 1,
        },
        {
            "applicable": "yes",
            "candidates": [],
            "correction_evidence": [],
            "turn_evidence": [],
            "role_evidence": [],
            "ordering_evidence": [],
        },
        {
            "applicable": True,
            "candidates": [],
            "correction_evidence": [],
            "turn_evidence": [],
            "role_evidence": [],
            "ordering_evidence": [],
        },
        {
            "applicable": False,
            "candidates": "none",
            "correction_evidence": [],
            "turn_evidence": [],
            "role_evidence": [],
            "ordering_evidence": [],
        },
        {
            "applicable": True,
            "candidates": [{}],
            "correction_evidence": [],
            "turn_evidence": [],
            "role_evidence": [],
            "ordering_evidence": [],
        },
        {
            "applicable": False,
            "candidates": [],
            "correction_evidence": [1],
            "turn_evidence": [],
            "role_evidence": [],
            "ordering_evidence": [],
        },
    ],
)
def test_more_malformed_scan_schema_paths_are_family_local_empty(
    document: object,
) -> None:
    report = _sweep().parse_scan_response(
        "family-00", json.dumps(document, separators=(",", ":"))
    )
    assert report.valid is False
    assert report.candidates == ()


def test_candidate_binding_and_count_limits_are_strict() -> None:
    sweep = _sweep()
    valid = json.loads(_scan_json(0))

    duplicate_candidates = dict(valid)
    duplicate_candidates["candidates"] = valid["candidates"] * 2
    assert (
        sweep.parse_scan_response("family-00", json.dumps(duplicate_candidates)).valid
        is False
    )

    too_many = dict(valid)
    too_many["candidates"] = valid["candidates"] * 9
    assert sweep.parse_scan_response("family-00", json.dumps(too_many)).valid is False

    binding_not_list = json.loads(_scan_json(0))
    binding_not_list["candidates"][0]["argument_bindings"] = "bad"
    assert (
        sweep.parse_scan_response("family-00", json.dumps(binding_not_list)).valid
        is False
    )

    malformed_binding = json.loads(_scan_json(0))
    malformed_binding["candidates"][0]["argument_bindings"] = [{}]
    assert (
        sweep.parse_scan_response("family-00", json.dumps(malformed_binding)).valid
        is False
    )

    missing_required = json.loads(_scan_json(0))
    missing_required["candidates"][0]["argument_bindings"] = []
    assert (
        sweep.parse_scan_response("family-00", json.dumps(missing_required)).valid
        is False
    )

    unbound_span = json.loads(_scan_json(0))
    unbound_span["candidates"][0]["argument_bindings"][0]["speech_span"] = "Bob"
    assert (
        sweep.parse_scan_response("family-00", json.dumps(unbound_span)).valid is False
    )

    copied_default = json.loads(_scan_json(0))
    copied_default["candidates"][0]["argument_bindings"][0]["value"] = "Bob"
    assert (
        sweep.parse_scan_response("family-00", json.dumps(copied_default)).valid
        is False
    )

    with pytest.raises(G6FamilySweepError, match="outside"):
        sweep.parse_scan_response("unknown", "{}")


def test_resolver_rejects_fabricated_report_and_malformed_argument_surfaces() -> None:
    sweep = _sweep()
    reports = sweep.parse_scan_responses(_responses(nominated=(0,)))
    fabricated = list(reports)
    fabricated[0] = replace(reports[0], canonical_json="{}")
    with pytest.raises(G6FamilySweepError, match="validated"):
        sweep.build_resolve_context(
            speech_packet_id="speech",
            speech_packet_sha256="a" * 64,
            task_contract="task",
            reports=fabricated,
        )

    for raw in (
        "{}",
        '[{"name":1,"arguments":{}}]',
        '[{"name":"tool00","arguments":[]}]',
        '[{"name":"tool00","arguments":{"target":[]}}]',
        '[{"name":"tool00","arguments":{"count":3}}]',
    ):
        assert sweep.parse_resolve_response(raw, reports=reports).valid is False


def test_prompt_and_trace_seams_reject_nonrequests_and_mismatched_state() -> None:
    with pytest.raises(G6FamilySweepError, match="rendered_request"):
        measure_prompt_envelope(
            contact_id="contact",
            rendered_request="",
            token_counter=len,
            speech_feature_tokens=0,
            special_token_reserve=0,
            completion_token_ceiling=0,
        )
    with pytest.raises(G6FamilySweepError, match="nonnegative"):
        measure_prompt_envelope(
            contact_id="contact",
            rendered_request="request",
            token_counter=lambda _: True,
            speech_feature_tokens=0,
            special_token_reserve=0,
            completion_token_ceiling=0,
        )

    sweep = _sweep()
    reports = sweep.parse_scan_responses(_responses())
    context = sweep.build_resolve_context(
        speech_packet_id="speech",
        speech_packet_sha256="a" * 64,
        task_contract="task",
        reports=reports,
    )
    resolution = sweep.parse_resolve_response("[]", reports=reports)
    with pytest.raises(G6FamilySweepError, match="28 SCAN"):
        build_trace_documents(
            scan_contact_ids=("one",),
            resolve_context=context,
            reports=reports,
            resolution=resolution,
            final_response_text="[]",
        )
    with pytest.raises(G6FamilySweepError, match="disagree"):
        build_trace_documents(
            scan_contact_ids=tuple(f"scan-{index}" for index in range(28)),
            resolve_context=context,
            reports=reports[:-1]
            + (FamilyScanReport(**{**reports[-1].__dict__, "canonical_json": "{}"}),),
            resolution=resolution,
            final_response_text="[]",
        )
