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

import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Collection, Mapping, Sequence

from ..data.splits import prefixed, split_identity_hash

RECEIPT_SCHEMA = "saea-roster-receipt-v1"

#: The two roles a frozen roster can have (owner decision 2026-09-05).
#: ``"evaluation"`` is the historical default and the conservative one: the
#: identities are exposure, they enter the Audio2Tool exposure union, and
#: their gold labels must never be read. ``"construction"`` marks a roster
#: whose identities may be read WITH their gold -- the same legality class as
#: TRAIN gold entering a knowledge-base build -- and which the exposure union
#: therefore excludes by design. The role is a property of the ROSTER, not of
#: the split: a construction roster still carries ``split_role="discovery"``
#: (the TRAIN90 precedent), because it is drawn from discovery data.
EVALUATION_ROSTER_ROLE = "evaluation"
CONSTRUCTION_ROSTER_ROLE = "construction"
ROSTER_ROLES = frozenset({EVALUATION_ROSTER_ROLE, CONSTRUCTION_ROSTER_ROLE})

__all__ = [
    "CONSTRUCTION_ROSTER_ROLE",
    "EVALUATION_ROSTER_ROLE",
    "RECEIPT_SCHEMA",
    "ROSTER_ROLES",
    "RosterError",
    "RosterItem",
    "as_probe_sample_receipt",
    "canonical_receipt_bytes",
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
        if isinstance(quota, bool) or not isinstance(quota, int) or quota < 0:
            raise RosterError(
                f"per_stratum quota for {stratum!r} must be a non-negative integer"
            )
    # A per-stratum MAPPING may declare 0 for a stratum the candidate population
    # still contains: on a depleted pool (SLURP devel after the equal-per-scenario
    # DEV ladder drained `audio`, `alarm`, `cooking`, `music` and `takeaway`) the
    # honest quota for a scenario with no surviving candidate is zero, and forcing
    # it to one would refuse the whole roster. A flat INTEGER per_stratum still has
    # to be positive -- "draw N from every stratum" with N = 0 is a caller mistake,
    # not a statement -- and the resolved quotas must still ask for at least one
    # sample overall.
    if sum(quotas.values()) <= 0:
        raise RosterError("per_stratum quotas sum to zero: the roster would be empty")
    return quotas


def mixture_quotas(
    total: int,
    weights: Mapping[str, float],
    capacities: Mapping[str, int],
) -> dict[str, int]:
    """Per-stratum quotas that reproduce a REFERENCE mixture as closely as the
    remaining pool allows.

    ``weights`` is the mixture the roster is meant to look like -- typically
    the FULL split's own per-stratum counts, not the depleted candidate pool's
    -- and ``capacities`` is how many candidates each stratum actually still
    has after exclusion. This is the counterpart of
    :func:`_resolve_quotas`'s flat ``per_stratum`` integer and of the DEV
    ladder's equal-per-scenario ``even_allocation``: neither can express "draw
    500 devel utterances shaped like devel" once an earlier ladder rung has
    drained the small scenarios.

    The rule, stated once. A stratum whose capacity is BELOW its fair share of
    ``total`` at the reference weights is SATURATED: it takes its whole
    capacity and its shortfall is redistributed across the still-unsaturated
    strata at the same reference weights, iterated to a fixed point (each pass
    saturates at least one stratum, so it terminates). What remains is then
    apportioned by largest remainder -- floor shares first, then one seat at a
    time in descending fractional remainder with ties broken by ascending
    stratum name. Deterministic and independent of dict order.

    Fails closed: ``total`` above the summed capacity, a non-positive weight
    on a stratum that still needs seats, or an arithmetic result that does not
    sum to ``total`` all raise :class:`RosterError` rather than silently
    returning a short roster.
    """

    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise RosterError("mixture_quotas: total must be a non-negative int")
    keys = sorted(set(weights) | set(capacities))
    if not keys:
        raise RosterError("mixture_quotas: no strata")
    capacity = {key: int(capacities.get(key, 0)) for key in keys}
    weight = {key: float(weights.get(key, 0.0)) for key in keys}
    for key in keys:
        if capacity[key] < 0:
            raise RosterError(f"mixture_quotas: stratum {key!r} has a negative capacity")
        if weight[key] < 0:
            raise RosterError(f"mixture_quotas: stratum {key!r} has a negative weight")
    if total > sum(capacity.values()):
        raise RosterError(
            f"mixture_quotas: total {total} exceeds the summed capacity "
            f"{sum(capacity.values())}"
        )

    quotas = {key: 0 for key in keys}
    active = [key for key in keys if capacity[key] > 0]
    remaining = total
    while True:
        weight_sum = sum(weight[key] for key in active)
        if remaining == 0 or not active:
            break
        if weight_sum <= 0:
            raise RosterError(
                "mixture_quotas: the strata that still have capacity carry zero "
                "reference weight, so the mixture cannot be reproduced"
            )
        saturated = [
            key
            for key in active
            if capacity[key] < remaining * weight[key] / weight_sum
        ]
        if not saturated:
            break
        for key in saturated:
            quotas[key] = capacity[key]
            remaining -= capacity[key]
            active.remove(key)
        if remaining < 0:  # pragma: no cover -- defensive, unreachable
            raise RosterError("mixture_quotas: saturation over-allocated")

    if remaining > 0:
        weight_sum = sum(weight[key] for key in active)
        raw = {key: remaining * weight[key] / weight_sum for key in active}
        for key in active:
            quotas[key] = min(int(raw[key]), capacity[key])
        short = remaining - sum(quotas[key] for key in active)
        order = sorted(active, key=lambda key: (-(raw[key] - int(raw[key])), key))
        while short > 0:
            progressed = False
            for key in order:
                if short <= 0:
                    break
                if quotas[key] < capacity[key]:
                    quotas[key] += 1
                    short -= 1
                    progressed = True
            if not progressed:  # pragma: no cover -- guarded by the total check
                raise RosterError("mixture_quotas: capacity exhausted before total")

    if sum(quotas.values()) != total:
        raise RosterError(
            f"mixture_quotas: quotas sum to {sum(quotas.values())}, not {total}"
        )
    return dict(sorted(quotas.items()))


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
    roster_role: str = EVALUATION_ROSTER_ROLE,
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
    if roster_role not in ROSTER_ROLES:
        raise RosterError(
            f"roster_role must be one of {sorted(ROSTER_ROLES)}; got {roster_role!r}"
        )
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
        if quota == 0:
            # An explicit zero is a statement, not a starved stratum: draw
            # nothing and do not advance the shared rng, so a drained stratum
            # cannot shift the draws of the strata processed after it.
            continue
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
        "roster_role": roster_role,
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
    # A receipt frozen before 2026-09-05 carries no role; it is an evaluation
    # roster, the conservative reading, and saying so here keeps every reader
    # of a historical receipt from having to re-derive that default.
    roster_role = receipt.get("roster_role", EVALUATION_ROSTER_ROLE)
    if roster_role not in ROSTER_ROLES:
        raise RosterError(
            f"roster receipt roster_role must be one of {sorted(ROSTER_ROLES)}; "
            f"got {roster_role!r}"
        )
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


def canonical_receipt_bytes(receipt: Mapping[str, object]) -> bytes:
    """The exact bytes :func:`write_roster` writes, for hashing a receipt
    without having to re-read the file it was written to."""

    return (
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def as_probe_sample_receipt(
    receipt: Mapping[str, object],
    *,
    carrier: str,
    design: str,
) -> dict[str, object]:
    """Render a ``saea-roster-receipt-v1`` in the LEGACY probe-sample shape.

    Two receipt conventions coexist in this repository and neither can be
    retired: :func:`freeze_roster`'s carrier-agnostic ``saea-roster-receipt
    -v1`` (hash over ``prefixed(carrier, sample_ids)``), and the frozen
    probe-sample shape that ``data.audio2tool.audio2tool_receipts`` loads and
    strictly re-verifies (hash over each item's already carrier-prefixed
    ``key``, and per-item ``id``/``tier``/``key`` agreement). A roster whose
    items are never rendered into the second shape is simply not loadable by
    the Audio2Tool carrier, so it can never be flown; dropping a
    ``saea-roster-receipt-v1`` file into ``docs/receipts/probe-samples/``
    instead would break loading outright, because that directory's reader
    fails closed on every file it cannot verify.

    This function is the ONE bridge between them. It copies each roster
    item's audit ``extra`` fields verbatim (``id``, ``key``, ``tier``,
    ``query_idx`` for Audio2Tool), recomputes the legacy hash over the
    ``key`` values by the legacy convention -- so
    :func:`hash_matches_legacy_receipt` is true of the result -- and carries
    ``split_role``, ``roster_role`` and ``derived_from_roster_sha256`` so the
    view can always be traced back to the roster receipt it renders. It never
    mutates the roster receipt and adds no identity of its own: the two
    documents name exactly the same samples.
    """

    verify_roster(receipt)
    if not isinstance(carrier, str) or not carrier:
        raise RosterError("carrier must be non-empty text")
    if not isinstance(design, str) or not design:
        raise RosterError("design must be non-empty text")
    items: list[dict[str, object]] = []
    keys: list[str] = []
    for index, item in enumerate(receipt["items"]):  # type: ignore[index]
        if not isinstance(item, Mapping):
            raise RosterError(f"roster receipt items[{index}] must be an object")
        rendered = {
            key: value
            for key, value in item.items()
            if key not in {"sample_id", "stratum"}
        }
        key = rendered.get("key")
        if not isinstance(key, str) or not key:
            raise RosterError(
                f"roster item {item.get('sample_id')!r} carries no 'key' extra; a "
                "probe-sample view needs the carrier-prefixed identity"
            )
        expected_key = f"{carrier}:{item['sample_id']}"
        if key != expected_key:
            raise RosterError(
                f"roster item {item.get('sample_id')!r} key {key!r} disagrees with the "
                f"carrier-prefixed sample id {expected_key!r}"
            )
        items.append(rendered)
        keys.append(key)
    items.sort(key=lambda entry: str(entry["key"]))
    keys.sort()
    return {
        "carrier": carrier,
        "derived_from_roster_id": receipt["roster_id"],
        "derived_from_roster_sha256": hashlib.sha256(
            canonical_receipt_bytes(receipt)
        ).hexdigest(),
        "design": design,
        "items": items,
        "n_items": len(items),
        "probe": receipt["roster_id"],
        "roster_role": receipt.get("roster_role", EVALUATION_ROSTER_ROLE),
        "seed": receipt["seed"],
        "split_identity_hash": split_identity_hash(keys),
        "split_identity_hash_basis": (
            "sha256 over LF-joined sorted receipt item key values; the probe-receipt "
            "integrity convention data.audio2tool._verify_receipt recomputes"
        ),
        "split_role": receipt["split_role"],
        "strata_counts": receipt["strata_counts"],
        "roster_split_identity_hash": receipt["split_identity_hash"],
        "roster_split_identity_hash_basis": (
            "sha256 over LF-joined sorted '<carrier_lock_key>/<sample_id>' ids; the "
            "core.roster / data.splits convention"
        ),
    }


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
