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
(``sample_index``, ``seed``, ``temperature``, parse status, parsed answer),
the commit policy's id and the exact parameters it was applied with, and the
delivered answer's support/tie-break provenance.

``reproduction.ojw.native_episode``'s ``_ApplyRole``/``_execution_receipt``
never read ``solver_group`` and are therefore unchanged by this module; a
samples-1 group (this function still accepts N == 1, trivially) is
byte-identical in its ``execution_receipt`` to a single ungrouped Solver
visit, with an all-support-1 ``solver_group`` record alongside it.

Live wiring (E2b): :class:`GroupedSolverRoleNode` below is the graph-facing
seam. ``rails.runner._invoke_native_role_episode`` builds one Solver
``NativeRoleNode`` exactly as it always has (with a ``contact_context``
provider that additionally tags every contact's ``sample_index`` as
``invocation_index % samples`` whenever the Solver role declares
``samples >= 2``), then wraps it in a ``GroupedSolverRoleNode`` and places
THAT at the "solver" position of ``reproduction.ojw.native_episode``'s role
graph instead of the plain node. Every sample is a REAL
``NativeRoleNode.invoke_direct`` call through the SAME metered request path
an ungrouped Solver visit uses, so contact counting, budget/FIT gates,
exposure and cost accounting all see every one of the N contacts as an
ordinary contact -- no separate accounting path exists or is needed.

E2c (2026-09-17): module M2 is sample-and-aggregate COMMIT, so the committed
answer IS the Solver's draft. The ``on_commit`` seam below hands the
committed role result to the caller before the graph advances;
``rails.runner._invoke_native_role_episode`` uses it to register exactly ONE
``phase:<solver>`` agent state per Solver visit, carrying that committed
answer, so the Reviewer and the Planner read one draft exactly as they do on
a samples-1 (anchor) visit. The N raw samples stay in custody -- in
``solver_group`` and in each sample's own contact, wave, trace and cost
records -- and this module's own aggregation is unchanged.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import WorkflowComponent

from .native_roles import NativeRoleNode, NativeRoleNodeSpec


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


def parse_solver_answer_text(text: str):
    """The structured answer of one Solver sample's raw text, or ``None`` when it does not parse -- the ONE parse the grouped
    visit and the decision-338 sampling column both vote with."""

    return _default_parse_answer(text)


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
        or not {"temperature", "seed_offset"} <= set(decoding_overrides)
        or not set(decoding_overrides) <= {"temperature", "seed_offset", "greedy_first"}
        or ("greedy_first" in decoding_overrides and decoding_overrides["greedy_first"] is not True)
    ):
        raise GroupedSolverError(
            "decoding_overrides must carry exactly temperature and seed_offset "
            "(and optionally greedy_first: true)"
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
    greedy_first = decoding_overrides.get("greedy_first", False) is True

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
            # VER-1a: the greedy first sample is custodied at the fragment's own
            # temperature 0 (``compose_solver_sample_decoding_params``).
            "temperature": 0 if (greedy_first and sample_index == 0) else temperature,
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
            # E2d (2026-09-17): the parameters the policy was ACTUALLY applied
            # with, recorded beside its id so a post-seal reader -- the bundle
            # verifier's I7g re-derivation, and the offline sensitivity table --
            # can re-run the exact commit this visit made without the composed
            # config, which no sealed bundle carries.
            "commit_params": dict(commit_params),
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


class GroupedSolverRoleNode(WorkflowComponent):
    """The "solver" position of a live native episode graph, grouped (E2b).

    Wraps ONE real Solver ``NativeRoleNode`` (``inner``) built exactly as an
    ungrouped Solver node always has -- same spec, same metered request
    path, same ``contact_context_provider`` -- and, on ``invoke()`` (the
    same ``{"query": ...} -> role-result`` contract
    ``reproduction.ojw.native_episode._add_role`` wires into the graph),
    drives :func:`run_grouped_solver_samples` over ``samples`` sequential
    ``inner.invoke_direct(query)`` calls instead of a single one.

    ``on_commit`` (E2c) is called with the committed role result the moment
    the commit policy has run and BEFORE this node returns, so the caller
    can register the committed answer as this visit's ONE Solver phase
    state while the visit's last sample is still its pending contact
    (``rails.runner._invoke_native_role_episode.record_solver_commit``).
    ``None`` -- the default, and every caller written before E2c -- leaves
    the node's behaviour byte-identical.

    Placed by ``rails.runner._invoke_native_role_episode`` in place of a
    plain ``NativeRoleNode`` whenever the Solver role's registered
    ``samples >= 2``; never constructed for a samples-1 role, so that path
    is untouched by this class's existence. ``spec`` delegates to
    ``inner.spec`` (``reproduction.ojw.native_episode.build_native_episode``
    and ``_RoleQuery`` read only ``spec.role_id``/``spec.role_kind``) and
    ``close()`` delegates to ``inner.close()``: there is no separate outer
    agent or rail to release.
    """

    def __init__(
        self,
        *,
        inner: NativeRoleNode,
        samples: int,
        fragment_seed: int,
        decoding_overrides: Mapping[str, object],
        commit: Mapping[str, object],
        delivery_allowed: Callable[[str, str], bool] = _default_delivery_allowed,
        on_commit: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        super().__init__()
        if not isinstance(inner, NativeRoleNode) or inner.spec.role_kind != "solver":
            raise GroupedSolverError(
                "a grouped Solver visit requires an inner Solver NativeRoleNode"
            )
        if not callable(delivery_allowed):
            raise GroupedSolverError("delivery_allowed must be callable")
        if on_commit is not None and not callable(on_commit):
            raise GroupedSolverError("on_commit must be callable")
        self._inner = inner
        self._samples = samples
        self._fragment_seed = fragment_seed
        self._decoding_overrides = dict(decoding_overrides)
        self._commit = dict(commit)
        self._delivery_allowed = delivery_allowed
        self._on_commit = on_commit

    @property
    def spec(self) -> NativeRoleNodeSpec:
        return self._inner.spec

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        query = inputs.get("query")
        if not isinstance(query, str) or not query:
            raise GroupedSolverError("native role query must be non-empty text")
        inner = self._inner

        async def invoke_sample(_sample_index: int) -> dict[str, object]:
            return await inner.invoke_direct(query)

        result = await run_grouped_solver_samples(
            invoke_sample,
            samples=self._samples,
            fragment_seed=self._fragment_seed,
            decoding_overrides=self._decoding_overrides,
            commit=self._commit,
            delivery_allowed=self._delivery_allowed,
        )
        # E2c: hand the committed answer to the caller BEFORE the graph
        # advances, while this visit's last sample is still the caller's
        # pending contact -- that is what lets the episode register ONE
        # Solver phase state per visit carrying this exact text.
        if self._on_commit is not None:
            self._on_commit(result)
        return result

    async def close(self) -> None:
        await self._inner.close()


__all__ = [
    "GroupedSolverError", "GroupedSolverRoleNode", "run_grouped_solver_samples",
]
