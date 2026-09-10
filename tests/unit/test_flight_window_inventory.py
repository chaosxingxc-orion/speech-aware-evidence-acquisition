"""Model-free FlightRuntime exact-window inventory integration."""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_windows import WindowRequestBatch
from speech_aware_evidence_acquisition.core.session import load_runtime_receipt


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _runtime_world(tmp_path, *, receipt_mutator=None):
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    runtime_root = tmp_path / "runtime"
    model_root = tmp_path / "model-root"
    for root in (repo / "docs/receipts", data, runtime_root / "bin", model_root / "models"):
        root.mkdir(parents=True, exist_ok=True)

    binary = b"synthetic pinned llama binary"
    decoder = b"synthetic decoder gguf"
    mmproj = b"synthetic mmproj gguf"
    (runtime_root / "bin/llama-server").write_bytes(binary)
    (model_root / "models/decoder.gguf").write_bytes(decoder)
    (model_root / "models/mmproj-audio.gguf").write_bytes(mmproj)
    receipt = {
        "schema": "saea-runtime-receipt-v3",
        "study": "speech-aware-evidence-acquisition",
        "model_lock_key": "synthetic-model",
        "llama_cpp": {
            "binary_path": "bin/llama-server",
            "binary_sha256": _sha(binary),
            "binary_bytes": len(binary),
            "build_commit": "a" * 40,
        },
        "gguf_files": [
            {
                "path": "models/decoder.gguf",
                "sha256": _sha(decoder),
                "bytes": len(decoder),
            },
            {
                "path": "models/mmproj-audio.gguf",
                "sha256": _sha(mmproj),
                "bytes": len(mmproj),
            },
        ],
    }
    if receipt_mutator is not None:
        receipt_mutator(receipt, runtime_root, model_root)
    receipt_path = repo / "docs/receipts/runtime.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    parent = data / "datasets/e21/sample.wav"
    parent.parent.mkdir(parents=True)
    parent.write_bytes(b"synthetic parent")
    window = data / "derived/obs-slices/run/sample/i0000.wav"
    window.parent.mkdir(parents=True)
    window.write_bytes(b"synthetic exact window")
    source = {
        "sample_id": "sample",
        "parent_media_relpath": "datasets/e21/sample.wav",
        "parent_sha256": _sha(parent.read_bytes()),
        "start_seconds": 0.0,
        "end_seconds": 1.0,
        "audio_seconds": 1.0,
        "sample_rate_hz": 16_000,
        "media_relpath": "derived/obs-slices/run/sample/i0000.wav",
        "sha256": _sha(window.read_bytes()),
        "bytes": window.stat().st_size,
        "iteration": 0,
        "preprocess": [],
        "pre_sha256": None,
    }
    batch = WindowRequestBatch(
        payloads=(
            {
                "sample_id": "sample",
                "media_relpath": source["media_relpath"],
                "audio_seconds": 1.0,
                "sample_rate_hz": 16_000,
            },
        ),
        request_keys=("sample#w0001",),
        source_bindings=(source,),
    )
    values = {
        "runtime_receipt": "receipts/runtime.json",
        "model_materialization_root": str(model_root),
    }
    runtime = object.__new__(FlightRuntime)
    runtime._repo_root = repo
    runtime._data_root = data
    runtime._runtime_root = runtime_root
    runtime._run_id = "SAEA-E21-SYNTHETIC-INVENTORY"
    runtime._runtime_receipt_loader = load_runtime_receipt
    runtime._prepare = lambda: (
        values,
        "earnings21-original",
        "discovery",
        "b" * 64,
    )
    return runtime, batch, receipt_path


def test_runtime_prepares_actual_window_batch_with_verified_encoder_identity(tmp_path):
    runtime, batch, receipt_path = _runtime_world(tmp_path)
    plan = object()
    seen = []
    runtime._build_execution_plan = lambda values, carrier, identity: plan

    def materialize(*, execution_plan):
        seen.append(execution_plan)
        return batch

    runtime.materialize_window_batch = materialize
    runtime.serve = lambda: pytest.fail("inventory must not start a service")
    runtime.session_required_identity = lambda: pytest.fail(
        "inventory must not require a serving session"
    )
    output = tmp_path / "prepared/window-inventory.json"

    result = runtime.prepare_window_inventory(output)
    document = json.loads(output.read_text(encoding="utf-8"))

    assert result["cache"] == "cold"
    assert seen == [plan]
    assert document["contact_class"] == "model-free"
    identity = document["output"]["encoder_identity"]
    assert identity == {
        "runtime_receipt_sha256": _sha(receipt_path.read_bytes()),
        "build_commit": "a" * 40,
        "decoder_gguf_sha256": _sha(b"synthetic decoder gguf"),
        "mmproj_sha256": _sha(b"synthetic mmproj gguf"),
    }
    assert document["output"]["request_count"] == 1
    assert document["output"]["state"] == (
        "inputs-verified-features-not-materialized"
    )


