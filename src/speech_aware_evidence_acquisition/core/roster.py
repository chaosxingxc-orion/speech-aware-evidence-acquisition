"""One carrier-agnostic roster freezer (consolidation slice C4d).

Roster/identity has historically been implemented three times in this
repository: :func:`speech_aware_evidence_acquisition.data.splits
.split_identity_hash` (the canonical E0 convention -- SHA-256 over the
LF-joined, sorted, carrier-prefixed sample ids, ``f"{lock_key}/{sample_id}"``,
no trailing newline), :func:`speech_aware_evidence_acquisition.reproduction
.sampling.split_identity_hash` (the same formula plus a duplicate-key
refusal), and an inline ``hashlib.sha256("\n".join(keys).encode("ascii"))``
call in ``analysis.a2t_fresh_agentloop_roster.build_receipt`` and its
siblings, where ``keys`` is the already carrier-prefixed ``key`` field
(``"audio2tool:tier1_direct:000074"``) rather than a re-prefixed sample id.
All three compute the SAME digest for the same sorted, ASCII, carrier-
prefixed id list -- see the identity-equivalence test in
``tests/unit/test_core_roster.py``. This module uses ONLY the canonical
``data.splits`` pair (:func:`speech_aware_evidence_acquisition.data.splits
.split_identity_hash` + :func:`speech_aware_evidence_acquisition.data.splits
.prefixed`); it never re-derives the hash formula.

Roster construction itself has ALSO been implemented repeatedly, once per
carrier probe (``analysis.a2t_fresh_agentloop_roster.select_fresh_roster``,
``analysis.a2t_factorial_roster.select_factorial_roster``,
``analysis.a2t_native_schema_roster.select_native_schema_roster``,
``analysis.a2t_canonical_family_secondary_roster.select_rows``,
``scripts.build_probe_samples`` via ``reproduction.sampling
.stratified_sample``). Each one is: (1) partition a candidate population
into strata, (2) draw a deterministic, seeded, stratified sample, (3) refuse
a stratum that cannot fill its quota, (4) refuse a candidate whose identity
(or a twin identity -- a shared query block, a shared normalized-text
equivalence class) has already been used or excluded, (5) freeze the result
into a receipt carrying a ``split_identity_hash``. :func:`freeze_roster` is
the ONE function that does all five steps for any carrier.

Deterministic seeded stratified draw (the rule, stated once)
--------------------------------------------------------------
Strata are processed in ascending name order. Within each stratum, eligible
candidates are first sorted by ``sample_id`` (so the draw does not depend on
input order), then a SINGLE ``random.Random(seed)`` instance -- shared and
advanced across every stratum, in that same ascending order -- shuffles the
sorted list in place (``rng.shuffle``). The shuffled order is then walked
and candidates are accepted until the stratum's quota is filled, skipping
any candidate whose exclusion group has already been used by an earlier
acceptance (see below). This differs, by design, from
``reproduction.sampling.stratified_sample``'s per-stratum-KEYED seeding
(``random.Random(f"{seed}:{stratum_name}")``, which isolates each stratum's
draw from the others): here one rng instance is shared, so changing one
stratum's candidate pool size can shift the draws of strata processed after
it. Both conventions are deterministic; this module picks the single-rng
convention and documents it so a caller is never surprised.

Group-uniqueness and exclusion
-------------------------------
``exclude_sample_ids`` removes candidates from the eligible pool outright.
``exclude_groups`` (sample_id -> group key, e.g. a query block or a
normalized-text equivalence class) does two more things: (a) any candidate
whose group equals the group of an EXCLUDED sample id is also removed from
the eligible pool (a "twin" of an excluded id is excluded too), and (b)
during the draw, at most one candidate per group is EVER selected across the
whole roster (not just within one stratum) -- a candidate whose group was
already used by an earlier acceptance is skipped. Either exclusion source
can starve a stratum below its quota, which is refused exactly like an
undersized candidate pool: :class:`RosterError`, fail closed.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Collection, Mapping, Sequence

from ..data.splits import prefixed, split_identity_hash

RECEIPT_SCHEMA = "saea-roster-receipt-v1"

__all__ = [
    "RECEIPT_SCHEMA",
    "RosterError",
    "RosterItem",
    "freeze_roster",
    "verify_roster",
    "write_roster",
    "read_roster",
    "hash_matches_legacy_receipt",
]


class RosterError(ValueError):
    """A roster cannot be frozen, verified, or read -- fail closed."""


@dataclass(frozen=True)
class RosterItem:
    """One candidate identity: a sample id, its stratum, and audit-only extras."""

    sample_id: str
    stratum: str
    extra: Mapping[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        if not isinstance(self.sample_id, str) or not self.sample_id:
            raise RosterError("roster item sample_id must be non-empty text")
        if not isinstance(self.stratum, str) or not self.stratum:
            raise RosterError(
                f"roster item {self.sample_id!r} stratum must be non-empty text"
            )
        if not isinstance(self.extra, Mapping):
            raise RosterError(f"roster item {self.sample_id!r} extra must be a mapping")
        overlap = set(self.extra) & {"sample_id", "stratum"}
        if overlap:
            raise RosterError(
                f"roster item {self.sample_id!r} extra fields collide with identity "
                f"fields: {sorted(overlap)}"
            )
        return {"sample_id": self.sample_id, "stratum": self.stratum, **self.extra}


def _resolve_quotas(
    per_stratum: int | Mapping[str, int], strata_present: Sequence[str]
) -> dict[str, int]:
    if isinstance(per_stratum, Mapping):
        quotas = dict(per_stratum)
        missing = set(strata_present) - set(quotas)
        if missing:
            raise RosterError(
                f"per_stratum is missing a quota for strata: {sorted(missing)}"
            )
    elif isinstance(per_stratum, bool) or not isinstance(per_stratum, int):
        raise RosterError("per_stratum must be a positive integer or a stratum->count mapping")
    else:
        if per_stratum <= 0:
            raise RosterError("per_stratum must be a positive integer")
        quotas = {stratum: per_stratum for stratum in strata_present}
    for stratum, quota in quotas.items():
        if isinstance(quota, bool) or not isinstance(quota, int) or quota <= 0:
            raise RosterError(f"per_stratum quota for {stratum!r} must be a positive integer")
    return quotas


def freeze_roster(
    *,
    carrier_lock_key: str,
    candidates: Sequence[RosterItem],
    per_stratum: int | Mapping[str, int],
    seed: int,
    split_role: str,
    exclude_sample_ids: Collection[str] = (),
    exclude_groups: Mapping[str, str] | None = None,
    roster_id: str,
) -> dict[str, object]:
    """Freeze a deterministic, seeded, stratified roster receipt.

    See the module docstring for the exact draw rule and the exclusion
    semantics. Refuses (raises :class:`RosterError`) when a stratum cannot
    fill its quota after exclusion and group-uniqueness filtering, whatever
    the root cause (too few candidates, an excluded id, or a group already
    used). Never mutates ``candidates``.
    """

    if not isinstance(carrier_lock_key, str) or not carrier_lock_key:
        raise RosterError("carrier_lock_key must be non-empty text")
    if not isinstance(split_role, str) or not split_role:
        raise RosterError("split_role must be non-empty text")
    if not isinstance(roster_id, str) or not roster_id:
        raise RosterError("roster_id must be non-empty text")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise RosterError("seed must be an integer")
    if isinstance(candidates, (str, bytes)):
        raise RosterError("candidates must be a sequence of RosterItem")
    rows = tuple(candidates)
    if not rows or any(not isinstance(row, RosterItem) for row in rows):
        raise RosterError("candidates must be a non-empty sequence of RosterItem")
    for row in rows:
        row.as_dict()  # validates shape; raises RosterError on a malformed item
    sample_ids_all = [row.sample_id for row in rows]
    if len(sample_ids_all) != len(set(sample_ids_all)):
        raise RosterError("candidates contain a duplicate sample_id")

    excluded_ids: set[str] = set()
    for value in exclude_sample_ids:
        if not isinstance(value, str) or not value:
            raise RosterError("exclude_sample_ids must contain non-empty text")
        excluded_ids.add(value)

    groups: dict[str, str] = dict(exclude_groups) if exclude_groups is not None else {}
    excluded_group_keys = {groups[sid] for sid in excluded_ids if sid in groups}

    eligible = [
        row
        for row in rows
        if row.sample_id not in excluded_ids
        and groups.get(row.sample_id) not in excluded_group_keys
    ]
    excluded_count = len(rows) - len(eligible)

    by_stratum: dict[str, list[RosterItem]] = {}
    for row in eligible:
        by_stratum.setdefault(row.stratum, []).append(row)
    # Strata are the ones declared by the FULL candidate population, not just
    # what survives exclusion -- a stratum that exclusion empties out entirely
    # must still be refused for failing to fill its quota, not silently
    # dropped from the receipt.
    all_strata = sorted({row.stratum for row in rows})
    quotas = _resolve_quotas(per_stratum, all_strata)

    rng = random.Random(seed)
    used_groups: set[str] = set()
    selected: list[RosterItem] = []
    for stratum in sorted(quotas):
        quota = quotas[stratum]
        pool = sorted(by_stratum.get(stratum, ()), key=lambda item: item.sample_id)
        rng.shuffle(pool)
        chosen: list[RosterItem] = []
        for item in pool:
            group = groups.get(item.sample_id)
            if group is not None and group in used_groups:
                continue
            chosen.append(item)
            if group is not None:
                used_groups.add(group)
            if len(chosen) == quota:
                break
        if len(chosen) != quota:
            raise RosterError(
                f"stratum {stratum!r} cannot fill its quota of {quota}: only "
                f"{len(chosen)} eligible, group-unique candidates are available"
            )
        selected.extend(chosen)

    items = sorted((row.as_dict() for row in selected), key=lambda d: str(d["sample_id"]))
    ids = [str(item["sample_id"]) for item in items]
    strata_counts = dict(Counter(str(item["stratum"]) for item in items))
    identity_hash = split_identity_hash(prefixed(carrier_lock_key, ids))

    return {
        "schema": RECEIPT_SCHEMA,
        "roster_id": roster_id,
        "carrier_lock_key": carrier_lock_key,
        "split_role": split_role,
        "seed": seed,
        "per_stratum": dict(sorted(quotas.items())),
        "strata_counts": dict(sorted(strata_counts.items())),
        "items": items,
        "excluded_count": excluded_count,
        "split_identity_hash": identity_hash,
    }


def verify_roster(receipt: Mapping[str, object]) -> str:
    """Recompute a receipt's ``split_identity_hash`` and check it; fail closed."""

    if not isinstance(receipt, Mapping):
        raise RosterError("roster receipt must be a mapping")
    carrier_lock_key = receipt.get("carrier_lock_key")
    if not isinstance(carrier_lock_key, str) or not carrier_lock_key:
        raise RosterError("roster receipt carrier_lock_key must be non-empty text")
    items = receipt.get("items")
    if not isinstance(items, list) or not items:
        raise RosterError("roster receipt items must be a non-empty list")
    recorded = receipt.get("split_identity_hash")
    if not isinstance(recorded, str) or not recorded:
        raise RosterError("roster receipt split_identity_hash must be non-empty text")
    ids: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise RosterError(f"roster receipt items[{index}] must be an object")
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise RosterError(
                f"roster receipt items[{index}].sample_id must be non-empty text"
            )
        ids.append(sample_id)
    if len(set(ids)) != len(ids):
        raise RosterError("roster receipt items contain a duplicate sample_id")
    measured = split_identity_hash(prefixed(carrier_lock_key, ids))
    if measured != recorded:
        raise RosterError(
            f"roster receipt split_identity_hash mismatch: recorded {recorded!r}, "
            f"recomputed {measured!r}"
        )
    return measured


