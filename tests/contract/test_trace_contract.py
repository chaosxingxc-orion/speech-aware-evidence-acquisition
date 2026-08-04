"""Contract 4: OBS/ORG/SUPPLY/USE separation; touch records serialize and hash."""

import pytest

from speech_aware_evidence_acquisition.contracts import (
    BoundaryViolation,
    TraceContractError,
    TraceRecord,
)


def test_research_axis_namespaces_are_disjoint():
    TraceRecord("OBS", "r1", {"obs_segment": "0001", "obs_pass": 2}).validate()
    TraceRecord("ORG", "r2", {"org_granularity": "entity", "org_index_revision": "abc"}).validate()
    TraceRecord("SUPPLY", "r3", {"supply_query": "acme revenue", "supply_source": "web"}).validate()
    TraceRecord("USE", "r4", {"use_action": "admit", "use_stop": False}).validate()

    with pytest.raises(TraceContractError):
        TraceRecord("OBS", "r5", {"supply_query": "smuggled"}).validate()
    with pytest.raises(TraceContractError):
        TraceRecord("SUPPLY", "r6", {"org_index_revision": "smuggled"}).validate()
    with pytest.raises(TraceContractError):
        TraceRecord("USE", "r7", {"obs_segment": "smuggled"}).validate()
    with pytest.raises(TraceContractError):
        TraceRecord("OBS", "r8", {"unprefixed": 1}).validate()


@pytest.mark.parametrize("channel", ["MODEL_REQUEST", "MODEL_RESPONSE", "TOOL", "COST"])
def test_all_touch_channels_serialize_deterministically_and_hash(channel):
    record = TraceRecord(channel, "r-0", {"b": 2, "a": 1, "nested": {"z": [1, 2]}})
    first = record.serialize()
    second = TraceRecord(channel, "r-0", {"a": 1, "nested": {"z": [1, 2]}, "b": 2}).serialize()
    assert first == second, "serialization must be key-order independent"
    assert record.content_hash() == TraceRecord(channel, "r-0", {"a": 1, "b": 2, "nested": {"z": [1, 2]}}).content_hash()
    assert len(record.content_hash()) == 64


def test_unknown_channel_and_unserializable_payload_fail_closed():
    with pytest.raises(TraceContractError):
        TraceRecord("SIDE_CHANNEL", "r", {}).validate()
    with pytest.raises(BoundaryViolation):
        TraceRecord("TOOL", "r", {"handle": object()}).serialize()


def test_trace_payload_cannot_carry_gold():
    with pytest.raises(BoundaryViolation):
        TraceRecord("MODEL_REQUEST", "r", {"prompt": "x", "gold": "leak"}).serialize()
