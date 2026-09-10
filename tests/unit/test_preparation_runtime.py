"""Model-free tests for role-specific runtime identity binding."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_runtime import (
    verify_feature_encoder_runtime,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _world(tmp_path: Path):
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    data = tmp_path / "data"
    (repo / "docs" / "receipts").mkdir(parents=True)
    (runtime / "bin").mkdir(parents=True)
    (data / "models").mkdir(parents=True)

    binary = b"server"
    library = b"library"
    decoder = b"decoder"
    mmproj = b"mmproj"
    (runtime / "bin" / "server").write_bytes(binary)
    (runtime / "bin" / "lib.so").write_bytes(library)
    (data / "models" / "decoder.gguf").write_bytes(decoder)
    (data / "models" / "mmproj.gguf").write_bytes(mmproj)

    common = {
        "schema": "saea-runtime-receipt-v3",
        "study": "speech-aware-evidence-acquisition",
        "model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf",
        "llama_cpp": {
            "build_commit": "a" * 40,
            "reported_build": "version: test",
            "binary_path": "bin/server",
            "binary_bytes": len(binary),
            "binary_sha256": _sha(binary),
        },
        "runtime_libraries": [
            {
                "path": "bin/lib.so",
                "bytes": len(library),
                "sha256": _sha(library),
            }
        ],
    }
    decoder_entry = {
        "path": "models/decoder.gguf",
        "bytes": len(decoder),
        "sha256": _sha(decoder),
    }
    mmproj_entry = {
        "path": "models/mmproj.gguf",
        "bytes": len(mmproj),
        "sha256": _sha(mmproj),
    }
    generation = copy.deepcopy({**common, "gguf_files": [decoder_entry]})
    preprocess = copy.deepcopy({
        **common,
        "role": "preprocess",
        "gguf_files": [decoder_entry, mmproj_entry],
    })
    receipt_path = repo / "docs" / "receipts" / "preprocess.json"
    receipt_path.write_text(json.dumps(preprocess), encoding="utf-8")
    return repo, runtime, data, generation, preprocess, receipt_path


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_role_only_receipt_pair_is_accepted_and_identity_uses_preprocess_receipt(tmp_path):
    repo, runtime, data, generation, _preprocess, receipt_path = _world(tmp_path)
    result = verify_feature_encoder_runtime(
        repo_root=repo,
        data_root=data,
        runtime_root=runtime,
        values={"feature_encoder_runtime_receipt": "receipts/preprocess.json"},
        generation_receipt=generation,
        receipt_loader=_load,
    )
    assert result is not None
    assert result.receipt_path == receipt_path
    assert result.encoder_identity.runtime_receipt_sha256 == _sha(receipt_path.read_bytes())
    assert result.encoder_identity.build_commit == "a" * 40


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("build_commit", "build identities differ"),
        ("model_lock_key", "model identities differ"),
    ],
)
def test_foreign_encoder_identity_is_refused(tmp_path, field, message):
    repo, runtime, data, generation, preprocess, receipt_path = _world(tmp_path)
    if field == "build_commit":
        preprocess["llama_cpp"]["build_commit"] = "b" * 40
    else:
        preprocess[field] = "foreign"
    receipt_path.write_text(json.dumps(preprocess), encoding="utf-8")
    with pytest.raises(PreparationError, match=message):
        verify_feature_encoder_runtime(
            repo_root=repo,
            data_root=data,
            runtime_root=runtime,
            values={"feature_encoder_runtime_receipt": "receipts/preprocess.json"},
            generation_receipt=generation,
            receipt_loader=_load,
        )


def test_generation_mmproj_mismatch_is_refused_when_both_are_truthfully_pinned(tmp_path):
    repo, runtime, data, generation, _preprocess, receipt_path = _world(tmp_path)
    other = b"generation-mmproj"
    other_path = data / "models" / "generation-mmproj.gguf"
    other_path.write_bytes(other)
    generation["gguf_files"].append(
        {
            "path": "models/generation-mmproj.gguf",
            "bytes": len(other),
            "sha256": _sha(other),
        }
    )
    receipt_path.write_text(receipt_path.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(PreparationError, match="mmproj identities differ"):
        verify_feature_encoder_runtime(
            repo_root=repo,
            data_root=data,
            runtime_root=runtime,
            values={"feature_encoder_runtime_receipt": "receipts/preprocess.json"},
            generation_receipt=generation,
            receipt_loader=_load,
        )


@pytest.mark.parametrize("change", ["binary", "library", "decoder"])
def test_foreign_file_identity_is_refused(tmp_path, change):
    repo, runtime, data, generation, preprocess, receipt_path = _world(tmp_path)
    if change == "binary":
        preprocess["llama_cpp"]["binary_sha256"] = "b" * 64
    elif change == "library":
        preprocess["runtime_libraries"][0]["sha256"] = "b" * 64
    else:
        preprocess["gguf_files"][0]["sha256"] = "b" * 64
    receipt_path.write_text(json.dumps(preprocess), encoding="utf-8")
    with pytest.raises(PreparationError):
        verify_feature_encoder_runtime(
            repo_root=repo,
            data_root=data,
            runtime_root=runtime,
            values={"feature_encoder_runtime_receipt": "receipts/preprocess.json"},
            generation_receipt=generation,
            receipt_loader=_load,
        )


def test_missing_or_wrong_role_refuses(tmp_path):
    repo, runtime, data, generation, preprocess, receipt_path = _world(tmp_path)
    receipt_path.unlink()
    with pytest.raises(PreparationError):
        verify_feature_encoder_runtime(
            repo_root=repo,
            data_root=data,
            runtime_root=runtime,
            values={"feature_encoder_runtime_receipt": "receipts/preprocess.json"},
            generation_receipt=generation,
            receipt_loader=_load,
        )
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    preprocess["role"] = "inference"
    receipt_path.write_text(json.dumps(preprocess), encoding="utf-8")
    with pytest.raises(PreparationError, match="role preprocess"):
        verify_feature_encoder_runtime(
            repo_root=repo,
            data_root=data,
            runtime_root=runtime,
            values={"feature_encoder_runtime_receipt": "receipts/preprocess.json"},
            generation_receipt=generation,
            receipt_loader=_load,
        )


def test_absent_override_preserves_legacy_identity_path(tmp_path):
    repo, runtime, data, generation, _preprocess, _receipt_path = _world(tmp_path)
    assert verify_feature_encoder_runtime(
        repo_root=repo,
        data_root=data,
        runtime_root=runtime,
        values={},
        generation_receipt=generation,
        receipt_loader=_load,
    ) is None
