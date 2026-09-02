"""Pure core for the G6 exhaustive family-local AgentLoop.

G6 schedules twenty-eight causally independent SCAN contacts and one dependent
RESOLVE contact.  This module performs no model, audio, network, launcher, or
scoring work.  It instead freezes the contact contexts, validates bounded model
outputs, derives the exact resolver supply, and exposes exact-request accounting
and OBS/ORG/SUPPLY/USE trace seams for a later runtime integration.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TypeAlias

FAMILY_COUNT = 28
SCAN_RESPONSE_ASCII_BYTE_CAP = 4_096
SCAN_REPORT_ASCII_BYTE_CAP = 2_048
ALL_REPORTS_ASCII_BYTE_CAP = 32_768
FAMILY_BUNDLE_ASCII_BYTE_CAP = 12_288
RESOLVE_CONTRACTS_ASCII_BYTE_CAP = 18_432
FINAL_RESPONSE_ASCII_BYTE_CAP = 8_192
MAX_CANDIDATES_PER_FAMILY = 8
MAX_SPEECH_SPANS_PER_CANDIDATE = 16
MAX_ARGUMENT_BINDINGS_PER_CANDIDATE = 24
MAX_CONTEXT_EVIDENCE_ITEMS = 16
PER_SLOT_CONTEXT_TOKENS = 32_768
OPERATIONAL_HEADROOM_TOKENS = 8_192
SCAN_COMPLETION_TOKENS = 512
RESOLVE_COMPLETION_TOKENS = 1_024
SPECIAL_TOKEN_RESERVE = 512

SCAN_STATUS_VALID = "VALID"
SCAN_STATUS_INVALID_EMPTY = "INVALID_EMPTY"
CONTROLLER_POLICY_ID = "saea-a2t-g6-exhaustive-family-sweep-v1"
SCAN_CONTACT_PREFIX = "g6-scan-"
RESOLVE_CONTACT_ID = "g6-resolve"
TRACE_PHASES = ("OBS", "ORG", "SUPPLY", "USE")

JsonScalar: TypeAlias = str | int | float | bool
Canonicalizer: TypeAlias = Callable[[JsonScalar], JsonScalar]

_SCAN_KEYS = frozenset(
    {
        "applicable",
        "candidates",
        "correction_evidence",
        "turn_evidence",
        "role_evidence",
        "ordering_evidence",
    }
)
_CANDIDATE_KEYS = frozenset(
    {
        "tool_name",
        "speech_spans",
        "argument_bindings",
        "unresolved_required_arguments",
    }
)
_BINDING_KEYS = frozenset({"key", "value", "speech_span"})
_FINAL_CALL_KEYS = frozenset({"name", "arguments"})
_FORBIDDEN_RUNTIME_KEY = re.compile(
    r"(?i)(?:gold|expected|reference_transcript|annotation|reward|score|tier|sample_id)"
)

_SCAN_INSTRUCTION = (
    "SCAN this one supplied family as reference-only evidence against the original "
    "speech. The family inventory is not an action list. Return exactly one compact "
    "ASCII JSON object with applicable, candidates, correction_evidence, "
    "turn_evidence, role_evidence, and ordering_evidence. Each candidate has exactly "
    "tool_name, ordered speech_spans, argument_bindings, and "
    "unresolved_required_arguments. Each binding has exactly key, value, and "
    "speech_span. Use only registered tools and legal keys from this family; copy task "
    "values only from speech evidence, never contract defaults. Abstain with "
    "applicable=false and empty arrays. Emit no final calls, prose, metadata, repair, "
    "or evaluation fields."
)
_RESOLVE_INSTRUCTION = (
    "RESOLVE the sole final answer from the original speech, all validated bounded "
    "family reports, and only the exact contracts nominated by their own reports. "
    "Return only a nonempty ASCII JSON array of call objects with exactly name and "
    "arguments. Use only nominated registered tools and legal argument keys. Bind "
    "values to nominated speech evidence or an explicitly permitted construction "
    "canonicalizer. Omit unspoken optional/default fields. Do not enumerate the "
    "inventory, duplicate a call, repair, retry, or add prose."
)


class G6FamilySweepError(RuntimeError):
    """A frozen G6 setup, context, identity, or size invariant failed."""


def _ascii(value: object, *, field: str, byte_cap: int | None = None) -> str:
    if not isinstance(value, str) or not value or not value.isascii():
        raise G6FamilySweepError(f"{field} must be nonempty ASCII English")
    if byte_cap is not None and len(value.encode("ascii")) > byte_cap:
        raise G6FamilySweepError(f"{field} byte cap exceeded")
    return value


def _ascii_tuple(
    value: object,
    *,
    field: str,
    allow_empty: bool = False,
    max_items: int | None = None,
) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)) or (not value and not allow_empty):
        qualifier = "an ordered sequence" if allow_empty else "a nonempty sequence"
        raise G6FamilySweepError(f"{field} must be {qualifier}")
    rows = tuple(value)
    if max_items is not None and len(rows) > max_items:
        raise G6FamilySweepError(f"{field} count exceeds {max_items}")
    if any(
        not isinstance(item, str) or not item or not item.isascii() for item in rows
    ):
        raise G6FamilySweepError(f"{field} must contain nonempty ASCII strings")
    if len(set(rows)) != len(rows):
        raise G6FamilySweepError(f"{field} must not contain duplicates")
    return rows


def _is_scalar(value: object) -> bool:
    return isinstance(value, (str, int, float, bool)) and not (
        isinstance(value, float)
        and (value != value or value in (float("inf"), float("-inf")))
    )


def _json_surface(raw: str) -> str:
    return raw.strip()


def _contains_forbidden_key(document: object) -> bool:
    if isinstance(document, dict):
        return any(
            not isinstance(key, str)
            or _FORBIDDEN_RUNTIME_KEY.search(key) is not None
            or _contains_forbidden_key(value)
            for key, value in document.items()
        )
    if isinstance(document, list):
        return any(_contains_forbidden_key(value) for value in document)
    return False


@dataclass(frozen=True)
class ArgumentSpec:
    """One legal argument key and its construction-only canonicalizer permits."""

    key: str
    required: bool
    canonicalizer_ids: tuple[str, ...] = ()

    def validate(self) -> ArgumentSpec:
        _ascii(self.key, field="ArgumentSpec.key")
        if not isinstance(self.required, bool):
            raise G6FamilySweepError("ArgumentSpec.required must be boolean")
        _ascii_tuple(
            self.canonicalizer_ids,
            field="ArgumentSpec.canonicalizer_ids",
            allow_empty=True,
        )
        return self


@dataclass(frozen=True)
class ToolContract:
    """One exact frozen registered-tool contract."""

    contract_id: str
    family_tag: str
    tool_name: str
    arguments: tuple[ArgumentSpec, ...]
    content: str
    legal_key_skeletons: tuple[tuple[str, ...], ...]

    def validate(self) -> ToolContract:
        _ascii(self.contract_id, field="ToolContract.contract_id")
        _ascii(self.family_tag, field="ToolContract.family_tag")
        _ascii(self.tool_name, field="ToolContract.tool_name")
        _ascii(self.content, field="ToolContract.content")
        if not isinstance(self.arguments, tuple):
            raise G6FamilySweepError("ToolContract.arguments must be a tuple")
        keys = tuple(item.validate().key for item in self.arguments)
        if len(set(keys)) != len(keys):
            raise G6FamilySweepError("ToolContract argument keys must be unique")
        if (
            not isinstance(self.legal_key_skeletons, tuple)
            or not self.legal_key_skeletons
            or any(not isinstance(skeleton, tuple) for skeleton in self.legal_key_skeletons)
        ):
            raise G6FamilySweepError(
                "ToolContract legal key skeletons must be a nonempty tuple of tuples"
            )
        legal_skeletons: list[tuple[str, ...]] = []
        for skeleton in self.legal_key_skeletons:
            legal_skeletons.append(
                _ascii_tuple(
                    skeleton,
                    field="ToolContract legal key skeleton",
                    allow_empty=True,
                    max_items=len(keys),
                )
            )
        if len(set(legal_skeletons)) != len(legal_skeletons) or any(
            not set(skeleton).issubset(keys) for skeleton in legal_skeletons
        ):
            raise G6FamilySweepError(
                "ToolContract legal key skeletons must be unique and use declared argument keys"
            )
        required_by_skeleton = set(legal_skeletons[0]).intersection(
            *map(set, legal_skeletons[1:])
        )
        declared_required = {item.key for item in self.arguments if item.required}
        if declared_required != required_by_skeleton:
            raise G6FamilySweepError(
                "ToolContract required arguments must equal the legal skeleton intersection"
            )
        return self

    @property
    def argument_by_key(self) -> dict[str, ArgumentSpec]:
        return {item.key: item for item in self.arguments}

    def render(self) -> str:
        return f"[{self.contract_id}] {self.content}"


@dataclass(frozen=True)
class FamilyBundle:
    """One complete family-local bundle supplied to exactly one SCAN."""

    family_tag: str
    contracts: tuple[ToolContract, ...]

    def validate(self) -> FamilyBundle:
        _ascii(self.family_tag, field="FamilyBundle.family_tag")
        if not isinstance(self.contracts, tuple) or not self.contracts:
            raise G6FamilySweepError("FamilyBundle.contracts must be a nonempty tuple")
        ids: list[str] = []
        names: list[str] = []
        for contract in self.contracts:
            if not isinstance(contract, ToolContract):
                raise G6FamilySweepError(
                    "FamilyBundle entries must be ToolContract values"
                )
            contract.validate()
            if contract.family_tag != self.family_tag:
                raise G6FamilySweepError("contract must belong to its supplied family")
            ids.append(contract.contract_id)
            names.append(contract.tool_name)
        if len(set(ids)) != len(ids) or len(set(names)) != len(names):
            raise G6FamilySweepError("family contract identities must be unique")
        _ascii(
            self.render(),
            field="family bundle",
            byte_cap=FAMILY_BUNDLE_ASCII_BYTE_CAP,
        )
        return self

    def render(self) -> str:
        return "\n".join(contract.render() for contract in self.contracts)


@dataclass(frozen=True)
class ArgumentBinding:
    key: str
    value: JsonScalar
    speech_span: str


@dataclass(frozen=True)
class ScanCandidate:
    tool_name: str
    speech_spans: tuple[str, ...]
    argument_bindings: tuple[ArgumentBinding, ...]
    unresolved_required_arguments: tuple[str, ...]


@dataclass(frozen=True)
class FamilyScanReport:
    """Canonical bounded SCAN report; invalid bytes are replaced, not retained."""

    family_tag: str
    valid: bool
    status: str
    applicable: bool
    candidates: tuple[ScanCandidate, ...]
    correction_evidence: tuple[str, ...]
    turn_evidence: tuple[str, ...]
    role_evidence: tuple[str, ...]
    ordering_evidence: tuple[str, ...]
    canonical_json: str


@dataclass(frozen=True)
class ContactContext:
    """Pure visible-context declaration for one later exact model request."""

    contact_id: str
    stage: str
    speech_packet_id: str
    speech_packet_sha256: str
    task_contract: str
    instruction: str
    family_tag: str | None
    contracts: tuple[ToolContract, ...]
    report_jsons: tuple[str, ...]
    causal_dependency_contact_ids: tuple[str, ...]
    completion_token_ceiling: int
    attempt_limit: int = 1

    def render_control_text(self) -> str:
        sections = [self.task_contract, self.instruction]
        if self.report_jsons:
            sections.append(
                "VALIDATED FAMILY REPORTS:\n" + "\n".join(self.report_jsons)
            )
        if self.contracts:
            sections.append(
                "EXACT VISIBLE CONTRACTS:\n"
                + "\n".join(contract.render() for contract in self.contracts)
            )
        return "\n\n".join(sections)

    def measure_exact_request(
        self,
        rendered_request: str,
        *,
        token_counter: Callable[[str], int],
        speech_feature_tokens: int,
        special_token_reserve: int = SPECIAL_TOKEN_RESERVE,
    ) -> PromptEnvelope:
        """Measure what integration actually rendered, not a prompt-size proxy."""

        return measure_prompt_envelope(
            contact_id=self.contact_id,
            rendered_request=rendered_request,
            token_counter=token_counter,
            speech_feature_tokens=speech_feature_tokens,
            special_token_reserve=special_token_reserve,
            completion_token_ceiling=self.completion_token_ceiling,
        )


@dataclass(frozen=True)
class FinalCall:
    name: str
    arguments: dict[str, JsonScalar]


@dataclass(frozen=True)
class ParsedResolution:
    valid: bool
    calls: tuple[FinalCall, ...]
    canonical_json: str


@dataclass(frozen=True)
class PromptEnvelope:
    """Measurement of the exact fully rendered request passed by integration."""

    contact_id: str
    rendered_request_sha256: str
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

    @property
    def remaining_tokens(self) -> int:
        return PER_SLOT_CONTEXT_TOKENS - self.total_tokens


def measure_prompt_envelope(
    *,
    contact_id: str,
    rendered_request: str,
    token_counter: Callable[[str], int],
    speech_feature_tokens: int,
    special_token_reserve: int,
    completion_token_ceiling: int,
) -> PromptEnvelope:
    """Measure one exact rendered request and refuse before model contact."""

    _ascii(contact_id, field="contact_id")
    if not isinstance(rendered_request, str) or not rendered_request:
        raise G6FamilySweepError("rendered_request must be nonempty text")
    if not callable(token_counter):
        raise G6FamilySweepError("token_counter must be callable")
    text_tokens = token_counter(rendered_request)
    numbers = {
        "text_tokens": text_tokens,
        "speech_feature_tokens": speech_feature_tokens,
        "special_token_reserve": special_token_reserve,
        "completion_token_ceiling": completion_token_ceiling,
    }
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in numbers.values()
    ):
        raise G6FamilySweepError(
            "prompt envelope token counts must be nonnegative integers"
        )
    envelope = PromptEnvelope(
        contact_id=contact_id,
        rendered_request_sha256=hashlib.sha256(
            rendered_request.encode("utf-8")
        ).hexdigest(),
        text_tokens=text_tokens,
        speech_feature_tokens=speech_feature_tokens,
        special_token_reserve=special_token_reserve,
        completion_token_ceiling=completion_token_ceiling,
    )
    if envelope.remaining_tokens < OPERATIONAL_HEADROOM_TOKENS:
        raise G6FamilySweepError(
            "prompt envelope leaves less than 8192 tokens of operational headroom"
        )
    return envelope


def _empty_report(family_tag: str) -> FamilyScanReport:
    document = {
        "family_tag": family_tag,
        "valid": False,
        "status": SCAN_STATUS_INVALID_EMPTY,
        "applicable": False,
        "candidates": [],
        "correction_evidence": [],
        "turn_evidence": [],
        "role_evidence": [],
        "ordering_evidence": [],
    }
    return FamilyScanReport(
        family_tag=family_tag,
        valid=False,
        status=SCAN_STATUS_INVALID_EMPTY,
        applicable=False,
        candidates=(),
        correction_evidence=(),
        turn_evidence=(),
        role_evidence=(),
        ordering_evidence=(),
        canonical_json=json.dumps(document, separators=(",", ":")),
    )


class G6FamilySweep:
    """Frozen, model-free protocol authority for SCAN then RESOLVE."""

    def __init__(
        self,
        *,
        family_bundles: Sequence[FamilyBundle],
        max_final_calls: int,
        canonicalizers: Mapping[str, Canonicalizer] | None = None,
    ) -> None:
        if (
            not isinstance(family_bundles, (tuple, list))
            or len(family_bundles) != FAMILY_COUNT
        ):
            raise G6FamilySweepError("G6 requires exactly 28 family bundles")
        self.family_bundles = tuple(bundle.validate() for bundle in family_bundles)
        tags = tuple(bundle.family_tag for bundle in self.family_bundles)
        if len(set(tags)) != FAMILY_COUNT:
            raise G6FamilySweepError("G6 family tags must be unique")
        if (
            isinstance(max_final_calls, bool)
            or not isinstance(max_final_calls, int)
            or max_final_calls < 1
        ):
            raise G6FamilySweepError("max_final_calls must be a positive integer")
        self.max_final_calls = max_final_calls
        self._bundle_by_family = {
            bundle.family_tag: bundle for bundle in self.family_bundles
        }
        contracts = tuple(
            contract for bundle in self.family_bundles for contract in bundle.contracts
        )
        ids = tuple(contract.contract_id for contract in contracts)
        names = tuple(contract.tool_name for contract in contracts)
        if len(set(ids)) != len(ids):
            raise G6FamilySweepError("contract ids must be globally unique")
        if len(set(names)) != len(names):
            raise G6FamilySweepError("registered tool names must be globally unique")
        self._contract_by_tool = {
            contract.tool_name: contract for contract in contracts
        }
        if canonicalizers is None:
            canonicalizers = {}
        if not isinstance(canonicalizers, Mapping) or any(
            not isinstance(key, str)
            or not key
            or not key.isascii()
            or not callable(value)
            for key, value in canonicalizers.items()
        ):
            raise G6FamilySweepError("canonicalizers must map ASCII ids to callables")
        self._canonicalizers = dict(canonicalizers)
        permits = {
            canonicalizer_id
            for contract in contracts
            for argument in contract.arguments
            for canonicalizer_id in argument.canonicalizer_ids
        }
        if not permits.issubset(self._canonicalizers):
            raise G6FamilySweepError("every permitted canonicalizer must be registered")

    @property
    def family_tags(self) -> tuple[str, ...]:
        return tuple(bundle.family_tag for bundle in self.family_bundles)

    def build_scan_contexts(
        self,
        *,
        speech_packet_id: str,
        speech_packet_sha256: str,
        task_contract: str,
    ) -> tuple[ContactContext, ...]:
        """Prospectively declare all independent SCAN contact contexts."""

        self._validate_context_identity(
            speech_packet_id, speech_packet_sha256, task_contract
        )
        return tuple(
            ContactContext(
                contact_id=f"{SCAN_CONTACT_PREFIX}{bundle.family_tag}",
                stage="SCAN",
                speech_packet_id=speech_packet_id,
                speech_packet_sha256=speech_packet_sha256,
                task_contract=task_contract,
                instruction=_SCAN_INSTRUCTION,
                family_tag=bundle.family_tag,
                contracts=bundle.contracts,
                report_jsons=(),
                causal_dependency_contact_ids=(),
                completion_token_ceiling=SCAN_COMPLETION_TOKENS,
            )
            for bundle in self.family_bundles
        )

    @staticmethod
    def _validate_context_identity(
        speech_packet_id: str, speech_packet_sha256: str, task_contract: str
    ) -> None:
        _ascii(speech_packet_id, field="speech_packet_id")
        if (
            not isinstance(speech_packet_sha256, str)
            or re.fullmatch(r"[0-9a-f]{64}", speech_packet_sha256) is None
        ):
            raise G6FamilySweepError("speech_packet_sha256 must be lowercase SHA-256")
        _ascii(task_contract, field="task_contract")

    def parse_scan_response(
        self, family_tag: str, response_text: object
    ) -> FamilyScanReport:
        """Strictly parse one SCAN; any invalidity empties this family only."""

        bundle = self._bundle_by_family.get(family_tag)
        if bundle is None:
            raise G6FamilySweepError(
                "SCAN family is outside the frozen 28-family surface"
            )
        invalid = _empty_report(family_tag)
        if (
            not isinstance(response_text, str)
            or not response_text.isascii()
            or len(response_text.encode("ascii")) > SCAN_RESPONSE_ASCII_BYTE_CAP
        ):
            return invalid
        try:
            document = json.loads(_json_surface(response_text))
            if (
                not isinstance(document, dict)
                or set(document) != _SCAN_KEYS
                or _contains_forbidden_key(document)
            ):
                return invalid
            applicable = document["applicable"]
            candidate_rows = document["candidates"]
            if not isinstance(applicable, bool) or not isinstance(candidate_rows, list):
                return invalid
            if len(candidate_rows) > MAX_CANDIDATES_PER_FAMILY:
                return invalid
            if applicable != bool(candidate_rows):
                return invalid
            contracts = {contract.tool_name: contract for contract in bundle.contracts}
            candidates: list[ScanCandidate] = []
            canonical_candidates: list[dict[str, object]] = []
            seen_tools: set[str] = set()
            for row in candidate_rows:
                parsed = self._parse_candidate(row, contracts, seen_tools)
                if parsed is None:
                    return invalid
                candidate, canonical = parsed
                candidates.append(candidate)
                canonical_candidates.append(canonical)
                seen_tools.add(candidate.tool_name)
            evidence_fields: dict[str, tuple[str, ...]] = {}
            for key in (
                "correction_evidence",
                "turn_evidence",
                "role_evidence",
                "ordering_evidence",
            ):
                try:
                    evidence_fields[key] = _ascii_tuple(
                        document[key],
                        field=key,
                        allow_empty=True,
                        max_items=MAX_CONTEXT_EVIDENCE_ITEMS,
                    )
                except G6FamilySweepError:
                    return invalid
            canonical_document = {
                "family_tag": family_tag,
                "valid": True,
                "status": SCAN_STATUS_VALID,
                "applicable": applicable,
                "candidates": canonical_candidates,
                **{key: list(value) for key, value in evidence_fields.items()},
            }
            canonical_json = json.dumps(canonical_document, separators=(",", ":"))
            if len(canonical_json.encode("ascii")) > SCAN_REPORT_ASCII_BYTE_CAP:
                return invalid
            return FamilyScanReport(
                family_tag=family_tag,
                valid=True,
                status=SCAN_STATUS_VALID,
                applicable=applicable,
                candidates=tuple(candidates),
                correction_evidence=evidence_fields["correction_evidence"],
                turn_evidence=evidence_fields["turn_evidence"],
                role_evidence=evidence_fields["role_evidence"],
                ordering_evidence=evidence_fields["ordering_evidence"],
                canonical_json=canonical_json,
            )
        except (TypeError, ValueError, UnicodeError):
            return invalid

    @staticmethod
    def _parse_candidate(
        row: object,
        contracts: Mapping[str, ToolContract],
        seen_tools: set[str],
    ) -> tuple[ScanCandidate, dict[str, object]] | None:
        if not isinstance(row, dict) or set(row) != _CANDIDATE_KEYS:
            return None
        tool_name = row["tool_name"]
        if not isinstance(tool_name, str) or tool_name in seen_tools:
            return None
        contract = contracts.get(tool_name)
        if contract is None:
            return None
        try:
            speech_spans = _ascii_tuple(
                row["speech_spans"],
                field="candidate speech_spans",
                max_items=MAX_SPEECH_SPANS_PER_CANDIDATE,
            )
        except G6FamilySweepError:
            return None
        binding_rows = row["argument_bindings"]
        if (
            not isinstance(binding_rows, list)
            or len(binding_rows) > MAX_ARGUMENT_BINDINGS_PER_CANDIDATE
        ):
            return None
        bindings: list[ArgumentBinding] = []
        canonical_bindings: list[dict[str, object]] = []
        bound_keys: set[str] = set()
        legal = contract.argument_by_key
        for binding in binding_rows:
            if not isinstance(binding, dict) or set(binding) != _BINDING_KEYS:
                return None
            key = binding["key"]
            value = binding["value"]
            speech_span = binding["speech_span"]
            if (
                not isinstance(key, str)
                or key not in legal
                or key in bound_keys
                or not _is_scalar(value)
                or not isinstance(speech_span, str)
                or not speech_span
                or not speech_span.isascii()
                or speech_span not in speech_spans
                or (isinstance(value, str) and value != speech_span)
            ):
                return None
            bound_keys.add(key)
            bindings.append(ArgumentBinding(key, value, speech_span))
            canonical_bindings.append(
                {"key": key, "value": value, "speech_span": speech_span}
            )
        try:
            unresolved = _ascii_tuple(
                row["unresolved_required_arguments"],
                field="unresolved_required_arguments",
                allow_empty=True,
                max_items=len(contract.arguments),
            )
        except G6FamilySweepError:
            return None
        required = {item.key for item in contract.arguments if item.required}
        if (
            not set(unresolved).issubset(required)
            or set(unresolved) & bound_keys
            or not required.issubset(bound_keys | set(unresolved))
            or not any(
                set(bound_keys).issubset(skeleton)
                and tuple(key for key in skeleton if key in bound_keys)
                == tuple(binding.key for binding in bindings)
                for skeleton in contract.legal_key_skeletons
            )
        ):
            return None
        candidate = ScanCandidate(
            tool_name=tool_name,
            speech_spans=speech_spans,
            argument_bindings=tuple(bindings),
            unresolved_required_arguments=unresolved,
        )
        return candidate, {
            "tool_name": tool_name,
            "speech_spans": list(speech_spans),
            "argument_bindings": canonical_bindings,
            "unresolved_required_arguments": list(unresolved),
        }

    def parse_scan_responses(
        self, responses_by_family: Mapping[str, object]
    ) -> tuple[FamilyScanReport, ...]:
        """Parse the one-attempt result for every prospectively scheduled family."""

        if not isinstance(responses_by_family, Mapping) or set(
            responses_by_family
        ) != set(self.family_tags):
            raise G6FamilySweepError(
                "SCAN responses must cover exactly the 28 families"
            )
        return tuple(
            self.parse_scan_response(tag, responses_by_family[tag])
            for tag in self.family_tags
        )

    def _validated_reports(
        self, reports: Sequence[FamilyScanReport]
    ) -> tuple[FamilyScanReport, ...]:
        if not isinstance(reports, (tuple, list)) or len(reports) != FAMILY_COUNT:
            raise G6FamilySweepError("resolver requires exactly 28 reports")
        rows = tuple(reports)
        if tuple(report.family_tag for report in rows) != self.family_tags:
            raise G6FamilySweepError("resolver reports changed frozen family order")
        for report in rows:
            if not isinstance(report, FamilyScanReport):
                raise G6FamilySweepError(
                    "resolver reports must be validated and bounded"
                )
            if report.valid:
                source_document = {
                    "applicable": report.applicable,
                    "candidates": [
                        {
                            "tool_name": candidate.tool_name,
                            "speech_spans": list(candidate.speech_spans),
                            "argument_bindings": [
                                {
                                    "key": binding.key,
                                    "value": binding.value,
                                    "speech_span": binding.speech_span,
                                }
                                for binding in candidate.argument_bindings
                            ],
                            "unresolved_required_arguments": list(
                                candidate.unresolved_required_arguments
                            ),
                        }
                        for candidate in report.candidates
                    ],
                    "correction_evidence": list(report.correction_evidence),
                    "turn_evidence": list(report.turn_evidence),
                    "role_evidence": list(report.role_evidence),
                    "ordering_evidence": list(report.ordering_evidence),
                }
                try:
                    reparsed = self.parse_scan_response(
                        report.family_tag,
                        json.dumps(source_document, separators=(",", ":")),
                    )
                except (TypeError, ValueError, UnicodeError):
                    raise G6FamilySweepError(
                        "resolver reports must be validated and bounded"
                    ) from None
            else:
                reparsed = _empty_report(report.family_tag)
            if reparsed != report:
                raise G6FamilySweepError(
                    "resolver reports must be validated and bounded"
                )
        total = sum(len(report.canonical_json.encode("ascii")) for report in rows)
        if total > ALL_REPORTS_ASCII_BYTE_CAP:
            raise G6FamilySweepError("resolver report byte cap exceeded")
        return rows

    def _selected_contracts(
        self, reports: tuple[FamilyScanReport, ...]
    ) -> tuple[ToolContract, ...]:
        nominated = {
            candidate.tool_name
            for report in reports
            if report.valid
            for candidate in report.candidates
        }
        selected = tuple(
            contract
            for bundle in self.family_bundles
            for contract in bundle.contracts
            if contract.tool_name in nominated
        )
        rendered = "\n".join(contract.render() for contract in selected)
        if (
            rendered
            and len(rendered.encode("ascii")) > RESOLVE_CONTRACTS_ASCII_BYTE_CAP
        ):
            raise G6FamilySweepError("resolver contract byte cap exceeded")
        return selected

    def build_resolve_context(
        self,
        *,
        speech_packet_id: str,
        speech_packet_sha256: str,
        task_contract: str,
        reports: Sequence[FamilyScanReport],
    ) -> ContactContext:
        """Build the single dependent RESOLVE context without raw scan history."""

        self._validate_context_identity(
            speech_packet_id, speech_packet_sha256, task_contract
        )
        rows = self._validated_reports(reports)
        return ContactContext(
            contact_id=RESOLVE_CONTACT_ID,
            stage="RESOLVE",
            speech_packet_id=speech_packet_id,
            speech_packet_sha256=speech_packet_sha256,
            task_contract=task_contract,
            instruction=_RESOLVE_INSTRUCTION,
            family_tag=None,
            contracts=self._selected_contracts(rows),
            report_jsons=tuple(report.canonical_json for report in rows),
            causal_dependency_contact_ids=tuple(
                f"{SCAN_CONTACT_PREFIX}{tag}" for tag in self.family_tags
            ),
            completion_token_ceiling=RESOLVE_COMPLETION_TOKENS,
        )

    def parse_resolve_response(
        self, response_text: object, *, reports: Sequence[FamilyScanReport]
    ) -> ParsedResolution:
        """Validate the one final attempt; invalid output seals as an empty result."""

        invalid = ParsedResolution(False, (), "[]")
        rows = self._validated_reports(reports)
        if (
            not isinstance(response_text, str)
            or not response_text.isascii()
            or len(response_text.encode("ascii")) > FINAL_RESPONSE_ASCII_BYTE_CAP
        ):
            return invalid
        candidate_by_tool = {
            candidate.tool_name: candidate
            for report in rows
            if report.valid
            for candidate in report.candidates
        }
        try:
            document = json.loads(_json_surface(response_text))
            if (
                not isinstance(document, list)
                or not document
                or len(document) > self.max_final_calls
                or _contains_forbidden_key(document)
            ):
                return invalid
            calls: list[FinalCall] = []
            canonical_rows: list[dict[str, object]] = []
            seen_calls: set[str] = set()
            for row in document:
                if not isinstance(row, dict) or set(row) != _FINAL_CALL_KEYS:
                    return invalid
                name = row["name"]
                arguments = row["arguments"]
                if not isinstance(name, str) or not isinstance(arguments, dict):
                    return invalid
                contract = self._contract_by_tool.get(name)
                candidate = candidate_by_tool.get(name)
                if contract is None or candidate is None:
                    return invalid
                if not self._arguments_are_evidence_bound(
                    contract, candidate, arguments
                ):
                    return invalid
                canonical_row = {"name": name, "arguments": arguments}
                call_key = json.dumps(
                    canonical_row, sort_keys=True, separators=(",", ":")
                )
                if call_key in seen_calls:
                    return invalid
                seen_calls.add(call_key)
                calls.append(FinalCall(name=name, arguments=dict(arguments)))
                canonical_rows.append(canonical_row)
            canonical_json = json.dumps(canonical_rows, separators=(",", ":"))
            return ParsedResolution(True, tuple(calls), canonical_json)
        except (TypeError, ValueError, UnicodeError, OverflowError):
            return invalid

    def _arguments_are_evidence_bound(
        self,
        contract: ToolContract,
        candidate: ScanCandidate,
        arguments: Mapping[object, object],
    ) -> bool:
        legal = contract.argument_by_key
        if any(not isinstance(key, str) or key not in legal for key in arguments):
            return False
        if tuple(arguments) not in contract.legal_key_skeletons:
            return False
        required = {item.key for item in contract.arguments if item.required}
        if not required.issubset(arguments):
            return False
        bindings = {
            binding.key: binding.value for binding in candidate.argument_bindings
        }
        for key, value in arguments.items():
            if not _is_scalar(value) or key not in bindings:
                return False
            source = bindings[key]
            if value == source:
                continue
            matched = False
            for canonicalizer_id in legal[key].canonicalizer_ids:
                try:
                    if self._canonicalizers[canonicalizer_id](source) == value:
                        matched = True
                        break
                except (TypeError, ValueError, OverflowError):
                    continue
            if not matched:
                return False
        return True


def build_trace_documents(
    *,
    scan_contact_ids: Sequence[str],
    resolve_context: ContactContext,
    reports: Sequence[FamilyScanReport],
    resolution: ParsedResolution,
    final_response_text: str,
) -> dict[str, dict[str, object]]:
    """Build phase-separated, hashable trace payloads for later append-only emission."""

    ids = _ascii_tuple(scan_contact_ids, field="scan_contact_ids")
    if len(ids) != FAMILY_COUNT:
        raise G6FamilySweepError("trace requires exactly 28 SCAN contact ids")
    if (
        resolve_context.stage != "RESOLVE"
        or resolve_context.contact_id != RESOLVE_CONTACT_ID
    ):
        raise G6FamilySweepError("trace requires the sole G6 RESOLVE context")
    rows = tuple(reports)
    if (
        len(rows) != FAMILY_COUNT
        or tuple(report.canonical_json for report in rows)
        != resolve_context.report_jsons
    ):
        raise G6FamilySweepError("trace reports disagree with RESOLVE context")
    if not isinstance(resolution, ParsedResolution):
        raise G6FamilySweepError("trace resolution must be parsed")
    if not isinstance(final_response_text, str):
        raise G6FamilySweepError("final_response_text must be text")
    return {
        "OBS": {
            "speech_packet_id": resolve_context.speech_packet_id,
            "speech_packet_sha256": resolve_context.speech_packet_sha256,
        },
        "ORG": {
            "controller_policy_id": CONTROLLER_POLICY_ID,
            "scan_contact_ids": list(ids),
            "scan_reports": [
                {
                    "family_tag": report.family_tag,
                    "valid": report.valid,
                    "status": report.status,
                    "report_sha256": hashlib.sha256(
                        report.canonical_json.encode("ascii")
                    ).hexdigest(),
                }
                for report in rows
            ],
        },
        "SUPPLY": {
            "selection_mode": "exact-report-nominations-only",
            "selected_contract_ids": [
                contract.contract_id for contract in resolve_context.contracts
            ],
            "selected_contract_sha256s": [
                hashlib.sha256(contract.render().encode("ascii")).hexdigest()
                for contract in resolve_context.contracts
            ],
        },
        "USE": {
            "resolve_contact_id": resolve_context.contact_id,
            "resolution_valid": resolution.valid,
            "final_response_sha256": hashlib.sha256(
                final_response_text.encode("utf-8")
            ).hexdigest(),
            "canonical_resolution_sha256": hashlib.sha256(
                resolution.canonical_json.encode("ascii")
            ).hexdigest(),
        },
    }


__all__ = [
    "ALL_REPORTS_ASCII_BYTE_CAP",
    "ArgumentBinding",
    "ArgumentSpec",
    "CONTROLLER_POLICY_ID",
    "ContactContext",
    "FAMILY_COUNT",
    "FamilyBundle",
    "FamilyScanReport",
    "FinalCall",
    "G6FamilySweep",
    "G6FamilySweepError",
    "OPERATIONAL_HEADROOM_TOKENS",
    "PER_SLOT_CONTEXT_TOKENS",
    "ParsedResolution",
    "PromptEnvelope",
    "RESOLVE_COMPLETION_TOKENS",
    "RESOLVE_CONTACT_ID",
    "SCAN_COMPLETION_TOKENS",
    "SCAN_CONTACT_PREFIX",
    "SCAN_REPORT_ASCII_BYTE_CAP",
    "SCAN_RESPONSE_ASCII_BYTE_CAP",
    "SPECIAL_TOKEN_RESERVE",
    "ScanCandidate",
    "TRACE_PHASES",
    "ToolContract",
    "build_trace_documents",
    "measure_prompt_envelope",
]
