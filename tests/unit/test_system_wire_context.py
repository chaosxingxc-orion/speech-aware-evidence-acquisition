"""Compact whole-system views preserve exact source content and original fitted bodies."""
import copy
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.shared_json import share_json, restore_json
from speech_aware_evidence_acquisition.analysis.system_semantic_trajectory import materialize_semantic_trajectories
from speech_aware_evidence_acquisition.analysis.system_wire_context import (
    compact_wire_episode, load_actor_wire_requests, prepare_actor_wire_requests,
)
from speech_aware_evidence_acquisition.core.preparation import digest, prepare_artifact
from speech_aware_evidence_acquisition.core.preparation_fit import boundary_identity
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_system_summary_preparation import summary_world as summary_world, pin, prepared, load
from test_system_semantic_trajectory import source, materialize


def test_references_roundtrip_reserved_keys_nested_strings_and_all_scalars():
    repeated = {"speech": "The complete information repeats. " * 30, "empty": [], "none": None}
    value = {"records": [repeated, repeated], "$ref": "literal source", "$object": [["key", True]],
             "nested": [0, 0.5, False, '{"escaped":"json"}', {"$ref": "p1"}]}
    before = copy.deepcopy(value)
    compact = share_json(value)
    assert restore_json(compact) == before == value
    assert share_json(value) == compact
    assert len(json.dumps(compact)) < len(json.dumps(value))


@pytest.mark.parametrize("mutation", ["missing", "cycle", "unreachable", "extra-ref-field", "bad-object"])
def test_invalid_shared_context_cannot_hide_source_content(mutation):
    document = share_json(["Long repeated text " * 10] * 3)
    if mutation == "missing":
        document["shared"] = {}
    elif mutation == "cycle":
        document["shared"]["p1"] = {"$ref": "p1"}
    elif mutation == "unreachable":
        document["shared"]["unused"] = "Hidden"
    elif mutation == "extra-ref-field":
        document["episode"][0]["hidden"] = "Hidden"
    else:
        document["episode"] = {"$object": [["a", 1], ["a", 2]]}
    with pytest.raises(ValueError):
        restore_json(document)


@pytest.mark.parametrize("finite", [None, True, False])
def test_view_retains_order_every_role_tool_and_delivery_without_gold(finite):
    from test_native_episode_diagnostics import _finite_fixture
    actor = source(None if finite is None else lambda: _finite_fixture(with_solver=finite))
    episode = materialize(actor)["episodes"][0]
    bodies = {c["request_record_id"]: {"messages": [{"role": "system", "content": "Source instruction"}]}
              for c in episode["contacts"]}
    compact = compact_wire_episode(episode, bodies)
    view = restore_json(compact["context"])
    assert compact["source_episode_sha256"] == episode["content_sha256"]
    assert len(view["contacts"]) == len(episode["contacts"])
    assert len(view["actual_tool_records"]) == len(episode["tool_records"])
    assert view["timeline_record_ids"] == episode["timeline_record_ids"]
    assert view["control_receipt"] == episode["control_receipt"]
    assert view["delivered_text"] == episode["delivered_text"]
    for new, old in zip(view["contacts"], episode["contacts"], strict=True):
        assert new["interrupted"] == old["interrupted"]
        assert new["request"] == bodies[old["request_record_id"]]
        assert new["response_record"] == episode["content_pool"][old["response_record_ref"]]
        if old["wire_response"] is not None:
            assert new["wire_response_utf8"] == episode["content_pool"][old["wire_response"]["body_utf8_ref"]]


