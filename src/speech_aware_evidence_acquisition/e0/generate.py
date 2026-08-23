"""E0 receipt CLI (model-free).

Usage (from the study repository root, WSL, speechrl venv)::

    python -m speech_aware_evidence_acquisition.e0.generate d1
    python -m speech_aware_evidence_acquisition.e0.generate d1-media-supplement
    python -m speech_aware_evidence_acquisition.e0.generate d2
    python -m speech_aware_evidence_acquisition.e0.generate d3
    python -m speech_aware_evidence_acquisition.e0.generate d4
    python -m speech_aware_evidence_acquisition.e0.generate close
    python -m speech_aware_evidence_acquisition.e0.generate runtime --runtime-root ~
    python -m speech_aware_evidence_acquisition.e0.generate verify  --runtime-root ~

    # A SECOND pinned model (e.g. a Q4_K_M requant, materialized in its own
    # directory the umbrella lock names under a NEW model key): pass
    # --model-lock-key and --out to write a receipt for that model without
    # touching docs/receipts/runtime.json (the Q8_0 default).
    python -m speech_aware_evidence_acquisition.e0.generate runtime \\
        --runtime-root ~ \\
        --model-lock-key qwen3-omni-30b-a3b-instruct-gguf-q4km \\
        --out docs/receipts/runtime-q4km.json

``close`` binds the four deliverable artifacts (re-measured SHA-256) into
``docs/receipts/e0-closure.json``. ``verify`` is a gate dry run: it builds a
temporary exposure-ledger row and a synthetic in-budget ExecutionPlan, then asks
the real ``contracts.FrozenCoreGate`` whether a model touch *would* be allowed.
No model is started or called by any subcommand.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from ..contracts import (
    E0_RECEIPT_SCHEMA,
    MODEL_LOCK_KEY,
    STUDY_SLUG,
    ExecutionPlan,
    FrozenCoreGate,
)
from ..data.lock import CORE_CARRIER_LOCK_KEYS, data_root, umbrella_lock_path
from .artifacts import (
    ARTIFACTS_SUBDIR,
    DEFAULT_RECEIPTS_DIR,
    DELIVERABLE_ARTIFACTS,
    REPO_ROOT,
    ArtifactError,
    sha256_file,
    write_json_artifact,
)
from .d1_identity import (
    build_d1,
    build_d1_media_supplement,
    build_speech_native_engineering_gate_view,
    build_speech_native_probe_receipt,
    build_speech_native_runtime_view,
)
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


def _runtime(
    receipts_dir: Path,
    lock_path: Path,
    root: Path,
    runtime_root: Path,
    *,
    model_lock_key: str = MODEL_LOCK_KEY,
    llama_dir_name: str = "llama.cpp",
    binary_relpath: str = "build/bin/llama-server",
    out: Path | None = None,
    role: str | None = None,
    model_root: Path | None = None,
) -> None:
    """Build and write a runtime receipt for ``model_lock_key`` (default: the
    frozen Q8_0 key) to ``out`` (default: ``<receipts_dir>/runtime.json``,
    the committed Q8_0 receipt -- unchanged for every caller that passes
    neither flag). Passing both lets an operator build a receipt for a
    SECOND pinned model (e.g. ``--model-lock-key
    qwen3-omni-30b-a3b-instruct-gguf-q4km --out docs/receipts/runtime-q4km.json``)
    without ever touching the default Q8_0 receipt."""

    binary_path = Path(binary_relpath)
    if (
        binary_path.is_absolute()
        or binary_path == Path(".")
        or ".." in binary_path.parts
    ):
        raise ArtifactError(
            "runtime binary path must be a non-empty checkout-relative path"
        )
    receipt = build_runtime_receipt(
        lock_path,
        root,
        runtime_root,
        llama_dir_name=llama_dir_name,
        binary_relpath=binary_relpath,
        model_lock_key=model_lock_key,
        role=role,
        model_root=model_root,
    )
    path = out if out is not None else receipts_dir / "runtime.json"
    digest = write_json_artifact(path, receipt)
    print(f"wrote {path} sha256={digest}")


def _verify(receipts_dir: Path, lock_path: Path, root: Path, runtime_root: Path) -> None:
    """Gate dry run. NOT an authorization and NOT a template for a real run.

    A real model run must construct its gate via ``FrozenCoreGate.for_study_repo``
    (which pins the committed ``docs/exposure-ledger.md``) and pre-register its row
    there before any byte is read. The synthetic temp-file ledger below exists only
    so the dry run can exercise the full verification path without fabricating a
    row in the real ledger; nothing it proves survives the ``with`` block.
    """

    e0_receipt = receipts_dir / "e0-closure.json"
    runtime_receipt = receipts_dir / "runtime.json"
    for path in (e0_receipt, runtime_receipt):
        if not path.is_file():
            raise ArtifactError(f"receipt missing for verification: {path}")

    run_id = "SAEA-E0-GATE-DRYRUN-NOT-A-RUN"
    header = (
        "| date | run/experiment id | execution profile | scope | model/tool "
        "| speech carrier + split | split role | split identity hash | consumed "
        "| calls | speech audio seconds | gpu hours | inherited exposure "
        "| artifacts | notes |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    row = (
        f"| dry-run | {run_id} | baseline-reproduction | gate dry run | none "
        f"| {CORE_CARRIER_LOCK_KEYS[0]} dev | dev | {sha256_file(e0_receipt)} | no "
        "| 1 | 1 | 0.01 | dry run only | none | synthetic row, temp file, no model touch |\n"
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
            source_root=REPO_ROOT,
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
        "GATE OPEN (dry run): E0 closure, scoring freeze, runtime set and receipts "
        "verified true against disk bytes and the umbrella lock at this instant. "
        "No model was touched, and this dry run authorizes nothing."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="speech_aware_evidence_acquisition.e0.generate")
    parser.add_argument(
        "command",
        choices=[
            "d1",
            "d1-media-supplement",
            "d2",
            "d3",
            "d4",
            "close",
            "runtime",
            "verify",
        ],
    )
    parser.add_argument("--receipts-dir", type=Path, default=DEFAULT_RECEIPTS_DIR)
    parser.add_argument("--lock", type=Path, default=None, help="umbrella datasets lock")
    parser.add_argument("--runtime-root", type=Path, default=None)
    parser.add_argument(
        "--llama-dir-name",
        default="llama.cpp",
        help=(
            "checkout directory directly under --runtime-root (runtime command only); "
            "use the existing named featcache checkout without a symlink or copied build"
        ),
    )
    parser.add_argument(
        "--binary-relpath",
        default="build/bin/llama-server",
        help=(
            "checkout-relative llama-server path (runtime command only); use an "
            "existing parallel build directory without copying or replacing the "
            "resident binary"
        ),
    )
    parser.add_argument(
        "--model-root",
        type=Path,
        default=None,
        help=(
            "root containing the lock-relative model directory (runtime command "
            "only); use the verified WSL ext4 mirror instead of the dataset root"
        ),
    )
    parser.add_argument(
        "--model-lock-key",
        default=MODEL_LOCK_KEY,
        help=(
            "umbrella-lock model entry name to pin (runtime command only); default: "
            "the frozen Q8_0 key. Pass a different key (e.g. a Q4_K_M requant's own "
            "lock entry) to build a receipt for a SECOND pinned model"
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "receipt output path (runtime command only); default: "
            "<receipts-dir>/runtime.json. Pass e.g. docs/receipts/runtime-q4km.json "
            "alongside --model-lock-key to write a second model's receipt without "
            "touching the default Q8_0 receipt"
        ),
    )
    parser.add_argument(
        "--binding",
        type=Path,
        default=None,
        help=(
            "speech-native binding for d1-media-supplement; defaults to the "
            "committed train binding"
        ),
    )
    parser.add_argument(
        "--parent-d1",
        type=Path,
        default=None,
        help=(
            "immutable parent D1 artifact for d1-media-supplement; defaults "
            "to <receipts-dir>/artifacts/d1-identity.json"
        ),
    )
    parser.add_argument(
        "--gate-view-out",
        type=Path,
        default=None,
        help=(
            "label-free ENG-GATE8 dataset config written with d1-media-supplement; "
            "defaults to configs/dataset/slurp-speech-native-eng-gate8.json"
        ),
    )
    parser.add_argument(
        "--runtime-views-dir",
        type=Path,
        default=None,
        help=(
            "directory for the TRAIN90/OPT-A36/OPT-B18/GATE18/KEY18 label-free "
            "runtime views written with d1-media-supplement; defaults to "
            "configs/dataset"
        ),
    )
    parser.add_argument(
        "--probe-receipts-dir",
        type=Path,
        default=None,
        help=(
            "directory for runtime-view probe split receipts written with "
            "d1-media-supplement; defaults to docs/receipts/probe-samples"
        ),
    )
    parser.add_argument(
        "--expected-query-count",
        type=int,
        default=72,
        help=(
            "total distinct query samples in --binding for d1-media-supplement; "
            "default 72 preserves the original train binding"
        ),
    )
    parser.add_argument(
        "--selection-name",
        default=None,
        help=(
            "optional additional split name from --binding to materialize as one "
            "label-free runtime view"
        ),
    )
    parser.add_argument(
        "--selection-count",
        type=int,
        default=None,
        help="expected item count for --selection-name",
    )
    parser.add_argument(
        "--selection-view-out",
        type=Path,
        default=None,
        help="output path for the optional additional runtime view",
    )
    parser.add_argument(
        "--selection-probe-out",
        type=Path,
        default=None,
        help="output path for the optional additional probe receipt",
    )
    parser.add_argument(
        "--supplement-relpath",
        default="receipts/artifacts/d1-speech-native-train90.json",
        help=(
            "repository-relative D1 supplement path embedded in generated runtime "
            "views; default preserves historical output"
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=16,
        help="bounded media-validation workers for d1-media-supplement (default: 16)",
    )
    parser.add_argument(
        "--role",
        choices=["preprocess", "inference"],
        default=None,
        help=(
            "runtime receipt role (runtime command only). preprocess binds decoder and "
            "mmproj; inference binds decoder only. Omit for the historical v2 receipt"
        ),
    )
    arguments = parser.parse_args(argv)

    receipts_dir = arguments.receipts_dir.resolve()

    def lock_path() -> Path:
        # Resolved lazily: d3/close never read the lock and must work standalone.
        return (arguments.lock or umbrella_lock_path()).resolve()

    try:
        if arguments.command == "d1":
            _write_deliverable(
                receipts_dir, "d1-identity.json", build_d1(lock_path(), data_root())
            )
        elif arguments.command == "d1-media-supplement":
            binding_path = (
                arguments.binding
                or REPO_ROOT
                / "configs"
                / "probes"
                / "g0-binding"
                / "speech-native-train-binding.json"
            ).resolve()
            parent_d1_path = (
                arguments.parent_d1
                or receipts_dir / ARTIFACTS_SUBDIR / "d1-identity.json"
            ).resolve()
            document = build_d1_media_supplement(
                binding_path=binding_path,
                data_root=data_root(),
                parent_d1_path=parent_d1_path,
                workers=arguments.workers,
                expected_query_count=arguments.expected_query_count,
            )
            out = (
                arguments.out
                or receipts_dir
                / ARTIFACTS_SUBDIR
                / "d1-speech-native-train90.json"
            ).resolve()
            digest = write_json_artifact(out, document)
            print(f"wrote {out} sha256={digest}")
            view = build_speech_native_engineering_gate_view(
                binding_path=binding_path,
                supplement=document,
                supplement_artifact_sha256=digest,
                supplement_relpath=arguments.supplement_relpath,
            )
            gate_view_out = (
                arguments.gate_view_out
                or REPO_ROOT
                / "configs"
                / "dataset"
                / "slurp-speech-native-eng-gate8.json"
            ).resolve()
            view_digest = write_json_artifact(gate_view_out, view)
            print(f"wrote {gate_view_out} sha256={view_digest}")
            runtime_views_dir = (
                arguments.runtime_views_dir
                or REPO_ROOT / "configs" / "dataset"
            ).resolve()
            probe_receipts_dir = (
                arguments.probe_receipts_dir
                or receipts_dir / "probe-samples"
            ).resolve()
            runtime_view_names = {
                "TRAIN90": "slurp-speech-native-train90.json",
                "OPT-A36": "slurp-speech-native-opt-a36.json",
                "OPT-B18": "slurp-speech-native-opt-b18.json",
                "GATE18": "slurp-speech-native-gate18.json",
                "KEY18": "slurp-speech-native-key18.json",
            }
            for selection_name, filename in runtime_view_names.items():
                runtime_view = build_speech_native_runtime_view(
                    binding_path=binding_path,
                    supplement=document,
                    supplement_artifact_sha256=digest,
                    selection_name=selection_name,
                    supplement_relpath=arguments.supplement_relpath,
                )
                runtime_view_path = runtime_views_dir / filename
                runtime_view_digest = write_json_artifact(
                    runtime_view_path, runtime_view
                )
                print(
                    f"wrote {runtime_view_path} sha256={runtime_view_digest}"
                )
                probe_receipt = build_speech_native_probe_receipt(runtime_view)
                probe_receipt_path = probe_receipts_dir / f"{selection_name}.json"
                probe_receipt_digest = write_json_artifact(
                    probe_receipt_path, probe_receipt
                )
                print(
                    f"wrote {probe_receipt_path} sha256={probe_receipt_digest}"
                )
            selection_arguments = (
                arguments.selection_name,
                arguments.selection_count,
                arguments.selection_view_out,
                arguments.selection_probe_out,
            )
            if any(value is not None for value in selection_arguments):
                if any(value is None for value in selection_arguments):
                    raise ArtifactError(
                        "--selection-name, --selection-count, --selection-view-out, "
                        "and --selection-probe-out must be supplied together"
                    )
                additional_view = build_speech_native_runtime_view(
                    binding_path=binding_path,
                    supplement=document,
                    supplement_artifact_sha256=digest,
                    selection_name=arguments.selection_name,
                    expected_count=arguments.selection_count,
                    supplement_relpath=arguments.supplement_relpath,
                )
                additional_view_path = arguments.selection_view_out.resolve()
                additional_view_digest = write_json_artifact(
                    additional_view_path, additional_view
                )
                print(
                    f"wrote {additional_view_path} sha256={additional_view_digest}"
                )
                additional_probe = build_speech_native_probe_receipt(
                    additional_view
                )
                additional_probe_path = arguments.selection_probe_out.resolve()
                additional_probe_digest = write_json_artifact(
                    additional_probe_path, additional_probe
                )
                print(
                    f"wrote {additional_probe_path} sha256={additional_probe_digest}"
                )
        elif arguments.command == "d2":
            _write_deliverable(receipts_dir, "d2-leakage.json", build_d2(lock_path()))
        elif arguments.command == "d3":
            _write_deliverable(receipts_dir, "d3-scoring.json", build_d3())
        elif arguments.command == "d4":
            _write_deliverable(
                receipts_dir, "d4-trace.json", build_d4(lock_path(), data_root())
            )
        elif arguments.command == "close":
            _close(receipts_dir)
        elif arguments.command in ("runtime", "verify"):
            if arguments.runtime_root is None:
                raise ArtifactError(f"--runtime-root is required for {arguments.command}")
            runtime_root = arguments.runtime_root.expanduser().resolve()
            if arguments.command == "runtime":
                _runtime(
                    receipts_dir,
                    lock_path(),
                    data_root(),
                    runtime_root,
                    model_lock_key=arguments.model_lock_key,
                    llama_dir_name=arguments.llama_dir_name,
                    binary_relpath=arguments.binary_relpath,
                    out=arguments.out,
                    role=arguments.role,
                    model_root=(
                        arguments.model_root.expanduser().resolve()
                        if arguments.model_root is not None
                        else None
                    ),
                )
            else:
                _verify(receipts_dir, lock_path(), data_root(), runtime_root)
    except Exception as error:
        print(f"E0 generation failed closed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
