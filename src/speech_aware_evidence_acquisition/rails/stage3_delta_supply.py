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

from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence

from .errors import RailsError

STAGE3_DELTA_CONTEXT_PROVIDER_ID = "stage3-delta-candidate-bound-v1"
#: S3-4s (owner decision 106, 2026-09-23): the Perception node has no
#: candidate state of its own -- it is the node that PRODUCES the candidates
#: -- so its deltas cannot be candidate-bound. They are supplied
#: UNCONDITIONALLY: the same ``prior_score``-ranked, capped list on every row
#: of the split. A separate provider id, not a mode flag on the one above,
#: because the two selections answer different questions and a config must
#: say which it declared.
STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID = "stage3-delta-unconditional-v1"
#: The named knowledge store role this provider is scoped to (S3-6 root
#: wiring: rails.knowledge_stores.build_knowledge_store_supply refuses
#: this provider id on any other store_role).
STAGE3_DELTA_STORE_ROLE = "stage3-deltas"
DEFAULT_STAGE3_DELTA_CAP = 8
#: S3-4s: the registered per-node caps. Solver 8 (v1's cap, unchanged),
#: Reviewer 4, Planner 4, Perception 4. A config still states its own ``cap``
#: explicitly; this mapping is the documented default and what the tests and
#: the readiness packages quote.
DEFAULT_STAGE3_DELTA_NODE_CAPS = {
    "perception": 4,
    "solver": DEFAULT_STAGE3_DELTA_CAP,
    "reviewer": 4,
    "planner": 4,
}
#: The nodes a delta row may target, spelled as PHASE names (the key a
#: ``context_supply`` route uses). Restated from
#: ``rails.stage3_advantage.LEGAL_DELTA_NODES``; this module keeps no import
#: of that one, exactly as ``rails.native_episode_receipt`` restates the
#: episode's own constants rather than importing the runtime.
STAGE3_DELTA_NODES = ("perception", "solver", "reviewer", "planner")
#: ITERATION 3, the coverage-gated application policy (the general-scenario
#: diagnostic, ``docs/results/2026-09-24-slurp-general-scenario-diagnostic.md``).
#: On TRAIN Fold A the delta store LOSES on the strata it has no reach into,
#: and the derangement twin loses as much -- so that loss is a FORM cost of
#: CARRYING a supply, not the content of any delta. The answer is therefore not
#: a better delta but a narrower APPLICATION: a row-level gate that declines to
#: supply a node at all where the store should not apply.
#:
#: The one registered policy id. A gate names it explicitly, exactly as a route
#: names its provider, so a config can never mean "some gate" -- and it
#: resolves in ``core.base.STAGE3_SUPPLY_GATE_POLICIES`` like every other
#: component id a config declares.
STAGE3_DELTA_SCENARIO_GATE_POLICY_ID = "majority-candidate-scenario-not-in-v1"
#: The OPTIONAL ``context_supply.<node>`` key that carries one.
STAGE3_DELTA_SCENARIO_GATE_KEY = "scenario_gate"
#: The ``reason`` a CLOSED gate receipts on the route's own skip audit
#: (``rails.knowledge_stores``'s ``delta_supply`` map). A short label, not a
#: sentence, because the consumption read counts it
#: (``scripts/analysis/stage3_delta_consumption_read.py``'s ``gated_rows``).
STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON = "scenario-gate-closed"


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
    # S3-4s: the NODE this delta is addressed to, read from a v2 row's
    # ``task_target`` (``NODE:DELTA-KIND:TARGET``). Declared LAST and
    # defaulted to ``None`` so every construction written before S3-4s --
    # and every v1 row, whose ``task_target`` is ``DELTA-KIND:TARGET`` and
    # names no node -- composes exactly what it did, and so a selection that
    # asks for no node filter behaves byte-identically to its pre-S3-4s self.
    node_target: str | None = None

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
        if self.node_target is not None and self.node_target not in STAGE3_DELTA_NODES:
            raise Stage3DeltaSupplyError(
                f"DeltaCandidate.node_target must be one of {STAGE3_DELTA_NODES} or None"
            )
        return self


