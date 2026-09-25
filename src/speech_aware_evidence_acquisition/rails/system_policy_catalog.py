"""Compile pinned complete native policy assets through the shared config loader."""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, replace

from .finite_policy_artifacts import _pinned_json, load_policy_schedule, load_policy_snapshot
from .hashing import content_hash
from .native_episode_config import load_native_episode_config
from .phase_tools import load_phase_tool_specs
from .system_episode_policy import (
    SystemEpisodePolicy, SystemEpisodePolicyError, build_system_policy_record,
    parse_system_policy_record,
)


@dataclass(frozen=True)
class SystemPolicyCatalog:
    snapshot: object
    schedule: object
    program: object
    configs: dict
    values: dict
    source_hashes: dict

    @property
    def definitions(self):
        return {name: {"config": asdict(self.configs[name]), "program": asdict(self.program),
                       "source_hashes": copy.deepcopy(self.source_hashes[name])}
                for name in self.snapshot.actions}

    def expected_record(self, sid, *, query_sha256, speech_packet_sha256):
        return build_system_policy_record(
            snapshot=self.snapshot, schedule=self.schedule, definitions=self.definitions,
            sid=sid, query_sha256=query_sha256, speech_packet_sha256=speech_packet_sha256)

    def values_for_record(self, record):
        decision = parse_system_policy_record(record)
        expected = self.expected_record(
            record["sample_id"], query_sha256=record["pre_action_query_sha256"],
            speech_packet_sha256=record["speech_packet_sha256"])
        if record != expected:
            raise SystemEpisodePolicyError("selected configuration differs from its pinned catalog")
        return self.values[decision.action]

    def native_for_episode(self, episode, *, sample_id, query_sha256,
                           speech_packet_sha256, contact_count):
        record = episode.get("system_policy_decision")
        expected = self.expected_record(
            sample_id, query_sha256=query_sha256, speech_packet_sha256=speech_packet_sha256)
        if record != expected:
            raise SystemEpisodePolicyError("episode does not carry its actual registered selection")
        values = self.values_for_record(record)
        config = self.configs[record["decision"]["action"]]
        if type(contact_count) is not int or not 0 <= contact_count <= config.max_contacts:
            raise SystemEpisodePolicyError("episode exceeded its selected policy contact ceiling")
        roles = {role.phase_id: role for role in config.roles}
        if config.acquisition_role is not None:
            roles[config.acquisition_role.phase_id] = config.acquisition_role
        visits = list(episode.get("role_visits", []))
        if episode.get("interrupted_role") is not None:
            visits.append(episode["interrupted_role"])
        for visit in visits:
            role = roles.get(visit.get("role_id"))
            if role is None:
                raise SystemEpisodePolicyError("episode visits a role absent from its selected policy")
            count = len((visit.get("execution_receipt") or {}).get("contacts", []))
            if count > role.max_iterations * role.samples:
                raise SystemEpisodePolicyError("role exceeded its selected policy iteration ceiling")
        return copy.deepcopy(values["native_episode"])

    def bind(self, base, *, tools_for_values, acquisition_for_config):
        actions = {
            name: replace(base, config=self.configs[name],
                          tools_for_phase=tools_for_values(self.values[name]),
                          acquisition_requery=acquisition_for_config(self.configs[name]))
            for name in self.snapshot.actions
        }
        policy = SystemEpisodePolicy(
            snapshot=self.snapshot, schedule=self.schedule, actions=actions,
            source_hashes=self.source_hashes)
        return replace(base, system_episode_policy=policy)


