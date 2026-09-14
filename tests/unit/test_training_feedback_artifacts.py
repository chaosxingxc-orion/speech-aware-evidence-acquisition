from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.preparation import canonical_bytes, digest
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.rails.training_feedback_artifacts import (
    TrainingFeedbackArtifactError,
    build_training_feedback_artifact_validator,
    training_feedback_response_format,
)


def _prepared_contexts(path, sample_options=None):
    sample_options = sample_options or {
        "slurp:train:1": ("option-1", "option-2"),
        "slurp:train:2": ("option-1", "option-2", "option-3"),
    }
    contexts = []
    for sample_id, options in sample_options.items():
        contexts.append(
            {
                "source_sample_id": sample_id,
                "source_feedback_sha256": "a" * 64,
                "candidate_bindings": [
                    {
                        "label": option,
                        "candidate_id": f"hidden-{index}",
                        "reward_link_sha256": "b" * 64,
                        "source": {
                            "source_sample_id": sample_id,
                            "partition_role": "train",
                        },
                    }
                    for index, option in enumerate(options, 1)
                ],
                "model_context": {"task_family": "slurp", "candidates": []},
                "model_context_sha256": "c" * 64,
            }
        )
    output = {
        "schema": "saea-training-proposal-contexts-v2",
        "status": "source-verified",
        "role": "training-feedback-proposal",
        "construction_roster_sha256": "d" * 64,
        "feedback_sha256": "e" * 64,
        "sources": [],
        "contexts": contexts,
    }
    document = {
        "schema": "saea-prepared-artifact-v1",
        "kind": "training-proposal-contexts",
        "inputs": {"fixture": "synthetic"},
        "contact_class": "model-free",
        "output": output,
        "output_sha256": digest(output),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(document))
    return document, hashlib.sha256(path.read_bytes()).hexdigest()


def _contract(path, file_sha, output_sha, **changes):
    contract = {
        "id": "training-feedback-proposal-v1",
        "prepared_contexts": {
            "data_relpath": str(path),
            "sha256": file_sha,
            "output_sha256": output_sha,
        },
        "applicability": {
            "allowed_task_ids": ["slurp"],
            "allowed_roles": ["solver"],
            "allowed_component_tags": ["org", "use"],
        },
    }
    contract.update(changes)
    return contract


def _response(**changes):
    proposal = {
        "kind": "corrective-experience",
        "diagnosis": "The first option omitted a necessary distinction.",
        "guidance": "When that structural state is present, retain the explicit distinction.",
        "limitations": ["This is guidance for later disjoint evaluation."],
        "applicability": {
            "task_ids": ["slurp"],
            "phases": ["solver"],
            "component_tags": ["org"],
            "required_conditions": ["state:prior-response-present"],
            "excluded_conditions": ["state:prior-response-absent"],
        },
        "primary_option": "option-2",
        "supporting_options": ["option-2"],
        "contradicting_options": ["option-1"],
    }
    proposal.update(changes)
    return json.dumps({"status": "provisional", "proposals": [proposal]})


def test_typed_train_proposal_canonicalizes_separately_and_permits_no_proposal(tmp_path):
    path = tmp_path / "prepared.json"
    document, file_sha = _prepared_contexts(path)
    contract = _contract("prepared.json", file_sha, document["output_sha256"])
    validator = build_training_feedback_artifact_validator(contract, data_root=tmp_path)
    raw = _response()
    canonical = validator.canonicalize(raw, sample_id="slurp:train:1")
    assert canonical != raw
    assert json.loads(canonical)["status"] == "provisional"
    assert validator.canonicalize(
        '{"proposals":[],"status":"provisional"}', sample_id="slurp:train:1"
    ) == '{"proposals":[],"status":"provisional"}'
    schema = training_feedback_response_format({}, tmp_path, **contract)
    assert schema["json_schema"]["schema"]["properties"]["proposals"]["maxItems"] == 2
    proposal_schema = schema["json_schema"]["schema"]["properties"]["proposals"][
        "items"
    ]
    assert proposal_schema["properties"]["primary_option"]["enum"] == [
        "option-1",
        "option-2",
        "option-3",
    ]


