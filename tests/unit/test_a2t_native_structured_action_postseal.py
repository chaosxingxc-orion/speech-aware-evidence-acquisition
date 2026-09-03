"""Synthetic-only tests for the native structured-action post-seal helper."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_native_structured_action_postseal import (
    CELL_ORDER,
    STRICT_CELLS,
    NativeStructuredActionPostsealError,
    analyze_four_cells,
    build_four_job_plan,
    evaluate_mechanism_gates,
    materialize_historical_subsets,
    prove_strict_cells_sealed,
    select_four_cell_oracle,
)
from speech_aware_evidence_acquisition.core.bundle import VerifiedBundle


IDS = tuple(f"tier{index}:00000{index}" for index in range(1, 9))
V1_RUN_ID = "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1"
V2_RUN_ID = "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-RECOVERY-V2"
V2_SPLIT_IDENTITY = "b15cf0c0874f7af7d10af6cc9801aae4535bbe57b5a6dc3add50bcdb40fd93aa"
V2_PROTOCOL = "a2f24da7254a62020d4dff5d681c873af0ff11e71126dae7b72b7b9b2a7158d0"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path.resolve()


def _output_row(
    sample_id: str, text: str, *, arm: str = "fixture-arm"
) -> dict[str, object]:
    response_text_sha256 = hashlib.sha256(text.encode()).hexdigest()
    return {
        "request_id": f"request-{sample_id}",
        "sample_id": sample_id,
        "carrier_lock_key": "audio2tool",
        "arm": arm,
        "text": text,
        "admitted": True,
        "request_sha256": "a" * 64,
        "response_sha256": "b" * 64,
        "response_text_sha256": response_text_sha256,
    }


def _verified_bundle(
    tmp_path: Path,
    cell: str,
    ids=IDS,
    *,
    texts=None,
    attempt_state="FINALIZED",
    run_id: str | None = None,
    split_identity: str = "d" * 64,
    protocol: str = "e" * 64,
) -> VerifiedBundle:
    effective_run_id = run_id or f"FIXTURE-{cell}"
    manifest_path = _write(tmp_path / cell / "run-manifest.json", "{}\n")
    outputs_path = tmp_path / cell / "outputs.jsonl"
    rows = tuple(
        _output_row(
            sample_id, (texts or {}).get(sample_id, '[{"name":"safe","arguments":{}}]')
        )
        for sample_id in ids
    )
    _write(
        outputs_path, "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    )
    attempt_path = _write(
        tmp_path / cell / "attempt.json",
        json.dumps(
            {
                "run_id": effective_run_id,
                "attempt_id": "attempt-fixture-0001",
                "state": attempt_state,
            },
            sort_keys=True,
        )
        + "\n",
    )
    raw_trace = _write(tmp_path / cell / "trace.jsonl", '{"sealed":true}\n')
    trace_manifest = _write(tmp_path / cell / "trace-manifest.json", "{}\n")
    manifest = {
        "run_id": effective_run_id,
        "status": "COMPLETED",
        "split": {
            "ids": sorted(ids),
            "count": len(ids),
            "identity_hash": split_identity,
        },
        "outputs": {
            "path": str(outputs_path.resolve()),
            "sha256": _sha256(outputs_path),
        },
        "raw_trace": {"path": str(raw_trace), "sha256": _sha256(raw_trace)},
        "trace_manifest": {
            "path": str(trace_manifest),
            "sha256": _sha256(trace_manifest),
        },
        "arm": "fixture-arm",
        "config": {"config_hash": "c" * 64, "fragments": {}},
        "plan": {
            "schema": "saea-execution-plan-v1",
            "study": "speech-aware-evidence-acquisition",
            "run_id": effective_run_id,
            "execution_profile": "bounded-discovery-probe",
            "carrier_lock_key": "audio2tool",
            "split_role": "discovery",
            "split_identity_hash": split_identity,
            "planned_model_calls": 8,
            "planned_gpu_hours": 0.1,
            "planned_speech_audio_seconds": 46,
            "protocol_hash": protocol,
            "attempt_id": "attempt-fixture-0001",
        },
        "session_receipt": None,
        "attempt": {
            "run_id": effective_run_id,
            "attempt_id": "attempt-fixture-0001",
            "state_path": str(attempt_path),
        },
        "protocol_hash": protocol,
        "cost": {"calls_used": 8},
    }
    return VerifiedBundle(
        manifest_path=manifest_path,
        manifest=manifest,
        outputs_path=outputs_path.resolve(),
        outputs_rows=rows,
        trace_records={"sealed/request": {}, "sealed/response": {}},
        split_ids=frozenset(ids),
        attempt_state=attempt_state,
    )


def _seal_descriptor(bundle: VerifiedBundle) -> dict[str, object]:
    manifest = bundle.manifest
    return {
        "manifest": str(bundle.manifest_path),
        "manifest_sha256": _sha256(bundle.manifest_path),
        "outputs_sha256": manifest["outputs"]["sha256"],
        "raw_trace_sha256": manifest["raw_trace"]["sha256"],
        "trace_manifest_sha256": manifest["trace_manifest"]["sha256"],
    }


def _recovery_receipt(tmp_path: Path, bundle: VerifiedBundle) -> Path:
    manifest = bundle.manifest
    original_manifest = _write(tmp_path / "original-registry-manifest.json", "{}\n")
    attempt = manifest["attempt"]
    receipt = tmp_path / "recovery-flight-receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schema": "saea-a2t-native-structured-action-fixed8-recovery-v2-flight-v1",
                "run_id": V2_RUN_ID,
                "registry_recovery": {
                    "cell": "REGISTRY_STRICT_ACTION",
                    "recovered_from_attempt_id": "attempt-fixture-0001",
                    "recovered_from_attempt_state": "ABORTED",
                    "registry_recontacted": False,
                    "registry_model_contacts": 0,
                    "completed_rows": 8,
                    "successor_run_id": V2_RUN_ID,
                    "verified_manifest_run_id": manifest["run_id"],
                    "successor_split_identity_hash": V2_SPLIT_IDENTITY,
                    "successor_protocol_hash": V2_PROTOCOL,
                    "successor_manifest_path": str(bundle.manifest_path),
                    "successor_manifest_sha256": _sha256(bundle.manifest_path),
                    "source_attempt": {
                        "attempt_id": attempt["attempt_id"],
                        "state": "ABORTED",
                        "sha256": _sha256(Path(attempt["state_path"])),
                    },
                    "original_source_artifacts": {
                        "manifest_path": str(original_manifest),
                        "manifest_sha256": _sha256(original_manifest),
                        "outputs_sha256": manifest["outputs"]["sha256"],
                        "raw_trace_sha256": manifest["raw_trace"]["sha256"],
                        "trace_manifest_sha256": manifest["trace_manifest"]["sha256"],
                    },
                    "source_artifacts": {
                        "manifest_path": str(bundle.manifest_path),
                        "manifest_sha256": _sha256(bundle.manifest_path),
                        "outputs_path": manifest["outputs"]["path"],
                        "outputs_sha256": manifest["outputs"]["sha256"],
                        "raw_trace_path": manifest["raw_trace"]["path"],
                        "raw_trace_sha256": manifest["raw_trace"]["sha256"],
                        "trace_manifest_path": manifest["trace_manifest"]["path"],
                        "trace_manifest_sha256": manifest["trace_manifest"]["sha256"],
                    },
                },
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return receipt


def _authorization(tmp_path: Path):
    bundles = {
        cell: _verified_bundle(tmp_path, cell, attempt_state="OPENED")
        for cell in STRICT_CELLS
    }
    by_path = {bundle.manifest_path: bundle for bundle in bundles.values()}
    authorization = prove_strict_cells_sealed(
        strict_seals={
            cell: _seal_descriptor(bundle) for cell, bundle in bundles.items()
        },
        sample_ids=IDS,
        verifier=lambda path: by_path[Path(path).resolve()],
    )
    return authorization, bundles


def _score_payload(manifest: Path, cell_index: int, *, exact_count: int = 8):
    details = []
    for index, sample_id in enumerate(IDS):
        exact = 1.0 if index < exact_count else 0.0
        details.append(
            {
                "sample_id": sample_id,
                "tier": sample_id.split(":", 1)[0],
                "parsed": True,
                "exact_match": exact,
                "tool_accuracy": 1.0,
                "slot_precision": 1.0 if exact else 0.5,
                "slot_recall": 1.0 if exact else 0.5,
                "slot_f1": 1.0 if exact else 0.5,
            }
        )
    slot_total = 80
    slot_tp = 80 if exact_count == 8 else 72
    return {
        "manifest": str(manifest.resolve()),
        "verified": True,
        "scores": {
            "a2t-toolcall": {
                "aggregate": {
                    "samples": 8,
                    "parse_failures": 0,
                    "exact_match": exact_count / 8,
                    "tool_accuracy": 1.0,
                    "slot_precision": slot_tp / slot_total,
                    "slot_recall": slot_tp / slot_total,
                    "slot_f1": slot_tp / slot_total,
                    "slot_true_positives": slot_tp,
                    "slot_expected_total": slot_total,
                    "slot_predicted_total": slot_total,
                },
                "per_sample": details,
            }
        },
    }


def test_proof_requires_both_complete_strict_bundles_and_all_seal_hashes(
    tmp_path: Path,
):
    authorization, bundles = _authorization(tmp_path)

    assert authorization.sample_ids == IDS
    assert set(authorization.strict_bundles) == set(STRICT_CELLS)

    incomplete = {STRICT_CELLS[0]: _seal_descriptor(bundles[STRICT_CELLS[0]])}
    with pytest.raises(
        NativeStructuredActionPostsealError, match="exactly the two strict"
    ):
        prove_strict_cells_sealed(
            strict_seals=incomplete,
            sample_ids=IDS,
            verifier=lambda _path: bundles[STRICT_CELLS[0]],
        )

    drifted = {cell: _seal_descriptor(bundle) for cell, bundle in bundles.items()}
    drifted[STRICT_CELLS[0]]["raw_trace_sha256"] = "0" * 64
    with pytest.raises(NativeStructuredActionPostsealError, match="raw trace SHA-256"):
        prove_strict_cells_sealed(
            strict_seals=drifted,
            sample_ids=IDS,
            verifier=lambda path: {
                bundle.manifest_path: bundle for bundle in bundles.values()
            }[Path(path).resolve()],
        )


def test_proof_refuses_partial_or_mismatched_identity_before_protected_access(
    tmp_path: Path,
):
    bundles = {
        cell: _verified_bundle(tmp_path, cell, attempt_state="OPENED")
        for cell in STRICT_CELLS
    }
    first = bundles[STRICT_CELLS[0]]
    first.manifest["split"]["ids"] = list(IDS[:-1])
    opened: list[Path] = []

    def verifier(path):
        opened.append(Path(path))
        return {bundle.manifest_path: bundle for bundle in bundles.values()}[
            Path(path).resolve()
        ]

    with pytest.raises(
        NativeStructuredActionPostsealError, match="exact eight-row identity"
    ):
        prove_strict_cells_sealed(
            strict_seals={
                cell: _seal_descriptor(bundle) for cell, bundle in bundles.items()
            },
            sample_ids=IDS,
            verifier=verifier,
        )

    assert len(opened) == 1


def test_proof_requires_strict_cells_to_remain_sealed_and_unscored(
    tmp_path: Path,
):
    bundles = {
        cell: _verified_bundle(tmp_path, cell, attempt_state="FINALIZED")
        for cell in STRICT_CELLS
    }

    with pytest.raises(
        NativeStructuredActionPostsealError, match="sealed and unscored"
    ):
        prove_strict_cells_sealed(
            strict_seals={
                cell: _seal_descriptor(bundle) for cell, bundle in bundles.items()
            },
            sample_ids=IDS,
            verifier=lambda path: {
                bundle.manifest_path: bundle for bundle in bundles.values()
            }[Path(path).resolve()],
        )


def test_proof_refuses_an_ordinary_aborted_strict_bundle(tmp_path: Path):
    bundles = {
        "REGISTRY_STRICT_ACTION": _verified_bundle(
            tmp_path, "registry", attempt_state="ABORTED"
        ),
        "HANDBOOK_STRICT_ACTION": _verified_bundle(
            tmp_path, "handbook", attempt_state="OPENED"
        ),
    }

    with pytest.raises(
        NativeStructuredActionPostsealError, match="sealed and unscored"
    ):
        prove_strict_cells_sealed(
            strict_seals={
                cell: _seal_descriptor(bundle) for cell, bundle in bundles.items()
            },
            sample_ids=IDS,
            verifier=lambda path: {
                bundle.manifest_path: bundle for bundle in bundles.values()
            }[Path(path).resolve()],
        )


def test_proof_admits_only_the_hash_pinned_aborted_registry_recovery(
    tmp_path: Path,
):
    registry = _verified_bundle(
        tmp_path,
        "registry",
        attempt_state="ABORTED",
        run_id=V1_RUN_ID,
        split_identity=V2_SPLIT_IDENTITY,
        protocol=V2_PROTOCOL,
    )
    handbook = _verified_bundle(tmp_path, "handbook", attempt_state="OPENED", run_id=V2_RUN_ID)
    receipt = _recovery_receipt(tmp_path, registry)
    registry_seal = _seal_descriptor(registry)
    registry_seal.update(
        {
            "recovered_from_aborted_attempt": True,
            "recovery_receipt": receipt,
            "recovery_receipt_sha256": _sha256(receipt),
        }
    )

    authorization = prove_strict_cells_sealed(
        strict_seals={
            "REGISTRY_STRICT_ACTION": registry_seal,
            "HANDBOOK_STRICT_ACTION": _seal_descriptor(handbook),
        },
        sample_ids=IDS,
        verifier=lambda path: {
            registry.manifest_path: registry,
            handbook.manifest_path: handbook,
        }[Path(path).resolve()],
    )

    assert authorization.strict_bundles["REGISTRY_STRICT_ACTION"] is registry


def test_proof_refuses_recovery_receipt_that_reports_registry_recontact(
    tmp_path: Path,
):
    registry = _verified_bundle(
        tmp_path,
        "registry",
        attempt_state="ABORTED",
        run_id=V1_RUN_ID,
        split_identity=V2_SPLIT_IDENTITY,
        protocol=V2_PROTOCOL,
    )
    handbook = _verified_bundle(tmp_path, "handbook", attempt_state="OPENED")
    receipt = _recovery_receipt(tmp_path, registry)
    document = json.loads(receipt.read_text(encoding="utf-8"))
    document["registry_recovery"]["registry_model_contacts"] = 1
    receipt.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    registry_seal = _seal_descriptor(registry)
    registry_seal.update(
        {
            "recovered_from_aborted_attempt": True,
            "recovery_receipt": receipt,
            "recovery_receipt_sha256": _sha256(receipt),
        }
    )

    with pytest.raises(
        NativeStructuredActionPostsealError, match="registry_model_contacts"
    ):
        prove_strict_cells_sealed(
            strict_seals={
                "REGISTRY_STRICT_ACTION": registry_seal,
                "HANDBOOK_STRICT_ACTION": _seal_descriptor(handbook),
            },
            sample_ids=IDS,
            verifier=lambda path: {
                registry.manifest_path: registry,
                handbook.manifest_path: handbook,
            }[Path(path).resolve()],
        )


def test_proof_refuses_recovery_receipt_with_stale_source_artifact_hash(
    tmp_path: Path,
):
    registry = _verified_bundle(
        tmp_path,
        "registry",
        attempt_state="ABORTED",
        run_id=V1_RUN_ID,
        split_identity=V2_SPLIT_IDENTITY,
        protocol=V2_PROTOCOL,
    )
    handbook = _verified_bundle(tmp_path, "handbook", attempt_state="OPENED")
    receipt = _recovery_receipt(tmp_path, registry)
    document = json.loads(receipt.read_text(encoding="utf-8"))
    document["registry_recovery"]["source_artifacts"]["outputs_sha256"] = "0" * 64
    receipt.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    registry_seal = _seal_descriptor(registry)
    registry_seal.update(
        {
            "recovered_from_aborted_attempt": True,
            "recovery_receipt": receipt,
            "recovery_receipt_sha256": _sha256(receipt),
        }
    )

    with pytest.raises(
        NativeStructuredActionPostsealError, match="source artifact hash drift"
    ):
        prove_strict_cells_sealed(
            strict_seals={
                "REGISTRY_STRICT_ACTION": registry_seal,
                "HANDBOOK_STRICT_ACTION": _seal_descriptor(handbook),
            },
            sample_ids=IDS,
            verifier=lambda path: {
                registry.manifest_path: registry,
                handbook.manifest_path: handbook,
            }[Path(path).resolve()],
        )


def test_proof_refuses_recovery_receipt_without_successor_lineage(
    tmp_path: Path,
):
    registry = _verified_bundle(
        tmp_path,
        "registry",
        attempt_state="ABORTED",
        run_id=V1_RUN_ID,
        split_identity=V2_SPLIT_IDENTITY,
        protocol=V2_PROTOCOL,
    )
    handbook = _verified_bundle(tmp_path, "handbook", attempt_state="OPENED")
    receipt = _recovery_receipt(tmp_path, registry)
    document = json.loads(receipt.read_text(encoding="utf-8"))
    document["registry_recovery"].pop("successor_manifest_sha256")
    receipt.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    registry_seal = _seal_descriptor(registry)
    registry_seal.update(
        {
            "recovered_from_aborted_attempt": True,
            "recovery_receipt": receipt,
            "recovery_receipt_sha256": _sha256(receipt),
        }
    )

    with pytest.raises(
        NativeStructuredActionPostsealError, match="successor manifest"
    ):
        prove_strict_cells_sealed(
            strict_seals={
                "REGISTRY_STRICT_ACTION": registry_seal,
                "HANDBOOK_STRICT_ACTION": _seal_descriptor(handbook),
            },
            sample_ids=IDS,
            verifier=lambda path: {
                registry.manifest_path: registry,
                handbook.manifest_path: handbook,
            }[Path(path).resolve()],
        )


def test_proof_refuses_v2_recovery_with_an_uncorrected_split_or_protocol(
    tmp_path: Path,
):
    registry = _verified_bundle(
        tmp_path,
        "registry",
        attempt_state="ABORTED",
        run_id=V1_RUN_ID,
        split_identity=V2_SPLIT_IDENTITY,
        protocol=V2_PROTOCOL,
    )
    handbook = _verified_bundle(tmp_path, "handbook", attempt_state="OPENED", run_id=V2_RUN_ID)
    receipt = _recovery_receipt(tmp_path, registry)
    document = json.loads(receipt.read_text(encoding="utf-8"))
    document["registry_recovery"]["successor_protocol_hash"] = "0" * 64
    receipt.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    registry_seal = _seal_descriptor(registry)
    registry_seal.update(
        {
            "recovered_from_aborted_attempt": True,
            "recovery_receipt": receipt,
            "recovery_receipt_sha256": _sha256(receipt),
        }
    )

    with pytest.raises(
        NativeStructuredActionPostsealError, match="V2 successor correction"
    ):
        prove_strict_cells_sealed(
            strict_seals={
                "REGISTRY_STRICT_ACTION": registry_seal,
                "HANDBOOK_STRICT_ACTION": _seal_descriptor(handbook),
            },
            sample_ids=IDS,
            verifier=lambda path: {
                registry.manifest_path: registry,
                handbook.manifest_path: handbook,
            }[Path(path).resolve()],
        )


def test_historical_materialization_is_inaccessible_without_a_valid_seal_proof(
    tmp_path: Path,
):
    parent = _verified_bundle(tmp_path, "parent", ids=IDS + ("extra:000009",))
    source = {
        "REGISTRY_NO_SCHEMA": {
            "manifest": str(parent.manifest_path),
            "manifest_sha256": _sha256(parent.manifest_path),
            "outputs_sha256": parent.manifest["outputs"]["sha256"],
        },
        "HANDBOOK_NO_SCHEMA": {
            "manifest": str(parent.manifest_path),
            "manifest_sha256": _sha256(parent.manifest_path),
            "outputs_sha256": parent.manifest["outputs"]["sha256"],
        },
    }

    with pytest.raises(NativeStructuredActionPostsealError, match="seal authorization"):
        materialize_historical_subsets(
            authorization=object(),
            historical_sources=source,
            output_root=tmp_path / "subsets",
            verifier=lambda _path: pytest.fail(
                "protected parent was opened before seal proof"
            ),
            manifest_builder=lambda **_kwargs: pytest.fail(
                "manifest builder must not run"
            ),
        )


def test_historical_materialization_requires_a_finalized_parent_attempt(
    tmp_path: Path,
):
    authorization, _strict = _authorization(tmp_path / "strict")
    parent = _verified_bundle(
        tmp_path,
        "parent",
        ids=IDS + ("extra:000009",),
        attempt_state="OPENED",
    )
    source = {
        cell: {
            "manifest": str(parent.manifest_path),
            "manifest_sha256": _sha256(parent.manifest_path),
            "outputs_sha256": parent.manifest["outputs"]["sha256"],
        }
        for cell in ("REGISTRY_NO_SCHEMA", "HANDBOOK_NO_SCHEMA")
    }

    with pytest.raises(
        NativeStructuredActionPostsealError, match="must be FINALIZED"
    ):
        materialize_historical_subsets(
            authorization=authorization,
            historical_sources=source,
            output_root=tmp_path / "subsets",
            verifier=lambda _path: parent,
            manifest_builder=lambda **_kwargs: pytest.fail("manifest must not build"),
        )


def test_materializes_exact_identity_historical_outputs_only_after_seal(tmp_path: Path):
    authorization, _strict = _authorization(tmp_path / "strict")
    parent_a = _verified_bundle(
        tmp_path, "registry-parent", ids=IDS + ("extra:000009",)
    )
    parent_b = _verified_bundle(
        tmp_path, "handbook-parent", ids=IDS + ("extra:000009",)
    )
    parents = {
        "REGISTRY_NO_SCHEMA": parent_a,
        "HANDBOOK_NO_SCHEMA": parent_b,
    }
    sources = {
        cell: {
            "manifest": str(bundle.manifest_path),
            "manifest_sha256": _sha256(bundle.manifest_path),
            "outputs_sha256": bundle.manifest["outputs"]["sha256"],
        }
        for cell, bundle in parents.items()
    }

    def manifest_builder(**kwargs):
        path = kwargs["run_dir"] / "derived.run-manifest.json"
        path.write_text(
            json.dumps(
                {
                    "status": "COMPLETED",
                    "split": {"ids": sorted(IDS), "count": 8},
                    "outputs": {"path": str(kwargs["result"].outputs_path)},
                }
            ),
            encoding="utf-8",
        )
        return path

    materialized = materialize_historical_subsets(
        authorization=authorization,
        historical_sources=sources,
        output_root=tmp_path / "subsets",
        verifier=lambda path: {
            bundle.manifest_path: bundle for bundle in parents.values()
        }[Path(path).resolve()],
        manifest_builder=manifest_builder,
    )

    assert set(materialized) == {"REGISTRY_NO_SCHEMA", "HANDBOOK_NO_SCHEMA"}
    for item in materialized.values():
        rows = [
            json.loads(line)
            for line in item.outputs.read_text(encoding="utf-8").splitlines()
        ]
        assert {row["sample_id"] for row in rows} == set(IDS)
        assert len(rows) == 8
        assert item.manifest.is_file()
        assert item.model_contacts == 0


def test_builds_exactly_four_unique_whole_manifest_jobs_for_four_workers(
    tmp_path: Path,
):
    authorization, _strict = _authorization(tmp_path / "strict")
    manifests = {}
    bundles = {}
    for cell in CELL_ORDER:
        bundle = _verified_bundle(tmp_path / "whole", cell)
        bundles[bundle.manifest_path] = bundle
        manifests[cell] = {"manifest": bundle.manifest_path, "sample_ids": IDS}

    plan = build_four_job_plan(
        authorization=authorization,
        manifests=manifests,
        jobs_path=tmp_path / "score-jobs.jsonl",
        score_output_dir=tmp_path / "scores",
        verifier=lambda path: bundles[Path(path).resolve()],
    )

    assert plan.workers == 4
    assert len(plan.jobs) == 4
    assert [job.job_id for job in plan.jobs] == list(CELL_ORDER)
    assert all(job.operation == "score" for job in plan.jobs)
    assert plan.dataset_sharding is False
    assert plan.shard_metric_averaging is False
    assert plan.command[-3:] == ("--workers", "4", "--include-per-sample")
    serialized_jobs = [
        json.loads(line)
        for line in plan.jobs_path.read_text(encoding="utf-8").splitlines()
    ]
    assert all(set(job) == {"job_id", "manifest"} for job in serialized_jobs)

    duplicate = dict(manifests)
    duplicate["HANDBOOK_STRICT_ACTION"] = duplicate["REGISTRY_STRICT_ACTION"]
    with pytest.raises(
        NativeStructuredActionPostsealError, match="duplicate scorer job"
    ):
        build_four_job_plan(
            authorization=authorization,
            manifests=duplicate,
            jobs_path=tmp_path / "duplicate.jsonl",
            score_output_dir=tmp_path / "duplicate-scores",
            verifier=lambda path: bundles[Path(path).resolve()],
        )


def test_analyzes_official_scores_hard_validity_legal_keys_and_pairs(tmp_path: Path):
    authorization, strict = _authorization(tmp_path / "strict")
    bundles = {
        "REGISTRY_NO_SCHEMA": _verified_bundle(tmp_path, "registry-no-schema"),
        "REGISTRY_STRICT_ACTION": strict["REGISTRY_STRICT_ACTION"],
        "HANDBOOK_NO_SCHEMA": _verified_bundle(tmp_path, "handbook-no-schema"),
        "HANDBOOK_STRICT_ACTION": strict["HANDBOOK_STRICT_ACTION"],
    }
    payloads = {
        cell: _score_payload(bundle.manifest_path, CELL_ORDER.index(cell))
        for cell, bundle in bundles.items()
    }
    sealed = {
        cell: {
            "manifest": str(bundle.manifest_path),
            "manifest_sha256": _sha256(bundle.manifest_path),
            "outputs": str(bundle.outputs_path),
            "outputs_sha256": _sha256(bundle.outputs_path),
        }
        for cell, bundle in bundles.items()
    }
    registry = (
        {"tool_name": "safe", "signature": "safe()", "argument_constraints": ""},
    )
    report = analyze_four_cells(
        authorization=authorization,
        score_payloads=payloads,
        sealed_cells=sealed,
        registry_rows=registry,
        legal_key_sets_by_tool={"safe": ((),)},
    )

    assert report.cells["REGISTRY_STRICT_ACTION"].parse_count == 8
    assert report.cells["REGISTRY_STRICT_ACTION"].exact_count == 8
    assert report.cells["REGISTRY_STRICT_ACTION"].tool_count == 8
    assert report.cells["REGISTRY_STRICT_ACTION"].slot_micro_f1 == 1.0
    assert report.cells["REGISTRY_STRICT_ACTION"].hard_valid_count == 8
    assert report.cells["REGISTRY_STRICT_ACTION"].legal_key_set_count == 8
    assert report.paired["REGISTRY_STRICT_ACTION_vs_REGISTRY_NO_SCHEMA"].wins == 0
    assert report.paired["HANDBOOK_STRICT_ACTION_vs_REGISTRY_STRICT_ACTION"].harms == 0

    payloads["HANDBOOK_STRICT_ACTION"]["scores"]["a2t-toolcall"]["per_sample"].pop()
    with pytest.raises(
        NativeStructuredActionPostsealError, match="complete per-sample"
    ):
        analyze_four_cells(
            authorization=authorization,
            score_payloads=payloads,
            sealed_cells=sealed,
            registry_rows=registry,
            legal_key_sets_by_tool={"safe": ((),)},
        )


def test_oracle_uses_exact_then_row_slot_then_tool_then_frozen_cell_order(
    tmp_path: Path,
):
    authorization, strict = _authorization(tmp_path / "strict")
    bundles = {
        "REGISTRY_NO_SCHEMA": _verified_bundle(tmp_path, "registry-no-schema"),
        "REGISTRY_STRICT_ACTION": strict["REGISTRY_STRICT_ACTION"],
        "HANDBOOK_NO_SCHEMA": _verified_bundle(tmp_path, "handbook-no-schema"),
        "HANDBOOK_STRICT_ACTION": strict["HANDBOOK_STRICT_ACTION"],
    }
    payloads = {
        cell: _score_payload(bundle.manifest_path, 0)
        for cell, bundle in bundles.items()
    }
    for cell in CELL_ORDER:
        row1 = payloads[cell]["scores"]["a2t-toolcall"]["per_sample"][1]
        row1.update(exact_match=0.0, slot_f1=0.5, tool_accuracy=0.5)
        row2 = payloads[cell]["scores"]["a2t-toolcall"]["per_sample"][2]
        row2.update(exact_match=0.0, slot_f1=0.5, tool_accuracy=0.5)
        row3 = payloads[cell]["scores"]["a2t-toolcall"]["per_sample"][3]
        row3.update(exact_match=0.0, slot_f1=0.5, tool_accuracy=0.5)
    payloads["HANDBOOK_STRICT_ACTION"]["scores"]["a2t-toolcall"]["per_sample"][1][
        "slot_f1"
    ] = 0.9
    payloads["HANDBOOK_NO_SCHEMA"]["scores"]["a2t-toolcall"]["per_sample"][2][
        "tool_accuracy"
    ] = 0.9
    sealed = {
        cell: {
            "manifest": str(bundle.manifest_path),
            "manifest_sha256": _sha256(bundle.manifest_path),
            "outputs": str(bundle.outputs_path),
            "outputs_sha256": _sha256(bundle.outputs_path),
        }
        for cell, bundle in bundles.items()
    }

    selections, summary = select_four_cell_oracle(
        authorization=authorization,
        score_payloads=payloads,
        sealed_cells=sealed,
    )
    by_id = {row.sample_id: row.cell for row in selections}

    assert by_id[IDS[0]] == "REGISTRY_NO_SCHEMA"
    assert by_id[IDS[1]] == "HANDBOOK_STRICT_ACTION"
    assert by_id[IDS[2]] == "HANDBOOK_NO_SCHEMA"
    assert by_id[IDS[3]] == "REGISTRY_NO_SCHEMA"
    assert (
        summary["selection_rule"]
        == "exact_match > slot_f1 > tool_accuracy > frozen_cell_order"
    )


def test_mechanism_gates_require_oracle_and_strict_thresholds_and_apply_tie_rule(
    tmp_path: Path,
):
    authorization, strict = _authorization(tmp_path / "strict")
    bundles = {
        "REGISTRY_NO_SCHEMA": _verified_bundle(tmp_path, "registry-no-schema"),
        "REGISTRY_STRICT_ACTION": strict["REGISTRY_STRICT_ACTION"],
        "HANDBOOK_NO_SCHEMA": _verified_bundle(tmp_path, "handbook-no-schema"),
        "HANDBOOK_STRICT_ACTION": strict["HANDBOOK_STRICT_ACTION"],
    }
    payloads = {
        "REGISTRY_NO_SCHEMA": _score_payload(
            bundles["REGISTRY_NO_SCHEMA"].manifest_path, 0, exact_count=4
        ),
        "REGISTRY_STRICT_ACTION": _score_payload(
            bundles["REGISTRY_STRICT_ACTION"].manifest_path, 1, exact_count=8
        ),
        "HANDBOOK_NO_SCHEMA": _score_payload(
            bundles["HANDBOOK_NO_SCHEMA"].manifest_path, 2, exact_count=4
        ),
        "HANDBOOK_STRICT_ACTION": _score_payload(
            bundles["HANDBOOK_STRICT_ACTION"].manifest_path, 3, exact_count=8
        ),
    }
    sealed = {
        cell: {
            "manifest": str(bundle.manifest_path),
            "manifest_sha256": _sha256(bundle.manifest_path),
            "outputs": str(bundle.outputs_path),
            "outputs_sha256": _sha256(bundle.outputs_path),
        }
        for cell, bundle in bundles.items()
    }
    report = analyze_four_cells(
        authorization=authorization,
        score_payloads=payloads,
        sealed_cells=sealed,
        registry_rows=(
            {"tool_name": "safe", "signature": "safe()", "argument_constraints": ""},
        ),
        legal_key_sets_by_tool={"safe": ((),)},
    )
    oracle_payload = _score_payload(
        tmp_path / "oracle.run-manifest.json", 0, exact_count=8
    )

    verdict = evaluate_mechanism_gates(
        report=report, oracle_score_payload=oracle_payload
    )

    assert verdict.passed is True
    assert verdict.selected_strict_cell == "REGISTRY_STRICT_ACTION"
    assert all(verdict.gates.values())

    oracle_payload["scores"]["a2t-toolcall"]["aggregate"]["slot_f1"] = 0.89
    failed = evaluate_mechanism_gates(
        report=report, oracle_score_payload=oracle_payload
    )
    assert failed.passed is False
    assert failed.gates["oracle_reachability"] is False