def node_target_of_task_target(task_target: object) -> str | None:
    """The NODE a store value is addressed to, read from its ``task_target``.

    S3-4s writes ``NODE:DELTA-KIND:TARGET``; a v1 row writes
    ``DELTA-KIND:TARGET`` and names no node. The node is therefore exactly
    the first colon-separated field WHEN that field is one of
    :data:`STAGE3_DELTA_NODES`, and ``None`` otherwise -- which is what makes
    a v1 store invisible to a node-filtered route instead of mis-routed into
    one. Never raises: a missing or malformed ``task_target`` reads ``None``.
    """

    if not isinstance(task_target, str) or not task_target:
        return None
    head = task_target.split(":", 1)[0]
    return head if head in STAGE3_DELTA_NODES else None


def _node_filtered(
    deltas: Sequence[DeltaCandidate], node_target: str | None
) -> list[DeltaCandidate]:
    if node_target is None:
        return list(deltas)
    if node_target not in STAGE3_DELTA_NODES:
        raise Stage3DeltaSupplyError(
            f"node_target must be one of {STAGE3_DELTA_NODES} or None"
        )
    return [delta for delta in deltas if delta.node_target == node_target]


def _ranked_ids(deltas: Sequence[DeltaCandidate], cap: int) -> tuple[str, ...]:
    ordered = sorted(deltas, key=lambda delta: (-delta.prior_score, delta.value_id))
    return tuple(delta.value_id for delta in ordered[:cap])


