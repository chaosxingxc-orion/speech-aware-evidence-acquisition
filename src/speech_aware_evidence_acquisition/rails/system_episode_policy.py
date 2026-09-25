"""Select a complete native binding before the first role, without running it.

FlightRuntime must verify and admit every action definition before binding this
callback. This module owns neither execution, service access, scoring nor learning.
"""
from __future__ import annotations

import copy
from dataclasses import asdict
from threading import RLock
from types import MappingProxyType

from .finite_action_policy import _sha
from .hashing import content_hash
from .native_episode_config import NativeEpisodeRunBinding


class SystemEpisodePolicyError(ValueError):
    """A complete-policy selection violates its frozen execution envelope."""


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
                or binding.config.max_contacts != reference.config.max_contacts
                or binding.config.local_tool_workers != reference.config.local_tool_workers):
            raise SystemEpisodePolicyError("actions changed the shared execution envelope")
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

    def select(self, context):
        """Log one real choice before any model contact; never silently replay it."""
        with self._lock:
            sid = context.sample_id
            if sid in self._decisions:
                raise SystemEpisodePolicyError("this episode already has a policy decision")
            query = context.query_state.validate()
            if (query.query_sample_id != sid or context.contact_index != 0
                    or context.agent_states or context.prior_response_sha256s
                    or query.agent_state_ids):
                raise SystemEpisodePolicyError("selection must occur before every native role")
            decision, index = self.schedule.decision_for(sid, "episode-start", self.snapshot)
            definition = self._definitions[decision.action]
            selected = self.actions[decision.action]
            if (asdict(selected.config) != definition["config"]
                    or asdict(selected.program) != definition["program"]):
                raise SystemEpisodePolicyError("selected action changed after round freeze")
            record = {
                "schema": "saea-system-episode-policy-decision-v1",
                "algorithm_id": "finite-system-policy-bandit-v1",
                "selection_scope": "complete-episode-policy",
                "sample_id": sid, "sequence_index": index,
                "pre_action_query_sha256": query.content_hash(),
                "speech_packet_sha256": query.speech_packet_sha256,
                "schedule_sha256": self.schedule.sha256,
                "action_space_sha256": self._definition_sha256,
                "selected_definition_sha256": content_hash(definition),
                "selected_source_hashes": copy.deepcopy(definition["source_hashes"]),
                "decision": decision.as_json(),
            }
            record["decision_receipt_sha256"] = content_hash(record)
            if self.emit_decision is not None:
                self.emit_decision(copy.deepcopy(record))
            self._decisions[sid] = copy.deepcopy(record)
            return self.actions[decision.action], record
