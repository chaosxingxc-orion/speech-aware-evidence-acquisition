"""P-EMB flight orchestration -- REGISTERED probes SAEA-PROBE-pemb1-78 /
SAEA-PROBE-pemb2-552 (``bounded-discovery-probe``):
``docs/readiness/2026-08-19-pemb-preregistration-REGISTERED.md``.

Two independent, zero-generation runs over :class:`~rails.embedding_client.
EmbeddingClientProtocol` (never ``rails.core_client.CoreClient`` -- the
embedding tier speaks a different wire protocol against a different
resident server, ``rails.embedding_client`` module docstring):

- **Run A** (:func:`run_pemb1_flight`, ``RUN_A_ID``): embed the frozen 60
  SLURP devel samples' audio (bare, no prompt text) + the 18 canonical
  scenario labels as text (bare label strings) = 78 contacts. The 60-sample
  set and its ``split_identity_hash`` are the SAME frozen manifest the
  consumed P-SLU/P-KEY probes used (``configs/probes/g0-binding/
  pslu-sample-devel-n60.json``, :func:`~.pslu_flight.load_pslu_sample_manifest`
  / :func:`~.pslu_flight.select_pslu_samples`, reused directly); the 18
  labels are the roster table's own scenario keys
  (``configs/probes/g0-binding/pslu-rosters-train-only.json``,
  :func:`~.pslu_flight.load_pslu_rosters`, reused directly -- never the
  ceiling-tier ontology miner, guarded below exactly like the parent
  P-SLU/P-KEY flights).
- **Run B** (:func:`run_pemb2_flight`, ``RUN_B_ID``): embed all 400 frozen
  Audio2Tool discovery-split samples' audio + the 152 tool registry rows as
  text (``data.audio2tool.render_registry_row`` default/shipped form) = 552
  contacts.

Both runs share: one ``client.verify_media_marker()`` call before any
embed contact (fail-closed, ``rails.embedding_client`` module docstring);
per-contact fail-closed dim/finite checks (the client's own job, reused
here, never re-checked a second way); a hard, pinned
``split_identity_hash`` check (never a re-derivation); and result-set
validation (:func:`_validate_run_summary`) before returning.

Vector persistence (:func:`write_embedding_manifest` /
:func:`load_embedding_manifest`): fp32 ``.npy`` per contact under
``$SPEECHRL_DATA_DIR/derived/embeddings/<run_id>/{audio,text}/<safe id>.npy``
plus a hashed ``manifest.json`` -- mirrors ``core.exemplars``'s own
manifest-plus-sha256 discipline (schema constant, per-entry sha256, a
verified re-load that never trusts a file on presence/size alone). Derived
artifact, data root only, never committed to Git.

Zero live model contact, engineering only: every test in this module's own
suite drives ``rails.embedding_client.MockEmbeddingClient``.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from ...data.audio2tool import render_registry_row
from ..adapters.audio2tool import Audio2ToolSample
from ..adapters.slurp import SlurpSample
from ..embedding_client import EMBEDDING_DIM, EmbeddingClientProtocol, EmbeddingVector
from .pslu_flight import _source_references_ontology_miner, assert_never_calls_ontology_miner

RUN_A_ID = "SAEA-PROBE-pemb1-78"
RUN_A_AUDIO_N = 60
RUN_A_LABEL_N = 18
RUN_A_TOTAL_N = RUN_A_AUDIO_N + RUN_A_LABEL_N  # 78, matches the registered exposure row

RUN_B_ID = "SAEA-PROBE-pemb2-552"
RUN_B_AUDIO_N = 400
RUN_B_ROW_N = 152
RUN_B_TOTAL_N = RUN_B_AUDIO_N + RUN_B_ROW_N  # 552, matches the registered exposure row

# Pinned VERBATIM from docs/exposure-ledger.md's own pemb1/pemb2 rows --
# Run A reuses the SAME frozen 60-sample subset the consumed P-SLU/P-KEY
# probes used; Run B reuses the SAME frozen 400-sample Audio2Tool discovery
# split the consumed A0/a2t-pop probes used.
EXPECTED_RUN_A_SPLIT_IDENTITY_HASH = "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"
EXPECTED_RUN_B_SPLIT_IDENTITY_HASH = "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"

EMBEDDING_MANIFEST_SCHEMA = "saea-pemb-embeddings-manifest-v1"


class PembFlightError(RuntimeError):
    """A P-EMB flight input is malformed, a hard count/identity/legality
    invariant is violated, or the ontology-miner import guard tripped."""


# ---------------------------------------------------------------------------
# The ontology-miner call guard (mirrors rails.probes.pkey_flight's own
# double-guard pattern exactly: the parent's checker reused against BOTH the
# parent's own source, via assert_never_calls_ontology_miner, AND this
# module's own source below).
# ---------------------------------------------------------------------------


def _assert_this_module_never_calls_ontology_miner(source: str | None = None) -> None:
    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise PembFlightError(
            "rails.probes.pemb_flight source references load_slurp_ontology; Run A's canonical "
            "scenario labels come ONLY from configs/probes/g0-binding/pslu-rosters-train-only.json "
            "(rails.probes.pslu_flight.load_pslu_rosters)"
        )


# ---------------------------------------------------------------------------
# Split-identity pins (never recomputed -- pinned verbatim, module docstring).
# ---------------------------------------------------------------------------


def assert_run_a_split_identity_hash(split_identity_hash: str) -> None:
    if split_identity_hash != EXPECTED_RUN_A_SPLIT_IDENTITY_HASH:
        raise PembFlightError(
            f"Run A split_identity_hash {split_identity_hash!r} does not match the pinned "
            f"{EXPECTED_RUN_A_SPLIT_IDENTITY_HASH!r} (the SAME frozen 60-sample subset the "
            "consumed P-SLU/P-KEY probes used) -- fail-closed"
        )


def assert_run_b_split_identity_hash(split_identity_hash: str) -> None:
    if split_identity_hash != EXPECTED_RUN_B_SPLIT_IDENTITY_HASH:
        raise PembFlightError(
            f"Run B split_identity_hash {split_identity_hash!r} does not match the pinned "
            f"{EXPECTED_RUN_B_SPLIT_IDENTITY_HASH!r} (the SAME frozen 400-sample Audio2Tool "
            "discovery split the consumed A0/a2t-pop probes used) -- fail-closed"
        )


# ---------------------------------------------------------------------------
# Audio loading -- reuses core.model.paths' own I4 confinement rail rather
# than re-implementing path safety a second way.
# ---------------------------------------------------------------------------


def _read_audio_bytes(data_root: Path, media_relpath: str) -> bytes:
    from ...core.model import FrozenCoreError
    from ...core.model.paths import _normalized_relative_path, _resolve_confined

    root = Path(data_root)
    try:
        relative = _normalized_relative_path(media_relpath, "pemb_flight media_relpath")
        resolved = _resolve_confined(root, relative, root, "pemb_flight media_relpath", strict=True)
    except FrozenCoreError as error:
        raise PembFlightError(str(error)) from error
    return resolved.read_bytes()


# ---------------------------------------------------------------------------
# Run summary + generic result validation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PembRunSummary:
    run_id: str
    audio_vectors: tuple[EmbeddingVector, ...]
    text_vectors: tuple[EmbeddingVector, ...]


def _validate_run_summary(summary: PembRunSummary, *, expected_audio_n: int, expected_text_n: int) -> None:
    if len(summary.audio_vectors) != expected_audio_n:
        raise PembFlightError(
            f"{summary.run_id}: {len(summary.audio_vectors)} audio vector(s), expected exactly "
            f"{expected_audio_n} (fail-closed count)"
        )
    if len(summary.text_vectors) != expected_text_n:
        raise PembFlightError(
            f"{summary.run_id}: {len(summary.text_vectors)} text vector(s), expected exactly "
            f"{expected_text_n} (fail-closed count)"
        )
    for kind, vectors in (("audio", summary.audio_vectors), ("text", summary.text_vectors)):
        ids = [vector.contact_id for vector in vectors]
        if len(set(ids)) != len(ids):
            raise PembFlightError(f"{summary.run_id}: duplicate {kind} contact_id in results")
        for vector in vectors:
            if vector.kind != kind:
                raise PembFlightError(
                    f"{summary.run_id}: {kind} vector for {vector.contact_id!r} carries kind={vector.kind!r}"
                )
            if vector.dims != EMBEDDING_DIM:
                raise PembFlightError(
                    f"{summary.run_id}: {kind} vector for {vector.contact_id!r} has dim {vector.dims} "
                    f"!= pinned {EMBEDDING_DIM}"
                )


# ---------------------------------------------------------------------------
# Run A -- SLURP scenario routing.
# ---------------------------------------------------------------------------


def run_pemb1_flight(
    *,
    client: EmbeddingClientProtocol,
    samples: Sequence[SlurpSample],
    canonical_labels: Sequence[str],
    split_identity_hash: str,
    data_root: Path,
    expected_audio_n: int = RUN_A_AUDIO_N,
    expected_label_n: int = RUN_A_LABEL_N,
) -> PembRunSummary:
    """Run A: 60 audio contacts (module docstring) + ``expected_label_n``
    bare canonical-label text contacts, zero generation. ``canonical_labels``
    is the caller's own already-loaded roster-table scenario keys
    (:func:`~.pslu_flight.load_pslu_rosters` -- this function never loads
    the roster table itself, mirroring the "caller loads/derives, this
    module only resolves" split every sibling probe module uses)."""

    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    assert_run_a_split_identity_hash(split_identity_hash)

    if len(samples) != expected_audio_n:
        raise PembFlightError(
            f"Run A requires exactly {expected_audio_n} audio sample(s), got {len(samples)}"
        )
    sample_ids = [sample.sample_id for sample in samples]
    if len(set(sample_ids)) != len(sample_ids):
        raise PembFlightError("Run A: duplicate sample_id in samples")

    labels = list(canonical_labels)
    if len(labels) != expected_label_n:
        raise PembFlightError(
            f"Run A requires exactly {expected_label_n} canonical label(s), got {len(labels)}"
        )
    if len(set(labels)) != len(labels):
        raise PembFlightError("Run A: duplicate canonical label")
    for label in labels:
        if not isinstance(label, str) or not label or label != label.strip():
            raise PembFlightError(f"Run A: canonical label must be a bare, non-empty string, got {label!r}")

    client.verify_media_marker()

    audio_vectors = tuple(
        client.embed_audio(contact_id=sample.sample_id, audio_bytes=_read_audio_bytes(data_root, sample.media_relpath))
        for sample in samples
    )
    text_vectors = tuple(client.embed_text(contact_id=label, text=label) for label in labels)

    summary = PembRunSummary(run_id=RUN_A_ID, audio_vectors=audio_vectors, text_vectors=text_vectors)
    _validate_run_summary(summary, expected_audio_n=expected_audio_n, expected_text_n=expected_label_n)
    return summary


# ---------------------------------------------------------------------------
# Run B -- Audio2Tool tool routing.
# ---------------------------------------------------------------------------


def run_pemb2_flight(
    *,
    client: EmbeddingClientProtocol,
    samples: Sequence[Audio2ToolSample],
    registry_rows: Sequence[Mapping[str, str]],
    split_identity_hash: str,
    data_root: Path,
    expected_audio_n: int = RUN_B_AUDIO_N,
    expected_row_n: int = RUN_B_ROW_N,
) -> PembRunSummary:
    """Run B: 400 audio contacts + ``expected_row_n`` tool-registry-row text
    contacts (``data.audio2tool.render_registry_row`` default/shipped form,
    keyed by each row's own ``tool_name``), zero generation."""

    assert_run_b_split_identity_hash(split_identity_hash)

    if len(samples) != expected_audio_n:
        raise PembFlightError(
            f"Run B requires exactly {expected_audio_n} audio sample(s), got {len(samples)}"
        )
    sample_ids = [sample.sample_id for sample in samples]
    if len(set(sample_ids)) != len(sample_ids):
        raise PembFlightError("Run B: duplicate sample_id in samples")

    rows = list(registry_rows)
    if len(rows) != expected_row_n:
        raise PembFlightError(
            f"Run B requires exactly {expected_row_n} tool registry row(s), got {len(rows)}"
        )
    tool_names: list[str] = []
    for row in rows:
        name = row.get("tool_name")
        if not isinstance(name, str) or not name:
            raise PembFlightError(f"Run B: registry row is missing a non-empty tool_name: {row!r}")
        tool_names.append(name)
    if len(set(tool_names)) != len(tool_names):
        raise PembFlightError("Run B: duplicate tool_name across registry_rows")

    client.verify_media_marker()

    audio_vectors = tuple(
        client.embed_audio(contact_id=sample.sample_id, audio_bytes=_read_audio_bytes(data_root, sample.media_relpath))
        for sample in samples
    )
    text_vectors = tuple(
        client.embed_text(contact_id=name, text=render_registry_row(row))
        for name, row in zip(tool_names, rows)
    )

    summary = PembRunSummary(run_id=RUN_B_ID, audio_vectors=audio_vectors, text_vectors=text_vectors)
    _validate_run_summary(summary, expected_audio_n=expected_audio_n, expected_text_n=expected_row_n)
    return summary


# ---------------------------------------------------------------------------
# Vector persistence: hashed manifest + fp32 .npy per contact (module
# docstring). Reused, unmodified, by analysis.pemb_read (load side only --
# that module never writes).
# ---------------------------------------------------------------------------

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_.-]")


