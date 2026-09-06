"""The three EVO-A1 loop rosters: how they are cut, and the proof they are disjoint.

``analysis.a2t_evo_capacity`` decides how many rows each targeted tool can
afford; this module turns that decision into three frozen
``core.roster.freeze_roster`` receipts and the disjointness proof a reviewer
needs. Identity only -- sample id, tier, ``query_idx``, manifest id, gold
primary ``tool_name`` -- and no I/O beyond what the caller hands in, except
:func:`covered_by_probe_receipts`, which reads this repository's own committed
probe-sample receipts and no carrier byte.

* ``A2T-EVO-FOLD-A-V1`` -- stage-one reward rows: each fold-capable target tool
  at its contention-resolved quota, plus a tier-stratified background drawn
  from tools no MF-1 target names. The background exists so the confirmation
  can see the failure a per-target count rule cannot: a rewrite that wins its
  own pair by breaking the tools nobody targeted.
* ``A2T-EVO-FOLD-B-V1`` -- the same shape on disjoint blocks.
* ``A2T-EVO-EXEMPLARS-V1`` -- every remaining unit of a fold-capable tool, and
  up to ``EXEMPLAR_RESERVE`` for each tool the census dropped so the proposer
  can still see both sides of a pair it is asked to separate. Text-only.

Two group-key regimes inside one draw, which is why ``exclude_groups`` is built
per row rather than per roster. A TARGET row's group is its own unit, because a
tool with 20 units in 5 blocks must be allowed several units of one block. A
BACKGROUND row's group is its BLOCK, so drawing one background row claims the
whole block and fold B can be given fold A's ids to exclude and get block
disjointness for free.
"""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..core.roster import RosterItem, freeze_roster
from ..data.audio2tool import AUDIO2TOOL_LOCK_KEY
from .a2t_evo_capacity import BUCKETS, EXEMPLAR_RESERVE, SENTINEL_RULE_TEXT

FOLD_A_ID = "A2T-EVO-FOLD-A-V1"
FOLD_B_ID = "A2T-EVO-FOLD-B-V1"
EXEMPLARS_ID = "A2T-EVO-EXEMPLARS-V1"
BACKGROUND_ROWS = 120
BACKGROUND_PREFIX = "background:"

#: Receipt stem and roster-id stem per roster key. The version suffix is
#: appended by :func:`roster_stems`, so V1 stays exactly what it was and V2
#: (the owner's 2026-09-06 sentinel re-freeze) is the same draw under a new
#: name rather than a second, forked family of receipts.
ROSTER_STEMS = {
    "fold_a": ("A2T-EVO-FOLD-A", "a2t-evo-fold-a"),
    "fold_b": ("A2T-EVO-FOLD-B", "a2t-evo-fold-b"),
    "exemplars": ("A2T-EVO-EXEMPLARS", "a2t-evo-exemplars"),
}

DESIGN = (
    "EVO-A1 loop roster, roster_role 'construction' (owner decision 2026-09-05): these "
    "identities may be read WITH their gold offline, and gold may reach the frozen core only "
    "through the text-only 'construction-proposer-text' arm as prompt artifacts, never answers. "
    "split_role stays 'discovery', the TRAIN90 precedent. Block-disjoint from the Audio2Tool "
    "exposure union, from the reserved A2T-FRESH-800-V1, and from the other two EVO rosters."
)

__all__ = [
    "FOLD_A_ID",
    "FOLD_B_ID",
    "EXEMPLARS_ID",
    "BACKGROUND_ROWS",
    "BACKGROUND_PREFIX",
    "DESIGN",
    "ROSTER_STEMS",
    "roster_items",
    "roster_stems",
    "sentinel_tools",
    "blocks_of",
    "ids_of",
    "gate_identity_hash",
    "background_quota",
    "fold_quotas",
    "freeze_evo_rosters",
    "disjointness_proof",
    "roster_documents",
    "ROLES",
    "FLIGHT_RECEIPT_SCHEMA",
    "FLIGHT_ITEM_KEYS",
    "flight_roster_document",
    "covered_by_probe_receipts",
    "probe_sample_document",
]


