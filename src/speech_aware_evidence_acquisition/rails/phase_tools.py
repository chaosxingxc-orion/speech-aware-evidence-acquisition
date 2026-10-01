"""Bounded, opt-in task actions over the shared tool and state rails.

The native catalog remains system-invoked. This bridge explicitly records
whether its task-level selection came from a fixed policy or the frozen core;
no historical toolkit acquires model-selected semantics merely by registering.
"""

from __future__ import annotations
import json
import hashlib
from threading import Lock
from types import SimpleNamespace
from typing import Mapping
from .errors import RailsError
from .knowledge import AgentStateArtifact, content_hash
from .tools import resolve_tool, assert_pinned_hash
from .candidate_contract_lookup import (
    TOOL_ID as CANDIDATE_CONTRACT_TOOL,
    MAX_CANDIDATE_IDS,
    CandidateContractLookupError,
    CandidateContractLookupResult,
    CandidateContractRequest,
)
from .controllers import PhaseSupply, PhaseToolStep
from .experience_memory_runtime import (
    CORRECTIVE_MEMORY_TOOL,
    ExperienceMemorySelection,
)

from .speech_observation import (
    PREPARED_SPEECH_OBSERVATION_TOOL,
    SpeechObservationSelection,
)

LIVE_SPEECH_OBSERVATION_TOOL = "saea-tool-live-speech-observation-v1"
LIVE_SPEECH_SPAN_TOOL = "saea-tool-live-speech-span-v1"

TASK_CONTRACT_TOOL = "saea-tool-task-contract-v1"
PHASE_KNOWLEDGE_TOOL = "saea-tool-phase-knowledge-v1"
KNOWLEDGE_TARGET_TOOL = "saea-tool-knowledge-target-lookup-v1"
KNOWLEDGE_TOOLS = frozenset({PHASE_KNOWLEDGE_TOOL, KNOWLEDGE_TARGET_TOOL})
ACTION_TOOLS = frozenset(
    {TASK_CONTRACT_TOOL, PHASE_KNOWLEDGE_TOOL, CORRECTIVE_MEMORY_TOOL,
     PREPARED_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_OBSERVATION_TOOL,
     LIVE_SPEECH_SPAN_TOOL, CANDIDATE_CONTRACT_TOOL, KNOWLEDGE_TARGET_TOOL}
)
MODES = frozenset({"fixed", "core-choice", "native-tools"})
VIEWS = frozenset({"text", "speech", "paired"})


class PhaseToolError(RailsError):
    """An action is unavailable, unbound, or cannot be executed as declared."""


def _unique(values, allowed, field):
    if (
        not isinstance(values, list)
        or not values
        or any(not isinstance(v, str) or v not in allowed for v in values)
        or len(set(values)) != len(values)
    ):
        raise PhaseToolError(f"{field} must be a nonempty unique allowed list")
    return tuple(values)


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PhaseToolError(f"duplicate action key: {key}")
        result[key] = value
    return result


def load_knowledge_value_rendering(config):
    """Validate an explicit rendering choice independently of tool authority.

    Absence preserves historical automatic rendering. Canonical text is an
    opt-in common representation for matched tool-enabled/tool-free policies.
    This changes presentation only; source binding and tool scopes still apply.
    """
    if "knowledge_value_rendering" not in config:
        return None
    value = config["knowledge_value_rendering"]
    if value != "canonical-plain-v1" or not isinstance(value, str):
        raise PhaseToolError(
            "knowledge_value_rendering must be canonical-plain-v1 when declared"
        )
    return value


def load_phase_tool_specs(config, program):
    load_knowledge_value_rendering(config)
    raw = config.get("phase_tools")
    candidate_memory = config.get("candidate_experience_memory") is not None
    if raw is None or raw == {}:
        return {}
    if not isinstance(raw, Mapping):
        raise PhaseToolError("phase_tools must be a mapping")
    phases = program.phase_names()
    tool_phases = phases if getattr(program, "stop_rule", None) == "native-role-episode" else phases[:-1]
    specs = {}
    for phase, entry in raw.items():
        if phase not in tool_phases:
            raise PhaseToolError("phase_tools must name a nonfinal phase or a native role")
        if not isinstance(entry, Mapping) or set(entry) - {
            "mode",
            "allowed_tools",
            "knowledge_views",
            "fixed_action",
            "candidate_limit",
            "knowledge_values_per_candidate",
            "knowledge_value_limit",
            "knowledge_store_ids",
            "source_authority_role",
            "knowledge_target_axis", "knowledge_selection_mode", "max_calls_per_sample",
        }:
            raise PhaseToolError("phase_tools entry has unknown fields")
        mode = entry.get("mode")
        if not isinstance(mode, str) or mode not in MODES:
            raise PhaseToolError("phase_tools mode must be fixed, core-choice or native-tools")
        authority_role = entry.get("source_authority_role")
        if authority_role is not None and (
            mode != "native-tools"
            or not isinstance(authority_role, str)
            or not authority_role
        ):
            raise PhaseToolError(
                "source_authority_role requires native-tools and a nonempty role ID"
            )
        tools = _unique(entry.get("allowed_tools"), ACTION_TOOLS, "allowed_tools")
        views = _unique(
            entry.get("knowledge_views", ["text"]), VIEWS, "knowledge_views"
        )
        store_ids = entry.get("knowledge_store_ids")
        if store_ids is not None:
            if not set(tools) & KNOWLEDGE_TOOLS:
                raise PhaseToolError("knowledge_store_ids requires a knowledge tool")
            if (not isinstance(store_ids, list) or not store_ids
                    or any(not isinstance(item, str) or not item for item in store_ids)
                    or len(set(store_ids)) != len(store_ids)):
                raise PhaseToolError("knowledge_store_ids must be a nonempty unique list")
            store_ids = tuple(store_ids)
        additions = {}
        for field, choices in (("knowledge_target_axis", {"task", "slot-type"}),
                               ("knowledge_selection_mode", {"targeted", "reread"})):
            if field in entry:
                if KNOWLEDGE_TARGET_TOOL not in tools or not isinstance(entry[field], str) or entry[field] not in choices:
                    raise PhaseToolError(f"invalid {field} for target knowledge")
                additions[field] = entry[field]
        if "max_calls_per_sample" in entry:
            cap = entry["max_calls_per_sample"]
            if mode != "native-tools" or isinstance(cap, bool) or not isinstance(cap, int) or cap != 1:
                raise PhaseToolError("max_calls_per_sample currently supports exactly one native call")
            additions["max_calls_per_sample"] = cap
        candidate_limit = entry.get("candidate_limit")
        if set(tools) & {CANDIDATE_CONTRACT_TOOL, KNOWLEDGE_TARGET_TOOL}:
            if (
                isinstance(candidate_limit, bool)
                or not isinstance(candidate_limit, int)
                or not 1 <= candidate_limit <= MAX_CANDIDATE_IDS
            ):
                raise PhaseToolError(
                    "candidate lookup requires an explicit candidate_limit between 1 and 32"
                )
            if mode != "native-tools":
                raise PhaseToolError("candidate lookup currently requires native-tools mode")
        elif "candidate_limit" in entry:
            raise PhaseToolError("candidate_limit requires the candidate lookup tool")
        target_limits = {}
        if KNOWLEDGE_TARGET_TOOL in tools:
            if (getattr(program, "stop_rule", None) != "native-role-episode"
                    or authority_role != phase or not store_ids or views != ("text",)):
                raise PhaseToolError(
                    "target knowledge requires a native role, named stores and text-only values"
                )
            for field in ("knowledge_values_per_candidate", "knowledge_value_limit"):
                value = entry.get(field)
                if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 32:
                    raise PhaseToolError(f"{field} requires an explicit integer between 1 and 32")
                target_limits[field] = value
        elif {"knowledge_values_per_candidate", "knowledge_value_limit"} & set(entry):
            raise PhaseToolError("knowledge value limits require the target knowledge tool")
        if LIVE_SPEECH_SPAN_TOOL in tools and mode != "native-tools":
            raise PhaseToolError("live speech span currently requires native-tools mode")
        fixed = entry.get("fixed_action")
        if mode == "fixed":
            _validate_action(fixed, tools, views)
        elif "fixed_action" in entry:
            raise PhaseToolError(f"{mode} cannot declare a fixed_action")
        for tool_id in tools:
            assert_pinned_hash(resolve_tool(tool_id).manifest)
        specs[phase] = {
            "mode": mode,
            "allowed_tools": tools,
            "knowledge_views": views,
            "fixed_action": fixed,
        }
        if store_ids is not None:
            specs[phase]["knowledge_store_ids"] = store_ids
        if authority_role is not None:
            specs[phase]["source_authority_role"] = authority_role
        if set(tools) & {CANDIDATE_CONTRACT_TOOL, KNOWLEDGE_TARGET_TOOL}:
            specs[phase]["candidate_limit"] = candidate_limit
        specs[phase].update(target_limits)
        specs[phase].update(additions)
        if candidate_memory and CORRECTIVE_MEMORY_TOOL in tools:
            specs[phase]["candidate_experience_memory"] = True
    stop_rule = getattr(program, "stop_rule", None)
    native_program = stop_rule == "native-answer-or-tool"
    native_role_episode = stop_rule == "native-role-episode"
    native_specs = any(spec["mode"] == "native-tools" for spec in specs.values())
    if native_program or (native_specs and not native_role_episode):
        nonfinal = set(phases[:-1])
        if (
            not native_program
            or set(specs) != nonfinal
            or any(spec["mode"] != "native-tools" for spec in specs.values())
        ):
            raise PhaseToolError(
                "native-answer-or-tool requires native-tools on every nonfinal phase"
            )
        signatures = {
            (spec["allowed_tools"], spec["knowledge_views"], spec.get("candidate_limit"), spec.get("knowledge_store_ids"))
            for spec in specs.values()
        }
        if len(signatures) != 1:
            raise PhaseToolError(
                "native-tools phases must expose one identical tool schema set"
            )
    elif native_role_episode:
        if any(
            spec["mode"] != "native-tools"
            or "source_authority_role" not in spec
            for spec in specs.values()
        ):
            raise PhaseToolError(
                "native-role-episode phase tools require native-tools with source authority"
            )
        schemas_by_name = {}
        for phase in phases:
            spec = specs.get(phase)
            if spec is None:
                continue
            for tool_id in spec["allowed_tools"]:
                schema = _native_tool_schema(
                    tool_id,
                    spec["knowledge_views"],
                    candidate_limit=spec.get("candidate_limit"),
                    store_ids=spec.get("knowledge_store_ids"),
                    candidate_memory=bool(spec.get("candidate_experience_memory")),
                )
                previous = schemas_by_name.setdefault(tool_id, schema)
                if previous != schema:
                    raise PhaseToolError(
                        "native-role-episode exposes one tool name with different schemas"
                    )
    return specs


