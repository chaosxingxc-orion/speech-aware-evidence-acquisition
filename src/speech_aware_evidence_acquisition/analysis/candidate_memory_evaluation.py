"""Post-seal source proof for provisional memory, without scoring or admission."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ..rails.candidate_experience_memory import load_candidate_experience_memory
from ..rails.controllers import default_phase_program
from ..rails.experience_memory_runtime import CORRECTIVE_MEMORY_TOOL
from ..rails.phase_tools import load_phase_tool_specs
from .native_episode_source import verify_native_episode_source
from .native_tool_exposure import analyze_verified_native_tool_exposure


class CandidateMemoryEvaluationError(ValueError):
    """The evaluated provisional selection differs from its registered source."""


def verify_candidate_memory_evaluation_source(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    phase_artifact_path: Path,
    expected_phase_sha256: str,
    repo_root: Path,
    data_root: Path,
) -> dict[str, object]:
    """Bind actual evaluated selections and visibility; do not infer helpful use."""
    from .native_query_state import reconstruct_verified_native_query_states

    source = verify_native_episode_source(
        manifest_path=manifest_path,
        expected_manifest_sha256=expected_manifest_sha256,
        phase_artifact_path=phase_artifact_path,
        expected_phase_sha256=expected_phase_sha256,
        repo_root=repo_root,
    )
    values = source.composed.values
    program = default_phase_program(values["policy"])
    memory = load_candidate_experience_memory(
        values, repo_root=repo_root, data_root=data_root,
        carrier_lock_key=source.plan.carrier_lock_key, plan=source.plan,
        sample_ids=source.sample_ids, program=program,
        tool_specs=load_phase_tool_specs(values, program),
    )
    if memory is None:
        raise CandidateMemoryEvaluationError("candidate evaluation requires its provisional binding")
    inputs = dict(
        sample_ids=source.sample_ids, controller_policy_id=values["policy"],
        phase_results=source.phase_results, output_rows=source.output_rows,
        trace_records=source.bundle.trace_records,
    )
    exposure = analyze_verified_native_tool_exposure(**inputs)
    states = reconstruct_verified_native_query_states(**inputs)
    calls = [row for row in exposure["calls"] if row["tool_id"] == CORRECTIVE_MEMORY_TOOL]
    expected_lineage_ids = {row["record_id"] for row in calls}
    actual_lineage_ids = {
        key for key, row in source.bundle.trace_records.items()
        if "use_internal_memory_lineage" in row
    }
    if actual_lineage_ids != expected_lineage_ids:
        raise CandidateMemoryEvaluationError("candidate lineage is missing or belongs to another call")

    verified_calls = []
    for call in calls:
        request_id = call["source_request_id"]
        request = source.bundle.trace_records[f"{request_id}/request"]["payload"]
        response = source.bundle.trace_records[f"{request_id}/response"]
        if request_id not in states:
            raise CandidateMemoryEvaluationError("candidate action lacks its reconstructed query state")
        # The real native runner appends this completion before invoking tools.
        # Its appended phase source is not a tool-result; prior tool states are
        # exactly the agent-state rows in the already verified source request.
        context = SimpleNamespace(
            query_state=states[request_id],
            prior_response_sha256s=(response["response_text_sha256"],),
            agent_states=tuple(
                SimpleNamespace(state_kind=row.get("state_kind"))
                for row in request.get("history", ())
                if row.get("role") == "agent_state"
            ),
        )
        expected = memory.select(next_phase=call["role_id"], context=context)
        event = source.bundle.trace_records[call["record_id"]]
        if (
            event.get("use_result") != expected.visible
            or event.get("use_internal_memory_lineage") != expected.lineage
        ):
            raise CandidateMemoryEvaluationError(
                "candidate selection does not reproduce from its actual source state and pack"
            )
        verified_calls.append({
            **call,
            "condition_tags": list(expected.visible["condition_tags"]),
            "selected_record_sha256s": [
                row["record_sha256"] for row in expected.visible["selected_records"]
            ],
        })
    called_samples = {row["sample_id"] for row in calls}
    return {
        "schema": "saea-candidate-memory-evaluation-source-v1",
        "source_verified": True,
        "admission": "none",
        "manifest_sha256": expected_manifest_sha256,
        "phase_artifact_sha256": expected_phase_sha256,
        "study_commit": source.bundle.manifest["study_commit"],
        "config_hash": source.composed.config_hash,
        "run_id": source.plan.run_id,
        "attempt_id": source.plan.attempt_id,
        "protocol_hash": source.plan.protocol_hash,
        "sample_count": len(source.sample_ids),
        "candidate_artifact_sha256": memory.artifact_sha256,
        "candidate_output_sha256": memory.artifact_output_sha256,
        "source_attestation_sha256": memory.source_attestation_sha256,
        "evaluation_decision_sha256": memory.evaluation_decision_sha256,
        "construction_roster_sha256": memory.construction_roster_sha256,
        "evaluation_roster_sha256": memory.evaluation_roster_sha256,
        "ordered_pack_record_sha256s": [row.record_sha256 for row in memory.records],
        "allowed_roles": list(memory.allowed_roles),
        "samples_without_successful_memory_call": [
            item for item in source.sample_ids if item not in called_samples
        ],
        "successful_memory_calls": verified_calls,
        "other_successful_call_count": exposure["successful_call_count"] - len(calls),
        "non_result_events": exposure["non_result_events"],
        "interpretation": (
            "Source and structural selection are independently verified. Exact "
            "later exposure is reported separately; neither proves semantic use, "
            "causal benefit or task quality. No memory admission is made."
        ),
    }
