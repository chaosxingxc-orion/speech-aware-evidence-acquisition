"""Acoustic exemplar banks: the ``exemplar_manifest_id`` optional
baseline-config key + fail-closed loading of an offline-materialized
exemplar-pairs manifest into a per-sample (audio exemplar, label) bank.

Prep infrastructure for a future "M-C-prime" arm (see ``docs/exposure-
ledger.md``'s ``SAEA-SMOKE-mm2`` row): this module resolves and verifies the
bank, and threads it through ``core.base.SampleContext``/``core.policies.
build_arm_payload`` exactly the way evidence already flows. The D2-frozen
arms ``exemplar-context`` and ``fixed-legal-context-replay``
(``e0.d2_leakage.ARM_VISIBLE_FIELDS``, 2026-08-13) declare an
``exemplar_bank`` field; ``build_arm_payload`` still fails closed for every
OTHER arm registered today (``core.policies`` module comment). Wire format
target: ``core.model.transport``'s
``"evidence-first-system-v3"`` prompt order, whose tier-2 ``exemplar_bank``
payload field is exactly a list of ``{"media_relpath": ..., "label": ...}``
mappings (``core.model.transport._exemplar_bank_entry``).

Manifest source: an offline materializer (mirroring ``scripts/
materialize_candidates.py``'s pattern for ``derived-candidates`` evidence)
writes ``$SPEECHRL_DATA_DIR/derived/exemplar-pairs/<manifest_id>/
manifest.json`` plus one ``<sample_id>/<term>.wav`` per located exemplar
(the real ``mc2-v1`` manifest, built by ledger row ``SAEA-TOOL-lexicon-v1``,
has this exact shape). Per (sample_id, term) entry the manifest records a
``status`` of ``"found"``, ``"alignment-rejected"`` or
``"no-cross-call-occurrence"``; only ``"found"`` entries -- each carrying the
cut WAV's own sha256 as ``span_sha256`` -- ever enter a bank. A sample with
zero "found" terms gets an EMPTY bank (legal: ``core.model.transport``'s v3
layout reduces an empty bank to exactly v2's shape for that sample).

Key legality (deliverable 1): ``exemplar_manifest_id`` is legal only when the
composed config's ``prompt_order`` is ``"evidence-first-system-v3"`` -- the
only prompt order whose transport accepts an ``exemplar_bank`` payload field
at all. A baseline fragment cannot check this alone: ``prompt_order`` is a
MODEL-fragment key and ``exemplar_manifest_id`` a BASELINE-fragment key, and
``core.config.compose`` merges every fragment's top-level keys into ONE flat
mapping before either is read -- so the one seam where both are visible is
the composed config's own ``values`` mapping (the SAME flat dict ``core.
driver.cli._cli_run`` hands to both ``TRANSPORTS.resolve(...)`` and
``run_experiment``). :func:`assert_exemplar_manifest_id_legal` is therefore
called once, early, in ``core.driver.run_experiment`` -- the same "resolved
and validated HERE, before any other per-run work" placement ``core.
evidence.assert_evidence_materialization_id_legal`` already established for
its own (differently-scoped) key.

Absent key: zero behaviour change -- no manifest load, no bank resolution,
no ``exemplar_bank`` payload field on any request, no new trace record.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

EXEMPLAR_MANIFEST_SCHEMA = "saea-mc2-exemplar-pairs-manifest-v1"
_KNOWN_STATUSES = ("found", "alignment-rejected", "no-cross-call-occurrence")


class ExemplarError(RuntimeError):
    """An exemplar manifest is missing/malformed, or a bank cannot be verified."""


def resolve_exemplar_manifest_id(values: Mapping[str, object]) -> str | None:
    """The optional ``exemplar_manifest_id`` baseline-config key. ``None``
    when the key is entirely absent (module docstring: zero behaviour
    change) -- never a code default silently applied. A present value must
    be a non-empty string."""

    if "exemplar_manifest_id" not in values:
        return None
    value = values["exemplar_manifest_id"]
    if not isinstance(value, str) or not value:
        raise ExemplarError(
            f"config exemplar_manifest_id must be a non-empty string, got {value!r}"
        )
    return value


def assert_exemplar_manifest_id_legal(values: Mapping[str, object]) -> None:
    """Key-legality matrix for ``exemplar_manifest_id`` (module docstring):
    legal ONLY WITH the composed config's ``prompt_order`` set to
    ``"evidence-first-system-v3"``. A missing ``prompt_order`` resolves to
    the same ``"system-instruction-v1"`` default ``core.model.transport.
    _llama_server_factory`` itself applies, so an absent key is refused
    exactly like an explicit non-v3 order -- never silently legal."""

    manifest_id = resolve_exemplar_manifest_id(values)
    if manifest_id is None:
        return
    prompt_order = values.get("prompt_order", "system-instruction-v1")
    if prompt_order != "evidence-first-system-v3":
        raise ExemplarError(
            "config exemplar_manifest_id requires the model fragment's prompt_order "
            "to be 'evidence-first-system-v3' (the only prompt order whose transport "
            f"accepts an exemplar_bank payload field), got prompt_order={prompt_order!r}"
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_path(root: Path, manifest_id: str) -> Path:
    return Path(root) / "derived" / "exemplar-pairs" / manifest_id / "manifest.json"


def _exemplar_wav_path(root: Path, manifest_id: str, sample_id: str, term: str) -> Path:
    return Path(root) / "derived" / "exemplar-pairs" / manifest_id / sample_id / f"{term}.wav"


def _exemplar_wav_relpath(manifest_id: str, sample_id: str, term: str) -> str:
    # Convention-built, never trusted off the manifest's own (absolute,
    # $SPEECHRL_DATA_DIR-rooted) "exemplar_wav" field -- the same "construct
    # the path ourselves" discipline core.evidence._derived_candidates
    # applies to its own materializer output, rather than trusting a
    # manifest-supplied path string.
    return f"derived/exemplar-pairs/{manifest_id}/{sample_id}/{term}.wav"


@dataclass(frozen=True)
class ExemplarManifest:
    """One loaded, verified exemplar-pairs manifest (module docstring)."""

    manifest_id: str
    sha256: str
    banks: Mapping[str, tuple[dict[str, str], ...]]


def load_exemplar_manifest(root: Path, manifest_id: str) -> ExemplarManifest:
    """Load ``derived/exemplar-pairs/<manifest_id>/manifest.json`` under the
    controlled data root and verify every "found" entry's WAV against the
    manifest's own ``span_sha256`` -- fail closed on a missing manifest, a
    missing/mismatched WAV, or an unrecognised per-entry ``status`` (never a
    silent skip): a bank the manifest cannot back up must never reach the
    model. Per-sample bank entries are ``{"media_relpath": ..., "label":
    ...}`` mappings, sorted by term, in exactly the shape ``core.model.
    transport``'s v3 exemplar_bank payload field expects (the transport
    itself re-sorts canonically by (label, relpath) before sending, so THIS
    order is never load-bearing for the wire bytes -- sorted here purely for
    a deterministic, testable ``ExemplarManifest.banks``)."""

    path = _manifest_path(root, manifest_id)
    if not path.is_file():
        raise ExemplarError(f"exemplar manifest missing for {manifest_id!r}: {path}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ExemplarError(f"cannot read exemplar manifest {path}: {error}") from error
    schema = document.get("schema") if isinstance(document, Mapping) else None
    if schema != EXEMPLAR_MANIFEST_SCHEMA:
        raise ExemplarError(
            f"exemplar manifest {path} has schema {schema!r}, expected "
            f"{EXEMPLAR_MANIFEST_SCHEMA!r}"
        )
    samples = document.get("samples")
    if not isinstance(samples, Mapping):
        raise ExemplarError(f"exemplar manifest {path} lacks a 'samples' mapping")
    banks: dict[str, tuple[dict[str, str], ...]] = {}
    for sample_id, terms in samples.items():
        if not isinstance(sample_id, str) or not isinstance(terms, Mapping):
            raise ExemplarError(
                f"exemplar manifest {path} sample entry {sample_id!r} must be a mapping "
                "of term -> entry"
            )
        pairs: list[dict[str, str]] = []
        for term, entry in sorted(terms.items()):
            if not isinstance(term, str) or not isinstance(entry, Mapping):
                raise ExemplarError(
                    f"exemplar manifest {path} sample {sample_id!r} term {term!r} entry "
                    "must be a mapping"
                )
            status = entry.get("status")
            if status not in _KNOWN_STATUSES:
                raise ExemplarError(
                    f"exemplar manifest {path} sample {sample_id!r} term {term!r} has "
                    f"unknown status {status!r}; known statuses: {_KNOWN_STATUSES}"
                )
            if status != "found":
                continue
            expected_sha256 = entry.get("span_sha256")
            if not isinstance(expected_sha256, str) or not expected_sha256:
                raise ExemplarError(
                    f"exemplar manifest {path} sample {sample_id!r} term {term!r} is "
                    "'found' but carries no span_sha256; refusing an unverifiable exemplar"
                )
            wav_path = _exemplar_wav_path(root, manifest_id, sample_id, term)
            if not wav_path.is_file():
                raise ExemplarError(
                    f"exemplar WAV missing for {manifest_id!r}/{sample_id!r}/{term!r}: {wav_path}"
                )
            actual_sha256 = _sha256_file(wav_path)
            if actual_sha256 != expected_sha256:
                raise ExemplarError(
                    f"exemplar WAV sha256 mismatch for {manifest_id!r}/{sample_id!r}/"
                    f"{term!r}: manifest says {expected_sha256}, file is {actual_sha256}"
                )
            pairs.append(
                {
                    "media_relpath": _exemplar_wav_relpath(manifest_id, sample_id, term),
                    "label": term,
                }
            )
        banks[sample_id] = tuple(pairs)
    return ExemplarManifest(manifest_id=manifest_id, sha256=_sha256_file(path), banks=banks)


def resolve_exemplar_bank(manifest: ExemplarManifest, sample_id: str) -> tuple[dict[str, str], ...]:
    """The sample's own exemplar bank -- an EMPTY tuple (never a KeyError)
    for a sample the manifest names no terms for at all, exactly like a
    sample whose every term is rejected/not-cross-call-occurring (module
    docstring: an empty bank is legal)."""

    return manifest.banks.get(sample_id, ())