def write_roster(receipt: Mapping[str, object], path: Path) -> str:
    """Write a verified roster receipt as canonical JSON; refuse to overwrite."""

    target = Path(path)
    if target.exists():
        raise RosterError(f"refusing to overwrite an existing roster receipt: {target}")
    verify_roster(receipt)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    target.write_text(text, encoding="utf-8", newline="\n")
    return text


def read_roster(path: Path) -> dict[str, object]:
    """Read and verify a roster receipt; fail closed on a tampered file."""

    source = Path(path)
    document = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RosterError(f"roster receipt at {source} is not a JSON object")
    verify_roster(document)
    return document


def hash_matches_legacy_receipt(receipt_path: Path) -> bool:
    """Check a pre-existing (non ``saea-roster-receipt-v1``) receipt's identity.

    Every roster receipt this repository has committed so far freezes
    ``split_identity_hash`` over its items' already carrier-prefixed ``key``
    field (e.g. ``"audio2tool:tier1_direct:000074"``), sorted and LF-joined --
    NOT over a re-prefixed ``sample_id`` (``data.splits.prefixed`` would add
    a SECOND prefix on top of ``key``). This function reproduces that exact
    convention: it reads ``item["key"]`` for every item and calls the
    canonical :func:`speech_aware_evidence_acquisition.data.splits
    .split_identity_hash` directly, with no re-prefixing. It never modifies
    the receipt. A receipt built on a different id convention (for example,
    ``A2T-CANONICAL-FAMILY-SECONDARY-FIXED8.json``, whose recorded hash is
    over ``f"audio2tool/{sample_id}"`` rather than ``item["key"]``) will
    legitimately return ``False`` here -- see the compatibility table in the
    C4d consolidation report for which receipts diverge and how.
    """

    path = Path(receipt_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise RosterError(f"{path} is not a JSON object")
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise RosterError(f"{path} has no items to check")
    recorded = document.get("split_identity_hash")
    if not isinstance(recorded, str) or not recorded:
        raise RosterError(f"{path} has no split_identity_hash to check")
    keys: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise RosterError(f"{path} items[{index}] is not an object")
        key = item.get("key")
        if not isinstance(key, str) or not key:
            raise RosterError(f"{path} items[{index}] has no 'key' identity field")
        keys.append(key)
    return split_identity_hash(keys) == recorded