def _safe_filename(contact_id: str) -> str:
    """A Windows/POSIX-safe on-disk stem for ``contact_id`` -- SLURP/
    Audio2Tool sample ids carry colons (``slurp:devel:000101:...``,
    ``tier1_direct:000077``), illegal in a Windows path component. Never
    trusted for uniqueness on its own: :func:`write_embedding_manifest`
    refuses if two distinct contact ids within the same kind collide under
    this sanitization."""

    return _UNSAFE_FILENAME_CHARS.sub("_", contact_id)


@dataclass(frozen=True)
class EmbeddingManifestEntry:
    contact_id: str
    kind: str
    relpath: str
    dims: int
    sha256: str


def _npy_bytes(values: Sequence[float]) -> bytes:
    import io

    import numpy as np

    array = np.asarray(values, dtype=np.float32)
    buffer = io.BytesIO()
    np.save(buffer, array, allow_pickle=False)
    return buffer.getvalue()


def _npy_to_array(data: bytes):
    import io

    import numpy as np

    return np.load(io.BytesIO(data), allow_pickle=False)


def write_embedding_manifest(root: Path, summary: PembRunSummary) -> Path:
    """Write every vector in ``summary`` as fp32 ``.npy`` under
    ``derived/embeddings/<run_id>/{audio,text}/<safe id>.npy`` plus a
    hashed ``manifest.json`` (module docstring). Returns the manifest path.
    Derived artifact, ``root`` (the data root) only -- never Git."""

    from ...e0.artifacts import write_json_artifact

    out_dir = Path(root) / "derived" / "embeddings" / summary.run_id
    entries: list[EmbeddingManifestEntry] = []
    seen_safe: dict[tuple[str, str], str] = {}
    for kind, vectors in (("audio", summary.audio_vectors), ("text", summary.text_vectors)):
        for vector in vectors:
            safe_id = _safe_filename(vector.contact_id)
            key = (kind, safe_id)
            if key in seen_safe and seen_safe[key] != vector.contact_id:
                raise PembFlightError(
                    f"{summary.run_id}: {kind} contact ids {seen_safe[key]!r} and "
                    f"{vector.contact_id!r} both sanitize to the on-disk filename {safe_id!r} -- "
                    "refusing a filename collision"
                )
            seen_safe[key] = vector.contact_id
            relpath = f"derived/embeddings/{summary.run_id}/{kind}/{safe_id}.npy"
            path = Path(root) / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            data = _npy_bytes(vector.values)
            path.write_bytes(data)
            entries.append(
                EmbeddingManifestEntry(
                    contact_id=vector.contact_id,
                    kind=kind,
                    relpath=relpath,
                    dims=len(vector.values),
                    sha256=hashlib.sha256(data).hexdigest(),
                )
            )
    entries.sort(key=lambda entry: (entry.kind, entry.contact_id))
    document = {
        "schema": EMBEDDING_MANIFEST_SCHEMA,
        "run_id": summary.run_id,
        "dims": EMBEDDING_DIM,
        "audio_count": len(summary.audio_vectors),
        "text_count": len(summary.text_vectors),
        "entries": [
            {
                "contact_id": entry.contact_id,
                "kind": entry.kind,
                "relpath": entry.relpath,
                "dims": entry.dims,
                "sha256": entry.sha256,
            }
            for entry in entries
        ],
    }
    manifest_path = out_dir / "manifest.json"
    write_json_artifact(manifest_path, document)
    return manifest_path


