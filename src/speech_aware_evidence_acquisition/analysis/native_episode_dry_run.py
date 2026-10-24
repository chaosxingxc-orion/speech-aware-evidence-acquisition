"""Contact-free dry run of one plan-based native role episode.

Why this module exists
----------------------
``core.flight.cli check`` proves that a cell's fragments compose, that its
pinned prepared artifacts still have the identity they were minted with, and
that its readiness requirements hold. It does NOT walk the episode: no node
ever asks for its material, no node boundary ever resolves its knowledge
supply, and therefore nothing ever reads a sealed role state. Cell CELL-1's
generation smoke passed ``check`` and then died at the openJiuwen vertex
``solver_0_input``, after four charged Perception contacts, because the
stage3-deltas candidate-bound route read the sealed Perception state as the
canonical four-key document while a native episode seals the model's own
COMPACT structured-output bytes (``{"candidates": [...]}``). Every unit test
of that route fed it a canonical document, so the whole ladder was green.

What this dry run is
--------------------
The REAL cell, walked node by node, with no model, no tool, no network, no
GPU, no gate, no transport, no client, no attempt and no serving session --
exactly the "model-free stage probe" discipline ``rails.core_client.
payload_binding_stage`` and ``scripts/checks/derived_media_confinement_check``
already use: the code under proof is the production function, and only the
lifecycle around it is absent.

REAL here: the four composed fragments, the carrier adapter and its split, the
phase program, the native episode config, every phase's rendered instruction
and resolved response format, the knowledge-store binding over the released
stores, the supply router (``rails.knowledge_stores.build_knowledge_store_
supply``) with every explicit, candidate-bound and unconditional route it
declares, the first-phase seed (the pinned ``prepared_phase_supply`` artifact
when the cell has one), ``rails.controllers.seal_phase_response_state`` and
``rails.controllers.advance_phase_response_state``.

SYNTHETIC here, and only here: the role responses. The caller supplies one per
role -- canned, deterministic and schema-valid -- exactly as a fake frozen
core would answer. Nothing else is faked, so a refusal raised by this walk is
a refusal the flight would raise.

What it walks
-------------
The node order a ``native-role-episode`` program takes on one row when the
Planner accepts on its first visit::

    perception -> solver -> reviewer -> planner -> delivery

At each boundary it performs, in the runner's own order
(``rails.runner._invoke_native_role_episode``: ``role_input`` calls
``settle(next_phase=...)`` and then ``material_for_phase``):

1. render the node's material from the composed fragments;
2. seal the node's response with the production sealer, under the same
   ``phase:<name>`` / ``<contact>:<phase>:<sample>`` identity a flight mints;
3. resolve the NEXT node's knowledge supply from a context that already
   carries that sealed state -- the call that failed on 2026-09-23;
4. advance the ``QueryState`` through the production advance, so the next
   node's context is the one a flight would hand it.

The receipt names, per node, the supplied value ids (so "the per-node deltas
were supplied" is a count a caller can assert on), the instruction digest, the
sealed state id and the delivered answer.

It also names, per node, every row-level SCENARIO-GATE decision the walked
routes recorded -- open and closed alike, as labels and counts
(``rails.stage3_delta_supply``'s iteration-3 application policy). A gate that
closes takes no supply step at all, which is indistinguishable in the supplied
counts from a node slice that simply matched nothing; the decision receipt is
what tells the two apart, so "the gate closed on this row and was open on that
one" is a fact a caller can assert on before a contact is ever spent.

Reuse
-----
``dry_run_native_episode(runtime, answers=...)`` takes any ``FlightRuntime``
built by ``core.flight.factory.build_flight_runtime``, so every future
plan-based cell can be dry-run before it is queued, from a test or from a
script, with no flight budget at risk.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Callable, Mapping, Sequence

DRY_RUN_SCHEMA = "saea-native-episode-dry-run-v1"

#: The contact-id namespace a dry run mints. Deliberately not a flight's
#: (``rails.execution_units.scoped_execution_contact_id``): a dry-run state id
#: must never be mistaken for a sealed flight state in a trace or a receipt.
CONTACT_NAMESPACE = "dry-run"

#: Run/attempt identity a dry run mints for the ``contracts.ExecutionPlan`` it
#: needs in order to read a pinned prepared artifact. It authorizes nothing:
#: no gate is ever asked, no attempt is ever opened, and the prefix keeps the
#: identity out of every registered run id's namespace -- the same discipline
#: ``core.flight.runtime.WIRE_CHECK_RUN_ID_PREFIX`` uses for its own.
DRY_RUN_RUN_ID_PREFIX = "SAEA-DRY-RUN-"
DRY_RUN_ATTEMPT_ID = "attempt-dry-run"


class NativeEpisodeDryRunError(RuntimeError):
    """The dry run cannot proceed, or the walked episode refused."""


@dataclass(frozen=True)
class DryRunNode:
    """One walked node: what it was given and what it produced."""

    phase: str
    visit: int
    contact_id: str
    instruction_sha256: str
    instruction_chars: int
    response_format_id: str | None
    supplied_value_ids: tuple[str, ...]
    supplied_facet_ids: tuple[str, ...]
    state_id: str
    state_kind: str
    state_content_sha256: str
    #: Item E42: every declared supply-variant arm of THIS visit, in declared
    #: order, when the episode fans this node out. Declared LAST and defaulted,
    #: so a cell that declares no arm group produces exactly the receipt it
    #: always did.
    supply_variant_arms: tuple[DryRunArm, ...] = ()

    def as_json(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "visit": self.visit,
            "contact_id": self.contact_id,
            "instruction_sha256": self.instruction_sha256,
            "instruction_chars": self.instruction_chars,
            "response_format_id": self.response_format_id,
            "supplied_value_ids": list(self.supplied_value_ids),
            "supplied_facet_ids": list(self.supplied_facet_ids),
            "supplied_value_count": len(self.supplied_value_ids),
            "state_id": self.state_id,
            "state_kind": self.state_kind,
            "state_content_sha256": self.state_content_sha256,
            "supply_variant_arms": [arm.as_json() for arm in self.supply_variant_arms],
        }


@dataclass(frozen=True)
class DryRunArm(object):
    """Item E42: ONE supply-variant arm of one node visit, as walked.

    Labels, ids and counts only -- an arm id, the knob values it resolved and
    the value ids its request would carry. Never a supplied value's text, never
    an utterance and never a gold label.
    """

    arm_id: str
    arm_index: int
    deliver: bool
    resolved_knobs: tuple[Mapping[str, object], ...]
    supplied_value_ids: tuple[str, ...]
    max_supplied_items: int
    #: NX programme E1 (node-template arms): the arm's pinned template, or
    #: ``None``; and the digest and length of the instruction text this arm's
    #: request would carry (the delivering arm's and the twin's are the node's
    #: own locked instruction -- which is what the walk proves). Declared LAST
    #: and defaulted, so a supply-kind walk produces exactly the receipt it
    #: always did.
    instruction_template: Mapping[str, str] | None = None
    instruction_sha256: str | None = None
    instruction_chars: int | None = None
    #: NX-T R1 (thinking-policy arms): the arm's declared per-node override map, and the per-node wire fields its
    #: Perception and Solver requests would carry (``thinking_budget_tokens`` / ``chat_template_kwargs`` / ``max_tokens``),
    #: resolved from the composed fragment by ``core.reasoning_knobs.resolve_node_decoding``. ``None`` for every other kind.
    thinking_policy: Mapping[str, Mapping[str, object]] | None = None
    node_decoding: Mapping[str, Mapping[str, object]] | None = None
    #: NX-T R4 (node-decoding arms): the arm's declared sampling override ``{name: value}`` applied to its Solver contact, or
    #: ``None`` (every other kind, the delivering arm and the twin).
    decoding_override: Mapping[str, object] | None = None

    def as_json(self) -> dict[str, object]:
        row: dict[str, object] = {
            "arm_id": self.arm_id,
            "arm_index": self.arm_index,
            "deliver": self.deliver,
            "resolved_knobs": [dict(entry) for entry in self.resolved_knobs],
            "supplied_value_ids": list(self.supplied_value_ids),
            "supplied_item_count": len(self.supplied_value_ids),
            "max_supplied_items": self.max_supplied_items,
        }
        if self.instruction_sha256 is not None:
            row["instruction_template"] = (
                None if self.instruction_template is None
                else dict(self.instruction_template)
            )
            row["instruction_sha256"] = self.instruction_sha256
            row["instruction_chars"] = self.instruction_chars
        if self.node_decoding is not None:
            row["thinking_policy"] = None if self.thinking_policy is None else {
                kind: dict(entry) for kind, entry in self.thinking_policy.items()
            }
            row["node_decoding"] = {kind: dict(fields) for kind, fields in self.node_decoding.items()}
        if self.instruction_sha256 is not None and self.decoding_override is not None:
            row["decoding_override"] = dict(self.decoding_override)
        return row


@dataclass(frozen=True)
class DryRunGateDecision:
    """One row-level scenario-gate decision at one node.

    Labels and counts only -- a node name, a policy id, the majority scenario
    NAME, how many candidates it was read from and whether the gate closed.
    Never an utterance, a transcript, a gold label or a statement.
    """

    phase: str
    node: str
    policy_id: str
    majority_scenario: str | None
    candidate_count: int
    closed: bool

    def as_json(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "node": self.node,
            "policy_id": self.policy_id,
            "majority_scenario": self.majority_scenario,
            "candidate_count": self.candidate_count,
            "closed": self.closed,
        }


@dataclass(frozen=True)
class DryRunResult:
    """One row's walked episode."""

    schema: str
    run_id: str
    cell_sample_id: str
    policy: str
    program_id: str
    episode_id: str
    nodes: tuple[DryRunNode, ...]
    bootstrap_value_ids: tuple[str, ...]
    bootstrap_facet_ids: tuple[str, ...]
    delivered_phase: str
    delivered_sha256: str
    store_ids: tuple[str, ...]
    first_phase_seed_source: str
    #: Declared LAST and defaulted, so a cell whose routes declare no gate
    #: produces exactly the receipt it always did.
    scenario_gate_decisions: tuple[DryRunGateDecision, ...] = ()

    def gate_closed_by_node(self) -> dict[str, bool]:
        """``{node: closed}`` -- the one-line answer to "which nodes did the
        gate withhold on this row?"""

        return {item.node: item.closed for item in self.scenario_gate_decisions}

    def supplied_counts(self) -> dict[str, int]:
        """``{phase: supplied value count}`` over every walked visit.

        The first phase's count is its SEED (a first phase has no preceding
        advance to carry a per-row decision, so its supply is seeded into the
        initial ``QueryState``); every later phase's is what its own boundary
        resolved.
        """

        counts: dict[str, int] = {}
        for node in self.nodes:
            counts[node.phase] = counts.get(node.phase, 0) + len(
                node.supplied_value_ids
            )
        if self.nodes:
            first = self.nodes[0].phase
            counts[first] = counts.get(first, 0) + len(self.bootstrap_value_ids)
        return counts

    def supplied_counts_by_arm(self) -> dict[str, dict[str, int]]:
        """Item E42: ``{phase: {arm id: supplied value count}}`` over the walk.

        Empty for every cell that declares no arm group. For a cell that does,
        this IS the dry run's per-arm table: one column per declared
        construction, so "the default arm supplies exactly what the unvaried
        plan supplies, and each variant differs only in its own declared knob"
        is a number a reader can check rather than a claim.
        """

        table: dict[str, dict[str, int]] = {}
        for node in self.nodes:
            for arm in node.supply_variant_arms:
                table.setdefault(node.phase, {})[arm.arm_id] = len(
                    arm.supplied_value_ids
                )
        return table

    def delivered_arm_id(self) -> str | None:
        """Item E42: the arm the walked episode delivered, or ``None``."""

        for node in self.nodes:
            for arm in node.supply_variant_arms:
                if arm.deliver:
                    return arm.arm_id
        return None

    def as_json(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "run_id": self.run_id,
            "cell_sample_id": self.cell_sample_id,
            "policy": self.policy,
            "program_id": self.program_id,
            "episode_id": self.episode_id,
            "store_ids": list(self.store_ids),
            "bootstrap_value_ids": list(self.bootstrap_value_ids),
            "bootstrap_facet_ids": list(self.bootstrap_facet_ids),
            "nodes": [node.as_json() for node in self.nodes],
            "supplied_value_counts": self.supplied_counts(),
            "delivered_phase": self.delivered_phase,
            "delivered_sha256": self.delivered_sha256,
            "first_phase_seed_source": self.first_phase_seed_source,
            "scenario_gate_decisions": [
                item.as_json() for item in self.scenario_gate_decisions
            ],
            "scenario_gate_closed_by_node": self.gate_closed_by_node(),
            "supplied_value_counts_by_arm": self.supplied_counts_by_arm(),
            "delivered_arm_id": self.delivered_arm_id(),
        }


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _scenario_gate_decisions(phase_binding, sample_id: str):
    """Every scenario-gate decision the walked routes recorded for ONE row.

    Read off the supply router's own receipt
    (``rails.knowledge_stores``'s ``delta_scenario_gate`` map), never
    recomputed here: a dry run that decided the gate a second time would be
    proving its own arithmetic instead of the router's. Absent -- and therefore
    empty -- for a cell whose routes declare no gate.
    """

    router = phase_binding.get("supply_for_store")
    audits = (getattr(router, "receipt", None) or {}).get("delta_scenario_gate") or {}
    decisions = [
        DryRunGateDecision(
            phase=str(entry.get("phase")),
            node=str(entry.get("node")),
            policy_id=str(entry.get("policy_id")),
            majority_scenario=entry.get("majority_scenario"),
            candidate_count=int(entry.get("candidate_count") or 0),
            closed=bool(entry.get("closed")),
        )
        for entry in audits.values()
        if isinstance(entry, Mapping) and entry.get("sample_id") == sample_id
    ]
    return tuple(sorted(decisions, key=lambda item: (item.phase, item.node)))


