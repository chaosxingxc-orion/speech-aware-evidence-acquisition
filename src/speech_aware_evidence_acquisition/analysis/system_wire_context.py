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
from pathlib import Path

from ..core.flight.receipts import read_flight_receipts
from ..core.preparation import canonical_bytes, digest, load_artifact, prepare_artifact
from ..core.preparation_fit import boundary_identity
from ..rails.hashing import content_hash
from ..rails.prepared_feedback import _read_pinned_json, _resolve_data_path
from .shared_json import restore_json, share_json


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
