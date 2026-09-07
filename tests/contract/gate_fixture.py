"""Shared GateFixture: a fully valid receipt/lock/file world that tests then tamper."""

import hashlib
import json
from pathlib import Path

from speech_aware_evidence_acquisition.contracts import (
    E0_RECEIPT_SCHEMA,
    MODEL_LOCK_KEY,
    RUNTIME_RECEIPT_SCHEMA,
    STUDY_SLUG,
    ExecutionPlan,
    FrozenCoreGate,
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class GateFixture:
    """A fully valid receipt/lock/file world in tmp_path that each test then tampers."""

    SUBDIR = f"models/{MODEL_LOCK_KEY}"
    GGUF_1 = b"GGUF-fake-model-shard-one" * 64
    GGUF_2 = b"GGUF-fake-mmproj" * 32
    BINARY = b"ELF-fake-llama-server" * 16
    LIBRARY = b"ELF-fake-libllama-impl" * 32
    ARTIFACT = b'{"receipt": "closed"}\n'
    SCORING_SOURCE = b"def score():\n    return 0\n"
    SCORING_REL = "src/speech_aware_evidence_acquisition/scoring/wer.py"
    RUN_ID = "SAEA-E-000-smoke"
    CARRIER = "earnings21-original"

    def __init__(self, tmp_path: Path) -> None:
        self.receipts = tmp_path / "receipts"
        self.data_root = tmp_path / "data"
        self.runtime_root = tmp_path / "runtime"
        self.source_root = tmp_path
        self.lock_path = tmp_path / "datasets.lock.json"
        model_dir = self.data_root / self.SUBDIR
        model_dir.mkdir(parents=True)
        (model_dir / "model-q8_0.gguf").write_bytes(self.GGUF_1)
        (model_dir / "mmproj-bf16.gguf").write_bytes(self.GGUF_2)
        binary = self.runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(self.BINARY)
        (binary.parent / "libfake-impl.so").write_bytes(self.LIBRARY)

        configs_dir = tmp_path / "configs" / "experiment"
        configs_dir.mkdir(parents=True)
        (configs_dir / "e0-model-free-closure.yaml").write_text(
            "excluded_lock_keys:\n"
            "  - fsd50k\n"
            "  - audioset-metadata-features\n"
            "  - esc-50\n",
            encoding="utf-8",
        )

        self.scoring_dir = tmp_path / "src" / "speech_aware_evidence_acquisition" / "scoring"
        self.scoring_dir.mkdir(parents=True)
        (self.scoring_dir / "wer.py").write_bytes(self.SCORING_SOURCE)
        self.d3_artifact = json.dumps(
            {"frozen_sources_sha256": {self.SCORING_REL: _sha(self.SCORING_SOURCE)}}
        ).encode("utf-8")

        (self.receipts / "e0").mkdir(parents=True)
        self.deliverables = {}
        for name in FrozenCoreGate.E0_DELIVERABLES:
            content = self.d3_artifact if name == "d3_scoring" else self.ARTIFACT
            artifact = self.receipts / "e0" / f"{name}.json"
            artifact.write_bytes(content)
            self.deliverables[name] = {
                "status": "CLOSED",
                "artifact": f"e0/{name}.json",
                "sha256": _sha(content),
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
            ],
            "datasets": [
                {
                    "name": self.CARRIER,
                    "kind": "dataset",
                    "profiles": ["speech-aware-core"],
                }
            ],
        }
        self.exposure_ledger = tmp_path / "exposure-ledger.md"
        self.write_ledger_rows(
            f"| 2026-08-04 | {self.RUN_ID} | baseline-reproduction | earnings21 dev slice "
            f"| qwen3-omni | {self.CARRIER} dev | dev | {'a' * 64} | no "
            "| 10 | 600 | 1.0 | W1 probes on other carriers only | mlflow://pending "
            "| pre-registered |\n"
        )
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
                "reported_build": "version: 9999 (ddddddd)",
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
            "runtime_libraries": [
                {
                    "path": "llama.cpp/build/bin/libfake-impl.so",
                    "bytes": len(self.LIBRARY),
                    "sha256": _sha(self.LIBRARY),
                }
            ],
        }

    def write_ledger_rows(self, rows: str) -> None:
        self.exposure_ledger.write_text(
            "| date | run/experiment id | execution profile | scope | model/tool "
            "| speech carrier + split | split role | split identity hash | consumed "
            "| calls | speech audio seconds | gpu hours | inherited exposure "
            "| artifacts | notes |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n" + rows,
            encoding="utf-8",
        )

    def gate(self, **overrides: object) -> FrozenCoreGate:
        """The fixture's gate. ``overrides`` set any additional ``FrozenCoreGate``
        field (e.g. a ``d1_media_supplement`` / ``d1_evidence_supplement`` pair);
        every caller that passes none is byte-identical to before this argument
        existed."""

        (self.receipts / "e0-closure.json").write_text(json.dumps(self.e0), encoding="utf-8")
        (self.receipts / "runtime.json").write_text(json.dumps(self.runtime), encoding="utf-8")
        self.lock_path.write_text(json.dumps(self.lock), encoding="utf-8")
        fields: dict = dict(
            e0_receipt=self.receipts / "e0-closure.json",
            runtime_receipt=self.receipts / "runtime.json",
            data_root=self.data_root,
            lock_path=self.lock_path,
            runtime_root=self.runtime_root,
            exposure_ledger=self.exposure_ledger,
            source_root=self.source_root,
        )
        fields.update(overrides)
        return FrozenCoreGate(**fields)

    def plan(self, **overrides: object) -> ExecutionPlan:
        base: dict = dict(
            run_id=self.RUN_ID,
            execution_profile="baseline-reproduction",
            carrier_lock_key=self.CARRIER,
            split_role="dev",
            split_identity_hash="a" * 64,
            planned_model_calls=10,
            planned_gpu_hours=1.0,
            planned_speech_audio_seconds=600,
            protocol_hash="b" * 64,
            attempt_id="attempt-0001",
        )
        base.update(overrides)
        return ExecutionPlan(**base)
