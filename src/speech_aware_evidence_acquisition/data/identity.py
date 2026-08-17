"""Cross-layer sample/segment identity for this study's speech carriers (E0 D1).

The three core carriers (earnings21-original, earnings22-original, conec) each
materialize several *layers* that must name the same samples: audio media, tabular
metadata, reference transcripts and (for ConEC) per-call context artifacts. D1
closes when every layer of one such carrier resolves to one deterministic identity
set and the cross-layer relations are machine-checked and receipted.

Two bounded-discovery-probe carriers (SLURP, Audio2Tool -- 2026-08-15 owner
amendment) are admitted with a deliberately NARROWER, single-layer MEDIA identity
closure only (:func:`slurp_layers`/:func:`audio2tool_layers`): each carrier's own
governed metadata (SLURP's ``annotation-receipt.json``) or frozen probe-sample
receipt (Audio2Tool's ``docs/receipts/probe-samples/r1-audio2tool-sample.json``)
already IS the sample universe's identity authority; D1's job for these two is
the one thing neither already does -- bind a fresh re-hash of the real audio
bytes on disk to each sample id, exactly the byte-identity guarantee the three
core carriers' own media layer gives. See each function's own docstring for its
carrier's scope.

Receipts carry only sample IDs, counts, byte sizes and SHA-256 digests — never
transcript, annotation or context *content* (E0 is model-free and the runtime
information boundary applies to derived artifacts as well).
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping


class IdentityError(RuntimeError):
    """A carrier layer is missing, unreadable or violates a hard identity invariant."""


@dataclass(frozen=True)
class FileFact:
    """Identity-grade facts about one layer file: size and content digest only."""

    bytes: int
    sha256: str


@dataclass
class Layer:
    """One identity layer: a deterministic mapping from sample ID to facts.

    ``extras`` lists directory entries that are not layer files (READMEs, stray
    auxiliary files); they are excluded from identity but never silently dropped —
    the D1 receipt shows them.
    """

    name: str
    ids: tuple[str, ...]
    files: Mapping[str, FileFact] = field(default_factory=dict)
    extras: tuple[str, ...] = ()

    def ids_sha256(self) -> str:
        joined = "\n".join(self.ids).encode("utf-8")
        return hashlib.sha256(joined).hexdigest()

    def manifest(self) -> list[dict[str, object]]:
        return [
            {"id": sample_id, "bytes": fact.bytes, "sha256": fact.sha256}
            for sample_id, fact in sorted(self.files.items())
        ]

    def manifest_sha256(self) -> str:
        lines = "\n".join(
            f"{sample_id},{fact.bytes},{fact.sha256}"
            for sample_id, fact in sorted(self.files.items())
        ).encode("utf-8")
        return hashlib.sha256(lines).hexdigest()

    def total_bytes(self) -> int:
        return sum(fact.bytes for fact in self.files.values())


def hash_file(path: Path) -> FileFact:
    digest = hashlib.sha256()
    size = 0
    try:
        with Path(path).open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as error:
        raise IdentityError(f"cannot read layer file {path}: {error}") from error
    return FileFact(bytes=size, sha256=digest.hexdigest())


def _dir_layer(name: str, directory: Path, strip: tuple[str, ...]) -> Layer:
    """Build a layer from one flat directory; IDs are file names minus ``strip`` suffixes.

    A file that does not end with one of the ``strip`` suffixes is not a layer file:
    it is recorded under ``extras`` (visible in the receipt), never treated as a
    sample and never silently dropped.
    """

    if not directory.is_dir():
        raise IdentityError(f"layer {name!r}: directory missing: {directory}")
    files: dict[str, FileFact] = {}
    extras: list[str] = []
    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            # Subdirectory or dangling symlink: not a layer file, but visible.
            extras.append(entry.name)
            continue
        if entry.name.startswith("."):
            extras.append(entry.name)
            continue
        matched = next((suffix for suffix in strip if entry.name.endswith(suffix)), None)
        if matched is None:
            extras.append(entry.name)
            continue
        sample_id = entry.name[: -len(matched)]
        if not sample_id:
            raise IdentityError(f"layer {name!r}: empty sample id from {entry.name!r}")
        if sample_id in files:
            raise IdentityError(f"layer {name!r}: duplicate sample id {sample_id!r}")
        files[sample_id] = hash_file(entry)
    if not files:
        raise IdentityError(f"layer {name!r}: no layer files under {directory}")
    return Layer(name=name, ids=tuple(sorted(files)), files=files, extras=tuple(extras))


def _explicit_media_layer(name: str, entries: Iterable[tuple[str, Path]]) -> Layer:
    """Build a layer from an explicit ``(sample_id, absolute_path)`` sequence.

    Unlike :func:`_dir_layer` (every file directly under one flat directory),
    this is for carriers whose per-sample media is not addressable by listing
    a directory: SLURP resolves samples through governed jsonl metadata into a
    shared ``slurp_real``/``slurp_synth`` audio tree that also holds files for
    OTHER splits/sentences; Audio2Tool resolves samples through a frozen
    probe-sample receipt into a much larger per-tier manifest tree. Both
    require enumerating exactly the caller-resolved sample set, never a
    directory listing. Same duplicate-id/empty-set fail-closed discipline as
    :func:`_dir_layer`; ``extras`` is always empty here since there is no
    directory listing to report stray entries from."""

    files: dict[str, FileFact] = {}
    for sample_id, path in entries:
        if not sample_id:
            raise IdentityError(f"layer {name!r}: empty sample id")
        if sample_id in files:
            raise IdentityError(f"layer {name!r}: duplicate sample id {sample_id!r}")
        files[sample_id] = hash_file(Path(path))
    if not files:
        raise IdentityError(f"layer {name!r}: no layer files")
    return Layer(name=name, ids=tuple(sorted(files)), files=files)


def _csv_layer(name: str, path: Path, id_column: str) -> Layer:
    if not path.is_file():
        raise IdentityError(f"layer {name!r}: metadata file missing: {path}")
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or id_column not in reader.fieldnames:
                raise IdentityError(
                    f"layer {name!r}: column {id_column!r} not in {reader.fieldnames}"
                )
            ids = []
            for row_number, row in enumerate(reader, start=2):
                raw = row[id_column]
                if raw is None:
                    raise IdentityError(
                        f"layer {name!r}: malformed row {row_number} in {path} "
                        f"(missing {id_column!r} value)"
                    )
                ids.append(str(raw).strip())
    except (OSError, UnicodeError, csv.Error) as error:
        raise IdentityError(f"layer {name!r}: cannot read {path}: {error}") from error
    if not ids or any(not value for value in ids):
        raise IdentityError(f"layer {name!r}: empty or blank sample ids in {path}")
    if len(set(ids)) != len(ids):
        raise IdentityError(f"layer {name!r}: duplicate sample ids in {path}")
    return Layer(name=name, ids=tuple(sorted(ids)), files={})


def relation(left: Layer, right: Layer) -> dict[str, object]:
    """Set relation between two layers, receipt-ready (IDs capped for readability)."""

    left_set, right_set = set(left.ids), set(right.ids)
    left_only = sorted(left_set - right_set)
    right_only = sorted(right_set - left_set)
    if not left_only and not right_only:
        kind = "equal"
    elif not left_only:
        kind = "left_subset_of_right"
    elif not right_only:
        kind = "right_subset_of_left"
    elif left_set & right_set:
        kind = "overlap"
    else:
        kind = "disjoint"
    return {
        "left": left.name,
        "right": right.name,
        "relation": kind,
        "intersection": len(left_set & right_set),
        "left_only_count": len(left_only),
        "right_only_count": len(right_only),
        "left_only_ids": left_only[:20],
        "right_only_ids": right_only[:20],
    }


def require_equal(left: Layer, right: Layer) -> None:
    if set(left.ids) != set(right.ids):
        facts = relation(left, right)
        raise IdentityError(
            f"identity invariant violated: layers {left.name!r} and {right.name!r} must "
            f"name the same samples; left_only={facts['left_only_ids']} "
            f"right_only={facts['right_only_ids']}"
        )


def require_subset(small: Layer, big: Layer) -> None:
    missing = sorted(set(small.ids) - set(big.ids))
    if missing:
        raise IdentityError(
            f"identity invariant violated: every {small.name!r} sample must appear in "
            f"{big.name!r}; missing={missing[:20]}"
        )


def earnings21_layers(root: Path) -> dict[str, Layer]:
    """Layers of ``earnings21-original``: media, file metadata, NLP references, WER tags."""

    return {
        "media": _dir_layer("media", root / "media", (".mp3",)),
        "file_metadata": _csv_layer(
            "file_metadata", root / "earnings21-file-metadata.csv", "file_id"
        ),
        "nlp_references": _dir_layer(
            "nlp_references", root / "transcripts" / "nlp_references", (".nlp",)
        ),
        "wer_tags": _dir_layer(
            "wer_tags", root / "transcripts" / "wer_tags", (".wer_tag.json",)
        ),
        "normalizations": _dir_layer(
            "normalizations", root / "transcripts" / "normalizations", (".norm.json",)
        ),
    }


def earnings22_layers(root: Path) -> dict[str, Layer]:
    """Layers of ``earnings22-original``: media, metadata rows, both reference layers."""

    return {
        "media": _dir_layer("media", root / "media", (".mp3",)),
        "file_metadata": _csv_layer("file_metadata", root / "metadata.csv", "File ID"),
        "nlp_references": _dir_layer(
            "nlp_references", root / "transcripts" / "nlp_references", (".nlp",)
        ),
        "force_aligned_nlp_references": _dir_layer(
            "force_aligned_nlp_references",
            root / "transcripts" / "force_aligned_nlp_references",
            (".aligned.nlp",),
        ),
        "subset10_media": _dir_layer("subset10_media", root / "subset10" / "media", (".mp3",)),
    }


def conec_layers(root: Path) -> dict[str, Layer]:
    """ConEC layers for the Earnings21 side: contexts, references, timestamps, WER tags.

    The ConEC Earnings22 side ships PDFs under a different structure; it is counted in
    the D1 receipt but carries no per-sample identity contract yet (frozen at R0 when
    an experiment first consumes it).
    """

    e21 = root / "earnings21"
    return {
        "e21_contexts": _dir_layer("e21_contexts", e21 / "contexts", (".txt",)),
        "e21_nlp_references": _dir_layer(
            "e21_nlp_references", e21 / "transcripts" / "nlp_references", (".nlp",)
        ),
        "e21_timestamps": _dir_layer(
            "e21_timestamps", e21 / "transcripts" / "timestamps", (".nlp",)
        ),
        "e21_wer_tags": _dir_layer(
            "e21_wer_tags", e21 / "transcripts" / "wer_tags", (".wer_tag.json",)
        ),
    }


def slurp_layers(
    lock: Mapping[str, object], root: Path, *, split_id: str = "devel"
) -> dict[str, Layer]:
    """SLURP layers: per-sample MEDIA identity for the flight-addressable
    split (module docstring's "deliberately narrower" scope).

    SLURP's own governed metadata already carries a reconciliation receipt
    (``datasets/slurp/annotation-receipt.json``, ``data.slurp`` module
    docstring) that verified every ``recordings[]`` reference against the
    flac tree upstream (100%, 141,648/141,648 unique recording refs across
    all four splits) -- D1 does not re-derive a second independent metadata
    layer here; it re-hashes the real flac bytes on disk fresh, exactly the
    byte-identity guarantee ``earnings21_layers``/``earnings22_layers`` give
    their own media layer, keyed by the SAME ``sample_id`` shape
    :func:`speech_aware_evidence_acquisition.data.slurp.load_slurp_split`
    already returns (``slurp:<split>:<slurp_id>:<recording stem>``).

    ``split_id`` defaults to, and this study's D1 closure only ever covers,
    ``devel`` -- the ONLY split this study's own ``CLAUDE.md`` research
    boundary and ``data.slurp`` split discipline make addressable without an
    explicit ``allow_heldout``/``allow_synthetic`` opt-in (``test`` is held
    out; ``train``/``train_synthetic`` are roster-construction-only, never a
    probe target). Coverage is the FULL split (every devel recording),
    mirroring the three core carriers' own "cover a full split" rule -- never
    a partial subset silently narrowed here."""

    from .slurp import load_slurp_split

    records = load_slurp_split(lock, root, split_id)
    entries = ((record.sample_id, Path(root) / record.media_relpath) for record in records)
    return {"media": _explicit_media_layer("media", entries)}


def audio2tool_layers(lock: Mapping[str, object], root: Path, *, repo_root: Path | None = None) -> dict[str, Layer]:
    """Audio2Tool layers: per-sample MEDIA identity for the frozen 400-item
    discovery split (module docstring's "deliberately narrower" scope).

    The sample universe IS the frozen probe-sample receipt
    (``docs/receipts/probe-samples/r1-audio2tool-sample.json``,
    ``split_role == "discovery"``, 400 items across 8 tiers) --
    ``data.audio2tool`` module docstring: pre-registration means no run may
    ever resolve Audio2Tool items outside it, so D1 covers exactly, and only,
    what a flight can ever touch. Each sample's WAV bytes are re-hashed fresh
    from disk (the receipt/manifest chain only carries a claimed ``duration``,
    never a byte digest, so nothing upstream of this function already proves
    byte identity the way SLURP's own reconciliation receipt does).

    ``repo_root`` is threaded straight to
    :func:`speech_aware_evidence_acquisition.data.audio2tool.load_audio2tool`
    (default: this study checkout, where the committed receipt lives) so a
    synthetic test world can point it at its own receipt tree without
    touching the real one."""

    from .audio2tool import load_audio2tool

    refs = load_audio2tool(lock, root, repo_root=repo_root)
    entries = ((ref.sample_id, Path(root) / ref.media_relpath) for ref in refs)
    return {"media": _explicit_media_layer("media", entries)}


def layer_report(layers: Mapping[str, Layer], embed_manifest: bool = True) -> dict[str, object]:
    report: dict[str, object] = {}
    for name, layer in layers.items():
        entry: dict[str, object] = {
            "count": len(layer.ids),
            "ids_sha256": layer.ids_sha256(),
        }
        if layer.files:
            entry["total_bytes"] = layer.total_bytes()
            entry["manifest_sha256"] = layer.manifest_sha256()
            if embed_manifest:
                entry["manifest"] = layer.manifest()
        if layer.extras:
            entry["excluded_non_layer_files"] = list(layer.extras)
        report[name] = entry
    return report


def relations_report(pairs: Iterable[tuple[Layer, Layer]]) -> list[dict[str, object]]:
    return [relation(left, right) for left, right in pairs]
