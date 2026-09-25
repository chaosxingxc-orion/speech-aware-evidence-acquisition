# ruff: noqa: F811
"""Replay consolidation lineage through the existing candidate attestation entry."""

from __future__ import annotations

import copy
import json
from types import SimpleNamespace
from pathlib import Path

import pytest
from test_provisional_candidate_materialization import (  # noqa: F401
    materialization_world,
    _sha,
    _write_json,
    source_pair,
    _spawn_live_matching_process,
)
from speech_aware_evidence_acquisition.core.provisional_candidate_materialization import (
    MaterializationError,
    prepare_provisional_candidates,
)
from speech_aware_evidence_acquisition.core.provisional_candidate_consolidation import (
    CONFIG_SCHEMA,
)
from speech_aware_evidence_acquisition.rails.candidate_experience_memory import (
    _records,
    prepare_candidate_experience_source_attestation,
)
from speech_aware_evidence_acquisition.rails.experience_consolidation import (
    initialize_candidate_snapshot,
)
from speech_aware_evidence_acquisition.rails.experience_memory import ExperienceRecord


pytest_plugins = ("test_bundle",)


@pytest.fixture
def consolidation_world(materialization_world, monkeypatch):
    import speech_aware_evidence_acquisition.core.provisional_candidate_consolidation as module

    w = materialization_world
    # The proposal fixture verifies its own materialization, contexts and pins.
    proposal = prepare_provisional_candidates(
        config_path=w["config_path"],
        expected_config_sha256=_sha(w["config_path"]),
        data_root=w["data_root"],
    )
    output = json.loads(Path(proposal["path"]).read_text())["output"]
    construction = output["provenance"]["construction_roster_sha256"]
    records = [
        ExperienceRecord.from_json(r)
        for row in output["samples"]
        for r in row["records"]
    ]
    roster = [row["source_sample_id"] for row in output["samples"]]
    base = initialize_candidate_snapshot(
        memory_id="system-memory",
        train_construction_sha256=construction,
        expected_train_sample_ids=roster,
    )
    plan = {
        "operations": [{"operation": "ADD", "proposal_id": records[0].record_id}],
    }
    plan_path = w["data_root"] / "runs/consolidation/run-manifest.json"
    manifest = {
        "status": "COMPLETED",
        "result_kind": "artifact",
        "run_id": "CONSOLIDATE-1",
        "protocol_hash": "a" * 64,
        "artifact_result": {
            "schema": "saea-artifact-result-binding-v1",
            "role": "training-feedback-proposal",
        },
        "split": {"role": "discovery", "carrier_lock_key": "slurp", "ids": [roster[0]]},
        "scorers": [],
    }
    _write_json(plan_path, manifest)
    bundle = SimpleNamespace(
        manifest=manifest,
        attempt_state="FINALIZED",
        outputs_rows=({"sample_id": roster[0], "text": json.dumps(plan)},),
    )
    monkeypatch.setattr(module, "verify_bundle", lambda path: bundle)
    config = {
        "schema": CONFIG_SCHEMA,
        "materialization_id": "consolidated-round-one",
        "memory_id": "system-memory",
        "max_candidates": 5,
        "initial_materialization": None,
        "rounds": [
            {
                "round_id": "round-one",
                "base_snapshot_sha256": base["content_sha256"],
                "proposal_materialization": {
                    "path": str(w["config_path"]),
                    "sha256": _sha(w["config_path"]),
                },
                "consolidation_bundle": {
                    "path": str(plan_path),
                    "sha256": _sha(plan_path),
                },
                "consolidation_sample_id": roster[0],
                "consolidation_protocol_hash": "a" * 64,
            }
        ],
    }
    path = w["data_root"] / "coordination/consolidation-config.json"
    _write_json(path, config)
    return {
        **w,
        "consolidation_config": config,
        "consolidation_config_path": path,
        "plan": plan,
        "plan_bundle": bundle,
        "plan_path": plan_path,
        "proposal": proposal,
        "records": records,
        "base": base,
    }