def select_stage3_delta_values(
    candidate_facet_ids: Sequence[str],
    deltas: Sequence[DeltaCandidate],
    *,
    cap: int = DEFAULT_STAGE3_DELTA_CAP,
    node_target: str | None = None,
) -> tuple[str, ...]:
    """Every delta whose ``associated_facet_ids`` intersects
    ``candidate_facet_ids``, capped at ``cap``, ordered by ``prior_score``
    descending with ``value_id`` ascending as the deterministic tie-break.

    S3-4s adds ``node_target``: when given, the pool is first restricted to
    the deltas addressed to that node (``DeltaCandidate.node_target``), so
    one store serves the Solver, the Reviewer and the Planner from three
    disjoint slices instead of three copies of the same slice. ``None`` --
    the default, and every caller written before S3-4s -- applies no node
    filter and returns byte-identically to its pre-S3-4s self.

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
        delta for delta in _node_filtered(deltas, node_target)
        if candidate_set.intersection(delta.associated_facet_ids)
    ]
    return _ranked_ids(matching, cap)


def select_unconditional_stage3_delta_values(
    deltas: Sequence[DeltaCandidate],
    *,
    cap: int = 4,
    node_target: str = "perception",
) -> tuple[str, ...]:
    """The UNCONDITIONAL route (S3-4s): the top ``cap`` deltas addressed to
    ``node_target``, ranked by ``prior_score`` descending with ``value_id``
    ascending as the deterministic tie-break, with NO row-dependent term.

    This is the Perception node's route. Perception is the node that
    PRODUCES the candidate list, so at the moment it is contacted the row
    has no candidate state to bind against; binding a Perception delta to
    the candidates the same node has not yet proposed would be circular.
    The selection is therefore a pure function of the store, identical on
    every row of the split -- which is also what makes it seedable as a
    first-phase bootstrap (``rails.knowledge_stores``'s
    ``bootstrap_first_phase``), where no preceding ``advance`` exists to
    carry a per-row decision.

    Pure and total: an empty pool returns ``()``.
    """

    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
        raise Stage3DeltaSupplyError("cap must be a positive integer")
    if node_target not in STAGE3_DELTA_NODES:
        raise Stage3DeltaSupplyError(
            f"node_target must be one of {STAGE3_DELTA_NODES}"
        )
    for delta in deltas:
        delta.validate()
    return _ranked_ids(_node_filtered(deltas, node_target), cap)


def stage3_delta_selection_receipt(
    *,
    sample_id: str,
    candidate_facet_ids: Sequence[str],
    deltas: Sequence[DeltaCandidate],
    selected_value_ids: Sequence[str],
    cap: int,
    node_target: str | None = None,
) -> Mapping[str, object]:
    """Identities and counts only -- no statement content, matching every
    other supply receipt in this study.

    ``node_target`` is declared LAST and defaulted, so a pre-S3-4s caller
    gets the identical receipt it always did; a node-filtered route names
    the node it filtered on and how large that node's slice was.
    """

    receipt: dict[str, object] = {
        "schema": "saea-stage3-delta-selection-receipt-v1",
        "sample_id": sample_id,
        "candidate_facet_count": len(set(candidate_facet_ids)),
        "delta_pool_size": len(deltas),
        "cap": cap,
        "selected_count": len(selected_value_ids),
        "selected_value_ids": list(selected_value_ids),
    }
    if node_target is not None:
        receipt["node_target"] = node_target
        receipt["node_pool_size"] = len(_node_filtered(deltas, node_target))
    return receipt


# ---------------------------------------------------------------------------
# Iteration 3: the row-level scenario gate (runtime state only)
# ---------------------------------------------------------------------------


def scenario_of_intent(intent_id: object) -> str:
    """The SLURP SCENARIO of one intent id: the part before the first ``_``.

    ``general_quirky -> general``, ``qa_factoid -> qa``,
    ``iot_hue_lightoff -> iot``. That is the catalog's own composition rule
    (``data.slurp``'s ontology pairs a scenario with its actions, and an
    intent id is ``<scenario>_<action>``), and this is the ONE implementation
    of it on the supply path -- the analysis scripts that already spell
    ``intent_id.split("_", 1)[0]`` read sealed outputs, never a live route.

    Total on a well-formed id and fail-closed on anything else: nothing is
    silently coerced into a scenario name.
    """

    if not isinstance(intent_id, str) or not intent_id:
        raise Stage3DeltaSupplyError("a SLURP intent id must be a non-empty string")
    return intent_id.split("_", 1)[0]


def catalog_scenarios(legal_intent_ids: Sequence[str]) -> tuple[str, ...]:
    """The scenario CATALOG, derived from the task adapter's authoritative
    legal candidate inventory rather than hard-coded here.

    A gate may only name a scenario this carrier actually has, and the one
    place that is known is the inventory the route already binds against
    (``rails.knowledge_stores``'s ``legal_candidate_ids``). Deriving it means
    a misspelling (``generl``) and a CATEGORY error (``qa_factoid``, which is
    an intent, not a scenario) are both refused by the same rule, at config
    load, before a contact is spent.
    """

    ids = tuple(legal_intent_ids or ())
    if not ids:
        raise Stage3DeltaSupplyError(
            "the scenario catalog requires the authoritative legal candidate inventory"
        )
    return tuple(sorted({scenario_of_intent(item) for item in ids}))


def majority_candidate_scenario(candidate_intent_ids: Sequence[str]) -> str | None:
    """The MAJORITY scenario of one row's projected Perception candidates, or
    ``None`` when the row proposed nothing.

    "Majority" is most-frequent, not strictly more than half: a candidate list
    ``qa_factoid, qa_definition, general_quirky`` has the majority scenario
    ``qa``. Ties are broken by the FIRST-LISTED candidate -- implemented as "of
    the scenarios tied at the maximum count, the one whose first occurrence in
    the candidate list is earliest", which IS the first-listed candidate's
    scenario whenever that scenario is one of the tied maxima (the case the
    rule describes), and is still deterministic when it is not (e.g.
    ``a_x, b_y, b_z, c_p, c_q``, where ``a`` cannot win a tie it is not in).
    """

    ordered = [scenario_of_intent(item) for item in candidate_intent_ids]
    if not ordered:
        return None
    counts = Counter(ordered)
    best = max(counts.values())
    for scenario in ordered:
        if counts[scenario] == best:
            return scenario
    raise AssertionError("unreachable: a counted scenario is always in the list")


@dataclass(frozen=True)
class ScenarioGateDecision:
    """One row's gate decision at one node. Labels and counts only -- never an
    utterance, a transcript, a gold label or a statement."""

    policy_id: str
    majority_scenario: str | None
    candidate_count: int
    closed: bool

    def as_json(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "majority_scenario": self.majority_scenario,
            "candidate_count": self.candidate_count,
            "closed": self.closed,
        }


@dataclass(frozen=True)
class ScenarioGate:
    """A parsed ``scenario_gate`` spec: WHICH policy, and WHICH scenarios."""

    policy_id: str
    scenarios: tuple[str, ...]

    def validate(self) -> "ScenarioGate":
        if self.policy_id != STAGE3_DELTA_SCENARIO_GATE_POLICY_ID:
            raise Stage3DeltaSupplyError(
                f"unknown scenario_gate policy {self.policy_id!r}; the one registered "
                f"policy is {STAGE3_DELTA_SCENARIO_GATE_POLICY_ID!r}"
            )
        if (
            not isinstance(self.scenarios, tuple)
            or not self.scenarios
            or any(not isinstance(item, str) or not item for item in self.scenarios)
            or len(set(self.scenarios)) != len(self.scenarios)
        ):
            raise Stage3DeltaSupplyError(
                "scenario_gate.scenarios must be a non-empty list of distinct "
                "scenario names"
            )
        return self

    def decide(self, candidate_intent_ids: Sequence[str]) -> ScenarioGateDecision:
        """CLOSED exactly when the row proposed candidates AND their majority
        scenario is one this gate names. Pure: the only input is the row's own
        projected Perception candidate list."""

        ordered = tuple(candidate_intent_ids)
        majority = majority_candidate_scenario(ordered)
        return ScenarioGateDecision(
            policy_id=self.policy_id,
            majority_scenario=majority,
            candidate_count=len(ordered),
            closed=majority is not None and majority in self.scenarios,
        )

    def as_json(self) -> dict[str, object]:
        return {"policy": self.policy_id, "scenarios": list(self.scenarios)}


def parse_scenario_gate(raw: object, *, legal_intent_ids: Sequence[str]) -> ScenarioGate:
    """Parse and VALIDATE one ``scenario_gate`` spec, fail-closed.

    Refused: an unknown policy id, a missing or extra key, a non-list, an
    empty list, a repeated name, a non-string name, and any name that is not a
    scenario of :func:`catalog_scenarios` -- which is what refuses an intent id
    (``qa_factoid``) written where a scenario belongs.
    """

    if not isinstance(raw, Mapping) or set(raw) != {"policy", "scenarios"}:
        raise Stage3DeltaSupplyError(
            "scenario_gate requires exactly the keys 'policy' and 'scenarios'"
        )
    scenarios = raw["scenarios"]
    if isinstance(scenarios, (str, bytes)) or not isinstance(scenarios, (list, tuple)):
        raise Stage3DeltaSupplyError(
            "scenario_gate.scenarios must be a non-empty list of distinct "
            "scenario names"
        )
    gate = ScenarioGate(policy_id=raw["policy"], scenarios=tuple(scenarios)).validate()
    catalog = frozenset(catalog_scenarios(legal_intent_ids))
    unknown = sorted(set(gate.scenarios) - catalog)
    if unknown:
        raise Stage3DeltaSupplyError(
            f"scenario_gate.scenarios names non-catalog scenario(s) {unknown}; a "
            "scenario is the part of a SLURP intent id before the first underscore, "
            "so an intent id is not one"
        )
    return gate


__all__ = [
    "DEFAULT_STAGE3_DELTA_CAP",
    "DEFAULT_STAGE3_DELTA_NODE_CAPS",
    "STAGE3_DELTA_CONTEXT_PROVIDER_ID",
    "STAGE3_DELTA_NODES",
    "STAGE3_DELTA_SCENARIO_GATE_KEY",
    "STAGE3_DELTA_SCENARIO_GATE_POLICY_ID",
    "STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON",
    "STAGE3_DELTA_STORE_ROLE",
    "STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID",
    "DeltaCandidate",
    "ScenarioGate",
    "ScenarioGateDecision",
    "Stage3DeltaSupplyError",
    "catalog_scenarios",
    "majority_candidate_scenario",
    "node_target_of_task_target",
    "parse_scenario_gate",
    "scenario_of_intent",
    "select_stage3_delta_values",
    "select_unconditional_stage3_delta_values",
    "stage3_delta_selection_receipt",
]
