"""One episode-held evidence action through the ordinary phase-supply callback.

A preview is observed by the control plane only. The shared runner subsequently
acquires the chosen supply, renders the actual request, and executes every role.
This callable does not answer, invoke models, or update a policy during a round.
"""

from __future__ import annotations

import copy
from threading import RLock
from types import MappingProxyType

from .hashing import content_hash
from .knowledge import AgentStateArtifact

AGREEMENT_STATES = (
    "no-exemplars", "agree-lt-0.25", "agree-0.25-0.50",
    "agree-0.50-0.75", "agree-ge-0.75",
)
ALGORITHM_ID = "finite-action-bandit-v1"


class FiniteSupplyPolicyError(ValueError):
    """The selected action lacks pre-action state or source custody."""


def agreement_state(candidates, labels):
    if not labels:
        return AGREEMENT_STATES[0]
    if not candidates:
        raise FiniteSupplyPolicyError("a nonempty preview needs a normalized candidate")
    matches = sum(label == candidates[0] for label in labels)
    share = matches / len(labels)
    for edge, state in zip((0.25, 0.50, 0.75), AGREEMENT_STATES[1:4]):
        if share < edge:
            return state
    return AGREEMENT_STATES[4]


class EpisodeSupplyPolicy:
    """An ordinary supply callback; one choice before the first Solver per row."""

    def __init__(
        self, *, snapshot, schedule, phase_id, perception_phase, preview_supply,
        preview_snapshot_sha256, preview_labels, action_supplies, default_supply,
        candidate_reader, emit_decision=None,
    ):
        if tuple(snapshot.states) != AGREEMENT_STATES:
            raise FiniteSupplyPolicyError("policy must use the frozen agreement states")
        if tuple(action_supplies) != snapshot.actions:
            raise FiniteSupplyPolicyError("action routers must match the ordered policy actions")
        if snapshot.sha256 != schedule.snapshot_sha256:
            raise FiniteSupplyPolicyError("schedule and policy snapshot disagree")
        if phase_id == perception_phase:
            raise FiniteSupplyPolicyError("action phase must follow Perception")
        self.snapshot, self.schedule = snapshot, schedule
        self.phase_id, self.perception_phase = phase_id, perception_phase
        self.preview_supply = preview_supply
        self.preview_snapshot_sha256 = preview_snapshot_sha256
        self.preview_labels = MappingProxyType(dict(preview_labels))
        self.action_supplies = MappingProxyType(dict(action_supplies))
        self.default_supply, self.candidate_reader = default_supply, candidate_reader
        self.emit_decision = emit_decision
        self._lock = RLock()
        self._decisions = {}
        self._initial = {}
        self.receipt = {
            "schema": "saea-finite-supply-policy-execution-v1",
            "algorithm_id": ALGORITHM_ID, "snapshot_sha256": snapshot.sha256,
            "schedule_sha256": schedule.sha256,
            "state_policy": "slurp-exemplar-top-agreement-v1",
            "agreement_edges": [0.25, 0.50, 0.75],
            "decision_phase": phase_id, "decisions": {}, "visits": [],
        }

    def _initial_state(self, context):
        query = context.query_state.validate()
        if query.query_sample_id != context.sample_id:
            raise FiniteSupplyPolicyError("policy context belongs to another sample")
        states = tuple(context.agent_states)
        if (len(states) != 1 or not isinstance(states[0], AgentStateArtifact)
                or states[0].state_kind != f"phase:{self.perception_phase}"):
            raise FiniteSupplyPolicyError(
                "first Perception state must precede every Solver/Reviewer/Planner state"
            )
        state = states[0].validate()
        if query.agent_state_ids:
            raise FiniteSupplyPolicyError("first decision requires the newly staged Perception state")
        if state.source_query_state_sha256 != query.content_hash():
            raise FiniteSupplyPolicyError("Perception is bound to another query")
        response_hashes = tuple(context.prior_response_sha256s)
        if not response_hashes or response_hashes[-1] != state.source_response_sha256:
            raise FiniteSupplyPolicyError("Perception is bound to another response")
        return state

    def _choose(self, context):
        state = self._initial_state(context)
        candidates = tuple(self.candidate_reader(state, context.sample_id))
        if not candidates or len(set(candidates)) != len(candidates):
            raise FiniteSupplyPolicyError("candidate reader must return ordered distinct candidates")
        preview = self.preview_supply(context)
        ids = ()
        preview_record = {
            "exposed_to_model": False, "snapshot_sha256": self.preview_snapshot_sha256,
            "query_state_sha256": context.query_state.content_hash(),
            "selected_value_ids": [], "rank_sha256": None, "fusion_sha256": None,
        }
        if preview is not None:
            preview.validate()
            rank, fusion = preview.rank_result, preview.fusion_decision
            if rank.snapshot_sha256 != self.preview_snapshot_sha256 or fusion.snapshot_sha256 != self.preview_snapshot_sha256:
                raise FiniteSupplyPolicyError("preview is bound to another knowledge snapshot")
            if rank.query_state_sha256 != context.query_state.content_hash() or fusion.query_state_sha256 != context.query_state.content_hash():
                raise FiniteSupplyPolicyError("preview is bound to another query")
            if fusion.rank_result_sha256 != rank.content_hash():
                raise FiniteSupplyPolicyError("preview fusion has another rank binding")
            ids = fusion.selected_value_ids
            if len(set(ids)) != len(ids):
                raise FiniteSupplyPolicyError("preview repeats a value")
            preview_record.update(
                selected_value_ids=list(ids), rank_sha256=rank.content_hash(),
                fusion_sha256=fusion.content_hash(),
            )
        if any(value not in self.preview_labels or not self.preview_labels[value] for value in ids):
            raise FiniteSupplyPolicyError("preview value lacks a released training label")
        state_id = agreement_state(candidates, [self.preview_labels[value] for value in ids])
        decision, sequence = self.schedule.decision_for(context.sample_id, state_id, self.snapshot)
        record = {
            "schema": "saea-pre-solver-action-decision-v1",
            "sample_id": context.sample_id, "sequence_index": sequence,
            "perception_state_id": state.state_id,
            "perception_state_sha256": state.content_hash(),
            "pre_action_query_sha256": context.query_state.content_hash(),
            "speech_packet_sha256": context.query_state.speech_packet_sha256,
            "candidates": list(candidates), "preview": preview_record,
            "state_id": state_id, "decision": decision.as_json(),
            "schedule_sha256": self.schedule.sha256,
        }
        record["decision_receipt_sha256"] = content_hash(record)
        if self.emit_decision is not None:
            self.emit_decision(copy.deepcopy(record))
        self._initial[context.sample_id] = (
            state.content_hash(), context.query_state.speech_packet_sha256,
        )
        self._decisions[context.sample_id] = decision
        self.receipt["decisions"][context.sample_id] = record
        return decision

    def __call__(self, phase, context):
        if phase != self.phase_id:
            return self.default_supply(phase, context) if self.default_supply else None
        with self._lock:
            if context.sample_id not in self.schedule.roster_ids:
                raise FiniteSupplyPolicyError("sample is outside the frozen policy roster")
            decision = self._decisions.get(context.sample_id)
            if decision is None:
                decision = self._choose(context)
            else:
                states = [state for state in context.agent_states
                          if isinstance(state, AgentStateArtifact)
                          and state.state_kind == f"phase:{self.perception_phase}"]
                expected_state, expected_speech = self._initial[context.sample_id]
                if (not states or states[0].content_hash() != expected_state
                        or context.query_state.query_sample_id != context.sample_id
                        or context.query_state.speech_packet_sha256 != expected_speech):
                    raise FiniteSupplyPolicyError("revision changed the initial episode binding")
            supply = self.action_supplies[decision.action](phase, context)
            self.receipt["visits"].append({
                "sample_id": context.sample_id, "action": decision.action,
                "query_state_sha256": context.query_state.content_hash(),
                "selected_value_ids": list(supply.fusion_decision.selected_value_ids) if supply else [],
                "fusion_sha256": supply.fusion_decision.content_hash() if supply else None,
            })
            return supply


