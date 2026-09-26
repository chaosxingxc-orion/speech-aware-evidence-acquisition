"""Bind complete-system comparison lessons and frozen memory for group updates."""
from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from pathlib import Path

from ..analysis.prepared_text_source import verify_prepared_text_source
from ..core.preparation import hash_stable_file, load_artifact, prepare_artifact
from ..core.provisional_candidate_materialization import prepare_provisional_candidates, ARTIFACT_KIND
from ..core.roster import verify_roster
from .experience_consolidation import initialize_candidate_snapshot, _load_snapshot, extend_candidate_construction
from .experience_memory import ExperienceRecord
from .hashing import content_hash
from .prepared_feedback import (
    PreparedFeedbackError, _read_pinned_json, _resolve_data_path, _canonical_context,
    load_verified_prepared_contexts,
)
from .system_comparison_context import PREPARED_COMPARISON_SCHEMA, build_system_comparison_contexts

SOURCE_SCHEMA = "saea-system-group-update-source-v1"
ROUND_SOURCE_SCHEMA = "saea-system-group-update-source-v2"
PREPARED_SCHEMA = "saea-prepared-system-group-update-v1"
KIND = "system-group-update-contexts"


def _require(condition, message):
    if not condition:
        raise PreparedFeedbackError(message)


def extract_experiences(text):
    """Retain raw text separately; classify empty/missing/ambiguous blocks explicitly."""
    pattern = r"<Experiences>\s*(.*?)\s*</Experiences>"
    blocks = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    if not blocks:
        return {"status": "missing-block", "text": ""}
    if len(blocks) != 1 or len(re.findall(r"</?Experiences>", text, re.IGNORECASE)) != 2:
        return {"status": "ambiguous-block", "text": ""}
    extracted = blocks[0].strip()
    return {"status": "ready" if extracted else "empty-block", "text": extracted}


def verify_system_comparisons(pin, *, repo_root, data_root):
    return verify_prepared_text_source(
        pin, repo_root=repo_root, data_root=data_root,
        input_schema=PREPARED_COMPARISON_SCHEMA, artifact_kind="system-comparison-contexts",
        rebuild_contexts=build_system_comparison_contexts)


def _roster(pin, data, name):
    roster, sha = _read_pinned_json(pin, data_root=data, field=name)
    verify_roster(roster)
    ids = [row["sample_id"] for row in roster["items"]]
    _require(roster.get("carrier_lock_key") == "slurp" and roster.get("split_role") == "discovery"
             and roster.get("roster_role") == "construction"
             and all(s.startswith("slurp:train:") for s in ids),
             name + " must be SLURP TRAIN construction")
    return ids, sha


def _base_memory(binding, data, full_ids, full_sha, *, same_population=True):
    pin = binding["base_memory"]
    memory_id = binding["memory_id"]
    _require(isinstance(memory_id, str) and bool(memory_id.strip()), "memory ID must be nonempty")
    if pin is None:
        return initialize_candidate_snapshot(memory_id=memory_id,
            train_construction_sha256=full_sha, expected_train_sample_ids=full_ids)
    _require(isinstance(pin, Mapping) and set(pin) == {
        "materialization_config", "candidate_artifact", "snapshot_sha256"},
        "base memory must bind a replayable materialization")
    config, config_sha = _read_pinned_json(pin["materialization_config"], data_root=data,
                                          field="base memory config")
    del config
    config_path = _resolve_data_path(pin["materialization_config"]["relpath"],
                                    data_root=data, field="base memory config")
    result = prepare_provisional_candidates(
        config_path=config_path, expected_config_sha256=config_sha, data_root=data)
    wrapper, artifact_sha = _read_pinned_json(pin["candidate_artifact"], data_root=data, field="base memory")
    path = _resolve_data_path(pin["candidate_artifact"]["relpath"], data_root=data, field="base memory")
    _require(Path(result["path"]).resolve() == path and result["sha256"] == artifact_sha,
             "base memory differs from replayed source")
    output = load_artifact(path, expected_sha256=artifact_sha, kind=ARTIFACT_KIND, inputs=wrapper["inputs"])
    source_sha = output["provenance"]["construction_roster_sha256"]
    source_ids = [s["source_sample_id"] for s in output["samples"]]
    if same_population:
        _require(source_sha == full_sha and source_ids == full_ids,
                 "base memory construction must cover the full source population")
    if "candidate_snapshot" in output:
        snapshot = output["candidate_snapshot"]
        _load_snapshot(snapshot)
    else:
        snapshot = initialize_candidate_snapshot(
            memory_id=memory_id, train_construction_sha256=source_sha,
            expected_train_sample_ids=source_ids,
            records=tuple(ExperienceRecord.from_json(rec)
                          for sample in output["samples"] for rec in sample["records"]))
    _require(snapshot["content_sha256"] == pin["snapshot_sha256"]
             and snapshot["memory_id"] == memory_id
             and snapshot["train_construction_sha256"] == source_sha
             and snapshot["train_sample_ids"] == sorted(source_ids),
             "frozen base snapshot identity differs")
    return snapshot


