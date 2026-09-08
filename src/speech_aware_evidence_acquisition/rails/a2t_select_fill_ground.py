"""Pure, selection-scoped routing and parameter ground builders.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``build_routing_knowledge_ground`` is catalog id
``saea-tool-a2t-routing-knowledge-ground-v1`` on the ``SUPPLY`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

from .a2t_canonical_family_ground import CanonicalContract
from .a2t_executable_semantic_cards import (
    ExecutableSemanticCardCorpus,
    TaskSemanticCard,
    ToolSemanticCard,
)
from .a2t_response_schema import (
    audio2tool_call_array_response_format,
    audio2tool_locked_call_array_response_format,
    audio2tool_selection_response_format,
)

ROUTING_MAX_CANDIDATES = 32
PARAMETER_MAX_OCCURRENCES = 7
DEFAULT_BYTE_CAP = 32_768
_NO_DECLARATION = frozenset({"", "none", "none declared", "(none)"})


class SelectFillGroundError(ValueError):
    """The selected ground inputs are malformed or exceed their contract."""


@dataclass(frozen=True)
class RoutingKnowledgeGround:
    candidate_tool_names: tuple[str, ...]
    text: str
    text_sha256: str
    response_format: Mapping[str, object]
    response_format_sha256: str
    report: Mapping[str, object]


@dataclass(frozen=True)
class JointKnowledgeGround:
    candidate_tool_names: tuple[str, ...]
    text: str
    text_sha256: str
    response_format: Mapping[str, object]
    response_format_sha256: str
    report: Mapping[str, object]


@dataclass(frozen=True)
class ParameterKnowledgeGround:
    selected_tool_names: tuple[str, ...]
    selected_tool_occurrences: tuple[str, ...]
    text: str
    text_sha256: str
    response_format: Mapping[str, object]
    response_format_sha256: str
    report: Mapping[str, object]


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def _corpus(value: object) -> ExecutableSemanticCardCorpus:
    if not isinstance(value, ExecutableSemanticCardCorpus):
        raise SelectFillGroundError("corpus must be an ExecutableSemanticCardCorpus")
    cards = value.tool_cards
    if not cards or any(not isinstance(card, ToolSemanticCard) for card in cards):
        raise SelectFillGroundError("corpus tool cards are malformed")
    if len({card.tool_name for card in cards}) != len(cards):
        raise SelectFillGroundError("corpus tool cards contain duplicates")
    if any(not isinstance(card.tool_name, str) or not card.tool_name.isascii() or not card.tool_name for card in cards):
        raise SelectFillGroundError("corpus tool names must be ASCII")
    if any(not isinstance(card, TaskSemanticCard) for card in value.task_cards):
        raise SelectFillGroundError("corpus task cards are malformed")
    return value


def _names(selection: Sequence[str], *, minimum: int, maximum: int, label: str, unique: bool) -> tuple[str, ...]:
    if isinstance(selection, (str, bytes)):
        raise SelectFillGroundError(f"{label} must be a sequence")
    try:
        result = tuple(selection)
    except TypeError as error:
        raise SelectFillGroundError(f"{label} must be a sequence") from error
    if not minimum <= len(result) <= maximum:
        if len(result) > maximum:
            raise SelectFillGroundError(f"{label} must contain at most {maximum} items")
        raise SelectFillGroundError(f"{label} must contain between {minimum} and {maximum} items")
    if any(not isinstance(name, str) or not name or not name.isascii() for name in result):
        raise SelectFillGroundError(f"{label} must contain ASCII names")
    if unique and len(result) != len(set(result)):
        raise SelectFillGroundError(f"{label} contains a duplicate")
    return result


def _bind(corpus: ExecutableSemanticCardCorpus, names: Sequence[str]) -> tuple[ToolSemanticCard, ...]:
    by_name = corpus.cards_by_name
    unknown = tuple(name for name in names if name not in by_name)
    if unknown:
        raise SelectFillGroundError(f"unknown tool {unknown[0]!r}")
    return tuple(by_name[name] for name in dict.fromkeys(names))


def _registry(cards: Sequence[ToolSemanticCard]) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "tool_name": card.tool_name,
            "signature": card.signature,
            "argument_constraints": card.constraints,
        }
        for card in cards
    )


def _schema_constraint(value: str) -> str:
    """Remove prose placeholders before the strict constraint parser."""

    normalized = value.strip().casefold()
    if normalized in _NO_DECLARATION or normalized.startswith("no public "):
        return ""
    return value


def _contract_registry(
    contracts: Sequence[CanonicalContract],
) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            "tool_name": contract.tool_name,
            "signature": contract.tool_name
            + "("
            + ", ".join(f"{key}: {kind}" for key, kind in contract.types)
            + ")",
            "argument_constraints": _schema_constraint(contract.constraints),
        }
        for contract in contracts
    )


def _contract_cards(
    contracts: Sequence[CanonicalContract],
    semantic_cards: Mapping[str, ToolSemanticCard],
) -> tuple[ToolSemanticCard, ...]:
    return tuple(
        ToolSemanticCard(
            tool_name=contract.tool_name,
            choose_semantics=contract.operation,
            avoid_semantics="Choose only for its exact operation meaning.",
            signature=contract.tool_name
            + "("
            + ", ".join(f"{key}: {kind}" for key, kind in contract.types)
            + ")",
            constraints=contract.constraints,
            legal_argument_key_sets=contract.legal_key_skeletons,
            compatibility_rules=semantic_cards[contract.tool_name].compatibility_rules,
            role_guidance=semantic_cards[contract.tool_name].role_guidance,
            examples=semantic_cards[contract.tool_name].examples,
            text="Selected public parameter contract.",
        )
        for contract in contracts
    )


def _selected_contracts(
    selected_names: Sequence[str],
    *,
    contracts_by_tool: Mapping[str, CanonicalContract],
) -> tuple[CanonicalContract, ...]:
    if not isinstance(contracts_by_tool, Mapping):
        raise SelectFillGroundError("contract coverage must be a mapping")
    contracts: list[CanonicalContract] = []
    for name in dict.fromkeys(selected_names):
        contract = contracts_by_tool.get(name)
        if not isinstance(contract, CanonicalContract) or contract.tool_name != name:
            raise SelectFillGroundError(
                "contract coverage must include every selected tool"
            )
        contracts.append(contract)
    return tuple(contracts)


def _parameter_contracts(
    selected_names: Sequence[str],
    *,
    contracts_by_tool: Mapping[str, CanonicalContract],
    canonicalizers: Mapping[str, str],
) -> tuple[tuple[CanonicalContract, ...], tuple[tuple[str, str], ...]]:
    contracts = _selected_contracts(
        selected_names,
        contracts_by_tool=contracts_by_tool,
    )
    if not isinstance(canonicalizers, Mapping):
        raise SelectFillGroundError("canonicalizer coverage must be a mapping")
    applicable = tuple(
        sorted(
            {
                rule
                for contract in contracts
                for rule in contract.canonicalization_rules
            }
        )
    )
    descriptions: list[tuple[str, str]] = []
    for name in applicable:
        description = canonicalizers.get(name)
        if (
            not isinstance(description, str)
            or not description
            or not name.isascii()
            or not description.isascii()
        ):
            raise SelectFillGroundError(
                "canonicalizer coverage must include every selected rule"
            )
        descriptions.append((name, description))
    return tuple(contracts), tuple(descriptions)


def _finish(text: str, response_format: Mapping[str, object], report: dict[str, object], byte_cap: int):
    if not text.isascii():
        raise SelectFillGroundError("rendered ground must be ASCII")
    if len(text.encode("ascii")) > byte_cap:
        raise SelectFillGroundError("rendered ground exceeds byte cap")
    response_hash = hashlib.sha256(_json_bytes(response_format)).hexdigest()
    return text, hashlib.sha256(text.encode("ascii")).hexdigest(), response_hash, report


def _parameter_lines(
    contract: CanonicalContract,
    card: ToolSemanticCard,
    *,
    include_default_semantics: bool = True,
    include_examples: bool = True,
    include_role_guidance: bool = True,
) -> tuple[str, ...]:
    lines = [
        "",
        f"Exact tool: {contract.tool_name}",
        f"Operation: {contract.operation}",
        f"Signature: {card.signature}",
        f"Constraints: {contract.constraints or '(none)'}",
        "Required keys: " + (", ".join(contract.required_keys) or "(none)"),
        "Optional keys: " + (", ".join(contract.optional_keys) or "(none)"),
        "Conditional keys: "
        + (", ".join(contract.conditional_keys) or "(none)"),
        "Forbidden keys: " + (", ".join(contract.forbidden_keys) or "(none)"),
        "Canonical key order: "
        + (", ".join(contract.ordered_keys) or "(none)"),
        "Applicable canonicalizers: "
        + (", ".join(contract.canonicalization_rules) or "(none)"),
    ]
    if include_default_semantics:
        lines[10:10] = [
            "Declared defaults for omission semantics: "
            + (contract.defaults or "(none)"),
            "Omission rules: "
            + (" ".join(contract.omission_rules) or "(none)"),
        ]
    lines.extend(
        f"Legal key set: {{{', '.join(keys)}}}"
        for keys in contract.legal_key_skeletons
    )
    lines.extend(
        "Compatibility: "
        f"{rule.legal_argument_key_set} -> {rule.value_forms}"
        for rule in card.compatibility_rules
    )
    if include_role_guidance:
        lines.extend(f"Role guidance: {item}" for item in card.role_guidance)
    if include_examples:
        lines.extend(f"Example: {item}" for item in card.examples)
    return tuple(lines)


def build_routing_knowledge_ground(
    corpus: ExecutableSemanticCardCorpus,
    candidate_tool_names: Sequence[str],
    *,
    byte_cap: int = DEFAULT_BYTE_CAP,
) -> RoutingKnowledgeGround:
    """Build a candidate-only SELECT packet."""
    corpus = _corpus(corpus)
    if isinstance(byte_cap, bool) or not isinstance(byte_cap, int) or byte_cap <= 0:
        raise SelectFillGroundError("byte cap must be a positive integer")
    names = _names(candidate_tool_names, minimum=1, maximum=ROUTING_MAX_CANDIDATES, label="candidate list", unique=True)
    cards = _bind(corpus, names)
    routing_task_ids = {
        "multi-call-ordering",
        "correction-resolution",
        "implicit-end-state-resolution",
        "multiturn-carryover",
    }
    task = tuple(
        card.text for card in corpus.task_cards if card.card_id in routing_task_ids
    )
    lines = [
        "AUDIO2TOOL ROUTING GROUND",
        "Select only from the exact candidate tool names below.",
        "Use choose semantics to identify the requested operation and avoid semantics to reject nearby operations.",
        "Return the requested tool occurrences in spoken order; preserve corrections and distinct intents.",
        "TASK-WIDE GUIDANCE:",
        *task,
        "CANDIDATES:",
    ]
    for card in cards:
        lines.extend((f"Exact tool: {card.tool_name}", f"Choose: {card.choose_semantics}", f"Avoid: {card.avoid_semantics}"))
    text = "\n".join(lines) + "\n"
    response = audio2tool_selection_response_format(
        _registry(cards),
        names,
        schema_name="audio2tool_routing_selection",
        min_calls=1,
        max_calls=PARAMETER_MAX_OCCURRENCES,
    )
    text, text_hash, response_hash, report = _finish(text, response, {
        "candidate_count": len(names), "task_guidance_count": len(task), "selected_tool_contracts_rendered": 0,
        "signature_rendered": 0, "examples_rendered": 0, "rendered_ascii_bytes": len(text.encode("ascii")), "byte_cap": byte_cap,
    }, byte_cap)
    return RoutingKnowledgeGround(names, text, text_hash, response, response_hash, report)


def build_interface_routing_knowledge_ground(
    corpus: ExecutableSemanticCardCorpus,
    candidate_tool_names: Sequence[str],
    *,
    contracts_by_tool: Mapping[str, CanonicalContract],
    byte_cap: int = DEFAULT_BYTE_CAP,
) -> RoutingKnowledgeGround:
    """Build SELECT ground with interface shape but no parameter values."""

    control = build_routing_knowledge_ground(
        corpus,
        candidate_tool_names,
        byte_cap=byte_cap,
    )
    corpus = _corpus(corpus)
    cards = _bind(corpus, control.candidate_tool_names)
    contracts = _selected_contracts(
        tuple(card.tool_name for card in cards),
        contracts_by_tool=contracts_by_tool,
    )
    routing_task_ids = {
        "multi-call-ordering",
        "correction-resolution",
        "implicit-end-state-resolution",
        "multiturn-carryover",
    }
    task = tuple(
        card.text for card in corpus.task_cards if card.card_id in routing_task_ids
    )
    lines = [
        "AUDIO2TOOL INTERFACE-AWARE ROUTING GROUND",
        "Select only from the exact candidate tool names below.",
        "Use operation meaning and argument shape together to reject nearby tools.",
        "Argument keys and types identify interfaces; they do not supply argument values.",
        "Return the requested tool occurrences in spoken order; preserve corrections and distinct intents.",
        "TASK-WIDE GUIDANCE:",
        *task,
        "CANDIDATES:",
    ]
    for card, contract in zip(cards, contracts, strict=True):
        signature = contract.tool_name + "(" + ", ".join(
            f"{key}: {kind}" for key, kind in contract.types
        ) + ")"
        lines.extend(
            (
                f"Exact tool: {card.tool_name}",
                f"Choose: {card.choose_semantics}",
                f"Avoid: {card.avoid_semantics}",
                f"Signature: {signature}",
                "Required keys: "
                + (", ".join(contract.required_keys) or "(none)"),
                "Optional keys: "
                + (", ".join(contract.optional_keys) or "(none)"),
                "Conditional keys: "
                + (", ".join(contract.conditional_keys) or "(none)"),
                "Forbidden keys: "
                + (", ".join(contract.forbidden_keys) or "(none)"),
            )
        )
        lines.extend(
            f"Legal key set: {{{', '.join(keys)}}}"
            for keys in contract.legal_key_skeletons
        )
    text = "\n".join(lines) + "\n"
    text, text_hash, response_hash, report = _finish(
        text,
        control.response_format,
        {
            "candidate_count": len(control.candidate_tool_names),
            "task_guidance_count": len(task),
            "interface_policy": "key-shape-only",
            "selected_tool_contracts_rendered": len(contracts),
            "signature_rendered": len(contracts),
            "parameter_values_rendered": 0,
            "defaults_rendered": 0,
            "examples_rendered": 0,
            "canonicalizers_rendered": 0,
            "rendered_ascii_bytes": len(text.encode("ascii")),
            "byte_cap": byte_cap,
        },
        byte_cap,
    )
    return RoutingKnowledgeGround(
        control.candidate_tool_names,
        text,
        text_hash,
        control.response_format,
        response_hash,
        report,
    )


def build_joint_knowledge_ground(
    corpus: ExecutableSemanticCardCorpus,
    candidate_tool_names: Sequence[str],
    *,
    contracts_by_tool: Mapping[str, CanonicalContract],
    canonicalizers: Mapping[str, str],
    byte_cap: int = 65_536,
) -> JointKnowledgeGround:
    """Build a K-bounded joint SELECT-and-FILL packet with 1--7 calls."""

    corpus = _corpus(corpus)
    if isinstance(byte_cap, bool) or not isinstance(byte_cap, int) or byte_cap <= 0:
        raise SelectFillGroundError("byte cap must be a positive integer")
    names = _names(
        candidate_tool_names,
        minimum=1,
        maximum=ROUTING_MAX_CANDIDATES,
        label="candidate list",
        unique=True,
    )
    semantic_cards = _bind(corpus, names)
    contracts, canonicalizer_descriptions = _parameter_contracts(
        tuple(card.tool_name for card in semantic_cards),
        contracts_by_tool=contracts_by_tool,
        canonicalizers=canonicalizers,
    )
    cards = _contract_cards(contracts, corpus.cards_by_name)
    joint_task_ids = {
        "multi-call-ordering",
        "correction-resolution",
        "implicit-end-state-resolution",
        "multiturn-carryover",
    }
    task = tuple(
        card.text for card in corpus.task_cards if card.card_id in joint_task_ids
    )
    lines = [
        "AUDIO2TOOL JOINT ROUTING AND PARAMETER GROUND",
        "Select and fill between one and seven requested calls using only the exact candidate tools below.",
        "Use choose and avoid semantics for routing, then apply only the selected tools' public parameter contracts.",
        "Preserve requested multiplicity and spoken order; a final correction supersedes an earlier value or action.",
        "A public default may complete an explicitly requested operation when speech omits that argument.",
        "A default never proves that an operation was requested and must not create a new call.",
        "TASK-WIDE GUIDANCE:",
        *task,
        "CANONICALIZATION RULES:",
        *(f"{name}: {description}" for name, description in canonicalizer_descriptions),
        "CANDIDATE CONTRACTS:",
    ]
    for contract, card in zip(contracts, cards, strict=True):
        semantic = corpus.cards_by_name[contract.tool_name]
        lines.extend(
            (
                f"Choose: {semantic.choose_semantics}",
                f"Avoid: {semantic.avoid_semantics}",
                *_parameter_lines(contract, card),
            )
        )
    text = "\n".join(lines) + "\n"
    response = audio2tool_call_array_response_format(
        _contract_registry(contracts),
        cards,
        schema_name="audio2tool_joint_candidate_calls",
        min_calls=1,
        max_calls=PARAMETER_MAX_OCCURRENCES,
    )
    text, text_hash, response_hash, report = _finish(
        text,
        response,
        {
            "candidate_count": len(names),
            "candidate_tool_names": names,
            "task_guidance_count": len(task),
            "selected_default_declaration_count": sum(
                bool(contract.defaults) for contract in contracts
            ),
            "selected_omission_rule_count": sum(
                len(contract.omission_rules) for contract in contracts
            ),
            "selected_canonicalizer_count": len(canonicalizer_descriptions),
            "answer_cardinality": {
                "minimum": 1,
                "maximum": PARAMETER_MAX_OCCURRENCES,
            },
            "rendered_ascii_bytes": len(text.encode("ascii")),
            "byte_cap": byte_cap,
        },
        byte_cap,
    )
    return JointKnowledgeGround(
        names, text, text_hash, response, response_hash, report
    )


def build_parameter_knowledge_ground(
    corpus: ExecutableSemanticCardCorpus,
    selected_tool_occurrences: Sequence[str],
    *,
    contracts_by_tool: Mapping[str, CanonicalContract],
    canonicalizers: Mapping[str, str],
    byte_cap: int = DEFAULT_BYTE_CAP,
) -> ParameterKnowledgeGround:
    """Build a selected-tool FILL packet, preserving occurrence positions."""
    corpus = _corpus(corpus)
    if isinstance(byte_cap, bool) or not isinstance(byte_cap, int) or byte_cap <= 0:
        raise SelectFillGroundError("byte cap must be a positive integer")
    occurrences = _names(selected_tool_occurrences, minimum=0, maximum=PARAMETER_MAX_OCCURRENCES, label="selected occurrences", unique=False)
    semantic_cards = _bind(corpus, occurrences)
    contracts, canonicalizer_descriptions = _parameter_contracts(
        tuple(card.tool_name for card in semantic_cards),
        contracts_by_tool=contracts_by_tool,
        canonicalizers=canonicalizers,
    )
    cards = _contract_cards(contracts, corpus.cards_by_name)
    task = tuple(
        card.text
        for card in corpus.task_cards
        if card.card_id
        in {
            "correction-resolution",
            "implicit-end-state-resolution",
            "multiturn-carryover",
        }
    )
    lines = [
        "AUDIO2TOOL PARAMETER GROUND",
        "Fill only the selected call positions using the selected tools' public contracts.",
        "Apply correction and multiturn guidance while preserving selected occurrence order.",
        "A public default may complete an explicitly requested operation when speech omits that argument.",
        "A default never proves that an operation was requested and must not create a new call.",
        "TASK-WIDE PARAMETER GUIDANCE:",
        *task,
        "CANONICALIZATION RULES:",
        *(f"{name}: {description}" for name, description in canonicalizer_descriptions),
    ]
    for contract, card in zip(contracts, cards, strict=True):
        lines.extend(_parameter_lines(contract, card))
    text = "\n".join(lines) + "\n"
    response = audio2tool_locked_call_array_response_format(
        _contract_registry(contracts) if contracts else _registry(corpus.tool_cards),
        cards,
        occurrences,
        schema_name="audio2tool_parameter_locked_calls",
    )
    text, text_hash, response_hash, report = _finish(text, response, {
        "selected_occurrence_count": len(occurrences), "selected_tool_count": len(cards), "selected_tool_names": tuple(card.tool_name for card in cards),
        "selected_default_declaration_count": sum(bool(contract.defaults) for contract in contracts),
        "selected_omission_rule_count": sum(len(contract.omission_rules) for contract in contracts),
        "selected_canonicalizer_count": len(canonicalizer_descriptions),
        "task_guidance_count": len(task), "rendered_ascii_bytes": len(text.encode("ascii")), "byte_cap": byte_cap,
    }, byte_cap)
    return ParameterKnowledgeGround(tuple(card.tool_name for card in cards), occurrences, text, text_hash, response, response_hash, report)


def build_sparse_parameter_knowledge_ground(
    corpus: ExecutableSemanticCardCorpus,
    selected_tool_occurrences: Sequence[str],
    *,
    contracts_by_tool: Mapping[str, CanonicalContract],
    canonicalizers: Mapping[str, str],
    byte_cap: int = DEFAULT_BYTE_CAP,
) -> ParameterKnowledgeGround:
    """Build an occurrence-indexed FILL packet without default completion."""

    corpus = _corpus(corpus)
    if isinstance(byte_cap, bool) or not isinstance(byte_cap, int) or byte_cap <= 0:
        raise SelectFillGroundError("byte cap must be a positive integer")
    occurrences = _names(
        selected_tool_occurrences,
        minimum=0,
        maximum=PARAMETER_MAX_OCCURRENCES,
        label="selected occurrences",
        unique=False,
    )
    semantic_cards = _bind(corpus, occurrences)
    contracts, canonicalizer_descriptions = _parameter_contracts(
        tuple(card.tool_name for card in semantic_cards),
        contracts_by_tool=contracts_by_tool,
        canonicalizers=canonicalizers,
    )
    cards = _contract_cards(contracts, corpus.cards_by_name)
    task = tuple(
        card.text
        for card in corpus.task_cards
        if card.card_id
        in {
            "correction-resolution",
            "implicit-end-state-resolution",
            "multiturn-carryover",
        }
    )
    lines = [
        "AUDIO2TOOL OCCURRENCE-INDEXED EVIDENCE-SPARSE PARAMETER GROUND",
        "Fill only the selected call positions using the selected tools' public contracts.",
        "Bind each argument object to its exact selected occurrence position.",
        "Use the shortest legal key set supported by original speech or canonical OBS.",
        "Do not add an argument key or value only because a public default exists.",
        "When no argument is supported and {} is a listed legal key set, emit {}.",
        "Apply correction and multiturn guidance while preserving selected occurrence order.",
        "SELECTED OCCURRENCES:",
        *(
            f"Occurrence {index}: {name}"
            for index, name in enumerate(occurrences, start=1)
        ),
        "TASK-WIDE PARAMETER GUIDANCE:",
        *task,
        "CANONICALIZATION RULES:",
        *(
            f"{name}: {description}"
            for name, description in canonicalizer_descriptions
        ),
        "UNIQUE SELECTED TOOL CONTRACTS:",
    ]
    for contract, card in zip(contracts, cards, strict=True):
        lines.extend(
            _parameter_lines(
                contract,
                card,
                include_default_semantics=False,
                include_examples=False,
                include_role_guidance=False,
            )
        )
    text = "\n".join(lines) + "\n"
    response = audio2tool_locked_call_array_response_format(
        _contract_registry(contracts) if contracts else _registry(corpus.tool_cards),
        cards,
        occurrences,
        schema_name="audio2tool_parameter_locked_calls",
    )
    text, text_hash, response_hash, report = _finish(
        text,
        response,
        {
            "fill_policy": "occurrence-indexed-evidence-sparse",
            "selected_occurrence_count": len(occurrences),
            "occurrence_bindings_rendered": len(occurrences),
            "selected_tool_count": len(cards),
            "selected_tool_names": tuple(card.tool_name for card in cards),
            "selected_default_declaration_count": 0,
            "selected_omission_rule_count": 0,
            "selected_canonicalizer_count": len(canonicalizer_descriptions),
            "examples_rendered": 0,
            "role_guidance_rendered": 0,
            "task_guidance_count": len(task),
            "rendered_ascii_bytes": len(text.encode("ascii")),
            "byte_cap": byte_cap,
        },
        byte_cap,
    )
    return ParameterKnowledgeGround(
        tuple(card.tool_name for card in cards),
        occurrences,
        text,
        text_hash,
        response,
        response_hash,
        report,
    )


__all__ = [
    "DEFAULT_BYTE_CAP", "PARAMETER_MAX_OCCURRENCES", "ROUTING_MAX_CANDIDATES", "JointKnowledgeGround", "ParameterKnowledgeGround", "RoutingKnowledgeGround", "SelectFillGroundError", "build_interface_routing_knowledge_ground", "build_joint_knowledge_ground", "build_parameter_knowledge_ground", "build_routing_knowledge_ground", "build_sparse_parameter_knowledge_ground",
]
