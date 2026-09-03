"""Pure tests for the G7 exhaustive construction-example loop core."""

from __future__ import annotations

import json
from types import SimpleNamespace
import threading
import time

import pytest

from speech_aware_evidence_acquisition.rails.probes.a2t_g7_example_ground import (
    ASSESSMENT_UNCERTAIN,
    G7ExampleGround,
    G7ExampleGroundError,
    MAX_OBSERVATION_ASCII_BYTES,
    execute_g7_workflows,
    build_trace_documents,
    parse_family_assessment,
    parse_observation,
)


def _bundles():
    rows = []
    for family_index in range(28):
        tools = tuple(
            SimpleNamespace(
                tool_name=f"tool_{family_index:02d}_{tool_index:02d}",
                operation=f"Operation {family_index} {tool_index}.",
                types=(("value", "String"),),
                legal_key_skeletons=(("value",),),
                patterns=(
                    SimpleNamespace(
                        tier="tier1_direct",
                        text="Example with {value}",
                        placeholders=("value",),
                    ),
                ),
            )
            for tool_index in range(6 if family_index < 12 else 5)
        )
        rows.append(
            SimpleNamespace(
                family_tag=f"family-{family_index:02d}",
                family_label=f"Family {family_index}",
                tools=tools,
                tool_names=tuple(tool.tool_name for tool in tools),
                text=f"Construction examples for family {family_index}.",
            )
        )
    assert sum(len(row.tools) for row in rows) == 152
    return tuple(rows)


def test_observation_is_bounded_plain_english_and_excludes_tool_names() -> None:
    names = ("tool_00_00", "tool_00_01")

    valid = parse_observation("The speaker asks to raise the cabin volume.", names)
    forbidden = parse_observation("The speaker asks for tool_00_00.", names)
    nonascii = parse_observation("The speaker says caf\u00e9.", names)

    assert valid.valid is True
    assert forbidden.valid is nonascii.valid is False
    assert forbidden.text == nonascii.text == "No reliable observation was available."


def test_observation_cap_is_1024_ascii_bytes_and_fails_closed_above_it() -> None:
    assert MAX_OBSERVATION_ASCII_BYTES == 1_024
    assert parse_observation("A" * 1_024, ()).valid is True
    assert parse_observation("A" * 1_025, ()).valid is False


def test_tolerant_parser_removes_one_exact_fence_and_ignores_unknown_keys() -> None:
    raw = """```json
{"assessments":[{"tool_name":"tool_00_00","status":"support","evidence":["o1"],"extra":1}],"unknown":true}
```"""

    result = parse_family_assessment(
        raw,
        family_tag="family-00",
        family_tool_names=("tool_00_00", "tool_00_01"),
    )

    assert result.tolerant_valid is True
    assert result.strict_valid is False
    assert result.records[0].tool_name == "tool_00_00"
    assert result.records[0].status == "support"


def test_tolerant_parser_normalizes_empty_object_and_retains_valid_siblings() -> None:
    empty = parse_family_assessment(
        "{}", family_tag="family-00", family_tool_names=("tool_00_00",)
    )
    mixed = parse_family_assessment(
        json.dumps(
            {
                "assessments": [
                    {"tool_name": "tool_00_00", "status": "contradict", "evidence": []},
                    {"tool_name": "invented", "status": "support", "evidence": []},
                    {"tool_name": "tool_00_01", "status": "maybe", "evidence": []},
                ]
            }
        ),
        family_tag="family-00",
        family_tool_names=("tool_00_00", "tool_00_01"),
    )

    assert empty.tolerant_valid is True
    assert empty.records == ()
    assert mixed.tolerant_valid is True
    assert [(row.tool_name, row.status) for row in mixed.records] == [
        ("tool_00_00", "contradict")
    ]
    assert mixed.invalid_record_count == 2


def test_no_alias_cross_family_or_value_synthesis_is_possible() -> None:
    result = parse_family_assessment(
        '{"assessments":[{"tool_name":"Tool_00_00","status":"support",'
        '"evidence":["value not copied"]},{"tool_name":"tool_01_00",'
        '"status":"support","evidence":[]}]}',
        family_tag="family-00",
        family_tool_names=("tool_00_00",),
    )

    assert result.records == ()
    assert result.invalid_record_count == 2
    assert "value not copied" not in result.canonical_json


def test_evidence_ids_are_bounded_without_truncation() -> None:
    result = parse_family_assessment(
        '{"assessments":[{"tool_name":"tool_00_00","status":"support",'
        '"evidence":["o3"]}]}',
        family_tag="family-00",
        family_tool_names=("tool_00_00",),
    )

    assert result.records == ()
    assert result.invalid_record_count == 1


