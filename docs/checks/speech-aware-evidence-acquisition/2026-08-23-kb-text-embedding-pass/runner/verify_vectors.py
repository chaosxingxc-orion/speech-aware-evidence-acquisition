"""Post-pass consumer-side verification of the landed vectors.

Zero model/tool contact. Proves, from the written bytes alone, that:
  * both .npz files re-hash to the manifest's recorded sha256;
  * ids are unique and aligned 1:1 with the snapshot's own ordering;
  * text_sha256[i] equals SHA-256 over the exact snapshot text for ids[i];
  * every vector is finite and dim 1024;
  * the facet_vectors callable rails.kb_policy expects can be built from them.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

DATA_ROOT = Path(os.environ["SPEECHRL_DATA_DIR"])
SNAPSHOT_DIR = DATA_ROOT / "knowledge/slurp/saea-kb-distmodel-v1/size-full"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


manifest = json.loads((SNAPSHOT_DIR / "embeddings-manifest.json").read_text(encoding="utf-8"))
document = json.loads((SNAPSHOT_DIR / "snapshot.json").read_text(encoding="utf-8"))

content_facets = [f for f in document["facets"] if f["dimension"] == "content"]
values = document["values"]

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    checks.append((name, bool(condition), detail))


for key, items, id_field, text_field in (
    ("content_facets", content_facets, "facet_id", "representation"),
    ("values", values, "value_id", "content"),
):
    entry = manifest["embedded"][key]
    path = SNAPSHOT_DIR / entry["file"]
    check(f"{key}: sha256 matches manifest", sha256_file(path) == entry["sha256"], entry["sha256"])
    data = np.load(path)
    vectors = data["vectors"]
    ids = data["ids"]
    hashes = data["text_sha256"]
    check(f"{key}: shape", vectors.shape == (entry["count"], entry["dims"]), str(vectors.shape))
    check(f"{key}: dtype float32", vectors.dtype == np.float32, str(vectors.dtype))
    check(f"{key}: all finite", bool(np.isfinite(vectors).all()))
    check(f"{key}: ids unique", len(set(ids.tolist())) == len(ids))
    expected_ids = [item[id_field] for item in items]
    check(f"{key}: ids match snapshot order", ids.tolist() == expected_ids)
    expected_hashes = [
        hashlib.sha256(item[text_field].encode("utf-8")).hexdigest() for item in items
    ]
    check(f"{key}: text_sha256 matches snapshot texts", hashes.tolist() == expected_hashes)
    norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
    check(f"{key}: no zero-norm rows", bool((norms > 0).all()),
          f"norm range [{norms.min():.6f}, {norms.max():.6f}]")

# rails.kb_policy expects facet_vectors: facet_id -> {dimension: vector}
facet_data = np.load(SNAPSHOT_DIR / manifest["embedded"]["content_facets"]["file"])
index = {fid: i for i, fid in enumerate(facet_data["ids"].tolist())}
matrix = facet_data["vectors"]


def facet_vectors(facet_id: str):
    position = index.get(facet_id)
    return {} if position is None else {"content": matrix[position]}


probe = content_facets[7]["facet_id"]
check("kb_policy facet_vectors callable works", "content" in facet_vectors(probe), probe)
check("kb_policy facet_vectors empty for a label facet",
      facet_vectors("facet:label:scenario:alarm") == {})

for name, ok, detail in checks:
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))

failed = [name for name, ok, _ in checks if not ok]
if failed:
    raise SystemExit(f"{len(failed)} verification check(s) FAILED: {failed}")
print(f"\nALL {len(checks)} VERIFICATION CHECKS PASS")
