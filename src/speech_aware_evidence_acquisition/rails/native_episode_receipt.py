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
        isinstance(disposition, Mapping)
        and disposition.get("reason") == SEAL_REFUSAL_DISPOSITION
    ):
        # E43: checked BEFORE the finite branch, for the same reason the
        # context-fit branch above is -- a seal-refusal row carries the same
        # ``interrupted_role``/``abstention_receipt`` marks a finite row
        # does and would otherwise be read (and rejected) as a malformed
        # finite one.
        return _with_exhaustion(
            _seal_refusal_delivery(receipt, role_visits, error_type=error_type)
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


#: The exact field set of an item E13 finite disposition.
_FINITE_DISPOSITION_FIELDS = frozenset({
    "reason", "finish_reason", "role_id", "stage", "revision_count",
    "planner_accepted", "rejected_contact",
})

#: Item E39 (2026-09-22): the ONE further key such a disposition may carry --
#: which scope rule ended the row. Absent on every row sealed before E39 and
#: on every ``finite_completion_scope`` ``"episode"`` row, so those receipts
#: validate byte-identically to before this key existed.
_FINITE_DISPOSITION_SCOPES = ("episode", "answering-node")


def _finite_delivery(receipt, visits, *, error_type):
    disposition = receipt.get("terminal_disposition")
    if not isinstance(disposition, Mapping) or not (
        _FINITE_DISPOSITION_FIELDS
        <= set(disposition)
        <= _FINITE_DISPOSITION_FIELDS | {"scope"}
    ):
        _raise(error_type, "finite terminal disposition is malformed")
    if (
        disposition.get("scope", "episode") not in _FINITE_DISPOSITION_SCOPES
        or disposition["reason"] != "finite_completion"
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


#: Item E43 (2026-09-28, coordinator ruling on
#: ``docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md``): the
#: ``terminal_disposition.reason`` of a row whose deciding completion -- a
#: grammar-valid ``stop`` finish -- the seal itself refused (a
#: ``rails.errors.RailsError`` raised by a structured-output contract's
#: parser, never by the wire). The COMP-1/B7a/B8b-anchor abort class: a
#: parser refusal with no per-row disposition, aborting the whole arm at one
#: row. Restated here for the same reason :data:`CONTEXT_COMPACTION_DISPOSITION`
#: is: this module keeps no runtime import.
SEAL_REFUSAL_DISPOSITION = "seal_refusal"

#: The exact field set of that disposition. No ``finish_reason``: the
#: completion a contract seal can refuse is always a ``"stop"`` finish by
#: construction (``rails.solver_citation.bind_cited_completion`` parses only
#: on that finish), so the field would carry no information the reason does
#: not already give a reader.
_SEAL_REFUSAL_DISPOSITION_FIELDS = frozenset({
    "reason", "role_id", "stage", "revision_count", "planner_accepted",
    "rejected_contact", "seal_refusal",
})


def _seal_refusal_delivery(receipt, visits, *, error_type):
    """E43: validate a retained row whose deciding completion the seal refused.

    Built to the E13 contract (:func:`_finite_delivery`) with one forced
    difference: the refused contact never reached ``capture_completion``'s
    own custody bookkeeping (the seal refused it before that ran), so the
    interrupted role's execution receipt carries exactly the one rejected
    contact and nothing earlier to cross-check it against.
    """

    disposition = receipt.get("terminal_disposition")
    if (
        not isinstance(disposition, Mapping)
        or set(disposition) != _SEAL_REFUSAL_DISPOSITION_FIELDS
    ):
        _raise(error_type, "seal-refusal terminal disposition is malformed")
    if (
        disposition["reason"] != SEAL_REFUSAL_DISPOSITION
        or disposition["stage"] not in ("perception", "solver", "review", "planner", "acquisition")
        or not isinstance(disposition["role_id"], str) or not disposition["role_id"]
        or isinstance(disposition["revision_count"], bool)
        or not isinstance(disposition["revision_count"], int)
        or disposition["revision_count"] < 0
        or disposition["planner_accepted"] is not False
        or receipt.get("accepted_solver_receipt") is not None
    ):
        _raise(error_type, "seal-refusal terminal disposition has invalid authority")
    refusal = disposition["seal_refusal"]
    if (
        not isinstance(refusal, Mapping)
        or set(refusal) != {"error_class", "message"}
        or not isinstance(refusal["error_class"], str) or not refusal["error_class"]
        or not isinstance(refusal["message"], str) or not refusal["message"]
    ):
        _raise(error_type, "seal-refusal record is malformed")
    rejected = _checked_contact(disposition["rejected_contact"], error_type=error_type)
    interrupted = receipt.get("interrupted_role")
    if (
        not isinstance(interrupted, Mapping)
        or interrupted.get("role_id") != disposition["role_id"]
        or interrupted.get("stage") != disposition["stage"]
    ):
        _raise(error_type, "seal-refusal disposition differs from its interrupted role")
    execution = _receipt(
        interrupted.get("execution_receipt"), "interrupted role", error_type=error_type
    )
    if execution["final_contact"] != rejected or execution["contacts"] != [rejected]:
        _raise(error_type, "seal-refusal disposition differs from its rejected contact")
    used = set()
    solvers = []
    for visit in visits:
        if not isinstance(visit, Mapping):
            _raise(error_type, "seal-refusal episode role visit must be a mapping")
        prior = _receipt(
            visit.get("execution_receipt"), "completed role", error_type=error_type
        )
        for contact in prior["contacts"]:
            _checked_contact(contact, error_type=error_type)
            pair = contact["agent_contact_id"], contact["request_id"]
            if pair in used:
                _raise(error_type, "seal-refusal episode duplicates completed contacts")
            used.add(pair)
        if visit.get("stage") == "solver":
            solvers.append(prior)
    pair = rejected["agent_contact_id"], rejected["request_id"]
    if pair in used:
        _raise(error_type, "seal-refusal interrupted role repeats a completed contact")
    terminal = receipt.get("terminal_solver_receipt")
    abstention = receipt.get("abstention_receipt")
    if solvers:
        if terminal != solvers[-1] or abstention is not None:
            _raise(error_type, "seal-refusal delivery must retain the last completed Solver")
        return NativeEpisodeDelivery(
            "finite", terminal, terminal["final_contact"], disposition, None
        )
    if terminal is not None or abstention != {"source_contact": rejected}:
        _raise(error_type, "seal-refusal episode without a Solver requires a bound abstention")
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


#: Item E39 (2026-09-22): the receipt key a row's tolerated ``length``
#: truncations are collected under, its schema, and the exact field set of one
#: event. Restated here for the same reason
#: :data:`CONTEXT_COMPACTION_DISPOSITION` is: this module keeps no runtime
#: import.
TRUNCATION_EVENTS = "truncation_events"
TRUNCATION_EVENTS_SCHEMA = "saea-native-length-truncation-v1"
_TRUNCATION_EVENT_FIELDS = frozenset({
    "role_id", "stage", "role_visit_index", "revision_count", "finish_reason",
    "contact",
})

#: Item E39: the stages whose truncation may be tolerated. The answering
#: stage (``solver``) is deliberately absent: its truncation is item E13's own
#: case under every scope.
_TRUNCATION_STAGES = frozenset({"perception", "review", "planner", "acquisition"})


def validate_native_episode_truncation_scope(
    receipt, *, finite_completion_scope, error_type=ValueError,
):
    """Item E39: this row's tolerated truncations, bound and scope-checked.

    A row without the key -- every row sealed before E39 and every row of an
    ``"episode"`` scope cell -- returns ``()`` without reading anything else.
    A row WITH it takes the same prospective-configuration rule items E13,
    E20 and E22 take: a row may only survive a truncation under a scope
    declared BEFORE the flight, never under one inferred from its own
    failure, so the default ``"episode"`` refuses the block outright. Each
    event must name a real visit of THIS row -- its ``role_visit_index``
    addressing a ``role_visits`` entry whose ``stage`` and ``role_id`` are the
    event's own and which carries ``truncated`` true -- so a truncation can
    never be claimed for a visit that did not happen, and the answering stage
    can never claim one at all.
    """

    block = receipt.get(TRUNCATION_EVENTS)
    if block is None:
        return ()
    if finite_completion_scope != "answering-node":
        _raise(
            error_type,
            "tolerated length truncation recorded without its declared scope",
        )
    visits = _sequence(
        receipt.get("role_visits"), "native role visits", error_type=error_type
    )
    if (
        not isinstance(block, Mapping)
        or set(block) != {"schema", "count", "events"}
        or block["schema"] != TRUNCATION_EVENTS_SCHEMA
    ):
        _raise(error_type, "length truncation block is malformed")
    events = _sequence(
        block["events"], "length truncation events", error_type=error_type
    )
    count = block["count"]
    if (
        isinstance(count, bool)
        or not isinstance(count, int)
        or count != len(events)
        or not events
    ):
        _raise(error_type, "length truncation count differs from its events")
    seen_indices: set[int] = set()
    for event in events:
        if not isinstance(event, Mapping) or set(event) != _TRUNCATION_EVENT_FIELDS:
            _raise(error_type, "length truncation event is malformed")
        index = event["role_visit_index"]
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or not 0 <= index < len(visits)
            or index in seen_indices
            or not isinstance(visits[index], Mapping)
            or visits[index].get("stage") != event["stage"]
            or visits[index].get("role_id") != event["role_id"]
            or visits[index].get("truncated") is not True
        ):
            _raise(
                error_type,
                "length truncation event does not bind an actual role visit",
            )
        seen_indices.add(index)
        if event["stage"] not in _TRUNCATION_STAGES:
            _raise(error_type, "length truncation names an inadmissible stage")
        if not isinstance(event["role_id"], str) or not event["role_id"]:
            _raise(error_type, "length truncation event has no role id")
        if event["finish_reason"] != "length":
            _raise(error_type, "length truncation event has an invalid finish reason")
        _nonneg_int(
            event["revision_count"], "length truncation revision_count",
            error_type=error_type,
        )
        _checked_contact(event["contact"], error_type=error_type)
    marked = sum(
        1 for visit in visits
        if isinstance(visit, Mapping) and visit.get("truncated") is True
    )
    if marked != len(events):
        _raise(
            error_type,
            "a truncated role visit has no length truncation event of its own",
        )
    return tuple(events)


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


#: Item E42 (2026-09-25, Stage-3 family VAR-2). Bumped to v2 by owner
#: decision 172 (2026-09-27, merge set B): v2 adds ``arm_visits`` and
#: ``visit_index`` at the block level and ``replicate_of`` on every arm row
#: (``rails.supply_variants``). Bumped again to v3 by the coordinator
#: amendment (2026-09-28, docs/superpowers/specs/2026-09-27-same-flight-
#: supply-variant-instrument-design.md, "Coordinator amendment (2026-09-28)"):
#: v3 adds ``release_swap`` on every arm row. A v1 or v2 receipt -- every
#: VAR-2 / E42b cell sealed before this decision -- still validates unchanged
#: below: no sealed data is rewritten.
SUPPLY_VARIANT_RECEIPT_SCHEMA_V1 = "saea-supply-variant-arms-v1"
SUPPLY_VARIANT_RECEIPT_SCHEMA_V2 = "saea-supply-variant-arms-v2"
SUPPLY_VARIANT_RECEIPT_SCHEMA = "saea-supply-variant-arms-v3"

_SUPPLY_VARIANT_FIELDS_V1 = frozenset(
    {"schema", "phase_id", "arm_count", "delivered_arm_id", "fit_estimate", "arms"}
)
_SUPPLY_VARIANT_FIELDS_V2 = _SUPPLY_VARIANT_FIELDS_V1 | {"arm_visits", "visit_index"}
_SUPPLY_VARIANT_ARM_FIELDS_V1 = frozenset(
    {
        "arm_index", "arm_id", "deliver", "contact_id", "resolved_knobs",
        "supplied_value_ids", "supplied_item_count", "max_supplied_items",
    }
)
_SUPPLY_VARIANT_ARM_FIELDS_V2 = _SUPPLY_VARIANT_ARM_FIELDS_V1 | {"replicate_of"}
_SUPPLY_VARIANT_ARM_FIELDS_V3 = _SUPPLY_VARIANT_ARM_FIELDS_V2 | {"release_swap"}
#: NX programme E1 (2026-10-09): the node-template kind. v4 = v3 plus
#: ``instruction_template`` on every arm row.
SUPPLY_VARIANT_RECEIPT_SCHEMA_V4 = "saea-supply-variant-arms-v4"
_SUPPLY_VARIANT_ARM_FIELDS_V4 = _SUPPLY_VARIANT_ARM_FIELDS_V3 | {"instruction_template"}
#: Loop engineering item E-T6 (2026-10-11, owner decision 263-A / 265): the
#: multi-store supply kind. v5 = v3 with ``release_swap`` REPLACED by
#: ``release_swaps`` -- an ordered (by ``store_id``) list of the declared
#: ``{store_id, release}`` of every store the arm repoints, one entry per
#: DISTINCT store, ``[]`` for the delivering arm, the twin and a knob-only arm.
#: A group seals v5 only when some arm swaps two or more stores; every group
#: with at most one swap per arm still seals v3, byte for byte as before.
SUPPLY_VARIANT_RECEIPT_SCHEMA_V5 = "saea-supply-variant-arms-v5"
_SUPPLY_VARIANT_ARM_FIELDS_V5 = (
    _SUPPLY_VARIANT_ARM_FIELDS_V2 | {"release_swaps"}
)
#: NX-T R4 (2026-10-18, owner rulings 329 A / 332 A): the node-DECODING kind.
#: v6 = v3 plus ``decoding_override`` on every arm row -- ``None`` for the
#: delivering arm and the twin, the declared ``{name: value}`` sampling override
#: for every other arm. A v1-v5 receipt validates unchanged.
SUPPLY_VARIANT_RECEIPT_SCHEMA_V6 = "saea-supply-variant-arms-v6"
_SUPPLY_VARIANT_ARM_FIELDS_V6 = _SUPPLY_VARIANT_ARM_FIELDS_V3 | {"decoding_override"}
#: The closed set of sampling parameters a decoding arm may override and the
#: bounds each must satisfy: ``name -> (kind, low, high, low_exclusive)``. Owned
#: HERE (the lower layer) so the parser (``rails.supply_variants``) and the
#: receipt validator share one table.
DECODING_VARIANT_KNOBS = {
    "temperature": ("number", 0.0, 1.5, False),
    "top_p": ("number", 0.0, 1.0, True),
    "top_k": ("integer", 1, 200, False),
    "presence_penalty": ("number", 0.0, 2.0, False),
}


def decoding_override_error(value: object) -> str | None:
    """Why ``value`` is not a well-formed sampling override, or ``None``.

    A non-empty mapping whose every key is in :data:`DECODING_VARIANT_KNOBS` and
    whose every value is a finite non-boolean number of the knob's kind inside its
    bounds."""

    if not isinstance(value, Mapping) or not value:
        return "must be a non-empty object of sampling parameters"
    for name, number in value.items():
        spec = DECODING_VARIANT_KNOBS.get(name) if isinstance(name, str) else None
        if spec is None:
            return f"names {name!r}, which is not in the closed set {sorted(DECODING_VARIANT_KNOBS)}"
        kind, low, high, low_exclusive = spec
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            return f"{name} must be a number"
        if kind == "integer" and not isinstance(number, int):
            return f"{name} must be an integer"
        if isinstance(number, float) and number != number or number in (float("inf"), float("-inf")):
            return f"{name} must be finite"
        if (number <= low if low_exclusive else number < low) or number > high:
            return f"{name} is outside its bounds"
    return None


_SUPPLY_VARIANT_FIT_FIELDS = frozenset(
    {
        "slot_tokens", "completion_ceiling", "base_prompt_tokens",
        "tokens_per_supplied_item", "reserve_tokens", "prompt_limit_tokens",
    }
)
_SUPPLY_VARIANT_ARM_VISITS_VALUES = ("every", "first")
_SUPPLY_VARIANT_ARM_VISITS_DEFAULT = "every"


def supply_variant_arm_release_swaps(
    row: Mapping[str, object],
) -> list[dict[str, str]]:
    """The declared ``[{store_id, release}, ...]`` of one sealed arm row,
    ordered by ``store_id``, whatever the receipt's schema.

    A v5 row carries ``release_swaps`` (a list); a v3 row carries the single
    ``release_swap`` (``None`` or one object), read here as a list of at most
    one; a v1, v2 or v4 row carries neither and reads as ``[]``. This is the
    ONE normalisation a reader compares against a declaration, so a one-store
    swap sealed under v3 and the same swap spelled as a one-element
    ``release_swaps`` agree.
    """

    plural = row.get("release_swaps")
    if plural is not None:
        return sorted((dict(entry) for entry in plural), key=lambda e: e["store_id"])
    single = row.get("release_swap")
    return [] if single is None else [dict(single)]


def validate_supply_variant_receipt(
    supply_variants: Mapping[str, object],
    *,
    arm_ids: Sequence[str],
    delivered_arm_id: str,
    phase_id: str,
    retrieved_value_ids: Sequence[str] | None = None,
    arm_visits: str | None = None,
    error_type: type[Exception] = ValueError,
) -> None:
    """Validate the custody a supply-variant visit keeps (item E42).

    The twin of :func:`validate_solver_group_receipt`, and as strict: distinct
    arm ids, EVERY declared arm present exactly once in declared order, the
    delivering arm named and last, each arm's contact bound, each arm's resolved
    knobs recorded, and each arm's supplied value ids ordered, unique and
    counted within the bound the fit refusal was computed against.

    ``arm_ids``/``delivered_arm_id`` are the CONFIGURATION's own -- the sealing
    caller reads them off the composed config, a post-seal reader off the raw
    ``native_episode.roles.solver.supply_variants`` block -- so a receipt can
    never describe a group other than the one the cell declared.

    ``retrieved_value_ids`` is the row's own accumulated state at whatever point
    the reader has it. When given, the DELIVERING arm's ``supplied_value_ids``
    must be an ordered PREFIX of it: that arm is rendered from the episode's own
    ``QueryState`` with no arm-scoped view, and the state only ever grows by
    append (``rails.controllers``' successor state is
    ``retrieved_value_ids + new_value_ids``), so a reader holding the row's FINAL
    state -- after any later phase took supply of its own -- still holds a state
    the delivering arm's ids must open. This is the checked statement of the one
    property the whole form rests on: the delivered request is the unvaried
    construction's request, and only the NON-delivering arms carry evidence the
    sealed state does not claim. Omitted (a reader with no state to compare) the
    rest of the walk is unchanged.

    Accepts all three schemas (owner decision 172, merge set B; coordinator
    amendment, 2026-09-28). A v1 receipt (``schema``
    ``saea-supply-variant-arms-v1``) validates exactly as before decision 172.
    A v2 receipt additionally carries ``arm_visits`` (``"every"`` or
    ``"first"``) and ``visit_index`` (always 0: only the first Solver visit is
    ever sealed), and its arm rows carry ``replicate_of`` -- the delivering
    arm's own id, naming that row the read's TWIN: no overrides, exempt from
    the "at least one knob" rule, and required to resolve exactly the
    delivering arm's own supplied ids. A v3 receipt (``schema``
    ``saea-supply-variant-arms-v3``) additionally carries ``release_swap`` on
    every arm row -- ``None``, or the declared ``{store_id, release}`` of the
    ONE store the arm repoints; the delivering arm and any twin must declare
    none, and it satisfies the "at least one knob" rule exactly as a knob
    override does. ``arm_visits``, when given, is the CONFIGURATION's own
    declared value; the receipt's arm_visits (v2/v3) or the implied
    ``"every"`` (v1) must equal it. Omitted, no such cross-check is made
    (``core.bundle.outputs`` reads a sealed row with no composed configuration
    to compare against).

    A v4 receipt (``saea-supply-variant-arms-v4``, NX programme E1) is the
    NODE-TEMPLATE kind: the arms vary the node's instruction template and
    nothing else. Every arm therefore resolves NO knob and NO release_swap and
    supplies EXACTLY the delivering arm's ids (the supply is unvaried); the
    delivering arm and the twin carry ``instruction_template`` ``None``; every
    other arm carries a ``{relpath, sha256}`` pin, distinct from every other
    arm's. The "at least one knob" rule is replaced by "exactly one template".
    """

    declared = list(arm_ids)
    if not declared or len(set(declared)) != len(declared):
        _raise(error_type, "supply variant receipt requires distinct declared arm ids")
    if not isinstance(delivered_arm_id, str) or delivered_arm_id != declared[-1]:
        _raise(
            error_type,
            "supply variant receipt requires the delivering arm to be the last "
            "declared arm",
        )
    if not isinstance(supply_variants, Mapping):
        _raise(error_type, "supply variant receipt has an invalid shape")
    schema = supply_variants.get("schema")
    is_v4 = False
    is_v5 = False
    is_v6 = False
    if schema == SUPPLY_VARIANT_RECEIPT_SCHEMA_V1:
        is_v2_or_later = False
        is_v3 = False
        expected_fields = _SUPPLY_VARIANT_FIELDS_V1
        arm_fields = _SUPPLY_VARIANT_ARM_FIELDS_V1
    elif schema == SUPPLY_VARIANT_RECEIPT_SCHEMA_V2:
        is_v2_or_later = True
        is_v3 = False
        expected_fields = _SUPPLY_VARIANT_FIELDS_V2
        arm_fields = _SUPPLY_VARIANT_ARM_FIELDS_V2
    elif schema == SUPPLY_VARIANT_RECEIPT_SCHEMA:
        is_v2_or_later = True
        is_v3 = True
        expected_fields = _SUPPLY_VARIANT_FIELDS_V2
        arm_fields = _SUPPLY_VARIANT_ARM_FIELDS_V3
    elif schema == SUPPLY_VARIANT_RECEIPT_SCHEMA_V4:
        is_v2_or_later = True
        is_v3 = True
        is_v4 = True
        expected_fields = _SUPPLY_VARIANT_FIELDS_V2
        arm_fields = _SUPPLY_VARIANT_ARM_FIELDS_V4
    elif schema == SUPPLY_VARIANT_RECEIPT_SCHEMA_V5:
        is_v2_or_later = True
        is_v3 = False
        is_v5 = True
        expected_fields = _SUPPLY_VARIANT_FIELDS_V2
        arm_fields = _SUPPLY_VARIANT_ARM_FIELDS_V5
    elif schema == SUPPLY_VARIANT_RECEIPT_SCHEMA_V6:
        is_v2_or_later = True
        is_v3 = True
        is_v6 = True
        expected_fields = _SUPPLY_VARIANT_FIELDS_V2
        arm_fields = _SUPPLY_VARIANT_ARM_FIELDS_V6
    else:
        _raise(error_type, "supply variant receipt has an unregistered schema")
    if set(supply_variants) != expected_fields:
        _raise(error_type, "supply variant receipt has an invalid shape")
    if supply_variants["phase_id"] != phase_id:
        _raise(error_type, "supply variant receipt names another phase")
    if supply_variants["arm_count"] != len(declared):
        _raise(
            error_type,
            "supply variant receipt does not carry every declared arm",
        )
    if supply_variants["delivered_arm_id"] != delivered_arm_id:
        _raise(error_type, "supply variant receipt names another delivering arm")
    if is_v2_or_later:
        receipt_arm_visits = supply_variants["arm_visits"]
        if receipt_arm_visits not in _SUPPLY_VARIANT_ARM_VISITS_VALUES:
            _raise(error_type, "supply variant receipt has an invalid arm_visits")
        visit_index = supply_variants["visit_index"]
        if isinstance(visit_index, bool) or visit_index != 0:
            _raise(
                error_type,
                "supply variant receipt visit_index must be 0: only the first "
                "Solver visit is ever sealed",
            )
    else:
        receipt_arm_visits = _SUPPLY_VARIANT_ARM_VISITS_DEFAULT
    if arm_visits is not None and receipt_arm_visits != arm_visits:
        _raise(
            error_type,
            "supply variant receipt arm_visits disagrees with the declared "
            "configuration",
        )
    fit = supply_variants["fit_estimate"]
    if not isinstance(fit, Mapping) or set(fit) != _SUPPLY_VARIANT_FIT_FIELDS:
        _raise(error_type, "supply variant receipt fit estimate has an invalid shape")
    rows = _sequence(supply_variants["arms"], "supply variant arms", error_type=error_type)
    if len(rows) != len(declared):
        _raise(error_type, "supply variant receipt does not carry every declared arm")
    contact_ids: list[str] = []
    delivering_ids: tuple[str, ...] | None = None
    twin_checks: list[tuple[str, tuple[str, ...]]] = []
    arm_id_lists: list[tuple[str, tuple[str, ...]]] = []
    template_pins: list[tuple[str, str]] = []
    decoding_pins: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != arm_fields:
            _raise(error_type, "supply variant arm record has an invalid shape")
        if row["arm_index"] != index:
            _raise(
                error_type,
                "supply variant arms must be ordered by ascending arm_index",
            )
        if row["arm_id"] != declared[index]:
            _raise(
                error_type,
                "supply variant arms must appear in their declared order",
            )
        deliver = row["deliver"]
        if not isinstance(deliver, bool) or deliver != (
            row["arm_id"] == delivered_arm_id
        ):
            _raise(
                error_type,
                "supply variant arm disagrees with the declared delivering arm",
            )
        contact_id = row["contact_id"]
        if not isinstance(contact_id, str) or not contact_id:
            _raise(error_type, "supply variant arm lacks its contact identity")
        contact_ids.append(contact_id)
        replicate_of = row.get("replicate_of") if is_v2_or_later else None
        if replicate_of is not None:
            if not isinstance(replicate_of, str) or not replicate_of:
                _raise(
                    error_type,
                    "supply variant arm replicate_of must be a non-empty string",
                )
            if replicate_of != delivered_arm_id:
                _raise(
                    error_type,
                    "supply variant arm names replicate_of that is not the "
                    "delivering arm",
                )
            if deliver:
                _raise(
                    error_type,
                    "the delivering supply variant arm cannot also declare "
                    "replicate_of",
                )
        # An ORDERED LIST of {path, value}: a mapping keyed by the dotted knob
        # path cannot survive the framework's own node-result transport, which
        # unflattens dotted keys (see ``rails.supply_variants.
        # supply_variant_arm_record``).
        knobs = _sequence(
            row["resolved_knobs"], "supply variant arm resolved_knobs",
            error_type=error_type,
        )
        if any(
            not isinstance(entry, Mapping)
            or set(entry) != {"path", "value"}
            or not isinstance(entry["path"], str)
            or not entry["path"]
            or isinstance(entry["value"], bool)
            or not isinstance(entry["value"], int)
            for entry in knobs
        ):
            _raise(error_type, "supply variant arm has malformed resolved knobs")
        paths = [entry["path"] for entry in knobs]
        if len(set(paths)) != len(paths) or paths != sorted(paths):
            _raise(
                error_type,
                "supply variant arm resolved knobs must be distinct and ordered "
                "by path",
            )
        if deliver and paths:
            _raise(
                error_type,
                "the delivering supply variant arm must resolve no knobs: it is "
                "the unvaried construction",
            )
        if replicate_of is not None and paths:
            _raise(
                error_type,
                "a supply variant twin arm (replicate_of) must resolve no "
                "knobs: it resolves exactly the delivering arm's ids",
            )
        release_swap = row.get("release_swap") if is_v3 else None
        if is_v5:
            # E-T6: every swapped store is checked on its own -- one entry per
            # DISTINCT store, ordered by store_id (I7v, per store).
            swaps = _sequence(
                row["release_swaps"], "supply variant arm release_swaps",
                error_type=error_type,
            )
            if any(
                not isinstance(entry, Mapping)
                or set(entry) != {"store_id", "release"}
                or not isinstance(entry["store_id"], str)
                or not entry["store_id"]
                or not isinstance(entry["release"], str)
                or not entry["release"]
                for entry in swaps
            ):
                _raise(
                    error_type,
                    "supply variant arm release_swaps has an invalid shape",
                )
            swap_stores = [entry["store_id"] for entry in swaps]
            if len(set(swap_stores)) != len(swap_stores):
                _raise(
                    error_type,
                    "supply variant arm release_swaps names a store twice: one "
                    "swap per distinct store",
                )
            if swap_stores != sorted(swap_stores):
                _raise(
                    error_type,
                    "supply variant arm release_swaps must be ordered by store_id",
                )
            if swaps and deliver:
                _raise(
                    error_type,
                    "the delivering supply variant arm must declare no "
                    "release_swaps: it is the unvaried construction over the "
                    "base's own released stores",
                )
            if swaps and replicate_of is not None:
                _raise(
                    error_type,
                    "a supply variant twin arm (replicate_of) must declare no "
                    "release_swaps: it resolves exactly the delivering arm's "
                    "ids",
                )
            release_swap = swaps[0] if swaps else None
        if release_swap is not None and not is_v5:
            if (
                not isinstance(release_swap, Mapping)
                or set(release_swap) != {"store_id", "release"}
                or not isinstance(release_swap["store_id"], str)
                or not release_swap["store_id"]
                or not isinstance(release_swap["release"], str)
                or not release_swap["release"]
            ):
                _raise(
                    error_type,
                    "supply variant arm release_swap has an invalid shape",
                )
            if deliver:
                _raise(
                    error_type,
                    "the delivering supply variant arm must declare no "
                    "release_swap: it is the unvaried construction over the "
                    "base's own released stores",
                )
            if replicate_of is not None:
                _raise(
                    error_type,
                    "a supply variant twin arm (replicate_of) must declare no "
                    "release_swap: it resolves exactly the delivering arm's "
                    "ids",
                )
        if is_v4:
            if paths:
                _raise(
                    error_type,
                    "a node-template supply variant arm must resolve no knobs: "
                    "the only thing it varies is its instruction template",
                )
            if release_swap is not None:
                _raise(
                    error_type,
                    "a node-template supply variant arm must declare no "
                    "release_swap: the supply is unvaried",
                )
            template = row["instruction_template"]
            if deliver or replicate_of is not None:
                if template is not None:
                    _raise(
                        error_type,
                        "the delivering arm and the twin of a node-template "
                        "receipt must declare no instruction_template: they "
                        "render the node's own locked template",
                    )
            else:
                if (
                    not isinstance(template, Mapping)
                    or set(template) != {"relpath", "sha256"}
                    or not isinstance(template["relpath"], str)
                    or not template["relpath"]
                    or not isinstance(template["sha256"], str)
                    or len(template["sha256"]) != 64
                    or any(
                        character not in "0123456789abcdef"
                        for character in template["sha256"]
                    )
                ):
                    _raise(
                        error_type,
                        "a candidate node-template arm must carry exactly one "
                        "{relpath, sha256} instruction_template",
                    )
                template_pins.append((template["relpath"], template["sha256"]))
        elif is_v6:
            if paths:
                _raise(
                    error_type,
                    "a node-decoding supply variant arm must resolve no knobs: "
                    "the only thing it varies is its sampling override",
                )
            if release_swap is not None:
                _raise(
                    error_type,
                    "a node-decoding supply variant arm must declare no "
                    "release_swap: the supply is unvaried",
                )
            override = row["decoding_override"]
            if deliver or replicate_of is not None:
                if override is not None:
                    _raise(
                        error_type,
                        "the delivering arm and the twin of a node-decoding "
                        "receipt must declare no decoding_override: they sample "
                        "exactly as the node's own locked request does",
                    )
            else:
                reason = decoding_override_error(override)
                if reason is not None:
                    _raise(
                        error_type,
                        "a candidate node-decoding arm must carry one well-formed "
                        f"decoding_override: {reason}",
                    )
                decoding_pins.append(json.dumps(dict(override), sort_keys=True))
        elif not deliver and not paths and replicate_of is None and release_swap is None:
            _raise(
                error_type,
                "a non-delivering supply variant arm must resolve at least one "
                "knob or a release_swap, or it is a second spelling of the "
                "delivering arm",
            )
        ids = _sequence(
            row["supplied_value_ids"], "supply variant arm supplied_value_ids",
            error_type=error_type,
        )
        if any(not isinstance(value, str) or not value for value in ids):
            _raise(error_type, "supply variant arm supplied ids must be nonempty strings")
        if len(set(ids)) != len(ids):
            _raise(error_type, "supply variant arm supplied ids must be unique")
        count = _nonneg_int(
            row["supplied_item_count"], "supply variant arm supplied_item_count",
            error_type=error_type,
        )
        if count != len(ids):
            _raise(
                error_type,
                "supply variant arm supplied_item_count disagrees with its ids",
            )
        bound = row["max_supplied_items"]
        if isinstance(bound, bool) or not isinstance(bound, int) or bound < 1:
            _raise(error_type, "supply variant arm max_supplied_items must be positive")
        if count > bound:
            _raise(
                error_type,
                "supply variant arm supplied more items than the bound its fit "
                "refusal was computed against",
            )
        if deliver:
            delivering_ids = tuple(ids)
            if retrieved_value_ids is not None:
                accumulated = list(retrieved_value_ids)
                if list(ids) != accumulated[: len(ids)]:
                    _raise(
                        error_type,
                        "the delivering supply variant arm's supplied ids are not "
                        "an ordered prefix of the row's own accumulated "
                        "retrieved_value_ids; the delivered request would not be "
                        "the unvaried construction's request",
                    )
        if replicate_of is not None:
            twin_checks.append((row["arm_id"], tuple(ids)))
        arm_id_lists.append((row["arm_id"], tuple(ids)))
    if is_v4:
        if len({pin[0] for pin in template_pins}) != len(template_pins) or len(
            {pin[1] for pin in template_pins}
        ) != len(template_pins):
            _raise(
                error_type,
                "node-template supply variant arms must name distinct templates",
            )
    if is_v6 and len(set(decoding_pins)) != len(decoding_pins):
        _raise(
            error_type,
            "node-decoding supply variant arms must declare distinct sampling overrides",
        )
    if is_v4 or is_v6:
        for arm_id, arm_ids_seen in arm_id_lists:
            if delivering_ids is None or arm_ids_seen != delivering_ids:
                _raise(
                    error_type,
                    f"node-template supply variant arm {arm_id!r} does not "
                    "supply exactly the delivering arm's ids: a template arm "
                    "varies the instruction, never the evidence"
                    if is_v4 else
                    f"node-decoding supply variant arm {arm_id!r} does not "
                    "supply exactly the delivering arm's ids: a decoding arm "
                    "varies the sampling, never the evidence",
                )
    if len(set(contact_ids)) != len(contact_ids):
        _raise(error_type, "supply variant arms must have distinct contact ids")
    for twin_arm_id, twin_ids in twin_checks:
        if delivering_ids is None or twin_ids != delivering_ids:
            _raise(
                error_type,
                f"supply variant twin arm {twin_arm_id!r} does not resolve "
                "exactly the delivering arm's ids",
            )


#: Same-flight instrument, PHASE 2 (merge set C, item 2): the receipt schema
#: one Perception branch group seals under ``perception_branches``
#: (``rails.supply_variants.PERCEPTION_BRANCH_RECEIPT_SCHEMA``, restated here
#: so this module keeps its "no runtime or framework imports" rule).
#:
#: v2 (2026-09-29, P-SV-1 seal abort): a branch's degenerate candidate list is
#: a MEASURED OUTCOME, never a seal failure. ``candidate_intent_ids`` is the
#: note's parsed order with duplicates collapsed (first occurrence kept), may
#: be empty, and is explained by two fields: ``candidate_intent_ids_raw_count``
#: (the number of intent ids the note listed before the collapse) and a closed
#: ``note_parse_status`` (:data:`PERCEPTION_BRANCH_NOTE_PARSE_STATUSES`). v1
#: receipts (sealed before the fix: the P-SV-1 4-row smoke) stay verifiable
#: under their own original rule, unchanged.
#:
#: v3 (2026-09-30, the ``key_source`` branch axis): every branch row also
#: carries ``key_source`` -- ``None`` for A, T and every branch that swaps no
#: retrieval-key pin; for a key-source B branch, the ``{store_id,
#: facet_source, query_source, agreement_source}`` pins it swapped (each
#: ``{relpath, sha256}`` or ``None``, at least one swapped). The note-parse
#: rule of v2 applies unchanged. A v1 or v2 receipt stays verifiable under its
#: own rule, unchanged: no sealed P-SV bundle is rewritten.
PERCEPTION_BRANCH_RECEIPT_SCHEMA = "saea-perception-branch-arms-v3"
PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2 = "saea-perception-branch-arms-v2"
PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1 = "saea-perception-branch-arms-v1"
#: v4 (2026-10-10, NX programme E1 for the Perception node): v3 plus
#: ``instruction_template`` on every branch row -- ``None`` for A and the twin,
#: the declared ``{relpath, sha256}`` for a template branch, whose ONLY axis it
#: is. Sealed by a ``roles.perception.template_variants`` group; v1-v3 verify
#: unchanged under their own rules.
PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4 = "saea-perception-branch-arms-v4"
#: v5 (2026-10-13, NX-T R1, the per-node THINKING-POLICY column): v3 plus ``thinking_policy`` on every branch row --
#: ``None`` for A and the twin, the declared ``{role kind: {enable_thinking | reasoning_budget_tokens |
#: answer_reserve_tokens}}`` override map for every other branch, whose ONLY axis it is. Sealed by a
#: ``roles.perception.thinking_variants`` group, whose twin is OPTIONAL (the column may fly without an in-flight A/A).
PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5 = "saea-perception-branch-arms-v5"
# (v6 is declared below, beside its validator, and appended to these tuples there.)
PERCEPTION_BRANCH_RECEIPT_SCHEMAS = (
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1, PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA, PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5, "saea-perception-branch-arms-v6",
)
#: The schemas whose rows carry the v2 note-parse fields (v2 and every later one).
PERCEPTION_BRANCH_NOTE_FIELD_SCHEMAS = (
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2, PERCEPTION_BRANCH_RECEIPT_SCHEMA,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4, PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5,
    "saea-perception-branch-arms-v6",
)
#: The three retrieval-key pins a ``key_source`` branch may swap (v3).
PERCEPTION_BRANCH_KEY_SOURCE_FIELDS = ("facet_source", "query_source", "agreement_source")


def perception_branch_key_source_error(key_source: object) -> str | None:
    """Why a v3 row's ``key_source`` value is malformed, or ``None`` when it is
    ``None`` or well formed: exactly ``{store_id, facet_source, query_source,
    agreement_source}``, a non-empty ``store_id``, each source ``None`` or
    exactly ``{relpath, sha256}`` (lowercase 64-hex), at least one swapped.
    Shared by the record constructor and :func:`validate_perception_branch_receipt`.
    """

    if key_source is None:
        return None
    if not isinstance(key_source, Mapping) or set(key_source) != {
        "store_id", *PERCEPTION_BRANCH_KEY_SOURCE_FIELDS,
    }:
        return (
            "perception branch key_source must be exactly {store_id, facet_source, "
            "query_source, agreement_source}"
        )
    if not isinstance(key_source["store_id"], str) or not key_source["store_id"]:
        return "perception branch key_source.store_id must be a non-empty string"
    swapped = 0
    for field in PERCEPTION_BRANCH_KEY_SOURCE_FIELDS:
        pin = key_source[field]
        if pin is None:
            continue
        if (
            not isinstance(pin, Mapping) or set(pin) != {"relpath", "sha256"}
            or not isinstance(pin["relpath"], str) or not pin["relpath"]
            or not isinstance(pin["sha256"], str) or len(pin["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in pin["sha256"])
        ):
            return (
                f"perception branch key_source.{field} must be None or exactly "
                "{relpath, sha256} with a lowercase 64-hex sha256"
            )
        swapped += 1
    if not swapped:
        return "perception branch key_source swaps no retrieval-key pin"
    return None

#: The closed ``note_parse_status`` vocabulary of a v2 branch row:
#:
#: * ``ok`` -- a well-shaped note listing at least one intent, none repeated;
#: * ``duplicates-collapsed`` -- a well-shaped note that listed at least one
#:   intent id more than once; ``candidate_intent_ids`` keeps the first
#:   occurrence of each, and ``candidate_intent_ids_raw_count`` the listed
#:   count (strictly larger);
#: * ``empty`` -- a well-shaped note whose ``candidates`` list is empty;
#: * ``malformed`` -- not a ``slurp-intent-hypotheses-v1``-shaped document (not
#:   JSON, no ``candidates`` list, or a candidate row without a non-empty
#:   string ``intent_id``). Nothing is extracted from it.
#:
#: ``empty`` and ``malformed`` both carry an empty ``candidate_intent_ids`` and
#: a zero raw count; every read treats either as gold-absent.
PERCEPTION_BRANCH_NOTE_OK = "ok"
PERCEPTION_BRANCH_NOTE_DUPLICATES_COLLAPSED = "duplicates-collapsed"
PERCEPTION_BRANCH_NOTE_EMPTY = "empty"
PERCEPTION_BRANCH_NOTE_MALFORMED = "malformed"
PERCEPTION_BRANCH_NOTE_PARSE_STATUSES = (
    PERCEPTION_BRANCH_NOTE_OK,
    PERCEPTION_BRANCH_NOTE_DUPLICATES_COLLAPSED,
    PERCEPTION_BRANCH_NOTE_EMPTY,
    PERCEPTION_BRANCH_NOTE_MALFORMED,
)


def parse_perception_branch_note(text: object) -> tuple[str, tuple[str, ...], int]:
    """One Perception branch note's ``(note_parse_status, candidate_intent_ids,
    candidate_intent_ids_raw_count)`` (receipt schema v2).

    The ONE parse the live runner (``rails.runner.read_perception_branch_record``),
    the resume replay (``rails.supply_variants.replay_perception_branch_block``)
    and the bundle's I7v re-derivation all apply, so a sealed row can always be
    re-derived from the trace's own recorded response text.

    Deliberately LIGHTER than ``rails.slurp_intent_hypotheses.
    parse_slurp_intent_hypothesis_content``: it extracts the ordered
    ``candidates[].intent_id`` list the ``slurp-intent-hypotheses-v1`` schema
    declares, without validating against the closed legal-intent inventory or a
    ``max_candidates`` bound -- that is the official scorer's job at read time.
    Duplicates collapse to their first occurrence (the same ordering rule the
    bounded projection policy ``bounded-first-occurrence-distinct-slurp-intent-
    hypotheses-v1`` and ``scripts/analysis/stage3_rollout_score.py`` apply).
    """

    if not isinstance(text, str):
        return PERCEPTION_BRANCH_NOTE_MALFORMED, (), 0
    try:
        document = json.loads(text)
    except (ValueError, TypeError):
        return PERCEPTION_BRANCH_NOTE_MALFORMED, (), 0
    candidates = document.get("candidates") if isinstance(document, Mapping) else None
    if not isinstance(candidates, list):
        return PERCEPTION_BRANCH_NOTE_MALFORMED, (), 0
    raw: list[str] = []
    for row in candidates:
        intent_id = row.get("intent_id") if isinstance(row, Mapping) else None
        if not isinstance(intent_id, str) or not intent_id:
            return PERCEPTION_BRANCH_NOTE_MALFORMED, (), 0
        raw.append(intent_id)
    if not raw:
        return PERCEPTION_BRANCH_NOTE_EMPTY, (), 0
    distinct = tuple(dict.fromkeys(raw))
    status = (
        PERCEPTION_BRANCH_NOTE_OK if len(distinct) == len(raw)
        else PERCEPTION_BRANCH_NOTE_DUPLICATES_COLLAPSED
    )
    return status, distinct, len(raw)


def perception_branch_note_fields_error(
    note_parse_status: object, candidate_intent_ids: object, raw_count: object,
) -> str | None:
    """Why a v2 branch row's three note-parse fields are inconsistent, or
    ``None`` when they agree. Shared by the record constructor
    (``rails.supply_variants.perception_branch_record``) and
    :func:`validate_perception_branch_receipt`, so the two rails state one rule.
    """

    if note_parse_status not in PERCEPTION_BRANCH_NOTE_PARSE_STATUSES:
        return (
            "perception branch note_parse_status must be one of "
            f"{list(PERCEPTION_BRANCH_NOTE_PARSE_STATUSES)}"
        )
    if (
        not isinstance(candidate_intent_ids, Sequence)
        or isinstance(candidate_intent_ids, (str, bytes))
        or any(not isinstance(value, str) or not value for value in candidate_intent_ids)
        or len(set(candidate_intent_ids)) != len(candidate_intent_ids)
    ):
        return (
            "perception branch candidate_intent_ids must be an ordered list of "
            "distinct non-empty strings"
        )
    if isinstance(raw_count, bool) or not isinstance(raw_count, int) or raw_count < 0:
        return "perception branch candidate_intent_ids_raw_count must be a non-negative integer"
    count = len(candidate_intent_ids)
    if note_parse_status in (PERCEPTION_BRANCH_NOTE_EMPTY, PERCEPTION_BRANCH_NOTE_MALFORMED):
        if count or raw_count:
            return (
                f"a perception branch note parsed as {note_parse_status!r} carries "
                "no candidate intent ids"
            )
    elif not count:
        return (
            f"a perception branch note parsed as {note_parse_status!r} carries at "
            "least one candidate intent id"
        )
    elif note_parse_status == PERCEPTION_BRANCH_NOTE_OK and raw_count != count:
        return (
            "a perception branch note parsed as 'ok' lists each candidate once "
            "(raw count equals the list length)"
        )
    elif note_parse_status == PERCEPTION_BRANCH_NOTE_DUPLICATES_COLLAPSED and raw_count <= count:
        return (
            "a perception branch note parsed as 'duplicates-collapsed' listed more "
            "intent ids than it keeps"
        )
    return None

_PERCEPTION_BRANCH_FIELDS = frozenset(
    {
        "schema", "phase_id", "level", "branch_count", "delivered_branch_id",
        "branch_visits", "visit_index", "fit_estimate", "branches",
    }
)
_PERCEPTION_BRANCH_FIT_FIELDS = frozenset(
    {
        "slot_tokens", "completion_ceiling", "base_prompt_tokens",
        "tokens_per_supplied_item", "reserve_tokens", "prompt_limit_tokens",
    }
)
_PERCEPTION_BRANCH_RECORD_FIELDS = frozenset(
    {
        "branch_index", "branch_id", "deliver", "replicate_of", "resolved_knobs",
        "release_swap", "presentation_id", "min_candidates", "supplied_value_ids",
        "supplied_count", "max_supplied_items", "contact_id", "request_sha256",
        "response_text_sha256", "note_sha256", "note_parse_status",
        "candidate_intent_ids",
        # "What to build" items 2 and 3.
        "presentation_skip_reason", "contrast_block_sha256", "min_candidates_met",
    }
)
_PERCEPTION_BRANCH_LEVEL2_FIELDS = _PERCEPTION_BRANCH_RECORD_FIELDS | {
    "solver_contact_id", "solver_request_sha256", "solver_response_text_sha256",
    "candidate_supply_value_ids",
}
#: NX-T R1 seal fix (2026-10-15): a NON-delivering level-2 branch whose Solver contact ended on a finite completion (``length`` or
#: ``content_filter``) has no authoritative Solver answer. Its row records that as two optional fields, present TOGETHER or not at all,
#: so every receipt sealed before this change (neither key) verifies unchanged and the receipt schema string is not bumped: the
#: contact itself was made and metered, and the four level-2 custody fields still name it.
PERCEPTION_BRANCH_ABSENT_FIELDS = frozenset({"solver_absent", "absent_reason"})
PERCEPTION_BRANCH_ABSENT_REASONS = frozenset({"finite-completion:length", "finite-completion:content_filter"})
#: Schema v2 adds exactly one field per branch row (the pre-collapse count).
_PERCEPTION_BRANCH_V2_EXTRA_FIELDS = frozenset({"candidate_intent_ids_raw_count"})
#: Schema v3 adds exactly one more field per branch row (the key-source axis).
_PERCEPTION_BRANCH_V3_EXTRA_FIELDS = frozenset({"key_source"})
#: Schema v4 adds exactly one more field per branch row (the template axis).
_PERCEPTION_BRANCH_V4_EXTRA_FIELDS = frozenset({"instruction_template"})
#: Schema v5 adds exactly one more field per branch row (the thinking-policy axis); it carries no ``instruction_template``.
_PERCEPTION_BRANCH_V5_EXTRA_FIELDS = frozenset({"thinking_policy"})
#: The role kinds and keys a branch's ``thinking_policy`` may name (``core.reasoning_knobs.NODE_POLICY_KEYS``, restated so this
#: module keeps its "no runtime or framework imports" rule).
_THINKING_POLICY_ROLE_KINDS = ("perception", "solver")
_THINKING_POLICY_KEYS = frozenset({"reasoning_budget_tokens", "answer_reserve_tokens", "enable_thinking"})


def perception_branch_thinking_policy_error(policy: object) -> str | None:
    """Why a v5 row's ``thinking_policy`` is malformed, or ``None`` when it is ``None`` or well formed."""

    if policy is None:
        return None
    if not isinstance(policy, Mapping) or not policy:
        return "perception branch thinking_policy must be None or a non-empty mapping of role kind to override"
    for kind, entry in policy.items():
        if kind not in _THINKING_POLICY_ROLE_KINDS:
            return f"perception branch thinking_policy names role kind {kind!r}; admitted: {list(_THINKING_POLICY_ROLE_KINDS)}"
        if not isinstance(entry, Mapping) or not entry or set(entry) - _THINKING_POLICY_KEYS:
            return (
                f"perception branch thinking_policy[{kind!r}] must be a non-empty mapping over "
                f"{sorted(_THINKING_POLICY_KEYS)}"
            )
        for key, value in entry.items():
            if key == "enable_thinking":
                if not isinstance(value, bool):
                    return "perception branch thinking_policy enable_thinking must be a boolean"
            elif isinstance(value, bool) or not isinstance(value, int) or value < 0:
                return f"perception branch thinking_policy {key} must be a non-negative integer"
    return None
#: v6 (2026-10-19, decision 338, the SAMPLING column): v3 plus ``sampling`` on every branch row -- ``None`` for A and the twin,
#: for every other branch ``{"perception_samples": <record>|None, "solver_samples": <record>|None}`` with at least one
#: record. Each record carries the branch's per-sample streams (seed, override, contact identity, request / response hashes,
#: parse status), the resolved seeds, and the merge (candidate union) or commit (first-support) outcome. Sealed by a
#: ``roles.perception.sampling_variants`` group, whose twin is required. v1-v5 verify unchanged under their own rules.
PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6 = "saea-perception-branch-arms-v6"
_PERCEPTION_BRANCH_V6_EXTRA_FIELDS = frozenset({"sampling"})
SAMPLING_AXES = ("perception_samples", "solver_samples")
_SAMPLING_DECODING_KEYS = frozenset({"temperature", "top_p", "top_k"})
_HEX = frozenset("0123456789abcdef")


def _is_hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX


def _is_int(value: object, low: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= low


def _sampling_stream_error(
    record: Mapping[str, object], *, count_key: str, low: int, high: int, status_key: str,
) -> str | None:
    """Shared shape of the per-sample stream every sampling record carries."""

    count = record.get(count_key)
    if not _is_int(count, low) or count > high:
        return f"sampling {count_key} must be an integer from {low} to {high}"
    decoding = record.get("decoding")
    if (
        not isinstance(decoding, Mapping) or not decoding or set(decoding) - _SAMPLING_DECODING_KEYS
        or "temperature" not in decoding
        or decoding_override_error(decoding) is not None
        or decoding["temperature"] <= 0
    ):
        return (
            f"sampling decoding must be a valid override over {sorted(_SAMPLING_DECODING_KEYS)} "
            "with a positive temperature"
        )
    offsets, seeds = record.get("seed_offsets"), record.get("seeds")
    if (
        not isinstance(offsets, list) or len(offsets) != count - 1
        or any(not _is_int(value, 1) for value in offsets) or len(set(offsets)) != len(offsets)
    ):
        return f"sampling seed_offsets must be {count - 1} distinct positive integers"
    if (
        not isinstance(seeds, list) or len(seeds) != count or any(not _is_int(value, 0) for value in seeds)
        or [seed - seeds[0] for seed in seeds[1:]] != offsets
    ):
        return "sampling seeds must be the lock seed followed by lock seed + each offset"
    samples = record.get("samples")
    if not isinstance(samples, list) or len(samples) != count:
        return f"sampling must record exactly {count} samples"
    contact_ids: list[str] = []
    for index, sample in enumerate(samples):
        keys = {
            "sample_index", "seed", "override", "contact_id", "request_sha256", "response_text_sha256", status_key,
        }
        if status_key == "note_parse_status":
            keys.add("candidate_intent_ids")
        if not isinstance(sample, Mapping) or set(sample) != keys:
            return "sampling sample record has an invalid shape"
        if sample["sample_index"] != index or sample["seed"] != seeds[index]:
            return "sampling samples must be ordered by sample_index and carry their derived seed"
        if (sample["override"] is None) != (index == 0) or (
            index > 0 and dict(sample["override"]) != dict(decoding)
        ):
            return "sampling sample 0 is greedy (override None); every later sample carries the declared override"
        if not isinstance(sample["contact_id"], str) or not sample["contact_id"]:
            return "sampling sample lacks its contact identity"
        contact_ids.append(sample["contact_id"])
        if not _is_hex64(sample["request_sha256"]) or not _is_hex64(sample["response_text_sha256"]):
            return "sampling sample hashes must be lowercase 64-hex SHA-256"
        if not isinstance(sample[status_key], str) or not sample[status_key]:
            return f"sampling sample {status_key} must be a non-empty string"
        if status_key == "note_parse_status":
            ids = sample["candidate_intent_ids"]
            if (
                not isinstance(ids, list) or any(not isinstance(value, str) or not value for value in ids)
                or len(set(ids)) != len(ids)
            ):
                return "sampling sample candidate_intent_ids must be distinct non-empty strings"
    if len(set(contact_ids)) != len(contact_ids):
        return "sampling samples must have distinct contact ids"
    return None


def perception_branch_sampling_error(sampling: object, *, is_b: bool) -> str | None:
    """Why a v6 row's ``sampling`` value is malformed, or ``None`` when it is well formed (``None`` for A / the twin)."""

    if not is_b:
        return None if sampling is None else "the delivering branch (A) and its twin (T) must declare no sampling axis"
    if not isinstance(sampling, Mapping) or set(sampling) != set(SAMPLING_AXES):
        return f"a sampling branch row must carry exactly {list(SAMPLING_AXES)}"
    if all(sampling[axis] is None for axis in SAMPLING_AXES):
        return "a B sampling branch must declare at least one sampling axis"
    perception = sampling["perception_samples"]
    if perception is not None:
        if not isinstance(perception, Mapping) or set(perception) != {
            "k", "decoding", "seed_offsets", "seeds", "samples", "merge_policy", "cap",
            "support_counts", "merged_candidate_ids", "appended_candidate_ids",
        }:
            return "sampling perception_samples record has an invalid shape"
        reason = _sampling_stream_error(
            perception, count_key="k", low=2, high=4, status_key="note_parse_status",
        )
        if reason is not None:
            return reason
        if not isinstance(perception["merge_policy"], str) or not perception["merge_policy"]:
            return "sampling merge_policy must be a non-empty string"
        if not _is_int(perception["cap"], 1):
            return "sampling cap must be a positive integer"
        merged = perception["merged_candidate_ids"]
        appended = perception["appended_candidate_ids"]
        if (
            not isinstance(merged, list) or len(merged) > perception["cap"]
            or any(not isinstance(value, str) or not value for value in merged)
            or len(set(merged)) != len(merged)
            or not isinstance(appended, list) or any(value not in merged for value in appended)
        ):
            return "sampling merged_candidate_ids must be distinct, within the cap, and contain every appended id"
        first = perception["samples"][0]["candidate_intent_ids"]
        if merged[: len(first)] != first[: perception["cap"]]:
            return "sampling merged list must start with sample 0's own list verbatim"
        counts = perception["support_counts"]
        if not isinstance(counts, list) or any(
            not isinstance(row, Mapping) or set(row) != {"intent_id", "support", "best_rank"}
            or not _is_int(row["support"], 1) or not _is_int(row["best_rank"], 1)
            for row in counts
        ) or any(value not in {row["intent_id"] for row in counts} for value in merged):
            return "sampling support_counts must cover every merged candidate"
    solver = sampling["solver_samples"]
    if solver is not None:
        if not isinstance(solver, Mapping) or set(solver) != {
            "n", "greedy_first", "decoding", "seed_offsets", "seeds", "samples", "commit", "outcome",
        }:
            return "sampling solver_samples record has an invalid shape"
        reason = _sampling_stream_error(
            solver, count_key="n", low=2, high=8, status_key="parse_status",
        )
        if reason is not None:
            return reason
        if solver["greedy_first"] is not True:
            return "sampling greedy_first must be true: the first-support commit keeps sample 0's labels"
        commit = solver["commit"]
        if not isinstance(commit, Mapping) or set(commit) != {
            "policy", "min_support", "similarity_threshold", "n1_min", "empty_votes_min",
        } or not isinstance(commit["policy"], str) or not commit["policy"]:
            return "sampling commit must carry policy, min_support, similarity_threshold, n1_min, empty_votes_min"
        outcome = solver["outcome"]
        if not isinstance(outcome, Mapping) or set(outcome) != {
            "intent_support", "entity_supports", "delivered_entity_count", "gate",
        } or not _is_int(outcome["delivered_entity_count"], 0) or not isinstance(outcome["entity_supports"], list):
            return "sampling commit outcome has an invalid shape"
        if outcome["gate"] is not None and not isinstance(outcome["gate"], Mapping):
            return "sampling commit outcome gate must be None or a mapping"
    return None


_PERCEPTION_BRANCH_LEVELS = (1, 2)
_PERCEPTION_BRANCH_VISITS = "first"


def validate_perception_branch_receipt(
    perception_branches: Mapping[str, object],
    *,
    branch_ids: Sequence[str],
    delivered_branch_id: str,
    twin_branch_id: str | None,
    phase_id: str,
    level: int,
    error_type: type[Exception] = ValueError,
) -> None:
    """Validate the custody a Perception branch visit keeps (phase 2, item
    merge set C).

    Structurally :func:`validate_supply_variant_receipt`'s twin, checked
    against the SAME row-identity discipline: distinct branch ids, EVERY
    declared branch present exactly once in declared order, the delivering
    branch (A) named and last, exactly one twin (T) naming A and resolving
    exactly A's OWN supplied ids, and every non-delivering branch's note
    custody sealed under its own row.

    AT-P2 ("T's wire bytes equal A's") is a structural guarantee of
    ``rails.runner.perception_branch_messages`` (the twin takes
    ``base_messages(ctx)`` UNCHANGED, the identical call A's own branch
    makes), not something this receipt-level check can re-verify through a
    raw ``request_sha256`` comparison: that per-contact digest necessarily
    differs between T and A, because it hashes the WHOLE realised request,
    including the one history turn that names each contact's OWN identity
    (``request_id``) -- the same reason phase 1's own AT2 test compares
    specific wire-payload FIELDS rather than a full-request digest between
    an arm and its twin. This function checks the supply-level proxy
    instead: T's ``supplied_value_ids`` must equal A's exactly. (An earlier
    revision of this function additionally required T's and A's
    ``request_sha256`` to be equal; that check could never pass for a real
    contact and was removed once a live episode proved it -- see
    ``tests/unit/test_perception_branch_live.py``.)

    ``branch_ids``/``delivered_branch_id``/``twin_branch_id``/``level`` are
    the CONFIGURATION's own -- the sealing caller reads them off the composed
    config, a post-seal reader off the raw
    ``native_episode.roles.perception.branches`` block -- so a receipt can
    never describe a group other than the one the cell declared.

    At level 1 no branch row carries a Solver-column field. At level 2 EVERY
    branch row carries all four (design section 3, "Level 2"): A's own
    naming its ordinary first Solver visit (no new contact), every other
    branch's naming the one Solver contact its note fanned out.

    Schema v2 (2026-09-29, the P-SV-1 seal abort): every branch row also
    carries ``candidate_intent_ids_raw_count``; ``candidate_intent_ids`` must
    be distinct (duplicates were collapsed at parse time) and may be empty
    exactly when ``note_parse_status`` is ``empty`` or ``malformed``
    (:func:`perception_branch_note_fields_error`); ``min_candidates_met`` must
    equal ``len(candidate_intent_ids) >= min_candidates``. A v1 row keeps its
    original rule (a non-empty list of distinct strings) so an already-sealed
    v1 bundle verifies unchanged.
    """

    declared = list(branch_ids)
    if not declared or len(set(declared)) != len(declared):
        _raise(error_type, "perception branch receipt requires distinct declared branch ids")
    if not isinstance(delivered_branch_id, str) or delivered_branch_id != declared[-1]:
        _raise(
            error_type,
            "perception branch receipt requires the delivering branch (A) to be "
            "the last declared branch",
        )
    twin_optional = (
        isinstance(perception_branches, Mapping)
        and perception_branches.get("schema") == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5
    )
    if twin_branch_id is None and twin_optional:
        pass                                     # a v5 (thinking-policy) column may fly without a twin
    elif not isinstance(twin_branch_id, str) or twin_branch_id not in declared:
        _raise(error_type, "perception branch receipt names an undeclared twin branch")
    if level not in _PERCEPTION_BRANCH_LEVELS:
        _raise(error_type, "perception branch receipt level must be 1 or 2")
    if not isinstance(perception_branches, Mapping) or set(perception_branches) != _PERCEPTION_BRANCH_FIELDS:
        _raise(error_type, "perception branch receipt has an invalid shape")
    schema = perception_branches["schema"]
    if schema not in PERCEPTION_BRANCH_RECEIPT_SCHEMAS:
        _raise(error_type, "perception branch receipt has an unregistered schema")
    is_v2 = schema in PERCEPTION_BRANCH_NOTE_FIELD_SCHEMAS
    is_v4 = schema == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4
    is_v5 = schema == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5
    is_v6 = schema == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6
    is_v3 = schema in (
        PERCEPTION_BRANCH_RECEIPT_SCHEMA, PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4, PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5,
        PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6,
    )
    if perception_branches["phase_id"] != phase_id:
        _raise(error_type, "perception branch receipt names another phase")
    if perception_branches["level"] != level:
        _raise(error_type, "perception branch receipt names another level")
    if perception_branches["branch_count"] != len(declared):
        _raise(error_type, "perception branch receipt does not carry every declared branch")
    if perception_branches["delivered_branch_id"] != delivered_branch_id:
        _raise(error_type, "perception branch receipt names another delivering branch")
    if perception_branches["branch_visits"] != _PERCEPTION_BRANCH_VISITS:
        _raise(
            error_type,
            "perception branch receipt branch_visits must be "
            f"{_PERCEPTION_BRANCH_VISITS!r}: Perception has no 'every' fan-out",
        )
    visit_index = perception_branches["visit_index"]
    if isinstance(visit_index, bool) or visit_index != 0:
        _raise(
            error_type,
            "perception branch receipt visit_index must be 0: Perception has "
            "one visit per row",
        )
    fit = perception_branches["fit_estimate"]
    if not isinstance(fit, Mapping) or set(fit) != _PERCEPTION_BRANCH_FIT_FIELDS:
        _raise(error_type, "perception branch receipt fit estimate has an invalid shape")
    rows = _sequence(
        perception_branches["branches"], "perception branches", error_type=error_type,
    )
    if len(rows) != len(declared):
        _raise(error_type, "perception branch receipt does not carry every declared branch")
    expected_fields = (
        _PERCEPTION_BRANCH_LEVEL2_FIELDS if level == 2 else _PERCEPTION_BRANCH_RECORD_FIELDS
    )
    if is_v2:
        expected_fields = expected_fields | _PERCEPTION_BRANCH_V2_EXTRA_FIELDS
    if is_v3:
        expected_fields = expected_fields | _PERCEPTION_BRANCH_V3_EXTRA_FIELDS
    if is_v4:
        expected_fields = expected_fields | _PERCEPTION_BRANCH_V4_EXTRA_FIELDS
    if is_v5:
        expected_fields = expected_fields | _PERCEPTION_BRANCH_V5_EXTRA_FIELDS
    if is_v6:
        expected_fields = expected_fields | _PERCEPTION_BRANCH_V6_EXTRA_FIELDS
    contact_ids: list[str] = []
    delivering_ids: tuple[str, ...] | None = None
    delivering_request_sha256: str | None = None
    twin_seen = False
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) not in (
            expected_fields, expected_fields | PERCEPTION_BRANCH_ABSENT_FIELDS,
        ):
            _raise(error_type, "perception branch record has an invalid shape")
        if "solver_absent" in row:
            # NX-T R1 seal fix: an absent Solver column exists only at level 2, only on a NON-delivering branch (the delivering
            # arm keeps its fail-closed custody), and always names the code path that ended it.
            if level != 2:
                _raise(error_type, "perception branch solver_absent exists only at level 2")
            if row["solver_absent"] is not True:
                _raise(error_type, "perception branch solver_absent must be true when present")
            if row["absent_reason"] not in PERCEPTION_BRANCH_ABSENT_REASONS:
                _raise(
                    error_type,
                    f"perception branch absent_reason must be one of {sorted(PERCEPTION_BRANCH_ABSENT_REASONS)}",
                )
            if row["branch_id"] == delivered_branch_id:
                _raise(error_type, "the delivering perception branch (A) cannot have an absent Solver column")
        if row["branch_index"] != index:
            _raise(error_type, "perception branches must be ordered by ascending branch_index")
        if row["branch_id"] != declared[index]:
            _raise(error_type, "perception branches must appear in their declared order")
        deliver = row["deliver"]
        if not isinstance(deliver, bool) or deliver != (row["branch_id"] == delivered_branch_id):
            _raise(error_type, "perception branch disagrees with the declared delivering branch")
        contact_id = row["contact_id"]
        if not isinstance(contact_id, str) or not contact_id:
            _raise(error_type, "perception branch lacks its contact identity")
        contact_ids.append(contact_id)
        replicate_of = row.get("replicate_of")
        is_twin = twin_branch_id is not None and row["branch_id"] == twin_branch_id
        if is_twin:
            if replicate_of != delivered_branch_id:
                _raise(
                    error_type,
                    "perception branch receipt names a twin that does not "
                    "replicate the delivering branch",
                )
            if deliver:
                _raise(error_type, "the delivering perception branch cannot also be the twin")
            twin_seen = True
        elif replicate_of is not None:
            _raise(
                error_type,
                "only the declared twin branch may carry replicate_of in a "
                "perception branch receipt",
            )
        for field in ("request_sha256", "response_text_sha256", "note_sha256"):
            value = row[field]
            if not isinstance(value, str) or len(value) != 64 or any(
                character not in "0123456789abcdef" for character in value
            ):
                _raise(error_type, f"perception branch {field} must be a lowercase 64-hex SHA-256")
        if not isinstance(row["note_parse_status"], str) or not row["note_parse_status"]:
            _raise(error_type, "perception branch note_parse_status must be a non-empty string")
        knobs = _sequence(
            row["resolved_knobs"], "perception branch resolved_knobs", error_type=error_type,
        )
        if any(
            not isinstance(entry, Mapping)
            or set(entry) != {"path", "value"}
            or not isinstance(entry["path"], str)
            or not entry["path"]
            or isinstance(entry["value"], bool)
            or not isinstance(entry["value"], (int, float))
            for entry in knobs
        ):
            _raise(error_type, "perception branch has malformed resolved knobs")
        paths = [entry["path"] for entry in knobs]
        if len(set(paths)) != len(paths) or paths != sorted(paths):
            _raise(
                error_type,
                "perception branch resolved knobs must be distinct and ordered by path",
            )
        release_swap = row.get("release_swap")
        if release_swap is not None and (
            not isinstance(release_swap, Mapping)
            or set(release_swap) != {"store_id", "release"}
            or not isinstance(release_swap["store_id"], str)
            or not release_swap["store_id"]
            or not isinstance(release_swap["release"], str)
            or not release_swap["release"]
        ):
            _raise(error_type, "perception branch release_swap has an invalid shape")
        presentation_id = row.get("presentation_id")
        if presentation_id is not None and (
            not isinstance(presentation_id, str) or not presentation_id
        ):
            _raise(error_type, "perception branch presentation_id must be a non-empty string")
        min_candidates = row.get("min_candidates")
        if min_candidates is not None and (
            isinstance(min_candidates, bool)
            or not isinstance(min_candidates, int)
            or min_candidates < 1
        ):
            _raise(error_type, "perception branch min_candidates must be a positive integer")
        presentation_skip_reason = row.get("presentation_skip_reason")
        if presentation_skip_reason is not None and (
            not isinstance(presentation_skip_reason, str) or not presentation_skip_reason
        ):
            _raise(
                error_type,
                "perception branch presentation_skip_reason must be a "
                "non-empty string or None",
            )
        contrast_block_sha256 = row.get("contrast_block_sha256")
        if contrast_block_sha256 is not None and (
            not isinstance(contrast_block_sha256, str)
            or len(contrast_block_sha256) != 64
            or any(character not in "0123456789abcdef" for character in contrast_block_sha256)
        ):
            _raise(
                error_type,
                "perception branch contrast_block_sha256 must be a lowercase "
                "64-hex SHA-256 or None",
            )
        if presentation_skip_reason is not None and contrast_block_sha256 is not None:
            _raise(
                error_type,
                "perception branch cannot carry both a rendered "
                "contrast_block_sha256 and a presentation_skip_reason",
            )
        if (
            presentation_id is None
            and (presentation_skip_reason is not None or contrast_block_sha256 is not None)
        ):
            _raise(
                error_type,
                "perception branch carries a presentation outcome but "
                "declares no presentation_id",
            )
        min_candidates_met = row.get("min_candidates_met")
        if min_candidates is None:
            if min_candidates_met is not None:
                _raise(
                    error_type,
                    "perception branch carries min_candidates_met but "
                    "declares no min_candidates",
                )
        elif not isinstance(min_candidates_met, bool):
            _raise(
                error_type,
                "perception branch declares min_candidates and must carry a "
                "min_candidates_met bool",
            )
        key_source = row.get("key_source") if is_v3 else None
        key_source_reason = perception_branch_key_source_error(key_source)
        if key_source_reason is not None:
            _raise(error_type, key_source_reason)
        instruction_template = row.get("instruction_template") if is_v4 else None
        if instruction_template is not None and (
            not isinstance(instruction_template, Mapping)
            or set(instruction_template) != {"relpath", "sha256"}
            or not isinstance(instruction_template["relpath"], str)
            or not instruction_template["relpath"]
            or not isinstance(instruction_template["sha256"], str)
            or len(instruction_template["sha256"]) != 64
            or any(
                character not in "0123456789abcdef"
                for character in instruction_template["sha256"]
            )
        ):
            _raise(
                error_type,
                "perception branch instruction_template must be None or exactly "
                "{relpath, sha256} with a lowercase 64-hex sha256",
            )
        thinking_policy = row.get("thinking_policy") if is_v5 else None
        reason = perception_branch_thinking_policy_error(thinking_policy)
        if reason is not None:
            _raise(error_type, reason)
        sampling = row.get("sampling") if is_v6 else None
        reason = perception_branch_sampling_error(sampling, is_b=is_v6 and not (deliver or is_twin))
        if reason is not None:
            _raise(error_type, reason)
        if deliver or is_twin:
            if (
                paths or release_swap is not None or presentation_id is not None
                or min_candidates is not None or presentation_skip_reason is not None
                or contrast_block_sha256 is not None or min_candidates_met is not None
                or key_source is not None or instruction_template is not None
                or thinking_policy is not None
            ):
                _raise(
                    error_type,
                    "the delivering perception branch (A) and its twin (T) must "
                    "declare no axis",
                )
        elif is_v6 and (
            paths or release_swap is not None or presentation_id is not None
            or min_candidates is not None or key_source is not None
            or instruction_template is not None or thinking_policy is not None
        ):
            _raise(
                error_type,
                "a v6 (sampling) perception branch declares its sampling axes as its only axis category",
            )
        elif not (
            paths or release_swap is not None or presentation_id is not None
            or min_candidates is not None or key_source is not None
            or instruction_template is not None or thinking_policy is not None or sampling is not None
        ):
            _raise(
                error_type,
                "a B perception branch must declare exactly one axis category",
            )
        elif is_v4 and (
            instruction_template is None
            or paths or release_swap is not None or presentation_id is not None
            or min_candidates is not None or key_source is not None
        ):
            _raise(
                error_type,
                "a v4 (template) perception branch declares its instruction_template "
                "as its only axis",
            )
        elif is_v5 and (
            thinking_policy is None
            or paths or release_swap is not None or presentation_id is not None
            or min_candidates is not None or key_source is not None
        ):
            _raise(
                error_type,
                "a v5 (thinking-policy) perception branch declares its thinking_policy as its only axis",
            )
        ids = _sequence(
            row["supplied_value_ids"], "perception branch supplied_value_ids", error_type=error_type,
        )
        if any(not isinstance(value, str) or not value for value in ids):
            _raise(error_type, "perception branch supplied ids must be nonempty strings")
        if len(set(ids)) != len(ids):
            _raise(error_type, "perception branch supplied ids must be unique")
        count = _nonneg_int(
            row["supplied_count"], "perception branch supplied_count", error_type=error_type,
        )
        if count != len(ids):
            _raise(error_type, "perception branch supplied_count disagrees with its ids")
        bound = row["max_supplied_items"]
        if isinstance(bound, bool) or not isinstance(bound, int) or bound < 1:
            _raise(error_type, "perception branch max_supplied_items must be positive")
        if count > bound:
            _raise(
                error_type,
                "perception branch supplied more items than the bound its fit "
                "refusal was computed against",
            )
        candidates = row["candidate_intent_ids"]
        if is_v2:
            # v2: a degenerate list is a measured outcome (empty, or collapsed
            # duplicates), explained by its own status and raw count; only an
            # INCONSISTENT triple is refused.
            reason = perception_branch_note_fields_error(
                row["note_parse_status"], candidates, row["candidate_intent_ids_raw_count"],
            )
            if reason is not None:
                _raise(error_type, reason)
            if min_candidates is not None and min_candidates_met != (
                len(candidates) >= min_candidates
            ):
                _raise(
                    error_type,
                    "perception branch min_candidates_met disagrees with its own "
                    "collapsed candidate list",
                )
        elif (
            not isinstance(candidates, Sequence)
            or isinstance(candidates, (str, bytes))
            or not candidates
            or any(not isinstance(value, str) or not value for value in candidates)
            or len(set(candidates)) != len(candidates)
        ):
            _raise(
                error_type,
                "perception branch candidate_intent_ids must be a non-empty "
                "ordered list of distinct non-empty strings",
            )
        if level == 2:
            for field in (
                "solver_contact_id", "solver_request_sha256", "solver_response_text_sha256",
            ):
                value = row[field]
                if field == "solver_contact_id":
                    if not isinstance(value, str) or not value:
                        _raise(error_type, "perception branch solver_contact_id must be non-empty")
                elif not isinstance(value, str) or len(value) != 64 or any(
                    character not in "0123456789abcdef" for character in value
                ):
                    _raise(error_type, f"perception branch {field} must be a lowercase 64-hex SHA-256")
            supply_ids = row["candidate_supply_value_ids"]
            if (
                not isinstance(supply_ids, Sequence)
                or isinstance(supply_ids, (str, bytes))
                or any(not isinstance(value, str) or not value for value in supply_ids)
                or len(set(supply_ids)) != len(supply_ids)
            ):
                _raise(
                    error_type,
                    "perception branch candidate_supply_value_ids must be a list "
                    "of distinct non-empty strings",
                )
        if deliver:
            delivering_ids = tuple(ids)
    if len(set(contact_ids)) != len(contact_ids):
        _raise(error_type, "perception branches must have distinct contact ids")
    if not twin_seen and not (twin_branch_id is None and twin_optional):
        _raise(error_type, "perception branch receipt does not carry the declared twin")
    for row in rows:
        if twin_branch_id is None or row["branch_id"] != twin_branch_id:
            continue
        if delivering_ids is None or tuple(row["supplied_value_ids"]) != delivering_ids:
            _raise(
                error_type,
                "perception twin branch does not resolve exactly the delivering "
                "branch's ids",
            )


__all__ = [
    "PLANNER_ACTION_ILLEGAL_DISPOSITION", "is_illegal_planner_route",
    "NativeEpisodeDelivery", "SUPPLY_VARIANT_RECEIPT_SCHEMA",
    "validate_native_episode_delivery_receipt",
    "validate_native_candidate_refresh_receipt", "validate_native_episode_terminal_policy",
    "validate_native_episode_finite_path", "validate_solver_group_receipt",
    "validate_supply_variant_receipt",
    "SUPPLY_VARIANT_RECEIPT_SCHEMA_V4",
    "SUPPLY_VARIANT_RECEIPT_SCHEMA_V5",
    "SUPPLY_VARIANT_RECEIPT_SCHEMA_V6",
    "DECODING_VARIANT_KNOBS",
    "decoding_override_error",
    "supply_variant_arm_release_swaps",
    "PERCEPTION_BRANCH_ABSENT_FIELDS",
    "PERCEPTION_BRANCH_ABSENT_REASONS",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6",
    "SAMPLING_AXES",
    "perception_branch_sampling_error",
    "perception_branch_thinking_policy_error",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMAS",
    "PERCEPTION_BRANCH_NOTE_FIELD_SCHEMAS",
    "PERCEPTION_BRANCH_KEY_SOURCE_FIELDS",
    "perception_branch_key_source_error",
    "PERCEPTION_BRANCH_NOTE_OK",
    "PERCEPTION_BRANCH_NOTE_DUPLICATES_COLLAPSED",
    "PERCEPTION_BRANCH_NOTE_EMPTY",
    "PERCEPTION_BRANCH_NOTE_MALFORMED",
    "PERCEPTION_BRANCH_NOTE_PARSE_STATUSES",
    "parse_perception_branch_note",
    "perception_branch_note_fields_error",
    "validate_perception_branch_receipt",
]