def roster_stems(version: str) -> dict[str, tuple[str, str]]:
    """``{key: (roster_id, file stem)}`` for one version, e.g. ``"v2"``."""

    tag = str(version).strip().lower()
    if not tag.startswith("v") or not tag[1:].isdigit():
        raise ValueError(f"roster version must look like 'v1' or 'v2', not {version!r}")
    return {
        key: (f"{roster}-{tag.upper()}", f"{stem}-{tag}")
        for key, (roster, stem) in ROSTER_STEMS.items()
    }


def sentinel_tools(capacity: Mapping[str, Mapping[str, object]]) -> tuple[str, ...]:
    """The tools the census dropped and the sentinel rule kept, name-sorted.

    A sentinel tool's fold rows are HARM DETECTORS and never reward rows: the
    loop rewrites its description because the model wrongly reaches for it,
    but the corpus cannot supply enough of its own gold rows to count saves
    on. Callers keep these rows out of a target's reward slice and report any
    harm on them by name.
    """

    return tuple(
        sorted(tool for tool, row in capacity.items() if row.get("sentinel"))
    )


def fold_quotas(
    capacity: Mapping[str, Mapping[str, object]], tools: Sequence[str], bucket: str
) -> dict[str, int]:
    """Each targeted tool's row quota on one fold.

    A tool the census kept draws its contention-resolved ``fold_quota``, the
    same on both folds. A SENTINEL tool draws every unit its own sentinel
    split awarded that fold, which is deliberately not the same number on
    both: whole blocks do not halve.
    """

    if bucket not in ("fold_a", "fold_b"):
        raise ValueError(f"bucket must be a fold, not {bucket!r}")
    quotas: dict[str, int] = {}
    for tool in tools:
        row = capacity[tool]
        if row.get("sentinel"):
            units = int(row["units_by_bucket"][bucket])  # type: ignore[index]
            if units:
                quotas[tool] = units
        elif row["fold_quota"]:
            quotas[tool] = int(row["fold_quota"])
    return quotas


def roster_items(rows: Sequence[object], stratum_of: Callable[[object], str]) -> list[RosterItem]:
    """One :class:`RosterItem` per unit, the wav chosen by the release's own
    first-successful-speaker rule -- the unit's lowest manifest id."""

    return [
        RosterItem(
            sample_id=row.sample_ids[0],  # type: ignore[attr-defined]
            stratum=stratum_of(row),
            extra={
                "id": row.item_ids[0],  # type: ignore[attr-defined]
                "key": f"{AUDIO2TOOL_LOCK_KEY}:{row.sample_ids[0]}",  # type: ignore[attr-defined]
                "query_idx": row.query_idx,  # type: ignore[attr-defined]
                "tier": row.tier,  # type: ignore[attr-defined]
                "tool_name": row.tool_name,  # type: ignore[attr-defined]
            },
        )
        for row in sorted(rows, key=lambda row: row.unit_id)  # type: ignore[attr-defined]
    ]


def blocks_of(receipt: Mapping[str, object]) -> set[int]:
    return {int(item["query_idx"]) for item in receipt["items"]}  # type: ignore[index,union-attr]


def ids_of(receipt: Mapping[str, object]) -> set[str]:
    return {str(item["sample_id"]) for item in receipt["items"]}  # type: ignore[index,union-attr]


def gate_identity_hash(receipt: Mapping[str, object]) -> str:
    """The identity ``contracts.gate_exposure`` recomputes for a construction
    roster: sha256 over the LF-joined sorted ``<carrier>/<sample_id>`` keys.

    Recomputed here rather than trusted from ``split_identity_hash`` so the
    receipt and the gate that will read it are proven to agree before the
    receipt is written, not on the first refused flight.
    """

    keys = sorted(
        f"{AUDIO2TOOL_LOCK_KEY}/{item['sample_id']}"  # type: ignore[index]
        for item in receipt["items"]  # type: ignore[union-attr]
    )
    return hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()


def background_quota(tiers: Sequence[str], total: int) -> dict[str, int]:
    """``total`` background rows spread evenly over ``tiers``, the remainder
    going to the earliest tiers by name so the split is deterministic."""

    per_tier, extra = divmod(total, len(tiers))
    return {
        f"{BACKGROUND_PREFIX}{tier}": per_tier + (1 if index < extra else 0)
        for index, tier in enumerate(sorted(tiers))
    }