def execute(w):
    return prepare_provisional_candidates(
        config_path=w["consolidation_config_path"],
        expected_config_sha256=_sha(w["consolidation_config_path"]),
        data_root=w["data_root"],
    )


def test_shared_materialization_and_attestation_replay_real_record_lineage(
    consolidation_world,
):
    w = consolidation_world
    result = execute(w)
    output = json.loads(Path(result["path"]).read_text())["output"]
    assert output["schema"] == "saea-provisional-consolidated-experience-candidates-v1"
    assert len(output["consolidation_receipts"]) == 1
    produced = _records(output, output["provenance"]["construction_roster_sha256"])
    assert len(produced) == 1
    assert produced[0].source == w["records"][0].source
    assert produced[0].guidance == w["records"][0].guidance
    assert produced[0].record_id != w["records"][0].record_id
    assert produced[0].validation.status == "provisional"
    again = execute(w)
    assert again["sha256"] == result["sha256"]
    attested = prepare_candidate_experience_source_attestation(
        config_path=w["consolidation_config_path"],
        expected_config_sha256=_sha(w["consolidation_config_path"]),
        data_root=w["data_root"],
        candidate_artifact_relpath=str(
            Path(result["path"]).relative_to(w["data_root"])
        ),
        expected_candidate_sha256=result["sha256"],
        output_relpath="prepared/consolidated-attestation.json",
    )
    assert attested["sha256"]
    original = json.loads(Path(w["proposal"]["path"]).read_text())["output"]
    assert original["samples"][0]["records"][0] == w["records"][0].as_json()


@pytest.mark.parametrize(
    "mutation",
    ["aborted", "wrong-protocol", "extra-output", "foreign-anchor", "stale-base"],
)
def test_invalid_model_plan_source_cannot_materialize(consolidation_world, mutation):
    w = consolidation_world
    b = w["plan_bundle"]
    if mutation == "aborted":
        b.attempt_state = "ABORTED"
    if mutation == "wrong-protocol":
        b.manifest["protocol_hash"] = "b" * 64
    if mutation == "extra-output":
        b.outputs_rows = tuple(b.outputs_rows) * 2
    if mutation == "foreign-anchor":
        b.outputs_rows = (
            {"sample_id": "slurp:train:foreign", "text": json.dumps(w["plan"])},
        )
    if mutation == "stale-base":
        w["consolidation_config"]["rounds"][0]["base_snapshot_sha256"] = "0" * 64
        _write_json(w["consolidation_config_path"], w["consolidation_config"])
    with pytest.raises(MaterializationError):
        execute(w)
    assert not (
        w["data_root"] / "provisional/experience-candidates/consolidated-round-one.json"
    ).exists()


def test_no_manual_plan_can_replace_the_sealed_response(consolidation_world):
    w = consolidation_world
    config = w["consolidation_config"]
    config["rounds"][0]["plan"] = w["plan"]
    _write_json(w["consolidation_config_path"], config)
    with pytest.raises(MaterializationError, match="round fields"):
        execute(w)


def test_invalid_operation_does_not_persist_partial_candidate(consolidation_world):
    w = consolidation_world
    plan = copy.deepcopy(w["plan"])
    plan["operations"].append({"operation": "DELETE", "record_id": "missing"})
    w["plan_bundle"].outputs_rows = (
        {
            "sample_id": w["plan_bundle"].outputs_rows[0]["sample_id"],
            "text": json.dumps(plan),
        },
    )
    with pytest.raises(MaterializationError, match="rejected"):
        execute(w)
    assert not (
        w["data_root"] / "provisional/experience-candidates/consolidated-round-one.json"
    ).exists()


