# ruff: noqa: F811
"""Native training proposal projection preserves useful tool semantics without custody IDs."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from test_group_relative_feedback import native_training_source_pair  # noqa: F401

from speech_aware_evidence_acquisition.rails.native_training_context import (
    NativeTrainingContextError,
    NativeTrainingContextProjector,
)
from speech_aware_evidence_acquisition.rails.training_proposal_context import (
    TrainingProposalContextError,
    _source_trajectories,
    build_training_proposal_contexts,
)
from speech_aware_evidence_acquisition.core.delivery import native_abstention_records

pytest_plugins = ("test_bundle",)


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_native_framework_projection_keeps_role_queries_and_bound_tool_semantics(
    native_training_source_pair,
):
    document = build_training_proposal_contexts(native_training_source_pair)
    candidate = document["contexts"][0]["model_context"]["candidates"][0]
    trajectory = candidate["trajectory"]

    reviewer_calls = [
        step for step in trajectory
        if step.get("role_id") == "reviewer" and step["tool_calls"]
    ]
    assert [step["tool_calls"][0]["name"] for step in reviewer_calls] == [
        "saea-tool-task-contract-v1",
        "saea-tool-candidate-contract-lookup-v1",
    ]
    assert reviewer_calls[0]["instruction"] == (
        "Review the Solver draft against the synthetic task contract."
    )
    assert reviewer_calls[0]["system_instruction"] == (
        "Apply the synthetic SLU task contract."
    )
    assert [
        tool["function"]["name"] for tool in reviewer_calls[0]["available_tools"]
    ] == ["saea-tool-task-contract-v1"]
    assert reviewer_calls[1]["tool_calls"][0]["arguments"] == {
        "candidate_ids": ["synthetic-candidate-marker"],
    }

    reviewer_continuations = [
        step for step in trajectory
        if step.get("role_id") == "reviewer" and step["tool_results"]
    ]
    assert [len(step["tool_results"]) for step in reviewer_continuations] == [1, 1, 2]
    result = reviewer_continuations[0]["tool_results"][0]
    assert result["call_label"] == reviewer_calls[0]["tool_calls"][0]["label"]
    assert result["name"] == "saea-tool-task-contract-v1"
    assert result["result"]["contract_status"] == "synthetic-contract-confirmed"
    assert result["result"]["evidence_marker"] == "synthetic-task-contract-evidence-marker"
    assert result["evidence"] == [{
        "reference": "reference-1",
        "content": "Synthetic task-contract evidence marker.", "kind": "observation",
    }]

    final = next(step for step in trajectory if step["selected_final"])
    assert final["role_id"] == "solver"
    assert final["action"] == "synthetic-program:solver:1"

    visible = json.dumps(document["contexts"][0]["model_context"], ensure_ascii=False)
    for private_value in (
        "slurp:train:", "synthetic-program:reviewer:0:slurp:train:",
        "synthetic-native-call-", "synthetic-task-contract://",
    ):
        assert private_value not in visible


def _abstention_source(native_training_source_pair, tmp_path):
    source_manifest = Path(native_training_source_pair[0]["config"]["manifest"]["path"])
    manifest = copy.deepcopy(json.loads(source_manifest.read_text()))
    trace_rows = [
        json.loads(line) for line in Path(manifest["raw_trace"]["path"]).read_text().splitlines()
        if line
    ]
    outputs = [
        json.loads(line) for line in Path(manifest["outputs"]["path"]).read_text().splitlines()
        if line
    ]
    output = outputs[0]
    sample_id = output["sample_id"]
    sample_requests = [
        row for row in trace_rows
        if row["channel"] == "MODEL_REQUEST"
        and row["payload"]["payload"]["sample_id"] == sample_id
    ]

    def role_and_contact(request_row):
        control = next(
            item for item in reversed(request_row["payload"]["payload"]["history"])
            if item["role"] == "control"
        )
        contact_id = control["contact_id"]
        role = next(
            name for name in ("perception", "solver", "reviewer", "planner")
            if f":{name}:" in contact_id
        )
        request_id = request_row["payload"]["payload"]["request_id"]
        response = next(
            row["payload"] for row in trace_rows
            if row["channel"] == "MODEL_RESPONSE"
            and row["record_id"] == request_id + "/response"
        )
        contact = {
            "agent_contact_id": contact_id,
            "request_id": request_id,
            "request_sha256": request_row["payload"]["payload_sha256"],
            "response_sha256": response["response_sha256"],
            "response_text_sha256": response["response_text_sha256"],
        }
        return role, contact

    role_contacts = [role_and_contact(row) for row in sample_requests]
    solver_index = next(
        index for index, (role, _contact) in enumerate(role_contacts)
        if role == "solver"
    )
    completed = [
        {
            "role_id": role,
            "stage": role,
            "execution_receipt": {"contacts": [contact], "final_contact": contact},
        }
        for role, contact in role_contacts[:solver_index]
    ]
    solver_contact = role_contacts[solver_index][1]
    interrupted = {
        "role_id": "solver",
        "stage": "solver",
        "execution_receipt": {
            "contacts": [solver_contact],
            "final_contact": solver_contact,
        },
    }
    rejected = interrupted["execution_receipt"]["final_contact"]
    receipt = {
        "role_visits": completed,
        "planner_routes": [],
        "interrupted_role": interrupted,
        "terminal_disposition": {
            "reason": "finite_completion",
            "finish_reason": "length",
            "role_id": interrupted["role_id"],
            "stage": interrupted["stage"],
            "revision_count": 0,
            "planner_accepted": False,
            "rejected_contact": rejected,
        },
        "abstention_receipt": {"source_contact": rejected},
    }
    output["native_episode_receipt"] = receipt
    derived_id, request_document, response_document = native_abstention_records(
        sample_id=sample_id, source_contact=rejected, finish_reason="length",
    )
    trace_rows.extend([
        {"channel": "TOOL", "record_id": derived_id + "/request", "payload": request_document},
        {"channel": "TOOL", "record_id": derived_id + "/response", "payload": response_document},
    ])
    output["request_id"] = derived_id
    for field in ("request_sha256", "response_sha256", "response_text_sha256"):
        output[field] = response_document[field]
    if "text" in output:
        output["text"] = ""
    if "response" in output:
        output["response"] = ""

    trace_path = tmp_path / "abstention-trace.jsonl"
    trace_path.write_text("".join(json.dumps(row) + "\n" for row in trace_rows))
    output_path = tmp_path / "abstention-outputs.jsonl"
    output_path.write_text("".join(json.dumps(row) + "\n" for row in outputs))
    manifest["raw_trace"] = {"path": str(trace_path), "sha256": _sha_file(trace_path)}
    manifest["outputs"] = {"path": str(output_path), "sha256": _sha_file(output_path)}
    manifest_path = tmp_path / "abstention-manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    source = {"manifest": {"path": str(manifest_path), "sha256": _sha_file(manifest_path)}}
    return source, tuple(row["sample_id"] for row in outputs), sample_id, derived_id, trace_path


def test_verified_abstention_retains_model_steps_and_binds_empty_derivative(
    native_training_source_pair, tmp_path,
):
    source, sample_ids, sample_id, derived_id, _trace_path = _abstention_source(
        native_training_source_pair, tmp_path,
    )
    result = _source_trajectories(source, sample_ids)
    projected = result[sample_id]

    assert projected["trajectory"]
    assert not any(step["selected_final"] for step in projected["trajectory"])
    assert projected["delivery"] == {
        "kind": "abstention",
        "delivered_solver": False,
        "derived_request_id": derived_id,
        "response_sha256": projected["delivery"]["response_sha256"],
        "response_text_sha256": hashlib.sha256(b"").hexdigest(),
    }
    assert projected["final_response_sha256"] == hashlib.sha256(b"").hexdigest()


def test_abstention_refuses_a_derivative_response_that_differs_from_shared_builder(
    native_training_source_pair, tmp_path,
):
    source, sample_ids, _sample_id, derived_id, trace_path = _abstention_source(
        native_training_source_pair, tmp_path,
    )
    rows = [json.loads(line) for line in trace_path.read_text().splitlines()]
    response = next(row for row in rows if row["record_id"] == derived_id + "/response")
    response["payload"]["text"] = "rejected partial response"
    trace_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    manifest_path = Path(source["manifest"]["path"])
    manifest = json.loads(manifest_path.read_text())
    manifest["raw_trace"]["sha256"] = _sha_file(trace_path)
    manifest_path.write_text(json.dumps(manifest))
    source["manifest"]["sha256"] = _sha_file(manifest_path)

    with pytest.raises(TrainingProposalContextError, match="abstention derivative"):
        _source_trajectories(source, sample_ids)


def test_legacy_projected_context_has_no_new_delivery_fields(native_training_source_pair):
    document = build_training_proposal_contexts(native_training_source_pair)
    for context in document["contexts"]:
        for candidate in context["model_context"]["candidates"]:
            assert "delivery" not in candidate
        for binding in context["candidate_bindings"]:
            assert "delivery" not in binding


def test_abstention_identity_is_private_while_visible_context_names_the_outcome(
    monkeypatch,
):
    from speech_aware_evidence_acquisition.rails import training_proposal_context as module

    empty_hash = hashlib.sha256(b"").hexdigest()
    private_delivery = {
        "kind": "abstention",
        "delivered_solver": False,
        "derived_request_id": "synthetic-request/delivery/native-abstention-v1",
        "response_sha256": "1" * 64,
        "response_text_sha256": empty_hash,
    }
    source = {
        "candidate_id": "candidate-1",
        "run_id": "synthetic-run",
        "attempt_id": "synthetic-attempt",
        "manifest": {"path": "/synthetic/manifest"},
        "reward_artifact": {"path": "/synthetic/reward"},
    }
    feedback = {
        "carrier_lock_key": "synthetic-carrier",
        "construction_roster_sha256": "2" * 64,
        "sources": [source],
        "groups": [{
            "sample_id": "synthetic-sample",
            "members": [{
                "candidate_id": "candidate-1",
                "reward_link_sha256": "3" * 64,
                "source": {"response_sha256": empty_hash},
                "native_counts": {},
                "quality": {},
            }],
        }],
    }
    trajectory = {
        "synthetic-sample": {
            "trajectory": [{"selected_final": False}],
            "evidence": [],
            "final_response_sha256": empty_hash,
            "delivery": private_delivery,
        },
    }
    monkeypatch.setattr(module, "build_group_relative_feedback", lambda _sources: feedback)
    monkeypatch.setattr(module, "_source_trajectories", lambda _source, _ids: trajectory)

    document = build_training_proposal_contexts([source])
    context = document["contexts"][0]
    assert context["model_context"]["candidates"][0]["delivery"] == {
        "kind": "abstention", "delivered_solver": False,
    }
    assert context["candidate_bindings"][0]["delivery"] == private_delivery
    assert private_delivery["derived_request_id"] not in json.dumps(
        context["model_context"], ensure_ascii=False,
    )


def _native_request_material(native_training_source_pair):
    manifest_path = Path(native_training_source_pair[0]["config"]["manifest"]["path"])
    manifest = json.loads(manifest_path.read_text())
    rows = [
        json.loads(line) for line in Path(manifest["raw_trace"]["path"]).read_text().splitlines()
        if line
    ]
    requests = {
        row["payload"]["payload"]["request_id"]: row["payload"]["payload"]
        for row in rows if row["channel"] == "MODEL_REQUEST"
    }
    responses = {
        row["record_id"].removesuffix("/response"): row["payload"]
        for row in rows if row["channel"] == "MODEL_RESPONSE"
    }
    completions = {
        row["payload"]["request_id"]: row["payload"]
        for row in rows if row["channel"] == "TOOL"
        and row["payload"].get("schema") == "saea-native-completion-v1"
    }
    reviewer_zero = next(
        request_id for request_id in requests if request_id.endswith("reviewer-0")
    )
    reviewer_one = next(
        request_id for request_id in requests if request_id.endswith("reviewer-1")
    )
    return manifest, requests, responses, completions, reviewer_zero, reviewer_one


@pytest.mark.parametrize("mode", ["missing", "wrong"])
def test_native_projection_refuses_missing_or_wrong_source_completion(
    native_training_source_pair,
    mode,
):
    _manifest, requests, responses, completions, reviewer_zero, _reviewer_one = (
        _native_request_material(native_training_source_pair)
    )
    completion = None if mode == "missing" else copy.deepcopy(completions[reviewer_zero])
    if completion is not None:
        completion["response_text_sha256"] = "0" * 64
    with pytest.raises(NativeTrainingContextError, match="completion"):
        NativeTrainingContextProjector().project(
            requests[reviewer_zero], responses[reviewer_zero], completion,
        )


def test_native_projection_refuses_a_future_or_unseen_tool_call(
    native_training_source_pair,
):
    _manifest, requests, responses, completions, _reviewer_zero, reviewer_one = (
        _native_request_material(native_training_source_pair)
    )
    with pytest.raises(NativeTrainingContextError, match="preceding actual model call"):
        NativeTrainingContextProjector().project(
            requests[reviewer_one], responses[reviewer_one], completions[reviewer_one],
        )


def test_native_projection_refuses_duplicate_native_call_identity(
    native_training_source_pair,
):
    _manifest, requests, responses, completions, reviewer_zero, _reviewer_one = (
        _native_request_material(native_training_source_pair)
    )
    completion = copy.deepcopy(completions[reviewer_zero])
    calls = json.loads(completion["native_tool_calls_json"])
    completion["native_tool_calls_json"] = json.dumps(
        [*calls, calls[0]], ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )
    completion["native_tool_calls_sha256"] = hashlib.sha256(
        completion["native_tool_calls_json"].encode()
    ).hexdigest()
    with pytest.raises(NativeTrainingContextError, match="invalid or out-of-scope"):
        NativeTrainingContextProjector().project(
            requests[reviewer_zero], responses[reviewer_zero], completion,
        )


def test_pinned_source_refuses_an_altered_local_tool_return(
    native_training_source_pair,
):
    manifest, _requests, _responses, _completions, _reviewer_zero, _reviewer_one = (
        _native_request_material(native_training_source_pair)
    )
    trace_path = Path(manifest["raw_trace"]["path"])
    original = trace_path.read_text()
    assert "Synthetic task-contract evidence marker." in original
    trace_path.write_text(original.replace(
        "Synthetic task-contract evidence marker.",
        "Altered synthetic task-contract evidence marker.",
        1,
    ))
    try:
        with pytest.raises(TrainingProposalContextError):
            build_training_proposal_contexts(native_training_source_pair)
    finally:
        trace_path.write_text(original)


def test_native_receipt_cannot_silently_fall_back_to_legacy_projection(
    native_training_source_pair,
):
    _manifest, requests, responses, completions, reviewer_zero, _ = (
        _native_request_material(native_training_source_pair)
    )
    request = copy.deepcopy(requests[reviewer_zero])
    request["history"][-1]["content"] = "A legacy instruction."
    with pytest.raises(NativeTrainingContextError, match="framework contact envelope"):
        NativeTrainingContextProjector().project(
            request, responses[reviewer_zero], completions[reviewer_zero],
        )


def test_rehashed_framework_tool_message_cannot_change_counted_result(
    native_training_source_pair,
):
    from speech_aware_evidence_acquisition.core.model import FrozenCoreError
    from speech_aware_evidence_acquisition.rails.hashing import content_hash

    _manifest, requests, responses, completions, first, second = (
        _native_request_material(native_training_source_pair)
    )
    projector = NativeTrainingContextProjector()
    projector.project(requests[first], responses[first], completions[first])
    request = copy.deepcopy(requests[second])
    control = request["history"][-1]
    envelope = json.loads(control["content"])
    visible = json.loads(envelope["messages"][-1]["content"])
    visible["result"]["contract_status"] = "fabricated improvement"
    envelope["messages"][-1]["content"] = json.dumps(visible, sort_keys=True)
    control["content"] = json.dumps(envelope, sort_keys=True)
    control["content_sha256"] = hashlib.sha256(control["content"].encode()).hexdigest()
    completion = {**completions[second], "request_sha256": content_hash(request)}
    with pytest.raises(FrozenCoreError, match="counted observation"):
        projector.project(request, responses[second], completion)


def test_proposal_source_requires_canonical_response_record_join(
    native_training_source_pair, tmp_path,
):
    from speech_aware_evidence_acquisition.rails.training_proposal_context import (
        _source_trajectories,
    )

    manifest, _requests, _responses, _completions, first, _second = (
        _native_request_material(native_training_source_pair)
    )
    rows = [
        json.loads(line) for line in Path(manifest["raw_trace"]["path"]).read_text().splitlines()
    ]
    row = next(row for row in rows if row["record_id"] == first + "/response")
    row["record_id"] = first
    trace = tmp_path / "renamed-response.jsonl"
    trace.write_text("".join(json.dumps(row) + "\n" for row in rows))
    manifest = copy.deepcopy(manifest)
    manifest["raw_trace"] = {
        "path": str(trace), "sha256": hashlib.sha256(trace.read_bytes()).hexdigest(),
    }
    source = tmp_path / "renamed-response-manifest.json"
    source.write_text(json.dumps(manifest))
    with pytest.raises(TrainingProposalContextError, match="ambiguous source response"):
        _source_trajectories(
            {"manifest": {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()}},
            ("slurp:train:1", "slurp:train:10"),
        )


@pytest.mark.parametrize("hash_field", ("request_sha256", "response_sha256"))
def test_abstention_source_rejects_mismatched_output_hash(
    native_training_source_pair, tmp_path, hash_field,
):
    source, sample_ids, sample_id, _derived_id, _trace_path = _abstention_source(
        native_training_source_pair, tmp_path,
    )
    manifest_path = Path(source["manifest"]["path"])
    manifest = json.loads(manifest_path.read_text())
    output_path = Path(manifest["outputs"]["path"])
    rows = [json.loads(line) for line in output_path.read_text().splitlines()]
    next(row for row in rows if row["sample_id"] == sample_id)[hash_field] = "0" * 64
    output_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    manifest["outputs"]["sha256"] = _sha_file(output_path)
    manifest_path.write_text(json.dumps(manifest))
    source["manifest"]["sha256"] = _sha_file(manifest_path)
    with pytest.raises(TrainingProposalContextError, match="abstention derivative"):
        _source_trajectories(source, sample_ids)