def _require_binding(runtime) -> Mapping[str, object]:
    binding = getattr(runtime, "_dry_run_binding", None)
    if binding is None:
        raise NativeEpisodeDryRunError(
            "compose_dry_run(runtime) must run before the composition is read"
        )
    return binding


def legal_intent_ids(runtime) -> tuple[str, ...]:
    """The first phase's OWN legal inventory, read off the resolved response
    format rather than re-derived -- the same enum the wire carries.

    ``()`` for a program whose first phase declares no structured output,
    which is the honest answer: such a cell has no closed candidate
    vocabulary to answer from.
    """

    binding = _require_binding(runtime)
    formats = binding["response_format_by_phase"]
    first = binding["program"].phase_names()[0]
    document = formats.get(first)
    if not isinstance(document, Mapping):
        return ()
    try:
        enum = document["json_schema"]["schema"]["properties"]["candidates"]["items"][
            "properties"
        ]["intent_id"]["enum"]
    except (KeyError, TypeError):
        return ()
    return tuple(str(item) for item in enum)


def store_facet_ids(runtime, store_id: str) -> tuple[str, ...]:
    """Every facet id the named released store's values associate with.

    A dry run that wants a candidate-bound route to select something has to
    answer with candidates that store addresses; this is where a caller reads
    them, from the store the flight itself would read.
    """

    binding = _require_binding(runtime)
    stores = binding["knowledge_stores"]
    if stores is None:
        raise NativeEpisodeDryRunError("this cell binds no named knowledge stores")
    store = stores.store(store_id)
    seen: dict[str, None] = {}
    for value in store.snapshot.values:
        for facet_id in value.associated_facet_ids:
            seen.setdefault(str(facet_id), None)
    return tuple(seen)


