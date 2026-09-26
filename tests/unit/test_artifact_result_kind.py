from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntimeError,
    validate_artifact_result_binding,
)
from speech_aware_evidence_acquisition.core.roster import split_identity_hash
from speech_aware_evidence_acquisition.data.splits import prefixed


def _roster(repo: Path):
    sample_ids = ("slurp:train:1", "slurp:train:2")
    identity = split_identity_hash(prefixed("slurp", sample_ids))
    document = {
        "schema": "saea-roster-receipt-v1",
        "roster_id": "SLURP-TRAIN-CONSTRUCTION-2",
        "carrier_lock_key": "slurp",
        "split_role": "discovery",
        "roster_role": "construction",
        "seed": 1,
        "per_stratum": {"all": 2},
        "strata_counts": {"all": 2},
        "items": [{"sample_id": sample, "stratum": "all"} for sample in sample_ids],
        "excluded_count": 0,
        "split_identity_hash": identity,
    }
    path = repo / "docs" / "receipts" / "rosters" / "train-2.json"
    path.parent.mkdir(parents=True)
    raw = json.dumps(document).encode()
    path.write_bytes(raw)
    return sample_ids, identity, path, hashlib.sha256(raw).hexdigest()


def _plan(identity, **changes):
    values = {
        "execution_profile": "bounded-discovery-probe",
        "split_role": "discovery",
        "carrier_lock_key": "slurp",
        "split_identity_hash": identity,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _values(path, sha, **changes):
    values = {
        "arm": "speech-feature-query",
        "policy": "phase-direct-only-v1",
        "scorers": [],
        "result_kind": "artifact",
        "artifact_result": {
            "schema": "saea-artifact-result-binding-v1",
            "role": "training-feedback-proposal",
            "construction_roster": {
                "repo_relpath": str(path.relative_to(path.parents[3])),
                "sha256": sha,
            },
        },
    }
    values.update(changes)
    return values


def test_artifact_result_binding_requires_exact_train_construction_roster(tmp_path):
    samples, identity, path, sha = _roster(tmp_path)
    binding = validate_artifact_result_binding(
        _values(path, sha),
        plan=_plan(identity),
        repo_root=tmp_path,
        sample_ids=samples,
    )
    assert binding["role"] == "training-feedback-proposal"
    assert binding["construction_roster"]["sha256"] == sha


@pytest.mark.parametrize(
    "change,match",
    [
        ({"scorers": ["slurp-slu-official-train"]}, "scorers"),
        ({"arm": "bare-core"}, "speech-feature"),
        ({"policy": "fixed"}, "phase program"),
    ],
)
def test_artifact_result_binding_rejects_task_scoring_or_wrong_path(
    tmp_path, change, match
):
    samples, identity, path, sha = _roster(tmp_path)
    with pytest.raises(FlightRuntimeError, match=match):
        validate_artifact_result_binding(
            _values(path, sha, **change),
            plan=_plan(identity),
            repo_root=tmp_path,
            sample_ids=samples,
        )


def test_result_kind_default_preserves_historical_task_answer_config(tmp_path):
    assert (
        validate_artifact_result_binding(
            {"arm": "bare-core", "policy": "fixed", "scorers": ["cost"]},
            plan=_plan("a" * 64),
            repo_root=tmp_path,
            sample_ids=("s1",),
        )
        is None
    )
    with pytest.raises(FlightRuntimeError, match="artifact_result"):
        validate_artifact_result_binding(
            {"arm": "bare-core", "policy": "fixed", "artifact_result": {}},
            plan=_plan("a" * 64),
            repo_root=tmp_path,
            sample_ids=("s1",),
        )


def test_typed_train_binding_rejects_slurp_non_train_construction_roster(
    tmp_path,
):
    from test_training_feedback_artifacts import _contract, _prepared_contexts

    samples, _identity, path, _sha = _roster(tmp_path)
    devel_samples = tuple(sample.replace(":train:", ":devel:") for sample in samples)
    identity = split_identity_hash(prefixed("slurp", devel_samples))
    document = json.loads(path.read_text())
    document["items"] = [
        {"sample_id": sample, "stratum": "all"} for sample in devel_samples
    ]
    document["split_identity_hash"] = identity
    raw = json.dumps(document).encode()
    path.write_bytes(raw)
    data_root = tmp_path / "data"
    prepared, prepared_sha = _prepared_contexts(
        data_root / "prepared.json",
        {sample: ("option-1", "option-2") for sample in devel_samples},
    )
    values = _values(
        path,
        hashlib.sha256(raw).hexdigest(),
        prepared_training_feedback={"synthetic": True},
    )
    values["artifact_result"] = {
        "schema": "saea-artifact-result-binding-v3",
        "role": "training-feedback-proposal",
        "construction_roster": values["artifact_result"]["construction_roster"],
        "content_contract": _contract(
            "prepared.json", prepared_sha, prepared["output_sha256"]
        ),
    }
    values["policy"] = "phase-training-feedback-proposal-v1"
    with pytest.raises(FlightRuntimeError, match="TRAIN construction samples"):
        validate_artifact_result_binding(
            values,
            plan=_plan(identity),
            repo_root=tmp_path,
            sample_ids=devel_samples,
            data_root=data_root,
        )


@pytest.mark.parametrize("change", [
    {}, {"result_kind": "task-answer"}, {"prepared_training_feedback": None},
    {"phase_supply": {"direct": {"provider": "unexpected"}}},
    {"phase_tools": {"direct": ["extra"]}},
    {"scorers": ["slurp-slu-official-train"]}, {"whole_roster_wave_barrier": False},
    {"task_instruction": "Answer the original task"}, {"policy": "phase-direct-then-slots-v1"},
])
def test_prepared_text_admits_only_registered_train_artifact_stages(tmp_path, change):
    from speech_aware_evidence_acquisition.rails.prepared_text import PREPARED_TEXT_INSTRUCTION
    samples, identity, path, sha = _roster(tmp_path)
    values = _values(path, sha, arm="prepared-context-text",
                     prepared_training_feedback={"source": "verified by later loader"},
                     task_instruction=PREPARED_TEXT_INSTRUCTION, evidence_source="none",
                     whole_roster_wave_barrier=True, live_phase_fit={"registered": True})
    values.update(change)
    if change:
        with pytest.raises(FlightRuntimeError):
            validate_artifact_result_binding(values, plan=_plan(identity), repo_root=tmp_path,
                                            sample_ids=samples)
    else:
        assert validate_artifact_result_binding(values, plan=_plan(identity), repo_root=tmp_path,
                                                sample_ids=samples)["role"] == "training-feedback-proposal"