def _exemplar_quota(row: Mapping[str, object], available: int) -> int:
    """One tool's exemplar quota: everything left for a tool the census kept,
    the sentinel reserve for a thin tool, ``EXEMPLAR_RESERVE`` for a tool the
    census dropped with no sentinel rule in force (the V1 reading)."""

    if row.get("sentinel"):
        return min(int(row["sentinel_exemplar_reserve"]), available)  # type: ignore[arg-type]
    if row["fold_quota"]:
        return available
    return min(EXEMPLAR_RESERVE, available)


def freeze_evo_rosters(
    pool: Sequence[object],
    tools: Sequence[str],
    capacity: Mapping[str, Mapping[str, object]],
    *,
    seed: int,
    exposed: frozenset[str],
    background_rows: int = BACKGROUND_ROWS,
    version: str = "v1",
) -> dict[str, dict[str, object]]:
    """Freeze all three rosters in one pass, so they can be proven disjoint.

    ``capacity`` decides everything about a targeted tool's share. When it
    carries the owner's sentinel rule (``joint_capacity(..., sentinels=True)``)
    the thin tools it dropped come back on both folds as harm sentinels and
    keep only their small exemplar reserve; when it does not, this is the V1
    draw unchanged.
    """

    ids = roster_stems(version)
    named = set(tools)
    bucket_of: dict[int, str] = {
        int(block): name
        for tool in tools
        for name in BUCKETS
        for block in capacity[tool]["blocks_by_bucket"][name]  # type: ignore[index]
    }
    occupied = {
        int(row.query_idx) for row in pool if row.tool_name in named  # type: ignore[attr-defined]
    }
    background = [
        row
        for row in pool
        if row.tool_name not in named and int(row.query_idx) not in occupied  # type: ignore[attr-defined]
    ]
    groups = {
        **{
            row.sample_ids[0]: f"unit:{row.unit_id}"  # type: ignore[attr-defined]
            for row in pool
            if row.tool_name in named  # type: ignore[attr-defined]
        },
        **{
            row.sample_ids[0]: f"block:{row.query_idx}"  # type: ignore[attr-defined]
            for row in background
        },
    }
    tiers = sorted({str(row.tier) for row in background})  # type: ignore[attr-defined]

    def stratum(row: object) -> str:
        tool = str(getattr(row, "tool_name"))
        return tool if tool in named else f"{BACKGROUND_PREFIX}{getattr(row, 'tier')}"

    def fold(roster_id: str, bucket: str, exclude: set[str]) -> dict[str, object]:
        quotas = fold_quotas(capacity, tools, bucket)
        rows = [
            row
            for row in pool
            if row.tool_name in named  # type: ignore[attr-defined]
            and row.tool_name in quotas  # type: ignore[attr-defined]
            and bucket_of.get(int(row.query_idx)) == bucket  # type: ignore[attr-defined]
        ] + background
        return freeze_roster(
            carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
            candidates=roster_items(rows, stratum),
            per_stratum={**quotas, **background_quota(tiers, background_rows)},
            seed=seed,
            split_role="discovery",
            exclude_sample_ids=set(exposed) | exclude,
            exclude_groups=groups,
            roster_id=roster_id,
            roster_role="construction",
        )

    fold_a = fold(ids["fold_a"][0], "fold_a", set())
    fold_b = fold(ids["fold_b"][0], "fold_b", ids_of(fold_a))
    left = [
        row
        for row in pool
        if row.tool_name in named  # type: ignore[attr-defined]
        and bucket_of.get(int(row.query_idx)) == "exemplars"  # type: ignore[attr-defined]
    ]
    available = collections.Counter(
        str(getattr(row, "tool_name")) for row in left
    )
    exemplars = freeze_roster(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        candidates=roster_items(left, stratum),
        per_stratum={
            tool: _exemplar_quota(capacity[tool], count)
            for tool, count in available.items()
        },
        seed=seed,
        split_role="discovery",
        exclude_sample_ids=set(exposed) | ids_of(fold_a) | ids_of(fold_b),
        exclude_groups=groups,
        roster_id=ids["exemplars"][0],
        roster_role="construction",
    )
    return {
        "fold_a": fold_a,
        "fold_b": fold_b,
        "exemplars": exemplars,
        "pool": {
            "fold_eligible_units": len(pool),
            "fold_eligible_blocks": len({int(row.query_idx) for row in pool}),  # type: ignore[attr-defined]
            "target_tool_blocks": len(occupied),
            "background_candidate_units": len(background),
            "background_candidate_blocks": len({int(row.query_idx) for row in background}),  # type: ignore[attr-defined]
            "exemplar_units_available": dict(sorted(available.items())),
        },
    }