#: The order a ``native-role-episode`` graph visits its roles on one row when
#: the Planner accepts on its first visit (``reproduction.ojw.native_episode``:
#: Perception forms the candidates, the Solver drafts, the Reviewer reviews the
#: draft, the Planner routes). It is NOT the program fragment's phase ORDER --
#: ``configs/policy/phase-native-candidates-review-revise-v1.json`` lists
#: perception, reviewer, planner, solver -- and walking the fragment's order
#: instead would put the Reviewer before the draft it reviews.
NATIVE_ROLE_GRAPH_ORDER = ("perception", "solver", "reviewer", "planner")


def episode_node_order(episode) -> tuple[str, ...]:
    """The phase ids of :data:`NATIVE_ROLE_GRAPH_ORDER`, for this episode."""

    by_kind = {role.role_kind: role.phase_id for role in episode.roles}
    missing = [kind for kind in NATIVE_ROLE_GRAPH_ORDER if kind not in by_kind]
    if missing:
        raise NativeEpisodeDryRunError(
            f"this episode declares no {missing} role(s); pass node_order "
            "explicitly to walk it"
        )
    return tuple(by_kind[kind] for kind in NATIVE_ROLE_GRAPH_ORDER)


def _first_phase_seed(runtime, program, phase_binding):
    """``(facet seed, value seed, source)`` for the program's first phase.

    A flight seeds it from the cell's pinned ``prepared_phase_supply``
    artifact, whose identity binds the composed config AND the sha256 of the
    rails/runtime modules that produced it
    (``FlightRuntime._phase_seed_inputs``). A dry run is USEFUL precisely on
    a working tree that carries a fix to one of those modules, and on such a
    tree the pin is stale by construction -- the re-pin refreshes it before
    the flight. So a stale pin falls back to the router's own
    ``bootstrap_first_phase``, which is the very function the artifact was
    minted from, and the source is REPORTED rather than silently swapped: a
    caller can assert on it, and a receipt says which seed the numbers came
    from.
    """

    from ..core.preparation import PreparationError

    pinned = runtime._composed.values.get("prepared_phase_supply") is not None
    try:
        facet_seed, value_seed = runtime._phase_supply_seeds(
            program,
            phase_binding,
            phase_binding.get("supply_specs") or {},
            runtime._plan,
        )
        return (
            facet_seed,
            value_seed,
            "prepared-artifact" if pinned else "router-bootstrap (no pinned artifact)",
        )
    except PreparationError as error:
        router = phase_binding.get("supply_for_store")
        bootstrap = getattr(router, "bootstrap_first_phase", None)
        if not callable(bootstrap):
            raise NativeEpisodeDryRunError(
                f"the pinned first-phase seed is unusable ({error}) and this "
                "cell's router publishes no bootstrap_first_phase to fall back on"
            ) from error
        facets, values = bootstrap(
            speech_packet_bindings=phase_binding["speech_packet_bindings"],
            split_identity_hash=runtime._plan.split_identity_hash,
            workers=1,
            lease_metadata_present=False,
        )
        first_phase = program.phase_names()[0]
        return (
            ({first_phase: facets} if facets else {}),
            ({first_phase: values} if values else {}),
            f"router-bootstrap (pinned artifact refused: {error})",
        )


