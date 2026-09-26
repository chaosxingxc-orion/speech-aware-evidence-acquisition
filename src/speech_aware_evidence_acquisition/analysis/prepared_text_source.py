"""Verify a sealed prepared-text stage against its exact frozen request context."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping

from ..contracts import ExecutionPlan
from ..core.bundle.git_commit import require_clean_study_repo
from ..core.bundle.verify import verify_bundle
from ..core.config import compose
from ..core.flight.runtime import validate_artifact_result_binding
from ..core.model.transport import _speech_history_texts
from ..core.preparation import load_artifact
from ..rails.core_client import _agent_history
from ..rails.controllers import default_phase_program
from ..rails.hashing import content_hash
from ..rails.phase_material import load_phase_material_specs, render_static_instruction
from ..rails.prepared_feedback import _read_pinned_json, states_from_contexts, _validate_spec
from ..rails.prepared_text import PREPARED_TEXT_ARM, validate_prepared_text_payload


class PreparedTextSourceError(ValueError):
    """A sealed stage cannot be traced to its registered prepared input."""


def _require(ok, message):
    if not ok:
        raise PreparedTextSourceError(message)


@dataclass(frozen=True)
class VerifiedPreparedTextSource:
    manifest: Mapping
    manifest_sha256: str
    source_binding: Mapping
    prepared_document: Mapping
    rows: Mapping


def verify_prepared_text_source(pin, *, repo_root, data_root, input_schema,
                                artifact_kind, rebuild_contexts, bundle_reader=None):
    """Rebuild one registered stage without contacting a service or interpreting its output."""
    try:
        return _verify(pin, Path(repo_root), Path(data_root), input_schema,
                       artifact_kind, rebuild_contexts, bundle_reader or verify_bundle)
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
        if isinstance(error, PreparedTextSourceError):
            raise
        raise PreparedTextSourceError(f"cannot verify prepared text source: {error}") from error


def _verify(pin, repo, data, input_schema, artifact_kind, rebuild_contexts, bundle_reader):
    manifest, manifest_sha = _read_pinned_json(pin, data_root=data, field="prepared text manifest")
    bundle = bundle_reader(data / pin["relpath"])
    _require(bundle.manifest == manifest, "prepared text manifest changed")
    _require(manifest.get("status") == "COMPLETED" and bundle.attempt_state == "FINALIZED"
             and manifest.get("result_kind") == "artifact" and manifest.get("scorers") == [],
             "prepared stages require a finalized scoreless artifact")
    _require(require_clean_study_repo(repo) == manifest["study_commit"],
             "prepared text source requires its recorded clean checkout")
    fragments = manifest["config"]["fragments"]
    _require(isinstance(fragments, Mapping)
             and set(fragments) == {"model", "dataset", "baseline", "experiment"},
             "prepared text source requires four frozen fragments")
    composed = compose(repo, **fragments)
    values = composed.values
    _require(composed.config_hash == manifest["config"]["config_hash"]
             and values.get("arm") == manifest.get("arm") == PREPARED_TEXT_ARM
             and values.get("result_kind") == "artifact" and values.get("scorers") == [],
             "prepared text source differs from frozen text-only configuration")
    ids = tuple(row["sample_id"] for row in bundle.outputs_rows)
    _require(ids and len(ids) == len(set(ids)) and set(ids) == bundle.split_ids,
             "prepared text output population differs")
    plan = ExecutionPlan(**manifest["plan"]).validate()
    authority = validate_artifact_result_binding(values, plan=plan, repo_root=repo,
                                                 sample_ids=ids, data_root=data)
    _require(authority == manifest["artifact_result"], "prepared text artifact authority differs")
    spec = values["prepared_training_feedback"]
    _require(spec.get("schema") == input_schema, "prepared text input stage differs")
    artifact_pin, source_pin, maximum = _validate_spec(dict(spec, schema="saea-prepared-training-feedback-v1"))
    rebuilt = rebuild_contexts(source_pin, data_root=data)
    source_binding, _ = _read_pinned_json(source_pin, data_root=data, field="actor binding")
    envelope, prepared_sha = _read_pinned_json(artifact_pin, data_root=data, field="prepared text contexts")
    _require(envelope.get("contact_class") == "model-free", "prepared text preparation must be model-free")
    recorded = load_artifact(data / artifact_pin["relpath"], expected_sha256=prepared_sha,
                             kind=artifact_kind, inputs=envelope["inputs"])
    # Old implementation bytes remain pinned by the original artifact and source
    # checkout. Compare reconstructed semantics, not today's implementation hash.
    _require(recorded == rebuilt and envelope["inputs"]["document_sha256"] == content_hash(rebuilt),
             "prepared text prepared content differs from its complete actor source")
    roster_sha = authority["construction_roster"]["sha256"]
    _require(roster_sha == rebuilt["construction_roster_sha256"], "prepared text roster differs")
    contexts = {c["source_sample_id"]: c for c in rebuilt["contexts"]}
    _require(len(contexts) == len(rebuilt["contexts"]), "duplicate actor context")
    states, _ = states_from_contexts(contexts, active_ids=ids, prepared_sha256=prepared_sha,
                                     source_bindings_sha256=rebuilt["source_bindings_sha256"],
                                     roster_sha=roster_sha, maximum=maximum)
    program = default_phase_program(values["policy"])
    materials = load_phase_material_specs(values, program)
    instruction = render_static_instruction(materials["direct"], repo, {}, data)
    requests = {}
    for record_id, record in bundle.trace_records.items():
        if not record_id.endswith("/request") or "payload" not in record:
            continue
        payload = record["payload"]
        validate_prepared_text_payload(payload)
        _speech_history_texts(payload["history"])
        sid, rid = payload["sample_id"], payload["request_id"]
        _require(sid in contexts and sid not in requests and record_id == rid + "/request",
                 "prepared text requests must cover every actor once")
        _require(record.get("payload_sha256") == content_hash(payload), "prepared text request hash differs")
        expected = _agent_history(agent_state=(states[sid].as_json(),),
                                   agent_contact_id=payload["history"][-1]["contact_id"],
                                   contact_instruction=instruction)
        _require(payload["history"] == expected, "prepared text request differs from prepared episode or phase")
        requests[sid] = payload
    _require(set(requests) == set(ids), "prepared text request population differs")
    rows = {}
    for output in bundle.outputs_rows:
        sid = output["sample_id"]
        payload = requests[sid]
        rid = payload["request_id"]
        response = bundle.trace_records[rid + "/response"]
        text = response["text"]
        _require(isinstance(text, str) and output["request_id"] == rid
                 and output["text"] == text
                 and output["response_text_sha256"] == response["response_text_sha256"]
                 == hashlib.sha256(text.encode()).hexdigest(), "prepared text output lineage differs")
        count = response.get("usage", {}).get("completion_tokens")
        cap = payload["decoding_params"].get("max_tokens")
        _require(type(cap) is int and cap > 0, "prepared text output cap is unbound")
        wire = bundle.trace_records.get(rid + "/wire-response", {})
        finish = wire.get("finish_reason")
        status = ("empty" if not text.strip() else
                  "output-limit" if finish == "length" or type(count) is int and count >= cap else
                  "unknown-completion" if type(count) is not int or count < 0 else
                  "nonstandard-finish" if finish not in (None, "stop") else "usable")
        rows[sid] = {
            "sample_id": sid, "text": text, "status": status,
            "source_context_sha256": contexts[sid]["source_feedback_sha256"],
            "manifest_sha256": manifest_sha, "request_id": rid,
            "response_text_sha256": response["response_text_sha256"],
        }
    _read_pinned_json(pin, data_root=data, field="prepared text manifest after read")
    return VerifiedPreparedTextSource(manifest, manifest_sha, source_binding, rebuilt, rows)
