"""Prepare immutable dimension aliases of sealed vectors without encoding.

Rename a declared vector axis for a separately organized knowledge store while
preserving every row ID, row order, and numeric component. This is a model-free
format derivative; it does not create an embedding space or authorize contact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from .preparation import (
    PreparationError, _publish_artifact, canonical_bytes, hash_stable_file,
    load_artifact, prepare_artifact, verify_source_receipts,
)
from ..rails.phase_supply import (
    PhaseSupplyError, load_sealed_segment_vectors, load_sealed_vectors,
)

SCHEMA = "saea-sealed-vector-dimension-alias-v1"
SEGMENT_SCHEMA = "saea-sealed-segment-vector-dimension-alias-v1"
SEGMENT_SOURCE_KIND = "sealed-segment-vectors"
KIND = "sealed-vector-dimension-alias"


def _confined(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise PreparationError("vector preparation paths must be relative")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or ".." in Path(relative).parts:
        raise PreparationError("vector preparation path escapes data root")
    return path


def _pinned_bytes(path, expected_sha, label):
    _, actual, fingerprint = hash_stable_file(path, label)
    raw = path.read_bytes()
    _, after, after_fingerprint = hash_stable_file(path, label + " after read")
    if (
        actual != expected_sha or hashlib.sha256(raw).hexdigest() != actual
        or actual != after or fingerprint != after_fingerprint
    ):
        raise PreparationError(label + " changed or has a wrong hash")
    return raw


def prepare_vector_dimension_alias(config, *, repo_root, data_root):
    """Materialize a config-bound alias and verify both cold and warm exports."""
    required = {
        "schema", "source", "target_dimension", "expected_rows", "vector_width",
        "output_relpath", "receipt_relpath", "source_receipts",
    }
    if (
        not isinstance(config, dict) or set(config) != required
        or config["schema"] not in {SCHEMA, SEGMENT_SCHEMA}
    ):
        raise PreparationError("vector dimension alias config has wrong fields")
    segmented = config["schema"] == SEGMENT_SCHEMA
    source = config["source"]
    source_fields = {"relpath", "sha256", "dimension"}
    if segmented:
        source_fields.add("kind")
    if not isinstance(source, dict) or set(source) != source_fields:
        raise PreparationError("vector dimension alias source has wrong fields")
    if segmented and source["kind"] != SEGMENT_SOURCE_KIND:
        raise PreparationError("segment vector alias source has wrong kind")
    for value in (source["dimension"], config["target_dimension"]):
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise PreparationError("vector dimensions must be nonempty canonical text")
    if source["dimension"] == config["target_dimension"]:
        raise PreparationError("vector alias must name a different target dimension")
    for field in ("expected_rows", "vector_width"):
        if isinstance(config[field], bool) or not isinstance(config[field], int) or config[field] <= 0:
            raise PreparationError(field + " must be a positive integer")
    data_root, repo_root = Path(data_root), Path(repo_root)
    source_path = _confined(data_root, source["relpath"])
    output_path = _confined(data_root, config["output_relpath"])
    receipt_path = _confined(data_root, config["receipt_relpath"])
    if len({source_path, output_path, receipt_path}) != 3:
        raise PreparationError("source, vector export, and receipt paths must differ")
    receipts = verify_source_receipts(
        config["source_receipts"], repo_root=repo_root, data_root=data_root,
    )
    raw = _pinned_bytes(source_path, source["sha256"], "sealed source vectors")
    try:
        loader = load_sealed_segment_vectors if segmented else load_sealed_vectors
        table = loader(
            source_path, expected_sha256=source["sha256"],
            dimensions=(source["dimension"],),
        )
    except PhaseSupplyError as error:
        raise PreparationError(str(error)) from error
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    if len(rows) != config["expected_rows"] or len(table) != len(rows):
        raise PreparationError("vector alias source roster count differs")
    aliased = []
    segment_ids = []
    if segmented:
        for row in rows:
            aliased_segments = []
            for segment in row["segments"]:
                vector = segment["vectors"][source["dimension"]]
                if len(vector) != config["vector_width"]:
                    raise PreparationError("vector alias width is invalid")
                segment_ids.append(segment["id"])
                aliased_segments.append({
                    "id": segment["id"],
                    "start_frame": segment["start_frame"],
                    "end_frame": segment["end_frame"],
                    "vectors": {config["target_dimension"]: vector},
                })
            aliased.append({
                "id": row["id"],
                "audio_sha256": row["audio_sha256"],
                "source_frames": row["source_frames"],
                "source_sample_rate_hz": row["source_sample_rate_hz"],
                "segments": aliased_segments,
            })
    else:
        for row in rows:
            if set(row["vectors"]) != {source["dimension"]}:
                raise PreparationError(
                    "vector alias source must carry exactly one declared dimension"
                )
            vector = row["vectors"][source["dimension"]]
            if (
                len(vector) != config["vector_width"]
                or any(not math.isfinite(value) for value in vector)
            ):
                raise PreparationError("vector alias width or numeric components are invalid")
            aliased.append({"id": row["id"], "vectors": {config["target_dimension"]: vector}})
    content = b"".join(canonical_bytes(row) + b"\n" for row in aliased)
    output_sha = hashlib.sha256(content).hexdigest()
    inputs = {
        "config": config, "source_receipts": receipts,
        "implementation_sha256": hash_stable_file(Path(__file__), "vector alias implementation")[1],
    }
    expected = {
        "schema": config["schema"], "source_sha256": source["sha256"],
        "source_dimension": source["dimension"], "target_dimension": config["target_dimension"],
        "output_relpath": config["output_relpath"], "output_sha256": output_sha,
        "row_count": len(rows), "vector_width": config["vector_width"],
        "ordered_ids_sha256": hashlib.sha256(canonical_bytes([row["id"] for row in rows])).hexdigest(),
        "values_unchanged": True, "max_absolute_delta": 0.0,
        "encoder_contacts": 0, "tokenizer_contacts": 0, "model_contacts": 0,
    }
    if segmented:
        expected.update({
            "source_kind": SEGMENT_SOURCE_KIND,
            "segment_count": len(segment_ids),
            "ordered_segment_ids_sha256": hashlib.sha256(
                canonical_bytes(segment_ids)
            ).hexdigest(),
        })

    def produce():
        _publish_artifact(output_path, content, contact_class="model-free")
        return expected

    receipt = prepare_artifact(
        receipt_path, kind=KIND, inputs=inputs, producer=produce, contact_class="model-free",
    )
    if load_artifact(receipt_path, expected_sha256=receipt["sha256"], kind=KIND, inputs=inputs) != expected:
        raise PreparationError("vector alias receipt differs from the derived output")
    if _pinned_bytes(output_path, output_sha, "aliased vectors") != content:
        raise PreparationError("vector alias export differs")
    readback = loader(
        output_path, expected_sha256=output_sha, dimensions=(config["target_dimension"],),
    )
    if list(readback) != list(table):
        raise PreparationError("vector alias changed row order")
    if segmented:
        if any(
            readback[sid].audio_sha256 != table[sid].audio_sha256
            or len(readback[sid].segments) != len(table[sid].segments)
            or any(
                output_segment[config["target_dimension"]]
                != source_segment[source["dimension"]]
                for source_segment, output_segment in zip(
                    table[sid].segments, readback[sid].segments, strict=True,
                )
            )
            for sid in table
        ):
            raise PreparationError("vector alias changed segment bindings or components")
    elif any(
        readback[sid][config["target_dimension"]] != table[sid][source["dimension"]]
        for sid in table
    ):
        raise PreparationError("vector alias changed components")
    return {"artifact": receipt, "output": expected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    raw = _pinned_bytes(args.config, args.config_sha256, "vector alias configuration")
    print(json.dumps(prepare_vector_dimension_alias(
        json.loads(raw), repo_root=args.repo_root, data_root=args.data_root,
    ), sort_keys=True))


if __name__ == "__main__":
    main()