def compose_dry_run(runtime, *, sample_limit: int = 1) -> Mapping[str, object]:
    """Compose the cell exactly as a flight's phase dispatch composes it.

    Reads only: the fragments, the lock, the split, the released stores, the
    pinned prepared artifacts and the promoted packet map. Opens no gate, no
    transport, no client and no attempt, and writes nothing anywhere.
    """

    from ..contracts import ExecutionPlan
    from ..core.flight.runtime import FlightRuntimeError, compute_protocol_hash
    from ..rails.controllers import default_phase_program
    from ..rails.native_episode_config import load_native_episode_config
    from ..rails.phase_material import (
        load_phase_material_specs,
        render_static_instruction,
        resolve_response_formats,
    )

    if (
        not isinstance(sample_limit, int)
        or isinstance(sample_limit, bool)
        or sample_limit < 1
    ):
        raise NativeEpisodeDryRunError("sample_limit must be a positive integer")

    values, carrier_lock_key, _split_id, identity = runtime._prepare()
    policy = values.get("policy")
    if not isinstance(policy, str) or not policy:
        raise NativeEpisodeDryRunError("baseline fragment declares no policy")
    program = default_phase_program(policy)
    episode = load_native_episode_config(values, program)
    if episode is None:
        raise NativeEpisodeDryRunError(
            f"policy {policy!r} declares no native_episode; this dry run walks "
            "native role episodes only"
        )
    if len(runtime._samples) > sample_limit:
        runtime._samples = tuple(runtime._samples[:sample_limit])

    # A plan is REQUIRED to read a pinned prepared artifact (its identity is
    # bound to the split identity hash), so this builds one -- under a
    # DRY-RUN run id that is not, and can never be confused with, a
    # registered run: it authorizes nothing, opens no attempt, and the only
    # field anything downstream reads from it is the split identity.
    declared = values.get("execution_plan")
    if not isinstance(declared, Mapping):
        raise NativeEpisodeDryRunError(
            "experiment fragment must declare an execution_plan"
        )
    plan = ExecutionPlan(
        run_id=f"{DRY_RUN_RUN_ID_PREFIX}{runtime.run_id}",
        execution_profile=declared["execution_profile"],
        carrier_lock_key=carrier_lock_key,
        split_role=declared["split_role"],
        split_identity_hash=identity,
        planned_model_calls=max(len(runtime._samples), 1),
        planned_gpu_hours=declared["planned_gpu_hours"],
        planned_speech_audio_seconds=declared["planned_speech_audio_seconds"],
        protocol_hash=compute_protocol_hash(
            runtime._composed.config_hash, str(values.get("arm")), identity
        ),
        attempt_id=DRY_RUN_ATTEMPT_ID,
    ).validate()
    runtime._plan = plan

    try:
        phase_binding = runtime._default_phase_program_binding(program, None)
    except FlightRuntimeError as error:
        raise NativeEpisodeDryRunError(str(error)) from error

    specs = load_phase_material_specs(values, program)
    formats = resolve_response_formats(specs, runtime._lock, runtime._data_root)
    static_text = {
        phase: render_static_instruction(
            spec, runtime._repo_root, runtime._lock, runtime._data_root
        )
        for phase, spec in specs.items()
    }
    stores = phase_binding.get("knowledge_stores")
    binding = {
        "values": values,
        "policy": policy,
        "program": program,
        "episode": episode,
        "phase_binding": phase_binding,
        "specs": specs,
        "response_format_by_phase": formats,
        "static_text_by_phase": static_text,
        "knowledge_stores": stores,
        "store_ids": tuple(stores.store_ids) if stores is not None else (),
        # Item E42: the SAME flight-owned per-arm resolver a live flight binds,
        # built here from the same composed values -- so a dry run walks the arm
        # routers the flight would use, not a stand-in. None for every cell that
        # declares no arm group.
        "supply_variant_for_phase": runtime._supply_variant_binding(episode, program),
        # NX programme E1: the SAME flight-owned per-arm material builders a
        # live flight binds (after the declared sha256 of every pinned
        # template was verified against its file's bytes). None for every cell
        # that declares no template group.
        "template_variant_materials": runtime._template_variant_materials(
            episode, program, phase_binding,
        ),
    }
    runtime._dry_run_binding = binding
    return binding


