"""Run the preregistered Audio2Tool schema-risk memory read exactly once.

This entry point is model-free.  It binds the completed self-consistency
result and all sealed response/score sources, reconstructs the predecessor
signed-return surface with the frozen official primitives, proves predecessor
policy fidelity, then exposes the newly registered schema-risk state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[5]

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal study src directory")

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    training_free_a2t_schema_risk_memory as risk,
)
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

RUN_ID = risk.EXPERIMENT_ID
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
RAW_RESULT_RELPATH = Path(
    "runs/SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1/analysis/"
    "self-consistency-result.json"
)
SUBSET_RECEIPT = REPO / "docs/receipts/a2t/A2T-G1-104.json"
FULL_RECEIPT = REPO / "docs/receipts/probe-samples/r1-audio2tool-sample.json"

EXPECTED_HASHES = {
    "raw_result": "8527282e110cd11a9d87f0d65d06d55f266e0a27a9bb95d7f7eff3b103266d39",
    "m0": "dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467",
    "observation_manifest": "73c901639916a28d67c2bc8a996d921371744f438c73be178c7fbe995fc1a238",
    "observation_outputs": "888626b97c0525ce16abd91e6d3da1d5df50955b5a7bf6eb6cda8ba8657fb0f9",
    "supply_manifest_scored": "e5270dea9b9fa1fd0b968518598a24f65761971093e2ed4d4d961ff4641f7575",
    "supply_outputs": "14cf59eaf053dd344b4b6b874f1e182de6ea11599c7e2a4a0a620f715690d93f",
    "supply_scores": "bb6e154c5da210f363ed7ea98c1c42b04087d5291bbf3d0a88516e7cf158fd07",
    "subset_receipt": "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db",
    "full_query_group_receipt": "d99570a797744f7dc3db53bdb898611836ae2682a02e726b974d05734c6cbb2d",
}
EXPECTED_PREDECESSOR = {
    "result_self_sha256": "ee7368f2ba0587fa959438a965bea3c604261aad0924dd303837f3f853668b2b",
    "policy_self_sha256": "9e16405535da114f1ccf42d457e7f7ec20099b2f6df5b76d264231e00365c132",
    "state_identity_sha256": "890538474a7fcbc0ab981f54e2168358096be66145f306c9e6f7ba063808b246",
    "decision_identity_sha256": "07afc9c6e51b8b61f5ce8c1cf1c705a2e727e7a82c1f9a556247f252f386c31c",
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


def _query_groups() -> dict[str, str]:
    _require_hash(SUBSET_RECEIPT, EXPECTED_HASHES["subset_receipt"], "subset receipt")
    _require_hash(
        FULL_RECEIPT,
        EXPECTED_HASHES["full_query_group_receipt"],
        "full query-group receipt",
    )
    subset = _read_json(SUBSET_RECEIPT)
    full = _read_json(FULL_RECEIPT)
    if subset.get("run_identity_hash") != SPLIT_IDENTITY_SHA256 or subset.get("count") != 104:
        raise RuntimeError("subset receipt identity drift")
    full_items = full.get("items")
    subset_items = subset.get("items")
    if not isinstance(full_items, list) or not isinstance(subset_items, list):
        raise RuntimeError("Audio2Tool receipt lacks items")
    all_groups: dict[str, str] = {}
    for item in full_items:
        if not isinstance(item, Mapping):
            raise RuntimeError("full receipt contains a non-object item")
        sample_id = f"{item['tier']}:{int(item['id']):06d}"
        all_groups[sample_id] = str(item["query_idx"])
    groups: dict[str, str] = {}
    for item in subset_items:
        if not isinstance(item, Mapping):
            raise RuntimeError("subset receipt contains a non-object item")
        sample_id = str(item["sample_id"])
        if sample_id not in all_groups:
            raise RuntimeError(f"query group missing for {sample_id}")
        groups[sample_id] = all_groups[sample_id]
    return groups


def _assert_predecessor(raw_result: Mapping[str, object]) -> None:
    selfcon.assert_self_hash(raw_result)
    if raw_result.get("self_sha256") != EXPECTED_PREDECESSOR["result_self_sha256"]:
        raise RuntimeError("predecessor result self identity drift")
    if raw_result.get("promotion_passed") is not False:
        raise RuntimeError("predecessor promotion verdict drift")
    policy = raw_result.get("policy_artifact")
    if not isinstance(policy, Mapping):
        raise RuntimeError("predecessor result lacks policy artifact")
    selfcon.assert_self_hash(policy)
    if (
        policy.get("self_sha256") != EXPECTED_PREDECESSOR["policy_self_sha256"]
        or policy.get("state_identity_sha256")
        != EXPECTED_PREDECESSOR["state_identity_sha256"]
    ):
        raise RuntimeError("predecessor policy identity drift")
    reports = policy.get("candidate_reports")
    if not isinstance(reports, Mapping) or set(reports) != set(selfcon.CANDIDATE_IDS):
        raise RuntimeError("predecessor candidate surface drift")
    for report in reports.values():
        if not isinstance(report, Mapping):
            raise RuntimeError("predecessor candidate report shape drift")
        if report.get("decision_identity_sha256") != EXPECTED_PREDECESSOR[
            "decision_identity_sha256"
        ]:
            raise RuntimeError("predecessor decision identity drift")


def _fold_identity(outcomes: Sequence[risk.SchemaRiskOutcome]) -> str:
    folds = selfcon.assign_folds(outcomes, seed=selfcon.FOLD_SEED, n_folds=5)  # type: ignore[arg-type]
    lines = [
        f"{fold_index}\t{item.sample_id}\t{item.group_id}"
        for fold_index, fold in enumerate(folds)
        for item in fold
    ]
    return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()


def _registry_audit(registry: Sequence[Mapping[str, str]]) -> dict[str, object]:
    signatures = [risk.parse_pseudo_signature(row.get("signature", "")) for row in registry]
    constraints = [
        spec
        for row in registry
        for spec in risk.parse_argument_constraints(
            row.get("argument_constraints", "")
        ).values()
    ]
    return {
        "rows": len(registry),
        "parsed_signatures": sum(value is not None for value in signatures),
        "unresolved_signatures": sum(value is None for value in signatures),
        "declared_parameters": sum(
            len(value.parameters) for value in signatures if value is not None
        ),
        "optional_parameters": sum(
            item.optional
            for value in signatures
            if value is not None
            for item in value.parameters
        ),
        "constraint_clauses": len(constraints),
        "enum_constraints": sum(item.kind == "enum" for item in constraints),
        "numeric_range_constraints": sum(
            item.kind == "numeric-range" for item in constraints
        ),
        "uncheckable_constraints": sum(
            item.kind == "uncheckable" for item in constraints
        ),
    }


def run_read(root: Path) -> dict[str, object]:
    study_commit = require_clean_study_repo(REPO)
    offline = arm_offline_guard()

    raw_result_path = root / RAW_RESULT_RELPATH
    m0_path = root / M0_RELPATH
    observation_manifest_path = root / OBSERVATION_MANIFEST_RELPATH
    supply_manifest_path = root / SUPPLY_MANIFEST_RELPATH
    for label, path in (
        ("raw_result", raw_result_path),
        ("m0", m0_path),
        ("observation_manifest", observation_manifest_path),
        ("supply_manifest_scored", supply_manifest_path),
    ):
        _require_hash(path, EXPECTED_HASHES[label], label)
    raw_result = _read_json(raw_result_path)
    _assert_predecessor(raw_result)

    observation_bundle = verify_bundle(observation_manifest_path)
    supply_bundle = verify_bundle(supply_manifest_path)
    for label, bundle in (("observation", observation_bundle), ("supply", supply_bundle)):
        if (
            bundle.attempt_state != "ABORTED"
            or bundle.manifest.get("status") != STATUS_COMPLETED
            or len(bundle.outputs_rows) != 104
            or bundle.outputs_path is None
        ):
            raise RuntimeError(f"{label} bundle is not the complete scored recovery source")
    if supply_bundle.manifest.get("scores") is None:
        raise RuntimeError("supply manifest lacks its attached official score")
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
    query_groups = _query_groups()
    if set(m0) != set(query_groups):
        raise RuntimeError("M0 ids do not equal the registered cohort")

    lock = load_lock(umbrella_lock_path(REPO))
    registry = load_tool_registry(lock, root)
    expected = load_expected_calls(lock, root, repo_root=REPO)
    predecessor_outcomes = selfcon.build_scored_outcomes(
        m0_response_by_id=m0,
        observation_response_by_id=observation,
        supply_response_by_id=supply,
        query_group_by_id=query_groups,
        registry_rows=registry,
        expected_by_id=expected,
    )
    if (
        len(predecessor_outcomes) != 104
        or sum(item.supply_available for item in predecessor_outcomes) != 92
        or sum(item.supply_available and item.delta > 0 for item in predecessor_outcomes) != 4
        or sum(item.supply_available and item.delta < 0 for item in predecessor_outcomes) != 10
    ):
        raise RuntimeError("predecessor signed-return surface drift")
    predecessor_screen = selfcon.screen_candidates(predecessor_outcomes)
    predecessor_policy = selfcon.build_policy_artifact(
        predecessor_outcomes,
        predecessor_screen,
        source_hashes={
            "m0": EXPECTED_HASHES["m0"],
            "repeat": EXPECTED_HASHES["observation_outputs"],
            "supply": EXPECTED_HASHES["supply_outputs"],
        },
        offline_attempts=offline.count,
    )
    if (
        predecessor_policy["state_identity_sha256"]
        != EXPECTED_PREDECESSOR["state_identity_sha256"]
        or any(
            report["decision_identity_sha256"]
            != EXPECTED_PREDECESSOR["decision_identity_sha256"]
            for report in predecessor_policy["candidate_reports"].values()
        )
    ):
        raise RuntimeError("reconstructed predecessor policy drift")

    outcomes = risk.augment_outcomes(
        predecessor_outcomes, m0, observation, registry
    )
    screen = risk.screen_candidates(outcomes)
    policy = risk.build_policy_artifact(
        outcomes,
        screen,
        source_hashes={
            "m0": EXPECTED_HASHES["m0"],
            "repeat": EXPECTED_HASHES["observation_outputs"],
            "supply": EXPECTED_HASHES["supply_outputs"],
        },
        offline_attempts=offline.count,
    )
    m0_risk = Counter(item.state.m0.risk_class for item in outcomes)
    observation_risk = Counter(item.state.observation.risk_class for item in outcomes)
    relations = Counter(item.state.risk_relation for item in outcomes)
    violation_pairs = Counter(
        (item.state.m0.violation_count, item.state.observation.violation_count)
        for item in outcomes
    )
    return risk.with_self_hash(
        {
            "schema": "saea-a2t-training-free-schema-risk-memory-result-v1",
            "experiment_id": RUN_ID,
            "study_commit": study_commit,
            "execution_profile": "model-free-check",
            "claim_status": "exposed-cohort retrospective feasibility only",
            "source_hashes": dict(sorted(EXPECTED_HASHES.items())),
            "predecessor_fidelity": {
                "result_self_sha256": raw_result["self_sha256"],
                "policy_self_sha256": predecessor_policy["self_sha256"],
                "state_identity_sha256": predecessor_policy["state_identity_sha256"],
                "decision_identity_sha256": EXPECTED_PREDECESSOR[
                    "decision_identity_sha256"
                ],
                "samples": 104,
                "supply_available": 92,
                "always_supply_saves": 4,
                "always_supply_harms": 10,
                "fold_identity_sha256": _fold_identity(outcomes),
            },
            "registry_parser_audit": _registry_audit(registry),
            "state_summary": {
                "m0_risk_class_counts": dict(sorted(m0_risk.items())),
                "observation_risk_class_counts": dict(sorted(observation_risk.items())),
                "risk_relation_counts": dict(sorted(relations.items())),
                "violation_pair_counts": {
                    json.dumps(key, separators=(",", ":")): value
                    for key, value in sorted(violation_pairs.items())
                },
                "coarse_return_cells": risk.state_return_cells(
                    outcomes, candidate_id=risk.COARSE_CANDIDATE
                ),
                "detailed_return_cells": risk.state_return_cells(
                    outcomes, candidate_id=risk.DETAILED_CANDIDATE
                ),
            },
            "policy_artifact": policy,
            "promotion_passed": screen.promotion_passed,
            "selected_candidate": screen.selected_candidate,
            "decision": (
                "freeze one controller proposal for a separately preregistered fresh support flight"
                if screen.promotion_passed
                else "close schema-risk targeting for the current supply action"
            ),
            "contacts": {
                "frozen_core": 0,
                "embedding_tool": 0,
                "tokenizer": 0,
                "http_or_socket": 0,
                "audio_seconds": 0,
                "gpu_hours": 0.0,
            },
            "offline_guard": {
                "outbound_connection_attempts": offline.count,
                "targets": [],
            },
        }
    )


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
