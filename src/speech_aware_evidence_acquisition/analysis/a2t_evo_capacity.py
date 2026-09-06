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
    _validate_audio_relpath,  # noqa: SLF001 -- the loader's own path confinement
)
from ..data.lock import asset_dir, lock_entry
from ..rails.knowledge_build_a2t import TIERS

#: ``M`` -- the proposer exemplar reserve per tool (program section 5).
EXEMPLAR_RESERVE = 8

#: The per-fold quota cap (program section 5: "20 units per targeted tool").
QUOTA_CAP = 20

#: Below this a tool is dropped from the loop entirely.
QUOTA_FLOOR = 6

#: Owner decision 2026-09-06 ("RELAXED with sentinels"): a tool the quota rule
#: drops is no longer removed from the loop. It keeps at most this many
#: exemplar units -- enough for the proposer to see WHAT the tool is -- and
#: every remaining block of it becomes a HARM SENTINEL on one of the folds.
SENTINEL_EXEMPLAR_CAP = 4

#: Fold rows carry speech; the program caps a fold row at 60 seconds.
FOLD_MAX_AUDIO_SECONDS = 60.0

#: The three disjoint slices, in the order a split fills their deficits.
BUCKETS = ("fold_a", "fold_b", "exemplars")

__all__ = [
    "EXEMPLAR_RESERVE",
    "QUOTA_CAP",
    "QUOTA_FLOOR",
    "SENTINEL_EXEMPLAR_CAP",
    "FOLD_MAX_AUDIO_SECONDS",
    "BUCKETS",
    "CAPACITY_SCHEMA",
    "SENTINEL_RULE_TEXT",
    "rule_quota",
    "split_blocks",
    "sentinel_split",
    "realized_quota",
    "tool_capacity",
    "joint_capacity",
    "target_capacity",
    "capacity_verdict",
    "capacity_document",
    "read_json",
    "audio_seconds_by_sample_id",
    "measured_media_facts",
    "domains_by_sample_id",
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


def sentinel_split(
    units_by_block: Mapping[int, int],
    *,
    key: str,
    cap: int = SENTINEL_EXEMPLAR_CAP,
) -> tuple[dict[str, tuple[int, ...]], dict[str, int], int]:
    """The THIN-tool block split (owner decision 2026-09-06).

    A tool the quota rule drops is not dropped from the loop: it keeps
    ``min(cap, units // 2)`` exemplar units, so the proposer can still see
    what the tool is, and every block left over becomes a HARM SENTINEL,
    split evenly between fold A and fold B with the odd block to fold A.

    Two orderings, both derived from the SAME seeded
    :func:`_order` so nothing here is a second source of randomness. The
    exemplar reserve is paid from the SMALLEST blocks first (the reverse of
    that order) because a block is indivisible and the reserve is a ceiling,
    not a target: paying it with a large block would burn sentinel mass the
    loop needs. The remainder is then dealt largest-first, alternating fold A,
    fold B, fold A, ..., which both gives fold A the odd block and keeps the
    two folds' sentinel UNIT counts as close as whole blocks allow.

    Returns ``(blocks_by_bucket, units_by_bucket, reserve)`` -- the same
    shape :func:`split_blocks` returns, plus the reserve it aimed at.
    """

    units = sum(units_by_block.values())
    reserve = max(0, min(int(cap), units // 2))
    order = _order(units_by_block, key)
    exemplars: list[int] = []
    have = 0
    for block in reversed(order):
        if have >= reserve:
            break
        exemplars.append(block)
        have += units_by_block[block]
    taken = set(exemplars)
    remainder = [block for block in order if block not in taken]
    buckets = {
        "fold_a": tuple(sorted(remainder[0::2])),
        "fold_b": tuple(sorted(remainder[1::2])),
        "exemplars": tuple(sorted(exemplars)),
    }
    counts = {
        name: sum(units_by_block[block] for block in buckets[name]) for name in BUCKETS
    }
    return {name: buckets[name] for name in BUCKETS}, counts, reserve


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


#: The owner's 2026-09-06 amendment to the census rule, stated once.
SENTINEL_RULE_TEXT = (
    f"thin tool (fold_quota 0): keep min({SENTINEL_EXEMPLAR_CAP}, units // 2) exemplar "
    "units, paid from the smallest blocks first, and split every remaining BLOCK evenly "
    "between fold A and fold B as HARM SENTINELS, the odd block to fold A. A sentinel "
    "row is never a reward row: it is counted in the confirmation's background bound and "
    "in the round receipt's per-target sentinel-harms line"
)

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


def _official_media_relpath(entry: Mapping[str, object], context: str) -> str:
    """The wav the OFFICIAL protocol serves for one manifest entry.

    Identical to ``data.audio2tool._entry_media`` except on
    ``tier7_multiturn``, whose rows carry no top-level ``path``: the released
    ``Tier7Dataset._get_audio_paths`` returns ``sorted(glob("turn_*_user_*.wav"))``
    and ``BenchmarkEvaluator`` evaluates ``audio_paths[0]``, so the official
    row is the FIRST user turn. ``_entry_media`` reads ``chat_history[-1]``
    instead -- the P1 scaffold's final-turn binding, a protocol-fidelity gap
    its own module docstring records -- and on every tier-7 row of these folds
    the two differ. The three sealed official-population rosters and the
    4,000 the loop must transfer to all fly the first turn, so these folds do
    too.
    """

    path = entry.get("path")
    if isinstance(path, str) and path:
        return _validate_audio_relpath(path, context)
    history = entry.get("chat_history")
    if not isinstance(history, list) or not history:
        raise ValueError(f"{context}: entry has neither a top-level path nor a chat_history")
    for turn in history:
        if isinstance(turn, Mapping) and turn.get("role") == "user":
            return _validate_audio_relpath(turn.get("path"), context)
    raise ValueError(f"{context}: chat_history carries no user turn")


def _wav_header(path: Path, context: str) -> tuple[int, int]:
    import wave  # noqa: PLC0415 -- container header only, never a decode

    try:
        with wave.open(str(path), "rb") as handle:
            frames, rate = handle.getnframes(), handle.getframerate()
    except (OSError, EOFError, wave.Error) as error:
        raise ValueError(f"{context}: cannot read WAV header: {error}") from error
    if frames <= 0 or rate <= 0:
        raise ValueError(f"{context}: invalid WAV header")
    return frames, rate


def measured_media_facts(
    lock: Mapping[str, object], root: Path, sample_ids: Iterable[str]
) -> dict[str, dict[str, object]]:
    """The four media facts a flight-roster receipt records, MEASURED.

    Two deliberate differences from ``data.audio2tool.load_media_rows``, both
    of which a fold receipt needs:

    * ``audio_seconds`` is the wav header's ``frames / sample_rate``, not the
      manifest's three-decimal ``duration`` cell. The D1 media supplement is
      built from headers and refuses a disagreement above 1e-6, so a
      manifest-rounded value cannot be carried into a flight binding.
    * tier-7 rows bind the FIRST user turn (:func:`_official_media_relpath`).
    """

    subdir = str(lock_entry(lock, AUDIO2TOOL_LOCK_KEY)["local_subdir"]).rstrip("/")
    public = Path(asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)) / "public"
    wanted: dict[str, set[int]] = {}
    for sample_id in sample_ids:
        tier, _, number = str(sample_id).partition(":")
        wanted.setdefault(tier, set()).add(int(number))
    out: dict[str, dict[str, object]] = {}
    for tier in sorted(wanted):
        entries = {
            int(entry["id"]): entry
            for entry in read_json(public / f"{tier}_data" / f"{tier}.json")  # type: ignore[union-attr]
        }
        for number in sorted(wanted[tier]):
            sample_id = f"{tier}:{number:06d}"
            if number not in entries:
                raise ValueError(f"{sample_id}: no row in the {tier} manifest")
            relative = _official_media_relpath(entries[number], sample_id)
            path = public / relative
            if not path.is_file():
                raise ValueError(f"{sample_id}: media missing: {path}")
            frames, rate = _wav_header(path, sample_id)
            out[sample_id] = {
                "media_relpath": f"{subdir}/public/{relative}",
                "audio_seconds": round(frames / rate, 9),
                "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "sample_rate_hz": rate,
            }
    return out


def domains_by_sample_id(
    lock: Mapping[str, object], root: Path, sample_ids: Iterable[str]
) -> dict[str, str]:
    """``sample_id -> domain`` for exactly the named samples, from the released
    tier manifests' own ``domain`` column.

    Stratum metadata, the same field the A2T-ORG-1 union receipt reads for the
    same purpose. It is recorded as aggregate counts in a receipt and never
    reaches a request.
    """

    public = Path(asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)) / "public"
    wanted: dict[str, set[int]] = {}
    for sample_id in sample_ids:
        tier, _, number = str(sample_id).partition(":")
        wanted.setdefault(tier, set()).add(int(number))
    out: dict[str, str] = {}
    for tier in sorted(wanted):
        for entry in read_json(public / f"{tier}_data" / f"{tier}.json"):  # type: ignore[union-attr]
            if int(entry["id"]) in wanted[tier]:
                out[f"{tier}:{int(entry['id']):06d}"] = str(entry["domain"])
    missing = sorted(
        f"{tier}:{number:06d}"
        for tier, numbers in wanted.items()
        for number in numbers
        if f"{tier}:{number:06d}" not in out
    )
    if missing:
        raise ValueError(f"no released manifest row for {missing}")
    return out


def joint_capacity(
    rows: Iterable[object],
    tools: Sequence[str],
    *,
    seed: int,
    cap: int = QUOTA_CAP,
    reserve: int = EXEMPLAR_RESERVE,
    floor: int = QUOTA_FLOOR,
    sentinels: bool = False,
) -> tuple[dict[str, dict[str, object]], frozenset[int]]:
    """:func:`tool_capacity`, but with block CONTENTION resolved, plus the set
    of blocks the target tools between them occupy.

    Fourteen construction blocks of this carrier carry gold for two different
    MF-1 target tools, so per-tool splits computed independently can hand one
    block to fold A for one tool and to fold B for another. A contended block
    is therefore awarded ONCE, to the tool it is worth most to, under a rule
    fixed before the counting: a tool the independent census DROPPED never
    takes a block from a tool it did not drop (a dropped tool needs at most
    ``reserve`` exemplar units and no fold rows at all); otherwise the tool with
    fewer blocks in the pool wins, because a block is worth more where blocks
    are scarce; ties by fewer units, then by name.

    ``sentinels`` switches on the owner's 2026-09-06 rule for the tools this
    census DROPS: instead of spending every one of their blocks on exemplars
    they keep at most :data:`SENTINEL_EXEMPLAR_CAP` exemplar units and
    contribute the rest as harm sentinels (:func:`sentinel_split`). It is off
    by default so the V1 draw and its committed receipts stay reproducible
    byte for byte, and it changes NOTHING for a tool the census keeps.
    """

    owned: dict[str, list[object]] = {tool: [] for tool in tools}
    for row in rows:
        bucket = owned.get(getattr(row, "tool_name"))
        if bucket is not None:
            bucket.append(row)
    blocks_of = {
        tool: collections.Counter(int(getattr(row, "query_idx")) for row in members)
        for tool, members in owned.items()
    }
    solo = tool_capacity(rows, tools, seed=seed, cap=cap, reserve=reserve, floor=floor)

    def rank(tool: str) -> tuple[int, int, int, str]:
        return (0 if solo[tool]["survives"] else 1, len(blocks_of[tool]), len(owned[tool]), tool)

    claimants: dict[int, list[str]] = collections.defaultdict(list)
    for tool, counts in blocks_of.items():
        for block in counts:
            claimants[block].append(tool)
    winner = {block: min(names, key=rank) for block, names in claimants.items()}

    report: dict[str, dict[str, object]] = {}
    for tool in sorted(owned):
        free = {
            block: count for block, count in blocks_of[tool].items() if winner[block] == tool
        }
        quota, buckets, have = realized_quota(free, key=f"{seed}:{tool}", cap=cap, reserve=reserve)
        survives = quota >= floor
        sentinel = bool(sentinels) and not survives
        sentinel_reserve = 0
        if sentinel:
            buckets, have, sentinel_reserve = sentinel_split(free, key=f"{seed}:{tool}")
        report[tool] = {
            "tool_name": tool,
            "units": len(owned[tool]),
            "blocks": len(blocks_of[tool]),
            "units_after_contention": sum(free.values()),
            "blocks_after_contention": len(free),
            "blocks_lost_to_contention": len(blocks_of[tool]) - len(free),
            "units_by_tier": dict(
                sorted(
                    collections.Counter(str(getattr(row, "tier")) for row in owned[tool]).items()
                )
            ),
            "solo_quota": int(solo[tool]["fold_quota"]),
            "rule_quota": rule_quota(sum(free.values()), reserve=reserve, cap=cap),
            "realized_quota": quota,
            "fold_quota": quota if survives else 0,
            "survives": survives,
            "blocks_by_bucket": {name: list(buckets[name]) for name in BUCKETS},
            "units_by_bucket": dict(have),
        }
        if sentinel:
            report[tool]["sentinel"] = True
            report[tool]["sentinel_exemplar_reserve"] = sentinel_reserve
            report[tool]["sentinel_rule"] = SENTINEL_RULE_TEXT
    return report, frozenset(winner)
