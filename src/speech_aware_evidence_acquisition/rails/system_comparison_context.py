"""Prepare actual trajectory summaries and official terminal feedback for comparison."""
from __future__ import annotations

from pathlib import Path
from collections.abc import Mapping

from ..analysis.native_episode_source import verify_native_episode_source
from ..analysis.system_feedback import load_system_feedback
from ..analysis.system_rollout_groups import load_group_source, group_complete_system_sources
from ..analysis.system_semantic_trajectory import materialize_semantic_trajectories
from ..analysis.system_semantic_feedback import prepare_semantic_feedback_groups, join_recorded_summaries
from ..analysis.system_summary_source import verify_system_summaries
from ..core.preparation import hash_stable_file, prepare_artifact
from ..core.roster import verify_roster
from .hashing import content_hash
from .prepared_feedback import (
    PreparedFeedbackError, _read_pinned_json, _resolve_data_path,
    _canonical_context, load_verified_prepared_contexts,
)
from .system_summary_context import _source_path

PREPARED_COMPARISON_SCHEMA = "saea-prepared-system-comparison-v1"
SOURCE_SCHEMA = "saea-system-comparison-source-v1"
EVENT_SOURCE_SCHEMA = "saea-system-comparison-source-v2"


def _require(ok, message):
    if not ok:
        raise PreparedFeedbackError(message)


def build_system_comparison_contexts(source_pin, *, data_root):
    """Rebuild closed actors, official feedback and actually generated summaries."""
    try:
        return _build(source_pin, Path(data_root))
    except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:
        if isinstance(error, PreparedFeedbackError):
            raise
        raise PreparedFeedbackError(f"cannot verify semantic comparison inputs: {error}") from error


def _build(source_pin, data):
    binding, binding_sha = _read_pinned_json(source_pin, data_root=data, field="comparison source")
    _require(isinstance(binding, Mapping), "comparison source must be an object")
    fields = {"schema", "round_id", "frozen_f0", "members", "comparison_roster"}
    event_mode = binding.get("schema") == EVENT_SOURCE_SCHEMA
    if event_mode:
        from ..analysis.system_event_evidence import EVENT_MODE
        fields.add("event_evidence")
        _require(binding.get("event_evidence") == EVENT_MODE, "unknown event evidence mode")
    _require(set(binding) == fields and binding.get("schema") in
             (SOURCE_SCHEMA, EVENT_SOURCE_SCHEMA), "comparison source schema differs")
    members = binding["members"]
    _require(isinstance(members, list) and len(members) >= 2, "comparison needs at least two full sources")
    labels = []
    summaries, groups, reports = [], [], []
    summary_identity = None
    source_roster = None
    for member in members:
        _require(isinstance(member, Mapping) and set(member) == {
            "label", "summary_manifest", "summary_repo_root", "feedback_export",
        }, "comparison member fields differ")
        label = member["label"]
        _require(isinstance(label, str) and label and label not in labels, "comparison labels must be unique")
        labels.append(label)
        repo = member["summary_repo_root"]
        _require(isinstance(repo, str) and Path(repo).is_absolute(), "summary checkout must be absolute")
        summary = verify_system_summaries(member["summary_manifest"], repo_root=repo, data_root=data)
        actor = summary.actor_binding
        actor_roster = actor["construction_roster"]["sha256"]
        _require(source_roster is None or source_roster == actor_roster,
                 "full construction roster bindings differ")
        source_roster = actor_roster
        _require(actor["round_id"] == binding["round_id"], "comparison construction round differs")
        identity = (summary.manifest["config"]["fragments"]["model"],
                    summary.manifest["session_receipt"]["sha256"])
        _require(summary_identity is None or summary_identity == identity,
                 "summary model or serving receipt differs")
        summary_identity = identity
        feedback, _ = _read_pinned_json(member["feedback_export"], data_root=data, field="feedback export")
        source_binding = feedback["source_bindings"]
        _require(source_binding["manifest"] == actor["manifest"]
                 and source_binding["phases"] == actor["phases"],
                 "summary and official feedback identify different actors")
        rebuilt = load_system_feedback(data_root=data, repo_root=Path(actor["source_repo_root"]),
                                       binding=source_binding)
        _require(feedback == rebuilt, "feedback export differs from complete official source")
        groups.append(load_group_source(data_root=data, feedback_pin=member["feedback_export"], label=label))
        manifest, manifest_sha = _source_path(actor["manifest"], data, "actor manifest")
        phases, phases_sha = _source_path(actor["phases"], data, "actor phases")
        source = verify_native_episode_source(
            manifest_path=manifest, expected_manifest_sha256=manifest_sha,
            phase_artifact_path=phases, expected_phase_sha256=phases_sha,
            repo_root=Path(actor["source_repo_root"]), data_root=data)
        reports.append(materialize_semantic_trajectories(source, round_id=binding["round_id"]))
        summaries.append(summary)
    grouped = group_complete_system_sources(groups, f0=binding["frozen_f0"])
    feedback = prepare_semantic_feedback_groups(grouped, reports)
    joined = join_recorded_summaries(feedback, summaries)
    if event_mode:
        from ..analysis.system_event_evidence import add_recorded_event_evidence
        joined = add_recorded_event_evidence(joined, reports, summaries)
    roster_sha = None
    if binding["comparison_roster"] is not None:
        roster, roster_sha = _read_pinned_json(binding["comparison_roster"], data_root=data, field="comparison roster")
        verify_roster(roster)
        _require(roster.get("carrier_lock_key") == "slurp"
                 and roster.get("split_role") == "discovery" and roster.get("roster_role") == "construction",
                 "comparison requires a TRAIN construction roster")
        ids = [row["sample_id"] for row in roster["items"]]
        _require(ids == joined["ready_sample_ids"] and all(s.startswith("slurp:train:") for s in ids),
                 "comparison roster must be exactly the ordered ready groups")
    contexts = []
    for group in joined["groups"]:
        _canonical_context(group["model_context"])
        if group["disposition"] == "ready":
            contexts.append({
                "source_sample_id": group["sample_id"],
                "source_feedback_sha256": content_hash(group),
                "model_context": group["model_context"],
                "model_context_sha256": group["model_context_sha256"],
            })
    return {
        "schema": "saea-system-comparison-contexts-v1",
        "source_bindings_sha256": binding_sha, "construction_roster_sha256": roster_sha,
        "round_id": binding["round_id"], "comparison": joined, "contexts": contexts,
        "source_construction_roster_sha256": source_roster,
        "model_contacts_added": 0, "scorer_contacts_added": 0,
    }


