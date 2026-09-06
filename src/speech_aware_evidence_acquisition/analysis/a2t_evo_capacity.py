"""EVO-A1 construction capacity: what the evolution loop's rosters can hold.

Model-free arithmetic, plus the one manifest read it needs. The evolution loop of
``docs/readiness/2026-09-05-three-dimension-experiment-program.md`` section 5
needs THREE disjoint slices of every targeted tool's construction rows:

* ``fold_a`` -- the reward rows stage one counts saves and harms on;
* ``fold_b`` -- the reward rows stage two confirms the assembly on;
* ``exemplars`` -- the ``M = 8`` rows per tool the text-only proposer is shown
  with their gold calls, and the ONLY rows whose gold the proposer may see.

The three must be BLOCK-disjoint, not merely row-disjoint: the carrier
re-renders one ``query_idx`` block at several tiers, so a block is the leakage
unit (``rails.knowledge_build_a2t`` module docstring). That is why a unit-level
quota is not enough on its own and :func:`realized_quota` exists.

The preregistered rule, applied verbatim::

    quota_A = quota_B = min(20, floor((units - 8) / 2))

A tool whose quota falls below :data:`QUOTA_FLOOR` is DROPPED: it can no longer
supply enough paired rows on either fold for a count rule to mean anything.
:func:`realized_quota` then lowers that quota to the largest value a whole-block
split can actually deliver, because blocks are indivisible.
"""

from __future__ import annotations

import collections
import hashlib
import json
import random
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ..data.audio2tool import (
    AUDIO2TOOL_LOCK_KEY,
    _entry_media,  # noqa: SLF001 -- the released manifests' own duration field
)
from ..data.lock import asset_dir
from ..rails.knowledge_build_a2t import TIERS

#: ``M`` -- the proposer exemplar reserve per tool (program section 5).
EXEMPLAR_RESERVE = 8

#: The per-fold quota cap (program section 5: "20 units per targeted tool").
QUOTA_CAP = 20

#: Below this a tool is dropped from the loop entirely.
QUOTA_FLOOR = 6

#: Fold rows carry speech; the program caps a fold row at 60 seconds.
FOLD_MAX_AUDIO_SECONDS = 60.0

#: The three disjoint slices, in the order a split fills their deficits.
BUCKETS = ("fold_a", "fold_b", "exemplars")

__all__ = [
    "EXEMPLAR_RESERVE",
    "QUOTA_CAP",
    "QUOTA_FLOOR",
    "FOLD_MAX_AUDIO_SECONDS",
    "BUCKETS",
    "CAPACITY_SCHEMA",
    "rule_quota",
    "split_blocks",
    "realized_quota",
    "tool_capacity",
    "target_capacity",
    "capacity_verdict",
    "capacity_document",
    "read_json",
    "audio_seconds_by_sample_id",
    "RULE_TEXT",
]

CAPACITY_SCHEMA = "saea-a2t-evo-construction-capacity-v1"


