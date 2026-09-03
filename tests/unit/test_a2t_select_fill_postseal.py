"""No-contact ordering and normalization for SELECT/FILL post-seal analysis."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_select_fill_postseal import (
    LINEAGE_PHASES,
    PHASE_ORDER,
    PostsealError,
    analyze_sealed_inputs,
    bind_select_fill_lineage,
    candidate_set_sha256,
    normalize_mixed_score_payloads,
    reconstruct_pre_score_manifest_sha256,
    sum_phase_efficiency,
    validate_mixed_score_batch,
)


def _write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(path: Path) -> tuple[Path, str]:
    _write(path, {"scores": None, "status": "COMPLETED"})
    return path.resolve(), _sha(path)


def _finalize_manifest(path: Path, scores: Path) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    document["scores"] = {
        "path": str(scores.resolve()),
        "sha256": _sha(scores),
        "bytes": scores.stat().st_size,
    }
    _write(path, document)


def _official(sample_id: str = "tier:000001") -> dict[str, object]:
    row = {
        "sample_id": sample_id,
        "tier": "tier",
        "exact_match": 0.0,
        "tool_accuracy": 1.0,
        "slot_f1": 0.5,
        "parsed": True,
    }
    aggregate = {
        "samples": 1,
        "exact_match": 0.0,
        "tool_accuracy": 1.0,
        "slot_precision": 1.0,
        "slot_recall": 2 / 3,
        "slot_f1": 0.8,
        "per_tier": {
            "tier": {
                "samples": 1,
                "exact_match": 0.0,
                "tool_accuracy": 1.0,
                "slot_precision": 1.0,
                "slot_recall": 2 / 3,
                "slot_f1": 0.8,
            }
        },
    }
    return {"aggregate": aggregate, "per_sample": [row]}


def _scores() -> dict[str, object]:
    return {
        "a2t-toolcall": _official(),
        "cost": {
            "aggregate": {
                "samples": 1,
                "calls": 1,
                "audio_seconds": 1.0,
            },
            "per_sample": [],
        },
    }


def test_reconstructs_the_exact_pre_finalize_manifest_hash(tmp_path: Path) -> None:
    manifest, before = _manifest(tmp_path / "joint.run-manifest.json")
    scores = _write(tmp_path / "joint.scores.json", _scores())
    _finalize_manifest(manifest, scores)

    assert reconstruct_pre_score_manifest_sha256(manifest) == before


def test_normalizes_direct_score_and_three_finalize_payloads(tmp_path: Path) -> None:
    roles = ("direct_m0", "joint_one_call", "joint_draft_revise", "select_then_fill")
    sealed = {}
    result_files = {}
    for role in roles:
        manifest, before = _manifest(tmp_path / role / f"{role}.run-manifest.json")
        sealed[role] = {"manifest": str(manifest), "manifest_sha256": before}
        if role == "direct_m0":
            payload = {
                "verified": True,
                "manifest": str(manifest),
                "scores": _scores(),
            }
        else:
            scores = _write(manifest.parent / f"{role}.scores.json", _scores())
            _finalize_manifest(manifest, scores)
            payload = {
                "verified": True,
                "manifest": str(manifest),
                "scores": str(scores.resolve()),
                "attempt_state": "FINALIZED",
            }
        result_files[role] = _write(tmp_path / "batch" / f"{role}.score.json", payload)

    normalized = normalize_mixed_score_payloads(
        sealed_manifests=sealed,
        result_files=result_files,
    )

    assert set(normalized) == set(roles)
    assert normalized["direct_m0"]["aggregate"]["slot_f1"] == 0.8
    assert normalized["select_then_fill"]["per_sample"][0]["slot_f1"] == 0.5


def test_normalizes_all_four_score_only_payloads_without_manifest_mutation(
    tmp_path: Path,
) -> None:
    roles = ("direct_m0", "joint_one_call", "joint_draft_revise", "select_then_fill")
    sealed = {}
    result_files = {}
    for role in roles:
        manifest, before = _manifest(tmp_path / role / f"{role}.run-manifest.json")
        sealed[role] = {"manifest": str(manifest), "manifest_sha256": before}
        result_files[role] = _write(
            tmp_path / "batch" / f"{role}.score.json",
            {
                "verified": True,
                "manifest": str(manifest),
                "scores": _scores(),
            },
        )

    normalized = normalize_mixed_score_payloads(
        sealed_manifests=sealed,
        result_files=result_files,
    )

    assert set(normalized) == set(roles)
    assert all(_sha(Path(sealed[role]["manifest"])) == sealed[role]["manifest_sha256"] for role in roles)


def test_refuses_missing_or_malformed_registered_cost_score(tmp_path: Path) -> None:
    roles = ("direct_m0", "joint_one_call", "joint_draft_revise", "select_then_fill")
    sealed = {}
    result_files = {}
    for role in roles:
        manifest, before = _manifest(tmp_path / role / f"{role}.run-manifest.json")
        sealed[role] = {"manifest": str(manifest), "manifest_sha256": before}
        result_files[role] = _write(
            tmp_path / "batch" / f"{role}.score.json",
            {
                "verified": True,
                "manifest": str(manifest),
                "scores": _scores(),
            },
        )

    payload = json.loads(result_files["joint_one_call"].read_text(encoding="utf-8"))
    payload["scores"].pop("cost")
    _write(result_files["joint_one_call"], payload)
    with pytest.raises(PostsealError, match="registered scorer set"):
        normalize_mixed_score_payloads(
            sealed_manifests=sealed,
            result_files=result_files,
        )

    payload["scores"]["cost"] = {"aggregate": {}, "per_sample": [{}]}
    _write(result_files["joint_one_call"], payload)
    with pytest.raises(PostsealError, match="cost score"):
        normalize_mixed_score_payloads(
            sealed_manifests=sealed,
            result_files=result_files,
        )


def test_mixed_batch_requires_exact_operations_and_whole_manifests(tmp_path: Path) -> None:
    manifests = {
        role: str(_manifest(tmp_path / role / f"{role}.run-manifest.json")[0])
        for role in ("direct_m0", "joint_one_call", "joint_draft_revise", "select_then_fill")
    }
    jobs = []
    for role, manifest in manifests.items():
        result = _write(tmp_path / f"{role}.score.json", {})
        jobs.append(
            {
                "job_id": role,
                "operation": "score" if role == "direct_m0" else "finalize",
                "manifest": manifest,
                "status": "succeeded",
                "returncode": 0,
                "result_file": str(result),
                "result_sha256": _sha(result),
            }
        )
    summary = {
        "schema": "saea-parallel-score-batch-v1",
        "operation": "per-job",
        "parallelism_boundary": "one-complete-verified-manifest-per-process",
        "aggregation_rule": "no dataset sharding and no averaging of shard-level official metrics",
        "requested_max_workers": 4,
        "effective_max_workers": 4,
        "job_count": 4,
        "succeeded": 4,
        "failed": 0,
        "jobs": jobs,
    }

    validated = validate_mixed_score_batch(summary, sealed_manifests={
        role: {"manifest": path} for role, path in manifests.items()
    }, base_dir=tmp_path)
    assert set(validated) == set(manifests)

    for job in jobs:
        job["operation"] = "score"
    validated = validate_mixed_score_batch(
        summary,
        sealed_manifests={
            role: {"manifest": path} for role, path in manifests.items()
        },
        base_dir=tmp_path,
    )
    assert set(validated) == set(manifests)

    jobs[0]["operation"] = "finalize"
    with pytest.raises(PostsealError, match="operation pattern"):
        validate_mixed_score_batch(
            summary,
            sealed_manifests={
                role: {"manifest": path} for role, path in manifests.items()
            },
            base_dir=tmp_path,
        )
    jobs[0]["operation"] = "score"
    jobs[1]["operation"] = "finalize"
    jobs[2]["operation"] = "score"
    with pytest.raises(PostsealError, match="operation pattern"):
        validate_mixed_score_batch(
            summary,
            sealed_manifests={
                role: {"manifest": path} for role, path in manifests.items()
            },
            base_dir=tmp_path,
        )

    summary["requested_max_workers"] = 5
    with pytest.raises(PostsealError, match="workers"):
        validate_mixed_score_batch(
            summary,
            sealed_manifests={role: {"manifest": path} for role, path in manifests.items()},
            base_dir=tmp_path,
        )


def test_source_has_no_contact_capable_imports_or_process_launches() -> None:
    repo = Path(__file__).resolve().parents[2]
    paths = (
        repo / "src/speech_aware_evidence_acquisition/analysis/a2t_select_fill_postseal.py",
        repo / "docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-select-fill-agentloop-104-v1/analyze.py",
    )
    for path in paths:
        source = path.read_text(encoding="utf-8")
        for prohibited in (
            "import subprocess",
            "import requests",
            "import urllib",
            "import socket",
            "run_score_batch(",
        ):
            assert prohibited not in source


def test_integrity_failure_precedes_gold_loading(tmp_path: Path) -> None:
    seal = _write(tmp_path / "seal.json", {"schema": "tampered"})
    batch = _write(tmp_path / "batch-summary.json", {})
    calls = 0

    def forbidden_gold_loader():
        nonlocal calls
        calls += 1
        pytest.fail("gold must remain unopened after an integrity failure")

    with pytest.raises(PostsealError, match="seal header"):
        analyze_sealed_inputs(
            seal_path=seal,
            batch_summary_path=batch,
            gold_loader=forbidden_gold_loader,
            population_mode=False,
            bootstrap_replicates=10,
        )
    assert calls == 0


def test_select_fill_efficiency_sums_distinct_select_and_fill_costs() -> None:
    value = sum_phase_efficiency(
        (
            {
                "prompt_tokens_total": 10,
                "calls_used": 104,
                "latency_seconds_total": 2.5,
            },
            {
                "prompt_tokens_total": 30,
                "calls_used": 104,
                "latency_seconds_total": 7.5,
            },
        )
    )

    assert value == {
        "prompt_tokens": 40,
        "contacts": 208,
        "raw_total_latency_seconds": 10.0,
    }
    assert "wall_time_seconds" not in value


def test_recovery_fill_lineage_binds_exact_select_response_hash_by_sample() -> None:
    assert PHASE_ORDER == (
        "JOINT_ONE_CALL",
        "SELECT",
        "JOINT_DRAFT_REVISE",
        "FILL",
    )
    assert LINEAGE_PHASES == {
        "joint_one_call": "JOINT_ONE_CALL",
        "joint_draft_revise": "JOINT_DRAFT_REVISE",
        "select_then_fill": "FILL",
    }
    select_hashes = {"tier:000001": "a" * 64, "tier:000002": "b" * 64}
    rows = [
        {
            "sample_id": sample_id,
            "predecessor_phase": "SELECT",
            "predecessor_response_text_sha256": digest,
            "source_request_body_sha256": "c" * 64,
            "source_response_text_sha256": "d" * 64,
        }
        for sample_id, digest in select_hashes.items()
    ]

    bind_select_fill_lineage(select_hashes, rows, ids=tuple(select_hashes))

    rows[1]["predecessor_response_text_sha256"] = "e" * 64
    with pytest.raises(PostsealError, match="does not bind SELECT"):
        bind_select_fill_lineage(select_hashes, rows, ids=tuple(select_hashes))


def test_k32_hash_covers_identity_names_scores_and_query_state() -> None:
    fields = {
        "sample_id": "tier:000001",
        "tool_names": ["tool_a", "tool_b"],
        "scores": [0.75, 0.25],
        "query_state_sha256": "a" * 64,
    }
    expected = hashlib.sha256(
        json.dumps(
            fields,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()

    assert candidate_set_sha256(**fields) == expected
    changed = dict(fields)
    changed["scores"] = [0.25, 0.75]
    assert candidate_set_sha256(**changed) != expected
