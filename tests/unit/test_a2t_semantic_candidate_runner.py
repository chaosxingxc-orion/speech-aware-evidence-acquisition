from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-03-a2t-semantic-candidate-audit"
    / "run_audit.py"
)


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "a2t_semantic_candidate_runner", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row() -> A2tKbRow:
    return A2tKbRow(
        unit_id="tier1_direct:000001",
        tier="tier1_direct",
        query_idx=1,
        text="warm the cabin",
        domain="private",
        category="private",
        tool_id=1,
        tool_name="setTemperature",
        arg_signature=(),
        arg_pairs=(),
        call_render="PRIVATE",
        extra_call_names=(),
        call_count=1,
        sample_ids=("private",),
        item_ids=(1,),
        media_relpath_by_sample_id={},
        speaker_ids=("private",),
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path, tuple[A2tKbRow, ...]]:
    repo = tmp_path / "repo"
    root = tmp_path / "data"
    artifact = root / "knowledge" / "audio2tool" / "fixture" / "size-full"
    receipt_path = repo / "docs" / "receipts" / "knowledge"
    artifact.mkdir(parents=True)
    receipt_path.mkdir(parents=True)
    row = _row()
    text_hash = hashlib.sha256(row.text.encode("utf-8")).hexdigest()
    snapshot = {
        "facets": [
            {
                "dimension": "content",
                "facet_id": f"facet:content:{row.unit_id}",
                "representation": row.text,
            }
        ],
        "source_split_identity_hash": "construction-hash",
    }
    snapshot_path = artifact / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    vectors_path = artifact / "vectors-content-facets.npz"
    np.savez_compressed(
        vectors_path,
        vectors=np.asarray([[0.6, 0.8]], dtype=np.float32),
        ids=np.asarray([f"facet:content:{row.unit_id}"]),
        text_sha256=np.asarray([text_hash]),
    )
    receipt = {
        "schema": "saea-kb-text-embeddings-receipt-v1",
        "exposure_ledger_row": "FIXTURE-ROW",
        "embedder": {
            "role": "pinned TOOL-level embedder",
            "dims": 2,
            "gguf_sha256": "model-hash",
            "build_commit": "build-commit",
        },
        "snapshot": {
            "artifact_relpath": "knowledge/audio2tool/fixture/size-full/snapshot.json",
            "file_sha256": _sha256(snapshot_path),
            "source_split_identity_hash": "construction-hash",
        },
        "vectors": {
            "content_facets": {
                "file": vectors_path.name,
                "sha256": _sha256(vectors_path),
                "count": 1,
                "dims": 2,
            }
        },
    }
    (receipt_path / "a2t-kb-size-full-embeddings.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )
    return repo, root, (row,)


def test_verified_loader_binds_receipt_snapshot_text_hashes_and_vectors(
    tmp_path: Path,
) -> None:
    runner = _load_runner()
    repo, root, rows = _fixture(tmp_path)

    vectors, provenance = runner._load_verified_unit_vectors(
        repo=repo,
        root=root,
        construction_rows=rows,
    )

    assert tuple(vectors) == ("tier1_direct:000001",)
    assert np.allclose(vectors["tier1_direct:000001"], [0.6, 0.8])
    assert provenance["all_unit_ids_match"] is True
    assert provenance["all_representations_match_construction_text"] is True
    assert provenance["all_text_hashes_match"] is True
    assert provenance["vector_dimension"] == 2
    assert provenance["vector_values_emitted"] is False


def test_verified_loader_refuses_tampered_vector_artifact(tmp_path: Path) -> None:
    runner = _load_runner()
    repo, root, rows = _fixture(tmp_path)
    vector_path = (
        root
        / "knowledge"
        / "audio2tool"
        / "fixture"
        / "size-full"
        / "vectors-content-facets.npz"
    )
    vector_path.write_bytes(vector_path.read_bytes() + b"tamper")

    with pytest.raises(RuntimeError, match="vector artifact SHA-256"):
        runner._load_verified_unit_vectors(
            repo=repo,
            root=root,
            construction_rows=rows,
        )
