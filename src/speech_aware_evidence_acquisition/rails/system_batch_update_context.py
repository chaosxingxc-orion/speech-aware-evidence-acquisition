"""Prepare one complete model-facing batch synthesis over frozen group operations."""
from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path

from ..analysis.system_group_operations import read_system_group_operations
from ..core.preparation import hash_stable_file, prepare_artifact
from .experience_memory import ExperienceSource
from .experience_memory_runtime import MAX_RUNTIME_RECORDS, PROJECTED_CONDITION_TAGS
from .experience_memory_sources import system_group_hash_source_ref
from .hashing import content_hash
from .prepared_feedback import (
    PreparedFeedbackError, _read_pinned_json, _resolve_data_path, _canonical_context,
    load_verified_prepared_contexts,
)
from .system_group_update_context import _roster
from .training_feedback_artifacts import training_feedback_validator_for_options

SOURCE_SCHEMA = "saea-system-batch-update-source-v1"
BOUNDED_SOURCE_SCHEMA = "saea-system-batch-update-source-v2"
PREPARED_SCHEMA = "saea-prepared-system-batch-update-v1"
KIND = "system-batch-update-contexts"


def _require(value, message):
    if not value:
        raise PreparedFeedbackError(message)


def experience_group_binding(group):
    """Project a composite source without pretending it is a single actor trajectory."""
    _require(isinstance(group, Mapping) and set(group) == {
        "schema", "sample_id", "input_group_sha256", "members", "frozen_f0"
    } and group["schema"] == "saea-complete-system-feedback-group-source-v1",
             "whole-system group source fields differ")
    members = group["members"]
    _require(isinstance(members, list) and len(members) >= 2, "whole-system source needs paired actors")
    identity = [(m["run_id"], m["attempt_id"]) for m in members]
    _require(len(set(identity)) == len(identity), "whole-system source repeats an actor")
    source = ExperienceSource(
        "train", group["sample_id"],
        content_hash([m["trajectory_sha256"] for m in members]),
        content_hash([m["action_sha256"] for m in members]),
        content_hash([m["response_sha256"] for m in members]),
        content_hash({"frozen_f0": group["frozen_f0"],
                      "outcomes": [{"official_feedback_sha256": m["official_feedback_sha256"],
                                    "outcome": m["outcome"]} for m in members]}))
    source.validate()
    sha = content_hash(group)
    return {"group_sha256": sha, "source": source.as_json(),
            "source_ref": system_group_hash_source_ref(sha).as_json(),
            "group": copy.deepcopy(group)}


def build_system_batch_update_contexts(source_pin, *, data_root):
    try:
        return _build(source_pin, Path(data_root))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        if isinstance(error, PreparedFeedbackError):
            raise
        raise PreparedFeedbackError(f"cannot prepare batch synthesis: {error}") from error


