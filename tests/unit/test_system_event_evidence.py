"""Test event credit projection through verified-source preparation and shared send."""
# Pytest resolves imported fixture names through test arguments.
# ruff: noqa: F811
import copy
import json

import pytest

from test_system_comparison_preparation import (  # noqa: F401
    comparison_world, prepared, load,
)
from test_system_summary_preparation import summary_world, pin  # noqa: F401
from speech_aware_evidence_acquisition.analysis.shared_json import restore_json, share_json
from speech_aware_evidence_acquisition.analysis.system_wire_context import compact_wire_episode
from speech_aware_evidence_acquisition.rails import system_comparison_context as module
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.prepared_feedback import PreparedFeedbackError


def wire_world(world):
    for summary in world["summaries"].values():
        for context in summary.prepared_document["contexts"]:
            episode = context["model_context"]["trajectory"]
            requests = {c["request_record_id"]: {"messages": [{"role": "user", "content": "source"}],
                        "tools": []} for c in episode["contacts"]}
            context["source_feedback_sha256"] = episode["content_sha256"]
            context["model_context"]["trajectory"] = compact_wire_episode(episode, requests)


def bind_events(world, mode="recorded-system-events-v1"):
    world["binding"] = dict(world["binding"], schema=module.EVENT_SOURCE_SCHEMA, event_evidence=mode)
    world["source_pin"] = pin(world["data"], "event-source.json", world["binding"])


def first_wire(world):
    return next(iter(world["summaries"].values())).prepared_document["contexts"][0]["model_context"]["trajectory"]


def test_event_projection_preserves_summaries_feedback_and_complete_history(comparison_world):
    world = comparison_world
    wire_world(world)
    before = module.build_system_comparison_contexts(world["source_pin"], data_root=world["data"])
    sources = copy.deepcopy(world["summaries"])
    bind_events(world)
    result = module.build_system_comparison_contexts(world["source_pin"], data_root=world["data"])
    old = before["comparison"]["groups"][0]["model_context"]
    new = result["comparison"]["groups"][0]["model_context"]
    assert before["comparison"]["ready_sample_ids"] == result["comparison"]["ready_sample_ids"]
    for left, right in zip(old["attempts"], new["attempts"]):
        assert left == {k: v for k, v in right.items() if k != "recorded_system_events"}
        evidence = right["recorded_system_events"]
        original = next(s for s in sources.values()
                        if s.rows[world["actor"].sample_ids[0]]["episode_sha256"] == evidence["source_episode_sha256"])
        visible = restore_json(original.prepared_document["contexts"][0]["model_context"]["trajectory"]["context"])
        assert all(c["advertised_tools"] == [] for c in evidence["contacts"])
        for key in ("actual_tool_records", "timeline_record_ids", "control_receipt", "delivery", "delivered_text"):
            assert evidence[key] == visible[key]
        assert len(evidence["contacts"]) == len(visible["contacts"])
        for actual, expected in zip(evidence["contacts"], visible["contacts"]):
            assert "request" not in actual
            assert actual["response_record"] == expected["response_record"]
            assert actual["wire_response_utf8"] == expected["wire_response_utf8"]
    assert new["feedback_definition"] == old["feedback_definition"]
    assert sources == world["summaries"]
    assert "reference_answer" not in json.dumps(new)
    assert result["comparison"]["content_sha256"] == content_hash(
        {k: v for k, v in result["comparison"].items() if k != "content_sha256"})
    assert result["model_contacts_added"] == result["scorer_contacts_added"] == 0


@pytest.mark.parametrize("kind", ["response", "tool", "route", "delivery", "timeline", "missing-contact", "duplicate-contact"])
def test_changed_or_missing_events_fail_before_preparation(comparison_world, kind):
    world = comparison_world
    wire_world(world)
    bind_events(world)
    wire = first_wire(world)
    visible = restore_json(wire["context"])
    if kind == "response":
        visible["contacts"][0]["response_record"]["text"] = "altered"
    elif kind == "tool":
        visible["actual_tool_records"].append({"record_id": "invented", "record": {"text": "fake"}})
    elif kind == "route":
        visible["control_receipt"]["unrecorded-route"] = "ACCEPT"
    elif kind == "delivery":
        visible["delivered_text"] = "altered"
    elif kind == "timeline":
        visible["timeline_record_ids"] = visible["timeline_record_ids"][::-1]
    elif kind == "missing-contact":
        visible["contacts"].pop()
    else:
        visible["contacts"].append(copy.deepcopy(visible["contacts"][0]))
    wire["context"] = share_json(visible)
    with pytest.raises(PreparedFeedbackError):
        module.build_system_comparison_contexts(world["source_pin"], data_root=world["data"])


@pytest.mark.parametrize("kind", ["unknown-mode", "legacy-extra-field", "wrong-episode", "non-wire", "missing-summary"])
def test_bad_event_source_binding_is_refused(comparison_world, kind):
    world = comparison_world
    if kind != "non-wire":
        wire_world(world)
    bind_events(world, "unknown" if kind == "unknown-mode" else "recorded-system-events-v1")
    if kind == "legacy-extra-field":
        world["binding"]["schema"] = module.SOURCE_SCHEMA
        world["source_pin"] = pin(world["data"], "bad-schema.json", world["binding"])
    elif kind == "wrong-episode":
        first_wire(world)["source_episode_sha256"] = "f"*64
    elif kind == "missing-summary":
        next(iter(world["summaries"].values())).prepared_document["contexts"].clear()
    with pytest.raises(PreparedFeedbackError):
        module.build_system_comparison_contexts(world["source_pin"], data_root=world["data"])


def test_tied_population_is_retained_with_event_evidence(comparison_world):
    world = comparison_world
    wire_world(world)
    for group in world["groups"].values():
        group["rows"][0]["fp"] = 0
    world["binding"]["comparison_roster"] = None
    bind_events(world)
    result = module.build_system_comparison_contexts(world["source_pin"], data_root=world["data"])
    assert not result["contexts"]
    group = result["comparison"]["groups"][0]
    assert group["disposition"] == "no-update-terminal-tie"
    assert len(group["model_context"]["attempts"]) == 2
    assert all(a["recorded_system_events"] for a in group["model_context"]["attempts"])


def test_event_context_reaches_same_request_fit_send_and_artifact(comparison_world, tmp_path):
    from test_system_summary_preparation import exercise_shared_fit_and_send
    world = comparison_world
    wire_world(world)
    bind_events(world)
    spec, _ = prepared(world)
    states, receipt = load(world, spec)
    assert "recorded_system_events" in next(iter(states.values())).content
    assert receipt["full_group_count"] == 1
    world_inputs = (world["data"], world["actor"],
                    {"construction_roster": world["binding"]["comparison_roster"]},
                    world["source_pin"], world["calls"])
    exercise_shared_fit_and_send(world_inputs, tmp_path, True, prepared_spec=spec,
                                baseline="system-semantic-comparison-text-v1", comparison=True)


def test_crossed_option_label_is_refused(comparison_world, monkeypatch):
    world = comparison_world
    wire_world(world)
    bind_events(world)
    original = module.join_recorded_summaries
    def crossed(*args):
        value = original(*args)
        value["groups"][0]["candidate_bindings"][0]["label"] = "option-other"
        return value
    monkeypatch.setattr(module, "join_recorded_summaries", crossed)
    with pytest.raises(PreparedFeedbackError, match="option identity"):
        module.build_system_comparison_contexts(world["source_pin"], data_root=world["data"])
