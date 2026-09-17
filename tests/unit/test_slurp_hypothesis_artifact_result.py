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


def _catalog(
    root: Path,
    *,
    max_candidates: int = 3,
    candidate_ids=("alarm_set", "weather_query", "music_play"),
):
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
            for value in candidate_ids
        ],
    }
    path = root / "prepared" / "contracts" / "catalog.json"
    path.parent.mkdir(parents=True)
    raw = (json.dumps(document, sort_keys=True) + "\n").encode()
    path.write_bytes(raw)
    contract = {
        "id": "slurp-intent-hypotheses-v1",
        "max_candidates": max_candidates,
        "source_catalog": {
            "data_relpath": "prepared/contracts/catalog.json",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source_sha256": canonical_sha256(document),
        },
    }
    return contract


def test_candidate_bound_can_reach_the_complete_source_catalog(tmp_path):
    candidate_ids = (
        "alarm_set",
        "weather_query",
        "music_play",
        "calendar_set",
        "email_send",
    )
    contract = _catalog(
        tmp_path, max_candidates=5, candidate_ids=candidate_ids
    )
    validator = build_slurp_hypothesis_artifact_validator(
        contract, data_root=tmp_path
    )
    canonical = validator.canonicalize(
        _response(*candidate_ids), sample_id="slurp:devel:7"
    )
    assert [
        row["intent_id"] for row in json.loads(canonical)["candidates"]
    ] == list(candidate_ids)
    schema = slurp_intent_hypotheses_response_format(
        {}, tmp_path, **contract
    )["json_schema"]["schema"]
    assert schema["properties"]["candidates"]["maxItems"] == 5

    with pytest.raises(ArtifactContentError, match="legal intent count"):
        build_slurp_hypothesis_artifact_validator(
            {**contract, "max_candidates": 6}, data_root=tmp_path
        )


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
        (
            _response("alarm_set", "weather_query", "music_play", "alarm_set"),
            "at most 3",
        ),
    ],
)
def test_hypothesis_content_refuses_unknown_duplicate_or_over_limit(
    tmp_path, raw, match
):
    validator = build_slurp_hypothesis_artifact_validator(
        _catalog(tmp_path), data_root=tmp_path
    )
    with pytest.raises(ValueError, match=match):
        validator.canonicalize(raw, sample_id="slurp:devel:7")


def test_response_format_exposes_exact_canonical_ids_and_no_sample_bookkeeping(
    tmp_path,
):
    schema = slurp_intent_hypotheses_response_format(
        {}, tmp_path, **_catalog(tmp_path)
    )["json_schema"]["schema"]
    assert schema["required"] == ["candidates"]
    assert "sample_id" not in schema["properties"]
    enum = schema["properties"]["candidates"]["items"]["properties"]["intent_id"][
        "enum"
    ]
    assert enum == ["alarm_set", "weather_query", "music_play"]


def test_legacy_contract_preserves_unbounded_distinction_and_32_item_arrays(tmp_path):
    contract = _catalog(tmp_path)
    schema = slurp_intent_hypotheses_response_format({}, tmp_path, **contract)[
        "json_schema"
    ]["schema"]
    candidate = schema["properties"]["candidates"]["items"]["properties"]
    assert candidate["distinction"] == {"type": "string"}
    assert candidate["evidence_refs"] == {
        "type": "array",
        "items": {"type": "string"},
        "maxItems": 32,
    }
    assert candidate["unresolved_fields"] == {
        "type": "array",
        "items": {"type": "string"},
        "maxItems": 32,
    }
    response = json.loads(_response("alarm_set"))
    response["candidates"][0]["distinction"] = "x" * 129
    response["candidates"][0]["evidence_refs"] = [
        f"source-{index}" for index in range(32)
    ]
    response["candidates"][0]["unresolved_fields"] = [
        f"field-{index}" for index in range(32)
    ]
    assert build_slurp_hypothesis_artifact_validator(
        contract, data_root=tmp_path
    ).canonicalize(json.dumps(response), sample_id="slurp:devel:7")