def test_all_152_tools_start_uncertain_and_survive_every_assessment() -> None:
    core = G7ExampleGround(_bundles())
    observation = parse_observation("The speaker requests a device action.", core.tool_names)
    contexts = core.build_evidence_contexts(observation)
    parsed = tuple(
        parse_family_assessment(
            "{}", family_tag=context.family_tag, family_tool_names=context.tool_names
        )
        for context in contexts
    )
    sheet = core.build_execution_sheet(parsed)

    assert len(contexts) == 28
    assert all(context.uses_audio is True for context in contexts)
    assert all("assessments" in context.instruction for context in contexts)
    assert all("tool_name, status, evidence" in context.instruction for context in contexts)
    assert all("support, contradict, or uncertain" in context.instruction for context in contexts)
    assert all("available OBS ID o1" in context.instruction for context in contexts)
    assert len(sheet.assessments) == 152
    assert {row.status for row in sheet.assessments} == {ASSESSMENT_UNCERTAIN}
    assert {row.tool_name for row in sheet.assessments} == set(core.tool_names)


def test_resolve_contains_observation_all_tools_and_all_assessments() -> None:
    core = G7ExampleGround(_bundles())
    observation = parse_observation("The speaker requests a device action.", core.tool_names)
    parsed = tuple(
        parse_family_assessment(
            "{}", family_tag=context.family_tag, family_tool_names=context.tool_names
        )
        for context in core.build_evidence_contexts(observation)
    )

    resolve = core.build_resolve_context(observation, parsed)

    assert resolve.stage == "RESOLVE"
    assert resolve.uses_audio is True
    assert len(resolve.assessments) == 152
    assert len(resolve.tool_names) == 152
    assert "No cumulative raw history" in resolve.instruction
    assert "JSON array" in resolve.instruction
    assert "exactly the keys name and arguments" in resolve.instruction
    assert "S=support, C=contradict, U=uncertain" in resolve.instruction
    assert "C and U never remove a tool" in resolve.instruction
    assert "Bind values only from the original audio or OBS" in resolve.instruction
    assert "Never copy a construction example" in resolve.instruction
    assert "types:value:String" in resolve.execution_sheet


def test_prompt_measurement_refuses_above_24576_including_completion() -> None:
    core = G7ExampleGround(_bundles())

    fit = core.measure_prompt(
        contact_id="g7-resolve", text="x" * 23_552, token_counter=len, completion_tokens=1024
    )
    with pytest.raises(G7ExampleGroundError, match="8192"):
        core.measure_prompt(
            contact_id="g7-resolve",
            text="x" * 23_553,
            token_counter=len,
            completion_tokens=1024,
        )

    assert fit.total_tokens == 24_576
    assert fit.remaining_tokens == 8_192


def test_executor_runs_30_contacts_per_row_with_two_sample_workers() -> None:
    bundles = _bundles()
    active = 0
    peak = 0
    lock = threading.Lock()
    seen: dict[str, list[str]] = {"a": [], "b": []}

    def invoke(sample_id: str, stage: str, _context: object) -> str:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            seen[sample_id].append(stage)
        time.sleep(0.001)
        with lock:
            active -= 1
        if stage == "OBS":
            return "The speaker requests a device action."
        if stage == "EVIDENCE":
            return "{}"
        return '{"calls":[]}'

    results = execute_g7_workflows(
        sample_ids=("a", "b"), bundles=bundles, invoke_contact=invoke
    )

    assert peak == 2
    assert len(results) == 2
    assert all(stages == ["OBS", *(["EVIDENCE"] * 28), "RESOLVE"] for stages in seen.values())
    assert sum(len(stages) for stages in seen.values()) == 60


def test_trace_documents_keep_phase_boundaries_and_both_validities() -> None:
    def invoke(_sample_id: str, stage: str, _context: object) -> str:
        return (
            "The speaker requests a device action."
            if stage == "OBS"
            else "{}"
            if stage == "EVIDENCE"
            else '{"calls":[]}'
        )

    result = execute_g7_workflows(
        sample_ids=("a",), bundles=_bundles(), invoke_contact=invoke
    )[0]
    trace = build_trace_documents(result)

    assert set(trace) == {"obs_state", "org_assessments", "supply_sheet", "use_final"}
    assert len(trace["org_assessments"]["families"]) == 28
    assert trace["org_assessments"]["families"][0]["strict_valid"] is False
    assert trace["org_assessments"]["families"][0]["tolerant_valid"] is True
    assert trace["supply_sheet"]["tool_count"] == 152
    assert trace["use_final"]["response_text"] == '{"calls":[]}'
