from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from speech_aware_evidence_acquisition.rails import a2t_frozen_semantic_assets as frozen


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    data_root = tmp_path / "data"
    rules_path = repo / "knowledge/audio2tool/runtime/compatibility-rules.json"
    centroid_path = data_root / "knowledge/audio2tool/runtime/centroids.npz"
    receipt_path = repo / "docs/receipts/knowledge/runtime.json"
    rules_path.parent.mkdir(parents=True)
    centroid_path.parent.mkdir(parents=True)
    receipt_path.parent.mkdir(parents=True)

    registry = tuple(f"tool{index:03d}" for index in range(152))
    centroid_names = (registry[0], registry[1])
    centroid_tiers = ("tier1_direct", "tier2_parametric")
    matrix = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float64)
    np.savez(
        centroid_path,
        centroid_tiers=np.asarray(centroid_tiers),
        centroid_tool_names=np.asarray(centroid_names),
        centroid_vectors=matrix,
        registry_tool_names=np.asarray(registry),
    )
    index_hash = frozen._semantic_index_hash(
        dimension=2,
        registry_names=registry,
        centroid_names=centroid_names,
        centroid_tiers=centroid_tiers,
        centroid_matrix=matrix,
    )
    monkeypatch.setattr(frozen, "EXPECTED_CENTROID_COUNT", 2)
    monkeypatch.setattr(frozen, "EXPECTED_DIMENSION", 2)
    monkeypatch.setattr(frozen, "SEMANTIC_INDEX_SHA256", index_hash)

    rule_payload = [
        {
            "construction_support_count": 2,
            "legal_argument_key_set": ["value"],
            "tool_name": registry[index],
            "value_forms": [["value", "string"]],
        }
        for index in range(43)
    ]
    rules_path.write_text(
        json.dumps(
            {
                "rules": rule_payload,
                "schema": "saea-a2t-aggregate-compatibility-rules-v1",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="ascii",
    )
    canonical_payload = json.dumps(
        rule_payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    receipt = {
        "artifacts": {
            "centroids": {
                "bytes": centroid_path.stat().st_size,
                "count": 2,
                "dimension": 2,
                "dtype": "float64",
                "path": "knowledge/audio2tool/runtime/centroids.npz",
                "sha256": _sha256(centroid_path),
            },
            "compatibility_rules": {
                "bytes": rules_path.stat().st_size,
                "compatibility_payload_sha256": hashlib.sha256(
                    canonical_payload
                ).hexdigest(),
                "count": 43,
                "path": "knowledge/audio2tool/runtime/compatibility-rules.json",
                "sha256": _sha256(rules_path),
            },
        },
        "contacts": {
            "embedding_tool": 0,
            "frozen_core": 0,
            "network": 0,
            "scorer": 0,
            "tokenizer": 0,
        },
        "privacy_boundary": {
            "concrete_argument_values_emitted": 0,
            "evaluation_rows_consumed": 0,
            "reference_transcripts_emitted": 0,
            "sample_identifiers_emitted": 0,
            "source_utterances_emitted": 0,
        },
        "schema": "saea-a2t-frozen-semantic-runtime-assets-receipt-v1",
        "semantic_index_sha256": index_hash,
        "sources": {
            "construction_partition_identity_sha256": (
                frozen.CONSTRUCTION_PARTITION_IDENTITY_SHA256
            ),
            "construction_rows_sha256": frozen.CONSTRUCTION_ROWS_SHA256,
            "embedding_receipt_relpath": frozen.SOURCE_RECEIPT_RELPATH,
            "embedding_receipt_sha256": frozen.SOURCE_RECEIPT_SHA256,
            "embedding_vector_sha256": frozen.SOURCE_VECTOR_SHA256,
        },
    }
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="ascii",
    )
    return repo, data_root, Path("docs/receipts/knowledge/runtime.json")


def test_loader_builds_runtime_index_and_exact_rule_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, data_root, receipt = _write_fixture(tmp_path, monkeypatch)

    assets = frozen.load_frozen_semantic_runtime_assets(
        repo=repo,
        data_root=data_root,
        receipt_relpath=receipt,
    )

    assert assets.index.construction_rows == ()
    assert assets.index.index_sha256 == frozen.SEMANTIC_INDEX_SHA256
    assert assets.index.rank([1.0, 0.0], top_k=1).selected_tool_names == (
        "tool000",
    )
    assert len(assets.compatibility_rules) == 43
    assert assets.compatibility_rules[0].construction_support_count == 2


def test_loader_refuses_tampered_rule_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, data_root, receipt = _write_fixture(tmp_path, monkeypatch)
    rules_path = repo / "knowledge/audio2tool/runtime/compatibility-rules.json"
    rules_path.write_bytes(rules_path.read_bytes() + b" ")

    with pytest.raises(frozen.FrozenSemanticAssetError, match="SHA-256 drift"):
        frozen.load_frozen_semantic_runtime_assets(
            repo=repo,
            data_root=data_root,
            receipt_relpath=receipt,
        )


def test_loader_has_no_construction_or_gold_derivation_surface() -> None:
    source = inspect.getsource(frozen)
    forbidden = (
        "a2t_pool_rows",
        "expected_tool_calls_for_entry",
        "build_a2t_g4_semantic_cards",
    )
    assert all(symbol not in source for symbol in forbidden)
