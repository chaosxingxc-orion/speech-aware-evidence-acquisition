"""Tests for the future sealed 104-row semantic AgentLoop analysis."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_semantic_agentloop_postseal import (
    ARM_ORDER,
    OBS_SEMANTIC_RETRIEVAL,
    AnalysisError,
    RetrievalDiagnosticSample,
    analyze_semantic_agentloop_flight,
    build_official_score_jobs,
)


REPO = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO / "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-semantic-agentloop-104-v1/analyze.py"
)


def _script_module():
    spec = importlib.util.spec_from_file_location(
        "semantic_agentloop_postseal_reader", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ids() -> tuple[str, ...]:
    return tuple(f"tier{(index % 8) + 1}:{index:06d}" for index in range(104))


def _manifest_descriptors(tmp_path: Path) -> dict[str, dict[str, object]]:
    result = {}
    for arm in ARM_ORDER:
        path = tmp_path / f"{arm}.run-manifest.json"
        path.write_text("{}\n", encoding="utf-8")
        result[arm] = {"manifest": str(path), "complete_rows": 104}
    return result


def _score_payload(
    manifest: Path, ids: tuple[str, ...], *, wins: set[str]
) -> dict[str, object]:
    per_sample = []
    for sample_id in ids:
        win = sample_id in wins
        per_sample.append(
            {
                "sample_id": sample_id,
                "tier": sample_id.split(":", 1)[0],
                "exact_match": float(win),
                "tool_accuracy": float(win),
                "slot_f1": float(win),
                "parsed": True,
            }
        )
    per_tier = {}
    for tier in sorted({sample_id.split(":", 1)[0] for sample_id in ids}):
        tier_rows = [row for row in per_sample if row["tier"] == tier]
        rate = sum(row["exact_match"] for row in tier_rows) / len(tier_rows)
        per_tier[tier] = {
            "samples": len(tier_rows),
            "exact_match": rate,
            "tool_accuracy": rate,
            "slot_f1": rate,
            "parse_failures": 0,
        }
    return {
        "verified": True,
        "manifest": str(manifest),
        "scores": {
            "a2t-toolcall": {
                "aggregate": {
                    "samples": 104,
                    "exact_match": len(wins) / 104,
                    "tool_accuracy": len(wins) / 104,
                    "slot_f1": len(wins) / 104,
                    "parse_failures": 0,
                    "per_tier": per_tier,
                },
                "per_sample": per_sample,
            }
        },
    }


def _diagnostics(ids: tuple[str, ...]) -> tuple[RetrievalDiagnosticSample, ...]:
    rows = []
    for sample_id in ids:
        rankings = {
            "transcript": ("tool-z", "tool-a"),
            "retrieval_query": ("tool-a", "tool-z"),
            "fused": ("tool-a", "tool-z"),
        }
        rows.append(
            RetrievalDiagnosticSample(
                sample_id=sample_id,
                tier=sample_id.split(":", 1)[0],
                retrieval_sealed=True,
                required_tool_ids=("tool-a",),
                ranked_tool_ids=rankings,
            )
        )
    return tuple(rows)


def test_builds_five_whole_manifest_score_jobs_and_never_scores_obs(
    tmp_path: Path,
) -> None:
    descriptors = _manifest_descriptors(tmp_path)

    jobs = build_official_score_jobs(descriptors)

    assert [job.job_id for job in jobs] == [
        "direct-m0",
        "transcript-top16-use",
        "model-query-top16-use",
        "rrf-fused-top16-use",
        "same-stratum-shuffled-fused-use",
    ]
    assert len(jobs) == 5
    assert all(job.manifest.name.endswith(".run-manifest.json") for job in jobs)


def test_reports_all_revised_paired_contrasts_and_unavailable_trace_ceilings(
    tmp_path: Path,
) -> None:
    ids = _ids()
    descriptors = _manifest_descriptors(tmp_path)
    direct = set(ids[:30])
    transcript = set(ids[:38])
    query = set(ids[:45])
    fused = set(ids[:50])
    shuffled = set(ids[:40])
    payloads = {
        "direct_m0": _score_payload(
            Path(descriptors["direct_m0"]["manifest"]), ids, wins=direct
        ),
        "transcript_top16_use": _score_payload(
            Path(descriptors["transcript_top16_use"]["manifest"]),
            ids,
            wins=transcript,
        ),
        "model_query_top16_use": _score_payload(
            Path(descriptors["model_query_top16_use"]["manifest"]), ids, wins=query
        ),
        "rrf_fused_top16_use": _score_payload(
            Path(descriptors["rrf_fused_top16_use"]["manifest"]), ids, wins=fused
        ),
        "same_stratum_shuffled_fused_use": _score_payload(
            Path(descriptors["same_stratum_shuffled_fused_use"]["manifest"]),
            ids,
            wins=shuffled,
        ),
    }

    report = analyze_semantic_agentloop_flight(
        manifests=descriptors,
        score_payloads=payloads,
        retrieval_samples=_diagnostics(ids),
        bootstrap_replicates=200,
        bootstrap_seed=17,
    )

    assert report["schema"] == "saea-a2t-semantic-agentloop-postseal-104-v1"
    assert report["arms"]["rrf_fused_top16_use"]["exact_match"] == pytest.approx(
        50 / 104
    )
    assert (
        report["arms"]["rrf_fused_top16_use"]["per_tier"]["tier1"]["samples"]
        == 13
    )
    gain = report["paired_contrasts"]["fused_m0"]
    assert gain["exact_match"]["point_estimate"] == pytest.approx(20 / 104)
    assert gain["exact_match"]["sign_test"]["wins"] == 20
    assert report["paired_contrasts"]["query_transcript"]["tool_accuracy"][
        "point_estimate"
    ] == pytest.approx(7 / 104)
    assert report["paired_contrasts"]["transcript_m0"]["exact_match"][
        "point_estimate"
    ] == pytest.approx(8 / 104)
    assert report["paired_contrasts"]["fused_transcript"]["slot_f1"][
        "point_estimate"
    ] == pytest.approx(12 / 104)
    assert report["paired_contrasts"]["fused_query"]["exact_match"][
        "point_estimate"
    ] == pytest.approx(5 / 104)
    causal = report["paired_contrasts"]["fused_shuffled"]
    assert causal["tool_accuracy"]["point_estimate"] == pytest.approx(10 / 104)
    retrieval = report["retrieval_upper_bounds"]
    assert retrieval["top_k"] == 16
    assert retrieval["conditions"]["transcript"]["top_k_tool_coverage"] == 1.0
    assert retrieval["conditions"]["fused"]["full_ordered_call_skeleton_coverage"] == {
        "status": "unavailable",
        "reason": "no sealed ordered-call skeleton trace artifact was supplied",
    }
    assert retrieval["conditions"]["retrieval_query"][
        "proposal_content_action_set_consumption_ceiling"
    ]["status"] == "unavailable"
    assert report["promotion_gates"]["future_tfrl_over_0_90_not_required"] is True
    assert "network jitter" in report["conclusion_exclusions"]


def test_derives_per_tier_parse_rate_from_official_per_sample_rows(
    tmp_path: Path,
) -> None:
    ids = _ids()
    descriptors = _manifest_descriptors(tmp_path)
    payloads = {
        arm: _score_payload(Path(descriptors[arm]["manifest"]), ids, wins=set())
        for arm in (
            "direct_m0",
            "transcript_top16_use",
            "model_query_top16_use",
            "rrf_fused_top16_use",
            "same_stratum_shuffled_fused_use",
        )
    }
    for payload in payloads.values():
        official = payload["scores"]["a2t-toolcall"]
        first = official["per_sample"][0]
        first["parsed"] = False
        official["aggregate"]["parse_failures"] = 1
        for tier_score in official["aggregate"]["per_tier"].values():
            del tier_score["parse_failures"]

    report = analyze_semantic_agentloop_flight(
        manifests=descriptors,
        score_payloads=payloads,
        retrieval_samples=_diagnostics(ids),
        bootstrap_replicates=10,
        bootstrap_seed=5,
    )

    assert report["arms"]["direct_m0"]["per_tier"]["tier1"][
        "parse_rate"
    ] == pytest.approx(12 / 13)
    assert report["arms"]["direct_m0"]["per_tier"]["tier2"][
        "parse_rate"
    ] == 1.0


def test_refuses_incomplete_or_mismatched_future_flight_inputs(tmp_path: Path) -> None:
    ids = _ids()
    descriptors = _manifest_descriptors(tmp_path)
    descriptors[OBS_SEMANTIC_RETRIEVAL]["complete_rows"] = 103
    payload = _score_payload(
        Path(descriptors["direct_m0"]["manifest"]), ids, wins=set()
    )

    with pytest.raises(AnalysisError, match="104"):
        analyze_semantic_agentloop_flight(
            manifests=descriptors,
            score_payloads={"direct_m0": payload},
            retrieval_samples=_diagnostics(ids),
            bootstrap_replicates=10,
        )


def test_is_pure_postseal_analysis_without_runtime_or_external_contacts() -> None:
    module_path = Path(__file__).resolve().parents[2] / (
        "src/speech_aware_evidence_acquisition/analysis/a2t_semantic_agentloop_postseal.py"
    )
    source = module_path.read_text(encoding="utf-8")

    for prohibited in (
        "subprocess",
        "requests",
        "urllib",
        "socket",
        "pyvw",
        "tokenizer",
    ):
        assert prohibited not in source


def test_no_contact_reader_accepts_only_the_explicit_future_input_shape(
    tmp_path: Path,
) -> None:
    ids = _ids()
    descriptors = _manifest_descriptors(tmp_path)
    empty = set()
    payloads = {
        arm: _score_payload(Path(descriptors[arm]["manifest"]), ids, wins=empty)
        for arm in (
            "direct_m0",
            "transcript_top16_use",
            "model_query_top16_use",
            "rrf_fused_top16_use",
            "same_stratum_shuffled_fused_use",
        )
    }
    module = _script_module()

    report = module.build_report(
        {
            "manifests": descriptors,
            "score_payloads": payloads,
            "retrieval_samples": [
                {
                    key: value
                    for key, value in sample.__dict__.items()
                    if value is not None
                }
                for sample in _diagnostics(ids)
            ],
        },
        bootstrap_replicates=10,
        bootstrap_seed=3,
    )

    assert report["row_count"] == 104