def build_system_group_update_contexts(source_pin, *, data_root):
    """Reverify every source; preserve the full population before selecting update contacts."""
    try:
        return _build(source_pin, Path(data_root))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        if isinstance(error, PreparedFeedbackError):
            raise
        raise PreparedFeedbackError(f"cannot build group update contexts: {error}") from error


def _build(source_pin, data):
    binding, binding_sha = _read_pinned_json(source_pin, data_root=data, field="group update source")
    _require(isinstance(binding, Mapping), "group update source must be an object")
    scoped = binding.get("schema") == ROUND_SOURCE_SCHEMA
    fields = {"schema", "comparison_manifest", "comparison_repo_root", "source_construction_roster",
              "update_roster", "memory_id", "base_memory"}
    if scoped:
        fields |= {"round_policy", "cumulative_construction_roster"}
    _require(set(binding) == fields and binding["schema"] in {SOURCE_SCHEMA, ROUND_SOURCE_SCHEMA},
             "group update source fields differ")
    repo = binding["comparison_repo_root"]
    _require(isinstance(repo, str) and Path(repo).is_absolute(), "comparison checkout must be absolute")
    source = verify_system_comparisons(binding["comparison_manifest"], repo_root=repo, data_root=data)
    full_ids, full_sha = _roster(binding["source_construction_roster"], data, "source construction roster")
    report = source.prepared_document["comparison"]
    _require(source.prepared_document["source_construction_roster_sha256"] == full_sha
             and [g["sample_id"] for g in report["groups"]] == full_ids,
             "full construction population differs from comparison sources")
    _require(set(source.rows) == set(report["ready_sample_ids"]), "comparison output population differs")
    snapshot = _base_memory(binding, data, full_ids, full_sha, same_population=not scoped)
    round_fields = {}
    if scoped:
        from ..analysis.system_update_round import verify_system_update_round
        receipt = verify_system_update_round(
            binding["round_policy"], source, base_memory_pin=binding["base_memory"],
            base_snapshot=snapshot, sample_ids=full_ids, round_id=report["round_id"], data_root=data)
        cumulative_ids, cumulative_sha = _roster(binding["cumulative_construction_roster"], data,
                                                "cumulative construction roster")
        if binding["base_memory"] is None:
            _require(cumulative_sha == full_sha and cumulative_ids == full_ids,
                     "initial cumulative construction must equal the current roster")
        else:
            snapshot = extend_candidate_construction(
                snapshot, round_construction_sha256=full_sha, round_sample_ids=full_ids,
                cumulative_construction_sha256=cumulative_sha, cumulative_sample_ids=cumulative_ids)
        round_fields = {
            "round_policy_receipt": receipt,
            "memory_construction": {"roster_sha256": cumulative_sha, "sample_ids": cumulative_ids},
        }
    memory = [{k: copy.deepcopy(record[k]) for k in
               ("record_id", "kind", "diagnosis", "guidance", "limitations", "applicability")}
              for record in snapshot["records"]]
    population, contexts = [], []
    for group in report["groups"]:
        sid = group["sample_id"]
        if group["disposition"] != "ready":
            population.append({"sample_id": sid, "disposition": group["disposition"],
                               "comparison": None, "extraction": None,
                               "experience_source": copy.deepcopy(group["experience_source"])})
            continue
        row = copy.deepcopy(source.rows[sid])
        _require(row["source_context_sha256"] == content_hash(group),
                 "comparison response is bound to another group")
        extraction = extract_experiences(row["text"])
        disposition = ("blocked-unusable-comparison" if row["status"] != "usable"
                       else "ready" if extraction["status"] == "ready"
                       else "no-update-no-experience" if extraction["status"] in {"empty-block", "missing-block"}
                       else "blocked-ambiguous-experience")
        entry = {"sample_id": sid, "disposition": disposition, "comparison": row, "extraction": extraction,
                 "experience_source": copy.deepcopy(group["experience_source"])}
        population.append(entry)
        if disposition == "ready":
            context = {
                "stage": "complete-system-group-update", "existing_experiences": memory,
                "new_experiences": extraction["text"],
                "comparison_analysis": row["text"],
                "observed_comparison": group["model_context"],
                "authority": "Offline provisional operation proposals only; no automatic memory update.",
            }
            _canonical_context(context)
            contexts.append({
                "source_sample_id": sid, "source_feedback_sha256": content_hash({
                    "group": group, "comparison": row, "base_snapshot_sha256": snapshot["content_sha256"]}),
                "model_context": context, "model_context_sha256": content_hash(context),
            })
    ready = [row["source_sample_id"] for row in contexts]
    active_sha = None
    if binding["update_roster"] is not None:
        active_ids, active_sha = _roster(binding["update_roster"], data, "update roster")
        _require(active_ids == ready, "update roster must match exactly the ordered ready groups")
    return {
        "schema": "saea-system-group-update-contexts-v1", "source_bindings_sha256": binding_sha,
        "construction_roster_sha256": active_sha, "source_construction_roster_sha256": full_sha,
        "full_construction_sample_ids": full_ids, "round_id": report["round_id"],
        "comparison_manifest_sha256": source.manifest_sha256, "population": population,
        "base_snapshot": snapshot, "contexts": contexts, "ready_sample_ids": ready, **round_fields,
        "model_contacts_added": 0, "scorer_contacts_added": 0,
    }


