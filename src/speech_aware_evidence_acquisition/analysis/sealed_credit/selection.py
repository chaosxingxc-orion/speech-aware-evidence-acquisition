"""Ruled selection, stop rule and the curve (decision 263 A; spec 5.3 and 5.4; the
coordinator's Q1 reading: CI95 lower bound > 0 AND point >= 1.49 pp AND above the twin,
with the 0.65 intent guard).

Inputs are credit vectors as laid out in :func:`archive.validate_credit` (paired deltas in
percentage points). Arguments of :func:`select`:

* ``child``  -- the child column's credit vector (``vs_lock`` required; ``vs_parent`` used
  when present);
* ``lock``   -- ``{"role": "lock", "n_rows": int}`` identity of the lock column (the child
  must be read on the same rows when it declares ``n_rows``);
* ``twin``   -- the twin (A/A) column's credit vector; its ``vs_lock.slu.point`` is the
  twin-minus-lock level the child must exceed;
* ``parent`` -- the parent column's credit vector measured in the SAME flight, or ``None``
  when no parent column exists (iteration 1, or an offline candidate);
* ``rules``  -- see :data:`DEFAULT_RULES`.

Clauses (all must hold; the verdict names every failure):

  a. ``child.vs_lock.slu.lo``    >  ``ci_lb_min_pp`` (0)
  b. ``child.vs_lock.slu.point`` >= ``slu_floor_pp``  (1.49)
  c. ``child.vs_lock.slu.point`` >  ``twin.vs_lock.slu.point``      (``require_beat_twin``)
  d. with a parent column: ``child.vs_parent.slu.point`` > 0 strictly (or, when the child
     carries no ``vs_parent``, ``child.vs_lock.slu.point - parent.vs_lock.slu.point`` > 0)
  e. intent guard: ``child.vs_lock.intent.lo`` >= ``-intent_guard_pp`` (-0.65) AND
     ``child.vs_lock.intent.point`` >= ``intent_point_floor_pp`` (0, "no loss").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

STOP_AFTER_ITERATIONS = 3
DEFAULT_RULES: dict[str, Any] = {
    "ci_lb_min_pp": 0.0,
    "slu_floor_pp": 1.49,
    "intent_guard_pp": 0.65,
    "intent_point_floor_pp": 0.0,
    "require_beat_twin": True,
}
SLU_DESIGN = "same-flight-supply-variant"


class SelectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Verdict:
    accepted: bool
    clauses: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def failed(self) -> list[str]:
        return [name for name, c in self.clauses.items() if not c["pass"]]

    @property
    def status(self) -> str:
        return "accepted" if self.accepted else "refused"

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "accepted": self.accepted, "failed": self.failed, "clauses": self.clauses}


def rules_from_floor_table(rows: int, repo_root: Path, design: str = SLU_DESIGN) -> dict[str, Any]:
    """The decision-190 numbers read from ``stage3_effect_floor_check.FLOOR_TABLE`` through
    ``accept`` (imported, never copied): SLU benefit floor and intent floor at ``rows``."""

    from speech_aware_evidence_acquisition.analysis.sealed_credit import accept

    bounds = accept.design_guard_and_floor(design, rows, repo_root)
    gate = accept._floor_gate(repo_root)
    slu_floor, _ = gate.floor_for(design, rows, purpose="benefit", metric="slu")
    return {**DEFAULT_RULES, "slu_floor_pp": float(slu_floor), "intent_guard_pp": float(bounds["floor_pp"])}


def _clause(passed: bool, value: Any, threshold: Any, op: str) -> dict[str, Any]:
    return {"pass": bool(passed), "value": value, "threshold": threshold, "op": op}


def select(
    child: Mapping[str, Any], lock: Mapping[str, Any], twin: Mapping[str, Any] | None,
    parent: Mapping[str, Any] | None, rules: Mapping[str, Any] | None = None,
) -> Verdict:
    rules = {**DEFAULT_RULES, **(rules or {})}
    n_child = child.get("n_rows")
    if n_child is not None and lock.get("n_rows") is not None and n_child != lock["n_rows"]:
        raise SelectionError("child and lock were not read on the same rows")
    slu = child["vs_lock"]["slu"]
    intent = child["vs_lock"]["intent"]
    clauses: dict[str, dict[str, Any]] = {}
    clauses["a_ci_lb"] = _clause(slu["lo"] > rules["ci_lb_min_pp"], slu["lo"], rules["ci_lb_min_pp"], ">")
    clauses["b_point_floor"] = _clause(slu["point"] >= rules["slu_floor_pp"], slu["point"], rules["slu_floor_pp"], ">=")
    if rules["require_beat_twin"]:
        if twin is None:
            raise SelectionError("a twin column is required (same-flight A/A)")
        twin_point = twin["vs_lock"]["slu"]["point"]
        clauses["c_beats_twin"] = _clause(slu["point"] > twin_point, slu["point"], twin_point, ">")
    if parent is not None:
        if child.get("vs_parent") is not None:
            vs_parent = child["vs_parent"]["slu"]["point"]
        else:
            vs_parent = slu["point"] - parent["vs_lock"]["slu"]["point"]
        clauses["d_beats_parent"] = _clause(vs_parent > 0, vs_parent, 0.0, ">")
    clauses["e_intent_guard"] = _clause(
        intent["lo"] >= -rules["intent_guard_pp"] and intent["point"] >= rules["intent_point_floor_pp"],
        {"lo": intent["lo"], "point": intent["point"]},
        {"lo_min": -rules["intent_guard_pp"], "point_min": rules["intent_point_floor_pp"]},
        "lo>=lo_min and point>=point_min",
    )
    return Verdict(accepted=all(c["pass"] for c in clauses.values()), clauses=clauses)


def loop_complete(iterations_done: int) -> bool:
    """Stop rule: exactly three iterations, whatever happens (no early stop, no extension)."""

    return iterations_done >= STOP_AFTER_ITERATIONS


def next_iteration(iterations_done: int) -> int | None:
    return None if loop_complete(iterations_done) else iterations_done + 1


_ZERO = {"point": 0.0, "lo": 0.0, "hi": 0.0}


def curve(states: Iterable[Mapping[str, Any]], arm: str = "typed", iterations: int = STOP_AFTER_ITERATIONS) -> list[dict[str, Any]]:
    """One point per iteration: the best accepted state's cumulative SLU delta vs lock with
    CI (best = highest point, ties by state_id). An iteration with no accepted state repeats
    the previous level and is marked (``marked``: ``refused`` when a flown child was refused,
    ``unflown`` when nothing flew). Every flown child's own delta is listed beside it."""

    states = [s for s in states if s["arm"] == arm and s["iteration"] >= 1]
    points: list[dict[str, Any]] = []
    level, level_id = dict(_ZERO), None
    for t in range(1, iterations + 1):
        flown = sorted(
            (s for s in states if s["iteration"] == t and s["verdict"] in ("accepted", "refused") and s.get("credit") is not None),
            key=lambda s: s["state_id"],
        )
        accepted = [s for s in flown if s["verdict"] == "accepted"]
        marked = None
        if accepted:
            best = min(accepted, key=lambda s: (-s["credit"]["vs_lock"]["slu"]["point"], s["state_id"]))
            level = {k: best["credit"]["vs_lock"]["slu"][k] for k in ("point", "lo", "hi")}
            level_id = best["state_id"]
        else:
            marked = "refused" if flown else "unflown"
        points.append({
            "iteration": t, "level": dict(level), "state_id": level_id, "marked": marked,
            "flown_children": [
                {"state_id": s["state_id"], "operator_class": s["operator_class"], "verdict": s["verdict"],
                 "delta_vs_lock": dict(s["credit"]["vs_lock"]["slu"])}
                for s in flown
            ],
        })
    return points


__all__ = [
    "Verdict", "SelectionError", "select", "curve", "loop_complete", "next_iteration",
    "rules_from_floor_table", "DEFAULT_RULES", "STOP_AFTER_ITERATIONS",
]