def test_three_round_replay_preserves_deleted_identity_and_prior_snapshot(
    consolidation_world, monkeypatch
):
    import speech_aware_evidence_acquisition.core.provisional_candidate_consolidation as module

    w = consolidation_world
    first = execute(w)
    first_bytes = Path(first["path"]).read_bytes()
    first_output = json.loads(first_bytes)["output"]
    first_snapshot = first_output["candidate_snapshot"]
    old_id = first_snapshot["records"][0]["record_id"]
    bundles = {str(w["plan_path"]): w["plan_bundle"]}
    config = copy.deepcopy(w["consolidation_config"])
    output = first_output
    for index, operations in [
        (2, [{"operation": "DELETE", "record_id": old_id}]),
        (3, [{"operation": "ADD", "proposal_id": w["records"][0].record_id}]),
    ]:
        prior_output = output
        plan = {
            "operations": operations,
        }
        manifest = copy.deepcopy(w["plan_bundle"].manifest)
        manifest["run_id"] = f"CONSOLIDATE-{index}"
        path = w["data_root"] / f"runs/consolidation-{index}/run-manifest.json"
        digest = _write_json(path, manifest)
        bundles[str(path)] = SimpleNamespace(
            manifest=manifest,
            attempt_state="FINALIZED",
            outputs_rows=({"sample_id": w["sample_ids"][0], "text": json.dumps(plan)},),
        )
        monkeypatch.setattr(module, "verify_bundle", lambda path: bundles[str(path)])
        config["rounds"].append(
            {
                **config["rounds"][0],
                "round_id": f"round-{index}",
                "base_snapshot_sha256": prior_output["candidate_snapshot"][
                    "content_sha256"
                ],
                "consolidation_bundle": {"path": str(path), "sha256": digest},
            }
        )
        config["materialization_id"] = f"consolidated-round-{index}"
        _write_json(w["consolidation_config_path"], config)
        result = execute(w)
        output = json.loads(Path(result["path"]).read_text())["output"]
    final_id = output["candidate_snapshot"]["records"][0]["record_id"]
    assert final_id != old_id
    assert set(output["candidate_snapshot"]["issued_record_ids"]) == {old_id, final_id}
    assert len(output["consolidation_receipts"]) == 3
    assert Path(first["path"]).read_bytes() == first_bytes


def test_rejection_receipt_retains_raw_operations_without_runtime_candidate(
    consolidation_world,
):
    w = consolidation_world
    bad = {
        "operations": [{"operation": "UNRECOGNIZED"}],
    }
    w["plan_bundle"].outputs_rows = (
        {"sample_id": w["sample_ids"][0], "text": json.dumps(bad)},
    )
    with pytest.raises(MaterializationError, match="receipt"):
        execute(w)
    path = (
        w["data_root"]
        / "provisional/experience-consolidation-rejections/consolidated-round-one.json"
    )
    output = json.loads(path.read_text())["output"]
    assert output["receipt"]["plan"]["operations"] == bad["operations"]
    assert (
        output["receipt"]["plan"]["base_snapshot_sha256"] == w["base"]["content_sha256"]
    )
    assert (
        output["receipt"]["snapshot"] is None and output["runtime_authorized"] is False
    )


def test_candidate_cap_refuses_without_truncation(consolidation_world):
    w = consolidation_world
    config = w["consolidation_config"]
    config["max_candidates"] = 0
    _write_json(w["consolidation_config_path"], config)
    with pytest.raises(MaterializationError, match="no truncation"):
        execute(w)


