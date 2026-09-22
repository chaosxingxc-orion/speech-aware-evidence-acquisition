"""Stage-3 S3-6: the stage3-deltas store's candidate-bound, prior_score-
capped Solver-phase supply (`docs/superpowers/specs/2026-09-22-stage3-tfrl-
base-loop-engineering.md` section S3-6).

Selection rule (verbatim from the spec): "every delta of the store whose
``associated_facet_ids`` intersect the row's Perception candidate intents
..., capped at 8 per row by ``prior_score`` = the statement's disagreement
mass." :func:`select_stage3_delta_values` is exactly that rule, as a pure,
fully tested function over already-loaded delta rows -- no store I/O, no
model contact, no knowledge-store binding.

A DOCUMENTED SCOPE DECISION: the spec's own prose names ``context_supply``
as the field, but ``rails.knowledge_stores.build_knowledge_store_supply``
hard-codes ``context_supply`` to accept EXACTLY one provider today
(``rails.governed_context_supply.SOURCE_SCOPED_CONTEXT_PROVIDER_ID``, a
source-scoped mechanism with no candidate-binding and no cap at all --
``set(raw_spec) != {"provider"}`` refuses any other shape outright). The
mechanism that actually IS candidate-bound and capped in this codebase is
``candidate_supply`` (the slot-contracts store's own routing, which the
spec's prose also names: "the same candidate-bound routing the slot-
contracts store uses") -- but ``rails.candidate_semantic_supply.
load_candidate_semantic_supply_specs`` hard-codes ``candidate_supply`` to
exactly two store roles (``slot-contracts``, ``parameter-meaning``), and its
selection algorithm is per-candidate round-robin, not a flat top-N by
``prior_score``.

Extending either hard-coded dispatcher to a third, not-yet-released store
role is real surgery to shared code two other admitted stores route
through today (``rails/knowledge_stores.py``, ``rails/
candidate_semantic_supply.py``), and this package cannot integration-test
that surgery against a live flight (flying is out of scope here, and this
store's own release does not exist yet -- config pins below are all
``PENDING_``). Rather than land an unverified change to code a live
campaign depends on, this module delivers the SELECTION ALGORITHM itself,
fully tested on synthetic fixtures. A real, registered
``rails.knowledge_provider.KnowledgeProvider`` (``Stage3DeltaCandidateProvider``,
registered under :data:`STAGE3_DELTA_CONTEXT_PROVIDER_ID` in
``core.base.KNOWLEDGE_PROVIDERS`` from ``rails/knowledge_provider.py``, the
canonical registration site) wraps this algorithm so a config fragment's
``"provider": "stage3-delta-candidate-bound-v1"`` resolves honestly; what
remains a named root follow-up is ONLY the dispatcher recognizing that
provider id inside ``build_knowledge_store_supply``'s ``context_supply``
branch (or a new ``candidate_supply`` role branch) -- see the S3-6 readiness
package README.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .errors import RailsError

STAGE3_DELTA_CONTEXT_PROVIDER_ID = "stage3-delta-candidate-bound-v1"
DEFAULT_STAGE3_DELTA_CAP = 8


class Stage3DeltaSupplyError(RailsError):
    """A delta candidate or a selection request is malformed."""


@dataclass(frozen=True)
class DeltaCandidate:
    """One value of the stage3-deltas store, as the selector needs it --
    never the statement text itself (the selector's job is routing, not
    rendering; rendering the CONTENT of a selected value into a Solver
    prompt is the store's ordinary supply-packet path, unchanged by this
    module)."""

    value_id: str
    associated_facet_ids: tuple[str, ...]
    prior_score: float

    def validate(self) -> "DeltaCandidate":
        if not isinstance(self.value_id, str) or not self.value_id:
            raise Stage3DeltaSupplyError("DeltaCandidate.value_id must be a non-empty string")
        if (
            not isinstance(self.associated_facet_ids, tuple)
            or not self.associated_facet_ids
            or any(not isinstance(item, str) or not item for item in self.associated_facet_ids)
        ):
            raise Stage3DeltaSupplyError(
                "DeltaCandidate.associated_facet_ids must be a non-empty tuple of strings"
            )
        if isinstance(self.prior_score, bool) or not isinstance(self.prior_score, (int, float)):
            raise Stage3DeltaSupplyError("DeltaCandidate.prior_score must be a number")
        return self


def select_stage3_delta_values(
    candidate_facet_ids: Sequence[str],
    deltas: Sequence[DeltaCandidate],
    *,
    cap: int = DEFAULT_STAGE3_DELTA_CAP,
) -> tuple[str, ...]:
    """Every delta whose ``associated_facet_ids`` intersects
    ``candidate_facet_ids``, capped at ``cap``, ordered by ``prior_score``
    descending with ``value_id`` ascending as the deterministic tie-break.

    Pure and total: an empty ``candidate_facet_ids`` or an empty ``deltas``
    both return ``()``, never raise (a row with no matching delta is simply
    supplied nothing, exactly like every other candidate-bound route in
    this study when a row's candidates map to no store value).
    """

    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
        raise Stage3DeltaSupplyError("cap must be a positive integer")
    for delta in deltas:
        delta.validate()
    candidate_set = frozenset(candidate_facet_ids)
    matching = [
        delta for delta in deltas if candidate_set.intersection(delta.associated_facet_ids)
    ]
    ordered = sorted(matching, key=lambda delta: (-delta.prior_score, delta.value_id))
    return tuple(delta.value_id for delta in ordered[:cap])


def stage3_delta_selection_receipt(
    *,
    sample_id: str,
    candidate_facet_ids: Sequence[str],
    deltas: Sequence[DeltaCandidate],
    selected_value_ids: Sequence[str],
    cap: int,
) -> Mapping[str, object]:
    """Identities and counts only -- no statement content, matching every
    other supply receipt in this study."""

    return {
        "schema": "saea-stage3-delta-selection-receipt-v1",
        "sample_id": sample_id,
        "candidate_facet_count": len(set(candidate_facet_ids)),
        "delta_pool_size": len(deltas),
        "cap": cap,
        "selected_count": len(selected_value_ids),
        "selected_value_ids": list(selected_value_ids),
    }


__all__ = [
    "DEFAULT_STAGE3_DELTA_CAP",
    "STAGE3_DELTA_CONTEXT_PROVIDER_ID",
    "DeltaCandidate",
    "Stage3DeltaSupplyError",
    "select_stage3_delta_values",
    "stage3_delta_selection_receipt",
]
