"""P-SLU Stage-2 follow-up flight orchestration -- REGISTERED probe
(SAEA-PROBE-pslu-s2-183, ``bounded-discovery-probe``):
``docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md``. Parent:
the consumed P-SLU read (``d8b71a5``, verdict UNRESOLVED,
``docs/readiness/2026-08-18-pslu-verdict.md``), whose own section 3/8/9
prescribe exactly these two arms.

Two arms over the SAME frozen 60-sample devel set the parent flight used
(``configs/probes/g0-binding/pslu-sample-devel-n60.json``, whose own
``split_identity_hash`` is
``fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5``):

- **F1** (format-matched filler control): one request per sample, a FIXED
  100-entry synthetic non-ontology roster
  (``rails.probes.pslu_s2_filler.generate_f1_filler_roster``) rendered
  byte-identically to A3's own ``"{type}={value}"`` shape (the SAME
  ``rails.probes.pslu_flight._roster_packet`` construction, arm="F1",
  never a re-implementation).
- **A1'r** (self-scoping re-fly, TWO-PHASE): phase 1 forces a CLOSED-SET
  scenario choice over the 18 canonical labels this flight derives from the
  SAME frozen, train-split-only, legality-checked roster table the parent
  flight already trusts (:func:`canonical_scenario_labels` ==
  ``sorted(rosters.scenario_rosters.keys())`` -- never devel gold, never a
  fresh ``data.slurp.load_slurp_ontology`` call). A deterministic parser
  (:func:`map_predicted_scenario_to_canonical`) resolves the closed-set
  response to one of those 18 labels, or records an A2-fallback -- the SAME
  never-gold-fallback discipline the parent's own A1p already applies
  (``rails.probes.pslu_flight`` module docstring: "NEVER to the gold
  scenario"). Phase 2 reuses the frozen
  ``rails.probes.pslu_flight.pslu_supply_packet("A1p", scenario=<the
  parsed label>, rosters=...)`` completely UNCHANGED -- this mission never
  edits that frozen function, and calling it with arm="A1p" (not a new arm
  string) is deliberate: it is the EXACT roster-selection code path the
  parent's own A1p used, the only thing that changed is the SOURCE of the
  ``scenario`` argument (a closed-set-constrained, deterministically-mapped
  choice, not an unconstrained free-form one).

3 seeded silence-swap requests re-fly A1'r's OWN phase-2 request ONLY (the
SAME 3 sample ids, seed, and selection rule as the parent's own
``silence_swap`` block, ``configs/probes/g0-binding/pslu-flight.json``) with
silenced audio -- never F1, and never A1'r's own phase-1 request (cost
accounting, this module's own docstring continued below: 60 + 60 + 60 + 3 ==
183, matching the registration's own "180 audio requests + 3 silence-swap =
183" exactly; silence-swapping both phases would cost 6 extra requests, not
3).

Same "never calls the ontology miner" guard the parent flight enforces,
reused verbatim (``rails.probes.pslu_flight.assert_never_calls_ontology_miner``,
checked again here at THIS module's own import time and again at the top of
:func:`run_pslu_s2_flight`) -- this module's rosters come ONLY from the SAME
frozen ``pslu-rosters-train-only.json`` table the parent flight already
loads via ``rails.probes.pslu_flight.load_pslu_rosters``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Mapping, Sequence

from ...reproduction.slurp_scoring import parse_slu_response
from ..adapters.slurp import SlurpAdapter, SlurpSample
from ..consumption import ConsumptionTrace
from ..supply import SupplyDose, SupplyForm, SupplyPacket
from .pslu_flight import (
    PsluFlightError,
    PsluRosters,
    _source_references_ontology_miner,
    _swap_audio_media_relpath,
    assert_never_calls_ontology_miner,
    pslu_supply_packet,
)
from .pslu_s2_filler import f1_filler_supply_packet

F1_ARM = "F1"
A1R_PHASE1_ARM = "A1r-phase1"
A1R_ARM = "A1r"
PSLU_S2_ARMS: tuple[str, ...] = (F1_ARM, A1R_PHASE1_ARM, A1R_ARM)

# This PROBE's own registered silence-swap count (configs/probes/g0-binding/
# pslu-s2-flight.json's own "silence_swap.count"). NOT enforced as a bare
# constant inside run_pslu_s2_flight/validate_pslu_s2_flight_summary below
# (those stay general over any caller-supplied silence_swap_media_relpaths
# size, e.g. this module's own small synthetic tests) -- it is enforced
# against a REAL attempt by analysis.pslu_s2_read's own harness-defect
# check, and can be passed explicitly as
# expected_silence_swap_sample_ids=<the 3 frozen ids> by a real flight
# launcher calling validate_pslu_s2_flight_summary directly.
EXPECTED_SILENCE_SWAP_COUNT = 3


def _assert_this_module_never_calls_ontology_miner(source: str | None = None) -> None:
    """This module's OWN ontology-miner guard. ``rails.probes.pslu_flight.
    assert_never_calls_ontology_miner``'s own default source resolves to
    ``pslu_flight.py``'s ``__file__`` (the module where it is DEFINED), not
    the caller's -- calling it from here only re-verifies the parent's own
    source has not been tampered with, it does NOT scan THIS file. This
    wrapper reuses the SAME pure ``_source_references_ontology_miner`` check
    (never a second implementation) against THIS module's own source text by
    default, so a future edit that adds a live reference to the forbidden
    ontology miner fails loud here too; ``source`` may be overridden (the
    SAME optional-override shape the parent's own
    ``assert_never_calls_ontology_miner`` exposes) so a caller (a test) can
    pass a synthetic snippet instead."""

    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise PsluFlightError(
            "rails.probes.pslu_s2_flight source references load_slurp_ontology; this "
            "flight is REGISTERED to consume rosters ONLY from "
            "configs/probes/g0-binding/pslu-rosters-train-only.json (load_pslu_rosters)"
        )


class PsluS2FlightError(RuntimeError):
    """A P-SLU Stage-2 flight input is malformed, or a fail-closed
    structural check (duplicate sample id, a silence-swap id outside this
    flight's own samples, an arm/sample-count mismatch, an unexpected
    silence-swap row count) tripped."""


MappingOutcome = Literal["exact", "case_insensitive", "unique_substring", "unmapped"]


@dataclass(frozen=True)
class ClosedSetMapping:
    """One phase-1 call's own mapping record (mission instruction: "Per-call
    record: chosen label, mapping outcome, fallback flag")."""

    predicted_raw: str | None
    canonical_label: str | None
    outcome: MappingOutcome
    fallback: bool

    def as_json(self) -> dict[str, object]:
        return {
            "predicted_raw": self.predicted_raw,
            "canonical_label": self.canonical_label,
            "outcome": self.outcome,
            "fallback": self.fallback,
        }


