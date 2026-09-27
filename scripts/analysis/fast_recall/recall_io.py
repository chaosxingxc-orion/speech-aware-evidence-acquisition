"""The sealed inputs the fast-recall identity proof reads (SPEECHRL_DATA_DIR)."""
import json
import os
from pathlib import Path

DATA = Path(os.environ["SPEECHRL_DATA_DIR"])

def pkg(expected_root):
    import speech_aware_evidence_acquisition as m
    assert m.__file__.startswith(expected_root), (m.__file__, expected_root)
    return m

def load_snapshot(relpath):
    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
    return KnowledgeSnapshot.from_frozen_json(json.loads((DATA / relpath).read_text(encoding="utf-8")))

def sha(relpath):
    import hashlib
    return hashlib.sha256((DATA / relpath).read_bytes()).hexdigest()

def load_vectors(relpath, dims):
    from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_vectors
    return load_sealed_vectors(DATA / relpath, expected_sha256=sha(relpath), dimensions=dims)

def load_segments(relpath, dims):
    from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_segment_vectors
    return load_sealed_segment_vectors(DATA / relpath, expected_sha256=sha(relpath), dimensions=dims)

EXEMPLAR_SNAPSHOT = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
EXEMPLAR_FACETS = "vectors/slurp-kus3/facet-vectors.jsonl"
IB_SNAPSHOT = "knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json"
IB_FACETS = {"key-encoding": "prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl",
             "centroid-keys": "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl"}
ROSTERS = {
    "fold-a": ("vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl",
               "vectors/slurp-intent-boundaries-train-fold-a-1080-v1/query-vectors-speech-segments.jsonl"),
    "dev2000-added": ("vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl",
                      "vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl"),
    "fold-b": ("vectors/slurp-system-update-fold-b-v1/query-vectors-speech-content-v1.jsonl",
               "vectors/slurp-intent-boundaries-train-fold-b-1080-v1/query-vectors-speech-segments.jsonl"),
}
