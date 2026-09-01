"""Committed zero-contact runner for registry-semantic reward memory v2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Mapping

from ..data.lock import load_lock
from . import training_free_a2t_registry_semantic_memory as v2
from . import training_free_a2t_supply_memory as v1

REGISTRATION_PATHS: tuple[str, ...] = (
    "configs/experiment/a2t-training-free-registry-semantic-memory-v2.json",
    "docs/readiness/2026-09-01-a2t-training-free-registry-semantic-memory-v2-preregistration.md",
    "docs/exposure-ledger.md",
    "src/speech_aware_evidence_acquisition/analysis/training_free_a2t_registry_semantic_memory.py",
    "src/speech_aware_evidence_acquisition/analysis/training_free_a2t_registry_semantic_memory_cli.py",
    "tests/unit/test_training_free_a2t_registry_semantic_memory.py",
)


def assert_registration_committed(repo_root: Path) -> None:
    for relpath in REGISTRATION_PATHS:
        v1._assert_file_committed(  # noqa: SLF001 - same repository guard
            repo_root=repo_root, relpath=relpath
        )
    ledger = (repo_root / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    if ledger.count(f"Row `{v2.EXPERIMENT_ID}`") != 1:
        raise v1.SupplyMemoryError(
            "committed exposure ledger lacks exactly one semantic-memory registration"
        )


def _load_v1_artifact(path: Path) -> Mapping[str, object]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise v1.SupplyMemoryError(f"cannot read v1 artifact {path}: {error}") from error
    if not isinstance(document, Mapping):
        raise v1.SupplyMemoryError("v1 artifact must be a JSON object")
    v1.assert_self_hash(document)
    return document


def _a0_direct_responses(a0_attempt: Path, repo_root: Path) -> dict[str, str]:
    from . import a2t_read

    rows = v1._validated_a0_rows(  # noqa: SLF001 - same efficient structural gate
        a2t_read, attempt_dir=a0_attempt, repo_root=repo_root
    )
    return {str(row.sample_id): str(row.response_text) for row in rows}


def _load_registry_rows(lock: Mapping[str, object], data_root: Path):
    from ..data.audio2tool import load_tool_registry

    return load_tool_registry(lock, data_root)


def _arm_offline_guard():
    from .dev100_reviewer_audit import arm_offline_guard

    return arm_offline_guard()


def run_registered_replay(
    *,
    repo_root: Path,
    data_root: Path,
    lock: Mapping[str, object],
    a0_attempt: Path,
    headroom_supply_attempt: Path,
    population_supply_attempt: Path,
    headroom_path: Path,
    stage2_arm_plan_path: Path,
    receipt_path: Path,
    v1_artifact_path: Path,
) -> dict[str, object]:
    assert_registration_committed(repo_root)
    attempts = _arm_offline_guard()
    surface = v1.load_registered_surface(
        repo_root=repo_root,
        data_root=data_root,
        lock=lock,
        a0_attempt=a0_attempt,
        headroom_supply_attempt=headroom_supply_attempt,
        population_supply_attempt=population_supply_attempt,
        headroom_path=headroom_path,
        stage2_arm_plan_path=stage2_arm_plan_path,
        receipt_path=receipt_path,
    )
    predecessor = _load_v1_artifact(v1_artifact_path)
    v2.assert_v1_surface_identity(surface, predecessor)
    direct_responses = _a0_direct_responses(a0_attempt, repo_root)
    registry_rows = _load_registry_rows(lock, data_root)
    outcomes = v2.augment_outcomes(surface.outcomes, direct_responses, registry_rows)
    screen = v2.screen_candidates(outcomes)
    source_hashes = {
        "v1_artifact": v1._sha256_file(v1_artifact_path),  # noqa: SLF001
        "a0_outputs": v1._sha256_file(a0_attempt / "outputs.jsonl"),  # noqa: SLF001
        "headroom_supply_outputs": v1._sha256_file(  # noqa: SLF001
            headroom_supply_attempt / "outputs.jsonl"
        ),
        "population_supply_outputs": v1._sha256_file(  # noqa: SLF001
            population_supply_attempt / "outputs.jsonl"
        ),
        "receipt": v1._sha256_file(receipt_path),  # noqa: SLF001
    }
    return v2.build_policy_artifact(
        outcomes,
        screen,
        offline_attempts=attempts.count,
        source_hashes=source_hashes,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m speech_aware_evidence_acquisition.analysis.training_free_a2t_registry_semantic_memory_cli"
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--a0-attempt", type=Path, required=True)
    parser.add_argument("--headroom-supply-attempt", type=Path, required=True)
    parser.add_argument("--population-supply-attempt", type=Path, required=True)
    parser.add_argument("--headroom", type=Path, required=True)
    parser.add_argument("--stage2-arm-plan", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--v1-artifact", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    artifact = run_registered_replay(
        repo_root=args.repo_root,
        data_root=args.data_root,
        lock=load_lock(args.lock),
        a0_attempt=args.a0_attempt,
        headroom_supply_attempt=args.headroom_supply_attempt,
        population_supply_attempt=args.population_supply_attempt,
        headroom_path=args.headroom,
        stage2_arm_plan_path=args.stage2_arm_plan,
        receipt_path=args.receipt,
        v1_artifact_path=args.v1_artifact,
    )
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by registered CLI run
    raise SystemExit(main())
