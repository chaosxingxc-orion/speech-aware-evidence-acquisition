"""Canonical JSON + sha256 content hashing shared by every rails dataclass.

Every rails packet (``ObsPacket``, ``EvidenceSet``, ``SupplyPacket``,
``ConsumptionTrace``) is versioned and content-hashable: two packets built
independently from the same field values must hash identically, and a
single-field change anywhere in a packet's own JSON-safe view must change
the hash. This module is the ONE place canonicalization happens (stable key
order, no extraneous whitespace, UTF-8, non-ASCII preserved verbatim) so
every rails dataclass's own ``content_hash()`` reuses exactly this rule
rather than each re-implementing its own ``json.dumps`` call with slightly
different kwargs -- the same discipline ``core.config.compose``'s own
``_canonical_hash`` already applies to config fragments, reused here rather
than re-invented for the rails layer.
"""

from __future__ import annotations

import hashlib
import json
from typing import Mapping


def canonical_json_bytes(document: Mapping[str, object]) -> bytes:
    """The canonical UTF-8 byte serialization of ``document``."""

    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def content_hash(document: Mapping[str, object]) -> str:
    """SHA-256 hex digest of ``document``'s canonical JSON serialization."""

    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()
