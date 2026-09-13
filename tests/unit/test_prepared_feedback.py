# ruff: noqa: F811  # imported pytest fixture shares its requested name
"""Synthetic verification for initial prepared-feedback ORG state."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from test_group_relative_feedback import source_pair  # noqa: F401

from speech_aware_evidence_acquisition.rails.prepared_feedback import (
    PREPARED_FEEDBACK_STATE_KIND,
    PreparedFeedbackError,
    PreparedFeedbackStateArtifact,
    _state_id,
    load_prepared_feedback,
)
from speech_aware_evidence_acquisition.rails.training_proposal_context import (
    build_training_proposal_contexts,
    prepare_training_proposal_contexts,
)

pytest_plugins = ("test_bundle",)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _data_relative_paths(value: object, root: Path) -> object:
    if isinstance(value, dict):
        return {
            key: (
                str(Path(nested).resolve().relative_to(root.resolve()))
                if key == "path" else _data_relative_paths(nested, root)
            )
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [_data_relative_paths(nested, root) for nested in value]
    return value


def _prepared_spec(source_pair, tmp_path):
    document = build_training_proposal_contexts(source_pair)
    artifact = tmp_path / "prepared-contexts.json"
    artifact_pin = prepare_training_proposal_contexts(source_pair, artifact)
    source_path = tmp_path / "source-bindings.json"
    source_path.write_text(json.dumps(_data_relative_paths(copy.deepcopy(source_pair), tmp_path)))
    spec = {
        "schema": "saea-prepared-training-feedback-v1",
        "artifact": {"relpath": artifact.name, "sha256": artifact_pin["sha256"]},
        "source_bindings": {"relpath": source_path.name, "sha256": _sha(source_path)},
        "language": "en",
        "max_context_bytes": 1_000_000,
    }
    return spec, document, artifact, source_path


def _load(spec, document, tmp_path, sample_ids=None, **overrides):
    active = tuple(sample_ids or (row["source_sample_id"] for row in document["contexts"]))
    arguments = {
        "repo_root": tmp_path,
        "data_root": tmp_path,
        "sample_ids": active,
        "construction_roster_sha256": document["construction_roster_sha256"],
        "result_kind": "artifact",
        "artifact_role": "training-feedback-proposal",
    }
    arguments.update(overrides)
    return load_prepared_feedback(spec, **arguments)


def test_loader_rebuilds_pins_and_orders_per_sample_states(source_pair, tmp_path):  # noqa: F811
    spec, document, _artifact, _source = _prepared_spec(source_pair, tmp_path)
    active = tuple(reversed([row["source_sample_id"] for row in document["contexts"]]))
    states, receipt = _load(spec, document, tmp_path, active)
    assert tuple(states) == active
    assert receipt["state_bindings"] == [
        {
            "sample_id": sample_id,
            "state_id": states[sample_id].state_id,
            "model_context_sha256": states[sample_id].model_context_sha256,
        }
        for sample_id in active
    ]
    for sample_id, state in states.items():
        context = next(row for row in document["contexts"] if row["source_sample_id"] == sample_id)
        assert state.state_kind == PREPARED_FEEDBACK_STATE_KIND
        assert state.cited_value_ids == ()
        assert sample_id not in state.content
        assert json.loads(state.content) == context["model_context"]
        assert state.model_context_sha256 == context["model_context_sha256"]
        assert "source_response_sha256" not in state.as_json()
        assert PreparedFeedbackStateArtifact.from_json(state.as_json()) == state


def test_loader_rejects_bad_pins_inputs_and_mutated_source(source_pair, tmp_path):  # noqa: F811
    spec, document, artifact, _source = _prepared_spec(source_pair, tmp_path)
    bad_source = copy.deepcopy(spec)
    bad_source["source_bindings"]["sha256"] = "0" * 64
    with pytest.raises(PreparedFeedbackError, match="wrong hash"):
        _load(bad_source, document, tmp_path)

    bad_artifact = copy.deepcopy(spec)
    bad_artifact["artifact"]["sha256"] = "0" * 64
    with pytest.raises(PreparedFeedbackError, match="wrong hash"):
        _load(bad_artifact, document, tmp_path)

    wrapper = json.loads(artifact.read_text())
    wrapper["inputs"]["document_sha256"] = "0" * 64
    artifact.write_text(json.dumps(wrapper))
    bad_inputs = copy.deepcopy(spec)
    bad_inputs["artifact"]["sha256"] = _sha(artifact)
    with pytest.raises(PreparedFeedbackError, match="identity mismatch"):
        _load(bad_inputs, document, tmp_path)

    artifact.unlink()
    spec, document, _artifact, _source = _prepared_spec(source_pair, tmp_path)
    manifest = Path(source_pair[0]["config"]["manifest"]["path"])
    manifest.write_text("{}")
    with pytest.raises(PreparedFeedbackError, match="cannot verify"):
        _load(spec, document, tmp_path)


@pytest.mark.parametrize(
    ("sample_ids", "result_kind", "artifact_role", "message"),
    [
        (("foreign",), "artifact", "training-feedback-proposal", "active cohort"),
        (None, "task-answer", "training-feedback-proposal", "artifact role"),
        (None, "artifact", "other", "artifact role"),
    ],
)
def test_loader_refuses_wrong_cohort_or_result_role(
    source_pair, tmp_path, sample_ids, result_kind, artifact_role, message
):  # noqa: F811
    spec, document, _artifact, _source = _prepared_spec(source_pair, tmp_path)
    with pytest.raises(PreparedFeedbackError, match=message):
        _load(
            spec, document, tmp_path, sample_ids,
            result_kind=result_kind, artifact_role=artifact_role,
        )


def test_loader_enforces_content_limit_and_never_writes(source_pair, tmp_path):  # noqa: F811
    spec, document, _artifact, _source = _prepared_spec(source_pair, tmp_path)
    before = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    spec["max_context_bytes"] = 1
    with pytest.raises(PreparedFeedbackError, match="max_context_bytes"):
        _load(spec, document, tmp_path)
    after = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert after == before


def test_state_refuses_non_latin_content_without_claiming_language_detection():
    state = PreparedFeedbackStateArtifact(
        state_id=_state_id(
            prepared_artifact_sha256="a" * 64,
            source_feedback_sha256="b" * 64,
            construction_roster_sha256="c" * 64,
            model_context_sha256="d" * 64,
        ),
        state_kind=PREPARED_FEEDBACK_STATE_KIND,
        content=json.dumps({"text": "English Ελληνικά"}, separators=(",", ":")),
        cited_value_ids=(),
        prepared_artifact_sha256="a" * 64,
        source_feedback_sha256="b" * 64,
        construction_roster_sha256="c" * 64,
        model_context_sha256="d" * 64,
    )
    with pytest.raises(PreparedFeedbackError, match="non-Latin"):
        state.validate()
