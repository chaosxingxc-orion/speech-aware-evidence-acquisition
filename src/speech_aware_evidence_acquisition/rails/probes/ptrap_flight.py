"""P-TRAP flight orchestration -- REGISTERED probe SAEA-PROBE-ptrap-120
(``bounded-discovery-probe``): ``docs/readiness/2026-08-19-ptrap-preregistration-
REGISTERED.md``.

Question: is supply-use matching **acoustically mediated**? If the core
matches roster entries against its acoustic percept, an entry equal to its
OWN earlier mishearing of THIS audio should capture its output at a higher
rate than an equally wrong entry with no acoustic relation to this audio.
Two arms over the SAME frozen 60 SLURP devel samples the consumed P-SLU/
P-KEY probes already used (``configs/probes/g0-binding/pslu-sample-devel-
n60.json``, ``split_identity_hash`` ``fc9de436eba5aba120ecf07ee112765cd4ac06
09150e0aaf36f4d44c9c5b5ee5`` -- :func:`assert_split_identity_hash` pins this
VERBATIM):

- **V1** (self-percept trap): the A3-form 100-entry legal roster
  (``rails.probes.pslu_flight.pslu_supply_packet("A3", scenario=None,
  rosters=...).items`` -- reused unmodified) PLUS K<=5 appended entries,
  each one of THIS sample's own A0 zero-supply wrong emitted value (model
  text, the CONSUMED P-SLU attempt, deployment-legal).
- **V2** (cross-percept control): IDENTICAL construction, but the K
  appended entries are seeded-drawn from OTHER samples' own A0 wrong
  values (fixed-point-free at sample level, length-matched to V1's own K
  for that SAME sample) -- same source distribution, no acoustic relation
  to this audio.

Trap content is NEVER gold-derived (hard rule, preregistration section 2):
every appended entry is the core's OWN model-generated text from the
consumed A0 attempt. This module never reads that consumed attempt's
outputs itself -- that is :func:`analysis.ptrap_read.harvest_a0_wrong_values`'s
job (an ANALYSIS-layer reader, mirroring how ``rails.probes.pkey_flight``
never reads an attempt directory either; the module-boundary convention
this repository already keeps is that ``rails.probes`` modules are pure
orchestrators over ALREADY-BUILT domain objects, never file-I/O readers of
another attempt's archived output). This module's own job starts one step
later: given an ALREADY-HARVESTED, per-sample pool of
:class:`HarvestedWrongValue` (whatever ``harvest_a0_wrong_values`` yielded),
:func:`build_trap_sets` performs the K-cap, the BINDING-TIME FAIL-CLOSED
gold zero-overlap check (preregistration section 2: "no appended entry
equals (post-normalization) any gold slot value of its target sample"), and
the seeded V2 cross-sample draw -- entirely offline, pure functions, unit-
testable against small synthetic :class:`~speech_aware_evidence_acquisition
.reproduction.slurp_scoring.SlotEntity` fixtures, exactly like
``rails.probes.pslu_flight.pslu_supply_packet`` is. :func:`run_ptrap_flight`
then consumes an ALREADY-BUILT ``trap_sets`` table (never re-derives it) and
issues exactly 120 requests (60 samples x 2 arms), reusing
``rails.adapters.slurp.SlurpAdapter.assemble_prompt``/``score``/
``extract_consumption`` verbatim -- the SAME primitives every other rails
probe in this family composes on top of.

ENGINEERING-INTERPRETATION NOTES (flagged here, not buried, matching this
probe family's own established discipline -- e.g. ``analysis.pslu_read``
module docstring's numbered notes -- each is a documented, reviewable
choice, not a silent guess):

1. "A0 wrong emitted value" (preregistration section 2) is read as one A0
   predicted entity ``(type, filler)`` that does NOT exact-match any gold
   entity of that SAME sample -- the IDENTICAL false-positive convention
   ``reproduction.slurp_scoring._exact_counts`` already uses to compute the
   official ``slot_f1_exact`` false-positive count, never a second,
   drifting "wrongness" definition. Harvested per sample, deduplicated by
   normalized ``(type, filler)``, order-preserving (first-emitted kept).
   Lives in :mod:`analysis.ptrap_read` (the harvester itself, since it
   requires attempt-dir I/O); this module only consumes its output.
2. "no appended entry equals (post-normalization) any gold slot value of
   its target sample" (preregistration section 2's binding-time check) is
   read as: the candidate's normalized filler must not equal the
   normalized filler of ANY gold entity of the TARGET sample, regardless
   of entity TYPE -- a wrong-typed A0 emission can still leak a real value
   from a DIFFERENT gold slot of the SAME sample (e.g. A0 wrongly emits
   ``date=chao`` when ``chao`` is actually this sample's own
   ``person`` filler), and that leak is exactly what this check exists to
   catch. See :func:`_gold_filler_values`.
3. "fixed-point-free at sample level" (V2's own construction clause) is
   read as a STRUCTURAL guarantee, not a permutation label: V2's candidate
   pool for target sample S is built by excluding S's own harvested pool
   entirely (never merely "avoid S in a random derangement step") -- every
   drawn V2 entry's ``origin_sample_id`` is therefore PROVABLY != its
   target sample id, by construction, not by chance. This is simpler and
   more robust than a single-donor derangement (which would couple a
   target's own V2 length to one donor's own pool size); it is checked
   directly by :func:`validate_ptrap_flight_summary` and by
   ``tests/unit/test_ptrap_flight.py``.
4. "length-matched" (V2's own construction clause) is read as a TARGET,
   not an invariant the pool can always deliver: V2 draws exactly
   ``len(v1_entries)`` candidates when the (gold-zero-overlap-filtered,
   deduplicated) cross-sample pool has that many available, and FEWER
   otherwise (never padded/repeated to force equality) -- the actual
   per-sample V2 K is recorded on :class:`SampleTrapSet` and reported
   alongside V1's own K, never silently coerced to match.
5. K-cap selection, when a sample's own harvested pool exceeds 5, takes
   the FIRST 5 in the harvester's own emission order (deterministic,
   order-preserving) -- never a random subsample of the pool (V1's own
   identity as "the model's actual first K distinct wrong values" would
   otherwise be diluted by an extra, unregistered source of randomness).

Never calls the ceiling-tier ontology miner (``data.slurp.
load_slurp_ontology``): this module's own AST guard
(:func:`_assert_this_module_never_calls_ontology_miner`) reuses
``rails.probes.pslu_flight._source_references_ontology_miner`` verbatim,
checked at import time and again at the top of :func:`run_ptrap_flight` --
V1/V2's base 100-entry roster comes ONLY from ``configs/probes/g0-binding/
pslu-rosters-train-only.json`` via the SAME frozen
``rails.probes.pslu_flight.load_pslu_rosters``/``pslu_supply_packet``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from ...core.retrieval import normalize_term
from ...reproduction.slurp_scoring import SlotEntity
from ..adapters.slurp import SlurpAdapter, SlurpSample
from ..consumption import ConsumptionTrace
from ..supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket
from .pslu_flight import (
    _source_references_ontology_miner,
    assert_never_calls_ontology_miner,
    render_roster_entries,
)

V1_ARM = "V1"
V2_ARM = "V2"
PTRAP_ARMS: tuple[str, ...] = (V1_ARM, V2_ARM)

# Preregistration section 2: "K<=5 appended entries per sample".
TRAP_K_CAP = 5
# Preregistration's own opening line / this study's SAME fixed seed used
# throughout the probe family -- the V2 cross-sample draw's own determinism.
DEFAULT_TRAP_SEED = 20260807

# docs/readiness/2026-08-19-ptrap-preregistration-REGISTERED.md's own opening
# line: "the SAME frozen 60 SLURP devel samples (seed 20260807)" --
# configs/probes/g0-binding/pslu-sample-devel-n60.json's own
# split_identity_hash, pinned VERBATIM (IDENTICAL to the consumed P-SLU/P-KEY
# flights' own value).
EXPECTED_SPLIT_IDENTITY_HASH = "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"


class PTrapFlightError(RuntimeError):
    """A P-TRAP flight/binding input is malformed, a hard invariant (split
    identity, K-cap, fixed-point-freeness, the gold zero-overlap check) is
    violated, or the ontology-miner import guard tripped."""


# ---------------------------------------------------------------------------
# The ontology-miner call guard -- reuses the parent's own pure checker
# against THIS module's own source (mirrors rails.probes.pkey_flight's own
# dual parent+self check).
# ---------------------------------------------------------------------------


def _assert_this_module_never_calls_ontology_miner(source: str | None = None) -> None:
    from pathlib import Path

    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise PTrapFlightError(
            "rails.probes.ptrap_flight source references load_slurp_ontology; this flight is "
            "REGISTERED to consume its base roster ONLY from configs/probes/g0-binding/"
            "pslu-rosters-train-only.json (rails.probes.pslu_flight.load_pslu_rosters)"
        )


def assert_split_identity_hash(split_identity_hash: str) -> None:
    """Fail-closed (module docstring): ``split_identity_hash`` must equal
    :data:`EXPECTED_SPLIT_IDENTITY_HASH` VERBATIM -- this probe reuses the
    SAME frozen 60-sample manifest the consumed P-SLU/P-KEY flights used,
    never a fresh draw."""

    if split_identity_hash != EXPECTED_SPLIT_IDENTITY_HASH:
        raise PTrapFlightError(
            f"split_identity_hash {split_identity_hash!r} does not match the REGISTERED P-TRAP "
            f"sample manifest's own hash {EXPECTED_SPLIT_IDENTITY_HASH!r} "
            "(configs/probes/g0-binding/pslu-sample-devel-n60.json, reused byte-identically for "
            "this probe) -- fail-closed"
        )


# ---------------------------------------------------------------------------
# Harvested-value / trap-entry shapes (analysis.ptrap_read.harvest_a0_wrong_
# values produces the FIRST of these; this module produces the rest).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HarvestedWrongValue:
    """One A0 predicted entity this study's harvester classified as WRONG
    (module docstring note 1) -- ``sample_id`` is the ORIGIN sample: whose
    own A0 response actually emitted ``filler`` for ``entity_type``. Model
    text, verbatim, never normalized/altered (the trap must still be one of
    THIS sample's -- or, for V2, one of ANOTHER sample's -- own actual
    emitted words)."""

    sample_id: str
    entity_type: str
    filler: str


@dataclass(frozen=True)
class TrapEntry:
    """One appended roster line actually rendered into a V1/V2 prompt --
    ``origin_sample_id`` equals the TARGET sample id on a V1 entry (by
    construction: V1 only ever appends a sample's own harvested pool) and
    a DIFFERENT sample id on every V2 entry (module docstring note 3)."""

    entity_type: str
    filler: str
    origin_sample_id: str

    def as_roster_pair(self) -> tuple[str, str]:
        return (self.entity_type, self.filler)

    def as_json(self) -> dict[str, object]:
        return {"type": self.entity_type, "filler": self.filler, "origin_sample_id": self.origin_sample_id}

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "TrapEntry":
        return cls(
            entity_type=str(document["type"]),
            filler=str(document["filler"]),
            origin_sample_id=str(document["origin_sample_id"]),
        )


@dataclass(frozen=True)
class SampleTrapSet:
    """One sample's fully-resolved V1/V2 trap construction -- the binding-
    time output ``run_ptrap_flight`` consumes without ever re-deriving it.
    ``*_excluded_gold_overlap`` are diagnostics: candidates the fail-closed
    zero-overlap check (module docstring note 2) actually dropped, kept for
    audit even though they never reach a prompt."""

    sample_id: str
    v1_entries: tuple[TrapEntry, ...]
    v2_entries: tuple[TrapEntry, ...]
    v1_excluded_gold_overlap: tuple[TrapEntry, ...]
    v2_excluded_gold_overlap: tuple[TrapEntry, ...]
    own_pool_size: int  # size of this sample's own harvested pool, pre-cap/pre-filter (diagnostic)

    @property
    def v1_k(self) -> int:
        return len(self.v1_entries)

    @property
    def v2_k(self) -> int:
        return len(self.v2_entries)


def _gold_filler_values(gold_entities: Sequence[SlotEntity]) -> frozenset[str]:
    """Module docstring note 2: every gold entity's normalized filler,
    across ALL types -- the zero-overlap check's own comparison set."""

    return frozenset(normalize_term(entity.filler) for entity in gold_entities)


def build_trap_sets(
    *,
    wrong_values_by_sample: Mapping[str, Sequence[HarvestedWrongValue]],
    gold_entities_by_sample_id: Mapping[str, Sequence[SlotEntity]],
    sample_ids: Sequence[str],
    k_cap: int = TRAP_K_CAP,
    seed: int = DEFAULT_TRAP_SEED,
) -> dict[str, SampleTrapSet]:
    """Offline, pure (no I/O, no model contact): the K-cap, the BINDING-TIME
    FAIL-CLOSED gold zero-overlap check, and the seeded V2 cross-sample draw
    (module docstring notes 2-5). ``wrong_values_by_sample`` is whatever
    ``analysis.ptrap_read.harvest_a0_wrong_values`` yielded (or a synthetic
    fixture in a test); a sample absent from it, or present with an empty
    tuple, is a legitimate K=0 shape (preregistration section 2: "Samples
    with zero usable A0 wrong values fly with K=0"), never an error.

    Determinism (module docstring note 3-4): a SINGLE ``random.Random(seed)``
    instance is walked across every sample IN SORTED ``sample_id`` ORDER, so
    the whole table is reproducible end-to-end from ``seed`` alone -- never
    per-sample reseeded (which would make each sample's own draw independent
    of every other sample having been processed, silently changing the
    output the moment a caller reorders ``sample_ids``)."""

    ids = tuple(sample_ids)
    if len(ids) != len(set(ids)):
        raise PTrapFlightError("build_trap_sets: sample_ids carries a duplicate")
    missing_gold = [sid for sid in ids if sid not in gold_entities_by_sample_id]
    if missing_gold:
        raise PTrapFlightError(
            f"build_trap_sets: no gold entities supplied for {len(missing_gold)} sample id(s): "
            f"{missing_gold[:5]}{'...' if len(missing_gold) > 5 else ''}"
        )

    gold_values_by_sample = {sid: _gold_filler_values(gold_entities_by_sample_id[sid]) for sid in ids}

    # --- V1: this sample's own pool, K-capped, gold-zero-overlap-filtered. ---
    v1_by_sample: dict[str, tuple[tuple[TrapEntry, ...], tuple[TrapEntry, ...], int]] = {}
    for sid in ids:
        own_pool = tuple(wrong_values_by_sample.get(sid, ()))
        gold_values = gold_values_by_sample[sid]
        kept: list[TrapEntry] = []
        excluded: list[TrapEntry] = []
        for value in own_pool:
            entry = TrapEntry(entity_type=value.entity_type, filler=value.filler, origin_sample_id=value.sample_id)
            if normalize_term(value.filler) in gold_values:
                excluded.append(entry)
            else:
                kept.append(entry)
        v1_by_sample[sid] = (tuple(kept[:k_cap]), tuple(excluded), len(own_pool))

    # --- V2: seeded cross-sample draw, fixed-point-free by pool exclusion. ---
    rng = random.Random(seed)
    result: dict[str, SampleTrapSet] = {}
    for sid in sorted(ids):
        v1_entries, v1_excluded, own_pool_size = v1_by_sample[sid]
        k_target = len(v1_entries)
        gold_values = gold_values_by_sample[sid]

        candidates: list[TrapEntry] = []
        v2_excluded: list[TrapEntry] = []
        seen_keys: set[tuple[str, str]] = set()
        for other_sid in sorted(wrong_values_by_sample.keys()):
            if other_sid == sid or other_sid not in set(ids):
                continue
            for value in wrong_values_by_sample[other_sid]:
                entry = TrapEntry(
                    entity_type=value.entity_type, filler=value.filler, origin_sample_id=value.sample_id
                )
                if normalize_term(value.filler) in gold_values:
                    v2_excluded.append(entry)
                    continue
                key = (value.entity_type, normalize_term(value.filler))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                candidates.append(entry)

        if k_target > 0 and candidates:
            draw_count = min(k_target, len(candidates))
            drawn_indices = sorted(rng.sample(range(len(candidates)), draw_count))
            v2_entries = tuple(candidates[i] for i in drawn_indices)
        else:
            v2_entries = ()

        for entry in v2_entries:
            if entry.origin_sample_id == sid:
                raise PTrapFlightError(
                    f"build_trap_sets: V2 fixed-point violation on target sample {sid!r} -- a drawn "
                    "entry's own origin_sample_id equals its target (should be structurally "
                    "impossible; the candidate pool excludes the target's own samples by "
                    "construction)"
                )

        result[sid] = SampleTrapSet(
            sample_id=sid,
            v1_entries=v1_entries,
            v2_entries=v2_entries,
            v1_excluded_gold_overlap=v1_excluded,
            v2_excluded_gold_overlap=tuple(v2_excluded),
            own_pool_size=own_pool_size,
        )
    return result


# ---------------------------------------------------------------------------
# Roster rendering: A3's own 100 entries + the appended trap entries.
# ---------------------------------------------------------------------------


def _trap_roster_packet(
    arm: str, sample_id: str, base_entries: Sequence[tuple[str, str]], trap_entries: Sequence[TrapEntry]
) -> SupplyPacket:
    entries: tuple[tuple[str, str], ...] = tuple(base_entries) + tuple(e.as_roster_pair() for e in trap_entries)
    prompt_block = render_roster_entries(entries)
    items = tuple(
        SupplyItem(item_id=f"{arm}-{sample_id}-{index:03d}", text=f"{entry_type}={value}")
        for index, (entry_type, value) in enumerate(entries)
    )
    return SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=len(entries), token_count=len(prompt_block.split())),
        prompt_block=prompt_block,
        assembly_template_id=f"ptrap-{arm}-roster-v1",
        items=items,
    ).validate()


