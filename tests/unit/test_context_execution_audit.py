"""Check actual context/routing through original FIT, not configuration labels."""
import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis import system_wire_context as wire
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes, digest, prepare_artifact
from speech_aware_evidence_acquisition.core.preparation_fit import boundary_identity
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_raw_native_transport import _raw_framework_payload, _transport

ROLE_SLOTS = dict(perception=0, solver=1, reviewer=2, planner=3)


def world(tmp_path, placement="legacy", scheduler="trajectory"):
    payload, _, _ = _raw_framework_payload(tmp_path)
    contract = json.loads(payload["history"][-1]["content"])
    role, sid, cid = (contract[key] for key in ("role_id", "sample_id", "contact_id"))
    payload["decoding_params"].update(max_tokens=512, id_slot=ROLE_SLOTS[role] if scheduler == "role" else 0)
    transport = _transport(tmp_path)
    transport._native_role_query_placement = None if placement == "legacy" else placement
    transport._post = lambda *a, **k: pytest.fail("audit must never POST")
    body, layout = transport.render_request_with_receipt(canonical_bytes(payload))
    rid = payload["request_id"] + "/request"
    report = {"episodes": [{"trajectory": {"sample_id": sid, "role_visits": [
        {"contacts": [{"request_record_id": rid, "agent_contact_id": cid}]}]},
        "contacts": [{"request_record_id": rid, "role_id": role}],
        "content_pool": copy.deepcopy(payload), "request_unused": None}]}
    report["episodes"][0]["contacts"][0]["request_field_refs"] = {key: key for key in payload}
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}")
    values = {"native_role_query_placement": placement}
    if scheduler == "role":
        values["native_prefix_slots"] = {"schema": "saea-native-prefix-slots-v1", "role_slots": ROLE_SLOTS}
    source = SimpleNamespace(
        plan=SimpleNamespace(run_id="run", attempt_id="attempt", split_identity_hash="a" * 64),
        composed=SimpleNamespace(values=values, config_hash="b" * 64), sample_ids=[sid],
        bundle=SimpleNamespace(manifest_path=manifest, trace_records={} if layout is None else {
            "layout": {"org_native_role_query_layout": layout}}))
    fit = prepare_artifact(tmp_path / "fit.json", kind="request-fit", contact_class="tokenizer",
        inputs={"sources": {"boundary_sha256": boundary_identity((payload,))},
                "native_contact": {"agent_contact_id": cid}, "split_identity_hash": "a" * 64},
        producer=lambda: {"sample_id": sid, "agent_contact_id": cid, "every_request_fits": True,
                          "rows": [{"request_body_sha256": digest(body)}]})
    stages = {"preflight": {"config_hash": "b" * 64}, "preprocess": {}, "serve": {},
              "run_phases": {"dispatch": {"native_contact_fit_receipts": [{**fit, "agent_contact_id": cid}]}},
              "seal": {}, "score": {"finalized_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest()}}
    for name, stage in stages.items():
        stage["stage"] = name
        stage["stage_hash"] = content_hash(stage)
    flight = {"schema": "saea-flight-receipts-v1", "run_id": "run", "attempt_id": "attempt", "stages": stages}
    flight["receipts_hash"] = content_hash(flight)
    raw = json.dumps(flight).encode()
    (tmp_path / "flight.json").write_bytes(raw)
    pin = {"relpath": "flight.json", "sha256": hashlib.sha256(raw).hexdigest()}
    return source, report, pin, transport


def audit(tmp_path, objects, placement="legacy", scheduler="trajectory", **kwargs):
    source, report, pin, transport = objects
    return wire.audit_context_execution(source, report, pin, data_root=tmp_path,
        render_request=kwargs.pop("render_request", transport.render_request), placement=placement,
        scheduler=scheduler, **kwargs)


@pytest.mark.parametrize("placement", ["legacy", "before-speech-v1"])
@pytest.mark.parametrize("scheduler", ["trajectory", "role"])
def test_exact_original_fit_layout_and_requested_routing_are_checked(tmp_path, placement, scheduler):
    objects = world(tmp_path, placement, scheduler)
    report = audit(tmp_path, objects, placement, scheduler)
    assert report["contacts_verified"] == report["original_fit_receipts"] == 1
    assert report["placement"] == placement and report["scheduler"] == scheduler
    assert report["model_contacts_added"] == report["tokenizer_contacts_added"] == 0
    assert report["server_assignment_verified"] is False
    assert report["contacts"][0]["output_reserve"] == 512
    assert "Solve the speech task." not in json.dumps(report)
    assert "messages" not in report["contacts"][0]


@pytest.mark.parametrize("fault", ["wrong_label", "wrong_scheduler", "layout_missing", "layout_duplicate",
    "layout_extra", "source_role", "source_sample", "slot_missing", "slot_bool", "slot_outside", "role_slot",
    "body", "body_slot", "output_reserve", "partial", "duplicate", "trajectory_changes_slot"])
def test_misapplied_or_incomplete_configuration_is_rejected(tmp_path, fault, monkeypatch):
    placement = "legacy" if fault == "trajectory_changes_slot" else "before-speech-v1"
    scheduler = "role" if fault == "role_slot" else "trajectory"
    objects = world(tmp_path, placement, scheduler)
    source, report, pin, transport = objects
    episode = report["episodes"][0]
    payload = episode["content_pool"]
    if fault == "wrong_label":
        source.composed.values["native_role_query_placement"] = "legacy"
    elif fault == "wrong_scheduler":
        source.composed.values["native_prefix_slots"] = {"role_slots": ROLE_SLOTS}
    elif fault == "layout_missing":
        source.bundle.trace_records.clear()
    elif fault == "layout_duplicate":
        source.bundle.trace_records["duplicate"] = copy.deepcopy(source.bundle.trace_records["layout"])
    elif fault == "layout_extra":
        extra = copy.deepcopy(source.bundle.trace_records["layout"])
        extra["org_native_role_query_layout"]["input_request_id"] = "foreign"
        source.bundle.trace_records["extra"] = extra
    elif fault == "source_role":
        episode["contacts"][0]["role_id"] = "planner"
    elif fault == "source_sample":
        episode["trajectory"]["sample_id"] = "foreign"
    elif fault == "slot_missing":
        payload["decoding_params"].pop("id_slot")
    elif fault == "slot_bool":
        payload["decoding_params"]["id_slot"] = True
    elif fault == "slot_outside":
        payload["decoding_params"]["id_slot"] = 4
    elif fault == "role_slot":
        payload["decoding_params"]["id_slot"] = (payload["decoding_params"]["id_slot"] + 1) % 4
    elif fault == "partial":
        report["episodes"] = []
    elif fault == "duplicate":
        report["episodes"].append(copy.deepcopy(episode))
    elif fault == "trajectory_changes_slot":
        second = copy.deepcopy(episode["contacts"][0])
        second["request_record_id"] = "second/request"
        second["request_field_refs"]["decoding_params"] = "second_decoding"
        payload["second_decoding"] = {**payload["decoding_params"], "id_slot": 1}
        second["request_field_refs"]["request_id"] = "second_id"
        payload["second_id"] = "second"
        episode["contacts"].append(second)
    def render(raw):
        result = transport.render_request(raw)
        if fault == "body":
            result["temperature"] = .7
        elif fault == "body_slot":
            result["id_slot"] = 3
        elif fault == "output_reserve":
            result["max_tokens"] = 1
        return result
    # Separate routing checks from original FIT validation for these negative cases.
    if fault in {"slot_missing", "slot_bool", "slot_outside", "role_slot", "source_role", "source_sample",
                 "trajectory_changes_slot", "body_slot", "output_reserve"}:
        monkeypatch.setattr(wire, "_fit_index", lambda *a: {
            contact["request_record_id"]: digest(render(canonical_bytes({key: episode["content_pool"][ref]
                for key, ref in contact["request_field_refs"].items()}))) for contact in episode["contacts"]})
    with pytest.raises(ValueError, match="trajectory changed" if fault == "trajectory_changes_slot" else None):
        audit(tmp_path, objects, placement, scheduler, render_request=render)


def panel_world(tmp_path, placement="legacy"):
    objects = world(tmp_path, placement)
    source, report, _, _ = objects
    sid = source.sample_ids[0]
    role = report["episodes"][0]["contacts"][0]["role_id"]
    order = list(ROLE_SLOTS)
    source.composed.values["native_node_pipeline"] = {
        "schema": "saea-native-node-pipeline-v1", "group_size": 1,
        "max_jobs": 2, "prepare_workers": 2, "node_order": order}
    source.bundle.trace_records["sample-timing"] = {"use_sample_execution_timing": {
        "schema": "saea-sample-execution-timing-v1", "sample_id": sid,
        "execution_unit_id": None, "panel_id": "panel", "panel_expected_samples": 2,
        "panel_admission_index": 0, "admission_index": 0, "expected_samples": 1,
        "slot_count": 4, "status": "completed", "error_type": None,
        "batch_started_ns": 0, "panel_execution_started_ns": 1, "admitted_ns": 1, "finished_ns": 5}}
    for kind, start, slot in [("prepare", 2, None), ("model", 3, 0)]:
        source.bundle.trace_records[kind] = {"use_node_pipeline_timing": {
            "schema": "saea-node-pipeline-timing-v1", "sample_id": sid,
            "execution_unit_id": None, "panel_id": "panel", "group_index": 0,
            "round_index": 0, "node_index": order.index(role), "node_id": role,
            "kind": kind, "slot_id": slot, "queued_ns": start, "started_ns": start,
            "finished_ns": start + 1, "status": "completed", "error_type": None}}
    identity = {"panel_id": "panel", "group_index": 0, "group_size": 1,
                "max_jobs": 2, "job_keys": [[sid, None]]}
    return objects, identity


@pytest.mark.parametrize("placement", ["legacy", "before-speech-v1"])
def test_panel_audit_joins_original_timing_and_full_fit(tmp_path, placement):
    objects, identity = panel_world(tmp_path, placement)
    result = audit(tmp_path, objects, placement, "panel", panel_identity=identity)
    assert result["node_panel_timing"]["model_contacts"] == result["contacts_verified"] == 1
    assert result["node_panel_timing"]["samples"][0]["batch_started_ns"] == 0
    assert result["server_assignment_verified"] is False


@pytest.mark.parametrize("fault", ["hidden-panel", "missing-identity", "wrong-identity", "extra-identity", "wrong-callback", "other-scheduler"])
def test_panel_cannot_masquerade_as_ordinary_execution(tmp_path, fault):
    objects, identity = panel_world(tmp_path)
    scheduler = "panel"
    if fault == "hidden-panel":
        scheduler = "trajectory"
    elif fault == "missing-identity":
        identity = None
    elif fault == "wrong-identity":
        identity["panel_id"] = "foreign"
    elif fault == "extra-identity":
        objects[0].composed.values.pop("native_node_pipeline")
        scheduler = "trajectory"
    elif fault == "wrong-callback":
        objects[0].bundle.trace_records["model"]["use_node_pipeline_timing"]["slot_id"] = 1
    else:
        objects[0].composed.values["native_node_batch"] = {"cohort_size": 4}
    with pytest.raises(ValueError):
        audit(tmp_path, objects, scheduler=scheduler, panel_identity=identity)
