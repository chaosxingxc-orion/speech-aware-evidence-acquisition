"""Contract 5: exposure-claim schema validates; the model entry gate refuses without receipts."""

import json
from pathlib import Path

import pytest

import hashlib

from speech_aware_evidence_acquisition.contracts import (
    E0_RECEIPT_SCHEMA,
    MODEL_LOCK_KEY,
    RUNTIME_RECEIPT_SCHEMA,
    STUDY_SLUG,
    ExposureSchemaError,
    FrozenCoreGate,
    GateClosed,
    validate_exposure_claim,
)


REPO_ROOT = Path(__file__).resolve().parents[2]

VALID_CLAIM = {
    "scope": "earnings21-original dev slice, D0 acquisition only",
    "date": "2026-08-03",
    "counts": {"model_calls": 0, "speech_audio_seconds": 0},
    "inherited": "W1 probe campaigns on other carriers; zero model exposure on the three carriers",
}


def test_valid_exposure_claim_passes():
    validate_exposure_claim(VALID_CLAIM)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda claim: claim.pop("scope"),
        lambda claim: claim.pop("inherited"),
        lambda claim: claim.update(date="03/08/2026"),
        lambda claim: claim.update(counts={}),
        lambda claim: claim.update(counts={"model_calls": -1}),
        lambda claim: claim.update(extra_field=1),
    ],
)
def test_malformed_exposure_claims_fail(mutation):
    claim = {key: (dict(value) if isinstance(value, dict) else value) for key, value in VALID_CLAIM.items()}
    mutation(claim)
    with pytest.raises(ExposureSchemaError):
        validate_exposure_claim(claim)


def test_exposure_ledger_file_exists_with_required_columns():
    ledger = (REPO_ROOT / "docs" / "exposure-ledger.md").read_text(encoding="utf-8")
    for column in (
        "date",
        "run/experiment id",
        "model/tool",
        "calls",
        "speech audio seconds",
    ):
        assert column in ledger


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class GateFixture:
    """A fully valid receipt/lock/file world in tmp_path that each test then tampers."""

    SUBDIR = f"models/{MODEL_LOCK_KEY}"
    GGUF_1 = b"GGUF-fake-model-shard-one" * 64
    GGUF_2 = b"GGUF-fake-mmproj" * 32
    BINARY = b"ELF-fake-llama-server" * 16
    ARTIFACT = b'{"receipt": "closed"}\n'

    def __init__(self, tmp_path: Path) -> None:
        self.receipts = tmp_path / "receipts"
        self.data_root = tmp_path / "data"
        self.runtime_root = tmp_path / "runtime"
        self.lock_path = tmp_path / "datasets.lock.json"
        model_dir = self.data_root / self.SUBDIR
        model_dir.mkdir(parents=True)
        (model_dir / "model-q8_0.gguf").write_bytes(self.GGUF_1)
        (model_dir / "mmproj-bf16.gguf").write_bytes(self.GGUF_2)
        binary = self.runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(self.BINARY)
        (self.receipts / "e0").mkdir(parents=True)
        self.deliverables = {}
        for name in FrozenCoreGate.E0_DELIVERABLES:
            artifact = self.receipts / "e0" / f"{name}.json"
            artifact.write_bytes(self.ARTIFACT)
            self.deliverables[name] = {
                "status": "CLOSED",
                "artifact": f"e0/{name}.json",
                "sha256": _sha(self.ARTIFACT),
            }
        self.lock = {
            "models": [
                {
                    "name": MODEL_LOCK_KEY,
                    "local_subdir": self.SUBDIR,
                    "files": 2,
                    "size_bytes": len(self.GGUF_1) + len(self.GGUF_2),
                    "note": "extra lock fields are tolerated",
                }
            ]
        }
        self.e0 = {
            "schema": E0_RECEIPT_SCHEMA,
            "study": STUDY_SLUG,
            "deliverables": self.deliverables,
        }
        self.runtime = {
            "schema": RUNTIME_RECEIPT_SCHEMA,
            "study": STUDY_SLUG,
            "model_lock_key": MODEL_LOCK_KEY,
            "llama_cpp": {
                "build_commit": "d" * 40,
                "binary_path": "llama.cpp/build/bin/llama-server",
                "binary_bytes": len(self.BINARY),
                "binary_sha256": _sha(self.BINARY),
            },
            "gguf_files": [
                {
                    "path": f"{self.SUBDIR}/model-q8_0.gguf",
                    "bytes": len(self.GGUF_1),
                    "sha256": _sha(self.GGUF_1),
                },
                {
                    "path": f"{self.SUBDIR}/mmproj-bf16.gguf",
                    "bytes": len(self.GGUF_2),
                    "sha256": _sha(self.GGUF_2),
                },
            ],
        }

    def gate(self) -> FrozenCoreGate:
        (self.receipts / "e0-closure.json").write_text(json.dumps(self.e0), encoding="utf-8")
        (self.receipts / "runtime.json").write_text(json.dumps(self.runtime), encoding="utf-8")
        self.lock_path.write_text(json.dumps(self.lock), encoding="utf-8")
        return FrozenCoreGate(
            e0_receipt=self.receipts / "e0-closure.json",
            runtime_receipt=self.receipts / "runtime.json",
            data_root=self.data_root,
            lock_path=self.lock_path,
            runtime_root=self.runtime_root,
        )


