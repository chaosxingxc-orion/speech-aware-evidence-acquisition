"""Read the sealed Audio2Tool self-consistency discovery flight.

The reader is model-free. It verifies the two complete manifests and their
official score artifacts, reconstructs per-sample scores through the frozen
official primitives, runs the preregistered grouped cross-fit policy screen,
and emits one self-hashed result document. It never opens another split.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[5]

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal study src directory")

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    training_free_a2t_self_consistency as selfcon,
)
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    STATUS_COMPLETED,
    require_clean_study_repo,
    verify_bundle,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_expected_calls,
    load_tool_registry,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (  # noqa: E402
    ItemScore,
    ToolCall,
    aggregate,
    parse_tool_calls_text,
    score_item,
)

RUN_ID = "SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1"
SPLIT_IDENTITY_SHA256 = (
    "f5a030189cf80dcbc52899e2fa5f819bac03874f2ad3f9645fdc60c432a9bf3a"
)
M0_RELPATH = Path(
    "runs/SAEA-A2T-G1/attempt-20260825T100735Z-a2tg1m0/arm1-m0-outputs.jsonl"
)
OBSERVATION_MANIFEST_RELPATH = Path(
    "runs/SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1/flight-20260901T172514Z/"
    "reobserve-direct/SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1.run-manifest.json"
)
SUPPLY_MANIFEST_RELPATH = Path(
    "runs/SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1/flight-20260901T174317Z/"
    "supply-union-stripped/SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1.run-manifest.json"
)
OBSERVATION_SCORE_RELPATH = Path(
    "runs/SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1/flight-20260901T174317Z/"
    "parallel-finalize/reobserve-direct-recovered.score.json"
)
BATCH_SUMMARY_RELPATH = Path(
    "runs/SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1/flight-20260901T174317Z/"
    "parallel-finalize/batch-summary.json"
)
SUBSET_RECEIPT = REPO / "docs/receipts/a2t/A2T-G1-104.json"
FULL_RECEIPT = REPO / "docs/receipts/probe-samples/r1-audio2tool-sample.json"

EXPECTED_HASHES = {
    "m0": "dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467",
    "observation_manifest": "73c901639916a28d67c2bc8a996d921371744f438c73be178c7fbe995fc1a238",
    "observation_outputs": "888626b97c0525ce16abd91e6d3da1d5df50955b5a7bf6eb6cda8ba8657fb0f9",
    "observation_score": "c82d04d110596c18319d3f9d5e364705193a6bd5bae83a6995981fd56e0e88ac",
    "supply_manifest_scored": "e5270dea9b9fa1fd0b968518598a24f65761971093e2ed4d4d961ff4641f7575",
    "supply_outputs": "14cf59eaf053dd344b4b6b874f1e182de6ea11599c7e2a4a0a620f715690d93f",
    "supply_scores": "bb6e154c5da210f363ed7ea98c1c42b04087d5291bbf3d0a88516e7cf158fd07",
    "parallel_batch": "ef8b3b398608003de13a91521adda855ac5ebebe635fd2018ce1d5a0bc97db12",
    "subset_receipt": "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db",
    "full_query_group_receipt": "d99570a797744f7dc3db53bdb898611836ae2682a02e726b974d05734c6cbb2d",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> None:
    actual = _sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} SHA-256 drift: {actual} != {expected}")


def _read_json(path: Path) -> Mapping[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise RuntimeError(f"JSON document is not an object: {path}")
    return value


def _response_map(path: Path, *, field: str) -> dict[str, str]:
    indexed: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        row = json.loads(line)
        if not isinstance(row, Mapping):
            raise RuntimeError(f"{path} line {line_number} is not an object")
        sample_id = row.get("sample_id")
        response = row.get(field)
        if not isinstance(sample_id, str) or not isinstance(response, str):
            raise RuntimeError(f"{path} line {line_number} lacks response identity")
        if sample_id in indexed:
            raise RuntimeError(f"{path} has duplicate sample_id {sample_id!r}")
        indexed[sample_id] = response
    return indexed


def _query_groups() -> tuple[dict[str, str], dict[str, str]]:
    _require_hash(SUBSET_RECEIPT, EXPECTED_HASHES["subset_receipt"], "subset receipt")
    _require_hash(
        FULL_RECEIPT,
        EXPECTED_HASHES["full_query_group_receipt"],
        "full query-group receipt",
    )
    subset = _read_json(SUBSET_RECEIPT)
    if (
        subset.get("run_identity_hash") != SPLIT_IDENTITY_SHA256
        or subset.get("count") != 104
    ):
        raise RuntimeError("subset receipt identity drift")
    full = _read_json(FULL_RECEIPT)
    full_items = full.get("items")
    subset_items = subset.get("items")
    if not isinstance(full_items, list) or not isinstance(subset_items, list):
        raise RuntimeError("Audio2Tool receipt lacks items")
    groups: dict[str, str] = {}
    for item in full_items:
        if not isinstance(item, Mapping):
            raise RuntimeError("full receipt contains a non-object item")
        sample_id = f"{item['tier']}:{int(item['id']):06d}"
        groups[sample_id] = str(item["query_idx"])
    subset_groups: dict[str, str] = {}
    tiers: dict[str, str] = {}
    for item in subset_items:
        if not isinstance(item, Mapping):
            raise RuntimeError("subset receipt contains a non-object item")
        sample_id = str(item["sample_id"])
        if sample_id not in groups:
            raise RuntimeError(f"query group missing for {sample_id}")
        subset_groups[sample_id] = groups[sample_id]
        tiers[sample_id] = str(item["tier"])
    return subset_groups, tiers


def _metric_payload(scores: Sequence[ItemScore]) -> dict[str, object]:
    value = aggregate(scores)
    return {
        "samples": value.n_items,
        "exact_match_count": int(round(value.exact_match * value.n_items)),
        "exact_match": value.exact_match,
        "tool_accuracy_count": int(round(value.tool_accuracy * value.n_items)),
        "tool_accuracy": value.tool_accuracy,
        "slot_true_positives": value.slot_true_positives,
        "slot_expected_total": value.slot_expected_total,
        "slot_predicted_total": value.slot_predicted_total,
        "slot_f1": value.slot_f1,
    }


def _score_arm(
    responses: Mapping[str, str], expected_by_id: Mapping[str, Sequence[ToolCall]]
) -> tuple[tuple[ItemScore, ...], int]:
    scores: list[ItemScore] = []
    parse_failures = 0
    for sample_id in sorted(responses):
        calls, parsed = parse_tool_calls_text(responses[sample_id])
        parse_failures += not parsed
        scores.append(score_item(expected_by_id[sample_id], calls))
    return tuple(scores), parse_failures


def _assert_official_aggregate(
    reconstructed: Mapping[str, object], official: Mapping[str, object], *, label: str
) -> None:
    pairs = {
        "samples": "samples",
        "exact_match": "exact_match",
        "tool_accuracy": "tool_accuracy",
        "slot_true_positives": "slot_true_positives",
        "slot_expected_total": "slot_expected_total",
        "slot_predicted_total": "slot_predicted_total",
        "slot_f1": "slot_f1",
    }
    for local, remote in pairs.items():
        left = reconstructed[local]
        right = official.get(remote)
        if isinstance(left, float) and isinstance(right, (int, float)):
            if abs(left - float(right)) > 1e-12:
                raise RuntimeError(f"{label} official {remote} disagrees")
        elif left != right:
            raise RuntimeError(f"{label} official {remote} disagrees")


def _state_return_cells(
    outcomes: Sequence[selfcon.SelfConsistencyOutcome], *, candidate_id: str
) -> dict[str, dict[str, int]]:
    cells: dict[str, dict[str, int]] = {}
    for item in outcomes:
        label = json.dumps(item.state.key(candidate_id), separators=(",", ":"))
        cell = cells.setdefault(
            label,
            {"n": 0, "available": 0, "saves": 0, "harms": 0, "neutral": 0},
        )
        cell["n"] += 1
        if not item.supply_available:
            continue
        cell["available"] += 1
        if item.delta > 0:
            cell["saves"] += 1
        elif item.delta < 0:
            cell["harms"] += 1
        else:
            cell["neutral"] += 1
    return dict(sorted(cells.items()))


def run_read(root: Path) -> dict[str, object]:
    study_commit = require_clean_study_repo(REPO)
    offline = arm_offline_guard()

    m0_path = root / M0_RELPATH
    observation_manifest_path = root / OBSERVATION_MANIFEST_RELPATH
    supply_manifest_path = root / SUPPLY_MANIFEST_RELPATH
    observation_score_path = root / OBSERVATION_SCORE_RELPATH
    batch_summary_path = root / BATCH_SUMMARY_RELPATH
    for label, path in (
        ("m0", m0_path),
        ("observation_manifest", observation_manifest_path),
        ("observation_score", observation_score_path),
        ("supply_manifest_scored", supply_manifest_path),
        ("parallel_batch", batch_summary_path),
    ):
        _require_hash(path, EXPECTED_HASHES[label], label)

    observation_bundle = verify_bundle(observation_manifest_path)
    supply_bundle = verify_bundle(supply_manifest_path)
    for label, bundle in (
        ("observation", observation_bundle),
        ("supply", supply_bundle),
    ):
        if (
            bundle.attempt_state != "ABORTED"
            or bundle.manifest.get("status") != STATUS_COMPLETED
            or len(bundle.outputs_rows) != 104
            or bundle.outputs_path is None
        ):
            raise RuntimeError(f"{label} bundle is not the complete scored recovery source")
    if supply_bundle.manifest.get("scores") is None:
        raise RuntimeError("supply manifest lacks the official attached score artifact")

    _require_hash(
        observation_bundle.outputs_path,
        EXPECTED_HASHES["observation_outputs"],
        "observation outputs",
    )
    _require_hash(
        supply_bundle.outputs_path,
        EXPECTED_HASHES["supply_outputs"],
        "supply outputs",
    )
    supply_scores_path = Path(str(supply_bundle.manifest["scores"]["path"]))
    _require_hash(supply_scores_path, EXPECTED_HASHES["supply_scores"], "supply scores")

    m0 = _response_map(m0_path, field="final_response_text")
    observation = _response_map(observation_bundle.outputs_path, field="text")
    supply = _response_map(supply_bundle.outputs_path, field="text")
    query_groups, tiers = _query_groups()
    if set(m0) != set(query_groups):
        raise RuntimeError("frozen M0 ids do not equal the registered cohort")

    lock = load_lock(umbrella_lock_path(REPO))
    registry = load_tool_registry(lock, root)
    expected_by_id = load_expected_calls(lock, root, repo_root=REPO)
    outcomes = selfcon.build_scored_outcomes(
        m0_response_by_id=m0,
        observation_response_by_id=observation,
        supply_response_by_id=supply,
        query_group_by_id=query_groups,
        registry_rows=registry,
        expected_by_id=expected_by_id,
    )
    observation_scores, observation_parse_failures = _score_arm(
        observation, expected_by_id
    )
    m0_scores, m0_parse_failures = _score_arm(m0, expected_by_id)
    supply_scores = tuple(item.supply_score for item in outcomes)
    supply_parse_failures = sum(
        not parse_tool_calls_text(supply[item.sample_id])[1] for item in outcomes
    )
    metrics = {
        "M0": {**_metric_payload(m0_scores), "parse_failures": m0_parse_failures},
        "REOBSERVE_DIRECT": {
            **_metric_payload(observation_scores),
            "parse_failures": observation_parse_failures,
        },
        "SUPPLY_UNION_STRIPPED": {
            **_metric_payload(supply_scores),
            "parse_failures": supply_parse_failures,
        },
    }

    observation_score = _read_json(observation_score_path)
    observation_official = observation_score["scores"]["a2t-toolcall"]
    supply_score_document = _read_json(supply_scores_path)
    supply_official = supply_score_document["a2t-toolcall"]["aggregate"]
    if not isinstance(observation_official, Mapping) or not isinstance(
        supply_official, Mapping
    ):
        raise RuntimeError("official score artifact shape drift")
    _assert_official_aggregate(
        metrics["REOBSERVE_DIRECT"], observation_official, label="observation"
    )
    _assert_official_aggregate(
        metrics["SUPPLY_UNION_STRIPPED"], supply_official, label="supply"
    )

    screen = selfcon.screen_candidates(outcomes)
    policy = selfcon.build_policy_artifact(
        outcomes,
        screen,
        source_hashes={
            "m0": EXPECTED_HASHES["m0"],
            "repeat": EXPECTED_HASHES["observation_outputs"],
            "supply": EXPECTED_HASHES["supply_outputs"],
        },
        offline_attempts=offline.count,
    )

    observation_delta = Counter(
        int(observation_scores[index].exact_match - item.stop_score.exact_match)
        for index, item in enumerate(outcomes)
    )
    eligible_supply_delta = Counter(
        item.delta for item in outcomes if item.supply_available
    )
    tier_delta: dict[str, Counter[int]] = defaultdict(Counter)
    for item in outcomes:
        tier_delta[tiers[item.sample_id]][item.delta] += 1
    batch = _read_json(batch_summary_path)
    jobs = batch.get("jobs")
    if (
        batch.get("parallelism_boundary")
        != "one-complete-verified-manifest-per-process"
        or not isinstance(jobs, list)
        or len(jobs) != 2
    ):
        raise RuntimeError("parallel scorer boundary drift")
    job_seconds = sum(float(job["elapsed_seconds"]) for job in jobs)
    wall_seconds = float(batch["elapsed_seconds"])

    result = selfcon.with_self_hash(
        {
            "schema": "saea-a2t-self-consistency-104-result-v1",
            "experiment_id": RUN_ID,
            "study_commit": study_commit,
            "claim_status": "exposed-cohort secondary discovery only",
            "source_hashes": dict(sorted(EXPECTED_HASHES.items())),
            "contact_accounting": {
                "observation_calls": 104,
                "supply_calls": 104,
                "total_calls": 208,
                "registered_ceiling": 213,
                "audio_seconds": 1174.034,
                "registered_audio_seconds_ceiling": 1200.0,
                "paid_api_spend": 0,
            },
            "official_aggregate_fidelity": {
                "observation": True,
                "supply": True,
            },
            "arm_metrics": metrics,
            "information_gain": {
                "m0_observation_byte_identical": sum(
                    m0[sample_id] == observation[sample_id] for sample_id in m0
                ),
                "m0_observation_changed": sum(
                    m0[sample_id] != observation[sample_id] for sample_id in m0
                ),
                "observation_exact_delta_counts": {
                    str(key): value for key, value in sorted(observation_delta.items())
                },
                "supply_available": sum(item.supply_available for item in outcomes),
                "supply_unavailable": sum(
                    not item.supply_available for item in outcomes
                ),
                "eligible_supply_exact_delta_counts": {
                    str(key): value
                    for key, value in sorted(eligible_supply_delta.items())
                },
                "coarse_return_cells": _state_return_cells(
                    outcomes, candidate_id=selfcon.COARSE_CANDIDATE
                ),
                "detailed_return_cells": _state_return_cells(
                    outcomes, candidate_id=selfcon.HIERARCHICAL_CANDIDATE
                ),
                "tier_supply_delta_counts": {
                    tier: {str(key): value for key, value in sorted(counts.items())}
                    for tier, counts in sorted(tier_delta.items())
                },
            },
            "policy_artifact": policy,
            "parallel_scoring": {
                "wall_seconds": wall_seconds,
                "sum_job_seconds": job_seconds,
                "effective_speedup": job_seconds / wall_seconds,
                "workers": batch["effective_max_workers"],
                "whole_manifest_jobs": 2,
                "dataset_shards": 0,
                "observation_job": jobs[0],
                "supply_job": jobs[1],
            },
            "finalization_incident": {
                "scientific_scores_complete": True,
                "observation_attempt_state": observation_bundle.attempt_state,
                "supply_attempt_state": supply_bundle.attempt_state,
                "supply_score_attached_before_tracking_failure": True,
                "failure_class": "missing human ledger cells after scoring",
                "prediction_reflight": False,
            },
            "promotion_passed": screen.promotion_passed,
            "selected_candidate": screen.selected_candidate,
            "decision": (
                "freeze the selected controller for a separate support run"
                if screen.promotion_passed
                else "close direct self-consistency as this targeting signal; do not scale"
            ),
            "offline_guard": {
                "outbound_connection_attempts": offline.count,
                "targets": [],
            },
        }
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = run_read(data_root())
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
