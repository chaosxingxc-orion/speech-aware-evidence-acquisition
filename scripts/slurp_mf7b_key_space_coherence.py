#!/usr/bin/env python3
"""MF-7b: is each TOWER healthy, or is the failure the modality gap itself?

Exposure row ``SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V2``. **Zero model, GPU, tool,
embedding, network and audio contacts** -- pure arithmetic over vectors two
ledgered producer passes already wrote.

A speech query set can miss for two very different reasons: the encoder's text
side is weak, or the encoder is fine on each side and the two sides do not
meet. The audit's corrective-power table cannot tell those apart, so this read
asks each side on its own terms and writes ``key-space-coherence.json`` beside
the audit's own receipts:

* **text key space** -- does a TRAIN utterance text's nearest OTHER TRAIN text
  carry the same gold intent?
* **speech query space** -- does a DEV recording's nearest OTHER DEV recording
  carry the same gold intent?
* **text to label** -- does a TRAIN utterance text find its own intent among
  the 60 label keys?

A negative verdict that survives three healthy towers is a statement about the
modality gap, not about the encoder.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    slurp_retrieval_key_audit as audit,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-retrieval-key-audit-v2"
)
MF7 = "vectors/slurp-mf7"
MF7B = "vectors/slurp-mf7b"
ROW_ID = "SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V2"

#: ``encoder -> (key jsonl, speech query jsonl, label key jsonl or None)``.
ENCODERS: dict[str, tuple[str, str, str | None]] = {
    "glap": (f"{MF7}/glap-key-vectors.jsonl",
             f"{MF7}/glap-q-speech-query-vectors.jsonl", None),
    "lco-embedding-omni-3b": (f"{MF7B}/lco-key-vectors.jsonl",
                              f"{MF7B}/lco-q-speech-query-vectors.jsonl",
                              f"{MF7B}/lco-label-key-vectors.jsonl"),
    "omni-embed-nemotron-3b": (f"{MF7B}/nemotron-key-vectors.jsonl",
                               f"{MF7B}/nemotron-q-speech-query-vectors.jsonl",
                               f"{MF7B}/nemotron-label-key-vectors.jsonl"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(directory: Path) -> None:
    lines = [
        f"{sha256_file(path)} *{path.name}"
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def ordered(path: Path, order: list[str]) -> np.ndarray:
    ids, vectors = audit.load_vectors_jsonl(path)
    position = {identifier: index for index, identifier in enumerate(ids)}
    return np.asarray(vectors, dtype=np.float64)[[position[key] for key in order]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    root = Path(data_root())
    dev = audit.load_dev_rows(root / MF7B / "dev-rows-projected-v2.jsonl")
    facets = audit.load_key_rows(root / MF7 / "train-facets.jsonl")
    key_order = [row.facet_id for row in facets]
    query_order = [row.sample_id for row in dev]
    key_labels = [row.intent for row in facets]
    query_labels = [row.intent for row in dev]

    blocks = []
    for encoder, (key_rel, query_rel, label_rel) in ENCODERS.items():
        key_path, query_path = root / key_rel, root / query_rel
        if not key_path.is_file() or not query_path.is_file():
            print(f"{encoder}: vectors missing, skipped")
            continue
        label_vectors = label_labels = None
        if label_rel and (root / label_rel).is_file():
            label_ids, raw = audit.load_vectors_jsonl(root / label_rel)
            label_vectors = np.asarray(raw, dtype=np.float64)
            label_labels = [identifier.split(":", 1)[1] for identifier in label_ids]
        block = audit.key_space_coherence(
            encoder=encoder,
            key_vectors=ordered(key_path, key_order), key_labels=key_labels,
            query_vectors=ordered(query_path, query_order), query_labels=query_labels,
            label_vectors=label_vectors, label_labels=label_labels,
        )
        block["provenance"] = {
            "key_vectors": {"file": key_rel, "sha256": sha256_file(key_path)},
            "query_vectors": {"file": query_rel, "sha256": sha256_file(query_path)},
        }
        blocks.append(block)
        text = block["text_key_space"]
        speech = block["speech_query_space"]
        label = block.get("train_text_to_label")
        print(f"{encoder:26s} text-tower {text['nearest_other_same_label_pp']:6.2f} "
              f"(cos {text['mean_cosine']:+.4f})  speech-tower "
              f"{speech['nearest_other_same_label_pp']:6.2f} "
              f"(cos {speech['mean_cosine']:+.4f})"
              + ("" if label is None
                 else f"  text->label {label['nearest_label_accuracy_pp']:6.2f}"))

    if not args.write:
        return 0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json_artifact(OUT_DIR / "key-space-coherence.json", {
        "schema": audit.AUDIT_SCHEMA,
        "exposure_ledger_row": ROW_ID,
        "note": "each tower measured on its own terms; nothing here gates the decision "
        "table, and no contact of any kind was made",
        "populations": {"text_keys": len(facets), "speech_queries": len(dev), "labels": 60},
        "encoders": blocks,
        "accounting": {"frozen_core_contacts": 0, "embedding_tool_contacts": 0,
                       "gpu_hours": 0.0},
    })
    write_manifest(OUT_DIR)
    print(f"wrote {OUT_DIR / 'key-space-coherence.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
