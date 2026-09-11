"""Bounded, opt-in task actions over the shared tool and state rails.

The native catalog remains system-invoked. This bridge explicitly records
whether its task-level selection came from a fixed policy or the frozen core;
no historical toolkit acquires model-selected semantics merely by registering.
"""

from __future__ import annotations
import json
import hashlib
from threading import Lock
from typing import Mapping
from .errors import RailsError
from .knowledge import AgentStateArtifact, content_hash
from .tools import resolve_tool, assert_pinned_hash
from .controllers import PhaseSupply, PhaseToolStep
from .experience_memory_runtime import (
    CORRECTIVE_MEMORY_TOOL,
    ExperienceMemorySelection,
)

TASK_CONTRACT_TOOL = "saea-tool-task-contract-v1"
PHASE_KNOWLEDGE_TOOL = "saea-tool-phase-knowledge-v1"
ACTION_TOOLS = frozenset(
    {TASK_CONTRACT_TOOL, PHASE_KNOWLEDGE_TOOL, CORRECTIVE_MEMORY_TOOL}
)
MODES = frozenset({"fixed", "core-choice"})
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
        }:
            raise PhaseToolError("phase_tools entry has unknown fields")
        mode = entry.get("mode")
        if not isinstance(mode, str) or mode not in MODES:
            raise PhaseToolError("phase_tools mode must be fixed or core-choice")
        tools = _unique(entry.get("allowed_tools"), ACTION_TOOLS, "allowed_tools")
        views = _unique(
            entry.get("knowledge_views", ["text"]), VIEWS, "knowledge_views"
        )
        fixed = entry.get("fixed_action")
        if mode == "fixed":
            _validate_action(fixed, tools, views)
        elif "fixed_action" in entry:
            raise PhaseToolError("core-choice cannot declare a fixed_action")
        for tool_id in tools:
            assert_pinned_hash(resolve_tool(tool_id).manifest)
        specs[phase] = {
            "mode": mode,
            "allowed_tools": tools,
            "knowledge_views": views,
            "fixed_action": fixed,
        }
    return specs


def _validate_action(action, allowed, views):
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
    return {"tool_id": tool_id, "arguments": dict(args)}


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
    ):
        self.specs = specs
        self.program = program
        self.snapshot = snapshot.validate()
        self.snapshot_sha256 = snapshot.content_hash()
        self.knowledge_catalog = knowledge_catalog
        self.experience_memory = experience_memory
        from .knowledge_value_views import KnowledgeValueRenderer

        self._value_renderer = KnowledgeValueRenderer(
            snapshot, catalog=knowledge_catalog
        )
        self.supply_for_phase = supply_for_phase
        self.trace_sink = trace_sink
        self._lock = Lock()
        self._attempts = set()
        self._records = {}
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

    def instruction_for_phase(self, phase, context):
        spec = self.specs.get(phase)
        if spec is None or spec["mode"] != "core-choice":
            return ""
        descriptions = {
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
        if spec["mode"] == "fixed":
            action = _validate_action(
                spec["fixed_action"], spec["allowed_tools"], spec["knowledge_views"]
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
        self._emit(context.sample_id, phase, "attempt", request)
        try:
            if action["tool_id"] == TASK_CONTRACT_TOOL:
                output = tool.call(context)
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
            elif action["tool_id"] == TASK_CONTRACT_TOOL:
                if not isinstance(output.result, Mapping) or output.result != {
                    "task_contract": context.task_contract
                }:
                    raise PhaseToolError(
                        "task-contract tool returned an unbound result"
                    )
                result = dict(output.result)
            else:
                if not isinstance(output.result, ExperienceMemorySelection):
                    raise PhaseToolError(
                        "corrective-memory tool did not return a bound selection"
                    )
                result = dict(output.result.visible)
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

    def _emit(self, sample_id, phase, event, payload):
        if self.trace_sink is not None:
            self.trace_sink.emit(
                "USE",
                f"{sample_id}/{self.program.program_id}/{phase}/tool-{event}",
                {f"use_{key}": value for key, value in payload.items()},
            )

    def render_values(self, snapshot, query_state, agent_states):
        """Assemble actual evidence from the latest source-bound tool selections."""
        selections = {}
        for artifact in agent_states:
            if artifact.state_kind != "tool-result":
                continue
            document = json.loads(artifact.content)
            result = document.get("result", {})
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
        return tuple(blocks)

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
        if memory_lineage:
            receipt["memory_lineage"] = memory_lineage
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
    )