# ---------------------------------------------------------------------------
# Flight orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PTrapArmResult:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace
    k: int
    # Embedded so the read suite's capture detector never needs to re-derive
    # the trap set live from build_trap_sets (harness-defect-resistant
    # design, mirrors rails.probes.pkey_flight.PKeyArmResult.transcript_
    # sha256_used carrying the ALREADY-COMPUTED hash rather than forcing a
    # recompute at read time).
    trap_entries: tuple[Mapping[str, object], ...]


@dataclass(frozen=True)
class PTrapFlightSummary:
    results: tuple[PTrapArmResult, ...]
    trap_sets: Mapping[str, SampleTrapSet]


def validate_ptrap_flight_summary(
    summary: PTrapFlightSummary,
    *,
    expected_sample_ids: Sequence[str],
    gold_entities_by_sample_id: Mapping[str, Sequence[SlotEntity]],
) -> None:
    """Fail-closed structural checks (module docstring): every arm in
    :data:`PTRAP_ARMS` carries EXACTLY one row per id in
    ``expected_sample_ids`` (60/60 per pass), no duplicate rows, each row's
    own ``k``/``trap_entries`` agree, V1's own K never exceeds
    :data:`TRAP_K_CAP`, V2's own K never exceeds that SAME sample's own V1
    K (the "length-matched, never padded beyond it" invariant), every V2
    row is fixed-point-free (no ``trap_entries`` entry's own
    ``origin_sample_id`` equals its row's own ``sample_id``), and -- THE
    binding-time fail-closed check preregistration section 2 mandates --
    no row's own trap entry filler (post-normalization) equals ANY gold
    slot value of that SAME row's own sample. Called automatically at the
    end of :func:`run_ptrap_flight`; independently callable against an
    already-assembled summary (e.g. by a test fixture)."""

    expected = tuple(expected_sample_ids)
    expected_set = set(expected)
    if len(expected) != len(expected_set):
        raise PTrapFlightError("expected_sample_ids carries a duplicate")

    by_arm: dict[str, list[PTrapArmResult]] = {arm: [] for arm in PTRAP_ARMS}
    for row in summary.results:
        if row.arm not in PTRAP_ARMS:
            raise PTrapFlightError(f"unknown P-TRAP arm {row.arm!r}")
        by_arm[row.arm].append(row)

    for arm in PTRAP_ARMS:
        rows = by_arm[arm]
        ids = [row.sample_id for row in rows]
        if len(ids) != len(set(ids)):
            raise PTrapFlightError(f"arm {arm}: duplicate sample_id row(s)")
        got = set(ids)
        if got != expected_set:
            missing = sorted(expected_set - got)
            extra = sorted(got - expected_set)
            raise PTrapFlightError(
                f"arm {arm}: sample id set does not match the expected {len(expected_set)}-sample "
                f"manifest (missing={missing[:5]}, extra={extra[:5]})"
            )

    v1_k_by_sample = {row.sample_id: row.k for row in by_arm[V1_ARM]}
    for row in summary.results:
        if row.k != len(row.trap_entries):
            raise PTrapFlightError(
                f"arm {row.arm} sample {row.sample_id!r}: k={row.k} disagrees with "
                f"len(trap_entries)={len(row.trap_entries)}"
            )
        if row.arm == V1_ARM and row.k > TRAP_K_CAP:
            raise PTrapFlightError(f"arm V1 sample {row.sample_id!r}: k={row.k} exceeds TRAP_K_CAP={TRAP_K_CAP}")
        if row.arm == V2_ARM:
            v1_k = v1_k_by_sample.get(row.sample_id)
            if v1_k is not None and row.k > v1_k:
                raise PTrapFlightError(
                    f"arm V2 sample {row.sample_id!r}: k={row.k} exceeds this SAME sample's own V1 "
                    f"k={v1_k} (length-matched invariant violated)"
                )
            for entry in row.trap_entries:
                if entry.get("origin_sample_id") == row.sample_id:
                    raise PTrapFlightError(
                        f"arm V2 sample {row.sample_id!r}: a trap entry's own origin_sample_id equals "
                        "its target sample id -- fixed-point-free invariant violated"
                    )
        gold_entities = gold_entities_by_sample_id.get(row.sample_id)
        if gold_entities is None:
            continue
        gold_values = _gold_filler_values(gold_entities)
        for entry in row.trap_entries:
            filler = str(entry.get("filler", ""))
            if normalize_term(filler) in gold_values:
                raise PTrapFlightError(
                    f"arm {row.arm} sample {row.sample_id!r}: appended trap entry {entry!r} equals "
                    "(post-normalization) a gold slot value of its OWN target sample -- binding-time "
                    "fail-closed zero-overlap check violated (preregistration section 2)"
                )