def test_shared_runtime_preserves_raw_response_and_seals_typed_content(tmp_path):
    path = tmp_path / "prepared.json"
    document, file_sha = _prepared_contexts(path)
    validator = build_training_feedback_artifact_validator(
        _contract("prepared.json", file_sha, document["output_sha256"]),
        data_root=tmp_path,
    )
    sample_id = "slurp:train:1"
    raw = _response()
    runtime = object.__new__(FlightRuntime)
    runtime._output_rows = [{"sample_id": sample_id, "response_text": raw}]
    runtime._artifact_result_binding = {"role": "training-feedback-proposal"}
    runtime._artifact_content_validator = validator
    runtime._plan = SimpleNamespace(carrier_lock_key="slurp")
    runtime._composed = SimpleNamespace(
        values={
            "arm": "speech-feature-query",
            "carrier_lock_key": "slurp",
            "result_kind": "artifact",
        }
    )
    timing = SimpleNamespace(
        sample_id=sample_id,
        request_id="request-1",
        request_sha256="1" * 64,
        response_sha256="2" * 64,
        response_text_sha256=hashlib.sha256(raw.encode()).hexdigest(),
    )
    rows = runtime._canonical_output_rows(SimpleNamespace(timings=(timing,)))
    assert rows[0]["text"] == raw
    assert rows[0]["artifact_content"] == validator.canonicalize(
        raw, sample_id=sample_id
    )
    assert rows[0]["artifact_source_sha256"] == file_sha


@pytest.mark.parametrize(
    "response,sample_id,match",
    [
        (_response(primary_option="option-3", supporting_options=["option-3"]), "slurp:train:1", "this sample"),
        (_response(guidance="Use slurp:train:1 as a lookup key."), "slurp:train:1", "sample ID"),
        (_response(guidance="Apply 修正 here."), "slurp:train:1", "non-Latin"),
        (
            _response(applicability={
                "task_ids": ["slurp"], "phases": ["solver"],
                "component_tags": ["org"],
                "required_conditions": ["signal:semantic-error"],
                "excluded_conditions": [],
            }),
            "slurp:train:1", "executable runtime scope",
        ),
    ],
)
def test_typed_train_proposal_rejects_hidden_ids_wrong_sample_options_and_semantic_tags(
    tmp_path, response, sample_id, match
):
    path = tmp_path / "prepared.json"
    document, file_sha = _prepared_contexts(path)
    validator = build_training_feedback_artifact_validator(
        _contract("prepared.json", file_sha, document["output_sha256"]), data_root=tmp_path
    )
    with pytest.raises(TrainingFeedbackArtifactError, match=match):
        validator.canonicalize(response, sample_id=sample_id)


def test_typed_train_proposal_refuses_source_byte_or_output_hash_tamper(tmp_path):
    path = tmp_path / "prepared.json"
    document, file_sha = _prepared_contexts(path)
    contract = _contract("prepared.json", file_sha, document["output_sha256"])
    build_training_feedback_artifact_validator(contract, data_root=tmp_path)
    contract["prepared_contexts"]["output_sha256"] = "0" * 64
    with pytest.raises(TrainingFeedbackArtifactError, match="identity"):
        build_training_feedback_artifact_validator(contract, data_root=tmp_path)
    contract["prepared_contexts"]["output_sha256"] = document["output_sha256"]
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(TrainingFeedbackArtifactError, match="file SHA"):
        build_training_feedback_artifact_validator(contract, data_root=tmp_path)


@pytest.mark.parametrize(
    "relpath",
    [
        "prepared//contexts.json",
        "prepared/./contexts.json",
        "prepared/contexts.json/",
        "prepared:C/contexts.json",
        "prepared/../contexts.json",
        r"prepared\contexts.json",
    ],
)
def test_typed_train_proposal_refuses_noncanonical_raw_source_paths(tmp_path, relpath):
    path = tmp_path / "prepared" / "contexts.json"
    document, file_sha = _prepared_contexts(path)
    contract = _contract(relpath, file_sha, document["output_sha256"])
    with pytest.raises(TrainingFeedbackArtifactError, match="canonical relative POSIX"):
        build_training_feedback_artifact_validator(contract, data_root=tmp_path)
