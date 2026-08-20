"""P-CORR-F flight orchestration -- REGISTERED probe SAEA-PROBE-pcorrf-240
(``bounded-discovery-probe``): ``docs/readiness/2026-08-20-pcorrf-
preregistration-REGISTERED.md``. MACHINERY ONLY: this module contains ZERO
live model/server contact and is never itself pointed at a real server --
every test drives ``rails.core_client.MockCoreClient``.

Question: is the core's OWN percept-derived type-name collision (section 0's
scope correction: 68/95 emitted slots, 71.6%, carry entity types outside
SLURP's 55-type train vocabulary -- the P-TRAP scope's "corrective CONFUSABLE
supply" assumption measured empty, 0/37 phonetic-confusion pairs) reparable
by TYPE-LOOKUP corrective supply built ENTIRELY from the core's own A0
zero-supply percept, never gold? Four arms over the SAME frozen 60 SLURP
devel samples the consumed P-SLU/P-KEY/P-TRAP probes already used
(``configs/probes/g0-binding/pslu-sample-devel-n60.json``,
:data:`EXPECTED_SPLIT_IDENTITY_HASH`):

- **W1 CORR-SELF**: the A3-form 100-entry legal roster
  (``rails.probes.pslu_flight.pslu_supply_packet("A3", ...).items``, reused
  via ``base_roster_entries``) PLUS THIS sample's own L1 TYPE-LOOKUP
  corrective entries (:func:`build_l1_entries`), rendered in the roster's
  item shape (:func:`~.pslu_flight.render_roster_entries`, pinned at
  binding -- the SAME renderer ``rails.probes.ptrap_flight`` reuses).
- **W2 CORR-CROSS** (control): IDENTICAL construction and per-sample entry
  count, but the appended entries are seeded-drawn, fixed-point-free, from
  OTHER samples' own L1 corrective entries (never this sample's own) --
  the SAME ``build_trap_sets`` determinism discipline
  ``rails.probes.ptrap_flight`` established (single ``random.Random(seed)``
  walked in sorted sample-id order), generalized from "other samples' own
  A0 wrong values" to "other samples' own L1 corrective entries".
- **W3 CORR-ONLY** (dose): the L1 corrective entries ALONE, no roster base
  -- a sample with K=0 (20/60 under the measured L1 yield) therefore flies
  truly zero-supply (``supply=None``), never an empty-but-present roster
  block (a documented construction choice: see :func:`_corrective_roster_
  packet`'s own docstring).
- **W4 CORR-WIDE** (descriptive, no clause): A3 + L2b, where L2b is L1's own
  entries UNION a retrieval-widened set built via
  ``core.retrieval.retrieve(k=3, min_score=0.70)`` over this sample's own
  emitted filler values against the FULL train-mined value universe
  (:func:`build_l2b_entries`) -- measured mean 2.00 entries/sample on the
  real consumed A0 (this module's own build-mission verification,
  reproducing the registration's own cited figure exactly).

Construction is entirely GOLD-FREE (preregistration section 1): for each
sample, EVERY one of the core's own A0 emitted ``(type, filler)`` slots --
NEVER a wrong-only subset ("wrong" is gold-defined and a wrong-only key is
an oracle here, unlike P-TRAP's own HARM-probe construction, which legally
needs ``analysis.ptrap_read.harvest_a0_wrong_values`` precisely because it
IS gold-scoped) -- is looked up in the train-mined legal pool
(:func:`mine_train_pool`, SLURP ``train.jsonl`` ONLY, full pairs, never
``data.slurp.load_slurp_ontology`` -- that function caps at 5 examples/type
and is the WRONG tool for a pool this construction needs to enumerate
completely) and every legal type that value actually occurs under is
supplied. A corrective entry MAY equal gold BY CONSTRUCTION (that is the
whole point of a type-repair probe); nothing in this module ever CHECKS
that equality to accept/reject a construction decision -- see the legality
guards below.

Three legality guards (preregistration section 4), all fail-closed:

1. **Tri-derivation corrective binding hash** (the ``build_trap_sets``
   pattern, generalized): :func:`compute_corrective_binding_hash` is a pure
   function of ``(a0 response sha256 per sample, train-mined pool sha256,
   seed)``, called at THREE independent sites -- the BUILDER
   (:func:`build_corrective_binding`, which embeds the hash on the returned
   :class:`PCorrFBindingTable`), the standalone VALIDATOR
   (:func:`assert_corrective_binding_hash`, called immediately after
   building AND independently callable by a test), and the FLIGHT PREFLIGHT
   (:func:`run_pcorrf_flight`, which calls the validator a THIRD time before
   issuing any request) -- refusing on any disagreement.
2. **Source-introspection assertion** (:func:`assert_never_references_
   forbidden_gold_symbols`, mirrors ``rails.probes.pslu_flight._source_
   references_ontology_miner``'s own AST-based, never-substring-search
   discipline): this module's OWN source must never reference
   ``analysis.ptrap_read.harvest_a0_wrong_values``, ``data.slurp.
   load_slurp_split``, or ``analysis.pslu_read.load_gold_by_sample_id`` --
   the three established gold-BEARING entry points in this codebase. The
   pre-existing ``rails.probes.pslu_flight.assert_never_calls_ontology_
   miner`` guard (reused verbatim, same as every sibling probe) already
   forbids ANY reference to ``load_slurp_ontology`` at all -- a STRICTER
   ban than the registration's own narrower "with ``include_synthetic``"
   phrasing, so reusing it discharges that clause too.
3. **Legality declarations** (:func:`assert_pcorrf_legality`, wired through
   ``core.legality``): ``span_source="percept-keyed-type-lookup"``,
   ``reference_source="slurp-train-ontology"``, ``legality_tier="legal"`` --
   neither declared value is in ``core.legality.GOLD_DERIVED_SPAN_SOURCES``/
   ``GOLD_DERIVED_REFERENCE_SOURCES``, so ``resolve_legality_declaration``
   accepts the ``legal`` tier cleanly. The either-field rule "catches
   declared contradictions only" (preregistration section 4 item 3); guards
   1-2 above exist precisely because it cannot detect a silently
   gold-conditioned construction.

Ceilings (preregistration section 6, fail-closed): :func:`assert_within_
registered_ceilings` refuses any plan claiming more than :data:`CEILING_
CALLS` = 260 calls, :data:`CEILING_AUDIO_SECONDS` = 1000 metered
audio-seconds, or :data:`CEILING_GPU_HOURS` = 0.35 GPU-hours.
:func:`build_execution_plan` constructs and ``.validate()``s a
``contracts.ExecutionPlan`` (``execution_profile = "bounded-discovery-
probe"``), mirroring ``rails.probes.pemb3m_flight.build_execution_plan``'s
own pattern.

Arm-level (and row-level) idempotence: :func:`run_pcorrf_flight` accepts an
``already_completed: Mapping[arm, frozenset[sample_id]]`` parameter (a
caller/launcher's own already-written ``outputs.jsonl`` rows, read
externally -- this module never touches attempt-dir I/O itself, the SAME
"rails.probes modules are pure orchestrators" convention ``rails.probes.
ptrap_flight``'s own module docstring states) and skips any ``(arm,
sample_id)`` cell already present -- an already-completed arm's own 60
cells are therefore NEVER re-fired a second time, generalizing ``rails.
probes.pemb3m_flight.is_arm_complete``'s manifest-file idempotence check
(vector files) to this row-shaped flight's own launcher-supplied resume
state (a documented design delta, recorded here for audit: pcorrf's output
unit is a scored SLU row, not a standalone vector file, so there is no
natural per-arm manifest path to check for THIS module the way pemb3m's own
``derived/embeddings/<run>/<arm>/manifest.json`` gives it one).

The consumed A0 source this module's own :func:`harvest_a0_emitted_slots`
reads is the CONSUMED P-SLU attempt (:data:`CONSUMED_PSLU_RUN_EXPERIMENT_ID`
/ :data:`CONSUMED_PSLU_ATTEMPT_ID`), ledger-verified ``consumed = yes``
BEFORE opening (:func:`assert_ledger_row_consumed`, mission instruction) --
this harvester is fully GOLD-FREE (only ``reproduction.slurp_scoring.
parse_slu_response`` on the response text, module docstring above), unlike
``analysis.ptrap_read.harvest_a0_wrong_values`` (which needs gold to
classify "wrong"), so it lives HERE in the flight module rather than in an
analysis-layer reader -- a considered, documented deviation from P-TRAP's
own module-boundary precedent, recorded for audit.

Zero live model contact, engineering only: every test in this module's own
suite drives ``rails.core_client.MockCoreClient``.
"""

