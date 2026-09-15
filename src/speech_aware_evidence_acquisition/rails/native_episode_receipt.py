"""Pure custody checks for native episode delivery receipts.

Legacy episodes end through explicit Planner acceptance or configured
revision exhaustion. A separately configured finite completion may retain
the last completed Solver or derive an empty abstention when none exists.  This module intentionally has no runtime or framework imports so
both sealing and post-seal readers apply the same receipt shape checks.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class NativeEpisodeDelivery:
    """The delivered Solver receipt, or rejected source for explicit abstention."""

    kind: str
    solver_receipt: Mapping[str, object] | None
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


def _validate_planner_control(receipt, visits, routes, *, error_type):
    raw = receipt.get("plan")
    control = receipt.get("planner_control")
    if control is None:
        return
    if not isinstance(raw, str) or not isinstance(control, Mapping) or set(control) != {"action"}:
        _raise(error_type, "structured Planner control is malformed")

    def unique_object(pairs):
        document = {}
        for key, value in pairs:
            if key in document:
                raise ValueError("duplicate key")
            document[key] = value
        return document

    try:
        parsed = json.loads(raw, object_pairs_hook=unique_object)
    except (TypeError, ValueError):
        _raise(error_type, "structured Planner control differs from raw output")
    if parsed != dict(control) or set(parsed) != {"action"} or not isinstance(parsed["action"], str):
        _raise(error_type, "structured Planner control differs from raw output")
    planner_indices = [
        index for index, visit in enumerate(visits)
        if isinstance(visit, Mapping) and visit.get("stage") == "planner"
    ]
    if not planner_indices or not routes or not isinstance(routes[-1], Mapping):
        _raise(error_type, "structured Planner control has no final route")
    planner_receipt = _receipt(
        visits[planner_indices[-1]].get("execution_receipt"),
        "structured Planner execution receipt",
        error_type=error_type,
    )
    if (
        hashlib.sha256(raw.encode()).hexdigest()
        != planner_receipt["final_contact"].get("response_text_sha256")
        or routes[-1].get("action") != parsed["action"]
    ):
        _raise(error_type, "structured Planner control lacks raw source custody")


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
    _validate_planner_control(
        receipt, role_visits, planner_routes, error_type=error_type
    )
    disposition = receipt.get("terminal_disposition")
    if (
        isinstance(disposition, Mapping) and disposition.get("reason") == "finite_completion"
        or receipt.get("abstention_receipt") is not None
        or receipt.get("interrupted_role") is not None
    ):
        return _finite_delivery(receipt, role_visits, error_type=error_type)
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
        if receipt.get("terminal_disposition") is not None:
            _raise(error_type, "accepted delivery must not carry a terminal disposition")
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
        if (
            len(allowed) not in {2, 3}
            or any(not isinstance(item, str) or not item for item in allowed)
            or len(set(allowed)) != len(allowed)
        ):
            _raise(error_type, "configured terminal actions are malformed")
        if action not in allowed:
            label = "revise/acquire action" if len(allowed) == 2 else "continuation action"
            _raise(error_type, f"terminal Planner action is not a configured {label}")
    elif action == "ACCEPT":
        _raise(error_type, "terminal Planner action must not be ACCEPT")

    return NativeEpisodeDelivery(
        kind="terminal",
        solver_receipt=terminal,
        final_contact=terminal["final_contact"],
        terminal_disposition=disposition,
        planner_route=route,
    )


def validate_native_candidate_refresh_receipt(
    receipt: Mapping[str, object], *,
    refresh_action: str, max_refreshes: int, max_revisions: int,
    accept_action: str, revise_action: str,
    error_type: type[Exception] = ValueError,
) -> int:
    """Bind each executed refresh to an actual Perception-before-Solver visit."""
    if (
        not isinstance(refresh_action, str) or not refresh_action
        or isinstance(max_refreshes, bool) or not isinstance(max_refreshes, int)
        or isinstance(max_revisions, bool) or not isinstance(max_revisions, int)
        or not 1 <= max_refreshes <= max_revisions
        or refresh_action in {accept_action, revise_action}
    ):
        _raise(error_type, "invalid candidate refresh receipt configuration")
    if not isinstance(receipt, Mapping):
        _raise(error_type, "candidate refresh receipt must be a mapping")
    disposition = receipt.get("terminal_disposition")
    if isinstance(disposition, Mapping) and disposition.get("reason") == "finite_completion":
        return validate_native_episode_finite_path(
            receipt, max_revisions=max_revisions, accept_action=accept_action,
            revise_action=revise_action, refresh_action=refresh_action,
            max_refreshes=max_refreshes, error_type=error_type,
        )
    visits = _sequence(receipt.get("role_visits"), "native role visits", error_type=error_type)
    routes = _sequence(receipt.get("planner_routes"), "Planner routes", error_type=error_type)
    if not visits or not all(isinstance(v, Mapping) for v in visits):
        _raise(error_type, "candidate refresh requires structured role visits")
    if visits[0].get("stage") != "perception":
        _raise(error_type, "candidate refresh requires the initial Perception visit")
    cursor, refreshes = 1, 0
    if not routes or len(routes) - 1 > max_revisions:
        _raise(error_type, "candidate refresh exceeds the revision allowance")
    for revision, route in enumerate(routes):
        if (
            not isinstance(route, Mapping)
            or isinstance(route.get("revision_count"), bool)
            or not isinstance(route.get("revision_count"), int)
            or route.get("revision_count") != revision
            or isinstance(route.get("role_visit_index"), bool)
            or not isinstance(route.get("role_visit_index"), int)
            or route.get("role_visit_index") != cursor + 2
            or [v.get("stage") for v in visits[cursor:cursor + 3]]
            != ["solver", "review", "planner"]
        ):
            _raise(error_type, "candidate refresh has an invalid ordered role/route binding")
        cursor += 3
        action = route.get("action")
        if revision == len(routes) - 1:
            delivery = validate_native_episode_delivery_receipt(receipt, error_type=error_type)
            if delivery.kind == "accepted" and action != accept_action:
                _raise(error_type, "candidate refresh accepted delivery has no final acceptance")
            if delivery.kind == "terminal" and revision != max_revisions:
                _raise(error_type, "candidate refresh terminated before the revision allowance")
            continue
        if action == refresh_action:
            if cursor >= len(visits) or visits[cursor].get("stage") != "perception":
                _raise(error_type, "candidate refresh route has no following Perception")
            refreshes += 1
            cursor += 1
        elif action != revise_action:
            _raise(error_type, "candidate refresh graph has an unsupported continuation")
        if refreshes > max_refreshes:
            _raise(error_type, "candidate refresh exceeds its configured allowance")
    if cursor != len(visits):
        _raise(error_type, "candidate refresh has extra or unaccounted role visits")
    return refreshes



_CONTACT_FIELDS = (
    "agent_contact_id", "request_id", "request_sha256",
    "response_sha256", "response_text_sha256",
)


def _checked_contact(value, *, error_type):
    if not isinstance(value, Mapping):
        _raise(error_type, "finite contact must be a mapping")
    for key in _CONTACT_FIELDS:
        item = value.get(key)
        if not isinstance(item, str) or not item:
            _raise(error_type, "finite contact lacks source identity")
        if key.endswith("sha256") and (
            len(item) != 64 or any(c not in "0123456789abcdef" for c in item)
        ):
            _raise(error_type, "finite contact has an invalid source hash")
    return value


def _finite_delivery(receipt, visits, *, error_type):
    disposition = receipt.get("terminal_disposition")
    if not isinstance(disposition, Mapping) or set(disposition) != {
        "reason", "finish_reason", "role_id", "stage", "revision_count",
        "planner_accepted", "rejected_contact",
    }:
        _raise(error_type, "finite terminal disposition is malformed")
    if (
        disposition["reason"] != "finite_completion"
        or disposition["finish_reason"] not in ("length", "content_filter")
        or disposition["stage"] not in ("perception", "solver", "review", "planner", "acquisition")
        or not isinstance(disposition["role_id"], str) or not disposition["role_id"]
        or isinstance(disposition["revision_count"], bool)
        or not isinstance(disposition["revision_count"], int)
        or disposition["revision_count"] < 0
        or disposition["planner_accepted"] is not False
        or receipt.get("accepted_solver_receipt") is not None
    ):
        _raise(error_type, "finite terminal disposition has invalid authority")
    rejected = _checked_contact(disposition["rejected_contact"], error_type=error_type)
    interrupted = receipt.get("interrupted_role")
    if (
        not isinstance(interrupted, Mapping)
        or interrupted.get("role_id") != disposition["role_id"]
        or interrupted.get("stage") != disposition["stage"]
    ):
        _raise(error_type, "finite disposition differs from its interrupted role")
    execution = _receipt(interrupted.get("execution_receipt"), "interrupted role", error_type=error_type)
    if execution["final_contact"] != rejected:
        _raise(error_type, "finite disposition differs from its rejected contact")
    used = set()
    solvers = []
    for visit in visits:
        if not isinstance(visit, Mapping):
            _raise(error_type, "finite episode role visit must be a mapping")
        prior = _receipt(visit.get("execution_receipt"), "completed role", error_type=error_type)
        for contact in prior["contacts"]:
            _checked_contact(contact, error_type=error_type)
            pair = contact["agent_contact_id"], contact["request_id"]
            if pair in used:
                _raise(error_type, "finite episode duplicates completed contacts")
            used.add(pair)
        if visit.get("stage") == "solver":
            solvers.append(prior)
    for contact in execution["contacts"]:
        _checked_contact(contact, error_type=error_type)
        pair = contact["agent_contact_id"], contact["request_id"]
        if pair in used:
            _raise(error_type, "interrupted role repeats a completed contact")
        used.add(pair)
    terminal = receipt.get("terminal_solver_receipt")
    abstention = receipt.get("abstention_receipt")
    if solvers:
        if terminal != solvers[-1] or abstention is not None:
            _raise(error_type, "finite delivery must retain the last completed Solver")
        return NativeEpisodeDelivery("finite", terminal, terminal["final_contact"], disposition, None)
    if terminal is not None or abstention != {"source_contact": rejected}:
        _raise(error_type, "finite episode without a Solver requires a bound abstention")
    return NativeEpisodeDelivery("abstention", None, rejected, disposition, None)


def validate_native_episode_terminal_policy(
    delivery, *, exhaustion_policy, finite_completion_policy, max_revisions,
    error_type=ValueError,
):
    """Require prospective configuration for either kind of terminal delivery."""
    if delivery.kind == "accepted":
        return
    disposition = delivery.terminal_disposition
    if isinstance(max_revisions, bool) or not isinstance(max_revisions, int) or max_revisions < 0:
        _raise(error_type, "invalid configured revision allowance")
    if delivery.kind == "terminal":
        if (
            exhaustion_policy != "deliver-latest-solver"
            or disposition["revision_count"] != max_revisions
        ):
            _raise(error_type, "terminal delivery differs from its configured policy")
    elif delivery.kind in {"finite", "abstention"}:
        if (
            finite_completion_policy != "deliver-latest-or-abstain"
            or not 0 <= disposition["revision_count"] <= max_revisions
        ):
            _raise(error_type, "finite delivery differs from its configured policy")
    else:
        _raise(error_type, "unknown native delivery kind")


def validate_native_episode_finite_path(
    receipt, *, max_revisions, accept_action, revise_action,
    refresh_action=None, max_refreshes=0, error_type=ValueError,
):
    """Validate a completed graph prefix and its exact next interrupted role."""
    delivery = validate_native_episode_delivery_receipt(receipt, error_type=error_type)
    if delivery.kind not in {"finite", "abstention"}:
        _raise(error_type, "finite path requires a finite delivery")
    if isinstance(max_revisions, bool) or not isinstance(max_revisions, int) or max_revisions < 0:
        _raise(error_type, "invalid finite path revision allowance")
    visits = receipt["role_visits"]
    routes = _sequence(receipt["planner_routes"], "finite Planner routes", error_type=error_type)
    terminal = delivery.terminal_disposition
    cursor = route_index = revision = refreshes = 0

    def stopped(stage):
        if (
            terminal["stage"] != stage or terminal["revision_count"] != revision
            or route_index != len(routes)
        ):
            _raise(error_type, "finite role or revision differs from the actual graph prefix")
        return refreshes

    def consume(stage):
        nonlocal cursor
        if visits[cursor].get("stage") != stage:
            _raise(error_type, "finite path has an invalid completed role order")
        cursor += 1

    if not visits:
        return stopped("perception")
    consume("perception")
    while True:
        for stage in ("solver", "review", "planner"):
            if cursor == len(visits):
                return stopped(stage)
            consume(stage)
        if route_index >= len(routes):
            _raise(error_type, "finite path omits an actual Planner route")
        route = routes[route_index]
        if (
            not isinstance(route, Mapping)
            or isinstance(route.get("revision_count"), bool)
            or not isinstance(route.get("revision_count"), int)
            or route.get("revision_count") != revision
            or isinstance(route.get("role_visit_index"), bool)
            or not isinstance(route.get("role_visit_index"), int)
            or route.get("role_visit_index") != cursor - 1
        ):
            _raise(error_type, "finite path has an invalid Planner route")
        action = route.get("action")
        if action == accept_action or revision >= max_revisions:
            _raise(error_type, "finite path continues after a terminal Planner route")
        route_index += 1
        revision += 1
        if refresh_action is not None and action == refresh_action:
            if refreshes >= max_refreshes:
                _raise(error_type, "finite path exceeds its candidate refresh allowance")
            if cursor == len(visits):
                return stopped("perception")
            consume("perception")
            refreshes += 1
        elif action != revise_action:
            _raise(error_type, "finite path has an unsupported Planner continuation")


__all__ = [
    "NativeEpisodeDelivery", "validate_native_episode_delivery_receipt",
    "validate_native_candidate_refresh_receipt", "validate_native_episode_terminal_policy",
    "validate_native_episode_finite_path",
]