def build_finite_supply_policy(
    values, *, program, native_config, store_binding, default_router,
    action_router_factory, data_root, roster_ids, split_identity_hash,
    legal_candidate_ids, emit_decision=None,
):
    """Bind one explicitly configured policy using existing released store routers."""
    from collections.abc import Mapping
    from .finite_policy_artifacts import load_policy_snapshot, load_policy_schedule
    from .candidate_semantic_supply import (
        candidate_state_read_parameters, load_candidate_semantic_supply_specs,
    )
    from .slurp_intent_hypotheses import parse_slurp_intent_hypothesis_state
    from .supply_variants import parse_supply_variant_knob
    from ..core.stage3_algorithms import resolve_stage3_algorithm

    raw = values.get("finite_supply_policy")
    if raw is None:
        return None
    keys = {
        "schema", "algorithm_id", "phase_id", "perception_phase", "preview_store",
        "preview_k", "snapshot", "schedule", "actions",
    }
    if not isinstance(raw, Mapping) or set(raw) != keys:
        raise FiniteSupplyPolicyError("finite_supply_policy has missing or unknown fields")
    if raw["schema"] != "saea-finite-supply-policy-config-v1" or raw["algorithm_id"] != ALGORITHM_ID:
        raise FiniteSupplyPolicyError("finite supply schema or algorithm identity disagrees")
    resolve_stage3_algorithm(raw["algorithm_id"])
    if native_config is None or store_binding is None or default_router is None:
        raise FiniteSupplyPolicyError("finite supply requires the ordinary native named-store path")
    solver = native_config.role("solver")
    perception = native_config.role("perception")
    if (raw["phase_id"] != solver.phase_id or raw["perception_phase"] != perception.phase_id
            or program.phase_names()[0] != perception.phase_id
            or program.phase(solver.phase_id).knowledge != "supplied"):
        raise FiniteSupplyPolicyError("finite supply must precede the native Solver after initial Perception")
    if (solver.samples != 1 or native_config.supply_variant_group is not None
            or native_config.knowledge_index_json is not None or native_config.acquisition_enabled):
        raise FiniteSupplyPolicyError("finite supply currently requires one ordinary Solver trajectory")
    preview_store = store_binding.store(raw["preview_store"])
    spec = preview_store.phase_supply.get(solver.phase_id)
    if (not isinstance(spec, Mapping) or raw["preview_k"] != 20
            or isinstance(raw["preview_k"], bool) or spec.get("k") != 20
            or preview_store.store_role != "train-exemplars"):
        raise FiniteSupplyPolicyError("state preview must use the fixed default20 exemplar route")
    params = candidate_state_read_parameters(
        load_candidate_semantic_supply_specs(store_binding, program),
        candidate_state_phase=perception.phase_id,
    )
    if params is None or not legal_candidate_ids:
        raise FiniteSupplyPolicyError("finite supply needs the plan's shared SLURP candidate reader")
    legal = frozenset(legal_candidate_ids)
    labels = {value.value_id: value.task_target for value in preview_store.snapshot.values}
    if any(label not in legal for label in labels.values()):
        raise FiniteSupplyPolicyError("preview requires legal released training labels")
    snapshot = load_policy_snapshot(data_root, raw["snapshot"])
    schedule = load_policy_schedule(
        data_root, raw["schedule"], snapshot=snapshot, expected_roster_ids=roster_ids,
        expected_split_identity_hash=split_identity_hash,
    )
    actions = raw["actions"]
    if not isinstance(actions, list) or not 2 <= len(actions) <= 4:
        raise FiniteSupplyPolicyError("finite supply requires two to four registered actions")
    if any(not isinstance(action, Mapping) or set(action) != {"action_id", "overrides"}
           or not isinstance(action["overrides"], Mapping) for action in actions):
        raise FiniteSupplyPolicyError("each finite action must declare id and overrides")
    if tuple(action["action_id"] for action in actions) != snapshot.actions or actions[0]["overrides"]:
        raise FiniteSupplyPolicyError("ordered actions must match the snapshot with unchanged default first")
    routers = {}
    action_receipts = {}
    for action in actions:
        prefix = f"knowledge_stores.{preview_store.store_id}.phase_supply.{solver.phase_id}."
        if any(not isinstance(path, str) or not path.startswith(prefix)
               for path in action["overrides"]):
            raise FiniteSupplyPolicyError("first finite policy may change only the exemplar supply route")
        knobs = tuple(parse_supply_variant_knob(
            path, value, phase_id=solver.phase_id,
            first_phase_id=perception.phase_id, declared_stores=store_binding.store_ids,
        ) for path, value in action["overrides"].items())
        if any(knob.store_id != preview_store.store_id or knob.route != "phase_supply" for knob in knobs):
            raise FiniteSupplyPolicyError("first finite policy may change only the exemplar supply route")
        router = action_router_factory(action["action_id"], knobs) if knobs else default_router
        automatic = getattr(router, "automatic_for_phase", None)
        if not callable(automatic):
            raise FiniteSupplyPolicyError("action router has no ordinary automatic supply callback")
        routers[action["action_id"]] = automatic
        action_receipts[action["action_id"]] = router.receipt

    def candidate_reader(state, sample_id):
        parsed = parse_slurp_intent_hypothesis_state(
            state, expected_sample_id=sample_id, legal_intent_ids=legal,
            max_candidates=params[0], compact_source_phase=perception.phase_id,
            projection_policy=params[1],
        )
        return tuple(candidate.intent_id for candidate in parsed.candidates)

    bound = EpisodeSupplyPolicy(
        snapshot=snapshot, schedule=schedule, phase_id=solver.phase_id,
        perception_phase=perception.phase_id,
        preview_supply=lambda context: default_router(preview_store.store_id, solver.phase_id, context),
        preview_snapshot_sha256=preview_store.snapshot.content_hash(),
        preview_labels=labels, action_supplies=routers,
        default_supply=default_router.automatic_for_phase,
        candidate_reader=candidate_reader, emit_decision=emit_decision,
    )
    bound.receipt.update(
        configuration_sha256=content_hash(dict(raw)),
        snapshot_file=dict(raw["snapshot"]), schedule_file=dict(raw["schedule"]),
        preview_store=preview_store.store_id, preview_k=20,
        actions=action_receipts,
    )
    return bound
