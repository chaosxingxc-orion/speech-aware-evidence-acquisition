"""Configuration and immutable callback binding for the public native role graph."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .context_fit import parse_context_fit_policy
from .native_tool_authority import (
    NativeToolAuthorityError,
    validate_native_call_rejection,
)

PLANNER_ACTION_RESPONSE_FORMAT_ID = "saea-native-planner-action-v1"
SOLVER_TOOL_ACCESS_MODE = "bounded-slot-lookup-v1"
SOLVER_SLOT_TOOL = "saea-tool-knowledge-target-lookup-v1"


#: Keys a Solver ``decoding_overrides`` block must carry, exactly.
SOLVER_DECODING_OVERRIDE_KEYS = frozenset({"temperature", "seed_offset"})
#: Optional keys a Solver ``decoding_overrides`` block may add (VER-1a, 2026-10-10).
#: ``greedy_first`` (the literal ``true``): sample 0 of the grouped visit keeps
#: the fragment's own greedy decoding (temperature 0) and samples 1.. take the
#: registered temperature. Absent -- every config written before VER-1a -- every
#: sample takes the registered temperature, byte for byte as before.
SOLVER_DECODING_OVERRIDE_OPTIONAL_KEYS = frozenset({"greedy_first"})
#: Keys a Solver ``commit`` block must carry, exactly.
SOLVER_COMMIT_KEYS = frozenset({"policy", "min_support", "similarity_threshold"})

#: Cell RANKVIS (owner decision 171, 2026-09-27): the schema of an armed
#: ``native_episode.knowledge_value_rendering`` block, its exact key set and
#: its two orders. ``supplied-order`` is today's behaviour (the fuser's own
#: order: rank order for the associated-values fuser, lexicographic value-id
#: order for the supply-filter fuser); ``retrieval-rank`` re-orders each named
#: store's newly supplied values by the score of their best supporting facet.
KNOWLEDGE_VALUE_RENDERING_SCHEMA = "saea-knowledge-value-rendering-v1"
KNOWLEDGE_VALUE_RENDERING_KEYS = frozenset({"schema", "order", "rank_visible", "stores"})
KNOWLEDGE_VALUE_ORDERS = ("supplied-order", "retrieval-rank")


def parse_knowledge_value_rendering(
    block: object, *, values: Mapping, knowledge_index_armed: bool = False,
) -> str:
    """Validate ``native_episode.knowledge_value_rendering``; return its canonical text.

    Refused by name, before any contact: a non-object or a wrong key set; an
    unknown schema or order; a non-boolean ``rank_visible``; an empty,
    repeating or malformed ``stores`` list, or a store the composed config's
    ``knowledge_stores`` does not bind; a block that changes nothing
    (``supplied-order`` without ``rank_visible``), which is dead config; a
    visible rank over the SUPPLIED order, which would print a number that is
    not a retrieval rank on the supply-filter fuser's lexicographic block; and
    the key armed beside ``knowledge_index``, which replaces the very value
    rendering this key changes.
    """

    if not isinstance(block, Mapping) or set(block) != KNOWLEDGE_VALUE_RENDERING_KEYS:
        raise ValueError(
            "native_episode.knowledge_value_rendering must carry exactly "
            f"{sorted(KNOWLEDGE_VALUE_RENDERING_KEYS)}"
        )
    if block["schema"] != KNOWLEDGE_VALUE_RENDERING_SCHEMA:
        raise ValueError(
            "native_episode.knowledge_value_rendering.schema must be "
            f"{KNOWLEDGE_VALUE_RENDERING_SCHEMA!r}"
        )
    order = block["order"]
    if not isinstance(order, str) or order not in KNOWLEDGE_VALUE_ORDERS:
        raise ValueError(
            "native_episode.knowledge_value_rendering.order must be one of "
            f"{list(KNOWLEDGE_VALUE_ORDERS)}"
        )
    rank_visible = block["rank_visible"]
    if not isinstance(rank_visible, bool):
        raise ValueError("native_episode.knowledge_value_rendering.rank_visible must be a bool")
    if order == "supplied-order" and not rank_visible:
        raise ValueError(
            "native_episode.knowledge_value_rendering changes nothing at "
            "supplied-order without rank_visible; leave the key absent instead"
        )
    if rank_visible and order != "retrieval-rank":
        raise ValueError(
            "native_episode.knowledge_value_rendering.rank_visible requires order "
            "'retrieval-rank': a visible position over the supplied order is not a rank"
        )
    stores = block["stores"]
    if (
        not isinstance(stores, list)
        or not stores
        or any(not isinstance(store, str) or not store.strip() or "::" in store for store in stores)
        or len(set(stores)) != len(stores)
    ):
        raise ValueError(
            "native_episode.knowledge_value_rendering.stores must be a non-empty list "
            "of distinct store ids"
        )
    bound = values.get("knowledge_stores")
    if not isinstance(bound, Mapping) or set(stores) - set(bound):
        raise ValueError(
            "native_episode.knowledge_value_rendering.stores names store(s) the "
            f"composed config does not bind: {sorted(set(stores) - set(bound or {}))}"
        )
    if knowledge_index_armed:
        raise ValueError(
            "native_episode.knowledge_value_rendering cannot be armed beside "
            "native_episode.knowledge_index: the index replaces the value rendering"
        )
    return json.dumps(
        {
            "schema": KNOWLEDGE_VALUE_RENDERING_SCHEMA,
            "order": order,
            "rank_visible": rank_visible,
            "stores": list(stores),
        },
        sort_keys=True,
        separators=(",", ":"),
    )


#: E18 (2026-09-19, owner decisions 43-44): the SIXTH node's role kind. It is
#: kept out of the four-role tuple every ceiling and coverage check iterates
#: because it is OPTIONAL: a config that does not declare it composes exactly
#: the episode it composed before E18, down to the contact ceiling.
ACQUISITION_ROLE_KIND = "acquisition"


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
    # E2b (SLURP v2 base program M2 live wiring): an explicit
    # 'greedy-repeat' twin (docs/superpowers/specs/
    # 2026-09-16-slurp-v2-base-program-design.md section 4, item E2's
    # "N greedy repeats aggregated identically" control) is the ONLY way
    # decoding_overrides.temperature may be 0 -- every other samples>=2
    # config keeps E2's original temperature-in-(0, 2] requirement. The
    # twin measures batch-composition nondeterminism only (llama.cpp
    # greedy decoding is not bitwise reproducible across batch shapes);
    # its N pinned seeds are recorded custody, never a source of
    # diversity at temperature 0.
    twin: str | None = None
    # E18 (2026-09-19, owner decisions 43-44): the acquisition KINDS this node
    # may execute, as registered in ``rails.acquisition.ACQUISITION_KINDS``.
    # Declared LAST so every positional construction written before E18 --
    # and there are several, here and in the tests -- composes exactly the
    # role it always did. Empty for every role but ``acquisition``.
    acquisition_kinds: tuple[str, ...] = ()
    # Item E39 (2026-09-22): this role's own completion cap, composed into
    # ``decoding_params.max_tokens`` for its contacts only, at request time
    # (``reproduction.ojw.native_request.MeteredNativeSpeechRequest.prepare``)
    # and nowhere else -- the same seam item E2's Solver ``decoding_overrides``
    # are composed at, so the model fragment and the serving-session identity
    # never move. ``None`` -- every role of every config written before E39 --
    # leaves the request's own ``max_tokens`` exactly as the fragment declares
    # it, byte for byte. The loader refuses a cap wider than the serving
    # geometry's own output cap, because a role may only ever ask for LESS
    # than the geometry allows. Declared LAST so every positional construction
    # written before E39 -- here and in the tests -- composes exactly the role
    # it always did.
    max_completion_tokens: int | None = None
    # Item E42 (2026-09-25, Stage-3 family VAR-2): this node's SUPPLY-VARIANT
    # arm group -- a validated ``rails.supply_variants.SupplyVariantGroup`` --
    # or ``None``, which is every role of every config written before E42 and
    # composes exactly the role it always did. K arms at one node multiply that
    # node's visits exactly as ``samples`` does, and are refused together with
    # ``samples >= 2``: two fan-outs at one node would make the visit's ONE
    # contact batch ambiguous and its ceiling contribution the product of two
    # independently declared knobs. Declared LAST, for the same reason E39's
    # field is.
    supply_variants: object = None
    # Same-flight instrument, PHASE 2 (merge set C, design docs/superpowers/
    # specs/2026-09-28-same-flight-instrument-phase2-perception-variants-
    # design.md): this node's PERCEPTION-BRANCH group -- a validated
    # ``rails.supply_variants.PerceptionBranchGroup`` -- or ``None``, which is
    # every role of every config written before phase 2 and composes exactly
    # the role it always did. Perception-only, for the mechanical reason
    # section 3 states: it forks the FIRST phase itself, before any contact,
    # into K branches over one audio packet; refused beside
    # ``supply_variants`` (two fan-out mechanisms in one episode would make
    # the ceiling's extra-contact term ambiguous). Declared LAST, for the
    # same reason ``supply_variants`` is.
    perception_branches: object = None

    def __post_init__(self):
        if self.role_kind == ACQUISITION_ROLE_KIND:
            # The sixth node's seat. It answers nothing, routes nothing and
            # carries no analytical tool, so every knob of the four model
            # roles is refused here by name rather than silently ignored.
            if self.tool_names or self.samples != 1 or self.twin is not None:
                raise ValueError("the acquisition role carries no role knobs")
            if self.decoding_overrides is not None or self.commit is not None:
                raise ValueError("the acquisition role carries no role knobs")
            if self.supply_variants is not None:
                # Item E42: the sixth node answers nothing and delivers
                # nothing, so it has no draft whose construction could be
                # varied and no delivering arm to name.
                raise ValueError("the acquisition role carries no role knobs")
            if self.perception_branches is not None:
                # Phase 2, merge set C: the sixth node is not Perception and
                # has no first-phase seed of its own to fork.
                raise ValueError("the acquisition role carries no role knobs")
            if self.max_completion_tokens is not None:
                # Item E39: the sixth node answers nothing and, on every kind
                # registered today, spends no model contact at all, so it has
                # no completion to cap.
                raise ValueError("the acquisition role carries no role knobs")
            if self.history_scope != "full":
                raise ValueError("the acquisition role cannot restrict history")
            if (
                isinstance(self.max_iterations, bool)
                or not isinstance(self.max_iterations, int)
                or not 0 <= self.max_iterations <= 1
            ):
                raise ValueError(
                    "the acquisition role spends 0 or 1 model contacts per visit"
                )
            if not isinstance(self.acquisition_kinds, tuple) or not self.acquisition_kinds:
                raise ValueError("the acquisition role must declare its kinds")
            if len(set(self.acquisition_kinds)) != len(self.acquisition_kinds):
                raise ValueError("acquisition kinds must be unique")
            # Function-local for the same reason ``commit.policy``'s import
            # is: importing rails.acquisition is what POPULATES
            # core.base.ACQUISITION_POLICIES, and this module keeps its
            # registration imports function-local.
            from .acquisition import ACQUISITION_KINDS  # noqa: PLC0415

            unknown = [
                kind for kind in self.acquisition_kinds if kind not in ACQUISITION_KINDS
            ]
            if unknown:
                raise ValueError(f"unknown acquisition kinds {sorted(unknown)}")
            return
        if self.acquisition_kinds:
            raise ValueError("only the acquisition role may declare acquisition kinds")
        if self.max_completion_tokens is not None and (
            isinstance(self.max_completion_tokens, bool)
            or not isinstance(self.max_completion_tokens, int)
            or self.max_completion_tokens < 1
        ):
            # Item E39. The geometry bound is checked by the loader, which is
            # the only place that can see the serving geometry; the shape is
            # checked here, so a directly constructed role is refused too.
            raise ValueError("max_completion_tokens must be a positive integer or None")
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
            or self.twin is not None
        ):
            raise ValueError("only the Solver role may declare grouped sampling")
        if self.twin is not None and self.twin != "greedy-repeat":
            raise ValueError("solver twin, when given, must be 'greedy-repeat'")
        # Item E42 (2026-09-25): the SUPPLY-variant arm group. Solver-only for
        # the same reason grouped sampling is: the node this program varies is
        # the one whose output is DELIVERED, so an arm group anywhere else would
        # fan out a state the whole row is keyed on without delivering any of
        # its arms. Refused beside ``samples >= 2`` because two fan-outs at one
        # node make the visit's ONE contact batch ambiguous.
        if self.supply_variants is not None:
            from .supply_variants import SupplyVariantGroup  # noqa: PLC0415

            if self.role_kind != "solver":
                raise ValueError("only the Solver role may declare supply variants")
            if not isinstance(self.supply_variants, SupplyVariantGroup):
                raise ValueError(
                    "supply_variants must be a parsed "
                    "rails.supply_variants.SupplyVariantGroup"
                )
            if self.samples != 1:
                raise ValueError(
                    "supply_variants cannot combine with a grouped Solver visit "
                    "(roles.solver.samples >= 2): two fan-outs at one node make "
                    "the visit's one contact batch ambiguous and its ceiling "
                    "contribution the product of two independently declared knobs"
                )
            if self.max_iterations != 1:
                # One arm is one CONTACT: the runner binds a contact to its arm
                # by ``invocation index % arm count`` (the same mapping E2b uses
                # for its samples), which is only a bijection while one visit of
                # this node spends exactly one contact. A multi-iteration
                # (ReAct) node would put several contacts under one arm and
                # silently shift every later arm's identity, so the combination
                # is refused before any contact rather than mis-attributed.
                raise ValueError(
                    "supply_variants requires roles.solver.max_iterations 1: one "
                    "arm is one contact, and the arm of a contact is its "
                    "invocation index modulo the arm count"
                )
            if self.tool_names:
                raise ValueError(
                    "supply_variants cannot combine with role tool authority: a "
                    "tool call would spend a second contact under one arm"
                )
        # Same-flight instrument, PHASE 2 (merge set C): the PERCEPTION-BRANCH
        # group. Perception-only for the mechanical reason section 3 states: it
        # forks the FIRST phase itself, and no other role owns that seed. The
        # cross-role refusal beside a Solver ``supply_variants`` group is
        # checked once, at the whole-config level
        # (``load_native_episode_config``), because one role's own
        # ``__post_init__`` cannot see another role's fields.
        if self.perception_branches is not None:
            from .supply_variants import PerceptionBranchGroup  # noqa: PLC0415

            if self.role_kind != "perception":
                raise ValueError(
                    "only the Perception role may declare perception branches"
                )
            if not isinstance(self.perception_branches, PerceptionBranchGroup):
                raise ValueError(
                    "perception_branches must be a parsed "
                    "rails.supply_variants.PerceptionBranchGroup"
                )
            if self.max_iterations != 1:
                raise ValueError(
                    "perception_branches requires roles.perception.max_iterations "
                    "1: Perception has one visit per row and no refresh (design "
                    "section 3, 'Branch visits')"
                )
            if self.tool_names:
                raise ValueError(
                    "perception_branches cannot combine with role tool authority"
                )
        if self.samples == 1:
            if self.decoding_overrides is not None:
                raise ValueError("decoding_overrides requires samples >= 2")
            if self.commit is not None:
                raise ValueError("commit is forbidden when samples == 1")
            if self.twin is not None:
                raise ValueError("twin requires samples >= 2")
            return
        if (
            not isinstance(self.decoding_overrides, Mapping)
            or not SOLVER_DECODING_OVERRIDE_KEYS <= set(self.decoding_overrides)
            or not set(self.decoding_overrides)
            <= SOLVER_DECODING_OVERRIDE_KEYS | SOLVER_DECODING_OVERRIDE_OPTIONAL_KEYS
        ):
            raise ValueError(
                "samples >= 2 requires decoding_overrides with exactly "
                "temperature and seed_offset (and optionally greedy_first)"
            )
        if "greedy_first" in self.decoding_overrides:
            if self.decoding_overrides["greedy_first"] is not True:
                raise ValueError("decoding_overrides.greedy_first, when given, must be true")
            if self.twin is not None:
                raise ValueError(
                    "decoding_overrides.greedy_first cannot combine with a greedy-repeat "
                    "twin: the twin is already greedy on every sample"
                )
        temperature = self.decoding_overrides["temperature"]
        is_greedy_repeat_twin = self.twin == "greedy-repeat"
        if (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not (
                0 <= temperature <= 2 if is_greedy_repeat_twin else 0 < temperature <= 2
            )
        ):
            raise ValueError(
                "decoding_overrides.temperature must be in (0, 2], or 0 for an "
                "explicit twin: greedy-repeat Solver group"
                if is_greedy_repeat_twin
                else "decoding_overrides.temperature must be in (0, 2]"
            )
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
    # E8a (2026-09-17, Node Context Policy): the canonical text of a
    # ``native_episode.context_policy`` whose effective level is NOT raw.
    # An absent key, the literal ``"raw"`` and an all-raw object are ONE
    # thing here -- ``None`` -- so the OFF arm reaches the runtime as no
    # policy at all and renders the pre-policy request bytes.
    context_policy_json: str | None = None
    # E11 (2026-09-18, owner directive 26): the registered
    # ``core.base.DELIVERY_NORMALISERS`` id of the delivery-time node, or
    # None when ``native_episode.deliver_normaliser`` is absent -- which is
    # every config written before E11 and every OFF arm, so the delivered
    # bytes are then exactly the accepted Solver response's own.
    deliver_normaliser_id: str | None = None
    # E12 (2026-09-19, owner directive 26): the canonical text of an armed
    # ``native_episode.reviewer_audit``, or None when the key is absent --
    # which is every config written before E12 and every OFF arm, so the
    # ``reviewer:current-draft`` boundary then renders exactly its pre-E12
    # bytes and no other boundary is reachable by this key at all.
    reviewer_audit_json: str | None = None
    # E14 (2026-09-19, owner directive 26): the canonical text of an armed
    # ``native_episode.solver_hints``, or None when the key is absent --
    # which is every config written before E14 and every OFF arm, so the
    # ``solver:candidate-hypothesis`` boundary then renders exactly its
    # pre-E14 bytes and no other boundary is reachable by this key at all.
    solver_hints_json: str | None = None
    # E17 (2026-09-19, throughput lever L1): how the native ``tools`` array
    # is RENDERED across the contacts of one row. ``"per-role"`` -- the
    # default, every config written before E17 and every OFF arm -- sends
    # each role exactly the schemas of the tools it may call, so a
    # tool-bearing role's request carries the array and every other role's
    # does not. ``"constant"`` sends EVERY role the same array (the union of
    # the tool schemas any role of this episode may call, in one fixed
    # order), so the rendered system message -- which is where the
    # Qwen3-Omni chat template puts the tools block -- stops toggling inside
    # a row and the pinned slot's KV prefix survives the role handover.
    #
    # Rendering is not authority. ``"constant"`` changes no role's
    # ``tool_names``, no role's ``tool_choice`` and no rail: a role with no
    # authority still sends ``tool_choice`` ``"none"``, is advertised no
    # ability by the framework, and is still refused by
    # ``reproduction.ojw.native_roles._RoleAuthorityRail`` if it emits a
    # call.
    tool_schema_rendering: str = "per-role"
    # E18 (2026-09-19, owner decisions 43-44): the sixth node. ``None`` --
    # every config written before E18 and every OFF arm -- means the key
    # ``native_episode.acquisition`` is ABSENT, no acquisition role is
    # declared, no acquisition node is built and the Planner's ACQUIRE names
    # no registered action, which is exactly the E15 retained-row behaviour.
    # Armed, the three carry the node's seat, its registered policy id and
    # its per-row budget.
    acquisition_role: NativeEpisodeRole | None = None
    acquisition_policy_id: str | None = None
    acquisition_budget: Mapping[str, int] | None = None
    # E20 (2026-09-19, owner decision 45): what an OVER-LONG request does.
    # ``"raise"`` -- every config written before E20 and every OFF arm --
    # is the pre-E20 behaviour: a request wider than the live slot aborts
    # the flight at preflight or kills it at dispatch.
    # ``"compact-or-abstain"`` drops droppable blocks in the declared order
    # (``rails.context_fit.DROP_ORDER``) and, when even that is not enough,
    # retains the row under a ``context_compaction`` terminal disposition.
    # It renders NO request byte on a row that fits. Declared LAST so every
    # positional construction written before E20 -- here and in the tests --
    # composes exactly the config it always did.
    context_fit_policy: str = "raise"
    # Item E21 (the knowledge index, not the Earnings-21 carrier), 2026-09-19,
    # owner decisions 48 and 50: the canonical text of an
    # armed ``native_episode.knowledge_index``, or None when the key is
    # absent -- which is every config written before E21 and every OFF arm,
    # so the system message then carries exactly its pre-E21 contract fill
    # and the evidence block exactly the selected values' own full text.
    # Armed, the episode renders the released index into the CONSTANT prefix
    # and replaces the per-row value rendering with a pointer block plus a
    # bounded expansion. Declared LAST, for the same reason E20's field is.
    knowledge_index_json: str | None = None
    # Item E22 (the ReAct-exhaustion disposition, not the Earnings-22
    # carrier), 2026-09-19: what a TOOL role's EXHAUSTED ReAct loop does.
    # ``"raise"`` -- every config written before E22 and every OFF arm -- is
    # the pre-E22 behaviour: the role returned no answer, the graph refuses
    # it and the flight dies at that row, which is exactly how the
    # B8b-anchor arm lost 2,016 contacts on 2026-09-19.
    # ``"continue-without-answer"`` ends that visit with NO finding and lets
    # the row continue through the Planner and deliver as usual, recording a
    # ``react_exhaustion`` VISIT disposition. It renders NO request byte on a
    # row whose roles answer. Declared LAST, for the same reason E20's and
    # E21's fields are.
    react_exhaustion_policy: str = "raise"
    # Item E36b (2026-09-22, owner decisions 90 and 70): the findings-keyed
    # requery repair. ``None`` -- every config written before E36b, and every
    # armed acquisition that does not declare
    # ``acquisition.budget.max_items_per_acquisition`` -- means the key is
    # ABSENT, so ``FlightRuntime._acquisition_requery_binding`` keeps running
    # the pre-E36b re-query (re-filter the Solver's own already-supplied
    # selection; the flown B9a-rec fragment's exact, byte-reproducible
    # behaviour). Present, this is the validated
    # ``rails.acquisition.RetrievalPolicy.as_json()`` document, and its
    # ``budget.max_items_per_acquisition`` sibling is a positive integer: the
    # runtime then searches the WHOLE released composite snapshot instead of
    # the Solver's own already-supplied selection, scored by inverse document
    # frequency over that snapshot. The two keys are one module --
    # ``acquisition.retrieval`` present requires
    # ``acquisition.budget.max_items_per_acquisition`` present and vice
    # versa -- so a half-armed declaration is refused before any contact.
    # Declared LAST, for the same reason E20's and E21's fields are.
    acquisition_retrieval: Mapping[str, object] | None = None
    # Item E37 (owner decision 84), 2026-09-22: the Reviewer's verdict as a
    # closed set of primitives. ``None`` -- every config written before E37
    # and every OFF arm -- means ``native_episode.reviewer_verdict`` is
    # absent, the Reviewer's ``_ApplyRole`` branch parses nothing and writes
    # no ``reviewer_verdicts`` receipt mark. A non-empty string is the armed
    # vocabulary id -- today only
    # ``rails.review_primitives.REVIEW_PRIMITIVES_VOCABULARY`` -- and is
    # refused below when it names anything else. Declared LAST, for the same
    # reason E22's field is.
    reviewer_verdict_vocabulary: str | None = None
    # Item E39 (2026-09-22), after the E35 sub10 read: WHICH node's truncated
    # completion ends the episode under item E13's
    # ``finite_completion_policy``. ``"episode"`` -- every config written
    # before E39 and every sealed cell -- is the pre-E39 behaviour: ANY role's
    # truncated completion ends the row, so a truncated Perception note voids
    # a window the Solver had not yet answered (75 of 342 windows on the E35
    # sub10 system arm, 95.6 % of its extra error mass).
    # ``"answering-node"`` scopes the rule to the node that answers: a
    # ``length`` truncation on Perception, Reviewer, Planner or Acquisition
    # keeps the truncated text as that role's output and the episode
    # continues, and only the Solver's own truncation -- or a truncation that
    # leaves no Solver draft at all -- takes the E13 disposition. It renders
    # NO request byte on a row whose roles finish. Declared LAST, for the same
    # reason E20's, E21's and E22's fields are.
    finite_completion_scope: str = "episode"
    # Cell RANKVIS (owner decision 171, 2026-09-27): the canonical text of an
    # armed ``native_episode.knowledge_value_rendering``, or None when the key
    # is absent -- which is every config written before it and every OFF arm,
    # so the named stores' values keep their supplied order and render as
    # their own content, byte for byte. Armed, the runner re-orders each named
    # store's newly supplied values by retrieval rank at the supply step and
    # (``rank_visible``) prefixes each rendered value of a named store with
    # its 1-based rank inside that store's block. Declared LAST, for the same
    # reason E20's, E21's, E22's and E39's fields are.
    knowledge_value_rendering_json: str | None = None
    # Item E4 (2026-09-28, owner decision 185, "core-native targeted re-
    # listen"): the canonical text of an armed ``native_episode.relisten``
    # block (``rails.relisten.RelistenConfig.as_json``), or ``None`` when the
    # key is absent -- which is every config written before E4 and every OFF
    # arm, so the post-accept stage is then unreachable, the deliver
    # normaliser's own output is exactly the delivered text, and the ceiling
    # formula's relisten term is 0. Declared LAST, for the same reason
    # E20's, E21's, E22's, E39's and RANKVIS's fields are.
    relisten_json: str | None = None
    # Owner decisions 195/196 (2026-09-29, the evidence-consumption module,
    # migration steps 1-2): the canonical text of a declared
    # ``native_episode.consumption_module`` block, or ``None`` when the key is
    # absent -- which is every config written before it, so nothing here
    # moves a byte for them. Present, the loader has already proven that the
    # config's own policy blocks are exactly what the block compiles to
    # (``rails.consumption_module.verify_declared_module``); the block is a
    # verified DECLARATION and adds no runtime path. Declared LAST, for the
    # same reason every field above it is.
    consumption_module_json: str | None = None
    # Migration step 5 (design 2b.4): the profile whose ``CarrierHooks`` the
    # carrier-agnostic runner reaches carrier facts through (the decision
    # candidates a presentation contrasts, the candidate-list ceiling, the
    # delivered units re-listen targets), or ``None`` when the declared
    # ``carrier_lock_key`` has no hooks file. It renders no request byte.
    carrier_profile: str | None = None
    # Absent preserves historical raw Reviewer state bytes.
    review_handoff: str | None = None
    # Absent preserves historical Solver tool prohibition and request bytes.
    solver_tool_access: str | None = None

    @property
    def knowledge_value_rendering(self) -> dict[str, object] | None:
        """The armed ``knowledge_value_rendering`` block, or ``None``."""

        if self.knowledge_value_rendering_json is None:
            return None
        return json.loads(self.knowledge_value_rendering_json)

    @property
    def relisten(self):
        """Item E4: the armed, parsed ``rails.relisten.RelistenConfig``, or
        ``None`` when ``native_episode.relisten`` is absent."""

        if self.relisten_json is None:
            return None
        from .relisten import parse_relisten  # noqa: PLC0415

        return parse_relisten(json.loads(self.relisten_json))

    @property
    def role_completion_caps(self) -> dict[str, int]:
        """Item E39: ``{role phase id: max_completion_tokens}`` for the roles
        that declare one.

        Empty for every config written before E39, which is what makes the
        request-time composition unreachable and the decoding block
        byte-identical for every sealed cell.
        """

        return {
            role.phase_id: int(role.max_completion_tokens)
            for role in self.roles
            if role.max_completion_tokens is not None
        }

    @property
    def supply_variant_group(self):
        """Item E42: the Solver's declared arm group, or ``None``.

        ``None`` for every config written before E42, which is what makes every
        supply-variant branch of the runner, the request path and the seal
        unreachable and their bytes identical.
        """

        return self.role("solver").supply_variants

    @property
    def supply_variant_arm_count(self) -> int:
        """Item E42: the arm count one Solver visit fans out to; 1 when unarmed."""

        return _supply_variant_arm_count(self.role("solver"))

    @property
    def supply_variant_phase_id(self) -> str | None:
        """Item E42: the phase whose visits fan out into arms, or ``None``."""

        role = self.role("solver")
        return None if role.supply_variants is None else role.phase_id

    @property
    def perception_branch_group(self):
        """Same-flight instrument, PHASE 2 (merge set C): the Perception
        role's declared branch group, or ``None``.

        ``None`` for every config written before phase 2, which is what
        makes every Perception-branch branch of the runner, the request
        path and the seal unreachable and their bytes identical --
        :attr:`supply_variant_group`'s own twin.
        """

        return self.role("perception").perception_branches

    @property
    def perception_branch_phase_id(self) -> str | None:
        """Same-flight instrument, PHASE 2: the phase whose one visit fans
        out into branches, or ``None`` -- :attr:`supply_variant_phase_id`'s
        own twin."""

        role = self.role("perception")
        return None if role.perception_branches is None else role.phase_id

    @property
    def acquisition_enabled(self) -> bool:
        """Whether this episode builds the sixth node (E18)."""

        return self.acquisition_role is not None

    @property
    def max_acquisitions_per_row(self) -> int:
        """The acquisition VISIT allowance of one row; 0 when unarmed."""

        if self.acquisition_budget is None:
            return 0
        return int(self.acquisition_budget["max_acquisitions_per_row"])

    @property
    def acquisition_contact_budget(self) -> int:
        """The model CONTACTS one row's acquisitions may spend; 0 when unarmed
        and 0 for every model-free acquisition kind."""

        if self.acquisition_budget is None:
            return 0
        return int(self.acquisition_budget["contact_budget"])

    @property
    def max_items_per_acquisition(self) -> int | None:
        """Item E36b: the most items a findings-keyed re-query may return, or
        ``None`` when the key is absent (the pre-E36b re-query, unbounded by
        this knob -- it is bounded by ``rails.acquisition.MAX_ACQUIRED_ITEMS``
        the same way every acquisition kind already is)."""

        if self.acquisition_budget is None:
            return None
        value = self.acquisition_budget.get("max_items_per_acquisition")
        return None if value is None else int(value)

    @property
    def constant_tool_names(self) -> tuple[str, ...] | None:
        """The one ordered tool-name array every role renders under
        ``tool_schema_rendering`` ``"constant"``, or ``None`` under
        ``"per-role"``.

        :func:`load_native_episode_config` refuses a ``"constant"`` episode
        whose tool-bearing roles do not all declare the SAME ordered
        ``tool_names``, so the first tool-bearing role's array IS the union,
        and a role that already carries tools renders byte-identically to
        the ``"per-role"`` arm. Only the tool-free roles gain the block.
        """

        if self.tool_schema_rendering != "constant":
            return None
        for role in self.roles:
            if role.tool_names:
                return role.tool_names
        return None

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
    # E8a: the repository root a declared ``context_policy`` reads its
    # committed, hash-pinned templates from (``configs/probes/ncp_*.txt``).
    # Required exactly when ``config.context_policy_json`` is not None;
    # every other binding leaves it None, byte-identically to before.
    repo_root: object = None
    # E14: the controlled data root a declared ``solver_hints`` reads its
    # RELEASED scenario-hints view from. Required exactly when
    # ``config.solver_hints_json`` is not None; every other binding leaves
    # it None, byte-identically to before.
    data_root: object = None
    # E18: the flight-owned, model-free knowledge re-query one
    # ``knowledge-requery`` acquisition runs -- the same seam
    # ``supply_for_phase`` is, and for the same reason: the runner never
    # reaches for a store of its own. Called as
    # ``(phase_id, filters, exclude_value_ids, scope, context) ->
    # Sequence[rails.acquisition.AcquiredItem]``. Required exactly when that
    # kind is the armed acquisition policy; every other binding leaves it
    # None, byte-identically to before.
    acquisition_requery: Callable | None = None
    # E20 (2026-09-19, owner decision 45): the live serving budget a
    # dispatch-time context-fit check measures each REALISED request
    # against. Required exactly when ``config.context_fit_policy`` is
    # ``"compact-or-abstain"``; every other binding leaves it None and the
    # dispatch path is byte-identical to its pre-E20 self.
    context_fit_budget: "ContextFitBudget | None" = None
    # E21 (2026-09-19, owner decisions 48 and 50): the flight-owned
    # knowledge-INDEX binding -- the loaded, hash-verified
    # ``rails.knowledge_index.KnowledgeIndexTable``, its resolved
    # ``IndexPlan`` and the row selector that turns one row's own Perception
    # candidates, retrieved exemplars and bound slot types into a
    # ``RowSelection``. The same seam ``supply_for_phase`` and
    # ``acquisition_requery`` are, and for the same reason: the runner never
    # reaches for a store of its own. Required exactly when
    # ``config.knowledge_index_json`` is not None; every other binding leaves
    # it None, byte-identically to before.
    knowledge_index: object = None
    # Item E42 (2026-09-25, Stage-3 family VAR-2): ONE arm's own resolved
    # knowledge supply. The same flight-owned seam ``supply_for_phase``,
    # ``acquisition_requery`` and ``knowledge_index`` are, and for the same
    # reason: the runner never reaches for a store of its own. Called as
    # ``(arm_id, phase_id, context) -> rails.controllers.PhaseSupply | None``
    # and answered by the flight from a router built over the SAME released,
    # pinned stores and the SAME composite snapshot as the delivering arm's,
    # with only that arm's declared selection knobs re-capped. Required exactly
    # when some role declares ``supply_variants``; every other binding leaves it
    # None, byte-identically to before. Declared LAST, for the same reason
    # E20's, E21's and E36's fields are.
    supply_variant_for_phase: Callable | None = None

    # Optional flight-owned complete-policy selector. No cell loader activates
    # this engineering seam until action/source/seal admission is implemented.
    # The shared graph still runs each selected binding from start to delivery.
    system_episode_policy: object = None
    # Optional source-bound interpretation of this episode's original
    # Perception and actual exemplar selection. Shared by all downstream roles.
    candidate_proposal_for_context: Callable | None = None
    # Owner decision 159 (2026-09-27): the dispatcher slot-fill switches
    # (``rails.dispatch_slot_fill.DispatchSlotFill``). Scheduling only -- no
    # request, state, output or trace byte depends on it. None, the value of
    # every committed configuration, leaves the dispatch exactly as it was.
    slot_fill: object = None
    # Same-flight instrument, PHASE 2 (merge set C, design docs/superpowers/
    # specs/2026-09-28-same-flight-instrument-phase2-perception-variants-
    # design.md section 3, "Branch seeds"): every declared Perception
    # branch's own PRE-FLIGHT, whole-roster first-phase seed --
    # ``{branch_id: {sample_id: (value_id, ...)}}`` -- flight-owned exactly
    # as ``supply_variant_for_phase`` is, and computed the same way
    # (:meth:`core.flight.runtime.FlightRuntime._perception_branch_seeds`).
    # ``None`` -- and therefore byte-identical to the pre-phase-2 tree --
    # unless ``roles.perception.branches`` is declared. Declared LAST, for
    # the same reason ``supply_variant_for_phase``'s field is.
    perception_branch_seeds: Mapping[str, Mapping[str, tuple]] | None = None
    # Same-flight instrument, PHASE 2, "What to build" item 1: every
    # declared Perception branch's own pinned, loaded, verified contrast-pair
    # table -- ``{branch_id: Mapping[frozenset[str], Mapping[str, object]]}``
    # -- flight-owned exactly as ``perception_branch_seeds`` is and computed
    # once, before any contact
    # (:meth:`core.flight.runtime.FlightRuntime._perception_contrast_pairs_
    # for_group`). ``None`` -- and therefore byte-identical to the tree
    # before this table existed -- unless some declared branch carries a
    # ``contrast_pairs`` pin. Declared LAST, after ``perception_branch_
    # seeds``, for the same reason that field is.
    perception_contrast_pairs: Mapping[str, Mapping] | None = None
    # NX programme E1 (2026-10-09, node-template arms): ``{arm_id: material
    # builder}`` for every arm of a template group that declares an
    # ``instruction_template`` -- each builder is the flight's own
    # ``material_for_phase`` with ONLY that arm's pinned template swapped in
    # (``core.flight.runtime.FlightRuntime._template_variant_materials``),
    # after the template's bytes were hashed against the declared sha256.
    # None -- and therefore byte-identical to the pre-programme tree -- unless
    # ``roles.solver.template_variants`` is declared. Declared LAST, for the
    # same reason the two fields above are.
    template_variant_materials: Mapping[str, Callable] | None = None
    # LEVEL 2 Perception-branch Solver supply (2026-10-09, the level-2 render
    # defect fix; docs/readiness/2026-10-09-slurp-psv-level2-render-defect-v1.md):
    # ``(*, branch_id, phase_id, context) -> rails.controllers.PhaseSupply |
    # None``, answered by the flight from a router built over the SAME
    # released, pinned stores as the delivering router (one independent router
    # per non-A, non-twin branch), so a branch's own first-visit Solver
    # contact re-resolves its candidate supply from ITS OWN note. Required
    # exactly when a level-2 branch group is declared beside a Solver
    # ``supply_for_phase``; every other binding leaves it None, byte-
    # identically to before. Declared LAST, after ``template_variant_
    # materials``, for the same reason that field is.
    perception_branch_solver_supply: Callable | None = None
    # Optional execution envelope, outside the policy dataclass so an absent
    # factor preserves existing whole-policy hashes and request semantics.
    prefix_slots: object = None
    node_batch: object = None
    node_pipeline: object = None
    workflow_panel: object = None
    # Thinking-core harness knobs (decision 283 A): the composed config's per-node ``thinking_policy`` map, keyed by role kind,
    # or None -- byte-identical to before. Resolved per contact at the request-composition seam.
    thinking_policy: Mapping[str, object] | None = None


@dataclass(frozen=True)
class ContextFitBudget:
    """E20: what the live slot allows one realised request, and how to count it.

    ``slot_tokens`` is the LIVE per-slot token limit of the session this
    flight runs on -- the same number ``serve()`` turns into ``-c`` divided
    by ``-np``, and the same one E17 bound the preflight budget to.
    ``reserve_tokens`` is the operational reserve
    (``rails.context_budget.serving_bound_reserve_tokens``) and
    ``completion_ceiling`` the generation cap this cell sends; together they
    are what a prompt may NOT use.

    ``token_counter`` maps exact request bytes to exact tokens. A real
    flight binds the resident server's own tokenizer; a test binds a
    deterministic counter. This rail never tokenizes anything itself.
    """

    slot_tokens: int
    reserve_tokens: int
    completion_ceiling: int
    token_counter: Callable
    special_token_reserve: int = 2

    def __post_init__(self) -> None:
        for name in (
            "slot_tokens", "reserve_tokens", "completion_ceiling",
            "special_token_reserve",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"context fit {name} must be a nonnegative integer")
        if self.slot_tokens <= 0:
            raise ValueError("context fit slot_tokens must be positive")
        if not callable(self.token_counter):
            raise ValueError("context fit token_counter must be callable")

    @property
    def prompt_limit_tokens(self) -> int:
        """What one request's PROMPT may occupy, in tokens.

        The live slot minus the operational reserve, the completion ceiling
        and the registered special-token reserve. Never below 1: a budget
        whose arithmetic leaves no room at all would refuse every request,
        including ones the physical slot holds.
        """

        return max(
            1,
            self.slot_tokens
            - self.reserve_tokens
            - self.completion_ceiling
            - self.special_token_reserve,
        )


#: Item E39 (2026-09-22): the two scopes ``native_episode.
#: finite_completion_scope`` may name. ``"episode"`` is the default and the
#: pre-E39 behaviour.
FINITE_COMPLETION_SCOPES = ("episode", "answering-node")


def _serving_geometry_max_tokens(values: Mapping) -> int | None:
    """Resolve the actual request output cap for every role admission path.

    A registered request-only max_tokens override takes precedence, with the
    shared decoding validation. Without it, preserve historical explicit
    serving_geometry precedence over decoding_params. Missing positive caps
    return None and are refused when a role explicitly declares its own cap.
    """

    # A request-only output override governs both raw preflight and live
    # dispatch. Resolve it through the shared validator; unrelated overrides
    # retain the historical explicit-geometry precedence below.
    overrides = values.get("request_decoding_overrides")
    if isinstance(overrides, Mapping) and "max_tokens" in overrides:
        from ..core.config import effective_request_decoding_params

        return int(effective_request_decoding_params(values)["max_tokens"])

    for block in ("serving_geometry", "decoding_params"):
        holder = values.get(block)
        if isinstance(holder, Mapping):
            value = holder.get("max_tokens")
            if not isinstance(value, bool) and isinstance(value, int) and value > 0:
                return value
    return None


def _validate_thinking_group_against_values(group, values: Mapping) -> None:
    """NX-T R1: resolve every arm's per-node policy against the composed fragment, before any contact.

    The group must sit on a reasoning (Thinking) fragment; each arm's per-node override must resolve through
    ``core.reasoning_knobs.resolve_node_decoding`` inside the serving geometry's output cap, and no arm's ``max_tokens`` may
    exceed the group's fit ``completion_ceiling`` (the per-contact context-fit gate then runs on each arm's REAL request).
    """

    from ..core.reasoning_knobs import (  # noqa: PLC0415
        ReasoningKnobError, fold_into_decoding, is_thinking_fragment, resolve_node_decoding,
    )

    if not is_thinking_fragment(values):
        raise ValueError(
            "roles.perception.thinking_variants is valid only on a reasoning fragment (reasoning_content_guard)"
        )
    folded = fold_into_decoding(values) or values
    decoding = folded.get("decoding_params")
    base = dict(decoding) if isinstance(decoding, Mapping) else {}
    geometry = _serving_geometry_max_tokens(values)
    ceiling = group.fit_estimate.completion_ceiling
    base_cap = base.get("max_tokens")
    if isinstance(base_cap, int) and base_cap > ceiling:
        raise ValueError(
            f"roles.perception.thinking_variants fit_estimate.completion_ceiling {ceiling} is below the delivering arm's "
            f"max_tokens {base_cap}"
        )
    for branch in group.branches:
        if branch.thinking_policy is None:
            continue
        for kind, entry in branch.thinking_policy.items():
            try:
                resolved = resolve_node_decoding(base, {kind: entry}, kind, cap=geometry)
            except ReasoningKnobError as error:
                raise ValueError(
                    f"roles.perception.thinking_variants arm {branch.branch_id!r} {kind} policy does not resolve: {error}"
                ) from error
            if resolved["max_tokens"] > ceiling:
                raise ValueError(
                    f"roles.perception.thinking_variants arm {branch.branch_id!r} {kind} max_tokens {resolved['max_tokens']} "
                    f"exceeds the group's fit completion_ceiling {ceiling}"
                )


def _supply_variant_arm_count(role: NativeEpisodeRole) -> int:
    """Item E42: this role's declared arm count, or 1 when it declares none.

    One function, read by the ceiling formula in
    :func:`load_native_episode_config` and by
    :attr:`NativeEpisodeConfig.supply_variant_arm_count`, so "how many contacts
    an arm group costs" has exactly one definition.
    """

    group = role.supply_variants
    return 1 if group is None else int(group.arm_count)


def _carrier_profile(values: Mapping[str, object]) -> str | None:
    """The declared carrier's hooks profile, or ``None`` (no hooks file)."""

    from .consumption_module import carrier_hooks_for_lock_key  # noqa: PLC0415

    hooks = carrier_hooks_for_lock_key(values.get("carrier_lock_key"))
    return None if hooks is None else hooks.profile


