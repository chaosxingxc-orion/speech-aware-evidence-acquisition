"""Tests for the construction-only G5 family-contract build entry point."""

from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "build_a2t_g5_family_contracts.py"
CORPUS = (
    REPO
    / "knowledge"
    / "audio2tool"
    / "g5-exhaustive-family-contracts-v1"
    / "corpus.json"
)
RECEIPT = (
    REPO
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-02-a2t-g5-family-contract-build-v1"
    / "build-receipt.json"
)


def _builder():
    spec = importlib.util.spec_from_file_location("build_a2t_g5_family_contracts", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_writes_only_the_explicit_corpus_and_receipt(monkeypatch, tmp_path: Path) -> None:
    builder = _builder()
    corpus_path = tmp_path / "corpus.json"
    receipt_path = tmp_path / "receipt.json"
    receipt = {"schema": "receipt", "contacts": {"model": 0, "network": 0}}
    monkeypatch.setattr(builder, "run_build", lambda _root: ("{}\n", receipt))
    monkeypatch.setattr(builder, "data_root", lambda: Path("/construction-only"))

    assert builder.main(
        ["--corpus-output", str(corpus_path), "--receipt-output", str(receipt_path)]
    ) == 0
    assert corpus_path.read_text(encoding="utf-8") == "{}\n"
    assert json.loads(receipt_path.read_text(encoding="utf-8")) == receipt


def test_run_build_records_model_free_qualification(monkeypatch) -> None:
    builder = _builder()
    corpus = SimpleNamespace(
        to_json=lambda: '{"schema":"test"}\n',
        sha256="a" * 64,
        families=(SimpleNamespace(tag="family", bundle_utf8_bytes=123),),
        contracts=(SimpleNamespace(tool_name="tool"),),
        report={"syntax_incompatible_skeleton_count": 0},
    )
    qualification = SimpleNamespace(
        passed=True,
        metrics={"complete_gold_tool_set_recall": 1.0},
        gates={"complete_gold_tool_set_recall_at_least_90_percent": True},
        as_json=lambda: {
            "passed": True,
            "metrics": {"complete_gold_tool_set_recall": 1.0},
            "gates": {"complete_gold_tool_set_recall_at_least_90_percent": True},
        },
    )
    rows = (SimpleNamespace(query_idx=1, unit_id="unit", sample_ids=("sample",)),)
    validation_rows = (
        SimpleNamespace(query_idx=2, unit_id="validation", sample_ids=("validation",)),
    )
    partition = SimpleNamespace(
        construction=rows,
        eval_sample_ids=("held-out-evaluation",),
        split_identity_hash=lambda: builder.PROPOSED_EVAL_IDENTITY,
        policy_id="partition-policy",
        seed=builder.PARTITION_SEED,
    )
    monkeypatch.setattr(builder, "require_clean_study_repo", lambda _repo: "commit")
    monkeypatch.setattr(builder, "arm_offline_guard", lambda: SimpleNamespace(count=0))
    monkeypatch.setattr(
        builder,
        "_sha256_file",
        lambda path: (
            builder.PARTITION_PROPOSAL_SHA256
            if path == builder.PARTITION_PROPOSAL
            else builder.REGISTRY_SHA256
            if path.name == "tools_registry.csv"
            else "b" * 64
        ),
    )
    monkeypatch.setattr(builder, "load_lock", lambda _path: object())
    monkeypatch.setattr(builder, "umbrella_lock_path", lambda _repo: Path("lock"))
    monkeypatch.setattr(builder, "asset_dir", lambda _lock, _name, root: root)
    monkeypatch.setattr(builder, "load_tool_registry", lambda _lock, _root: ({"tool_name": "tool"},))
    monkeypatch.setattr(builder, "a2t_pool_rows", lambda _lock, _root: (rows, {"pool_units": 1}))
    monkeypatch.setattr(builder, "exposed_sample_ids", lambda _repo: frozenset())
    monkeypatch.setattr(builder, "propose_partition", lambda *_args, **_kwargs: partition)
    monkeypatch.setattr(
        builder,
        "split_construction_validation",
        lambda _rows, seed: (rows, validation_rows),
    )
    monkeypatch.setattr(builder, "build_action_family_corpus", lambda *_args: corpus)
    monkeypatch.setattr(builder, "qualify_action_family_corpus", lambda *_args, **_kwargs: qualification)

    text, receipt = builder.run_build(Path("data"))

    assert text == '{"schema":"test"}\n'
    assert receipt["execution_profile"] == "model-free-check"
    assert receipt["qualification"]["passed"] is True
    assert set(receipt["contacts"].values()) == {0}
    assert receipt["scope"]["evaluation_rows_consumed"] == 0


def test_committed_corpus_and_receipt_preserve_all_fixed_gates() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    corpus_bytes = CORPUS.read_bytes()

    assert receipt["execution_profile"] == "model-free-check"
    assert receipt["corpus"]["sha256"] == hashlib.sha256(corpus_bytes).hexdigest()
    assert receipt["corpus"]["family_count"] > 1
    assert receipt["corpus"]["contract_count"] == 152
    assert receipt["corpus"]["maximum_family_bundle_ascii_bytes"] <= 18_432
    assert receipt["corpus"]["sha256"] == receipt["corpus"][
        "reverse_order_build_sha256"
    ]
    assert receipt["qualification"]["passed"] is True
    assert all(receipt["qualification"]["gates"].values())
    assert set(receipt["contacts"].values()) == {0}
    assert receipt["offline_guard"]["outbound_connection_attempts"] == 0
    assert set(receipt["scope"].values()) == {0, False}
