"""Pure tests for the G8 action-support branch core."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.probes.a2t_g7_example_ground import (
    ExecutionSheet,
    FamilyAssessment,
    G7ExampleGround,
    NormalizedAssessment,
    Observation,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_g8_action_support import (
    G8ActionSupportCore,
    G8ActionSupportError,
    MAX_BINDING_RESPONSE_UTF8_BYTES,
    MAX_SELECTION_CALLS,
    MAX_SELECTION_RESPONSE_UTF8_BYTES,
    build_g8_trace_documents,
    measure_rendered_prompt,
)


def _bundles() -> tuple[SimpleNamespace, ...]:
    bundles: list[SimpleNamespace] = []
    for family_index in range(28):
        tools = tuple(
            SimpleNamespace(
                tool_name=f"tool_{family_index:02d}_{tool_index:02d}",
                operation=f"Perform operation {family_index} {tool_index}.",
                types=(
                    (("enabled", "Boolean"), ("level", "Int"))
                    if tool_index == 0
                    else (("value", "SecretType"),)
                ),
                legal_key_skeletons=(
                    ((), ("enabled", "level"))
                    if tool_index == 0
                    else ((), ("value",))
                ),
            )
            for tool_index in range(6 if family_index < 12 else 5)
        )
        bundles.append(
            SimpleNamespace(
                family_tag=f"family-{family_index:02d}",
                family_label=f"Family objective {family_index}",
                tools=tools,
                tool_names=tuple(tool.tool_name for tool in tools),
            )
        )
    assert sum(len(bundle.tools) for bundle in bundles) == 152
    return tuple(bundles)


def _sheet(core: G8ActionSupportCore) -> ExecutionSheet:
    rows: list[NormalizedAssessment] = []
    lines: list[str] = []
    for index, (family_tag, tool_name) in enumerate(core.registry_order):
        status = "support" if index in {0, 7, 151} else "uncertain"
        evidence = ("o1",) if status == "support" else ()
        rows.append(NormalizedAssessment(family_tag, tool_name, status, evidence))
        lines.append(f"sealed-line-{index}:{tool_name}:{status}")
    return ExecutionSheet(tuple(rows), "\n".join(lines))


def test_normalized_sheet_delegates_the_frozen_g7_family_assessment_contract() -> None:
    bundles = _bundles()
    core = G8ActionSupportCore(bundles)
    parsed = tuple(
        FamilyAssessment(
            family_tag=bundle.family_tag,
            strict_valid=False,
            tolerant_valid=True,
            records=(),
            invalid_record_count=0,
            canonical_json='{"assessments":[]}',
        )
        for bundle in bundles
    )

    result = core.build_normalized_sheet(parsed)

    assert result == G7ExampleGround(bundles).build_execution_sheet(parsed)


def test_support_only_sheet_retains_exact_support_lines_in_registry_order() -> None:
    core = G8ActionSupportCore(_bundles())
    source = _sheet(core)

    result = core.build_support_only_sheet(source)

    assert [row.tool_name for row in result.assessments] == [
        "tool_00_00",
        "tool_01_01",
        "tool_27_04",
    ]
    assert result.text.splitlines() == [
        "sealed-line-0:tool_00_00:support",
        "sealed-line-7:tool_01_01:support",
        "sealed-line-151:tool_27_04:support",
    ]


def test_support_only_sheet_fails_closed_on_noncanonical_source_order() -> None:
    core = G8ActionSupportCore(_bundles())
    source = _sheet(core)
    swapped = ExecutionSheet(
        (source.assessments[1], source.assessments[0], *source.assessments[2:]),
        source.text,
    )

    with pytest.raises(G8ActionSupportError, match="registry order"):
        core.build_support_only_sheet(swapped)


def test_empty_support_is_explicit_and_never_falls_back() -> None:
    core = G8ActionSupportCore(_bundles())
    source = _sheet(core)
    empty_source = ExecutionSheet(
        tuple(
            NormalizedAssessment(row.family_tag, row.tool_name, "uncertain", ())
            for row in source.assessments
        ),
        "\n".join(f"uncertain-{index}" for index in range(152)),
    )

    support = core.build_support_only_sheet(empty_source)
    selection = core.parse_selection("[]")
    binding_context = core.build_binding_context(Observation("Request.", True), selection)
    bindings = core.parse_bindings("[]", selection)
    resolve = core.build_resolve_context(Observation("Request.", True), selection, bindings)

    assert support == ExecutionSheet((), "")
    assert selection.tool_names == ()
    assert binding_context.selected_contracts == ()
    assert bindings.calls == ()
    assert resolve.calls == ()
    assert "empty" in binding_context.instruction.casefold()
    assert "empty" in resolve.instruction.casefold()


def test_selection_context_has_speech_observation_objectives_operations_and_full_status() -> None:
    core = G8ActionSupportCore(_bundles())
    observation = Observation("The speaker requests two device actions.", True)

    context = core.build_selection_context(observation, _sheet(core))
    rendered = context.render_prompt()

    assert context.stage == "DECOMPOSED_SELECT"
    assert context.uses_audio is True
    assert context.observation == observation.text
    assert len(context.status_surface) == 152
    assert "Family objective 0" in rendered
    assert "Perform operation 0 0." in rendered
    assert "tool_27_04" in rendered
    assert "support" in rendered and "uncertain" in rendered
    assert "SecretType" not in rendered
    assert "legal_key_skeletons" not in rendered
    assert "types:" not in rendered


@pytest.mark.parametrize(
    "raw",
    [
        '["unknown"]',
        '["tool_00_00", {"name":"tool_00_01"}]',
        '{"tools":["tool_00_00"]}',
        '["tool_00_00"] trailing prose',
        '```json\n["tool_00_00"]\n```',
    ],
)
def test_selection_parser_rejects_unknown_names_arguments_wrappers_and_prose(raw: str) -> None:
    core = G8ActionSupportCore(_bundles())

    with pytest.raises(G8ActionSupportError, match="selection"):
        core.parse_selection(raw)


def test_selection_parser_preserves_exact_order_and_repeated_calls() -> None:
    core = G8ActionSupportCore(_bundles())

    result = core.parse_selection(
        '["tool_01_01","tool_00_00","tool_01_01"]'
    )

    assert result.tool_names == ("tool_01_01", "tool_00_00", "tool_01_01")
    assert result.canonical_json == '["tool_01_01","tool_00_00","tool_01_01"]'


def test_selection_parser_refuses_fanout_and_utf8_response_overflow() -> None:
    core = G8ActionSupportCore(_bundles())
    too_many = json.dumps(["tool_00_00"] * (MAX_SELECTION_CALLS + 1))

    with pytest.raises(G8ActionSupportError, match="call limit"):
        core.parse_selection(too_many)
    with pytest.raises(G8ActionSupportError, match="UTF-8 byte limit"):
        core.parse_selection(" " * (MAX_SELECTION_RESPONSE_UTF8_BYTES + 1))


def test_binding_context_contains_only_selected_legal_contracts() -> None:
    core = G8ActionSupportCore(_bundles())
    selection = core.parse_selection('["tool_00_00","tool_01_01"]')

    context = core.build_binding_context(Observation("Request.", True), selection)
    rendered = context.render_prompt()

    assert context.stage == "DECOMPOSED_BIND"
    assert context.uses_audio is True
    assert [item.tool_name for item in context.selected_contracts] == [
        "tool_00_00",
        "tool_01_01",
    ]
    assert "enabled:Boolean" in rendered
    assert "level:Int" in rendered
    assert "tool_00_01" not in rendered
    assert "Perform operation" not in rendered


def test_binding_parser_preserves_selected_tools_and_unmodified_typed_values() -> None:
    core = G8ActionSupportCore(_bundles())
    selection = core.parse_selection('["tool_00_00","tool_01_01","tool_00_00"]')
    raw = json.dumps(
        [
            {"name": "tool_00_00", "arguments": {"enabled": True, "level": 2}},
            {"name": "tool_01_01", "arguments": {"value": "two"}},
            {"name": "tool_00_00", "arguments": {}},
        ],
        separators=(",", ":"),
    )

    result = core.parse_bindings(raw, selection)

    assert [call.tool_name for call in result.calls] == list(selection.tool_names)
    assert result.calls[0].arguments == {"enabled": True, "level": 2}
    assert result.calls[1].arguments == {"value": "two"}
    assert result.calls[2].arguments == {}
    assert result.canonical_json == raw


def test_binding_parser_refuses_utf8_response_overflow_before_json_parsing() -> None:
    core = G8ActionSupportCore(_bundles())
    selection = core.parse_selection('["tool_00_00"]')

    with pytest.raises(G8ActionSupportError, match="UTF-8 byte limit"):
        core.parse_bindings("\u00e9" * (MAX_BINDING_RESPONSE_UTF8_BYTES // 2 + 1), selection)


@pytest.mark.parametrize(
    "raw,match",
    [
        ('[]', "one argument object"),
        ('[{"name":"tool_00_01","arguments":{}}]', "one argument object"),
        (
            '[{"name":"tool_00_00","arguments":{}},'
            '{"name":"tool_01_01","arguments":{"value":"x"}}]',
            "one argument object",
        ),
        ('[{"name":"tool_00_00","arguments":{},"extra":1}]', "exact keys"),
        ('[{"name":"tool_00_00","arguments":{"enabled":"true","level":2}}]', "type"),
        ('[{"name":"tool_00_00","arguments":{"enabled":true}}]', "skeleton"),
        ('```json\n[{"name":"tool_00_00","arguments":{}}]\n```', "binding"),
    ],
)
def test_binding_parser_rejects_count_order_schema_type_and_prose_drift(
    raw: str, match: str
) -> None:
    core = G8ActionSupportCore(_bundles())
    selection = core.parse_selection('["tool_00_00"]')

    with pytest.raises(G8ActionSupportError, match=match):
        core.parse_bindings(raw, selection)


def test_final_resolve_uses_only_sealed_selection_and_bindings() -> None:
    core = G8ActionSupportCore(_bundles())
    selection = core.parse_selection('["tool_00_00"]')
    bindings = core.parse_bindings(
        '[{"name":"tool_00_00","arguments":{"enabled":true,"level":2}}]',
        selection,
    )

    context = core.build_resolve_context(Observation("Request.", True), selection, bindings)
    rendered = context.render_prompt()

    assert context.stage == "DECOMPOSED_RESOLVE"
    assert context.uses_audio is True
    assert context.calls == bindings.calls
    assert "tool_00_00" in rendered
    assert '"enabled":true' in rendered
    assert "tool_00_01" not in rendered
    assert "official tool-call JSON array" in context.instruction
    assert "frozen core" in context.instruction
    assert "repair" in context.instruction


def test_measurement_counts_the_actual_rendered_prompt_and_all_reserves() -> None:
    core = G8ActionSupportCore(_bundles())
    context = core.build_selection_context(Observation("Request.", True), _sheet(core))
    seen: list[str] = []

    fit = measure_rendered_prompt(
        context,
        token_counter=lambda rendered: seen.append(rendered) or 20_000,
        completion_tokens=1_000,
        speech_feature_tokens=2_000,
        special_token_reserve=1_576,
    )

    assert seen == [context.render_prompt()]
    assert fit.prompt_tokens == 23_576
    assert fit.total_tokens == 24_576
    assert fit.remaining_tokens == 8_192
    with pytest.raises(G8ActionSupportError, match="24,576"):
        measure_rendered_prompt(
            context,
            token_counter=lambda _rendered: 20_001,
            completion_tokens=1_000,
            speech_feature_tokens=2_000,
            special_token_reserve=1_576,
        )


def test_trace_documents_keep_obs_org_supply_and_use_separate() -> None:
    core = G8ActionSupportCore(_bundles())
    observation = Observation("Request.", True)
    source = _sheet(core)
    support = core.build_support_only_sheet(source)
    selection = core.parse_selection('["tool_00_00"]')
    bindings = core.parse_bindings(
        '[{"name":"tool_00_00","arguments":{"enabled":true,"level":2}}]',
        selection,
    )

    trace = build_g8_trace_documents(
        sample_id="sample-a",
        observation=observation,
        normalized_sheet=source,
        support_only_sheet=support,
        selection=selection,
        bindings=bindings,
        final_response_text='[{"name":"tool_00_00","arguments":{}}]',
    )

    assert set(trace) == {"obs_state", "org_state", "supply_state", "use_state"}
    assert set(trace["obs_state"]) == {"sample_id", "valid", "text"}
    assert trace["org_state"]["normalized_tool_count"] == 152
    assert trace["supply_state"]["support_tool_count"] == 3
    assert "selected_tool_names" not in trace["supply_state"]
    assert trace["use_state"]["selected_tool_names"] == ["tool_00_00"]
    assert trace["use_state"]["binding_count"] == 1
    assert "final_response_text" in trace["use_state"]
    assert "final_response_text" not in trace["org_state"]
    assert "final_response_text" not in trace["supply_state"]
