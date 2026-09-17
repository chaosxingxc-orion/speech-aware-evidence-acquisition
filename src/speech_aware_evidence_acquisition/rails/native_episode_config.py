"""Configuration and immutable callback binding for the public native role graph."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .native_tool_authority import (
    NativeToolAuthorityError,
    validate_native_call_rejection,
)

PLANNER_ACTION_RESPONSE_FORMAT_ID = "saea-native-planner-action-v1"


#: Keys a Solver ``decoding_overrides`` block must carry, exactly.
SOLVER_DECODING_OVERRIDE_KEYS = frozenset({"temperature", "seed_offset"})
#: Keys a Solver ``commit`` block must carry, exactly.
SOLVER_COMMIT_KEYS = frozenset({"policy", "min_support", "similarity_threshold"})


@dataclass(frozen=True)
class NativeEpisodeRole:
    phase_id: str
    role_kind: str
    max_iterations: int
    tool_names: tuple[str, ...]
    history_scope: str = "full"
    # E2 (SLURP v2 base program M2): grouped Solver sampling. ``samples`` is
    # the number of distinct pinned-seed contacts made for one Solver visit
    # (default 1, today's behaviour); ``decoding_overrides``/``commit`` are
    # required together exactly when ``samples >= 2`` and forbidden
    # otherwise, so a samples-1 config carries none of this and validates
    # byte-identically to before this field existed.
    samples: int = 1
    decoding_overrides: Mapping[str, object] | None = None
    commit: Mapping[str, object] | None = None

    def __post_init__(self):
        if not isinstance(self.history_scope, str) or self.history_scope not in {
            "full", "latest-solver-and-local-tools",
        }:
            raise ValueError("native role history scope is invalid")
        if self.history_scope != "full" and self.role_kind != "reviewer":
            raise ValueError("only Reviewer may restrict history to the latest Solver")
        if (
            isinstance(self.samples, bool)
            or not isinstance(self.samples, int)
            or not 1 <= self.samples <= 8
        ):
            raise ValueError("solver samples must be an integer between 1 and 8")
        if self.role_kind != "solver" and (
            self.samples != 1
            or self.decoding_overrides is not None
            or self.commit is not None
        ):
            raise ValueError("only the Solver role may declare grouped sampling")
        if self.samples == 1:
            if self.decoding_overrides is not None:
                raise ValueError("decoding_overrides requires samples >= 2")
            if self.commit is not None:
                raise ValueError("commit is forbidden when samples == 1")
            return
        if (
            not isinstance(self.decoding_overrides, Mapping)
            or set(self.decoding_overrides) != SOLVER_DECODING_OVERRIDE_KEYS
        ):
            raise ValueError(
                "samples >= 2 requires decoding_overrides with exactly "
                "temperature and seed_offset"
            )
        temperature = self.decoding_overrides["temperature"]
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not 0 < temperature <= 2
        ):
            raise ValueError("decoding_overrides.temperature must be in (0, 2]")
        seed_offset = self.decoding_overrides["seed_offset"]
        if (
            isinstance(seed_offset, bool)
            or not isinstance(seed_offset, int)
            or seed_offset < 0
        ):
            raise ValueError("decoding_overrides.seed_offset must be a nonnegative integer")
        if not isinstance(self.commit, Mapping) or set(self.commit) != SOLVER_COMMIT_KEYS:
            raise ValueError(
                "samples >= 2 requires a commit block with exactly policy, "
                "min_support and similarity_threshold"
            )
        policy_id = self.commit["policy"]
        if not isinstance(policy_id, str) or not policy_id:
            raise ValueError("commit.policy must be a non-empty string")
        # Function-local: importing rails.commit_policies is what POPULATES
        # core.base.COMMIT_POLICIES (the registration lives beside the
        # implementation, in the one canonical policy-registration site), and
        # this module deliberately does not import rails.commit_policies at
        # module scope (it would be an import cycle: commit_policies needs
        # nothing from here, but the light-import discipline this package
        # follows elsewhere keeps registration imports function-local).
        from . import commit_policies as _commit_policies  # noqa: PLC0415, F401 (registration)
        from ..core.base import COMMIT_POLICIES, CoreError  # noqa: PLC0415

        try:
            COMMIT_POLICIES.resolve(policy_id)
        except CoreError as error:
            raise ValueError(f"commit.policy is invalid: {error}") from error
        min_support = self.commit["min_support"]
        if (
            isinstance(min_support, bool)
            or not isinstance(min_support, int)
            or not 1 <= min_support <= self.samples
        ):
            raise ValueError("commit.min_support must be an integer between 1 and samples")
        similarity_threshold = self.commit["similarity_threshold"]
        if (
            isinstance(similarity_threshold, bool)
            or not isinstance(similarity_threshold, (int, float))
            or not 0 < similarity_threshold <= 1
        ):
            raise ValueError("commit.similarity_threshold must be in (0, 1]")


def select_native_role_history(
    *, role: NativeEpisodeRole, solver_phase_id: str, states, local_tool_result_ids,
):
    """Select exposed state without modifying the complete episode history.

    Keep original speech and supplied knowledge in the caller's base messages.
    The restricted view retains one current Solver draft and the current
    Reviewer's complete native call/result chain. Older role opinions and tool
    conversations are excluded; this is draft-visible, not draft-blind review.
    """
    if role.history_scope == "full":
        return states
    if not isinstance(local_tool_result_ids, (tuple, list)):
        raise ValueError("local history IDs must be an ordered sequence")
    ids = [state.state_id for state in states]
    if len(ids) != len(set(ids)) or len(local_tool_result_ids) != len(
        set(local_tool_result_ids)
    ):
        raise ValueError("role history contains duplicate IDs")
    positions = {value: index for index, value in enumerate(ids)}
    solver_indices = [
        i
        for i, state in enumerate(states)
        if state.state_kind == f"phase:{solver_phase_id}"
    ]
    if not solver_indices:
        raise ValueError("restricted Reviewer history requires a Solver draft")
    solver_index = solver_indices[-1]
    selected = {ids[solver_index]}
    encountered = []
    sources = set()
    cursor = 0
    while cursor < len(local_tool_result_ids):
        result_id = local_tool_result_ids[cursor]
        if result_id not in positions:
            raise ValueError("local tool history result is missing")
        result_index = positions[result_id]
        result = states[result_index]
        if result.state_kind != "tool-result":
            raise ValueError("local history ID does not name a tool result")
        try:
            document = json.loads(result.content)
            source_id = document.get("native_source_state_id")
        except (TypeError, ValueError, AttributeError) as error:
            raise ValueError("local tool history envelope is malformed") from error
        if not isinstance(source_id, str) or source_id not in positions:
            raise ValueError("local tool history source is missing")
        source_index = positions[source_id]
        if (
            states[source_index].state_kind != f"phase:{role.phase_id}"
            or not solver_index < source_index < result_index
            or source_id in sources
        ):
            raise ValueError("local tool history has a foreign, old or repeated source")
        if document.get("schema") == "saea-phase-tool-rejection-v1":
            try:
                authority, _selected_call = validate_native_call_rejection(document)
                calls = authority["original_assistant_message"]["tool_calls"]
                original_ids = [call["id"] for call in calls]
            except (NativeToolAuthorityError, KeyError, TypeError) as error:
                raise ValueError("local rejected tool batch is malformed") from error
            batch_ids = list(
                local_tool_result_ids[cursor : cursor + len(original_ids)]
            )
            if len(batch_ids) != len(original_ids):
                raise ValueError("local rejected tool batch is incomplete")
            batch_positions = []
            for offset, (batch_id, original_id) in enumerate(
                zip(batch_ids, original_ids, strict=True), start=1
            ):
                batch_position = positions.get(batch_id)
                if batch_position != source_index + offset:
                    raise ValueError(
                        "local rejected tool batch is omitted, reordered or interleaved"
                    )
                batch_state = states[batch_position]
                if batch_state.state_kind != "tool-result":
                    raise ValueError("local rejected tool batch contains a non-result")
                try:
                    batch_document = json.loads(batch_state.content)
                    batch_authority, batch_call = validate_native_call_rejection(
                        batch_document
                    )
                except (NativeToolAuthorityError, TypeError, ValueError) as error:
                    raise ValueError("local rejected tool batch is malformed") from error
                if (
                    batch_document.get("native_source_state_id") != source_id
                    or batch_authority != authority
                    or batch_call.get("id") != original_id
                ):
                    raise ValueError(
                        "local rejected tool batch mixes source or call identities"
                    )
                batch_positions.append(batch_position)
                selected.add(batch_id)
            selected.add(source_id)
            sources.add(source_id)
            encountered.extend(batch_positions)
            cursor += len(original_ids)
            continue
        if result_index != source_index + 1:
            raise ValueError("local tool history has a foreign, old or repeated source")
        sources.add(source_id)
        selected.update((source_id, result_id))
        encountered.append(result_index)
        cursor += 1
    if encountered != sorted(encountered):
        raise ValueError("local tool history result order differs")
    # The shared framework renderer verifies the full source authority and
    # exact call/result bytes; retain those artifacts verbatim for that check.
    return tuple(state for state in states if state.state_id in selected)


@dataclass(frozen=True)
class NativeEpisodeConfig:
    episode_id: str
    max_revisions: int
    actions: tuple[str, str, str]
    roles: tuple[NativeEpisodeRole, ...]
    max_contacts: int
    exhaustion_policy: str = "raise"
    refresh_action: str | None = None
    max_candidate_refreshes: int = 0
    local_tool_workers: int = 0
    reserve_final_report: bool = False
    finite_completion_policy: str = "raise"
    planner_output_format: str = "exact-text"
    role_context_json: str | None = None

    @property
    def terminal_actions(self) -> tuple[str, ...]:
        return self.actions[1:] + (() if self.refresh_action is None else (self.refresh_action,))

    @property
    def review_loop_enabled(self) -> bool:
        """Whether Reviewer/Planner actually run.

        The paired validation in :func:`load_native_episode_config` makes
        Reviewer's ``max_iterations`` the single reliable witness: it is 0
        exactly when Planner's is also 0 and ``max_revisions`` is 0.
        """
        return self.role("reviewer").max_iterations > 0

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
    optional_fields = {
        "exhaustion_policy",
        "candidate_refresh",
        "local_tool_execution",
        "tool_iteration_policy",
        "finite_completion_policy",
        "planner_output_format",
        "role_context",
        "review_loop",
    }
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
    finite_completion_policy = raw.get("finite_completion_policy", "raise")
    if (
        not isinstance(finite_completion_policy, str)
        or finite_completion_policy not in {"raise", "deliver-latest-or-abstain"}
    ):
        raise ValueError("native episode finite completion policy is invalid")
    planner_output_format = raw.get("planner_output_format", "exact-text")
    if planner_output_format not in {"exact-text", "json-action-v1"}:
        raise ValueError("native episode Planner output format is invalid")
    actions = raw["actions"]
    if not isinstance(actions, Mapping) or set(actions) != {"accept", "revise", "acquire"}:
        raise ValueError("native actions must name accept, revise and acquire")
    action_values = tuple(actions[key] for key in ("accept", "revise", "acquire"))
    if any(not isinstance(v, str) or not v for v in action_values) or len(set(action_values)) != 3:
        raise ValueError("native actions must be distinct nonempty strings")
    refresh_action, refreshes = None, 0
    if "candidate_refresh" in raw:
        refresh = raw["candidate_refresh"]
        if not isinstance(refresh, Mapping) or set(refresh) != {"action", "max_refreshes"}:
            raise ValueError("candidate_refresh requires action and max_refreshes")
        refresh_action, refreshes = refresh["action"], refresh["max_refreshes"]
        if (
            not isinstance(refresh_action, str) or not refresh_action.strip()
            or refresh_action in action_values
            or isinstance(refreshes, bool) or not isinstance(refreshes, int)
            or not 1 <= refreshes <= revisions
        ):
            raise ValueError("candidate_refresh needs a distinct action and a bounded revision allowance")
    local_workers = 0
    if "local_tool_execution" in raw:
        local_execution = raw["local_tool_execution"]
        if (
            not isinstance(local_execution, Mapping)
            or set(local_execution) != {"mode", "max_workers"}
            or local_execution["mode"] != "yield-model-slot"
            or isinstance(local_execution["max_workers"], bool)
            or not isinstance(local_execution["max_workers"], int)
            or not 1 <= local_execution["max_workers"] <= 8
        ):
            raise ValueError("local_tool_execution requires yield-model-slot and 1..8 workers")
        local_workers = local_execution["max_workers"]
    reserve_report = "tool_iteration_policy" in raw
    if reserve_report and raw["tool_iteration_policy"] != "reserve-final-report":
        raise ValueError("tool_iteration_policy must be reserve-final-report")
    raw_roles = raw["roles"]
    kinds = ("perception", "solver", "reviewer", "planner")
    if not isinstance(raw_roles, Mapping) or set(raw_roles) != set(kinds):
        raise ValueError("native episode requires exactly perception, solver, reviewer and planner")
    tool_specs = values.get("phase_tools") or {}
    if not isinstance(tool_specs, Mapping):
        raise ValueError("phase_tools must be a mapping")
    iterations_by_kind: dict[str, int] = {}
    for kind in kinds:
        row = raw_roles[kind]
        base_fields = {"phase_id", "max_iterations", "history_scope"}
        # Only the Solver row may carry grouped-sampling fields (E2, SLURP v2
        # base program M2); every other role keeps the historical shape.
        solver_fields = {"samples", "decoding_overrides", "commit"} if kind == "solver" else set()
        if (
            not isinstance(row, Mapping)
            or not {"phase_id", "max_iterations"} <= set(row)
            or set(row) - base_fields - solver_fields
        ):
            raise ValueError("each native role requires phase_id and max_iterations")
        if row["phase_id"] not in program.phase_names():
            raise ValueError("native role references an unknown program phase")
        iterations = row["max_iterations"]
        # 0 is provisionally accepted here (Reviewer/Planner only, when the
        # review loop is off); the paired cross-role check below is what
        # actually decides whether 0 is legal for this configuration.
        if isinstance(iterations, bool) or not isinstance(iterations, int) or iterations < 0:
            raise ValueError("role max_iterations must be positive")
        iterations_by_kind[kind] = iterations
    if iterations_by_kind["perception"] < 1 or iterations_by_kind["solver"] < 1:
        raise ValueError("role max_iterations must be positive")
    reviewer_iterations = iterations_by_kind["reviewer"]
    planner_iterations = iterations_by_kind["planner"]
    # The review loop (Reviewer + Planner + revisions) is either fully present
    # or fully absent; a partial shape (only one role at 0, or a nonzero
    # revision allowance with no role left to consume it) is refused rather
    # than silently interpreted as either intent.
    review_loop_disabled = reviewer_iterations == 0 or planner_iterations == 0
    if review_loop_disabled and (
        reviewer_iterations != 0 or planner_iterations != 0 or revisions != 0
    ):
        raise ValueError(
            "review loop off requires reviewer 0, planner 0 and max_revisions 0"
        )
    if not review_loop_disabled and (reviewer_iterations < 1 or planner_iterations < 1):
        raise ValueError("role max_iterations must be positive")
    # Fable E6 (2026-09-16, harness-admission v3, class 'episode'): an
    # OPTIONAL, VALIDATED marker for the module M0 actually is. The three
    # leaves above stay authoritative and required exactly as before this
    # field existed; the marker is a redundant, checked declaration of what
    # they already mean, refused here the moment it disagrees with them, so a
    # config can never carry a "review_loop": "on" label over a paired-off
    # shape or vice versa.
    review_loop_marker = raw.get("review_loop")
    if review_loop_marker is not None:
        if review_loop_marker not in ("on", "off"):
            raise ValueError("native_episode.review_loop must be 'on' or 'off'")
        expected_marker = "off" if review_loop_disabled else "on"
        if review_loop_marker != expected_marker:
            raise ValueError(
                "native_episode.review_loop is inconsistent with the reviewer/"
                "planner max_iterations and max_revisions it must agree with"
            )
    roles = []
    for kind in kinds:
        row = raw_roles[kind]
        phase_id, iterations = row["phase_id"], iterations_by_kind[kind]
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
        if reserve_report and tools and iterations < 2:
            raise ValueError("reserve-final-report requires at least two tool-role iterations")
        roles.append(NativeEpisodeRole(
            phase_id, kind, iterations, tools, row.get("history_scope", "full"),
            row.get("samples", 1), row.get("decoding_overrides"), row.get("commit"),
        ))
    phase_ids = tuple(role.phase_id for role in roles)
    if len(set(phase_ids)) != 4 or set(phase_ids) != set(program.phase_names()):
        raise ValueError("native roles must cover the program once each")
    if set(tool_specs) - set(phase_ids):
        raise ValueError("native tool phase is outside the episode")
    planner_phase = program.phase(next(role.phase_id for role in roles if role.role_kind == "planner"))
    if (
        planner_output_format == "json-action-v1"
        and planner_phase.response_format_id != PLANNER_ACTION_RESPONSE_FORMAT_ID
    ):
        raise ValueError(
            "json-action-v1 requires the registered Planner phase response format"
        )
    role_context_json = None
    if "role_context" in raw:
        from .role_context_binding import (
            role_context_source_format_id, validate_role_context_config,
        )

        if any(role.history_scope != "full" for role in roles):
            raise ValueError("role context compilation cannot combine with a history filter")
        role_context_json = validate_role_context_config(raw["role_context"])
        perception = next(role for role in roles if role.role_kind == "perception")
        if program.phase(perception.phase_id).response_format_id != role_context_source_format_id(role_context_json):
            raise ValueError("role context requires the registered Perception phase format")
    if any(phase.barrier for phase in program.phases):
        raise ValueError("conditional native episodes cannot declare whole-roster phase barriers")
    if refresh_action is not None:
        stores = values.get("knowledge_stores", {})
        if not isinstance(stores, Mapping):
            raise ValueError("candidate refresh knowledge_stores must be a mapping")
        for store in stores.values():
            if not isinstance(store, Mapping):
                raise ValueError("candidate refresh knowledge store must be a mapping")
            supplies = store.get("candidate_supply", {})
            if not isinstance(supplies, Mapping):
                raise ValueError("candidate refresh candidate_supply must be a mapping")
            for spec in supplies.values():
                if not isinstance(spec, Mapping):
                    raise ValueError("candidate refresh candidate supply must be a mapping")
                if (
                    spec.get("candidate_state_phase") == roles[0].phase_id
                    and spec.get("candidate_state_selection", "single") != "latest"
                ):
                    raise ValueError("candidate refresh requires latest candidate source selection")
    # E2 (SLURP v2 base program M2): the Solver's own contribution is
    # multiplied by its registered ``samples`` (1 for every role, and for
    # every pre-E2 config, which reduces this to the historical formula
    # exactly). Every other role's iterations are unchanged.
    per_revision = sum(
        r.max_iterations * r.samples if r.role_kind == "solver" else r.max_iterations
        for r in roles[1:]
    )
    ceiling = roles[0].max_iterations + (revisions + 1) * per_revision
    ceiling += refreshes * roles[0].max_iterations
    if program.max_contacts != ceiling:
        raise ValueError("program contact ceiling must equal the bounded native graph ceiling")
    return NativeEpisodeConfig(
        raw["episode_id"],
        revisions,
        action_values,
        tuple(roles),
        ceiling,
        exhaustion_policy,
        refresh_action,
        refreshes,
        local_workers,
        reserve_report,
        finite_completion_policy,
        planner_output_format,
        role_context_json,
    )
