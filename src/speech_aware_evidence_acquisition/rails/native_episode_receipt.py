"""Pure custody checks for native episode delivery receipts.

Legacy episodes end through explicit Planner acceptance or configured
revision exhaustion. A separately configured finite completion may retain
the last completed Solver or derive an empty abstention when none exists.  This module intentionally has no runtime or framework imports so
both sealing and post-seal readers apply the same receipt shape checks.
"""

from __future__ import annotations

import dataclasses
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
    # Item E22 (the ReAct-exhaustion disposition, not the Earnings-22
    # carrier), 2026-09-19: the row's ``react_exhaustion`` block, or ``None``
    # when no visit of this row exhausted its ReAct loop -- which is every
    # row sealed before E22 and every row on the null arm. It is a VISIT
    # disposition and NOT a delivery kind: a row that carries it still
    # delivers through whichever of the five kinds above it took. Declared
    # LAST and defaulted so every positional construction in this module,
    # and every reader written before E22, composes exactly what it did.
    react_exhaustion: Mapping[str, object] | None = None


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


#: E8c: the ``planner_routes`` disposition a row takes when the Planner
#: named no registered action.  Mirrors
#: ``reproduction.ojw.native_episode.PLANNER_ACTION_ILLEGAL_DISPOSITION``;
#: this module keeps no runtime import, so the name is restated here.
PLANNER_ACTION_ILLEGAL_DISPOSITION = "planner_action_illegal"


def is_illegal_planner_route(route: object) -> bool:
    """Is this route the E8c row-level illegal-Planner-output disposition?

    Such a route seals its row through the same explicit acceptance an
    ``ACCEPT`` takes -- the committed draft, unchanged -- so its ``action``
    is the truncated malformed token and is deliberately NOT one of the
    configured actions.
    """
    return (
        isinstance(route, Mapping)
        and route.get("legal") is False
        and route.get("disposition") == PLANNER_ACTION_ILLEGAL_DISPOSITION
    )


#: Item E22 (the ReAct-exhaustion disposition, not the Earnings-22 carrier):
#: the receipt key and schema of a row one of whose tool roles spent its
#: whole ReAct iteration budget on tool calls without producing an answer.
#: Restated here for the same reason
#: :data:`PLANNER_ACTION_ILLEGAL_DISPOSITION` is: this module keeps no
#: runtime import.
REACT_EXHAUSTION_DISPOSITION = "react_exhaustion"
REACT_EXHAUSTION_SCHEMA = "saea-native-react-exhaustion-v1"

#: The exact field set of one exhausted VISIT record.
_REACT_EXHAUSTION_VISIT_FIELDS = frozenset({
    "role_id", "stage", "role_visit_index", "revision_count",
    "iterations_used", "max_iterations", "identical_calls", "calls",
    "last_observation_sha256",
})

#: The exact field set of one recorded call.
_REACT_EXHAUSTION_CALL_FIELDS = frozenset({"tool_id", "arguments_sha256"})

#: The stages an exhausted visit may belong to, restated from
#: ``reproduction.ojw.native_episode.REACT_EXHAUSTION_STAGES``.
_REACT_EXHAUSTION_STAGES = ("review",)


def _sha256_text(value: object, label: str, *, error_type) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _raise(error_type, f"{label} must be a lowercase 64-hex SHA-256")
    return value


