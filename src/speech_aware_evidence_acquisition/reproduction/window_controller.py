"""Single-phase controller bridge over the shared OBS/OpenJiuwen window seam.

The controller dispatches each actual window instruction and seals the raw
terminal model response. The existing hook still owns delivery. A skipped
window has no response and never receives a fabricated controller advance.
This bridge makes no claim of live multi-phase history or knowledge supply.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Mapping

from ..contracts import ExecutionPlan
from ..core.base import CoreError
from ..rails.controllers import EvidenceAgentController, default_phase_program
from ..rails.hashing import content_hash
from ..rails.knowledge import QueryState
from ..rails.material import PhaseMaterial
from ..rails.runner import AgentRuntimeContext

PROGRAM_KEY = "obs_controller_program"
DIRECT_PROGRAM = "phase-direct-only-v1"
_NULL_KNOWLEDGE = {"schema": "saea-window-controller-context-v1", "knowledge": "none"}


def _controller_knowledge(ctx):
    """Hash the actual external evidence a window carries, when present."""
    evidence = tuple(getattr(ctx, "evidence", ()))
    if not evidence:
        return _NULL_KNOWLEDGE
    return {
        "schema": "saea-window-controller-context-v2",
        "knowledge": "external-evidence",
        "items": [
            {
                "evidence_id": item.evidence_id,
                "source_uri": item.source_uri,
                "content_sha256": hashlib.sha256(item.content.encode("utf-8")).hexdigest(),
                "derivation_identity_sha256": (
                    content_hash(item.derivation.trace_view())
                    if item.derivation is not None
                    else None
                ),
            }
            for item in evidence
        ],
    }


class WindowControllerError(CoreError):
    """An unsupported controller bridge or inconsistent terminal binding refuses."""


def validate_window_controller(values: Mapping) -> bool:
    """Admit only the explicit single-phase bridge, with no inert module switches."""
    program_id = values.get(PROGRAM_KEY)
    if program_id is None:
        return False
    if program_id != DIRECT_PROGRAM:
        raise WindowControllerError(
            "window controller currently supports phase-direct-only-v1 only"
        )
    if values.get("policy") not in (
        "obs-agent-loop",
        "obs-agent-loop-ojw",
        "obs-repair-loop",
        "obs-repair-loop-ojw",
    ):
        raise WindowControllerError("window controller requires the shared OBS policy")
    if (
        values.get("obs_boundary_mode", "fixed") != "fixed"
        or values.get("obs_condition_tail_chars", 0)
        or values.get("obs_vad_trim_min_seconds", 0)
    ):
        raise WindowControllerError(
            "window controller requires fixed, zero-tail, untrimmed windows"
        )
    for key in (
        "phase_supply",
        "phase_review",
        "phase_planner",
        "judges",
        "knowledge_views",
        "observe",
        "toolkits",
    ):
        if values.get(key):
            raise WindowControllerError(
                f"single-phase window bridge cannot execute {key}"
            )
    return True


@dataclass
class _Window:
    controller: EvidenceAgentController
    context: AgentRuntimeContext
    contact: object
    slice_sha256: str
    knowledge: Mapping[str, object]
    raw_response: str | None = None
    terminal_request_id: str | None = None
    skipped: bool = False
    saturated: bool = False
    accepted: bool = False


class ControllerWindowHook:
    """Compose a direct or repair hook with the actual shared controller base."""

    def __init__(self, ctx, delegate=None):
        self._ctx, self._delegate = ctx, delegate
        self._program = default_phase_program(DIRECT_PROGRAM)
        plan = ctx.extras.get("execution_plan")
        if not isinstance(plan, ExecutionPlan):
            raise WindowControllerError(
                "window controller requires the actual ExecutionPlan"
            )
        self._split_hash = plan.split_identity_hash
        self._windows: dict[int, _Window] = {}

    def instruction(self, *, iteration, record, default):
        instruction = (
            default
            if self._delegate is None
            else self._delegate.instruction(
                iteration=iteration, record=record, default=default
            )
        )
        existing = self._windows.get(iteration)
        if existing is not None:
            if (
                existing.slice_sha256 != record.sha256
                or existing.contact.instruction != instruction
                or existing.accepted
            ):
                raise WindowControllerError(
                    "retried window changed its speech or instruction"
                )
            return existing.contact.instruction
        packet_id, packet_sha256, query_source = (
            record.media_relpath, record.sha256, "speech_audio"
        )
        prepared_packets = self._ctx.extras.get("window_feature_packets")
        if prepared_packets is not None:
            binding = prepared_packets.binding_for(
                f"{self._ctx.sample.sample_id}#w{iteration + 1:04d}", record.trace_view()
            )
            packet_id, packet_sha256, query_source = (
                binding.packet_id, binding.packet_sha256, "speech_features"
            )
        query = QueryState(
            query_id=f"{self._ctx.request_id_base}-i{iteration:04d}",
            query_sample_id=self._ctx.sample.sample_id,
            speech_packet_id=packet_id,
            speech_packet_sha256=packet_sha256,
            use_split_identity_hash=self._split_hash,
            query_source=query_source,
        ).validate()
        knowledge = _controller_knowledge(self._ctx)
        context = AgentRuntimeContext(
            sample_id=self._ctx.sample.sample_id,
            knowledge_snapshot_sha256=content_hash(knowledge),
            catalog_facet_ids=(),
            catalog_value_ids=(),
            query_state=query,
            task_contract=self._ctx.task_instruction,
            agent_states=(),
            prior_response_sha256s=(),
            contact_index=0,
        )
        material = PhaseMaterial(instruction, None, query.query_id, "window-decode")
        controller = EvidenceAgentController(
            program=self._program,
            material_for_phase=lambda _phase, _context: material,
            state_namespace=query.query_id,
        )
        contact = controller.initial_contact(context)
        self._windows[iteration] = _Window(
            controller, context, contact, record.sha256, knowledge
        )
        return contact.instruction

    def terminal(self, *, iteration, request_id, response, skipped, saturated):
        window = self._windows.get(iteration)
        if window is None or window.terminal_request_id is not None:
            raise WindowControllerError("terminal window is absent or already recorded")
        if not isinstance(skipped, bool) or not isinstance(saturated, bool):
            raise WindowControllerError("terminal window flags must be booleans")
        if (response is None) != skipped:
            raise WindowControllerError("terminal skipped/response binding disagrees")
        if (
            not isinstance(request_id, str)
            or re.fullmatch(
                re.escape(window.contact.contact_id) + r"(?:-r[1-9][0-9]*)?", request_id
            )
            is None
        ):
            raise WindowControllerError(
                "terminal request identity is not this window or its retry"
            )
        window.terminal_request_id = request_id
        window.raw_response = None if response is None else response.text
        window.skipped, window.saturated = skipped, saturated

    def accept(self, *, iteration, record, transcript, saturated=False, skipped=False):
        window = self._windows.get(iteration)
        if window is None or window.terminal_request_id is None or window.accepted:
            raise WindowControllerError(
                "window delivery requires one authoritative terminal record"
            )
        if window.slice_sha256 != record.sha256 or (skipped, saturated) != (
            window.skipped,
            window.saturated,
        ):
            raise WindowControllerError("terminal window delivery binding changed")
        transition, sealed = None, None
        if not skipped:
            advance = window.controller.advance(
                window.context, window.contact, window.raw_response
            )
            if (
                advance.next_contact is not None
                or advance.next_query_state is not None
                or advance.final_response_contact_id != window.contact.contact_id
            ):
                raise WindowControllerError(
                    "single-phase window controller failed to stop"
                )
            transition = advance.transition.as_json()
            sealed = window.controller.sealed_states["direct"].as_json()
        if self._delegate is None:
            delivered, fields = transcript, {}
        else:
            delivered, fields = self._delegate.accept(
                iteration=iteration,
                record=record,
                transcript=transcript,
                saturated=saturated,
                skipped=skipped,
            )
        self._ctx.sink.emit(
            "USE",
            f"{window.terminal_request_id}/window-controller",
            {
                "use_program_id": self._program.program_id,
                "use_program_sha256": content_hash(self._program.as_json()),
                "use_context": dict(window.knowledge),
                "use_query_state": window.context.query_state.as_json(),
                "use_contact": window.contact.as_json(),
                "use_terminal_request_id": window.terminal_request_id,
                "use_skipped": skipped,
                "use_saturated": saturated,
                "use_transition": transition,
                "use_sealed_state": sealed,
                "use_delivered_text_sha256": hashlib.sha256(
                    delivered.encode("utf-8")
                ).hexdigest(),
                "use_scope": "single-phase window compatibility; no live multi-phase history",
            },
        )
        window.accepted = True
        return delivered, {**fields, "obs_controller_program": self._program.program_id}


def build_controller_window_hook(ctx, cfg, delegate=None):
    values = ctx.extras["config_values"]
    return (
        ControllerWindowHook(ctx, delegate)
        if validate_window_controller(values)
        else delegate
    )


def record_controller_terminal(
    hook, *, iteration, request_id, response, skipped, saturated
):
    """Record the actual terminal retry once; leave historical hooks unchanged."""
    terminal = getattr(hook, "terminal", None)
    if callable(terminal):
        terminal(
            iteration=iteration,
            request_id=request_id,
            response=response,
            skipped=skipped,
            saturated=saturated,
        )
