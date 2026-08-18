"""P-SLU Stage-2 F1 format-matched filler control -- roster generator plus
the fail-closed binding check (Stage-2 follow-up probe SAEA-PROBE-pslu-s2-183,
``docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md`` section 1,
arm F1): "a 100-entry roster rendered byte-compatibly with A3's own
``"{type}={value}"`` item shape and prompt framing, but carrying SYNTHETIC
NON-ONTOLOGY filler -- type names and values drawn from a seeded generator
over a non-SLURP wordlist, machine-checked at binding for ZERO overlap with
(a) the 55 ontology type names, (b) every ontology value, (c) the 89 gold
slot values of the 60 samples."

Wordlist source (mission instruction: "construct a deterministic English
filler lexicon inside the repo ... NOT drawn from SLURP anywhere"): a
hand-authored, 300-word, deterministic English common-noun lexicon shipped
as ``configs/probes/g0-binding/pslu-s2-filler-lexicon.json`` -- deliberately
drawn from a technical/scientific/nature register (mineralogy, anatomy,
mechanics, architecture, taxonomy, mathematics, ...) rather than an
everyday-object register, because the REAL SLURP ontology's own values are
themselves largely everyday nouns (foods, drinks, apps, places, brands --
verified against the committed roster table: "banana"/"apple"/"beer"/"bar"/
"book"/"chicken" are ALL real A1/A3 roster values). :func:`load_filler_lexicon`
machine-checks the shipped file's own ``slurp_derived: false`` flag at load
time (the SAME "trust a load-time-checked field, never a bare claim"
discipline ``rails.probes.pslu_flight.load_pslu_rosters`` already applies to
``legality_tier``/``train_synthetic_refused``); :func:`check_f1_filler_binding`
below is the actual, executed, fail-closed proof -- run against the REAL
committed roster table and the REAL frozen 60-sample gold values in this
mission's own test suite (never merely assumed clean because the wordlist
was chosen carefully).

Gold isolation (mirrors how the existing legality checks handle gold-side
data, e.g. ``analysis.pslu_read.load_gold_by_sample_id``'s own
``RUNTIME_PROHIBITED_NOTE``): :func:`generate_f1_filler_roster` and
:func:`f1_filler_supply_packet` -- the two functions on this module's own
PROMPT path -- never read gold anywhere. :func:`_gold_slot_values` is the
ONLY function in this module that touches gold, and it is called ONLY from
:func:`check_f1_filler_binding`, itself a binding-time/scoring-side gate,
never invoked from ``rails.probes.pslu_s2_flight``'s own request-assembly
loop.

Byte-compatibility with A3 (mission instruction): :func:`f1_filler_supply_packet`
reuses ``rails.probes.pslu_flight._roster_packet`` UNCHANGED (arm="F1") --
the SAME "{type}={value}"-join/``SupplyItem``/``SupplyPacket`` construction
A3's own roster uses, never a second, drifting re-implementation.

ENGINEERING-INTERPRETATION NOTES:

1. "100-entry roster" (singular, not "one per sample") mirrors A3's own
   ``rosters.full_roster`` -- ONE fixed table generated once
   (:func:`generate_f1_filler_roster`) and reused byte-identically across
   all 60 F1 requests (``rails.probes.pslu_s2_flight.run_pslu_s2_flight``),
   never a fresh per-sample draw.
2. Disjoint type/value halves: the lexicon is deterministically shuffled
   once (``random.Random(f"{seed}:f1-filler")``) and split into a first
   half (100 words -> the ``type`` half of each pair) and a disjoint second
   half (100 words -> the ``value`` half) -- guarantees ``type != value`` on
   every one of the 100 entries without an explicit post-hoc check, and
   needs the lexicon to carry at least ``2 * n_entries`` distinct words
   (:data:`FILLER_LEXICON_MIN_WORDS`).
3. The binding check's overlap comparison applies to the FULL flat token
   set of each F1 entry (BOTH the type half and the value half), not only
   "type half vs types" / "value half vs values" separately -- a strictly
   STRONGER, safer reading of the mission's "(a)/(b)/(c)" wording: a
   filler word landing in the ontology's type-name space, its value space,
   or the gold value space is a leak regardless of which half of the pair
   it happened to land in this particular draw.
4. Normalization reuses ``core.retrieval.normalize_term`` (lowercase,
   punctuation-to-space, whitespace-collapse) for every side of the
   comparison -- the SAME normalization ``analysis.pslu_read.
   _roster_values_for_packet``/``count_induced_substitutions`` already
   apply to roster/gold filler text, so a case or punctuation difference
   alone can never hide a real overlap or manufacture a false one.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ...core.retrieval import normalize_term
from .pslu_flight import PsluRosters, _roster_packet

FILLER_LEXICON_SCHEMA = "pslu-s2-filler-lexicon-v1"
_PROBE_ID = "P-SLU-S2"
_WORD_RE = re.compile(r"^[a-z]+$")

F1_FILLER_SEED = 20260807
F1_ROSTER_SIZE = 100
FILLER_LEXICON_MIN_WORDS = 2 * F1_ROSTER_SIZE  # disjoint type/value halves (note 2)


class PsluS2FillerError(RuntimeError):
    """The shipped filler-lexicon file fails its own load-time legality
    checks, or a caller asked :func:`generate_f1_filler_roster` for more
    entries than the lexicon can supply disjoint type/value halves for."""


class FillerBindingError(RuntimeError):
    """:func:`check_f1_filler_binding` found a non-empty overlap between the
    F1 filler roster and the ontology type names / ontology values / gold
    slot values it was checked against -- fail-closed, never a warning."""


# ---------------------------------------------------------------------------
# Lexicon loading (data file: configs/probes/g0-binding/pslu-s2-filler-lexicon.json)
# ---------------------------------------------------------------------------


def load_filler_lexicon(path: Path) -> tuple[str, ...]:
    """Load + validate the shipped filler-lexicon data file: ``probe`` and
    ``lexicon_version`` must match, ``slurp_derived`` must be the literal
    ``false`` (module docstring's own load-time-checked-field discipline),
    every word must be a lowercase-alphabetic token, no duplicates, and at
    least :data:`FILLER_LEXICON_MIN_WORDS` words total."""

    path = Path(path)
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("probe") != _PROBE_ID:
        raise PsluS2FillerError(f"{path}: probe must be {_PROBE_ID!r}, got {document.get('probe')!r}")
    if document.get("lexicon_version") != FILLER_LEXICON_SCHEMA:
        raise PsluS2FillerError(
            f"{path}: lexicon_version must be {FILLER_LEXICON_SCHEMA!r}, got {document.get('lexicon_version')!r}"
        )
    if document.get("slurp_derived") is not False:
        raise PsluS2FillerError(f"{path}: slurp_derived must be the literal false")
    words = document.get("words")
    if not isinstance(words, list) or not words:
        raise PsluS2FillerError(f"{path}: no words")
    if len(words) < FILLER_LEXICON_MIN_WORDS:
        raise PsluS2FillerError(
            f"{path}: needs at least {FILLER_LEXICON_MIN_WORDS} words to draw "
            f"{F1_ROSTER_SIZE} disjoint type/value halves, got {len(words)}"
        )
    seen: set[str] = set()
    for word in words:
        if not isinstance(word, str) or not _WORD_RE.match(word):
            raise PsluS2FillerError(f"{path}: word {word!r} is not a lowercase-alphabetic token")
        if word in seen:
            raise PsluS2FillerError(f"{path}: duplicate word {word!r}")
        seen.add(word)
    return tuple(words)


# ---------------------------------------------------------------------------
# Deterministic roster generation + A3-byte-compatible rendering.
# ---------------------------------------------------------------------------


def generate_f1_filler_roster(
    lexicon: Sequence[str], *, seed: int = F1_FILLER_SEED, n_entries: int = F1_ROSTER_SIZE
) -> tuple[tuple[str, str], ...]:
    """Deterministic (module docstring note 2): shuffle ``lexicon`` once
    under ``random.Random(f"{seed}:f1-filler")`` (the SAME
    ``f"{seed}:<purpose>"`` seeding-string discipline the parent flight's
    own silence-swap block uses,
    ``configs/probes/g0-binding/pslu-flight.json``'s
    ``"f'{seed}:silence-swap'"``) and split into two disjoint ``n_entries``-
    word halves -- the first half renders as every entry's ``type``, the
    second as its ``value``. Pure and gold-free: never reads any file, never
    imports ``normalize_term``/gold-scoring code."""

    import random

    if isinstance(n_entries, bool) or not isinstance(n_entries, int) or n_entries <= 0:
        raise PsluS2FillerError(f"n_entries must be a positive integer, got {n_entries!r}")
    words = list(lexicon)
    if len(words) < 2 * n_entries:
        raise PsluS2FillerError(
            f"lexicon has {len(words)} word(s), need at least {2 * n_entries} for "
            f"{n_entries} disjoint type/value pairs"
        )
    rng = random.Random(f"{seed}:f1-filler")
    rng.shuffle(words)
    types = words[:n_entries]
    values = words[n_entries : 2 * n_entries]
    return tuple(zip(types, values))


def f1_filler_supply_packet(entries: Sequence[tuple[str, str]]):
    """Byte-compatible with A3 (module docstring): reuses
    ``rails.probes.pslu_flight._roster_packet`` UNCHANGED, arm="F1" --
    ``"; ".join(f"{type}={value}")`` rendering, ``SupplyItem`` ids
    ``F1-000``.. ``F1-099``, ``assembly_template_id ==
    "pslu-F1-roster-v1"``."""

    return _roster_packet("F1", entries)


# ---------------------------------------------------------------------------
# Fail-closed binding check (module docstring notes 3-4).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FillerBindingReport:
    entries_checked: int
    overlap_with_ontology_types: tuple[str, ...]
    overlap_with_ontology_values: tuple[str, ...]
    overlap_with_gold_values: tuple[str, ...]

    @property
    def clean(self) -> bool:
        return not (
            self.overlap_with_ontology_types
            or self.overlap_with_ontology_values
            or self.overlap_with_gold_values
        )


def _filler_binding_report(
    entries: Sequence[tuple[str, str]],
    *,
    ontology_types: Iterable[str],
    ontology_values: Iterable[str],
    gold_values: Iterable[str],
) -> FillerBindingReport:
    """Pure (no I/O, no gold-loading) -- mirrors the
    ``_source_references_ontology_miner`` / ``assert_never_calls_ontology_miner``
    split in ``rails.probes.pslu_flight``: a pure, directly-testable
    computation here, a fail-closed I/O-performing wrapper
    (:func:`check_f1_filler_binding`) below."""

    tokens = {normalize_term(text) for pair in entries for text in pair}
    types_set = {normalize_term(t) for t in ontology_types}
    values_set = {normalize_term(v) for v in ontology_values}
    gold_set = {normalize_term(v) for v in gold_values}
    return FillerBindingReport(
        entries_checked=len(entries),
        overlap_with_ontology_types=tuple(sorted(tokens & types_set)),
        overlap_with_ontology_values=tuple(sorted(tokens & values_set)),
        overlap_with_gold_values=tuple(sorted(tokens & gold_set)),
    )


def _ontology_values(rosters: PsluRosters) -> tuple[str, ...]:
    """Every value the frozen roster table carries anywhere -- the union of
    every A1 scenario roster's own values and A3's dose-capped roster's own
    values (the only two value-bearing sections ``PsluRosters`` exposes;
    A2/A4 carry no values of their own -- A2 is bare types, A4 reuses A1's
    per-scenario value rosters under a deranged key)."""

    values: set[str] = set()
    for entries in rosters.scenario_rosters.values():
        for _entry_type, value in entries:
            values.add(value)
    for _entry_type, value in rosters.full_roster:
        values.add(value)
    return tuple(sorted(values))


def _gold_slot_values(lock: Mapping[str, object], root: Path, sample_ids: Sequence[str]) -> tuple[str, ...]:
    """RUNTIME_PROHIBITED (module docstring): the ONLY function in the F1
    filler machinery that reads a gold slot filler -- called ONLY from
    :func:`check_f1_filler_binding`. Deliberately re-derives the same tiny
    devel-split-by-id load ``analysis.pslu_read.load_gold_by_sample_id``
    performs, rather than importing that analysis-layer function, so this
    rails-layer module's only gold dependency stays the single, already-
    audited ``data.slurp`` loader."""

    from ...data.slurp import load_slurp_split

    records = load_slurp_split(lock, root, "devel")
    by_id = {record.sample_id: record for record in records}
    missing = [sample_id for sample_id in sample_ids if sample_id not in by_id]
    if missing:
        raise FillerBindingError(
            f"gold devel metadata missing {len(missing)} sample id(s) the manifest names: "
            f"{missing[:5]}{'...' if len(missing) > 5 else ''}"
        )
    values: set[str] = set()
    for sample_id in sample_ids:
        for entity in by_id[sample_id].entities:
            values.add(entity.filler)
    return tuple(sorted(values))


def check_f1_filler_binding(
    entries: Sequence[tuple[str, str]],
    *,
    rosters: PsluRosters,
    lock: Mapping[str, object],
    root: Path,
    sample_ids: Sequence[str],
) -> FillerBindingReport:
    """The fail-closed binding check (mission instruction): raises
    :class:`FillerBindingError` if ``entries`` overlaps the 55 ontology type
    names, any ontology value, or any gold slot value of ``sample_ids`` --
    returns the (necessarily clean) :class:`FillerBindingReport` otherwise.
    The ONLY caller of :func:`_gold_slot_values` anywhere in this module."""

    ontology_types = rosters.global_types
    ontology_values = _ontology_values(rosters)
    gold_values = _gold_slot_values(lock, root, sample_ids)
    report = _filler_binding_report(
        entries, ontology_types=ontology_types, ontology_values=ontology_values, gold_values=gold_values
    )
    if not report.clean:
        raise FillerBindingError(
            "F1 filler roster binding check FAILED -- overlap detected: "
            f"ontology_types={report.overlap_with_ontology_types!r}, "
            f"ontology_values={report.overlap_with_ontology_values!r}, "
            f"gold_values={report.overlap_with_gold_values!r}"
        )
    return report


__all__ = [
    "FILLER_LEXICON_MIN_WORDS",
    "FILLER_LEXICON_SCHEMA",
    "F1_FILLER_SEED",
    "F1_ROSTER_SIZE",
    "FillerBindingError",
    "FillerBindingReport",
    "PsluS2FillerError",
    "check_f1_filler_binding",
    "f1_filler_supply_packet",
    "generate_f1_filler_roster",
    "load_filler_lexicon",
]