def comparison_preparation_inputs(document):
    from ..analysis import (native_episode_source, prepared_text_source, system_feedback, system_rollout_groups,
                            system_semantic_feedback, system_semantic_trajectory, system_summary_source)
    from . import prepared_feedback, system_summary_context
    modules = (native_episode_source, prepared_text_source, system_feedback, system_rollout_groups,
               system_semantic_feedback, system_semantic_trajectory, system_summary_source,
               prepared_feedback, system_summary_context)
    paths = [Path(__file__), *(Path(m.__file__) for m in modules)]
    if document["comparison"].get("event_evidence"):
        from ..analysis import shared_json, system_event_evidence, system_wire_context
        paths.extend(Path(m.__file__) for m in (shared_json, system_event_evidence, system_wire_context))
    return {
        "document_sha256": content_hash(document),
        "implementation_sha256": content_hash({p.name: hash_stable_file(p, "comparison implementation")[1]
                                               for p in paths}),
    }


def prepare_system_comparison_contexts(source_pin, output_path, *, data_root):
    document = build_system_comparison_contexts(source_pin, data_root=data_root)
    return prepare_artifact(Path(output_path), kind="system-comparison-contexts",
                            inputs=comparison_preparation_inputs(document),
                            producer=lambda: document, contact_class="model-free")


def load_system_comparison_feedback(spec, *, data_root, sample_ids, construction_roster_sha256):
    states, receipt, rebuilt = load_verified_prepared_contexts(
        spec, data_root=data_root, sample_ids=sample_ids,
        construction_roster_sha256=construction_roster_sha256,
        schema=PREPARED_COMPARISON_SCHEMA, build_contexts=build_system_comparison_contexts,
        preparation_inputs=comparison_preparation_inputs, artifact_kind="system-comparison-contexts",
        input_stage="complete-system-semantic-comparison")
    receipt.update(input_stage="complete-system-semantic-comparison",
                   runtime_input_contract="shared-prepared-text-artifact",
                   comparison_sha256=rebuilt["comparison"]["content_sha256"],
                   full_group_count=len(rebuilt["comparison"]["groups"]),
                   ready_group_count=len(rebuilt["contexts"]))
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
        path = _resolve_data_path(args.output_relpath, data_root=args.data_root, field="comparison output")
        result = prepare_system_comparison_contexts(
            {"relpath": args.source_relpath, "sha256": args.source_sha256}, path, data_root=args.data_root)
    except (ValueError, OSError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
