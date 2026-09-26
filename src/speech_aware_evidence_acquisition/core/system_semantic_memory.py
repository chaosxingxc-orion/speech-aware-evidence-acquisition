"""Materialize model-synthesized whole-system guidance through the shared memory path."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from . import provisional_candidate_materialization as materialization
from .config import ConfigError, _reject_duplicate_keys
from .preparation import prepare_artifact, hash_stable_file
from .provisional_candidate_consolidation import OUTPUT_SCHEMA
from ..analysis.prepared_text_source import verify_prepared_text_source
from ..rails.experience_consolidation import consolidate_experience_candidates
from ..rails.experience_memory import ExperienceRecord, ExperienceSource, Applicability, SourceRef, ValidationBinding
from ..rails.hashing import content_hash
from ..rails.system_batch_update_context import PREPARED_SCHEMA, KIND, build_system_batch_update_contexts
from ..rails.training_feedback_artifacts import training_feedback_validator_for_options

CONFIG_SCHEMA = "saea-system-semantic-memory-materialization-v1"
SOURCE_KIND = "sealed-system-semantic-batch"


def _require(ok, message):
    if not ok:
        raise materialization.MaterializationError(message)


def parse_batch_operations(raw_text, document, anchor):
    """Validate typed content and frozen targets without choosing or rewriting model text."""
    try:
        value = json.loads(raw_text, object_pairs_hook=_reject_duplicate_keys(Path("batch-response.json")))
    except ConfigError as error:
        raise materialization.MaterializationError(str(error)) from error
    _require(isinstance(value, Mapping) and set(value) == {"operations"}, "batch operation fields differ")
    operations = value["operations"]
    _require(isinstance(operations, list) and len(operations) <= document["max_operations"],
             "batch operation count exceeds registration")
    targets = {r["record_id"] for r in document["base_snapshot"]["records"]}
    labels = frozenset(row["label"] for row in document["source_groups"])
    validator = training_feedback_validator_for_options(
        {**document["proposal_contract"], "max_proposals": 1}, {anchor: labels},
        document["source_bindings_sha256"])
    normalized, seen = [], set()
    for operation in operations:
        _require(isinstance(operation, Mapping)
                 and set(operation) == {"operation", "record_id", "proposal"}, "batch operation fields differ")
        op, target, proposal = operation["operation"], operation["record_id"], operation["proposal"]
        _require(isinstance(op, str) and op in {"ADD", "UPDATE", "DELETE"}, "unknown batch operation")
        if op == "ADD":
            _require(target is None, "ADD cannot assign a record ID")
        else:
            _require(isinstance(target, str) and target in targets and target not in seen,
                     "batch target is unknown, repeated or created in this plan")
            seen.add(target)
        if op == "DELETE":
            _require(proposal is None, "DELETE cannot contain synthesized guidance")
            normalized.append(dict(operation))
        else:
            canonical = json.loads(validator.canonicalize(
                json.dumps({"status": "provisional", "proposals": [proposal]}), sample_id=anchor))
            normalized.append({"operation": op, "record_id": target, "proposal": canonical["proposals"][0]})
    if "max_memory_records" in document:
        final_count = len(targets) + sum(op["operation"] == "ADD" for op in normalized) - sum(
            op["operation"] == "DELETE" for op in normalized)
        _require(final_count <= document["max_memory_records"],
                 "final memory record count exceeds registered max_memory_records; no truncation")
    return normalized


def synthesize_records(operations, document, *, manifest_sha, protocol_sha, response_sha, config_sha):
    """Assign provenance to new model content from exact composite source groups."""
    groups = {row["label"]: row for row in document["source_groups"]}
    full_sha = document["base_snapshot"]["train_construction_sha256"]
    records, plan = {}, []
    decision_sha = content_hash({"materialization_config_sha256": config_sha,
                                 "operations_sha256": content_hash(operations), "admission": "none"})
    for i, op in enumerate(operations):
        if op["operation"] == "DELETE":
            plan.append({"operation": "DELETE", "record_id": op["record_id"]})
            continue
        proposal = op["proposal"]
        primary = groups[proposal["primary_option"]]
        record_id = "semantic-proposal-" + content_hash({"manifest": manifest_sha, "index": i})
        record = ExperienceRecord.create(
            record_id=record_id, revision=1, kind=proposal["kind"], train_construction_sha256=full_sha,
            source=ExperienceSource.from_json(primary["source"]),
            applicability=Applicability.from_json(proposal["applicability"]),
            diagnosis=proposal["diagnosis"], guidance=proposal["guidance"], limitations=proposal["limitations"],
            supporting_source_refs=tuple(SourceRef.from_json(groups[g]["source_ref"]) for g in proposal["supporting_options"]),
            contradicting_source_refs=tuple(SourceRef.from_json(groups[g]["source_ref"]) for g in proposal["contradicting_options"]),
            validation=ValidationBinding("provisional", decision_sha, protocol_sha, full_sha, response_sha))
        records[record_id] = record
        step = {"operation": op["operation"], "proposal_id": record_id}
        if op["operation"] == "UPDATE":
            step["record_id"] = op["record_id"]
        plan.append(step)
    return records, {"base_snapshot_sha256": document["base_snapshot"]["content_sha256"], "operations": plan}


def prepare_system_semantic_memory(*, config_path, expected_config_sha256, data_root):
    """Rebuild sealed inputs, retain a rejected model plan or publish one atomic successor."""
    config_path, data_root = Path(config_path).resolve(), Path(data_root).resolve()
    config, config_sha, fingerprint = materialization._load_config(config_path, expected_config_sha256)
    _require(config["schema"] == CONFIG_SCHEMA, "semantic memory configuration differs")
    manifest_path, expected = materialization._path_pin(config["batch_manifest"], "batch manifest")
    _require(manifest_path.resolve().is_relative_to(data_root), "batch manifest must remain in DATA")
    repo = config["batch_repo_root"]
    _require(isinstance(repo, str) and Path(repo).is_absolute(), "batch checkout must be absolute")
    source = verify_prepared_text_source(
        {"relpath": manifest_path.resolve().relative_to(data_root).as_posix(), "sha256": expected},
        repo_root=repo, data_root=data_root, input_schema=PREPARED_SCHEMA,
        artifact_kind=KIND, rebuild_contexts=build_system_batch_update_contexts)
    document = source.prepared_document
    anchor = document["full_construction_sample_ids"][0]
    _require(set(source.rows) == {anchor}, "batch requires one registered full-input synthesis")
    row = source.rows[anchor]
    binding = {"schema": CONFIG_SCHEMA, "materialization_config_sha256": config_sha,
               "batch_manifest_sha256": source.manifest_sha256, "batch_response": row,
               "base_snapshot_sha256": document["base_snapshot"]["content_sha256"],
               "runtime_authorized": False,
               **{k: document[k] for k in ("max_memory_records",) if k in document}}
    try:
        if "max_memory_records" in document:
            _require(config["max_candidates"] == document["max_memory_records"],
                     "materialization candidate cap differs from model-visible max_memory_records")
        _require(row["status"] == "usable", "batch response is unusable; no recovery or truncation")
        operations = parse_batch_operations(row["text"], document, anchor)
        records, plan = synthesize_records(
            operations, document, manifest_sha=source.manifest_sha256,
            protocol_sha=source.manifest["plan"]["protocol_hash"],
            response_sha=row["response_text_sha256"], config_sha=config_sha)
        proposed = prepare_artifact(
            data_root / "provisional/system-semantic-proposals" / (config["materialization_id"] + ".json"),
            kind="system-semantic-proposals",
            inputs={"batch_manifest_sha256": source.manifest_sha256, "configuration_sha256": config_sha},
            producer=lambda: {**binding, "operations": operations, "records": [r.as_json() for r in records.values()],
                              "source_groups": document["source_groups"]}, contact_class="model-free")
        receipt = consolidate_experience_candidates(
            document["base_snapshot"], plan, records, round_id=document["round_id"],
            source_bindings={
                "complete_system_feedback_sha256": document["group_operation_report"]["content_sha256"],
                "proposal_artifact_sha256": proposed["sha256"],
                "consolidation_response_sha256": row["response_text_sha256"]})
        _require(receipt["status"] in {"applied", "unchanged"}, "atomic semantic update rejected: " + str(receipt["error"]))
        snapshot = receipt["snapshot"]
        _require(len(snapshot["records"]) <= config["max_candidates"], "candidate cap exceeded; no selection or truncation")
    except (ValueError, KeyError, TypeError) as error:
        materialization._assert_unchanged(config_path, config_sha, fingerprint, "semantic memory config")
        rejection = {**binding, "error": str(error), "status": "rejected", "snapshot": None}
        refusal = prepare_artifact(
            data_root / "provisional/system-semantic-rejections" / (config["materialization_id"] + ".json"),
            kind="system-semantic-rejection", inputs={"configuration_sha256": config_sha, "batch_manifest_sha256": expected},
            producer=lambda: rejection,
            contact_class="model-free")
        raise materialization.MaterializationError(f"semantic batch rejected; retained at {refusal['path']}: {error}") from error
    full_sha = document["base_snapshot"]["train_construction_sha256"]
    memory_ids = document.get("memory_construction", {}).get("sample_ids", document["full_construction_sample_ids"])
    output = {
        "schema": OUTPUT_SCHEMA, "status": "provisional", "materialization_id": config["materialization_id"],
        "provenance": {
            "source_kind": SOURCE_KIND, "materialization_config_sha256": config_sha,
            "construction_roster_sha256": full_sha, "batch_manifest_sha256": source.manifest_sha256,
            "group_operation_report_sha256": document["group_operation_report"]["content_sha256"],
            "proposal_artifact_sha256": proposed["sha256"]},
        "samples": [{"source_sample_id": sid, "records": [r for r in snapshot["records"]
                     if r["source"]["source_sample_id"] == sid]} for sid in memory_ids],
        "candidate_snapshot": snapshot, "consolidation_receipts": [receipt],
        "interpretation": "Model-synthesized provisional content, not validation or runtime admission.",
    }
    inputs = {"materialization_config_sha256": config_sha, "construction_roster_sha256": full_sha,
              "batch_manifest_sha256": source.manifest_sha256, "proposal_artifact_sha256": proposed["sha256"],
              "implementation_sha256": hash_stable_file(Path(__file__), "semantic materialization")[1]}
    materialization._assert_unchanged(config_path, config_sha, fingerprint, "semantic memory config")
    result = prepare_artifact(
        data_root / "provisional/experience-candidates" / (config["materialization_id"] + ".json"),
        kind=materialization.ARTIFACT_KIND, inputs=inputs, producer=lambda: output, contact_class="model-free")
    materialization._assert_unchanged(config_path, config_sha, fingerprint, "semantic memory config")
    return result
