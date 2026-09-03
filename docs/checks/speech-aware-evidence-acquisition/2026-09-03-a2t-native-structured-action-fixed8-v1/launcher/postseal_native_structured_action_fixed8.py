#!/usr/bin/env python3
"""Materialize fixed-eight historical cells only after both strict cells seal.

This dispatcher is intentionally not a scorer or model launcher.  Its only
write path is the two zero-contact historical derivatives and the four-whole-
manifest scorer jobs file, and that path is unreachable until the strict-cell
seal proof has succeeded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_native_structured_action_postseal import (  # noqa: E402
    CELL_ORDER,
    HISTORICAL_CELLS,
    STRICT_CELLS,
    build_four_job_plan,
    materialize_historical_subsets,
    prove_strict_cells_sealed,
)


RUN_ID = "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1"
FLIGHT_ID = "flight-20260903T013000Z"
ROSTER_RELPATH = Path("docs/receipts/a2t/A2T-NATIVE-STRUCTURED-ACTION-FIXED8.json")
PARENT_RUN_ID = "SAEA-A2T-EXECUTABLE-GROUND-QUALIFICATION-104-V1"
PARENT_FLIGHT_ID = "flight-20260902T145019Z"
PARENT_SOURCES = {
    "REGISTRY_NO_SCHEMA": {
        "directory": "m0-registry-direct",
        "manifest_sha256": "96ee952acc10aa414ec4ddf3965bb08519b7407c36c40445d09150145e841836",
        "outputs_sha256": "b30a5aa8fbb9b5bc61483f117a3ba2546c71d15ba357ad099792a45dfa0af49f",
    },
    "HANDBOOK_NO_SCHEMA": {
        "directory": "g1-full-executable-ground",
        "manifest_sha256": "b0b19f4c537267da358545b4ae73a0a75d0ee42e40614e9ee86ba4ed221e71de",
        "outputs_sha256": "f4c92804e359dda1faa7880a27bffb709db9638619e51b1f7e02c74176063803",
    },
}
REGISTRY_SUCCESSOR_DIRECTORY = "registry_strict_action_recovery_v2"
HANDBOOK_RECOVERY_DIRECTORY = "handbook_strict_action_recovery_v2"
RECOVERY_V2_RUN_ID = "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-RECOVERY-V2"
RECOVERY_V2_RECEIPT_NAME = "recovery-v2-flight-receipt.json"


def _read_object(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read {label}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} must be a JSON object")
    return value


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise RuntimeError(f"cannot hash {path}: {error}") from error


def fixed8_sample_ids() -> tuple[str, ...]:
    """Read identity-only roster metadata; never open output or score bytes."""

    roster = _read_object(REPO / ROSTER_RELPATH, "fixed-eight roster")
    items = roster.get("items")
    sample_ids = (
        [item.get("sample_id") for item in items]
        if isinstance(items, list) and all(isinstance(item, Mapping) for item in items)
        else None
    )
    if (
        not isinstance(sample_ids, list)
        or len(sample_ids) != 8
        or len(set(sample_ids)) != 8
        or not all(isinstance(sample_id, str) and sample_id for sample_id in sample_ids)
    ):
        raise RuntimeError("fixed-eight roster must carry exactly eight unique sample ids")
    return tuple(sample_ids)


def strict_seals_from_mission(mission_dir: Path) -> Mapping[str, Mapping[str, object]]:
    """Collect strict manifest hashes without opening any historical artifact."""

    descriptors: dict[str, Mapping[str, object]] = {}
    for cell in STRICT_CELLS:
        recovery_receipt = Path(mission_dir) / RECOVERY_V2_RECEIPT_NAME
        successor_manifest = (
            Path(mission_dir) / REGISTRY_SUCCESSOR_DIRECTORY / f"{RUN_ID}.run-manifest.json"
        )
        handbook_recovery_manifest = (
            Path(mission_dir)
            / HANDBOOK_RECOVERY_DIRECTORY
            / f"{RECOVERY_V2_RUN_ID}.run-manifest.json"
        )
        if (
            cell == "REGISTRY_STRICT_ACTION"
            and recovery_receipt.is_file()
            and successor_manifest.is_file()
        ):
            manifest_path = successor_manifest
        elif (
            cell == "HANDBOOK_STRICT_ACTION"
            and recovery_receipt.is_file()
            and handbook_recovery_manifest.is_file()
        ):
            manifest_path = handbook_recovery_manifest
        else:
            manifest_path = (
                Path(mission_dir) / cell.lower() / f"{RUN_ID}.run-manifest.json"
            )
        manifest = _read_object(manifest_path, f"{cell} strict manifest")
        descriptor: dict[str, object] = {
            "manifest": manifest_path.resolve(),
            "manifest_sha256": _sha256(manifest_path),
        }
        for key, descriptor_key in (
            ("outputs", "outputs_sha256"),
            ("raw_trace", "raw_trace_sha256"),
            ("trace_manifest", "trace_manifest_sha256"),
        ):
            artifact = manifest.get(key)
            if not isinstance(artifact, Mapping) or not isinstance(artifact.get("sha256"), str):
                raise RuntimeError(f"{cell} strict manifest lacks {key} SHA-256")
            descriptor[descriptor_key] = artifact["sha256"]
        if cell == "REGISTRY_STRICT_ACTION" and recovery_receipt.is_file():
            descriptor.update(
                {
                    "recovered_from_aborted_attempt": True,
                    "recovery_receipt": recovery_receipt.resolve(),
                    "recovery_receipt_sha256": _sha256(recovery_receipt),
                }
            )
        descriptors[cell] = descriptor
    return descriptors


def historical_sources(data_root: Path) -> Mapping[str, Mapping[str, object]]:
    """Return pinned parent addresses only; do not open parent artifacts here."""

    flight_root = (
        Path(data_root) / "runs" / PARENT_RUN_ID / PARENT_FLIGHT_ID
    )
    descriptors: dict[str, Mapping[str, object]] = {}
    for cell in HISTORICAL_CELLS:
        source = PARENT_SOURCES[cell]
        directory = str(source["directory"])
        manifest = flight_root / directory / f"{PARENT_RUN_ID}.run-manifest.json"
        descriptors[cell] = {
            "manifest": manifest,
            "manifest_sha256": source["manifest_sha256"],
            "outputs_sha256": source["outputs_sha256"],
        }
    return descriptors


def dispatch_postseal(
    *,
    sample_ids: Sequence[str],
    strict_seals: Mapping[str, Mapping[str, object]],
    historical_sources: Mapping[str, Mapping[str, object]],
    output_root: Path,
    jobs_path: Path,
    score_output_dir: Path,
):
    """Prove strict sealing, then materialize and plan four complete jobs."""

    authorization = prove_strict_cells_sealed(
        strict_seals=strict_seals,
        sample_ids=sample_ids,
    )
    materialized = materialize_historical_subsets(
        authorization=authorization,
        historical_sources=historical_sources,
        output_root=output_root,
    )
    manifests = {}
    for cell in CELL_ORDER:
        manifest = (
            strict_seals[cell]["manifest"]
            if cell in STRICT_CELLS
            else materialized[cell].manifest
        )
        manifests[cell] = {"manifest": manifest, "sample_ids": tuple(sample_ids)}
    return build_four_job_plan(
        authorization=authorization,
        manifests=manifests,
        jobs_path=jobs_path,
        score_output_dir=score_output_dir,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--flight-id", default=FLIGHT_ID)
    parser.add_argument(
        "--materialize",
        action="store_true",
        help="explicitly create post-seal zero-contact derivatives and score jobs",
    )
    args = parser.parse_args(argv)
    if not args.materialize:
        parser.error("--materialize is required; this runner never scores or contacts a model")

    mission_dir = Path(args.data_root) / "runs" / RUN_ID / args.flight_id
    plan = dispatch_postseal(
        sample_ids=fixed8_sample_ids(),
        strict_seals=strict_seals_from_mission(mission_dir),
        historical_sources=historical_sources(args.data_root),
        output_root=mission_dir / "historical-subsets",
        jobs_path=mission_dir / "score-jobs.jsonl",
        score_output_dir=mission_dir / "parallel-official-score",
    )
    print(
        json.dumps(
            {
                "status": "POSTSEAL_MATERIALIZED_UNSCORED",
                "run_id": RUN_ID,
                "jobs_path": str(plan.jobs_path),
                "score_command": list(plan.command),
                "contacts": {"model": 0, "scorer": 0, "network": 0, "gold": 0},
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
