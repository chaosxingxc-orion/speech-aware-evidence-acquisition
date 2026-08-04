"""E0 receipt CLI (model-free).

Usage (from the study repository root, WSL, speechrl venv)::

    python -m speech_aware_evidence_acquisition.e0.generate d1
    python -m speech_aware_evidence_acquisition.e0.generate d2
    python -m speech_aware_evidence_acquisition.e0.generate d3
    python -m speech_aware_evidence_acquisition.e0.generate d4
    python -m speech_aware_evidence_acquisition.e0.generate close
    python -m speech_aware_evidence_acquisition.e0.generate runtime --runtime-root ~
    python -m speech_aware_evidence_acquisition.e0.generate verify  --runtime-root ~

``close`` binds the four deliverable artifacts (re-measured SHA-256) into
``docs/receipts/e0-closure.json``. ``verify`` is a gate dry run: it builds a
temporary exposure-ledger row and a synthetic in-budget ExecutionPlan, then asks
the real ``contracts.FrozenCoreGate`` whether a model touch *would* be allowed.
No model is started or called by any subcommand.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from ..contracts import (
    E0_RECEIPT_SCHEMA,
    STUDY_SLUG,
    ExecutionPlan,
    FrozenCoreGate,
)
from ..data.lock import CORE_CARRIER_LOCK_KEYS, data_root, umbrella_lock_path
from .artifacts import (
    ARTIFACTS_SUBDIR,
    DEFAULT_RECEIPTS_DIR,
    DELIVERABLE_ARTIFACTS,
    ArtifactError,
    sha256_file,
    write_json_artifact,
)
from .d1_identity import build_d1
from .d2_leakage import build_d2
from .d3_scoring import build_d3
from .d4_trace import build_d4
from .runtime_receipt import build_runtime_receipt


def _write_deliverable(receipts_dir: Path, artifact_name: str, document: dict) -> None:
    path = receipts_dir / ARTIFACTS_SUBDIR / artifact_name
    digest = write_json_artifact(path, document)
    print(f"wrote {path} sha256={digest}")


def _close(receipts_dir: Path) -> None:
    deliverables: dict[str, object] = {}
    for name, artifact_name in DELIVERABLE_ARTIFACTS.items():
        artifact = receipts_dir / ARTIFACTS_SUBDIR / artifact_name
        if not artifact.is_file():
            raise ArtifactError(
                f"deliverable {name} artifact missing: {artifact}; generate it first"
            )
        deliverables[name] = {
            "status": "CLOSED",
            "artifact": f"{ARTIFACTS_SUBDIR}/{artifact_name}",
            "sha256": sha256_file(artifact),
        }
    receipt = {
        "schema": E0_RECEIPT_SCHEMA,
        "study": STUDY_SLUG,
        "deliverables": deliverables,
    }
    path = receipts_dir / "e0-closure.json"
    digest = write_json_artifact(path, receipt)
    print(f"wrote {path} sha256={digest}")


def _runtime(receipts_dir: Path, lock_path: Path, root: Path, runtime_root: Path) -> None:
    receipt = build_runtime_receipt(lock_path, root, runtime_root)
    path = receipts_dir / "runtime.json"
    digest = write_json_artifact(path, receipt)
    print(f"wrote {path} sha256={digest}")


def _verify(receipts_dir: Path, lock_path: Path, root: Path, runtime_root: Path) -> None:
    e0_receipt = receipts_dir / "e0-closure.json"
    runtime_receipt = receipts_dir / "runtime.json"
    for path in (e0_receipt, runtime_receipt):
        if not path.is_file():
            raise ArtifactError(f"receipt missing for verification: {path}")

    run_id = "SAEA-E0-GATE-DRYRUN"
    header = (
        "| date | run/experiment id | execution profile | scope | model/tool "
        "| speech carrier + split | split role | split identity hash | consumed "
        "| calls | speech audio seconds | inherited exposure | artifacts | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    row = (
        f"| dry-run | {run_id} | baseline-reproduction | gate dry run | none "
        f"| {CORE_CARRIER_LOCK_KEYS[0]} dev | dev | {sha256_file(e0_receipt)} | no "
        "| 0 | 0 | dry run only | none | synthetic row, temp file, no model touch |\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "exposure-ledger-dryrun.md"
        ledger.write_text(header + row, encoding="utf-8")
        gate = FrozenCoreGate(
            e0_receipt=e0_receipt,
            runtime_receipt=runtime_receipt,
            data_root=root,
            lock_path=lock_path,
            runtime_root=runtime_root,
            exposure_ledger=ledger,
        )
        plan = ExecutionPlan(
            run_id=run_id,
            execution_profile="baseline-reproduction",
            carrier_lock_key=CORE_CARRIER_LOCK_KEYS[0],
            split_role="dev",
            split_identity_hash=sha256_file(e0_receipt),
            planned_model_calls=1,
            planned_gpu_hours=0.01,
            planned_speech_audio_seconds=1,
            protocol_hash=sha256_file(runtime_receipt),
        )
        gate.assert_model_touch_allowed(plan)
    print(
        "GATE OPEN (dry run): E0 closure and runtime receipts verified true against "
        "disk bytes and the umbrella lock. No model was touched."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="speech_aware_evidence_acquisition.e0.generate")
    parser.add_argument(
        "command",
        choices=["d1", "d2", "d3", "d4", "close", "runtime", "verify"],
    )
    parser.add_argument("--receipts-dir", type=Path, default=DEFAULT_RECEIPTS_DIR)
    parser.add_argument("--lock", type=Path, default=None, help="umbrella datasets lock")
    parser.add_argument("--runtime-root", type=Path, default=None)
    arguments = parser.parse_args(argv)

    receipts_dir = arguments.receipts_dir.resolve()
    lock_path = (arguments.lock or umbrella_lock_path()).resolve()

    try:
        if arguments.command == "d1":
            _write_deliverable(receipts_dir, "d1-identity.json", build_d1(lock_path, data_root()))
        elif arguments.command == "d2":
            _write_deliverable(receipts_dir, "d2-leakage.json", build_d2(lock_path))
        elif arguments.command == "d3":
            _write_deliverable(receipts_dir, "d3-scoring.json", build_d3())
        elif arguments.command == "d4":
            _write_deliverable(receipts_dir, "d4-trace.json", build_d4(lock_path, data_root()))
        elif arguments.command == "close":
            _close(receipts_dir)
        elif arguments.command in ("runtime", "verify"):
            if arguments.runtime_root is None:
                raise ArtifactError(f"--runtime-root is required for {arguments.command}")
            runtime_root = arguments.runtime_root.expanduser().resolve()
            if arguments.command == "runtime":
                _runtime(receipts_dir, lock_path, data_root(), runtime_root)
            else:
                _verify(receipts_dir, lock_path, data_root(), runtime_root)
    except Exception as error:
        print(f"E0 generation failed closed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
