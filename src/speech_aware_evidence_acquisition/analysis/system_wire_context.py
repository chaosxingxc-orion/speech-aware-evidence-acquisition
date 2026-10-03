"""Exact fitted actor requests and compact whole-system semantic views.

The view preserves model-visible requests, responses, actual tools, control and
delivery. Internal custody is retained in the immutable actor source, not copied
into the summary prompt. It is not a lossless serialization of the internal
request envelope. Loading an archive is offline and does not require the former
model service to remain alive.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from ..core.flight.receipts import read_flight_receipts
from ..core.model import FrozenCoreError
from ..core.model.native_framework_history import validate_native_framework_contact
from ..core.preparation import canonical_bytes, digest, load_artifact, prepare_artifact
from ..core.preparation_fit import boundary_identity
from ..rails.hashing import content_hash
from ..rails.prepared_feedback import _read_pinned_json, _resolve_data_path
from .node_panel_timing import audit_member_node_timing
from .shared_json import restore_json, share_json


def verify_role_query_layout_receipt(request_bytes, body, receipt, *, fitted_body_sha256):
    """Check one recorded layout against its original source and actual FIT body.

    This pure structural check grants no read or execution permission. The caller
    must supply the independently pinned original FIT hash and ensure complete
    contact coverage under the applicable engineering or full-family read scope.
    Render body with the original frozen shared renderer, without contacting a
    service. Never substitute a newly measured FIT for the original receipt.
    """
    payload = json.loads(request_bytes)
    if (not isinstance(payload, dict) or not isinstance(receipt, dict)
            or not isinstance(body, dict)
            or not isinstance(payload.get("request_id"), str)
            or not payload["request_id"]):
        raise ValueError("layout source and receipt require a request identity")
    body_sha = digest(body)
    if body_sha != fitted_body_sha256:
        raise ValueError("layout body differs from the original independently pinned FIT")
    request_sha = hashlib.sha256(request_bytes).hexdigest()
    if (receipt.get("input_request_id") != payload["request_id"]
            or receipt.get("input_request_bytes_sha256") != request_sha
            or receipt.get("rendered_body_canonical_sha256") != body_sha):
        raise ValueError("layout receipt source/body binding differs")
    try:
        validated = validate_native_framework_contact(payload)
    except FrozenCoreError as exc:
        raise ValueError("layout source framework is invalid") from exc
    if validated is None:
        raise ValueError("layout source requires the native framework contract")
    contract, _, _ = validated
    control = payload["history"][-1]
    control_sha = hashlib.sha256(control["content"].encode("utf-8")).hexdigest()
    if control.get("content_sha256") != control_sha:
        raise ValueError("layout source control hash differs from its actual bytes")
    query = contract["messages"][1]["content"]
    expected = {
        "schema": "saea-native-role-query-layout-v1",
        "placement": "before-speech-v1",
        **{key: contract[key] for key in ("role_id", "sample_id", "contact_id")},
        "source_control_sha256": control_sha,
        "role_query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
    }
    layout = receipt.get("role_query_layout")
    if not isinstance(layout, dict) or any(layout.get(k) != v for k, v in expected.items()):
        raise ValueError("layout receipt differs from the original role/control identity")
    messages = body.get("messages")
    if (not isinstance(messages, list) or len(messages) < 2
            or messages[0] != contract["messages"][0]
            or not isinstance(messages[1], dict) or messages[1].get("role") != "user"
            or not isinstance(messages[1].get("content"), list)
            or not messages[1]["content"]
            or messages[1]["content"][0] != {"type": "text", "text": query}):
        raise ValueError("actual role query placement or message authority differs")
    return {
        "schema": "saea-verified-native-role-query-layout-v1", "verified": True,
        **{key: expected[key] for key in ("placement", "role_id", "sample_id", "contact_id",
                                         "source_control_sha256", "role_query_sha256")},
        "request_id": payload["request_id"], "request_bytes_sha256": request_sha,
        "request_body_sha256": body_sha,
    }


def _read(pin, data_root, label):
    document, sha = _read_pinned_json(pin, data_root=Path(data_root), field=label)
    path = _resolve_data_path(pin["relpath"], data_root=Path(data_root), field=label)
    return document, sha, path


def _contacts(report):
    for episode in report["episodes"]:
        for contact in episode["contacts"]:
            payload = {k: episode["content_pool"][v]
                       for k, v in contact["request_field_refs"].items()}
            yield episode, contact, payload


def _fit_index(source, report, flight_pin, data_root):
    flight, _sha, path = _read(flight_pin, data_root, "actor flight receipts")
    if read_flight_receipts(path) != flight:
        raise ValueError("actor flight receipts changed during validation")
    if (flight["run_id"] != source.plan.run_id
            or flight["attempt_id"] != source.plan.attempt_id
            or flight["stages"]["preflight"]["config_hash"] != source.composed.config_hash
            or flight["stages"]["score"]["finalized_manifest_sha256"]
            != hashlib.sha256(source.bundle.manifest_path.read_bytes()).hexdigest()):
        raise ValueError("actor receipts differ from the finalized source")
    receipts = flight["stages"]["run_phases"]["dispatch"]["native_contact_fit_receipts"]
    indexed = {}
    for receipt in receipts:
        contact_id = receipt["agent_contact_id"]
        if contact_id in indexed:
            raise ValueError("duplicate original request-fit contact")
        fit_path = Path(receipt["path"]).resolve()
        if not fit_path.is_relative_to(Path(data_root).resolve()):
            raise ValueError("original fit artifact escapes data root")
        fit_doc, _, fit_path = _read({
            "relpath": str(fit_path.relative_to(Path(data_root).resolve())),
            "sha256": receipt["sha256"]}, data_root, "original request fit")
        output = load_artifact(fit_path, expected_sha256=receipt["sha256"],
                               kind="request-fit", inputs=fit_doc["inputs"])
        if (fit_doc["contact_class"] != "tokenizer" or output["every_request_fits"] is not True
                or len(output["rows"]) != 1
                or output["agent_contact_id"] != contact_id
                or fit_doc["inputs"]["native_contact"]["agent_contact_id"] != contact_id):
            raise ValueError("original fit is not one admitted native contact")
        indexed[contact_id] = (fit_doc, output)
    result, seen = {}, set()
    for episode, contact, payload in _contacts(report):
        contact_id = next(
            c["agent_contact_id"] for visit in episode["trajectory"]["role_visits"]
            for c in visit["contacts"] if c["request_record_id"] == contact["request_record_id"])
        if contact_id in seen or contact_id not in indexed:
            raise ValueError("actor contact has missing or repeated fitted evidence")
        seen.add(contact_id)
        fit, output = indexed[contact_id]
        sid = episode["trajectory"]["sample_id"]
        if (fit["inputs"]["sources"]["boundary_sha256"] != boundary_identity((payload,))
                or output["sample_id"] != sid
                or fit["inputs"]["split_identity_hash"] != source.plan.split_identity_hash):
            raise ValueError("original fit does not bind this complete actor input")
        result[contact["request_record_id"]] = output["rows"][0]["request_body_sha256"]
    if seen != set(indexed):
        raise ValueError("original fit roster differs from generated contacts")
    return result


def _inputs(source, report, flight_pin):
    return {"source_manifest_sha256": hashlib.sha256(
                source.bundle.manifest_path.read_bytes()).hexdigest(),
            "source_materialization_sha256": report["content_sha256"],
            "flight_receipts": dict(flight_pin)}


def audit_context_execution(source, report, flight_pin, *, data_root, render_request,
                            placement, scheduler, panel_identity=None):
    """Check original fitted requests against the declared context comparison.

    The caller first qualifies the complete family and its exact root READ.
    Supply the normal shared renderer from the retained configuration. Every
    rendered body must match the independently pinned original FIT; no request
    is sent. This view contains hashes and routing only, never model text.
    Requested slots are not independently observed server assignments.
    """
    values = source.composed.values
    role_slots = dict(perception=0, solver=1, reviewer=2, planner=3)
    if (placement not in ("legacy", "before-speech-v1") or scheduler not in ("trajectory", "role", "panel")
            or values.get("native_role_query_placement", "legacy") != placement):
        raise ValueError("context layout label differs from retained configuration")
    if (bool(values.get("native_node_pipeline")) != (scheduler == "panel")
            or (panel_identity is not None) != (scheduler == "panel")
            or values.get("native_node_batch") is not None):
        raise ValueError("context node scheduler or panel identity differs")
    expected_slots = ({"schema": "saea-native-prefix-slots-v1", "role_slots": role_slots}
                      if scheduler == "role" else None)
    if values.get("native_prefix_slots") != expected_slots:
        raise ValueError("context scheduler label differs from retained configuration")
    episodes = report["episodes"]
    ids = [episode["trajectory"]["sample_id"] for episode in episodes]
    if len(ids) != len(set(ids)) or set(ids) != set(source.sample_ids):
        raise ValueError("context audit must retain every complete sample once")
    fitted = _fit_index(source, report, flight_pin, data_root)
    layouts = {}
    for record_id, record in source.bundle.trace_records.items():
        if "org_native_role_query_layout" not in record:
            continue
        receipt = record["org_native_role_query_layout"]
        rid = receipt["input_request_id"]
        if rid in layouts:
            raise ValueError("duplicate original layout receipt")
        layouts[rid] = (receipt, record_id)
    contacts, seen, sample_slots = [], set(), {sid: set() for sid in ids}
    for episode, contact, payload in _contacts(report):
        record_id, role = contact["request_record_id"], contact["role_id"]
        rid, sid = payload["request_id"], episode["trajectory"]["sample_id"]
        if record_id != rid + "/request" or rid in seen or record_id not in fitted:
            raise ValueError("context contact identity or coverage differs")
        seen.add(rid)
        slot = payload.get("decoding_params", {}).get("id_slot")
        if type(slot) is not int or not 0 <= slot < 4 or role not in role_slots:
            raise ValueError("context contact lacks one legal requested slot and role")
        if scheduler == "role" and slot != role_slots[role]:
            raise ValueError("actual requested slot differs from role mapping")
        sample_slots[sid].add(slot)
        if scheduler == "trajectory" and len(sample_slots[sid]) != 1:
            raise ValueError("trajectory changed requested slot within the sample")
        validated = validate_native_framework_contact(payload)
        if validated is None:
            raise ValueError("context contact requires native framework custody")
        contract, _, _ = validated
        if contract["role_id"] != role or contract["sample_id"] != sid or payload["sample_id"] != sid:
            raise ValueError("context role or sample identity differs from source")
        raw = canonical_bytes(payload)
        body = render_request(raw)
        if digest(body) != fitted[record_id]:
            raise ValueError("context request differs from its original FIT body")
        if body.get("id_slot") != slot or type(body.get("id_slot")) is not int or body.get("max_tokens") != 512:
            raise ValueError("actual body routing or full output reserve differs")
        proof = None
        if placement == "before-speech-v1":
            if rid not in layouts:
                raise ValueError("original context layout receipt is missing")
            proof = verify_role_query_layout_receipt(raw, body, layouts[rid][0],
                                                     fitted_body_sha256=fitted[record_id])
        else:
            messages = body.get("messages", [])
            query = contract["messages"][1]["content"]
            if (len(messages) < 2 or messages[0] != contract["messages"][0]
                    or messages[1].get("role") != "user"
                    or not isinstance(messages[1].get("content"), list) or not messages[1]["content"]
                    or messages[1]["content"][-1] != {"type": "text", "text": query}):
                raise ValueError("legacy role query placement differs from source")
        contacts.append({"request_id": rid, "sample_id": sid, "role_id": role,
                         "request_payload_sha256": hashlib.sha256(raw).hexdigest(),
                         "request_body_sha256": fitted[record_id], "requested_slot_id": slot,
                         "output_reserve": 512, "system_message_sha256": content_hash(contract["messages"][0]),
                         "role_query_sha256": content_hash(contract["messages"][1]), "layout_proof": proof,
                         "layout_source": None if rid not in layouts else {
                             "record_id": layouts[rid][1], "receipt_sha256": content_hash(layouts[rid][0])}})
    if not contacts or set(layouts) != (seen if placement == "before-speech-v1" else set()):
        raise ValueError("original layout receipts differ from complete contact coverage")
    result = {"schema": "saea-context-execution-audit-v1", "placement": placement, "scheduler": scheduler,
              "source_manifest_sha256": hashlib.sha256(source.bundle.manifest_path.read_bytes()).hexdigest(),
              "flight_receipts": dict(flight_pin), "contacts_verified": len(contacts),
              "original_fit_receipts": len(fitted), "contacts": contacts,
              "sample_requested_slots": {sid: sorted(slots) for sid, slots in sample_slots.items()},
              "server_assignment_verified": False, "model_contacts_added": 0, "tokenizer_contacts_added": 0}
    if scheduler == "panel":
        result["node_panel_timing"] = audit_member_node_timing(source, contacts, **panel_identity)
    result["content_sha256"] = content_hash(result)
    return result


def prepare_actor_wire_requests(source, report, flight_pin, output_path, *,
                                data_root, render_request):
    """Archive shared-transport renderings only if every original fitted hash matches.

    render_request must be the recorded worker's normal render_request method.
    It performs no POST. A renderer change cannot silently alter an archived
    request because the original per-contact fit pins its complete wire body.
    """
    expected = _fit_index(source, report, flight_pin, data_root)

    def produce():
        rows = []
        for _episode, contact, payload in _contacts(report):
            body = render_request(canonical_bytes(payload))
            if digest(body) != expected[contact["request_record_id"]]:
                raise ValueError("rendered request differs from its original exact fit")
            rows.append({"request_record_id": contact["request_record_id"],
                         "request_payload_sha256": content_hash(payload), "body": body})
        return {"schema": "saea-system-actor-wire-requests-v1", "requests": rows}

    return prepare_artifact(Path(output_path), kind="system-actor-wire-requests",
                            inputs=_inputs(source, report, flight_pin), producer=produce,
                            contact_class="model-free")


def load_actor_wire_requests(source, report, spec, *, data_root):
    """Verify exact bodies against original fit receipts without opening any endpoint."""
    if not isinstance(spec, dict) or set(spec) != {"artifact", "flight_receipts"}:
        raise ValueError("wire archive requires artifact and original receipt pins")
    expected = _fit_index(source, report, spec["flight_receipts"], data_root)
    envelope, sha, path = _read(spec["artifact"], data_root, "actor wire archive")
    if envelope["contact_class"] != "model-free":
        raise ValueError("actor wire archive must be model-free")
    document = load_artifact(path, expected_sha256=sha, kind="system-actor-wire-requests",
                            inputs=_inputs(source, report, spec["flight_receipts"]))
    if set(document) != {"schema", "requests"} or document["schema"] != "saea-system-actor-wire-requests-v1":
        raise ValueError("actor wire archive schema differs")
    original = {c["request_record_id"]: p for _, c, p in _contacts(report)}
    rows = {}
    for row in document["requests"]:
        rid = row["request_record_id"]
        if (set(row) != {"request_record_id", "request_payload_sha256", "body"}
                or rid in rows or rid not in original
                or row["request_payload_sha256"] != content_hash(original[rid])
                or digest(row["body"]) != expected[rid]):
            raise ValueError("actor wire archive differs from exact source/fit binding")
        rows[rid] = row["body"]
    if set(rows) != set(original):
        raise ValueError("actor wire archive omits generated contacts")
    return rows


def compact_wire_episode(episode, requests):
    """Keep every role, actual tool, revision, interrupted output and final delivery."""
    pool = episode["content_pool"]
    contacts = []
    for contact in episode["contacts"]:
        wire = contact["wire_response"]
        contacts.append({
            **{k: contact[k] for k in ("visit_index", "role_id", "stage", "interrupted",
                                       "request_record_id", "response_record_id")},
            "request": copy.deepcopy(requests[contact["request_record_id"]]),
            "response_record": copy.deepcopy(pool[contact["response_record_ref"]]),
            "wire_response_utf8": None if wire is None else pool[wire["body_utf8_ref"]],
        })
    visible = {
        "input_group_sha256": episode["input_group_sha256"],
        "contacts": contacts,
        "actual_tool_records": [{"record_id": t["record_id"], "record": copy.deepcopy(pool[t["record_ref"]])}
                                for t in episode["tool_records"]],
        "timeline_record_ids": episode["timeline_record_ids"],
        "control_receipt": episode["control_receipt"],
        "delivery": episode["trajectory"]["delivery"],
        "delivered_text": episode["delivered_text"],
    }
    compact = share_json(visible)
    if restore_json(compact) != visible:
        raise ValueError("shared wire view failed exact semantic reconstruction")
    return {
        "schema": "saea-complete-episode-wire-view-v1",
        "source_episode_sha256": episode["content_sha256"],
        "reading_contract": (
            "Read all contacts and actual_tool_records in timeline order. Resolve $ref through "
            "shared; $object encodes literal key/value pairs, not references. Requests are exact "
            "original fitted model bodies; responses, controls and delivery retain all recorded "
            "content. Speech packet descriptors identify the original audio, which is not replayed. "
            "Internal non-model custody fields remain in the bound source rather than this view. "
            "A role's claimed tool result is not an actual tool event."
        ),
        "context": compact,
    }
