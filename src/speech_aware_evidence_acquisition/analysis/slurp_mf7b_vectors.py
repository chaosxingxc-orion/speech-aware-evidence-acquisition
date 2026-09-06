"""MF-7b: the shared vector-material layer of the SLURP retrieval-key audit's
GPU part.

Both encoder passes (``scripts/slurp_mf7b_lco_embedding_pass.py``,
``scripts/slurp_mf7b_nemotron_embedding_pass.py``) and the audit runner
(``scripts/run_slurp_retrieval_key_audit_v2.py``) read their inputs and write
their vectors through this one module, so a query set produced by either
encoder is byte-comparable with the other and with MF-7's own CPU sets.

Everything here is stdlib plus ``numpy`` and ``soundfile``. No model, no
network, no torch: the encoders themselves live in their own scripts, under
their own exposure-ledger rows.

THE FOUR INPUTS, all produced by earlier registered work and reused unchanged:

* ``vectors/slurp-mf7/dev-rows.jsonl`` -- MF-7's DEV-1000 roster (sample id,
  population, gold scenario/intent/entities, media relpath, audio seconds,
  the sealed draft's intent);
* ``vectors/slurp-mf7/train-facets.jsonl`` -- the 11,514 TRAIN content facets,
  each with its utterance text, TRAIN gold intent and gold slots;
* the sealed KU-S1c phase-1 draft response text, read out of that flight's own
  ``.phases.json`` (already paid for, no contact, no new exposure);
* the pinned SLURP ontology, for the 60 legal ``(scenario, action)`` pairs.

THE LABEL-TEXT RULE, fixed in the preregistration before it was built:
**``saea-mf7b-label-text-v1``** -- for intent ``(scenario, action)`` the key
text is ``f"{scenario} {action}"`` with every ``_`` replaced by a single space,
lower-cased, and no other edit. It is the label itself in words: no invented
gloss, no example filler, nothing written by an agent.

AUDIO: read with ``soundfile`` and, only if the carrier ever ships a rate other
than 16 kHz, resampled with ``librosa``. **ffmpeg is deliberately absent from
this machine and must never be installed** -- installing it would change audio
bytes and cold the feature cache.
"""

from __future__ import annotations

import hashlib
import io
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np

#: The vector interchange schema MF-7 defined; MF-7b writes the same one so the
#: audit runner consumes both generations without a code change.
VECTORS_SCHEMA = "saea-mf7-vectors-v1"

#: The producer-receipt schema MF-7's CPU passes emitted.
RECEIPT_SCHEMA = "saea-mf7-vectors-receipt-v1"

#: Identity of the label-key text rule (module docstring).
LABEL_TEXT_RULE = "saea-mf7b-label-text-v1"

#: Where MF-7 left the roster and the facets. Read-only here.
MF7_VECTORS = "vectors/slurp-mf7"

#: The sealed KU-S1c flight whose phase-1 draft text is the "state" half of a
#: speech+state query.
DRAFT_RUN = "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1"
DRAFT_ATTEMPT = "attempt-20260906T042946Z-44720f"

#: Target sample rate of the WAV handed to an audio encoder.
SAMPLE_RATE_HZ = 16_000


class VectorMaterialError(RuntimeError):
    """A malformed or missing MF-7b input."""


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path | str) -> list[dict]:
    rows: list[dict] = []
    for line in Path(path).read_text(encoding="utf-8").split("\n"):
        if line.strip():
            rows.append(json.loads(line))
    if not rows:
        raise VectorMaterialError(f"{path} is empty")
    return rows


def dev_rows(root: Path | str) -> list[dict]:
    """MF-7's DEV-1000 roster, in file order."""

    rows = read_jsonl(Path(root) / MF7_VECTORS / "dev-rows.jsonl")
    if len(rows) != 1000:
        raise VectorMaterialError(f"expected 1,000 DEV rows, got {len(rows)}")
    return rows


def train_facets(root: Path | str) -> list[dict]:
    """The 11,514 TRAIN content facets, in file order."""

    rows = read_jsonl(Path(root) / MF7_VECTORS / "train-facets.jsonl")
    if len(rows) != 11514:
        raise VectorMaterialError(f"expected 11,514 TRAIN facets, got {len(rows)}")
    return rows


def draft_texts(root: Path | str) -> dict[str, str]:
    """``sample_id -> sealed KU-S1c phase-1 draft response text``.

    The bytes were paid for by that flight; reading them adds no contact and no
    new exposure. This is the agent's own intermediate state, never a
    transcript and never gold.
    """

    path = (
        Path(root) / "runs" / DRAFT_RUN / DRAFT_ATTEMPT / f"{DRAFT_RUN}.phases.json"
    )
    document = json.loads(path.read_text(encoding="utf-8"))
    for summary in document["phases"]:
        if str(summary["controller_policy_id"]).endswith(":draft"):
            texts = {
                str(result["sample_id"]): str(result["final_response_text"])
                for result in summary["results"]
            }
            if len(texts) != 1000:
                raise VectorMaterialError(
                    f"the sealed draft phase carries {len(texts)} rows, expected 1,000"
                )
            return texts
    raise VectorMaterialError(f"{path} carries no draft phase")


