"""Stage-3 S3-6: the stage3-deltas store's candidate-bound, prior_score-
capped Solver-phase supply (`docs/superpowers/specs/2026-09-22-stage3-tfrl-
base-loop-engineering.md` section S3-6).

Selection rule (verbatim from the spec): "every delta of the store whose
``associated_facet_ids`` intersect the row's Perception candidate intents
..., capped at 8 per row by ``prior_score`` = the statement's disagreement
mass." :func:`select_stage3_delta_values` is exactly that rule, as a pure,
fully tested function over already-loaded delta rows -- no store I/O, no
model contact, no knowledge-store binding.

ROOT WIRING (S3-6w, 2026-09-22): ``rails.knowledge_stores.
build_knowledge_store_supply``'s ``context_supply`` dispatcher now
recognises a ``store_role: "stage3-deltas"`` store declaring
``{"provider": STAGE3_DELTA_CONTEXT_PROVIDER_ID, "candidate_state_phase",
"cap", "rank_by": "prior_score"}`` -- the SAME field the spec's own prose
names, and the same shape the delta-cell baseline fragments
(``configs/baseline/slurp-native-stage3-delta-cell-*-v1.json``) already
carried. The pre-existing ``context_supply`` shape (the source-scoped
provider, ``set(raw_spec) == {"provider"}``) is completely unchanged; the
router now branches on ``raw_spec["provider"]`` instead of hard-coding one
provider id. The router's own collision guard (rule 1, module comment in
``rails/knowledge_stores.py``) is narrowed the same way: a stage3-deltas
store's context_supply may now coexist with a DIFFERENT store's
candidate_supply on the same phase -- this program's anchor case,
``stage3-deltas`` ``context_supply.solver`` alongside ``slot-contracts``
``candidate_supply.solver`` -- while the source-scoped provider keeps
refusing that overlap exactly as before. See
``rails.knowledge_stores._stage3_delta_local_supply`` (the glue that reads
the row's Perception candidate intents, then routes them through
:class:`~.knowledge_provider.Stage3DeltaCandidateProvider`) and
``tests/unit/test_stage3_delta_supply_router.py``. What remains PENDING is
only the store's own release (S3-5) and a root admission decision to fly
it -- never the routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .errors import RailsError

STAGE3_DELTA_CONTEXT_PROVIDER_ID = "stage3-delta-candidate-bound-v1"
#: The named knowledge store role this provider is scoped to (S3-6 root
#: wiring: rails.knowledge_stores.build_knowledge_store_supply refuses
#: this provider id on any other store_role).
STAGE3_DELTA_STORE_ROLE = "stage3-deltas"
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
    "STAGE3_DELTA_STORE_ROLE",
    "DeltaCandidate",
    "Stage3DeltaSupplyError",
    "select_stage3_delta_values",
    "stage3_delta_selection_receipt",
]
