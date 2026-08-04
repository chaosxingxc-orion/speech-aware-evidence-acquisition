"""E0 generators produce truthful artifacts and the real gate accepts what they bind."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import (
    MODEL_LOCK_KEY,
    ExecutionPlan,
    FrozenCoreGate,
    GateClosed,
)
from speech_aware_evidence_acquisition.e0.artifacts import (
    ARTIFACTS_SUBDIR,
    write_json_artifact,
)
from speech_aware_evidence_acquisition.e0.d1_identity import build_d1
from speech_aware_evidence_acquisition.e0.d2_leakage import build_d2, excluded_lock_keys
from speech_aware_evidence_acquisition.e0.d3_scoring import build_d3
from speech_aware_evidence_acquisition.e0.d4_trace import build_d4
from speech_aware_evidence_acquisition.e0.generate import _close
from speech_aware_evidence_acquisition.e0.runtime_receipt import (
    ArtifactError,
    build_runtime_receipt,
)

from conftest import E21_IDS, SUBSET10_IDS


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class TestD1:
    def test_closure_on_clean_world(self, synthetic_world):
        artifact = build_d1(synthetic_world.lock_path, synthetic_world.data_root)
        carriers = artifact["carriers"]
        assert carriers["earnings21-original"]["sample_count"] == len(E21_IDS)
        assert carriers["earnings22-original"]["sample_count"] == 12
        for report in carriers.values():
            for fact in report["cross_layer_relations"]:
                if fact["right"] == "subset10_media":
                    assert fact["relation"] == "right_subset_of_left"
                else:
                    assert fact["relation"] == "equal"
        assert "license_facts" in carriers["conec"]

    def test_layer_drift_refuses_closure(self, synthetic_world):
        (synthetic_world.conec / "earnings21" / "contexts" / "extra_call.txt").write_text(
            "ctx", encoding="utf-8"
        )
        with pytest.raises(Exception, match="invariant violated"):
            build_d1(synthetic_world.lock_path, synthetic_world.data_root)

    def test_lock_count_disagreement_refuses_closure(self, synthetic_world):
        lock = json.loads(synthetic_world.lock_path.read_text(encoding="utf-8"))
        lock["datasets"][0]["verification"]["main_audio_files"] = 99
        synthetic_world.lock_path.write_text(json.dumps(lock), encoding="utf-8")
        with pytest.raises(Exception, match="disagrees with the umbrella lock"):
            build_d1(synthetic_world.lock_path, synthetic_world.data_root)


class TestD2:
    def test_negative_controls_all_executed(self, synthetic_world):
        artifact = build_d2(synthetic_world.lock_path)
        boundary = artifact["negative_controls"]["boundary_injections"]
        assert boundary["executed"] == 12 * 3
        assert boundary["all_rejected"] is True
        assert artifact["negative_controls"]["trace_axis_smuggling"]["executed"] == 4
        exclusion = artifact["general_audio_exclusion"]
        assert set(exclusion["excluded_lock_keys"]) == set(excluded_lock_keys())
        assert not set(exclusion["excluded_lock_keys"]) & set(
            exclusion["configured_lock_keys"]
        )

    def test_excluded_keys_come_from_config_not_code(self):
        keys = excluded_lock_keys()
        assert len(keys) == 3
        source_root = (
            Path(__file__).resolve().parents[2] / "src" / "speech_aware_evidence_acquisition"
        )
        for source in source_root.rglob("*.py"):
            text = source.read_text(encoding="utf-8").lower()
            for key in keys:
                assert key.lower() not in text, f"{source.name} hard-codes {key}"


class TestD3:
    def test_golden_vectors_and_source_freeze(self):
        artifact = build_d3()
        assert artifact["golden_vectors"]["all_matched"] is True
        assert artifact["golden_vectors"]["executed"] >= 8
        for relpath, digest in artifact["frozen_sources_sha256"].items():
            assert len(digest) == 64, relpath


class TestD4:
    def test_ten_sample_receipt(self, synthetic_world):
        artifact = build_d4(synthetic_world.lock_path, synthetic_world.data_root)
        assert artifact["sample_count"] == 10
        assert [sample["sample_id"] for sample in artifact["samples"]] == sorted(SUBSET10_IDS)
        first = artifact["samples"][0]
        assert {record["channel"] for record in first["trace_records"]} == {
            "OBS",
            "ORG",
            "SUPPLY",
            "USE",
            "COST",
        }
        for record in first["trace_records"]:
            payload = json.loads(record["serialized"])
            assert record["content_sha256"] == _sha(record["serialized"].encode("utf-8"))
            assert payload["record_id"].startswith("SAEA-E0-D4/")
        assert artifact["validations"]["model_calls"] == 0
        assert first["provenance"]["media_sha256"]
        org = next(r for r in first["trace_records"] if r["channel"] == "ORG")
        assert json.loads(org["serialized"])["payload"]["org_context_files"] == 2


class TestCloseAndGate:
    """The generated closure receipt must satisfy the real FrozenCoreGate."""

    def _generated_receipts(self, synthetic_world, tmp_path) -> Path:
        receipts = tmp_path / "receipts"
        for name, builder in (
            ("d1-identity.json", lambda: build_d1(synthetic_world.lock_path, synthetic_world.data_root)),
            ("d2-leakage.json", lambda: build_d2(synthetic_world.lock_path)),
            ("d3-scoring.json", build_d3),
            ("d4-trace.json", lambda: build_d4(synthetic_world.lock_path, synthetic_world.data_root)),
        ):
            write_json_artifact(receipts / ARTIFACTS_SUBDIR / name, builder())
        _close(receipts)
        return receipts

    def _model_world(self, synthetic_world, tmp_path) -> tuple[Path, Path, dict]:
        data_root = synthetic_world.data_root
        model_dir = data_root / "models" / MODEL_LOCK_KEY
        model_dir.mkdir(parents=True)
        gguf = b"GGUF fake main model" * 8
        mmproj = b"GGUF fake mmproj" * 4
        (model_dir / "model.gguf").write_bytes(gguf)
        (model_dir / "mmproj.gguf").write_bytes(mmproj)
        lock = json.loads(synthetic_world.lock_path.read_text(encoding="utf-8"))
        lock["models"] = [
            {
                "name": MODEL_LOCK_KEY,
                "local_subdir": f"models/{MODEL_LOCK_KEY}",
                "files": 2,
                "size_bytes": len(gguf) + len(mmproj),
            }
        ]
        synthetic_world.lock_path.write_text(json.dumps(lock), encoding="utf-8")
        runtime_root = tmp_path / "runtime"
        binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"fake-llama-server")
        runtime = {
            "schema": "saea-runtime-receipt-v1",
            "study": "speech-aware-evidence-acquisition",
            "model_lock_key": MODEL_LOCK_KEY,
            "llama_cpp": {
                "build_commit": "a" * 40,
                "binary_path": "llama.cpp/build/bin/llama-server",
                "binary_bytes": binary.stat().st_size,
                "binary_sha256": _sha(b"fake-llama-server"),
            },
            "gguf_files": [
                {
                    "path": f"models/{MODEL_LOCK_KEY}/mmproj.gguf",
                    "bytes": len(mmproj),
                    "sha256": _sha(mmproj),
                },
                {
                    "path": f"models/{MODEL_LOCK_KEY}/model.gguf",
                    "bytes": len(gguf),
                    "sha256": _sha(gguf),
                },
            ],
        }
        return runtime_root, binary, runtime

    def test_generated_receipts_open_and_tampering_recloses(
        self, synthetic_world, tmp_path
    ):
        receipts = self._generated_receipts(synthetic_world, tmp_path)
        runtime_root, _, runtime = self._model_world(synthetic_world, tmp_path)
        (receipts / "runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
        ledger = tmp_path / "ledger.md"
        ledger.write_text(
            "| date | run/experiment id | execution profile | scope | model/tool "
            "| speech carrier + split | split role | split identity hash | consumed "
            "| calls | speech audio seconds | inherited exposure | artifacts | notes |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
            "| 2026-08-04 | RUN-1 | baseline-reproduction | s | m | c dev | dev "
            f"| {'a' * 64} | no | 1 | 1 | none | none | test |\n",
            encoding="utf-8",
        )
        gate = FrozenCoreGate(
            e0_receipt=receipts / "e0-closure.json",
            runtime_receipt=receipts / "runtime.json",
            data_root=synthetic_world.data_root,
            lock_path=synthetic_world.lock_path,
            runtime_root=runtime_root,
            exposure_ledger=ledger,
        )
        plan = ExecutionPlan(
            run_id="RUN-1",
            execution_profile="baseline-reproduction",
            carrier_lock_key="earnings21-original",
            split_role="dev",
            split_identity_hash="a" * 64,
            planned_model_calls=1,
            planned_gpu_hours=0.1,
            planned_speech_audio_seconds=60,
            protocol_hash="b" * 64,
        )
        gate.assert_model_touch_allowed(plan)

        artifact = receipts / ARTIFACTS_SUBDIR / "d4-trace.json"
        tampered = artifact.read_text(encoding="utf-8").replace(
            '"model_calls": 0', '"model_calls": 1'
        )
        artifact.write_text(tampered, encoding="utf-8")
        with pytest.raises(GateClosed, match="hash drift"):
            gate.assert_model_touch_allowed(plan)


@pytest.mark.skipif(shutil.which("git") is None, reason="git required")
class TestRuntimeReceiptGenerator:
    def _llama_checkout(self, tmp_path: Path) -> Path:
        runtime_root = tmp_path / "runtime"
        llama = runtime_root / "llama.cpp"
        binary = llama / "build" / "bin" / "llama-server"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"fake-llama-server-binary")
        subprocess.run(["git", "init", "-q", str(llama)], check=True)
        env_args = [
            "git",
            "-C",
            str(llama),
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "user.name=t",
            "commit",
            "--allow-empty",
            "-q",
            "-m",
            "build",
        ]
        subprocess.run(["git", "-C", str(llama), "add", "-A"], check=True)
        subprocess.run(env_args, check=True)
        return runtime_root

    def _with_models(self, synthetic_world) -> None:
        model_dir = synthetic_world.data_root / "models" / MODEL_LOCK_KEY
        model_dir.mkdir(parents=True)
        (model_dir / "model.gguf").write_bytes(b"gguf-one")
        (model_dir / "mmproj.gguf").write_bytes(b"gguf-two")
        lock = json.loads(synthetic_world.lock_path.read_text(encoding="utf-8"))
        lock["models"] = [
            {
                "name": MODEL_LOCK_KEY,
                "local_subdir": f"models/{MODEL_LOCK_KEY}",
                "files": 2,
                "size_bytes": 16,
            }
        ]
        synthetic_world.lock_path.write_text(json.dumps(lock), encoding="utf-8")

    def test_receipt_binds_commit_files_and_bytes(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        receipt = build_runtime_receipt(
            synthetic_world.lock_path, synthetic_world.data_root, runtime_root
        )
        assert len(receipt["llama_cpp"]["build_commit"]) == 40
        assert len(receipt["gguf_files"]) == 2
        assert sum(entry["bytes"] for entry in receipt["gguf_files"]) == 16

    def test_dirty_tree_refused(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        (runtime_root / "llama.cpp" / "uncommitted.txt").write_text("x", encoding="utf-8")
        with pytest.raises(ArtifactError, match="dirty"):
            build_runtime_receipt(
                synthetic_world.lock_path, synthetic_world.data_root, runtime_root
            )

    def test_wrong_file_count_refused(self, synthetic_world, tmp_path):
        runtime_root = self._llama_checkout(tmp_path)
        self._with_models(synthetic_world)
        stray = synthetic_world.data_root / "models" / MODEL_LOCK_KEY / "stray.gguf"
        stray.write_bytes(b"extra")
        with pytest.raises(ArtifactError, match="lock freezes"):
            build_runtime_receipt(
                synthetic_world.lock_path, synthetic_world.data_root, runtime_root
            )