def test_verified_consolidated_source_reaches_actual_native_tool_history(
    source_pair,
    synthetic_world,
    tmp_path,
    monkeypatch,
):
    """Stub only the consolidation bundle; replay real proposal/source authority."""
    import test_provisional_candidate_materialization as fixtures
    import speech_aware_evidence_acquisition.core.provisional_candidate_consolidation as module

    original = fixtures._real_materialized_source

    def transformed(*args, **kwargs):
        source = original(*args, **kwargs)
        data = source["data_root"]
        proposal = json.loads(Path(source["receipt"]["path"]).read_bytes())["output"]
        records = [
            ExperienceRecord.from_json(r)
            for row in proposal["samples"]
            for r in row["records"]
        ]
        base = initialize_candidate_snapshot(
            memory_id="connected-system-memory",
            train_construction_sha256=source["roster_sha"],
            expected_train_sample_ids=source["sample_ids"],
        )
        plan = {
            "operations": [
                {"operation": "ADD", "proposal_id": r.record_id} for r in records
            ],
        }
        anchor = source["sample_ids"][0]
        manifest = {
            "status": "COMPLETED",
            "result_kind": "artifact",
            "run_id": "SYNTHETIC-CONSOLIDATION",
            "protocol_hash": "a" * 64,
            "scorers": [],
            "artifact_result": {
                "schema": "saea-artifact-result-binding-v1",
                "role": "training-feedback-proposal",
            },
            "split": {
                "role": "discovery",
                "carrier_lock_key": "slurp",
                "ids": [anchor],
            },
        }
        path = data / "runs/connected-consolidation/run-manifest.json"
        sha = _write_json(path, manifest)
        bundle = SimpleNamespace(
            manifest=manifest,
            attempt_state="FINALIZED",
            outputs_rows=({"sample_id": anchor, "text": json.dumps(plan)},),
        )

        def verified(candidate_path):
            assert candidate_path == path
            return bundle

        monkeypatch.setattr(module, "verify_bundle", verified)
        config = {
            "schema": CONFIG_SCHEMA,
            "materialization_id": "connected-consolidated",
            "memory_id": "connected-system-memory",
            "max_candidates": 4,
            "initial_materialization": None,
            "rounds": [
                {
                    "round_id": "round-one",
                    "base_snapshot_sha256": base["content_sha256"],
                    "proposal_materialization": {
                        "path": str(source["config_path"]),
                        "sha256": _sha(source["config_path"]),
                    },
                    "consolidation_bundle": {"path": str(path), "sha256": sha},
                    "consolidation_sample_id": anchor,
                    "consolidation_protocol_hash": "a" * 64,
                }
            ],
        }
        config_path = data / "coordination/connected-consolidation.json"
        config_sha = _write_json(config_path, config)
        result = prepare_provisional_candidates(
            config_path=config_path,
            expected_config_sha256=config_sha,
            data_root=data,
        )
        attestation = prepare_candidate_experience_source_attestation(
            config_path=config_path,
            expected_config_sha256=config_sha,
            data_root=data,
            candidate_artifact_relpath=str(Path(result["path"]).relative_to(data)),
            expected_candidate_sha256=result["sha256"],
            output_relpath="prepared/connected-consolidation-attestation.json",
        )
        return {
            **source,
            "receipt": result,
            "attestation": attestation,
            "config_path": config_path,
            "config": config,
        }

    monkeypatch.setattr(fixtures, "_real_materialized_source", transformed)
    result = fixtures._connected_candidate_native_source(
        source_pair,
        synthetic_world,
        tmp_path,
        monkeypatch,
    )
    assert len(result["memory"].records) == 1
    assert result["memory"].records[0].record_id.startswith("experience-")
    assert result["memory"].records[0].validation.status == "provisional"


def test_duplicate_model_operation_keys_are_refused(consolidation_world):
    w = consolidation_world
    text = (
        '{"operations":[{"operation":"DELETE","operation":"ADD","proposal_id":"'
        + w["records"][0].record_id
        + '"}]}'
    )
    w["plan_bundle"].outputs_rows = ({"sample_id": w["sample_ids"][0], "text": text},)
    with pytest.raises(MaterializationError, match="duplicate"):
        execute(w)


def test_model_cannot_author_custody_metadata(consolidation_world):
    w = consolidation_world
    plan = {**w["plan"], "base_snapshot_sha256": w["base"]["content_sha256"]}
    w["plan_bundle"].outputs_rows = (
        {"sample_id": w["sample_ids"][0], "text": json.dumps(plan)},
    )
    with pytest.raises(MaterializationError, match="operations only"):
        execute(w)
