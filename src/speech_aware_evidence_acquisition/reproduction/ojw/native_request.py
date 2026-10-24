"""Bind public OpenJiuwen turns to the shared prepared speech request path."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from ...core.model.native_framework_history import framework_contact_instruction
from ...e0.d2_leakage import ARM_VISIBLE_FIELDS
from ...rails.core_client import CoreCompletion, FrozenCoreClient, PreparedCoreRequest
from ...core.reasoning_knobs import (
    ReasoningKnobError, answer_only_decoding, fallback_receipt, fallback_reserve, last_cost_record,
    resolve_node_decoding,
)
from .native_roles import (
    FROZEN_CORE_CALLBACK_MODEL, NativeRoleContactContext, NativeRoleModelRequest,
)


class NativeSpeechRequestError(ValueError):
    """Framework inputs differ from their registered speech/role binding."""


def _bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


#: Keys ``compose_solver_sample_decoding_params`` requires, exactly -- the
#: same shape ``rails.native_episode_config.SOLVER_DECODING_OVERRIDE_KEYS``
#: validates in the composed configuration.
SOLVER_DECODING_OVERRIDE_KEYS = frozenset({"temperature", "seed_offset"})
#: Optional key (VER-1a): ``greedy_first`` -- see
#: ``rails.native_episode_config.SOLVER_DECODING_OVERRIDE_OPTIONAL_KEYS``.
SOLVER_DECODING_OVERRIDE_OPTIONAL_KEYS = frozenset({"greedy_first"})


def compose_solver_sample_decoding_params(
    base_decoding_params: Mapping[str, object],
    *,
    fragment_seed: int,
    decoding_overrides: Mapping[str, object],
    sample_index: int,
) -> dict[str, object]:
    """Compose one grouped-Solver sample's decoding params (E2, SLURP v2 base
    program M2).

    ``base_decoding_params`` is the fragment's own greedy decoding block for
    every other role and contact. This function changes exactly two keys --
    ``temperature`` (the registered override) and ``seed`` (``fragment_seed +
    seed_offset + sample_index``) -- and carries every other key (including
    ``max_tokens``, ``tool_choice``, ``parallel_tool_calls`` and any
    ``id_slot`` per-sample sentinel) through unchanged. The N sibling
    requests of one Solver visit are therefore byte-identical except
    ``seed`` (and ``temperature`` versus the fragment's own greedy value),
    because they differ only by which two keys this function overwrites.
    """

    if isinstance(fragment_seed, bool) or not isinstance(fragment_seed, int):
        raise NativeSpeechRequestError("fragment seed must be an integer")
    if (
        isinstance(sample_index, bool)
        or not isinstance(sample_index, int)
        or sample_index < 0
    ):
        raise NativeSpeechRequestError("sample_index must be a nonnegative integer")
    if (
        not isinstance(decoding_overrides, Mapping)
        or not SOLVER_DECODING_OVERRIDE_KEYS <= set(decoding_overrides)
        or not set(decoding_overrides)
        <= SOLVER_DECODING_OVERRIDE_KEYS | SOLVER_DECODING_OVERRIDE_OPTIONAL_KEYS
    ):
        raise NativeSpeechRequestError(
            "decoding_overrides must carry exactly temperature and seed_offset "
            "(and optionally greedy_first)"
        )
    greedy_first = decoding_overrides.get("greedy_first", False)
    if "greedy_first" in decoding_overrides and greedy_first is not True:
        raise NativeSpeechRequestError("decoding_overrides.greedy_first must be true")
    temperature = decoding_overrides["temperature"]
    seed_offset = decoding_overrides["seed_offset"]
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
        raise NativeSpeechRequestError("decoding_overrides.temperature must be a number")
    if isinstance(seed_offset, bool) or not isinstance(seed_offset, int) or seed_offset < 0:
        raise NativeSpeechRequestError(
            "decoding_overrides.seed_offset must be a nonnegative integer"
        )
    composed = dict(base_decoding_params)
    # VER-1a: under ``greedy_first`` sample 0 keeps the fragment's own greedy
    # temperature (the base block's literal, 0) and only its pinned seed is
    # set, so it is request-identical to the single-sample delivery except the
    # ``seed`` field, which a temperature-0 request does not consume.
    if not (greedy_first and sample_index == 0):
        composed["temperature"] = temperature
    composed["seed"] = fragment_seed + seed_offset + sample_index
    return composed


def _model_messages(messages: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Remove only the installed framework's non-model routing metadata."""
    normalized = []
    for original in messages:
        if not isinstance(original, Mapping):
            raise NativeSpeechRequestError("framework message must be an object")
        message = dict(original)
        if "metadata" in message:
            metadata = message.pop("metadata")
            if not isinstance(metadata, Mapping):
                raise NativeSpeechRequestError("framework routing metadata is malformed")
            if metadata:
                context_id = metadata.get("context_message_id")
                if (
                    message.get("role") == "system"
                    or set(metadata) != {"context_message_id"}
                    or not isinstance(context_id, str) or len(context_id) != 32
                    or any(c not in "0123456789abcdef" for c in context_id)
                ):
                    raise NativeSpeechRequestError("unregistered framework message metadata")
        normalized.append(message)
    return normalized


def _assert_framework_schemas(
    visible_schemas: Sequence[Mapping[str, object]],
    selected: Sequence[Mapping[str, object]],
    *,
    constant_rendering: bool,
) -> None:
    """Check the framework's visible schemas against the rendered array.

    ``per-role`` (``constant_rendering`` False, every contact written before
    E17) is the historical rule, unchanged: the two arrays must be the same
    length and pair up exactly, in order.

    ``constant`` (E17) renders a superset, so the rule becomes containment:
    every schema the framework advertised to THIS role must appear in the
    rendered array under the same name, with the same description and the
    same parameters. A rendered array that does not cover the framework's
    own scope is still refused -- rendering may only ever be wider.
    """

    if not constant_rendering:
        if len(visible_schemas) != len(selected):
            raise NativeSpeechRequestError("framework schemas do not match the selected scope")
        pairs = list(zip(visible_schemas, selected, strict=True))
    else:
        by_name: dict[str, Mapping[str, object]] = {}
        for schema in selected:
            if not isinstance(schema, Mapping) or not isinstance(schema.get("function"), Mapping):
                raise NativeSpeechRequestError("framework tool schema is malformed")
            name = schema["function"].get("name")
            if not isinstance(name, str) or not name or name in by_name:
                raise NativeSpeechRequestError("rendered tool schemas are not uniquely named")
            by_name[name] = schema
        pairs = []
        for visible in visible_schemas:
            if not isinstance(visible, Mapping):
                raise NativeSpeechRequestError("framework tool schema is malformed")
            schema = by_name.get(visible.get("name"))
            if schema is None:
                raise NativeSpeechRequestError(
                    "framework schemas do not match the selected scope"
                )
            pairs.append((visible, schema))
    for visible, schema in pairs:
        if (
            not isinstance(visible, Mapping) or not isinstance(schema, Mapping)
            or not isinstance(schema.get("function"), Mapping)
        ):
            raise NativeSpeechRequestError("framework tool schema is malformed")
        function = schema["function"]
        if any(visible.get(key) != function.get(key) for key in ("name", "description", "parameters")):
            raise NativeSpeechRequestError("framework tool schema differs from the registered tool")


@dataclass(frozen=True)
class NativeRoleSpeechBinding:
    """One caller-owned task state, rendered through the existing TaskAdapter."""

    role_id: str
    sample_id: str
    role_query: str
    base_messages: Sequence[Mapping[str, object]]
    core_kwargs: Mapping[str, object]
    tool_names: tuple[str, ...]
    local_tool_result_ids: tuple[str, ...] = ()
    query_source: str = "speech_features"
    # E17 (2026-09-19, throughput lever L1): the ordered tool names this
    # contact RENDERS, when that differs from the ordered tool names this
    # contact may CALL. ``None`` -- every binding written before E17 and
    # every ``tool_schema_rendering`` ``"per-role"`` episode -- renders
    # exactly ``tool_names``, byte-identically to before this field existed.
    # Set, it must CONTAIN ``tool_names``: rendering may only ever be wider
    # than authority, never narrower, and authority is enforced entirely
    # elsewhere (``native_roles._RoleAuthorityRail``, plus the
    # ``tool_choice`` this binding still derives from ``tool_names`` alone).
    rendered_tool_names: tuple[str, ...] | None = None
    _messages_bytes: bytes = field(init=False, repr=False)
    _kwargs_bytes: bytes = field(init=False, repr=False)

    def __post_init__(self):
        for value in (self.role_id, self.sample_id, self.role_query):
            if not isinstance(value, str) or not value:
                raise NativeSpeechRequestError("role, sample and query must be nonempty")
        for values in (self.tool_names, self.local_tool_result_ids):
            if (
                not isinstance(values, tuple) or len(set(values)) != len(values)
                or any(not isinstance(x, str) or not x for x in values)
            ):
                raise NativeSpeechRequestError("tool and local result IDs must be ordered unique tuples")
        if self.query_source not in {"speech_features", "speech_audio"}:
            raise NativeSpeechRequestError("unsupported speech query source")
        if self.rendered_tool_names is not None:
            rendered = self.rendered_tool_names
            if (
                not isinstance(rendered, tuple)
                or not rendered
                or len(set(rendered)) != len(rendered)
                or any(not isinstance(name, str) or not name for name in rendered)
            ):
                raise NativeSpeechRequestError(
                    "rendered tool names must be a nonempty ordered unique tuple"
                )
            if not set(self.tool_names) <= set(rendered):
                raise NativeSpeechRequestError(
                    "rendered tool names must contain every tool this role may call"
                )
        kwargs = dict(self.core_kwargs)
        reserved = {
            "agent_contact_id", "contact_instruction", "tool_names", "prepare_only",
            "text_only_sample_id", "speech_feature_sample_id", "raw_agent_sample_id",
        }
        if set(kwargs) & reserved:
            raise NativeSpeechRequestError("binding overrides a controlled request field")
        if "agent_state" not in kwargs:
            raise NativeSpeechRequestError("binding must name the complete ordered agent state")
        messages = list(self.base_messages)
        if (
            len(messages) != 2 or messages[0].get("role") != "system"
            or not isinstance(messages[0].get("content"), str)
            or messages[1].get("role") != "user"
        ):
            raise NativeSpeechRequestError("binding requires shared system/user speech messages")
        object.__setattr__(self, "_messages_bytes", _bytes(messages))
        object.__setattr__(self, "_kwargs_bytes", _bytes(kwargs))

    def messages(self):
        return json.loads(self._messages_bytes)

    def kwargs(self):
        return json.loads(self._kwargs_bytes)


@dataclass(frozen=True)
class PreparedNativeRoleContact:
    """Actual immutable request and rendered body exposed for existing fit checks."""

    request: PreparedCoreRequest
    role_request_bytes: bytes = field(repr=False)
    body_bytes: bytes
    owner: object = field(repr=False, compare=False)
    # E2 (SLURP v2 base program M2): the group sample index this contact was
    # composed for, or None for every non-grouped contact -- exposed
    # directly (not only inside role_request_bytes) so a caller can attach
    # it to custody without decoding JSON.
    sample_index: int | None = None
    # E17: the ordered tool names this contact actually RENDERED, when they
    # differ from the ones it may call. None for every ``per-role`` contact,
    # which is every contact written before E17.
    rendered_tool_names: tuple[str, ...] | None = None
    # E20 (2026-09-19): the exact binding this contact was composed from,
    # so a dispatch-time context-fit check can narrow it and re-prepare
    # WITHOUT re-running the caller's binding provider -- which settles
    # episode state, may spend a cleaning contact, and is not idempotent.
    # Excluded from equality and repr: it is the same object the provider
    # already returned, carried for reuse rather than as new custody.
    binding: object = field(default=None, repr=False, compare=False)

    @property
    def role_request(self) -> NativeRoleModelRequest:
        document = json.loads(self.role_request_bytes)
        return NativeRoleModelRequest(
            role_id=document["role_id"],
            context=NativeRoleContactContext(**document["context"]),
            messages=tuple(document["messages"]),
            tool_schemas=tuple(document["tool_schemas"]),
            visible_tool_names=tuple(document["visible_tool_names"]),
            decoding_controls=document["decoding_controls"],
        )

    def rendered_body(self) -> dict[str, object]:
        return json.loads(self.body_bytes)


class MeteredNativeSpeechRequest:
    """Use one flight client; delegate state and contact custody to its caller.

    The binding provider uses the existing TaskAdapter/AgentRuntimeContext.
    The completion sink uses the existing phase-state sealing path. This
    adapter neither stores conversation history nor executes tool backends.
    """

    def __init__(
        self, *, client: FrozenCoreClient,
        binding_provider: Callable[[NativeRoleModelRequest], NativeRoleSpeechBinding],
        render_request: Callable[[bytes], Mapping[str, object]],
        completion_sink: Callable[[NativeRoleModelRequest, CoreCompletion], None],
        solver_role_id: str | None = None,
        solver_sampling: Mapping[str, object] | None = None,
        role_completion_caps: Mapping[str, int] | None = None,
        role_thinking_policy: Mapping[str, Mapping[str, object]] | None = None,
        branch_thinking_policy: Mapping[str, Mapping[str, Mapping[str, object]]] | None = None,
        solver_arm_decoding: Mapping[str, Mapping[str, object]] | None = None,
        solver_arm_decoding_role_id: str | None = None,
        branch_sampling: Mapping[str, Mapping[str, Mapping[str, object]]] | None = None,
    ):
        if not isinstance(client, FrozenCoreClient):
            raise NativeSpeechRequestError("use the flight's existing FrozenCoreClient")
        if not all(callable(x) for x in (binding_provider, render_request, completion_sink)):
            raise NativeSpeechRequestError("binding, rendering and completion hooks are required")
        if (solver_role_id is None) != (solver_sampling is None):
            raise NativeSpeechRequestError(
                "solver sampling requires both a role id and its sampling config"
            )
        if solver_sampling is not None:
            if not isinstance(solver_role_id, str) or not solver_role_id:
                raise NativeSpeechRequestError("solver_role_id must be a non-empty string")
            if (
                not isinstance(solver_sampling, Mapping)
                or set(solver_sampling) != {"fragment_seed", "decoding_overrides"}
            ):
                raise NativeSpeechRequestError(
                    "solver_sampling must carry exactly fragment_seed and decoding_overrides"
                )
        # Item E39 (2026-09-22): ``{role_id: max_tokens}`` for the roles whose
        # configuration declares a completion cap of their own. Empty or None
        # -- every adapter written before E39 and every config that declares
        # no cap -- leaves every composed request byte-identical.
        caps = dict(role_completion_caps or {})
        for role_id, cap in caps.items():
            if (
                not isinstance(role_id, str)
                or not role_id
                or isinstance(cap, bool)
                or not isinstance(cap, int)
                or cap < 1
            ):
                raise NativeSpeechRequestError(
                    "role_completion_caps must map role ids to positive integers"
                )
        self._role_completion_caps = caps
        # Decision 283 A: ``{role phase id: thinking override}``; None or empty leaves every request as composed before.
        policy = dict(role_thinking_policy or {})
        if any(not isinstance(role_id, str) or not role_id or not isinstance(entry, Mapping) for role_id, entry in policy.items()):
            raise NativeSpeechRequestError("role_thinking_policy must map role ids to override mappings")
        self._role_thinking_policy = policy
        # NX-T R1 (2026-10-13): ``{perception branch id: {role phase id: thinking override}}`` -- the per-ARM override of a
        # thinking-policy column, composed at this same seam on top of the role-level one. None or empty (every adapter written
        # before NX-T R1) leaves every composed request as before.
        branch_policy = {
            str(branch_id): dict(entries) for branch_id, entries in dict(branch_thinking_policy or {}).items()
        }
        if any(
            not branch_id or not isinstance(entries, Mapping) or not entries
            or any(not isinstance(role_id, str) or not role_id or not isinstance(entry, Mapping)
                   for role_id, entry in entries.items())
            for branch_id, entries in branch_policy.items()
        ):
            raise NativeSpeechRequestError(
                "branch_thinking_policy must map branch ids to {role id: override mapping} maps"
            )
        self._branch_thinking_policy = branch_policy
        # NX-T R4 (2026-10-18): ``{Solver arm id: {sampling parameter: value}}`` -- the per-ARM sampling override of a decoding
        # column, composed at this same seam and only on the Solver role's contacts. Closed set and bounds are the receipt
        # module's table; None or empty (every adapter written before NX-T R4) leaves every composed request as before.
        from ...rails.native_episode_receipt import decoding_override_error  # noqa: PLC0415

        arm_decoding = {str(arm_id): dict(entry) for arm_id, entry in dict(solver_arm_decoding or {}).items()}
        for arm_id, entry in arm_decoding.items():
            reason = decoding_override_error(entry)
            if not arm_id or reason is not None:
                raise NativeSpeechRequestError(f"solver_arm_decoding[{arm_id!r}] is invalid: {reason or 'empty arm id'}")
        if bool(arm_decoding) != (solver_arm_decoding_role_id is not None) or (
            solver_arm_decoding_role_id is not None
            and (not isinstance(solver_arm_decoding_role_id, str) or not solver_arm_decoding_role_id)
        ):
            raise NativeSpeechRequestError("solver_arm_decoding requires exactly one non-empty solver_arm_decoding_role_id")
        self._solver_arm_decoding = arm_decoding
        self._solver_arm_decoding_role_id = solver_arm_decoding_role_id
        # Decision 338 (2026-10-19): {Perception branch id: {role phase id: {"decoding": {...}, "seed_offsets": [...]}}} -- the
        # per-BRANCH sampling axes of a sampling column (rails.supply_variants.sampling_decoding_table), composed at this same
        # seam. A contact bound to such a branch and role carries a sample_index: sample 0 keeps the lock's greedy request
        # (and its seed), sample i >= 1 gets the declared sampling parameters and seed = lock seed + offset i. None or empty
        # (every adapter written before decision 338) leaves every composed request as before.
        sampling_table: dict[str, dict[str, dict[str, object]]] = {}
        for branch_id, per_role in dict(branch_sampling or {}).items():
            if not isinstance(branch_id, str) or not branch_id or not isinstance(per_role, Mapping) or not per_role:
                raise NativeSpeechRequestError("branch_sampling must map branch ids to non-empty {role id: axis} maps")
            sampling_table[branch_id] = {}
            for role_id, axis in per_role.items():
                if (
                    not isinstance(role_id, str) or not role_id or not isinstance(axis, Mapping)
                    or set(axis) != {"decoding", "seed_offsets"}
                    or decoding_override_error(axis["decoding"]) is not None
                    or not isinstance(axis["seed_offsets"], Sequence) or isinstance(axis["seed_offsets"], (str, bytes))
                    or any(isinstance(o, bool) or not isinstance(o, int) or o < 1 for o in axis["seed_offsets"])
                ):
                    raise NativeSpeechRequestError(f"branch_sampling[{branch_id!r}][{role_id!r}] is invalid")
                sampling_table[branch_id][role_id] = {
                    "decoding": dict(axis["decoding"]), "seed_offsets": [int(o) for o in axis["seed_offsets"]],
                }
        self._branch_sampling = sampling_table
        # {agent contact id: the integer seed the composed request carried}, written for every contact bound to a sampling
        # axis (sample 0 included, whose seed is the lock's own). The runner reads it to seal each sample's seed from the
        # request that was actually composed, never from a recomputation.
        self.branch_sample_seeds: dict[str, int] = {}
        self._owner = object()
        self._client = client
        self._binding_provider = binding_provider
        self._render_request = render_request
        self._completion_sink = completion_sink
        self._solver_role_id = solver_role_id
        self._solver_sampling = solver_sampling

    def prepare(
        self,
        request: NativeRoleModelRequest,
        *,
        binding_override: "NativeRoleSpeechBinding | None" = None,
        answer_only: bool = False,
    ) -> PreparedNativeRoleContact:
        """Compose one immutable request from this caller's task state.

        ``binding_override`` (E20, 2026-09-19) re-composes a contact from an
        ALREADY OBTAINED binding instead of asking the provider again. It
        exists for exactly one caller -- the dispatch-time context-fit
        check, which narrows a binding's evidence blocks and needs the same
        request built again over fewer of them. The provider is not
        idempotent (it settles episode state and may spend a cleaning
        contact), so calling it twice for one contact is a defect, not an
        option.
        """

        binding = (
            self._binding_provider(request) if binding_override is None
            else binding_override
        )
        if not isinstance(binding, NativeRoleSpeechBinding):
            raise NativeSpeechRequestError("binding provider returned no speech binding")
        if (
            request.role_id != binding.role_id
            or request.context.sample_id != binding.sample_id
            or request.visible_tool_names != binding.tool_names
        ):
            raise NativeSpeechRequestError("framework role, sample or tool scope differs")
        messages = binding.messages()
        framework = _model_messages(request.messages)
        if (
            len(framework) < 2
            or framework[0] != messages[0]
            or framework[1] != {"role": "user", "content": binding.role_query}
        ):
            raise NativeSpeechRequestError("framework system or original query differs")
        kwargs = binding.kwargs()
        decoding = dict(kwargs.get("decoding_params") or {})
        expected_choice = "auto" if binding.tool_names else "none"
        if decoding.get("tool_choice", expected_choice) != expected_choice:
            raise NativeSpeechRequestError("registered tool choice differs from role scope")
        if decoding.get("parallel_tool_calls", False) is not False:
            raise NativeSpeechRequestError("this role binding requires sequential native calls")
        # The registered flight owns decoding settings. Framework defaults
        # may repeat them, but cannot silently change the actual request.
        framework_controls = dict(request.decoding_controls)
        if "model" in framework_controls:
            if framework_controls.pop("model") != FROZEN_CORE_CALLBACK_MODEL:
                raise NativeSpeechRequestError("framework model routing differs from the frozen callback")
        for key, value in framework_controls.items():
            if key not in decoding or decoding[key] != value:
                raise NativeSpeechRequestError("framework decoding override is not registered: " + key)
        native_arm = "tool_schemas" in ARM_VISIBLE_FIELDS[self._client.arm]
        if native_arm:
            decoding.update(tool_choice=expected_choice, parallel_tool_calls=False)
        else:
            if binding.tool_names:
                raise NativeSpeechRequestError("ordinary arm cannot expose native tools")
            decoding.pop("tool_choice", None)
            decoding.pop("parallel_tool_calls", None)
        # E2 (SLURP v2 base program M2): compose this Solver sample's
        # decoding params from the fragment's greedy base plus the
        # registered override, at request-composition time and nowhere
        # else -- the model fragment and serving-session identity never
        # change, only this one request's temperature/seed.
        sample_index = request.context.sample_index
        if self._solver_role_id is not None and request.role_id == self._solver_role_id:
            if sample_index is None:
                raise NativeSpeechRequestError(
                    "a grouped Solver contact requires a bound sample_index"
                )
            decoding = compose_solver_sample_decoding_params(
                decoding,
                fragment_seed=self._solver_sampling["fragment_seed"],
                decoding_overrides=self._solver_sampling["decoding_overrides"],
                sample_index=sample_index,
            )
        elif sample_index is not None and not self._binds_branch_sample(request):
            raise NativeSpeechRequestError(
                "only the registered Solver role may bind a sample_index"
            )
        # Item E39 (2026-09-22): this role's own completion cap, composed at
        # request-composition time and nowhere else -- the same seam E2's
        # Solver overrides are composed at, and for the same reason: the model
        # fragment and the serving-session identity never change, only this
        # one request's ``max_tokens``. The loader has already refused a cap
        # wider than the serving geometry's own, so this only ever narrows.
        cap = self._role_completion_caps.get(request.role_id)
        if cap is not None:
            decoding["max_tokens"] = cap
        # Decision 283 A: this role's own thinking override, composed at the same seam and nowhere else. A role with no entry
        # (and every config without a policy) keeps the fragment's folded reasoning fields exactly.
        if request.role_id in self._role_thinking_policy:
            try:
                decoding = resolve_node_decoding(decoding, self._role_thinking_policy, request.role_id)
            except ReasoningKnobError as error:
                raise NativeSpeechRequestError(str(error)) from error
        # NX-T R1: this contact's ARM override (the per-node thinking policy of the Perception branch it belongs to), composed after
        # the role-level one. The delivering branch and the twin have no entry, so their requests are the locked plan's.
        arm_id = getattr(request.context, "perception_branch_id", None)
        if arm_id is not None and arm_id in self._branch_thinking_policy:
            arm_policy = self._branch_thinking_policy[arm_id]
            if request.role_id in arm_policy:
                try:
                    decoding = resolve_node_decoding(decoding, arm_policy, request.role_id)
                except ReasoningKnobError as error:
                    raise NativeSpeechRequestError(str(error)) from error
        # Decision 338: this contact's BRANCH sampling axis (a sampling column's Perception or Solver samples), composed after the
        # role-level and thinking fields and before the answer-only re-ask, so a re-ask keeps the sample's own decoding.
        if self._binds_branch_sample(request):
            if sample_index is None:
                raise NativeSpeechRequestError("a sampling-branch contact requires a bound sample_index")
            axis = self._branch_sampling[arm_id][request.role_id]
            if sample_index > len(axis["seed_offsets"]):
                raise NativeSpeechRequestError("sampling-branch sample_index exceeds the declared sample count")
            if sample_index >= 1:
                lock_seed = decoding.get("seed")
                if isinstance(lock_seed, bool) or not isinstance(lock_seed, int):
                    raise NativeSpeechRequestError("a sampling-branch contact needs the fragment's integer lock seed")
                decoding.update(axis["decoding"])
                decoding["seed"] = lock_seed + axis["seed_offsets"][sample_index - 1]
            composed_seed = decoding.get("seed")
            if isinstance(composed_seed, bool) or not isinstance(composed_seed, int):
                raise NativeSpeechRequestError("a sampling-branch contact needs the fragment's integer lock seed")
            self.branch_sample_seeds[request.context.agent_contact_id] = composed_seed
        # NX-T R4: this Solver contact's ARM sampling override (a decoding column's candidate arm), composed after every
        # role-level field and BEFORE the answer-only re-ask, so the re-ask of an arm's contact keeps the arm's sampling. The
        # delivering arm and the twin have no entry: their requests are the locked plan's, byte for byte.
        solver_arm = getattr(request.context, "variant_arm_id", None)
        if (
            solver_arm is not None
            and request.role_id == self._solver_arm_decoding_role_id
            and solver_arm in self._solver_arm_decoding
        ):
            decoding.update(self._solver_arm_decoding[solver_arm])
        if answer_only:
            # The one receipted answer-only re-ask (decision 278): thinking off, max_tokens = the reserve.
            try:
                decoding = answer_only_decoding(decoding)
            except ReasoningKnobError as error:
                raise NativeSpeechRequestError(str(error)) from error
        kwargs["decoding_params"] = decoding
        instruction = framework_contact_instruction(
            role_id=binding.role_id, sample_id=binding.sample_id,
            contact_id=request.context.agent_contact_id, messages=framework,
            local_tool_result_ids=binding.local_tool_result_ids,
        )
        source_selector = (
            {"speech_feature_sample_id": binding.sample_id}
            if binding.query_source == "speech_features"
            else {"raw_agent_sample_id": binding.sample_id}
        )
        # E17: WHAT IS RENDERED versus WHAT MAY BE CALLED. ``rendered_names``
        # below is the rendering scope handed to the client's registered
        # superset selector; ``binding.tool_names`` remains the authority
        # scope, and it alone decides the ``tool_choice`` checked above. The
        # two are the same object for every ``per-role`` contact, so nothing
        # here moves a byte without a ``constant`` episode.
        if binding.rendered_tool_names is not None and not native_arm:
            raise NativeSpeechRequestError(
                "constant tool rendering requires a native tool-calling arm"
            )
        rendered_names = (
            binding.tool_names if binding.rendered_tool_names is None
            else binding.rendered_tool_names
        )
        prepared = self._client.prepare_request(
            messages, **kwargs, **source_selector,
            agent_contact_id=request.context.agent_contact_id,
            contact_instruction=instruction,
            tool_names=(
                None if not native_arm
                else rendered_names
            ),
        )
        payload = prepared.as_payload()
        selected = payload.get("tool_schemas", [])
        _assert_framework_schemas(
            request.tool_schemas,
            selected,
            constant_rendering=binding.rendered_tool_names is not None,
        )
        # The authoritative transport validates and renders the SAME object
        # that dispatch consumes; capacity checks can inspect this body.
        body = self._render_request(prepared.payload_bytes)
        # Item E42 (2026-09-25): the declared supply-variant arm this contact was
        # composed for, recorded in the role custody document ONLY when it is
        # set. Conditional on purpose: every contact of every episode form
        # written before E42 carries no arm, so its ``role_request_bytes`` stay
        # byte-identical to the pre-E42 tree's, and
        # ``PreparedNativeRoleContact.role_request`` reconstructs the context
        # from the dataclass default.
        arm_context: dict[str, object] = {
            "sample_id": request.context.sample_id,
            "agent_contact_id": request.context.agent_contact_id,
            "evidence_pins": dict(request.context.evidence_pins),
            "budget_id": request.context.budget_id,
            "sample_index": sample_index,
        }
        variant_arm_id = getattr(request.context, "variant_arm_id", None)
        if variant_arm_id is not None:
            arm_context["variant_arm_id"] = variant_arm_id
        # Same-flight instrument, PHASE 2 (merge set C): the declared
        # Perception branch this contact was composed for -- variant_arm_id's
        # own twin, and recorded in the role custody document the SAME
        # conditional way, for the same reason: every contact of every
        # episode form written before phase 2 carries no branch, so its
        # ``role_request_bytes`` stay byte-identical to the pre-phase-2
        # tree's.
        perception_branch_id = getattr(request.context, "perception_branch_id", None)
        if perception_branch_id is not None:
            arm_context["perception_branch_id"] = perception_branch_id
        role_bytes = _bytes({
            "role_id": request.role_id,
            "context": arm_context,
            "messages": framework,
            "tool_schemas": list(request.tool_schemas),
            "visible_tool_names": list(request.visible_tool_names),
            "decoding_controls": framework_controls,
        })
        return PreparedNativeRoleContact(
            prepared, role_bytes, _bytes(body), self._owner, sample_index,
            binding.rendered_tool_names, binding,
        )

    def _binds_branch_sample(self, request: NativeRoleModelRequest) -> bool:
        branch_id = getattr(request.context, "perception_branch_id", None)
        return branch_id is not None and request.role_id in self._branch_sampling.get(branch_id, {})

    def dispatch(self, prepared: PreparedNativeRoleContact) -> CoreCompletion:
        if not isinstance(prepared, PreparedNativeRoleContact) or prepared.owner is not self._owner:
            raise NativeSpeechRequestError("dispatch requires this adapter's prepared native contact")
        completion = self._client.complete_prepared_with_metadata(prepared.request)
        completion = self._answer_only_fallback(prepared, completion)
        self._completion_sink(prepared.role_request, completion)
        return completion

    def _answer_only_fallback(
        self, prepared: PreparedNativeRoleContact, completion: CoreCompletion,
    ) -> CoreCompletion:
        """Decision 278 / 283 A: ONE receipted answer-only re-ask of a budgeted thinking contact that came back empty.

        Fires only when the rendered request carried a thinking budget with room for an answer, the delivered text is empty and
        the server stopped at its cap (finish reason ``length``; ``None`` when wire responses are not preserved). The re-ask is
        the same role contact re-composed with ``enable_thinking: false`` and ``max_tokens`` = the reserve, dispatched through
        the same client (metered, traced, and counted against the plan's model-call budget). Its completion replaces the empty
        one for the episode; the ``saea-thinking-answer-fallback-v1`` receipt binds both requests. If it is empty too, the
        caller sees that empty completion and the existing finite-completion disposition applies. No thinking text is carried.
        """

        if completion.text != "" or completion.tool_calls:
            return completion
        finish = completion.finish_reason
        if finish not in ("length", None):
            return completion
        # The payload's own decoding block is the request's source of truth (the rendered HTTP body carries the same values at top
        # level); reading it here keeps the check independent of how a caller renders the body.
        reserve = fallback_reserve(prepared.request.as_payload().get("decoding_params") or {})
        if reserve is None:
            return completion
        from ...core.tracing import get_current_trace_buffer  # noqa: PLC0415

        trace = get_current_trace_buffer()
        if trace is None:
            raise NativeSpeechRequestError("the answer-only fallback needs a current trace buffer for its receipt")
        first_id, first_cost = last_cost_record(trace)
        reask_prepared = self.prepare(
            prepared.role_request, binding_override=prepared.binding, answer_only=True,
        )
        second = self._client.complete_prepared_with_metadata(reask_prepared.request)
        second_id, second_cost = last_cost_record(trace)
        if second_id == first_id:
            raise NativeSpeechRequestError("the answer-only re-ask left no COST record")
        trace.emit(
            "TOOL", f"{completion.agent_contact_id}/reasoning-fallback",
            fallback_receipt(
                agent_contact_id=completion.agent_contact_id,
                first_request_id=completion.request_id, reask_request_id=second.request_id,
                first_finish_reason=finish if finish is not None else first_cost.get("finish_reason"),
                reask_finish_reason=second.finish_reason if second.finish_reason is not None else second_cost.get("finish_reason"),
                first_tokens=first_cost, reask_tokens=second_cost, reserve=reserve, answered=second.text != "",
            ),
        )
        return second

    def __call__(self, request: NativeRoleModelRequest) -> CoreCompletion:
        return self.dispatch(self.prepare(request))