def disjointness_proof(
    rosters: Mapping[str, Mapping[str, object]],
    *,
    exposure_blocks: set[int],
    exposed: frozenset[str],
) -> dict[str, int]:
    """Every overlap that must be zero, recomputed from the receipts."""

    names = ("fold_a", "fold_b", "exemplars")
    blocks = {name: blocks_of(rosters[name]) for name in names}
    ids = {name: ids_of(rosters[name]) for name in names}
    drawn: set[str] = set().union(*ids.values())
    proof = {
        f"{left}_vs_{right}_blocks": len(blocks[left] & blocks[right])
        for index, left in enumerate(names)
        for right in names[index + 1 :]
    }
    proof["any_vs_exposure_union_blocks"] = len(set().union(*blocks.values()) & exposure_blocks)
    proof["any_vs_exposure_union_sample_ids"] = len(drawn & set(exposed))
    proof["duplicate_sample_ids_across_rosters"] = sum(len(ids[name]) for name in names) - len(drawn)
    return proof


#: One-line role per roster key; the file stem comes from :func:`roster_stems`.
ROLES = {
    "fold_a": "stage-one reward rows, fold A",
    "fold_b": "stage-two confirmation rows, fold B",
    "exemplars": "the proposer's exemplar pool; text-only",
}

BLOCK_POLICY = (
    "block-level: a query_idx block is the leakage unit, because the carrier re-renders one "
    "base scenario at several tiers. Every block belongs to at most one of the three rosters, "
    "by construction and re-proved here"
)

SELECTION_RULE = (
    "one wav per (tier, query_idx) unit: the unit's lowest manifest id, which is the release's "
    "own first-successful-speaker pick"
)


def roster_documents(
    cut: Mapping[str, Mapping[str, object]],
    capacity: Mapping[str, Mapping[str, object]],
    *,
    proof: Mapping[str, int],
    exposure: Mapping[str, object],
    exposure_blocks: int,
    shared: Mapping[str, object],
    version: str = "v1",
) -> list[tuple[str, dict[str, object]]]:
    """``[(file stem, receipt document)]``, one per roster, gate-hash verified.

    Raises :class:`ValueError` when a receipt's own ``split_identity_hash``
    disagrees with what ``contracts.gate_exposure`` would recompute -- a
    disagreement is a refused flight later, and is refused here instead.
    """

    stems = roster_stems(version)
    sentinels = sentinel_tools(capacity)
    common = {
        **shared,
        "design": DESIGN,
        "status": "FROZEN_CONSTRUCTION_ROSTER",
        "sample_selection_rule": SELECTION_RULE,
        "target_gold_opened_before_receipt": False,
        "tool_capacity": {tool: dict(capacity[tool]) for tool in sorted(capacity)},
        "exposure_union": exposure,
        "sentinel_tools": list(sentinels),
        "sentinel_rule": SENTINEL_RULE_TEXT if sentinels else "not in force for this draw",
    }
    out: list[tuple[str, dict[str, object]]] = []
    for key, role in ROLES.items():
        stem = stems[key][1]
        receipt = cut[key]
        document = {
            **receipt,
            **common,
            "role": role,
            "gate_exposure_identity_hash": gate_identity_hash(receipt),
            "block_disjointness": {
                "policy": BLOCK_POLICY,
                "distinct_blocks": len(blocks_of(receipt)),
                "exposure_union_sample_ids": exposure["union_sample_ids"],
                "exposure_union_blocks": exposure_blocks,
                **proof,
            },
        }
        if document["gate_exposure_identity_hash"] != receipt["split_identity_hash"]:
            raise ValueError(
                f"{receipt['roster_id']}: the gate's identity hash disagrees with freeze_roster"
            )
        out.append((stem, document))
    return out


# ---------------------------------------------------------------------------
# The flight view of a fold: what a speech-bearing cell needs beyond identity
# ---------------------------------------------------------------------------

FLIGHT_RECEIPT_SCHEMA = "saea-a2t-agentloop-flight-roster-receipt-v1"