def canonical_scenario_labels(rosters: PsluRosters) -> tuple[str, ...]:
    """The 18 canonical SLURP scenario labels -- sorted keys of the SAME
    frozen, train-split-only, legality-checked roster table
    (``rails.probes.pslu_flight.load_pslu_rosters``) the parent flight
    already trusts (module docstring). Never devel gold, never a fresh
    ``data.slurp.load_slurp_ontology`` call."""

    return tuple(sorted(rosters.scenario_rosters.keys()))


def map_predicted_scenario_to_canonical(
    predicted: str | None, canonical_labels: Sequence[str]
) -> ClosedSetMapping:
    """Deterministic three-tier mapper (mission instruction): exact match,
    then case-insensitive, then unique-substring (a canonical label found
    as a case-insensitive substring of the predicted text, and ONLY that
    one label -- ambiguous multi-candidate matches are unmapped, never
    guessed); unmapped otherwise. Unmapped always sets ``fallback=True`` --
    phase 2 then falls back to A2's global vocabulary via the frozen
    ``pslu_supply_packet``'s own A1p branch, EXACTLY like the parent's own
    A1p fallback, never a silent promotion to gold."""

    if predicted is None:
        return ClosedSetMapping(predicted, None, "unmapped", True)
    if predicted in canonical_labels:
        return ClosedSetMapping(predicted, predicted, "exact", False)
    lowered = predicted.lower()
    lower_to_canonical = {label.lower(): label for label in canonical_labels}
    if lowered in lower_to_canonical:
        return ClosedSetMapping(predicted, lower_to_canonical[lowered], "case_insensitive", False)
    candidates = sorted({label for label in canonical_labels if label.lower() in lowered})
    if len(candidates) == 1:
        return ClosedSetMapping(predicted, candidates[0], "unique_substring", False)
    return ClosedSetMapping(predicted, None, "unmapped", True)


