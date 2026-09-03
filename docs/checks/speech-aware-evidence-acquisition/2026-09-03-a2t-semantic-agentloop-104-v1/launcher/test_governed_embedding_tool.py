"""Contact-free tests for the governed local semantic embedding wrapper."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan


MODULE = Path(__file__).with_name("governed_embedding_tool.py")


def _module():
    name = "test_governed_semantic_embedding_tool"
    spec = importlib.util.spec_from_file_location(name, MODULE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _Gate:
    def __init__(self) -> None:
        self.plans = []

    def assert_model_touch_allowed(self, plan):
        self.plans.append(plan)
        return "a" * 64


class _EmbeddingClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.http_request_count = 0
        self.closed = False
        self.batches = []
        self.fail = fail

    def embed_text_batch(self, items):
        self.batches.append(tuple(items))
        self.http_request_count += 1
        if self.fail:
            raise RuntimeError("synthetic embedding failure")
        return tuple(
            type(
                "Vector",
                (),
                {"contact_id": item[0], "kind": "text", "values": (0.25, float(index + 1))},
            )()
            for index, item in enumerate(items)
        )

    def close(self) -> None:
        self.closed = True


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        run_id="SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1-EMBED",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash="b" * 64,
        planned_model_calls=208,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1,
        protocol_hash="c" * 64,
        attempt_id="semantic-embedding-tool-once",
    ).validate()


def _items(offset: int, count: int):
    return tuple(
        (f"semantic:item:{offset + index:03d}", f"English text {offset + index}.")
        for index in range(count)
    )


def _wrapper(module, tmp_path: Path, *, client=None, preregistration: bytes = b"English preregistration\n"):
    preregistration_path = tmp_path / "preregistration.md"
    preregistration_path.write_bytes(preregistration)
    return module.GovernedEmbeddingClient(
        client=client or _EmbeddingClient(),
        gate=_Gate(),
        plan=_plan(),
        preregistration_path=preregistration_path,
        preregistration_sha256=hashlib.sha256(preregistration).hexdigest(),
        attempts_root=tmp_path / "attempts",
        receipt_path=tmp_path / "embedding-tool-receipt.json",
    )


def test_transparently_wraps_seven_physical_batches_and_finalizes_a_hash_only_receipt(tmp_path: Path) -> None:
    module = _module()
    client = _EmbeddingClient()
    wrapper = _wrapper(module, tmp_path, client=client)

    observed = []
    for batch_index, count in enumerate((32, 32, 32, 32, 32, 32, 16)):
        vectors = wrapper.embed_text_batch(_items(batch_index * 32, count))
        observed.extend(vectors)

    receipt = wrapper.close()

    assert len(observed) == 208
    assert client.http_request_count == 7
    assert client.closed is True
    assert wrapper.physical_request_count == 7
    assert wrapper.logical_contact_count == 208
    assert receipt["status"] == "FINALIZED"
    assert receipt["physical_request_count"] == 7
    assert receipt["logical_contact_count"] == 208
    assert receipt["pinned_runtime_receipt_relpath"] == "docs/receipts/runtime-qwen3-embedding-q8.json"
    assert len(receipt["batches"]) == 7
    assert set(receipt["batches"][0]) == {
        "logical_contact_count",
        "logical_contact_ids_sha256",
        "physical_ordinal",
        "request_body_sha256",
        "response_vectors_sha256",
    }
    raw = (tmp_path / "embedding-tool-receipt.json").read_text(encoding="utf-8")
    assert "English text" not in raw
    assert "0.25" not in raw
    assert wrapper.gate.plans == [_plan()]
    attempt = json.loads(
        (
            tmp_path / "attempts" / _plan().run_id / f"{_plan().attempt_id}.json"
        ).read_text(encoding="utf-8")
    )
    assert attempt["actual"] == {"audio_seconds": 0.0, "calls": 208}


def test_preregistration_drift_refuses_before_the_first_embedding_request(tmp_path: Path) -> None:
    module = _module()
    client = _EmbeddingClient()
    wrapper = _wrapper(module, tmp_path, client=client)
    (tmp_path / "preregistration.md").write_text("changed\n", encoding="utf-8")

    with pytest.raises(module.GovernedEmbeddingError, match="preregistration SHA-256 drift"):
        wrapper.embed_text_batch(_items(0, 32))

    assert client.http_request_count == 0
    assert not (tmp_path / "attempts" / _plan().run_id / f"{_plan().attempt_id}.json").exists()


def test_plan_counts_logical_contacts_and_the_gate_pins_the_embedding_receipt(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    calls = []

    class _GateFactory:
        @staticmethod
        def for_study_repo(*args, **kwargs):
            calls.append((args, kwargs))
            return object()

    monkeypatch.setattr(module, "FrozenCoreGate", _GateFactory)
    monkeypatch.setattr(module, "d1_media_supplement_relpath", lambda _values: "receipts/artifacts/d1-a2t-semantic-agentloop-104.json")
    monkeypatch.setattr(module, "d1_media_supplement_sha256", lambda _values: "d" * 64)
    assert module.build_embedding_gate(
        repo_root=tmp_path / "repo",
        data_root=tmp_path / "data",
        runtime_root=tmp_path / "runtime",
        model_root=tmp_path / "models",
        composed_values={},
    ) is not None
    assert calls[0][1]["runtime_receipt_relpath"] == "receipts/runtime-qwen3-embedding-q8.json"
    assert calls[0][1]["expected_model_lock_key"] == "qwen3-embedding-0.6b-gguf"
    assert calls[0][1]["d1_media_supplement_sha256"] == "d" * 64

    invalid = ExecutionPlan(
        **{**_plan().__dict__, "planned_model_calls": 7}
    ).validate()
    preregistration = tmp_path / "preregistration.md"
    preregistration.write_text("English\n", encoding="utf-8")
    with pytest.raises(module.GovernedEmbeddingError, match="208 logical contacts"):
        module.GovernedEmbeddingClient(
            client=_EmbeddingClient(),
            gate=_Gate(),
            plan=invalid,
            preregistration_path=preregistration,
            preregistration_sha256=hashlib.sha256(preregistration.read_bytes()).hexdigest(),
            attempts_root=tmp_path / "attempts",
            receipt_path=tmp_path / "receipt.json",
        )


def test_eighth_batch_is_refused_without_a_retry_or_a_network_send(tmp_path: Path) -> None:
    module = _module()
    client = _EmbeddingClient()
    wrapper = _wrapper(module, tmp_path, client=client)

    for batch_index in range(7):
        wrapper.embed_text_batch(_items(batch_index, 1))
    with pytest.raises(module.GovernedEmbeddingError, match="physical request budget"):
        wrapper.embed_text_batch(_items(99, 1))

    assert client.http_request_count == 7
    aborted = wrapper.abort("test close after expected refusal")
    assert aborted["status"] == "ABORTED"


def test_failed_underlying_batch_is_terminal_and_records_only_hash_metadata(tmp_path: Path) -> None:
    module = _module()
    client = _EmbeddingClient(fail=True)
    wrapper = _wrapper(module, tmp_path, client=client)

    with pytest.raises(RuntimeError, match="synthetic embedding failure"):
        wrapper.embed_text_batch(_items(0, 2))

    receipt = json.loads((tmp_path / "embedding-tool-receipt.json").read_text(encoding="utf-8"))
    assert receipt["status"] == "ABORTED"
    assert receipt["physical_request_count"] == 1
    assert receipt["logical_contact_count"] == 2
    assert receipt["batches"][0]["request_body_sha256"]
    assert "English text" not in json.dumps(receipt)
    with pytest.raises(module.GovernedEmbeddingError, match="terminal"):
        wrapper.embed_text_batch(_items(2, 1))
