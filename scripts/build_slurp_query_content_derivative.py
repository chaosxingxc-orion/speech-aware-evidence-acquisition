#!/usr/bin/env python3
"""CLI: generalised, reusable builder for a SLURP query-side content-dimension
derivative (item 1 of cell B6's registration).

MODEL-FREE. Profile ``model-free-check``: zero frozen-core, tool, embedding,
GPU or network contacts. This is a pure re-derivation of bytes already sealed
by an earlier pass: it flattens a ``sealed-segment-vectors`` file (one
segment per sample, dimension ``intent-boundary``) into a flat
``sealed-vectors`` file (dimension renamed to ``content``) -- the exact
transform ``build_query_derivative`` in
``scripts/build_slurp_exemplar_pool_assets.py`` performs, hard-wired to the
TRAIN Fold A roster. This script generalises that transform to any source
file/roster via CLI arguments, so a fresh roster (DEV-2000-ADDED, and any
later one) never needs a hand-copied, hard-wired script; it never touches
``build_slurp_exemplar_pool_assets.py`` or its Fold A output bytes. It never
overwrites an existing output file: a re-run against the same
``--out-dir``/``--out-name`` refuses rather than risk silently changing
sealed bytes.

Every float in the output is byte-identical to the parent's single segment
vector; nothing is recomputed, re-encoded or renormalised anywhere in this
file.

Usage::

    python scripts/build_slurp_query_content_derivative.py \
        --source-relpath vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl \
        --source-sha256 e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d \
        --out-dir vectors/slurp-dev2000-added-v1 \
        --out-name query-vectors-speech-content-v1.jsonl \
        --ledger-row SAEA-SLURP-DEV2000-ADDED-SPEECH-QUERY-ENCODING-V1

    python scripts/build_slurp_query_content_derivative.py ... --check   # verify only, write nothing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402

QUERY_SOURCE_DIMENSION = "intent-boundary"
QUERY_TARGET_DIMENSION = "content"
PROVENANCE_SCHEMA = "saea-slurp-exemplar-query-vectors-provenance-v1"
EXECUTION_PROFILE = "model-free-check"
GENERATOR = "scripts/build_slurp_query_content_derivative.py"


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_query_content_derivative(
    root: Path,
    *,
    source_relpath: str,
    source_sha256: str,
    out_dir_relpath: str,
    out_name: str,
    ledger_row: str,
    check: bool,
) -> dict[str, object]:
    """Flatten one sealed Fold-A-shaped speech-SEGMENT file into a flat
    ``sealed-vectors`` file: one ``content`` vector per sample id,
    byte-identical to that sample's single segment.

    Generalises ``build_query_derivative`` in
    ``scripts/build_slurp_exemplar_pool_assets.py`` (the TRAIN Fold A
    instance of exactly this transform) to any source file via
    ``source_relpath``/``source_sha256`` and any output location via
    ``out_dir_relpath``/``out_name``, so a fresh roster's own derivative can
    be built without touching that script or its Fold A output bytes.
    """

    source_path = root / source_relpath
    if not source_path.is_file():
        raise SystemExit(f"source file not found: {source_path}")
    raw = source_path.read_bytes()
    measured = _sha256_bytes(raw)
    if measured != source_sha256:
        raise SystemExit(
            f"{source_path} hashes to {measured}, not the pinned {source_sha256}"
        )

    rows: list[tuple[str, list[float]]] = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        document = json.loads(line)
        segments = document["segments"]
        if len(segments) != 1:
            raise SystemExit(
                f"{source_path} id={document.get('id')!r} carries {len(segments)} segments; "
                "flattening to one vector per sample requires exactly one"
            )
        vectors = segments[0]["vectors"]
        if set(vectors) != {QUERY_SOURCE_DIMENSION}:
            raise SystemExit(
                f"{source_path} id={document.get('id')!r} carries dimensions "
                f"{sorted(vectors)}, expected exactly {{{QUERY_SOURCE_DIMENSION!r}}}"
            )
        rows.append((str(document["id"]), list(vectors[QUERY_SOURCE_DIMENSION])))

    out_lines = [
        json.dumps(
            {"id": entry_id, "vectors": {QUERY_TARGET_DIMENSION: vector}},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        for entry_id, vector in rows
    ]
    out_dir = root / out_dir_relpath
    out_path = out_dir / out_name
    out_bytes = ("\n".join(out_lines) + "\n").encode("utf-8")
    out_sha256 = _sha256_bytes(out_bytes)

    if out_path.exists():
        raise SystemExit(
            f"refusing to overwrite an existing derivative at {out_path}; "
            "delete it deliberately first if a fresh derivation is truly intended"
        )

    if not check:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(out_bytes)
        print(f"wrote {out_path}  sha256={out_sha256[:16]}...  rows={len(rows)}")
    else:
        print(
            f"(check) query derivative would be {out_path}  sha256={out_sha256[:16]}...  "
            f"rows={len(rows)}"
        )

    provenance = {
        "schema": PROVENANCE_SCHEMA,
        "generator": GENERATOR,
        "transform": (
            "flatten one-segment-per-sample sealed-segment-vectors into flat "
            "sealed-vectors, dimension renamed intent-boundary -> content; every float "
            "is byte-identical to the parent's single segment vector; zero model or "
            "encoder contact"
        ),
        "parent_relpath": source_relpath,
        "parent_sha256": source_sha256,
        "parent_kind": "sealed-segment-vectors",
        "output_kind": "sealed-vectors",
        "source_dimension": QUERY_SOURCE_DIMENSION,
        "target_dimension": QUERY_TARGET_DIMENSION,
        "row_count": len(rows),
        "sha256": out_sha256,
        "exposure_ledger_row": ledger_row,
        "execution_profile": EXECUTION_PROFILE,
    }
    provenance_path = out_dir / (Path(out_name).stem + ".provenance.json")
    if not check:
        write_json_artifact(provenance_path, provenance)
        print(f"wrote {provenance_path}")
    return {"sha256": out_sha256, "row_count": len(rows), "out_path": str(out_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-relpath", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--out-dir", required=True, dest="out_dir_relpath")
    parser.add_argument("--out-name", required=True)
    parser.add_argument("--ledger-row", required=True)
    parser.add_argument("--check", action="store_true", help="verify only; write nothing")
    args = parser.parse_args(argv)

    root = data_root()
    result = build_query_content_derivative(
        root,
        source_relpath=args.source_relpath,
        source_sha256=args.source_sha256,
        out_dir_relpath=args.out_dir_relpath,
        out_name=args.out_name,
        ledger_row=args.ledger_row,
        check=args.check,
    )
    print("---")
    print(f"sha256={result['sha256']} rows={result['row_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
