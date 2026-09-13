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

TASK_CONTRACT_TOOL = "saea-tool-task-contract-v1"
PHASE_KNOWLEDGE_TOOL = "saea-tool-phase-knowledge-v1"
ACTION_TOOLS = frozenset(
    {TASK_CONTRACT_TOOL, PHASE_KNOWLEDGE_TOOL, CORRECTIVE_MEMORY_TOOL,
     PREPARED_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_OBSERVATION_TOOL,
     CANDIDATE_CONTRACT_TOOL}
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


def load_phase_tool_specs(config, program):
    raw = config.get("phase_tools")
    if raw is None or raw == {}:
        return {}
    if not isinstance(raw, Mapping):
        raise PhaseToolError("phase_tools must be a mapping")
    phases = program.phase_names()
    specs = {}
    for phase, entry in raw.items():
        if phase not in phases[:-1]:
            raise PhaseToolError("phase_tools must name a nonfinal phase")
        if not isinstance(entry, Mapping) or set(entry) - {
            "mode",
            "allowed_tools",
            "knowledge_views",
            "fixed_action",
            "candidate_limit",
        }:
            raise PhaseToolError("phase_tools entry has unknown fields")
        mode = entry.get("mode")
        if not isinstance(mode, str) or mode not in MODES:
            raise PhaseToolError("phase_tools mode must be fixed, core-choice or native-tools")
        tools = _unique(entry.get("allowed_tools"), ACTION_TOOLS, "allowed_tools")
        views = _unique(
            entry.get("knowledge_views", ["text"]), VIEWS, "knowledge_views"
        )
        candidate_limit = entry.get("candidate_limit")
        if CANDIDATE_CONTRACT_TOOL in tools:
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
        if CANDIDATE_CONTRACT_TOOL in tools:
            specs[phase]["candidate_limit"] = candidate_limit
    native_program = getattr(program, "stop_rule", None) == "native-answer-or-tool"
    native_specs = any(spec["mode"] == "native-tools" for spec in specs.values())
    if native_program or native_specs:
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
            (spec["allowed_tools"], spec["knowledge_views"], spec.get("candidate_limit"))
            for spec in specs.values()
        }
        if len(signatures) != 1:
            raise PhaseToolError(
                "native-tools phases must expose one identical tool schema set"
            )
    return specs


def _validate_action(action, allowed, views, *, candidate_limit=None):
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
        if (
            set(args) != {"view"}
            or not isinstance(args["view"], str)
            or args["view"] not in views
        ):
            raise PhaseToolError("knowledge action needs one allowed knowledge view")
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
    if tool_id == CANDIDATE_CONTRACT_TOOL:
        if set(args) != {"candidate_ids"} or not isinstance(args["candidate_ids"], list):
            raise PhaseToolError("candidate lookup requires only a candidate_ids list")
        try:
            request = CandidateContractRequest.from_ids(args["candidate_ids"])
        except CandidateContractLookupError as error:
            raise PhaseToolError(str(error)) from error
        if candidate_limit is None or len(request.candidate_ids) > candidate_limit:
            raise PhaseToolError("candidate request exceeds the configured candidate_limit")
    return {"tool_id": tool_id, "arguments": dict(args)}