def closed_set_phase1_supply_packet(canonical_labels: Sequence[str]) -> SupplyPacket:
    """Phase-1's own instruction text: the closed list of canonical scenario
    labels plus the closed-set-choice instruction, injected as a rails
    ``SupplyForm.TEXT`` block ahead of the audio -- the SAME "text content
    part before the audio" framing every other arm in this study already
    uses (``rails.adapters.slurp.SlurpAdapter.assemble_prompt``), never a
    bespoke system-message edit. Carries no ``items`` (this is an
    instruction, not an evidence roster) -- ``SupplyPacket``'s own
    documented "no per-item granularity" legal shape (``dose.n_items=0``,
    ``items=()``)."""

    labels_text = ", ".join(canonical_labels)
    prompt_block = (
        "Choose the scenario from EXACTLY this closed list, and respond with "
        'that scenario name verbatim in the "scenario" field: '
        f"{labels_text}. Respond with ONLY a JSON object of the form "
        '{"scenario": "<one of the list above, exactly>", "action": "...", '
        '"entities": [{"type": "...", "filler": "..."}, ...]}.'
    )
    return SupplyPacket(
        form=SupplyForm.TEXT,
        dose=SupplyDose(n_items=0, token_count=len(prompt_block.split())),
        prompt_block=prompt_block,
        assembly_template_id="pslu-s2-a1r-phase1-closed-set-v1",
        items=(),
    ).validate()


# ---------------------------------------------------------------------------
# Flight orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PsluS2ArmResult:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace
    silence_swapped: bool = False
    # Only populated on an "A1r-phase1" row -- None everywhere else.
    closed_set_mapping: ClosedSetMapping | None = None


@dataclass(frozen=True)
class PsluS2FlightSummary:
    results: tuple[PsluS2ArmResult, ...]
    canonical_labels: tuple[str, ...]