def _build(source_pin, data):
    binding, binding_sha = _read_pinned_json(source_pin, data_root=data, field="batch update source")
    _require(isinstance(binding, Mapping), "batch source fields differ")
    bounded = binding.get("schema") == BOUNDED_SOURCE_SCHEMA
    fields = {"schema", "group_update_manifest", "group_update_repo_root", "batch_roster",
              "max_operations", "proposal_contract"}
    if bounded:
        fields.add("max_memory_records")
    _require(set(binding) == fields and binding["schema"] in {SOURCE_SCHEMA, BOUNDED_SOURCE_SCHEMA},
             "batch source fields differ")
    pool_contract = {}
    if bounded:
        limit = binding["max_memory_records"]
        _require(type(limit) is int and 1 <= limit <= MAX_RUNTIME_RECORDS,
                 f"max_memory_records must be an integer from 1 to {MAX_RUNTIME_RECORDS}")
        pool_contract["max_memory_records"] = limit
    repo = binding["group_update_repo_root"]
    _require(isinstance(repo, str) and Path(repo).is_absolute(), "group update checkout must be absolute")
    maximum = binding["max_operations"]
    _require(type(maximum) is int and maximum > 0, "max_operations must be positive")
    report = read_system_group_operations(binding["group_update_manifest"], repo_root=repo, data_root=data)
    contract = binding["proposal_contract"]
    _require(isinstance(contract, Mapping) and set(contract) == {
        "applicability", "max_diagnosis_chars", "max_guidance_chars", "max_limitation_chars",
        "max_limitations", "max_option_refs",
    }, "batch proposal contract fields differ")
    full_ids = report["full_construction_sample_ids"]
    _require(full_ids and [g["sample_id"] for g in report["population"]] == full_ids,
             "batch lost full construction population")
    snapshot = report["base_snapshot"]
    memory_scope = report.get("memory_construction", {
        "sample_ids": full_ids, "roster_sha256": report["source_construction_roster_sha256"]})
    _require(snapshot["train_sample_ids"] == sorted(memory_scope["sample_ids"])
             and snapshot["train_construction_sha256"] == memory_scope["roster_sha256"],
             "batch base memory construction differs")
    visible, bindings = [], []
    for group in report["population"]:
        if group["disposition"] != "ready":
            continue
        operations = group["parsed"]["operations"]
        if not any(op["operation"] != "NONE" for op in operations):
            continue
        label = f"group-{len(bindings) + 1}"
        source = experience_group_binding(group["experience_source"])
        _require(source["source"]["source_sample_id"] == group["sample_id"], "batch group source sample differs")
        bindings.append({"label": label, **source})
        visible.append({"label": label, "operations": copy.deepcopy(operations)})
    labels = frozenset(row["label"] for row in bindings)
    anchor = full_ids[0]
    validator = training_feedback_validator_for_options(
        {**contract, "max_proposals": 1}, {anchor: labels}, report["source_manifest_sha256"])
    scope = {
        "task_ids": sorted(validator.allowed_task_ids), "phases": sorted(validator.allowed_roles),
        "component_tags": sorted(validator.allowed_component_tags),
        "condition_tags": sorted(PROJECTED_CONDITION_TAGS),
        "max_diagnosis_chars": validator.max_diagnosis_chars,
        "max_guidance_chars": validator.max_guidance_chars,
        "max_limitation_chars": validator.max_limitation_chars,
        "max_limitations": validator.max_limitations, "max_option_refs": validator.max_option_refs,
    }
    memory = [{k: copy.deepcopy(rec[k]) for k in
               ("record_id", "kind", "diagnosis", "guidance", "limitations", "applicability")}
              for rec in snapshot["records"]]
    context = {
        "stage": "complete-system-batch-update", "existing_experiences": memory,
        **pool_contract,
        "group_operations": visible, "proposal_scope": scope, "max_operations": maximum,
        "source_semantics": "Each group label denotes its complete paired system trajectories and terminal feedback, not one actor or a causal component effect.",
    }
    _require(not bounded or bindings or len(memory) <= pool_contract["max_memory_records"],
             "unchanged memory record count exceeds max_memory_records")
    _canonical_context(context)
    roster_sha = None
    if binding["batch_roster"] is not None:
        ids, roster_sha = _roster(binding["batch_roster"], data, "batch anchor roster")
        _require(bool(bindings) and ids == [anchor], "batch anchor must be the first full construction sample with a nonempty update batch")
    return {
        "schema": "saea-system-batch-update-contexts-v2" if bounded else "saea-system-batch-update-contexts-v1",
        "source_bindings_sha256": binding_sha, **pool_contract,
        "construction_roster_sha256": roster_sha,
        "source_construction_roster_sha256": report["source_construction_roster_sha256"],
        "full_construction_sample_ids": full_ids, "round_id": report["round_id"],
        "group_operation_report": report, "base_snapshot": snapshot, "source_groups": bindings,
        **{k: report[k] for k in ("memory_construction", "round_policy_receipt") if k in report},
        "proposal_contract": dict(contract), "max_operations": maximum,
        "contexts": [{"source_sample_id": anchor, "source_feedback_sha256": report["content_sha256"],
                      "model_context": context, "model_context_sha256": content_hash(context)}] if bindings else [],
        "disposition": "ready" if bindings else "no-change-no-operation",
        "model_contacts_added": 0, "scorer_contacts_added": 0,
    }


def preparation_inputs(document):
    from ..analysis import system_group_operations, system_semantic_feedback, prepared_text_source
    from . import prepared_feedback, training_feedback_artifacts, system_group_update_context
    paths = [Path(__file__), *(Path(m.__file__) for m in (
        system_group_operations, system_semantic_feedback, prepared_text_source,
        prepared_feedback, training_feedback_artifacts, system_group_update_context))]
    return {"document_sha256": content_hash(document),
            "implementation_sha256": content_hash({p.name: hash_stable_file(p, "batch update implementation")[1] for p in paths})}


def prepare_system_batch_update_contexts(source_pin, output_path, *, data_root):
    document = build_system_batch_update_contexts(source_pin, data_root=data_root)
    return prepare_artifact(Path(output_path), kind=KIND, inputs=preparation_inputs(document),
                            producer=lambda: document, contact_class="model-free")


def load_system_batch_update(spec, *, data_root, sample_ids, construction_roster_sha256):
    states, receipt, document = load_verified_prepared_contexts(
        spec, data_root=data_root, sample_ids=sample_ids,
        construction_roster_sha256=construction_roster_sha256, schema=PREPARED_SCHEMA,
        build_contexts=build_system_batch_update_contexts, preparation_inputs=preparation_inputs,
        artifact_kind=KIND, input_stage="complete-system-batch-update")
    receipt.update(source_construction_roster_sha256=document["source_construction_roster_sha256"],
                   full_group_count=len(document["group_operation_report"]["population"]),
                   base_snapshot_sha256=document["base_snapshot"]["content_sha256"])
    return states, receipt


def main(argv=None):
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--source-relpath", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output-relpath", required=True)
    args = parser.parse_args(argv)
    try:
        path = _resolve_data_path(args.output_relpath, data_root=args.data_root, field="batch output")
        result = prepare_system_batch_update_contexts(
            {"relpath": args.source_relpath, "sha256": args.source_sha256}, path, data_root=args.data_root)
    except (ValueError, OSError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