from __future__ import annotations

import ast
import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from ...contracts import ExecutionPlan, assert_execution_scope
from ...core.retrieval import normalize_term, retrieve
from ...reproduction.slurp_scoring import parse_slu_response
from ..adapters.slurp import SlurpAdapter, SlurpSample
from ..consumption import ConsumptionTrace
from ..supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket
from .pslu_flight import (
    _source_references_ontology_miner,
    assert_never_calls_ontology_miner,
    render_roster_entries,
)

PROBE_ID = "SAEA-PROBE-pcorrf-240"

W1_ARM = "W1"
W2_ARM = "W2"
W3_ARM = "W3"
W4_ARM = "W4"
PCORRF_ARMS: tuple[str, ...] = (W1_ARM, W2_ARM, W3_ARM, W4_ARM)

ARM_N = 60  # the frozen 60 SLURP devel samples, every arm
PLANNED_TOTAL_CALLS = len(PCORRF_ARMS) * ARM_N  # 240 (preregistration section 6)

# Preregistration section 6 ceilings.
CEILING_CALLS = 260
CEILING_AUDIO_SECONDS = 1000
CEILING_GPU_HOURS = 0.35

# Preregistration section 6's own registered plan (never the ceiling itself
# -- module docstring / rails.probes.pemb3m_flight's own DEFAULT_PLANNED_*
# convention of citing the REGISTERED plan, distinct from the ceiling that
# bounds it): "729 s planned (4 passes x 182.26 s)" and "measured-equivalent
# ~=0.15" GPU-h.
DEFAULT_PLANNED_MODEL_CALLS = PLANNED_TOTAL_CALLS
DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS = 730  # ceil(4 * 182.26) = 729.04 -> 730
DEFAULT_PLANNED_GPU_HOURS = 0.15

# This study's SAME fixed seed used throughout the probe family (P-TRAP's
# own DEFAULT_TRAP_SEED, analysis.bootstrap's own DEFAULT_SEED) -- reused
# here for BOTH the W2 cross-sample draw and (by a caller of analysis.
# pcorrf_read) the bootstrap.
DEFAULT_SEED = 20260807

# docs/readiness/2026-08-20-pcorrf-preregistration-REGISTERED.md's own
# opening line: "frozen SLURP 60, split identity fc9de436...5ee5" --
# configs/probes/g0-binding/pslu-sample-devel-n60.json's own
# split_identity_hash, pinned VERBATIM (IDENTICAL to the consumed P-SLU/
# P-KEY/P-TRAP flights' own value). Not imported from a sibling probe
# module (ptrap_flight/pslu_flight each redefine this literal themselves
# too) -- a deliberate decoupling choice, matching that established
# precedent rather than adding a cross-probe import for one literal.
EXPECTED_SPLIT_IDENTITY_HASH = "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"

# The consumed A0 source (mission instruction): the CONSUMED P-SLU flight's
# own zero-supply arm, ledger row `SAEA-PROBE-pslu-n60` (consumed = yes,
# verified by this module's own build mission BEFORE opening the artifact --
# docs/exposure-ledger.md line naming this row).
CONSUMED_PSLU_RUN_EXPERIMENT_ID = "SAEA-PROBE-pslu-n60"
CONSUMED_PSLU_ATTEMPT_ID = "attempt-20260818T010218Z-4c97cb"
CONSUMED_PSLU_OUTPUTS_RELPATH = (
    f"runs/{CONSUMED_PSLU_RUN_EXPERIMENT_ID}/{CONSUMED_PSLU_ATTEMPT_ID}/outputs.jsonl"
)
CONSUMED_PSLU_ARM = "A0"  # matches analysis.ptrap_read's own CONSUMED_PSLU_ARM alias

# The ledger's own column order (docs/exposure-ledger.md header row), SAME
# convention as rails.probes.pemb3m_flight.LEDGER_CONSUMED_COLUMN_INDEX
# (duplicated here, not imported -- module docstring's own recorded
# judgment call: avoids an unrelated cross-probe dependency between two
# conceptually independent probes).
LEDGER_CONSUMED_COLUMN_INDEX = 8

# Train-mined pool (module docstring, :func:`mine_train_pool`): pinned
# against SLURP train.jsonl's own content AT THE TIME this module was
# built -- verified LIVE, read-only, against the real governed corpus
# during this module's own build mission (mirrors rails.probes.
# pemb3m_flight's own PKEY2_338_TRANSCRIPT_REGISTRY_SHA256 precedent: a
# real artifact hash pinned during a machinery-build mission for a LATER
# flight session to drift-check against, never itself a model/server
# contact). 4157 raw (type, filler) pairs / 3961 distinct raw filler
# values / 55 distinct types -- reproduces the g0 binding's own
# ontology_train_only.distinct_values=4157 EXACTLY once counted on RAW
# (lowercased-only, not additionally punctuation-normalized) filler text;
# the preregistration's own disclosure that this label is "pair-count-
# ambiguous" is resolved HERE: 4157 is the PAIR count on raw text, distinct
# from the (slightly smaller) 3958-pair / 3958-value picture a caller gets
# by deduping via core.retrieval.normalize_term first (3 raw filler-text
# variants -- "mary s."/"mary 's", "microsoft"/"@microsoft",
# "nike"/"@nike" -- collapse under normalization, each losing exactly one
# pair). This module's own :attr:`TrainPool.legal_types_by_value` LOOKUP
# index is still built via normalize_term (robust matching against an A0
# emission's own possibly differently-punctuated text), but the pinned
# COUNTS/STATISTICS below are the raw-text figures the registration itself
# cites.
TRAIN_POOL_SHA256 = "fe372974b7047526212cb23799c457d5a5a10a1a116fa0fa413748038d0a6ef6"
TRAIN_POOL_N_PAIRS = 4157
TRAIN_POOL_N_VALUES = 3961
TRAIN_POOL_N_TYPES = 55

# L2b widening (module docstring, W4): core.retrieval.retrieve(k=3,
# min_score=0.70) -- preregistration's own cited parameters.
L2B_K = 3
L2B_MIN_SCORE = 0.70