def validate_pslu_s2_flight_summary(
    summary: PsluS2FlightSummary,
    *,
    expected_sample_ids: Sequence[str],
    expected_silence_swap_sample_ids: Sequence[str] = (),
) -> None:
    """Fail-closed structural check (mission instruction: "fail-closed
    structural checks (arm counts 60/60, no duplicates ...)"): every arm in
    :data:`PSLU_S2_ARMS` carries EXACTLY one row per id in
    ``expected_sample_ids``, no duplicate sample_id rows, and EXACTLY one
    silence-swap row per id in ``expected_silence_swap_sample_ids`` (no
    extras, no duplicates), all on :data:`A1R_ARM`. ``expected_silence_swap_sample_ids``
    is CALLER-supplied (never the frozen :data:`EXPECTED_SILENCE_SWAP_COUNT`
    module constant, which names only THIS probe's own registered count of
    3 and would make this otherwise-general validator unusable against any
    other sample count -- ``analysis.pslu_s2_read``'s own harness-defect
    check is the place that enforces the registered 3 against a REAL
    attempt). Called automatically at the end of :func:`run_pslu_s2_flight`
    with the SAME ``silence_swap_media_relpaths`` keys that function itself
    consumed; independently callable by a caller (e.g. a later, separately-
    registered flight launcher) re-validating an already-assembled
    summary."""

    expected = tuple(expected_sample_ids)
    expected_set = set(expected)
    if len(expected) != len(expected_set):
        raise PsluS2FlightError("expected_sample_ids carries a duplicate")
    expected_silence = tuple(expected_silence_swap_sample_ids)
    expected_silence_set = set(expected_silence)
    if len(expected_silence) != len(expected_silence_set):
        raise PsluS2FlightError("expected_silence_swap_sample_ids carries a duplicate")

    by_arm: dict[str, list[PsluS2ArmResult]] = {arm: [] for arm in PSLU_S2_ARMS}
    silence_rows: list[PsluS2ArmResult] = []
    for row in summary.results:
        if row.arm not in PSLU_S2_ARMS:
            raise PsluS2FlightError(f"unknown P-SLU Stage-2 arm {row.arm!r}")
        if row.silence_swapped:
            silence_rows.append(row)
        else:
            by_arm[row.arm].append(row)

    for arm in PSLU_S2_ARMS:
        rows = by_arm[arm]
        ids = [row.sample_id for row in rows]
        if len(ids) != len(set(ids)):
            raise PsluS2FlightError(f"arm {arm}: duplicate sample_id row(s)")
        got = set(ids)
        if got != expected_set:
            missing = sorted(expected_set - got)
            extra = sorted(got - expected_set)
            raise PsluS2FlightError(
                f"arm {arm}: sample id set does not match the expected {len(expected_set)}-sample "
                f"manifest (missing={missing[:5]}, extra={extra[:5]})"
            )

    silence_ids = [row.sample_id for row in silence_rows]
    if len(silence_ids) != len(set(silence_ids)):
        raise PsluS2FlightError("duplicate silence-swap sample_id row(s)")
    got_silence = set(silence_ids)
    if got_silence != expected_silence_set:
        missing = sorted(expected_silence_set - got_silence)
        extra = sorted(got_silence - expected_silence_set)
        raise PsluS2FlightError(
            f"silence-swap sample id set does not match the expected {len(expected_silence_set)}-sample "
            f"set (missing={missing[:5]}, extra={extra[:5]})"
        )
    for row in silence_rows:
        if row.arm != A1R_ARM:
            raise PsluS2FlightError(
                f"silence-swap row on sample {row.sample_id!r} is on arm {row.arm!r}, expected {A1R_ARM!r}"
            )


