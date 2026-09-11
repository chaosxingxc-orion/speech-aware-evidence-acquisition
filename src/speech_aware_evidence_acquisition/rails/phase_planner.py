"""Choose whether to enter the next declared phase from typed Reviewer flags.

A planner never writes an answer or introduces a contact. It may stop at the
current core response or let EvidenceAgentController advance to its next phase.
Unconfigured programs retain their historical behavior and receipt shape.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import threading
from typing import Mapping

from ..core.base import CoreError, JUDGE_FLAG_SEVERITIES, JudgeVerdict, PHASE_PLANNERS
from .controllers import PhaseProgram
from .phase_review import PhaseReviewSpec
from .runner import AgentRuntimeContext

SCHEMA = "saea-phase-planner-v1"
_KEYS = frozenset(("planner_policy_id", "judges", "minimum_severity"))


class PhasePlannerError(ValueError):
    """Refuse an unbound, stale, unsupported, or malformed planner decision."""


def continue_on_flag(
    verdicts: tuple[JudgeVerdict, ...], minimum_severity: str
) -> bool:
    """Continue only when a selected judge flags at or above the threshold."""
    threshold = JUDGE_FLAG_SEVERITIES.index(minimum_severity)
    return any(
        JUDGE_FLAG_SEVERITIES.index(flag.severity) >= threshold
        for verdict in verdicts for flag in verdict.flags
    )


PHASE_PLANNERS.register("continue-on-flag-v1", continue_on_flag)


@dataclass(frozen=True)
class PhasePlannerSpec:
    phase: str
    program_id: str
    completed_phases: tuple[str, ...]
    planner_policy_id: str
    judges: tuple[str, ...]
    minimum_severity: str
    review: PhaseReviewSpec

    def as_json(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "program_id": self.program_id,
            "completed_phases": list(self.completed_phases),
            "planner_policy_id": self.planner_policy_id,
            "judges": list(self.judges),
            "minimum_severity": self.minimum_severity,
            "review": self.review.as_json(),
        }


def load_phase_planner_specs(
    values: Mapping[str, object],
    program: PhaseProgram,
    review_specs: Mapping[str, PhaseReviewSpec],
) -> dict[str, PhasePlannerSpec]:
    program.validate()
    declared = values.get("phase_planner")
    if declared is None or declared == {}:
        return {}
    if not isinstance(declared, Mapping):
        raise PhasePlannerError("phase_planner must be an object keyed by phase")
    if program.stop_rule != "stop-policy-optional-early-exit":
        raise PhasePlannerError("phase_planner requires optional early-exit semantics")
    names = program.phase_names()
    if any(name not in names[:-1] for name in declared):
        raise PhasePlannerError("phase_planner must name a declared non-final phase")
    specs = {}
    for index, phase in enumerate(names):
        if phase not in declared:
            continue
        entry = declared[phase]
        if not isinstance(entry, Mapping) or set(entry) - _KEYS:
            raise PhasePlannerError("phase_planner entry must contain only declared keys")
        policy = entry.get("planner_policy_id")
        try:
            rule = PHASE_PLANNERS.resolve(policy)
        except (CoreError, TypeError) as exc:
            raise PhasePlannerError("phase_planner requires a registered policy") from exc
        if not callable(rule):
            raise PhasePlannerError("registered phase planner must be callable")
        judges = entry.get("judges")
        if (
            not isinstance(judges, (list, tuple)) or not judges
            or any(not isinstance(judge, str) or not judge for judge in judges)
            or len(set(judges)) != len(judges)
        ):
            raise PhasePlannerError("phase_planner judges must be unique non-empty ids")
        review = review_specs.get(phase)
        if not isinstance(review, PhaseReviewSpec) or not set(judges) <= set(review.judges):
            raise PhasePlannerError("phase_planner judges must be declared in this phase review")
        review.validate()
        severity = entry.get("minimum_severity", "warn")
        if severity not in JUDGE_FLAG_SEVERITIES:
            raise PhasePlannerError("phase_planner minimum_severity is invalid")
        specs[phase] = PhasePlannerSpec(
            phase, program.program_id, names[:index + 1], policy,
            tuple(judges), severity, review,
        )
    return specs


class _PhasePlanner:
    def __init__(self, specs: Mapping[str, PhasePlannerSpec], reviewer: object):
        self._specs = dict(specs)
        read = getattr(reviewer, "reviewed_response", None)
        reviews = getattr(reviewer, "specs", None)
        if not callable(read) or not isinstance(reviews, Mapping) or any(
            reviews.get(phase) != spec.review for phase, spec in specs.items()
        ):
            raise PhasePlannerError("phase_planner requires the declared bound reviewer")
        self._read = read
        self._rules = {
            phase: PHASE_PLANNERS.resolve(spec.planner_policy_id)
            for phase, spec in specs.items()
        }
        self._lock = threading.Lock()
        self._decisions: dict[tuple[str, str], dict[str, object]] = {}

    def __call__(
        self, context: AgentRuntimeContext, completed_phases: tuple[str, ...]
    ) -> bool:
        if not completed_phases:
            raise PhasePlannerError("phase_planner needs a completed phase")
        phase = completed_phases[-1]
        spec = self._specs.get(phase)
        if spec is None:
            return False
        if tuple(completed_phases) != spec.completed_phases:
            raise PhasePlannerError("phase_planner completed phases differ from the program")
        if context.sample_id != context.query_state.query_sample_id or not context.agent_states:
            raise PhasePlannerError("phase_planner needs the current sample's sealed state")
        state = context.agent_states[-1]
        if (
            state.state_kind != f"phase:{phase}"
            or state.producer_policy_id != spec.program_id
            or state.source_query_state_sha256 != context.query_state.content_hash()
            or not context.prior_response_sha256s
            or state.source_response_sha256 != context.prior_response_sha256s[-1]
        ):
            raise PhasePlannerError("phase_planner sealed phase or source binding differs")
        reviewed = self._read(phase, context.sample_id)
        if reviewed is None or reviewed[0] != state.source_response_sha256:
            raise PhasePlannerError("phase_planner review is missing or stale")
        digest, verdicts = reviewed
        if (
            not isinstance(verdicts, tuple)
            or any(not isinstance(verdict, JudgeVerdict) for verdict in verdicts)
            or tuple(verdict.judge_id for verdict in verdicts) != spec.review.judges
        ):
            raise PhasePlannerError("phase_planner review judge identities differ")
        for verdict in verdicts:
            verdict.validate()
        selected = tuple(verdict for verdict in verdicts if verdict.judge_id in spec.judges)
        should_continue = self._rules[phase](selected, spec.minimum_severity)
        if type(should_continue) is not bool:
            raise PhasePlannerError("phase planner must return only a boolean continuation decision")
        row = {
            "use_schema": SCHEMA,
            "use_phase": phase,
            "use_sample_id": context.sample_id,
            "use_planner_policy_id": spec.planner_policy_id,
            "use_judge_ids": list(spec.judges),
            "use_minimum_severity": spec.minimum_severity,
            "use_review_response_sha256": digest,
            "use_review_verdicts_sha256": hashlib.sha256(
                json.dumps([v.as_json() for v in verdicts], sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "use_decision": "continue" if should_continue else "stop",
            "use_flags_total": sum(len(verdict.flags) for verdict in selected),
        }
        key = (phase, context.sample_id)
        with self._lock:
            prior = self._decisions.get(key)
            if prior is not None and prior != row:
                raise PhasePlannerError("phase_planner decision conflicts with a recorded source")
            self._decisions[key] = row
        return not should_continue

    def active_sample_ids(
        self, phase: str, phase_names: tuple[str, ...], sample_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Derive a phase roster only from completed decisions on prior phases."""
        if phase not in phase_names:
            raise PhasePlannerError("active roster needs a declared phase")
        active = tuple(sample_ids)
        decisions = self.decisions()
        for prior in phase_names[:phase_names.index(phase)]:
            if prior not in self._specs:
                continue
            if any((prior, sample_id) not in decisions for sample_id in active):
                raise PhasePlannerError("active roster is missing a prior planner decision")
            active = tuple(
                sample_id for sample_id in active
                if decisions[(prior, sample_id)]["use_decision"] == "continue"
            )
        return active

    def decisions(self) -> dict[tuple[str, str], dict[str, object]]:
        with self._lock:
            return {
                key: {**row, "use_judge_ids": list(row["use_judge_ids"])}
                for key, row in self._decisions.items()
            }