class PCorrFFlightError(RuntimeError):
    """A P-CORR-F flight/binding input is malformed, a hard invariant (split
    identity, tri-derivation binding hash, fixed-point-freeness, a legality
    declaration, a registered ceiling, or the forbidden-symbol/ontology-
    miner import guards) is violated."""


# ---------------------------------------------------------------------------
# Guard 2: source-introspection, forbidden gold symbols (module docstring).
# ---------------------------------------------------------------------------

_FORBIDDEN_GOLD_SYMBOLS = frozenset(
    {"harvest_a0_wrong_values", "load_slurp_split", "load_gold_by_sample_id"}
)


def _source_references_forbidden_gold_symbol(source: str) -> str | None:
    """AST-based (module docstring: never a substring search, mirrors
    ``rails.probes.pslu_flight._source_references_ontology_miner`` exactly
    -- this module's OWN docstrings legitimately name every one of these
    symbols in prose). Returns the offending symbol name, or ``None``."""

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in _FORBIDDEN_GOLD_SYMBOLS:
                    return alias.name
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_GOLD_SYMBOLS:
            return node.id
        if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_GOLD_SYMBOLS:
            return node.attr
    return None


def assert_never_references_forbidden_gold_symbols(source: str | None = None) -> None:
    """Legality guard 2 (module docstring). Runs at IMPORT time (module-
    level call at the bottom of this file) and again at the top of every
    gold-adjacent entry point (:func:`harvest_a0_emitted_slots`,
    :func:`build_corrective_binding`, :func:`run_pcorrf_flight`) -- so a
    future edit that adds a forbidden reference fails LOUD immediately."""

    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    offender = _source_references_forbidden_gold_symbol(text)
    if offender is not None:
        raise PCorrFFlightError(
            f"rails.probes.pcorrf_flight source references forbidden symbol {offender!r}; L1/W1-W4 "
            "construction must be fully gold-free (preregistration section 4 item 2 -- the "
            "assert_never_calls_ontology_miner pattern extended to harvest_a0_wrong_values, "
            "data.slurp.load_slurp_split, and analysis.pslu_read.load_gold_by_sample_id)"
        )


def _assert_this_module_never_calls_ontology_miner(source: str | None = None) -> None:
    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise PCorrFFlightError(
            "rails.probes.pcorrf_flight source references load_slurp_ontology; this probe's own "
            "train-mined pool comes ONLY from mine_train_pool's direct train.jsonl read (data.slurp's "
            "private _governed_roots/_read_jsonl/_tokens_by_id/_entity_filler primitives), never the "
            "5-example/type-capped ontology miner"
        )


def assert_split_identity_hash(split_identity_hash: str) -> None:
    """Fail-closed: ``split_identity_hash`` must equal
    :data:`EXPECTED_SPLIT_IDENTITY_HASH` VERBATIM -- this probe reuses the
    SAME frozen 60-sample manifest the consumed P-SLU/P-KEY/P-TRAP flights
    used, never a fresh draw."""

    if split_identity_hash != EXPECTED_SPLIT_IDENTITY_HASH:
        raise PCorrFFlightError(
            f"split_identity_hash {split_identity_hash!r} does not match the REGISTERED P-CORR-F "
            f"sample manifest's own hash {EXPECTED_SPLIT_IDENTITY_HASH!r} "
            "(configs/probes/g0-binding/pslu-sample-devel-n60.json, reused byte-identically) -- "
            "fail-closed"
        )


# ---------------------------------------------------------------------------
# Ledger anchor check (mission instruction: verify consumed=yes BEFORE
# opening the consumed artifact).
# ---------------------------------------------------------------------------


def assert_ledger_row_consumed(
    ledger_text: str, *, run_experiment_id: str = CONSUMED_PSLU_RUN_EXPERIMENT_ID
) -> None:
    """Fail-closed: locate the UNIQUE ledger row naming ``run_experiment_id``
    and check its own ``consumed`` column reads exactly ``"yes"`` -- mirrors
    ``rails.probes.pemb3m_flight.assert_ledger_row_consumed`` verbatim
    (duplicated, not imported: module docstring's own recorded judgment
    call)."""

    anchor = f"| {run_experiment_id} |"
    matches = [line for line in ledger_text.splitlines() if anchor in line]
    if not matches:
        raise PCorrFFlightError(f"exposure ledger carries no row for {run_experiment_id!r}")
    if len(matches) > 1:
        raise PCorrFFlightError(
            f"exposure ledger carries {len(matches)} row(s) matching anchor {anchor!r}, expected exactly one"
        )
    cells = [cell.strip() for cell in matches[0].strip().strip("|").split("|")]
    if len(cells) <= LEDGER_CONSUMED_COLUMN_INDEX:
        raise PCorrFFlightError(
            f"exposure ledger row for {run_experiment_id!r} has {len(cells)} column(s), fewer than "
            f"the {LEDGER_CONSUMED_COLUMN_INDEX + 1} required to read its consumed column"
        )
    consumed_cell = cells[LEDGER_CONSUMED_COLUMN_INDEX]
    if consumed_cell != "yes":
        raise PCorrFFlightError(
            f"exposure ledger row for {run_experiment_id!r} carries consumed={consumed_cell!r}, expected "
            "'yes' -- the P-CORR-F harvester refuses to read from an unconsumed artifact"
        )


# ---------------------------------------------------------------------------
# Train-mined pool (module docstring: SLURP train.jsonl ONLY, full pairs).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrainPool:
    """The full, gold-free legal-value pool mined from ``train.jsonl``
    (module docstring): ``legal_types_by_value``/``canonical_value_by_
    normalized`` are keyed by :func:`core.retrieval.normalize_term`'s own
    normalized form (robust lookup); ``n_pairs``/``n_values``/``n_types``
    are the RAW-text statistics the registration itself cites (module
    docstring's own reconciliation note)."""

    legal_types_by_value: Mapping[str, tuple[str, ...]]
    canonical_value_by_normalized: Mapping[str, str]
    all_values_sorted: tuple[str, ...]
    n_pairs: int
    n_values: int
    n_types: int
    sha256: str


