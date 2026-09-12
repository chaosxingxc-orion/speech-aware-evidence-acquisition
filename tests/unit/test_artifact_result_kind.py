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