def _native_tool_schema(tool_id, views, *, candidate_limit=None):
    descriptions = {
        TASK_CONTRACT_TOOL: "Read the legal task contract.",
        CANDIDATE_CONTRACT_TOOL: (
            "Read compact contracts for ordered competing intent or tool candidates. "
            "Returned field associations are task knowledge, not evidence of spoken values."
        ),
        PHASE_KNOWLEDGE_TOOL: "Retrieve prepared task knowledge.",
        CORRECTIVE_MEMORY_TOOL: "Read admitted corrective guidance.",
        PREPARED_SPEECH_OBSERVATION_TOOL: "Read a prepared speech transcript.",
        LIVE_SPEECH_OBSERVATION_TOOL: "Transcribe the current full utterance on demand.",
    }
    if tool_id in {TASK_CONTRACT_TOOL, CORRECTIVE_MEMORY_TOOL}:
        properties = {}
        required = []
    elif tool_id == PHASE_KNOWLEDGE_TOOL:
        properties = {"view": {"type": "string", "enum": list(views)}}
        required = ["view"]
    elif tool_id == CANDIDATE_CONTRACT_TOOL:
        properties = {"candidate_ids": {
            "type": "array", "minItems": 1, "maxItems": candidate_limit,
            "uniqueItems": True, "items": {"type": "string", "minLength": 1},
        }}
        required = ["candidate_ids"]
    else:
        properties = {
            "span": {"type": "string", "enum": ["full-utterance"]},
            "representation": {"type": "string", "enum": ["asr-transcript"]},
            "distinction": {"type": "string", "minLength": 1, "maxLength": 512},
        }
        required = ["span", "representation", "distinction"]
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
        self._records = {}
        self._native_rejections = []
        if (
            any(set(spec["knowledge_views"]) - {"text"} for spec in specs.values())
            and knowledge_catalog is None
        ):
            raise PhaseToolError(
                "speech/paired action requires a prepared knowledge catalog"
            )
        if any(
            PHASE_KNOWLEDGE_TOOL in s["allowed_tools"] for s in specs.values()
        ) and not callable(supply_for_phase):
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
            LIVE_SPEECH_OBSERVATION_TOOL in spec["allowed_tools"]
            for spec in specs.values()
        ) and live_speech_observations is None:
            raise PhaseToolError("live speech observation action requires a loaded provider")
        if self.native_enabled and not callable(tool_contact):
            raise PhaseToolError("native tools require a tool contact custodian")

    @property
    def native_enabled(self):
        return getattr(self.program, "stop_rule", None) == "native-answer-or-tool"

    def is_native_phase(self, phase):
        spec = self.specs.get(phase)
        return bool(self.native_enabled and spec and spec["mode"] == "native-tools")

    def native_tool_schemas(self):
        if not self.native_enabled:
            return ()
        ordered = []
        seen = set()
        for phase in self.program.phase_names()[:-1]:
            for tool_id in self.specs[phase]["allowed_tools"]:
                if tool_id not in seen:
                    ordered.append(_native_tool_schema(
                        tool_id, self.specs[phase]["knowledge_views"],
                        candidate_limit=self.specs[phase].get("candidate_limit"),
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

    def __call__(self, phase, next_phase, context):
        spec = self.specs.get(phase)
        if spec is None:
            return None
        phases = self.program.phase_names()
        if next_phase != phases[phases.index(phase) + 1]:
            raise PhaseToolError("action successor differs from the program")
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
        key = (context.sample_id, phase)
        with self._lock:
            if key in self._attempts:
                raise PhaseToolError(
                    "tool action already attempted for this phase/sample"
                )
            self._attempts.add(key)
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
                )
                if not isinstance(invocation, Mapping):
                    raise PhaseToolError(
                        "tool contact custodian returned no invocation receipt"
                    )
                content_hash(invocation)
                request["tool_invocation"] = dict(invocation)
            if action["tool_id"] == TASK_CONTRACT_TOOL:
                output = tool.call(context)
            elif action["tool_id"] == CANDIDATE_CONTRACT_TOOL:
                output = tool.call(
                    self.candidate_contracts, action["arguments"]["candidate_ids"]
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
            elif action["tool_id"] == CORRECTIVE_MEMORY_TOOL:
                output = tool.call(self.experience_memory, next_phase, context)
            else:
                output = tool.call(self.supply_for_phase, next_phase, context)
            if output.tool_id != action["tool_id"] or output.derivation is not None:
                raise PhaseToolError(
                    "tool returned a different identity or unexpected derivation"
                )
            supply = None
            cited = ()
            if action["tool_id"] == PHASE_KNOWLEDGE_TOOL:
                supply = output.result
                if not isinstance(supply, PhaseSupply):
                    raise PhaseToolError("knowledge tool did not return a PhaseSupply")
                supply.validate()
                from .knowledge import assert_knowledge_use_binding

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
                    "rank_sha256": content_hash(supply.rank_result.as_json()),
                    "fusion_sha256": content_hash(supply.fusion_decision.as_json()),
                }
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
            }:
                if not isinstance(output.result, SpeechObservationSelection):
                    raise PhaseToolError("speech observation tool returned an unbound selection")
                if action["tool_id"] == LIVE_SPEECH_OBSERVATION_TOOL:
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
                if action["tool_id"] == LIVE_SPEECH_OBSERVATION_TOOL:
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
                if action["tool_id"] == PHASE_KNOWLEDGE_TOOL:
                    native_content = list(self._value_renderer.assemble(
                        cited, view=action["arguments"]["view"],
                    ))
                elif action["tool_id"] in {
                    PREPARED_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_OBSERVATION_TOOL,
                }:
                    native_content = [output.result.content_block()]
                else:
                    native_content = []
                request["native_result_content"] = native_content
                request["native_result_content_sha256"] = content_hash(
                    {"blocks": native_content}
                )
            document = {
                **request,
                "schema": "saea-phase-tool-result-v1",
                "result": result,
                "result_sha256": content_hash(result),
            }
            artifact = AgentStateArtifact(
                state_id=f"tool-result:{phase}:{context.sample_id}",
                state_kind="tool-result",
                content=json.dumps(document, sort_keys=True),
                source_query_state_sha256=expected,
                source_response_sha256=source.source_response_sha256,
                producer_policy_id=self.program.program_id,
                cited_value_ids=cited,
            ).validate()
            receipt_document = document
            if action["tool_id"] == CORRECTIVE_MEMORY_TOOL:
                receipt_document = {
                    **document,
                    "internal_memory_lineage": dict(output.result.lineage),
                }
            if action["tool_id"] in {
                PREPARED_SPEECH_OBSERVATION_TOOL,
                LIVE_SPEECH_OBSERVATION_TOOL,
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

    def _parse_native_action(self, context, source, spec):
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
            calls = completion.tool_calls
        except Exception as error:
            raise PhaseToolError("native completion binding or tool calls are malformed") from error
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
        )
        if action["tool_id"] == CANDIDATE_CONTRACT_TOOL:
            if not set(action["arguments"]["candidate_ids"]) <= set(self._candidate_ids):
                raise PhaseToolError("candidate request contains unknown legal IDs")
        return action, {
            "call_id": call["id"],
            "completion": completion,
        }

    def _native_error(self, phase, context, source, expected, message):
        document = {
            "schema": "saea-phase-tool-error-v1",
            "selection_mode": "native-tools",
            "error": message,
            "query_state_sha256": expected,
            "source_response_sha256": source.source_response_sha256,
        }
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

    def _emit(self, sample_id, phase, event, payload):
        if self.trace_sink is not None:
            axis = "OBS" if payload.get("tool_id") in {PREPARED_SPEECH_OBSERVATION_TOOL, LIVE_SPEECH_OBSERVATION_TOOL} else "USE"
            self.trace_sink.emit(
                axis,
                f"{sample_id}/{self.program.program_id}/{phase}/tool-{event}",
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
            result = document.get("result", {})
            if document.get("tool_id") in {
                PREPARED_SPEECH_OBSERVATION_TOOL,
                LIVE_SPEECH_OBSERVATION_TOOL,
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
        return tuple(blocks + observations)

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
            if row["tool_id"] == LIVE_SPEECH_OBSERVATION_TOOL
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
    )
