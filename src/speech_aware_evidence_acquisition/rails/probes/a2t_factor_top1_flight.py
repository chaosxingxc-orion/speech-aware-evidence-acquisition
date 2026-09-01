"""Flight boundary for the semantic-factor top-1 Audio2Tool AgentLoop.

One speech-conditioned contact produces a bounded ORG artifact. Deterministic
BM25 then selects at most one frozen external-governed registry value. One
later contact retains the original speech and is the only new task-answer
authority. Invalid factor output is represented by a fixed English sentinel
and receives no registry value; scoring-side composition returns frozen M0 for
that unavailable action.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Mapping, Sequence

from ...analysis import training_free_a2t_factor_top1 as factor
from ...data.audio2tool import render_registry_row
from ..knowledge import (
    AgentStateArtifact,
    AgentStepTransition,
    FusionDecision,
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    RankedFacet,
    RankResult,
    ValueBundle,
)
from ..runner import AgentContactPlan, AgentLoopAdvance, AgentRuntimeContext

FACTOR_CONTACT_ID = "semantic-factor"
FINAL_CONTACT_ID = "factor-top1-final"
CONTROLLER_POLICY_ID = "saea-a2t-factor-top1-agentloop-v1"
SNAPSHOT_BUILDER_ID = "saea-a2t-registry-snapshot-v1"
FACTOR_STATE_KIND = "speech-semantic-factors"
INVALID_FACTOR_SENTINEL = (
    "Semantic factor parsing failed; no factor state is available."
)
FACTOR_FIELDS = frozenset(
    {
        "task_action",
        "task_object",
        "qualifiers",
        "argument_hints",
        "uncertainty",
    }
)


class A2TFactorTop1FlightError(RuntimeError):
    """The flight boundary refused an invalid or unregistered trajectory."""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _registry_identity(registry_sha256: str) -> str:
    if (
        not isinstance(registry_sha256, str)
        or len(registry_sha256) != 64
        or any(character not in "0123456789abcdef" for character in registry_sha256)
    ):
        raise A2TFactorTop1FlightError(
            "registry_sha256 must be lowercase 64-hex"
        )
    return f"external:audio2tool-registry:{registry_sha256}"


def _ordered_registry(
    registry_rows: Sequence[Mapping[str, str]],
) -> tuple[tuple[int, Mapping[str, str]], ...]:
    ordered: list[tuple[int, Mapping[str, str]]] = []
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    for row in registry_rows:
        name = row.get("tool_name")
        if not isinstance(name, str) or not name:
            raise A2TFactorTop1FlightError(
                "registry row lacks a non-empty tool_name"
            )
        try:
            tool_id = int(row.get("tool_id", ""))
        except (TypeError, ValueError):
            raise A2TFactorTop1FlightError(
                f"registry tool {name!r} lacks numeric tool_id"
            ) from None
        if tool_id in seen_ids or name in seen_names:
            raise A2TFactorTop1FlightError(
                "registry tool ids and names must be unique"
            )
        seen_ids.add(tool_id)
        seen_names.add(name)
        ordered.append((tool_id, row))
    if not ordered:
        raise A2TFactorTop1FlightError("registry must contain at least one row")
    return tuple(sorted(ordered, key=lambda item: (item[0], item[1]["tool_name"])))


def _facet_id(tool_id: int) -> str:
    return f"registry-facet:{tool_id}"


def _value_id(tool_id: int) -> str:
    return f"registry-value:{tool_id}"


def build_registry_snapshot(
    registry_rows: Sequence[Mapping[str, str]],
    *,
    registry_sha256: str,
) -> KnowledgeSnapshot:
    """Build a deterministic external-governed snapshot from the registry."""

    ordered = _ordered_registry(registry_rows)
    source_id = _registry_identity(registry_sha256)
    source_split_identity = _sha256_text(f"{source_id}\n")
    facets = tuple(
        KeyFacet(
            facet_id=_facet_id(tool_id),
            dimension="content",
            representation_kind="text",
            representation=factor.registry_document_text(row),
            source_sample_ids=(source_id,),
        ).validate()
        for tool_id, row in ordered
    )
    values = tuple(
        ValueBundle(
            value_id=_value_id(tool_id),
            content=render_registry_row(row, strip_defaults=True),
            associated_facet_ids=(_facet_id(tool_id),),
            source_sample_ids=(source_id,),
            provenance_refs=(
                f"audio2tool-registry-sha256:{registry_sha256}",
                f"audio2tool-registry-tool-id:{tool_id}",
            ),
            task_target=row["tool_name"],
            prior_score=None,
        ).validate()
        for tool_id, row in ordered
    )
    return KnowledgeSnapshot(
        snapshot_id=f"audio2tool-registry-{registry_sha256[:16]}",
        source_split_identity_hash=source_split_identity,
        source_sample_ids=(source_id,),
        builder_policy_id=SNAPSHOT_BUILDER_ID,
        facets=facets,
        values=values,
        source_partition_role="external-governed",
    ).validate()


def factor_response_format() -> dict[str, object]:
    ascii_phrase = {
        "type": "string",
        "minLength": 0,
        "maxLength": 80,
        "pattern": r"^[\x20-\x7e]*$",
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "speech_semantic_factors",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "task_action": dict(ascii_phrase),
                    "task_object": dict(ascii_phrase),
                    "qualifiers": {
                        "type": "array",
                        "maxItems": 4,
                        "items": dict(ascii_phrase),
                    },
                    "argument_hints": {
                        "type": "array",
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": dict(ascii_phrase),
                                "value_hint": dict(ascii_phrase),
                            },
                            "required": ["role", "value_hint"],
                            "additionalProperties": False,
                        },
                    },
                    "uncertainty": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
                "required": [
                    "task_action",
                    "task_object",
                    "qualifiers",
                    "argument_hints",
                    "uncertainty",
                ],
                "additionalProperties": False,
            },
        },
    }


@dataclass(frozen=True)
class ControllerObservation:
    factor_parse: factor.FactorParse
    retrieval: factor.Top1Retrieval


class FactorTop1Controller:
    """Two-contact controller: ORG factors, then exactly-one-row final USE."""

    def __init__(
        self,
        registry_rows: Sequence[Mapping[str, str]],
        snapshot: KnowledgeSnapshot,
    ) -> None:
        self._registry_rows = tuple(row for _tool_id, row in _ordered_registry(registry_rows))
        self._tool_names = tuple(row["tool_name"] for row in self._registry_rows)
        self._snapshot = snapshot.validate()
        self._facet_ids = {int(row["tool_id"]): _facet_id(int(row["tool_id"])) for row in self._registry_rows}
        self._value_ids = {int(row["tool_id"]): _value_id(int(row["tool_id"])) for row in self._registry_rows}
        if set(self._facet_ids.values()) != {item.facet_id for item in snapshot.facets}:
            raise A2TFactorTop1FlightError(
                "registry rows do not match snapshot facet identities"
            )
        if set(self._value_ids.values()) != {item.value_id for item in snapshot.values}:
            raise A2TFactorTop1FlightError(
                "registry rows do not match snapshot value identities"
            )

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if context.query_state.loop_step != 0:
            raise A2TFactorTop1FlightError(
                "initial factor contact requires loop step zero"
            )
        return AgentContactPlan(
            contact_id=FACTOR_CONTACT_ID,
            query_state_sha256=context.query_state.content_hash(),
            purpose="organize-speech-semantic-factors",
            instruction=(
                "Analyze the original speech without transcribing it. Describe only "
                "task semantics in English. Do not name, choose, or emit a tool or "
                "tool-call list. Return only one raw JSON object with the exact "
                "required factor fields in assistant content."
            ),
            key_representation_id=f"{CONTROLLER_POLICY_ID}:speech-factors",
            matcher_policy_id=factor.RETRIEVER_POLICY_ID,
            decoding_params={"max_tokens": 256},
        ).validate()

    def _final_contact(self, query_state: QueryState) -> AgentContactPlan:
        return AgentContactPlan(
            contact_id=FINAL_CONTACT_ID,
            query_state_sha256=query_state.content_hash(),
            purpose="answer-with-factor-top1-evidence",
            instruction=(
                "Produce the final task answer from the original speech. Use the "
                "semantic factor state and the single supplied registry row when "
                "they are available. Respond only with the task contract's JSON "
                "array of tool calls."
            ),
            key_representation_id=f"{CONTROLLER_POLICY_ID}:factor-top1",
            matcher_policy_id=factor.RETRIEVER_POLICY_ID,
            decoding_params={},
        ).validate()

    def _organize(
        self,
        context: AgentRuntimeContext,
        response_text: str,
    ) -> AgentLoopAdvance:
        parsed = factor.parse_semantic_factors(
            response_text,
            registry_tool_names=self._tool_names,
        )
        if parsed.status == "valid-nonempty" and parsed.factors is not None:
            retrieval = factor.retrieve_registry_top1(
                parsed.factors, self._registry_rows
            )
        else:
            retrieval = factor.Top1Retrieval(
                available=False,
                tool_id=None,
                tool_name=None,
                score=0.0,
                second_score=0.0,
                ranking_relation="no-positive",
                positive_document_count=0,
                matched_token_fraction=0.0,
                prompt_block="",
            )
        state_id = f"state:{context.sample_id}:semantic-factor"
        state = AgentStateArtifact(
            state_id=state_id,
            state_kind=FACTOR_STATE_KIND,
            content=(
                parsed.canonical_json
                if parsed.status == "valid-nonempty"
                else INVALID_FACTOR_SENTINEL
            ),
            source_query_state_sha256=context.query_state.content_hash(),
            source_response_sha256=_sha256_text(response_text),
            producer_policy_id=CONTROLLER_POLICY_ID,
            cited_value_ids=(),
        ).validate()

        rank_result: RankResult | None = None
        fusion_decision: FusionDecision | None = None
        new_value_ids: tuple[str, ...] = ()
        new_facet_ids: tuple[str, ...] = ()
        if retrieval.available and retrieval.tool_id is not None:
            facet_id = self._facet_ids[retrieval.tool_id]
            value_id = self._value_ids[retrieval.tool_id]
            rank_result = RankResult(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                query_state_sha256=context.query_state.content_hash(),
                ranking_policy_id=factor.RETRIEVER_POLICY_ID,
                candidates=(RankedFacet(facet_id, retrieval.score),),
            ).validate()
            fusion_decision = FusionDecision(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                query_state_sha256=context.query_state.content_hash(),
                rank_result_sha256=rank_result.content_hash(),
                fusion_policy_id=f"{CONTROLLER_POLICY_ID}:single-row",
                supporting_facet_ids=(facet_id,),
                selected_value_ids=(value_id,),
            ).validate()
            new_value_ids = (value_id,)
            new_facet_ids = (facet_id,)

        next_state = QueryState(
            query_id=context.query_state.query_id,
            query_sample_id=context.query_state.query_sample_id,
            speech_packet_id=context.query_state.speech_packet_id,
            speech_packet_sha256=context.query_state.speech_packet_sha256,
            use_split_identity_hash=context.query_state.use_split_identity_hash,
            loop_step=1,
            visible_facet_ids=new_facet_ids,
            agent_state_ids=(state_id,),
            retrieved_value_ids=new_value_ids,
        ).validate()
        action_target_refs = (
            (
                f"rank-result:{rank_result.content_hash()}",
                f"fusion-decision:{fusion_decision.content_hash()}",
                f"agent-state:{state_id}",
            )
            if rank_result is not None and fusion_decision is not None
            else (f"agent-state:{state_id}",)
        )
        transition = AgentStepTransition(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            prior_query_state_sha256=context.query_state.content_hash(),
            next_query_state_sha256=next_state.content_hash(),
            action_kind="acquire" if new_value_ids else "organize",
            action_target_refs=action_target_refs,
            new_value_ids=new_value_ids,
            used_value_ids=(),
            dropped_value_ids=(),
            new_agent_state_ids=(state_id,),
            dropped_agent_state_ids=(),
            new_facet_ids=new_facet_ids,
        ).validate()
        return AgentLoopAdvance(
            transition=transition,
            next_query_state=next_state,
            new_agent_states=(state,),
            next_contact=self._final_contact(next_state),
            rank_result=rank_result,
            fusion_decision=fusion_decision,
        )

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: object,
    ) -> AgentLoopAdvance:
        if not isinstance(contact, AgentContactPlan) or not isinstance(
            response_text, str
        ):
            raise A2TFactorTop1FlightError(
                "factor top-1 controller requires one contact and one string response"
            )
        if context.query_state.loop_step == 0:
            if contact.contact_id != FACTOR_CONTACT_ID:
                raise A2TFactorTop1FlightError(
                    "loop step zero received the wrong factor contact"
                )
            return self._organize(context, response_text)
        if context.query_state.loop_step != 1 or contact.contact_id != FINAL_CONTACT_ID:
            raise A2TFactorTop1FlightError(
                "factor top-1 controller received an invalid contact sequence"
            )
        return AgentLoopAdvance(
            transition=AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=context.query_state.content_hash(),
                next_query_state_sha256=None,
                action_kind="stop",
                action_target_refs=(),
                new_value_ids=(),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(),
                dropped_agent_state_ids=(),
            ).validate(),
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
            final_response_contact_id=FINAL_CONTACT_ID,
        )


__all__ = [
    "CONTROLLER_POLICY_ID",
    "FACTOR_CONTACT_ID",
    "FACTOR_FIELDS",
    "FACTOR_STATE_KIND",
    "FINAL_CONTACT_ID",
    "INVALID_FACTOR_SENTINEL",
    "SNAPSHOT_BUILDER_ID",
    "A2TFactorTop1FlightError",
    "ControllerObservation",
    "FactorTop1Controller",
    "build_registry_snapshot",
    "factor_response_format",
]