def rule_quota(units: int, *, reserve: int = EXEMPLAR_RESERVE, cap: int = QUOTA_CAP) -> int:
    """``min(cap, floor((units - reserve) / 2))``, never negative."""

    if isinstance(units, bool) or not isinstance(units, int) or units < 0:
        raise ValueError("units must be a non-negative integer")
    return max(0, min(cap, (units - reserve) // 2))


def _order(units_by_block: Mapping[int, int], key: str) -> list[int]:
    """Blocks largest-first, ties broken by a key-seeded shuffle.

    Largest-first is what makes a whole-block split reach a unit deficit at
    all; the seeded shuffle underneath it is what keeps equal-sized blocks
    from being ordered by ``query_idx`` and so correlated across tools.
    """

    rng = random.Random(int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big"))
    order = sorted(units_by_block)
    rng.shuffle(order)
    order.sort(key=lambda block: -units_by_block[block])
    return order


def split_blocks(
    units_by_block: Mapping[int, int],
    *,
    quota: int,
    key: str,
    reserve: int = EXEMPLAR_RESERVE,
) -> tuple[dict[str, tuple[int, ...]], dict[str, int]]:
    """Deal whole blocks into the three slices, deficit-first.

    Each block goes to whichever slice is furthest from its need (``quota``,
    ``quota``, ``reserve``), ties resolved in :data:`BUCKETS` order; once every
    need is met the remainder falls to ``exemplars``, which the program defines
    as "every remaining construction unit".
    """

    needs = {"fold_a": quota, "fold_b": quota, "exemplars": reserve}
    buckets: dict[str, list[int]] = {name: [] for name in BUCKETS}
    have = {name: 0 for name in BUCKETS}
    for block in _order(units_by_block, key):
        best = max(BUCKETS, key=lambda name: (needs[name] - have[name], -BUCKETS.index(name)))
        if needs[best] - have[best] <= 0:
            best = "exemplars"
        buckets[best].append(block)
        have[best] += units_by_block[block]
    return {name: tuple(sorted(buckets[name])) for name in BUCKETS}, have


def realized_quota(
    units_by_block: Mapping[int, int],
    *,
    key: str,
    cap: int = QUOTA_CAP,
    reserve: int = EXEMPLAR_RESERVE,
) -> tuple[int, dict[str, tuple[int, ...]], dict[str, int]]:
    """The largest quota a whole-block split can actually deliver, and it.

    Searches down from :func:`rule_quota` because blocks are indivisible: a
    tool with 30 units in 10 blocks passes the unit rule at 11 per fold and
    still cannot cut 11 / 11 / 8 out of ten whole blocks.
    """

    units = sum(units_by_block.values())
    for quota in range(rule_quota(units, reserve=reserve, cap=cap), -1, -1):
        buckets, have = split_blocks(units_by_block, quota=quota, key=key, reserve=reserve)
        if have["fold_a"] >= quota and have["fold_b"] >= quota and have["exemplars"] >= reserve:
            return quota, buckets, have
    buckets, have = split_blocks(units_by_block, quota=0, key=key, reserve=reserve)
    return 0, buckets, have


def tool_capacity(
    rows: Iterable[object],
    tools: Sequence[str],
    *,
    seed: int,
    cap: int = QUOTA_CAP,
    reserve: int = EXEMPLAR_RESERVE,
    floor: int = QUOTA_FLOOR,
) -> dict[str, dict[str, object]]:
    """Per-tool capacity over ``rows`` (anything with ``tool_name``, ``tier``
    and ``query_idx``), keyed by tool name and sorted by it."""

    by_tool: dict[str, list[object]] = {tool: [] for tool in tools}
    for row in rows:
        bucket = by_tool.get(getattr(row, "tool_name"))
        if bucket is not None:
            bucket.append(row)
    report: dict[str, dict[str, object]] = {}
    for tool in sorted(by_tool):
        owned = by_tool[tool]
        units_by_block = collections.Counter(int(getattr(row, "query_idx")) for row in owned)
        quota, buckets, have = realized_quota(
            units_by_block, key=f"{seed}:{tool}", cap=cap, reserve=reserve
        )
        survives = quota >= floor
        report[tool] = {
            "tool_name": tool,
            "units": len(owned),
            "blocks": len(units_by_block),
            "units_by_tier": dict(
                sorted(collections.Counter(str(getattr(row, "tier")) for row in owned).items())
            ),
            "rule_quota": rule_quota(len(owned), reserve=reserve, cap=cap),
            "realized_quota": quota,
            "fold_quota": quota if survives else 0,
            "survives": survives,
            "blocks_by_bucket": {name: list(buckets[name]) for name in BUCKETS},
            "units_by_bucket": dict(have),
        }
    return report


def _sides(pair_id: str) -> list[list[str]]:
    return [side.split("+") for side in pair_id.split("|")]


def target_capacity(
    targets: Sequence[Mapping[str, object]],
    capacity: Mapping[str, Mapping[str, object]],
    pair_mass: Mapping[str, int],
) -> list[dict[str, object]]:
    """Per-target survival: a target lives only while its DOMINANT confusion
    pair -- the highest sealed-miss pair inside it -- keeps every tool on both
    sides, because a contrast is only rewardable when both sides have rows."""

    out: list[dict[str, object]] = []
    for target in targets:
        tools = [str(tool) for tool in target["tools"]]  # type: ignore[index]
        alive = {tool for tool in tools if capacity.get(tool, {}).get("survives")}
        pairs = sorted(
            ((int(pair_mass.get(str(pair), 0)), str(pair)) for pair in target["pairs"]),  # type: ignore[index]
            key=lambda item: (-item[0], item[1]),
        )
        intact = [
            (mass, pair)
            for mass, pair in pairs
            if all(all(tool in alive for tool in side) for side in _sides(pair))
        ]
        dominant_mass, dominant = pairs[0]
        dominant_intact = bool(intact) and intact[0][1] == dominant
        out.append(
            {
                "target_id": target["target_id"],
                "tools": tools,
                "strict_mass": target["strict_mass"],
                "component_mass": target["component_mass"],
                "surviving_tools": sorted(alive),
                "dropped_tools": sorted(set(tools) - alive),
                "dominant_pair": dominant,
                "dominant_pair_mass": dominant_mass,
                "dominant_pair_intact": dominant_intact,
                "intact_pairs": [{"pair_id": pair, "mass": mass} for mass, pair in intact],
                "intact_pair_mass": sum(mass for mass, _ in intact),
                "survives": dominant_intact and len(alive) >= 2,
            }
        )
    return out


def capacity_verdict(
    per_target: Sequence[Mapping[str, object]],
    capacity: Mapping[str, Mapping[str, object]],
    *,
    target_strict_mass_total: int,
) -> dict[str, object]:
    """The headline the loop's preregistration has to state before takeoff.

    Two readings, both reported. STRICT is the preregistered rule of section 5
    as this study applies it: a target lives only while its dominant confusion
    pair is intact. RELAXED is the fallback a coordinator may ratify instead --
    keep any target that still holds ONE intact pair, dropping the tools that
    cannot supply reward rows. Only the strict set is drawn into round 1; the
    relaxed set is priced here so ratifying it needs no fresh draw.
    """

    def _rows(targets: Sequence[Mapping[str, object]]) -> int:
        return sum(
            int(capacity[tool]["fold_quota"])
            for target in targets
            for tool in target["surviving_tools"]  # type: ignore[union-attr]
        )

    strict = [target for target in per_target if target["survives"]]
    relaxed = [target for target in per_target if target["intact_pairs"]]
    total = max(int(target_strict_mass_total), 1)
    strict_mass = sum(int(target["intact_pair_mass"]) for target in strict)
    relaxed_mass = sum(int(target["intact_pair_mass"]) for target in relaxed)
    return {
        "strict": {
            "targets": [target["target_id"] for target in strict],
            "tools": sorted(tool for target in strict for tool in target["surviving_tools"]),
            "targeted_rows_per_fold": _rows(strict),
            "addressable_strict_mass": strict_mass,
            "share_of_mf1_target_mass": round(strict_mass / total, 4),
        },
        "relaxed": {
            "targets": [target["target_id"] for target in relaxed],
            "tools": sorted(tool for target in relaxed for tool in target["surviving_tools"]),
            "targeted_rows_per_fold": _rows(relaxed),
            "addressable_strict_mass": relaxed_mass,
            "share_of_mf1_target_mass": round(relaxed_mass / total, 4),
        },
        "dropped_targets": [target["target_id"] for target in per_target if not target["survives"]],
        "dropped_tools": sorted(
            tool for tool, row in capacity.items() if not row["survives"]
        ),
        "fold_quotas": {
            tool: int(row["fold_quota"]) for tool, row in sorted(capacity.items()) if row["survives"]
        },
    }


#: The census rule, stated once so a receipt and this module cannot drift.
RULE_TEXT = (
    f"quota_A = quota_B = min({QUOTA_CAP}, floor((units - {EXEMPLAR_RESERVE}) / 2)), lowered "
    "to the largest whole-BLOCK split that still yields both folds and the "
    f"{EXEMPLAR_RESERVE}-unit exemplar reserve; a tool is DROPPED below a quota of "
    f"{QUOTA_FLOOR}; a target survives only while its dominant confusion pair keeps every "
    "tool on both sides"
)


def capacity_document(
    *,
    seed: int,
    generator: str,
    exposure_row: str,
    authority: str,
    population: Mapping[str, object],
    mf1_receipt: Mapping[str, object],
    capacity: Mapping[str, Mapping[str, object]],
    per_target: Sequence[Mapping[str, object]],
    verdict: Mapping[str, object],
    offline_guard: Mapping[str, object],
) -> dict[str, object]:
    """The committed receipt shape, assembled from already-measured parts."""

    return {
        "schema": CAPACITY_SCHEMA,
        "authority": authority,
        "exposure_row": exposure_row,
        "generator": generator,
        "seed": seed,
        "rule": RULE_TEXT,
        "population": dict(population),
        "mf1_receipt": dict(mf1_receipt),
        "tools": {tool: dict(capacity[tool]) for tool in sorted(capacity)},
        "targets": [dict(target) for target in per_target],
        "verdict": dict(verdict),
        "offline_guard": dict(offline_guard),
    }


def read_json(path: Path) -> object:
    """One committed or released JSON document, UTF-8, fail-closed."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def audio_seconds_by_sample_id(lock: Mapping[str, object], root: Path) -> dict[str, float]:
    """``sample_id -> runtime wav seconds`` from the released tier manifests'
    own ``duration`` field -- the same field ``data.audio2tool`` resolves.

    The five quarantined units have no resolvable runtime media and are
    skipped, exactly as ``a2t_pool_rows`` already drops them.
    """

    public = Path(asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)) / "public"
    seconds: dict[str, float] = {}
    for tier in TIERS:
        entries = read_json(public / f"{tier}_data" / f"{tier}.json")
        for entry in entries:  # type: ignore[union-attr]
            sample_id = f"{tier}:{int(entry['id']):06d}"
            try:
                seconds[sample_id] = _entry_media(entry, sample_id)[1]
            except Exception:  # noqa: BLE001 -- unresolvable media is a skip, not a stop
                continue
    return seconds