def dry_run_native_episode(
    runtime,
    *,
    answers: Mapping[str, str] | Callable[[str, int], str],
    sample_id: str | None = None,
    sample_limit: int = 1,
    node_order: Sequence[str] | None = None,
) -> DryRunResult:
    """Walk ONE row of this cell's native episode, contact-free.

    ``answers`` is the fake frozen core: either ``{role: text}`` or
    ``(role, visit) -> text``. Every text must satisfy that role's own
    registered response format, because this walk seals and reads it with the
    production sealer and the production consumers.

    ``node_order`` overrides the walked order (default: the program's own
    phase order).
    """

    from ..rails.controllers import (
        advance_phase_response_state,
        restrict_repeat_visit_supply,
        seal_phase_response_state,
    )
    from ..rails.knowledge import QueryState
    from ..rails.material import PhaseMaterial
    from ..rails.obs import default_obs_packet
    from ..rails.runner import AgentRuntimeContext, order_supply_by_retrieval_rank

    binding = getattr(runtime, "_dry_run_binding", None)
    if binding is None:
        binding = compose_dry_run(runtime, sample_limit=sample_limit)
    program = binding["program"]
    phase_binding = binding["phase_binding"]
    material_for_phase = phase_binding["material_for_phase"]
    supply_for_phase = phase_binding.get("supply_for_phase")
    # Item E42: the arm group this cell declares, and the resolver that answers
    # one arm's own supply. Both None for every cell written before E42, which
    # leaves the walk below byte-identical to its pre-E42 self.
    supply_variant_group = binding["episode"].supply_variant_group
    supply_variant_phase = binding["episode"].supply_variant_phase_id
    supply_variant_resolver = binding.get("supply_variant_for_phase")
    # NX programme E1: a node-template group varies the instruction, never the
    # supply, so the walk resolves no per-arm supply for it; the arms are walked
    # at the node itself, against the node's own material inputs.
    template_group = (
        supply_variant_group
        if supply_variant_group is not None and supply_variant_group.unvaried_evidence
        else None
    )
    template_materials = binding.get("template_variant_materials") or {}
    # NX programme E1, Perception node: the template arms may sit at the
    # Perception visit instead (the branch group's branches are the arms). The
    # walk covers each arm's Perception instruction; the level-2 Solver columns
    # are a runner statement proven by the live proofs, not a dry-run one.
    template_entries = None
    template_phase = None
    if template_group is not None:
        template_entries = [
            (arm.arm_id, arm.deliver, arm.max_supplied_items, arm.instruction_template)
            for arm in template_group.arms
        ]
        template_phase = supply_variant_phase
    else:
        perception_group = binding["episode"].perception_branch_group
        if perception_group is not None and perception_group.renders_unvaried_evidence:
            template_entries = [
                (branch.branch_id, branch.deliver, branch.max_supplied_items,
                 branch.instruction_template)
                for branch in perception_group.branches
            ]
            template_phase = binding["episode"].perception_branch_phase_id
    # NX-T R1: a thinking-policy group's arms render the node's locked instruction (no template) and differ in the per-node
    # thinking decoding of their own contacts; the walk reports each arm's resolved per-node wire fields.
    thinking_policy_by_arm: dict[str, Mapping[str, Mapping[str, object]] | None] = {}
    thinking_base: dict[str, object] | None = None
    episode_group = binding["episode"].perception_branch_group
    # Decision 338: a SAMPLING group's branches carry no thinking policy either (``thinking_policy`` is None), so its arms resolve to the node's own role-level
    # decoding -- the lock's thinking fields -- and the walk reports them like a thinking group's.
    if episode_group is not None and (episode_group.is_thinking or episode_group.is_sampling):
        from ..core.reasoning_knobs import fold_into_decoding

        thinking_policy_by_arm = {b.branch_id: b.thinking_policy for b in episode_group.branches}
        folded = fold_into_decoding(binding["values"]) or binding["values"]
        decoding_values = folded.get("decoding_params")
        thinking_base = dict(decoding_values) if isinstance(decoding_values, Mapping) else {}
    elif template_group is not None:
        # NX-T R3: a Solver template group on a THINKING fragment. The arms differ in the instruction only; the walk reports each arm's resolved per-node wire
        # fields (no arm policy exists, so every arm resolves to the node's own role-level decoding) so a dry run shows that an arm contact carries the lock's
        # thinking fields. Nothing is reported for a non-thinking fragment (``fold_into_decoding`` returns None), which leaves every Instruct walk unchanged.
        from ..core.reasoning_knobs import fold_into_decoding

        folded = fold_into_decoding(binding["values"]) if binding.get("values") is not None else None
        if folded:
            decoding_values = folded.get("decoding_params")
            thinking_base = dict(decoding_values) if isinstance(decoding_values, Mapping) else {}

    def _arm_node_decoding(arm_id: str) -> dict[str, dict[str, object]] | None:
        if thinking_base is None:
            return None
        from ..core.reasoning_knobs import resolve_node_decoding

        policy = thinking_policy_by_arm.get(arm_id) or {}
        # The cell-level ``thinking_policy`` (decision 283 A; NX-T R2b states the lock form there because the serving fragment carries the geometry cap) is
        # composed FIRST, exactly as the request composer does, then the arm's own policy on top; a cell without one is unchanged.
        cell_policy = binding["values"].get("thinking_policy") or {}
        out: dict[str, dict[str, object]] = {}
        for kind in ("perception", "solver"):
            resolved = resolve_node_decoding(resolve_node_decoding(thinking_base, cell_policy, kind), policy, kind)
            out[kind] = {key: resolved.get(key) for key in ("thinking_budget_tokens", "chat_template_kwargs", "max_tokens")}
        return out

    # Cell RANKVIS (owner decision 171): honour native_episode.
    # knowledge_value_rendering exactly as rails.runner.
    # _invoke_native_role_episode does -- the stores whose newly supplied
    # values are re-ordered by retrieval rank before the repeat-visit
    # restriction, or () for every cell that does not arm the key, which
    # leaves this walk byte-identical to its pre-RANKVIS self.
    value_rendering = getattr(binding["episode"], "knowledge_value_rendering", None)
    rank_order_stores: tuple[str, ...] = ()
    if value_rendering is not None and value_rendering.get("order") == "retrieval-rank":
        rank_order_stores = tuple(value_rendering["stores"])
    snapshot = phase_binding["knowledge_snapshot"]
    packets = phase_binding["speech_packet_bindings"]
    query_source = phase_binding.get("query_source", "speech_features")

    samples = runtime._samples
    if sample_id is not None:
        samples = tuple(item for item in samples if item.sample_id == sample_id)
    if not samples:
        raise NativeEpisodeDryRunError(
            f"sample {sample_id!r} is not in this cell's roster"
        )
    sample = samples[0]
    descriptor = packets.get(sample.sample_id)
    if not isinstance(descriptor, Mapping):
        raise NativeEpisodeDryRunError(
            f"no speech packet binding for row {sample.sample_id!r}"
        )

    facet_seed, value_seed, seed_source = _first_phase_seed(
        runtime, program, phase_binding
    )
    first_phase = program.phase_names()[0]
    bootstrap_facets = tuple(
        (facet_seed.get(first_phase) or {}).get(sample.sample_id, ())
    )
    bootstrap_values = tuple(
        (value_seed.get(first_phase) or {}).get(sample.sample_id, ())
    )

    task_contract = runtime._adapter.build_task_contract(
        sample, default_obs_packet(sample)
    )
    query_state = QueryState(
        query_id=f"{runtime._plan.run_id}:{sample.sample_id}:step0",
        query_sample_id=sample.sample_id,
        speech_packet_id=descriptor["packet_id"],
        speech_packet_sha256=descriptor["sha256"],
        use_split_identity_hash=runtime._plan.split_identity_hash,
        visible_facet_ids=bootstrap_facets,
        retrieved_value_ids=bootstrap_values,
        query_source=query_source,
    ).validate()

    snapshot_sha256 = snapshot.content_hash()
    catalog_facet_ids = tuple(item.facet_id for item in snapshot.facets)
    catalog_value_ids = tuple(item.value_id for item in snapshot.values)

    def context_at(state, states, responses):
        return AgentRuntimeContext(
            sample_id=sample.sample_id,
            knowledge_snapshot_sha256=snapshot_sha256,
            catalog_facet_ids=catalog_facet_ids,
            catalog_value_ids=catalog_value_ids,
            query_state=state,
            task_contract=task_contract,
            agent_states=tuple(states),
            prior_response_sha256s=tuple(responses),
            contact_index=len(responses),
        )

    order = (
        tuple(node_order)
        if node_order is not None
        else episode_node_order(binding["episode"])
    )
    known = set(program.phase_names())
    unknown = [phase for phase in order if phase not in known]
    if unknown:
        raise NativeEpisodeDryRunError(f"node order names unknown phases {unknown}")

    def answer(phase: str, visit: int) -> str:
        text = answers(phase, visit) if callable(answers) else answers.get(phase)
        if not isinstance(text, str) or not text:
            raise NativeEpisodeDryRunError(
                f"no canned response for role {phase!r} visit {visit}"
            )
        return text

    states: list[object] = []
    responses: list[str] = []
    visits: dict[str, int] = {}
    nodes: list[DryRunNode] = []
    pending_supply = None
    pending_arms: tuple = ()
    #: Item E42: what the variant node's own supply steps have acquired on this
    #: row, cumulatively -- the set a non-delivering arm replaces, exactly as
    #: ``rails.runner`` tracks it.
    variant_node_acquired: list[str] = []
    delivered = None
    delivered_phase = None

    for position, phase in enumerate(order):
        visits[phase] = visits.get(phase, 0) + 1
        context = context_at(query_state, states, responses)
        material = material_for_phase(
            phase, context, {sample.sample_id: states[-1]} if states else {}
        )
        if not isinstance(material, PhaseMaterial):
            raise NativeEpisodeDryRunError("phase material must be a PhaseMaterial")
        material.validate()
        template_arms: tuple = ()
        if template_entries is not None and phase == template_phase:
            # NX programme E1: the template arms of THIS visit, walked at the
            # node. Every arm supplies the row's own accumulated evidence (the
            # supply is unvaried); the delivering arm and the twin render the
            # node's locked instruction, every other arm its own pinned
            # template through the flight-owned builder, over the same
            # predecessor binding, fill and response format.
            sealed_arg = {sample.sample_id: states[-1]} if states else {}
            walked_template = []
            for arm_index, (arm_id, arm_deliver, arm_max_items, arm_pin) in enumerate(
                template_entries
            ):
                if arm_pin is not None:
                    arm_material = template_materials[arm_id](
                        phase, context, sealed_arg,
                    )
                    arm_material.validate()
                    if arm_material.response_format != material.response_format:
                        raise NativeEpisodeDryRunError(
                            f"template arm {arm_id!r} changed the node's response "
                            "format; an arm overrides the instruction template only"
                        )
                    instruction = arm_material.instruction
                else:
                    instruction = material.instruction
                walked_template.append(DryRunArm(
                    arm_id=arm_id, arm_index=arm_index, deliver=arm_deliver,
                    resolved_knobs=(),
                    supplied_value_ids=tuple(query_state.retrieved_value_ids),
                    max_supplied_items=arm_max_items,
                    instruction_template=(
                        None if arm_pin is None else arm_pin.as_json()
                    ),
                    instruction_sha256=_sha256(instruction),
                    instruction_chars=len(instruction),
                    thinking_policy=thinking_policy_by_arm.get(arm_id),
                    node_decoding=_arm_node_decoding(arm_id),
                    decoding_override=(
                        template_group.arm(arm_id).decoding
                        if template_group is not None and template_group.is_decoding else None
                    ),
                ))
            template_arms = tuple(walked_template)
        text = answer(phase, visits[phase])
        contact_id = f"{CONTACT_NAMESPACE}:{phase}:{visits[phase]:02d}"
        state = seal_phase_response_state(
            phase_name=phase,
            sample_id=sample.sample_id,
            state_content=text,
            raw_response_text=text,
            source_query_state_sha256=query_state.content_hash(),
            producer_policy_id=program.program_id,
            state_namespace=contact_id,
        )
        # The exact boundary the CELL-1 smoke died at: the NEXT node's supply
        # is resolved from a context that already carries this node's sealed
        # state (``rails.runner``'s ``settle(next_phase=...)``), so every
        # candidate-bound route reads a state whose bytes are the model's own.
        next_phase = order[position + 1] if position + 1 < len(order) else None
        supply = None
        if next_phase is not None and supply_for_phase is not None:
            staged = context_at(
                query_state, [*states, state], [*responses, _sha256(text)]
            )
            supply = supply_for_phase(next_phase, staged)
            if supply is not None and rank_order_stores:
                # Cell RANKVIS: re-order each named store's selection by
                # retrieval rank BEFORE the repeat-visit restriction, exactly
                # where rails.runner._invoke_native_role_episode does it, by
                # calling that same function -- never a re-implementation.
                supply = order_supply_by_retrieval_rank(supply, snapshot, rank_order_stores)
            if supply is not None:
                supply.validate()
                if program.phase(next_phase).knowledge != "supplied":
                    raise NativeEpisodeDryRunError(
                        f"phase {next_phase!r} received supply but is not supplied"
                    )
                # The runner's own next step (``rails.runner``'s settle, E3c):
                # a prepared per-node selection is a pure function of (phase,
                # sample), so a REVISITED node is handed the SAME decision and
                # may acquire only what the accumulated QueryState does not
                # already carry. Walking without this made the dry run
                # DIVERGE from the flight on exactly the path a REVISE
                # verdict takes -- so the walk performs it, against the same
                # pre-seal context the runner passes.
                supply = restrict_repeat_visit_supply(
                    supply, context, phase_name=next_phase
                )
        arms: tuple = ()
        if (
            next_phase is not None
            and supply_variant_group is not None
            and template_group is None
            and next_phase == supply_variant_phase
        ):
            # Item E42: every declared arm's own supply, resolved against the
            # SAME staged context the ordinary step above was -- the one place
            # the flight resolves it too. Zero contacts: the routers read the
            # released, pinned stores and nothing else.
            from ..rails.supply_variants import arm_supplied_value_ids

            if supply_variant_resolver is None:
                raise NativeEpisodeDryRunError(
                    "this cell declares roles.solver.supply_variants but the "
                    "composed binding carries no per-arm resolver"
                )
            if supply is not None:
                variant_node_acquired.extend(
                    supply.fusion_decision.selected_value_ids
                )
            staged_for_arms = context_at(
                query_state, [*states, state], [*responses, _sha256(text)]
            )
            walked = []
            for arm_index, arm in enumerate(supply_variant_group.arms):
                arm_supply = supply_variant_resolver(
                    arm_id=arm.arm_id, phase_id=next_phase,
                    context=staged_for_arms,
                )
                selected = (
                    ()
                    if arm_supply is None
                    else tuple(arm_supply.fusion_decision.selected_value_ids)
                )
                if arm.deliver:
                    if selected != tuple(variant_node_acquired):
                        raise NativeEpisodeDryRunError(
                            "the delivering supply-variant arm resolves a "
                            "different supply than this row's own supply step "
                            "acquired; the delivered request would not be the "
                            "unvaried construction's request"
                        )
                    # The delivering arm renders the row's own accumulated
                    # state, unmodified -- which is what the walk proves.
                    supplied = tuple(query_state.retrieved_value_ids) + tuple(
                        () if supply is None
                        else supply.fusion_decision.selected_value_ids
                    )
                else:
                    supplied = arm_supplied_value_ids(
                        retrieved_value_ids=(
                            tuple(query_state.retrieved_value_ids) + tuple(
                                () if supply is None
                                else supply.fusion_decision.selected_value_ids
                            )
                        ),
                        node_acquired_value_ids=tuple(variant_node_acquired),
                        arm_selected_value_ids=selected,
                    )
                walked.append(DryRunArm(
                    arm_id=arm.arm_id,
                    arm_index=arm_index,
                    deliver=arm.deliver,
                    resolved_knobs=tuple(
                        {"path": knob.path, "value": knob.value}
                        for knob in sorted(arm.knobs, key=lambda item: item.path)
                    ),
                    supplied_value_ids=supplied,
                    max_supplied_items=arm.max_supplied_items,
                ))
            arms = tuple(walked)
        nodes.append(
            DryRunNode(
                phase=phase,
                visit=visits[phase],
                contact_id=contact_id,
                instruction_sha256=_sha256(material.instruction),
                instruction_chars=len(material.instruction),
                response_format_id=program.phase(phase).response_format_id,
                supplied_value_ids=(
                    ()
                    if pending_supply is None
                    else tuple(pending_supply.fusion_decision.selected_value_ids)
                ),
                supplied_facet_ids=(
                    ()
                    if pending_supply is None
                    else tuple(pending_supply.fusion_decision.supporting_facet_ids)
                ),
                state_id=state.state_id,
                state_kind=state.state_kind,
                state_content_sha256=_sha256(state.content),
                supply_variant_arms=template_arms or pending_arms,
            )
        )
        query_state, _transition = advance_phase_response_state(
            context=context,
            added_states=(state,),
            action_target_ref=f"{program.program_id}:{phase}:{contact_id}",
            supply=supply,
        )
        states.append(state)
        responses.append(_sha256(text))
        pending_supply = supply
        pending_arms = arms
        delivered, delivered_phase = text, phase

    solver_states = [item for item in states if item.state_kind == "phase:solver"]
    if solver_states:
        delivered = solver_states[-1].content
        delivered_phase = "solver"
    if delivered is None:
        raise NativeEpisodeDryRunError("the walk delivered nothing")
    return DryRunResult(
        schema=DRY_RUN_SCHEMA,
        run_id=runtime._plan.run_id,
        cell_sample_id=sample.sample_id,
        policy=str(binding["policy"]),
        program_id=program.program_id,
        episode_id=binding["episode"].episode_id,
        nodes=tuple(nodes),
        bootstrap_value_ids=bootstrap_values,
        bootstrap_facet_ids=bootstrap_facets,
        delivered_phase=str(delivered_phase),
        delivered_sha256=_sha256(delivered),
        store_ids=tuple(binding["store_ids"]),
        first_phase_seed_source=seed_source,
        scenario_gate_decisions=_scenario_gate_decisions(
            phase_binding, sample.sample_id
        ),
    )


