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
from speech_aware_evidence_acquisition.rails.artifact_results import (
    ArtifactContentError,
    build_slurp_hypothesis_artifact_validator,
    slurp_intent_hypotheses_response_format,
)
from speech_aware_evidence_acquisition.rails.candidate_contract_lookup import (
    canonical_sha256,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program


def _catalog(root: Path):
    document = {
        "schema": "saea-slurp-candidate-contract-catalog-v1",
        "projection_version": "saea-slurp-candidate-contract-projection-v1",
        "source_schema_id": "fixture",
        "source_schema_sha256": "a" * 64,
        "source_split": "train",
        "source_identity_sha256": "b" * 64,
        "source_utterance_count": 3,
        "retention": {"min_share": 0.02, "examples_per_type": 0},
        "profiles": [
            {"candidate_id": value, "utterances": 1, "slot_mentions": 0, "types": []}
            for value in ("alarm_set", "weather_query", "music_play")
        ],
    }
    path = root / "prepared" / "contracts" / "catalog.json"
    path.parent.mkdir(parents=True)
    raw = (json.dumps(document, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    contract = {
        "id": "slurp-intent-hypotheses-v1",
        "max_candidates": 3,
        "source_catalog": {
            "data_relpath": "prepared/contracts/catalog.json",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_sha256": canonical_sha256(document),
        },
    }
    return contract


def _response(*ids: str) -> str:
    return json.dumps(
        {
            "candidates": [
                {
                    "intent_id": value,
                    "distinction": f"observed distinction {index}",
                    "evidence_refs": [],
                    "unresolved_fields": [],
                }
                for index, value in enumerate(ids)
            ]
        }
    )


def test_compact_response_is_canonicalized_without_model_visible_bookkeeping(tmp_path):
    contract = _catalog(tmp_path)
    validator = build_slurp_hypothesis_artifact_validator(contract, data_root=tmp_path)
    raw = _response("weather_query", "alarm_set")
    canonical = json.loads(validator.canonicalize(raw, sample_id="slurp:devel:7"))
    assert set(json.loads(raw)) == {"candidates"}
    assert canonical["sample_id"] == "slurp:devel:7"
    assert [row["intent_id"] for row in canonical["candidates"]] == [
        "weather_query",
        "alarm_set",
    ]


@pytest.mark.parametrize(
    "raw,match",
    [
        (_response("unknown"), "not legal"),
        (_response("alarm_set", "alarm_set"), "unique"),
        (_response("alarm_set", "weather_query", "music_play", "alarm_set"), "at most 3"),
    ],
)
def test_hypothesis_content_refuses_unknown_duplicate_or_over_limit(tmp_path, raw, match):
    validator = build_slurp_hypothesis_artifact_validator(
        _catalog(tmp_path), data_root=tmp_path
    )
    with pytest.raises(ValueError, match=match):
        validator.canonicalize(raw, sample_id="slurp:devel:7")


def test_response_format_exposes_exact_canonical_ids_and_no_sample_bookkeeping(tmp_path):
    schema = slurp_intent_hypotheses_response_format(
        {}, tmp_path, **_catalog(tmp_path)
    )["json_schema"]["schema"]
    assert schema["required"] == ["candidates"]
    assert "sample_id" not in schema["properties"]
    enum = schema["properties"]["candidates"]["items"]["properties"]["intent_id"]["enum"]
    assert enum == ["alarm_set", "weather_query", "music_play"]


def test_fixed_top_three_contract_refuses_a_collapsed_shortlist(tmp_path):
    contract = {**_catalog(tmp_path), "min_candidates": 3}
    validator = build_slurp_hypothesis_artifact_validator(contract, data_root=tmp_path)
    with pytest.raises(ArtifactContentError, match="at least 3"):
        validator.canonicalize(
            _response("alarm_set"), sample_id="slurp:devel:7"
        )
    schema = slurp_intent_hypotheses_response_format(
        {}, tmp_path, **contract
    )["json_schema"]["schema"]
    assert schema["properties"]["candidates"]["minItems"] == 3


def test_registered_source_program_is_one_typed_contact():
    program = default_phase_program("phase-intent-hypotheses-only-v1")
    assert program.max_contacts == 1
    assert [(phase.name, phase.knowledge, phase.response_format_id) for phase in program.phases] == [
        ("hypotheses", "none", "slurp-intent-hypotheses-v1")
    ]


def test_dev_artifact_binding_requires_exact_evaluation_roster_and_catalog(tmp_path):
    samples = ("slurp:devel:1", "slurp:devel:2")
    identity = split_identity_hash(prefixed("slurp", samples))
    roster = {
        "schema": "saea-roster-receipt-v1",
        "roster_id": "SLURP-DEV-FIXTURE",
        "carrier_lock_key": "slurp",
        "split_role": "dev",
        "roster_role": "evaluation",
        "seed": 1,
        "per_stratum": {"all": 2},
        "strata_counts": {"all": 2},
        "items": [{"sample_id": sid, "stratum": "all"} for sid in samples],
        "excluded_count": 0,
        "split_identity_hash": identity,
    }
    path = tmp_path / "docs" / "rosters" / "dev.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(roster))
    values = {
        "arm": "speech-feature-query",
        "policy": "phase-intent-hypotheses-only-v1",
        "scorers": [],
        "result_kind": "artifact",
        "artifact_result": {
            "schema": "saea-artifact-result-binding-v2",
            "role": "slurp-intent-hypotheses",
            "source_roster": {
                "repo_relpath": "docs/rosters/dev.json",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            },
            "content_contract": _catalog(tmp_path),
        },
    }
    plan = SimpleNamespace(
        execution_profile="bounded-discovery-probe",
        split_role="dev",
        carrier_lock_key="slurp",
        split_identity_hash=identity,
    )
    binding = validate_artifact_result_binding(
        values,
        plan=plan,
        repo_root=tmp_path,
        data_root=tmp_path,
        sample_ids=samples,
    )
    assert binding["role"] == "slurp-intent-hypotheses"

    with pytest.raises(FlightRuntimeError, match="exactly bind"):
        validate_artifact_result_binding(
            values,
            plan=plan,
            repo_root=tmp_path,
            data_root=tmp_path,
            sample_ids=(samples[0],),
        )

    values["artifact_result"]["content_contract"]["max_candidates"] = 4
    with pytest.raises(FlightRuntimeError, match="content contract"):
        validate_artifact_result_binding(
            values,
            plan=plan,
            repo_root=tmp_path,
            data_root=tmp_path,
            sample_ids=samples,
        )


def test_catalog_tamper_is_refused_before_content_use(tmp_path):
    contract = _catalog(tmp_path)
    (tmp_path / contract["source_catalog"]["data_relpath"]).write_text("{}")
    with pytest.raises(ArtifactContentError, match="file SHA"):
        build_slurp_hypothesis_artifact_validator(contract, data_root=tmp_path)
