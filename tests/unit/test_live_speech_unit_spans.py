"""CPU-only proofs of on-demand current-window speech selection."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails import live_speech_observation as live
from test_feature_execution_unit_client import _feature_unit_world
from test_live_speech_observation import FakeBackend, inventory, protocol, arguments


def _arguments(start=0.0, end=0.125):
    return arguments(span={"start_seconds": start, "end_seconds": end})


def _context(unit):
    return SimpleNamespace(
        sample_id=unit.parent_sample_id, execution_unit_id=unit.request_key,
        execution_unit_binding=unit.as_json(),
        query_state=SimpleNamespace(
            query_sample_id=unit.parent_sample_id,
            speech_packet_id=unit.speech_packet_id,
            speech_packet_sha256=unit.speech_packet_sha256,
        ),
    )


def _provider(tmp_path):
    world, _, _, _, _, roster, _ = _feature_unit_world(tmp_path)
    events = []
    provider = live.LiveSpeechObservationProvider(
        inventory=inventory(), protocol=protocol(source_selection="bounded-span-v1"),
        execution_units=roster,
        source_bindings=live.execution_unit_source_bindings(roster),
        data_root=world.data_root, output_root=world.data_root / "observations",
        contact=lambda **facts: events.append(("contact", facts)) or {"ordinal": len(events)},
        backend_factory=lambda _i, _p, _d, event: FakeBackend(events, event=event),
        host_memory_guard=lambda: None,
    )
    return provider, roster, events


def test_selected_span_is_lazy_exact_and_cached_by_unit_and_frames(tmp_path):
    provider, roster, events = _provider(tmp_path)
    assert events == []
    unit = roster.units[0]
    selection = provider.observe_span(
        context=_context(unit), arguments=_arguments(), source_response_sha256="a" * 64,
    )
    contact, decoded = events
    assert contact[0] == "contact" and decoded[0] == "decode"
    assert contact[1]["audio_seconds"] == 0.125
    assert contact[1]["execution_unit_id"] == unit.request_key
    assert (decoded[1]["start_frame"], decoded[1]["end_frame"]) == (0, 2000)
    assert decoded[1]["source_frames"] == 8000
    assert selection.visible["execution_unit_id"] == unit.request_key
    assert selection.visible["source_span"] == {
        "kind": "unit-relative-frames", "start_frame": 0, "end_frame": 2000,
        "sample_rate_hz": 16000,
    }
    warm = provider.observe_span(
        context=_context(unit), arguments=_arguments(), source_response_sha256="b" * 64,
    )
    assert warm.lineage["cache"] == "warm"
    assert len(events) == 2
    later = provider.observe_span(
        context=_context(unit), arguments=_arguments(0.125, 0.25),
        source_response_sha256="c" * 64,
    )
    assert later.visible["artifact_sha256"] != selection.visible["artifact_sha256"]
    sibling = provider.observe_span(
        context=_context(roster.units[1]), arguments=_arguments(), source_response_sha256="d" * 64,
    )
    assert sibling.visible["artifact_sha256"] != selection.visible["artifact_sha256"]
    assert len(events) == 6
    provider.close()


@pytest.mark.parametrize("change", ["unit", "parent", "packet", "binding"])
def test_foreign_unit_or_source_refuses_before_any_contact(tmp_path, change):
    provider, roster, events = _provider(tmp_path)
    context = _context(roster.units[0])
    if change == "unit":
        context.execution_unit_id = roster.units[1].request_key
    elif change == "parent":
        context.sample_id = "foreign"
    elif change == "packet":
        context.query_state.speech_packet_sha256 = "e" * 64
    else:
        context.execution_unit_binding = roster.units[1].as_json()
    with pytest.raises(live.LiveSpeechObservationError):
        provider.observe_span(
            context=context, arguments=_arguments(), source_response_sha256="a" * 64,
        )
    assert events == []


@pytest.mark.parametrize("start,end", [
    (-0.1, 0.1), (0.2, 0.1), (0.0, 0.0), (0.0, 0.5001),
    (True, 0.1), (0.0, float("nan")), (0.0, float("inf")),
])
def test_invalid_or_outside_window_span_refuses_before_contact(tmp_path, start, end):
    provider, roster, events = _provider(tmp_path)
    with pytest.raises(live.LiveSpeechObservationError):
        provider.observe_span(
            context=_context(roster.units[0]), arguments=_arguments(start,end),
            source_response_sha256="a" * 64,
        )
    assert events == []


def test_long_window_selects_bounded_span_without_clipping():
    from test_execution_unit_static_fit import _unit
    unit = _unit("parent", 0)
    unit = replace(unit, slice_record=replace(
        unit.slice_record, end_seconds=90.0, audio_seconds=90.0,
    ))
    span, duration = live.select_execution_unit_span(unit, _arguments(60.0, 90.0))
    assert (span["start_frame"], span["end_frame"], duration) == (960000, 1440000, 30.0)
    with pytest.raises(live.LiveSpeechObservationError, match="30 seconds"):
        live.select_execution_unit_span(unit, _arguments(0.0, 30.01))


def test_whole_utterance_tool_cannot_alias_current_window(tmp_path):
    provider, roster, events = _provider(tmp_path)
    with pytest.raises(live.LiveSpeechObservationError, match="span"):
        provider.observe(
            context=_context(roster.units[0]), arguments=arguments(),
            source_response_sha256="a" * 64,
        )
    assert events == []


def test_returned_span_evidence_cannot_be_relabelled(tmp_path):
    from types import MappingProxyType
    provider, roster, _events = _provider(tmp_path)
    context = _context(roster.units[0])
    selection = provider.observe_span(
        context=context, arguments=_arguments(), source_response_sha256="a" * 64,
    )
    facts = dict(context=context, arguments=_arguments(), source_response_sha256="a" * 64)
    provider.validate_span_selection(**facts, selection=selection)
    altered = replace(selection, visible=MappingProxyType({
        **selection.visible, "source_span": {"start_frame": 2000, "end_frame": 4000},
    }))
    with pytest.raises(live.LiveSpeechObservationError, match="foreign evidence"):
        provider.validate_span_selection(**facts, selection=altered)
