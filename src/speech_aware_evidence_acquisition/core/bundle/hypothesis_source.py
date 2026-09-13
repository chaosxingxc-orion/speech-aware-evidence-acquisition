"""Prepare and verify source-bound hypothesis projections without new inference.

The original failed attempt remains aborted. A separately sealed preparation
artifact binds its original contacts and the explicit deterministic policy.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path

from ...data.splits import prefixed, split_identity_hash
from ...rails.artifact_results import build_slurp_hypothesis_artifact_validator
from ...rails.slurp_intent_hypotheses import (
    FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256,
    project_fixed_three_slurp_intent_hypotheses,
)
from ...reproduction.probe_split import load_verified_probe_split
from ..preparation import artifact_inputs, canonical_bytes, load_artifact, prepare_artifact
from . import BundleError
from .artifacts import VerifiedBundle

PREPARATION_KIND = "distinct-hypothesis-source-v1"
MANIFEST_SCHEMA = "saea-derived-hypothesis-source-v1"
RESULT_BINDING_SCHEMA = "saea-derived-hypothesis-result-binding-v1"


def _read_pin(binding: object, label: str):
    if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
        raise BundleError(f"{label} requires a path and SHA-256")
    try:
        path = Path(binding["path"])
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != binding["sha256"]:
            raise BundleError(f"{label} hash mismatch")
        document = json.loads(raw)
    except (OSError, TypeError, UnicodeError, json.JSONDecodeError) as error:
        raise BundleError(f"cannot read {label}: {error}") from error
    if not isinstance(document, Mapping):
        raise BundleError(f"{label} must be a JSON object")
    return document


def _context(registration_pin, data_root):
    registration = _read_pin(registration_pin, "hypothesis recovery registration")
    if (
        registration.get("schema") != "saea-model-free-hypothesis-recovery-registration-v1"
        or registration.get("execution_profile") != "model-free-check"
        or registration.get("recovery_number") != 1
        or registration.get("original_attempt_state_required") != "ABORTED"
        or registration.get("projection_policy") != FIRST_OCCURRENCE_PROJECTION_POLICY_ID
        or registration.get("contacts") != {
            "model": 0, "tokenizer": 0, "encoder": 0, "asr": 0, "official_scorer": 0,
        }
    ):
        raise BundleError("hypothesis recovery registration identity or scope is invalid")
    roster = _read_pin(registration["full_roster"], "hypothesis full roster")
    roster_path = Path(registration["full_roster"]["path"])
    if roster_path.parent.name != "probe-samples":
        raise BundleError("hypothesis recovery requires the registered probe-sample roster")
    verified = load_verified_probe_split(roster_path.parents[3], roster_path.stem)
    ids = tuple(item["id"] for item in roster["items"])
    if (
        verified.carrier_lock_key != "slurp"
        or len(ids) != len(set(ids))
        or set(ids) != set(verified.ids)
        or verified.split_role != "dev"
        or verified.identity_hash != registration["split_identity_hash"]
    ):
        raise BundleError("hypothesis source roster differs from registration")
    baseline = _read_pin(registration["source_config"], "hypothesis source baseline")
    validator = build_slurp_hypothesis_artifact_validator(
        baseline["artifact_result"]["content_contract"], data_root=Path(data_root)
    )
    return registration, baseline, validator, ids


def _rebuild(registration_pin, data_root, implementation_commit):
    from .raw_contact_source import verify_aborted_contact_source

    registration, baseline, validator, ids = _context(registration_pin, data_root)
    source = verify_aborted_contact_source(
        attempt_pin=registration["source_attempt"],
        trace_pin=registration["source_trace"],
        generation_plan_pin=registration["source_generation_plan"],
        expected_sample_ids=ids,
    )
    producer_id = baseline["policy"]
    producers = [
        (record_id.split("/", 1)[0], payload["use_controller_policy_id"])
        for record_id, payload in source.trace_records.items()
        if "use_controller_policy_id" in payload
    ]
    if (
        len(producers) != len(ids) or {sid for sid, _ in producers} != set(ids)
        or {policy for _, policy in producers} != {producer_id}
    ):
        raise BundleError("hypothesis source runtime producer differs from its baseline")
    rows = []
    for sample_id in sorted(ids):
        contact = source.contacts_by_sample_id[sample_id]
        response = contact["response"]
        projected = project_fixed_three_slurp_intent_hypotheses(
            response["text"], sample_id=sample_id, legal_intent_ids=validator.legal_intent_ids
        )
        rows.append({
            "sample_id": sample_id,
            "request_id": contact["request_id"],
            "request_sha256": contact["request"]["payload_sha256"],
            "text": response["text"],
            "response_text_sha256": response["response_text_sha256"],
            "artifact_role": "slurp-intent-hypotheses",
            "artifact_content": projected.content,
            "artifact_content_sha256": projected.projected_content_sha256,
            "projection_policy_id": projected.projection_policy_id,
            "projection_policy_sha256": projected.projection_policy_sha256,
            "original_text_sha256": projected.original_text_sha256,
            "raw_positions": [asdict(position) for position in projected.raw_positions],
        })
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "status": "COMPLETED_DERIVATION",
        "result_kind": "artifact",
        "run_id": registration["experiment_id"],
        "source_run_id": source.attempt["run_id"],
        "source_attempt_state": "ABORTED",
        "study_commit": implementation_commit,
        "producer_policy_id": producer_id,
        "artifact_result": {
            "schema": RESULT_BINDING_SCHEMA, "role": "slurp-intent-hypotheses",
            "projection_policy_id": FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
            "projection_policy_sha256": FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256,
            "candidate_count": {"minimum": 1, "maximum": 3},
        },
        "split": {
            "carrier_lock_key": "slurp", "role": "dev",
            "ids": sorted(ids), "count": len(ids),
            "identity_hash": split_identity_hash(prefixed("slurp", ids)),
        },
        "registration": dict(registration_pin),
        "data_root": str(Path(data_root).resolve()),
        "source_inputs": {
            key: registration[key] for key in (
                "source_attempt", "source_trace", "source_generation_plan", "source_config", "full_roster"
            )
        },
        "contact_accounting": {
            "new_model_calls": 0,
            "new_tool_calls": 0,
            "source_model_calls": source.attempt["actual"]["calls"],
            "source_audio_seconds": source.attempt["actual"]["audio_seconds"],
            "source_counted_once": True,
        },
        "scorers": [],
        "rows": rows,
    }
    return manifest, source


def _inputs(registration_pin, data_root, implementation_commit):
    registration, _, _, _ = _context(registration_pin, data_root)
    if (
        not isinstance(implementation_commit, str) or len(implementation_commit) != 40
        or any(ch not in "0123456789abcdef" for ch in implementation_commit)
    ):
        raise BundleError("hypothesis preparation requires a full implementation commit")
    return artifact_inputs(
        config={
            "projection_policy_id": FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
            "projection_policy_sha256": FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256,
            "implementation_commit": implementation_commit,
            "data_root": str(Path(data_root).resolve()),
        },
        split_identity_hash=registration["split_identity_hash"],
        sources={"registration": dict(registration_pin)},
    )


def prepare_hypothesis_source(*, registration_path: Path, data_root: Path, implementation_commit: str):
    """Seal a separately identified source through shared preparation locks/cache."""
    registration_path = Path(registration_path).resolve()
    registration_pin = {
        "path": str(registration_path),
        "sha256": hashlib.sha256(registration_path.read_bytes()).hexdigest(),
    }
    registration, _, _, _ = _context(registration_pin, data_root)
    root = Path(data_root).resolve()
    output_dir = (root / registration["output_relpath"]).resolve()
    if not output_dir.is_relative_to(root) or output_dir == root:
        raise BundleError("hypothesis preparation output must remain inside the data root")
    path = output_dir / "hypotheses.source.json"
    inputs = _inputs(registration_pin, root, implementation_commit)
    receipt = prepare_artifact(
        path, kind=PREPARATION_KIND, inputs=inputs,
        producer=lambda: _rebuild(registration_pin, root, implementation_commit)[0],
        contact_class="model-free",
    )
    verified = verify_hypothesis_source(path)
    return {**receipt, "sample_count": len(verified.split_ids), "source_attempt_state": "ABORTED",
            "attempt_state": "DERIVED", "new_model_calls": 0}


def verify_hypothesis_source(manifest_path: Path) -> VerifiedBundle:
    """Recompute every projection from its unchanged original contact source."""
    manifest_path = Path(manifest_path)
    raw = manifest_path.read_bytes()
    document = json.loads(raw)
    if (
        document.get("schema") != "saea-prepared-artifact-v1"
        or document.get("kind") != PREPARATION_KIND
        or document.get("contact_class") != "model-free"
    ):
        raise BundleError("hypothesis source must be an explicitly model-free prepared artifact")
    output = document.get("output")
    if not isinstance(output, Mapping) or output.get("schema") != MANIFEST_SCHEMA:
        raise BundleError("hypothesis source output schema is invalid")
    registration_pin = output.get("registration")
    data_root = Path(output["data_root"])
    implementation_commit = output["study_commit"]
    inputs = _inputs(registration_pin, data_root, implementation_commit)
    verified_output = load_artifact(
        manifest_path, expected_sha256=hashlib.sha256(raw).hexdigest(),
        kind=PREPARATION_KIND, inputs=inputs,
    )
    registration = _read_pin(registration_pin, "hypothesis recovery registration")
    expected_path = (data_root / registration["output_relpath"] / "hypotheses.source.json").resolve()
    if manifest_path.resolve() != expected_path:
        raise BundleError("hypothesis source path differs from registered output")
    rebuilt, source = _rebuild(registration_pin, data_root, implementation_commit)
    if canonical_bytes(verified_output) != canonical_bytes(rebuilt):
        raise BundleError("hypothesis projection differs from deterministic source replay")
    return VerifiedBundle(
        manifest_path=manifest_path,
        manifest=rebuilt,
        outputs_path=None,
        outputs_rows=tuple(rebuilt["rows"]),
        trace_records=source.trace_records,
        split_ids=frozenset(rebuilt["split"]["ids"]),
        attempt_state="DERIVED",
    )


def is_derived_hypothesis_bundle(verified: VerifiedBundle) -> bool:
    """Recognize only the explicitly verified, separately identified source kind."""
    manifest = getattr(verified, "manifest", None)
    if not isinstance(manifest, Mapping):
        return False
    binding = manifest.get("artifact_result")
    return (
        getattr(verified, "attempt_state", None) == "DERIVED"
        and manifest.get("schema") == MANIFEST_SCHEMA
        and manifest.get("status") == "COMPLETED_DERIVATION"
        and manifest.get("source_attempt_state") == "ABORTED"
        and manifest.get("result_kind") == "artifact"
        and isinstance(binding, Mapping)
        and binding.get("schema") == RESULT_BINDING_SCHEMA
        and binding.get("role") == "slurp-intent-hypotheses"
        and binding.get("projection_policy_id") == FIRST_OCCURRENCE_PROJECTION_POLICY_ID
        and binding.get("projection_policy_sha256") == FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256
    )
