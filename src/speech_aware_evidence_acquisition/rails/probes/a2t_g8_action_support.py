"""Pure branch construction for the G8 action-support reachability screen.

The module performs no I/O.  It derives branch-specific prompt documents from
the frozen G7 observation, normalized-assessment, and execution-sheet
contracts.  Selection and binding parsers are deliberately strict: invalid
model text is refused rather than repaired.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Callable, Mapping, Sequence

from .a2t_g7_example_ground import (
    ASSESSMENT_CONTRADICT,
    ASSESSMENT_SUPPORT,
    ASSESSMENT_UNCERTAIN,
    ExecutionSheet,
    FamilyAssessment,
    G7ExampleGround,
    MAX_PROMPT_PLUS_COMPLETION_TOKENS,
    NormalizedAssessment,
    Observation,
    PromptFit,
    SLOT_TOKENS,
)


_STATUSES = frozenset(
    {ASSESSMENT_SUPPORT, ASSESSMENT_CONTRADICT, ASSESSMENT_UNCERTAIN}
)
MAX_SELECTION_CALLS = 32
MAX_SELECTION_RESPONSE_UTF8_BYTES = 4_096
MAX_BINDING_RESPONSE_UTF8_BYTES = 12_288


class G8ActionSupportError(ValueError):
    """Raised when a derived G8 branch violates its frozen contract."""


@dataclass(frozen=True)
class FamilyOperation:
    """One schema-free operation description exposed during selection."""

    family_tag: str
    family_objective: str
    tool_name: str
    operation: str


@dataclass(frozen=True)
class SelectedToolContract:
    """The legal argument surface for one selected tool occurrence."""

    tool_name: str
    legal_key_skeletons: tuple[tuple[str, ...], ...]
    types: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ToolSelection:
    """A sealed ordered selection; repeated tool calls remain repeated."""

    tool_names: tuple[str, ...]
    canonical_json: str


@dataclass(frozen=True)
class BoundCall:
    """One selected tool occurrence with its unmodified JSON argument object."""

    tool_name: str
    arguments_json: str

    @property
    def arguments(self) -> dict[str, object]:
        """Return a fresh view so callers cannot mutate the sealed value."""
        value = json.loads(self.arguments_json)
        if not isinstance(value, dict):  # pragma: no cover - constructor invariant
            raise AssertionError("sealed arguments must remain an object")
        return value


@dataclass(frozen=True)
class ToolBindings:
    """Sealed ordered argument objects aligned one-to-one with a selection."""

    calls: tuple[BoundCall, ...]
    canonical_json: str


@dataclass(frozen=True)
class SelectionContext:
    """Speech-carrying operation-selection request without argument schemas."""

    contact_id: str
    stage: str
    uses_audio: bool
    observation: str
    family_operations: tuple[FamilyOperation, ...]
    status_surface: tuple[NormalizedAssessment, ...]
    instruction: str

    def render_prompt(self) -> str:
        """Render the exact deterministic control text measured before contact."""
        operation_lines = [
            (
                f"FAMILY {row.family_tag} | objective: {row.family_objective} | "
                f"tool: {row.tool_name} | operation: {row.operation}"
            )
            for row in self.family_operations
        ]
        status_lines = [
            (
                f"STATUS {row.family_tag} | {row.tool_name} | {row.status} | "
                f"evidence: {','.join(row.evidence) or '-'}"
            )
            for row in self.status_surface
        ]
        return "\n".join(
            [
                "G8 DECOMPOSED TOOL SELECTION",
                "Original complete-dialogue speech is attached to this request.",
                f"OBSERVATION: {self.observation}",
                "FAMILY OBJECTIVES AND OPERATIONS:",
                *operation_lines,
                "COMPLETE NORMALIZED STATUS SURFACE:",
                *status_lines,
                "INSTRUCTION:",
                self.instruction,
            ]
        )


@dataclass(frozen=True)
class BindingContext:
    """Speech-carrying binding request exposing only selected contracts."""

    contact_id: str
    stage: str
    uses_audio: bool
    observation: str
    selection: ToolSelection
    selected_contracts: tuple[SelectedToolContract, ...]
    instruction: str

    def render_prompt(self) -> str:
        """Render the selected-only binding request."""
        contract_lines = []
        for index, contract in enumerate(self.selected_contracts):
            skeletons = "/".join(
                "{" + ",".join(keys) + "}" for keys in contract.legal_key_skeletons
            )
            types = ",".join(f"{key}:{kind}" for key, kind in contract.types) or "-"
            contract_lines.append(
                f"CALL {index} | {contract.tool_name} | skeletons:{skeletons} | "
                f"types:{types}"
            )
        if not contract_lines:
            contract_lines.append("EMPTY SEALED SELECTION: no contracts are supplied.")
        return "\n".join(
            [
                "G8 DECOMPOSED ARGUMENT BINDING",
                "Original complete-dialogue speech is attached to this request.",
                f"OBSERVATION: {self.observation}",
                f"SEALED ORDERED SELECTION: {self.selection.canonical_json}",
                "SELECTED LEGAL CONTRACTS:",
                *contract_lines,
                "INSTRUCTION:",
                self.instruction,
            ]
        )


@dataclass(frozen=True)
class FinalResolveContext:
    """Speech-carrying final request built only from sealed selection and bindings."""

    contact_id: str
    stage: str
    uses_audio: bool
    observation: str
    selection: ToolSelection
    calls: tuple[BoundCall, ...]
    bindings_json: str
    instruction: str

    def render_prompt(self) -> str:
        """Render the exact final request without any unselected tool details."""
        return "\n".join(
            [
                "G8 DECOMPOSED FINAL RESOLVE",
                "Original complete-dialogue speech is attached to this request.",
                f"OBSERVATION: {self.observation}",
                f"SEALED ORDERED SELECTION: {self.selection.canonical_json}",
                f"SEALED TYPED BINDINGS: {self.bindings_json}",
                "INSTRUCTION:",
                self.instruction,
            ]
        )


class G8ActionSupportCore:
    """Derive the G8 complete-action branches from frozen G7 contracts."""

    def __init__(self, bundles: Sequence[object]) -> None:
        self._g7 = G7ExampleGround(bundles)
        self.bundles = tuple(bundles)
        self.registry_order = tuple(
            (str(bundle.family_tag), str(tool.tool_name))
            for bundle in self.bundles
            for tool in bundle.tools
        )
        self._contracts: dict[str, SelectedToolContract] = {}
        family_operations: list[FamilyOperation] = []
        for bundle in self.bundles:
            family_objective = str(bundle.family_label)
            for tool in bundle.tools:
                name = str(tool.tool_name)
                self._contracts[name] = SelectedToolContract(
                    tool_name=name,
                    legal_key_skeletons=tuple(
                        tuple(str(key) for key in keys)
                        for keys in tool.legal_key_skeletons
                    ),
                    types=tuple((str(key), str(kind)) for key, kind in tool.types),
                )
                family_operations.append(
                    FamilyOperation(
                        family_tag=str(bundle.family_tag),
                        family_objective=family_objective,
                        tool_name=name,
                        operation=str(tool.operation),
                    )
                )
        self.family_operations = tuple(family_operations)

    def build_normalized_sheet(
        self, assessments: Sequence[FamilyAssessment]
    ) -> ExecutionSheet:
        """Delegate normalization to the frozen G7 family-assessment contract."""
        return self._g7.build_execution_sheet(assessments)

    def _validate_normalized_sheet(self, sheet: ExecutionSheet) -> tuple[str, ...]:
        identities = tuple(
            (row.family_tag, row.tool_name) for row in sheet.assessments
        )
        if identities != self.registry_order:
            raise G8ActionSupportError(
                "normalized sheet must contain every tool in frozen registry order"
            )
        if any(row.status not in _STATUSES for row in sheet.assessments):
            raise G8ActionSupportError("normalized sheet contains an unknown status")
        lines = tuple(sheet.text.splitlines())
        if len(lines) != len(sheet.assessments):
            raise G8ActionSupportError(
                "normalized sheet must contain one sealed line per registry tool"
            )
        return lines

    def build_support_only_sheet(self, sheet: ExecutionSheet) -> ExecutionSheet:
        """Retain exact support rows and lines in frozen registry order."""
        lines = self._validate_normalized_sheet(sheet)
        kept = tuple(
            (row, line)
            for row, line in zip(sheet.assessments, lines, strict=True)
            if row.status == ASSESSMENT_SUPPORT
        )
        return ExecutionSheet(
            assessments=tuple(row for row, _line in kept),
            text="\n".join(line for _row, line in kept),
        )

    def build_selection_context(
        self, observation: Observation, sheet: ExecutionSheet
    ) -> SelectionContext:
        """Expose operations and the full status surface, never argument schemas."""
        self._validate_normalized_sheet(sheet)
        return SelectionContext(
            contact_id="g8-decomposed-select",
            stage="DECOMPOSED_SELECT",
            uses_audio=True,
            observation=observation.text,
            family_operations=self.family_operations,
            status_surface=sheet.assessments,
            instruction=(
                "Select the requested tools and call order from the original speech, OBS, "
                "family objectives, operations, and statuses. Return only one JSON array "
                "of exact registered tool-name strings. Preserve repeated calls and requested "
                f"order, with at most {MAX_SELECTION_CALLS} calls and at most "
                f"{MAX_SELECTION_RESPONSE_UTF8_BYTES} UTF-8 bytes. Return [] for no selected "
                "call. Do not emit arguments, prose, a fence, a final answer, aliases, or "
                "unregistered names."
            ),
        )

    def parse_selection(self, raw: str) -> ToolSelection:
        """Strictly parse one ordered exact registered-name JSON array."""
        _enforce_response_utf8_limit(
            raw,
            limit=MAX_SELECTION_RESPONSE_UTF8_BYTES,
            stage="selection",
        )
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise G8ActionSupportError("selection must be one unfenced JSON array") from exc
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise G8ActionSupportError(
                "selection must contain only exact registered tool-name strings"
            )
        if any(item not in self._contracts for item in value):
            raise G8ActionSupportError("selection contains an unknown registered tool name")
        if len(value) > MAX_SELECTION_CALLS:
            raise G8ActionSupportError(
                f"selection exceeds the {MAX_SELECTION_CALLS}-call limit"
            )
        names = tuple(value)
        return ToolSelection(
            tool_names=names,
            canonical_json=json.dumps(list(names), ensure_ascii=True, separators=(",", ":")),
        )

    def build_binding_context(
        self, observation: Observation, selection: ToolSelection
    ) -> BindingContext:
        """Expose selected legal skeletons and types, including repeated selections."""
        contracts = self._contracts_for_selection(selection)
        empty_rule = (
            "For an empty sealed selection, return [] exactly. "
            if not contracts
            else ""
        )
        return BindingContext(
            contact_id="g8-decomposed-bind",
            stage="DECOMPOSED_BIND",
            uses_audio=True,
            observation=observation.text,
            selection=selection,
            selected_contracts=contracts,
            instruction=(
                empty_rule
                + "Return only one JSON array with exactly one ordered object per selected "
                "call. Each object has exactly keys name and arguments. Copy each sealed name "
                "in the same order and bind one legal argument skeleton using values from the "
                "original speech or OBS with the declared JSON types. Do not add, remove, "
                "rename, reorder, infer a fallback, repair a value, answer the task, emit prose, "
                f"or use a fence. The complete response must not exceed "
                f"{MAX_BINDING_RESPONSE_UTF8_BYTES} UTF-8 bytes."
            ),
        )

    def _contracts_for_selection(
        self, selection: ToolSelection
    ) -> tuple[SelectedToolContract, ...]:
        if selection.canonical_json != json.dumps(
            list(selection.tool_names), ensure_ascii=True, separators=(",", ":")
        ):
            raise G8ActionSupportError("selection seal does not match its ordered names")
        try:
            return tuple(self._contracts[name] for name in selection.tool_names)
        except KeyError as exc:
            raise G8ActionSupportError("selection contains an unknown tool") from exc

    def parse_bindings(
        self, raw: str, selection: ToolSelection
    ) -> ToolBindings:
        """Parse typed arguments one-to-one without altering selection or values."""
        contracts = self._contracts_for_selection(selection)
        _enforce_response_utf8_limit(
            raw,
            limit=MAX_BINDING_RESPONSE_UTF8_BYTES,
            stage="binding",
        )
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise G8ActionSupportError("binding must be one unfenced JSON array") from exc
        if not isinstance(value, list) or len(value) != len(contracts):
            raise G8ActionSupportError(
                "binding requires one argument object for every selected call"
            )
        calls: list[BoundCall] = []
        for item, contract in zip(value, contracts, strict=True):
            if not isinstance(item, dict) or set(item) != {"name", "arguments"}:
                raise G8ActionSupportError(
                    "each binding item must have exact keys name and arguments"
                )
            if item["name"] != contract.tool_name:
                raise G8ActionSupportError(
                    "binding requires one argument object in exact selected order"
                )
            arguments = item["arguments"]
            if not isinstance(arguments, dict):
                raise G8ActionSupportError("binding arguments must be a JSON object")
            self._validate_arguments(arguments, contract)
            arguments_json = json.dumps(
                arguments, ensure_ascii=True, separators=(",", ":")
            )
            calls.append(BoundCall(contract.tool_name, arguments_json))
        canonical = json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        return ToolBindings(tuple(calls), canonical)

    def _validate_arguments(
        self, arguments: Mapping[str, object], contract: SelectedToolContract
    ) -> None:
        keys = frozenset(arguments)
        legal = {frozenset(skeleton) for skeleton in contract.legal_key_skeletons}
        if keys not in legal:
            raise G8ActionSupportError(
                f"binding arguments do not match a legal skeleton for {contract.tool_name}"
            )
        types = dict(contract.types)
        for key, value in arguments.items():
            if key not in types or not _value_matches_type(value, types[key]):
                raise G8ActionSupportError(
                    f"binding value for {contract.tool_name}.{key} has the wrong JSON type"
                )

    def build_resolve_context(
        self,
        observation: Observation,
        selection: ToolSelection,
        bindings: ToolBindings,
    ) -> FinalResolveContext:
        """Build the final-author request from sealed selection and bindings only."""
        self._contracts_for_selection(selection)
        if tuple(call.tool_name for call in bindings.calls) != selection.tool_names:
            raise G8ActionSupportError("sealed bindings do not match the sealed selection")
        expected = json.dumps(
            [
                {"name": call.tool_name, "arguments": call.arguments}
                for call in bindings.calls
            ],
            ensure_ascii=True,
            separators=(",", ":"),
        )
        if bindings.canonical_json != expected:
            raise G8ActionSupportError("binding seal does not match its ordered calls")
        empty_rule = (
            "The sealed selection is empty; keep it empty and return [] without fallback. "
            if not bindings.calls
            else ""
        )
        return FinalResolveContext(
            contact_id="g8-decomposed-resolve",
            stage="DECOMPOSED_RESOLVE",
            uses_audio=True,
            observation=observation.text,
            selection=selection,
            calls=bindings.calls,
            bindings_json=bindings.canonical_json,
            instruction=(
                empty_rule
                + "The frozen core has sole final-answer authority. Author only the unchanged "
                "official tool-call JSON array from the original speech, OBS, sealed selection, "
                "and sealed typed bindings. Preserve exact call count, names, order, argument "
                "keys, and JSON values. Do not add a fallback, repair, prose, fence, metadata, "
                "or extra key."
            ),
        )


def _value_matches_type(value: object, declared: str) -> bool:
    alternatives = tuple(part.strip() for part in declared.split("|") if part.strip())
    if len(alternatives) > 1:
        return any(_value_matches_type(value, part) for part in alternatives)
    kind = alternatives[0] if alternatives else declared
    if kind == "null":
        return value is None
    if kind == "Boolean":
        return isinstance(value, bool)
    if kind == "Int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "Float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if kind == "Map":
        return isinstance(value, dict)
    if kind == "List":
        return isinstance(value, list)
    if kind.startswith("List<") and kind.endswith(">"):
        element_kind = kind[len("List<") : -1]
        return isinstance(value, list) and all(
            _value_matches_type(item, element_kind) for item in value
        )
    return isinstance(value, str)


def measure_rendered_prompt(
    context: SelectionContext | BindingContext | FinalResolveContext,
    *,
    token_counter: Callable[[str], int],
    completion_tokens: int,
    speech_feature_tokens: int = 0,
    special_token_reserve: int = 0,
) -> PromptFit:
    """Render now and measure the complete request against the 24,576 cap."""
    reserves = (completion_tokens, speech_feature_tokens, special_token_reserve)
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in reserves):
        raise G8ActionSupportError("prompt reserves must be non-negative integers")
    rendered = context.render_prompt()
    counted = token_counter(rendered)
    if not isinstance(counted, int) or isinstance(counted, bool) or counted < 0:
        raise G8ActionSupportError("token counter must return a non-negative integer")
    prompt_tokens = counted + speech_feature_tokens + special_token_reserve
    total = prompt_tokens + completion_tokens
    if total > MAX_PROMPT_PLUS_COMPLETION_TOKENS:
        raise G8ActionSupportError(
            "rendered prompt is refused because it exceeds the 24,576-token "
            "prompt-plus-completion cap"
        )
    return PromptFit(
        contact_id=context.contact_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total,
        remaining_tokens=SLOT_TOKENS - total,
    )


def _enforce_response_utf8_limit(raw: str, *, limit: int, stage: str) -> None:
    if not isinstance(raw, str):
        raise G8ActionSupportError(f"{stage} response must be text")
    if len(raw.encode("utf-8")) > limit:
        raise G8ActionSupportError(
            f"{stage} response exceeds the frozen UTF-8 byte limit of {limit}"
        )


def build_g8_trace_documents(
    *,
    sample_id: str,
    observation: Observation,
    normalized_sheet: ExecutionSheet,
    support_only_sheet: ExecutionSheet,
    selection: ToolSelection,
    bindings: ToolBindings,
    final_response_text: str,
) -> dict[str, object]:
    """Render separately hashable OBS, ORG, SUPPLY, and USE documents."""
    statuses = {status: 0 for status in sorted(_STATUSES)}
    for row in normalized_sheet.assessments:
        if row.status not in statuses:
            raise G8ActionSupportError("trace received an unknown normalized status")
        statuses[row.status] += 1
    return {
        "obs_state": {
            "sample_id": sample_id,
            "valid": observation.valid,
            "text": observation.text,
        },
        "org_state": {
            "sample_id": sample_id,
            "normalized_tool_count": len(normalized_sheet.assessments),
            "status_counts": statuses,
            "normalized_execution_sheet": normalized_sheet.text,
        },
        "supply_state": {
            "sample_id": sample_id,
            "support_tool_count": len(support_only_sheet.assessments),
            "support_tool_names": [
                row.tool_name for row in support_only_sheet.assessments
            ],
            "support_execution_sheet": support_only_sheet.text,
        },
        "use_state": {
            "sample_id": sample_id,
            "selected_tool_names": list(selection.tool_names),
            "binding_count": len(bindings.calls),
            "bindings_json": bindings.canonical_json,
            "final_response_text": final_response_text,
        },
    }
