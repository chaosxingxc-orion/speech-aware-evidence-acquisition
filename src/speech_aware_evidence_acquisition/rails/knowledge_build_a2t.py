"""KB-BUILD-A2T v1: tool-shaped, distribution-modeled, MODEL-FREE knowledge
construction for the Audio2Tool carrier (Audio2Tool generality campaign,
stage G0; authority ``docs/readiness/2026-08-25-a2t-generality-campaign-plan.md``
sections 3.2, 3.3 and 3.6).

This module is the Audio2Tool analogue of :mod:`.knowledge_build`, NOT an
edit of it. The SLURP builder stays byte-frozen because the locked baseline
cites its snapshot hash; everything Audio2Tool-specific lives here.

Scope discipline, identical to the SLURP builder: text facets and metadata
ONLY. No embeddings, no tokenizer, no model contacts, no network of any
kind. Every byte is read from the already-landed Audio2Tool tier manifests,
``tools_registry.csv`` and this repository's committed receipts.

WHAT CHANGES FROM THE SLURP SHAPE, and why (campaign plan section 3.2 -- the
campaign's main scientific decision):

* **Unit.** SLURP's KB unit was "utterance text -> intent". The A2T unit is
  "invocation utterance text -> tool call". A unit here is one
  ``(tier, query_idx)`` pair, which the carrier renders as one to four wav
  files by different synthetic speakers; the manifest text and the whole
  gold call list are IDENTICAL across a unit's renderings (verified over all
  16,843 units: zero text-inconsistent, zero gold-inconsistent), so merging
  them is lossless and mirrors SLURP's one-utterance-many-recordings shape.
* **Label facets.** One per GOLD tool name, hierarchically parented by
  ``domain -> category``, exactly as SLURP parented intent by
  ``scenario -> action``.
* **Value bundles carry ARGUMENT STRUCTURE.** SLURP's values carried a label;
  the measured A2T tool-acc/EM gap of +30.0 pp (the A0 verdict) says argument
  construction, not tool selection, is the dominant loss channel, so every
  value carries the tool's registry signature, constraints and defaults, this
  exemplar's own argument pattern, and the other argument patterns observed
  for the same tool in the construction pool.
* **Prior facets are argument-pattern priors.** SLURP's prior facet was
  ``p(entity_type | intent)``; here it is ``p(argument-pattern | tool)`` plus
  ``p(argument-key | tool)`` -- the same statistical role, aimed at the
  channel the A0 verdict identified.
* **The speaker dimension is DROPPED by default.** SLURP speakers are real
  people whose identity carries acoustic and distributional information;
  Audio2Tool speakers are synthetic voice assignments drawn from voice banks,
  they carry no tool-selection information, and 821 tier8 rows have no
  speaker id at all. The dimension remains representable (``dimensions``
  accepts ``"speaker"``) but is off in the registered default, and this
  deviation is reported rather than silently taken.

IDENTITY FACTS this module depends on, each measured rather than assumed
(the G0 report carries the full table):

* The tool registry declares **152** tools. The corpus's gold uses **151**
  of them as a primary tool; ``getLockStatus`` never appears as a gold tool
  anywhere in the 30,733-item pool, so it cannot receive a sample-bound
  facet. The campaign plan's "152 label facets" is corrected to 151 by
  measurement.
* ``tool_id`` is NOT a reliable join key between the manifests and the
  registry: 10 ``tool_id`` values carry a different ``tool_name`` in the
  manifests than in ``tools_registry.csv`` (e.g. id 70 is ``setLighting`` in
  gold and ``setLightState`` in the registry). The join here is by NAME,
  which is also what ``reproduction.toolcall_scoring`` compares.
* ``query_idx`` is shared ACROSS tiers -- 4,646 distinct values over 8
  tiers, 2,495 of them appearing in more than one tier -- so the same base
  scenario is re-rendered at several difficulty tiers. That makes the
  ``query_idx`` BLOCK, not the item, the unit that carries leakage between a
  construction pool and an evaluation tier, and it is the unit
  :func:`propose_partition` partitions on.

Decontamination is fail-closed and belt-and-braces, on the SLURP pattern:
the selected construction units' sample ids are checked against the whole
exposure union (:func:`exposed_sample_ids`, which since 2026-09-05 is every
committed EVALUATION identity, not only the frozen 400 of
``docs/receipts/probe-samples/r1-audio2tool-sample.json``) AND against
whatever proposed evaluation tier the caller asked :func:`propose_partition`
for -- empty by default since the tier was retired -- and any intersection
raises before a snapshot is returned.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..data.audio2tool import (
    AUDIO2TOOL_LOCK_KEY,
    _entry_media,  # noqa: SLF001 -- reused, not reimplemented; see module docstring
    audio2tool_receipts,
)
from ..data.loader import LoaderError
from ..data.lock import REPO_ROOT, asset_dir, lock_entry
from ..reproduction.toolcall_gold import GoldParseError, expected_tool_calls_for_entry
from ..reproduction.toolcall_scoring import ToolCall
from .errors import RailsError
from .hashing import content_hash
from .knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
    assert_prior_scores_are_probabilities,
)
from .knowledge_build_common import (
    greedy_diverse_pick,
    hamilton_apportion,
    jaccard,
    shingles,
)

A2T_KB_BUILD_POLICY_ID = "saea-kb-a2t-toolshaped-v1"
A2T_PARTITION_POLICY_ID = "saea-a2t-block-partition-v1"

TIERS: tuple[str, ...] = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)

_ALLOWED_DIMENSIONS = frozenset({"content", "label", "prior", "speaker"})
_DEFAULT_DIMENSIONS: tuple[str, ...] = ("content", "label", "prior")

EXPOSED_RECEIPT_RELPATH = "docs/receipts/probe-samples/r1-audio2tool-sample.json"
EXPOSED_RECEIPT_NAME = "r1-audio2tool-sample"

#: Exposure-union sources (E2.2, 2026-09-05). Evaluation identity is frozen
#: in three different places in this repository; the union reads all three.
PROBE_SAMPLE_RELDIR = "docs/receipts/probe-samples"
D1_SUPPLEMENT_RELDIR = "docs/receipts/artifacts"
D1_SUPPLEMENT_GLOB = "d1-a2t-*.json"
D1_SUPPLEMENT_SCHEMA = "saea-d1-media-supplement-v1"
ROSTER_RECEIPTS_RELDIR = "docs/receipts/rosters"
EXPOSURE_UNION_POLICY_ID = "saea-a2t-exposure-union-v1"

#: A per-roster companion file committed beside its ``saea-roster-receipt-v1``
#: sibling in the same directory (e.g. ``a2t-paired-400-v1.comparator-rows.json``
#: beside ``a2t-paired-400-v1.json``, written by ``scripts/build_a2t_paired_400_roster.py``).
#: It carries analysis-recipe comparator rows, never sample identities, and is
#: not an exposure source; the roster glob must recognize and skip it rather
#: than fail closed on an unexpected schema.
A2T_PAIRED_ROSTER_COMPARATOR_ROWS_SCHEMA = "saea-a2t-paired-roster-comparator-rows-v1"

#: The two roster roles (owner decision 2026-09-05). An EVALUATION roster's
#: identities are exposure and must never be read with their gold; a
#: CONSTRUCTION roster's identities may be, which is exactly why the union
#: excludes them. A receipt with no ``roster_role`` field predates the
#: distinction and is an evaluation roster.
EVALUATION_ROSTER_ROLE = "evaluation"
CONSTRUCTION_ROSTER_ROLE = "construction"
_ROSTER_ROLES = frozenset({EVALUATION_ROSTER_ROLE, CONSTRUCTION_ROSTER_ROLE})

_AUTHORITY = (
    "docs/readiness/2026-08-25-a2t-generality-campaign-plan.md sections 3.2, 3.3 and 3.6"
)
_LONG_TAIL_THRESHOLD = 5

A2T_CONSTRUCTION_SELECTION_SCHEMA = "saea-a2t-construction-selection-v1"

#: An item is eligible for the proposed evaluation tier only when its gold
#: primary tool has at least this many units in the exposure-free pool. The
#: rule exists so the evaluation draw can never starve the construction
#: floor of a rare tool; the tools it excludes are named in the partition
#: report rather than dropped silently.
EVAL_TOOL_MIN_POOL_ROWS = 8


# ---------------------------------------------------------------------------
# Task-neutral A2T rows
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _A2tManifestItem:
    tier: str
    item_id: int
    query_idx: int
    sample_id: str
    unit_id: str
    entry: Mapping[str, object]


@dataclass(frozen=True)
class _A2tManifestInventory:
    units: Mapping[str, tuple[_A2tManifestItem, ...]]
    source_manifest_sha256_by_tier: Mapping[str, str]
    tier_item_counts: Mapping[str, int]

    @property
    def sample_by_id(self) -> dict[str, _A2tManifestItem]:
        return {
            item.sample_id: item
            for members in self.units.values()
            for item in members
        }


@dataclass(frozen=True)
class _ConstructionSelection:
    allowed_unit_ids: frozenset[str]
    summary: Mapping[str, object]


@dataclass(frozen=True)
class A2tKbRow:
    """One Audio2Tool ``(tier, query_idx)`` unit's task-neutral row.

    ``sample_ids`` are the loader's own ``f"{tier}:{id:06d}"`` ids for every
    manifest item in the unit, so decontamination compares like with like
    against the frozen probe receipt.
    """

    unit_id: str
    tier: str
    query_idx: int
    text: str
    domain: str
    category: str
    tool_id: int
    tool_name: str
    arg_signature: tuple[str, ...]
    arg_pairs: tuple[tuple[str, str], ...]
    call_render: str
    extra_call_names: tuple[str, ...]
    call_count: int
    sample_ids: tuple[str, ...]
    item_ids: tuple[int, ...]
    media_relpath_by_sample_id: Mapping[str, str]
    speaker_ids: tuple[str, ...]

    @property
    def family_key(self) -> tuple[str, tuple[str, ...]]:
        """This unit's argument-pattern family: the gold primary tool paired
        with the sorted tuple of its argument KEY names."""

        return (self.tool_name, self.arg_signature)


def _render_value(value: object) -> str:
    """Deterministic one-line rendering of one gold argument value."""

    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def render_call(call: ToolCall) -> str:
    """Deterministic ``name(k=v, ...)`` rendering with keys sorted."""

    inner = ", ".join(
        f"{key}={_render_value(call.arguments[key])!r}" for key in sorted(call.arguments)
    )
    return f"{call.name}({inner})"


def _unit_text(tier: str, entry: Mapping[str, object]) -> str:
    """The invocation utterance text of one manifest entry.

    tier7_multiturn's ``query`` field is the WHOLE conversation transcript,
    while the runtime protocol sends only the final user turn's wav
    (``data.audio2tool`` module docstring). ``user_request`` is that final
    turn, so it -- not ``query`` -- is the text the runtime percept
    corresponds to, and it is what this builder keys the tier7 content facet
    on.
    """

    raw = entry.get("user_request") if tier == "tier7_multiturn" else entry.get("query")
    if not isinstance(raw, str) or not raw.strip():
        raise RailsError(f"{tier}: manifest entry lacks a non-empty invocation text")
    return raw.strip()


def _tier_manifest_path(public_dir: Path, tier: str) -> Path:
    return public_dir / f"{tier}_data" / f"{tier}.json"


def _load_a2t_manifest_inventory(
    lock: Mapping[str, object], root: Path
) -> _A2tManifestInventory:
    """Load source bytes once and inspect only construction identity metadata."""

    carrier_dir = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    public_dir = carrier_dir / "public"
    if not public_dir.is_dir():
        raise RailsError(f"audio2tool public directory missing: {public_dir}")

    units: dict[str, list[_A2tManifestItem]] = defaultdict(list)
    source_hashes: dict[str, str] = {}
    tier_item_counts: dict[str, int] = {}
    seen_sample_ids: set[str] = set()
    for tier in TIERS:
        path = _tier_manifest_path(public_dir, tier)
        if not path.is_file():
            raise RailsError(f"audio2tool tier manifest missing: {path}")
        try:
            raw = path.read_bytes()
            entries = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise RailsError(
                f"cannot read audio2tool tier manifest {path}: {error}"
            ) from error
        if not isinstance(entries, list) or not entries:
            raise RailsError(
                f"audio2tool tier manifest {path} must be a non-empty JSON list"
            )
        source_hashes[tier] = hashlib.sha256(raw).hexdigest()
        tier_item_counts[tier] = len(entries)
        for raw_item in entries:
            if not isinstance(raw_item, Mapping):
                raise RailsError(f"audio2tool tier manifest {path} has a malformed item")
            item_tier = raw_item.get("tier")
            if item_tier != tier:
                raise RailsError(
                    f"audio2tool tier manifest {path} has a tier mismatch: "
                    f"{item_tier!r} != {tier!r}"
                )
            item_id = raw_item.get("id")
            if isinstance(item_id, bool) or not isinstance(item_id, int):
                raise RailsError(f"{tier}: manifest entry lacks an integer id")
            if item_id < 0:
                raise RailsError(f"{tier}: manifest entry id must be non-negative")
            query_idx = raw_item.get("query_idx")
            if isinstance(query_idx, bool) or not isinstance(query_idx, int):
                raise RailsError(f"{tier}: manifest entry lacks an integer query_idx")
            if query_idx < 0:
                raise RailsError(f"{tier}: manifest entry query_idx must be non-negative")
            sample_id = f"{tier}:{item_id:06d}"
            if sample_id in seen_sample_ids:
                raise RailsError(
                    f"audio2tool manifests contain repeated sample identity {sample_id!r}"
                )
            seen_sample_ids.add(sample_id)
            unit_id = f"{tier}:{query_idx:06d}"
            units[unit_id].append(
                _A2tManifestItem(
                    tier=tier,
                    item_id=item_id,
                    query_idx=query_idx,
                    sample_id=sample_id,
                    unit_id=unit_id,
                    entry=raw_item,
                )
            )

    frozen_units = {
        unit_id: tuple(sorted(members, key=lambda item: item.item_id))
        for unit_id, members in sorted(units.items())
    }
    return _A2tManifestInventory(
        units=frozen_units,
        source_manifest_sha256_by_tier=source_hashes,
        tier_item_counts=tier_item_counts,
    )


def a2t_metadata_inventory(
    lock: Mapping[str, object], root: Path
) -> dict[str, object]:
    """Return deterministic Audio2Tool identities and source-manifest hashes.

    This public inventory does not inspect or expose invocation text, gold,
    tools, speakers, or media fields.
    """

    inventory = _load_a2t_manifest_inventory(lock, root)
    units = [
        {
            "unit_id": unit_id,
            "tier": members[0].tier,
            "query_idx": members[0].query_idx,
            "sample_ids": [item.sample_id for item in members],
        }
        for unit_id, members in inventory.units.items()
    ]
    return {
        "source_manifest_sha256_by_tier": dict(
            inventory.source_manifest_sha256_by_tier
        ),
        "item_count": sum(inventory.tier_item_counts.values()),
        "item_count_by_tier": dict(inventory.tier_item_counts),
        "unit_count": len(units),
        "units": units,
    }


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _load_construction_selection_receipt(
    path: Path, expected_sha256: str
) -> Mapping[str, object]:
    """Verify receipt bytes before parsing any governed tier manifest."""

    if not _is_sha256(expected_sha256):
        raise RailsError("construction receipt SHA-256 must be 64 lowercase hex digits")
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise RailsError(f"cannot read construction receipt {path}: {error}") from error
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != expected_sha256:
        raise RailsError(
            f"construction receipt SHA-256 mismatch: expected {expected_sha256}, "
            f"got {actual_sha256}"
        )
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RailsError(f"cannot parse construction receipt {path}: {error}") from error
    if not isinstance(document, Mapping):
        raise RailsError("construction receipt must be a JSON object")
    expected_keys = {
        "schema",
        "source_manifest_sha256_by_tier",
        "allowed_units",
        "excluded_sample_ids",
    }
    if set(document) != expected_keys:
        raise RailsError(
            "construction receipt must contain exactly "
            f"{sorted(expected_keys)}, got {sorted(str(key) for key in document)}"
        )
    if document.get("schema") != A2T_CONSTRUCTION_SELECTION_SCHEMA:
        raise RailsError(
            "construction receipt schema must be "
            f"{A2T_CONSTRUCTION_SELECTION_SCHEMA!r}"
        )
    source_hashes = document.get("source_manifest_sha256_by_tier")
    if not isinstance(source_hashes, Mapping) or set(source_hashes) != set(TIERS):
        raise RailsError(
            "construction receipt source_manifest_sha256_by_tier must cover "
            "exactly the eight Audio2Tool tiers"
        )
    for tier in TIERS:
        if not _is_sha256(source_hashes.get(tier)):
            raise RailsError(
                f"construction receipt source hash for {tier!r} is not a SHA-256"
            )
    allowed_units = document.get("allowed_units")
    if not isinstance(allowed_units, list) or not allowed_units:
        raise RailsError("construction receipt allowed_units must be non-empty")
    excluded = document.get("excluded_sample_ids")
    if not isinstance(excluded, list):
        raise RailsError("construction receipt excluded_sample_ids must be a list")
    return document


def _validate_construction_selection(
    receipt: Mapping[str, object],
    inventory: _A2tManifestInventory,
    *,
    receipt_path: Path,
    receipt_sha256: str,
) -> _ConstructionSelection:
    source_hashes = receipt["source_manifest_sha256_by_tier"]
    assert isinstance(source_hashes, Mapping)
    for tier in TIERS:
        if source_hashes[tier] != inventory.source_manifest_sha256_by_tier[tier]:
            raise RailsError(
                f"construction receipt source manifest SHA-256 mismatch for {tier}"
            )

    sample_by_id = inventory.sample_by_id
    excluded_raw = receipt["excluded_sample_ids"]
    assert isinstance(excluded_raw, list)
    excluded_ids: list[str] = []
    excluded_seen: set[str] = set()
    for sample_id in excluded_raw:
        if not isinstance(sample_id, str) or not sample_id:
            raise RailsError(
                "construction receipt excluded_sample_ids must contain strings"
            )
        if sample_id in excluded_seen:
            raise RailsError(
                f"construction receipt has duplicate excluded_sample_id {sample_id!r}"
            )
        if sample_id not in sample_by_id:
            raise RailsError(
                f"construction receipt has unknown excluded_sample_id {sample_id!r}"
            )
        excluded_seen.add(sample_id)
        excluded_ids.append(sample_id)
    excluded_query_indices = {
        sample_by_id[sample_id].query_idx for sample_id in excluded_ids
    }

    allowed_raw = receipt["allowed_units"]
    assert isinstance(allowed_raw, list)
    allowed_unit_ids: set[str] = set()
    allowed_sample_ids: set[str] = set()
    allowed_sample_count = 0
    for record in allowed_raw:
        if not isinstance(record, Mapping) or set(record) != {"unit_id", "sample_ids"}:
            raise RailsError(
                "each construction receipt allowed unit must contain exactly "
                "unit_id and sample_ids"
            )
        unit_id = record.get("unit_id")
        if not isinstance(unit_id, str) or not unit_id:
            raise RailsError("construction receipt allowed unit_id must be a string")
        if unit_id in allowed_unit_ids:
            raise RailsError(
                f"construction receipt has duplicate allowed unit {unit_id!r}"
            )
        if unit_id not in inventory.units:
            raise RailsError(
                f"construction receipt has unknown allowed unit {unit_id!r}"
            )
        sample_ids = record.get("sample_ids")
        if not isinstance(sample_ids, list) or not sample_ids:
            raise RailsError(
                f"construction receipt allowed unit {unit_id!r} has no sample_ids"
            )
        local_seen: set[str] = set()
        for sample_id in sample_ids:
            if not isinstance(sample_id, str) or not sample_id:
                raise RailsError(
                    f"construction receipt allowed unit {unit_id!r} has a malformed sample"
                )
            if sample_id in local_seen or sample_id in allowed_sample_ids:
                raise RailsError(
                    f"construction receipt has duplicate sample {sample_id!r}"
                )
            if sample_id not in sample_by_id:
                raise RailsError(
                    f"construction receipt allowed unit {unit_id!r} has unknown sample "
                    f"{sample_id!r}"
                )
            local_seen.add(sample_id)
        expected_ids = {item.sample_id for item in inventory.units[unit_id]}
        if local_seen != expected_ids:
            raise RailsError(
                f"construction receipt selects a partial unit {unit_id!r}: "
                f"expected {sorted(expected_ids)}, got {sorted(local_seen)}"
            )
        query_idx = inventory.units[unit_id][0].query_idx
        if query_idx in excluded_query_indices:
            raise RailsError(
                f"construction receipt allows unit {unit_id!r} sharing excluded "
                f"query_idx {query_idx}"
            )
        allowed_unit_ids.add(unit_id)
        allowed_sample_ids.update(local_seen)
        allowed_sample_count += len(local_seen)

    summary = {
        "schema": A2T_CONSTRUCTION_SELECTION_SCHEMA,
        "receipt_path": str(Path(receipt_path)),
        "receipt_sha256": receipt_sha256,
        "source_manifest_sha256_by_tier": dict(
            inventory.source_manifest_sha256_by_tier
        ),
        "source_item_count": sum(inventory.tier_item_counts.values()),
        "source_unit_count": len(inventory.units),
        "allowed_unit_count": len(allowed_unit_ids),
        "allowed_sample_count": allowed_sample_count,
        "excluded_sample_count": len(excluded_ids),
        "excluded_query_idx_count": len(excluded_query_indices),
    }
    return _ConstructionSelection(
        allowed_unit_ids=frozenset(allowed_unit_ids),
        summary=summary,
    )


def load_tool_registry_by_name(
    lock: Mapping[str, object], root: Path
) -> dict[str, dict[str, str]]:
    """``tools_registry.csv`` keyed by ``tool_name``.

    Keyed by NAME rather than ``tool_id`` because the two disagree on 10 ids
    (module docstring) and because the scorer compares names.
    """

    path = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root) / "tools_registry.csv"
    if not path.is_file():
        raise RailsError(f"audio2tool tools_registry.csv missing: {path}")
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error) as error:
        raise RailsError(f"cannot read tools_registry.csv {path}: {error}") from error
    by_name: dict[str, dict[str, str]] = {}
    for row in rows:
        name = (row.get("tool_name") or "").strip()
        if not name:
            raise RailsError("tools_registry.csv row lacks tool_name")
        if name in by_name:
            raise RailsError(f"tools_registry.csv has a duplicate tool_name {name!r}")
        by_name[name] = {key: (row.get(key) or "") for key in row}
    if not by_name:
        raise RailsError(f"tools_registry.csv {path} has no rows")
    return by_name


def a2t_pool_rows(
    lock: Mapping[str, object],
    root: Path,
    *,
    construction_receipt_path: Path | None = None,
    construction_receipt_sha256: str | None = None,
) -> tuple[tuple[A2tKbRow, ...], dict[str, object]]:
    """Every Audio2Tool ``(tier, query_idx)`` unit in the FULL carrier pool,
    sorted by ``unit_id``, plus an integrity report.

    Fail-closed on a unit whose manifest items disagree on invocation text or
    on parsed gold. Units whose parsed gold names a call OUTSIDE the tool
    registry are QUARANTINED rather than silently kept: the only observed
    case is an upstream data defect (two tier2 rows whose
    ``expected_tool_call`` string carries Telugu codepoints spliced into the
    middle of ``getApplianceState``), and a corrupted-gold row must never
    enter either a knowledge base or an evaluation tier.

    When both construction receipt arguments are present, the returned rows
    and the existing pool report fields describe only the receipt's allowed
    units. Selection provenance is added under construction_selection.
    Omitting both arguments preserves the full-pool behavior and report shape.
    """

    if (construction_receipt_path is None) != (
        construction_receipt_sha256 is None
    ):
        raise RailsError(
            "construction_receipt_path and construction_receipt_sha256 "
            "must be provided together"
        )
    receipt: Mapping[str, object] | None = None
    if (
        construction_receipt_path is not None
        and construction_receipt_sha256 is not None
    ):
        receipt = _load_construction_selection_receipt(
            construction_receipt_path, construction_receipt_sha256
        )

    entry = lock_entry(lock, AUDIO2TOOL_LOCK_KEY)
    subdir = str(entry["local_subdir"]).rstrip("/")
    inventory = _load_a2t_manifest_inventory(lock, root)
    selection: _ConstructionSelection | None = None
    if receipt is not None:
        assert construction_receipt_path is not None
        assert construction_receipt_sha256 is not None
        selection = _validate_construction_selection(
            receipt,
            inventory,
            receipt_path=construction_receipt_path,
            receipt_sha256=construction_receipt_sha256,
        )
    selected_unit_ids = (
        frozenset(inventory.units)
        if selection is None
        else selection.allowed_unit_ids
    )
    units = {
        unit_id: tuple((item.item_id, item.entry) for item in members)
        for unit_id, members in inventory.units.items()
        if unit_id in selected_unit_ids
    }
    if selection is None:
        tier_item_counts = dict(inventory.tier_item_counts)
    else:
        tier_item_counts = dict.fromkeys(TIERS, 0)
        for unit_id in selected_unit_ids:
            for item in inventory.units[unit_id]:
                tier_item_counts[item.tier] += 1
    registry = load_tool_registry_by_name(lock, root)

    rows: list[A2tKbRow] = []
    quarantined: list[dict[str, object]] = []
    for unit_id in sorted(units):
        tier, _, idx_text = unit_id.partition(":")
        members = sorted(units[unit_id], key=lambda pair: pair[0])
        texts = {_unit_text(tier, item) for _item_id, item in members}
        if len(texts) != 1:
            raise RailsError(f"unit {unit_id!r} has inconsistent invocation text")
        text = texts.pop()
        signatures: set[tuple[tuple[str, str], ...]] = set()
        parsed_calls: tuple[ToolCall, ...] | None = None
        for _item_id, item in members:
            try:
                calls = expected_tool_calls_for_entry(item)
            except GoldParseError as error:
                raise RailsError(f"unit {unit_id!r}: cannot parse gold: {error}") from error
            signatures.add(tuple((call.name, render_call(call)) for call in calls))
            parsed_calls = calls
        if len(signatures) != 1 or parsed_calls is None:
            raise RailsError(f"unit {unit_id!r} has inconsistent gold across its renderings")
        unknown = sorted({call.name for call in parsed_calls} - set(registry))
        if unknown:
            quarantined.append(
                {
                    "unit_id": unit_id,
                    "reason": "gold names a call outside the tool registry",
                    "unknown_call_names": unknown,
                }
            )
            continue

        primary = parsed_calls[0]
        sample_ids: list[str] = []
        media: dict[str, str] = {}
        speakers: list[str] = []
        item_ids: list[int] = []
        last_item: Mapping[str, object] = members[0][1]
        media_error: str | None = None
        for item_id, item in members:
            sample_id = f"{tier}:{item_id:06d}"
            try:
                relpath, _seconds = _entry_media(item, sample_id)
            except LoaderError as error:
                media_error = str(error)
                break
            sample_ids.append(sample_id)
            media[sample_id] = f"{subdir}/public/{relpath}"
            item_ids.append(item_id)
            speaker = item.get("speaker_id") or item.get("user_speaker_id")
            speakers.append(
                str(speaker) if isinstance(speaker, str) and speaker else "unknown"
            )
            last_item = item
        if media_error is not None:
            # tier7_multiturn rows whose final chat_history turn is not a user
            # turn carry no resolvable request audio, so the runtime protocol
            # cannot send them and a facet cannot bind to a sample id. They are
            # quarantined with their reason, never silently repaired.
            quarantined.append(
                {
                    "unit_id": unit_id,
                    "reason": "media unresolvable under the frozen runtime protocol",
                    "detail": media_error,
                }
            )
            continue
        rows.append(
            A2tKbRow(
                unit_id=unit_id,
                tier=tier,
                query_idx=int(idx_text),
                text=text,
                domain=str(last_item.get("domain") or "unknown"),
                category=str(last_item.get("category") or "unknown"),
                tool_id=int(last_item.get("tool_id", -1)),
                tool_name=primary.name,
                arg_signature=tuple(sorted(primary.arguments)),
                arg_pairs=tuple(
                    (key, _render_value(primary.arguments[key]))
                    for key in sorted(primary.arguments)
                ),
                call_render=" ".join(render_call(call) for call in parsed_calls),
                extra_call_names=tuple(call.name for call in parsed_calls[1:]),
                call_count=len(parsed_calls),
                sample_ids=tuple(sample_ids),
                item_ids=tuple(item_ids),
                media_relpath_by_sample_id=media,
                speaker_ids=tuple(speakers),
            )
        )

    report = {
        "pool_items": sum(tier_item_counts.values()),
        "pool_items_by_tier": dict(sorted(tier_item_counts.items())),
        "pool_units": len(units),
        "usable_units": len(rows),
        "usable_items": sum(len(row.sample_ids) for row in rows),
        "quarantined_unit_count": len(quarantined),
        "quarantined_units_by_reason": dict(
            sorted(Counter(str(record["reason"]) for record in quarantined).items())
        ),
        "quarantined_units": quarantined,
        "registry_tool_count": len(registry),
        "gold_primary_tool_count": len({row.tool_name for row in rows}),
        "registry_tools_never_gold": sorted(set(registry) - {row.tool_name for row in rows}),
    }
    if selection is not None:
        report["construction_selection"] = dict(selection.summary)
    return tuple(sorted(rows, key=lambda row: row.unit_id)), report


# ---------------------------------------------------------------------------
# Split governance: the block partition proposal
# ---------------------------------------------------------------------------


def _probe_sample_source(name: str, payload: Mapping[str, object]) -> dict[str, object]:
    """One audio2tool probe-sample receipt as an identity source.

    ``roster_role`` is the E2.3 field: absent means the historical default,
    an EVALUATION identity roster (every receipt committed before 2026-09-05
    is one), ``"construction"`` means the identities may be read WITH their
    gold labels and are therefore deliberately NOT exposure, and any other
    value fails closed rather than being guessed at. Both roles are returned;
    :func:`_exposure_sources` keeps the evaluation ones as exposure and uses
    the construction ones only to recognise a construction identity elsewhere.
    """

    role = payload.get("roster_role", EVALUATION_ROSTER_ROLE)
    if role not in _ROSTER_ROLES:
        raise RailsError(
            f"probe-sample receipt {name!r} declares roster_role {role!r}; the known "
            f"roles are {sorted(_ROSTER_ROLES)} (fail-closed)"
        )
    items = payload["items"]  # audio2tool_receipts already verified the shape
    return {
        "kind": "probe-sample",
        "name": name,
        "relpath": f"{PROBE_SAMPLE_RELDIR}/{name}.json",
        "roster_role": role,
        "sample_ids": frozenset(
            f"{item['tier']}:{int(item['id']):06d}" for item in items
        ),
    }


def _d1_supplement_source(path: Path) -> dict[str, object]:
    """One committed D1 media supplement as an exposure source.

    Every id under ``manifest[]`` is an identity this study has already bound
    to real media bytes for a flight, so it is exposure whatever its shape --
    including the derived ids (``a2t-g3-dialogue:000318``) that name no pool
    unit at all and therefore reserve no block. Malformed is REFUSED, never
    skipped: a supplement this reader cannot parse is a hole in the union.
    """

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RailsError(f"cannot read D1 media supplement {path}: {error}") from error
    if not isinstance(document, Mapping):
        raise RailsError(f"D1 media supplement {path} must be a JSON object")
    if document.get("schema") != D1_SUPPLEMENT_SCHEMA:
        raise RailsError(
            f"D1 media supplement {path} schema {document.get('schema')!r} is not "
            f"{D1_SUPPLEMENT_SCHEMA!r}"
        )
    if document.get("carrier_lock_key") != AUDIO2TOOL_LOCK_KEY:
        raise RailsError(
            f"D1 media supplement {path} names carrier "
            f"{document.get('carrier_lock_key')!r}, not {AUDIO2TOOL_LOCK_KEY!r}"
        )
    manifest = document.get("manifest")
    if not isinstance(manifest, list) or not manifest:
        raise RailsError(f"D1 media supplement {path} has no manifest entries")
    ids: set[str] = set()
    for index, entry in enumerate(manifest):
        if not isinstance(entry, Mapping):
            raise RailsError(
                f"D1 media supplement {path} manifest[{index}] is not an object"
            )
        sample_id = entry.get("id")
        if not isinstance(sample_id, str) or not sample_id:
            raise RailsError(
                f"D1 media supplement {path} manifest[{index}] has no non-empty id"
            )
        ids.add(sample_id)
    if document.get("count") != len(manifest) or len(ids) != len(manifest):
        raise RailsError(
            f"D1 media supplement {path} count/manifest/id-uniqueness disagree "
            f"(count={document.get('count')!r}, entries={len(manifest)}, "
            f"distinct ids={len(ids)})"
        )
    return {
        "kind": "d1-media-supplement",
        "name": path.stem,
        "relpath": f"{D1_SUPPLEMENT_RELDIR}/{path.name}",
        "roster_role": EVALUATION_ROSTER_ROLE,
        "sample_ids": frozenset(ids),
    }


#: ``data.runtime_subset``'s receipt schema: a SLURP seeded subset of a runtime view.
RUNTIME_SUBSET_RECEIPT_SCHEMAS = frozenset({
    "saea-runtime-subset-receipt-v1", "saea-runtime-subset-receipt-v2",
})


def _roster_receipt_source(path: Path) -> dict[str, object] | None:
    """One committed ``saea-roster-receipt-v1`` as an identity source.

    Returns ``None`` for another carrier's roster, for a SLURP ``saea-runtime-subset-receipt-v1``/``-v2``
    filed in the same directory (every id must be a ``slurp:`` id), and also for a
    ``saea-a2t-paired-roster-comparator-rows-v1`` companion file committed
    beside a roster receipt in the same directory (it carries no sample
    identities). An Audio2Tool roster
    is returned with its own ``roster_role``; a ``"construction"`` one is not
    exposure -- those identities may be read WITH their gold (owner decision
    2026-09-05) -- and :func:`_exposure_sources` drops it from the union while
    keeping its ids as the construction identity universe. The receipt's own
    ``split_identity_hash`` is recomputed before its items are trusted,
    exactly as the probe-sample reader does.
    """

    from ..core.roster import RECEIPT_SCHEMA, RosterError, verify_roster

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RailsError(f"cannot read roster receipt {path}: {error}") from error
    if not isinstance(document, Mapping):
        raise RailsError(f"roster receipt {path} must be a JSON object")
    if document.get("schema") != RECEIPT_SCHEMA:
        if document.get("schema") == A2T_PAIRED_ROSTER_COMPARATOR_ROWS_SCHEMA:
            # A comparator-rows companion, not a roster receipt: no sample
            # identities to contribute to the exposure union.
            return None
        if document.get("schema") in RUNTIME_SUBSET_RECEIPT_SCHEMAS:
            # A SLURP runtime-subset receipt filed in the shared roster directory. It names no
            # Audio2Tool identity; fail closed if any id is not a SLURP id, so an Audio2Tool
            # subset can never hide behind this schema.
            ids = document.get("sample_ids")
            if (isinstance(ids, list) and ids
                    and all(isinstance(i, str) and i.startswith("slurp:") for i in ids)):
                return None
            raise RailsError(
                f"runtime-subset receipt {path} names a non-SLURP or empty identity list "
                "(fail-closed)"
            )
        raise RailsError(
            f"roster receipt {path} schema {document.get('schema')!r} is not "
            f"{RECEIPT_SCHEMA!r}"
        )
    if document.get("carrier_lock_key") != AUDIO2TOOL_LOCK_KEY:
        return None
    role = document.get("roster_role", EVALUATION_ROSTER_ROLE)
    if role not in _ROSTER_ROLES:
        raise RailsError(
            f"roster receipt {path} declares roster_role {role!r}; the known roles are "
            f"{sorted(_ROSTER_ROLES)} (fail-closed)"
        )
    try:
        verify_roster(document)
    except RosterError as error:
        raise RailsError(f"roster receipt {path} does not verify: {error}") from error
    return {
        "kind": "roster-receipt",
        "name": path.stem,
        "relpath": f"{ROSTER_RECEIPTS_RELDIR}/{path.name}",
        "roster_role": role,
        "sample_ids": frozenset(str(item["sample_id"]) for item in document["items"]),
    }


def _exposure_sources(repo_root: Path | None = None) -> list[dict[str, object]]:
    """Every committed EVALUATION identity source of the Audio2Tool carrier,
    in a deterministic order (probe samples, then D1 supplements, then
    roster receipts; each group sorted by name).

    Three kinds, because this repository froze evaluation identity in three
    different places over the campaign and every one of them is a genuine
    exposure record:

    (a) ``docs/receipts/probe-samples/*.json`` with ``carrier == audio2tool``
        -- the loader's own frozen sample universe (``data.audio2tool
        .audio2tool_receipts`` verifies each one's ``split_identity_hash``
        before this function sees it);
    (b) ``docs/receipts/artifacts/d1-a2t-*.json`` -- the additive D1 media
        supplements, which bind identities to media bytes for a flight and
        exist precisely because a roster's probe-sample receipt carries only
        the ids no earlier receipt covered;
    (c) ``docs/receipts/rosters/*.json`` -- the ``saea-roster-receipt-v1``
        rosters, of which only the ``roster_role == "evaluation"`` ones are
        exposure.

    A D1 supplement carries no role of its own -- ``contracts
    .gate_media_identity`` requires its ten keys EXACTLY, so it cannot be
    given one -- and it is therefore read through the CONSTRUCTION IDENTITY
    UNIVERSE the (a) and (c) receipts declare: an id a committed
    construction-role receipt claims stays out of the union whichever
    artifact binds its media, and a supplement all of whose ids are
    construction is not an exposure source at all. Without that rule a
    construction roster's own flight products would retro-actively remove
    that roster's rows from the construction pool it was drawn from, and no
    committed construction draw would reproduce.

    The frozen 400 (``r1-audio2tool-sample``) must be present or the whole
    union fails closed: it is the one receipt every A2T decontamination
    argument in this repository cites, so silently building a union without
    it would be the exact failure this function exists to prevent.
    """

    root = Path(REPO_ROOT if repo_root is None else repo_root)
    receipts = audio2tool_receipts(root)
    if EXPOSED_RECEIPT_NAME not in receipts:
        raise RailsError(
            f"exposed discovery receipt {EXPOSED_RECEIPT_NAME!r} not found among "
            f"{sorted(receipts)}"
        )
    probes = [_probe_sample_source(name, payload) for name, payload in sorted(receipts.items())]
    rosters: list[dict[str, object]] = []
    roster_dir = root / ROSTER_RECEIPTS_RELDIR
    if roster_dir.is_dir():
        for path in sorted(roster_dir.glob("*.json")):
            source = _roster_receipt_source(path)
            if source is not None:
                rosters.append(source)
    construction: set[str] = set()
    for source in (*probes, *rosters):
        if source["roster_role"] != EVALUATION_ROSTER_ROLE:
            construction |= set(source["sample_ids"])  # type: ignore[arg-type]

    sources = [source for source in probes if source["roster_role"] == EVALUATION_ROSTER_ROLE]
    for path in sorted((root / D1_SUPPLEMENT_RELDIR).glob(D1_SUPPLEMENT_GLOB)):
        supplement = _d1_supplement_source(path)
        ids = frozenset(supplement["sample_ids"]) - construction  # type: ignore[arg-type]
        if ids:
            sources.append({**supplement, "sample_ids": ids})
    sources.extend(
        source for source in rosters if source["roster_role"] == EVALUATION_ROSTER_ROLE
    )
    return sources


def exposed_identity_report(repo_root: Path | None = None) -> dict[str, object]:
    """The exposure union with a per-source account of where it came from.

    ``new_sample_ids`` is each source's MARGINAL contribution in the
    deterministic order above, so the per-source numbers sum to the union
    size and a reader can see which receipt actually widened the hold-out.
    Identity only: no gold, no task text and no score is read anywhere here.
    """

    union: set[str] = set()
    rows: list[dict[str, object]] = []
    for source in _exposure_sources(repo_root):
        ids = source["sample_ids"]
        assert isinstance(ids, frozenset)
        rows.append(
            {
                "kind": source["kind"],
                "name": source["name"],
                "relpath": source["relpath"],
                "roster_role": source["roster_role"],
                "sample_ids": len(ids),
                "new_sample_ids": len(ids - union),
            }
        )
        union |= ids
    counts_by_kind: Counter[str] = Counter(str(row["kind"]) for row in rows)
    return {
        "policy_id": EXPOSURE_UNION_POLICY_ID,
        "sources": rows,
        "source_count": len(rows),
        "sources_by_kind": dict(sorted(counts_by_kind.items())),
        "union_sample_ids": len(union),
        "excluded_roster_role": CONSTRUCTION_ROSTER_ROLE,
        "note": (
            "Union of every committed EVALUATION identity of the audio2tool carrier: "
            "probe-sample receipts, additive D1 media supplements, and roster-v1 "
            "receipts whose roster_role is 'evaluation'. Construction-role rosters are "
            "excluded by design (owner decision 2026-09-05: construction identities may "
            "be read with their gold labels, evaluation identities never can)."
        ),
    }


def exposed_sample_ids(repo_root: Path | None = None) -> frozenset[str]:
    """Every committed EVALUATION sample id of the Audio2Tool carrier.

    Was, until 2026-09-05, the frozen 400 of ``r1-audio2tool-sample`` alone,
    which had become a large under-count: the three official-population
    rosters, the two 104-row AgentLoop cohorts and the ORG-1 union manifest
    have all been flown since. See :func:`exposed_identity_report` for the
    per-source account and :func:`_exposure_sources` for what counts.
    """

    union: set[str] = set()
    for source in _exposure_sources(repo_root):
        ids = source["sample_ids"]
        assert isinstance(ids, frozenset)
        union |= ids
    return frozenset(union)


@dataclass(frozen=True)
class PartitionProposal:
    """A PROPOSED construction-versus-evaluation partition. Not a registered
    split: registering ``eval_sample_ids`` as a flyable roster was always
    "later campaign work with its own preregistration", and it never
    happened -- ``A2T-FRESH-800-V1`` became the registered fresh reserve
    instead. Since the 2026-09-05 retirement of the proposed tier,
    ``eval_items``/``eval_blocks``/``eval_sample_ids`` are EMPTY unless the
    caller asked for the legacy draw with ``eval_per_tier > 0``, and
    ``split_identity_hash()`` is then the sha256 of the empty string. Every
    field is kept so a legacy generator that pins the old identity still
    fails CLOSED on the hash rather than on an attribute error."""

    policy_id: str
    seed: int
    construction: tuple[A2tKbRow, ...]
    eval_items: tuple[tuple[str, int, str, str], ...]
    reserved_exposed_blocks: tuple[int, ...]
    eval_blocks: tuple[int, ...]
    report: Mapping[str, object]

    @property
    def eval_sample_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(f"{tier}:{item_id:06d}" for tier, item_id, _text, _tool in self.eval_items)
        )

    def split_identity_hash(self) -> str:
        return hashlib.sha256("\n".join(self.eval_sample_ids).encode("utf-8")).hexdigest()


def propose_partition(
    rows: Sequence[A2tKbRow],
    exposed: frozenset[str],
    *,
    seed: int = 20260807,
    eval_per_tier: int = 0,
    tool_min_pool_rows: int = EVAL_TOOL_MIN_POOL_ROWS,
) -> PartitionProposal:
    """Partition the carrier's ``query_idx`` BLOCKS two ways -- three when a
    caller explicitly asks for the retired evaluation tier back.

    1. **RESERVED-EXPOSED** -- every block touched by the exposure union
       (:func:`exposed_sample_ids`). Held out of BOTH sides. An exposed
       roster may still fly as the campaign plan's SECONDARY comparator;
       holding its cross-tier siblings out too is the conservative choice
       that makes that secondary reading safe against the same knowledge
       base.
    2. **EVAL** -- ``eval_per_tier`` is 0 by DEFAULT and the tier is then
       EMPTY. With a positive value: a seeded, tier-stratified draw of
       ``eval_per_tier`` items per tier, each from a DISTINCT block, whose
       whole block is then reserved. Tiers are processed in ascending order
       of candidate count (scarcest first: tier8 has only 821 items) so a
       later tier can never be starved by an earlier one, then by tier name;
       the order is deterministic and independent of pool order.
    3. **CONSTRUCTION** -- every remaining block. This is the KB TRAIN pool.

    WHY THE EVALUATION TIER IS RETIRED BY DEFAULT (owner-coordinator
    decision 2026-09-05). The 400-block tier this function used to carve was
    a PROPOSAL and was never registered as a flyable split; nothing has ever
    flown it. ``A2T-FRESH-800-V1``
    (``docs/receipts/rosters/a2t-fresh-800-v1.json``, ``roster_role``
    ``evaluation``, RESERVED_AND_UNOPENED) is the fresh reserve now, it is
    inside the exposure union, and its blocks are therefore already held out
    by clause 1. The proposal only cost the construction side -- it held 204
    of ``A2T-CONSTRUCTION-800-V1``'s 483 blocks, which is exactly the pool a
    knowledge base is built from -- so the default now retires it and
    construction is every block the exposure union does not hold.

    REPRODUCIBILITY OF THE SEALED RECEIPTS. Passing ``eval_per_tier=50``
    reproduces the pre-retirement partition BYTE FOR BYTE on the same rows,
    exposure set and seed: the draw, the tier order, the floors and the
    reported keys are unchanged, only the default moved. Every generator
    that cites a pinned ``split_identity_hash`` from before this change --
    ``scripts/build_a2t_g3_plain_english_cards.py``,
    ``scripts/build_a2t_g4_semantic_cards.py``,
    ``scripts/build_a2t_g5_family_contracts.py``,
    ``scripts/build_a2t_g7_example_ground.py``,
    ``scripts/build_a2t_structured_action_schema.py``,
    ``scripts/build_a2t_frozen_semantic_runtime_assets.py`` and the frozen
    launchers under ``docs/checks/`` -- must therefore pass
    ``eval_per_tier=50`` to reproduce, and fails CLOSED on its pinned hash
    if it does not.

    Eval candidacy (a positive ``eval_per_tier`` only) additionally requires
    the item's gold primary tool to have at least ``tool_min_pool_rows``
    units in the exposure-free pool, so the build's hard "at least one
    exemplar per tool" floor can never be starved by the evaluation draw;
    the whole BLOCK of any such rare tool is held out of candidacy too,
    because a block is shared across tiers and drawing a sibling would
    reserve it. EVERY OTHER tool additionally keeps ONE deterministic block
    -- the block of its lexicographically first unit -- out of candidacy, so
    the floor holds for tools that clear ``tool_min_pool_rows`` yet have few
    free blocks; without it an ``eval_per_tier=50`` draw against the
    A2T-FRESH-800-bearing exposure union starves nine smart_home tools. With
    the tier retired NOTHING can be drawn, so those protections reserve
    nothing and the report's ``blocks_protected_*`` counts are 0 by
    construction rather than by luck. The tools whose every unit already
    sits inside an exposed block -- which the construction pool cannot
    represent no matter how the tier is drawn -- are still named in the
    report, and the fail-closed floor check still refuses a partition that
    starves a tool the free pool could have supplied.
    """

    rows = tuple(rows)
    if not rows:
        raise RailsError("propose_partition: rows must be non-empty")
    if (
        isinstance(eval_per_tier, bool)
        or not isinstance(eval_per_tier, int)
        or eval_per_tier < 0
    ):
        raise RailsError(
            "propose_partition: eval_per_tier must be a non-negative int "
            "(0 retires the proposed evaluation tier)"
        )

    exposed_blocks = frozenset(
        row.query_idx
        for row in rows
        if any(sample_id in exposed for sample_id in row.sample_ids)
    )
    free_rows = tuple(row for row in rows if row.query_idx not in exposed_blocks)
    if not free_rows:
        raise RailsError("propose_partition: exposure reserved the whole pool")
    tool_pool_counts = Counter(row.tool_name for row in free_rows)
    construction_only_tools = sorted(
        tool for tool, count in tool_pool_counts.items() if count < tool_min_pool_rows
    )

    construction_only = set(construction_only_tools)
    rare_protected_blocks: frozenset[int] = frozenset()
    floor_blocks: set[int] = set()
    order: list[str] = []
    eval_items: list[tuple[str, int, str, str]] = []
    per_tier_drawn: dict[str, int] = {}
    reserved: set[int] = set()

    if eval_per_tier:
        # BLOCK-level protection of the construction floor (2026-09-05 repair).
        # Dropping a construction-only tool's own ROWS from eval candidacy was
        # never enough: a query_idx block is shared across tiers, so another
        # tier's candidate in the SAME block could still be drawn, reserving the
        # block and taking the rare tool's last exemplar with it. Under the
        # frozen-400-only exposure roster the free pool was large enough that
        # this never fired; under the full exposure union it fires immediately
        # (foldExteriorMirrors and initiateAutoPark keep exactly one free unit
        # each). Protecting the whole BLOCK is the fix, and it is stated in the
        # report rather than left implicit.
        rare_protected_blocks = frozenset(
            row.query_idx for row in free_rows if row.tool_name in construction_only
        )

        # ONE-BLOCK FLOOR FOR EVERY OTHER TOOL (2026-09-05, second repair, MF-1).
        # Protecting only the RARE tools' blocks still let the draw starve a tool
        # that clears ``tool_min_pool_rows`` but whose free blocks are few and
        # shared: under the exposure union that now also reserves A2T-FRESH-800,
        # an eval_per_tier=50 draw wiped out nine smart_home tools
        # (broadcastMessage, castContent, controlPlayback_home, getCameraStream,
        # rampBrightness, setAdaptiveLighting, setApplianceMode, setBrightness,
        # setHumidifierState) and the fail-closed floor check refused the whole
        # partition. Reserving ONE deterministic block per remaining tool -- the
        # block of its lexicographically first unit, skipped when one of its
        # blocks is already protected -- makes ``missing_tools`` unreachable by
        # construction instead of leaving it to the draw's luck. The cost is
        # bounded and reported: the extra blocks never enter eval candidacy.
        rows_by_tool: dict[str, list[A2tKbRow]] = defaultdict(list)
        for row in free_rows:
            rows_by_tool[row.tool_name].append(row)
        for tool in sorted(rows_by_tool):
            if tool in construction_only:
                continue
            tool_rows = sorted(rows_by_tool[tool], key=lambda row: row.unit_id)
            if any(
                row.query_idx in rare_protected_blocks or row.query_idx in floor_blocks
                for row in tool_rows
            ):
                continue
            floor_blocks.add(tool_rows[0].query_idx)
        protected_blocks = frozenset(rare_protected_blocks | floor_blocks)

        candidates_by_tier: dict[str, list[A2tKbRow]] = defaultdict(list)
        for row in free_rows:
            if row.tool_name in construction_only or row.query_idx in protected_blocks:
                continue
            candidates_by_tier[row.tier].append(row)

        order = sorted(
            candidates_by_tier, key=lambda tier: (len(candidates_by_tier[tier]), tier)
        )
        for tier in order:
            pool = sorted(
                (row for row in candidates_by_tier[tier] if row.query_idx not in reserved),
                key=lambda row: row.unit_id,
            )
            if len(pool) < eval_per_tier:
                raise RailsError(
                    f"propose_partition: tier {tier!r} offers only {len(pool)} block-free "
                    f"candidates for a draw of {eval_per_tier}"
                )
            rng = random.Random(f"{seed}:{tier}")
            picked = rng.sample(range(len(pool)), eval_per_tier)
            for index in sorted(picked):
                row = pool[index]
                reserved.add(row.query_idx)
                # One wav per drawn unit: the lowest item id, so the draw is a
                # deterministic ITEM roster and never two near-identical
                # renderings of one unit.
                eval_items.append((row.tier, row.item_ids[0], row.text, row.tool_name))
            per_tier_drawn[tier] = eval_per_tier
    else:
        # THE RETIRED TIER (default). Nothing is drawn, so nothing has to be
        # protected FROM the draw: the floors above exist only to keep eval
        # candidacy from taking a tool's last free block, and with no candidacy
        # they would reserve blocks against nothing. Construction is therefore
        # every block the exposure union does not hold, and the report's
        # protection counts are honestly 0.
        protected_blocks = frozenset()

    eval_blocks = frozenset(reserved)
    construction = tuple(row for row in free_rows if row.query_idx not in eval_blocks)
    if not construction:
        raise RailsError("propose_partition: empty construction pool")

    # The floor is measured against what the EXPOSURE-FREE pool can possibly
    # deliver, not against every tool the carrier has ever used (2026-09-05
    # repair). A tool whose every unit sits inside an already-exposed block
    # cannot enter the construction pool no matter how the evaluation tier is
    # drawn, so raising on it would be blaming the draw for the exposure
    # union; it is REPORTED by name instead, and the draw is still refused if
    # it starves a tool the free pool could have supplied.
    tools_reserved_by_exposure = sorted(
        {row.tool_name for row in rows} - set(tool_pool_counts)
    )
    missing_tools = sorted(
        set(tool_pool_counts) - {row.tool_name for row in construction}
    )
    if missing_tools:
        raise RailsError(
            "propose_partition: the evaluation draw starved the construction floor for "
            f"tools {missing_tools}"
        )

    eval_ids = {f"{tier}:{item_id:06d}" for tier, item_id, _text, _tool in eval_items}
    construction_ids = {sid for row in construction for sid in row.sample_ids}
    if eval_ids & construction_ids:
        raise RailsError("propose_partition: eval and construction sample ids intersect")
    if eval_ids & set(exposed):
        raise RailsError("propose_partition: eval intersects the frozen exposed 400")
    if construction_ids & set(exposed):
        raise RailsError("propose_partition: construction intersects the frozen exposed 400")

    report = {
        "policy_id": A2T_PARTITION_POLICY_ID,
        "seed": seed,
        "eval_per_tier": eval_per_tier,
        "eval_tier_retired": eval_per_tier == 0,
        "eval_tool_min_pool_rows": tool_min_pool_rows,
        "blocks_total": len({row.query_idx for row in rows}),
        "blocks_reserved_exposed": len(exposed_blocks),
        "blocks_eval": len(eval_blocks),
        "blocks_construction": len({row.query_idx for row in construction}),
        "units_total": len(rows),
        "units_reserved_exposed": len(rows) - len(free_rows),
        "units_eval_drawn": len(eval_items),
        "units_construction": len(construction),
        "items_construction": sum(len(row.sample_ids) for row in construction),
        "eval_items_by_tier": dict(sorted(per_tier_drawn.items())),
        "eval_draw_order": list(order),
        "construction_only_tools": construction_only_tools,
        "construction_only_tool_units": {
            tool: tool_pool_counts[tool] for tool in construction_only_tools
        },
        "blocks_protected_for_construction_only_tools": len(rare_protected_blocks),
        "blocks_protected_for_tool_floor": len(floor_blocks),
        "blocks_protected_total": len(protected_blocks),
        "tools_reserved_entirely_by_exposure": tools_reserved_by_exposure,
        # The per-tool construction floor, stated rather than left implicit:
        # every tool the EXPOSURE-FREE pool can supply must survive into the
        # construction pool. ``tools_missing`` is [] by the fail-closed check
        # above -- it is reported so a reader of the receipt sees the floor
        # was evaluated, not assumed.
        "construction_floor": {
            "rule": (
                "every tool the exposure-free pool can supply must appear in the "
                "construction pool"
            ),
            "tools_supplied_by_free_pool": len(tool_pool_counts),
            "tools_in_construction": len({row.tool_name for row in construction}),
            "tools_missing": missing_tools,
            "satisfied": True,
        },
        "construction_units_by_tier": dict(
            sorted(Counter(row.tier for row in construction).items())
        ),
        "construction_tool_count": len({row.tool_name for row in construction}),
        "eval_tools_covered": len({tool for _t, _i, _x, tool in eval_items}),
    }
    return PartitionProposal(
        policy_id=A2T_PARTITION_POLICY_ID,
        seed=seed,
        construction=construction,
        eval_items=tuple(sorted(eval_items)),
        reserved_exposed_blocks=tuple(sorted(exposed_blocks)),
        eval_blocks=tuple(sorted(eval_blocks)),
        report=report,
    )


# ---------------------------------------------------------------------------
# Model-free build spec
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tKnowledgeBuildSpec:
    """Model-free KB-BUILD-A2T configuration. ``datastore_size=None`` selects
    the entire construction pool (the 'full' tier)."""

    carrier_lock_key: str = AUDIO2TOOL_LOCK_KEY
    datastore_size: int | None = None
    seed: int = 20260825
    dimensions: tuple[str, ...] = _DEFAULT_DIMENSIONS

    def validate(self) -> "A2tKnowledgeBuildSpec":
        if self.carrier_lock_key != AUDIO2TOOL_LOCK_KEY:
            raise RailsError(
                "KB-BUILD-A2T is Audio2Tool-only; got carrier_lock_key="
                f"{self.carrier_lock_key!r}"
            )
        if self.datastore_size is not None and (
            isinstance(self.datastore_size, bool)
            or not isinstance(self.datastore_size, int)
            or self.datastore_size <= 0
        ):
            raise RailsError(
                "A2tKnowledgeBuildSpec.datastore_size must be a positive int or None"
            )
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise RailsError("A2tKnowledgeBuildSpec.seed must be an int")
        if (
            not isinstance(self.dimensions, tuple)
            or not self.dimensions
            or len(set(self.dimensions)) != len(self.dimensions)
            or not set(self.dimensions) <= _ALLOWED_DIMENSIONS
        ):
            raise RailsError(
                "A2tKnowledgeBuildSpec.dimensions must be a non-empty, duplicate-free "
                f"tuple drawn from {sorted(_ALLOWED_DIMENSIONS)}"
            )
        if not ({"content", "label"} & set(self.dimensions)):
            raise RailsError(
                "A2tKnowledgeBuildSpec.dimensions must include 'content' or 'label' so "
                "every value has at least one grounded facet"
            )
        return self


# ---------------------------------------------------------------------------
# Distribution-modeled sampling with tool-shaped floors
# ---------------------------------------------------------------------------


def _shingles(text: str) -> frozenset[str]:
    """Alias kept for backward compatibility; moved to
    :func:`.knowledge_build_common.shingles` (C4b consolidation)."""

    return shingles(text)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    """Alias kept for backward compatibility; moved to
    :func:`.knowledge_build_common.jaccard` (C4b consolidation)."""

    return jaccard(a, b)


def _greedy_diverse_pick(
    candidates: Sequence[A2tKbRow],
    count: int,
    already_selected: Sequence[A2tKbRow],
    rng: random.Random,
    *,
    tool_cap: int,
) -> list[A2tKbRow]:
    """Alias kept for backward compatibility, same call signature as before
    C4b consolidation: delegates to the shared, row-shape-generalized
    :func:`.knowledge_build_common.greedy_diverse_pick` with Audio2Tool's own
    ``text``/``unit_id``/``tool_name`` accessors plugged in."""

    return greedy_diverse_pick(
        candidates,
        count,
        already_selected,
        rng,
        text_of=lambda row: row.text,
        id_of=lambda row: row.unit_id,
        group_of=lambda row: row.tool_name,
        group_cap=tool_cap,
    )


def _hamilton_apportion(capacity_by_key: Mapping[str, int], total: int) -> dict[str, int]:
    """Alias kept for backward compatibility; moved to
    :func:`.knowledge_build_common.hamilton_apportion` (C4b consolidation)."""

    return hamilton_apportion(capacity_by_key, total)


def distribution_sample_a2t(
    rows: Sequence[A2tKbRow], size: int | None, seed: int
) -> tuple[A2tKbRow, ...]:
    """Distribution-modeled construction-pool selection with THREE hard
    floors (campaign plan section 3.2): at least one exemplar per GOLD TOOL,
    at least one per ARGUMENT-PATTERN FAMILY ``(tool, sorted argument keys)``,
    and at least one per TIER. The remaining budget is Hamilton-apportioned
    over TIER strata (the plan's "tier-stratified") and filled by greedy
    content-diversity picks under a soft per-tool cap.

    ``size=None`` selects the whole pool. When the floors alone already meet
    or exceed ``size``, the floor set IS the returned (larger) selection:
    floors are a HARD requirement, ``size`` a best-effort target.

    Deterministic and pool-order independent: every draw samples a
    ``unit_id``-sorted candidate list through ``random.Random`` seeded by a
    namespaced tag.
    """

    rows = tuple(rows)
    if not rows:
        raise RailsError("distribution_sample_a2t: rows must be non-empty")
    rows_by_id = {row.unit_id: row for row in rows}
    if len(rows_by_id) != len(rows):
        raise RailsError("distribution_sample_a2t: rows must have unique unit_id values")

    if size is None or size >= len(rows):
        return tuple(sorted(rows, key=lambda row: row.unit_id))
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise RailsError("distribution_sample_a2t: size must be a positive int or None")

    selected_ids: set[str] = set()

    # Phase 1: every gold tool keeps at least one exemplar.
    rows_by_tool: dict[str, list[A2tKbRow]] = defaultdict(list)
    for row in rows:
        rows_by_tool[row.tool_name].append(row)
    for tool in sorted(rows_by_tool):
        pool = sorted(rows_by_tool[tool], key=lambda row: row.unit_id)
        rng = random.Random(f"{seed}:tool:{tool}")
        selected_ids.add(pool[rng.randrange(len(pool))].unit_id)

    # Phase 2: every argument-pattern family keeps at least one exemplar.
    rows_by_family: dict[tuple[str, tuple[str, ...]], list[A2tKbRow]] = defaultdict(list)
    for row in rows:
        rows_by_family[row.family_key].append(row)
    covered = {rows_by_id[i].family_key for i in selected_ids}
    for family in sorted(set(rows_by_family) - covered):
        pool = sorted(rows_by_family[family], key=lambda row: row.unit_id)
        unselected = [row for row in pool if row.unit_id not in selected_ids]
        candidates = unselected or pool
        rng = random.Random(f"{seed}:family:{family[0]}:{'|'.join(family[1])}")
        selected_ids.add(candidates[rng.randrange(len(candidates))].unit_id)

    # Phase 3: every tier keeps at least one exemplar.
    rows_by_tier: dict[str, list[A2tKbRow]] = defaultdict(list)
    for row in rows:
        rows_by_tier[row.tier].append(row)
    covered_tiers = {rows_by_id[i].tier for i in selected_ids}
    for tier in sorted(set(rows_by_tier) - covered_tiers):
        pool = sorted(rows_by_tier[tier], key=lambda row: row.unit_id)
        rng = random.Random(f"{seed}:tier:{tier}")
        selected_ids.add(pool[rng.randrange(len(pool))].unit_id)

    floor_count = len(selected_ids)
    if size <= floor_count:
        return tuple(
            sorted((rows_by_id[i] for i in selected_ids), key=lambda row: row.unit_id)
        )

    # Phase 4: Hamilton-apportion the remaining budget over TIER strata.
    remaining_budget = size - floor_count
    floor_by_tier: Counter[str] = Counter(rows_by_id[i].tier for i in selected_ids)
    capacity_by_tier = {
        tier: len(members) - floor_by_tier.get(tier, 0)
        for tier, members in rows_by_tier.items()
    }
    additional_by_tier = _hamilton_apportion(capacity_by_tier, remaining_budget)
    for tier in sorted(rows_by_tier):
        extra = additional_by_tier.get(tier, 0)
        if extra <= 0:
            continue
        already = [rows_by_id[i] for i in selected_ids if rows_by_id[i].tier == tier]
        candidate_pool = [
            row for row in rows_by_tier[tier] if row.unit_id not in selected_ids
        ]
        target_stratum_size = len(already) + extra
        tool_cap = max(1, math.ceil(0.10 * target_stratum_size))
        rng = random.Random(f"{seed}:{tier}")
        for row in _greedy_diverse_pick(
            candidate_pool, extra, already, rng, tool_cap=tool_cap
        ):
            selected_ids.add(row.unit_id)

    return tuple(sorted((rows_by_id[i] for i in selected_ids), key=lambda row: row.unit_id))


# ---------------------------------------------------------------------------
# Facet / value emission
# ---------------------------------------------------------------------------


def _pattern_text(signature: Sequence[str]) -> str:
    return "(" + ", ".join(signature) + ")" if signature else "(no arguments)"


def _build_facets_and_values(
    selected: Sequence[A2tKbRow],
    rows: Sequence[A2tKbRow],
    spec: A2tKnowledgeBuildSpec,
    registry: Mapping[str, Mapping[str, str]],
    *,
    governed_relpath_by_tier: Mapping[str, str],
) -> tuple[list[KeyFacet], list[ValueBundle]]:
    dims = set(spec.dimensions)

    rows_by_tool_full: dict[str, list[A2tKbRow]] = defaultdict(list)
    rows_by_category_full: dict[tuple[str, str], list[A2tKbRow]] = defaultdict(list)
    # The JOINT count -- rows carrying this tool AND this (domain, category).
    # It exists so the value-side prior can condition on the category instead
    # of dividing two independently-keyed global counts; see the prior_score
    # comment below.
    rows_by_tool_in_category_full: Counter[tuple[str, str, str]] = Counter()
    patterns_by_tool_full: dict[str, Counter[tuple[str, ...]]] = defaultdict(Counter)
    pairs_by_tool_full: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        rows_by_tool_full[row.tool_name].append(row)
        rows_by_category_full[(row.domain, row.category)].append(row)
        rows_by_tool_in_category_full[(row.domain, row.category, row.tool_name)] += 1
        patterns_by_tool_full[row.tool_name][row.arg_signature] += 1
        for key, value in row.arg_pairs:
            pairs_by_tool_full[row.tool_name][key].add(value)

    selected_by_tool: dict[str, list[A2tKbRow]] = defaultdict(list)
    for row in selected:
        selected_by_tool[row.tool_name].append(row)

    facets: list[KeyFacet] = []
    content_facet_id: dict[str, str] = {}
    tool_facet_id: dict[str, str] = {}
    prior_facet_id: dict[str, str] = {}
    prior_representation: dict[str, str] = {}
    speaker_facet_id: dict[str, str] = {}

    # ---- label dimension: domain -> category -> tool -------------------
    if "label" in dims:
        for domain in sorted({row.domain for row in selected}):
            domain_rows = [row for row in selected if row.domain == domain]
            domain_fid = f"facet:label:domain:{domain}"
            facets.append(
                KeyFacet(
                    facet_id=domain_fid,
                    dimension="label",
                    representation_kind="text",
                    representation=(
                        f"Tool domain '{domain}' ({len(domain_rows)} construction "
                        "invocations in this snapshot)."
                    ),
                    source_sample_ids=tuple(
                        sorted({sid for row in domain_rows for sid in row.sample_ids})
                    ),
                ).validate()
            )
            for category in sorted({row.category for row in domain_rows}):
                category_rows = [row for row in domain_rows if row.category == category]
                category_fid = f"facet:label:category:{domain}:{category}"
                facets.append(
                    KeyFacet(
                        facet_id=category_fid,
                        dimension="label",
                        representation_kind="text",
                        representation=(
                            f"Tool category '{category}' under domain '{domain}' "
                            f"({len(category_rows)} construction invocations in this "
                            "snapshot)."
                        ),
                        source_sample_ids=tuple(
                            sorted({sid for row in category_rows for sid in row.sample_ids})
                        ),
                        parent_facet_ids=(domain_fid,),
                    ).validate()
                )
                for tool in sorted({row.tool_name for row in category_rows}):
                    if tool in tool_facet_id:
                        continue
                    tool_rows = [row for row in selected if row.tool_name == tool]
                    entry = registry.get(tool, {})
                    signature = entry.get("signature", "")
                    description = entry.get("description", "")
                    constraints = entry.get("argument_constraints", "")
                    defaults = entry.get("argument_defaults", "")
                    tool_fid = f"facet:label:tool:{tool}"
                    facets.append(
                        KeyFacet(
                            facet_id=tool_fid,
                            dimension="label",
                            representation_kind="text",
                            representation=(
                                f"Tool '{tool}' (domain='{domain}', category='{category}'); "
                                f"registry signature {signature or 'unavailable'}; "
                                f"{description or 'no registry description'} "
                                f"Argument defaults: {defaults or 'none'}. "
                                f"Argument constraints: {constraints or 'none'}. "
                                f"{len(tool_rows)} construction invocations in this snapshot."
                            ),
                            source_sample_ids=tuple(
                                sorted({sid for row in tool_rows for sid in row.sample_ids})
                            ),
                            parent_facet_ids=(category_fid,),
                        ).validate()
                    )
                    tool_facet_id[tool] = tool_fid

    # ---- content dimension: one facet per selected invocation ----------
    if "content" in dims:
        for row in selected:
            parent = (tool_facet_id[row.tool_name],) if row.tool_name in tool_facet_id else ()
            content_fid = f"facet:content:{row.unit_id}"
            facets.append(
                KeyFacet(
                    facet_id=content_fid,
                    dimension="content",
                    representation_kind="text",
                    representation=row.text,
                    source_sample_ids=row.sample_ids,
                    parent_facet_ids=parent,
                ).validate()
            )
            content_facet_id[row.unit_id] = content_fid

    # ---- speaker dimension (off by default; see module docstring) ------
    if "speaker" in dims:
        rows_by_speaker: dict[str, list[A2tKbRow]] = defaultdict(list)
        for row in selected:
            rows_by_speaker[row.speaker_ids[0]].append(row)
        for speaker_id in sorted(rows_by_speaker):
            speaker_rows = rows_by_speaker[speaker_id]
            speaker_fid = f"facet:speaker:{speaker_id}"
            histogram = Counter(row.tier for row in speaker_rows)
            hist_text = ", ".join(
                f"{tier}={count}"
                for tier, count in sorted(histogram.items(), key=lambda kv: (-kv[1], kv[0]))
            )
            facets.append(
                KeyFacet(
                    facet_id=speaker_fid,
                    dimension="speaker",
                    representation_kind="text",
                    representation=(
                        f"Synthetic voice '{speaker_id}': {len(speaker_rows)} construction "
                        f"invocations in this snapshot; tier histogram: {hist_text}."
                    ),
                    source_sample_ids=tuple(
                        sorted({sid for row in speaker_rows for sid in row.sample_ids})
                    ),
                ).validate()
            )
            speaker_facet_id[speaker_id] = speaker_fid

    # ---- prior dimension: p(argument pattern | tool) -------------------
    if "prior" in dims:
        for tool in sorted(selected_by_tool):
            total = len(rows_by_tool_full.get(tool, ()))
            patterns = patterns_by_tool_full.get(tool, Counter())
            if patterns and total:
                pattern_text = "; ".join(
                    f"{_pattern_text(signature)}={count / total:.4f} ({count}/{total})"
                    for signature, count in sorted(
                        patterns.items(), key=lambda item: (-item[1], item[0])
                    )
                )
                key_counts: Counter[str] = Counter()
                for signature, count in patterns.items():
                    for key in signature:
                        key_counts[key] += count
                key_text = (
                    "; ".join(
                        f"{key}={count / total:.4f} ({count}/{total})"
                        for key, count in sorted(
                            key_counts.items(), key=lambda item: (-item[1], item[0])
                        )
                    )
                    or "no argument keys observed"
                )
                representation = (
                    f"Argument-pattern prior for tool '{tool}' from full construction-pool "
                    f"counts (n={total} invocations). Patterns: {pattern_text}. "
                    f"Argument keys: {key_text}."
                )
            else:
                representation = (
                    f"Argument-pattern prior for tool '{tool}' from full construction-pool "
                    f"counts (n={total} invocations): no argument patterns observed."
                )
            prior_fid = f"facet:prior:{tool}"
            facets.append(
                KeyFacet(
                    facet_id=prior_fid,
                    dimension="prior",
                    representation_kind="text",
                    representation=representation,
                    source_sample_ids=tuple(
                        sorted(
                            {sid for row in selected_by_tool[tool] for sid in row.sample_ids}
                        )
                    ),
                ).validate()
            )
            prior_facet_id[tool] = prior_fid
            prior_representation[tool] = representation

    # ---- values: one ValueBundle per selected invocation ----------------
    values: list[ValueBundle] = []
    for row in selected:
        entry = registry.get(row.tool_name, {})
        signature = entry.get("signature", "")
        description = entry.get("description", "")
        constraints = entry.get("argument_constraints", "")
        defaults = entry.get("argument_defaults", "")
        own_pattern = (
            "; ".join(f"{key}={value}" for key, value in row.arg_pairs)
            if row.arg_pairs
            else "no arguments"
        )
        other_patterns = sorted(
            candidate
            for candidate in patterns_by_tool_full.get(row.tool_name, Counter())
            if candidate != row.arg_signature
        )[:5]
        other_text = (
            ", ".join(_pattern_text(item) for item in other_patterns)
            if other_patterns
            else "no other argument pattern observed for this tool"
        )
        filler_lines = []
        for key in sorted(pairs_by_tool_full.get(row.tool_name, {})):
            observed = sorted(pairs_by_tool_full[row.tool_name][key])[:5]
            filler_lines.append(f"{key}: {', '.join(observed)}")
        filler_text = "; ".join(filler_lines) if filler_lines else "no argument values observed"
        extra_text = (
            f" Further calls in this exemplar: {', '.join(row.extra_call_names)}."
            if row.extra_call_names
            else ""
        )
        content_text = (
            f'Invocation exemplar: "{row.text}" -> tool call: {row.call_render}. '
            f"Tool '{row.tool_name}' (domain={row.domain}, category={row.category}); "
            f"registry signature {signature or 'unavailable'}; "
            f"{description or 'no registry description'} "
            f"Argument defaults: {defaults or 'none'}. "
            f"Argument constraints: {constraints or 'none'}. "
            f"This exemplar's argument pattern: {own_pattern}. "
            f"Other argument patterns for this tool: {other_text}. "
            f"Argument values observed for this tool in the construction pool: "
            f"{filler_text}.{extra_text}"
        )
        if row.tool_name in prior_representation:
            content_text += f" {prior_representation[row.tool_name]}"

        # p(tool | domain, category). BOTH counts range over the SAME
        # population -- the rows of this one (domain, category) -- because
        # that is what conditioning on the category MEANS. Before
        # 2026-08-25 the numerator was ``len(rows_by_tool_full[tool])``, this
        # tool's rows over the WHOLE construction pool, against a denominator
        # counting one (domain, category) only. The numerator was then not a
        # subset of the denominator, the ratio was not a conditional
        # probability, and it reached 4.1 on the pinned snapshot
        # ``ec2f9ec4...9fb2`` with 193 of 12,601 values above 1 -- which the
        # ranker then read as prior MASS and let monopolise its admission
        # window. Repair record:
        # ``docs/readiness/2026-08-25-prior-score-semantics-repair.md``.
        category_total = len(rows_by_category_full.get((row.domain, row.category), ()))
        tool_total_in_category = rows_by_tool_in_category_full.get(
            (row.domain, row.category, row.tool_name), 0
        )
        prior_score = tool_total_in_category / category_total if category_total else 0.0

        associated: list[str] = []
        if row.tool_name in tool_facet_id:
            associated.append(tool_facet_id[row.tool_name])
        if row.unit_id in content_facet_id:
            associated.append(content_facet_id[row.unit_id])
        if row.speaker_ids and row.speaker_ids[0] in speaker_facet_id:
            associated.append(speaker_facet_id[row.speaker_ids[0]])
        if row.tool_name in prior_facet_id:
            associated.append(prior_facet_id[row.tool_name])
        if not associated:
            raise RailsError(
                f"KB-BUILD-A2T value for unit {row.unit_id!r} has no associated facet"
            )

        governed = governed_relpath_by_tier.get(row.tier, f"audio2tool/{row.tier}.json")
        provenance_refs = tuple(
            sorted(
                {
                    *(f"sample:{sid}" for sid in row.sample_ids),
                    f"utterance:{row.unit_id}",
                    f"tool:{row.tool_name}",
                    f"governed-json:{governed}#query_idx={row.query_idx}",
                }
            )
        )
        values.append(
            ValueBundle(
                value_id=f"value:{row.unit_id}",
                content=content_text,
                associated_facet_ids=tuple(sorted(set(associated))),
                source_sample_ids=row.sample_ids,
                provenance_refs=provenance_refs,
                task_target=row.tool_name,
                prior_score=prior_score,
            ).validate()
        )

    return facets, values


# ---------------------------------------------------------------------------
# Snapshot build
# ---------------------------------------------------------------------------


def build_a2t_knowledge_snapshot(
    spec: A2tKnowledgeBuildSpec,
    *,
    rows: Sequence[A2tKbRow],
    registry: Mapping[str, Mapping[str, str]],
    forbidden_sample_ids: frozenset[str],
    governed_relpath_by_tier: Mapping[str, str] | None = None,
) -> KnowledgeSnapshot:
    """Build one standalone, model-free construction-pool
    :class:`KnowledgeSnapshot` for Audio2Tool.

    ``rows`` must already be the CONSTRUCTION pool (the caller partitions;
    see :func:`propose_partition`). ``forbidden_sample_ids`` must carry the
    whole exposure union AND whatever proposed evaluation tier the caller
    drew (empty since the tier was retired on 2026-09-05, which is why the
    union alone must be non-empty for this build to be legal) -- the check is
    fail-closed and belt-and-braces: the partition already guarantees
    disjointness, and this re-proves it against the snapshot that is actually
    emitted.
    """

    spec.validate()
    rows = tuple(rows)
    if not rows:
        raise RailsError("build_a2t_knowledge_snapshot: zero construction rows")
    if not forbidden_sample_ids:
        raise RailsError(
            "build_a2t_knowledge_snapshot: refusing to build with an EMPTY "
            "decontamination roster (fail-closed)"
        )

    selected = distribution_sample_a2t(rows, spec.datastore_size, spec.seed)
    selected_sample_ids = {sid for row in selected for sid in row.sample_ids}
    contaminated = selected_sample_ids & set(forbidden_sample_ids)
    if contaminated:
        preview = sorted(contaminated)[:5]
        raise RailsError(
            "KB-BUILD-A2T selection intersects the frozen exposed-400 / proposed-eval "
            f"decontamination roster: {preview}"
            + (f" (+{len(contaminated) - 5} more)" if len(contaminated) > 5 else "")
        )

    facets, values = _build_facets_and_values(
        selected,
        rows,
        spec,
        registry,
        governed_relpath_by_tier=dict(governed_relpath_by_tier or {}),
    )
    # The prior-score range contract, construction side (see
    # ``knowledge.assert_prior_scores_are_probabilities``): a builder that
    # emits a non-probability has computed the wrong quantity, so it is
    # refused here, at the earliest point the values exist, rather than
    # later at freeze time.
    assert_prior_scores_are_probabilities(values, builder="KB-BUILD-A2T")

    source_sample_ids = tuple(sorted(selected_sample_ids))
    source_split_identity_hash = hashlib.sha256(
        "\n".join(source_sample_ids).encode("utf-8")
    ).hexdigest()
    build_descriptor = {
        "schema": "saea-kb-a2t-toolshaped-build-v1",
        "carrier_lock_key": spec.carrier_lock_key,
        "datastore_size": spec.datastore_size,
        "seed": spec.seed,
        "dimensions": list(spec.dimensions),
        "source_split_identity_hash": source_split_identity_hash,
        "unit_count": len(selected),
    }
    build_sha256 = content_hash(build_descriptor)
    return KnowledgeSnapshot(
        snapshot_id=f"a2t-kb-toolshaped-{build_sha256[:16]}",
        source_split_identity_hash=source_split_identity_hash,
        source_sample_ids=source_sample_ids,
        builder_policy_id=A2T_KB_BUILD_POLICY_ID,
        facets=tuple(facets),
        values=tuple(values),
    ).validate()


def build_a2t_knowledge_snapshot_from_lock(
    spec: A2tKnowledgeBuildSpec,
    *,
    lock: Mapping[str, object],
    root: Path,
    repo_root: Path | None = None,
) -> KnowledgeSnapshot:
    """The registered ``KNOWLEDGE_BUILDERS`` entry point for Audio2Tool.

    :func:`build_a2t_knowledge_snapshot` takes an ALREADY partitioned
    construction pool, because the partition is a governance decision the
    caller must make explicitly. A registry entry, however, must be callable
    from a carrier-agnostic seam that knows only the composed config, so this
    thin wrapper performs the three steps ``scripts/build_a2t_knowledge_
    snapshot.py`` already performs in exactly the same order, and adds
    nothing of its own:

    1. :func:`a2t_pool_rows` -- every ``(tier, query_idx)`` unit of the full
       carrier pool, from the governed manifests under ``root``;
    2. :func:`propose_partition` against :func:`exposed_sample_ids`
       (``repo_root``'s committed evaluation identities) at the DEFAULT
       ``eval_per_tier=0`` -- the proposed evaluation tier is retired, so
       the construction pool is every block the exposure union does not
       hold;
    3. :func:`build_a2t_knowledge_snapshot` with the forbidden roster set to
       the exposure union PLUS the proposed evaluation tier (empty under the
       default), which is the belt-and-braces decontamination roster that
       function requires.

    The governed source relpath of every tier present in the construction
    pool is threaded through, exactly as the script does, so the emitted
    facets name the file their text came from.
    """

    spec.validate()
    rows, _inventory = a2t_pool_rows(lock, root)
    exposed = exposed_sample_ids(repo_root)
    partition = propose_partition(rows, exposed)
    registry = load_tool_registry_by_name(lock, root)
    return build_a2t_knowledge_snapshot(
        spec,
        rows=partition.construction,
        registry=registry,
        forbidden_sample_ids=frozenset(exposed) | frozenset(partition.eval_sample_ids),
        governed_relpath_by_tier={
            tier: f"datasets/audio2tool/public/{tier}_data/{tier}.json"
            for tier in {row.tier for row in partition.construction}
        },
    )


# ---------------------------------------------------------------------------
# Coverage report
# ---------------------------------------------------------------------------


def _selected_rows_from_snapshot(
    snapshot: KnowledgeSnapshot, rows: Sequence[A2tKbRow]
) -> tuple[A2tKbRow, ...]:
    rows_by_sample_id = {sid: row for row in rows for sid in row.sample_ids}
    seen: set[str] = set()
    selected: list[A2tKbRow] = []
    for sample_id in snapshot.source_sample_ids:
        row = rows_by_sample_id.get(sample_id)
        if row is None:
            raise RailsError(
                f"snapshot sample id {sample_id!r} not found in the provided construction rows"
            )
        if row.unit_id not in seen:
            seen.add(row.unit_id)
            selected.append(row)
    return tuple(sorted(selected, key=lambda row: row.unit_id))


def coverage_report_a2t(
    snapshot: KnowledgeSnapshot,
    rows: Sequence[A2tKbRow],
    *,
    registry_tool_count: int | None = None,
) -> dict[str, object]:
    """Coverage/diversity statistics for a built A2T snapshot, measured
    against the FULL construction population ``rows``."""

    rows = tuple(rows)
    selected = _selected_rows_from_snapshot(snapshot, rows)

    pool_tools: Counter[str] = Counter(row.tool_name for row in rows)
    sel_tools: Counter[str] = Counter(row.tool_name for row in selected)
    pool_families: Counter[tuple[str, tuple[str, ...]]] = Counter(
        row.family_key for row in rows
    )
    sel_families: Counter[tuple[str, tuple[str, ...]]] = Counter(
        row.family_key for row in selected
    )
    pool_tiers: Counter[str] = Counter(row.tier for row in rows)
    sel_tiers: Counter[str] = Counter(row.tier for row in selected)
    pool_categories: Counter[tuple[str, str]] = Counter(
        (row.domain, row.category) for row in rows
    )
    sel_categories: Counter[tuple[str, str]] = Counter(
        (row.domain, row.category) for row in selected
    )
    pool_keys: Counter[str] = Counter()
    for row in rows:
        pool_keys.update(set(row.arg_signature))
    sel_keys: Counter[str] = Counter()
    for row in selected:
        sel_keys.update(set(row.arg_signature))

    def _coverage(pool: Mapping[object, int], chosen: Mapping[object, int]) -> float:
        if not pool:
            return 1.0
        return sum(1 for key in pool if chosen.get(key, 0) > 0) / len(pool)

    def _kl(pool: Mapping[object, int], chosen: Mapping[object, int]) -> float:
        total_pool = sum(pool.values())
        total_sel = sum(chosen.values())
        value = 0.0
        for key, count in chosen.items():
            p = count / total_sel
            q = pool.get(key, 0) / total_pool
            if q <= 0:
                raise RailsError(f"selected stratum {key!r} absent from the construction pool")
            if p > 0:
                value += p * math.log(p / q)
        return value

    long_tail_tools = {tool for tool, n in pool_tools.items() if n < _LONG_TAIL_THRESHOLD}
    long_tail_families = {
        family for family, n in pool_families.items() if n < _LONG_TAIL_THRESHOLD
    }
    covered_long_tail_tools = sum(1 for tool in long_tail_tools if sel_tools.get(tool, 0) > 0)
    covered_long_tail_families = sum(
        1 for family in long_tail_families if sel_families.get(family, 0) > 0
    )

    pool_shingles: set[str] = set()
    for row in rows:
        pool_shingles |= _shingles(row.text)
    sel_shingles: set[str] = set()
    for row in selected:
        sel_shingles |= _shingles(row.text)

    call_counts = Counter(row.call_count for row in selected)
    multi_call = sum(count for calls, count in call_counts.items() if calls > 1)

    return {
        "datastore_size_actual": len(selected),
        "tool_coverage": _coverage(pool_tools, sel_tools),
        "argument_pattern_family_coverage": _coverage(pool_families, sel_families),
        "argument_key_coverage": _coverage(pool_keys, sel_keys),
        "tier_coverage": _coverage(pool_tiers, sel_tiers),
        "category_coverage": _coverage(pool_categories, sel_categories),
        "long_tail_coverage": {
            "tool": {
                "pool_long_tail_count": len(long_tail_tools),
                "covered_count": covered_long_tail_tools,
                "coverage": (
                    covered_long_tail_tools / len(long_tail_tools) if long_tail_tools else 1.0
                ),
                "threshold": _LONG_TAIL_THRESHOLD,
            },
            "argument_pattern_family": {
                "pool_long_tail_count": len(long_tail_families),
                "covered_count": covered_long_tail_families,
                "coverage": (
                    covered_long_tail_families / len(long_tail_families)
                    if long_tail_families
                    else 1.0
                ),
                "threshold": _LONG_TAIL_THRESHOLD,
            },
        },
        "cluster_coverage_proxy": (
            len(sel_shingles) / len(pool_shingles) if pool_shingles else 1.0
        ),
        "kl_selected_given_pool_over_tool": _kl(pool_tools, sel_tools),
        "kl_selected_given_pool_over_tier": _kl(pool_tiers, sel_tiers),
        "counts": {
            "pool_units": len(rows),
            "selected_units": len(selected),
            "pool_tools": len(pool_tools),
            "selected_tools": len(sel_tools),
            "registry_tools": registry_tool_count,
            "pool_argument_pattern_families": len(pool_families),
            "selected_argument_pattern_families": len(sel_families),
            "pool_argument_keys": len(pool_keys),
            "selected_argument_keys": len(sel_keys),
            "selected_multi_call_units": multi_call,
        },
        "selected_units_by_tier": dict(sorted(sel_tiers.items())),
        "tool_histogram_summary": {
            "distinct_tools": len(sel_tools),
            "max_tool_share": (max(sel_tools.values()) / len(selected)) if selected else 0.0,
            "min_tool_count": min(sel_tools.values()) if sel_tools else 0,
            "top_tools": [
                {"tool_name": tool, "count": count}
                for tool, count in sorted(sel_tools.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
            ],
        },
    }


__all__ = [
    "A2T_CONSTRUCTION_SELECTION_SCHEMA",
    "A2T_KB_BUILD_POLICY_ID",
    "A2T_PAIRED_ROSTER_COMPARATOR_ROWS_SCHEMA",
    "A2T_PARTITION_POLICY_ID",
    "CONSTRUCTION_ROSTER_ROLE",
    "EVALUATION_ROSTER_ROLE",
    "EVAL_TOOL_MIN_POOL_ROWS",
    "EXPOSED_RECEIPT_RELPATH",
    "EXPOSURE_UNION_POLICY_ID",
    "ROSTER_RECEIPTS_RELDIR",
    "TIERS",
    "A2tKbRow",
    "A2tKnowledgeBuildSpec",
    "PartitionProposal",
    "a2t_metadata_inventory",
    "a2t_pool_rows",
    "build_a2t_knowledge_snapshot",
    "build_a2t_knowledge_snapshot_from_lock",
    "coverage_report_a2t",
    "distribution_sample_a2t",
    "exposed_identity_report",
    "exposed_sample_ids",
    "load_tool_registry_by_name",
    "propose_partition",
    "render_call",
]
