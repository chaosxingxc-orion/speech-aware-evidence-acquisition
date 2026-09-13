"""Pure custody checks for native episode delivery receipts.

The graph has two mutually exclusive delivery outcomes.  Legacy episodes end
only through an explicit Planner acceptance.  A prospectively configured
episode may instead deliver its latest valid Solver result after revision
exhaustion.  This module intentionally has no runtime or framework imports so
both sealing and post-seal readers apply the same receipt shape checks.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class NativeEpisodeDelivery:
    """The one Solver receipt that is authorized to supply final text."""

    kind: str
    solver_receipt: Mapping[str, object]
    final_contact: Mapping[str, object]
    terminal_disposition: Mapping[str, object] | None
    planner_route: Mapping[str, object] | None


def _raise(error_type: type[Exception], message: str) -> None:
    raise error_type(message)


def _sequence(
    value: object, label: str, *, error_type: type[Exception]
) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        _raise(error_type, f"{label} must be an ordered sequence")
    return value


def _receipt(
    value: object, label: str, *, error_type: type[Exception]
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        _raise(error_type, f"{label} must be a mapping")
    contacts = _sequence(value.get("contacts"), f"{label}.contacts", error_type=error_type)
    if not contacts or not all(isinstance(contact, Mapping) for contact in contacts):
        _raise(error_type, f"{label}.contacts must contain contact mappings")
    final_contact = value.get("final_contact")
    if not isinstance(final_contact, Mapping) or final_contact != contacts[-1]:
        _raise(error_type, f"{label}.final_contact must equal its last contact")
    return value


def validate_native_episode_delivery_receipt(
    receipt: Mapping[str, object],
    role_visits: Sequence[object] | None = None,
    planner_routes: Sequence[object] | None = None,
    *,
    terminal_actions: Sequence[str] | None = None,
    error_type: type[Exception] = ValueError,
) -> NativeEpisodeDelivery:
    """Validate and classify an accepted or exhaustion-terminal delivery.

    Callers remain responsible for validating contact hashes against their
    request/response custody.  This check establishes which exact Solver visit
    owns delivery, and for terminal delivery ties the disposition to the last
    Planner visit and route.  ``terminal_actions`` is supplied by the runtime
    from the composed configuration; a post-seal reader without that config
    can still reject a literal ``ACCEPT`` route and verify exact route custody.
    """
    if not isinstance(receipt, Mapping):
        _raise(error_type, "native episode receipt must be a mapping")

    if role_visits is None:
        role_visits = _sequence(
            receipt.get("role_visits"), "native role visits", error_type=error_type
        )
    if planner_routes is None:
        planner_routes = _sequence(
            receipt.get("planner_routes"), "Planner routes", error_type=error_type
        )
    accepted_present = receipt.get("accepted_solver_receipt") is not None
    terminal_present = receipt.get("terminal_solver_receipt") is not None
    if accepted_present == terminal_present:
        _raise(error_type, "native episode must contain exactly one delivery receipt")

    solver_visits: list[Mapping[str, object]] = []
    for raw_visit in role_visits:
        if not isinstance(raw_visit, Mapping):
            _raise(error_type, "native role visit must be a mapping")
        if raw_visit.get("stage") == "solver":
            solver_visits.append(raw_visit)
    if not solver_visits:
        _raise(error_type, "native episode has no Solver visit")
    latest_solver = _receipt(
        solver_visits[-1].get("execution_receipt"),
        "latest Solver execution receipt",
        error_type=error_type,
    )

    if accepted_present:
        accepted = _receipt(
            receipt.get("accepted_solver_receipt"),
            "accepted Solver receipt",
            error_type=error_type,
        )
        if accepted != latest_solver:
            _raise(error_type, "accepted Solver receipt is not the exact last Solver visit")
        return NativeEpisodeDelivery(
            kind="accepted",
            solver_receipt=accepted,
            final_contact=accepted["final_contact"],
            terminal_disposition=None,
            planner_route=None,
        )

    terminal = _receipt(
        receipt.get("terminal_solver_receipt"),
        "terminal Solver receipt",
        error_type=error_type,
    )
    if terminal != latest_solver:
        _raise(error_type, "terminal Solver receipt is not the exact last Solver visit")
    disposition = receipt.get("terminal_disposition")
    if not isinstance(disposition, Mapping):
        _raise(error_type, "terminal disposition must be a mapping")
    revision_count = disposition.get("revision_count")
    action = disposition.get("planner_action")
    if (
        disposition.get("reason") != "revision_limit"
        or isinstance(revision_count, bool)
        or not isinstance(revision_count, int)
        or revision_count < 0
        or not isinstance(action, str)
        or not action
        or disposition.get("planner_accepted") is not False
    ):
        _raise(error_type, "terminal disposition is malformed")

    routes = _sequence(planner_routes, "Planner routes", error_type=error_type)
    if not routes or not isinstance(routes[-1], Mapping):
        _raise(error_type, "terminal disposition requires a final Planner route")
    route = routes[-1]
    route_visit_index = route.get("role_visit_index")
    if (
        isinstance(route_visit_index, bool)
        or not isinstance(route_visit_index, int)
        or not 0 <= route_visit_index < len(role_visits)
        or not isinstance(role_visits[route_visit_index], Mapping)
        or role_visits[route_visit_index].get("stage") != "planner"
        or route.get("revision_count") != revision_count
        or route.get("action") != action
    ):
        _raise(error_type, "terminal disposition differs from the last Planner route")
    last_planner_index = max(
        (index for index, visit in enumerate(role_visits)
         if isinstance(visit, Mapping) and visit.get("stage") == "planner"),
        default=-1,
    )
    if route_visit_index != last_planner_index:
        _raise(error_type, "terminal disposition does not bind the last Planner visit")
    if terminal_actions is not None:
        allowed = tuple(terminal_actions)
        if len(allowed) != 2 or any(not isinstance(item, str) or not item for item in allowed):
            _raise(error_type, "configured terminal actions are malformed")
        if action not in allowed:
            _raise(error_type, "terminal Planner action is not a configured revise/acquire action")
    elif action == "ACCEPT":
        _raise(error_type, "terminal Planner action must not be ACCEPT")

    return NativeEpisodeDelivery(
        kind="terminal",
        solver_receipt=terminal,
        final_contact=terminal["final_contact"],
        terminal_disposition=disposition,
        planner_route=route,
    )


__all__ = ["NativeEpisodeDelivery", "validate_native_episode_delivery_receipt"]
