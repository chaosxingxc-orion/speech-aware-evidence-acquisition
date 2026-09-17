"""Grouped Solver sampling orchestration (E2, SLURP v2 base program M2).

``docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`` section
4, item M2: inside the native four-role episode, the Solver phase may be
sampled N times per request (temperature > 0, distinct pinned seeds), with
ALL N raw responses kept in custody, and a deterministic, registered COMMIT
policy (``core.base.COMMIT_POLICIES``, ``rails.commit_policies``) that
aggregates the N structured answers into the one delivered answer.

This module composes N independent Solver role invocations -- each produced
by the caller's ``invoke_sample`` callback, typically a partial binding to
``reproduction.ojw.native_roles.NativeRoleNode.invoke_direct`` on a Solver
node whose ``metered_request`` callback (``reproduction.ojw.native_request.
MeteredNativeSpeechRequest``, constructed with ``solver_role_id`` and
``solver_sampling``) and ``contact_context_provider`` (emitting
``sample_index``-tagged ``reproduction.ojw.native_roles.
NativeRoleContactContext`` values) already apply this program's per-sample
decoding override -- into the ONE role-result the rest of the episode graph
consumes.

Each sample's callback returns the SAME per-role result shape
``NativeRoleNode._run`` already returns: ``role_id``, ``actor_output``,
``result_type``, ``delivery_eligible``, ``execution_receipt`` (``contacts``
plus ``final_contact``). :func:`run_grouped_solver_samples` parses every
sample's ``actor_output``, resolves and applies the registered commit
policy, renders the committed answer in the EXACT format
``reproduction.slurp_delivery``/``reproduction.slurp_scoring`` already parse
and score, merges the N execution receipts into ONE (``contacts`` = every
sample's contacts concatenated in sample order, ``final_contact`` = the
last), and returns a role-result dict in that SAME contract shape plus one
additional ``solver_group`` custody field carrying every raw sample
(``sample_index``, ``seed``, ``temperature``, parse status, parsed answer)
and the delivered answer's support/tie-break provenance.

``reproduction.ojw.native_episode``'s ``_ApplyRole``/``_execution_receipt``
never read ``solver_group`` and are therefore unchanged by this module; a
samples-1 group (this function still accepts N == 1, trivially) is
byte-identical in its ``execution_receipt`` to a single ungrouped Solver
visit, with an all-support-1 ``solver_group`` record alongside it.

Remaining integration seam, explicitly out of this module's scope: wiring a
live episode's Solver ``NativeRoleNode`` with a ``contact_context_provider``
sized to ``roles.solver.samples`` and calling this module through it is
``core.flight.runtime.FlightRuntime``'s job, not this module's.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any


class GroupedSolverError(ValueError):
    """A grouped Solver sample, its config, or its commit policy is invalid."""


def _default_parse_answer(text: str):
    from ..slurp_scoring import SlotEntity, parse_slu_response  # noqa: PLC0415

    scenario, action, entities, parsed = parse_slu_response(text)
    if not parsed:
        return None
    from ...rails.commit_policies import ParsedSlurpAnswer  # noqa: PLC0415

    return ParsedSlurpAnswer(
        scenario=scenario or "",
        action=action or "",
        entities=tuple(SlotEntity(type=entity.type, filler=entity.filler) for entity in entities),
    )


def _default_render_answer(answer) -> str:
    import json

    payload = {
        "scenario": answer.scenario,
        "action": answer.action,
        "entities": [{"type": entity.type, "filler": entity.filler} for entity in answer.entities],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _default_delivery_allowed(_role_id: str, actor_output: str) -> bool:
    return bool(actor_output)


async def run_grouped_solver_samples(
    invoke_sample: Callable[[int], Awaitable[Mapping[str, Any]]],
    *,
    samples: int,
    fragment_seed: int,
    decoding_overrides: Mapping[str, object],
    commit: Mapping[str, object],
    parse_answer: Callable[[str], object] = _default_parse_answer,
    render_answer: Callable[[object], str] = _default_render_answer,
    delivery_allowed: Callable[[str, str], bool] = _default_delivery_allowed,
) -> dict[str, object]:
    """Run N Solver samples and commit them into one delivered role result.

    ``decoding_overrides`` and ``commit`` are the SAME mappings the composed
    config carries at ``native_episode.roles.solver.decoding_overrides`` and
    ``...commit`` -- this function's caller passes them through unchanged
    rather than re-deriving them, so the recorded custody (seed, temperature)
    and the applied commit parameters can never drift from the config that
    the request-composition path (``reproduction.ojw.native_request.
    compose_solver_sample_decoding_params``) actually used.
    """

    from ...core.base import COMMIT_POLICIES, CoreError  # noqa: PLC0415
    from ...rails.commit_policies import SolverSampleVote  # noqa: PLC0415
    # Function-local: importing rails.commit_policies is what POPULATES
    # core.base.COMMIT_POLICIES; this module deliberately does not import it
    # at module scope (same discipline as every other registration import in
    # this package).
    from ...rails import commit_policies as _commit_policies  # noqa: PLC0415, F401

    if isinstance(samples, bool) or not isinstance(samples, int) or not 1 <= samples <= 8:
        raise GroupedSolverError("samples must be an integer between 1 and 8")
    if not callable(invoke_sample):
        raise GroupedSolverError("invoke_sample must be callable")
    if isinstance(fragment_seed, bool) or not isinstance(fragment_seed, int):
        raise GroupedSolverError("fragment_seed must be an integer")
    if (
        not isinstance(decoding_overrides, Mapping)
        or set(decoding_overrides) != {"temperature", "seed_offset"}
    ):
        raise GroupedSolverError(
            "decoding_overrides must carry exactly temperature and seed_offset"
        )
    if not isinstance(commit, Mapping) or set(commit) != {
        "policy", "min_support", "similarity_threshold",
    }:
        raise GroupedSolverError(
            "commit must carry exactly policy, min_support and similarity_threshold"
        )
    commit_policy_id = commit["policy"]
    commit_params = {"min_support": commit["min_support"], "similarity_threshold": commit["similarity_threshold"]}
    try:
        policy = COMMIT_POLICIES.resolve(commit_policy_id)
    except CoreError as error:
        raise GroupedSolverError(str(error)) from error

    role_id: str | None = None
    contacts: list[dict[str, str]] = []
    sample_records: list[dict[str, object]] = []
    votes: list[SolverSampleVote] = []
    seed_offset = decoding_overrides["seed_offset"]
    temperature = decoding_overrides["temperature"]

    for sample_index in range(samples):
        result = await invoke_sample(sample_index)
        if (
            not isinstance(result, Mapping)
            or result.get("result_type") != "answer"
            or not isinstance(result.get("actor_output"), str)
            or not result.get("actor_output")
            or not isinstance(result.get("role_id"), str)
            or not result.get("role_id")
        ):
            raise GroupedSolverError(
                f"grouped Solver sample {sample_index} returned no answer"
            )
        if role_id is None:
            role_id = result["role_id"]
        elif result["role_id"] != role_id:
            raise GroupedSolverError("every grouped Solver sample must share one role_id")
        receipt = result.get("execution_receipt")
        raw_contacts = receipt.get("contacts") if isinstance(receipt, Mapping) else None
        if (
            not isinstance(receipt, Mapping)
            or not isinstance(raw_contacts, Sequence)
            or isinstance(raw_contacts, (str, bytes))
            or not raw_contacts
            or not all(isinstance(contact, Mapping) for contact in raw_contacts)
        ):
            raise GroupedSolverError(
                f"grouped Solver sample {sample_index} has no execution receipt"
            )
        sample_contacts = [dict(contact) for contact in raw_contacts]
        contacts.extend(sample_contacts)

        actor_output = result["actor_output"]
        parsed = parse_answer(actor_output)
        sample_records.append({
            "sample_index": sample_index,
            "seed": fragment_seed + seed_offset + sample_index,
            "temperature": temperature,
            "parse_status": "ok" if parsed is not None else "malformed",
            "parsed_answer": (
                None
                if parsed is None
                else {
                    "scenario": parsed.scenario,
                    "action": parsed.action,
                    "entities": [
                        {"type": entity.type, "filler": entity.filler}
                        for entity in parsed.entities
                    ],
                }
            ),
            "contacts": sample_contacts,
        })
        votes.append(SolverSampleVote(sample_index=sample_index, parsed=parsed))

    try:
        outcome = policy(votes, **dict(commit_params))
    except TypeError as error:
        raise GroupedSolverError(f"commit policy parameters are invalid: {error}") from error

    committed_text = render_answer(outcome.answer)
    eligible = bool(delivery_allowed(role_id, committed_text))
    return {
        "role_id": role_id,
        "actor_output": committed_text,
        "result_type": "answer",
        "delivery_eligible": eligible,
        "execution_receipt": {
            "contacts": contacts,
            "final_contact": contacts[-1],
        },
        "solver_group": {
            "commit_policy_id": outcome.policy_id,
            "samples": sample_records,
            "delivered": {
                "intent_support": outcome.intent_support,
                "intent_member_sample_indices": list(outcome.intent_member_sample_indices),
                "intent_tie_break_sample_index": outcome.intent_tie_break_sample_index,
                "entities": [
                    {
                        "type": entity.type,
                        "filler": entity.filler,
                        "support": entity.support,
                        "member_sample_indices": list(entity.member_sample_indices),
                        "tie_break_sample_index": entity.tie_break_sample_index,
                    }
                    for entity in outcome.entities
                ],
            },
        },
    }


__all__ = ["GroupedSolverError", "run_grouped_solver_samples"]