def run_ptrap_flight(
    *,
    adapter: SlurpAdapter,
    core_client,
    samples: Sequence[SlurpSample],
    base_roster_entries: Sequence[tuple[str, str]],
    trap_sets: Mapping[str, SampleTrapSet],
    split_identity_hash: str,
    decoding_params: Mapping[str, object] | None = None,
) -> PTrapFlightSummary:
    """Execute the full two-arm P-TRAP flight over ``samples`` (module
    docstring): exactly ``2 * len(samples)`` requests, V1 then V2 per
    sample. ``base_roster_entries`` is the SAME A3-form 100-entry roster the
    consumed P-SLU/P-KEY flights used (``rails.probes.pslu_flight.
    pslu_supply_packet("A3", scenario=None, rosters=...).items`` rendered
    back to ``(type, value)`` pairs by the caller, or simply
    ``rosters.full_roster`` -- this module never loads the roster table
    itself, mirroring how ``run_pkey_flight`` receives ``rosters:
    PsluRosters`` from ITS caller rather than loading it). ``trap_sets`` is
    the ALREADY-BUILT :func:`build_trap_sets` output -- never re-derived
    here.

    ``core_client`` is duck-typed against ``rails.core_client.CoreClient``
    (the SAME "no forced import" discipline every sibling flight in this
    package uses)."""

    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    assert_split_identity_hash(split_identity_hash)
    if not samples:
        raise PTrapFlightError("run_ptrap_flight requires at least one sample")
    sample_ids_list = [sample.sample_id for sample in samples]
    if len(sample_ids_list) != len(set(sample_ids_list)):
        raise PTrapFlightError("duplicate sample_id in samples")
    missing_trap_sets = [sid for sid in sample_ids_list if sid not in trap_sets]
    if missing_trap_sets:
        raise PTrapFlightError(
            f"trap_sets carries no SampleTrapSet for {len(missing_trap_sets)} sample id(s) this "
            f"flight's own samples name: {missing_trap_sets[:5]}"
        )

    base_entries = tuple(base_roster_entries)
    results: list[PTrapArmResult] = []
    for sample in samples:
        trap_set = trap_sets[sample.sample_id]
        for arm, entries in ((V1_ARM, trap_set.v1_entries), (V2_ARM, trap_set.v2_entries)):
            supply = _trap_roster_packet(arm, sample.sample_id, base_entries, entries)
            messages = adapter.assemble_prompt(sample, supply)
            response_text = core_client.complete(messages, decoding_params=decoding_params)
            metrics = adapter.score(sample, response_text)
            consumption = adapter.extract_consumption(sample, supply, response_text)
            results.append(
                PTrapArmResult(
                    arm=arm,
                    sample_id=sample.sample_id,
                    messages=tuple(messages),
                    response_text=response_text,
                    metrics=metrics,
                    consumption=consumption,
                    k=len(entries),
                    trap_entries=tuple(entry.as_json() for entry in entries),
                )
            )

    summary = PTrapFlightSummary(
        results=tuple(results), trap_sets=MappingProxyType(dict(trap_sets))
    )
    gold_entities_by_sample_id = {sample.sample_id: sample.entities for sample in samples}
    validate_ptrap_flight_summary(
        summary, expected_sample_ids=tuple(sample_ids_list), gold_entities_by_sample_id=gold_entities_by_sample_id
    )
    return summary


__all__ = [
    "DEFAULT_TRAP_SEED",
    "EXPECTED_SPLIT_IDENTITY_HASH",
    "PTRAP_ARMS",
    "TRAP_K_CAP",
    "V1_ARM",
    "V2_ARM",
    "HarvestedWrongValue",
    "PTrapArmResult",
    "PTrapFlightError",
    "PTrapFlightSummary",
    "SampleTrapSet",
    "TrapEntry",
    "assert_split_identity_hash",
    "build_trap_sets",
    "run_ptrap_flight",
    "validate_ptrap_flight_summary",
]


# Executed at import time (mirrors rails.probes.pslu_flight's own
# module-bottom self-check, and rails.probes.pkey_flight's own dual
# parent+self check): fails LOUD the moment this module is loaded if a
# future edit adds a live reference to the forbidden ontology miner.
assert_never_calls_ontology_miner()
_assert_this_module_never_calls_ontology_miner()