def _validate_action(action, allowed, views, *, candidate_limit=None, store_ids=None):
    if not isinstance(action, Mapping) or set(action) != {"tool_id", "arguments"}:
        raise PhaseToolError("action must contain exactly tool_id and arguments")
    tool_id = action["tool_id"]
    args = action["arguments"]
    if not isinstance(tool_id, str) or tool_id not in allowed:
        raise PhaseToolError("action tool is outside the configured allowlist")
    if not isinstance(args, Mapping):
        raise PhaseToolError("action arguments must be an object")
    if tool_id in {TASK_CONTRACT_TOOL, CORRECTIVE_MEMORY_TOOL} and args:
        raise PhaseToolError(f"{tool_id} action takes no arguments")
    if tool_id == PHASE_KNOWLEDGE_TOOL:
        expected = {"view"} if store_ids is None else {"store_id", "view"}
        if (set(args) != expected or not isinstance(args["view"], str)
                or args["view"] not in views):
            raise PhaseToolError("knowledge action needs one allowed knowledge view")
        if store_ids is not None and (
                not isinstance(args["store_id"], str) or args["store_id"] not in store_ids):
            raise PhaseToolError("knowledge action names a disallowed knowledge store")
    if tool_id in {PREPARED_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_OBSERVATION_TOOL}:
        if (
            set(args) != {"span", "representation", "distinction"}
            or args["span"] != "full-utterance"
            or args["representation"] != "asr-transcript"
            or not isinstance(args["distinction"], str)
            or not args["distinction"].strip()
            or len(args["distinction"]) > 512
        ):
            raise PhaseToolError(
                "speech observation requires full-utterance, asr-transcript and a bounded distinction"
            )
    if tool_id == LIVE_SPEECH_SPAN_TOOL:
        try:
            from .live_speech_observation import normalize_live_span_arguments

            args = normalize_live_span_arguments(args)
        except RailsError as error:
            raise PhaseToolError(str(error)) from error
    if tool_id == KNOWLEDGE_TARGET_TOOL:
        if set(args) != {"store_id", "view", "candidate_ids", "distinction"}:
            raise PhaseToolError("target knowledge requires store, view, candidates and distinction")
        if (not isinstance(args["store_id"], str) or not store_ids
                or args["store_id"] not in store_ids or args["view"] != "text"):
            raise PhaseToolError("target knowledge request exceeds its store or view authority")
        distinction = args["distinction"]
        if not isinstance(distinction, str) or not distinction.strip() or len(distinction) > 512:
            raise PhaseToolError("target knowledge requires a bounded nonempty distinction")
    if tool_id in {CANDIDATE_CONTRACT_TOOL, KNOWLEDGE_TARGET_TOOL}:
        expected = {"candidate_ids"} if tool_id == CANDIDATE_CONTRACT_TOOL else {
            "store_id", "view", "candidate_ids", "distinction"
        }
        if set(args) != expected or not isinstance(args["candidate_ids"], list):
            raise PhaseToolError("candidate lookup requires only a candidate_ids list")
        try:
            request = CandidateContractRequest.from_ids(args["candidate_ids"])
        except CandidateContractLookupError as error:
            raise PhaseToolError(str(error)) from error
        if candidate_limit is None or len(request.candidate_ids) > candidate_limit:
            raise PhaseToolError("candidate request exceeds the configured candidate_limit")
    return {"tool_id": tool_id, "arguments": dict(args)}


