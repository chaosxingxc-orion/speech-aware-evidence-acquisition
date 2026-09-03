from __future__ import annotations

import hashlib

import pytest

from speech_aware_evidence_acquisition.rails.a2t_select_fill_factorial import (
    DEFAULT_FILL,
    FACTORIAL_CELLS,
    INTERFACE_SELECT,
    ROUTING_SELECT,
    SPARSE_FILL,
    FactorialBindingError,
    bind_factorial_predecessors,
)
from speech_aware_evidence_acquisition.rails.a2t_stage_state import (
    SelectOccurrence,
    build_select_stage_envelope,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _state(sample_id: str, select_ground: str):
    ground_sha256 = _sha(f"ground:{select_ground}:{sample_id}")
    return build_select_stage_envelope(
        sample_identity_sha256=_sha(sample_id),
        split_identity_sha256=_sha("fresh-factorial-split"),
        speech_packet_sha256=_sha(f"speech:{sample_id}"),
        source_query_state_sha256=_sha(f"query:{select_ground}:{sample_id}"),
        source_response_sha256=_sha(f"response:{select_ground}:{sample_id}"),
        observation_state_sha256=_sha(f"obs:{sample_id}"),
        observation_source_response_sha256=_sha(f"obs-response:{sample_id}"),
        source_request_body_sha256=_sha(f"request:{select_ground}:{sample_id}"),
        candidate_tool_names=("setTimer", "setAlarm"),
        ground_sha256=ground_sha256,
        response_schema_sha256=_sha("select-schema"),
        predecessor_envelope_sha256=None,
        occurrences=(SelectOccurrence("occurrence-01", "setTimer"),),
    )


def test_factorial_cells_are_complete_unique_and_prospectively_ordered() -> None:
    assert [cell.cell_id for cell in FACTORIAL_CELLS] == [
        "Y00",
        "Y01",
        "Y10",
        "Y11",
    ]
    assert {
        (cell.select_ground, cell.fill_policy) for cell in FACTORIAL_CELLS
    } == {
        (ROUTING_SELECT, DEFAULT_FILL),
        (ROUTING_SELECT, SPARSE_FILL),
        (INTERFACE_SELECT, DEFAULT_FILL),
        (INTERFACE_SELECT, SPARSE_FILL),
    }
    assert len({cell.execution_id for cell in FACTORIAL_CELLS}) == 4
    assert len({cell.manifest_role for cell in FACTORIAL_CELLS}) == 4
    assert all(cell.execution_id.isascii() for cell in FACTORIAL_CELLS)


def test_fill_cells_share_each_selector_state_map_byte_exactly() -> None:
    sample_ids = ("tier1_direct:000001", "tier2_parametric:000002")
    states = {
        select_ground: {
            sample_id: _state(sample_id, select_ground)
            for sample_id in sample_ids
        }
        for select_ground in (ROUTING_SELECT, INTERFACE_SELECT)
    }
    expected_ground = {
        select_ground: {
            sample_id: state.ground_sha256
            for sample_id, state in arm.items()
        }
        for select_ground, arm in states.items()
    }

    bindings = bind_factorial_predecessors(
        states,
        sample_ids=sample_ids,
        expected_ground_sha256=expected_ground,
        split_identity_sha256=_sha("fresh-factorial-split"),
        expected_row_count=2,
    )
    by_cell = {binding.cell_id: binding for binding in bindings}

    assert (
        by_cell["Y00"].selector_state_map_sha256
        == by_cell["Y01"].selector_state_map_sha256
    )
    assert (
        by_cell["Y10"].selector_state_map_sha256
        == by_cell["Y11"].selector_state_map_sha256
    )
    assert (
        by_cell["Y00"].selector_state_map_sha256
        != by_cell["Y10"].selector_state_map_sha256
    )
    assert by_cell["Y00"].selector_envelope_sha256s == tuple(
        states[ROUTING_SELECT][sample_id].envelope_sha256
        for sample_id in sample_ids
    )


def test_factorial_binding_rejects_cross_condition_or_incomplete_state() -> None:
    sample_ids = ("tier1_direct:000001", "tier2_parametric:000002")
    states = {
        select_ground: {
            sample_id: _state(sample_id, select_ground)
            for sample_id in sample_ids
        }
        for select_ground in (ROUTING_SELECT, INTERFACE_SELECT)
    }
    expected_ground = {
        select_ground: {
            sample_id: state.ground_sha256
            for sample_id, state in arm.items()
        }
        for select_ground, arm in states.items()
    }
    swapped = {
        **states,
        INTERFACE_SELECT: {
            **states[INTERFACE_SELECT],
            sample_ids[0]: states[ROUTING_SELECT][sample_ids[0]],
        },
    }

    with pytest.raises(FactorialBindingError, match="ground"):
        bind_factorial_predecessors(
            swapped,
            sample_ids=sample_ids,
            expected_ground_sha256=expected_ground,
            split_identity_sha256=_sha("fresh-factorial-split"),
            expected_row_count=2,
        )

    incomplete = {
        **states,
        ROUTING_SELECT: {sample_ids[0]: states[ROUTING_SELECT][sample_ids[0]]},
    }
    with pytest.raises(FactorialBindingError, match="cover"):
        bind_factorial_predecessors(
            incomplete,
            sample_ids=sample_ids,
            expected_ground_sha256=expected_ground,
            split_identity_sha256=_sha("fresh-factorial-split"),
            expected_row_count=2,
        )