__all__ = [
    "CONTACT_NAMESPACE",
    "NATIVE_ROLE_GRAPH_ORDER",
    "DRY_RUN_SCHEMA",
    "DryRunGateDecision",
    "DryRunNode",
    "DryRunResult",
    "NativeEpisodeDryRunError",
    "compose_dry_run",
    "dry_run_native_episode",
    "episode_node_order",
    "legal_intent_ids",
    "main",
    "store_facet_ids",
]


def main(argv=None) -> int:
    """``python -m speech_aware_evidence_acquisition.analysis.native_episode_dry_run``.

    ``--describe`` prints what a caller needs in order to write answers for
    this cell (its bound stores, its first phase's legal inventory, and the
    facet ids a named store addresses). ``--answers`` then walks the episode
    with a committed ``{role: text}`` document and prints the receipt.

    Contact-free by construction: this entry point never opens a gate, a
    transport, a client, an attempt or a serving session.
    """

    import argparse
    import json
    import os
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Dry-run one native role episode.")
    for name in ("repo-root", "data-root", "runtime-root", "lock-path"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument("--answers", type=Path)
    parser.add_argument("--describe", action="store_true")
    parser.add_argument("--store", action="append", default=[])
    parser.add_argument("--sample-id")
    args = parser.parse_args(argv)
    if not args.describe and args.answers is None:
        parser.error("pass --answers <json> or --describe")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        parser.error("PYTHONDONTWRITEBYTECODE=1 is required")

    from ..core.flight.factory import build_flight_runtime

    repo, data = Path(args.repo_root).resolve(), Path(args.data_root).resolve()
    fragment = json.loads(
        (repo / "configs" / "experiment" / f"{args.experiment}.json").read_text(
            encoding="utf-8"
        )
    )
    cells = [item for item in fragment["cells"] if item["cell_id"] == args.cell]
    if len(cells) != 1:
        parser.error(f"cell {args.cell!r} is not declared by the experiment")
    cell = cells[0]
    runtime = build_flight_runtime(
        repo,
        data,
        model=cell["model_fragment"],
        dataset=cell["dataset_fragment"],
        baseline=cell["baseline_fragment"],
        experiment=args.experiment,
        run_id=cell["run_id"],
        attempt_id=cell["attempt_id"],
        runtime_root=Path(args.runtime_root),
        lock_path=Path(args.lock_path),
        campaign_active=False,
    )
    binding = compose_dry_run(runtime, sample_limit=1)
    if args.describe:
        print(
            json.dumps(
                {
                    "schema": DRY_RUN_SCHEMA,
                    "cell": args.cell,
                    "policy": binding["policy"],
                    "program_id": binding["program"].program_id,
                    "node_order": list(episode_node_order(binding["episode"])),
                    "store_ids": list(binding["store_ids"]),
                    "legal_candidate_ids": list(legal_intent_ids(runtime)),
                    "store_facet_ids": {
                        store: list(store_facet_ids(runtime, store))
                        for store in args.store
                    },
                },
                indent=1,
                sort_keys=True,
            )
        )
        if args.answers is None:
            return 0
    answers = json.loads(args.answers.read_text(encoding="utf-8"))
    if not isinstance(answers, dict):
        parser.error("--answers must be a {role: text} JSON object")
    result = dry_run_native_episode(
        runtime, answers=answers, sample_id=args.sample_id, sample_limit=1
    )
    print(json.dumps(result.as_json(), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