@pytest.mark.parametrize(
    "mutation, message",
    [
        (
            lambda receipt, _runtime_root, model_root: (
                model_root / "models/decoder.gguf"
            ).write_bytes(b"x" * len(b"synthetic decoder gguf")),
            "hash",
        ),
        (
            lambda receipt, _runtime_root, _model_root: receipt["gguf_files"].pop(),
            "exactly one decoder and one mmproj",
        ),
        (
            lambda receipt, _runtime_root, _model_root: receipt["gguf_files"][0].pop(
                "bytes"
            ),
            "size",
        ),
        (
            lambda receipt, _runtime_root, _model_root: receipt["gguf_files"][0].update(
                {"sha256": "INVALID"}
            ),
            "hash",
        ),
        (
            lambda receipt, runtime_root, _model_root: (
                runtime_root / receipt["llama_cpp"]["binary_path"]
            ).unlink(),
            "cannot resolve",
        ),
        (
            lambda receipt, _runtime_root, model_root: (
                model_root / receipt["gguf_files"][1]["path"]
            ).unlink(),
            "cannot resolve",
        ),
        (
            lambda receipt, _runtime_root, _model_root: receipt.pop("llama_cpp"),
            "llama_cpp",
        ),
        (
            lambda receipt, _runtime_root, _model_root: receipt["llama_cpp"].pop(
                "build_commit"
            ),
            "build_commit",
        ),
        (
            lambda receipt, _runtime_root, _model_root: receipt["gguf_files"][0].update(
                {"path": "../foreign.gguf"}
            ),
            "traversal",
        ),
    ],
)
def test_runtime_refuses_unverified_or_ambiguous_encoder_identity(
    tmp_path, mutation, message
):
    runtime, batch, _receipt_path = _runtime_world(
        tmp_path, receipt_mutator=mutation
    )
    runtime._build_execution_plan = lambda *args: object()
    runtime.materialize_window_batch = lambda **kwargs: pytest.fail(
        "invalid encoder identity must refuse before window materialization"
    )

    with pytest.raises((PreparationError, FlightRuntimeError), match=message):
        runtime.prepare_window_inventory(tmp_path / "inventory.json")


def test_runtime_refuses_missing_or_unreadable_receipt(tmp_path):
    from speech_aware_evidence_acquisition.core.session import SessionError

    runtime, _batch, receipt_path = _runtime_world(tmp_path)
    runtime._build_execution_plan = lambda *args: object()
    runtime.materialize_window_batch = lambda **kwargs: pytest.fail(
        "invalid receipt must refuse before window materialization"
    )
    receipt_path.unlink()
    with pytest.raises(PreparationError, match="cannot stat runtime receipt"):
        runtime.prepare_window_inventory(tmp_path / "missing.json")

    runtime, _batch, receipt_path = _runtime_world(tmp_path / "unreadable")
    runtime._build_execution_plan = lambda *args: object()
    runtime.materialize_window_batch = lambda **kwargs: pytest.fail(
        "invalid receipt must refuse before window materialization"
    )
    receipt_path.write_text("{", encoding="utf-8")
    with pytest.raises(SessionError, match="cannot read runtime receipt"):
        runtime.prepare_window_inventory(tmp_path / "unreadable.json")


def test_runtime_refuses_receipt_changed_between_hash_and_load(tmp_path):
    runtime, _batch, receipt_path = _runtime_world(tmp_path)
    original_loader = runtime._runtime_receipt_loader

    def changing_loader(path):
        document = original_loader(path)
        path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
        return document

    runtime._runtime_receipt_loader = changing_loader
    runtime._build_execution_plan = lambda *args: object()
    runtime.materialize_window_batch = lambda **kwargs: pytest.fail(
        "changed receipt must refuse before window materialization"
    )

    with pytest.raises(PreparationError, match="changed while it was read"):
        runtime.prepare_window_inventory(tmp_path / "inventory.json")
    assert receipt_path.exists()


def test_runtime_refuses_missing_composed_execution_plan_before_materialization(tmp_path):
    runtime, _batch, _receipt_path = _runtime_world(tmp_path)
    runtime._build_execution_plan = lambda *args: (_ for _ in ()).throw(
        FlightRuntimeError("experiment fragment must declare an execution_plan")
    )
    runtime.materialize_window_batch = lambda **kwargs: pytest.fail(
        "missing plan must refuse before window materialization"
    )

    with pytest.raises(FlightRuntimeError, match="execution_plan"):
        runtime.prepare_window_inventory(tmp_path / "inventory.json")
