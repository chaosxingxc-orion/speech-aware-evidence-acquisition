"""Freeze label-free semantic routing assets for the Audio2Tool runtime.

This is a model-free construction step.  It reconstructs the admitted
construction partition, verifies the previously recorded embedding artifact,
and emits only aggregate tool-tier centroids and aggregate compatibility
rules.  Construction utterances, sample identities, and concrete argument
values are not copied into either runtime artifact.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence
import zipfile


REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_tool_registry,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.a2t_semantic_router import (  # noqa: E402
    ToolTierSemanticIndex,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)


PARTITION_SEED = 20260807
PARTITION_IDENTITY = "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
SOURCE_RECEIPT_RELPATH = Path(
    "docs/receipts/knowledge/a2t-kb-size-full-embeddings.json"
)
SOURCE_RECEIPT_SHA256 = (
    "571ab8179a426ea9a41383d8b44f6bb99986ba5bab7be36646aee1a812d8fb61"
)
SOURCE_VECTOR_SHA256 = (
    "00a7ebe9b8325ffc2c7b8e45ac4f0c8475b2d3e76994cc0f539f7b5ad5740f45"
)
CONSTRUCTION_ROWS_SHA256 = (
    "4d8e90b61c14bada2ad04308068b6033ba6e6721f29b84b7eb2c1c987bd1d141"
)
SEMANTIC_INDEX_SHA256 = (
    "40b275636675adda1d185a13d0ed76d07b18c90b0d7e164535486c7374448fdb"
)
EXPECTED_RULE_COUNT = 43
EXPECTED_CENTROID_COUNT = 1095
EXPECTED_DIMENSION = 1024


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _load_script(relative_path: str, module_name: str) -> object:
    path = REPO / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load required builder: {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _npy_bytes(array: object) -> bytes:
    import numpy as np

    stream = io.BytesIO()
    np.lib.format.write_array(
        stream,
        np.asarray(array),
        version=(1, 0),
        allow_pickle=False,
    )
    return stream.getvalue()


def _deterministic_npz(arrays: Mapping[str, object]) -> bytes:
    """Render a timestamp-free, uncompressed NPZ with stable member order."""

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(arrays):
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, _npy_bytes(arrays[name]))
    return stream.getvalue()


def _rule_payload(rule: object) -> dict[str, object]:
    return {
        "construction_support_count": rule.construction_support_count,
        "legal_argument_key_set": list(rule.legal_argument_key_set),
        "tool_name": rule.tool_name,
        "value_forms": [list(value) for value in rule.value_forms],
    }


def build_assets(root: Path) -> tuple[bytes, bytes, dict[str, object]]:
    """Return deterministic centroid bytes, rule bytes, and their receipt."""

    source_receipt_path = REPO / SOURCE_RECEIPT_RELPATH
    if _sha256_bytes(source_receipt_path.read_bytes()) != SOURCE_RECEIPT_SHA256:
        raise RuntimeError("source embedding receipt identity drift")

    lock = load_lock(umbrella_lock_path(REPO))
    registry = load_tool_registry(lock, root)
    registry_names = tuple(sorted({row["tool_name"] for row in registry}))
    if len(registry_names) != 152:
        raise RuntimeError("Audio2Tool registry must contain exactly 152 tools")

    pool_rows, _inventory = a2t_pool_rows(lock, root)
    partition = propose_partition(
        pool_rows,
        exposed_sample_ids(REPO),
        seed=PARTITION_SEED,
    )
    if partition.split_identity_hash() != PARTITION_IDENTITY:
        raise RuntimeError("construction partition identity drift")
    construction = tuple(partition.construction)
    rows_sha256 = _sha256_bytes(
        _canonical_json_bytes([asdict(row) for row in construction])
    )
    if rows_sha256 != CONSTRUCTION_ROWS_SHA256:
        raise RuntimeError("construction rows identity drift")

    audit = _load_script(
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-03-a2t-semantic-candidate-audit/run_audit.py",
        "a2t_semantic_candidate_audit_for_runtime_freeze",
    )
    vectors, vector_provenance = audit._load_verified_unit_vectors(  # noqa: SLF001
        repo=REPO,
        root=root,
        construction_rows=construction,
    )
    if vector_provenance.get("vector_artifact_sha256") != SOURCE_VECTOR_SHA256:
        raise RuntimeError("construction vector identity drift")

    index = ToolTierSemanticIndex.build(
        construction_rows=construction,
        vectors_by_unit_id=vectors,
        registry_tool_names=registry_names,
    )
    if index.index_sha256 != SEMANTIC_INDEX_SHA256:
        raise RuntimeError("semantic index identity drift")
    centroid_keys = tuple(
        sorted(
            {
                (tool_name, row.tier)
                for row in construction
                for tool_name in dict.fromkeys(
                    (row.tool_name, *row.extra_call_names)
                )
            }
        )
    )
    if (
        len(centroid_keys) != EXPECTED_CENTROID_COUNT
        or index.tool_tier_centroid_count != EXPECTED_CENTROID_COUNT
        or index.dimension != EXPECTED_DIMENSION
        or tuple(tool_name for tool_name, _tier in centroid_keys)
        != tuple(index._centroid_tool_names)  # noqa: SLF001
    ):
        raise RuntimeError("semantic centroid coverage drift")

    import numpy as np

    centroids_bytes = _deterministic_npz(
        {
            "centroid_tiers": np.asarray(
                [tier for _tool_name, tier in centroid_keys]
            ),
            "centroid_tool_names": np.asarray(
                [tool_name for tool_name, _tier in centroid_keys]
            ),
            "centroid_vectors": np.asarray(
                index._centroid_matrix,  # noqa: SLF001
                dtype=np.float64,
            ),
            "registry_tool_names": np.asarray(registry_names),
        }
    )

    g4_builder = _load_script(
        "scripts/build_a2t_g4_semantic_cards.py",
        "a2t_g4_builder_for_runtime_freeze",
    )
    rules, rule_report = g4_builder.derive_compatibility_rules(
        registry,
        construction,
    )
    if len(rules) != EXPECTED_RULE_COUNT or rule_report.get("rule_count") != 43:
        raise RuntimeError("aggregate compatibility rule count drift")
    rule_list = [_rule_payload(rule) for rule in rules]
    rules_document = {
        "rules": rule_list,
        "schema": "saea-a2t-aggregate-compatibility-rules-v1",
    }
    rules_bytes = json.dumps(
        rules_document,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ).encode("ascii") + b"\n"
    compatibility_payload_sha256 = _sha256_bytes(
        _canonical_json_bytes(rule_list)
    )

    receipt = {
        "artifacts": {
            "centroids": {
                "bytes": len(centroids_bytes),
                "count": EXPECTED_CENTROID_COUNT,
                "dimension": EXPECTED_DIMENSION,
                "dtype": "float64",
                "sha256": _sha256_bytes(centroids_bytes),
            },
            "compatibility_rules": {
                "bytes": len(rules_bytes),
                "compatibility_payload_sha256": compatibility_payload_sha256,
                "count": EXPECTED_RULE_COUNT,
                "sha256": _sha256_bytes(rules_bytes),
            },
        },
        "contacts": {
            "embedding_tool": 0,
            "frozen_core": 0,
            "network": 0,
            "scorer": 0,
            "tokenizer": 0,
        },
        "execution_profile": "model-free-check",
        "privacy_boundary": {
            "concrete_argument_values_emitted": 0,
            "evaluation_rows_consumed": 0,
            "reference_transcripts_emitted": 0,
            "sample_identifiers_emitted": 0,
            "source_utterances_emitted": 0,
        },
        "schema": "saea-a2t-frozen-semantic-runtime-assets-receipt-v1",
        "semantic_index_sha256": index.index_sha256,
        "sources": {
            "construction_partition_identity_sha256": PARTITION_IDENTITY,
            "construction_rows_sha256": rows_sha256,
            "embedding_receipt_relpath": str(SOURCE_RECEIPT_RELPATH).replace(
                "\\", "/"
            ),
            "embedding_receipt_sha256": SOURCE_RECEIPT_SHA256,
            "embedding_vector_sha256": SOURCE_VECTOR_SHA256,
        },
    }
    return centroids_bytes, rules_bytes, receipt


def _write_new(path: Path, value: bytes) -> None:
    if path.exists():
        raise RuntimeError(f"output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--centroids-output", type=Path, required=True)
    parser.add_argument("--rules-output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args(argv)
    centroids, rules, receipt = build_assets(data_root())
    centroids_output = args.centroids_output.resolve()
    rules_output = args.rules_output.resolve()
    receipt_output = args.receipt_output.resolve()
    receipt["artifacts"]["centroids"]["path"] = str(
        centroids_output.relative_to(data_root().resolve())
    ).replace("\\", "/")
    receipt["artifacts"]["compatibility_rules"]["path"] = str(
        rules_output.relative_to(REPO.resolve())
    ).replace("\\", "/")
    receipt_bytes = json.dumps(
        receipt,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ).encode("ascii") + b"\n"
    _write_new(centroids_output, centroids)
    _write_new(rules_output, rules)
    _write_new(receipt_output, receipt_bytes)
    print(receipt_bytes.decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