def _carrier_max_decision_candidates(values: Mapping[str, object]) -> int:
    """The declared carrier's ``max_decision_candidates`` hook, or 0."""

    from .consumption_module import carrier_hooks_for_lock_key  # noqa: PLC0415

    hooks = carrier_hooks_for_lock_key(values.get("carrier_lock_key"))
    if hooks is None or hooks.max_decision_candidates is None:
        return 0
    return int(hooks.max_decision_candidates())


def _module_delivering_axes(raw: Mapping[str, object]) -> tuple[str, ...]:
    """The delivering-branch axes a declared consumption-module block admits
    (``rails.consumption_module.delivered_perception_axes``); ``()`` when the
    config declares no module block -- every hand-written config."""

    if "consumption_module" not in raw:
        return ()
    from .consumption_module import delivered_perception_axes  # noqa: PLC0415

    return delivered_perception_axes(raw["consumption_module"])


def load_native_episode_config(
    values: Mapping, program, *, allow_subceiling: bool = False,
) -> NativeEpisodeConfig | None:
    """Require explicit role limits, role-local tool authority and a graph ceiling.

    THE CONTACT CEILING, stated once (E1's formula, extended by E2, E8b and
    E18; ``program.max_contacts`` must equal it exactly)::

        ceiling = perception.max_iterations
                + (max_revisions + 1) * per_revision
                + max_candidate_refreshes * perception.max_iterations
                + max_acquisitions_per_row * acquisition.max_iterations

        per_revision = solver.max_iterations * solver.samples * solver.arms
                     + reviewer.max_iterations
                     + planner.max_iterations
                     + cleaning contacts per revision

    where ``solver.arms`` (item E42) is the Solver's registered supply-variant
    arm count and is 1 for every config that declares no arm group.

    Term by term: Perception runs once at the head of the row (E1); each of
    the ``max_revisions + 1`` rounds spends one Solver visit -- ``samples``
    contacts when the visit is grouped (E2) -- plus the Reviewer's and the
    Planner's iterations, plus one cleaning contact per contact of each
    ``cleaned`` boundary's consumer role (E8b); each candidate refresh
    re-enters Perception once; and -- E18 -- each acquisition VISIT spends
    the acquisition role's own contact allowance, which is 0 for every
    model-free kind (``knowledge-requery``, ``tool-acquire``) and 1 for the
    kind that re-observes (``speech-reobserve``). With no acquisition key the
    last term is 0 and the formula is exactly its pre-E18 self.

    ITEM E36b (2026-09-22, owner decisions 90 and 70): two OPTIONAL keys
    inside an armed ``native_episode.acquisition`` block, spending no
    contact and moving no term of the ceiling above.

    * ``acquisition.budget.max_items_per_acquisition`` (int, >= 1, bounded by
      ``rails.acquisition.MAX_ACQUIRED_ITEMS``) -- the most items one
      ``knowledge-requery`` visit may return.
    * ``acquisition.retrieval`` -- ``{"policy": <a registered id in
      rails.acquisition.RETRIEVAL_POLICY_IDS>, "min_token_chars": <int, >=
      1>, "max_document_frequency": <float in (0, 1]>,
      "exclude_visible_tokens": <bool>}`` -- the findings-keyed search rule
      the requery ranks by.

    Both keys are ONE module: declaring either without the other is refused.
    Absent (both keys), the requery keeps its pre-E36b behaviour byte for
    byte -- re-running the Solver's own already-prepared supply and
    restricting it to the state tokens, which the 2026-09-22 B9a-rec read
    found is empty by construction on every row (the exclusion set and the
    selection set are the same ids). Present, ``core.flight.runtime.
    FlightRuntime._acquisition_requery_binding`` instead searches the WHOLE
    released composite snapshot the flight bound, scored by inverse document
    frequency over that snapshot's tokens, zero model contacts either way.
    """
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
        "context_fit_policy",
        "react_exhaustion_policy",
        "finite_completion_scope",
        "planner_output_format",
        "role_context",
        "review_loop",
        "context_policy",
        "deliver_normaliser",
        "reviewer_audit",
        "solver_hints",
        "tool_schema_rendering",
        "acquisition",
        "knowledge_index",
        "reviewer_verdict",
        "knowledge_value_rendering",
        "relisten",
        "consumption_module",
        "review_handoff",
        "solver_tool_access",
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
    solver_access = raw.get("solver_tool_access")
    if "solver_tool_access" in raw and solver_access != SOLVER_TOOL_ACCESS_MODE:
        raise ValueError("solver_tool_access must be bounded-slot-lookup-v1 or absent")
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
    # Item E39 (2026-09-22): read exactly as E13's own key is -- absent means
    # the default ``"episode"`` (the pre-E39 whole-episode scope), and a third
    # value is refused here rather than reaching the graph.
    finite_completion_scope = raw.get("finite_completion_scope", "episode")
    if (
        not isinstance(finite_completion_scope, str)
        or finite_completion_scope not in FINITE_COMPLETION_SCOPES
    ):
        raise ValueError("native episode finite completion scope is invalid")
    # E20 (2026-09-19, owner decision 45). Parsed by the rail that owns the
    # mechanism, so the config surface and the runtime read one definition.
    context_fit_policy = parse_context_fit_policy(raw.get("context_fit_policy"))
    # Item E22 (the ReAct-exhaustion disposition, not the Earnings-22
    # carrier), 2026-09-19: read exactly as E13's key is -- absent means the
    # default ``"raise"``, and a third value is refused here rather than
    # reaching the graph.
    react_exhaustion_policy = raw.get("react_exhaustion_policy", "raise")
    if (
        not isinstance(react_exhaustion_policy, str)
        or react_exhaustion_policy not in {"raise", "continue-without-answer"}
    ):
        raise ValueError("native episode react exhaustion policy is invalid")
    # Item E37 (owner decision 84), 2026-09-22: the Reviewer's verdict as a
    # closed set of primitives. Absent -- every config written before E37 and
    # every OFF arm -- is None: the parse is unarmed. Present, the block must
    # name exactly the ONE registered vocabulary id; any other id, or any
    # other shape, is refused here, before any contact, rather than reaching
    # the graph as a silently-unarmed key.
    reviewer_verdict_vocabulary = None
    if "reviewer_verdict" in raw:
        from .review_primitives import REVIEW_PRIMITIVES_VOCABULARY  # noqa: PLC0415

        block = raw["reviewer_verdict"]
        if not isinstance(block, Mapping) or set(block) != {"vocabulary"}:
            raise ValueError(
                "native_episode.reviewer_verdict must be an object with exactly a "
                "'vocabulary' id"
            )
        reviewer_verdict_vocabulary = block["vocabulary"]
        if reviewer_verdict_vocabulary != REVIEW_PRIMITIVES_VOCABULARY:
            raise ValueError(
                f"native_episode.reviewer_verdict.vocabulary is "
                f"{reviewer_verdict_vocabulary!r}; the only registered vocabulary is "
                f"{REVIEW_PRIMITIVES_VOCABULARY!r}"
            )
    planner_output_format = raw.get("planner_output_format", "exact-text")
    if planner_output_format not in {"exact-text", "json-action-v1"}:
        raise ValueError("native episode Planner output format is invalid")
    # E17 (2026-09-19, throughput lever L1). Parsed here, cross-checked
    # against the composed roles below -- the shape check is cheap and the
    # authority check needs the roles.
    tool_schema_rendering = raw.get("tool_schema_rendering", "per-role")
    if (
        not isinstance(tool_schema_rendering, str)
        or tool_schema_rendering not in {"per-role", "constant"}
    ):
        raise ValueError(
            "native episode tool_schema_rendering must be 'per-role' or 'constant'"
        )
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
    # E18: the fifth role is OPTIONAL and is the ONLY key ``roles`` may carry
    # beyond the four. It is present exactly when ``native_episode.
    # acquisition`` is, checked below: a node with no policy and a policy
    # with no node are both refused rather than half-armed.
    acquisition_armed = "acquisition" in raw
    if not isinstance(raw_roles, Mapping) or set(raw_roles) != set(kinds) | (
        {ACQUISITION_ROLE_KIND} if ACQUISITION_ROLE_KIND in raw_roles else set()
    ):
        raise ValueError("native episode requires exactly perception, solver, reviewer and planner")
    if (ACQUISITION_ROLE_KIND in raw_roles) != acquisition_armed:
        raise ValueError(
            "native_episode.acquisition and roles.acquisition are one module: "
            "declare both or neither"
        )
    tool_specs = values.get("phase_tools") or {}
    if not isinstance(tool_specs, Mapping):
        raise ValueError("phase_tools must be a mapping")
    iterations_by_kind: dict[str, int] = {}
    # Item E39 (2026-09-22): the per-role completion caps, read in the same
    # pass the iterations are and bounded by the composed serving geometry.
    completion_caps_by_kind: dict[str, int | None] = {}
    geometry_max_tokens = _serving_geometry_max_tokens(values)
    # E21 (2026-09-19): the per-role pointer/expansion override table. It is
    # part of the ``native_episode.knowledge_index`` MODULE and is refused
    # without it, exactly as E18's ``roles.acquisition`` is refused without
    # ``native_episode.acquisition`` -- a node with no policy and a policy
    # with no node are both half-armed, and so is a budget override with no
    # index to budget.
    knowledge_index_armed = "knowledge_index" in raw
    for kind in kinds:
        row = raw_roles[kind]
        base_fields = {
            "phase_id", "max_iterations", "history_scope", "knowledge_index_budget",
            # Item E39 (2026-09-22): this role's own completion cap.
            "max_completion_tokens",
        }
        # Only the Solver row may carry grouped-sampling fields (E2, SLURP v2
        # base program M2); every other role keeps the historical shape.
        solver_fields = (
            # Item E42 (2026-09-25): ``supply_variants`` joins the Solver-only
            # row fields for the same reason ``samples`` is one -- it fans out
            # the delivering node's visit and nothing else may declare it.
            {"samples", "decoding_overrides", "commit", "twin", "supply_variants"}
            if kind == "solver" else set()
        )
        # Same-flight instrument, PHASE 2 (merge set C): ``branches`` joins the
        # Perception-only row fields for the same reason -- it forks the FIRST
        # phase's own visit and nothing else may declare it.
        perception_fields = {"branches", "thinking_variants", "sampling_variants"} if kind == "perception" else set()
        # Decision 338 (2026-10-19): ``sampling_variants`` is the Perception-only SAMPLING fan-out (Perception and/or Solver
        # samples per branch); one fan-out mechanism per node, so it cannot combine with the other declarations.
        if isinstance(row, Mapping) and "sampling_variants" in row:
            for other in ("branches", "template_variants", "supply_variants", "decoding_variants", "thinking_variants"):
                if other in row:
                    raise ValueError(
                        f"roles.{kind}.sampling_variants cannot combine with roles.{kind}.{other}: one fan-out mechanism per node"
                    )
        # NX-T R1 (2026-10-13): ``thinking_variants`` is a Perception-only fan-out of the per-node thinking policy; it is one
        # of the branch group's kinds, so it cannot combine with the other fan-out declarations of the node.
        if isinstance(row, Mapping) and "thinking_variants" in row:
            for other in ("branches", "template_variants", "supply_variants", "decoding_variants"):
                if other in row:
                    raise ValueError(
                        f"roles.{kind}.thinking_variants cannot combine with roles.{kind}.{other}: one fan-out mechanism per node"
                    )
        # NX programme E1 (2026-10-09): ``template_variants`` joins the row
        # fields of exactly the nodes ``rails.supply_variants.
        # TEMPLATE_VARIANT_NODES`` names (the Solver today). Declared on any
        # other node it is refused BY NAME rather than as an unknown key.
        if isinstance(row, Mapping) and "template_variants" in row:
            from .supply_variants import TEMPLATE_VARIANT_NODES  # noqa: PLC0415

            if kind not in TEMPLATE_VARIANT_NODES:
                raise ValueError(
                    f"roles.{kind}.template_variants is refused: a node-template "
                    f"arm group may sit only at {list(TEMPLATE_VARIANT_NODES)}"
                )
            if "supply_variants" in row:
                raise ValueError(
                    f"roles.{kind}.template_variants cannot combine with "
                    f"roles.{kind}.supply_variants: one fan-out mechanism per node"
                )
            if "branches" in row:
                raise ValueError(
                    f"roles.{kind}.template_variants cannot combine with "
                    f"roles.{kind}.branches: one fan-out mechanism per node"
                )
            solver_fields = solver_fields | {"template_variants"}
        # NX-T R4 (2026-10-18): ``decoding_variants`` -- the Solver-only node-DECODING arm
        # group (a sibling of ``template_variants``). Declared on any other node, or beside
        # another fan-out declaration, it is refused BY NAME.
        if isinstance(row, Mapping) and "decoding_variants" in row:
            from .supply_variants import DECODING_VARIANT_NODES  # noqa: PLC0415

            if kind not in DECODING_VARIANT_NODES:
                raise ValueError(
                    f"roles.{kind}.decoding_variants is refused: a node-decoding "
                    f"arm group may sit only at {list(DECODING_VARIANT_NODES)}"
                )
            for other in ("supply_variants", "template_variants", "branches", "thinking_variants"):
                if other in row:
                    raise ValueError(
                        f"roles.{kind}.decoding_variants cannot combine with "
                        f"roles.{kind}.{other}: one fan-out mechanism per node"
                    )
            solver_fields = solver_fields | {"decoding_variants"}
        if (
            not isinstance(row, Mapping)
            or not {"phase_id", "max_iterations"} <= set(row)
            or set(row) - base_fields - solver_fields - perception_fields
        ):
            raise ValueError("each native role requires phase_id and max_iterations")
        if row["phase_id"] not in program.phase_names():
            raise ValueError("native role references an unknown program phase")
        if "knowledge_index_budget" in row and not knowledge_index_armed:
            raise ValueError(
                "native_episode.knowledge_index and "
                "roles.<role>.knowledge_index_budget are one module: declare both "
                "or neither"
            )
        cap = row.get("max_completion_tokens")
        if cap is not None:
            # Item E39: shape here, and the GEOMETRY bound here too -- this is
            # the only place that can see the composed serving geometry, and a
            # cap wider than the geometry's own output cap is a cap that can
            # never bind. Refused before any contact, by name.
            if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
                raise ValueError(
                    "roles.<role>.max_completion_tokens must be a positive integer"
                )
            if geometry_max_tokens is None:
                raise ValueError(
                    "roles.<role>.max_completion_tokens requires a declared "
                    "serving_geometry.max_tokens or decoding_params.max_tokens"
                )
            if cap > geometry_max_tokens:
                raise ValueError(
                    "roles.<role>.max_completion_tokens must not exceed the serving "
                    f"geometry's own max_tokens ({geometry_max_tokens})"
                )
        completion_caps_by_kind[kind] = cap
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
    # Item E42 (2026-09-25, Stage-3 family VAR-2): the Solver's SUPPLY-variant
    # arm group, parsed HERE -- before any contact -- so a fragment can never
    # name a knob path this rail does not admit, re-cap a store it does not
    # declare, vary the pre-flight-seeded first phase, name zero or several
    # delivering arms, or declare a combination whose prompt-fit estimate
    # exceeds the live slot with the registered reserve. ``None`` for every
    # config written before E42, which leaves the ceiling below and every role
    # exactly as they were.
    supply_variant_group = None
    if "supply_variants" in raw_roles["solver"]:
        from .knowledge_stores import declared_alternate_release_relpaths
        from .supply_variants import SupplyVariantError, parse_supply_variants

        declared_stores = values.get("knowledge_stores")
        if declared_stores is not None and not isinstance(declared_stores, Mapping):
            raise ValueError("knowledge_stores must be a mapping")
        try:
            supply_variant_group = parse_supply_variants(
                raw_roles["solver"]["supply_variants"],
                phase_id=raw_roles["solver"]["phase_id"],
                first_phase_id=program.phase_names()[0],
                declared_stores=(
                    None if declared_stores is None else tuple(declared_stores)
                ),
                # Coordinator amendment, 2026-09-28: an arm's release_swap is
                # refused by name here when it names a release the store's
                # base config does not also declare under its own
                # ``alternates``.
                declared_alternate_relpaths=declared_alternate_release_relpaths(
                    declared_stores
                ),
            )
        except SupplyVariantError as error:
            raise ValueError(
                f"roles.solver.supply_variants is invalid: {error}"
            ) from error
        if knowledge_index_armed:
            # The index REPLACES the row's ``value:`` evidence blocks with a
            # pointer block plus a bounded expansion and appends its own system
            # suffix (item E21, ``rails.knowledge_index.apply_to_payload``). An
            # arm varies exactly those value blocks, so the two keys would each
            # be rewriting the other's output with only one of them in custody.
            # Refused by name until a cell needs it and its custody form is
            # designed.
            raise ValueError(
                "roles.solver.supply_variants cannot combine with "
                "native_episode.knowledge_index: the index replaces the very "
                "value blocks an arm varies"
            )
    # NX programme E1 (2026-10-09): the Solver's NODE-TEMPLATE arm group,
    # parsed HERE -- before any contact -- into the SAME group slot the supply
    # arm group fills (``roles.solver.supply_variants`` and ``template_variants``
    # are mutually exclusive), kind ``template``. Every arm renders the
    # delivering arm's own evidence and differs only in its pinned instruction
    # template, so the ceiling term, the contact batch, the receipt and the
    # bundle invariant I7v are the supply form's own.
    if "template_variants" in raw_roles["solver"]:
        from .supply_variants import SupplyVariantError, parse_template_variants

        solver_phase = raw_roles["solver"]["phase_id"]
        material = values.get("phase_material")
        locked_entry = material.get(solver_phase) if isinstance(material, Mapping) else None
        locked_template = (
            locked_entry.get("instruction_template")
            if isinstance(locked_entry, Mapping) else None
        )
        if not isinstance(locked_template, str):
            raise ValueError(
                "roles.solver.template_variants requires the node's own "
                f"phase_material[{solver_phase!r}].instruction_template: the "
                "delivering arm renders it"
            )
        try:
            supply_variant_group = parse_template_variants(
                raw_roles["solver"]["template_variants"],
                role_kind="solver", phase_id=solver_phase,
                locked_template=locked_template,
            )
        except SupplyVariantError as error:
            raise ValueError(
                f"roles.solver.template_variants is invalid: {error}"
            ) from error
        if knowledge_index_armed:
            raise ValueError(
                "roles.solver.template_variants cannot combine with "
                "native_episode.knowledge_index: the index appends to the system "
                "message every arm shares and has no per-arm custody form"
            )
    # NX-T R4 (2026-10-18, owner rulings 329 A / 332 A): the Solver's NODE-DECODING arm
    # group, parsed HERE -- before any contact -- into the SAME group slot (kind
    # ``decoding``). Every arm renders the delivering arm's own evidence and the node's own
    # locked template; a candidate arm overrides only the sampling parameters of its own
    # contact (applied at request composition, ``reproduction.ojw.native_request``).
    if "decoding_variants" in raw_roles["solver"]:
        from .supply_variants import SupplyVariantError, parse_decoding_variants

        locked_decoding = None
        try:
            from ..core.config import ConfigError, effective_request_decoding_params

            effective = effective_request_decoding_params(values)
            locked_decoding = dict(effective) if isinstance(effective, Mapping) else None
        except ConfigError:
            locked_decoding = None  # a config that cannot resolve its own decoding has none to compare
        try:
            supply_variant_group = parse_decoding_variants(
                raw_roles["solver"]["decoding_variants"],
                role_kind="solver", phase_id=raw_roles["solver"]["phase_id"],
                locked_decoding=locked_decoding,
            )
        except SupplyVariantError as error:
            raise ValueError(
                f"roles.solver.decoding_variants is invalid: {error}"
            ) from error
        if knowledge_index_armed:
            raise ValueError(
                "roles.solver.decoding_variants cannot combine with "
                "native_episode.knowledge_index: the index appends to the system "
                "message every arm shares and has no per-arm custody form"
            )
    # Same-flight instrument, PHASE 2 (merge set C, design docs/superpowers/
    # specs/2026-09-28-same-flight-instrument-phase2-perception-variants-
    # design.md): the Perception's own PERCEPTION-BRANCH group, parsed HERE
    # -- before any contact -- for the same reason the Solver's supply-variant
    # arm group is: a fragment can never name a knob path this rail does not
    # admit, an unregistered presentation, an out-of-range response-contract
    # bound, or a combination whose prompt-fit estimate exceeds the live slot
    # with the registered reserve. ``None`` for every config written before
    # phase 2, which leaves the ceiling below and every role exactly as they
    # were.
    perception_branch_group = None
    # NX programme E1, Perception node (2026-10-10, owner decision 239): the
    # Perception's NODE-TEMPLATE arm group, parsed HERE -- before any contact --
    # into the SAME level-2 branch group ``roles.perception.branches`` fills
    # (the two are mutually exclusive), each non-A, non-twin branch varying the
    # Perception instruction template only. The branch mechanism's contact
    # mapping, level-2 Solver render, receipt and ceiling term are used as is.
    if "template_variants" in raw_roles["perception"]:
        from .supply_variants import SupplyVariantError, parse_perception_template_variants

        perception_phase = raw_roles["perception"]["phase_id"]
        material = values.get("phase_material")
        locked_entry = material.get(perception_phase) if isinstance(material, Mapping) else None
        locked_template = (
            locked_entry.get("instruction_template")
            if isinstance(locked_entry, Mapping) else None
        )
        if not isinstance(locked_template, str):
            raise ValueError(
                "roles.perception.template_variants requires the node's own "
                f"phase_material[{perception_phase!r}].instruction_template: the "
                "delivering arm renders it"
            )
        try:
            perception_branch_group = parse_perception_template_variants(
                raw_roles["perception"]["template_variants"],
                phase_id=perception_phase, locked_template=locked_template,
            )
        except SupplyVariantError as error:
            raise ValueError(
                f"roles.perception.template_variants is invalid: {error}"
            ) from error
        if supply_variant_group is not None:
            raise ValueError(
                "roles.perception.template_variants cannot combine with a Solver "
                "supply_variants or template_variants group: two fan-out "
                "mechanisms in one episode make the ceiling's extra-contact term "
                "ambiguous"
            )
        if knowledge_index_armed:
            raise ValueError(
                "roles.perception.template_variants cannot combine with "
                "native_episode.knowledge_index: the index appends to the system "
                "message every arm shares and has no per-arm custody form"
            )
    # NX-T R1 (2026-10-13): the Perception's per-node THINKING-POLICY column, parsed HERE -- before any contact -- into the SAME
    # level-2 branch group slot (mutually exclusive with ``branches`` and ``template_variants``). Every arm renders the
    # delivering arm's own evidence and differs only in the thinking decoding of its own Perception and Solver contacts.
    if "thinking_variants" in raw_roles["perception"]:
        from .supply_variants import PerceptionBranchError, parse_perception_thinking_variants

        try:
            perception_branch_group = parse_perception_thinking_variants(
                raw_roles["perception"]["thinking_variants"],
                phase_id=raw_roles["perception"]["phase_id"],
            )
        except PerceptionBranchError as error:
            raise ValueError(f"roles.perception.thinking_variants is invalid: {error}") from error
        _validate_thinking_group_against_values(perception_branch_group, values)
        if supply_variant_group is not None:
            raise ValueError(
                "roles.perception.thinking_variants cannot combine with a Solver supply_variants or template_variants group: "
                "two fan-out mechanisms in one episode make the ceiling's extra-contact term ambiguous"
            )
        if knowledge_index_armed:
            raise ValueError(
                "roles.perception.thinking_variants cannot combine with native_episode.knowledge_index: the index appends to "
                "the system message every arm shares and has no per-arm custody form"
            )
    # Decision 338 (2026-10-19): the SAMPLING column, parsed HERE -- before any contact -- into the same level-2 branch group
    # slot. A branch fans out Perception samples (merged into its shortlist) and/or Solver samples (committed into its answer);
    # the delivering branch and the twin declare neither, so the delivery-time v4g rule below stays scoped to the delivering
    # branch (it is refused only beside a role-wide grouped visit, ``roles.solver.samples >= 2``, which this column never sets).
    if "sampling_variants" in raw_roles["perception"]:
        from .supply_variants import PerceptionBranchError, parse_perception_sampling_variants

        try:
            perception_branch_group = parse_perception_sampling_variants(
                raw_roles["perception"]["sampling_variants"],
                phase_id=raw_roles["perception"]["phase_id"],
            )
        except PerceptionBranchError as error:
            raise ValueError(f"roles.perception.sampling_variants is invalid: {error}") from error
        shortlist_cap = _carrier_max_decision_candidates(values)
        for branch in perception_branch_group.branches:
            axis = branch.perception_samples
            if axis is not None and axis.cap != shortlist_cap:
                raise ValueError(
                    f"roles.perception.sampling_variants arm {branch.branch_id!r} perception_samples.cap {axis.cap} must "
                    f"equal the Solver's own candidate_supply.max_candidates {shortlist_cap}: the merge adds no supply knob"
                )
        if supply_variant_group is not None:
            raise ValueError(
                "roles.perception.sampling_variants cannot combine with a Solver supply_variants or template_variants group: "
                "two fan-out mechanisms in one episode make the ceiling's extra-contact term ambiguous"
            )
        if knowledge_index_armed:
            raise ValueError(
                "roles.perception.sampling_variants cannot combine with native_episode.knowledge_index: the index appends to "
                "the system message every arm shares and has no per-arm custody form"
            )
    if "branches" in raw_roles["perception"]:
        from .knowledge_stores import declared_alternate_release_relpaths
        from .supply_variants import PerceptionBranchError, parse_perception_branches
        # Importing the BARE registry object from ``core.base`` is not enough:
        # ``core.base.PERCEPTION_PRESENTATIONS`` is populated by
        # ``rails.perception_presentations``'s own module-level ``.register(
        # ...)`` calls, which only run once that module has been imported --
        # the same reason ``rails.acquisition`` must be imported to populate
        # ``core.base.ACQUISITION_POLICIES``. Importing the REGISTERING
        # module here (not just the registry) is what makes
        # ``registered_presentation_ids`` below non-empty the first time this
        # loader runs, regardless of what any other module has already
        # imported.
        from .perception_presentations import (  # noqa: F401
            PERCEPTION_PRESENTATIONS, TOP2_CONTRAST_PRESENTATION_ID,
        )

        declared_stores = values.get("knowledge_stores")
        if declared_stores is not None and not isinstance(declared_stores, Mapping):
            raise ValueError("knowledge_stores must be a mapping")
        try:
            perception_branch_group = parse_perception_branches(
                raw_roles["perception"]["branches"],
                first_phase_id=program.phase_names()[0],
                declared_stores=(
                    None if declared_stores is None else tuple(declared_stores)
                ),
                declared_alternate_relpaths=declared_alternate_release_relpaths(
                    declared_stores
                ),
                registered_presentation_ids=tuple(PERCEPTION_PRESENTATIONS.names()),
                # Migration step 5: the carrier's ``max_decision_candidates``
                # hook (SLURP: 3); a carrier without it admits no
                # ``min_candidates`` at all (ceiling 0 refuses every value).
                max_candidates_ceiling=_carrier_max_decision_candidates(values),
                # "What to build" item 1: a branch declaring top2-contrast-v1
                # must carry a contrast_pairs pin, and no other branch may.
                top2_contrast_presentation_id=TOP2_CONTRAST_PRESENTATION_ID,
                # Ruling R3 (evidence-consumption module, migration step 4):
                # only a declared module block's ADMITTED delivered policy may
                # set A's axes; the block itself is verified against these
                # very blocks (``verify_declared_module``), so a hand-written
                # A axis stays refused (refusal 6).
                delivering_axes_admitted=_module_delivering_axes(raw),
            )
        except PerceptionBranchError as error:
            raise ValueError(
                f"roles.perception.branches is invalid: {error}"
            ) from error
        if supply_variant_group is not None:
            raise ValueError(
                "roles.perception.branches cannot combine with "
                "roles.solver.supply_variants: two fan-out mechanisms in one "
                "episode make the ceiling's extra-contact term ambiguous"
            )
        if knowledge_index_armed:
            # Same reason the Solver's own arm group refuses this combination
            # above: the index replaces the very value blocks a branch varies.
            raise ValueError(
                "roles.perception.branches cannot combine with "
                "native_episode.knowledge_index: the index replaces the very "
                "value blocks a branch varies"
            )
    # Item E4 (2026-09-28, owner decision 185, "core-native targeted re-
    # listen"; design docs/superpowers/specs/2026-09-28-e4-core-native-
    # targeted-relisten-design.md section 6): the post-accept relisten
    # block, parsed HERE -- before any contact -- so a fragment can never
    # name an unregistered policy or a cap outside its declared bounds.
    # ``None`` for every config written before E4 and every OFF arm, which
    # leaves the ceiling below and every role exactly as they were.
    relisten_json = None
    if "relisten" in raw:
        from .relisten import RelistenError, parse_relisten  # noqa: PLC0415

        try:
            relisten_config = parse_relisten(raw["relisten"])
        except RelistenError as error:
            raise ValueError(f"native_episode.relisten is invalid: {error}") from error
        # v1 refuses beside a Solver supply-variant arm group and beside a
        # grouped Solver visit (design section 6's implementation-plan
        # table): both fan the Solver's OWN visit out into several
        # contacts, and the relisten stage's own entity-index addressing
        # ("up to 3 delivered entities, in delivery order") assumes exactly
        # one delivered Solver answer per row to re-listen against.
        if supply_variant_group is not None:
            raise ValueError(
                "native_episode.relisten cannot combine with "
                "roles.solver.supply_variants in v1"
            )
        if raw_roles["solver"].get("samples", 1) != 1:
            raise ValueError(
                "native_episode.relisten cannot combine with a grouped Solver "
                "visit (roles.solver.samples > 1) in v1"
            )
        relisten_json = relisten_config.as_json()
    # Owner decisions 195/196 (2026-09-29): the evidence-consumption module's
    # block, parsed HERE -- before any contact -- fail-closed: an unknown
    # component id or state, an armed component without a resolvable
    # admitting record, or a config whose policy blocks are not exactly what
    # the block compiles to is refused. Absent -> ``None``, byte for byte.
    consumption_module_json = None
    if "consumption_module" in raw:
        from .consumption_module import (  # noqa: PLC0415
            ConsumptionModuleConfigError, verify_declared_module,
        )

        try:
            consumption_module_json = verify_declared_module(raw["consumption_module"], values)
        except ConsumptionModuleConfigError as error:
            raise ValueError(f"native_episode.consumption_module is invalid: {error}") from error
    roles = []
    for kind in kinds:
        row = raw_roles[kind]
        phase_id, iterations = row["phase_id"], iterations_by_kind[kind]
        spec = tool_specs.get(phase_id)
        tools = ()
        if spec is not None:
            if kind not in {"reviewer", "planner"} and not (kind == "solver" and solver_access):
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
            row.get("twin"),
            # Item E39: keyword, because the role's own field is last and
            # every positional argument above is the pre-E39 order.
            max_completion_tokens=completion_caps_by_kind[kind],
            # Item E42: keyword for the same reason, and None for every role
            # but the Solver of a config that declares the key at all.
            supply_variants=(
                supply_variant_group if kind == "solver" else None
            ),
            # Phase 2, merge set C: keyword for the same reason, and None for
            # every role but the Perception of a config that declares the key.
            perception_branches=(
                perception_branch_group if kind == "perception" else None
            ),
        ))
    # E17: ``constant`` rendering is admitted only where it leaves every
    # tool-bearing role's request array exactly as ``per-role`` renders it.
    # Two reasons, both fail-closed:
    #   * custody -- ``rails.native_tool_authority.select_completion_tool_
    #     schemas`` re-derives the request's schema array from the names the
    #     model actually called and compares its digest to the request's own
    #     ``tool_schemas_sha256``, which only holds when a caller's array is
    #     exactly its own authority;
    #   * honesty -- widening one role's rendered array beyond its authority
    #     would make "authority unchanged" false for that role.
    # With every tool-bearing role declaring the SAME ordered names, the
    # union IS each of their arrays, and only the tool-free roles change.
    if tool_schema_rendering == "constant":
        bearing = [role.tool_names for role in roles if role.tool_names]
        # Preserve the seed node-context declaration only for the explicitly
        # compiled and verified plain review-off architecture. Other tool-free
        # configs retain the historical refusal of this rendering alias.
        plain_off_profile = (consumption_module_json is not None and solver_access is None
                             and raw["consumption_module"].get("review_loop") == "off")
        if not bearing and not plain_off_profile:
            raise ValueError(
                "native_episode.tool_schema_rendering 'constant' requires at least "
                "one role with tool authority; with no tools at all it is a second "
                "spelling of 'per-role'"
            )
        if any(names != bearing[0] for names in bearing[1:]):
            raise ValueError(
                "native_episode.tool_schema_rendering 'constant' requires every "
                "role with tool authority to declare the same ordered tool names, "
                "so the constant array is each of their own arrays and no role's "
                "rendered scope exceeds its authority"
            )
    # E18: the sixth node's seat, parsed HERE -- before any contact -- so a
    # fragment can never name an unregistered policy, arm a kind its node may
    # not execute, or declare a contact budget its own arithmetic refuses.
    acquisition_role = None
    acquisition_policy_id = None
    acquisition_budget = None
    acquisition_retrieval = None
    if acquisition_armed:
        row = raw_roles[ACQUISITION_ROLE_KIND]
        if (
            not isinstance(row, Mapping)
            or set(row) != {"phase_id", "max_iterations", "kinds"}
        ):
            raise ValueError(
                "the acquisition role requires exactly phase_id, max_iterations "
                "and kinds"
            )
        if row["phase_id"] not in program.phase_names():
            raise ValueError("native role references an unknown program phase")
        declared_kinds = row["kinds"]
        if (
            not isinstance(declared_kinds, list)
            or not declared_kinds
            or any(not isinstance(item, str) or not item for item in declared_kinds)
        ):
            raise ValueError("the acquisition role must declare its kinds")
        acquisition_role = NativeEpisodeRole(
            row["phase_id"], ACQUISITION_ROLE_KIND, row["max_iterations"], (),
            "full", 1, None, None, None, tuple(declared_kinds),
        )
        block = raw["acquisition"]
        if not isinstance(block, Mapping) or not {"policy", "budget"} <= set(block) <= {
            "policy", "budget", "retrieval",
        }:
            raise ValueError(
                "native_episode.acquisition must be an object with exactly a "
                "'policy' id, a 'budget' and an optional 'retrieval' (item E36b)"
            )
        acquisition_policy_id = block["policy"]
        if not isinstance(acquisition_policy_id, str) or not acquisition_policy_id.strip():
            raise ValueError("acquisition.policy must be a non-empty string")
        # Function-local: importing rails.acquisition is what POPULATES
        # core.base.ACQUISITION_POLICIES, the same registration discipline
        # commit.policy and deliver_normaliser follow above.
        from .acquisition import (  # noqa: PLC0415
            AcquisitionBudget,
            AcquisitionError,
            RetrievalPolicy,
            resolve_acquisition_policy,
        )

        try:
            policy = resolve_acquisition_policy(acquisition_policy_id)
        except AcquisitionError as error:
            raise ValueError(f"acquisition.policy is invalid: {error}") from error
        if policy.kind not in acquisition_role.acquisition_kinds:
            raise ValueError(
                f"acquisition.policy {acquisition_policy_id!r} is of kind "
                f"{policy.kind!r}, which roles.acquisition.kinds does not admit"
            )
        if acquisition_role.max_iterations != policy.contacts_per_acquisition:
            raise ValueError(
                "roles.acquisition.max_iterations must equal the policy's own "
                "contacts per acquisition"
            )
        budget_block = block["budget"]
        if not isinstance(budget_block, Mapping) or not {
            "max_acquisitions_per_row", "contact_budget",
        } <= set(budget_block) <= {
            "max_acquisitions_per_row", "contact_budget", "max_items_per_acquisition",
        }:
            raise ValueError(
                "acquisition.budget requires exactly max_acquisitions_per_row, "
                "contact_budget and an optional max_items_per_acquisition (item E36b)"
            )
        # Item E36b: the findings-keyed requery repair is ONE module, not two
        # independently-armable keys -- a budget cap with no ranking rule, or
        # a ranking rule with no cap, is a half-armed declaration refused
        # before any contact, exactly as ``knowledge_index_budget`` requires
        # its own armed index above.
        if ("max_items_per_acquisition" in budget_block) != ("retrieval" in block):
            raise ValueError(
                "acquisition.budget.max_items_per_acquisition and "
                "acquisition.retrieval are one module: declare both or neither"
            )
        try:
            budget = AcquisitionBudget(
                budget_block["max_acquisitions_per_row"],
                budget_block["contact_budget"],
                budget_block.get("max_items_per_acquisition"),
            ).validate()
        except AcquisitionError as error:
            raise ValueError(f"acquisition.budget is invalid: {error}") from error
        if "retrieval" in block:
            retrieval_block = block["retrieval"]
            if not isinstance(retrieval_block, Mapping) or set(retrieval_block) != {
                "policy", "min_token_chars", "max_document_frequency",
                "exclude_visible_tokens",
            }:
                raise ValueError(
                    "acquisition.retrieval requires exactly policy, "
                    "min_token_chars, max_document_frequency and "
                    "exclude_visible_tokens"
                )
            try:
                retrieval_policy = RetrievalPolicy(
                    retrieval_block["policy"],
                    retrieval_block["min_token_chars"],
                    retrieval_block["max_document_frequency"],
                    retrieval_block["exclude_visible_tokens"],
                ).validate()
            except AcquisitionError as error:
                raise ValueError(f"acquisition.retrieval is invalid: {error}") from error
            acquisition_retrieval = retrieval_policy.as_json()
        if not 1 <= budget.max_acquisitions_per_row <= revisions:
            # An ACQUIRE spends a revision, exactly as a REVISE and a
            # candidate refresh do, so an allowance larger than the revision
            # allowance is one that can never be spent.
            raise ValueError(
                "acquisition.budget.max_acquisitions_per_row must be bounded by "
                "max_revisions"
            )
        expected_contacts = (
            budget.max_acquisitions_per_row * acquisition_role.max_iterations
        )
        if budget.contact_budget != expected_contacts:
            # A redundant, CHECKED declaration, exactly as ``review_loop`` is:
            # the fragment writes what it believes it will spend and the
            # parser refuses the moment that disagrees with its own node.
            raise ValueError(
                "acquisition.budget.contact_budget must equal "
                "max_acquisitions_per_row x roles.acquisition.max_iterations"
            )
        acquisition_budget = budget.as_json()
        if refresh_action is not None:
            # Two back-edges into the same revision budget, whose receipts
            # are validated by two different stage walkers
            # (``rails.native_episode_receipt``). The combination is a
            # question for the cell that needs it, not a default: refuse it
            # by name rather than let one validator silently mis-read the
            # other's visits.
            raise ValueError(
                "native_episode.acquisition and candidate_refresh both consume "
                "the revision allowance; declare one of them"
            )
    phase_ids = tuple(role.phase_id for role in roles) + (
        () if acquisition_role is None else (acquisition_role.phase_id,)
    )
    expected_phase_count = 4 + (0 if acquisition_role is None else 1)
    if (
        len(set(phase_ids)) != expected_phase_count
        or set(phase_ids) != set(program.phase_names())
    ):
        raise ValueError("native roles must cover the program once each")
    if set(tool_specs) - set(phase_ids):
        raise ValueError("native tool phase is outside the episode")
    if acquisition_role is not None and acquisition_role.phase_id in tool_specs:
        # The Acquisition node is not one of the two seats owner decision 11
        # allows a model-callable action; its own tool kind is the registered
        # ``tool-acquire`` policy, executed by the node, not a native tool the
        # core may call.
        raise ValueError("the acquisition role may not expose analytical tools")
    planner_phase = program.phase(next(role.phase_id for role in roles if role.role_kind == "planner"))
    if (
        planner_output_format == "json-action-v1"
        and planner_phase.response_format_id != PLANNER_ACTION_RESPONSE_FORMAT_ID
    ):
        raise ValueError(
            "json-action-v1 requires the registered Planner phase response format"
        )
    # E8a (2026-09-17): ONE key, not two. ``native_episode.role_context`` is
    # folded under ``native_episode.context_policy`` -- its policy_id/params
    # pair IS the structured level's implementation -- so a fragment carrying
    # both is refused rather than silently letting two compilers write the
    # same ``agent_state`` slot. A fragment carrying only ``role_context``
    # keeps working unchanged, which is what lets the 2026-09-16 aborted
    # typed-context flight's configs still be read.
    if "role_context" in raw and "context_policy" in raw:
        raise ValueError(
            "native_episode declares both role_context and context_policy; the "
            "role_context block is folded under context_policy (E8a), so exactly "
            "one of them may be present"
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
    context_policy_json = None
    # E8b: what a declared node-context policy adds to the bounded contact
    # ceiling. Zero for every level up to and including L1, and for every
    # config that declares no policy at all, so the historical formula below
    # is reduced to exactly itself.
    cleaning_contacts_per_revision = 0
    if "context_policy" in raw:
        from .node_context_binding import (
            is_node_context_null_arm,
            node_context_cleaning_boundaries,
            node_context_producer_formats,
            node_context_source_format_id,
            validate_node_context_policy_config,
        )

        # A DECLARED policy always reaches the runtime, including its OFF arm:
        # an all-raw policy renders every state untouched -- the request bytes
        # are the pre-policy bytes -- and still emits one ``level: "raw"``
        # receipt row per boundary per contact, which is what makes L0's byte
        # identity a checked statement (design section 9). The key's ABSENCE
        # remains the arm that composes to the pre-key config hash.
        context_policy_json = validate_node_context_policy_config(
            raw["context_policy"]
        )
        if not is_node_context_null_arm(raw["context_policy"]):
            # A boundary policy and a history filter are two ways to answer
            # the same question; composing them silently would make neither
            # auditable. Inherited verbatim from the role_context rule above.
            if any(role.history_scope != "full" for role in roles):
                raise ValueError(
                    "node context policy cannot combine with a history filter"
                )
            perception = next(role for role in roles if role.role_kind == "perception")
            if program.phase(perception.phase_id).response_format_id != (
                node_context_source_format_id(context_policy_json)
            ):
                raise ValueError(
                    "node context policy requires the registered Perception phase format"
                )
            by_kind = {role.role_kind: role for role in roles}
            for role_kind, format_id in node_context_producer_formats(
                context_policy_json
            ).items():
                phase = program.phase(by_kind[role_kind].phase_id)
                if phase.response_format_id != format_id:
                    raise ValueError(
                        f"node context policy declares response_format_id "
                        f"{format_id!r} for the {role_kind} producer, but its phase "
                        f"declares {phase.response_format_id!r}"
                    )
            # E8b: each declared cleaning boundary spends at most ONE extra
            # contact per contact of its CONSUMER role, so the ceiling gains
            # (max_revisions + 1) * consumer.max_iterations. For the only
            # boundary the design proposes -- planner:review-finding, with a
            # one-iteration Planner -- that is exactly the (max_revisions + 1)
            # of design section 7, which takes the anchor's 11 to 13.
            declared_cleanings = node_context_cleaning_boundaries(context_policy_json)
            phase_names = set(program.phase_names())
            for spelling in declared_cleanings:
                consumer_kind = spelling.split(":", 1)[0]
                if consumer_kind not in by_kind:
                    raise ValueError(
                        f"node context cleaning boundary {spelling!r} names no "
                        "episode role"
                    )
                cleaning_contacts_per_revision += by_kind[consumer_kind].max_iterations
            for entry in raw["context_policy"].get("boundaries", {}).values():
                cleaning = entry.get("cleaning") if isinstance(entry, Mapping) else None
                if isinstance(cleaning, Mapping) and cleaning.get("phase_id") in phase_names:
                    # A cleaning contact is NOT one of the four role phases: it
                    # registers no agent state and routes no episode step. Its
                    # phase_id may therefore never be mistaken for a program
                    # phase name.
                    raise ValueError(
                        "node context cleaning phase_id cannot be one of the "
                        "episode's own program phases"
                    )
    # E12 (2026-09-19, owner directive 26): the Reviewer slot-audit context
    # block. ONE key, validated fail-closed HERE -- before any contact -- so a
    # fragment can never arm it on a carrier with no registered view, on a
    # boundary whose rendering it would be cleaned out of, or against pins
    # whose bytes are not the released construction table. E19 re-based the
    # block off the L1 policy, so a fragment may now arm it with no
    # ``context_policy`` at all.
    reviewer_audit_json = None
    if "reviewer_audit" in raw:
        from .node_context_binding import (
            reviewer_audit_boundary_attachment,
            validate_reviewer_audit_config,
        )

        declared_carrier = values.get("carrier_lock_key")
        if declared_carrier != "slurp":
            raise ValueError(
                "native_episode.reviewer_audit is defined for carrier 'slurp', but "
                f"this config declares carrier_lock_key {declared_carrier!r}"
            )
        reviewer_audit_json = validate_reviewer_audit_config(raw["reviewer_audit"])
        # E19 (owner decision 32): the block is an ADDITION to the ONE thing
        # the Reviewer would otherwise receive at reviewer:current-draft --
        # the boundary's L1 rendering where a policy declares one (E12), the
        # SEALED draft bytes where the boundary is at raw or no policy is
        # declared at all. Only 'cleaned' is refused, by name: a cleaning
        # contact rewrites the rendering the block is appended to.
        reviewer_audit_boundary_attachment(context_policy_json)
    # E14 (2026-09-19, owner directive 26): the Solver scenario-hints
    # context block. ONE key, validated fail-closed HERE -- before any
    # contact -- so a fragment can never arm it on a carrier with no
    # registered view, on a boundary that is not at L1, or against pins
    # whose bytes are not the released construction table.
    solver_hints_json = None
    if "solver_hints" in raw:
        from .node_context_binding import (
            solver_hints_requires_structured_boundary,
            validate_solver_hints_config,
        )

        declared_carrier = values.get("carrier_lock_key")
        if declared_carrier != "slurp":
            raise ValueError(
                "native_episode.solver_hints is defined for carrier 'slurp', but "
                f"this config declares carrier_lock_key {declared_carrier!r}"
            )
        solver_hints_json = validate_solver_hints_config(raw["solver_hints"])
        # The block is an ADDITION to the solver:candidate-hypothesis L1
        # rendering. It has nothing to attach to at 'raw' and would be
        # replaced at 'cleaned', so both are refused by name rather than
        # silently rendering nothing.
        solver_hints_requires_structured_boundary(context_policy_json)
    # E21 (2026-09-19, owner decisions 48 and 50): the knowledge INDEX and
    # index-based context assembly. ONE key, validated fail-closed HERE --
    # before any contact -- under the eight refusals of design section 6.4.
    knowledge_index_json = None
    if knowledge_index_armed:
        knowledge_index_json = _load_knowledge_index(
            raw["knowledge_index"],
            values=values,
            raw_roles=raw_roles,
            kinds=kinds,
            tool_schema_rendering=tool_schema_rendering,
            tool_authority_present=any(role.tool_names for role in roles),
        )
    # E11 (2026-09-18, owner directive 26): the delivery-time normaliser
    # node. ONE key, validated fail-closed HERE -- before any contact -- so a
    # fragment can never arm a carrier-specific delivery rule on the wrong
    # carrier, name an unregistered rule, or reach delivery in a shape whose
    # custody the seal cannot re-derive.
    deliver_normaliser_id = None
    if "deliver_normaliser" in raw:
        block = raw["deliver_normaliser"]
        if not isinstance(block, Mapping) or set(block) != {"normaliser"}:
            raise ValueError(
                "native_episode.deliver_normaliser must be an object with exactly "
                "a 'normaliser' id"
            )
        deliver_normaliser_id = block["normaliser"]
        if not isinstance(deliver_normaliser_id, str) or not deliver_normaliser_id.strip():
            raise ValueError("deliver_normaliser.normaliser must be a non-empty string")
        # Function-local: importing rails.delivery_normalisers is what
        # POPULATES core.base.DELIVERY_NORMALISERS, the same registration
        # discipline commit.policy follows above.
        from . import delivery_normalisers as _delivery_normalisers  # noqa: PLC0415, F401
        from ..core.base import DELIVERY_NORMALISERS, CoreError  # noqa: PLC0415

        try:
            normaliser = DELIVERY_NORMALISERS.resolve(deliver_normaliser_id)
        except CoreError as error:
            raise ValueError(f"deliver_normaliser.normaliser is invalid: {error}") from error
        declared_carrier = values.get("carrier_lock_key")
        if getattr(normaliser, "carrier_lock_key", None) != declared_carrier:
            raise ValueError(
                f"deliver_normaliser {deliver_normaliser_id!r} is defined for carrier "
                f"{getattr(normaliser, 'carrier_lock_key', None)!r}, but this config "
                f"declares carrier_lock_key {declared_carrier!r}"
            )
        # Two spellings of one rule is how a cell ends up with two
        # identities: the E4 run-level key applies the SAME projection at the
        # SEAL, outside the agent. A fragment declares one or the other.
        if values.get("slurp_projection_v3_delivery"):
            raise ValueError(
                "native_episode.deliver_normaliser and the run-level "
                "slurp_projection_v3_delivery key apply the same rule at two "
                "different places; declare exactly one of them"
            )
        # Custody, not taste: a grouped Solver row's delivered text is already
        # the COMMIT policy's aggregate (E2d, invariant I7g), which the bundle
        # re-derives from the row's own recorded samples. Normalising on top
        # of it would make the delivered bytes a function of BOTH rules with
        # only one of them in custody, so the combination is refused until a
        # cell needs it and its custody form is designed.
        if any(role.role_kind == "solver" and role.samples > 1 for role in roles):
            raise ValueError(
                "native_episode.deliver_normaliser cannot combine with a grouped "
                "Solver visit (roles.solver.samples >= 2)"
            )
    # Gap G1 plumbing (``rails.solver_citation``): the cited-answer contract
    # and its unwrapping delivery normaliser are ONE arming, checked here,
    # fail-closed, before any contact. The contract alone would deliver the
    # citation envelope as the answer; the normaliser alone would unwrap an
    # answer that is not an envelope; and only the ANSWERING node may cite,
    # because its state is the one whose ``cited_value_ids`` the credit read
    # consumes. Absent both -- every fragment written before this seam --
    # nothing here is reachable.
    from .solver_citation import (  # noqa: PLC0415
        CITED_ANSWER_NORMALISER_IDS,
        CITED_ANSWER_RESPONSE_FORMAT_ID,
    )

    citing_phases = [
        phase.name for phase in program.phases
        if phase.response_format_id == CITED_ANSWER_RESPONSE_FORMAT_ID
    ]
    solver_phase_id = next(role.phase_id for role in roles if role.role_kind == "solver")
    if citing_phases and citing_phases != [solver_phase_id]:
        raise ValueError(
            "the cited-answer response format may be declared by the Solver phase only, "
            f"got {citing_phases!r}"
        )
    unwraps = deliver_normaliser_id in CITED_ANSWER_NORMALISER_IDS
    if citing_phases and not unwraps:
        raise ValueError(
            "a Solver phase declaring saea-solver-cited-answer-v1 requires "
            "native_episode.deliver_normaliser to name one of "
            f"{sorted(CITED_ANSWER_NORMALISER_IDS)}; otherwise the citation envelope "
            "would be delivered as the answer"
        )
    if unwraps and not citing_phases:
        raise ValueError(
            f"deliver_normaliser {deliver_normaliser_id!r} unwraps a cited-answer "
            "envelope, so the Solver phase must declare response_format_id "
            "saea-solver-cited-answer-v1"
        )
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
    #
    # Item E42 (2026-09-25, family VAR-2): and by its registered supply-variant
    # ARM COUNT, for exactly the same reason -- K arms at one node are K real
    # metered contacts of that node, one per declared construction. 1 for every
    # config that declares no arm group, which again reduces this to the
    # formula above. ``samples >= 2`` and an arm group are refused together
    # (``NativeEpisodeRole.__post_init__``), so the product is never of two
    # simultaneously non-unit factors.
    # Item E42b (2026-09-27, owner decision 172, merge set B): under
    # ``supply_variants.arm_visits: "first"`` the arm group fans out ONLY at
    # the Solver's first visit of the whole episode; every later revision
    # visit contacts the delivering arm alone (``rails.runner``,
    # ``rails.native_episode_receipt``). The per_revision term below must
    # therefore NOT multiply every revision's Solver contribution by the arm
    # count -- that was VAR-2's own bug (docs/results/2026-09-25-slurp-var2-
    # closed-engineering-failure.md): the fit bound covers exactly one visit.
    # Instead the formula counts the Solver's ordinary ONE contact per
    # revision and adds the (K - 1) extra contacts of the one visit that
    # fans out exactly once, matching the design's own simple form: ceiling
    # = base_ceiling + (K - 1). Absent an arm group, or under the default
    # "every", this reduces to exactly the pre-E42b formula.
    solver_role_for_ceiling = next(r for r in roles if r.role_kind == "solver")
    variant_group_for_ceiling = solver_role_for_ceiling.supply_variants
    variant_arm_count_for_ceiling = _supply_variant_arm_count(solver_role_for_ceiling)
    variant_fans_out_once = (
        variant_group_for_ceiling is not None
        and variant_group_for_ceiling.arm_visits == "first"
    )
    per_revision = sum(
        r.max_iterations * r.samples * (
            1 if (r.role_kind == "solver" and variant_fans_out_once)
            else _supply_variant_arm_count(r)
        )
        if r.role_kind == "solver" else r.max_iterations
        for r in roles[1:]
    )
    # E8b (SLURP v2 base program M5, design section 7): plus one cleaning
    # contact per contact of each cleaned boundary's consumer role. Zero
    # without a declared cleaning boundary.
    per_revision += cleaning_contacts_per_revision
    ceiling = roles[0].max_iterations + (revisions + 1) * per_revision
    ceiling += refreshes * roles[0].max_iterations
    if variant_fans_out_once:
        ceiling += variant_arm_count_for_ceiling - 1
    # Same-flight instrument, PHASE 2 (merge set C): the Perception-branch
    # group's extra-contact term (design section 3, "Budget"): level 1 adds
    # the K - 1 extra PERCEPTION contacts of the non-A branches; level 2 adds
    # those plus one extra SOLVER contact per non-A branch. Perception has
    # exactly one visit per row (no refresh, no revision re-entry), so --
    # unlike the Solver arm-group term above -- this is added once, never
    # multiplied by ``revisions``. Zero (the ``roles[0].perception_branches
    # is None`` branch below is simply skipped) for every config that
    # declares no branch group, which reduces this to exactly the
    # pre-phase-2 formula. Refused beside a Solver arm group
    # (``NativeEpisodeRole.__post_init__`` / the parse-time check above), so
    # this and the ``variant_fans_out_once`` term above are never both taken.
    if roles[0].perception_branches is not None:
        from .supply_variants import perception_branch_ceiling, sampling_extra_contacts  # noqa: PLC0415

        ceiling = perception_branch_ceiling(
            base_ceiling=ceiling,
            branch_count=roles[0].perception_branches.branch_count,
            level=roles[0].perception_branches.level,
        )
        # Decision 338: plus the sampling column's extra contacts ((k - 1) Perception and (n - 1) Solver per sampling branch).
        ceiling += sampling_extra_contacts(roles[0].perception_branches)
    # E18 (2026-09-19, owner decisions 43-44): plus the contacts the
    # Acquisition node's own visits may spend. Zero for every model-free kind
    # and for every config that declares no acquisition at all, which reduces
    # this to exactly the pre-E18 formula.
    if acquisition_role is not None:
        ceiling += (
            acquisition_budget["max_acquisitions_per_row"]
            * acquisition_role.max_iterations
        )
    # Item E4 (2026-09-28, owner decision 185): plus the relisten stage's own
    # contacts -- up to 2 per triggered entity (blind + forced choice),
    # bounded by ``relisten.max_slots_per_row`` and added ONCE (the stage
    # runs once per row, after the last accepted answer, never once per
    # revision). Zero for every config that declares no relisten block,
    # which reduces this to exactly the pre-E4 formula.
    if relisten_json is not None:
        from .relisten import relisten_extra_ceiling  # noqa: PLC0415

        ceiling += relisten_extra_ceiling(json.loads(relisten_json)["max_slots_per_row"])
    if allow_subceiling:
        if ceiling > program.max_contacts:
            raise ValueError("selected native graph exceeds the shared program contact ceiling")
    elif program.max_contacts != ceiling:
        raise ValueError("program contact ceiling must equal the bounded native graph ceiling")
    # Cell RANKVIS (owner decision 171): absent -> None, the pre-RANKVIS
    # config byte for byte. Armed, it is refused beside the two mechanisms
    # that own the same bytes: phase tools render the values through their
    # own renderer, and a supply-variant arm group resolves each arm's
    # selection independently of this row's supply step (item E42's live
    # delivering-arm check would refuse the re-ordered selection).
    knowledge_value_rendering_json = None
    if "knowledge_value_rendering" in raw:
        knowledge_value_rendering_json = parse_knowledge_value_rendering(
            raw["knowledge_value_rendering"],
            values=values,
            knowledge_index_armed=knowledge_index_armed,
        )
        if values.get("phase_tools"):
            raise ValueError(
                "native_episode.knowledge_value_rendering cannot be armed beside "
                "phase_tools: the tool dispatcher renders the values itself"
            )
        solver_roles = [role for role in roles if role.role_kind == "solver"]
        if any(getattr(role, "supply_variants", None) is not None for role in solver_roles):
            raise ValueError(
                "native_episode.knowledge_value_rendering cannot be armed beside a "
                "Solver supply-variant arm group"
            )
        # Same-flight instrument, PHASE 2 (merge set C): the same custody
        # reason -- a Perception branch group resolves each branch's own
        # selection independently of this row's supply step.
        if roles[0].perception_branches is not None:
            raise ValueError(
                "native_episode.knowledge_value_rendering cannot be armed beside "
                "a Perception branch group"
            )
    # Same-flight instrument, PHASE 2 (merge set C, design section 3,
    # "Refused"): a declared branch group is refused beside a frozen
    # finite_supply_policy (a frozen policy resolves this row's supply
    # independently of a branch's own pre-flight seed -- the same custody
    # reason knowledge_value_rendering is refused above) and beside an
    # acquisition policy that RE-ENTERS Perception (kind
    # ``speech-reobserve``): that policy's own re-observation node would
    # contact Perception a SECOND time, outside the branch fork entirely,
    # for a phase whose branch group already claims sole ownership of its
    # one seed.
    if roles[0].perception_branches is not None:
        if values.get("finite_supply_policy") is not None:
            raise ValueError(
                "native_episode.roles.perception.branches cannot be armed "
                "beside finite_supply_policy"
            )
        if acquisition_policy_id is not None:
            # Function-local: the same registration discipline every other
            # rails.acquisition import in this module follows.
            from .acquisition import (  # noqa: PLC0415
                KIND_SPEECH_REOBSERVE, AcquisitionError, resolve_acquisition_policy,
            )

            try:
                acquisition_policy = resolve_acquisition_policy(acquisition_policy_id)
            except AcquisitionError as error:
                raise ValueError(f"acquisition.policy is invalid: {error}") from error
            if acquisition_policy.kind == KIND_SPEECH_REOBSERVE:
                raise ValueError(
                    "native_episode.roles.perception.branches cannot be armed "
                    "beside an acquisition policy that re-enters Perception "
                    f"({KIND_SPEECH_REOBSERVE!r})"
                )
    review_handoff = raw.get("review_handoff")
    if review_handoff not in (None, "slot-issues-v1"):
        raise ValueError("native_episode.review_handoff is invalid")
    result = NativeEpisodeConfig(
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
        context_policy_json,
        deliver_normaliser_id,
        reviewer_audit_json,
        solver_hints_json,
        tool_schema_rendering,
        acquisition_role,
        acquisition_policy_id,
        acquisition_budget,
        context_fit_policy,
        knowledge_index_json,
        react_exhaustion_policy,
        acquisition_retrieval,
        reviewer_verdict_vocabulary,
        finite_completion_scope,
        knowledge_value_rendering_json,
        relisten_json,
        consumption_module_json,
        carrier_profile=_carrier_profile(values),
        review_handoff=review_handoff,
        solver_tool_access=solver_access,
    )
    if solver_access:
        stores = values.get("knowledge_stores")
        if not isinstance(stores, Mapping) or "slot-contracts" not in stores:
            raise ValueError("Solver lookup requires the declared slot-contracts store")
        validate_solver_tool_access(result, tool_specs)
    return result


def validate_solver_tool_access(config, tool_specs, *, dispatcher=None):
    """Recheck opt-in authority at load and shared-runtime binding boundaries."""
    if config.solver_tool_access is None:
        return
    solver, perception = config.role("solver"), config.role("perception")
    if (config.solver_tool_access != SOLVER_TOOL_ACCESS_MODE or config.review_loop_enabled
            or config.role("planner").max_iterations != 0 or config.max_revisions != 0
            or solver.max_iterations != 2 or solver.samples != 1 or solver.supply_variants is not None
            or perception.max_iterations != 1 or perception.perception_branches is not None
            or config.max_contacts != 3 or not config.reserve_final_report
            or config.tool_schema_rendering != "per-role" or config.acquisition_enabled
            or config.refresh_action is not None or config.relisten_json is not None
            or solver.tool_names != (SOLVER_SLOT_TOOL,)
            or any(r.tool_names for r in config.roles if r.role_kind != "solver")):
        raise ValueError("Solver bounded lookup requires the reserved three-contact review-off graph")
    expected = {"mode": "native-tools", "source_authority_role": solver.phase_id,
                "allowed_tools": (SOLVER_SLOT_TOOL,), "knowledge_views": ("text",),
                "knowledge_store_ids": ("slot-contracts",), "knowledge_target_axis": "slot-type",
                "knowledge_selection_mode": "targeted", "candidate_limit": 2,
                "knowledge_values_per_candidate": 1, "max_calls_per_sample": 1}
    if not isinstance(tool_specs, Mapping) or set(tool_specs) != {solver.phase_id}:
        raise ValueError("Solver lookup requires exactly its own phase tool authority")
    spec = tool_specs[solver.phase_id]
    for key, value in expected.items():
        actual = spec.get(key)
        if isinstance(value, tuple) and isinstance(actual, list):
            actual = tuple(actual)
        if type(actual) is not type(value) or actual != value:
            raise ValueError(f"Solver lookup authority differs at {key}")
    cap = spec.get("knowledge_value_limit")
    if type(cap) is not int or not 1 <= cap <= 2:
        raise ValueError("Solver lookup permits at most two fixed slot values")
    if dispatcher is not None:
        stores = getattr(dispatcher, "knowledge_stores", None)
        indices = getattr(getattr(dispatcher, "supply_for_store", None), "slot_target_indices", {})
        if (stores is None or "slot-contracts" not in stores.store_ids
                or "slot-contracts" not in indices or not callable(dispatcher.tool_contact)):
            raise ValueError("Solver lookup requires the bound fixed store, authored slot index and custodian")


def _load_knowledge_index(
    block, *, values: Mapping, raw_roles: Mapping, kinds, tool_schema_rendering: str,
    tool_authority_present: bool = True,
) -> str:
    """E21: validate ``native_episode.knowledge_index``, fail-closed.

    The eight refusals of design section 6.4, in order, each raising by name
    before any contact is made:

    1. an unreleased or hash-mismatched ``view`` -- the id here, the BYTES
       at :func:`rails.knowledge_index.load_knowledge_index_table`, which is
       the same two-stage split ``solver_hints`` uses so a fragment can be
       validated on a machine with no data root;
    2. a ``granularity`` naming an entry kind the view does not carry (the
       ``exemplar`` kind is pointer-and-expansion only);
    3. ``expansion_budget.exemplar > 0`` with no exemplar store armed on any
       phase;
    4. ``pointer_budget.intent > candidate_supply.max_candidates`` -- the
       pointer block may never name more candidates than the projection
       produced;
    5. ``expansion_budget.slot_card > candidate_supply.max_total_values``;
    6. an ``ordering`` id not registered in ``core.base``;
    7. the key armed without a constant prefix -- ``tool_schema_rendering``
       absent or ``"per-role"`` WHILE some role holds tool authority. The
       economic premise of the design is the CONSTANT prefix, and an arm whose
       system message toggles per role is measuring something else. Owner
       decision 53 (2026-09-20, after EFF-1 read HARMFUL and repair form 0-B
       withdrew the Reviewer's tool): an episode in which NO role holds tool
       authority renders no tools array anywhere, so its prefix is constant by
       construction and the key is admitted under per-role rendering;
    8. the key armed on a carrier whose descriptor declares no
       ``knowledge_layer`` (today: both Earnings descriptors, base-lock
       finding F-1).
    """

    from .knowledge_index import (  # noqa: PLC0415
        EXEMPLAR_STORE_ROLE,
        KnowledgeIndexError,
        knowledge_index_profile,
        parse_knowledge_index_config,
        parse_role_budget_override,
        validate_knowledge_index_config,
    )

    # Refusal 8 first: it is the cheapest, and a carrier with no knowledge
    # layer has no index to declare a granularity over.
    declared_carrier = values.get("carrier_lock_key")
    if not isinstance(declared_carrier, str) or not declared_carrier:
        raise ValueError(
            "native_episode.knowledge_index requires a declared carrier_lock_key "
            "whose descriptor names a knowledge layer"
        )
    from ..data.carriers import get_carrier_descriptor  # noqa: PLC0415

    try:
        descriptor = get_carrier_descriptor(declared_carrier)
    except Exception as error:  # noqa: BLE001 - the loader's own error type
        raise ValueError(
            f"native_episode.knowledge_index names carrier {declared_carrier!r}: "
            f"{error}"
        ) from error
    task = getattr(descriptor, "task", None)
    if task is None or not getattr(task, "knowledge_layer", None):
        raise ValueError(
            f"native_episode.knowledge_index is armed on carrier "
            f"{declared_carrier!r}, whose descriptor declares no knowledge_layer; "
            "an index is a catalogue of a knowledge layer and there is none to "
            "catalogue"
        )
    # Item E27: the carrier equality test against one literal becomes a
    # profile lookup, and the view check becomes membership in that
    # profile's released view ids -- the same two facts refusal 1 already
    # states, now read from a table keyed by carrier rather than from a
    # constant defined for one carrier alone. Refusals 7 and 8 are unchanged
    # in meaning and position.
    try:
        profile = knowledge_index_profile(declared_carrier)
    except ValueError as error:
        raise ValueError(
            f"native_episode.knowledge_index names carrier {declared_carrier!r}: "
            f"{error}"
        ) from error
    if not isinstance(block, Mapping):
        raise ValueError("native_episode.knowledge_index must be an object")
    declared_view = block.get("view")
    if declared_view not in profile.view_ids:
        raise ValueError(
            f"the knowledge-index carrier profile for {profile.carrier!r} names "
            f"released view id(s) {sorted(profile.view_ids)}, but this config "
            f"declares knowledge_index.view {declared_view!r}"
        )
    if "roles" in block:
        # Two spellings of one override is how a cell ends up with two
        # identities: the per-role table is declared ON THE ROLE ROW, beside
        # the role it budgets, exactly as E18's acquisition seat is.
        raise ValueError(
            "native_episode.knowledge_index.roles and "
            "native_episode.roles.<role>.knowledge_index_budget are two spellings "
            "of one override; declare it on the role row"
        )
    overrides = {
        kind: raw_roles[kind]["knowledge_index_budget"]
        for kind in kinds
        if isinstance(raw_roles.get(kind), Mapping)
        and "knowledge_index_budget" in raw_roles[kind]
    }
    composed = dict(block)
    try:
        if overrides:
            composed["roles"] = {
                role: parse_role_budget_override(value, role=role)
                for role, value in overrides.items()
            }
        plan = parse_knowledge_index_config(composed)
        canonical = validate_knowledge_index_config(composed)
    except KnowledgeIndexError as error:
        raise ValueError(f"native_episode.knowledge_index is invalid: {error}") from error
    # Refusal 7 (owner decision 53: a tool-free episode is constant by construction).
    if tool_schema_rendering != "constant" and tool_authority_present:
        raise ValueError(
            "native_episode.knowledge_index requires "
            "native_episode.tool_schema_rendering 'constant' while a role holds tool "
            "authority: the index is free only while the prefix is constant, and an "
            "arm whose system message toggles twice per row is measuring something else"
        )
    stores = values.get("knowledge_stores") or {}
    if not isinstance(stores, Mapping):
        raise ValueError("knowledge_stores must be a mapping")
    exemplar_armed = False
    candidate_supplies: list[tuple[str, str, Mapping]] = []
    for store_id, store in stores.items():
        if not isinstance(store, Mapping):
            raise ValueError("a knowledge store must be a mapping")
        supplies = store.get("phase_supply") or {}
        if store.get("store_role") == EXEMPLAR_STORE_ROLE and supplies:
            exemplar_armed = True
        candidates = store.get("candidate_supply") or {}
        if not isinstance(candidates, Mapping):
            raise ValueError("candidate_supply must be a mapping")
        for phase_id, spec in candidates.items():
            if not isinstance(spec, Mapping):
                raise ValueError("a candidate supply must be a mapping")
            candidate_supplies.append((str(store_id), str(phase_id), spec))
    # Refusal 3.
    for role_budget in (plan.budget, *plan.role_budgets.values()):
        if role_budget.expansion["exemplar"] > 0 and not exemplar_armed:
            raise ValueError(
                "native_episode.knowledge_index.expansion_budget.exemplar is positive "
                f"but no store of role {EXEMPLAR_STORE_ROLE!r} is armed on any phase; "
                "the expansion block would name exemplars this row never retrieved"
            )
    # Refusals 4 and 5: a pointer may never name more candidates than the
    # projection produced, and an expansion may never read more cards than
    # the candidate supply selected.
    for role_budget in (plan.budget, *plan.role_budgets.values()):
        for store_id, phase_id, spec in candidate_supplies:
            max_candidates = spec.get("max_candidates")
            if isinstance(max_candidates, int) and not isinstance(max_candidates, bool):
                if role_budget.pointer["intent"] > max_candidates:
                    raise ValueError(
                        "native_episode.knowledge_index.pointer_budget.intent "
                        f"({role_budget.pointer['intent']}) exceeds "
                        f"{store_id}.candidate_supply.{phase_id}.max_candidates "
                        f"({max_candidates})"
                    )
            max_total = spec.get("max_total_values")
            if isinstance(max_total, int) and not isinstance(max_total, bool):
                if role_budget.expansion["slot_card"] > max_total:
                    raise ValueError(
                        "native_episode.knowledge_index.expansion_budget.slot_card "
                        f"({role_budget.expansion['slot_card']}) exceeds "
                        f"{store_id}.candidate_supply.{phase_id}.max_total_values "
                        f"({max_total})"
                    )
        if (
            role_budget.expansion["slot_card"] > 0 or role_budget.pointer["slot"] > 0
        ) and not candidate_supplies:
            raise ValueError(
                "native_episode.knowledge_index budgets slot pointers or slot cards "
                "but no store declares a candidate_supply; there is no projection to "
                "bind slot types to the candidates"
            )
    return canonical