def mine_train_pool(lock: Mapping[str, object], root: Path) -> TrainPool:
    """The L1/L2b pool miner (module docstring): reads ``train.jsonl``
    DIRECTLY via ``data.slurp``'s own private governed-path/jsonl/token/
    filler primitives (precedented cross-module private-helper reuse, e.g.
    ``rails.probes.ptrap_flight`` importing ``pslu_flight._source_
    references_ontology_miner``) -- NEVER ``data.slurp.load_slurp_ontology``
    (that function caps at 5 examples/type; the mission's own instruction:
    "do NOT use it for the pool")."""

    from ...data.slurp import _entity_filler, _entity_type, _governed_roots, _read_jsonl, _tokens_by_id

    _, _, metadata_dir = _governed_roots(lock, root)
    train_path = metadata_dir / "train.jsonl"
    if not train_path.is_file():
        raise PCorrFFlightError(f"SLURP train split metadata file missing: {train_path}")

    raw_pairs: set[tuple[str, str]] = set()
    for line_no, raw in enumerate(_read_jsonl(train_path), start=1):
        context = f"SLURP train.jsonl line {line_no}"
        tokens_by_id = _tokens_by_id(raw.get("tokens"), context)
        entities = raw.get("entities")
        if not isinstance(entities, list):
            continue
        for entity in entities:
            if not isinstance(entity, Mapping):
                continue
            entity_type = _entity_type(entity, context)
            filler = _entity_filler(tokens_by_id, entity.get("span"), context)
            raw_pairs.add((entity_type, filler))

    if not raw_pairs:
        raise PCorrFFlightError(f"{train_path}: mined zero (type, filler) pairs")

    n_pairs = len(raw_pairs)
    n_values = len({filler for _entity_type, filler in raw_pairs})
    n_types = len({entity_type for entity_type, _filler in raw_pairs})
    canonical_json = json.dumps(
        sorted([list(pair) for pair in raw_pairs]), sort_keys=True, separators=(",", ":")
    )
    pool_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    legal_types_by_value: dict[str, set[str]] = {}
    canonical_value_by_normalized: dict[str, str] = {}
    for entity_type, filler in raw_pairs:
        norm = normalize_term(filler)
        if not norm:
            continue
        legal_types_by_value.setdefault(norm, set()).add(entity_type)
        if norm not in canonical_value_by_normalized or filler < canonical_value_by_normalized[norm]:
            canonical_value_by_normalized[norm] = filler

    legal_types_frozen = {value: tuple(sorted(types)) for value, types in legal_types_by_value.items()}
    all_values_sorted = tuple(sorted(legal_types_frozen.keys()))

    return TrainPool(
        legal_types_by_value=MappingProxyType(legal_types_frozen),
        canonical_value_by_normalized=MappingProxyType(dict(canonical_value_by_normalized)),
        all_values_sorted=all_values_sorted,
        n_pairs=n_pairs,
        n_values=n_values,
        n_types=n_types,
        sha256=pool_sha256,
    )


def assert_train_pool_sha256(pool: TrainPool) -> None:
    """Fail-closed drift check against :data:`TRAIN_POOL_SHA256` and its
    companion counts -- refuses if SLURP ``train.jsonl`` or the mining
    algorithm changed since this probe's own binding was pinned."""

    if (
        pool.sha256 != TRAIN_POOL_SHA256
        or pool.n_pairs != TRAIN_POOL_N_PAIRS
        or pool.n_values != TRAIN_POOL_N_VALUES
        or pool.n_types != TRAIN_POOL_N_TYPES
    ):
        raise PCorrFFlightError(
            "train-mined pool sha256/counts drifted from the pinned build-mission verification "
            f"(pairs={pool.n_pairs} vs {TRAIN_POOL_N_PAIRS}, values={pool.n_values} vs "
            f"{TRAIN_POOL_N_VALUES}, types={pool.n_types} vs {TRAIN_POOL_N_TYPES}, "
            f"sha256={pool.sha256!r} vs {TRAIN_POOL_SHA256!r}) -- refusing (fail-closed)"
        )


# ---------------------------------------------------------------------------
# Harvester: ALL A0 emitted (type, filler) slots -- gold-free (module
# docstring).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HarvestedA0Slots:
    sample_id: str
    emitted_slots: tuple[tuple[str, str], ...]  # ALL emitted (type, filler), order-preserving
    response_sha256: str  # sha256 of the raw response_text (never the raw text itself, kept lean)


def harvest_a0_emitted_slots(pslu_attempt_dir: Path) -> dict[str, HarvestedA0Slots]:
    """Reads the CONSUMED P-SLU attempt's own ``outputs.jsonl`` A0
    (zero-supply, non-silence-swapped) rows and parses each response's FULL
    predicted-entity set via ``reproduction.slurp_scoring.parse_slu_response``
    -- module docstring: fully gold-free, no gold artifact is ever opened
    here. Zero model contact -- reads an already-written CONSUMED attempt
    only."""

    assert_never_references_forbidden_gold_symbols()
    path = Path(pslu_attempt_dir) / "outputs.jsonl"
    if not path.is_file():
        raise PCorrFFlightError(f"no outputs.jsonl under consumed P-SLU attempt dir {pslu_attempt_dir}")

    result: dict[str, HarvestedA0Slots] = {}
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise PCorrFFlightError(f"{path} line {line_no}: invalid JSON: {error}") from error
        if document.get("arm") != CONSUMED_PSLU_ARM or document.get("silence_swapped", False):
            continue
        sample_id = str(document["sample_id"])
        if sample_id in result:
            raise PCorrFFlightError(f"{path}: duplicate non-silence-swapped {CONSUMED_PSLU_ARM!r} row for {sample_id!r}")
        text = str(document["response_text"])
        _scenario, _action, entities, _parsed = parse_slu_response(text)
        result[sample_id] = HarvestedA0Slots(
            sample_id=sample_id,
            emitted_slots=tuple((entity.type, entity.filler) for entity in entities),
            response_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )
    if not result:
        raise PCorrFFlightError(f"{path}: zero non-silence-swapped {CONSUMED_PSLU_ARM!r} rows found -- nothing to harvest")
    return result


# ---------------------------------------------------------------------------
# Corrective entry shape + L1/L2b builders.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CorrectiveEntry:
    """One appended roster line -- ``origin_sample_id`` names WHICH sample's
    own A0 percept produced the lookup driving this entry (the target
    sample itself for W1/W3/W4; a DIFFERENT sample for every W2 entry,
    mirroring ``rails.probes.ptrap_flight.TrapEntry``'s own field)."""

    entity_type: str
    filler: str
    origin_sample_id: str

    def as_roster_pair(self) -> tuple[str, str]:
        return (self.entity_type, self.filler)

    def as_json(self) -> dict[str, object]:
        return {"type": self.entity_type, "filler": self.filler, "origin_sample_id": self.origin_sample_id}

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "CorrectiveEntry":
        return cls(
            entity_type=str(document["type"]),
            filler=str(document["filler"]),
            origin_sample_id=str(document["origin_sample_id"]),
        )


def build_l1_entries(
    emitted_slots: Sequence[tuple[str, str]], pool: TrainPool, *, origin_sample_id: str
) -> tuple[CorrectiveEntry, ...]:
    """L1 TYPE-LOOKUP (preregistration section 1, module docstring): for
    EVERY emitted ``(type, filler)`` slot (never wrong-only), look up
    ``filler``'s normalized form in the pool and supply EVERY legal type
    that value actually occurs under -- the emitted TYPE itself is never
    consulted (a value's OWN legal types may or may not include what the
    core originally emitted; that mismatch IS the type-collision this probe
    repairs). Order-preserving, deduplicated by ``(type, normalized
    value)``; a filler with no pool match contributes nothing."""

    seen: set[tuple[str, str]] = set()
    entries: list[CorrectiveEntry] = []
    for _emitted_type, filler in emitted_slots:
        norm = normalize_term(filler)
        if not norm:
            continue
        legal_types = pool.legal_types_by_value.get(norm)
        if not legal_types:
            continue
        canonical_value = pool.canonical_value_by_normalized[norm]
        for legal_type in legal_types:  # already sorted at mine_train_pool
            key = (legal_type, norm)
            if key in seen:
                continue
            seen.add(key)
            entries.append(CorrectiveEntry(entity_type=legal_type, filler=canonical_value, origin_sample_id=origin_sample_id))
    return tuple(entries)