def _validate_react_exhaustion(receipt, visits, *, error_type):
    """E22: the row's exhausted-visit block, validated and bound, or ``None``.

    A row without the key is every row sealed before E22 and every row on
    the null arm, and returns ``None`` without reading anything else. A row
    WITH it must name real visits of this row: each record's
    ``role_visit_index`` must address a ``role_visits`` entry whose
    ``stage`` and ``role_id`` are the record's own, so an exhaustion can
    never be claimed for a visit that did not happen.
    """

    block = receipt.get(REACT_EXHAUSTION_DISPOSITION)
    if block is None:
        return None
    if (
        not isinstance(block, Mapping)
        or set(block) != {"schema", "count", "visits"}
        or block["schema"] != REACT_EXHAUSTION_SCHEMA
    ):
        _raise(error_type, "ReAct exhaustion block is malformed")
    records = _sequence(
        block["visits"], "ReAct exhaustion visits", error_type=error_type
    )
    count = block["count"]
    if (
        isinstance(count, bool)
        or not isinstance(count, int)
        or count != len(records)
        or not records
    ):
        _raise(error_type, "ReAct exhaustion count differs from its visits")
    seen_indices: set[int] = set()
    for record in records:
        if (
            not isinstance(record, Mapping)
            or set(record) != _REACT_EXHAUSTION_VISIT_FIELDS
        ):
            _raise(error_type, "ReAct exhaustion visit is malformed")
        index = record["role_visit_index"]
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or not 0 <= index < len(visits)
            or index in seen_indices
            or not isinstance(visits[index], Mapping)
            or visits[index].get("stage") != record["stage"]
            or visits[index].get("role_id") != record["role_id"]
        ):
            _raise(
                error_type,
                "ReAct exhaustion visit does not bind an actual role visit",
            )
        seen_indices.add(index)
        if record["stage"] not in _REACT_EXHAUSTION_STAGES:
            _raise(error_type, "ReAct exhaustion names an inadmissible stage")
        if not isinstance(record["role_id"], str) or not record["role_id"]:
            _raise(error_type, "ReAct exhaustion visit has no role id")
        if record["identical_calls"] not in (True, False):
            _raise(error_type, "ReAct exhaustion identical_calls must be a boolean")
        _nonneg_int(
            record["revision_count"], "ReAct exhaustion revision_count",
            error_type=error_type,
        )
        used, ceiling = record["iterations_used"], record["max_iterations"]
        _nonneg_int(used, "ReAct exhaustion iterations_used", error_type=error_type)
        _nonneg_int(ceiling, "ReAct exhaustion max_iterations", error_type=error_type)
        if used != ceiling or ceiling < 1:
            _raise(
                error_type,
                "ReAct exhaustion must spend its whole declared iteration budget",
            )
        calls = _sequence(
            record["calls"], "ReAct exhaustion calls", error_type=error_type
        )
        if not calls:
            _raise(error_type, "ReAct exhaustion records no tool call")
        signatures = set()
        for call in calls:
            if (
                not isinstance(call, Mapping)
                or set(call) != _REACT_EXHAUSTION_CALL_FIELDS
                or not isinstance(call["tool_id"], str)
                or not call["tool_id"]
            ):
                _raise(error_type, "ReAct exhaustion call is malformed")
            digest = _sha256_text(
                call["arguments_sha256"], "ReAct exhaustion arguments_sha256",
                error_type=error_type,
            )
            signatures.add((call["tool_id"], digest))
        if record["identical_calls"] is not (len(signatures) == 1):
            _raise(
                error_type,
                "ReAct exhaustion identical_calls differs from its own calls",
            )
        observation = record["last_observation_sha256"]
        if observation is not None:
            _sha256_text(
                observation, "ReAct exhaustion last_observation_sha256",
                error_type=error_type,
            )
    return block


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
    # E22: a VISIT-level disposition, so it is read here -- once, for every
    # delivery kind -- and carried beside whichever kind the row took. A row
    # without the key reads ``None`` and composes exactly its pre-E22
    # delivery.
    exhaustion = _validate_react_exhaustion(
        receipt, role_visits, error_type=error_type
    )

    def _with_exhaustion(delivery: NativeEpisodeDelivery) -> NativeEpisodeDelivery:
        if exhaustion is None:
            return delivery
        return dataclasses.replace(delivery, react_exhaustion=exhaustion)

    disposition = receipt.get("terminal_disposition")
    if (
        isinstance(disposition, Mapping)
        and disposition.get("reason") == CONTEXT_COMPACTION_DISPOSITION
    ):
        # E20: checked BEFORE the finite branch, because a context-fit row
        # carries the same ``interrupted_role``/``abstention_receipt``
        # marks and would otherwise be read as a malformed finite row.
        return _with_exhaustion(
            _context_fit_delivery(receipt, role_visits, error_type=error_type)
        )
    if (
        isinstance(disposition, Mapping) and disposition.get("reason") == "finite_completion"
        or receipt.get("abstention_receipt") is not None
        or receipt.get("interrupted_role") is not None
    ):
        return _with_exhaustion(
            _finite_delivery(receipt, role_visits, error_type=error_type)
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
        if receipt.get("terminal_disposition") is not None:
            _raise(error_type, "accepted delivery must not carry a terminal disposition")
        accepted = _receipt(
            receipt.get("accepted_solver_receipt"),
            "accepted Solver receipt",
            error_type=error_type,
        )
        if accepted != latest_solver:
            _raise(error_type, "accepted Solver receipt is not the exact last Solver visit")
        return _with_exhaustion(
            NativeEpisodeDelivery(
                kind="accepted",
                solver_receipt=accepted,
                final_contact=accepted["final_contact"],
                terminal_disposition=None,
                planner_route=None,
            )
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

    return _with_exhaustion(
        NativeEpisodeDelivery(
            kind="terminal",
            solver_receipt=terminal,
            final_contact=terminal["final_contact"],
            terminal_disposition=disposition,
            planner_route=route,
        )
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
            if (
                delivery.kind == "accepted"
                and action != accept_action
                # E8c: an illegal Planner output ends the row through the
                # same explicit acceptance, so the final route is the
                # disposition rather than the configured accept action.
                and not is_illegal_planner_route(route)
            ):
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


#: E20 (2026-09-19): the ``terminal_disposition.reason`` of a row whose
#: next request did not fit the live serving slot. Restated here for the
#: same reason :data:`PLANNER_ACTION_ILLEGAL_DISPOSITION` is: this module
#: keeps no runtime import.
CONTEXT_COMPACTION_DISPOSITION = "context_compaction"

#: The exact field set of that disposition.
_CONTEXT_DISPOSITION_FIELDS = frozenset({
    "reason", "role_id", "stage", "revision_count", "planner_accepted",
    "compaction_pass", "dropped_identifiers", "tokens_before", "tokens_after",
    "limit_tokens", "source", "server_message",
})

#: The two seams that may refuse a request for width.
_CONTEXT_REFUSAL_SOURCES = ("dispatch-budget", "server-refusal")

#: The identifier prefixes a compaction may drop, restated from
#: ``rails.context_budget._DROPPABLE_IDENTIFIER_PREFIXES``.
_CONTEXT_DROPPABLE_PREFIXES = ("agent-state:", "facet:", "value:")


def _context_fit_delivery(receipt, visits, *, error_type):
    """E20: validate a retained row whose next request was too wide.

    Built to the E13 contract with one forced difference: there is NO
    rejected contact, because the refused request was never answered. The
    interrupted role therefore carries an execution receipt only when the
    role had already completed a contact of its own.
    """

    disposition = receipt.get("terminal_disposition")
    if (
        not isinstance(disposition, Mapping)
        or set(disposition) != _CONTEXT_DISPOSITION_FIELDS
    ):
        _raise(error_type, "context-fit terminal disposition is malformed")
    if (
        disposition["reason"] != CONTEXT_COMPACTION_DISPOSITION
        or disposition["stage"] not in (
            "perception", "solver", "review", "planner", "acquisition"
        )
        or not isinstance(disposition["role_id"], str) or not disposition["role_id"]
        or isinstance(disposition["revision_count"], bool)
        or not isinstance(disposition["revision_count"], int)
        or disposition["revision_count"] < 0
        or disposition["planner_accepted"] is not False
        or isinstance(disposition["compaction_pass"], bool)
        or not isinstance(disposition["compaction_pass"], int)
        or not 0 <= disposition["compaction_pass"] <= 2
        or disposition["source"] not in _CONTEXT_REFUSAL_SOURCES
        or receipt.get("accepted_solver_receipt") is not None
    ):
        _raise(error_type, "context-fit terminal disposition has invalid authority")
    for field in ("tokens_before", "tokens_after", "limit_tokens"):
        _nonneg_int(disposition[field], f"context-fit {field}", error_type=error_type)
    dropped = _sequence(
        disposition["dropped_identifiers"],
        "context-fit dropped_identifiers",
        error_type=error_type,
    )
    seen = set()
    for identifier in dropped:
        if (
            not isinstance(identifier, str)
            or not identifier.startswith(_CONTEXT_DROPPABLE_PREFIXES)
            or identifier.endswith(":")
            or identifier in seen
        ):
            _raise(error_type, "context-fit dropped identifiers are malformed")
        seen.add(identifier)
    message = disposition["server_message"]
    if message is not None and (not isinstance(message, str) or not message):
        _raise(error_type, "context-fit server message must be text or null")
    if disposition["source"] == "server-refusal" and message is None:
        _raise(error_type, "a server refusal must record the server's own message")
    interrupted = receipt.get("interrupted_role")
    if (
        not isinstance(interrupted, Mapping)
        or interrupted.get("role_id") != disposition["role_id"]
        or interrupted.get("stage") != disposition["stage"]
        or set(interrupted) - {"role_id", "stage", "execution_receipt"}
    ):
        _raise(error_type, "context-fit disposition differs from its interrupted role")
    used = set()
    solvers = []
    for visit in visits:
        if not isinstance(visit, Mapping):
            _raise(error_type, "context-fit episode role visit must be a mapping")
        prior = _receipt(
            visit.get("execution_receipt"), "completed role", error_type=error_type
        )
        for contact in prior["contacts"]:
            _checked_contact(contact, error_type=error_type)
            pair = contact["agent_contact_id"], contact["request_id"]
            if pair in used:
                _raise(error_type, "context-fit episode duplicates completed contacts")
            used.add(pair)
        if visit.get("stage") == "solver":
            solvers.append(prior)
    if "execution_receipt" in interrupted:
        execution = _receipt(
            interrupted["execution_receipt"], "interrupted role", error_type=error_type
        )
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
            _raise(
                error_type,
                "context-fit delivery must retain the last completed Solver",
            )
        return NativeEpisodeDelivery(
            "context-fit", terminal, terminal["final_contact"], disposition, None
        )
    expected_abstention = {
        "source_contact": None,
        "reason": CONTEXT_COMPACTION_DISPOSITION,
        "source": disposition["source"],
    }
    if terminal is not None or abstention != expected_abstention:
        _raise(
            error_type,
            "context-fit episode without a Solver requires its bound abstention",
        )
    return NativeEpisodeDelivery("context-abstention", None, {}, disposition, None)


def validate_native_episode_terminal_policy(
    delivery, *, exhaustion_policy, finite_completion_policy, max_revisions,
    context_fit_policy="raise",
    react_exhaustion_policy="raise",
    error_type=ValueError,
):
    """Require prospective configuration for either kind of terminal delivery."""
    # E22: checked FIRST and for EVERY delivery kind, because the exhausted
    # visit is not a terminal disposition -- an accepted row can carry one
    # and still be an ordinary ACCEPT. The rule is the same prospective one
    # E13 and E20 take: a visit may only end without a finding under a
    # policy declared BEFORE the flight, never under one inferred from its
    # own failure. The default ``"raise"`` therefore refuses the block, and
    # every row sealed before E22 carries none and passes untouched.
    if getattr(delivery, "react_exhaustion", None) is not None and (
        react_exhaustion_policy != "continue-without-answer"
    ):
        _raise(
            error_type,
            "ReAct exhaustion recorded without its declared policy",
        )
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
    elif delivery.kind in {"context-fit", "context-abstention"}:
        # E20: the same prospective-configuration rule the finite kinds
        # take -- a row may only degrade under a policy declared before the
        # flight, never under one inferred from the failure.
        if (
            context_fit_policy != "compact-or-abstain"
            or not 0 <= disposition["revision_count"] <= max_revisions
        ):
            _raise(error_type, "context-fit delivery differs from its configured policy")
    else:
        _raise(error_type, "unknown native delivery kind")


def validate_native_episode_finite_path(
    receipt, *, max_revisions, accept_action, revise_action,
    refresh_action=None, max_refreshes=0,
    acquire_action=None, max_acquisitions=0,
    error_type=ValueError,
):
    """Validate a completed graph prefix and its exact next interrupted role."""
    delivery = validate_native_episode_delivery_receipt(receipt, error_type=error_type)
    # E20: a context-fit row stops the graph at exactly the same place a
    # finite completion does -- after a completed prefix, at one named role
    # -- so the same walker proves its prefix too.
    if delivery.kind not in {
        "finite", "abstention", "context-fit", "context-abstention",
    }:
        _raise(error_type, "finite path requires a finite delivery")
    if isinstance(max_revisions, bool) or not isinstance(max_revisions, int) or max_revisions < 0:
        _raise(error_type, "invalid finite path revision allowance")
    visits = receipt["role_visits"]
    routes = _sequence(receipt["planner_routes"], "finite Planner routes", error_type=error_type)
    terminal = delivery.terminal_disposition
    cursor = route_index = revision = refreshes = 0
    # E18: the acquisition visits already walked, so an ACQUIRE continuation
    # is checked against its own declared allowance exactly as a refresh is.
    acquisitions = 0

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
        elif acquire_action is not None and action == acquire_action:
            # E18: an ACQUIRE continuation registers exactly one acquisition
            # visit between the Planner that routed it and the Solver that
            # reads what it brought in.
            if acquisitions >= max_acquisitions:
                _raise(error_type, "finite path exceeds its acquisition allowance")
            if cursor == len(visits):
                return stopped("acquisition")
            consume("acquisition")
            acquisitions += 1
        elif action != revise_action:
            _raise(error_type, "finite path has an unsupported Planner continuation")


_SOLVER_GROUP_FIELDS = frozenset(
    {"commit_policy_id", "commit_params", "samples", "delivered"}
)
_SOLVER_GROUP_SAMPLE_FIELDS = frozenset(
    {"sample_index", "seed", "temperature", "parse_status", "parsed_answer", "contacts"}
)
_SOLVER_GROUP_DELIVERED_FIELDS = frozenset(
    {
        "intent_support", "intent_member_sample_indices",
        "intent_tie_break_sample_index", "entities",
    }
)
_SOLVER_GROUP_ENTITY_FIELDS = frozenset(
    {"type", "filler", "support", "member_sample_indices", "tie_break_sample_index"}
)


def _nonneg_int(value, label, *, error_type):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _raise(error_type, f"{label} must be a nonnegative integer")
    return value


def validate_solver_group_receipt(
    solver_group: Mapping[str, object],
    *,
    samples: int,
    error_type: type[Exception] = ValueError,
) -> None:
    """Validate the custody a grouped Solver visit keeps (E2, SLURP v2 base
    program M2, ``reproduction.ojw.native_group_solver.
    run_grouped_solver_samples``'s ``solver_group`` output): every raw
    sample of one Solver visit -- its pinned seed, decoding temperature,
    parse status and parsed answer -- plus the registered commit policy's id,
    the exact parameters it was applied with (E2d) and its support/tie-break
    provenance for the ONE delivered answer.

    This is additional custody beside the role's ordinary
    ``execution_receipt`` (:func:`_receipt` above), which
    ``reproduction.ojw.native_episode``'s ``_execution_receipt`` already
    validates and which stays exactly the concatenation, in sample order, of
    every sample's own contacts.
    """

    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1:
        _raise(error_type, "solver group receipt requires a positive registered sample count")
    if not isinstance(solver_group, Mapping) or set(solver_group) != _SOLVER_GROUP_FIELDS:
        _raise(error_type, "solver group receipt has an invalid shape")
    if not isinstance(solver_group["commit_policy_id"], str) or not solver_group["commit_policy_id"]:
        _raise(error_type, "solver group receipt names no commit policy")
    params = solver_group["commit_params"]
    if not isinstance(params, Mapping) or not all(
        isinstance(key, str) and key and isinstance(value, (bool, int, float, str))
        for key, value in params.items()
    ):
        _raise(error_type, "solver group receipt has malformed commit parameters")
    records = _sequence(solver_group["samples"], "solver group samples", error_type=error_type)
    if len(records) != samples:
        _raise(error_type, "solver group receipt does not carry every registered sample")
    seen_seeds: set[int] = set()
    for index, record in enumerate(records):
        if not isinstance(record, Mapping) or set(record) != _SOLVER_GROUP_SAMPLE_FIELDS:
            _raise(error_type, "solver group sample record has an invalid shape")
        if record.get("sample_index") != index:
            _raise(error_type, "solver group samples must be ordered by ascending sample_index")
        seed = record.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int):
            _raise(error_type, "solver group sample seed must be an integer")
        if seed in seen_seeds:
            _raise(error_type, "solver group samples must carry distinct pinned seeds")
        seen_seeds.add(seed)
        if record.get("parse_status") not in {"ok", "malformed"}:
            _raise(error_type, "solver group sample parse_status is invalid")
        if (record["parse_status"] == "ok") == (record.get("parsed_answer") is None):
            _raise(error_type, "solver group sample parse_status disagrees with parsed_answer")
        contacts = _sequence(
            record.get("contacts"), "solver group sample contacts", error_type=error_type
        )
        if not contacts or not all(isinstance(contact, Mapping) for contact in contacts):
            _raise(error_type, "solver group sample requires at least one raw contact")
    delivered = solver_group["delivered"]
    if not isinstance(delivered, Mapping) or set(delivered) != _SOLVER_GROUP_DELIVERED_FIELDS:
        _raise(error_type, "solver group delivered provenance has an invalid shape")
    support = _nonneg_int(
        delivered.get("intent_support"), "solver group delivered intent_support", error_type=error_type
    )
    intent_members = _sequence(
        delivered.get("intent_member_sample_indices"),
        "solver group delivered intent_member_sample_indices",
        error_type=error_type,
    )
    if len(intent_members) != support:
        _raise(error_type, "solver group delivered intent_support disagrees with its member indices")
    tie_break = delivered.get("intent_tie_break_sample_index")
    if tie_break is not None:
        _nonneg_int(tie_break, "solver group delivered intent_tie_break_sample_index", error_type=error_type)
    entities = _sequence(
        delivered.get("entities"), "solver group delivered entities", error_type=error_type
    )
    for entity in entities:
        if not isinstance(entity, Mapping) or set(entity) != _SOLVER_GROUP_ENTITY_FIELDS:
            _raise(error_type, "solver group delivered entity has an invalid shape")
        if not isinstance(entity.get("type"), str) or not entity["type"]:
            _raise(error_type, "solver group delivered entity requires a nonempty type")
        if not isinstance(entity.get("filler"), str):
            _raise(error_type, "solver group delivered entity requires a filler string")
        entity_support = _nonneg_int(
            entity.get("support"), "solver group delivered entity support", error_type=error_type
        )
        members = _sequence(
            entity.get("member_sample_indices"),
            "solver group delivered entity member_sample_indices",
            error_type=error_type,
        )
        if len(members) != entity_support:
            _raise(error_type, "solver group delivered entity support disagrees with its member indices")
        entity_tie_break = entity.get("tie_break_sample_index")
        if entity_tie_break is not None:
            _nonneg_int(
                entity_tie_break, "solver group delivered entity tie_break_sample_index",
                error_type=error_type,
            )


__all__ = [
    "PLANNER_ACTION_ILLEGAL_DISPOSITION", "is_illegal_planner_route",
    "NativeEpisodeDelivery", "validate_native_episode_delivery_receipt",
    "validate_native_candidate_refresh_receipt", "validate_native_episode_terminal_policy",
    "validate_native_episode_finite_path", "validate_solver_group_receipt",
]