@pytest.fixture()
def world(tmp_path):
    return GateFixture(tmp_path)


def test_fully_valid_receipts_open_the_gate(world):
    world.gate().assert_model_touch_allowed()


def test_gate_refuses_when_receipts_are_missing(tmp_path, world):
    gate = FrozenCoreGate(
        tmp_path / "absent-e0.json",
        tmp_path / "absent-runtime.json",
        world.data_root,
        world.lock_path,
        world.runtime_root,
    )
    world.lock_path.write_text(json.dumps(world.lock), encoding="utf-8")
    with pytest.raises(GateClosed, match="missing or unreadable"):
        gate.assert_model_touch_allowed()


def test_gate_refuses_nonexistent_model_file(world):
    world.runtime["gguf_files"][1]["path"] = f"{world.SUBDIR}/definitely-does-not-exist.gguf"
    with pytest.raises(GateClosed, match="does not exist"):
        world.gate().assert_model_touch_allowed()


def test_gate_refuses_fabricated_hash_and_size(world):
    world.runtime["gguf_files"][0]["sha256"] = "0" * 64
    with pytest.raises(GateClosed, match="SHA-256 drift"):
        world.gate().assert_model_touch_allowed()

    world.runtime["gguf_files"][0]["sha256"] = _sha(world.GGUF_1)
    world.runtime["gguf_files"][0]["bytes"] = 12345
    with pytest.raises(GateClosed, match="size drift"):
        world.gate().assert_model_touch_allowed()


def test_gate_refuses_model_byte_drift_on_disk(world):
    (world.data_root / world.SUBDIR / "model-q8_0.gguf").write_bytes(b"tampered")
    with pytest.raises(GateClosed, match="drift"):
        world.gate().assert_model_touch_allowed()


@pytest.mark.parametrize(
    "bad_path",
    [
        "/definitely/does/not/exist/model.gguf",
        "C:/leak/model.gguf",
        "../outside.gguf",
        "models/../../escape.gguf",
    ],
)
def test_gate_refuses_absolute_and_traversal_paths(world, bad_path):
    world.runtime["gguf_files"][1]["path"] = bad_path
    with pytest.raises(GateClosed):
        world.gate().assert_model_touch_allowed()


