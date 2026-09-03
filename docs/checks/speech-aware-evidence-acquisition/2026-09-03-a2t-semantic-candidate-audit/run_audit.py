"""Reproduce the Audio2Tool local-semantic candidate audit."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence


REPO = Path(__file__).resolve().parents[4]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_dense_candidate_validation import (  # noqa: E402
    analyze_dense_candidate_validation,
)
from speech_aware_evidence_acquisition.analysis.a2t_grouped_candidate_validation import (  # noqa: E402
    assign_grouped_validation_folds,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    load_tool_registry,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    A2tKbRow,
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)


PARTITION_SEED = 20260807
PARTITION_IDENTITY = "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
VALIDATION_SEED = 20260903
FOLD_COUNT = 5
K_GRID = (1, 3, 5, 8, 16, 32, 64)
RECEIPT_RELPATH = Path("docs/receipts/knowledge/a2t-kb-size-full-embeddings.json")
_DIALOGUE_RELPATH = Path("public/tier7_multiturn_data/tier7_multiturn.json")
_ASCII_TRANSLATION = {
    0x00B0: " degrees",
    0x2011: "-",
    0x2013: "-",
    0x2014: " -- ",
    0x2018: "'",
    0x201D: '"',
    0x2026: "...",
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _resolved_under(root: Path, relative: str, *, label: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise RuntimeError(f"{label} path must be relative to the data root")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise RuntimeError(f"{label} path escapes the data root")
    return resolved


def _load_verified_unit_vectors(
    *,
    repo: Path,
    root: Path,
    construction_rows: Sequence[A2tKbRow],
) -> tuple[dict[str, object], dict[str, object]]:
    """Load a receipt-bound vector artifact and bind every row to exact text."""

    import numpy as np

    receipt_path = repo / RECEIPT_RELPATH
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes.decode("utf-8"))
    if receipt.get("schema") != "saea-kb-text-embeddings-receipt-v1":
        raise RuntimeError("embedding receipt schema drift")
    embedder = receipt.get("embedder")
    snapshot_record = receipt.get("snapshot")
    vectors_record = receipt.get("vectors", {}).get("content_facets")
    if not all(
        isinstance(value, Mapping)
        for value in (embedder, snapshot_record, vectors_record)
    ):
        raise RuntimeError("embedding receipt lacks required records")
    assert isinstance(embedder, Mapping)
    assert isinstance(snapshot_record, Mapping)
    assert isinstance(vectors_record, Mapping)
    role = embedder.get("role")
    if not isinstance(role, str) or "TOOL-level embedder" not in role:
        raise RuntimeError("embedding receipt does not name a tool-level embedder")
    snapshot_relpath = snapshot_record.get("artifact_relpath")
    if not isinstance(snapshot_relpath, str):
        raise RuntimeError("embedding receipt lacks the snapshot path")
    snapshot_path = _resolved_under(root, snapshot_relpath, label="snapshot")
    if _sha256_file(snapshot_path) != snapshot_record.get("file_sha256"):
        raise RuntimeError("snapshot artifact SHA-256 does not match its receipt")
    vector_name = vectors_record.get("file")
    if not isinstance(vector_name, str) or Path(vector_name).name != vector_name:
        raise RuntimeError("embedding receipt has a malformed vector filename")
    vector_path = snapshot_path.parent / vector_name
    if _sha256_file(vector_path) != vectors_record.get("sha256"):
        raise RuntimeError("vector artifact SHA-256 does not match its receipt")

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    facets = snapshot.get("facets")
    if not isinstance(facets, list):
        raise RuntimeError("snapshot facets are malformed")
    content_by_id: dict[str, Mapping[str, object]] = {}
    for facet in facets:
        if not isinstance(facet, Mapping) or facet.get("dimension") != "content":
            continue
        facet_id = facet.get("facet_id")
        if not isinstance(facet_id, str) or facet_id in content_by_id:
            raise RuntimeError("snapshot content facet ids are malformed or duplicated")
        content_by_id[facet_id] = facet

    with np.load(vector_path, allow_pickle=False) as archive:
        if set(archive.files) != {"vectors", "ids", "text_sha256"}:
            raise RuntimeError("vector archive field set drift")
        matrix = np.asarray(archive["vectors"], dtype=np.float32)
        ids = tuple(str(value) for value in archive["ids"])
        text_hashes = tuple(str(value) for value in archive["text_sha256"])
    expected_count = len(construction_rows)
    expected_dimension = embedder.get("dims")
    if (
        matrix.ndim != 2
        or matrix.shape[0] != expected_count
        or matrix.shape[1] != expected_dimension
        or matrix.shape[0] != vectors_record.get("count")
        or matrix.shape[1] != vectors_record.get("dims")
        or len(ids) != matrix.shape[0]
        or len(text_hashes) != matrix.shape[0]
    ):
        raise RuntimeError(
            "vector artifact shape does not match receipt or construction"
        )
    if len(ids) != len(set(ids)):
        raise RuntimeError("vector artifact ids are duplicated")
    if not bool(np.isfinite(matrix).all()) or bool(
        (np.linalg.norm(matrix, axis=1) == 0.0).any()
    ):
        raise RuntimeError("vector artifact contains non-finite or zero vectors")

    row_by_facet_id = {f"facet:content:{row.unit_id}": row for row in construction_rows}
    if set(ids) != set(row_by_facet_id) or set(content_by_id) != set(row_by_facet_id):
        raise RuntimeError("vector and snapshot ids do not exactly match construction")
    vectors_by_unit_id: dict[str, object] = {}
    for index, facet_id in enumerate(ids):
        row = row_by_facet_id[facet_id]
        representation = content_by_id[facet_id].get("representation")
        if representation != row.text:
            raise RuntimeError(
                "snapshot representation does not match construction text"
            )
        if _sha256_bytes(row.text.encode("utf-8")) != text_hashes[index]:
            raise RuntimeError("vector text SHA-256 does not match construction text")
        vectors_by_unit_id[row.unit_id] = matrix[index]

    return vectors_by_unit_id, {
        "receipt_relpath": str(RECEIPT_RELPATH).replace("\\", "/"),
        "receipt_sha256": _sha256_bytes(receipt_bytes),
        "exposure_ledger_row": receipt.get("exposure_ledger_row"),
        "embedder_role": role,
        "embedder_build_commit": embedder.get("build_commit"),
        "embedder_gguf_sha256": embedder.get("gguf_sha256"),
        "snapshot_relpath": snapshot_relpath,
        "snapshot_sha256": snapshot_record.get("file_sha256"),
        "source_split_identity_hash": snapshot_record.get("source_split_identity_hash"),
        "vector_artifact_sha256": vectors_record.get("sha256"),
        "vector_count": matrix.shape[0],
        "vector_dimension": matrix.shape[1],
        "all_unit_ids_match": True,
        "all_representations_match_construction_text": True,
        "all_text_hashes_match": True,
        "vector_values_emitted": False,
        "source_text_emitted": False,
    }


def _translate_dialogue(value: str) -> str:
    observed = {ord(character) for character in value if not character.isascii()}
    unknown = sorted(observed - set(_ASCII_TRANSLATION))
    if unknown:
        raise RuntimeError("tier-7 dialogue contains unregistered non-ASCII")
    translated = " ".join(value.translate(_ASCII_TRANSLATION).split())
    if not translated or not translated.isascii():
        raise RuntimeError("tier-7 dialogue translation failed")
    return translated


def _load_dialogue_overrides(
    manifest_path: Path, construction_rows: Sequence[A2tKbRow]
) -> dict[str, str]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("tier-7 dialogue manifest must be a list")
    required = {
        row.query_idx: row.unit_id
        for row in construction_rows
        if row.tier == "tier7_multiturn"
    }
    by_query: dict[int, str] = {}
    for entry in payload:
        if not isinstance(entry, Mapping):
            raise RuntimeError("tier-7 dialogue entry is malformed")
        query_idx = entry.get("query_idx")
        if type(query_idx) is not int or query_idx not in required:
            continue
        text = entry.get("query")
        if not isinstance(text, str):
            raise RuntimeError("tier-7 dialogue entry lacks text")
        translated = _translate_dialogue(text)
        prior = by_query.setdefault(query_idx, translated)
        if prior != translated:
            raise RuntimeError("tier-7 dialogue drifts within a query block")
    if set(by_query) != set(required):
        raise RuntimeError("tier-7 dialogue does not cover construction")
    return {required[index]: by_query[index] for index in sorted(required)}


def _quality_gate(method: Mapping[str, object]) -> dict[str, object]:
    pooled = method["pooled"]
    worst = method["worst_fold"]
    assert isinstance(pooled, Mapping)
    assert isinstance(worst, Mapping)
    per_tier = pooled["per_tier"]
    multi = pooled["multi_call"]
    near = pooled["near_duplicate_sensitivity"]
    assert isinstance(per_tier, Mapping)
    assert isinstance(multi, Mapping)
    assert isinstance(near, Mapping)
    no_near = near["no_near_duplicate"]
    assert isinstance(no_near, Mapping)
    by_k: dict[str, object] = {}
    for k in K_GRID:
        key = str(k)
        metrics = pooled["k_metrics"][key]
        checks = {
            "overall_full_set_at_least_0_95": metrics["full_set_coverage"] >= 0.95,
            "overall_label_recall_at_least_0_97": metrics["required_item_recall"]
            >= 0.97,
            "mean_distractors_at_most_15": metrics["mean_distractor_burden"] <= 15.0,
            "worst_fold_full_set_at_least_0_93": worst[key]["minimum_full_set_coverage"]
            >= 0.93,
            "every_tier_full_set_at_least_0_90": all(
                values[key]["full_set_coverage"] >= 0.90 for values in per_tier.values()
            ),
            "multi_call_full_set_at_least_0_90": multi["k_metrics"][key][
                "full_set_coverage"
            ]
            >= 0.90,
            "no_near_duplicate_full_set_at_least_0_95": no_near["k_metrics"][key][
                "full_set_coverage"
            ]
            >= 0.95,
            "fixed_candidate_count_at_most_32": k <= 32,
        }
        by_k[key] = checks
    passing = [int(key) for key, checks in by_k.items() if all(checks.values())]
    return {"by_k": by_k, "passing_fixed_k": passing, "admitted": bool(passing)}


def _deltas(methods: Mapping[str, object]) -> dict[str, object]:
    baseline = methods["bm25"]["pooled"]
    result: dict[str, object] = {}
    for name in sorted(set(methods) - {"bm25"}):
        current = methods[name]["pooled"]
        result[name] = {
            str(k): {
                "full_set_coverage_delta": current["k_metrics"][str(k)][
                    "full_set_coverage"
                ]
                - baseline["k_metrics"][str(k)]["full_set_coverage"],
                "required_item_recall_delta": current["k_metrics"][str(k)][
                    "required_item_recall"
                ]
                - baseline["k_metrics"][str(k)]["required_item_recall"],
                "mean_distractor_burden_delta": current["k_metrics"][str(k)][
                    "mean_distractor_burden"
                ]
                - baseline["k_metrics"][str(k)]["mean_distractor_burden"],
                "implicit_full_set_coverage_delta": current["per_tier"][
                    "tier4_implicit"
                ][str(k)]["full_set_coverage"]
                - baseline["per_tier"]["tier4_implicit"][str(k)]["full_set_coverage"],
                "multiturn_full_set_coverage_delta": current["per_tier"][
                    "tier7_multiturn"
                ][str(k)]["full_set_coverage"]
                - baseline["per_tier"]["tier7_multiturn"][str(k)]["full_set_coverage"],
            }
            for k in K_GRID
        }
    return result


def run_audit(*, repo: Path, root: Path) -> dict[str, object]:
    lock = load_lock(umbrella_lock_path(repo))
    rows, _inventory = a2t_pool_rows(lock, root)
    partition = propose_partition(rows, exposed_sample_ids(repo), seed=PARTITION_SEED)
    if partition.split_identity_hash() != PARTITION_IDENTITY:
        raise RuntimeError("construction/evaluation partition identity drift")
    construction = partition.construction
    registry = load_tool_registry(lock, root)
    registry_names = tuple(str(row["tool_name"]) for row in registry)
    vectors, vector_provenance = _load_verified_unit_vectors(
        repo=repo,
        root=root,
        construction_rows=construction,
    )
    dialogue = _load_dialogue_overrides(
        asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root) / _DIALOGUE_RELPATH,
        construction,
    )
    folds = assign_grouped_validation_folds(
        construction,
        seed=VALIDATION_SEED,
        fold_count=FOLD_COUNT,
        alternate_text_by_unit_id=dialogue,
    )
    audit = analyze_dense_candidate_validation(
        construction_rows=construction,
        vectors_by_unit_id=vectors,
        registry_tool_names=registry_names,
        validation_folds=folds,
        k_grid=K_GRID,
    )
    methods = audit.report["methods"]
    quality = {name: _quality_gate(report) for name, report in methods.items()}
    return {
        "schema": "saea-a2t-semantic-candidate-audit-summary-v1",
        "scope": {
            "construction_training_population_only": True,
            "frozen_local_tool_level_embedder_outputs_reused": True,
            "new_embedding_model_contacts": 0,
            "new_frozen_core_contacts": 0,
            "network_contacts": 0,
            "scorer_contacts": 0,
            "runtime_performance_claim": False,
            "model_consumption_upper_bound": False,
        },
        "vector_provenance": vector_provenance,
        "construction": {
            "unit_count": len(construction),
            "query_block_count": len({row.query_idx for row in construction}),
            "tier_counts": dict(
                sorted(Counter(row.tier for row in construction).items())
            ),
            "registry_label_count": len(registry_names),
        },
        "semantic_candidate_report_sha256": _sha256_bytes(
            audit.canonical_json.encode("ascii")
        ),
        "semantic_candidate_report": audit.report,
        "deltas_vs_bm25": _deltas(methods),
        "quality_gate": quality,
        "decision": {
            "strict_ground_gate_admitted_methods": [
                name for name, gate in quality.items() if gate["admitted"]
            ],
            "bounded_engineering_flight_candidate": {
                "method": "dense",
                "candidate_count": 16,
                "status": "FROZEN_FOR_PREREGISTRATION_NOT_CONTACT_AUTHORITY",
                "basis": (
                    "Large stable gain; passes six of seven strict retrieval gates. "
                    "The post-training-free-RL greater-than-0.90 target does not bind "
                    "the baseline engineering flight."
                ),
            },
            "nearest_exemplar_hypothesis": "REJECTED",
            "next_step": "FREEZE_AGENTLOOP_CONSUMPTION_FLIGHT_AND_DECISION_CARDS",
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--verify-summary", type=Path)
    args = parser.parse_args(argv)
    result = run_audit(
        repo=REPO,
        root=args.data_root.resolve() if args.data_root else data_root(),
    )
    rendered = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    if args.verify_summary is not None:
        expected = json.loads(args.verify_summary.read_text(encoding="utf-8"))
        if expected != result:
            raise RuntimeError("committed summary does not reproduce")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