def build_l2b_entries(
    emitted_slots: Sequence[tuple[str, str]],
    pool: TrainPool,
    *,
    origin_sample_id: str,
    exclude_keys: frozenset[tuple[str, str]],
    k: int = L2B_K,
    min_score: float = L2B_MIN_SCORE,
) -> tuple[CorrectiveEntry, ...]:
    """W4's own L2b widening (module docstring): ``core.retrieval.
    retrieve(k=3, min_score=0.70)`` over this sample's own DISTINCT
    normalized emitted-filler query terms against the FULL train-mined
    value universe, unioned with (never duplicating) ``exclude_keys`` --
    the caller's own L1 ``(type, normalized value)`` key set. Returns ONLY
    the ADDITIONAL entries beyond ``exclude_keys`` (the caller merges with
    L1 itself, module docstring's own "L2b is L1's own entries UNION a
    retrieval-widened set" framing)."""

    query_terms = sorted({normalize_term(filler) for _entity_type, filler in emitted_slots if normalize_term(filler)})
    if not query_terms or not pool.all_values_sorted:
        return ()
    retrieved = retrieve(query_terms, list(pool.all_values_sorted), k=k, min_score=min_score)
    seen = set(exclude_keys)
    entries: list[CorrectiveEntry] = []
    for candidate_value, _score in retrieved:
        legal_types = pool.legal_types_by_value.get(candidate_value, ())
        canonical_value = pool.canonical_value_by_normalized.get(candidate_value, candidate_value)
        for legal_type in legal_types:
            key = (legal_type, candidate_value)
            if key in seen:
                continue
            seen.add(key)
            entries.append(CorrectiveEntry(entity_type=legal_type, filler=canonical_value, origin_sample_id=origin_sample_id))
    return tuple(entries)


# ---------------------------------------------------------------------------
# Per-sample corrective set table (build_trap_sets pattern, generalized).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SampleCorrectiveSet:
    sample_id: str
    l1_entries: tuple[CorrectiveEntry, ...]  # W1's own addition (= W3's own supply)
    w2_entries: tuple[CorrectiveEntry, ...]  # cross-sample-drawn, length-matched to l1_entries
    w4_added_entries: tuple[CorrectiveEntry, ...]  # W4's ADDITIONAL entries beyond l1_entries
    emitted_slot_count: int  # diagnostic: how many A0 (type, filler) slots this sample emitted

    @property
    def l1_k(self) -> int:
        return len(self.l1_entries)

    @property
    def w2_k(self) -> int:
        return len(self.w2_entries)


def build_corrective_sets(
    *,
    emitted_slots_by_sample: Mapping[str, Sequence[tuple[str, str]]],
    pool: TrainPool,
    sample_ids: Sequence[str],
    seed: int = DEFAULT_SEED,
) -> dict[str, SampleCorrectiveSet]:
    """Offline, pure (no I/O, no model contact): builds L1 (every sample's
    own), the W4-additional L2b widening, and the seeded W2 cross-sample
    draw -- the ``build_trap_sets`` pattern (module docstring), generalized
    from ``rails.probes.ptrap_flight.build_trap_sets``. A sample id absent
    from ``emitted_slots_by_sample`` (or present with an empty tuple) is a
    legitimate K=0 shape, never an error (mirrors ptrap's own convention)."""

    ids = tuple(sample_ids)
    if len(ids) != len(set(ids)):
        raise PCorrFFlightError("build_corrective_sets: sample_ids carries a duplicate")

    l1_by_sample: dict[str, tuple[CorrectiveEntry, ...]] = {}
    w4_added_by_sample: dict[str, tuple[CorrectiveEntry, ...]] = {}
    slot_count_by_sample: dict[str, int] = {}
    for sid in ids:
        slots = tuple(emitted_slots_by_sample.get(sid, ()))
        slot_count_by_sample[sid] = len(slots)
        l1_entries = build_l1_entries(slots, pool, origin_sample_id=sid)
        l1_by_sample[sid] = l1_entries
        l1_keys = frozenset((entry.entity_type, normalize_term(entry.filler)) for entry in l1_entries)
        w4_added_by_sample[sid] = build_l2b_entries(slots, pool, origin_sample_id=sid, exclude_keys=l1_keys)

    # W2: SAME determinism discipline as rails.probes.ptrap_flight.
    # build_trap_sets -- a SINGLE random.Random(seed) walked across every
    # sample IN SORTED sample_id ORDER, never per-sample reseeded.
    rng = random.Random(seed)
    result: dict[str, SampleCorrectiveSet] = {}
    for sid in sorted(ids):
        k_target = len(l1_by_sample[sid])
        candidates: list[CorrectiveEntry] = []
        seen_keys: set[tuple[str, str]] = set()
        for other_sid in sorted(ids):
            if other_sid == sid:
                continue
            for entry in l1_by_sample[other_sid]:
                key = (entry.entity_type, normalize_term(entry.filler))
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                candidates.append(entry)
        if k_target > 0 and candidates:
            draw_count = min(k_target, len(candidates))
            drawn_indices = sorted(rng.sample(range(len(candidates)), draw_count))
            w2_entries = tuple(candidates[i] for i in drawn_indices)
        else:
            w2_entries = ()
        for entry in w2_entries:
            if entry.origin_sample_id == sid:
                raise PCorrFFlightError(
                    f"build_corrective_sets: W2 fixed-point violation on target sample {sid!r} -- should "
                    "be structurally impossible (the candidate pool excludes the target's own L1 by "
                    "construction)"
                )
        result[sid] = SampleCorrectiveSet(
            sample_id=sid,
            l1_entries=l1_by_sample[sid],
            w2_entries=w2_entries,
            w4_added_entries=w4_added_by_sample[sid],
            emitted_slot_count=slot_count_by_sample[sid],
        )
    return result


def validate_pcorrf_corrective_sets(
    corrective_sets: Mapping[str, SampleCorrectiveSet], *, expected_sample_ids: Sequence[str]
) -> None:
    """Fail-closed structural checks, independently callable (a test
    fixture, or :func:`build_corrective_binding`'s own call)."""

    expected = tuple(expected_sample_ids)
    expected_set = set(expected)
    if len(expected) != len(expected_set):
        raise PCorrFFlightError("expected_sample_ids carries a duplicate")
    got = set(corrective_sets.keys())
    if got != expected_set:
        missing = sorted(expected_set - got)
        extra = sorted(got - expected_set)
        raise PCorrFFlightError(
            f"corrective_sets sample id set does not match the expected {len(expected_set)}-sample "
            f"manifest (missing={missing[:5]}, extra={extra[:5]})"
        )
    for sid, corrective_set in corrective_sets.items():
        if corrective_set.sample_id != sid:
            raise PCorrFFlightError(f"corrective_sets[{sid!r}].sample_id={corrective_set.sample_id!r} disagrees with its own key")
        if len(corrective_set.w2_entries) > len(corrective_set.l1_entries):
            raise PCorrFFlightError(
                f"sample {sid!r}: W2 k={len(corrective_set.w2_entries)} exceeds this sample's own L1 "
                f"k={len(corrective_set.l1_entries)} (length-matched invariant violated)"
            )
        for entry in corrective_set.w2_entries:
            if entry.origin_sample_id == sid:
                raise PCorrFFlightError(
                    f"sample {sid!r}: a W2 entry's own origin_sample_id equals its target -- "
                    "fixed-point-free invariant violated"
                )
        l1_keys = {(entry.entity_type, normalize_term(entry.filler)) for entry in corrective_set.l1_entries}
        for entry in corrective_set.w4_added_entries:
            key = (entry.entity_type, normalize_term(entry.filler))
            if key in l1_keys:
                raise PCorrFFlightError(
                    f"sample {sid!r}: W4-added entry {entry!r} duplicates an L1 entry -- dedupe invariant violated"
                )