def preparation_inputs(document):
    from ..analysis import prepared_text_source, system_update_round
    from ..core import provisional_candidate_materialization, provisional_candidate_consolidation
    from . import experience_consolidation, system_comparison_context
    modules = (prepared_text_source, system_update_round, provisional_candidate_materialization,
               provisional_candidate_consolidation, experience_consolidation, system_comparison_context)
    paths = [Path(__file__), *(Path(m.__file__) for m in modules)]
    return {"document_sha256": content_hash(document),
            "implementation_sha256": content_hash({p.name: hash_stable_file(p, "group update implementation")[1]
                                                   for p in paths})}


def prepare_system_group_update_contexts(source_pin, output_path, *, data_root):
    document = build_system_group_update_contexts(source_pin, data_root=data_root)
    return prepare_artifact(Path(output_path), kind=KIND, inputs=preparation_inputs(document),
                            producer=lambda: document, contact_class="model-free")


def load_system_group_update(spec, *, data_root, sample_ids, construction_roster_sha256):
    states, receipt, rebuilt = load_verified_prepared_contexts(
        spec, data_root=data_root, sample_ids=sample_ids,
        construction_roster_sha256=construction_roster_sha256, schema=PREPARED_SCHEMA,
        build_contexts=build_system_group_update_contexts, preparation_inputs=preparation_inputs,
        artifact_kind=KIND, input_stage="complete-system-group-update")
    receipt.update(source_construction_roster_sha256=rebuilt["source_construction_roster_sha256"],
                   full_group_count=len(rebuilt["population"]), ready_group_count=len(rebuilt["contexts"]),
                   base_snapshot_sha256=rebuilt["base_snapshot"]["content_sha256"])
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
        path = _resolve_data_path(args.output_relpath, data_root=args.data_root, field="group update output")
        receipt = prepare_system_group_update_contexts(
            {"relpath": args.source_relpath, "sha256": args.source_sha256}, path, data_root=args.data_root)
    except (ValueError, OSError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