def _native_tool_schema(
    tool_id, views, *, candidate_limit=None, store_ids=None, candidate_memory=False, target_axis="task"
):
    descriptions = {
        TASK_CONTRACT_TOOL: "Read the legal task contract.",
        CANDIDATE_CONTRACT_TOOL: (
            "Read compact contracts for ordered competing intent or tool candidates. "
            "Returned field associations are task knowledge, not evidence of spoken values."
        ),
        PHASE_KNOWLEDGE_TOOL: "Retrieve prepared task knowledge.",
        KNOWLEDGE_TARGET_TOOL: (
            "Read target-specific knowledge for a named unresolved distinction. Choose the "
            "activation or parameter-meaning store as appropriate. Missing targets are reported; "
            "knowledge is guidance, not evidence that an action or value was spoken."
        ),
        CORRECTIVE_MEMORY_TOOL: (
            "Read provisional guidance for this registered TRAIN evaluation."
            if candidate_memory
            else "Read admitted corrective guidance."
        ),
        PREPARED_SPEECH_OBSERVATION_TOOL: "Read a prepared speech transcript.",
        LIVE_SPEECH_OBSERVATION_TOOL: "Transcribe the current full utterance on demand.",
        LIVE_SPEECH_SPAN_TOOL: (
            "Transcribe a span of at most 30 seconds on demand. Start and end are "
            "seconds relative to the current speech unit, within its duration."
        ),
    }
    if tool_id in {TASK_CONTRACT_TOOL, CORRECTIVE_MEMORY_TOOL}:
        properties = {}
        required = []
    elif tool_id in KNOWLEDGE_TOOLS:
        properties = {"view": {"type": "string", "enum": list(views)}}
        required = ["view"]
        if store_ids is not None:
            properties = {"store_id": {"type": "string", "enum": list(store_ids)}, **properties}
            required = ["store_id", "view"]
        if tool_id == KNOWLEDGE_TARGET_TOOL:
            properties.update({
                "candidate_ids": {
                    "type": "array", "minItems": 1, "maxItems": candidate_limit,
                    "uniqueItems": True, "items": {"type": "string", "minLength": 1},
                },
                "distinction": {"type": "string", "minLength": 1, "maxLength": 512},
            })
            required += ["candidate_ids", "distinction"]
    elif tool_id == CANDIDATE_CONTRACT_TOOL:
        properties = {"candidate_ids": {
            "type": "array", "minItems": 1, "maxItems": candidate_limit,
            "uniqueItems": True, "items": {"type": "string", "minLength": 1},
        }}
        required = ["candidate_ids"]
    elif tool_id == LIVE_SPEECH_SPAN_TOOL:
        properties = {
            "span": {
                "type": "object",
                "properties": {
                    "start_seconds": {"type": "number", "minimum": 0},
                    "end_seconds": {"type": "number", "exclusiveMinimum": 0},
                },
                "required": ["start_seconds", "end_seconds"],
                "additionalProperties": False,
            },
            "representation": {"type": "string", "enum": ["asr-transcript"]},
            "distinction": {"type": "string", "minLength": 1, "maxLength": 512},
        }
        required = ["span", "representation", "distinction"]
    else:
        properties = {
            "span": {"type": "string", "enum": ["full-utterance"]},
            "representation": {"type": "string", "enum": ["asr-transcript"]},
            "distinction": {"type": "string", "minLength": 1, "maxLength": 512},
        }
        required = ["span", "representation", "distinction"]
    if tool_id == KNOWLEDGE_TARGET_TOOL and target_axis == "slot-type":
        descriptions[tool_id] = (
            "Read existing slot knowledge for a concrete unresolved type meaning, boundary "
            "or existence question. candidate_ids are at most two slot type identifiers. "
            "Empty results are legal. Knowledge explains types and extraction scope; "
            "it never proves a value was spoken. The Solver owns the final answer."
        )
    return {
        "type": "function",
        "function": {
            "name": tool_id,
            "description": descriptions[tool_id],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


class PhaseToolDispatcher:
    def __init__(
        self,
        specs,
        program,
        *,
        snapshot,
        supply_for_phase=None,
        trace_sink=None,
        knowledge_catalog=None,
        experience_memory=None,
        speech_observations=None,
        live_speech_observations=None,
        tool_contact=None,
        candidate_contracts=None,
        knowledge_stores=None,
        supply_for_store=None,
        knowledge_value_rendering=None,
    ):
        self.specs = specs
        self.program = program
        self.snapshot = snapshot.validate()
        self.snapshot_sha256 = snapshot.content_hash()
        self.knowledge_catalog = knowledge_catalog
        self.experience_memory = experience_memory
        self.speech_observations = speech_observations
        self.live_speech_observations = live_speech_observations
        self.tool_contact = tool_contact
        self.candidate_contracts = candidate_contracts
        self.knowledge_stores = knowledge_stores
        self.supply_for_store = supply_for_store
        self.knowledge_value_rendering = load_knowledge_value_rendering(
            {} if knowledge_value_rendering is None
            else {"knowledge_value_rendering": knowledge_value_rendering}
        )
        self._candidate_ids = ()
        self._candidate_source_sha256 = None
        if any(CANDIDATE_CONTRACT_TOOL in spec["allowed_tools"] for spec in specs.values()):
            source_sha = getattr(candidate_contracts, "source_sha256", None)
            ids = getattr(candidate_contracts, "candidate_ids", None)
            if (
                not callable(getattr(candidate_contracts, "lookup", None))
                or not isinstance(source_sha, str) or len(source_sha) != 64
                or any(char not in "0123456789abcdef" for char in source_sha)
                or not isinstance(ids, tuple) or not ids
                or any(not isinstance(key, str) or not key for key in ids)
                or len(ids) != len(set(ids))
            ):
                raise PhaseToolError("candidate lookup requires a bound canonical provider")
            self._candidate_ids = ids
            self._candidate_source_sha256 = source_sha
        self._live_selections = {}
        from .knowledge_value_views import KnowledgeValueRenderer

        self._value_renderer = KnowledgeValueRenderer(
            snapshot, catalog=knowledge_catalog
        )
        self.supply_for_phase = supply_for_phase
        self.trace_sink = trace_sink
        self._lock = Lock()
        self._attempts = set()
        self._invocation_counts = {}
        self._records = {}
        self._native_rejections = []
        self._native_rejected_batches = set()
        if (
            any(set(spec["knowledge_views"]) - {"text"} for spec in specs.values())
            and knowledge_catalog is None
        ):
            raise PhaseToolError(
                "speech/paired action requires a prepared knowledge catalog"
            )
        configured_store_ids = {
            store_id for spec in specs.values()
            for store_id in spec.get("knowledge_store_ids", ())
        }
        if configured_store_ids:
            needs_router = any(
                PHASE_KNOWLEDGE_TOOL in spec["allowed_tools"] for spec in specs.values()
            )
            if knowledge_stores is None or (needs_router and not callable(supply_for_store)):
                raise PhaseToolError("named knowledge stores require a bound store router")
            if not configured_store_ids <= set(getattr(knowledge_stores, "store_ids", ())):
                raise PhaseToolError("configured knowledge stores differ from the bound releases")
            if getattr(knowledge_stores, "binding_sha256", None) != self.snapshot_sha256:
                raise PhaseToolError("named knowledge stores differ from the runtime snapshot")
        elif knowledge_stores is not None or supply_for_store is not None:
            raise PhaseToolError("named knowledge stores are bound without configured store IDs")
        if (any(PHASE_KNOWLEDGE_TOOL in spec["allowed_tools"] for spec in specs.values())
                and not configured_store_ids and not callable(supply_for_phase)):
            raise PhaseToolError("knowledge action requires the shared supply binding")
        if any(
            CORRECTIVE_MEMORY_TOOL in s["allowed_tools"] for s in specs.values()
        ) and experience_memory is None:
            raise PhaseToolError("corrective-memory action requires a loaded memory binding")

        if any(
            PREPARED_SPEECH_OBSERVATION_TOOL in spec["allowed_tools"]
            for spec in specs.values()
        ) and speech_observations is None:
            raise PhaseToolError("speech observation action requires a loaded source binding")
        if any(
            set(spec["allowed_tools"]) & {LIVE_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_SPAN_TOOL}
            for spec in specs.values()
        ) and live_speech_observations is None:
            raise PhaseToolError("live speech observation action requires a loaded provider")
        if self.native_enabled and not callable(tool_contact):
            raise PhaseToolError("native tools require a tool contact custodian")

    @property
    def native_enabled(self):
        return getattr(self.program, "stop_rule", None) in {
            "native-answer-or-tool", "native-role-episode",
        }

    @property
    def native_role_episode(self):
        return getattr(self.program, "stop_rule", None) == "native-role-episode"

    def is_native_phase(self, phase):
        spec = self.specs.get(phase)
        return bool(self.native_enabled and spec and spec["mode"] == "native-tools")

    def native_tool_schemas(self):
        if not self.native_enabled:
            return ()
        ordered = []
        seen = set()
        phases = self.program.phase_names()
        for phase in (phases if self.native_role_episode else phases[:-1]):
            spec = (
                self.specs.get(phase)
                if self.native_role_episode
                else self.specs[phase]
            )
            if spec is None:
                continue
            for tool_id in spec["allowed_tools"]:
                if tool_id not in seen:
                    ordered.append(_native_tool_schema(
                        tool_id, spec["knowledge_views"],
                        candidate_limit=spec.get("candidate_limit"),
                        store_ids=spec.get("knowledge_store_ids"),
                        candidate_memory=bool(spec.get("candidate_experience_memory")),
                        target_axis=spec.get("knowledge_target_axis", "task"),
                    ))
                    seen.add(tool_id)
        return tuple(ordered)

    def instruction_for_phase(self, phase, context):
        spec = self.specs.get(phase)
        if spec is None or spec["mode"] not in {"core-choice", "native-tools"}:
            return ""
        if spec["mode"] == "native-tools":
            return (
                "Answer the task directly when the available evidence is sufficient. "
                "Otherwise call at most one available internal tool that is needed, "
                "then use its returned evidence in the next decision. Do not invent "
                "tool results or call a tool merely because it is available."
            )
        descriptions = {
            LIVE_SPEECH_OBSERVATION_TOOL: (
                "Transcribe the full original utterance on demand. Name the distinction "
                "the observation should resolve; the frozen core retains answer authority."
            ),
            PREPARED_SPEECH_OBSERVATION_TOOL: (
                "Inspect an independently prepared transcription of the full original utterance. "
                "Name the distinction it should resolve; the Solver retains the answer."
            ),
            TASK_CONTRACT_TOOL: "Read the current task's legal schema and instructions.",
            PHASE_KNOWLEDGE_TOOL: "Retrieve and open prepared TRAIN knowledge for this task. Arguments: view.",
            CORRECTIVE_MEMORY_TOOL: (
                "Read offline-admitted procedural guidance applicable to the next phase."
            ),
        }
        choices = [
            {
                "tool_id": tool,
                "description": descriptions[tool],
                "arguments": {}
                if tool in {TASK_CONTRACT_TOOL, CORRECTIVE_MEMORY_TOOL}
                else {
                    "span": "full-utterance", "representation": "asr-transcript",
                    "distinction": "Describe the suspected missing evidence or problem in English.",
                } if tool == PREPARED_SPEECH_OBSERVATION_TOOL
                else {"view": list(spec["knowledge_views"])},
            }
            for tool in spec["allowed_tools"]
        ]
        return (
            "Act as the bounded Planner. Select one available task action; "
            "the following Solver owns the task answer. Return only a JSON object "
            "with exactly tool_id, arguments, and query_state_sha256. "
            "Do not provide a task answer in this phase.\n"
            f"query_state_sha256: {context.query_state.content_hash()}\n"
            "Available actions: " + json.dumps(choices, sort_keys=True)
        )

    def is_action_phase(self, phase):
        return phase in self.specs

    def _phase_source(self, phase, context):
        states = [s for s in context.agent_states if s.state_kind == f"phase:{phase}"]
        if not states:
            raise PhaseToolError("action requires the current sealed phase response")
        source = states[-1]
        expected = context.query_state.content_hash()
        if context.knowledge_snapshot_sha256 != self.snapshot_sha256:
            raise PhaseToolError("action snapshot differs from the configured snapshot")
        if (
            source.source_query_state_sha256 != expected
            or not context.prior_response_sha256s
            or source.source_response_sha256 != context.prior_response_sha256s[-1]
            or hashlib.sha256(source.content.encode()).hexdigest()
            != source.source_response_sha256
            or source.producer_policy_id != self.program.program_id
            or context.sample_id != context.query_state.query_sample_id
        ):
            raise PhaseToolError("action has stale or cross-sample source state")
        return source, expected

    def __call__(self, phase, next_phase, context):
        spec = self.specs.get(phase)
        if spec is None:
            return None
        phases = self.program.phase_names()
        phase_index = phases.index(phase)
        if not (self.native_role_episode and next_phase == phase):
            if phase_index + 1 >= len(phases) or next_phase != phases[phase_index + 1]:
                raise PhaseToolError("action successor differs from the program")
        source, expected = self._phase_source(phase, context)
        native_call = None
        if spec["mode"] == "fixed":
            action = _validate_action(
                spec["fixed_action"], spec["allowed_tools"], spec["knowledge_views"]
            )
        elif spec["mode"] == "native-tools":
            try:
                action, native_call = self._parse_native_action(
                    context, source, spec
                )
            except PhaseToolError as error:
                return self._native_error(
                    phase, context, source, expected, str(error)
                )
        else:
            try:
                raw = json.loads(source.content, object_pairs_hook=_json_object)
            except (ValueError, TypeError) as exc:
                raise PhaseToolError("Planner response is not a JSON action") from exc
            if not isinstance(raw, dict) or set(raw) != {
                "tool_id",
                "arguments",
                "query_state_sha256",
            }:
                raise PhaseToolError("Planner action has wrong fields")
            if raw["query_state_sha256"] != expected:
                raise PhaseToolError("Planner action references a stale QueryState")
            action = _validate_action(
                {k: raw[k] for k in ("tool_id", "arguments")},
                spec["allowed_tools"],
                spec["knowledge_views"],
            )
        if self.native_role_episode:
            key = (
                native_call["completion"].request_id,
                native_call["call_id"],
            )
            duplicate_error = (
                "tool action already attempted for this source completion/tool call"
            )
        else:
            key = (context.sample_id, phase)
            duplicate_error = "tool action already attempted for this phase/sample"
        count_key = (context.sample_id, getattr(context, "execution_unit_id", None), phase)
        with self._lock:
            if key in self._attempts:
                raise PhaseToolError(duplicate_error)
            self._attempts.add(key)
            limit = spec.get("max_calls_per_sample")
            used = self._invocation_counts.get(count_key, 0)
            exhausted = limit is not None and used >= limit
            if not exhausted:
                self._invocation_counts[count_key] = used + 1
        if exhausted:
            return self.reject_native_batch(phase, context, call_limit=True)[0]
        tool = resolve_tool(action["tool_id"])
        request = {
            "selection_mode": spec["mode"],
            "tool_id": action["tool_id"],
            "arguments": action["arguments"],
            "query_state_sha256": expected,
            "source_response_sha256": source.source_response_sha256,
            "snapshot_sha256": context.knowledge_snapshot_sha256,
            "tool_source_sha256": tool.manifest.pinned_sha256,
        }
        if native_call is not None:
            request.update({
                "tool_call_id": native_call["call_id"],
                "tool_calls_sha256": native_call["completion"].tool_calls_sha256,
                "core_request_id": native_call["completion"].request_id,
                "sample_id": context.sample_id,
                "phase": phase,
                "next_phase": next_phase,
                "speech_packet_id": context.query_state.speech_packet_id,
                "speech_packet_sha256": context.query_state.speech_packet_sha256,
                "native_source_state_id": source.state_id,
                "native_tool_calls_json": (
                    native_call["completion"].tool_calls_json.decode("utf-8")
                ),
            })
            authority_role = spec.get("source_authority_role")
            if authority_role is not None:
                from .native_tool_authority import (
                    build_native_tool_authority, select_completion_tool_schemas,
                )

                completion = native_call["completion"]
                selected_schemas = select_completion_tool_schemas(
                    completion, self.native_tool_schemas()
                )
                authority = build_native_tool_authority(
                    completion, role_id=authority_role, phase_id=phase,
                    selected_tool_schemas=selected_schemas,
                )
                request["source_authority"] = authority
                request["source_authority_sha256"] = content_hash(authority)
        self._emit(context.sample_id, phase, "attempt", request)
        try:
            if spec["mode"] == "native-tools":
                invocation = self.tool_contact(
                sample_id=context.sample_id,
                phase=phase,
                next_phase=next_phase,
                tool_id=action["tool_id"],
                arguments=dict(action["arguments"]),
                source_response_sha256=source.source_response_sha256,
                request_id=native_call["completion"].request_id,
                tool_call_id=native_call["call_id"],
                tool_calls_sha256=native_call["completion"].tool_calls_sha256,
                **({
                    "source_authority": request["source_authority"],
                    "source_authority_role": spec["source_authority_role"],
                } if "source_authority" in request else {}),
                **({
                    "execution_unit_id": context.execution_unit_id,
                    "execution_unit_binding_sha256": content_hash(
                        context.execution_unit_binding
                    ),
                } if getattr(context, "execution_unit_id", None) is not None else {}),
                )
                if not isinstance(invocation, Mapping):
                    raise PhaseToolError(
                        "tool contact custodian returned no invocation receipt"
                    )
                content_hash(invocation)
                request["tool_invocation"] = dict(invocation)
            if (
                self.native_role_episode
                and action["tool_id"] == CANDIDATE_CONTRACT_TOOL
                and not set(action["arguments"]["candidate_ids"]) <= set(self._candidate_ids)
            ):
                return self._native_candidate_rejection(
                    phase, context, source, expected, request, key
                )
            if action["tool_id"] == TASK_CONTRACT_TOOL:
                output = tool.call(context)
            elif action["tool_id"] == CANDIDATE_CONTRACT_TOOL:
                output = tool.call(
                    self.candidate_contracts, action["arguments"]["candidate_ids"]
                )
            elif action["tool_id"] == KNOWLEDGE_TARGET_TOOL:
                store_id = action["arguments"]["store_id"]
                prefix = store_id + "::"
                visible = tuple(
                    value_id[len(prefix):] for value_id in context.query_state.retrieved_value_ids
                    if value_id.startswith(prefix)
                )
                index_attribute = ("slot_target_indices" if spec.get("knowledge_target_axis") == "slot-type"
                                   else "target_indices")
                target_index = getattr(self.supply_for_store, index_attribute, {}).get(store_id)
                if spec.get("knowledge_target_axis") == "slot-type" and target_index is None:
                    raise PhaseToolError("slot-type lookup requires an authored slot index")
                output = tool.call(
                    self.knowledge_stores.snapshot_for(store_id), context.query_state,
                    action["arguments"]["candidate_ids"],
                    max_values_per_candidate=spec["knowledge_values_per_candidate"],
                    max_total_values=spec["knowledge_value_limit"],
                    already_visible_value_ids=visible,
                    selection_mode=spec.get("knowledge_selection_mode", "targeted"),
                    **({"target_index": target_index} if target_index is not None else {}),
                )
            elif action["tool_id"] == PREPARED_SPEECH_OBSERVATION_TOOL:
                output = tool.call(self.speech_observations, context)
            elif action["tool_id"] == LIVE_SPEECH_OBSERVATION_TOOL:
                output = tool.call(
                    self.live_speech_observations,
                    context,
                    action["arguments"],
                    source.source_response_sha256,
                )
            elif action["tool_id"] == LIVE_SPEECH_SPAN_TOOL:
                output = tool.call(
                    self.live_speech_observations,
                    context,
                    action["arguments"],
                    source.source_response_sha256,
                )
            elif action["tool_id"] == CORRECTIVE_MEMORY_TOOL:
                output = tool.call(self.experience_memory, next_phase, context)
            else:
                store_id = action["arguments"].get("store_id")
                if store_id is None:
                    output = tool.call(self.supply_for_phase, next_phase, context)
                else:
                    output = tool.call(
                        lambda next_name, ctx: self.supply_for_store(store_id, next_name, ctx),
                        next_phase, context,
                    )
            if output.tool_id != action["tool_id"] or output.derivation is not None:
                raise PhaseToolError(
                    "tool returned a different identity or unexpected derivation"
                )
            supply = None
            cited = ()
            store_receipt = None
            if action["tool_id"] == KNOWLEDGE_TARGET_TOOL:
                supply, cited, result, store_receipt = self._target_knowledge_result(
                    output.result, action["arguments"], context, spec
                )
            elif action["tool_id"] == PHASE_KNOWLEDGE_TOOL:
                supply = output.result
                if not isinstance(supply, PhaseSupply):
                    raise PhaseToolError("knowledge tool did not return a PhaseSupply")
                supply.validate()
                from .knowledge import assert_knowledge_use_binding

                store_id = action["arguments"].get("store_id")
                store_receipt = None
                local_identity = None
                if store_id is not None:
                    try:
                        local_identity = {
                            "local_rank_sha256": supply.rank_result.content_hash(),
                            "local_fusion_sha256": supply.fusion_decision.content_hash(),
                        }
                        supply = self.knowledge_stores.qualify_supply(
                            store_id, supply, context.query_state
                        )
                        store_receipt = self.knowledge_stores.store_receipt(store_id)
                    except RailsError as error:
                        raise PhaseToolError(str(error)) from error
                assert_knowledge_use_binding(
                    snapshot=self.snapshot,
                    query_state=context.query_state,
                    rank_result=supply.rank_result,
                    fusion_decision=supply.fusion_decision,
                    snapshot_sha256=self.snapshot_sha256,
                )
                cited = supply.fusion_decision.selected_value_ids
                result = {
                    "selected_value_ids": list(cited),
                    "supporting_facet_ids": list(
                        supply.fusion_decision.supporting_facet_ids
                    ),
                    "knowledge_view": action["arguments"]["view"],
                }
                if store_receipt is not None:
                    result.update(
                        {
                            **store_receipt,
                            **local_identity,
                            "qualified_rank_sha256": supply.rank_result.content_hash(),
                            "qualified_fusion_sha256": supply.fusion_decision.content_hash(),
                        }
                    )
                else:
                    result.update(
                        rank_sha256=content_hash(supply.rank_result.as_json()),
                        fusion_sha256=content_hash(supply.fusion_decision.as_json()),
                    )
                if action["arguments"]["view"] != "text":
                    # Preserve an explicit association in the source-bound tool
                    # state; the legacy packet wire grammar uses ordered keys.
                    by_value = {
                        episode.value_id: episode
                        for episode in self.knowledge_catalog.episodes
                    }
                    if any(value_id not in by_value for value_id in cited):
                        raise PhaseToolError(
                            "selected speech knowledge is not prepared"
                        )
                    result["speech_evidence_order"] = [
                        {
                            "value_id": value_id,
                            "packet_id": by_value[value_id].packet_id,
                            "packet_sha256": by_value[value_id].packet_sha256,
                        }
                        for value_id in cited
                    ]
            elif action["tool_id"] == CANDIDATE_CONTRACT_TOOL:
                if not isinstance(output.result, CandidateContractLookupResult):
                    raise PhaseToolError("candidate tool returned an unbound result")
                output.result.validate_for(CandidateContractRequest.from_ids(
                    action["arguments"]["candidate_ids"]
                ))
                if output.result.source_sha256 != self._candidate_source_sha256:
                    raise PhaseToolError("candidate tool returned a foreign canonical source")
                result = output.result.as_json()
            elif action["tool_id"] == TASK_CONTRACT_TOOL:
                if not isinstance(output.result, Mapping) or output.result != {
                    "task_contract": context.task_contract
                }:
                    raise PhaseToolError(
                        "task-contract tool returned an unbound result"
                    )
                result = dict(output.result)
            elif action["tool_id"] in {
                PREPARED_SPEECH_OBSERVATION_TOOL,
                LIVE_SPEECH_OBSERVATION_TOOL,
                LIVE_SPEECH_SPAN_TOOL,
            }:
                if not isinstance(output.result, SpeechObservationSelection):
                    raise PhaseToolError("speech observation tool returned an unbound selection")
                if action["tool_id"] in {LIVE_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_SPAN_TOOL}:
                    visible = output.result.visible
                    lineage = output.result.lineage
                    if (
                        not isinstance(visible, Mapping)
                        or visible.get("schema")
                        != "saea-live-speech-observation-selection-v1"
                        or visible.get("sample_id") != context.sample_id
                        or visible.get("speech_packet_id")
                        != context.query_state.speech_packet_id
                        or visible.get("speech_packet_sha256")
                        != context.query_state.speech_packet_sha256
                        or not isinstance(lineage, Mapping)
                        or lineage.get("source_response_sha256")
                        != source.source_response_sha256
                    ):
                        raise PhaseToolError(
                            "live speech observation returned foreign evidence"
                        )
                # The typed OBS block supplies the transcript once; history keeps its reference.
                result = {key: value for key, value in output.result.visible.items() if key != "transcript"}
                if action["tool_id"] in {LIVE_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_SPAN_TOOL}:
                    with self._lock:
                        prior = self._live_selections.get(result["artifact_sha256"])
                        if (
                            prior is not None
                            and dict(prior.visible) != dict(output.result.visible)
                        ):
                            raise PhaseToolError(
                                "live speech observation returned conflicting duplicate evidence"
                            )
                        self._live_selections[result["artifact_sha256"]] = output.result
            else:
                if not isinstance(output.result, ExperienceMemorySelection):
                    raise PhaseToolError(
                        "corrective-memory tool did not return a bound selection"
                    )
                result = dict(output.result.visible)
            if native_call is not None:
                # Preserve the actual return at invocation time. Later knowledge
                # selections can change the current view but not an earlier turn.
                if action["tool_id"] in KNOWLEDGE_TOOLS:
                    native_content = list(
                        self._model_knowledge_blocks(
                            self._value_renderer.assemble(
                                cited, view=action["arguments"]["view"]
                            )
                        )
                    )
                elif action["tool_id"] in {
                    PREPARED_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_OBSERVATION_TOOL,
                    LIVE_SPEECH_SPAN_TOOL,
                }:
                    native_content = [output.result.content_block()]
                else:
                    native_content = []
                request["native_result_content"] = native_content
                request["native_result_content_sha256"] = content_hash(
                    {"blocks": native_content}
                )
            model_result = result
            if action["tool_id"] in KNOWLEDGE_TOOLS and store_receipt is not None:
                model_result = {
                    "store_id": result["store_id"],
                    "store_role": result["store_role"],
                    "selected_value_ids": result["selected_value_ids"],
                    "supporting_facet_ids": result["supporting_facet_ids"],
                    "knowledge_view": result["knowledge_view"],
                }
                if action["tool_id"] == KNOWLEDGE_TARGET_TOOL:
                    model_result.update({
                        key: result[key] for key in (
                            "candidate_ids", "missing_candidate_ids", "supply_disposition",
                        )
                    })
            document = {
                **request,
                "schema": (
                    "saea-phase-tool-result-v2"
                    if "source_authority" in request else "saea-phase-tool-result-v1"
                ),
                "result": model_result,
                "result_sha256": content_hash(model_result),
            }
            state_id = f"tool-result:{phase}:{context.sample_id}"
            if self.native_role_episode:
                state_id += ":" + content_hash({
                    "request_id": native_call["completion"].request_id,
                    "tool_call_id": native_call["call_id"],
                })
            artifact = AgentStateArtifact(
                state_id=state_id,
                state_kind="tool-result",
                content=json.dumps(document, sort_keys=True),
                source_query_state_sha256=expected,
                source_response_sha256=source.source_response_sha256,
                producer_policy_id=self.program.program_id,
                cited_value_ids=cited,
            ).validate()
            receipt_document = (
                {
                    **document,
                    "result": result,
                    "result_sha256": content_hash(result),
                    "model_result_sha256": content_hash(model_result),
                }
                if model_result is not result
                else document
            )
            if action["tool_id"] == CORRECTIVE_MEMORY_TOOL:
                receipt_document = {
                    **document,
                    "internal_memory_lineage": dict(output.result.lineage),
                }
            if action["tool_id"] in {
                PREPARED_SPEECH_OBSERVATION_TOOL,
                LIVE_SPEECH_OBSERVATION_TOOL,
                LIVE_SPEECH_SPAN_TOOL,
            }:
                receipt_document = {
                    **document,
                    "internal_observation_lineage": dict(output.result.lineage),
                }
            self._emit(context.sample_id, phase, "result", receipt_document)
            with self._lock:
                self._records[key] = receipt_document
            return PhaseToolStep(supply=supply, state=artifact)
        except Exception as exc:
            self._emit(
                context.sample_id,
                phase,
                "failed",
                {**request, "error_type": type(exc).__name__},
            )
            raise

    def _native_completion(self, context, source, spec):
        completions = []
        for completion in getattr(context, "core_completions", ()):
            if (
                getattr(completion, "sample_id", None) == context.sample_id
                and getattr(completion, "text", None) == source.content
                and getattr(completion, "response_text_sha256", None)
                == source.source_response_sha256
            ):
                completions.append(completion)
        if len(completions) != 1:
            raise PhaseToolError("native action requires exactly one source-bound completion")
        completion = completions[0]
        try:
            completion.assert_binding(
                sample_id=context.sample_id,
                agent_contact_id=completion.agent_contact_id,
                response_text=source.content,
            )
            completion.tool_calls
        except Exception as error:
            raise PhaseToolError("native completion binding or tool calls are malformed") from error
        if self.native_role_episode:
            authority_role = spec.get("source_authority_role")
            prefix = f"{self.program.program_id}:{authority_role}:"
            suffix = f":{context.sample_id}"
            from .execution_units import unscoped_execution_contact_id
            try:
                contact_id = unscoped_execution_contact_id(
                    completion.agent_contact_id, getattr(context, "execution_unit_id", None),
                )
            except RailsError as error:
                raise PhaseToolError(str(error)) from error
            if (
                not isinstance(contact_id, str)
                or not contact_id.startswith(prefix)
                or not contact_id.endswith(suffix)
            ):
                raise PhaseToolError(
                    "native completion contact does not match the authorized role"
                )
            iteration = contact_id[len(prefix):len(contact_id) - len(suffix)]
            if (
                not iteration.isdecimal()
                or str(int(iteration)) != iteration
            ):
                raise PhaseToolError(
                    "native completion contact has a malformed iteration identity"
                )
        return completion

    def _parse_native_action(self, context, source, spec):
        completion = self._native_completion(context, source, spec)
        calls = completion.tool_calls
        if not isinstance(calls, list) or len(calls) != 1:
            raise PhaseToolError("native action must contain exactly one tool call")
        call = calls[0]
        if (
            not isinstance(call, Mapping)
            or set(call) != {"id", "type", "function"}
            or not isinstance(call["id"], str)
            or not call["id"]
            or call["type"] != "function"
            or not isinstance(call["function"], Mapping)
            or set(call["function"]) != {"name", "arguments"}
            or not isinstance(call["function"]["name"], str)
            or not isinstance(call["function"]["arguments"], str)
        ):
            raise PhaseToolError("native tool call has the wrong OpenAI function shape")
        try:
            arguments = json.loads(
                call["function"]["arguments"], object_pairs_hook=_json_object
            )
        except (ValueError, TypeError) as error:
            raise PhaseToolError("native tool arguments are not one JSON object") from error
        action = _validate_action(
            {"tool_id": call["function"]["name"], "arguments": arguments},
            spec["allowed_tools"],
            spec["knowledge_views"],
            candidate_limit=spec.get("candidate_limit"),
            store_ids=spec.get("knowledge_store_ids"),
        )
        if action["tool_id"] == CANDIDATE_CONTRACT_TOOL and not self.native_role_episode:
            if not set(action["arguments"]["candidate_ids"]) <= set(self._candidate_ids):
                raise PhaseToolError("candidate request contains unknown legal IDs")
        return action, {
            "call_id": call["id"],
            "completion": completion,
        }

    def reject_native_batch(self, phase, context, *, call_limit=False, invalid_arguments=False):
        """Reject every returned action before dispatch; execute and count no tool."""
        from .native_tool_authority import (
            MULTIPLE_CALL_REJECTION_SCHEMA, build_native_tool_authority,
            multiple_call_rejection_result, episode_call_limit_rejection_result, invalid_arguments_rejection_result, select_completion_tool_schemas,
            validate_native_call_rejection,
        )

        spec = self.specs.get(phase)
        if not self.native_role_episode or spec is None or spec["mode"] != "native-tools":
            raise PhaseToolError("batch rejection requires a configured native role")
        source, expected = self._phase_source(phase, context)
        completion = self._native_completion(context, source, spec)
        authority = build_native_tool_authority(
            completion, role_id=spec["source_authority_role"], phase_id=phase,
            selected_tool_schemas=select_completion_tool_schemas(
                completion, self.native_tool_schemas(),
            ),
        )
        calls = completion.tool_calls
        if call_limit and invalid_arguments:
            raise PhaseToolError("one rejection must name one cause")
        result = (invalid_arguments_rejection_result(len(calls)) if invalid_arguments else
                  episode_call_limit_rejection_result(len(calls)) if call_limit
                  else multiple_call_rejection_result(len(calls)))
        documents, steps = [], []
        for call in calls:
            document = {
                "schema": MULTIPLE_CALL_REJECTION_SCHEMA,
                "selection_mode": "native-tools",
                "tool_id": call["function"]["name"],
                "arguments": json.loads(call["function"]["arguments"]),
                "tool_call_id": call["id"],
                "tool_calls_sha256": completion.tool_calls_sha256,
                "core_request_id": completion.request_id,
                "sample_id": context.sample_id, "phase": phase, "next_phase": phase,
                "query_state_sha256": expected,
                "source_response_sha256": source.source_response_sha256,
                "snapshot_sha256": context.knowledge_snapshot_sha256,
                "speech_packet_id": context.query_state.speech_packet_id,
                "speech_packet_sha256": context.query_state.speech_packet_sha256,
                "native_source_state_id": source.state_id,
                "native_tool_calls_json": completion.tool_calls_json.decode("utf-8"),
                "source_authority": authority,
                "source_authority_sha256": content_hash(authority),
                "result": result, "result_sha256": content_hash(result),
                "native_result_content": [],
                "native_result_content_sha256": content_hash({"blocks": []}),
            }
            validate_native_call_rejection(document)
            artifact = AgentStateArtifact(
                state_id=f"tool-rejection:{phase}:{context.sample_id}:" + content_hash({
                    "request_id": completion.request_id, "tool_call_id": call["id"],
                }),
                state_kind="tool-result", content=json.dumps(document, sort_keys=True),
                source_query_state_sha256=expected,
                source_response_sha256=source.source_response_sha256,
                producer_policy_id=self.program.program_id, cited_value_ids=(),
            ).validate()
            documents.append(document)
            steps.append(PhaseToolStep(supply=None, state=artifact).validate())
        with self._lock:
            if completion.request_id in self._native_rejected_batches:
                raise PhaseToolError("native batch was already rejected")
            self._native_rejected_batches.add(completion.request_id)
            self._native_rejections.extend(content_hash(doc) for doc in documents)
        for document in documents:
            self._emit(context.sample_id, phase, "attempt", document)
            self._emit(context.sample_id, phase, "rejected", document)
        return tuple(steps)

    def _native_candidate_rejection(self, phase, context, source, expected, request, key):
        """Return counted input feedback after source validation, before lookup.

        The framework consumes the same bound assistant/tool sequence as a
        successful invocation. Do not catch execution, custody or source errors.
        """
        result = {
            "status": "rejected",
            "error_code": "unknown-candidate-ids",
            "message": "Use exact candidate IDs from the task's legal label catalog.",
            "invalid_candidate_ids": [
                item for item in request["arguments"]["candidate_ids"]
                if item not in self._candidate_ids
            ],
            "lookup_performed": False,
        }
        document = {
            **request,
            "schema": "saea-phase-tool-result-v2",
            "candidate_source_sha256": self._candidate_source_sha256,
            "result": result,
            "result_sha256": content_hash(result),
            "native_result_content": [],
            "native_result_content_sha256": content_hash({"blocks": []}),
        }
        artifact = AgentStateArtifact(
            state_id=f"tool-rejection:{phase}:{context.sample_id}:" + content_hash({
                "request_id": key[0], "tool_call_id": key[1],
            }),
            state_kind="tool-result",
            content=json.dumps(document, sort_keys=True),
            source_query_state_sha256=expected,
            source_response_sha256=source.source_response_sha256,
            producer_policy_id=self.program.program_id,
            cited_value_ids=(),
        ).validate()
        with self._lock:
            self._native_rejections.append(content_hash(document))
        self._emit(context.sample_id, phase, "rejected", document)
        return PhaseToolStep(supply=None, state=artifact)

    def _native_error(self, phase, context, source, expected, message):
        document = {
            "schema": "saea-phase-tool-error-v1",
            "selection_mode": "native-tools",
            "error": message,
            "query_state_sha256": expected,
            "source_response_sha256": source.source_response_sha256,
        }
        if self.native_role_episode:
            with self._lock:
                self._native_rejections.append(content_hash(document))
            self._emit(context.sample_id, phase, "rejected", document)
            raise PhaseToolError(message)
        artifact = AgentStateArtifact(
            state_id=f"tool-error:{phase}:{context.sample_id}",
            state_kind="tool-result",
            content=json.dumps(document, sort_keys=True),
            source_query_state_sha256=expected,
            source_response_sha256=source.source_response_sha256,
            producer_policy_id=self.program.program_id,
            cited_value_ids=(),
        ).validate()
        with self._lock:
            self._native_rejections.append(content_hash(document))
        self._emit(context.sample_id, phase, "rejected", document)
        return PhaseToolStep(supply=None, state=artifact)

    def _target_knowledge_result(self, selection, arguments, context, spec=None):
        spec = spec or {}
        from .knowledge import assert_knowledge_use_binding
        from .knowledge_target_lookup import KnowledgeTargetSelection

        if not isinstance(selection, KnowledgeTargetSelection):
            raise PhaseToolError("target knowledge returned an unbound selection")
        store_id = arguments["store_id"]
        local = self.knowledge_stores.snapshot_for(store_id)
        audit = dict(selection.audit)
        unsigned = {k: v for k, v in audit.items() if k != "selection_sha256"}
        if (
            audit.get("snapshot_sha256") != local.content_hash()
            or audit.get("query_state_sha256") != context.query_state.content_hash()
            or audit.get("candidate_ids") != arguments["candidate_ids"]
            or audit.get("selected_value_ids") != list(selection.selected_value_ids)
            or audit.get("selection_sha256") != content_hash(unsigned)
        ):
            raise PhaseToolError("target knowledge selection differs from its source or request")
        index_attribute = ("slot_target_indices" if spec.get("knowledge_target_axis") == "slot-type"
                           else "target_indices")
        expected_index = getattr(self.supply_for_store, index_attribute, {}).get(store_id)
        if audit.get("selection_mode", "targeted") != spec.get("knowledge_selection_mode", "targeted"):
            raise PhaseToolError("target knowledge selection mode differs from its configuration")
        expected_receipt = None if expected_index is None else dict(expected_index.receipt)
        if audit.get("target_index") != expected_receipt:
            raise PhaseToolError("target knowledge selection differs from its released index")
        supply = selection.supply
        receipt = dict(self.knowledge_stores.store_receipt(store_id))
        if supply is not None:
            supply.validate()
            if list(supply.fusion_decision.selected_value_ids) != audit.get("new_value_ids"):
                raise PhaseToolError("target knowledge supply differs from its selected new values")
            receipt.update(local_rank_sha256=supply.rank_result.content_hash(),
                           local_fusion_sha256=supply.fusion_decision.content_hash())
            supply = self.knowledge_stores.qualify_supply(store_id, supply, context.query_state)
            assert_knowledge_use_binding(
                snapshot=self.snapshot, query_state=context.query_state,
                rank_result=supply.rank_result, fusion_decision=supply.fusion_decision,
                snapshot_sha256=self.snapshot_sha256,
            )
            receipt.update(qualified_rank_sha256=supply.rank_result.content_hash(),
                           qualified_fusion_sha256=supply.fusion_decision.content_hash())
        elif audit.get("new_value_ids"):
            raise PhaseToolError("target knowledge omitted its new-value supply")
        cited = tuple(f"{store_id}::{value_id}" for value_id in selection.selected_value_ids)
        introduced = set(supply.fusion_decision.selected_value_ids) if supply else set()
        if not set(cited) <= set(context.query_state.retrieved_value_ids) | introduced:
            raise PhaseToolError("target knowledge cites values without retained or new supply")
        values = {v.value_id: v for v in local.values}
        facets = tuple(dict.fromkeys(
            f"{store_id}::{facet}" for value_id in selection.selected_value_ids
            for facet in values[value_id].associated_facet_ids
        ))
        result = {
            **receipt, "target_selection": audit,
            "candidate_ids": list(arguments["candidate_ids"]),
            "missing_candidate_ids": [
                row["candidate_id"] for row in audit["mappings"] if row["status"] == "absent"
            ],
            "supply_disposition": audit["supply_disposition"],
            "selected_value_ids": list(cited), "supporting_facet_ids": list(facets),
            "knowledge_view": "text",
        }
        return supply, cited, result, receipt

    def _emit(self, sample_id, phase, event, payload):
        if self.trace_sink is not None:
            axis = "OBS" if payload.get("tool_id") in {
                PREPARED_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_OBSERVATION_TOOL,
                LIVE_SPEECH_SPAN_TOOL,
            } else "USE"
            event_id = f"{sample_id}/{self.program.program_id}/{phase}/tool-{event}"
            if (
                self.native_role_episode
                and isinstance(payload.get("core_request_id"), str)
                and isinstance(payload.get("tool_call_id"), str)
            ):
                event_id += "/" + content_hash({
                    "request_id": payload["core_request_id"],
                    "tool_call_id": payload["tool_call_id"],
                })
            self.trace_sink.emit(
                axis,
                event_id,
                {f"{axis.lower()}_{key}": value for key, value in payload.items()},
            )

    def render_values(self, snapshot, query_state, agent_states):
        """Assemble actual evidence from the latest source-bound tool selections."""
        selections = {}
        observations = []
        observed_evidence = {}
        for artifact in agent_states:
            if artifact.state_kind != "tool-result":
                continue
            document = json.loads(artifact.content)
            if document.get("schema") == "saea-phase-tool-error-v1":
                if artifact.state_id not in query_state.agent_state_ids:
                    raise PhaseToolError("tool error is absent from current bound state")
                observations.append({
                    "type": "text",
                    "text": "The internal tool request was rejected: " + document["error"],
                    "evidence_id": artifact.state_id,
                    "source_uri": (
                        "phase-tool-error://"
                        + artifact.source_response_sha256
                        + "/"
                        + artifact.state_id
                    ),
                })
                continue
            if document.get("schema") == "saea-phase-tool-rejection-v1":
                # Rejected actions supply no task evidence; exact feedback stays in history.
                continue
            result = document.get("result", {})
            if document.get("tool_id") in {
                PREPARED_SPEECH_OBSERVATION_TOOL,
                LIVE_SPEECH_OBSERVATION_TOOL,
                LIVE_SPEECH_SPAN_TOOL,
            }:
                if artifact.state_id not in query_state.agent_state_ids:
                    raise PhaseToolError("speech observation is absent from current bound state")
                if document["tool_id"] == PREPARED_SPEECH_OBSERVATION_TOOL:
                    if self.speech_observations is None:
                        raise PhaseToolError("prepared speech observation binding is absent")
                    selected = self.speech_observations.select(
                        context=SimpleNamespace(
                            sample_id=query_state.query_sample_id, query_state=query_state,
                        )
                    )
                else:
                    with self._lock:
                        selected = self._live_selections.get(
                            result.get("artifact_sha256")
                        )
                    if selected is None:
                        raise PhaseToolError("live speech observation is absent from this dispatcher")
                if (
                    result != {key: value for key, value in selected.visible.items() if key != "transcript"}
                    or document.get("result_sha256") != content_hash(result)
                    or document.get("snapshot_sha256") != self.snapshot_sha256
                ):
                    raise PhaseToolError("speech observation state differs from its sealed evidence")
                evidence_id = result["evidence_id"]
                block = selected.content_block()
                previous = observed_evidence.get(evidence_id)
                if previous is not None and previous != block:
                    raise PhaseToolError(
                        "speech observation repeats an evidence ID with conflicting content"
                    )
                if previous is None:
                    observations.append(block)
                    observed_evidence[evidence_id] = block
                continue
            if "knowledge_view" not in result:
                continue
            if document.get("snapshot_sha256") != self.snapshot_sha256:
                raise PhaseToolError("tool evidence view references another snapshot")
            selected = result.get("selected_value_ids")
            if selected != list(artifact.cited_value_ids):
                raise PhaseToolError(
                    "tool evidence selection differs from its source citations"
                )
            for value_id in selected:
                selections[value_id] = result["knowledge_view"]
        # Preserve the runner's historical QueryState order. Coalesce adjacent
        # views so the shared renderer resolves the snapshot once per group.
        blocks = []
        group = []
        previous = None
        for value_id in query_state.retrieved_value_ids:
            view = selections.get(value_id, "text")
            if group and view != previous:
                blocks.extend(self._value_renderer.assemble(group, view=previous))
                group = []
            group.append(value_id)
            previous = view
        if group:
            blocks.extend(self._value_renderer.assemble(group, view=previous))
        blocks = list(self._model_knowledge_blocks(blocks))
        return tuple(blocks + observations)

    def _model_knowledge_blocks(self, blocks):
        if self.knowledge_stores is None:
            return tuple(blocks)
        named_blocks = []
        for block in blocks:
            evidence_id = str(block.get("evidence_id", ""))
            store_id, separator, local_id = evidence_id.partition("::")
            if not separator or not local_id:
                raise PhaseToolError(
                    "named knowledge evidence lacks a store-qualified ID"
                )
            if block.get("type") != "text" or not isinstance(block.get("text"), str):
                raise PhaseToolError(
                    "named knowledge evidence requires a text value block"
                )
            try:
                visible = self.knowledge_stores.model_evidence_block(
                    store_id,
                    local_evidence_id=local_id,
                    content=block["text"],
                )
            except RailsError as error:
                raise PhaseToolError(str(error)) from error
            if visible["evidence_id"] != evidence_id:
                raise PhaseToolError(
                    "named knowledge evidence changed its store-qualified ID"
                )
            # Validate source identity above even when no model-facing prefix
            # is requested. Rendering never grants or removes tool authority.
            named_blocks.append(
                block if self.knowledge_value_rendering == "canonical-plain-v1"
                else {**block, **visible}
            )
        return tuple(named_blocks)

    def receipt(self):
        with self._lock:
            records = [self._records[key] for key in sorted(self._records)]
            attempts = len(self._attempts)
        memory_lineage = [
            row["internal_memory_lineage"]
            for row in records
            if "internal_memory_lineage" in row
        ]
        receipt = {
            "schema": "saea-phase-tools-receipt-v1",
            "phases": {name: dict(spec) for name, spec in self.specs.items()},
            "attempts": attempts,
            "completed": len(records),
            "result_hashes": [content_hash(row) for row in records],
        }
        if self.knowledge_value_rendering is not None:
            receipt["knowledge_value_rendering"] = self.knowledge_value_rendering
        if self.native_enabled:
            with self._lock:
                rejected = tuple(self._native_rejections)
            receipt["native_rejected_requests"] = {
                "count": len(rejected),
                "hashes": sorted(rejected),
            }
        if memory_lineage:
            receipt["memory_lineage"] = memory_lineage
        observation_records = [
            row for row in records
            if row["tool_id"] == PREPARED_SPEECH_OBSERVATION_TOOL
        ]
        if self.speech_observations is not None:
            receipt["speech_observations"] = {
                **self.speech_observations.receipt(),
                "supplied_samples": len({row["result"]["sample_id"] for row in observation_records}),
                "supply_events": len(observation_records),
                "new_neural_contacts": 0,
                "lineage": [row["internal_observation_lineage"] for row in observation_records],
            }
        live_records = [
            row for row in records
            if row["tool_id"] in {LIVE_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_SPAN_TOOL}
        ]
        if self.live_speech_observations is not None:
            receipt["live_speech_observations"] = {
                **self.live_speech_observations.receipt(),
                "supply_events": len(live_records),
                "lineage": [
                    row["internal_observation_lineage"] for row in live_records
                ],
            }
        if self._candidate_source_sha256 is not None:
            receipt["candidate_contracts"] = {
                "source_sha256": self._candidate_source_sha256,
                "legal_candidate_count": len(self._candidate_ids),
                "supply_events": sum(
                    row["tool_id"] == CANDIDATE_CONTRACT_TOOL for row in records
                ),
                "new_neural_contacts": 0,
            }
        return receipt


def build_phase_tools(
    config,
    program,
    *,
    snapshot,
    supply_for_phase=None,
    trace_sink=None,
    knowledge_catalog=None,
    experience_memory=None,
    speech_observations=None,
    live_speech_observations=None,
    tool_contact=None,
    candidate_contracts=None,
    knowledge_stores=None,
    supply_for_store=None,
):
    specs = load_phase_tool_specs(config, program)
    if not specs:
        return None
    return PhaseToolDispatcher(
        specs,
        program,
        snapshot=snapshot,
        supply_for_phase=supply_for_phase,
        trace_sink=trace_sink,
        knowledge_catalog=knowledge_catalog,
        experience_memory=experience_memory,
        speech_observations=speech_observations,
        live_speech_observations=live_speech_observations,
        tool_contact=tool_contact,
        candidate_contracts=candidate_contracts,
        knowledge_stores=knowledge_stores,
        supply_for_store=supply_for_store,
        knowledge_value_rendering=load_knowledge_value_rendering(config),
    )