# ---------------------------------------------------------------------------
# Guard 1: tri-derivation corrective binding hash (module docstring).
# ---------------------------------------------------------------------------


def compute_corrective_binding_hash(
    *, response_sha256_by_sample: Mapping[str, str], pool_sha256: str, seed: int
) -> str:
    """Pure function of ``(A0 response text [content-addressed by its own
    sha256], train-mined pool sha256, seed)`` -- the tri-derivation guard's
    ONE shared primitive, called identically at all three sites (module
    docstring)."""

    canonical = json.dumps(
        {
            "a0_response_sha256_by_sample": dict(sorted(response_sha256_by_sample.items())),
            "pool_sha256": pool_sha256,
            "seed": seed,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PCorrFBindingTable:
    corrective_sets: Mapping[str, SampleCorrectiveSet]
    pool_sha256: str
    seed: int
    binding_hash: str


def build_corrective_binding(
    *,
    harvested: Mapping[str, HarvestedA0Slots],
    pool: TrainPool,
    sample_ids: Sequence[str],
    seed: int = DEFAULT_SEED,
) -> PCorrFBindingTable:
    """Tri-derivation site #1 (the BUILDER, module docstring): builds the
    full corrective-set table, validates it structurally, and embeds the
    corrective binding hash on the returned table."""

    assert_never_references_forbidden_gold_symbols()
    emitted_slots_by_sample = {
        sid: harvested[sid].emitted_slots for sid in sample_ids if sid in harvested
    }
    corrective_sets = build_corrective_sets(
        emitted_slots_by_sample=emitted_slots_by_sample, pool=pool, sample_ids=sample_ids, seed=seed
    )
    validate_pcorrf_corrective_sets(corrective_sets, expected_sample_ids=sample_ids)
    response_sha256_by_sample = {sid: harvested[sid].response_sha256 for sid in sample_ids if sid in harvested}
    binding_hash = compute_corrective_binding_hash(
        response_sha256_by_sample=response_sha256_by_sample, pool_sha256=pool.sha256, seed=seed
    )
    return PCorrFBindingTable(
        corrective_sets=MappingProxyType(corrective_sets),
        pool_sha256=pool.sha256,
        seed=seed,
        binding_hash=binding_hash,
    )


def assert_corrective_binding_hash(
    table: PCorrFBindingTable, *, harvested: Mapping[str, HarvestedA0Slots], seed: int
) -> None:
    """Tri-derivation sites #2 and #3 (the standalone VALIDATOR, module
    docstring): independently RE-DERIVES the corrective binding hash from
    ``harvested``/``table.pool_sha256``/``seed`` and compares against
    ``table.binding_hash`` -- refusing (fail-closed) on disagreement. Called
    once, standalone, immediately after :func:`build_corrective_binding`
    (site #2), and again, unmodified, inside :func:`run_pcorrf_flight`'s own
    preflight (site #3) -- the SAME "call the SAME validator from a second,
    independent site" idiom ``rails.probes.ptrap_flight.validate_ptrap_
    flight_summary`` already establishes in this codebase."""

    if seed != table.seed:
        raise PCorrFFlightError(f"corrective binding hash re-derivation seed {seed!r} != table.seed {table.seed!r}")
    response_sha256_by_sample = {
        sid: record.response_sha256 for sid, record in harvested.items() if sid in table.corrective_sets
    }
    recomputed = compute_corrective_binding_hash(
        response_sha256_by_sample=response_sha256_by_sample, pool_sha256=table.pool_sha256, seed=seed
    )
    if recomputed != table.binding_hash:
        raise PCorrFFlightError(
            f"corrective binding hash mismatch: table carries {table.binding_hash!r}, independently "
            f"recomputed {recomputed!r} -- refusing (fail-closed tri-derivation guard, preregistration "
            "section 4 item 1)"
        )


# ---------------------------------------------------------------------------
# Legality guard 3 (module docstring): declarations wired through contracts.
# ---------------------------------------------------------------------------

LEGALITY_SPAN_SOURCE = "percept-keyed-type-lookup"
LEGALITY_REFERENCE_SOURCE = "slurp-train-ontology"
LEGALITY_TIER = "legal"


def build_pcorrf_legality_values() -> dict[str, object]:
    return {
        "arm": PROBE_ID,
        "span_source": LEGALITY_SPAN_SOURCE,
        "reference_source": LEGALITY_REFERENCE_SOURCE,
        "legality_tier": LEGALITY_TIER,
        "evidence_source": "corrective-supply",
    }


def assert_pcorrf_legality(root: Path):
    """Wires the three declarations through ``core.legality`` (module
    docstring). Neither declared value is a GOLD_DERIVED_* marker, so this
    NEVER refuses for a correctly-declared P-CORR-F call -- a refusal here
    would mean the declared values themselves drifted into a ceiling marker,
    a genuine defect."""

    from ...core.legality import assert_legality_declaration_legal

    return assert_legality_declaration_legal(build_pcorrf_legality_values(), root)


# ---------------------------------------------------------------------------
# Ceilings + contracts.ExecutionPlan (preregistration section 6).
# ---------------------------------------------------------------------------


def assert_within_registered_ceilings(*, calls: int, audio_seconds: float, gpu_hours: float) -> None:
    if calls > CEILING_CALLS:
        raise PCorrFFlightError(f"{calls} calls exceeds the registered ceiling of {CEILING_CALLS}")
    if audio_seconds > CEILING_AUDIO_SECONDS:
        raise PCorrFFlightError(
            f"{audio_seconds} metered audio-second(s) exceeds the registered ceiling of {CEILING_AUDIO_SECONDS}"
        )
    if gpu_hours > CEILING_GPU_HOURS:
        raise PCorrFFlightError(f"{gpu_hours} GPU-hour(s) exceeds the registered ceiling of {CEILING_GPU_HOURS}")


def build_execution_plan(
    *,
    attempt_id: str | None = None,
    planned_model_calls: int = DEFAULT_PLANNED_MODEL_CALLS,
    planned_gpu_hours: float = DEFAULT_PLANNED_GPU_HOURS,
    planned_speech_audio_seconds: int = DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS,
    carrier_lock_key: str = "slurp",
) -> ExecutionPlan:
    """Constructs and ``.validate()``s the ``contracts.ExecutionPlan`` for
    this probe -- mirrors ``rails.probes.pemb3m_flight.build_execution_
    plan``'s own pattern. ``protocol_hash`` is :func:`binding_config_
    sha256` (an existing 64-hex sha256, never a second digest)."""

    execution_profile = assert_execution_scope("bounded-discovery-probe")
    assert_within_registered_ceilings(
        calls=planned_model_calls, audio_seconds=planned_speech_audio_seconds, gpu_hours=planned_gpu_hours
    )
    plan = ExecutionPlan(
        run_id=PROBE_ID,
        execution_profile=execution_profile,
        carrier_lock_key=carrier_lock_key,
        split_role="discovery",
        split_identity_hash=EXPECTED_SPLIT_IDENTITY_HASH,
        planned_model_calls=planned_model_calls,
        planned_gpu_hours=planned_gpu_hours,
        planned_speech_audio_seconds=planned_speech_audio_seconds,
        protocol_hash=binding_config_sha256(),
        attempt_id=attempt_id,
    )
    return plan.validate()


# ---------------------------------------------------------------------------
# Binding config document + pinned sha256 (drift check, module docstring).
# ---------------------------------------------------------------------------

BINDING_CONFIG_SCHEMA = "saea-pcorrf-binding-config-v1"


def build_binding_config_document() -> dict[str, object]:
    return {
        "schema": BINDING_CONFIG_SCHEMA,
        "split_identity_hash": EXPECTED_SPLIT_IDENTITY_HASH,
        "arms": list(PCORRF_ARMS),
        "arm_n": ARM_N,
        "seed": DEFAULT_SEED,
        "train_pool": {
            "sha256": TRAIN_POOL_SHA256,
            "n_pairs": TRAIN_POOL_N_PAIRS,
            "n_values": TRAIN_POOL_N_VALUES,
            "n_types": TRAIN_POOL_N_TYPES,
        },
        "l2b": {"k": L2B_K, "min_score": L2B_MIN_SCORE},
        "consumed_pslu_source": {
            "run_experiment_id": CONSUMED_PSLU_RUN_EXPERIMENT_ID,
            "attempt_id": CONSUMED_PSLU_ATTEMPT_ID,
            "arm": CONSUMED_PSLU_ARM,
        },
        "legality": build_pcorrf_legality_values(),
    }


def binding_config_sha256() -> str:
    canonical = json.dumps(build_binding_config_document(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


# Pinned against this module's own binding table AT THE TIME it was
# written (module docstring) -- a future edit to the arm table, seed,
# train-pool pin, L2b params, or the legality declarations drifts this
# digest and refuses fail-closed via assert_binding_config_sha256.
BINDING_CONFIG_SHA256 = "4f540b24df430cbb80c4e1e9dc6c0ee09f61b698d1022ca39a50a750fdd7400e"


def assert_binding_config_sha256() -> None:
    actual = binding_config_sha256()
    if actual != BINDING_CONFIG_SHA256:
        raise PCorrFFlightError(
            f"P-CORR-F binding config sha256 {actual!r} does not match the pinned "
            f"{BINDING_CONFIG_SHA256!r} -- the arm table, seed, train-pool pin, L2b params, or the "
            "legality declarations have drifted; refusing (fail-closed)"
        )


# ---------------------------------------------------------------------------
# Roster rendering per arm (module docstring: W1/W2 = A3 + addition, W3 =
# addition alone (None when empty), W4 = A3 + L1 + L2b-additional).
# ---------------------------------------------------------------------------


def _corrective_roster_packet(
    arm: str, sample_id: str, base_entries: Sequence[tuple[str, str]], entries: Sequence[CorrectiveEntry]
) -> SupplyPacket | None:
    """Renders ``base_entries + entries`` in the SAME roster item shape
    every sibling probe uses (``rails.probes.pslu_flight.render_roster_
    entries``, pinned at binding). Returns ``None`` (true zero-supply, the
    SAME shape ``TaskAdapter.assemble_prompt`` gives A0) when the combined
    entry list is EMPTY -- a documented construction choice for W3's own
    K=0 samples (20/60 under the measured L1 yield): "no roster base" plus
    "zero corrective entries" is read as NOTHING supplied, never an
    ambiguous empty-roster-block artifact with a blank prompt_block."""

    combined: tuple[tuple[str, str], ...] = tuple(base_entries) + tuple(entry.as_roster_pair() for entry in entries)
    if not combined:
        return None
    prompt_block = render_roster_entries(combined)
    items = tuple(
        SupplyItem(item_id=f"{arm}-{sample_id}-{index:03d}", text=f"{entry_type}={value}")
        for index, (entry_type, value) in enumerate(combined)
    )
    return SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=len(combined), token_count=len(prompt_block.split())),
        prompt_block=prompt_block,
        assembly_template_id=f"pcorrf-{arm}-roster-v1",
        items=items,
    ).validate()


def _arm_entries(arm: str, corrective_set: SampleCorrectiveSet) -> tuple[CorrectiveEntry, ...]:
    if arm == W1_ARM:
        return corrective_set.l1_entries
    if arm == W2_ARM:
        return corrective_set.w2_entries
    if arm == W3_ARM:
        return corrective_set.l1_entries
    if arm == W4_ARM:
        return corrective_set.l1_entries + corrective_set.w4_added_entries
    raise PCorrFFlightError(f"unknown P-CORR-F arm {arm!r}; known arms are {PCORRF_ARMS}")


def pcorrf_supply_packet(
    arm: str,
    sample_id: str,
    *,
    base_roster_entries: Sequence[tuple[str, str]],
    corrective_set: SampleCorrectiveSet,
) -> SupplyPacket | None:
    entries = _arm_entries(arm, corrective_set)
    base = () if arm == W3_ARM else base_roster_entries
    return _corrective_roster_packet(arm, sample_id, base, entries)


# ---------------------------------------------------------------------------
# Flight orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PCorrFArmResult:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace
    k: int
    # Embedded so the read suite's dual measurement never needs to re-derive
    # the corrective set live (harness-defect-resistant design, mirrors
    # rails.probes.ptrap_flight.PTrapArmResult.trap_entries).
    corrective_entries: tuple[Mapping[str, object], ...]


@dataclass(frozen=True)
class PCorrFFlightSummary:
    results: tuple[PCorrFArmResult, ...]
    binding_table: PCorrFBindingTable


def validate_pcorrf_flight_summary(
    summary: PCorrFFlightSummary, *, expected_sample_ids: Sequence[str]
) -> None:
    """Fail-closed structural checks over WHATEVER rows are actually
    present in ``summary`` -- deliberately NOT a completeness check (module
    docstring: arm/row-level idempotence means a legitimate partial-resume
    summary may carry fewer than every ``(arm, sample_id)`` cell)."""

    expected_set = set(expected_sample_ids)
    seen_keys: set[tuple[str, str]] = set()
    l1_k_by_sample: dict[str, int] = {
        row.sample_id: row.k for row in summary.results if row.arm == W1_ARM
    }
    for row in summary.results:
        if row.arm not in PCORRF_ARMS:
            raise PCorrFFlightError(f"unknown P-CORR-F arm {row.arm!r}")
        key = (row.arm, row.sample_id)
        if key in seen_keys:
            raise PCorrFFlightError(f"duplicate row for (arm, sample_id)={key}")
        seen_keys.add(key)
        if row.sample_id not in expected_set:
            raise PCorrFFlightError(f"row sample_id {row.sample_id!r} is not in the expected frozen manifest")
        if row.k != len(row.corrective_entries):
            raise PCorrFFlightError(
                f"arm {row.arm} sample {row.sample_id!r}: k={row.k} disagrees with "
                f"len(corrective_entries)={len(row.corrective_entries)}"
            )
        if row.arm == W2_ARM:
            for entry in row.corrective_entries:
                if entry.get("origin_sample_id") == row.sample_id:
                    raise PCorrFFlightError(
                        f"arm W2 sample {row.sample_id!r}: a corrective entry's own origin_sample_id "
                        "equals its target sample id -- fixed-point-free invariant violated"
                    )
            l1_k = l1_k_by_sample.get(row.sample_id)
            if l1_k is not None and row.k > l1_k:
                raise PCorrFFlightError(
                    f"arm W2 sample {row.sample_id!r}: k={row.k} exceeds this SAME sample's own W1 "
                    f"k={l1_k} (length-matched invariant violated)"
                )


def run_pcorrf_flight(
    *,
    adapter: SlurpAdapter,
    core_client,
    samples: Sequence[SlurpSample],
    base_roster_entries: Sequence[tuple[str, str]],
    binding_table: PCorrFBindingTable,
    harvested: Mapping[str, HarvestedA0Slots],
    root: Path,
    split_identity_hash: str,
    decoding_params: Mapping[str, object] | None = None,
    already_completed: Mapping[str, frozenset[str]] = MappingProxyType({}),
) -> PCorrFFlightSummary:
    """Execute the four-arm P-CORR-F flight over ``samples`` (module
    docstring): up to ``4 * len(samples)`` requests, W1..W4 per sample,
    skipping any ``(arm, sample_id)`` cell already present in
    ``already_completed`` (arm/row-level idempotence). ``core_client`` is
    duck-typed against ``rails.core_client.CoreClient`` (the SAME
    "no forced import" discipline every sibling flight in this package
    uses)."""

    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    assert_never_references_forbidden_gold_symbols()
    assert_split_identity_hash(split_identity_hash)
    assert_pcorrf_legality(root)
    # Tri-derivation guard site #3 (module docstring): the FLIGHT PREFLIGHT
    # re-derivation, independent of build_corrective_binding's own site #1
    # and the standalone site #2 call a caller/test makes -- refuses BEFORE
    # any request is issued.
    assert_corrective_binding_hash(binding_table, harvested=harvested, seed=binding_table.seed)

    if not samples:
        raise PCorrFFlightError("run_pcorrf_flight requires at least one sample")
    sample_ids_list = [sample.sample_id for sample in samples]
    if len(sample_ids_list) != len(set(sample_ids_list)):
        raise PCorrFFlightError("duplicate sample_id in samples")
    missing = [sid for sid in sample_ids_list if sid not in binding_table.corrective_sets]
    if missing:
        raise PCorrFFlightError(
            f"binding_table carries no SampleCorrectiveSet for {len(missing)} sample id(s) this "
            f"flight's own samples name: {missing[:5]}"
        )
    unknown_arms = set(already_completed) - set(PCORRF_ARMS)
    if unknown_arms:
        raise PCorrFFlightError(f"already_completed names unknown arm id(s) {sorted(unknown_arms)}")

    total_planned = len(samples) * len(PCORRF_ARMS)
    if total_planned > CEILING_CALLS:
        raise PCorrFFlightError(
            f"planned {total_planned} calls ({len(samples)} samples x {len(PCORRF_ARMS)} arms) exceeds "
            f"the registered ceiling of {CEILING_CALLS}"
        )

    base_entries = tuple(base_roster_entries)
    results: list[PCorrFArmResult] = []
    for sample in samples:
        corrective_set = binding_table.corrective_sets[sample.sample_id]
        for arm in PCORRF_ARMS:
            if sample.sample_id in already_completed.get(arm, frozenset()):
                continue
            entries = _arm_entries(arm, corrective_set)
            supply = pcorrf_supply_packet(
                arm, sample.sample_id, base_roster_entries=base_entries, corrective_set=corrective_set
            )
            messages = adapter.assemble_prompt(sample, supply)
            response_text = core_client.complete(messages, decoding_params=decoding_params)
            metrics = adapter.score(sample, response_text)
            consumption = adapter.extract_consumption(sample, supply, response_text)
            results.append(
                PCorrFArmResult(
                    arm=arm,
                    sample_id=sample.sample_id,
                    messages=tuple(messages),
                    response_text=response_text,
                    metrics=metrics,
                    consumption=consumption,
                    k=len(entries),
                    corrective_entries=tuple(entry.as_json() for entry in entries),
                )
            )

    summary = PCorrFFlightSummary(results=tuple(results), binding_table=binding_table)
    validate_pcorrf_flight_summary(summary, expected_sample_ids=tuple(sample_ids_list))
    return summary


__all__ = [
    "ARM_N",
    "BINDING_CONFIG_SCHEMA",
    "BINDING_CONFIG_SHA256",
    "CEILING_AUDIO_SECONDS",
    "CEILING_CALLS",
    "CEILING_GPU_HOURS",
    "CONSUMED_PSLU_ARM",
    "CONSUMED_PSLU_ATTEMPT_ID",
    "CONSUMED_PSLU_OUTPUTS_RELPATH",
    "CONSUMED_PSLU_RUN_EXPERIMENT_ID",
    "DEFAULT_PLANNED_GPU_HOURS",
    "DEFAULT_PLANNED_MODEL_CALLS",
    "DEFAULT_PLANNED_SPEECH_AUDIO_SECONDS",
    "DEFAULT_SEED",
    "EXPECTED_SPLIT_IDENTITY_HASH",
    "L2B_K",
    "L2B_MIN_SCORE",
    "LEDGER_CONSUMED_COLUMN_INDEX",
    "LEGALITY_REFERENCE_SOURCE",
    "LEGALITY_SPAN_SOURCE",
    "LEGALITY_TIER",
    "PCORRF_ARMS",
    "PLANNED_TOTAL_CALLS",
    "PROBE_ID",
    "TRAIN_POOL_N_PAIRS",
    "TRAIN_POOL_N_TYPES",
    "TRAIN_POOL_N_VALUES",
    "TRAIN_POOL_SHA256",
    "W1_ARM",
    "W2_ARM",
    "W3_ARM",
    "W4_ARM",
    "CorrectiveEntry",
    "HarvestedA0Slots",
    "PCorrFArmResult",
    "PCorrFBindingTable",
    "PCorrFFlightError",
    "PCorrFFlightSummary",
    "SampleCorrectiveSet",
    "TrainPool",
    "assert_binding_config_sha256",
    "assert_corrective_binding_hash",
    "assert_ledger_row_consumed",
    "assert_never_references_forbidden_gold_symbols",
    "assert_pcorrf_legality",
    "assert_split_identity_hash",
    "assert_train_pool_sha256",
    "assert_within_registered_ceilings",
    "binding_config_sha256",
    "build_binding_config_document",
    "build_corrective_binding",
    "build_corrective_sets",
    "build_execution_plan",
    "build_l1_entries",
    "build_l2b_entries",
    "build_pcorrf_legality_values",
    "compute_corrective_binding_hash",
    "harvest_a0_emitted_slots",
    "mine_train_pool",
    "pcorrf_supply_packet",
    "run_pcorrf_flight",
    "validate_pcorrf_corrective_sets",
    "validate_pcorrf_flight_summary",
]


# Executed at import time (mirrors rails.probes.ptrap_flight's own
# module-bottom self-check): fails LOUD the moment this module is next
# imported if a future edit adds a live reference to the forbidden ontology
# miner or a forbidden gold symbol.
assert_never_calls_ontology_miner()
_assert_this_module_never_calls_ontology_miner()
assert_never_references_forbidden_gold_symbols()
