"""Acceptance / nomination (design spec task 6), under the coordinator's Q2 ruling
(``docs/superpowers/specs/2026-09-29-sealed-credit-inner-loop-run-1-design.md``,
"Coordinator rulings" section appended 2026-09-29):

    intent primary; the SLU guard is the READ design's null (the twin null for
    same-flight, the in-chain A/A null for cross-flight), not -0.10 pp;
    candidates are ranked by predicted intent gain, discarded if the predicted
    SLU change is below minus the guard; a candidate is nominated only if its
    predicted effect exceeds the floor of the design that will read it.

Both the guard and the floor are read from ``scripts/checks/stage3_effect_floor_
check.py``'s own ``FLOOR_TABLE`` / ``floor_for`` (imported, never copied -- design
spec task 6): the GUARD is ``floor_for(design, rows, purpose="harm", metric="slu")``
(the design's SLU sampling half-width alone -- owner decision 127's no-harm floor,
which for ``same-flight-supply-variant`` and ``same-flight-shadow-relisten`` IS the
twin/shadow null the ruling names, and for ``cross-flight-with-in-chain-
replicate`` IS the in-chain replicate's own sampling half-width); the FLOOR a
nominated candidate's predicted effect must exceed is ``floor_for(design, rows,
purpose="benefit", metric="intent")`` (the larger of the intent sampling
half-width and the rule-3 admission bar). Owner decision 190 (2026-09-29) put a
DIFFERENT number on each metric for the same-flight design family (intent 0.65,
SLU 1.49 pp at n = 1,080), so the guard and the floor read different anchors from
the same call site; a design with no per-metric floor ignores ``metric`` and
returns its one metric-blind number for both, as before decision 190. A
candidate whose predicted SLU delta is not modelled (``None``) is never
guard-discarded (the guard cannot be evaluated against nothing) but carries the
caveat.

Ranking: every candidate not guard-discarded, ordered by ``predicted_intent_pp``
descending (ties broken by knob id then value, for determinism). Nomination: the
HIGHEST-ranked candidate that ALSO clears its floor; ``None`` (and a stated
reason) when no candidate clears. Claim ceiling is always ``"nominated"`` -- a
same-flight read never admits (the same-flight-supply-variant instrument
design's own Q6 ruling, cited by this design spec's section 2e); this module
never writes ``"admitted"``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping


class AcceptError(RuntimeError):
    pass


def _floor_gate(repo_root: Path):
    checks_dir = repo_root / "scripts" / "checks"
    if str(checks_dir) not in sys.path:
        sys.path.insert(0, str(checks_dir))
    spec = importlib.util.spec_from_file_location("stage3_effect_floor_check", checks_dir / "stage3_effect_floor_check.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Registered in sys.modules BEFORE exec: this module's ``@dataclass class Floor``
    # needs ``sys.modules[cls.__module__]`` to resolve during class creation (Python's
    # dataclasses._is_type), which otherwise fails with a bare AttributeError.
    sys.modules["stage3_effect_floor_check"] = module
    spec.loader.exec_module(module)
    return module


def design_guard_and_floor(design: str, rows: int, repo_root: Path) -> dict[str, Any]:
    """The SLU guard and the intent floor for one read design, at ``rows``.

    Owner decision 190 (2026-09-29) put a per-metric floor on the same-flight
    design family: the intent floor and the SLU guard are no longer the same
    metric-blind number. Per the coordinator's Q2 ruling (module docstring),
    ranking is by predicted intent gain and the guard bounds predicted SLU
    loss, so the floor is read with ``metric="intent"`` and the guard with
    ``metric="slu"``. A design with no per-metric floor (``sampling_by_metric``
    empty) ignores ``metric`` entirely and returns the same number for both,
    as before decision 190.
    """

    gate = _floor_gate(repo_root)
    if design not in gate.FLOOR_TABLE:
        raise AcceptError(f"read design {design!r} is not in stage3_effect_floor_check.FLOOR_TABLE")
    guard_pp, guard_lines = gate.floor_for(design, rows, purpose="harm", metric="slu")
    floor_pp, floor_lines = gate.floor_for(design, rows, purpose="benefit", metric="intent")
    return {
        "design": design, "rows": rows,
        "guard_pp": guard_pp, "guard_arithmetic": guard_lines,
        "floor_pp": floor_pp, "floor_arithmetic": floor_lines,
        "source": "scripts/checks/stage3_effect_floor_check.py FLOOR_TABLE / floor_for",
    }


def score_candidate(estimate: Mapping[str, Any], design_bounds: Mapping[str, Any]) -> dict[str, Any]:
    guard_pp, floor_pp = design_bounds["guard_pp"], design_bounds["floor_pp"]
    slu_pp = estimate.get("predicted_slu_pp")
    if slu_pp is None:
        guard_discarded = False
        guard_note = "SLU guard not evaluated: predicted_slu_pp is not modelled for this conversion source"
    else:
        guard_discarded = slu_pp < -guard_pp
        guard_note = f"predicted SLU {slu_pp:+.4f} pp vs guard -{guard_pp:.4f} pp"
    clears_floor = (
        not estimate["unobserved"]
        and floor_pp is not None
        and estimate["predicted_intent_pp"] > floor_pp
    )
    return {
        **estimate,
        "read_design": design_bounds["design"],
        "read_rows": design_bounds["rows"],
        "guard_pp": guard_pp,
        "floor_pp": floor_pp,
        "guard_discarded": guard_discarded,
        "guard_note": guard_note,
        "clears_floor": clears_floor,
    }


def rank_candidates(
    estimates: list[Mapping[str, Any]], design: str, rows: int, repo_root: Path,
) -> list[dict[str, Any]]:
    """Every candidate, scored against ``design``'s guard/floor at ``rows``, in
    ranked order (guard-discarded candidates sort last, by predicted_intent_pp
    within each group, ties broken by knob id then value for determinism)."""

    bounds = design_guard_and_floor(design, rows, repo_root)
    scored = [score_candidate(e, bounds) for e in estimates]
    scored.sort(key=lambda c: (
        c["guard_discarded"],
        -c["predicted_intent_pp"],
        c["knob_id"],
        json.dumps(c["value"], sort_keys=True),
    ))
    for rank, candidate in enumerate(scored, start=1):
        candidate["rank"] = rank
    return scored


def nominate(ranked: list[dict[str, Any]]) -> dict[str, Any]:
    """The highest-ranked candidate that is not guard-discarded and clears its
    floor, or ``{"nominated": False, ...}`` when none does."""

    clearing = [c for c in ranked if not c["guard_discarded"] and c["clears_floor"]]
    # Run 3: a candidate whose line is ``admitted`` or ``closed`` (policy-space value status) is
    # ranked and composed but never nominated; the ones that would have cleared are listed.
    eligible = [c for c in clearing if c.get("status", "open") == "open"]
    skipped = [
        {"knob_id": c["knob_id"], "value": c["value"], "status": c["status"], "rank": c["rank"],
         "predicted_intent_pp": c["predicted_intent_pp"]}
        for c in clearing if c.get("status", "open") != "open"
    ]
    extra = {"cleared_but_not_open": skipped} if skipped else {}
    if not eligible:
        if skipped:
            reason = "no open candidate clears its read design's floor after the SLU guard"
        elif any(not c["guard_discarded"] for c in ranked):
            reason = "no candidate clears its read design's floor after the SLU guard"
        else:
            reason = "every candidate was discarded by the SLU guard"
        return {
            "nominated": False,
            "reason": reason,
            "candidates_considered": len(ranked),
            **extra,
        }
    top = min(eligible, key=lambda c: c["rank"])
    return {
        "nominated": True,
        "claim_ceiling": "nominated",
        "candidate": top,
        "candidates_considered": len(ranked),
        **extra,
    }


def score_compositions(
    estimates: list[Mapping[str, Any]], compositions: list[Mapping[str, Any]],
    design: str, rows: int, repo_root: Path,
) -> list[dict[str, Any]]:
    """Composed policies (run 2; the design spec's coordinator ruling Q4 deferred them from run
    1): each named composition lists ``{"knob_id", "value"}`` components; their single-knob
    estimates are summed by ``estimate.compose`` (which refuses two components on one node) and
    the sum is scored against ``design``'s guard and floor exactly like a single candidate.

    The sum is ADDITIVE: rows two components both act on are not de-duplicated for cited or
    pool-pair sources, so for same-direction components the sum is an upper bound and every
    composition carries that caveat. A composition naming an unknown (knob, value) is refused.
    """

    from speech_aware_evidence_acquisition.analysis.sealed_credit import estimate as est

    bounds = design_guard_and_floor(design, rows, repo_root)
    index = {(e["knob_id"], json.dumps(e["value"], sort_keys=True)): e for e in estimates}
    out = []
    for comp in compositions:
        parts = []
        for component in comp["components"]:
            key = (component["knob_id"], json.dumps(component["value"], sort_keys=True))
            if key not in index:
                raise AcceptError(
                    f"composition {comp['id']!r}: no estimate for knob {component['knob_id']!r} "
                    f"value {component['value']!r}"
                )
            parts.append(index[key])
        composed = est.compose(parts)
        scored = score_candidate(
            {"knob_id": comp["id"], "value": [c["value"] for c in comp["components"]],
             "predicted_intent_pp": composed["predicted_intent_pp"],
             "predicted_slu_pp": composed["predicted_slu_pp"], "unobserved": composed["unobserved"]},
            bounds,
        )
        out.append({
            "id": comp["id"], "note": comp.get("note", ""),
            "components": [
                {"knob_id": c["knob_id"], "value": c["value"], "node": c["node"],
                 "predicted_intent_pp": c["predicted_intent_pp"], "predicted_slu_pp": c["predicted_slu_pp"],
                 "unobserved": c["unobserved"]}
                for c in composed["components"]
            ],
            "predicted_intent_pp": composed["predicted_intent_pp"],
            "predicted_slu_pp": composed["predicted_slu_pp"],
            "unobserved_component": composed["unobserved"],
            "read_design": design, "read_rows": rows,
            "guard_pp": bounds["guard_pp"], "floor_pp": bounds["floor_pp"],
            "guard_discarded": scored["guard_discarded"], "guard_note": scored["guard_note"],
            "clears_floor": (not scored["guard_discarded"]
                             and bounds["floor_pp"] is not None
                             and composed["predicted_intent_pp"] > bounds["floor_pp"]),
            "caveat": "additive sum of single-knob estimates; overlapping rows are not de-duplicated",
        })
    return out


__all__ = [
    "AcceptError", "design_guard_and_floor", "score_candidate", "rank_candidates", "nominate",
    "score_compositions",
]