#: The item keys a flight-roster receipt carries. Deliberately IDENTITY AND
#: MEDIA ONLY -- no ``tool_name`` and no ``stratum``, even though the
#: construction receipt beside it records both and may legally do so. This is
#: the file ``scripts/flights/run_calibration_cell.py`` reads to build its
#: samples, and a gold-adjacent per-row label has no business in it -- the
#: same reasoning the A2T-ORG-1 union receipt applied to ``domain``. The
#: counts are kept as aggregates instead.
FLIGHT_ITEM_KEYS = (
    "sample_id",
    "id",
    "key",
    "tier",
    "query_idx",
    "media_relpath",
    "audio_sha256",
    "audio_seconds",
)


def _sha256_lines(lines: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def flight_roster_document(
    receipt: Mapping[str, object],
    media: Mapping[str, Mapping[str, object]],
    *,
    split_name: str,
    domains: Mapping[str, str],
    shared: Mapping[str, object],
) -> dict[str, object]:
    """The ``saea-a2t-agentloop-flight-roster-receipt-v1`` view of one frozen
    construction roster.

    ``media`` is ``data.audio2tool.load_media_rows``'s output for exactly this
    roster's ids -- MEASURED facts, sha256 over the bytes on disk and the
    sample rate from the wav header -- and ``domains`` the released manifests'
    own ``domain`` column, kept as aggregate counts only.

    Two identity hashes, both re-derived here rather than copied:
    ``split_identity_hash`` over the LF-joined sorted ``key`` values (the
    Audio2Tool probe-receipt convention) and ``flight_split_identity_hash``
    over ``audio2tool/<sample_id>``, which is what ``FlightRuntime.preflight``
    computes and what the construction receipt already carries. A disagreement
    between the second and the frozen roster is refused here rather than on
    the first refused flight.
    """

    items: list[dict[str, object]] = []
    for item in receipt["items"]:  # type: ignore[union-attr]
        sample_id = str(item["sample_id"])  # type: ignore[index]
        facts = media.get(sample_id)
        if facts is None:
            raise ValueError(f"no measured media facts for {sample_id}")
        merged: dict[str, object] = {**item, **facts, "sample_id": sample_id}
        items.append({key: merged[key] for key in FLIGHT_ITEM_KEYS})
    items.sort(key=lambda row: str(row["sample_id"]))
    seconds = [float(row["audio_seconds"]) for row in items]
    tiers = collections.Counter(str(row["tier"]) for row in items)
    flight_identity = _sha256_lines(
        [f"{AUDIO2TOOL_LOCK_KEY}/{row['sample_id']}" for row in items]
    )
    if flight_identity != receipt["split_identity_hash"]:
        raise ValueError(
            f"{split_name}: the flight identity hash disagrees with the frozen roster"
        )
    return {
        "schema": FLIGHT_RECEIPT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier": AUDIO2TOOL_LOCK_KEY,
        "split_name": split_name,
        "split_role": str(receipt["split_role"]),
        "roster_role": str(receipt["roster_role"]),
        "split_identity_hash": _sha256_lines([str(row["key"]) for row in items]),
        "split_identity_hash_convention": (
            "sha256 over the LF-joined sorted 'key' values (audio2tool:<tier>:<id6>, "
            "UTF-8, no trailing newline) -- the Audio2Tool probe-receipt integrity "
            "convention"
        ),
        "flight_split_identity_hash": flight_identity,
        "flight_split_identity_hash_convention": (
            "data.splits.split_identity_hash(prefixed('audio2tool', sample_ids)) over "
            "audio2tool/<tier>:<id6> -- the value core.flight.FlightRuntime.preflight "
            "computes at flight time, and the value the frozen construction roster "
            "receipt beside this one already carries as its own split_identity_hash"
        ),
        "count": len(items),
        "items": items,
        "tier_counts": dict(sorted(tiers.items())),
        "domain_counts": dict(
            sorted(
                collections.Counter(
                    domains[str(row["sample_id"])] for row in items
                ).items()
            )
        ),
        "strata_counts": dict(receipt["strata_counts"]),  # type: ignore[arg-type]
        "strata": "gold tool for the targeted rows, tier for the background rows",
        "strata_basis": (
            "carried as AGGREGATE COUNTS only, copied from the frozen construction "
            "receipt beside this one. The per-row gold tool is not written into this "
            "file: this is what the flight entry point reads to build its samples, and "
            "a construction row's gold is legal to read OFFLINE, never at request time"
        ),
        "audio_seconds_total": round(sum(seconds), 6),
        "audio_seconds_longest_item": round(max(seconds), 6),
        "audio_seconds_shortest_item": round(min(seconds), 6),
        "audio_seconds_basis": (
            "exact wav header value (frames / sample rate), measured from the file here"
        ),
        "media_roster_sha256": _sha256_lines(
            [
                "|".join(
                    (
                        str(row["sample_id"]),
                        str(row["media_relpath"]),
                        str(row["audio_sha256"]),
                        str(row["audio_seconds"]),
                    )
                )
                for row in items
            ]
        ),
        "contacts": {
            "audio": "wav bytes hashed and wav headers read for duration; no decoding",
            "model": "none",
            "network": "none",
            "scorer": "none",
        },
        "status": "PREPARED_NOT_CONTACT_AUTHORITY",
        **dict(shared),
    }


def covered_by_probe_receipts(
    directory: Path, sample_ids: Sequence[str]
) -> dict[str, list[str]]:
    """``receipt stem -> the ids of ``sample_ids`` it already carries``.

    The one read this module performs, and it is over COMMITTED receipts of
    this repository rather than over any carrier byte: ``data.audio2tool``
    refuses a sample id that two probe-sample receipts claim, so a new receipt
    has to know what is already covered before it is written.
    """

    wanted = set(sample_ids)
    hits: dict[str, list[str]] = {}
    for path in sorted(Path(directory).glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, Mapping) or document.get("carrier") != AUDIO2TOOL_LOCK_KEY:
            continue
        found = sorted(
            sample
            for item in document.get("items", ())
            if (sample := str(item["key"]).split(":", 1)[1]) in wanted
        )
        if found:
            hits[path.stem] = found
    return hits


def probe_sample_document(
    receipt: Mapping[str, object],
    *,
    probe: str,
    already_covered: Mapping[str, Sequence[str]],
    shared: Mapping[str, object],
) -> dict[str, object]:
    """The additive probe-sample view that puts a fold's ids inside
    ``data.audio2tool``'s frozen-receipt universe.

    Additive for the reason the tier-1 official-population receipt is:
    ``data.audio2tool._resolve_items`` builds the loadable universe from the
    UNION of every committed receipt and refuses an id that appears in two, so
    this one carries exactly the ids no committed receipt covers yet. Without
    it the official scorer cannot score the fold at all.

    It declares the source roster's own ``roster_role``, and for a
    construction roster that field is load-bearing rather than decorative:
    ``rails.knowledge_build_a2t._probe_sample_source`` reads an unmarked
    receipt as EVALUATION exposure, which would put a fold's own rows into
    the exposure union and remove them from the construction pool that fold
    was drawn from -- a receipt that makes its own draw irreproducible.
    """

    covered = {sample for hits in already_covered.values() for sample in hits}
    items = sorted(
        (
            {
                "id": int(item["id"]),  # type: ignore[index]
                "key": str(item["key"]),  # type: ignore[index]
                "query_idx": int(item["query_idx"]),  # type: ignore[index]
                "tier": str(item["tier"]),  # type: ignore[index]
            }
            for item in receipt["items"]  # type: ignore[union-attr]
            if str(item["sample_id"]) not in covered  # type: ignore[index]
        ),
        key=lambda item: (str(item["tier"]), int(item["id"])),
    )
    return {
        "probe": probe,
        "carrier": AUDIO2TOOL_LOCK_KEY,
        "roster_role": str(receipt["roster_role"]),
        "split_role": str(receipt["split_role"]),
        "items": items,
        "n_items": len(items),
        "seed": receipt["seed"],
        "split_identity_hash": _sha256_lines([str(item["key"]) for item in items]),
        "split_identity_hash_basis": (
            "sha256 over LF-joined sorted receipt item key values; the Audio2Tool "
            "probe-receipt integrity convention data.audio2tool._verify_receipt recomputes"
        ),
        "strata_counts": dict(
            sorted(collections.Counter(str(item["tier"]) for item in items).items())
        ),
        "already_covered_by_other_receipts": {
            name: list(hits) for name, hits in sorted(already_covered.items())
        },
        "target_gold_opened_before_receipt": False,
        **dict(shared),
    }