def test_explicit_output_bounds_are_emitted_and_enforced_without_repair(tmp_path):
    contract = {
        **_catalog(tmp_path),
        "max_distinction_chars": 3,
        "max_evidence_refs": 0,
        "max_unresolved_fields": 1,
    }
    validator = build_slurp_hypothesis_artifact_validator(contract, data_root=tmp_path)
    valid = json.dumps(
        {
            "candidates": [
                {
                    "intent_id": "alarm_set",
                    "distinction": "yes",
                    "evidence_refs": [],
                    "unresolved_fields": ["time"],
                }
            ]
        }
    )
    assert json.loads(validator.canonicalize(valid, sample_id="slurp:devel:7"))[
        "candidates"
    ][0] == {
        "intent_id": "alarm_set",
        "distinction": "yes",
        "evidence_refs": [],
        "unresolved_fields": ["time"],
    }

    for field, value, match in (
        ("distinction", "four", "distinction"),
        ("evidence_refs", ["source"], "evidence_refs"),
        ("unresolved_fields", ["time", "date"], "unresolved_fields"),
    ):
        response = json.loads(valid)
        response["candidates"][0][field] = value
        with pytest.raises(ArtifactContentError, match=match):
            validator.canonicalize(json.dumps(response), sample_id="slurp:devel:7")

    candidate = slurp_intent_hypotheses_response_format({}, tmp_path, **contract)[
        "json_schema"
    ]["schema"]["properties"]["candidates"]["items"]["properties"]
    assert candidate["distinction"]["maxLength"] == 3
    assert candidate["evidence_refs"]["maxItems"] == 0
    assert candidate["unresolved_fields"]["maxItems"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_distinction_chars", 0),
        ("max_distinction_chars", True),
        ("max_evidence_refs", -1),
        ("max_evidence_refs", 33),
        ("max_unresolved_fields", -1),
        ("max_unresolved_fields", 33),
    ],
)
def test_output_bound_contract_values_are_strictly_bounded(tmp_path, field, value):
    contract = {**_catalog(tmp_path), field: value}
    with pytest.raises(ArtifactContentError, match="output bound"):
        build_slurp_hypothesis_artifact_validator(contract, data_root=tmp_path)


def test_fixed_top_three_contract_refuses_a_collapsed_shortlist(tmp_path):
    contract = {**_catalog(tmp_path), "min_candidates": 3}
    validator = build_slurp_hypothesis_artifact_validator(contract, data_root=tmp_path)
    with pytest.raises(ArtifactContentError, match="at least 3"):
        validator.canonicalize(_response("alarm_set"), sample_id="slurp:devel:7")
    schema = slurp_intent_hypotheses_response_format({}, tmp_path, **contract)[
        "json_schema"
    ]["schema"]
    assert schema["properties"]["candidates"]["minItems"] == 3


def test_registered_source_program_is_one_typed_contact():
    program = default_phase_program("phase-intent-hypotheses-only-v1")
    assert program.max_contacts == 1
    assert [
        (phase.name, phase.knowledge, phase.response_format_id)
        for phase in program.phases
    ] == [("hypotheses", "none", "slurp-intent-hypotheses-v1")]


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


# ---------------------------------------------------------------------------
# FIX-1 standing fallback candidate
# (docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md)
# ---------------------------------------------------------------------------


def test_fallback_candidates_is_validated_but_never_reaches_the_response_schema(
    tmp_path,
):
    contract = _catalog(tmp_path)
    with_fallback = {**contract, "fallback_candidates": ["music_play"]}
    validator = build_slurp_hypothesis_artifact_validator(
        with_fallback, data_root=tmp_path
    )
    assert validator.fallback_candidates == ("music_play",)
    # The Perception response-format SCHEMA -- what the model itself is
    # asked to produce -- is byte-identical whether or not a fallback is
    # configured: the option never widens or narrows the model's own
    # contract.
    with_schema = slurp_intent_hypotheses_response_format(
        {}, tmp_path, **with_fallback
    )
    without_schema = slurp_intent_hypotheses_response_format({}, tmp_path, **contract)
    assert with_schema == without_schema
    assert "fallback_candidates" not in json.dumps(with_schema)


def test_fallback_candidates_refuses_an_id_outside_the_legal_inventory(tmp_path):
    contract = _catalog(tmp_path)
    with pytest.raises(ArtifactContentError, match="outside the legal inventory"):
        build_slurp_hypothesis_artifact_validator(
            {**contract, "fallback_candidates": ["not_a_real_intent"]},
            data_root=tmp_path,
        )


def test_fallback_candidates_refuses_more_than_two_ids(tmp_path):
    contract = _catalog(tmp_path)
    with pytest.raises(ArtifactContentError, match="more than 2"):
        build_slurp_hypothesis_artifact_validator(
            {
                **contract,
                "fallback_candidates": ["alarm_set", "weather_query", "music_play"],
            },
            data_root=tmp_path,
        )


def test_fallback_distinction_without_fallback_candidates_is_refused(tmp_path):
    contract = _catalog(tmp_path)
    with pytest.raises(ArtifactContentError, match="fallback_distinction"):
        build_slurp_hypothesis_artifact_validator(
            {**contract, "fallback_distinction": "An override with no configured id."},
            data_root=tmp_path,
        )


def test_fallback_candidates_absent_is_the_documented_default():
    from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
        DEFAULT_FALLBACK_DISTINCTION,
    )
    from speech_aware_evidence_acquisition.rails.artifact_results import (
        SlurpHypothesisArtifactValidator,
    )

    validator = SlurpHypothesisArtifactValidator(
        legal_intent_ids=("alarm_set",), min_candidates=1, max_candidates=1,
        source_sha256="a" * 64,
    )
    assert validator.fallback_candidates == ()
    assert validator.fallback_distinction == DEFAULT_FALLBACK_DISTINCTION
