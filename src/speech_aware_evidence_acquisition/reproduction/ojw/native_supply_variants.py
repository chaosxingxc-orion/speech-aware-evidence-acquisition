"""Supply-variant arm orchestration (item E42, Stage-3 family VAR-2).

``docs/readiness/2026-09-25-slurp-stage3-var2-supply-variant-interleaving-
design-v1.md``: inside the native four-role episode, the Solver phase may be
contacted K times per visit, each contact composed over a DIFFERENT declared
knowledge-supply construction, with all K raw responses kept in custody and
exactly ONE of them -- the arm the configuration declares ``deliver: true``,
which is the LAST arm and carries no overrides -- delivered.

This module is the structural twin of
:mod:`speech_aware_evidence_acquisition.reproduction.ojw.native_group_solver`,
with two deliberate differences:

* **The varied axis.** E2 varies DECODING per sample and composes it in
  ``native_request.compose_solver_sample_decoding_params``. E42 varies SUPPLY
  per arm and composes it in the caller's binding provider, which reads the
  arm id off ``native_roles.NativeRoleContactContext.variant_arm_id``. Neither
  touches the model fragment, the serving geometry or the prompt order.
* **The delivered text.** E2 delivers the COMMIT policy's aggregate of N
  samples, which is why ``rails.runner``'s delivery binding needs an explicit
  ``solver_group`` exception and why the bundle re-derives it (invariant I7g).
  E42 delivers the delivering arm's OWN response text, unchanged, so invariant
  I7 ("the delivered text is a model response") holds with no new exception and
  no aggregation rule exists to audit. There is therefore no commit policy
  here, and no ``on_commit`` seam: the delivering arm's contact settles through
  the ordinary path and registers the ordinary ONE Solver phase state.

Every arm is a REAL ``NativeRoleNode.invoke_direct`` call through the SAME
metered request path an ungrouped Solver visit uses, so contact counting,
budget and FIT gates, exposure and cost accounting all see every one of the K
contacts as an ordinary contact -- no separate accounting path exists or is
needed.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import WorkflowComponent

from .native_roles import NativeRoleNode, NativeRoleNodeSpec


class SupplyVariantNodeError(ValueError):
    """An arm invocation, its group config or its per-arm record is invalid."""


def _default_delivery_allowed(_role_id: str, actor_output: str) -> bool:
    return bool(actor_output)


async def run_supply_variant_arms(
    invoke_arm: Callable[[int], Awaitable[Mapping[str, Any]]],
    *,
    group,
    arm_record: Callable[[int, Mapping[str, Any]], Mapping[str, object]],
    phase_id: str,
    delivery_allowed: Callable[[str, str], bool] = _default_delivery_allowed,
) -> dict[str, object]:
    """Run K arms and deliver the declared delivering arm's own answer.

    ``group`` is the validated ``rails.supply_variants.SupplyVariantGroup`` the
    composed config carries at ``native_episode.roles.solver.supply_variants``;
    it is passed through rather than re-derived, so the recorded custody can
    never drift from the configuration the request-composition path actually
    used. ``arm_record`` is the caller's own per-arm receipt row -- it is the
    caller, not this module, that knows which value ids the arm's request
    carried, because it is the caller's binding provider that composed them.

    The returned mapping is the SAME per-role result shape
    ``NativeRoleNode._run`` returns (``role_id``, ``actor_output``,
    ``result_type``, ``delivery_eligible``, ``execution_receipt`` with
    ``contacts`` plus ``final_contact``) plus one additional
    ``supply_variants`` custody field. ``actor_output`` is the delivering
    (last) arm's own text, and ``execution_receipt.contacts`` is every arm's
    contacts concatenated in arm order, so ``final_contact`` is the delivering
    arm's own final contact and the delivered text is bound to it.
    """

    from ...rails.supply_variants import (  # noqa: PLC0415 (light top-level imports)
        SupplyVariantError,
        supply_variant_receipt,
    )

    if not callable(invoke_arm):
        raise SupplyVariantNodeError("invoke_arm must be callable")
    if not callable(arm_record):
        raise SupplyVariantNodeError("arm_record must be callable")
    if not callable(delivery_allowed):
        raise SupplyVariantNodeError("delivery_allowed must be callable")
    arms = getattr(group, "arms", None)
    if not isinstance(arms, tuple) or not arms:
        raise SupplyVariantNodeError(
            "a supply-variant visit requires a parsed SupplyVariantGroup"
        )

    role_id: str | None = None
    contacts: list[dict[str, str]] = []
    records: list[Mapping[str, object]] = []
    delivered: Mapping[str, Any] | None = None

    for arm_index, arm in enumerate(arms):
        result = await invoke_arm(arm_index)
        if (
            not isinstance(result, Mapping)
            or result.get("result_type") != "answer"
            or not isinstance(result.get("actor_output"), str)
            or not result.get("actor_output")
            or not isinstance(result.get("role_id"), str)
            or not result.get("role_id")
        ):
            raise SupplyVariantNodeError(
                f"supply-variant arm {arm.arm_id!r} returned no answer"
            )
        if role_id is None:
            role_id = result["role_id"]
        elif result["role_id"] != role_id:
            raise SupplyVariantNodeError(
                "every supply-variant arm must share one role_id"
            )
        receipt = result.get("execution_receipt")
        raw_contacts = receipt.get("contacts") if isinstance(receipt, Mapping) else None
        if (
            not isinstance(receipt, Mapping)
            or not isinstance(raw_contacts, Sequence)
            or isinstance(raw_contacts, (str, bytes))
            or not raw_contacts
            or not all(isinstance(contact, Mapping) for contact in raw_contacts)
        ):
            raise SupplyVariantNodeError(
                f"supply-variant arm {arm.arm_id!r} has no execution receipt"
            )
        contacts.extend(dict(contact) for contact in raw_contacts)
        try:
            row = arm_record(arm_index, result)
        except SupplyVariantError as error:
            raise SupplyVariantNodeError(
                f"supply-variant arm {arm.arm_id!r} record is invalid: {error}"
            ) from error
        if not isinstance(row, Mapping) or row.get("arm_id") != arm.arm_id:
            raise SupplyVariantNodeError(
                f"supply-variant arm {arm.arm_id!r} record names another arm"
            )
        records.append(dict(row))
        if arm.deliver:
            delivered = result

    if delivered is None or delivered is not result:
        # ``parse_supply_variants`` already refuses a group whose delivering arm
        # is not the last one; this is the runtime half of that same statement,
        # and it is what makes ``final_contact`` below the delivered answer's
        # own contact rather than some earlier arm's.
        raise SupplyVariantNodeError(
            "the delivering supply-variant arm must be the last arm invoked"
        )
    actor_output = delivered["actor_output"]
    return {
        "role_id": role_id,
        "actor_output": actor_output,
        "result_type": "answer",
        "delivery_eligible": bool(delivery_allowed(role_id, actor_output)),
        "execution_receipt": {
            "contacts": contacts,
            "final_contact": contacts[-1],
        },
        "supply_variants": supply_variant_receipt(
            group=group, phase_id=phase_id, records=records,
        ),
    }


class SupplyVariantRoleNode(WorkflowComponent):
    """The "solver" position of a live native episode graph, arm-grouped (E42).

    Wraps ONE real Solver ``NativeRoleNode`` (``inner``) built exactly as an
    ungrouped Solver node always has -- same spec, same metered request path,
    same ``contact_context_provider`` -- and, on ``invoke()`` (the same
    ``{"query": ...} -> role-result`` contract
    ``reproduction.ojw.native_episode._add_role`` wires into the graph), drives
    :func:`run_supply_variant_arms` over ``group.arm_count`` sequential
    ``inner.invoke_direct(query)`` calls instead of a single one.

    Placed by ``rails.runner._invoke_native_role_episode`` in place of a plain
    ``NativeRoleNode`` whenever the Solver role declares ``supply_variants``;
    never constructed otherwise, so that path is untouched by this class's
    existence. ``spec`` delegates to ``inner.spec`` and ``close()`` to
    ``inner.close()``, exactly as ``GroupedSolverRoleNode`` does: there is no
    separate outer agent or rail to release.
    """

    def __init__(
        self,
        *,
        inner: NativeRoleNode,
        group,
        arm_record: Callable[[int, Mapping[str, Any]], Mapping[str, object]],
        delivery_allowed: Callable[[str, str], bool] = _default_delivery_allowed,
    ) -> None:
        super().__init__()
        if not isinstance(inner, NativeRoleNode) or inner.spec.role_kind != "solver":
            raise SupplyVariantNodeError(
                "a supply-variant visit requires an inner Solver NativeRoleNode"
            )
        if not callable(arm_record):
            raise SupplyVariantNodeError("arm_record must be callable")
        if not callable(delivery_allowed):
            raise SupplyVariantNodeError("delivery_allowed must be callable")
        self._inner = inner
        self._group = group
        self._arm_record = arm_record
        self._delivery_allowed = delivery_allowed
        # Owner decision 172 (2026-09-27, merge set B): counts REAL visits of
        # this node (not contacts). Under ``group.arm_visits == "first"`` only
        # visit 0 fans out; see ``invoke`` below.
        self._visit_index = 0

    @property
    def spec(self) -> NativeRoleNodeSpec:
        return self._inner.spec

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        query = inputs.get("query")
        if not isinstance(query, str) or not query:
            raise SupplyVariantNodeError("native role query must be non-empty text")
        inner = self._inner
        visit_index = self._visit_index
        self._visit_index += 1
        if getattr(self._group, "arm_visits", "every") == "first" and visit_index > 0:
            # Owner decision 172 (2026-09-27, merge set B): under
            # ``arm_visits: "first"`` only the visit whose GLOBAL visit index
            # is 0 fans out to every declared arm; every later visit of this
            # same node contacts the delivering arm alone, through the
            # ordinary path -- no arm custody, no ``supply_variants`` key on
            # this visit's own result, byte-identical to a plain (unarmed)
            # Solver visit. This is the VAR-2 fix: the fit bound
            # (``max_supplied_items``) then covers exactly one visit, not
            # every revision. ``native_episode._ApplyRole`` carries the
            # visit-0 receipt forward so it still reaches the delivered role
            # result even when a LATER visit is the one actually delivered.
            return await inner.invoke_direct(query)

        async def invoke_arm(_arm_index: int) -> dict[str, object]:
            return await inner.invoke_direct(query)

        return await run_supply_variant_arms(
            invoke_arm,
            group=self._group,
            arm_record=self._arm_record,
            phase_id=inner.spec.role_id,
            delivery_allowed=self._delivery_allowed,
        )

    async def close(self) -> None:
        await self._inner.close()




async def run_perception_branch_arms(
    invoke_branch: Callable[[int], Awaitable[Mapping[str, Any]]],
    *,
    group,
    branch_record: Callable[[int, Mapping[str, Any]], Mapping[str, object]],
    phase_id: str,
    delivery_allowed: Callable[[str, str], bool] = _default_delivery_allowed,
) -> dict[str, object]:
    """Run K Perception branches and deliver ONLY branch A's own answer.

    Same-flight instrument, PHASE 2 (merge set C, design docs/superpowers/
    specs/2026-09-28-same-flight-instrument-phase2-perception-variants-
    design.md section 3, "Fork point"). Structurally :func:`run_supply_
    variant_arms`'s twin, over the Perception phase instead of the Solver's,
    with the one difference that IS the whole point of the mechanism: a
    NON-delivering branch's completion registers NO node state at all --
    unlike a non-delivering Solver arm, which at least shares the row's own
    QueryState -- because it is sealed as a column (its own note), never read
    by Reviewer, Planner or the delivered Solver. Only branch A's (last,
    override-free) completion becomes this visit's delivered ``actor_output``,
    exactly as the delivering arm's does in the supply-variant form; T
    (``replicate_of: "A"``) is simply another branch in the batch whose
    request the CALLER composes byte-identical to A's (this function does not
    itself enforce wire identity -- that is the caller's messages-composition
    responsibility, checked by :func:`rails.native_episode_receipt.
    validate_perception_branch_receipt`'s AT-P2 wire-identity rule).

    ``group`` is the validated ``rails.supply_variants.PerceptionBranchGroup``
    the composed config carries at ``native_episode.roles.perception.
    branches``; it is passed through rather than re-derived, so recorded
    custody can never drift from the configuration the request-composition
    path actually used. ``branch_record`` is the caller's own per-branch
    receipt row (``rails.supply_variants.perception_branch_record``) -- it is
    the caller, not this module, that knows which value ids, knobs and note
    hash each branch's request and response actually carried, because it is
    the caller's binding provider that composed them.

    The returned mapping is the SAME per-role result shape
    :func:`run_supply_variant_arms` returns, with one renamed custody field:
    ``perception_branches`` (:func:`rails.supply_variants.
    perception_branch_receipt`) in place of ``supply_variants``.
    ``actor_output`` is branch A's own text, and ``execution_receipt.
    contacts`` is every branch's contacts concatenated in branch order, so
    ``final_contact`` is A's own final contact and the delivered text is
    bound to it -- I7 holds with no new exception, exactly as it does for the
    delivering Solver arm.
    """

    from ...rails.supply_variants import (  # noqa: PLC0415 (light top-level imports)
        PerceptionBranchError,
        perception_branch_receipt,
    )

    if not callable(invoke_branch):
        raise SupplyVariantNodeError("invoke_branch must be callable")
    if not callable(branch_record):
        raise SupplyVariantNodeError("branch_record must be callable")
    if not callable(delivery_allowed):
        raise SupplyVariantNodeError("delivery_allowed must be callable")
    branches = getattr(group, "branches", None)
    if not isinstance(branches, tuple) or not branches:
        raise SupplyVariantNodeError(
            "a perception-branch visit requires a parsed PerceptionBranchGroup"
        )

    role_id: str | None = None
    contacts: list[dict[str, str]] = []
    records: list[Mapping[str, object]] = []
    delivered: Mapping[str, Any] | None = None

    for branch_index, branch in enumerate(branches):
        result = await invoke_branch(branch_index)
        if (
            not isinstance(result, Mapping)
            or result.get("result_type") != "answer"
            or not isinstance(result.get("actor_output"), str)
            or not result.get("actor_output")
            or not isinstance(result.get("role_id"), str)
            or not result.get("role_id")
        ):
            raise SupplyVariantNodeError(
                f"perception branch {branch.branch_id!r} returned no answer"
            )
        if role_id is None:
            role_id = result["role_id"]
        elif result["role_id"] != role_id:
            raise SupplyVariantNodeError(
                "every perception branch must share one role_id"
            )
        receipt = result.get("execution_receipt")
        raw_contacts = receipt.get("contacts") if isinstance(receipt, Mapping) else None
        if (
            not isinstance(receipt, Mapping)
            or not isinstance(raw_contacts, Sequence)
            or isinstance(raw_contacts, (str, bytes))
            or not raw_contacts
            or not all(isinstance(contact, Mapping) for contact in raw_contacts)
        ):
            raise SupplyVariantNodeError(
                f"perception branch {branch.branch_id!r} has no execution receipt"
            )
        contacts.extend(dict(contact) for contact in raw_contacts)
        try:
            row = branch_record(branch_index, result)
        except PerceptionBranchError as error:
            raise SupplyVariantNodeError(
                f"perception branch {branch.branch_id!r} record is invalid: {error}"
            ) from error
        if not isinstance(row, Mapping) or row.get("branch_id") != branch.branch_id:
            raise SupplyVariantNodeError(
                f"perception branch {branch.branch_id!r} record names another branch"
            )
        records.append(dict(row))
        if branch.deliver:
            delivered = result

    if delivered is None or delivered is not result:
        # ``parse_perception_branches`` already refuses a group whose
        # delivering branch (A) is not the last one; this is the runtime half
        # of that same statement, and it is what makes ``final_contact``
        # below A's own final contact rather than some earlier branch's.
        raise SupplyVariantNodeError(
            "the delivering perception branch (A) must be the last branch invoked"
        )
    actor_output = delivered["actor_output"]
    return {
        "role_id": role_id,
        "actor_output": actor_output,
        "result_type": "answer",
        "delivery_eligible": bool(delivery_allowed(role_id, actor_output)),
        "execution_receipt": {
            "contacts": contacts,
            "final_contact": contacts[-1],
        },
        "perception_branches": perception_branch_receipt(
            group=group, phase_id=phase_id, records=records,
        ),
    }


class PerceptionBranchRoleNode(WorkflowComponent):
    """The "perception" position of a live native episode graph, branched
    (same-flight instrument phase 2, merge set C).

    Wraps ONE real Perception ``NativeRoleNode`` (``inner``) built exactly as
    an unbranched Perception node always has -- same spec, same metered
    request path, same ``contact_context_provider`` -- and, on ``invoke()``
    (the same ``{"query": ...} -> role-result`` contract
    ``reproduction.ojw.native_episode._add_role`` wires into the graph),
    drives :func:`run_perception_branch_arms` over ``group.branch_count``
    sequential ``inner.invoke_direct(query)`` calls instead of a single one.

    Placed by ``rails.runner._invoke_native_role_episode`` in place of a
    plain ``NativeRoleNode`` whenever the Perception role declares
    ``perception_branches``; never constructed otherwise, so that path is
    untouched by this class's existence. Unlike :class:`SupplyVariantRoleNode`
    there is no visit-index bookkeeping and no "first visit only" branch:
    Perception has exactly one visit per row (``max_iterations`` 1, no
    refresh, design section 3 "Branch visits"), so every invocation of this
    node fans out to every declared branch. ``spec`` delegates to
    ``inner.spec`` and ``close()`` to ``inner.close()``, exactly as
    :class:`SupplyVariantRoleNode` does.
    """

    def __init__(
        self,
        *,
        inner: NativeRoleNode,
        group,
        branch_record: Callable[[int, Mapping[str, Any]], Mapping[str, object]],
        delivery_allowed: Callable[[str, str], bool] = _default_delivery_allowed,
    ) -> None:
        super().__init__()
        if not isinstance(inner, NativeRoleNode) or inner.spec.role_kind != "perception":
            raise SupplyVariantNodeError(
                "a perception-branch visit requires an inner Perception NativeRoleNode"
            )
        if not callable(branch_record):
            raise SupplyVariantNodeError("branch_record must be callable")
        if not callable(delivery_allowed):
            raise SupplyVariantNodeError("delivery_allowed must be callable")
        self._inner = inner
        self._group = group
        self._branch_record = branch_record
        self._delivery_allowed = delivery_allowed

    @property
    def spec(self) -> NativeRoleNodeSpec:
        return self._inner.spec

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        query = inputs.get("query")
        if not isinstance(query, str) or not query:
            raise SupplyVariantNodeError("native role query must be non-empty text")
        inner = self._inner

        async def invoke_branch(_branch_index: int) -> dict[str, object]:
            return await inner.invoke_direct(query)

        return await run_perception_branch_arms(
            invoke_branch,
            group=self._group,
            branch_record=self._branch_record,
            phase_id=inner.spec.role_id,
            delivery_allowed=self._delivery_allowed,
        )

    async def close(self) -> None:
        await self._inner.close()


__all__ = [
    "PerceptionBranchRoleNode",
    "SupplyVariantNodeError",
    "SupplyVariantRoleNode",
    "run_perception_branch_arms",
    "run_supply_variant_arms",
]
