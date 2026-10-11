"""Deterministic parent choice and the edit budget L_t (spec section 1.3).

parent = the ACCEPTED state (the lock root counts as accepted with a zero lower bound)
maximising::

    score = LB_slu(state - lock) - CHILD_PENALTY_PP * n_children(state)

``n_children`` counts the state's FLOWN children (accepted + refused); proposed-not-flown
children carry no measurement and do not count. Ties break by the smaller ``state_id``
(lexicographic). A parent with at least ``MASK_AFTER_REFUSED`` refused children of one
operator class has that class masked for the next proposal under that parent.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

CHILD_PENALTY_PP = 0.25
MASK_AFTER_REFUSED = 2


def edit_budget(iteration: int) -> int:
    """L_t: at most 2 operator applications in iteration 1, 1 afterwards."""

    if not isinstance(iteration, int) or isinstance(iteration, bool) or iteration < 1:
        raise ValueError("iteration must be an integer >= 1")
    return 2 if iteration == 1 else 1


def _lower_bound(state: Mapping[str, Any]) -> float:
    if state["iteration"] == 0 or state.get("credit") is None:
        return 0.0
    return float(state["credit"]["vs_lock"]["slu"]["lo"])


def _flown_children(states: Iterable[Mapping[str, Any]], state_id: str) -> list[Mapping[str, Any]]:
    # an unmeasured refusal (no credit vector) is not a flown child
    return [s for s in states if s["parent_id"] == state_id and s["verdict"] in ("accepted", "refused")
            and s.get("credit") is not None]


def masked_classes(states: Iterable[Mapping[str, Any]], parent_id: str) -> list[str]:
    counts: dict[str, int] = {}
    for s in states:
        if (s["parent_id"] == parent_id and s["verdict"] == "refused" and s.get("operator_class")
                and s.get("credit") is not None):
            counts[s["operator_class"]] = counts.get(s["operator_class"], 0) + 1
    return sorted(c for c, n in counts.items() if n >= MASK_AFTER_REFUSED)


def choose_parent(
    states: Iterable[Mapping[str, Any]], arm: str = "typed", penalty_pp: float = CHILD_PENALTY_PP,
) -> dict[str, Any]:
    """Choose the parent among ``arm``'s accepted states (plus the root, iteration 0)."""

    states = list(states)
    eligible = [
        s for s in states
        if s["arm"] == arm and (s["iteration"] == 0 or s["verdict"] == "accepted")
    ]
    if not eligible:
        raise ValueError(f"no root or accepted state for arm {arm!r}")
    ranking = []
    for s in eligible:
        n_children = len(_flown_children(states, s["state_id"]))
        lb = _lower_bound(s)
        ranking.append({
            "state_id": s["state_id"], "lb_slu_pp": lb, "n_children": n_children,
            "score": lb - penalty_pp * n_children,
        })
    ranking.sort(key=lambda r: (-r["score"], r["state_id"]))
    best = ranking[0]
    return {
        "parent_id": best["state_id"], "score": best["score"],
        "masked_classes": masked_classes(states, best["state_id"]),
        "penalty_pp": penalty_pp, "ranking": ranking,
    }


__all__ = ["edit_budget", "choose_parent", "masked_classes", "CHILD_PENALTY_PP", "MASK_AFTER_REFUSED"]
