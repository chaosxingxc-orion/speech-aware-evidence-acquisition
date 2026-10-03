"""Select a complete native binding before the first role, without running it.

FlightRuntime must verify and admit every action definition before binding this
callback. This module owns neither execution, service access, scoring nor learning.
"""
from __future__ import annotations

import copy
from dataclasses import asdict
from threading import RLock
from types import MappingProxyType

from .finite_action_policy import PolicyDecision, _sha
from .hashing import content_hash
from .native_episode_config import NativeEpisodeRunBinding


class SystemEpisodePolicyError(ValueError):
    """A complete-policy selection violates its frozen execution envelope."""


def parse_system_policy_record(record):
    """Validate a recorded choice's shape, never its admission or source truth."""
    keys = {
        "schema", "algorithm_id", "selection_scope", "sample_id", "sequence_index",
        "pre_action_query_sha256", "speech_packet_sha256", "schedule_sha256",
        "action_space_sha256", "selected_definition_sha256", "selected_source_hashes",
        "decision", "decision_receipt_sha256",
    }
    if not isinstance(record, dict) or set(record) != keys:
        raise SystemEpisodePolicyError("system policy record has missing or unknown fields")
    if (record["schema"] != "saea-system-episode-policy-decision-v1"
            or record["algorithm_id"] != "finite-system-policy-bandit-v1"
            or record["selection_scope"] != "complete-episode-policy"):
        raise SystemEpisodePolicyError("system policy record schema or scope differs")
    if (not isinstance(record["sample_id"], str) or not record["sample_id"]
            or type(record["sequence_index"]) is not int or record["sequence_index"] < 0):
        raise SystemEpisodePolicyError("system policy sample or sequence is invalid")
    for field in keys:
        if field.endswith("_sha256"):
            _sha(record[field], "system policy " + field)
    sources = record["selected_source_hashes"]
    if (not isinstance(sources, dict) or not sources
            or any(not isinstance(k, str) or not k for k in sources)):
        raise SystemEpisodePolicyError("system policy selected sources are invalid")
    for value in sources.values():
        _sha(value, "system policy selected source")
    unsigned = dict(record)
    claimed = unsigned.pop("decision_receipt_sha256")
    if claimed != content_hash(unsigned):
        raise SystemEpisodePolicyError("system policy decision fingerprint differs")
    decision = PolicyDecision.from_json(record["decision"])
    if decision.state_id != "episode-start":
        raise SystemEpisodePolicyError("system policy decision uses a future/unsupported state")
    return decision


def build_system_policy_record(*, snapshot, schedule, definitions, sid,
                               query_sha256, speech_packet_sha256):
    """One canonical allocation record for execution and source verification."""
    _sha(query_sha256, "initial query")
    _sha(speech_packet_sha256, "initial speech")
    decision, index = schedule.decision_for(sid, "episode-start", snapshot)
    definition = definitions[decision.action]
    record = {
        "schema": "saea-system-episode-policy-decision-v1",
        "algorithm_id": "finite-system-policy-bandit-v1",
        "selection_scope": "complete-episode-policy",
        "sample_id": sid, "sequence_index": index,
        "pre_action_query_sha256": query_sha256,
        "speech_packet_sha256": speech_packet_sha256,
        "schedule_sha256": schedule.sha256,
        "action_space_sha256": content_hash(definitions),
        "selected_definition_sha256": content_hash(definition),
        "selected_source_hashes": copy.deepcopy(definition["source_hashes"]),
        "decision": decision.as_json(),
    }
    record["decision_receipt_sha256"] = content_hash(record)
    return record


