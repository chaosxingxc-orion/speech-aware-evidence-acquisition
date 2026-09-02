"""Generic G5 same-core PLAN -> COMPILE -> EXECUTE AgentLoop boundary.

PLAN and EXECUTE are the only frozen-core contacts.  The injected family
compiler is a deterministic, contact-free capability: it receives only the
validated closed-taxonomy plan (or its frozen fallback family union) and
returns every compatible frozen contract.  The plan is traced as ORG, the
selected contract values as SUPPLY, and EXECUTE is the sole final USE.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ...core.base import Registry
from ..adapters.audio2tool import Audio2ToolSample
from ..consumption import ConsumptionTrace, build_consumption_trace
from ..hashing import content_hash
from ..knowledge import (
    AgentStateArtifact,
    AgentStepTransition,
    FusionDecision,
    KnowledgeSnapshot,
    QueryState,
    RankResult,
    RankedFacet,
)
from ..runner import (
    AgentContact,
    AgentContactPlan,
    AgentLoopAdvance,
    AgentResponse,
    AgentRuntimeContext,
    run_speech_native_agent_loop,
)
from ..task_adapter import TaskAdapter
from .a2t_contract_preserving_cascade_flight import AGENT_EXECUTOR_ID

PLAN_STATE_ASCII_BYTE_CAP = 4_096
BUNDLE_ASCII_BYTE_CAP = 18_432
PER_SLOT_PROMPT_TOKENS = 32_768
PLAN_COMPLETION_TOKENS = 256
EXECUTE_COMPLETION_TOKENS = 1_024
DEFAULT_SPECIAL_TOKEN_RESERVE = 512
G5_SLOT_COUNT = 2
G5_QUEUE_DEPTH = 4
G5_TRACE_PHASES = ("OBS", "ORG", "SUPPLY", "USE")

PLAN_STATUS = "VALID"
FALLBACK_STATUS = "INVALID_FALLBACK"
PLAN_CONTACT_ID = "g5-plan"
EXECUTE_CONTACT_ID = "g5-execute"
CONTROLLER_POLICY_ID = "saea-a2t-g5-plan-compile-execute-v1"
PLAN_STATE_KIND = "g5-closed-family-plan-v1"
COMPILER_POLICY_ID = "g5-full-unranked-family-compiler-v1"

_PLAN_KEYS = frozenset({"operations"})
_OPERATION_KEYS = frozenset(
    {
        "family",
        "operation",
        "values",
        "correction",
        "supersedes",
        "turn_refs",
        "role",
    }
)
_VALUE_KEYS = frozenset({"label", "span"})
_TURN_REF = re.compile(r"(?:current|prior:[1-9][0-9]*)\Z")
_ROLES = frozenset({"user", "assistant", "other"})
_FORBIDDEN_RUNTIME_FIELD = re.compile(
    r"(?i)(?:^|[^a-z0-9_])(?:gold|expected_calls|sample_id|tier_hint|reward|score)\s*:"
)

_PLAN_INSTRUCTION = (
    "PLAN only from the original speech and the closed family taxonomy. Return "
    "exactly one compact ASCII JSON object with ordered operations. Each operation "
    "must contain exactly family, operation, values, correction, supersedes, "
    "turn_refs, and role; each value must contain exactly label and span. Use only "
    "declared family and operation tags. Emit no tool names, no calls, no final "
    "answer, no metadata, and no sample or evaluation fields. Exact shape: "
    '{"operations":[{"family":"<family-tag>","operation":"<operation-tag>",'
    '"values":[{"label":"<span-label>","span":"<speech-span>"}],'
    '"correction":false,"supersedes":[],"turn_refs":["current"],'
    '"role":"user"}]}. Use prior:N for an earlier turn and use zero-based '
    "operation indexes in supersedes."
)
_EXECUTE_INSTRUCTION = (
    "EXECUTE the final answer from the original speech, the validated parsed PLAN "
    "state, and the complete unranked compatible family-contract bundle. Preserve "
    "operation order unless the PLAN correction and supersedes fields direct a "
    "replacement. Copy task values only from original speech or PLAN span labels. "
    "Return only a nonempty JSON array of registered tool-call objects with exactly "
    "name and arguments; add no prose."
)


class G5AgentLoopError(RuntimeError):
    """A G5 protocol, compiler, budget, identity, or contact invariant failed."""


def _ascii_text(value: object, *, field: str, byte_cap: int | None = None) -> str:
    if not isinstance(value, str) or not value or not value.isascii():
        raise G5AgentLoopError(f"{field} must be nonempty ASCII English")
    if _FORBIDDEN_RUNTIME_FIELD.search(value):
        raise G5AgentLoopError(f"{field} contains a forbidden runtime field")
    size = len(value.encode("ascii"))
    if byte_cap is not None and size > byte_cap:
        raise G5AgentLoopError(f"{field} byte cap exceeded: {size} > {byte_cap}")
    return value


def _unique_text_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple) or not value:
        raise G5AgentLoopError(f"{field} must be a nonempty tuple")
    if any(not isinstance(item, str) or not item or not item.isascii() for item in value):
        raise G5AgentLoopError(f"{field} must contain nonempty ASCII strings")
    if len(set(value)) != len(value):
        raise G5AgentLoopError(f"{field} must not contain duplicates")
    return value


@dataclass(frozen=True)
class FamilyTaxon:
    """One closed PLAN family and its closed operation-tag vocabulary."""

    family_tag: str
    operation_tags: tuple[str, ...]

    def validate(self) -> "FamilyTaxon":
        _ascii_text(self.family_tag, field="FamilyTaxon.family_tag")
        _unique_text_tuple(self.operation_tags, field="FamilyTaxon.operation_tags")
        return self


@dataclass(frozen=True)
class PlanValueSpan:
    label: str
    span: str


@dataclass(frozen=True)
class PlanOperation:
    family: str
    operation: str
    values: tuple[PlanValueSpan, ...]
    correction: bool
    supersedes: tuple[int, ...]
    turn_refs: tuple[str, ...]
    role: str


@dataclass(frozen=True)
class ParsedPlan:
    """Canonical plan only; invalid model bytes are never retained."""

    valid: bool
    status: str
    operations: tuple[PlanOperation, ...]
    selected_family_tags: tuple[str, ...]
    canonical_json: str


def _validated_taxonomy(
    taxonomy: Sequence[FamilyTaxon],
) -> tuple[FamilyTaxon, ...]:
    if not isinstance(taxonomy, (tuple, list)) or not taxonomy:
        raise G5AgentLoopError("taxonomy must be a nonempty sequence")
    rows = tuple(item.validate() for item in taxonomy)
    tags = tuple(item.family_tag for item in rows)
    if len(set(tags)) != len(tags):
        raise G5AgentLoopError("taxonomy family tags must be unique")
    return rows


def _validated_fallback(
    fallback_family_tags: Sequence[str], family_tags: set[str]
) -> tuple[str, ...]:
    if not isinstance(fallback_family_tags, (tuple, list)):
        raise G5AgentLoopError("fallback family tags must be an ordered sequence")
    fallback = tuple(fallback_family_tags)
    _unique_text_tuple(fallback, field="fallback_family_tags")
    if not set(fallback).issubset(family_tags):
        raise G5AgentLoopError("fallback family tags must belong to the taxonomy")
    return fallback


def _fallback_plan(fallback_family_tags: tuple[str, ...]) -> ParsedPlan:
    canonical = json.dumps(
        {"operations": [], "status": FALLBACK_STATUS}, separators=(",", ":")
    )
    return ParsedPlan(
        valid=False,
        status=FALLBACK_STATUS,
        operations=(),
        selected_family_tags=fallback_family_tags,
        canonical_json=canonical,
    )


def _json_surface(raw: str) -> str:
    stripped = raw.strip()
    if stripped.startswith("```json\n") and stripped.endswith("\n```"):
        return stripped[len("```json\n") : -len("\n```")]
    return stripped


def _contains_forbidden_term(document: object, forbidden_terms: set[str]) -> bool:
    if isinstance(document, str):
        return document.casefold() in forbidden_terms
    if isinstance(document, list):
        return any(_contains_forbidden_term(item, forbidden_terms) for item in document)
    if isinstance(document, dict):
        return any(
            _contains_forbidden_term(key, forbidden_terms)
            or _contains_forbidden_term(value, forbidden_terms)
            for key, value in document.items()
        )
    return False


def parse_plan_response(
    response_text: object,
    *,
    taxonomy: Sequence[FamilyTaxon],
    fallback_family_tags: Sequence[str],
    forbidden_terms: Sequence[str] = (),
) -> ParsedPlan:
    """Parse one exact raw/fenced JSON object; never extract, repair, or retry."""

    rows = _validated_taxonomy(taxonomy)
    operations_by_family = {
        item.family_tag: set(item.operation_tags) for item in rows
    }
    fallback = _validated_fallback(
        fallback_family_tags, set(operations_by_family)
    )
    if not isinstance(forbidden_terms, (tuple, list)) or any(
        not isinstance(item, str) or not item for item in forbidden_terms
    ):
        raise G5AgentLoopError("forbidden_terms must be an ordered string sequence")
    forbidden = {item.casefold() for item in forbidden_terms}
    invalid = _fallback_plan(fallback)
    if (
        not isinstance(response_text, str)
        or not response_text.isascii()
        or len(response_text.encode("ascii")) > PLAN_STATE_ASCII_BYTE_CAP
    ):
        return invalid
    try:
        document = json.loads(_json_surface(response_text))
        if not isinstance(document, dict) or set(document) != _PLAN_KEYS:
            return invalid
        if _contains_forbidden_term(document, forbidden):
            return invalid
        operation_rows = document["operations"]
        if not isinstance(operation_rows, list) or not operation_rows:
            return invalid
        operations: list[PlanOperation] = []
        canonical_rows: list[dict[str, object]] = []
        selected_families: list[str] = []
        for index, row in enumerate(operation_rows):
            if not isinstance(row, dict) or set(row) != _OPERATION_KEYS:
                return invalid
            family = row["family"]
            operation = row["operation"]
            role = row["role"]
            correction = row["correction"]
            if (
                not isinstance(family, str)
                or family not in operations_by_family
                or not isinstance(operation, str)
                or operation not in operations_by_family[family]
                or role not in _ROLES
                or not isinstance(correction, bool)
            ):
                return invalid
            value_rows = row["values"]
            if not isinstance(value_rows, list):
                return invalid
            values: list[PlanValueSpan] = []
            canonical_values: list[dict[str, str]] = []
            labels: set[str] = set()
            for value_row in value_rows:
                if not isinstance(value_row, dict) or set(value_row) != _VALUE_KEYS:
                    return invalid
                label = value_row["label"]
                span = value_row["span"]
                if (
                    not isinstance(label, str)
                    or not label
                    or not label.isascii()
                    or label in labels
                    or not isinstance(span, str)
                    or not span
                    or not span.isascii()
                ):
                    return invalid
                labels.add(label)
                values.append(PlanValueSpan(label, span))
                canonical_values.append({"label": label, "span": span})
            supersedes = row["supersedes"]
            if (
                not isinstance(supersedes, list)
                or any(
                    isinstance(item, bool)
                    or not isinstance(item, int)
                    or item < 0
                    or item >= index
                    for item in supersedes
                )
                or len(set(supersedes)) != len(supersedes)
                or correction != bool(supersedes)
            ):
                return invalid
            turn_refs = row["turn_refs"]
            if (
                not isinstance(turn_refs, list)
                or not turn_refs
                or any(
                    not isinstance(item, str) or _TURN_REF.fullmatch(item) is None
                    for item in turn_refs
                )
                or len(set(turn_refs)) != len(turn_refs)
            ):
                return invalid
            operation_item = PlanOperation(
                family=family,
                operation=operation,
                values=tuple(values),
                correction=correction,
                supersedes=tuple(supersedes),
                turn_refs=tuple(turn_refs),
                role=role,
            )
            operations.append(operation_item)
            if family not in selected_families:
                selected_families.append(family)
            canonical_rows.append(
                {
                    "family": family,
                    "operation": operation,
                    "values": canonical_values,
                    "correction": correction,
                    "supersedes": supersedes,
                    "turn_refs": turn_refs,
                    "role": role,
                }
            )
        canonical = json.dumps({"operations": canonical_rows}, separators=(",", ":"))
        if len(canonical.encode("ascii")) > PLAN_STATE_ASCII_BYTE_CAP:
            return invalid
        return ParsedPlan(
            valid=True,
            status=PLAN_STATUS,
            operations=tuple(operations),
            selected_family_tags=tuple(selected_families),
            canonical_json=canonical,
        )
    except (TypeError, ValueError, UnicodeError):
        return invalid


@dataclass(frozen=True)
class CompiledContract:
    contract_id: str
    family_tag: str
    facet_id: str
    value_id: str
    content: str

    def validate(self) -> "CompiledContract":
        for field in ("contract_id", "family_tag", "facet_id", "value_id"):
            _ascii_text(getattr(self, field), field=f"CompiledContract.{field}")
        _ascii_text(self.content, field="CompiledContract.content")
        return self


@dataclass(frozen=True)
class CompiledFamilyBundle:
    """Complete, ordered compiler output; no score or rank surface exists."""

    family_tags: tuple[str, ...]
    contracts: tuple[CompiledContract, ...]
    complete: bool
    selection_mode: str
    synthetic_literals: tuple[str, ...] = ()

    def render(self) -> str:
        return "\n".join(
            f"[{item.contract_id}] {item.content}" for item in self.contracts
        )

    def validate(
        self, *, requested_family_tags: tuple[str, ...]
    ) -> "CompiledFamilyBundle":
        if self.family_tags != requested_family_tags:
            raise G5AgentLoopError("compiler bundle changed requested family order")
        _unique_text_tuple(self.family_tags, field="CompiledFamilyBundle.family_tags")
        if self.complete is not True:
            raise G5AgentLoopError("compiler bundle must declare complete coverage")
        if self.selection_mode != "full-unranked-compatible":
            raise G5AgentLoopError("compiler bundle must be full and unranked")
        if not isinstance(self.synthetic_literals, tuple):
            raise G5AgentLoopError("compiler synthetic_literals must be a tuple")
        if self.synthetic_literals:
            raise G5AgentLoopError("compiler bundle contains synthetic task literals")
        if not isinstance(self.contracts, tuple) or not self.contracts:
            raise G5AgentLoopError("compiler bundle must contain contracts")
        ids: set[str] = set()
        value_ids: set[str] = set()
        covered: set[str] = set()
        for contract in self.contracts:
            if not isinstance(contract, CompiledContract):
                raise G5AgentLoopError("compiler bundle entries must be contracts")
            contract.validate()
            if contract.family_tag not in requested_family_tags:
                raise G5AgentLoopError("compiler bundle introduced an unrequested family")
            if contract.contract_id in ids or contract.value_id in value_ids:
                raise G5AgentLoopError("compiler bundle identities must be unique")
            ids.add(contract.contract_id)
            value_ids.add(contract.value_id)
            covered.add(contract.family_tag)
        if covered != set(requested_family_tags):
            raise G5AgentLoopError("compiler bundle does not cover every requested family")
        _ascii_text(
            self.render(),
            field="compiler bundle",
            byte_cap=BUNDLE_ASCII_BYTE_CAP,
        )
        return self

    def content_hash(self) -> str:
        return content_hash(
            {
                "family_tags": list(self.family_tags),
                "contracts": [
                    {
                        "contract_id": item.contract_id,
                        "family_tag": item.family_tag,
                        "facet_id": item.facet_id,
                        "value_id": item.value_id,
                        "content_sha256": hashlib.sha256(
                            item.content.encode("ascii")
                        ).hexdigest(),
                    }
                    for item in self.contracts
                ],
                "complete": self.complete,
                "selection_mode": self.selection_mode,
                "synthetic_literals": list(self.synthetic_literals),
            }
        )


class FamilyCompiler(Protocol):
    taxonomy: tuple[FamilyTaxon, ...]
    fallback_family_tags: tuple[str, ...]
    registered_tool_names: tuple[str, ...]

    def compile(self, plan: ParsedPlan) -> CompiledFamilyBundle: ...


@dataclass(frozen=True)
class PromptEnvelope:
    text_tokens: int
    speech_feature_tokens: int
    special_token_reserve: int
    completion_token_ceiling: int

    @property
    def total_tokens(self) -> int:
        return (
            self.text_tokens
            + self.speech_feature_tokens
            + self.special_token_reserve
            + self.completion_token_ceiling
        )

    def validate(self) -> "PromptEnvelope":
        for field in (
            "text_tokens",
            "speech_feature_tokens",
            "special_token_reserve",
            "completion_token_ceiling",
        ):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise G5AgentLoopError(f"prompt envelope {field} must be an integer")
        if self.total_tokens > PER_SLOT_PROMPT_TOKENS:
            raise G5AgentLoopError(
                "prompt envelope exceeds the per-slot limit: "
                f"{self.total_tokens} > {PER_SLOT_PROMPT_TOKENS}"
            )
        return self


class G5AgentLoopAdapter(TaskAdapter):
    """Gold-free adapter that exposes only the closed family taxonomy."""

    def __init__(
        self,
        samples: Sequence[Audio2ToolSample],
        *,
        split_id: str,
        taxonomy: Sequence[FamilyTaxon],
    ) -> None:
        if not isinstance(split_id, str) or not split_id:
            raise G5AgentLoopError("split_id must be nonempty")
        rows = tuple(samples)
        by_id = {sample.sample_id: sample for sample in rows}
        if not rows or len(by_id) != len(rows):
            raise G5AgentLoopError("G5 samples must be nonempty and unique")
        self._samples = tuple(sorted(rows, key=lambda item: item.sample_id))
        self._split_id = split_id
        self._taxonomy = _validated_taxonomy(taxonomy)
        taxonomy_text = "; ".join(
            f"{item.family_tag}=[{','.join(item.operation_tags)}]"
            for item in self._taxonomy
        )
        self._task_contract = _ascii_text(
            "Use original speech as the only task authority. Closed family taxonomy: "
            f"{taxonomy_text}.",
            field="G5 taxonomy task contract",
            byte_cap=PLAN_STATE_ASCII_BYTE_CAP,
        )

    @property
    def taxonomy(self) -> tuple[FamilyTaxon, ...]:
        return self._taxonomy

    def load_split(self, split_id: str) -> tuple[Audio2ToolSample, ...]:
        if split_id != self._split_id:
            raise G5AgentLoopError("G5 adapter received the wrong split")
        return self._samples

    def build_task_contract(self, sample: Audio2ToolSample, obs: object) -> str:
        del obs
        if sample.sample_id not in {item.sample_id for item in self._samples}:
            raise G5AgentLoopError("G5 sample falls outside the adapter surface")
        return self._task_contract

    def assemble_prompt(
        self, sample: Audio2ToolSample, supply: object
    ) -> tuple[Mapping[str, object], ...]:
        if supply is not None:
            raise G5AgentLoopError("G5 adapter rejects an untraced supply channel")
        return (
            {"role": "system", "content": self.build_task_contract(sample, None)},
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "media_relpath": sample.media_relpath}
                ],
            },
        )

    def score(self, sample: Audio2ToolSample, response: str) -> Mapping[str, object]:
        del sample, response
        return {"scoring_deferred": True}

    def extract_consumption(
        self, sample: Audio2ToolSample, supply: object, response: str
    ) -> ConsumptionTrace:
        del sample
        return build_consumption_trace(
            span_id="g5-final", supply=supply, response_text=response
        )


class G5AgentLoopController:
    """Two-contact same-core controller with deterministic middle compilation."""

    def __init__(
        self,
        *,
        compiler: FamilyCompiler,
        snapshot: KnowledgeSnapshot,
        speech_feature_tokens: int,
        token_counter: Callable[[str], int] | None = None,
        special_token_reserve: int = DEFAULT_SPECIAL_TOKEN_RESERVE,
    ) -> None:
        self._compiler = compiler
        self._snapshot = snapshot.validate()
        self._taxonomy = _validated_taxonomy(compiler.taxonomy)
        self._fallback = _validated_fallback(
            compiler.fallback_family_tags,
            {item.family_tag for item in self._taxonomy},
        )
        if not isinstance(compiler.registered_tool_names, tuple) or any(
            not isinstance(item, str) or not item for item in compiler.registered_tool_names
        ):
            raise G5AgentLoopError("compiler registered tool names must be a tuple")
        if (
            isinstance(speech_feature_tokens, bool)
            or not isinstance(speech_feature_tokens, int)
            or speech_feature_tokens < 0
        ):
            raise G5AgentLoopError("speech_feature_tokens must be a nonnegative integer")
        if (
            isinstance(special_token_reserve, bool)
            or not isinstance(special_token_reserve, int)
            or special_token_reserve < 0
        ):
            raise G5AgentLoopError("special_token_reserve must be a nonnegative integer")
        self._speech_feature_tokens = speech_feature_tokens
        self._special_token_reserve = special_token_reserve
        self._token_counter = token_counter or (lambda text: len(text.encode("ascii")))
        self.last_bundle: CompiledFamilyBundle | None = None

    def _envelope(
        self, texts: Sequence[str], completion_tokens: int
    ) -> PromptEnvelope:
        counts = tuple(self._token_counter(text) for text in texts)
        if any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in counts):
            raise G5AgentLoopError("token_counter must return nonnegative integers")
        return PromptEnvelope(
            text_tokens=sum(counts),
            speech_feature_tokens=self._speech_feature_tokens,
            special_token_reserve=self._special_token_reserve,
            completion_token_ceiling=completion_tokens,
        ).validate()

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if (
            context.query_state.loop_step != 0
            or context.contact_index != 0
            or context.agent_states
            or context.query_state.retrieved_value_ids
        ):
            raise G5AgentLoopError("G5 PLAN requires a clean loop-step-zero state")
        self._envelope(
            (context.task_contract, _PLAN_INSTRUCTION), PLAN_COMPLETION_TOKENS
        )
        return AgentContactPlan(
            contact_id=PLAN_CONTACT_ID,
            query_state_sha256=context.query_state.content_hash(),
            purpose="organize-closed-family-plan",
            instruction=_PLAN_INSTRUCTION,
            key_representation_id=f"{CONTROLLER_POLICY_ID}:plan",
            matcher_policy_id=COMPILER_POLICY_ID,
            decoding_params={
                "max_tokens": PLAN_COMPLETION_TOKENS,
                "temperature": 0,
            },
        ).validate()

    def _validated_bundle(self, plan: ParsedPlan) -> CompiledFamilyBundle:
        bundle = self._compiler.compile(plan)
        if not isinstance(bundle, CompiledFamilyBundle):
            raise G5AgentLoopError("family compiler returned an invalid bundle")
        bundle.validate(requested_family_tags=plan.selected_family_tags)
        facet_by_id = {item.facet_id: item for item in self._snapshot.facets}
        value_by_id = {item.value_id: item for item in self._snapshot.values}
        for contract in bundle.contracts:
            facet = facet_by_id.get(contract.facet_id)
            value = value_by_id.get(contract.value_id)
            if facet is None or value is None:
                raise G5AgentLoopError("compiler bundle references outside the snapshot")
            if contract.facet_id not in value.associated_facet_ids:
                raise G5AgentLoopError("compiler contract facet/value binding disagrees")
            if contract.content != value.content:
                raise G5AgentLoopError("compiler contract content disagrees with snapshot")
        return bundle

    def _compile_advance(
        self, context: AgentRuntimeContext, response_text: str
    ) -> AgentLoopAdvance:
        parsed = parse_plan_response(
            response_text,
            taxonomy=self._taxonomy,
            fallback_family_tags=self._fallback,
            forbidden_terms=self._compiler.registered_tool_names,
        )
        bundle = self._validated_bundle(parsed)
        self.last_bundle = bundle
        facet_by_id = {item.facet_id: item for item in self._snapshot.facets}
        selected_facet_texts = tuple(
            facet_by_id[facet_id].representation
            for facet_id in dict.fromkeys(
                item.facet_id for item in bundle.contracts
            )
        )
        self._envelope(
            (
                context.task_contract,
                _EXECUTE_INSTRUCTION,
                parsed.canonical_json,
                bundle.render(),
                *selected_facet_texts,
            ),
            EXECUTE_COMPLETION_TOKENS,
        )

        response_sha256 = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
        state_id = f"state:g5-plan:{response_sha256[:24]}"
        state = AgentStateArtifact(
            state_id=state_id,
            state_kind=PLAN_STATE_KIND,
            content=parsed.canonical_json,
            source_query_state_sha256=context.query_state.content_hash(),
            source_response_sha256=response_sha256,
            producer_policy_id=CONTROLLER_POLICY_ID,
            cited_value_ids=(),
        ).validate()
        value_ids = tuple(item.value_id for item in bundle.contracts)
        facet_ids = tuple(dict.fromkeys(item.facet_id for item in bundle.contracts))
        next_state = QueryState(
            query_id=context.query_state.query_id,
            query_sample_id=context.query_state.query_sample_id,
            speech_packet_id=context.query_state.speech_packet_id,
            speech_packet_sha256=context.query_state.speech_packet_sha256,
            use_split_identity_hash=context.query_state.use_split_identity_hash,
            loop_step=1,
            visible_facet_ids=facet_ids,
            agent_state_ids=(state_id,),
            retrieved_value_ids=value_ids,
        ).validate()
        rank_result = RankResult(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            query_state_sha256=context.query_state.content_hash(),
            ranking_policy_id=f"{COMPILER_POLICY_ID}:equal-admission",
            candidates=tuple(
                RankedFacet(facet_id, 0.0)
                for facet_id in sorted(facet_ids)
            ),
        ).validate()
        fusion = FusionDecision(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            query_state_sha256=context.query_state.content_hash(),
            rank_result_sha256=rank_result.content_hash(),
            fusion_policy_id=f"{COMPILER_POLICY_ID}:complete-union",
            supporting_facet_ids=tuple(item.facet_id for item in rank_result.candidates),
            selected_value_ids=value_ids,
        ).validate()
        transition = AgentStepTransition(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            prior_query_state_sha256=context.query_state.content_hash(),
            next_query_state_sha256=next_state.content_hash(),
            action_kind="acquire",
            action_target_refs=(
                f"agent-state:{state_id}",
                f"compiled-bundle:{bundle.content_hash()}",
                f"rank-result:{rank_result.content_hash()}",
                f"fusion-decision:{fusion.content_hash()}",
            ),
            new_value_ids=value_ids,
            used_value_ids=(),
            dropped_value_ids=(),
            new_agent_state_ids=(state_id,),
            dropped_agent_state_ids=(),
            new_facet_ids=facet_ids,
        ).validate()
        execute_contact = AgentContactPlan(
            contact_id=EXECUTE_CONTACT_ID,
            query_state_sha256=next_state.content_hash(),
            purpose="execute-complete-family-contract-bundle",
            instruction=_EXECUTE_INSTRUCTION,
            key_representation_id=f"{CONTROLLER_POLICY_ID}:execute",
            matcher_policy_id=COMPILER_POLICY_ID,
            decoding_params={
                "max_tokens": EXECUTE_COMPLETION_TOKENS,
                "temperature": 0,
            },
        ).validate()
        return AgentLoopAdvance(
            transition=transition,
            next_query_state=next_state,
            new_agent_states=(state,),
            next_contact=execute_contact,
            rank_result=rank_result,
            fusion_decision=fusion,
        )

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContact,
        response_text: AgentResponse,
    ) -> AgentLoopAdvance:
        if not isinstance(contact, AgentContactPlan) or not isinstance(
            response_text, str
        ):
            raise G5AgentLoopError("G5 requires one ordered string response per contact")
        if context.query_state.loop_step == 0:
            if contact.contact_id != PLAN_CONTACT_ID or context.contact_index != 0:
                raise G5AgentLoopError("G5 loop step zero received a non-PLAN contact")
            return self._compile_advance(context, response_text)
        if (
            context.query_state.loop_step != 1
            or context.contact_index != 1
            or contact.contact_id != EXECUTE_CONTACT_ID
        ):
            raise G5AgentLoopError("G5 received a contact outside PLAN then EXECUTE")
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
            final_response_contact_id=EXECUTE_CONTACT_ID,
        )


def run_g5_agentloop(
    *,
    data_root: Path,
    plan: object,
    adapter: G5AgentLoopAdapter,
    core_client: object,
    knowledge_snapshot: KnowledgeSnapshot,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    speech_feature_tokens_by_sample: Mapping[str, int],
    compiler: FamilyCompiler,
    trace_sink: object,
    agent_runner: Callable[..., object] = run_speech_native_agent_loop,
) -> object:
    """Run exactly two sequential contacts per sample on OpenJiuwen slot2/q4."""

    samples = adapter.load_split(adapter._split_id)
    sample_ids = {item.sample_id for item in samples}
    if set(speech_packet_bindings) != sample_ids:
        raise G5AgentLoopError("G5 speech-packet identity surface disagrees")
    if set(speech_feature_tokens_by_sample) != sample_ids:
        raise G5AgentLoopError("G5 speech-token identity surface disagrees")
    if adapter.taxonomy != tuple(compiler.taxonomy):
        raise G5AgentLoopError("adapter and compiler taxonomies disagree")
    controllers = Registry("A2T G5 PLAN-COMPILE-EXECUTE controller")
    controllers.register(
        CONTROLLER_POLICY_ID,
        lambda sample_id: G5AgentLoopController(
            compiler=compiler,
            snapshot=knowledge_snapshot,
            speech_feature_tokens=speech_feature_tokens_by_sample[sample_id],
        ),
    )
    summary = agent_runner(
        data_root=data_root,
        plan=plan,
        adapter=adapter,
        core_client=core_client,
        split_id=adapter._split_id,
        knowledge_snapshot=knowledge_snapshot,
        speech_packet_bindings=speech_packet_bindings,
        controller_policy_id=CONTROLLER_POLICY_ID,
        bootstrap_facet_ids=(),
        bootstrap_value_ids=(),
        max_contacts=2,
        slot_count=G5_SLOT_COUNT,
        queue_depth=G5_QUEUE_DEPTH,
        trace_sink=trace_sink,
        agent_executor_id=AGENT_EXECUTOR_ID,
        decoding_params={},
        controller_registry=controllers,
    )
    if getattr(summary, "agent_executor_id", None) != AGENT_EXECUTOR_ID:
        raise G5AgentLoopError("G5 is not bound to the OpenJiuwen runner")
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or len(results) != len(samples):
        raise G5AgentLoopError("G5 result identity surface is incomplete")
    result_ids: list[str] = []
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        contacts = getattr(result, "contacts", None)
        if not isinstance(sample_id, str) or not isinstance(contacts, tuple):
            raise G5AgentLoopError("G5 result identity surface is malformed")
        if len(contacts) != 2:
            raise G5AgentLoopError("G5 result must contain exactly two contacts")
        result_ids.append(sample_id)
    if len(set(result_ids)) != len(result_ids) or set(result_ids) != sample_ids:
        raise G5AgentLoopError("G5 result identity surface disagrees")
    return summary


__all__ = [
    "BUNDLE_ASCII_BYTE_CAP",
    "CONTROLLER_POLICY_ID",
    "CompiledContract",
    "CompiledFamilyBundle",
    "EXECUTE_COMPLETION_TOKENS",
    "EXECUTE_CONTACT_ID",
    "FALLBACK_STATUS",
    "FamilyCompiler",
    "FamilyTaxon",
    "G5AgentLoopAdapter",
    "G5AgentLoopController",
    "G5AgentLoopError",
    "G5_QUEUE_DEPTH",
    "G5_SLOT_COUNT",
    "G5_TRACE_PHASES",
    "PER_SLOT_PROMPT_TOKENS",
    "PLAN_COMPLETION_TOKENS",
    "PLAN_CONTACT_ID",
    "PLAN_STATE_ASCII_BYTE_CAP",
    "ParsedPlan",
    "PlanOperation",
    "PlanValueSpan",
    "PromptEnvelope",
    "parse_plan_response",
    "run_g5_agentloop",
]