@pytest.fixture
def wire_world(summary_world):
    data, actor, binding, source_pin, calls = summary_world
    actor.bundle.manifest_path = data / binding["manifest"]["relpath"]
    actor.composed.config_hash = "f" * 64
    report = materialize_semantic_trajectories(actor, round_id=binding["round_id"])
    receipts, bodies = [], {}
    for episode in report["episodes"]:
        for contact in episode["contacts"]:
            payload = {k: episode["content_pool"][v] for k, v in contact["request_field_refs"].items()}
            cid = next(c["agent_contact_id"] for visit in episode["trajectory"]["role_visits"]
                       for c in visit["contacts"] if c["request_record_id"] == contact["request_record_id"])
            body = {"messages": [{"role": "system", "content": payload.get("task_instruction", "Continue.")}],
                    "max_tokens": 512}
            bodies[contact["request_record_id"]] = body
            fit = prepare_artifact(
                data / ("fits/" + cid.replace("/", "-") + ".json"), kind="request-fit",
                inputs={"sources": {"boundary_sha256": boundary_identity((payload,))},
                        "native_contact": {"agent_contact_id": cid},
                        "split_identity_hash": actor.plan.split_identity_hash},
                producer=lambda cid=cid, body=body: {
                    "sample_id": actor.sample_ids[0], "agent_contact_id": cid,
                    "every_request_fits": True, "rows": [{"request_body_sha256": digest(body)}]},
                contact_class="tokenizer")
            receipts.append({**fit, "agent_contact_id": cid})
    stages = {
        "preflight": {"config_hash": actor.composed.config_hash},
        "preprocess": {}, "serve": {},
        "run_phases": {"dispatch": {"native_contact_fit_receipts": receipts}},
        "seal": {},
        "score": {"finalized_manifest_sha256": binding["manifest"]["sha256"]},
    }
    for stage, row in stages.items():
        row["stage"] = stage
        row["stage_hash"] = content_hash(row)
    flight = {"schema": "saea-flight-receipts-v1", "run_id": actor.plan.run_id,
              "attempt_id": actor.plan.attempt_id, "stages": stages}
    flight["receipts_hash"] = content_hash(flight)
    flight_pin = pin(data, "run/flight-receipts.json", flight)
    receipt = prepare_actor_wire_requests(
        actor, report, flight_pin, data / "wire.json", data_root=data,
        render_request=lambda raw: bodies[json.loads(raw)["request_id"] + "/request"])
    binding.update(schema="saea-system-summary-source-v2", wire_requests={
        "flight_receipts": flight_pin,
        "artifact": {"relpath": "wire.json", "sha256": receipt["sha256"]}})
    updated = pin(data, "wire-source.json", binding)
    return (data, actor, binding, updated, calls), report, bodies


def test_complete_wire_view_rebuilds_offline_and_keeps_original_episode_join(wire_world):
    world, report, bodies = wire_world
    data, actor, binding, _, _ = world
    assert load_actor_wire_requests(actor, report, binding["wire_requests"], data_root=data) == bodies
    spec, _ = prepared(world)
    states, _ = load(world, spec)
    context = json.loads(next(iter(states.values())).content)
    episode = context["trajectory"]
    assert episode["schema"] == "saea-complete-episode-wire-view-v1"
    assert episode["source_episode_sha256"] == report["episodes"][0]["content_sha256"]
    view = restore_json(episode["context"])
    assert len(view["contacts"]) == 5
    assert len(view["actual_tool_records"]) == 2


@pytest.mark.parametrize("mutation", ["body", "payload", "missing", "duplicate", "fit-body", "fit-boundary"])
def test_archive_tampering_refused_even_after_rehash(wire_world, mutation):
    world, report, _ = wire_world
    data, actor, binding, _, _ = world
    spec = copy.deepcopy(binding["wire_requests"])
    doc = json.loads((data / "wire.json").read_text())
    if mutation.startswith("fit-"):
        flight = json.loads((data / spec["flight_receipts"]["relpath"]).read_text())
        receipt = flight["stages"]["run_phases"]["dispatch"]["native_contact_fit_receipts"][0]
        path = Path(receipt["path"])
        fit = json.loads(path.read_text())
        if mutation == "fit-body":
            fit["output"]["rows"][0]["request_body_sha256"] = "a" * 64
        else:
            fit["inputs"]["sources"]["boundary_sha256"] = "a" * 64
        fit["output_sha256"] = digest(fit["output"])
        path.write_text(json.dumps(fit))
        # The original pinned flight receipt still identifies the original fit.
    else:
        rows = doc["output"]["requests"]
        if mutation == "body":
            rows[0]["body"]["max_tokens"] = 1
        elif mutation == "payload":
            rows[0]["request_payload_sha256"] = "a" * 64
        elif mutation == "missing":
            rows.pop()
        else:
            rows.append(copy.deepcopy(rows[0]))
        doc["output_sha256"] = digest(doc["output"])
        spec["artifact"] = pin(data, "changed-wire.json", doc)
    with pytest.raises(ValueError):
        load_actor_wire_requests(actor, report, spec, data_root=data)


def test_changed_renderer_cannot_create_a_new_archive(wire_world):
    world, report, _ = wire_world
    data, actor, binding, _, _ = world
    with pytest.raises(ValueError, match="original exact fit"):
        prepare_actor_wire_requests(
            actor, report, binding["wire_requests"]["flight_receipts"],
            data / "wrong-render.json", data_root=data, render_request=lambda _: {"messages": []})
    assert not (data / "wrong-render.json").exists()


def test_compact_context_uses_same_executor_actual_fit_and_send(wire_world, tmp_path):
    from test_system_summary_preparation import exercise_shared_fit_and_send

    world, _report, _bodies = wire_world
    spec, _ = prepared(world)
    exercise_shared_fit_and_send(
        world, tmp_path, True, prepared_spec=spec,
        baseline="system-trajectory-summary-wire-text-v1", wire_view=True)