class SystemEpisodePolicy:
    """An episode-level bandit selection, not node-level causal credit.

    The initial version uses one pre-episode state. It is deliberately a global
    policy selector, not a contextual classifier using future Perception output.
    A selected policy receives its complete terminal outcome even when its tool
    is never called. That is not credit to an unexecuted tool action.
    """

    def __init__(self, *, snapshot, schedule, actions, source_hashes, emit_decision=None):
        if snapshot.states != ("episode-start",):
            raise SystemEpisodePolicyError("only the pre-role episode-start state is admitted")
        if tuple(actions) != snapshot.actions or set(source_hashes) != set(actions):
            raise SystemEpisodePolicyError("ordered action bindings differ from the snapshot")
        if schedule.snapshot_sha256 != snapshot.sha256:
            raise SystemEpisodePolicyError("schedule differs from the frozen snapshot")
        # Rebind rather than trusting caller-provided cached assignments.
        self.schedule = schedule.bind(snapshot)
        self.snapshot = snapshot
        self.actions = MappingProxyType(dict(actions))
        self.emit_decision = emit_decision
        definitions = {}
        reference = next(iter(actions.values()))
        if not isinstance(reference, NativeEpisodeRunBinding):
            raise SystemEpisodePolicyError("action needs a native binding")
        self._reference = reference
        for name, binding in self.actions.items():
            if not isinstance(binding, NativeEpisodeRunBinding) or binding.system_episode_policy is not None:
                raise SystemEpisodePolicyError("action needs a nonrecursive native binding")
            self.assert_envelope(binding)
            sources = source_hashes[name]
            if not isinstance(sources, dict) or not sources:
                raise SystemEpisodePolicyError("action definition needs verified source hashes")
            for key, value in sources.items():
                if not isinstance(key, str) or not key:
                    raise SystemEpisodePolicyError("source name must be nonempty text")
                _sha(value, "whole-policy source")
            definitions[name] = {
                "config": asdict(binding.config), "program": asdict(binding.program),
                "source_hashes": copy.deepcopy(sources),
            }
        self._definitions = definitions
        self._definition_sha256 = content_hash(definitions)
        for credit in snapshot.credited:
            sources = dict(credit.source_hashes)
            if (sources.get("system_action_space") != self._definition_sha256
                    or sources.get("system_action_definition") != content_hash(definitions[credit.action])):
                raise SystemEpisodePolicyError("learned values belong to another whole-policy action space")
        self._lock = RLock()
        self._decisions = {}

    def assert_envelope(self, binding):
        """Refuse an action set built for a different outer scheduler or service."""
        reference = self._reference
        if (binding.program != reference.program
                or not 0 < binding.config.max_contacts <= reference.program.max_contacts
                or binding.config.local_tool_workers != reference.config.local_tool_workers
                or binding.prefix_slots != reference.prefix_slots
                or binding.node_batch != reference.node_batch
                or binding.node_pipeline != reference.node_pipeline
                or binding.workflow_panel is not reference.workflow_panel):
            raise SystemEpisodePolicyError("actions changed the shared execution envelope")
        if binding.node_pipeline is not None:
            from .dispatch_slot_fill import NativeNodePipelineError
            try:
                binding.node_pipeline.validate(binding.config)
            except NativeNodePipelineError as error:
                raise SystemEpisodePolicyError(str(error)) from error
        if binding.node_batch is not None:
            from .dispatch_slot_fill import NativeNodeBatchError
            try:
                binding.node_batch.validate(binding.config, queue_depth=binding.node_batch.batch_size)
            except NativeNodeBatchError as error:
                raise SystemEpisodePolicyError(str(error)) from error
        if binding.prefix_slots is not None:
            from .dispatch_slot_fill import NativePrefixSlotsError

            try:
                binding.prefix_slots.validate(
                    binding.config,
                    slot_count=1 + max(binding.prefix_slots.slot_bindings().values()),
                )
            except NativePrefixSlotsError as error:
                raise SystemEpisodePolicyError(str(error)) from error
        for field in ("material_for_phase", "render_request", "request_gate"):
            if getattr(binding, field) is not getattr(reference, field):
                raise SystemEpisodePolicyError("actions changed the shared service/input envelope")
        for field in ("repo_root", "data_root", "context_fit_budget"):
            if getattr(binding, field) != getattr(reference, field):
                raise SystemEpisodePolicyError("actions changed the shared source/capacity envelope")

    @property
    def decisions(self):
        with self._lock:
            return copy.deepcopy(self._decisions)

    def expected_record(self, sid, *, query_sha256, speech_packet_sha256):
        """Reproduce the registered allocation; no contact, selection side effect or update."""
        _sha(query_sha256, "initial query")
        _sha(speech_packet_sha256, "initial speech")
        decision, index = self.schedule.decision_for(sid, "episode-start", self.snapshot)
        definition = self._definitions[decision.action]
        selected = self.actions[decision.action]
        if (asdict(selected.config) != definition["config"]
                or asdict(selected.program) != definition["program"]):
            raise SystemEpisodePolicyError("selected action changed after round freeze")
        return build_system_policy_record(
            snapshot=self.snapshot, schedule=self.schedule, definitions=self._definitions,
            sid=sid, query_sha256=query_sha256, speech_packet_sha256=speech_packet_sha256,
        )

    def validate_record(self, record):
        decision = parse_system_policy_record(record)
        expected = self.expected_record(
            record["sample_id"], query_sha256=record["pre_action_query_sha256"],
            speech_packet_sha256=record["speech_packet_sha256"],
        )
        if record != expected:
            raise SystemEpisodePolicyError("system policy record differs from frozen allocation or sources")
        return decision

    def select(self, context):
        """Log one real choice before any model contact; never silently replay it."""
        with self._lock:
            sid = context.sample_id
            if sid in self._decisions:
                raise SystemEpisodePolicyError("this episode already has a policy decision")
            query = context.query_state.validate()
            if (query.query_sample_id != sid or context.contact_index != 0
                    or context.agent_states or context.prior_response_sha256s
                    or query.agent_state_ids or query.loop_step != 0):
                raise SystemEpisodePolicyError("selection must occur before every native role")
            record = self.expected_record(
                sid, query_sha256=query.content_hash(),
                speech_packet_sha256=query.speech_packet_sha256,
            )
            if self.emit_decision is not None:
                self.emit_decision(copy.deepcopy(record))
            self._decisions[sid] = copy.deepcopy(record)
            return self.actions[record["decision"]["action"]], record
