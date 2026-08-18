"""P-SLU offline read suite (pinned, pre-registered).

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores an already-written attempt's
``outputs.jsonl`` / ``predicted-scenarios.json`` / ``flight-receipt.json``
(``rails.probes.pslu_flight.run_pslu_flight`` / the flight launcher's own
write shape, see ``docs/checks/speech-aware-evidence-acquisition/
2026-08-17-pslu-flight/launcher/launch_pslu_flight.py``) through the SAME
frozen official-metric scorer every other consumer of this carrier uses
(``reproduction.slurp_scoring.score_slu`` / ``parse_slu_response``), plus
the same roster-construction function the flight itself calls
(``rails.probes.pslu_flight.pslu_supply_packet``) to cross-check what was
actually supplied against what the registered roster table says should
have been supplied.

Sources of truth this module implements EXACTLY (never re-derives on its
own authority):

- ``docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md`` sections
  3 (metrics) and 4 (branch rules): SUPPLY-CONVERTS / COPY-TRAP /
  DOSE-CONFIRM / INERT / VOID, with their bound thresholds.
- ``configs/probes/g0-binding/pslu-sample-devel-n60.json`` (the frozen
  sample set) and ``configs/probes/g0-binding/pslu-rosters-train-only.json``
  (the frozen rosters), loaded via ``rails.probes.pslu_flight``'s own
  loaders -- never re-parsed by hand here.
- ``configs/probes/g0-binding/pslu-flight.json``'s own metrics line:
  ``"copy_rate (rails.consumption.ConsumptionTrace)"`` -- copy-rate is read
  off the already-embedded ``ConsumptionTrace`` the flight computed at
  write time, never re-derived by a second, drifting algorithm.

DEVELOPED AND TESTED EXCLUSIVELY AGAINST HAND-AUTHORED SYNTHETIC FIXTURES
(``tests/unit/test_pslu_read.py``). This module is never run against the
real flight attempt directory
(``$SPEECHRL_DATA_DIR/runs/SAEA-PROBE-pslu-n60/``) by the task that wrote
it; a later, separately-registered one-shot read session points
``build_pslu_report``/the CLI at the real COMPLETED attempt.

ENGINEERING-INTERPRETATION NOTES (flagged here, not buried, because the
pre-registration text is genuinely underspecified on these exact points --
each is a documented, reviewable choice, not a silent guess):

1. "supplied roster tokens" (prereg section 2's induced-substitution
   parenthetical) means the VALUE half of each ``"{type}={value}"`` roster
   entry actually reconstructed for that exact (arm, sample) call via the
   frozen :func:`rails.probes.pslu_flight.pslu_supply_packet` -- never the
   bare TYPE half A2 supplies. A2 supplies no values at all (only type
   names), so its induced-substitution count is 0 by construction (see
   :func:`_roster_values_for_packet`).
2. "appearing as a slot filler" is read as normalized EXACT equality
   between a predicted entity's filler and a supplied roster value -- not a
   substring/subsequence test -- mirroring ``slot_f1_exact``'s own
   exact-filler-match convention (``reproduction.slurp_scoring`` module
   docstring), the metric family this induced-substitution count is most
   naturally paired with.
3. "the aligned reference" (same clause) is the same-type gold entity a
   predicted entity would greedily match under the frozen scorer's OWN
   nearest-word-distance alignment -- ``reproduction.slurp_scoring.
   _lowest_distance`` / ``_word_distance``, imported directly (private
   cross-module reuse already precedented in this repository:
   ``rails.consumption.classify_outcome`` imports
   ``analysis.p2_reads._count_subsequence`` the same way). A predicted
   entity with no same-type gold entity left in the remaining pool has NO
   aligned reference and is excluded from the count (the clause requires
   one to exist). See :func:`count_induced_substitutions`.
4. "copy-rate" itself (as opposed to what counts as a "copy") has no
   formula anywhere in the prereg text; section 2's parenthetical actually
   defines induced-substitution, not copy-rate. This module reads
   copy-rate exactly as ``configs/probes/g0-binding/pslu-flight.json``'s
   own metrics line names it -- the arm-level MICRO aggregate (copies /
   total supplied items, summed across every one of that arm's 60
   non-silence-swap calls) of the ``rails.consumption.ConsumptionTrace``
   records the flight itself already embedded per row at write time, never
   re-derived by a second algorithm here. Silence-swap rows are excluded
   from every per-arm aggregate. See :func:`arm_copy_rate`.
5. COPY-TRAP's third disjunct, "copy-rate >= 50%" (section 4), names no
   arm. Read as A1''s OWN copy-rate specifically -- the SAME arm/quantity
   SUPPLY-CONVERTS' own third AND-clause already names ("A1' copy-rate <
   50%"); section 4 gives copy-rate no other arm-scoped reading anywhere.
6. "entity true-positive gain" (COPY-TRAP's second disjunct) is read as
   that arm's summed ``slot_f1_exact_tp`` minus A0's -- the official
   "entities" exact-match ledger (``reproduction.slurp_scoring`` module
   docstring's own "not official SLU-F1" naming), the same TP unit
   induced-substitution's own exact-equality convention (note 2) is
   already scoped to -- never the word/char-distance ``slu_f1`` TP
   ingredient, which counts same-TYPE matches regardless of filler
   correctness and would make "true positive" mean something looser than
   the clause's own wording suggests.
7. VOID's silence-swap clause fires iff ALL THREE silence-swap samples show
   an unchanged parsed answer (scenario + action + entity set) versus
   their real-audio counterpart. The prereg names no quantifier; unanimity
   is read as the more defensible bar for a claim this strong (a single
   flipped sample is still reported, but does not by itself void the
   read). See :func:`compare_silence_swap` / :func:`_void_clause_silence_swap`.
8. "harness defect" (VOID, section 4) is machine-checked, not
   judgment-based: arm/sample-set completeness against the frozen
   manifest, duplicate rows, a missing silence-swap real-audio
   counterpart, a non-``COMPLETED`` flight receipt, and -- reusing the
   frozen ``pslu_supply_packet`` production code directly rather than a
   second, drifting reconstruction -- any row whose own supplied prompt
   text disagrees with what that exact function would produce for its
   (arm, scenario) pair. See :func:`_harness_defect_reasons`.
9. COPY-TRAP's two gain/count-based disjuncts ("A4 gain >= half of A1'
   gain", "induced-substitution count >= entity TP gain"), read
   completely literally with a non-strict ">=", are VACUOUSLY satisfied
   whenever both sides are exactly zero (``0 >= 0``) -- which would make
   COPY-TRAP fire on nearly every no-effect run. That cannot be the
   intended reading: INERT is a separate, explicitly named branch in the
   SAME rule set for exactly the no-effect case, and a rule that makes
   COPY-TRAP win nearly every tie against INERT would make INERT close to
   unreachable. This module therefore requires the reference quantity each
   disjunct is fundamentally ABOUT to be strictly POSITIVE before the
   disjunct can fire: clause 1 requires A1' gain > 0 (there must be a real
   improvement for A4 to be suspiciously matching) before comparing A4's
   gain to half of it; clause 2 requires induced_substitution_count > 0
   (there must be at least one actual induced substitution) before
   comparing it to the entity TP gain. Both are documented, reviewable,
   MECHANICAL additions -- never a silent pass-through of the bare ">="
   that would make the branch rule set internally incoherent. See
   :func:`_copy_trap_clauses`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from ..reproduction.slurp_scoring import SlotEntity, SluScore, parse_slu_response, score_slu
from ..rails.probes.pslu_flight import (
    PSLU_ARMS,
    PSLU_PHASE1_ARM,
    PsluFlightError,
    PsluRosters,
    PsluSampleManifest,
    load_pslu_rosters,
    load_pslu_sample_manifest,
    pslu_supply_packet,
)

REPORT_SCHEMA = "saea-pslu-read-v1"
RUNTIME_PROHIBITED_NOTE = "gold-derived; scoring-side only; must never enter a runtime path"

# Arms with a supply packet ("glossary arms"); A0 is the zero-supply baseline.
GLOSSARY_ARMS: tuple[str, ...] = tuple(arm for arm in PSLU_ARMS if arm != PSLU_PHASE1_ARM)
# A1/A4 select their roster by the sample's GOLD scenario (ceiling companion,
# control); A1'/A2/A3 select by the phase-1 PREDICTED scenario (self-supplied,
# deployment-legal) -- module docstring / rails.probes.pslu_flight docstring.
GOLD_SCOPED_ARMS: tuple[str, ...] = ("A1", "A4")
PREDICTED_SCOPED_ARMS: tuple[str, ...] = ("A1p", "A2", "A3")

SILENCE_SWAP_ARM = "A1p"
EXPECTED_SILENCE_SWAP_COUNT = 3

# docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md section 4,
# quoted verbatim in each clause's own detail text below.
SUPPLY_CONVERTS_MIN_GAIN = 0.05
SUPPLY_CONVERTS_A4_MAX_GAIN = 0.01
SUPPLY_CONVERTS_A1P_COPY_RATE_CEILING = 0.50  # strictly <
COPY_TRAP_A4_HALF_FACTOR = 0.5
COPY_TRAP_A1P_COPY_RATE_FLOOR = 0.50  # >=
INERT_MAX_GAIN = 0.02  # "no arm gains >= +0.02" -> INERT iff max gain < this
INTENT_DRIFT_GUARDRAIL_FLOOR = -0.05  # -5pp

ClauseVerdict = Literal["met", "not_met"]


class PsluReadError(RuntimeError):
    """Malformed attempt-dir/binding input, or gold metadata cannot be
    resolved for a sample the manifest names -- never raised for a
    legitimate VOID-worthy data shape (those are reported as clause
    results, not exceptions)."""


# ---------------------------------------------------------------------------
# Loading: outputs.jsonl / predicted-scenarios.json / flight-receipt.json.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutputRow:
    arm: str
    sample_id: str
    silence_swapped: bool
    phase1_scenario_parsed: bool | None
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: Mapping[str, object]

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "OutputRow":
        return cls(
            arm=str(document["arm"]),
            sample_id=str(document["sample_id"]),
            silence_swapped=bool(document["silence_swapped"]),
            phase1_scenario_parsed=document.get("phase1_scenario_parsed"),
            messages=tuple(document["messages"]),
            response_text=str(document["response_text"]),
            metrics=document["metrics"],
            consumption=document["consumption"],
        )


def load_attempt_rows(attempt_dir: Path) -> tuple[OutputRow, ...]:
    path = Path(attempt_dir) / "outputs.jsonl"
    if not path.is_file():
        raise PsluReadError(f"no outputs.jsonl under attempt dir {attempt_dir}")
    rows: list[OutputRow] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise PsluReadError(f"{path} line {line_no}: invalid JSON: {error}") from error
        rows.append(OutputRow.from_json(document))
    if not rows:
        raise PsluReadError(f"{path}: zero rows")
    return tuple(rows)


def load_predicted_scenarios(attempt_dir: Path) -> Mapping[str, str | None]:
    path = Path(attempt_dir) / "predicted-scenarios.json"
    if not path.is_file():
        raise PsluReadError(f"no predicted-scenarios.json under attempt dir {attempt_dir}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_flight_status(attempt_dir: Path) -> tuple[str | None, str | None]:
    """``(status, error)`` from ``flight-receipt.json``; ``(None, <reason>)``
    when the receipt is missing entirely (itself a harness defect: the
    launcher writes this file unconditionally once it starts, whether the
    flight completes or aborts)."""

    path = Path(attempt_dir) / "flight-receipt.json"
    if not path.is_file():
        return None, "flight-receipt.json missing"
    document = json.loads(path.read_text(encoding="utf-8"))
    return document.get("status"), document.get("error")


def load_gold_by_sample_id(
    lock: Mapping[str, object], root: Path, sample_ids: Sequence[str]
) -> dict[str, object]:
    """RUNTIME_PROHIBITED: gold scenario/action/entities, scoring-side only
    (module docstring / repo convention, ``scripts/build_entity_inventory.py``'s
    own ``RUNTIME_PROHIBITED_NOTE``). Reads the ``devel`` split only (this
    probe's own discovery surface; no ``allow_heldout``/``allow_synthetic``
    is ever passed) and indexes by ``sample_id``."""

    from ..data.slurp import load_slurp_split

    records = load_slurp_split(lock, root, "devel")
    by_id = {record.sample_id: record for record in records}
    missing = [sample_id for sample_id in sample_ids if sample_id not in by_id]
    if missing:
        raise PsluReadError(
            f"gold devel metadata missing {len(missing)} sample id(s) the manifest names: "
            f"{missing[:5]}{'...' if len(missing) > 5 else ''}"
        )
    return by_id


# ---------------------------------------------------------------------------
# Per-row analysis: recompute score_slu, cross-check the embedded metrics,
# reconstruct the expected roster packet, count induced substitutions.
# ---------------------------------------------------------------------------

_RECHECK_NUMERIC_FIELDS: tuple[str, ...] = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_tp",
    "slot_f1_exact_fp",
    "slot_f1_exact_fn",
    "slu_f1_word_tp",
    "slu_f1_word_fp",
    "slu_f1_word_fn",
    "slu_f1_char_tp",
    "slu_f1_char_fp",
    "slu_f1_char_fn",
)


@dataclass(frozen=True)
class RecheckMismatch:
    arm: str
    sample_id: str
    field: str
    embedded: object
    recomputed: object


def _numbers_match(a: object, b: object) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-9  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return a == b


def _recheck_row(row: OutputRow, recomputed: SluScore, parsed: bool) -> tuple[RecheckMismatch, ...]:
    """VOID clause 3 (module docstring): recompute this row's score_slu
    ingredients from the SAME response_text + gold this module itself
    loaded, and diff them against the metrics the flight already embedded
    (``rails.adapters.slurp.SlurpAdapter.score``'s own output) -- a real
    reproduction check, never a re-trust of the embedded field."""

    recomputed_dict = recomputed.as_metrics_dict()
    mismatches = [
        RecheckMismatch(row.arm, row.sample_id, field, row.metrics.get(field), recomputed_dict[field])
        for field in _RECHECK_NUMERIC_FIELDS
        if not _numbers_match(row.metrics.get(field), recomputed_dict[field])
    ]
    if row.metrics.get("parsed") != parsed:
        mismatches.append(RecheckMismatch(row.arm, row.sample_id, "parsed", row.metrics.get("parsed"), parsed))
    return tuple(mismatches)


def _roster_values_for_packet(packet) -> tuple[str, ...]:
    """Note 1: the VALUE half of every ``"{type}={value}"`` item a
    reconstructed :class:`~speech_aware_evidence_acquisition.rails.supply.SupplyPacket`
    carries -- ``None`` (excluded) for a bare-type item (A2's own shape),
    which therefore never contributes a roster VALUE at all."""

    from ..core.retrieval import normalize_term

    if packet is None:
        return ()
    values: set[str] = set()
    for item in packet.items:
        if "=" not in item.text:
            continue
        _type, _sep, value = item.text.partition("=")
        values.add(normalize_term(value))
    return tuple(sorted(values))


@dataclass(frozen=True)
class RosterReconciliation:
    arm: str
    sample_id: str
    scenario_used: str | None
    expected_prompt_block: str
    actual_prompt_block: str
    matches: bool
    roster_values: tuple[str, ...]


def _row_prompt_text(row: OutputRow) -> str:
    """The text content block a phase-2 row's own ``assemble_prompt`` call
    prepended before the audio part (``rails.adapters.slurp.SlurpAdapter.
    assemble_prompt``); ``""`` for a row that carries none (A0, or a
    malformed row -- reported as a harness defect via the mismatch this
    produces against a reconstructed non-empty expectation)."""

    if len(row.messages) < 2:
        return ""
    content = row.messages[1].get("content")
    if not isinstance(content, Sequence) or not content:
        return ""
    first = content[0]
    if not isinstance(first, Mapping) or first.get("type") != "text":
        return ""
    return str(first.get("text", ""))


def reconcile_roster(
    row: OutputRow,
    *,
    gold_scenario_by_sample: Mapping[str, str],
    predicted_scenario_by_sample: Mapping[str, str | None],
    rosters: PsluRosters,
) -> RosterReconciliation:
    """Module docstring note 8: rebuilds the EXACT packet the frozen
    :func:`pslu_supply_packet` would produce for this row's own (arm,
    scenario) and compares its ``prompt_block`` against what the row
    actually carries -- never a second, drifting reconstruction."""

    scenario = (
        gold_scenario_by_sample.get(row.sample_id)
        if row.arm in GOLD_SCOPED_ARMS
        else predicted_scenario_by_sample.get(row.sample_id)
    )
    try:
        expected_packet = pslu_supply_packet(row.arm, scenario=scenario, rosters=rosters)
    except PsluFlightError as error:
        raise PsluReadError(f"arm {row.arm!r} sample {row.sample_id!r}: cannot reconstruct roster: {error}") from error
    expected_text = expected_packet.prompt_block if expected_packet is not None else ""
    actual_text = _row_prompt_text(row)
    return RosterReconciliation(
        arm=row.arm,
        sample_id=row.sample_id,
        scenario_used=scenario,
        expected_prompt_block=expected_text,
        actual_prompt_block=actual_text,
        matches=(expected_text == actual_text),
        roster_values=_roster_values_for_packet(expected_packet),
    )


def count_induced_substitutions(
    predicted_entities: Sequence[SlotEntity],
    gold_entities: Sequence[SlotEntity],
    roster_values: Sequence[str],
) -> int:
    """Module docstring notes 1-3, prereg section 2 verbatim: "supplied
    roster tokens appearing as slot fillers where the aligned reference is
    a non-roster word counts as induced substitution." Reuses the frozen
    scorer's OWN greedy same-type nearest-word-distance alignment
    (``reproduction.slurp_scoring._lowest_distance``/``_word_distance``) --
    the exact algorithm ``_distance_based_counts`` already runs to compute
    the official ``slu_f1_word`` TP ingredient -- never a new alignment."""

    from ..core.retrieval import normalize_term
    from ..reproduction.slurp_scoring import _lowest_distance, _word_distance

    roster_set = set(roster_values)
    if not roster_set:
        return 0
    remaining_types = [entity.type for entity in gold_entities]
    remaining_fillers = [entity.filler for entity in gold_entities]
    count = 0
    for entity in predicted_entities:
        if entity.type not in remaining_types:
            continue
        index, _distance = _lowest_distance(entity, remaining_types, remaining_fillers, _word_distance)
        aligned_filler = normalize_term(remaining_fillers[index])
        predicted_filler = normalize_term(entity.filler)
        del remaining_types[index]
        del remaining_fillers[index]
        if predicted_filler in roster_set and aligned_filler not in roster_set:
            count += 1
    return count


@dataclass(frozen=True)
class RowAnalysis:
    row: OutputRow
    predicted_scenario: str | None
    predicted_action: str | None
    predicted_entities: tuple[SlotEntity, ...]
    parsed: bool
    recomputed_score: SluScore
    recheck_mismatches: tuple[RecheckMismatch, ...]
    roster_reconciliation: RosterReconciliation | None
    induced_substitutions: int


def analyze_row(
    row: OutputRow,
    gold,
    *,
    gold_scenario_by_sample: Mapping[str, str],
    predicted_scenario_by_sample: Mapping[str, str | None],
    rosters: PsluRosters,
) -> RowAnalysis:
    predicted_scenario, predicted_action, predicted_entities, parsed = parse_slu_response(row.response_text)
    predicted_entities = tuple(predicted_entities)
    recomputed = score_slu(
        gold_scenario=gold.scenario,
        gold_action=gold.action,
        gold_entities=gold.entities,
        predicted_scenario=predicted_scenario,
        predicted_action=predicted_action,
        predicted_entities=predicted_entities,
    )
    mismatches = _recheck_row(row, recomputed, parsed)

    reconciliation: RosterReconciliation | None = None
    induced = 0
    if row.arm != PSLU_PHASE1_ARM:
        reconciliation = reconcile_roster(
            row,
            gold_scenario_by_sample=gold_scenario_by_sample,
            predicted_scenario_by_sample=predicted_scenario_by_sample,
            rosters=rosters,
        )
        induced = count_induced_substitutions(predicted_entities, gold.entities, reconciliation.roster_values)

    return RowAnalysis(
        row=row,
        predicted_scenario=predicted_scenario,
        predicted_action=predicted_action,
        predicted_entities=predicted_entities,
        parsed=parsed,
        recomputed_score=recomputed,
        recheck_mismatches=mismatches,
        roster_reconciliation=reconciliation,
        induced_substitutions=induced,
    )


# ---------------------------------------------------------------------------
# copy-rate (module docstring note 4): micro aggregate over the embedded
# rails.consumption.ConsumptionTrace records, never re-derived.
# ---------------------------------------------------------------------------


def arm_copy_rate(rows: Sequence[OutputRow]) -> tuple[float, int, int]:
    """``(rate, copy_records, total_records)`` -- 0.0 when nothing was ever
    supplied to copy (A0, or an arm with zero rows), never a bare
    ZeroDivisionError, mirroring ``analysis.p2_reads.CopyCountResult.
    copy_rate``'s own guard convention."""

    copy_records = 0
    total_records = 0
    for row in rows:
        for record in row.consumption.get("records", []):
            total_records += 1
            if record.get("outcome") == "copy":
                copy_records += 1
    rate = copy_records / total_records if total_records else 0.0
    return rate, copy_records, total_records


# ---------------------------------------------------------------------------
# silence-swap comparison (module docstring note 7).
# ---------------------------------------------------------------------------


def _parsed_answer_signature(response_text: str) -> tuple[str | None, str | None, tuple[tuple[str, str], ...]]:
    scenario, action, entities, _parsed = parse_slu_response(response_text)
    return scenario, action, tuple(sorted((entity.type, entity.filler) for entity in entities))


@dataclass(frozen=True)
class SilenceSwapComparison:
    sample_id: str
    real_response_text: str
    silence_response_text: str
    real_signature: tuple[str | None, str | None, tuple[tuple[str, str], ...]]
    silence_signature: tuple[str | None, str | None, tuple[tuple[str, str], ...]]
    unchanged: bool
    has_real_counterpart: bool


def compare_silence_swap(rows: Sequence[OutputRow]) -> tuple[SilenceSwapComparison, ...]:
    real_by_sample: dict[str, OutputRow] = {}
    silence_by_sample: dict[str, OutputRow] = {}
    for row in rows:
        if row.arm != SILENCE_SWAP_ARM:
            continue
        if row.silence_swapped:
            silence_by_sample[row.sample_id] = row
        else:
            real_by_sample[row.sample_id] = row

    comparisons: list[SilenceSwapComparison] = []
    for sample_id, silence_row in sorted(silence_by_sample.items()):
        real_row = real_by_sample.get(sample_id)
        has_real = real_row is not None
        real_text = real_row.response_text if real_row is not None else ""
        real_sig = _parsed_answer_signature(real_text) if real_row is not None else (None, None, ())
        silence_sig = _parsed_answer_signature(silence_row.response_text)
        comparisons.append(
            SilenceSwapComparison(
                sample_id=sample_id,
                real_response_text=real_text,
                silence_response_text=silence_row.response_text,
                real_signature=real_sig,
                silence_signature=silence_sig,
                unchanged=has_real and real_sig == silence_sig,
                has_real_counterpart=has_real,
            )
        )
    return tuple(comparisons)


# ---------------------------------------------------------------------------
# Per-arm aggregate.
# ---------------------------------------------------------------------------


def _aggregate_slu_score(scores: Sequence[SluScore]) -> SluScore:
    """Sums ingredient fields across samples (module docstring: the
    official corpus-level micro-averaging convention,
    ``reproduction.slurp_scoring`` module docstring) and reuses
    :class:`SluScore`'s own ``.slu_f1``/``.slot_f1_exact`` properties
    (each calling the frozen ``_prf``) unmodified. An empty ``scores``
    sequence yields an all-zero ``SluScore`` (``_prf(0, 0, 0)`` is already
    defined as ``(0.0, 0.0, 0.0)``) -- never a crash; the missing samples
    are reported separately as a harness defect."""

    return SluScore(
        scenario_action_exact=sum(s.scenario_action_exact for s in scores),
        scenario_exact=sum(s.scenario_exact for s in scores),
        action_exact=sum(s.action_exact for s in scores),
        slot_f1_exact_tp=sum(s.slot_f1_exact_tp for s in scores),
        slot_f1_exact_fp=sum(s.slot_f1_exact_fp for s in scores),
        slot_f1_exact_fn=sum(s.slot_f1_exact_fn for s in scores),
        slu_f1_word_tp=sum(s.slu_f1_word_tp for s in scores),
        slu_f1_word_fp=sum(s.slu_f1_word_fp for s in scores),
        slu_f1_word_fn=sum(s.slu_f1_word_fn for s in scores),
        slu_f1_char_tp=sum(s.slu_f1_char_tp for s in scores),
        slu_f1_char_fp=sum(s.slu_f1_char_fp for s in scores),
        slu_f1_char_fn=sum(s.slu_f1_char_fn for s in scores),
    )


@dataclass(frozen=True)
class ArmAggregate:
    arm: str
    n_samples: int
    aggregate_score: SluScore
    slu_f1_precision: float
    slu_f1_recall: float
    slu_f1_f1: float
    slot_f1_exact_precision: float
    slot_f1_exact_recall: float
    slot_f1_exact_f1: float
    slot_f1_exact_tp_sum: float
    intent_accuracy: float
    copy_rate: float
    copy_records: int
    copy_records_total: int
    induced_substitution_count: int


def build_arm_aggregate(arm: str, analyses: Sequence[RowAnalysis]) -> ArmAggregate:
    scores = [analysis.recomputed_score for analysis in analyses]
    aggregate_score = _aggregate_slu_score(scores)
    slu_p, slu_r, slu_f1 = aggregate_score.slu_f1
    slot_p, slot_r, slot_f1 = aggregate_score.slot_f1_exact
    n = len(analyses)
    intent_accuracy = (aggregate_score.scenario_action_exact / n) if n else 0.0
    copy_rate, copy_records, copy_total = arm_copy_rate([a.row for a in analyses])
    induced = sum(a.induced_substitutions for a in analyses)
    return ArmAggregate(
        arm=arm,
        n_samples=n,
        aggregate_score=aggregate_score,
        slu_f1_precision=slu_p,
        slu_f1_recall=slu_r,
        slu_f1_f1=slu_f1,
        slot_f1_exact_precision=slot_p,
        slot_f1_exact_recall=slot_r,
        slot_f1_exact_f1=slot_f1,
        slot_f1_exact_tp_sum=aggregate_score.slot_f1_exact_tp,
        intent_accuracy=intent_accuracy,
        copy_rate=copy_rate,
        copy_records=copy_records,
        copy_records_total=copy_total,
        induced_substitution_count=induced,
    )


# ---------------------------------------------------------------------------
# Structural / harness-defect checks.
# ---------------------------------------------------------------------------


def _harness_defect_reasons(
    *,
    flight_status: str | None,
    flight_error: str | None,
    rows_by_arm: Mapping[str, Sequence[OutputRow]],
    silence_rows: Sequence[OutputRow],
    sample_ids: Sequence[str],
    unknown_arm_rows: Sequence[OutputRow],
    duplicate_keys: Sequence[tuple[str, str, bool]],
    roster_reconciliations: Sequence[RosterReconciliation],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if flight_status != "COMPLETED":
        reasons.append(f"flight-receipt status={flight_status!r} (expected 'COMPLETED'); error={flight_error!r}")
    for row in unknown_arm_rows:
        reasons.append(f"unknown arm {row.arm!r} on sample {row.sample_id!r}")
    for key in duplicate_keys:
        reasons.append(f"duplicate row for (arm, sample_id, silence_swapped)={key}")
    id_set = set(sample_ids)
    for arm, rows in rows_by_arm.items():
        got = {row.sample_id for row in rows}
        missing = id_set - got
        extra = got - id_set
        if missing:
            reasons.append(f"arm {arm}: missing {len(missing)} sample(s) from the frozen manifest: {sorted(missing)[:5]}")
        if extra:
            reasons.append(f"arm {arm}: {len(extra)} sample(s) not in the frozen manifest: {sorted(extra)[:5]}")
        duplicate_ids = len(rows) - len({row.sample_id for row in rows})
        if duplicate_ids > 0:
            reasons.append(f"arm {arm}: {duplicate_ids} duplicate sample_id row(s)")
    if len(silence_rows) != EXPECTED_SILENCE_SWAP_COUNT:
        reasons.append(f"expected exactly {EXPECTED_SILENCE_SWAP_COUNT} silence-swap rows, found {len(silence_rows)}")
    for row in silence_rows:
        if row.arm != SILENCE_SWAP_ARM:
            reasons.append(f"silence-swap row on sample {row.sample_id!r} is on arm {row.arm!r}, expected {SILENCE_SWAP_ARM!r}")
    for reconciliation in roster_reconciliations:
        if not reconciliation.matches:
            reasons.append(
                f"arm {reconciliation.arm} sample {reconciliation.sample_id}: supplied prompt text does not "
                "match the reconstructed roster table (roster-reconstruction mismatch)"
            )
    return tuple(reasons)


# ---------------------------------------------------------------------------
# Mechanical branch-rule evaluator (prereg section 4, quoted verbatim below).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClauseResult:
    clause_text: str
    verdict: ClauseVerdict
    detail: str


@dataclass(frozen=True)
class BranchVerdict:
    void_clauses: tuple[ClauseResult, ...]
    voided: bool
    copy_trap_clauses: tuple[ClauseResult, ...]
    copy_trap: bool
    supply_converts_clauses: tuple[ClauseResult, ...]
    supply_converts: bool
    dose_confirm: ClauseResult
    inert: bool
    inert_detail: str
    intent_drift_flags: tuple[str, ...]
    overall: str


def _void_clause_recheck(mismatches: Sequence[RecheckMismatch]) -> ClauseResult:
    clause_text = "per-sample TP/FP/FN fail to reproduce the adapter's committed scorer on recheck"
    if mismatches:
        shown = "; ".join(
            f"{m.arm}/{m.sample_id}.{m.field}: embedded={m.embedded!r} recomputed={m.recomputed!r}"
            for m in mismatches[:10]
        )
        more = f" (+{len(mismatches) - 10} more)" if len(mismatches) > 10 else ""
        return ClauseResult(clause_text, "met", f"{len(mismatches)} mismatch(es): {shown}{more}")
    return ClauseResult(clause_text, "not_met", "every row's recomputed TP/FP/FN/parsed matched its embedded metrics exactly")


def _void_clause_harness_defect(reasons: Sequence[str]) -> ClauseResult:
    clause_text = "harness defect"
    if reasons:
        return ClauseResult(clause_text, "met", "; ".join(reasons))
    return ClauseResult(clause_text, "not_met", "no structural harness defects detected")


def _void_clause_silence_swap(comparisons: Sequence[SilenceSwapComparison]) -> ClauseResult:
    clause_text = "silence-swap answers persist unchanged"
    if not comparisons:
        return ClauseResult(
            clause_text, "not_met",
            "no silence-swap rows found to compare (a missing-row shape is reported separately under harness defect)",
        )
    detail = "; ".join(
        f"{c.sample_id}: unchanged={c.unchanged}" + ("" if c.has_real_counterpart else " (no real-audio counterpart)")
        for c in comparisons
    )
    unanimous = all(c.unchanged for c in comparisons)
    resolution = (
        f"module docstring note 7: VOID iff ALL {len(comparisons)} silence-swap sample(s) are unchanged "
        f"(documented ambiguity resolution -- the prereg names no quantifier)"
    )
    return ClauseResult(clause_text, "met" if unanimous else "not_met", f"{resolution}; {detail}")


def _copy_trap_clauses(
    gains: Mapping[str, float],
    entity_tp_gains: Mapping[str, float],
    aggregates: Mapping[str, ArmAggregate],
) -> tuple[ClauseResult, ClauseResult, ClauseResult]:
    a1p_gain = gains.get("A1p", 0.0)
    a4_gain = gains.get("A4", 0.0)
    a4_half_fires = a1p_gain > 0.0 and a4_gain >= COPY_TRAP_A4_HALF_FACTOR * a1p_gain
    clause_a4_half = ClauseResult(
        "A4 gain >= half of A1' gain",
        "met" if a4_half_fires else "not_met",
        f"module docstring note 9 (requires A1' gain > 0 -- a bare >= is vacuous at 0 vs 0): "
        f"A1' gain={a1p_gain:+.4f}, A4 gain={a4_gain:+.4f}, "
        f"threshold={COPY_TRAP_A4_HALF_FACTOR * a1p_gain:+.4f} (half of A1' gain)",
    )
    induced_hits = [
        arm for arm in GLOSSARY_ARMS
        if aggregates[arm].induced_substitution_count > 0
        and aggregates[arm].induced_substitution_count >= entity_tp_gains.get(arm, 0.0)
    ]
    clause_induced = ClauseResult(
        "any glossary-arm induced-substitution count >= its entity true-positive gain",
        "met" if induced_hits else "not_met",
        "module docstring notes 6+9 (entity TP = summed slot_f1_exact_tp; requires induced count > 0 -- "
        "a bare >= is vacuous at 0 vs 0): "
        + "; ".join(
            f"{arm}: induced={aggregates[arm].induced_substitution_count}, "
            f"entity_tp_gain={entity_tp_gains.get(arm, 0.0):+.2f}"
            for arm in GLOSSARY_ARMS
        ),
    )
    a1p_copy_rate = aggregates["A1p"].copy_rate
    clause_copy_rate = ClauseResult(
        "copy-rate >= 50%",
        "met" if a1p_copy_rate >= COPY_TRAP_A1P_COPY_RATE_FLOOR else "not_met",
        f"module docstring note 5 (A1' copy-rate specifically): A1' copy_rate={a1p_copy_rate:.4f} "
        f"({aggregates['A1p'].copy_records}/{aggregates['A1p'].copy_records_total}), "
        f"floor={COPY_TRAP_A1P_COPY_RATE_FLOOR:.2f}",
    )
    return clause_a4_half, clause_induced, clause_copy_rate


def _supply_converts_clauses(
    gains: Mapping[str, float], aggregates: Mapping[str, ArmAggregate]
) -> tuple[ClauseResult, ClauseResult, ClauseResult]:
    a1p_gain = gains.get("A1p", 0.0)
    a4_gain = gains.get("A4", 0.0)
    a1p_copy_rate = aggregates["A1p"].copy_rate
    clause_gain = ClauseResult(
        "A1' SLU-F1 gain >= +0.05 absolute over A0",
        "met" if a1p_gain >= SUPPLY_CONVERTS_MIN_GAIN else "not_met",
        f"A1' gain={a1p_gain:+.4f}, floor={SUPPLY_CONVERTS_MIN_GAIN:.2f}",
    )
    clause_a4 = ClauseResult(
        "A4 gain <= +0.01",
        "met" if a4_gain <= SUPPLY_CONVERTS_A4_MAX_GAIN else "not_met",
        f"A4 gain={a4_gain:+.4f}, ceiling={SUPPLY_CONVERTS_A4_MAX_GAIN:.2f}",
    )
    clause_copy = ClauseResult(
        "A1' copy-rate < 50%",
        "met" if a1p_copy_rate < SUPPLY_CONVERTS_A1P_COPY_RATE_CEILING else "not_met",
        f"A1' copy_rate={a1p_copy_rate:.4f} ({aggregates['A1p'].copy_records}/{aggregates['A1p'].copy_records_total}), "
        f"ceiling={SUPPLY_CONVERTS_A1P_COPY_RATE_CEILING:.2f}",
    )
    return clause_gain, clause_a4, clause_copy


def evaluate_branch_rules(
    *,
    recheck_mismatches: Sequence[RecheckMismatch],
    harness_defect_reasons: Sequence[str],
    silence_comparisons: Sequence[SilenceSwapComparison],
    aggregates: Mapping[str, ArmAggregate],
) -> BranchVerdict:
    """The mechanical evaluator, checked in the registered order: VOID
    first, then COPY-TRAP, then SUPPLY-CONVERTS, then DOSE-CONFIRM
    (secondary/descriptive -- reported alongside whichever primary branch
    fired, never itself competing for ``overall``), then INERT."""

    a0 = aggregates[PSLU_PHASE1_ARM]
    gains = {arm: aggregates[arm].slu_f1_f1 - a0.slu_f1_f1 for arm in GLOSSARY_ARMS}
    entity_tp_gains = {arm: aggregates[arm].slot_f1_exact_tp_sum - a0.slot_f1_exact_tp_sum for arm in GLOSSARY_ARMS}

    void_recheck = _void_clause_recheck(recheck_mismatches)
    void_harness = _void_clause_harness_defect(harness_defect_reasons)
    void_silence = _void_clause_silence_swap(silence_comparisons)
    void_clauses = (void_silence, void_harness, void_recheck)
    voided = any(c.verdict == "met" for c in void_clauses)

    copy_trap_clauses = _copy_trap_clauses(gains, entity_tp_gains, aggregates)
    copy_trap = (not voided) and any(c.verdict == "met" for c in copy_trap_clauses)

    supply_converts_clauses = _supply_converts_clauses(gains, aggregates)
    supply_converts = (
        (not voided) and (not copy_trap) and all(c.verdict == "met" for c in supply_converts_clauses)
    )

    a3_f1 = aggregates["A3"].slu_f1_f1
    a2_f1 = aggregates["A2"].slu_f1_f1
    dose_confirm = ClauseResult(
        "A3 underperforms A2 (secondary, descriptive)",
        "met" if a3_f1 < a2_f1 else "not_met",
        f"A3 slu_f1={a3_f1:.4f}, A2 slu_f1={a2_f1:.4f}",
    )

    max_gain = max(gains.values()) if gains else float("-inf")
    inert = (not voided) and (not copy_trap) and (not supply_converts) and max_gain < INERT_MAX_GAIN
    inert_detail = (
        "no arm gains >= +0.02 SLU-F1 over A0: "
        + "; ".join(f"{arm}={gains[arm]:+.4f}" for arm in GLOSSARY_ARMS)
    )

    intent_accuracy_a0 = a0.intent_accuracy
    intent_drift_flags = tuple(
        f"{arm}: drift={aggregates[arm].intent_accuracy - intent_accuracy_a0:+.4f}"
        for arm in GLOSSARY_ARMS
        if (aggregates[arm].intent_accuracy - intent_accuracy_a0) < INTENT_DRIFT_GUARDRAIL_FLOOR
    )

    if voided:
        overall = "VOID"
    elif copy_trap:
        overall = "COPY-TRAP"
    elif supply_converts:
        overall = "SUPPLY-CONVERTS"
    elif inert:
        overall = "INERT"
    else:
        overall = "UNRESOLVED (no branch rule fired mechanically)"
    if dose_confirm.verdict == "met":
        overall += " + DOSE-CONFIRM (secondary, descriptive)"

    return BranchVerdict(
        void_clauses=void_clauses,
        voided=voided,
        copy_trap_clauses=copy_trap_clauses,
        copy_trap=copy_trap,
        supply_converts_clauses=supply_converts_clauses,
        supply_converts=supply_converts,
        dose_confirm=dose_confirm,
        inert=inert,
        inert_detail=inert_detail,
        intent_drift_flags=intent_drift_flags,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PsluReadReport:
    attempt_dir: Path
    flight_status: str | None
    flight_error: str | None
    analyses_by_arm: Mapping[str, tuple[RowAnalysis, ...]]
    aggregates: Mapping[str, ArmAggregate]
    silence_comparisons: tuple[SilenceSwapComparison, ...]
    recheck_mismatches: tuple[RecheckMismatch, ...]
    harness_defect_reasons: tuple[str, ...]
    branch_verdict: BranchVerdict


def build_pslu_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    sample_manifest_path: Path,
    roster_table_path: Path,
) -> PsluReadReport:
    attempt_dir = Path(attempt_dir)
    rows = load_attempt_rows(attempt_dir)
    predicted_scenarios = load_predicted_scenarios(attempt_dir)
    flight_status, flight_error = load_flight_status(attempt_dir)

    manifest: PsluSampleManifest = load_pslu_sample_manifest(sample_manifest_path)
    rosters: PsluRosters = load_pslu_rosters(roster_table_path)
    sample_ids = manifest.sample_ids

    gold_by_id = load_gold_by_sample_id(lock, root, sample_ids)  # RUNTIME_PROHIBITED
    gold_scenario_by_id = {sample_id: record.scenario for sample_id, record in gold_by_id.items()}

    rows_by_arm: dict[str, list[OutputRow]] = {arm: [] for arm in PSLU_ARMS}
    silence_rows: list[OutputRow] = []
    unknown_arm_rows: list[OutputRow] = []
    seen_keys: set[tuple[str, str, bool]] = set()
    duplicate_keys: list[tuple[str, str, bool]] = []
    for row in rows:
        key = (row.arm, row.sample_id, row.silence_swapped)
        if key in seen_keys:
            duplicate_keys.append(key)
            continue
        seen_keys.add(key)
        if row.arm not in PSLU_ARMS:
            unknown_arm_rows.append(row)
            continue
        if row.silence_swapped:
            silence_rows.append(row)
        else:
            rows_by_arm[row.arm].append(row)

    analyses_by_arm: dict[str, tuple[RowAnalysis, ...]] = {}
    recheck_mismatches: list[RecheckMismatch] = []
    roster_reconciliations: list[RosterReconciliation] = []
    for arm in PSLU_ARMS:
        analyses: list[RowAnalysis] = []
        for row in rows_by_arm[arm]:
            gold = gold_by_id.get(row.sample_id)
            if gold is None:
                continue  # already reported as a missing-manifest-id harness defect below
            analysis = analyze_row(
                row,
                gold,
                gold_scenario_by_sample=gold_scenario_by_id,
                predicted_scenario_by_sample=predicted_scenarios,
                rosters=rosters,
            )
            analyses.append(analysis)
            recheck_mismatches.extend(analysis.recheck_mismatches)
            if analysis.roster_reconciliation is not None:
                roster_reconciliations.append(analysis.roster_reconciliation)
        analyses_by_arm[arm] = tuple(analyses)

    for row in silence_rows:
        gold = gold_by_id.get(row.sample_id)
        if gold is None:
            continue
        _predicted_scenario, _predicted_action, predicted_entities, parsed = parse_slu_response(row.response_text)
        recomputed = score_slu(
            gold_scenario=gold.scenario,
            gold_action=gold.action,
            gold_entities=gold.entities,
            predicted_scenario=_predicted_scenario,
            predicted_action=_predicted_action,
            predicted_entities=tuple(predicted_entities),
        )
        recheck_mismatches.extend(_recheck_row(row, recomputed, parsed))

    aggregates = {arm: build_arm_aggregate(arm, analyses_by_arm[arm]) for arm in PSLU_ARMS}

    harness_defect_reasons = _harness_defect_reasons(
        flight_status=flight_status,
        flight_error=flight_error,
        rows_by_arm=rows_by_arm,
        silence_rows=silence_rows,
        sample_ids=sample_ids,
        unknown_arm_rows=unknown_arm_rows,
        duplicate_keys=duplicate_keys,
        roster_reconciliations=roster_reconciliations,
    )

    # compare_silence_swap needs BOTH sides -- the real-audio A1' rows (in
    # rows_by_arm[SILENCE_SWAP_ARM]) and the silence-swapped extras -- to
    # find each sample's own real-audio counterpart; passing silence_rows
    # alone would leave every comparison with no counterpart to compare.
    silence_comparisons = compare_silence_swap(list(rows_by_arm[SILENCE_SWAP_ARM]) + silence_rows)

    branch_verdict = evaluate_branch_rules(
        recheck_mismatches=recheck_mismatches,
        harness_defect_reasons=harness_defect_reasons,
        silence_comparisons=silence_comparisons,
        aggregates=aggregates,
    )

    return PsluReadReport(
        attempt_dir=attempt_dir,
        flight_status=flight_status,
        flight_error=flight_error,
        analyses_by_arm=analyses_by_arm,
        aggregates=aggregates,
        silence_comparisons=silence_comparisons,
        recheck_mismatches=tuple(recheck_mismatches),
        harness_defect_reasons=harness_defect_reasons,
        branch_verdict=branch_verdict,
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def _aggregate_json(aggregate: ArmAggregate) -> dict[str, object]:
    return {
        "arm": aggregate.arm,
        "n_samples": aggregate.n_samples,
        "slu_f1": {
            "precision": aggregate.slu_f1_precision,
            "recall": aggregate.slu_f1_recall,
            "f1": aggregate.slu_f1_f1,
        },
        "slot_f1_exact": {
            "precision": aggregate.slot_f1_exact_precision,
            "recall": aggregate.slot_f1_exact_recall,
            "f1": aggregate.slot_f1_exact_f1,
            "tp_sum": aggregate.slot_f1_exact_tp_sum,
        },
        "intent_accuracy": aggregate.intent_accuracy,
        "copy_rate": aggregate.copy_rate,
        "copy_records": aggregate.copy_records,
        "copy_records_total": aggregate.copy_records_total,
        "induced_substitution_count": aggregate.induced_substitution_count,
    }


def report_to_json(report: PsluReadReport) -> dict[str, object]:
    verdict = report.branch_verdict
    return {
        "runtime_prohibited": True,
        "note": RUNTIME_PROHIBITED_NOTE,
        "schema": REPORT_SCHEMA,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "flight_error": report.flight_error,
        "aggregates": {arm: _aggregate_json(agg) for arm, agg in report.aggregates.items()},
        "silence_swap": [
            {
                "sample_id": c.sample_id,
                "unchanged": c.unchanged,
                "has_real_counterpart": c.has_real_counterpart,
                "real_signature": list(c.real_signature[:2]) + [list(c.real_signature[2])],
                "silence_signature": list(c.silence_signature[:2]) + [list(c.silence_signature[2])],
            }
            for c in report.silence_comparisons
        ],
        "recheck_mismatch_count": len(report.recheck_mismatches),
        "harness_defect_reasons": list(report.harness_defect_reasons),
        "branch_verdict": {
            "void_clauses": [_clause_json(c) for c in verdict.void_clauses],
            "voided": verdict.voided,
            "copy_trap_clauses": [_clause_json(c) for c in verdict.copy_trap_clauses],
            "copy_trap": verdict.copy_trap,
            "supply_converts_clauses": [_clause_json(c) for c in verdict.supply_converts_clauses],
            "supply_converts": verdict.supply_converts,
            "dose_confirm": _clause_json(verdict.dose_confirm),
            "inert": verdict.inert,
            "inert_detail": verdict.inert_detail,
            "intent_drift_guardrail_flags": list(verdict.intent_drift_flags),
            "overall": verdict.overall,
        },
    }


def render_report(report: PsluReadReport) -> str:
    verdict = report.branch_verdict
    lines = [
        "P-SLU pinned offline read (docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md)",
        "=" * 70,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r} (error={report.flight_error!r})",
        "",
        "Per-arm aggregates",
    ]
    header = f"  {'arm':<6}{'n':>4}{'slu_f1':>9}{'slot_f1x':>10}{'intent_acc':>12}{'copy_rate':>11}{'induced':>9}"
    lines.append(header)
    for arm in PSLU_ARMS:
        agg = report.aggregates[arm]
        lines.append(
            f"  {arm:<6}{agg.n_samples:>4}{agg.slu_f1_f1:>9.4f}{agg.slot_f1_exact_f1:>10.4f}"
            f"{agg.intent_accuracy:>12.4f}{agg.copy_rate:>11.4f}{agg.induced_substitution_count:>9}"
        )
    lines.append("")

    lines.append("Silence-swap comparison (3 A1' silence variants vs their real-audio counterparts)")
    if not report.silence_comparisons:
        lines.append("  (none found)")
    for c in report.silence_comparisons:
        lines.append(f"  {c.sample_id}: unchanged={c.unchanged} has_real_counterpart={c.has_real_counterpart}")
    lines.append("")

    if report.harness_defect_reasons:
        lines.append("!" * 70)
        lines.append("HARNESS DEFECT REASONS")
        for reason in report.harness_defect_reasons:
            lines.append(f"  {reason}")
        lines.append("!" * 70)
        lines.append("")

    lines.append(f"recheck mismatches (TP/FP/FN vs adapter's committed scorer): {len(report.recheck_mismatches)}")
    lines.append("")

    lines.append(f"VOID (checked FIRST): {'MET' if verdict.voided else 'not met'}")
    for clause in verdict.void_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append("")

    lines.append(f"COPY-TRAP: {'MET' if verdict.copy_trap else 'not met'}")
    for clause in verdict.copy_trap_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append("")

    lines.append(f"SUPPLY-CONVERTS: {'MET' if verdict.supply_converts else 'not met'}")
    for clause in verdict.supply_converts_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append("")

    lines.append(f"DOSE-CONFIRM (secondary, descriptive): {verdict.dose_confirm.verdict.upper()}")
    lines.append(f"  {verdict.dose_confirm.detail}")
    lines.append("")

    lines.append(f"INERT: {'MET' if verdict.inert else 'not met'}")
    lines.append(f"  {verdict.inert_detail}")
    lines.append("")

    lines.append("intent-accuracy drift guardrail (-5pp)")
    if verdict.intent_drift_flags:
        for flag in verdict.intent_drift_flags:
            lines.append(f"  FLAGGED: {flag}")
    else:
        lines.append("  no arm drifted below -5pp intent accuracy vs A0")
    lines.append("")

    lines.append(f"OVERALL: {verdict.overall}")
    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pslu-read",
        description=(
            "P-SLU pinned offline read suite: official SLU-F1/slot_f1_exact, intent accuracy, "
            "copy-rate, induced-substitution count, silence-swap comparison, and the mechanical "
            "branch-rule evaluator. Model-free, read-only; never opens a model session."
        ),
    )
    parser.add_argument("attempt_dir", type=Path, help="the flight's own attempt directory (carries outputs.jsonl)")
    parser.add_argument("--output-dir", required=True, type=Path, help="directory to write verdict.json / report.txt")
    parser.add_argument(
        "--sample-manifest", type=Path, default=None,
        help="override the sample-manifest JSON path (default: configs/probes/g0-binding/pslu-sample-devel-n60.json)",
    )
    parser.add_argument(
        "--roster-table", type=Path, default=None,
        help="override the roster-table JSON path (default: configs/probes/g0-binding/pslu-rosters-train-only.json)",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="TEST-ONLY override of the study repo root used to resolve the umbrella lock and default configs",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT, write_json_artifact

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    sample_manifest_path = args.sample_manifest or (repo_root / "configs/probes/g0-binding/pslu-sample-devel-n60.json")
    roster_table_path = args.roster_table or (repo_root / "configs/probes/g0-binding/pslu-rosters-train-only.json")

    output_dir = Path(args.output_dir)
    verdict_path = output_dir / "verdict.json"
    if verdict_path.exists():
        print(
            f"REFUSED: {verdict_path} already exists -- this suite refuses to run twice against the same "
            "output dir (one-shot read discipline); choose a fresh --output-dir if a genuinely new read is "
            "intended",
            file=sys.stderr,
        )
        return 1

    lock = load_lock(umbrella_lock_path(repo_root))
    root = data_root()

    try:
        report = build_pslu_report(
            args.attempt_dir,
            lock,
            root,
            sample_manifest_path=sample_manifest_path,
            roster_table_path=roster_table_path,
        )
    except (PsluReadError, PsluFlightError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    document = report_to_json(report)
    write_json_artifact(verdict_path, document)
    rendered = render_report(report)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