def build_phase_planner(
    specs: Mapping[str, PhasePlannerSpec], reviewer: object
) -> _PhasePlanner | None:
    return _PhasePlanner(specs, reviewer) if specs else None


def emit_planner_records(
    planner: _PhasePlanner | None, sink: object, *,
    record_namespace: str | None = None,
) -> int:
    if planner is None:
        return 0
    rows = planner.decisions()
    for (phase, sample_id), row in sorted(rows.items()):
        base = sample_id if record_namespace is None else f"{sample_id}/{record_namespace}"
        sink.emit("USE", f"{base}/{phase}/planner", row)
    return len(rows)


def phase_planner_receipt(
    specs: Mapping[str, PhasePlannerSpec], planner: _PhasePlanner | None = None,
) -> dict[str, object]:
    if not specs:
        return {}
    decisions = {} if planner is None else planner.decisions()
    phases = []
    for phase, spec in specs.items():
        rows = [row for (name, _), row in decisions.items() if name == phase]
        phases.append({
            "spec": spec.as_json(),
            "rows_decided": len(rows),
            "rows_continued": sum(row["use_decision"] == "continue" for row in rows),
            "rows_stopped": sum(row["use_decision"] == "stop" for row in rows),
        })
    return {"schema": SCHEMA, "phases": phases}