def run_pslu_s2_flight(
    *,
    adapter: SlurpAdapter,
    core_client,
    samples: Sequence[SlurpSample],
    rosters: PsluRosters,
    filler_entries: Sequence[tuple[str, str]],
    decoding_params: Mapping[str, object] | None = None,
    silence_swap_media_relpaths: Mapping[str, str] = MappingProxyType({}),
) -> PsluS2FlightSummary:
    """Execute the full F1 + A1'r (two-phase) Stage-2 flight over
    ``samples`` (module docstring) plus one extra A1'r phase-2 request per
    entry in ``silence_swap_media_relpaths`` (``sample_id -> already-
    registered silent media_relpath`` -- ``rails.silence_swap`` +
    ``FrozenCoreClient.register_slice`` build that registration, exactly as
    the parent flight's own ``run_pslu_flight`` already documents; this
    function only consumes the resulting mapping).

    ``core_client`` is duck-typed against ``rails.core_client.CoreClient``
    (the SAME "no forced import" discipline the parent flight's own
    ``run_pslu_flight`` uses).
    """

    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    if not samples:
        raise PsluS2FlightError("run_pslu_s2_flight requires at least one sample")
    sample_ids_list = [sample.sample_id for sample in samples]
    if len(sample_ids_list) != len(set(sample_ids_list)):
        raise PsluS2FlightError("duplicate sample_id in samples")
    sample_id_set = set(sample_ids_list)
    unknown_silence_ids = set(silence_swap_media_relpaths) - sample_id_set
    if unknown_silence_ids:
        raise PsluS2FlightError(
            f"silence_swap_media_relpaths names sample ids outside this flight's own "
            f"samples: {sorted(unknown_silence_ids)}"
        )

    canonical_labels = canonical_scenario_labels(rosters)
    f1_supply = f1_filler_supply_packet(filler_entries)
    phase1_supply = closed_set_phase1_supply_packet(canonical_labels)

    results: list[PsluS2ArmResult] = []

    # F1: one fixed-roster request per sample.
    for sample in samples:
        messages = adapter.assemble_prompt(sample, f1_supply)
        response_text = core_client.complete(messages, decoding_params=decoding_params)
        metrics = adapter.score(sample, response_text)
        consumption = adapter.extract_consumption(sample, f1_supply, response_text)
        results.append(
            PsluS2ArmResult(
                arm=F1_ARM,
                sample_id=sample.sample_id,
                messages=tuple(messages),
                response_text=response_text,
                metrics=metrics,
                consumption=consumption,
            )
        )

    # A1'r: phase 1 (closed-set scenario choice) then phase 2 (frozen
    # pslu_supply_packet, keyed on phase 1's own parsed label).
    for sample in samples:
        phase1_messages = adapter.assemble_prompt(sample, phase1_supply)
        phase1_response = core_client.complete(phase1_messages, decoding_params=decoding_params)
        predicted_scenario, _predicted_action, _predicted_entities, parsed = parse_slu_response(phase1_response)
        mapping = map_predicted_scenario_to_canonical(
            predicted_scenario if parsed else None, canonical_labels
        )
        phase1_metrics = adapter.score(sample, phase1_response)
        phase1_consumption = adapter.extract_consumption(sample, phase1_supply, phase1_response)
        results.append(
            PsluS2ArmResult(
                arm=A1R_PHASE1_ARM,
                sample_id=sample.sample_id,
                messages=tuple(phase1_messages),
                response_text=phase1_response,
                metrics=phase1_metrics,
                consumption=phase1_consumption,
                closed_set_mapping=mapping,
            )
        )

        supply2 = pslu_supply_packet("A1p", scenario=mapping.canonical_label, rosters=rosters)
        phase2_messages = adapter.assemble_prompt(sample, supply2)
        phase2_response = core_client.complete(phase2_messages, decoding_params=decoding_params)
        phase2_metrics = adapter.score(sample, phase2_response)
        phase2_consumption = adapter.extract_consumption(sample, supply2, phase2_response)
        results.append(
            PsluS2ArmResult(
                arm=A1R_ARM,
                sample_id=sample.sample_id,
                messages=tuple(phase2_messages),
                response_text=phase2_response,
                metrics=phase2_metrics,
                consumption=phase2_consumption,
            )
        )

        silence_media_relpath = silence_swap_media_relpaths.get(sample.sample_id)
        if silence_media_relpath is not None:
            silence_messages = _swap_audio_media_relpath(phase2_messages, silence_media_relpath)
            silence_response = core_client.complete(silence_messages, decoding_params=decoding_params)
            silence_metrics = adapter.score(sample, silence_response)
            silence_consumption = adapter.extract_consumption(sample, supply2, silence_response)
            results.append(
                PsluS2ArmResult(
                    arm=A1R_ARM,
                    sample_id=sample.sample_id,
                    messages=silence_messages,
                    response_text=silence_response,
                    metrics=silence_metrics,
                    consumption=silence_consumption,
                    silence_swapped=True,
                )
            )

    summary = PsluS2FlightSummary(results=tuple(results), canonical_labels=canonical_labels)
    validate_pslu_s2_flight_summary(
        summary,
        expected_sample_ids=tuple(sample_ids_list),
        expected_silence_swap_sample_ids=tuple(silence_swap_media_relpaths.keys()),
    )
    return summary


__all__ = [
    "A1R_ARM",
    "A1R_PHASE1_ARM",
    "EXPECTED_SILENCE_SWAP_COUNT",
    "F1_ARM",
    "PSLU_S2_ARMS",
    "ClosedSetMapping",
    "PsluS2ArmResult",
    "PsluS2FlightError",
    "PsluS2FlightSummary",
    "canonical_scenario_labels",
    "closed_set_phase1_supply_packet",
    "map_predicted_scenario_to_canonical",
    "run_pslu_s2_flight",
    "validate_pslu_s2_flight_summary",
]


# Executed at import time (mirrors rails.probes.pslu_flight's own
# module-bottom self-check): fails LOUD the moment this module is loaded if
# a future edit adds a live reference to the forbidden ontology miner --
# BOTH the parent's own source (re-verified) and this module's own source
# (actually scanned, see _assert_this_module_never_calls_ontology_miner's
# own docstring for why the parent's default guard alone cannot do this).
assert_never_calls_ontology_miner()
_assert_this_module_never_calls_ontology_miner()