def test_gate_refuses_duplicate_and_extra_model_files(world):
    world.runtime["gguf_files"][1] = dict(world.runtime["gguf_files"][0])
    with pytest.raises(GateClosed, match="duplicates"):
        world.gate().assert_model_touch_allowed()

    world.runtime["gguf_files"] = [
        world.runtime["gguf_files"][0],
        {
            "path": f"{world.SUBDIR}/mmproj-bf16.gguf",
            "bytes": len(world.GGUF_2),
            "sha256": _sha(world.GGUF_2),
        },
        {
            "path": f"{world.SUBDIR}/model-q8_0.gguf",
            "bytes": len(world.GGUF_1),
            "sha256": _sha(world.GGUF_1),
        },
    ]
    with pytest.raises(GateClosed, match="extra or missing"):
        world.gate().assert_model_touch_allowed()


def test_gate_refuses_lock_key_mismatch_and_missing_lock_entry(world):
    world.runtime["model_lock_key"] = "some-other-model"
    with pytest.raises(GateClosed, match="does not match"):
        world.gate().assert_model_touch_allowed()

    world.runtime["model_lock_key"] = MODEL_LOCK_KEY
    world.lock["models"][0]["name"] = "renamed-away"
    with pytest.raises(GateClosed, match="not found in datasets lock"):
        world.gate().assert_model_touch_allowed()


def test_gate_refuses_path_outside_lock_subdir(world):
    stray = world.data_root / "models" / "other"
    stray.mkdir(parents=True)
    (stray / "model.gguf").write_bytes(world.GGUF_1)
    world.runtime["gguf_files"][0]["path"] = "models/other/model.gguf"
    with pytest.raises(GateClosed, match="canonical subdir"):
        world.gate().assert_model_touch_allowed()


def test_gate_refuses_unbacked_build_commit(world):
    world.runtime["llama_cpp"]["build_commit"] = "abc123"
    with pytest.raises(GateClosed, match="full 40-hex"):
        world.gate().assert_model_touch_allowed()

    world.runtime["llama_cpp"]["build_commit"] = "d" * 40
    world.runtime["llama_cpp"]["binary_sha256"] = "e" * 64
    with pytest.raises(GateClosed, match="binary drift"):
        world.gate().assert_model_touch_allowed()

    world.runtime["llama_cpp"]["binary_sha256"] = _sha(world.BINARY)
    world.runtime["llama_cpp"]["binary_path"] = "llama.cpp/missing/llama-server"
    with pytest.raises(GateClosed, match="does not exist"):
        world.gate().assert_model_touch_allowed()


def test_gate_refuses_e0_artifact_hash_drift(world):
    world.deliverables["d2_leakage"]["sha256"] = "f" * 64
    with pytest.raises(GateClosed, match="artifact hash drift"):
        world.gate().assert_model_touch_allowed()


def test_gate_refuses_open_deliverable_and_missing_artifact(world):
    world.deliverables["d3_scoring"]["status"] = "OPEN"
    with pytest.raises(GateClosed, match="d3_scoring"):
        world.gate().assert_model_touch_allowed()

    world.deliverables["d3_scoring"]["status"] = "CLOSED"
    (world.receipts / "e0" / "d4_trace.json").unlink()
    with pytest.raises(GateClosed, match="d4_trace"):
        world.gate().assert_model_touch_allowed()


def test_gate_refuses_schema_or_identity_mismatch(world):
    world.e0["schema"] = "some-other-schema"
    with pytest.raises(GateClosed, match="schema mismatch"):
        world.gate().assert_model_touch_allowed()

    world.e0["schema"] = E0_RECEIPT_SCHEMA
    world.runtime["study"] = "another-study"
    with pytest.raises(GateClosed, match="study identity mismatch"):
        world.gate().assert_model_touch_allowed()


def test_gate_refuses_lock_total_size_mismatch(world):
    world.lock["models"][0]["size_bytes"] += 1
    with pytest.raises(GateClosed, match="total"):
        world.gate().assert_model_touch_allowed()
