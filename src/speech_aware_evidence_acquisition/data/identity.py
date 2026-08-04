"""Cross-layer sample/segment identity for the three core speech carriers (E0 D1).

Each carrier materializes several *layers* that must name the same samples: audio
media, tabular metadata, reference transcripts and (for ConEC) per-call context
artifacts. D1 closes when every layer of one carrier resolves to one deterministic
identity set and the cross-layer relations are machine-checked and receipted.

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
