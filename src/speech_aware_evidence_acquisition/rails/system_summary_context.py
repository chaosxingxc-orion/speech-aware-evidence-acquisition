"""Prepare complete TRAIN actor episodes for the shared scoreless model path.

Preparation is model-free. The runtime config chooses the historical
speech-feature artifact arm or the prepared-text arm without fresh speech.
Neither connection alone establishes an executed TF-GRPO reproduction.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..analysis.native_episode_source import verify_native_episode_source
from ..analysis.system_semantic_trajectory import (
    materialize_semantic_trajectories, tfgrpo_summary_fields,
)
from ..core.preparation import hash_stable_file, load_artifact, prepare_artifact
from ..core.roster import verify_roster
from .hashing import content_hash
from .prepared_feedback import (
    PREPARED_FEEDBACK_SCHEMA, PreparedFeedbackError, _canonical_context,
    _read_pinned_json, _resolve_data_path, _sha256, _validate_spec, states_from_contexts,
)

PREPARED_SUMMARY_SCHEMA = "saea-prepared-system-summary-v1"
SUMMARY_CONTEXT_SCHEMA = "saea-system-summary-contexts-v1"


def _source_path(pin, data_root, label):
    if not isinstance(pin, Mapping) or set(pin) != {"relpath", "sha256"}:
        raise PreparedFeedbackError(f"{label} pin has wrong fields")
    return (_resolve_data_path(pin["relpath"], data_root=data_root, field=label),
            _sha256(pin["sha256"], field=label + ".sha256"))


def build_system_summary_contexts(source_pin, *, data_root):
    """Reverify one sealed full source; never project scores, slice or merge episodes."""
    data_root = Path(data_root)
    binding, binding_sha = _read_pinned_json(
        source_pin, data_root=data_root, field="summary source binding")
    fields = {"schema", "round_id", "source_repo_root", "manifest", "phases", "construction_roster"}
    wire_view = isinstance(binding, Mapping) and binding.get("schema") == "saea-system-summary-source-v2"
    if wire_view:
        fields.add("wire_requests")
    if (not isinstance(binding, Mapping) or set(binding) != fields
            or binding["schema"] not in {"saea-system-summary-source-v1", "saea-system-summary-source-v2"}):
        raise PreparedFeedbackError("summary source binding has wrong fields")
    checkout = binding["source_repo_root"]
    if not isinstance(checkout, str) or not Path(checkout).is_absolute():
        raise PreparedFeedbackError("summary source requires its absolute frozen checkout")
    manifest, manifest_sha = _source_path(binding["manifest"], data_root, "manifest")
    phases, phases_sha = _source_path(binding["phases"], data_root, "phases")
    roster, roster_sha = _read_pinned_json(
        binding["construction_roster"], data_root=data_root, field="construction roster")
    try:
        identity = verify_roster(roster)
        ids = tuple(row["sample_id"] for row in roster["items"])
        if (roster.get("schema") != "saea-roster-receipt-v1"
                or roster.get("carrier_lock_key") != "slurp"
                or roster.get("split_role") != "discovery"
                or roster.get("roster_role") != "construction"
                or any(not sid.startswith("slurp:train:") for sid in ids)):
            raise PreparedFeedbackError("summary source requires SLURP TRAIN construction")
        source = verify_native_episode_source(
            manifest_path=manifest, expected_manifest_sha256=manifest_sha,
            phase_artifact_path=phases, expected_phase_sha256=phases_sha,
            repo_root=Path(checkout), data_root=data_root,
        )
        if (source.plan.carrier_lock_key != "slurp" or source.plan.split_role != "discovery"
                or source.plan.split_identity_hash != identity
                or set(source.sample_ids) != set(ids) or len(source.sample_ids) != len(ids)):
            raise PreparedFeedbackError("summary source differs from full TRAIN construction roster")
        report = materialize_semantic_trajectories(source, round_id=binding["round_id"])
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
        raise PreparedFeedbackError(f"cannot verify complete summary source: {error}") from error
    wire_requests = None
    if wire_view:
        from ..analysis.system_wire_context import load_actor_wire_requests

        wire_requests = load_actor_wire_requests(
            source, report, binding["wire_requests"], data_root=data_root)
    contexts = []
    for episode in report["episodes"]:
        # The upstream first trajectory slot is the whole episode. Present the
        # same object without nested escaped JSON strings to the shared model.
        fields = tfgrpo_summary_fields(episode)
        trajectory = episode
        if wire_requests is not None:
            from ..analysis.system_wire_context import compact_wire_episode

            trajectory = compact_wire_episode(episode, wire_requests)
        context = {
            "stage": "complete-system-trajectory-summary",
            "raw_question": fields["raw_question"], "trajectory": trajectory,
        }
        _canonical_context(context)
        contexts.append({
            "source_sample_id": episode["trajectory"]["sample_id"],
            # This legacy custody field binds actor content, not a score.
            "source_feedback_sha256": episode["content_sha256"],
            "model_context": context, "model_context_sha256": content_hash(context),
        })
    return {
        "schema": SUMMARY_CONTEXT_SCHEMA, "source_bindings_sha256": binding_sha,
        "construction_roster_sha256": roster_sha, "round_id": binding["round_id"],
        "source_materialization_sha256": report["content_sha256"], "contexts": contexts,
        "model_contacts_added": 0, "scorer_contacts_added": 0,
    }


def summary_preparation_inputs(document):
    """Bind the verified content and the source/serialization implementations."""
    from ..analysis import native_episode_source, system_semantic_trajectory, system_trajectory
    from . import prepared_feedback

    paths = [Path(__file__), *(Path(module.__file__) for module in (
        native_episode_source, system_semantic_trajectory, system_trajectory, prepared_feedback,
    ))]
    if any(row["model_context"]["trajectory"].get("schema") == "saea-complete-episode-wire-view-v1"
           for row in document["contexts"]):
        from ..analysis import shared_json, system_wire_context

        paths.extend(Path(module.__file__) for module in (shared_json, system_wire_context))
    return {
        "document_sha256": content_hash(document),
        "implementation_sha256": content_hash({
            path.name: hash_stable_file(path, "summary implementation")[1] for path in paths
        }),
    }


def prepare_system_summary_contexts(source_pin, output_path, *, data_root):
    """Use shared immutable preparation, including source verification on cache hits."""
    document = build_system_summary_contexts(source_pin, data_root=data_root)
    return prepare_artifact(
        Path(output_path), kind="system-summary-contexts",
        inputs=summary_preparation_inputs(document), producer=lambda: document,
        contact_class="model-free",
    )


def load_system_summary_feedback(spec, *, data_root, sample_ids, construction_roster_sha256):
    """Load one complete trajectory per sample through the existing ORG state."""
    try:
        if spec.get("schema") != PREPARED_SUMMARY_SCHEMA:
            raise PreparedFeedbackError("summary prepared schema differs")
        # Preserve the existing strict pin, language and size contract.
        legacy_shape = dict(spec, schema=PREPARED_FEEDBACK_SCHEMA)
        artifact_pin, source_pin, maximum = _validate_spec(legacy_shape)
        rebuilt = build_system_summary_contexts(source_pin, data_root=data_root)
        if rebuilt["construction_roster_sha256"] != construction_roster_sha256:
            raise PreparedFeedbackError("summary construction roster hash differs")
        envelope, prepared_sha = _read_pinned_json(
            artifact_pin, data_root=data_root, field="summary artifact")
        if not isinstance(envelope, Mapping) or envelope.get("contact_class") != "model-free":
            raise PreparedFeedbackError("summary prepared artifact must be model-free")
        path, _ = _source_path(artifact_pin, data_root, "summary artifact")
        output = load_artifact(path, expected_sha256=prepared_sha, kind="system-summary-contexts",
                               inputs=summary_preparation_inputs(rebuilt))
        if output != rebuilt:
            raise PreparedFeedbackError("summary artifact differs from its verified source")
        contexts = {row["source_sample_id"]: row for row in rebuilt["contexts"]}
        if len(contexts) != len(rebuilt["contexts"]):
            raise PreparedFeedbackError("summary contexts contain duplicate samples")
        states, receipt = states_from_contexts(
            contexts, active_ids=sample_ids, prepared_sha256=prepared_sha,
            source_bindings_sha256=rebuilt["source_bindings_sha256"],
            roster_sha=construction_roster_sha256, maximum=maximum,
        )
        receipt.update(input_stage="complete-system-trajectory-summary",
                       runtime_input_contract="shared-speech-feature-artifact",
                       source_feedback_semantics="score-free-complete-actor-episode-sha256")
        return states, receipt
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
        if isinstance(error, PreparedFeedbackError):
            raise
        raise PreparedFeedbackError(f"cannot load complete summary feedback: {error}") from error


def main(argv=None):
    """Prepare a registered source through the shared immutable artifact store."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--source-relpath", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--output-relpath", required=True)
    args = parser.parse_args(argv)
    try:
        path = _resolve_data_path(
            args.output_relpath, data_root=args.data_root, field="summary output")
        receipt = prepare_system_summary_contexts(
            {"relpath": args.source_relpath, "sha256": args.source_sha256},
            path, data_root=args.data_root,
        )
    except (ValueError, OSError, RuntimeError) as error:
        parser.error(str(error))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
