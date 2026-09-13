"""Configuration and immutable callback binding for the public native role graph."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class NativeEpisodeRole:
    phase_id: str
    role_kind: str
    max_iterations: int
    tool_names: tuple[str, ...]


@dataclass(frozen=True)
class NativeEpisodeConfig:
    episode_id: str
    max_revisions: int
    actions: tuple[str, str, str]
    roles: tuple[NativeEpisodeRole, ...]
    max_contacts: int
    exhaustion_policy: str = "raise"

    def role(self, kind: str) -> NativeEpisodeRole:
        return next(role for role in self.roles if role.role_kind == kind)


@dataclass(frozen=True)
class NativeEpisodeRunBinding:
    """Flight-owned material/custody callbacks; no history, router or scheduler."""

    config: NativeEpisodeConfig
    program: object
    material_for_phase: Callable
    render_request: Callable
    request_gate: Callable
    tools_for_phase: object = None
    supply_for_phase: Callable | None = None
    review_for_phase: Callable | None = None


def load_native_episode_config(values: Mapping, program) -> NativeEpisodeConfig | None:
    """Require explicit role limits, role-local tool authority and a graph ceiling."""
    raw = values.get("native_episode")
    active = program.stop_rule == "native-role-episode"
    if raw is None:
        if active:
            raise ValueError("native-role-episode requires native_episode configuration")
        return None
    if not active:
        raise ValueError("native_episode requires the registered native-role-episode program")
    required_fields = {
        "schema", "episode_id", "max_revisions", "actions", "roles",
    }
    optional_fields = {"exhaustion_policy"}
    if (
        not isinstance(raw, Mapping)
        or set(raw) - required_fields - optional_fields
        or not required_fields <= set(raw)
        or raw["schema"] != "saea-native-episode-config-v1"
    ):
        raise ValueError("native_episode has unknown or missing fields")
    if not isinstance(raw["episode_id"], str) or not raw["episode_id"].strip():
        raise ValueError("native episode identity must be nonempty")
    revisions = raw["max_revisions"]
    if isinstance(revisions, bool) or not isinstance(revisions, int) or revisions < 0:
        raise ValueError("max_revisions must be a nonnegative integer")
    exhaustion_policy = raw.get("exhaustion_policy", "raise")
    if (
        not isinstance(exhaustion_policy, str)
        or exhaustion_policy not in {"raise", "deliver-latest-solver"}
    ):
        raise ValueError("native episode exhaustion policy is invalid")
    actions = raw["actions"]
    if not isinstance(actions, Mapping) or set(actions) != {"accept", "revise", "acquire"}:
        raise ValueError("native actions must name accept, revise and acquire")
    action_values = tuple(actions[key] for key in ("accept", "revise", "acquire"))
    if any(not isinstance(v, str) or not v for v in action_values) or len(set(action_values)) != 3:
        raise ValueError("native actions must be distinct nonempty strings")
    raw_roles = raw["roles"]
    kinds = ("perception", "solver", "reviewer", "planner")
    if not isinstance(raw_roles, Mapping) or set(raw_roles) != set(kinds):
        raise ValueError("native episode requires exactly perception, solver, reviewer and planner")
    tool_specs = values.get("phase_tools") or {}
    if not isinstance(tool_specs, Mapping):
        raise ValueError("phase_tools must be a mapping")
    roles = []
    for kind in kinds:
        row = raw_roles[kind]
        if not isinstance(row, Mapping) or set(row) != {"phase_id", "max_iterations"}:
            raise ValueError("each native role requires phase_id and max_iterations")
        phase_id, iterations = row["phase_id"], row["max_iterations"]
        if phase_id not in program.phase_names():
            raise ValueError("native role references an unknown program phase")
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 1:
            raise ValueError("role max_iterations must be positive")
        spec = tool_specs.get(phase_id)
        tools = ()
        if spec is not None:
            if kind not in {"reviewer", "planner"}:
                raise ValueError("only Reviewer and Planner may expose analytical tools")
            if spec.get("mode") != "native-tools" or spec.get("source_authority_role") != phase_id:
                raise ValueError("native role tools require exact phase source authority")
            tools = tuple(spec.get("allowed_tools", ()))
            if not tools or len(set(tools)) != len(tools):
                raise ValueError("native role tool names must be nonempty and unique")
        roles.append(NativeEpisodeRole(phase_id, kind, iterations, tools))
    phase_ids = tuple(role.phase_id for role in roles)
    if len(set(phase_ids)) != 4 or set(phase_ids) != set(program.phase_names()):
        raise ValueError("native roles must cover the program once each")
    if set(tool_specs) - set(phase_ids):
        raise ValueError("native tool phase is outside the episode")
    if any(phase.barrier for phase in program.phases):
        raise ValueError("conditional native episodes cannot declare whole-roster phase barriers")
    ceiling = roles[0].max_iterations + (revisions + 1) * sum(r.max_iterations for r in roles[1:])
    if program.max_contacts != ceiling:
        raise ValueError("program contact ceiling must equal the bounded native graph ceiling")
    return NativeEpisodeConfig(
        raw["episode_id"],
        revisions,
        action_values,
        tuple(roles),
        ceiling,
        exhaustion_policy,
    )
