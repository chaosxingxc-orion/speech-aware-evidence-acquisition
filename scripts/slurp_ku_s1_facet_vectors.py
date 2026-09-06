"""SAEA-SLURP-MF-KU-S1-FACET-VECTORS-V1 -- format conversion of the already
sealed SLURP content-facet vectors into the ``sealed-vectors`` JSONL the E6
``phase_supply`` seam reads.

ZERO CONTACTS OF ANY KIND. No server is spawned, no socket is opened, no
model is loaded and no text is embedded. Every number written here was
produced on 2026-08-24 by the registered tool-contact pass
``SAEA-SN-TOOL-KB-TEXT-EMB-PASS`` (receipt
``docs/receipts/knowledge/slurp-kb-size-full-embeddings.json``, attempt
``attempt-20260824T030738Z-kbtxemb``, 23,030 embedding tool contacts, 0
frozen-core contacts) and has been sitting in
``vectors-content-facets.npz`` ever since. This script re-reads that file,
verifies its sha256 against the receipt's pin, and rewrites the SAME
vectors, unmodified, in the one-JSON-object-per-line form
``rails.phase_supply.load_sealed_vectors`` expects::

    {"id": "<facet id>", "vectors": {"content": [<1024 floats>]}}

What it deliberately does not do:

* it never touches ``vectors-values.npz``. The 2026-08-23 Q-K-V ruling is
  that V is consumed, never embedded as key material, and the DEV-1000 lock
  flight never loaded the value vectors either.
* it never re-embeds anything. A rewrite that produced a NEW vector would be
  a tool contact and would need its own ledger row; the whole point of this
  row is that the signal is already paid for.
* it applies no normalization and no rounding. Each stored ``float32`` is
  widened to the exactly-equal Python ``float`` and serialised with the
  shortest decimal that round-trips that double, so the JSONL carries the
  same numbers the npz carries, bit for bit.

Integrity gates, all before a single byte is written:

1. the npz file's sha256 equals the embeddings receipt's pin;
2. the frozen snapshot's own content hash equals the fragment's
   ``knowledge_snapshot_sha256``;
3. the npz's ``ids`` array equals, in order, the snapshot's ``dimension ==
   "content"`` facet ids -- so a consumer indexing this JSONL by facet id is
   indexing the same snapshot the flight will bind;
4. every row has exactly 1,024 finite components.

Usage (WSL2, from the study repository root)::

    python scripts/slurp_ku_s1_facet_vectors.py [--force]

``--force`` is required to overwrite an existing output file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN_ID = "SAEA-SLURP-MF-KU-S1-FACET-VECTORS-V1"

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit(
        "PYTHONDONTWRITEBYTECODE=1 is required (bytecode under the frozen "
        "package closes the D3 gate)"
    )
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal " + str(REPO / "src"))

import speech_aware_evidence_acquisition as _pkg  # noqa: E402

_pkg_file = Path(_pkg.__file__ or "")
if _pkg_file != REPO / "src" / "speech_aware_evidence_acquisition" / "__init__.py":
    raise SystemExit(
        "package resolves to %s, not this checkout (hijacked install)" % (_pkg_file,)
    )

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
)

DATA_ROOT = Path(os.environ["SPEECHRL_DATA_DIR"])
SNAPSHOT_DIR = DATA_ROOT / "knowledge/slurp/saea-kb-distmodel-v1/size-full"
SNAPSHOT_PATH = SNAPSHOT_DIR / "snapshot.json"
SOURCE_NPZ = SNAPSHOT_DIR / "vectors-content-facets.npz"

#: docs/receipts/knowledge/slurp-kb-size-full-embeddings.json ->
#: vectors.content_facets.sha256 / .count / .dims, and .snapshot.content_sha256.
EMBEDDINGS_RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-kb-size-full-embeddings.json"
SOURCE_NPZ_SHA256 = "0bcb955a3a0ab84880f0d039ae702e77d1247ed23c3b8cecb468cbb1e0221c72"
SNAPSHOT_CONTENT_SHA256 = (
    "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"
)
EXPECTED_ROWS = 11514
EXPECTED_DIMS = 1024

#: The relpath configs/baseline/slurp-phase-blend-cl-v1.json names under
#: phase_supply.evidence.facet_source.
OUTPUT_RELPATH = "vectors/slurp-ku-s1/facet-vectors.jsonl"
DIMENSION = "content"

RECEIPT_DIR = (
    REPO
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-06-slurp-ku-s1-vectors"
)
RECEIPT_PATH = RECEIPT_DIR / "facet-vectors.json"


def iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing output JSONL",
    )
    args = parser.parse_args()

    started = time.time()
    print("[%s] %s" % (iso_now(), RUN_ID), flush=True)

    # ---- gate 1: the source npz is the receipt's own file -----------------
    receipt_path = REPO / EMBEDDINGS_RECEIPT_RELPATH
    embeddings_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    pinned = embeddings_receipt["vectors"]["content_facets"]
    if pinned["sha256"] != SOURCE_NPZ_SHA256:
        raise SystemExit(
            "the embeddings receipt pins %s but this script expects %s; the "
            "receipt moved and this conversion must be re-derived, not forced"
            % (pinned["sha256"], SOURCE_NPZ_SHA256)
        )
    measured_npz = sha256_file(SOURCE_NPZ)
    if measured_npz != SOURCE_NPZ_SHA256:
        raise SystemExit(
            "source %s hashes to %s, not the receipt's pin %s"
            % (SOURCE_NPZ, measured_npz, SOURCE_NPZ_SHA256)
        )
    print("[%s] source npz sha256 VERIFIED against the sealed embeddings "
          "receipt (%s tool contacts already paid)"
          % (iso_now(), embeddings_receipt["accounting"]["embedding_tool_contacts"]),
          flush=True)

    # ---- gate 2: the snapshot is the one the fragment pins ----------------
    snapshot_file_sha256 = sha256_file(SNAPSHOT_PATH)
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    )
    content_hash = snapshot.content_hash()
    if content_hash != SNAPSHOT_CONTENT_SHA256:
        raise SystemExit(
            "snapshot content hash %s != pinned %s" % (content_hash, SNAPSHOT_CONTENT_SHA256)
        )
    snapshot_content_facet_ids = tuple(
        facet.facet_id for facet in snapshot.facets if facet.dimension == DIMENSION
    )
    print(
        "[%s] snapshot %s VERIFIED (%d facets, %d values, %d of dimension %r)"
        % (
            iso_now(),
            snapshot.snapshot_id,
            len(snapshot.facets),
            len(snapshot.values),
            len(snapshot_content_facet_ids),
            DIMENSION,
        ),
        flush=True,
    )

    # ---- gate 3: the npz's ids ARE those facet ids, in order --------------
    with np.load(SOURCE_NPZ) as archive:
        vectors = np.asarray(archive["vectors"])
        ids = [str(value) for value in archive["ids"]]
    if vectors.shape != (EXPECTED_ROWS, EXPECTED_DIMS):
        raise SystemExit(
            "npz vectors have shape %r, expected %r"
            % (vectors.shape, (EXPECTED_ROWS, EXPECTED_DIMS))
        )
    if vectors.dtype != np.float32:
        raise SystemExit("npz vectors are %s, expected float32" % vectors.dtype)
    if len(ids) != EXPECTED_ROWS:
        raise SystemExit("npz carries %d ids, expected %d" % (len(ids), EXPECTED_ROWS))
    if tuple(ids) != snapshot_content_facet_ids:
        raise SystemExit(
            "the npz's ids are not the snapshot's content facet ids in snapshot "
            "order; this conversion would index a different snapshot"
        )
    if len(set(ids)) != len(ids):
        raise SystemExit("the npz carries duplicate facet ids")
    print("[%s] npz ids == snapshot content facet ids, in order" % iso_now(), flush=True)

    # ---- write the JSONL --------------------------------------------------
    output_path = DATA_ROOT / OUTPUT_RELPATH
    if output_path.exists() and not args.force:
        raise SystemExit(
            "refusing to overwrite an existing %s (pass --force)" % output_path
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_started = time.time()
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for index, facet_id in enumerate(ids):
            row = vectors[index]
            components = [float(value) for value in row]
            if any(not math.isfinite(value) for value in components):
                raise SystemExit("row %d (%s) carries a non-finite component"
                                 % (index, facet_id))
            handle.write(
                json.dumps(
                    {"id": facet_id, "vectors": {DIMENSION: components}},
                    sort_keys=True,
                )
                + "\n"
            )
    write_seconds = time.time() - write_started
    output_sha256 = sha256_file(output_path)
    output_bytes = output_path.stat().st_size
    print(
        "[%s] wrote %s (%d bytes, sha256 %s, %.1fs)"
        % (iso_now(), output_path, output_bytes, output_sha256, write_seconds),
        flush=True,
    )

    # ---- read the JSONL BACK through the real consumer --------------------
    from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: PLC0415
        load_sealed_vectors,
    )

    reload_started = time.time()
    table = load_sealed_vectors(
        output_path, expected_sha256=output_sha256, dimensions=(DIMENSION,)
    )
    reload_seconds = time.time() - reload_started
    if len(table) != EXPECTED_ROWS:
        raise SystemExit("reload produced %d rows, expected %d" % (len(table), EXPECTED_ROWS))
    max_abs_delta = 0.0
    for index, facet_id in enumerate(ids):
        restored = table[facet_id][DIMENSION]
        if len(restored) != EXPECTED_DIMS:
            raise SystemExit("reloaded row %s has width %d" % (facet_id, len(restored)))
        original = vectors[index]
        for position, value in enumerate(restored):
            delta = abs(value - float(original[position]))
            if delta > max_abs_delta:
                max_abs_delta = delta
    if max_abs_delta != 0.0:
        raise SystemExit(
            "round trip is not exact: max |delta| = %r" % (max_abs_delta,)
        )
    print(
        "[%s] round trip through rails.phase_supply.load_sealed_vectors is EXACT "
        "(%d rows, max |delta| 0.0, %.1fs)" % (iso_now(), len(table), reload_seconds),
        flush=True,
    )

    norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
    receipt = {
        "schema": "saea-sealed-vector-conversion-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": "slurp",
        "run_id": RUN_ID,
        "exposure_ledger_row": RUN_ID,
        "execution_profile": "model-free-check",
        "generated_at": iso_now(),
        "generator": "scripts/slurp_ku_s1_facet_vectors.py",
        "generator_sha256": sha256_file(Path(__file__).resolve()),
        "purpose": (
            "Convert the already sealed SLURP content-facet vectors into the "
            "sealed-vectors JSONL that configs/baseline/slurp-phase-blend-cl-v1.json's "
            "phase_supply.evidence.facet_source names, so cell KU-S1 can bind them "
            "through the E6 config seam. A pure format change: same vectors, same "
            "order, same numbers."
        ),
        "accounting": {
            "frozen_core_contacts": 0,
            "embedding_tool_contacts": 0,
            "http_requests": 0,
            "gpu_hours": 0.0,
            "speech_audio_seconds": 0,
            "gold_reads": 0,
            "total_wall_seconds": round(time.time() - started, 3),
            "write_seconds": round(write_seconds, 3),
            "reload_seconds": round(reload_seconds, 3),
        },
        "source": {
            "artifact_relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-full/vectors-content-facets.npz",
            "sha256": measured_npz,
            "sha256_pin_source": EMBEDDINGS_RECEIPT_RELPATH,
            "count": int(pinned["count"]),
            "dims": int(pinned["dims"]),
            "source_field": pinned["source_field"],
            "order": pinned["order"],
            "paid_by": {
                "run_id": embeddings_receipt["run_id"],
                "attempt_id": embeddings_receipt["attempt_id"],
                "embedding_tool_contacts": embeddings_receipt["accounting"][
                    "embedding_tool_contacts"
                ],
                "frozen_core_contacts": embeddings_receipt["accounting"][
                    "frozen_core_contacts"
                ],
                "embedder_gguf_sha256": embeddings_receipt["embedder"]["gguf_sha256"],
                "embedder_build_commit": embeddings_receipt["embedder"]["build_commit"],
            },
        },
        "snapshot": {
            "snapshot_id": snapshot.snapshot_id,
            "artifact_relpath": "knowledge/slurp/saea-kb-distmodel-v1/size-full/snapshot.json",
            "content_sha256": content_hash,
            "file_sha256": snapshot_file_sha256,
            "builder_policy_id": snapshot.builder_policy_id,
            "source_split_identity_hash": snapshot.source_split_identity_hash,
            "facet_count": len(snapshot.facets),
            "value_count": len(snapshot.values),
            "content_facet_count": len(snapshot_content_facet_ids),
        },
        "output": {
            "artifact_relpath": OUTPUT_RELPATH,
            "sha256": output_sha256,
            "bytes": output_bytes,
            "rows": len(table),
            "dims": EXPECTED_DIMS,
            "dimension": DIMENSION,
            "line_form": '{"id": "<facet id>", "vectors": {"content": [<1024 floats>]}}',
            "id_space": "KeyFacet.facet_id of the size-full snapshot, dimension == 'content'",
            "round_trip": {
                "reader": "rails.phase_supply.load_sealed_vectors",
                "max_abs_delta_vs_npz": 0.0,
                "exact": True,
            },
        },
        "storage": {
            "normalization_applied_by_this_pass": "none",
            "rounding_applied_by_this_pass": "none",
            "note": (
                "each float32 is widened to the exactly equal Python float and "
                "serialised with the shortest decimal that round-trips that double, "
                "so the JSONL reproduces the npz numbers exactly (verified above by "
                "reading the file back through the flight's own reader)."
            ),
            "l2_norms": {
                "min": float(norms.min()),
                "max": float(norms.max()),
                "mean": float(norms.mean()),
            },
        },
        "not_converted": {
            "vectors-values.npz": (
                "the VALUE vectors stay sealed and are never loaded (owner Q-K-V "
                "ruling 2026-08-23: V is consumed, never embedded as key material). "
                "The DEV-1000 lock flight never loaded them either."
            ),
            "label/prior/speaker facets": (
                "never embedded at all; they are recalled by prior mass and exact-key "
                "agreement, never by vector similarity."
            ),
        },
    }
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("[%s] wrote %s" % (iso_now(), RECEIPT_PATH), flush=True)
    print("OUTPUT_SHA256=%s" % output_sha256, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
