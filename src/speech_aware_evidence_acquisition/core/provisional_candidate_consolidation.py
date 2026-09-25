"""Materialize a sealed consolidation chain through the existing candidate path.

Rebuild original proposal authority for every round; never load an unauthenticated
candidate snapshot as a root. Consolidation may select/revise existing proposals
only. This proves lineage, not semantic-stage fidelity or scientific admission.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from .bundle.verify import verify_bundle
from .config import _reject_duplicate_keys
from .preparation import hash_stable_file, load_artifact, prepare_artifact
from . import provisional_candidate_materialization as materialization
from ..rails.experience_consolidation import (
    consolidate_experience_candidates,
    initialize_candidate_snapshot,
)
from ..rails.experience_memory import ExperienceRecord

CONFIG_SCHEMA = "saea-provisional-consolidation-materialization-config-v1"
OUTPUT_SCHEMA = "saea-provisional-consolidated-experience-candidates-v1"
ROUND_KEYS = {
    "round_id",
    "proposal_materialization",
    "consolidation_bundle",
    "consolidation_sample_id",
    "consolidation_protocol_hash",
    "base_snapshot_sha256",
}


def _require(condition, message):
    if not condition:
        raise materialization.MaterializationError(message)


def _original(pin, data_root, guards):
    """Rebuild one original typed-proposal source; forbid recursive config roots."""
    path, expected = materialization._path_pin(pin, "original materialization")
    config, actual, fingerprint = materialization._load_config(path, expected)
    _require(
        config["schema"] == materialization.CONFIG_SCHEMA,
        "lineage roots must be original proposal materializations",
    )
    result = materialization.prepare_provisional_candidates(
        config_path=path,
        expected_config_sha256=expected,
        data_root=data_root,
    )
    candidate_path = Path(result["path"])
    _, raw, digest, candidate_fingerprint = materialization._stable_pinned_bytes(
        {"path": str(candidate_path), "sha256": result["sha256"]},
        "original candidates",
    )
    wrapper = json.loads(raw)
    output = load_artifact(
        candidate_path,
        expected_sha256=digest,
        kind=materialization.ARTIFACT_KIND,
        inputs=wrapper["inputs"],
    )
    _require(
        output["schema"] == materialization.OUTPUT_SCHEMA,
        "original candidate schema differs",
    )
    guards.extend(
        [
            (path, actual, fingerprint, "original materialization config"),
            (
                candidate_path,
                digest,
                candidate_fingerprint,
                "original candidate artifact",
            ),
        ]
    )
    prepared_pin = config["prepared_contexts"]
    prepared_path = materialization._data_path(
        data_root,
        prepared_pin["data_relpath"],
        "original prepared contexts",
    )
    _, prepared_raw, _, prepared_guard = materialization._stable_pinned_bytes(
        {"path": str(prepared_path), "sha256": prepared_pin["sha256"]},
        "original prepared contexts",
    )
    # prepare_provisional_candidates has already reconstructed these exact bytes
    # from complete, finalized reward sources. The hash here is that feedback's
    # provenance, not a new scalar reward or an upstream semantic-comparison result.
    feedback_sha = materialization._sha(
        json.loads(prepared_raw)["output"]["feedback_sha256"],
        "verified feedback",
    )
    guards.append(
        (
            prepared_path,
            prepared_pin["sha256"],
            prepared_guard,
            "original prepared contexts",
        )
    )
    return output, result, feedback_sha


def _records(output):
    return tuple(
        ExperienceRecord.from_json(record)
        for row in output["samples"]
        for record in row["records"]
    )


def _plan(round_spec, roster, guards):
    path, raw, digest, fingerprint = materialization._stable_pinned_bytes(
        round_spec["consolidation_bundle"],
        "consolidation manifest",
    )
    bundle = verify_bundle(path)
    manifest = bundle.manifest
    _require(
        json.loads(raw) == manifest, "verified consolidation manifest differs from pin"
    )
    _require(
        manifest.get("status") == "COMPLETED"
        and bundle.attempt_state == "FINALIZED"
        and manifest.get("result_kind") == "artifact"
        and manifest.get("scorers") == [],
        "consolidation requires a finalized scoreless artifact",
    )
    role = manifest.get("artifact_result", {})
    _require(
        role.get("schema") == "saea-artifact-result-binding-v1"
        and role.get("role") == "training-feedback-proposal",
        "consolidation must use the existing scoreless construction artifact contract",
    )
    expected_protocol = materialization._sha(
        round_spec["consolidation_protocol_hash"],
        "consolidation protocol",
    )
    _require(
        manifest.get("protocol_hash") == expected_protocol,
        "consolidation protocol differs",
    )
    anchor = round_spec["consolidation_sample_id"]
    _require(
        isinstance(anchor, str) and anchor in roster,
        "consolidation anchor is outside construction",
    )
    split = manifest.get("split", {})
    _require(
        split.get("role") == "discovery"
        and split.get("carrier_lock_key") == "slurp"
        and split.get("ids") == [anchor],
        "consolidation split differs",
    )
    rows = tuple(bundle.outputs_rows)
    _require(
        len(rows) == 1 and rows[0].get("sample_id") == anchor,
        "consolidation requires exactly its registered anchor output",
    )
    response = rows[0].get("text")
    _require(isinstance(response, str), "consolidation response is missing")
    try:
        plan = json.loads(response, object_pairs_hook=_reject_duplicate_keys(path))
    except json.JSONDecodeError as error:
        raise materialization.MaterializationError(
            "consolidation response is not JSON"
        ) from error
    _require(
        isinstance(plan, Mapping) and set(plan) == {"operations"},
        "model consolidation output must contain operations only",
    )
    guards.append((path, digest, fingerprint, "consolidation manifest"))
    return plan, {
        "manifest_sha256": digest,
        "run_id": manifest["run_id"],
        "protocol_hash": expected_protocol,
        "sample_id": anchor,
        "response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
    }


def prepare_consolidated_candidates(*, config_path, expected_config_sha256, data_root):
    """Replay every sealed operation before writing one immutable candidate artifact.

    Append rounds to a new config/output identity. Earlier rounds are replayed,
    preserving their IDs and deleted-ID history. The original materializer,
    common preparation cache, existing source attestation and runtime candidate
    reader remain authoritative; this function never activates a memory pack.
    """
    config_path, data_root = Path(config_path).resolve(), Path(data_root).resolve()
    config, config_sha, fingerprint = materialization._load_config(
        config_path,
        expected_config_sha256,
    )
    _require(config["schema"] == CONFIG_SCHEMA, "consolidation config schema differs")
    memory_id = config["memory_id"]
    _require(
        isinstance(memory_id, str) and bool(memory_id.strip()),
        "memory_id must be nonempty",
    )
    rounds = config["rounds"]
    _require(
        isinstance(rounds, list) and bool(rounds),
        "consolidation rounds must be nonempty",
    )
    round_ids = set()
    for spec in rounds:
        _require(
            isinstance(spec, Mapping) and set(spec) == ROUND_KEYS,
            "consolidation round fields differ",
        )
        rid = spec["round_id"]
        _require(
            isinstance(rid, str) and bool(rid.strip()) and rid not in round_ids,
            "round IDs must be nonempty and unique",
        )
        round_ids.add(rid)
    guards = [(config_path, config_sha, fingerprint, "consolidation config")]
    try:
        initial = None
        if config["initial_materialization"] is not None:
            initial = _original(config["initial_materialization"], data_root, guards)
        snapshot, roster, construction = None, None, None
        receipts, sources = [], []
        for spec in rounds:
            proposal_output, proposal_receipt, feedback_sha = _original(
                spec["proposal_materialization"],
                data_root,
                guards,
            )
            current_roster = [
                row["source_sample_id"] for row in proposal_output["samples"]
            ]
            current_construction = proposal_output["provenance"][
                "construction_roster_sha256"
            ]
            if snapshot is None:
                roster, construction = current_roster, current_construction
                if initial is not None:
                    _require(
                        [row["source_sample_id"] for row in initial[0]["samples"]]
                        == roster
                        and initial[0]["provenance"]["construction_roster_sha256"]
                        == construction,
                        "initial materialization construction differs",
                    )
                snapshot = initialize_candidate_snapshot(
                    memory_id=memory_id,
                    train_construction_sha256=construction,
                    expected_train_sample_ids=roster,
                    records=_records(initial[0]) if initial is not None else (),
                )
            _require(
                current_roster == roster and current_construction == construction,
                "round construction roster differs",
            )
            expected_base = materialization._sha(
                spec["base_snapshot_sha256"], "base snapshot"
            )
            _require(
                snapshot["content_sha256"] == expected_base,
                "registered base snapshot differs from replay",
            )
            model_plan, source = _plan(spec, roster, guards)
            # Custody metadata is bound by the registered configuration, never
            # authored, repaired or guessed by the model.
            plan = {
                "base_snapshot_sha256": expected_base,
                "operations": model_plan["operations"],
            }
            source["base_snapshot_sha256"] = expected_base
            proposals = {
                record.record_id: record for record in _records(proposal_output)
            }
            _require(
                len(proposals)
                == sum(len(row["records"]) for row in proposal_output["samples"]),
                "proposal identities repeat",
            )
            receipt = consolidate_experience_candidates(
                snapshot,
                plan,
                proposals,
                round_id=spec["round_id"],
                source_bindings={
                    "complete_system_feedback_sha256": feedback_sha,
                    "proposal_artifact_sha256": proposal_receipt["sha256"],
                    "consolidation_response_sha256": source["response_sha256"],
                },
            )
            if receipt["status"] not in {"applied", "unchanged"}:
                for guard in guards:
                    materialization._assert_unchanged(*guard)
                refusal = prepare_artifact(
                    data_root
                    / "provisional/experience-consolidation-rejections"
                    / (config["materialization_id"] + ".json"),
                    kind="experience-consolidation-rejection",
                    inputs={
                        "materialization_config_sha256": config_sha,
                        "consolidation_manifest_sha256": source["manifest_sha256"],
                        "proposal_artifact_sha256": proposal_receipt["sha256"],
                        "receipt_sha256": receipt["content_sha256"],
                    },
                    producer=lambda: {
                        "schema": "saea-candidate-consolidation-rejection-v1",
                        "round_id": spec["round_id"],
                        "receipt": receipt,
                        "prior_round_receipts": receipts,
                        "runtime_authorized": False,
                    },
                    contact_class="model-free",
                )
                raise materialization.MaterializationError(
                    f"consolidation rejected: {receipt['error']}; receipt {refusal['path']}"
                )
            snapshot = receipt["snapshot"]
            _require(
                len(snapshot["records"]) <= config["max_candidates"],
                "consolidation exceeds max_candidates; no truncation",
            )
            receipts.append(receipt)
            sources.append(
                {
                    "round_id": spec["round_id"],
                    "proposal_artifact_sha256": proposal_receipt["sha256"],
                    "proposal_feedback_sha256": feedback_sha,
                    **source,
                }
            )
        assert snapshot is not None
        samples = [
            {
                "source_sample_id": sid,
                "records": [
                    record
                    for record in snapshot["records"]
                    if record["source"]["source_sample_id"] == sid
                ],
            }
            for sid in roster
        ]
        output = {
            "schema": OUTPUT_SCHEMA,
            "status": "provisional",
            "materialization_id": config["materialization_id"],
            "provenance": {
                "source_kind": "sealed-consolidation-chain",
                "materialization_config_sha256": config_sha,
                "construction_roster_sha256": construction,
                "initial_candidate_artifact_sha256": initial[1]["sha256"]
                if initial
                else None,
                "round_sources": sources,
            },
            "samples": samples,
            "candidate_snapshot": snapshot,
            "consolidation_receipts": receipts,
            "interpretation": "Verified provisional lineage only; no admission or semantic-stage fidelity claim.",
        }
        inputs = {
            "materialization_config_sha256": config_sha,
            "construction_roster_sha256": construction,
            "implementation_sha256": hash_stable_file(
                Path(__file__), "consolidation materializer"
            )[1],
            "original_materializer_sha256": hash_stable_file(
                Path(materialization.__file__), "original materializer"
            )[1],
            "applier_sha256": hash_stable_file(
                Path(__file__).parent.parent / "rails/experience_consolidation.py",
                "consolidation applier",
            )[1],
            "round_sources": sources,
            "initial_candidate_artifact_sha256": initial[1]["sha256"]
            if initial
            else None,
        }
        for guard in guards:
            materialization._assert_unchanged(*guard)
        result = prepare_artifact(
            data_root
            / "provisional/experience-candidates"
            / (config["materialization_id"] + ".json"),
            kind=materialization.ARTIFACT_KIND,
            inputs=inputs,
            producer=lambda: output,
            contact_class="model-free",
        )
        for guard in guards:
            materialization._assert_unchanged(*guard)
        return result
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as error:
        if isinstance(error, materialization.MaterializationError):
            raise
        raise materialization.MaterializationError(
            f"consolidation source replay failed: {error}"
        ) from error