def label_text(scenario: str, action: str) -> str:
    """The ``saea-mf7b-label-text-v1`` key text for one intent."""

    return f"{scenario} {action}".replace("_", " ").lower()


def label_key_texts(root: Path | str, *, lock: Mapping[str, object] | None = None
                    ) -> list[tuple[str, str]]:
    """``[(key id, key text)]`` for the 60 legal ``(scenario, action)`` pairs.

    The key id is ``label:<scenario>_<action>`` so a label key is never
    confusable with a TRAIN facet id, and the pairs come from the SAME pinned
    ontology the closed-list inventory renders.
    """

    from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_ontology

    resolved = lock if lock is not None else load_lock(umbrella_lock_path())
    ontology = load_slurp_ontology(resolved, Path(root))
    if not ontology.actions_by_scenario:
        raise VectorMaterialError("the ontology carries no actions_by_scenario pairing")
    out: list[tuple[str, str]] = []
    for scenario, actions in sorted(ontology.actions_by_scenario.items()):
        for action in sorted(actions):
            out.append((f"label:{scenario}_{action}", label_text(scenario, action)))
    if len(out) != 60:
        raise VectorMaterialError(f"expected 60 legal intents, got {len(out)}")
    return out


def read_audio_wav_bytes(path: Path | str) -> bytes:
    """One recording as 16 kHz mono PCM-16 WAV bytes, in memory.

    ``soundfile`` reads the carrier's flac; ``librosa`` resamples only if the
    file is not already at :data:`SAMPLE_RATE_HZ`. ffmpeg is never invoked.
    """

    import soundfile

    wave, sample_rate = soundfile.read(str(path), dtype="float32", always_2d=False)
    array = np.asarray(wave, dtype=np.float32)
    if array.ndim > 1:
        array = array.mean(axis=1).astype(np.float32)
    if int(sample_rate) != SAMPLE_RATE_HZ:
        import librosa

        array = librosa.resample(
            array, orig_sr=int(sample_rate), target_sr=SAMPLE_RATE_HZ
        ).astype(np.float32)
    buffer = io.BytesIO()
    soundfile.write(buffer, array, SAMPLE_RATE_HZ, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def read_audio_array(path: Path | str) -> np.ndarray:
    """One recording as a 16 kHz mono float32 array (the transformers path)."""

    import soundfile

    wave, sample_rate = soundfile.read(str(path), dtype="float32", always_2d=False)
    array = np.asarray(wave, dtype=np.float32)
    if array.ndim > 1:
        array = array.mean(axis=1).astype(np.float32)
    if int(sample_rate) != SAMPLE_RATE_HZ:
        import librosa

        array = librosa.resample(
            array, orig_sr=int(sample_rate), target_sr=SAMPLE_RATE_HZ
        ).astype(np.float32)
    return array


def write_vectors_jsonl(
    path: Path | str, ids: Sequence[str], vectors: Sequence[Sequence[float]]
) -> Path:
    """Write the one interchange schema: ``{"id": ..., "vector": [...]}``."""

    if len(ids) != len(vectors):
        raise VectorMaterialError("ids and vectors must be the same length")
    if len(set(ids)) != len(ids):
        raise VectorMaterialError("vector ids must be distinct")
    target = Path(path)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        for identifier, vector in zip(ids, vectors, strict=True):
            handle.write(
                json.dumps({"id": identifier, "vector": [float(v) for v in vector]}) + "\n"
            )
    return target


def vector_set_block(
    path: Path,
    ids: Sequence[str],
    vectors: Sequence[Sequence[float]],
    wall_seconds: float,
    *,
    extra: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """One ``sets`` entry of a ``saea-mf7-vectors-receipt-v1`` receipt."""

    matrix = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1)
    block: dict[str, object] = {
        "file": path.name,
        "count": len(ids),
        "dims": int(matrix.shape[1]) if matrix.ndim == 2 else 0,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "l2_norms": {
            "min": float(norms.min()),
            "mean": float(norms.mean()),
            "max": float(norms.max()),
        },
        "wall_seconds": wall_seconds,
        "throughput_items_per_second": (len(ids) / wall_seconds) if wall_seconds else None,
    }
    if extra:
        block.update(dict(extra))
    return block


__all__ = [
    "LABEL_TEXT_RULE",
    "RECEIPT_SCHEMA",
    "SAMPLE_RATE_HZ",
    "VECTORS_SCHEMA",
    "VectorMaterialError",
    "dev_rows",
    "draft_texts",
    "label_key_texts",
    "label_text",
    "read_audio_array",
    "read_audio_wav_bytes",
    "read_jsonl",
    "sha256_file",
    "train_facets",
    "vector_set_block",
    "write_vectors_jsonl",
]