def load_system_policy_catalog(*, repo_root, data_root, values, program,
                               expected_roster_ids, expected_split_identity_hash,
                               shared_source_hashes):
    spec = values.get("system_episode_policy")
    if spec is None:
        return None
    required = {"schema", "algorithm_id", "snapshot", "schedule", "actions"}
    if (not isinstance(spec, dict) or set(spec) != required
            or spec["schema"] != "saea-system-episode-policy-config-v1"
            or spec["algorithm_id"] != "finite-system-policy-bandit-v1"
            or values.get("stage3_algorithm", {}).get("id") != spec["algorithm_id"]):
        raise SystemEpisodePolicyError("complete policy configuration or algorithm label differs")
    if values.get("finite_supply_policy") is not None:
        raise SystemEpisodePolicyError("nested policy decisions need separately registered credit")
    entries = spec["actions"]
    if (not isinstance(entries, list) or not 2 <= len(entries) <= 4
            or any(not isinstance(e, dict) or set(e) != {"action_id", "source"} for e in entries)):
        raise SystemEpisodePolicyError("catalog requires two to four pinned complete policies")
    ids = tuple(e["action_id"] for e in entries)
    if (any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids)):
        raise SystemEpisodePolicyError("catalog action identities must be distinct")
    snapshot = load_policy_snapshot(data_root, spec["snapshot"])
    if snapshot.actions != ids or snapshot.states != ("episode-start",):
        raise SystemEpisodePolicyError("catalog actions/state differ from frozen values")
    schedule = load_policy_schedule(
        data_root, spec["schedule"], snapshot=snapshot,
        expected_roster_ids=expected_roster_ids,
        expected_split_identity_hash=expected_split_identity_hash)
    parent = load_native_episode_config(values, program)
    parent_tools = load_phase_tool_specs(values, program)
    if parent is None or parent.supply_variant_group is not None:
        raise SystemEpisodePolicyError("catalog requires an ordinary complete native episode")
    compiled, configs, sources = {}, {}, {}
    for entry in entries:
        name, pin = entry["action_id"], entry["source"]
        if (not isinstance(pin, dict)
                or not str(pin.get("relpath", "")).startswith("configs/probes/")):
            raise SystemEpisodePolicyError("policy source must be a confined config asset")
        asset, sha = _pinned_json(repo_root, pin, "complete policy action")
        if (not isinstance(asset, dict) or set(asset) != {"schema", "native_episode", "phase_tools"}
                or asset["schema"] != "saea-system-policy-action-v1"):
            raise SystemEpisodePolicyError("action may declare only native behavior and existing tool authority")
        child = copy.deepcopy(dict(values))
        child.pop("system_episode_policy")
        child["native_episode"] = copy.deepcopy(asset["native_episode"])
        child["phase_tools"] = copy.deepcopy(asset["phase_tools"])
        config = load_native_episode_config(child, program, allow_subceiling=True)
        if config is None:
            raise SystemEpisodePolicyError("action requires an explicit complete native configuration")
        tools = load_phase_tool_specs(child, program)
        for phase, spec_tools in tools.items():
            permitted = parent_tools.get(phase)
            if permitted is None:
                raise SystemEpisodePolicyError("action introduces undeclared tool authority")
            a, b = dict(spec_tools), dict(permitted)
            chosen = a.pop("allowed_tools")
            allowed = b.pop("allowed_tools")
            if not set(chosen) <= set(allowed) or a != b:
                raise SystemEpisodePolicyError("action changes shared tool source/authority parameters")
        # These objects are prebound outside the selected native graph. Their
        # source/representation cannot change without rebuilding that binding.
        for field in ("episode_id", "local_tool_workers", "knowledge_index_json", "solver_hints_json"):
            if getattr(config, field) != getattr(parent, field):
                raise SystemEpisodePolicyError("action changes a shared prebound source or scheduler")
        if config.supply_variant_group is not None:
            raise SystemEpisodePolicyError("Solver-only side branches are not complete policies")
        compiled[name], configs[name] = child, config
        sources[name] = {**shared_source_hashes, "policy_action_asset": sha}
    # Detect an asset replacement during compilation before any dispatch.
    for entry in entries:
        _pinned_json(repo_root, entry["source"], "complete policy action")
    catalog = SystemPolicyCatalog(snapshot, schedule, program, configs, compiled, sources)
    definitions = catalog.definitions
    for credit in snapshot.credited:
        prior = dict(credit.source_hashes)
        if (prior.get("system_action_space") != content_hash(definitions)
                or prior.get("system_action_definition") != content_hash(definitions[credit.action])):
            raise SystemEpisodePolicyError("learned values refer to another pinned policy catalog")
    return catalog
