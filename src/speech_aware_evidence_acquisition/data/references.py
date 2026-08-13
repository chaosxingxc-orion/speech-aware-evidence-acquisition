"""Scoring-side reference access. RUNTIME-FORBIDDEN.

Reads reference transcript tokens for offline scoring only. The ONLY module
allowed to import this is core/scorers.py — an AST contract test enforces
that. References never cross the runtime boundary; they meet the hypothesis
only inside the scoring phase.

R0 repair refactor stage 2 (part B): the carrier -> reference-subdir mapping
used to live here as its own ``_NLP_SUBDIR`` dict, independently maintained
in parallel with ``contracts.gate_identity``'s reference-scoped carrier set
(and, before that, ``data/loader.py``'s per-carrier media knowledge). Both
functions below now read a carrier's ``data.carriers.CarrierDescriptor``
instead; a carrier whose descriptor declares no reference layer (or that is
not registered at all) fails closed with the SAME message either way, exactly
as ``_NLP_SUBDIR.get(...) is None`` did before.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .carriers import CarrierDescriptorError, get_carrier_descriptor
from .lock import asset_dir, lock_entry


class ReferenceError(RuntimeError):
    """A reference layer is missing, malformed, or requested for an unknown carrier."""


def _reference_layout(carrier_lock_key: str):
    try:
        descriptor = get_carrier_descriptor(carrier_lock_key)
    except CarrierDescriptorError:
        descriptor = None
    if descriptor is None or descriptor.reference is None:
        raise ReferenceError(f"no reference layer registered for carrier {carrier_lock_key!r}")
    return descriptor.reference


def reference_file_relpath(
    lock: Mapping[str, object], carrier_lock_key: str, sample_id: str
) -> str:
    """The reference file's path, relative to the controlled data root -- the
    SAME relative-path convention :func:`reference_tokens` resolves
    internally (``asset_dir(...) / subdir / f"{sample_id}{extension}"``,
    where ``asset_dir`` is ``root / local_subdir``), exposed here as its own
    function so ``core.scorers``' reference-identity gate (IMPORTANT 2, R0
    repair fix-wave3, external-threat-model review round 3) can ask
    ``contracts.FrozenCoreGate.verify_reference_identity`` to re-hash EXACTLY
    the file :func:`reference_tokens` is about to read, from one shared path
    convention rather than a second, independently-drifting construction.
    Deliberately NOT routed through :func:`reference_tokens` itself (kept
    additive, not a refactor of that RUNTIME-FORBIDDEN, already-tested
    function) and deliberately NOT via ``asset_dir``'s own directory-must-
    exist check (the gate needs the RELATIVE path string to pass to its own
    ``_resolve_under``, which performs its own existence check)."""

    layout = _reference_layout(carrier_lock_key)
    entry = lock_entry(lock, carrier_lock_key)
    local_subdir = entry.get("local_subdir")
    if not isinstance(local_subdir, str) or not local_subdir:
        raise ReferenceError(
            f"asset {carrier_lock_key!r} lacks a usable local_subdir in the lock"
        )
    return f"{local_subdir.rstrip('/')}/{layout.subdir}/{sample_id}{layout.extension}"


def reference_tokens(
    lock: Mapping[str, object], root: Path, carrier_lock_key: str, sample_id: str
) -> list[str]:
    layout = _reference_layout(carrier_lock_key)
    path = asset_dir(lock, carrier_lock_key, root) / layout.subdir / f"{sample_id}{layout.extension}"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ReferenceError(f"cannot read reference {path}: {error}") from error
    if not lines:
        raise ReferenceError(f"reference {path} is empty")
    header = lines[0].split("|")
    if "token" not in header:
        raise ReferenceError(f"reference {path} lacks a 'token' column: {header}")
    column = header.index("token")
    tokens: list[str] = []
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        cells = line.split("|")
        if len(cells) <= column:
            raise ReferenceError(f"reference {path}: malformed line {number}")
        tokens.append(cells[column])
    if not tokens:
        raise ReferenceError(f"reference {path} has no token rows")
    return tokens


# ---------------------------------------------------------------------------
# Entity mentions (owner decision D-3, entity-class WER scorer admission).
# RUNTIME-FORBIDDEN, same as reference_tokens above -- these are gold
# annotations, consumed at SCORING time only, never inside a request loop.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EntityMention:
    """One entity mention: the reference-token positions sharing one
    ``wer_tags`` entity ID, plus that ID's ``entity_type`` label.

    ``token_indices`` are 0-based positions into the SAME reference token
    sequence :func:`reference_tokens` returns for the identical
    ``(carrier_lock_key, sample_id)`` pair -- the exact indexing
    :mod:`speech_aware_evidence_acquisition.scoring.wer`'s ``align`` result
    (``ref_hit_mask``) uses, once that sequence is run through
    ``scoring.normalize.tokens_v1``. Tokens sharing one entity ID are NOT
    assumed contiguous (the Earnings21 README documents non-contiguous
    entity spans explicitly) -- ``token_indices`` preserves each member
    token's own original position rather than a start/end pair. A single
    reference token MAY belong to more than one entity ID at once (nested or
    overlapping spans, e.g. a YEAR nested inside a longer DATE); it then
    contributes to every one of those mentions, unchanged from what the
    ``wer_tags`` column itself already encodes.
    """

    entity_id: str
    entity_type: str
    token_indices: tuple[int, ...]
    tokens: tuple[str, ...]


def _entity_layout(carrier_lock_key: str):
    try:
        descriptor = get_carrier_descriptor(carrier_lock_key)
    except CarrierDescriptorError:
        descriptor = None
    if descriptor is None or descriptor.entity is None:
        raise ReferenceError(f"no entity layer registered for carrier {carrier_lock_key!r}")
    if descriptor.reference is None:
        raise ReferenceError(
            f"carrier {carrier_lock_key!r} declares an entity layer but no reference layer; "
            "entity mentions are grouped from the reference file's own wer_tags column, so a "
            "reference layer is required too"
        )
    return descriptor.reference, descriptor.entity


def reference_entity_mentions(
    lock: Mapping[str, object], root: Path, carrier_lock_key: str, sample_id: str
) -> list[EntityMention]:
    """Entity mentions for one (carrier, sample), grounded in TWO gold layers:

    1. the SAME ``.nlp`` reference file :func:`reference_tokens` reads for
       this carrier/sample, this time ALSO reading its ``wer_tags`` column --
       a Python-repr list of entity-ID strings per token (e.g.
       ``"['0', '1']"``, ``"[]"``), parsed with :func:`ast.literal_eval`
       (format decision #1, owner-decisions-pending item 1, resolved by
       owner decision D-3): this is gold TEXT, not code, and
       ``literal_eval`` refuses anything that is not a Python literal, unlike
       ``eval``;
    2. the carrier's ``entity`` layout sidecar, one JSON file per sample
       (``<sample_id>.wer_tag.json``): a mapping from entity ID to
       ``{"entity_type": "..."}``, giving each grouped mention its class
       label.

    Grouping rule (format decision #2, resolved by D-3): reference tokens are
    grouped by shared entity ID, in the order they appear in the reference --
    never assumed contiguous. The token list used for grouping is the exact
    list :func:`reference_tokens` itself returns (this function calls it
    internally rather than re-deriving its own, so the two can never drift
    apart on which lines count as blank/malformed); the ``wer_tags`` column is
    then read as a SECOND, independent pass over the same file and its row
    count is asserted to match the token count -- a defensive cross-check,
    not merely an assumption.

    Only a carrier whose descriptor declares BOTH a reference layer and an
    entity layer is supported -- today, ``earnings21-original`` only (see
    :func:`speech_aware_evidence_acquisition.data.carriers.entity_scoped_carrier_lock_keys`).
    Fails closed (:class:`ReferenceError`) for any other carrier, a missing or
    malformed sidecar, a missing ``wer_tags`` column, a non-literal or
    wrong-shaped ``wer_tags`` cell, or an entity ID the sidecar never labels.

    Consumed at SCORING time only (same discipline as :func:`reference_tokens`
    -- this module is RUNTIME-FORBIDDEN, AST-enforced, module docstring).
    """

    reference_layout, entity_layout = _entity_layout(carrier_lock_key)
    tokens = reference_tokens(lock, root, carrier_lock_key, sample_id)

    ref_path = (
        asset_dir(lock, carrier_lock_key, root)
        / reference_layout.subdir
        / f"{sample_id}{reference_layout.extension}"
    )
    try:
        lines = ref_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ReferenceError(f"cannot read reference {ref_path}: {error}") from error
    header = lines[0].split("|")
    if "wer_tags" not in header:
        raise ReferenceError(f"reference {ref_path} lacks a 'wer_tags' column: {header}")
    column = header.index("wer_tags")
    per_token_entity_ids: list[list[str]] = []
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        cells = line.split("|")
        if len(cells) <= column:
            raise ReferenceError(f"reference {ref_path}: malformed line {number}")
        raw_cell = cells[column]
        try:
            parsed = ast.literal_eval(raw_cell)
        except (ValueError, SyntaxError) as error:
            raise ReferenceError(
                f"reference {ref_path}: line {number} wer_tags cell {raw_cell!r} is not a "
                f"parseable Python literal: {error}"
            ) from error
        if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
            raise ReferenceError(
                f"reference {ref_path}: line {number} wer_tags cell {raw_cell!r} must parse "
                "to a list of strings"
            )
        per_token_entity_ids.append(parsed)
    if len(per_token_entity_ids) != len(tokens):
        raise ReferenceError(
            f"reference {ref_path}: wer_tags column has {len(per_token_entity_ids)} token "
            f"row(s) but the token column has {len(tokens)}; the two passes over this file "
            "disagree on row count"
        )

    sidecar_path = (
        asset_dir(lock, carrier_lock_key, root)
        / entity_layout.subdir
        / f"{sample_id}{entity_layout.extension}"
    )
    try:
        sidecar_raw = sidecar_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ReferenceError(f"cannot read entity sidecar {sidecar_path}: {error}") from error
    try:
        sidecar = json.loads(sidecar_raw)
    except json.JSONDecodeError as error:
        raise ReferenceError(f"entity sidecar {sidecar_path} is not valid JSON: {error}") from error
    if not isinstance(sidecar, dict):
        raise ReferenceError(f"entity sidecar {sidecar_path} must be a JSON object")

    groups: dict[str, list[int]] = {}
    for index, entity_ids in enumerate(per_token_entity_ids):
        for entity_id in entity_ids:
            groups.setdefault(entity_id, []).append(index)

    mentions: list[EntityMention] = []
    for entity_id, indices in groups.items():
        type_entry = sidecar.get(entity_id)
        if not isinstance(type_entry, Mapping) or not isinstance(type_entry.get("entity_type"), str):
            raise ReferenceError(
                f"entity id {entity_id!r} (referenced by {ref_path}) has no usable "
                f"entity_type in {sidecar_path}"
            )
        mentions.append(
            EntityMention(
                entity_id=entity_id,
                entity_type=type_entry["entity_type"],
                token_indices=tuple(indices),
                tokens=tuple(tokens[index] for index in indices),
            )
        )
    mentions.sort(key=lambda mention: (mention.token_indices[0], mention.entity_id))
    return mentions
