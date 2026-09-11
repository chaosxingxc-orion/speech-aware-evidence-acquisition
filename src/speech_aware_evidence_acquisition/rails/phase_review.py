"""The Reviewer seam: a phase program's per-phase criticism, from config alone.

``rails.phase_material`` closed the "what does this phase SAY" seam and
``rails.phase_supply`` the "what does this phase SEE" one. This module closes
the third: **what does the harness make of what the phase ANSWERED.** A
baseline fragment declares

.. code-block:: json

    "phase_review": {
      "draft": {
        "judges": ["earnings-numeric-format-v1", "e21-substitution-alignment-v1"],
        "on_flag": "record",
        "params": {"e21-substitution-alignment-v1": {"max_span_tokens": 4}}
      }
    }

and :func:`load_phase_review_specs` turns it into one :class:`PhaseReviewSpec`
per declared phase, fail-closed against the program's own ``PhaseSpec`` list
exactly the way ``phase_supply`` is. ``core.flight.FlightRuntime`` resolves
those specs into the ``review_for_phase`` callable
:class:`rails.controllers.EvidenceAgentController` consults after each Solve
phase, with NO launcher and no new class outside the bases.

Owner Decision 11-C, 2026-09-08: criticism only
------------------------------------------------

**A judge SCORES and FLAGS; it never proposes a revision.** Its whole output
is a ``core.base.JudgeVerdict`` -- a score, flags carrying span and field
references into the draft, and reasons -- consumed by the Planner's loop
decision and by the Solver's constrained revise. That is enforced by the
verdict TYPE (``core.base.assert_criticism_only``), not by this module's good
manners, so nothing here can put replacement text anywhere: not on a control
turn, not in a trace record, not in a receipt.

The consequence worth stating twice: **reviewing a phase changes not one byte
of what the flight sends.** ``review_for_phase`` runs AFTER the phase's
response is sealed, reads the sealed bytes, and returns verdicts the
controller records. With ``on_flag: "record"`` -- the default and, today, the
only accepted value -- the transition, the successor ``QueryState`` and the
next contact are identical to the same cell run with no ``phase_review``
block at all. The paired contrast a judge's admission receipt needs is
therefore a config key and its null arm, never a second code path.

``on_flag: "loop"`` is refused, and why
----------------------------------------

The design's loop (Plan -> Observe -> Solve -> Review -> Plan again) wants a
flagged row to spend another contact on the SAME phase. That is not a change
to this module or to :class:`~.controllers.EvidenceAgentController`; it is a
change to the two invariants ``rails.runner`` enforces around them, and
``rails.runner`` belongs to another wave of this convergence:

* ``rails.runner._validate_new_agent_states`` refuses an
  ``AgentStateArtifact`` whose ``state_id`` already exists, and the
  controller's state id is ``f"{phase}:{sample_id}"`` -- so a phase cannot
  seal twice for one sample without a new id scheme;
* ``rails.runner.schedule_wave`` refuses a reused ``contact_id``, and a
  phase's contact id comes from its ``PhaseMaterial`` -- so a re-ask needs a
  per-attempt contact identity too.

Both are deliberate rails, not accidents, and relaxing them is W2's Observer
seam work (assessment change #3/#4). Until then :data:`LOOP_REFUSAL_REASON`
is what a fragment declaring ``on_flag: "loop"`` gets, by name, before any
contact -- rather than a half-wired loop that silently records instead.

What a judge is given
---------------------

``judge(draft, material, state)``:

* ``draft`` -- the phase's own sealed response text, verbatim;
* ``material`` -- the phase's per-judge material: the config-pinned ``params``
  merged over whatever :func:`build_review_for_phase`'s caller injected for
  that judge (the carrier data a judge needs -- a legal-label inventory, a
  slot-type block, a candidate roster -- is far too large for a config
  fragment, exactly as ``phase_supply``'s providers are). Config params win a
  key collision, because those are what ride the config hash;
* ``state`` -- this row's own runtime state, derived from the
  ``AgentRuntimeContext`` alone: sample id, phase, loop step, contact index,
  the ids the trajectory carries, and the immediately preceding sealed state's
  text as ``predecessor_text`` (what a substitution-only judge compares
  against). No gold, no reference, no future turn: the ``REVIEW`` trace record
  every verdict lands in passes ``contracts.assert_information_boundary`` like
  every other record.

Where the verdicts go
---------------------

Verdicts are collected per ``(phase, sample_id)`` while the roster flies, and
written out ONCE, in sorted order, by :func:`emit_review_records` after the
wave settles -- the same "buffer per sample, flush in deterministic order"
discipline ``rails.runner`` and ``core.tracing`` already use, and the reason
this module never touches the sink from inside a trajectory.
:func:`phase_review_receipt` summarizes the same collection for the run
outcome: rows reviewed, flags raised per judge, per phase, and the ids and
versions that raised them.
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from typing import Callable, Mapping, Sequence

from ..core.base import JUDGES, CoreError, JudgeVerdict
from .controllers import PhaseProgram
from .errors import RailsError
from .runner import AgentRuntimeContext

PHASE_REVIEW_SCHEMA = "saea-phase-review-v1"

#: What the Planner does with a raised flag. ``record`` traces it and moves
#: on -- the whole cell is byte-identical to the same cell with no review.
#: ``loop`` would spend another contact on the flagged row and is refused
#: today (:data:`LOOP_REFUSAL_REASON`, module docstring).
PHASE_REVIEW_ON_FLAG = ("record", "loop")

DEFAULT_ON_FLAG = "record"

LOOP_REFUSAL_REASON = (
    "phase_review on_flag='loop' is not wired yet: a re-ask on a flagged row "
    "would seal a second AgentStateArtifact under the same state_id "
    "(rails.runner._validate_new_agent_states refuses it) and reuse the "
    "phase's contact_id (rails.runner.schedule_wave refuses it). Both rails "
    "live in rails/runner.py and relaxing them is the Observer-seam wave of "
    "this convergence, not this one. Declare on_flag='record' -- the verdicts "
    "are still traced and summarized -- or land the runner change first"
)

_SPEC_KEYS = frozenset({"judges", "on_flag", "params"})

#: ``review_for_phase(phase_name, context, response_text) -> verdicts``. The
#: fourth injected callable of ``EvidenceAgentController``, beside
#: ``material_for_phase`` / ``supply_for_phase`` / ``stop_policy``.
ReviewForPhase = Callable[
    [str, AgentRuntimeContext, str], "Sequence[JudgeVerdict]"
]


class PhaseReviewError(RailsError):
    """A ``phase_review`` config block, an injected judge, or a returned
    verdict violated the shape this module requires."""


def _require_nonempty_str(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PhaseReviewError(f"{field_name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class PhaseReviewSpec:
    """One phase's declared criticism: which judges read its draft, and what
    the Planner does with a raised flag."""

    phase: str
    judges: tuple[str, ...]
    on_flag: str = DEFAULT_ON_FLAG
    params: Mapping[str, Mapping[str, object]] = field(default_factory=dict)

    def validate(self) -> "PhaseReviewSpec":
        _require_nonempty_str(self.phase, field_name="PhaseReviewSpec.phase")
        if not isinstance(self.judges, tuple) or not self.judges:
            raise PhaseReviewError(
                f"phase_review[{self.phase!r}].judges must be a non-empty list of "
                "registered judge ids; a review block that names no judge reviews "
                "nothing and would read as if it did"
            )
        seen: set[str] = set()
        for index, judge_id in enumerate(self.judges):
            _require_nonempty_str(
                judge_id, field_name=f"phase_review[{self.phase!r}].judges[{index}]"
            )
            if judge_id in seen:
                raise PhaseReviewError(
                    f"phase_review[{self.phase!r}].judges repeats {judge_id!r}; one "
                    "judge reads one draft once"
                )
            seen.add(judge_id)
            try:
                JUDGES.resolve(judge_id)
            except CoreError as error:
                raise PhaseReviewError(
                    f"phase_review[{self.phase!r}].judges[{index}]: {error}"
                ) from None
        if self.on_flag not in PHASE_REVIEW_ON_FLAG:
            raise PhaseReviewError(
                f"phase_review[{self.phase!r}].on_flag must be one of "
                f"{list(PHASE_REVIEW_ON_FLAG)}, got {self.on_flag!r}"
            )
        if self.on_flag == "loop":
            raise PhaseReviewError(f"phase_review[{self.phase!r}]: {LOOP_REFUSAL_REASON}")
        if not isinstance(self.params, Mapping):
            raise PhaseReviewError(
                f"phase_review[{self.phase!r}].params must be an object keyed by judge id"
            )
        unknown = sorted(set(self.params) - set(self.judges))
        if unknown:
            raise PhaseReviewError(
                f"phase_review[{self.phase!r}].params names judge(s) {unknown} that this "
                f"phase does not review; its judges are {sorted(self.judges)}"
            )
        for judge_id, entry in self.params.items():
            if not isinstance(entry, Mapping):
                raise PhaseReviewError(
                    f"phase_review[{self.phase!r}].params[{judge_id!r}] must be an object"
                )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "phase": self.phase,
            "judges": list(self.judges),
            "on_flag": self.on_flag,
            "params": {
                judge_id: dict(sorted(self.params[judge_id].items()))
                for judge_id in sorted(self.params)
            },
            "judge_versions": {
                judge_id: str(getattr(JUDGES.resolve(judge_id), "version", ""))
                for judge_id in sorted(self.judges)
            },
        }


def load_phase_review_specs(
    values: Mapping[str, object], program: PhaseProgram
) -> Mapping[str, PhaseReviewSpec]:
    """Parse the baseline fragment's ``phase_review`` object against ``program``.

    Absent or empty: no phase is reviewed and an empty mapping is returned
    (every fragment written before this wave). Present: refuses a non-object;
    a phase the program does not declare; an unknown key in a phase entry; an
    empty or repeating ``judges`` list; a judge id that resolves in no
    ``core.base.JUDGES`` entry; an ``on_flag`` outside
    :data:`PHASE_REVIEW_ON_FLAG`; and ``on_flag: "loop"`` by name
    (:data:`LOOP_REFUSAL_REASON`).

    Returned in the program's own phase order, so a receipt reads the way the
    program runs.
    """

    program.validate()
    declared = values.get("phase_review")
    if declared is None or declared == {}:
        return {}
    if not isinstance(declared, Mapping):
        raise PhaseReviewError(
            "'phase_review' must be an object keyed by phase name "
            f"({list(program.phase_names())})"
        )
    known = set(program.phase_names())
    unknown = sorted(set(declared) - known)
    if unknown:
        raise PhaseReviewError(
            f"phase_review names phase(s) {unknown} that program "
            f"{program.program_id!r} does not declare; its phases are {sorted(known)}"
        )
    specs: dict[str, PhaseReviewSpec] = {}
    for phase in program.phases:
        if phase.name not in declared:
            continue
        entry = declared[phase.name]
        if not isinstance(entry, Mapping):
            raise PhaseReviewError(f"phase_review[{phase.name!r}] must be an object")
        extra = sorted(set(entry) - _SPEC_KEYS)
        if extra:
            raise PhaseReviewError(
                f"phase_review[{phase.name!r}] carries unknown key(s) {extra}; known "
                f"keys are {sorted(_SPEC_KEYS)}"
            )
        judges = entry.get("judges")
        if isinstance(judges, (str, bytes)) or not isinstance(judges, (list, tuple)):
            raise PhaseReviewError(
                f"phase_review[{phase.name!r}].judges must be a list of registered "
                f"judge ids, got {judges!r}"
            )
        specs[phase.name] = PhaseReviewSpec(
            phase=phase.name,
            judges=tuple(judges),
            on_flag=entry.get("on_flag", DEFAULT_ON_FLAG),
            params=entry.get("params", {}) or {},
        ).validate()
    return specs


def default_state_for_review(
    phase_name: str, context: AgentRuntimeContext
) -> dict[str, object]:
    """This row's runtime state, derived from the context and nothing else.

    ``predecessor_text`` is the immediately preceding sealed phase state's
    own content -- what a substitution-only or a delta judge compares the
    draft against -- and is empty for a program's first phase. Nothing here
    is gold, a reference, or a future turn (module docstring).
    """

    states = tuple(context.agent_states or ())
    predecessor = states[-2].content if len(states) >= 2 else ""
    return {
        "sample_id": context.sample_id,
        "phase": phase_name,
        "loop_step": context.query_state.loop_step,
        "contact_index": context.contact_index,
        "predecessor_text": predecessor,
        "agent_state_ids": tuple(context.query_state.agent_state_ids),
        "visible_facet_ids": tuple(context.query_state.visible_facet_ids),
        "retrieved_value_ids": tuple(context.query_state.retrieved_value_ids),
    }


class _PhaseReview:
    """The ``review_for_phase`` callable, plus the collection it fills.

    One instance per run (never per sample): the controller factory hands the
    same object to every sample's controller, and the collection is keyed by
    ``(phase, sample_id)`` so a whole-roster wave and a continuous trajectory
    both land in the same place. Guarded by a lock because a trajectory may
    run on a worker thread while another one does.
    """

    def __init__(
        self,
        specs: Mapping[str, PhaseReviewSpec],
        *,
        judges: Mapping[str, object] | None = None,
        extra_material: Mapping[str, Mapping[str, Mapping[str, object]]] | None = None,
        state_for_review: Callable[[str, AgentRuntimeContext], Mapping[str, object]]
        | None = None,
    ) -> None:
        self._specs = {phase: spec.validate() for phase, spec in specs.items()}
        resolved: dict[str, object] = {}
        for spec in self._specs.values():
            for judge_id in spec.judges:
                if judge_id in resolved:
                    continue
                if judges is not None and judge_id in judges:
                    resolved[judge_id] = judges[judge_id]
                else:
                    resolved[judge_id] = JUDGES.resolve(judge_id)
        self._judges = resolved
        self._extra_material = {
            phase: {
                judge_id: dict(material)
                for judge_id, material in (entry or {}).items()
            }
            for phase, entry in (extra_material or {}).items()
        }
        self._state_for_review = state_for_review or default_state_for_review
        self._lock = threading.Lock()
        self._verdicts: dict[tuple[str, str], tuple[JudgeVerdict, ...]] = {}
        self._response_sha256: dict[tuple[str, str], str] = {}

    @property
    def specs(self) -> Mapping[str, PhaseReviewSpec]:
        return dict(self._specs)

    @property
    def reviewed_phases(self) -> tuple[str, ...]:
        return tuple(self._specs)

    def verdicts(self) -> Mapping[tuple[str, str], tuple[JudgeVerdict, ...]]:
        with self._lock:
            return dict(self._verdicts)

    def response_hashes(self) -> Mapping[tuple[str, str], str]:
        with self._lock:
            return dict(self._response_sha256)

    def reviewed_response(
        self, phase: str, sample_id: str
    ) -> tuple[str, tuple[JudgeVerdict, ...]] | None:
        """Read verdicts and their source hash atomically for a Planner."""
        key = (phase, sample_id)
        with self._lock:
            if key not in self._verdicts:
                return None
            return self._response_sha256[key], self._verdicts[key]

    def _material(self, phase: str, judge_id: str) -> Mapping[str, object]:
        material = dict(self._extra_material.get(phase, {}).get(judge_id, {}))
        # Config params win a collision: they are what rides the config hash,
        # so a receipt that quotes them describes what actually ran.
        material.update(dict(self._specs[phase].params.get(judge_id, {})))
        return material

    def __call__(
        self,
        phase_name: str,
        context: AgentRuntimeContext,
        response_text: str,
    ) -> tuple[JudgeVerdict, ...]:
        spec = self._specs.get(phase_name)
        if spec is None:
            return ()
        if not isinstance(response_text, str):
            raise PhaseReviewError(
                "review_for_phase requires the phase's own response text"
            )
        state = self._state_for_review(phase_name, context)
        if not isinstance(state, Mapping):
            raise PhaseReviewError("state_for_review must return a mapping")
        verdicts: list[JudgeVerdict] = []
        for judge_id in spec.judges:
            judge = self._judges[judge_id]
            verdict = judge(response_text, self._material(phase_name, judge_id), state)
            if not isinstance(verdict, JudgeVerdict):
                raise PhaseReviewError(
                    f"judge {judge_id!r} returned {type(verdict).__name__}, not a "
                    "core.base.JudgeVerdict; a judge scores and flags and never "
                    "proposes a revision (owner Decision 11-C)"
                )
            verdict.validate()
            if verdict.judge_id != judge_id:
                raise PhaseReviewError(
                    f"judge {judge_id!r} returned a verdict signed "
                    f"{verdict.judge_id!r}; the registered id and the verdict's own "
                    "id are one identity"
                )
            verdicts.append(verdict)
        key = (phase_name, context.sample_id)
        with self._lock:
            self._verdicts[key] = tuple(verdicts)
            self._response_sha256[key] = hashlib.sha256(
                response_text.encode("utf-8")
            ).hexdigest()
        return tuple(verdicts)


def build_review_for_phase(
    specs: Mapping[str, PhaseReviewSpec],
    *,
    judges: Mapping[str, object] | None = None,
    extra_material: Mapping[str, Mapping[str, Mapping[str, object]]] | None = None,
    state_for_review: Callable[[str, AgentRuntimeContext], Mapping[str, object]]
    | None = None,
) -> "_PhaseReview | None":
    """The ``review_for_phase`` callable for ``specs``, or ``None`` when no
    phase is reviewed -- and ``None`` is exactly today's behaviour, so an
    unreviewed cell keeps the byte-identical path it already had.

    ``judges`` injects an INSTANCE per id (a test double, or a judge that
    needs a pinned artifact); the id still has to resolve in
    ``core.base.JUDGES``, which :class:`PhaseReviewSpec` already checked --
    this seam supplies the instance, never the identity, exactly as
    ``FlightRuntime.bind_phase_supply_providers`` does for providers.
    """

    if not specs:
        return None
    return _PhaseReview(
        specs,
        judges=judges,
        extra_material=extra_material,
        state_for_review=state_for_review,
    )


def emit_review_records(
    review_for_phase: object,
    sink: object,
    *,
    record_namespace: str | None = None,
    phase_name: str | None = None,
) -> int:
    """Write one ``REVIEW`` trace record per reviewed row, in sorted order.

    Called once, after a wave settles, by whoever owns the sink
    (``rails.phase_runner``) -- never from inside a trajectory, so the record
    order is decided by this loop rather than by task completion (the
    ``core.tracing`` flush discipline). Returns the number of records written;
    a ``None``/empty reviewer writes nothing and returns 0.

    Every payload key carries the ``review_`` prefix
    (``contracts.boundary._CHANNEL_PREFIX``), and every verdict is rendered
    through ``JudgeVerdict.as_json`` -- which is capped and criticism-only, so
    a REVIEW record cannot carry a proposed revision either.
    """

    if review_for_phase is None:
        return 0
    verdicts = getattr(review_for_phase, "verdicts", None)
    if not callable(verdicts):
        raise PhaseReviewError(
            "emit_review_records needs the callable build_review_for_phase returned"
        )
    collected = verdicts()
    hashes = review_for_phase.response_hashes()
    specs = review_for_phase.specs
    written = 0
    for phase, sample_id in sorted(collected):
        if phase_name is not None and phase != phase_name:
            continue
        row = collected[(phase, sample_id)]
        base = (
            f"{sample_id}/{phase}/review"
            if record_namespace is None
            else f"{sample_id}/{record_namespace}/{phase}/review"
        )
        sink.emit(
            "REVIEW",
            base,
            {
                "review_schema": PHASE_REVIEW_SCHEMA,
                "review_phase": phase,
                "review_sample_id": sample_id,
                "review_on_flag": specs[phase].on_flag,
                "review_judge_ids": list(specs[phase].judges),
                "review_response_sha256": hashes[(phase, sample_id)],
                "review_verdicts": [verdict.as_json() for verdict in row],
                "review_flags_total": sum(len(verdict.flags) for verdict in row),
            },
        )
        written += 1
    return written


def phase_review_receipt(
    specs: Mapping[str, PhaseReviewSpec], review_for_phase: object = None
) -> dict[str, object]:
    """A hashable identity record for what this run's review IS, plus what it
    found: the spec per phase, and -- when the reviewer ran -- rows reviewed,
    rows carrying at least one flag, and the flag count per judge per
    severity. Never a draft, never a flag's reason in bulk: this is the
    summary a run outcome carries, and the per-row detail is in the REVIEW
    trace records.
    """

    phases: list[dict[str, object]] = []
    collected: Mapping[tuple[str, str], tuple[JudgeVerdict, ...]] = {}
    if review_for_phase is not None:
        collected = review_for_phase.verdicts()
    for phase in sorted(specs):
        spec = specs[phase]
        rows = [row for (name, _), row in collected.items() if name == phase]
        per_judge: dict[str, dict[str, object]] = {
            judge_id: {
                "version": str(getattr(JUDGES.resolve(judge_id), "version", "")),
                "rows_flagged": 0,
                "flags": 0,
                "by_severity": {},
            }
            for judge_id in spec.judges
        }
        flagged_rows = 0
        for row in rows:
            if any(verdict.flagged for verdict in row):
                flagged_rows += 1
            for verdict in row:
                entry = per_judge.setdefault(
                    verdict.judge_id,
                    {
                        "version": verdict.version,
                        "rows_flagged": 0,
                        "flags": 0,
                        "by_severity": {},
                    },
                )
                if verdict.flagged:
                    entry["rows_flagged"] = int(entry["rows_flagged"]) + 1
                entry["flags"] = int(entry["flags"]) + len(verdict.flags)
                severities = entry["by_severity"]
                for flag in verdict.flags:
                    severities[flag.severity] = int(severities.get(flag.severity, 0)) + 1
        phases.append(
            {
                "spec": spec.as_json(),
                "rows_reviewed": len(rows),
                "rows_flagged": flagged_rows,
                "judges": {
                    judge_id: {
                        "version": per_judge[judge_id]["version"],
                        "rows_flagged": per_judge[judge_id]["rows_flagged"],
                        "flags": per_judge[judge_id]["flags"],
                        "by_severity": dict(
                            sorted(per_judge[judge_id]["by_severity"].items())
                        ),
                    }
                    for judge_id in sorted(per_judge)
                },
            }
        )
    return {
        "schema": PHASE_REVIEW_SCHEMA,
        "on_flag_vocabulary": list(PHASE_REVIEW_ON_FLAG),
        "criticism_only": True,
        "phases": phases,
    }


__all__ = [
    "DEFAULT_ON_FLAG",
    "LOOP_REFUSAL_REASON",
    "PHASE_REVIEW_ON_FLAG",
    "PHASE_REVIEW_SCHEMA",
    "PhaseReviewError",
    "PhaseReviewSpec",
    "ReviewForPhase",
    "build_review_for_phase",
    "default_state_for_review",
    "emit_review_records",
    "load_phase_review_specs",
    "phase_review_receipt",
]