@dataclass(frozen=True)
class LoadedEmbeddingManifest:
    run_id: str
    audio: Mapping[str, object]  # contact_id -> numpy.ndarray, shape (EMBEDDING_DIM,)
    text: Mapping[str, object]


def load_embedding_manifest(root: Path, run_id: str) -> LoadedEmbeddingManifest:
    """Model-free load-and-verify: every entry's own ``.npy`` is re-read and
    its sha256 re-checked against the manifest's own recorded value (never
    trusted on file presence/size alone -- mirrors ``core.exemplars.
    load_exemplar_manifest``'s discipline), plus a fresh dim/finite check
    per vector (never trusted merely because the flight checked it once at
    write time)."""

    import numpy as np

    manifest_path = Path(root) / "derived" / "embeddings" / run_id / "manifest.json"
    if not manifest_path.is_file():
        raise PembFlightError(f"embedding manifest missing for run {run_id!r}: {manifest_path}")
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PembFlightError(f"cannot read embedding manifest {manifest_path}: {error}") from error
    if not isinstance(document, Mapping):
        raise PembFlightError(f"{manifest_path}: must be a JSON object")
    if document.get("schema") != EMBEDDING_MANIFEST_SCHEMA:
        raise PembFlightError(
            f"{manifest_path}: schema must be {EMBEDDING_MANIFEST_SCHEMA!r}, got {document.get('schema')!r}"
        )
    if document.get("run_id") != run_id:
        raise PembFlightError(
            f"{manifest_path}: run_id {document.get('run_id')!r} does not match requested {run_id!r}"
        )
    if document.get("dims") != EMBEDDING_DIM:
        raise PembFlightError(f"{manifest_path}: dims {document.get('dims')!r} != pinned {EMBEDDING_DIM}")
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise PembFlightError(f"{manifest_path}: no entries")

    audio: dict[str, object] = {}
    text: dict[str, object] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise PembFlightError(f"{manifest_path}: entry is not an object: {entry!r}")
        contact_id = entry.get("contact_id")
        kind = entry.get("kind")
        relpath = entry.get("relpath")
        expected_sha256 = entry.get("sha256")
        if not isinstance(contact_id, str) or not contact_id:
            raise PembFlightError(f"{manifest_path}: entry missing non-empty contact_id: {entry!r}")
        if kind not in ("audio", "text"):
            raise PembFlightError(f"{manifest_path}: entry {contact_id!r} has unknown kind {kind!r}")
        if not isinstance(relpath, str) or not relpath:
            raise PembFlightError(f"{manifest_path}: entry {contact_id!r} missing non-empty relpath")
        if not isinstance(expected_sha256, str) or not expected_sha256:
            raise PembFlightError(f"{manifest_path}: entry {contact_id!r} missing non-empty sha256")
        bucket = audio if kind == "audio" else text
        if contact_id in bucket:
            raise PembFlightError(f"{manifest_path}: duplicate {kind} contact_id {contact_id!r}")
        vector_path = Path(root) / relpath
        if not vector_path.is_file():
            raise PembFlightError(f"{manifest_path}: vector file missing for {contact_id!r}: {vector_path}")
        data = vector_path.read_bytes()
        actual_sha256 = hashlib.sha256(data).hexdigest()
        if actual_sha256 != expected_sha256:
            raise PembFlightError(
                f"{manifest_path}: sha256 mismatch for {contact_id!r}: manifest says "
                f"{expected_sha256}, file is {actual_sha256}"
            )
        array = _npy_to_array(data)
        if array.shape != (EMBEDDING_DIM,):
            raise PembFlightError(
                f"{manifest_path}: vector for {contact_id!r} has shape {array.shape}, expected "
                f"({EMBEDDING_DIM},)"
            )
        if not np.isfinite(array).all():
            raise PembFlightError(f"{manifest_path}: vector for {contact_id!r} contains a non-finite value")
        bucket[contact_id] = array

    if document.get("audio_count") != len(audio):
        raise PembFlightError(
            f"{manifest_path}: audio_count {document.get('audio_count')!r} does not match "
            f"{len(audio)} loaded audio entries"
        )
    if document.get("text_count") != len(text):
        raise PembFlightError(
            f"{manifest_path}: text_count {document.get('text_count')!r} does not match "
            f"{len(text)} loaded text entries"
        )
    return LoadedEmbeddingManifest(run_id=run_id, audio=MappingProxyType(audio), text=MappingProxyType(text))


__all__ = [
    "EMBEDDING_MANIFEST_SCHEMA",
    "EXPECTED_RUN_A_SPLIT_IDENTITY_HASH",
    "EXPECTED_RUN_B_SPLIT_IDENTITY_HASH",
    "RUN_A_AUDIO_N",
    "RUN_A_ID",
    "RUN_A_LABEL_N",
    "RUN_A_TOTAL_N",
    "RUN_B_AUDIO_N",
    "RUN_B_ID",
    "RUN_B_ROW_N",
    "RUN_B_TOTAL_N",
    "EmbeddingManifestEntry",
    "LoadedEmbeddingManifest",
    "PembFlightError",
    "PembRunSummary",
    "assert_run_a_split_identity_hash",
    "assert_run_b_split_identity_hash",
    "load_embedding_manifest",
    "run_pemb1_flight",
    "run_pemb2_flight",
    "write_embedding_manifest",
]


# Executed at import time (mirrors rails.probes.pkey_flight's own
# module-bottom self-check): fails LOUD the moment this module is next
# imported if a future edit adds a live reference to the forbidden
# ontology miner.
assert_never_calls_ontology_miner()
_assert_this_module_never_calls_ontology_miner()
