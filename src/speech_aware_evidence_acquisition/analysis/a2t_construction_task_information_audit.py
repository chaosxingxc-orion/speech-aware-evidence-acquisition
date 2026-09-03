"""Detailed model-free task-information audit for Audio2Tool construction rows.

The audit consumes only caller-supplied :class:`A2tKbRow` construction rows
and frozen canonical action-contract and tool-family metadata.  It never reads
evaluation or test data, model outputs, files, scorers, models, or the network.
Construction utterances are neither inspected nor emitted. Concrete argument
values are checked only for row-integrity agreement with their key skeleton;
they are never aggregated, used as analysis features, or emitted.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
import json
import math
import re
from typing import Mapping, Sequence

from ..rails.action_family_contracts import ActionContract, ActionFamily
from ..rails.knowledge_build_a2t import A2tKbRow, TIERS


AUDIT_SCHEMA = "saea-a2t-construction-task-information-audit-v1"
DEFAULT_LONG_TAIL_MAX_UNIT_SUPPORT = 5
DEFAULT_TOP_K = (1, 5, 10, 25, 50, 100, 151)
_NO_DEFAULT = "No public default is declared."
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_FAMILY_TAG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_COMPLEX_TIER_NEEDS = {
    "tier3_multi_intent": "Discriminate multiple intents and preserve all call occurrences in order.",
    "tier6_correction": "Resolve corrections without retaining superseded tool or value bindings.",
    "tier7_multiturn": "Use the relevant dialogue state while preserving final-turn bindings and omissions.",
    "tier8_intent_blending": "Separate blended intents and preserve their multiplicity, arguments, and order.",
}


class A2tConstructionTaskInformationError(ValueError):
    """Construction rows or frozen metadata violate the audit contract."""


@dataclass(frozen=True)
class A2tConstructionTaskInformationAudit:
    """A JSON-compatible report and its deterministic canonical serialization."""

    report: Mapping[str, object]
    canonical_json: str


def _nonempty_ascii(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or not value.isascii():
        raise A2tConstructionTaskInformationError(
            f"{label} must be non-empty ASCII English text"
        )
    return value


def _key_tuple(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise A2tConstructionTaskInformationError(f"{label} must be a tuple")
    if len(value) != len(set(value)) or any(
        not isinstance(key, str) or _IDENTIFIER.fullmatch(key) is None for key in value
    ):
        raise A2tConstructionTaskInformationError(
            f"{label} must contain unique identifier keys"
        )
    return value


def _construction_key_tuple(value: object, label: str) -> tuple[str, ...]:
    """Validate preserved construction keys without treating them as canonical."""

    if (
        not isinstance(value, tuple)
        or len(value) != len(set(value))
        or any(
            not isinstance(key, str) or not key or not key.isascii() for key in value
        )
    ):
        raise A2tConstructionTaskInformationError(
            f"{label} must contain unique non-empty ASCII keys"
        )
    return value


def _syntax_compatible(signature: Sequence[str]) -> bool:
    return all(_IDENTIFIER.fullmatch(key) is not None for key in signature)


def _validate_controls(
    *,
    long_tail_max_unit_support: int,
    top_k: Sequence[int],
    tier_order: Sequence[str],
) -> tuple[tuple[int, ...], tuple[str, ...]]:
    if type(long_tail_max_unit_support) is not int or long_tail_max_unit_support <= 0:
        raise A2tConstructionTaskInformationError(
            "long-tail maximum unit support must be a positive integer"
        )
    if isinstance(top_k, (str, bytes)):
        raise A2tConstructionTaskInformationError(
            "top-k values must be unique positive integers"
        )
    k_values = tuple(top_k)
    if (
        not k_values
        or len(k_values) != len(set(k_values))
        or any(type(value) is not int or value <= 0 for value in k_values)
    ):
        raise A2tConstructionTaskInformationError(
            "top-k values must be unique positive integers"
        )
    if isinstance(tier_order, (str, bytes)):
        raise A2tConstructionTaskInformationError(
            "tier order must equal the frozen Audio2Tool tier order"
        )
    tiers = tuple(tier_order)
    if tiers != TIERS:
        raise A2tConstructionTaskInformationError(
            "tier order must equal the frozen Audio2Tool tier order"
        )
    return tuple(sorted(k_values)), tiers


def _validate_families(
    families: Sequence[ActionFamily],
) -> tuple[tuple[ActionFamily, ...], dict[str, ActionFamily]]:
    if isinstance(families, (str, bytes)):
        raise A2tConstructionTaskInformationError(
            "families must contain frozen ActionFamily metadata"
        )
    ordered = tuple(sorted(families, key=lambda family: getattr(family, "tag", "")))
    if not ordered:
        raise A2tConstructionTaskInformationError(
            "at least one frozen tool family is required"
        )
    by_tag: dict[str, ActionFamily] = {}
    seen_tools: set[str] = set()
    for family in ordered:
        if not isinstance(family, ActionFamily):
            raise A2tConstructionTaskInformationError(
                "families must contain frozen ActionFamily metadata"
            )
        tag = _nonempty_ascii(family.tag, "family tag")
        if _FAMILY_TAG.fullmatch(tag) is None or tag in by_tag:
            raise A2tConstructionTaskInformationError(
                "family tags must be unique canonical slugs"
            )
        _nonempty_ascii(family.label, f"family {tag!r} label")
        if (
            not isinstance(family.tool_names, tuple)
            or not family.tool_names
            or family.tool_names != tuple(sorted(set(family.tool_names)))
            or any(
                not isinstance(name, str) or _IDENTIFIER.fullmatch(name) is None
                for name in family.tool_names
            )
        ):
            raise A2tConstructionTaskInformationError(
                f"family {tag!r} tool membership must be sorted, unique identifiers"
            )
        overlap = seen_tools & set(family.tool_names)
        if overlap:
            raise A2tConstructionTaskInformationError(
                f"family membership repeats tools: {sorted(overlap)!r}"
            )
        seen_tools.update(family.tool_names)
        if (
            not isinstance(family.bundle_sha256, str)
            or len(family.bundle_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in family.bundle_sha256
            )
            or type(family.bundle_utf8_bytes) is not int
            or family.bundle_utf8_bytes <= 0
        ):
            raise A2tConstructionTaskInformationError(
                f"family {tag!r} lacks a frozen canonical bundle identity"
            )
        by_tag[tag] = family
    return ordered, by_tag


def _validate_contracts(
    contracts: Sequence[ActionContract],
    families_by_tag: Mapping[str, ActionFamily],
) -> tuple[tuple[ActionContract, ...], dict[str, ActionContract]]:
    if isinstance(contracts, (str, bytes)):
        raise A2tConstructionTaskInformationError(
            "contracts must contain frozen ActionContract metadata"
        )
    ordered = tuple(
        sorted(contracts, key=lambda contract: getattr(contract, "tool_name", ""))
    )
    if not ordered:
        raise A2tConstructionTaskInformationError(
            "at least one frozen action contract is required"
        )
    by_tool: dict[str, ActionContract] = {}
    contract_ids: set[str] = set()
    for contract in ordered:
        if not isinstance(contract, ActionContract):
            raise A2tConstructionTaskInformationError(
                "contracts must contain frozen ActionContract metadata"
            )
        tool = _nonempty_ascii(contract.tool_name, "contract tool_name")
        if _IDENTIFIER.fullmatch(tool) is None or tool in by_tool:
            raise A2tConstructionTaskInformationError(
                "duplicate contract tool or malformed tool identifier"
            )
        contract_id = _nonempty_ascii(contract.contract_id, f"{tool} contract_id")
        if contract_id in contract_ids:
            raise A2tConstructionTaskInformationError("duplicate contract id")
        contract_ids.add(contract_id)
        if contract.family_tag not in families_by_tag:
            raise A2tConstructionTaskInformationError(
                f"contract {tool!r} names an unknown family"
            )
        ordered_keys = _key_tuple(contract.ordered_keys, f"{tool} ordered_keys")
        required = _key_tuple(contract.required_keys, f"{tool} required_keys")
        optional = _key_tuple(contract.optional_keys, f"{tool} optional_keys")
        conditional = _key_tuple(contract.conditional_keys, f"{tool} conditional_keys")
        forbidden = _key_tuple(contract.forbidden_keys, f"{tool} forbidden_keys")
        roles = (set(required), set(optional), set(conditional))
        if (
            any(roles[left] & roles[right] for left, right in combinations(range(3), 2))
            or set(ordered_keys) != set().union(*roles)
            or set(forbidden) & set(ordered_keys)
        ):
            raise A2tConstructionTaskInformationError(
                f"contract {tool!r} key roles do not partition ordered keys"
            )
        if (
            not isinstance(contract.legal_key_skeletons, tuple)
            or not contract.legal_key_skeletons
        ):
            raise A2tConstructionTaskInformationError(
                f"contract {tool!r} needs at least one legal skeleton"
            )
        skeletons: list[tuple[str, ...]] = []
        positions = {key: index for index, key in enumerate(ordered_keys)}
        for skeleton_value in contract.legal_key_skeletons:
            skeleton = _key_tuple(skeleton_value, f"{tool} legal skeleton")
            if (
                not set(skeleton).issubset(ordered_keys)
                or tuple(sorted(skeleton, key=positions.__getitem__)) != skeleton
            ):
                raise A2tConstructionTaskInformationError(
                    f"contract {tool!r} has an invalid legal skeleton"
                )
            skeletons.append(skeleton)
        if len(skeletons) != len(set(skeletons)):
            raise A2tConstructionTaskInformationError(
                f"contract {tool!r} repeats a legal skeleton"
            )
        if (
            not isinstance(contract.types, tuple)
            or any(
                not isinstance(pair, tuple)
                or len(pair) != 2
                or not isinstance(pair[0], str)
                or not isinstance(pair[1], str)
                or not pair[1]
                or not pair[1].isascii()
                for pair in contract.types
            )
            or tuple(key for key, _type_name in contract.types) != ordered_keys
        ):
            raise A2tConstructionTaskInformationError(
                f"contract {tool!r} typed rules must cover ordered keys exactly"
            )
        _nonempty_ascii(contract.operation, f"{tool} operation")
        _nonempty_ascii(contract.defaults, f"{tool} defaults")
        _nonempty_ascii(contract.constraints, f"{tool} constraints")
        if (
            not isinstance(contract.omission_rules, tuple)
            or not contract.omission_rules
            or any(
                not isinstance(rule, str) or not rule or not rule.isascii()
                for rule in contract.omission_rules
            )
        ):
            raise A2tConstructionTaskInformationError(
                f"contract {tool!r} omission rules must be ASCII English text"
            )
        if not isinstance(contract.canonicalization_rules, tuple) or any(
            not isinstance(rule, str) or not rule or not rule.isascii()
            for rule in contract.canonicalization_rules
        ):
            raise A2tConstructionTaskInformationError(
                f"contract {tool!r} canonicalization rules are malformed"
            )
        by_tool[tool] = contract

    expected_by_family = {
        tag: tuple(
            contract.tool_name for contract in ordered if contract.family_tag == tag
        )
        for tag in families_by_tag
    }
    for tag, family in families_by_tag.items():
        if family.tool_names != expected_by_family[tag]:
            raise A2tConstructionTaskInformationError(
                f"family membership drift for {tag!r}"
            )
    return ordered, by_tool


def _validate_rows(
    rows: Sequence[A2tKbRow],
    contracts_by_tool: Mapping[str, ActionContract],
    tier_order: Sequence[str],
) -> tuple[A2tKbRow, ...]:
    if isinstance(rows, (str, bytes)):
        raise A2tConstructionTaskInformationError(
            "construction_rows must contain A2tKbRow values"
        )
    ordered = tuple(sorted(rows, key=lambda row: getattr(row, "unit_id", "")))
    if not ordered:
        raise A2tConstructionTaskInformationError(
            "at least one construction row is required"
        )
    seen_units: set[str] = set()
    tier_set = set(tier_order)
    for row in ordered:
        if not isinstance(row, A2tKbRow):
            raise A2tConstructionTaskInformationError(
                "construction_rows must contain A2tKbRow values"
            )
        unit_id = _nonempty_ascii(row.unit_id, "construction unit_id")
        if unit_id in seen_units:
            raise A2tConstructionTaskInformationError(f"duplicate unit id {unit_id!r}")
        seen_units.add(unit_id)
        if row.tier not in tier_set:
            raise A2tConstructionTaskInformationError(
                f"construction row {unit_id!r} has an unknown tier"
            )
        if type(row.query_idx) is not int or row.query_idx < 0:
            raise A2tConstructionTaskInformationError(
                f"construction row {unit_id!r} has an invalid query_idx"
            )
        if unit_id != f"{row.tier}:{row.query_idx:06d}":
            raise A2tConstructionTaskInformationError(
                f"construction row {unit_id!r} identity disagrees with tier/query_idx"
            )
        contract = contracts_by_tool.get(row.tool_name)
        if contract is None:
            raise A2tConstructionTaskInformationError(
                f"construction row {unit_id!r} names an unknown tool"
            )
        if not isinstance(row.extra_call_names, tuple) or any(
            name not in contracts_by_tool for name in row.extra_call_names
        ):
            raise A2tConstructionTaskInformationError(
                f"construction row {unit_id!r} names an unknown tool in extra calls"
            )
        if type(row.call_count) is not int or row.call_count != 1 + len(
            row.extra_call_names
        ):
            raise A2tConstructionTaskInformationError(
                f"construction row {unit_id!r} call_count disagrees with call occurrences"
            )
        signature = _construction_key_tuple(
            row.arg_signature, f"construction row {unit_id!r} arg_signature"
        )
        if signature != tuple(sorted(signature)):
            raise A2tConstructionTaskInformationError(
                f"construction row {unit_id!r} arg_signature must be sorted"
            )
        if _syntax_compatible(signature):
            contract_positions = {
                key: index for index, key in enumerate(contract.ordered_keys)
            }
            if not set(signature).issubset(contract_positions):
                raise A2tConstructionTaskInformationError(
                    f"construction row {unit_id!r} arg_signature is not a legal skeleton"
                )
            contract_ordered_signature = tuple(
                sorted(signature, key=contract_positions.__getitem__)
            )
            if contract_ordered_signature not in contract.legal_key_skeletons:
                raise A2tConstructionTaskInformationError(
                    f"construction row {unit_id!r} arg_signature is not a legal skeleton"
                )
        if (
            not isinstance(row.arg_pairs, tuple)
            or any(
                not isinstance(pair, tuple)
                or len(pair) != 2
                or not isinstance(pair[0], str)
                or not isinstance(pair[1], str)
                for pair in row.arg_pairs
            )
            or tuple(key for key, _value in row.arg_pairs) != signature
        ):
            raise A2tConstructionTaskInformationError(
                f"construction row {unit_id!r} arg_signature and arg_pairs disagree"
            )
    return ordered


def _histogram(values: Sequence[int]) -> dict[str, int]:
    return {str(value): count for value, count in sorted(Counter(values).items())}


def _shares(counts: Mapping[str, int], denominator: int) -> dict[str, float]:
    return {key: counts[key] / denominator for key in sorted(counts)}


def _edges(
    per_unit: Sequence[Sequence[str]], total_units: int
) -> list[dict[str, object]]:
    counts: Counter[tuple[str, str]] = Counter()
    for labels in per_unit:
        counts.update(combinations(sorted(set(labels)), 2))
    return [
        {
            "left": left,
            "right": right,
            "unit_count": counts[(left, right)],
            "unit_share": counts[(left, right)] / total_units,
        }
        for left, right in sorted(counts)
    ]


def _minimum_k_for_mass(
    ranked_counts: Sequence[int], total_calls: int
) -> dict[str, int]:
    thresholds = (0.50, 0.80, 0.90, 0.95, 0.99, 1.00)
    cumulative = 0
    result: dict[str, int] = {}
    for rank, count in enumerate(ranked_counts, start=1):
        cumulative += count
        mass = cumulative / total_calls
        for threshold in thresholds:
            key = f"{threshold:.2f}"
            if key not in result and mass >= threshold - 1e-15:
                result[key] = rank
    return result


def audit_construction_task_information(
    *,
    construction_rows: Sequence[A2tKbRow],
    contracts: Sequence[ActionContract],
    families: Sequence[ActionFamily],
    long_tail_max_unit_support: int = DEFAULT_LONG_TAIL_MAX_UNIT_SUPPORT,
    top_k: Sequence[int] = DEFAULT_TOP_K,
    tier_order: Sequence[str] = TIERS,
) -> A2tConstructionTaskInformationAudit:
    """Return construction-only task-information diagnostics and canonical JSON."""

    k_values, tiers = _validate_controls(
        long_tail_max_unit_support=long_tail_max_unit_support,
        top_k=top_k,
        tier_order=tier_order,
    )
    ordered_families, families_by_tag = _validate_families(families)
    ordered_contracts, contracts_by_tool = _validate_contracts(
        contracts, families_by_tag
    )
    rows = _validate_rows(construction_rows, contracts_by_tool, tiers)
    total_units = len(rows)
    tool_names = tuple(contract.tool_name for contract in ordered_contracts)
    family_tags = tuple(family.tag for family in ordered_families)
    family_by_tool = {
        contract.tool_name: contract.family_tag for contract in ordered_contracts
    }

    tier_counts: Counter[str] = Counter(row.tier for row in rows)
    tier_count_map = {tier: tier_counts[tier] for tier in tiers}
    unit_tool_lists = [(row.tool_name, *row.extra_call_names) for row in rows]
    unit_family_lists = [
        tuple(family_by_tool[name] for name in names) for names in unit_tool_lists
    ]
    call_counts = [len(names) for names in unit_tool_lists]
    distinct_tool_counts = [len(set(names)) for names in unit_tool_lists]
    distinct_family_counts = [len(set(tags)) for tags in unit_family_lists]
    total_calls = sum(call_counts)

    tool_unit_support: Counter[str] = Counter()
    tool_call_occurrences: Counter[str] = Counter()
    family_unit_support: Counter[str] = Counter()
    family_call_occurrences: Counter[str] = Counter()
    for names, tags in zip(unit_tool_lists, unit_family_lists, strict=True):
        tool_unit_support.update(set(names))
        tool_call_occurrences.update(names)
        family_unit_support.update(set(tags))
        family_call_occurrences.update(tags)
    unit_support_by_tool = {tool: tool_unit_support[tool] for tool in tool_names}
    calls_by_tool = {tool: tool_call_occurrences[tool] for tool in tool_names}
    unit_support_by_family = {tag: family_unit_support[tag] for tag in family_tags}
    calls_by_family = {tag: family_call_occurrences[tag] for tag in family_tags}

    skeleton_rows = tuple(row for row in rows if _syntax_compatible(row.arg_signature))
    canonical_skeleton_rows = tuple(
        (
            row,
            tuple(
                sorted(
                    row.arg_signature,
                    key={
                        key: index
                        for index, key in enumerate(
                            contracts_by_tool[row.tool_name].ordered_keys
                        )
                    }.__getitem__,
                )
            ),
        )
        for row in skeleton_rows
    )
    skeleton_frequency: Counter[tuple[str, tuple[str, ...]]] = Counter(
        (row.tool_name, skeleton) for row, skeleton in canonical_skeleton_rows
    )
    skeleton_shape_frequency: Counter[tuple[str, ...]] = Counter(
        skeleton for _row, skeleton in canonical_skeleton_rows
    )
    skeleton_shape_tools: dict[tuple[str, ...], set[str]] = {}
    key_frequency: Counter[str] = Counter()
    for row, skeleton in canonical_skeleton_rows:
        skeleton_shape_tools.setdefault(skeleton, set()).add(row.tool_name)
        key_frequency.update(skeleton)
    legal_skeletons = [
        (contract.tool_name, skeleton)
        for contract in ordered_contracts
        for skeleton in contract.legal_key_skeletons
    ]
    legal_support = [
        {
            "tool_name": tool,
            "keys": list(skeleton),
            "primary_unit_count": skeleton_frequency[(tool, skeleton)],
            "observed": skeleton_frequency[(tool, skeleton)] > 0,
        }
        for tool, skeleton in legal_skeletons
    ]

    type_frequency = Counter(
        type_name
        for contract in ordered_contracts
        for _key, type_name in contract.types
    )
    tools_permitting_no_argument = sum(
        () in contract.legal_key_skeletons for contract in ordered_contracts
    )
    tools_with_defaults = sum(
        contract.defaults != _NO_DEFAULT for contract in ordered_contracts
    )
    tools_with_optional = sum(
        bool(contract.optional_keys) for contract in ordered_contracts
    )
    tools_with_conditional = sum(
        bool(contract.conditional_keys) for contract in ordered_contracts
    )
    tools_with_multiple_skeletons = sum(
        len(contract.legal_key_skeletons) > 1 for contract in ordered_contracts
    )
    tools_with_typed_rules = sum(bool(contract.types) for contract in ordered_contracts)
    typed_key_rules = sum(len(contract.types) for contract in ordered_contracts)

    ranked_tools = sorted(
        tool_names,
        key=lambda tool: (-tool_call_occurrences[tool], tool),
    )
    probabilities = [
        tool_call_occurrences[tool] / total_calls
        for tool in ranked_tools
        if tool_call_occurrences[tool]
    ]
    entropy_bits = -sum(
        probability * math.log2(probability) for probability in probabilities
    )
    effective_label_count = 2**entropy_bits
    normalized_entropy = (
        entropy_bits / math.log2(len(tool_names)) if len(tool_names) > 1 else 0.0
    )
    cumulative_counts: list[int] = []
    running = 0
    for tool in ranked_tools:
        running += tool_call_occurrences[tool]
        cumulative_counts.append(running)
    top_k_mass = {
        str(k): cumulative_counts[min(k, len(cumulative_counts)) - 1] / total_calls
        for k in k_values
    }
    ranked_tool_rows = [
        {
            "rank": rank,
            "tool_name": tool,
            "call_occurrences": tool_call_occurrences[tool],
            "prior_mass": tool_call_occurrences[tool] / total_calls,
        }
        for rank, tool in enumerate(ranked_tools, start=1)
    ]
    missing_tools = sorted(tool for tool in tool_names if tool_unit_support[tool] == 0)
    long_tail_tools = sorted(
        tool
        for tool in tool_names
        if 0 < tool_unit_support[tool] <= long_tail_max_unit_support
    )

    contract_burdens: dict[str, object] = {
        "tools_permitting_no_argument_call": tools_permitting_no_argument,
        "tools_requiring_no_arguments": sum(
            not contract.ordered_keys for contract in ordered_contracts
        ),
        "tools_with_declared_defaults": tools_with_defaults,
        "tools_with_optional_keys": tools_with_optional,
        "tools_with_conditional_keys": tools_with_conditional,
        "tools_with_multiple_legal_skeletons": tools_with_multiple_skeletons,
        "tools_with_typed_rules": tools_with_typed_rules,
        "typed_key_rule_count": typed_key_rules,
        "required_key_rule_count": sum(
            len(contract.required_keys) for contract in ordered_contracts
        ),
        "optional_key_rule_count": sum(
            len(contract.optional_keys) for contract in ordered_contracts
        ),
        "conditional_key_rule_count": sum(
            len(contract.conditional_keys) for contract in ordered_contracts
        ),
        "legal_key_skeleton_count": len(legal_skeletons),
        "type_rule_frequency": dict(sorted(type_frequency.items())),
    }
    primary_argument_counts = [len(row.arg_signature) for row in rows]
    call_structure = {
        "calls_per_unit": _histogram(call_counts),
        "maximum_calls_per_unit": max(call_counts),
        "multi_call_unit_count": sum(count > 1 for count in call_counts),
        "multi_call_rate": sum(count > 1 for count in call_counts) / total_units,
        "distinct_tools_per_unit": _histogram(distinct_tool_counts),
        "distinct_families_per_unit": _histogram(distinct_family_counts),
    }
    argument_structure = {
        "scope": "Primary calls only; A2tKbRow does not retain argument skeletons for extra calls.",
        "extra_call_argument_structure_available": False,
        "primary_argument_count_per_unit": _histogram(primary_argument_counts),
        "skeleton_eligible_primary_unit_count": len(skeleton_rows),
        "syntax_incompatible_primary_unit_count": total_units - len(skeleton_rows),
        "argument_bearing_primary_unit_count": sum(
            count > 0 for count in primary_argument_counts
        ),
        "no_argument_primary_unit_count": sum(
            count == 0 for count in primary_argument_counts
        ),
        "primary_argument_key_frequency": dict(sorted(key_frequency.items())),
        "distinct_observed_primary_key_skeleton_count": len(skeleton_frequency),
        "key_skeleton_frequency": [
            {
                "tool_name": tool,
                "keys": list(skeleton),
                "primary_unit_count": count,
                "primary_unit_share": count / total_units,
            }
            for (tool, skeleton), count in sorted(skeleton_frequency.items())
        ],
        "skeleton_support": [
            {
                "keys": list(skeleton),
                "primary_unit_count": skeleton_shape_frequency[skeleton],
                "supporting_tool_count": len(skeleton_shape_tools[skeleton]),
                "supporting_tools": sorted(skeleton_shape_tools[skeleton]),
            }
            for skeleton in sorted(
                skeleton_shape_frequency,
                key=lambda value: (-skeleton_shape_frequency[value], value),
            )
        ],
        "legal_skeleton_support_by_tool": legal_support,
        "observed_legal_skeleton_count": sum(
            item["observed"] is True for item in legal_support
        ),
        "unobserved_legal_skeleton_count": sum(
            item["observed"] is False for item in legal_support
        ),
    }
    tier_composition = {
        tier: {
            "unit_count": tier_count_map[tier],
            "unit_share": tier_count_map[tier] / total_units,
            "information_need": description,
        }
        for tier, description in _COMPLEX_TIER_NEEDS.items()
    }
    report: dict[str, object] = {
        "schema": AUDIT_SCHEMA,
        "input_boundary": {
            "construction_rows_only": True,
            "canonical_contract_and_family_metadata_only": True,
            "evaluation_or_test_rows_consumed": 0,
            "model_outputs_consumed": 0,
            "model_contacts": 0,
            "scorer_contacts": 0,
            "network_contacts": 0,
            "construction_text_or_argument_values_emitted": False,
        },
        "population": {
            "construction_unit_count": total_units,
            "registry_tool_count": len(tool_names),
            "family_count": len(family_tags),
            "call_occurrence_count": total_calls,
        },
        "tiers": {
            "counts": tier_count_map,
            "shares": {tier: tier_count_map[tier] / total_units for tier in tiers},
        },
        "tool_support": {
            "unit_support_by_tool": unit_support_by_tool,
            "unit_support_shares_by_tool": _shares(unit_support_by_tool, total_units),
            "call_occurrences_by_tool": calls_by_tool,
            "call_occurrence_shares_by_tool": _shares(calls_by_tool, total_calls),
            "unit_support_distribution": _histogram(
                list(unit_support_by_tool.values())
            ),
            "long_tail_max_unit_support": long_tail_max_unit_support,
            "long_tail_tools": long_tail_tools,
            "missing_registry_tools": missing_tools,
        },
        "family_support": {
            "unit_support_by_family": unit_support_by_family,
            "unit_support_shares": _shares(unit_support_by_family, total_units),
            "call_occurrences_by_family": calls_by_family,
            "call_occurrence_shares": _shares(calls_by_family, total_calls),
        },
        "call_structure": call_structure,
        "argument_structure": argument_structure,
        "contract_burdens": contract_burdens,
        "cooccurrence": {
            "tool_edges": _edges(unit_tool_lists, total_units),
            "family_edges": _edges(unit_family_lists, total_units),
            "multi_tool_unit_count": sum(count > 1 for count in distinct_tool_counts),
            "cross_family_unit_count": sum(
                count > 1 for count in distinct_family_counts
            ),
        },
        "raw_tool_prior": {
            "basis": "All ordered primary and extra call-name occurrences in construction rows.",
            "entropy_bits": entropy_bits,
            "effective_label_count": effective_label_count,
            "normalized_entropy": normalized_entropy,
            "ranked_tools": ranked_tool_rows,
            "top_k_mass": top_k_mass,
            "minimum_k_for_mass": _minimum_k_for_mass(
                [tool_call_occurrences[tool] for tool in ranked_tools], total_calls
            ),
            "safe_registry_label_reduction_supported": False,
            "interpretation": (
                "A construction-frequency prior is population-level rather than per-unit "
                f"evidence and cannot safely exclude any of the {len(tool_names)} frozen "
                "registry labels; zero or low construction support does not make a "
                "registered tool impossible."
            ),
        },
        "task_information_needs": {
            "tool_discrimination": {
                "registry_labels": len(tool_names),
                "observed_labels": len(tool_names) - len(missing_tools),
                "missing_registry_labels": len(missing_tools),
                "effective_label_count_from_raw_prior": effective_label_count,
                "raw_prior_safely_reduces_registry": False,
                "need": "Use unit-specific speech evidence to discriminate exact registered tools.",
            },
            "multiplicity_and_order": {
                "multi_call_units": call_structure["multi_call_unit_count"],
                "multi_call_rate": call_structure["multi_call_rate"],
                "maximum_calls_per_unit": call_structure["maximum_calls_per_unit"],
                "ordered_call_names_available": True,
                "need": "Preserve primary-plus-extra call multiplicity and order, including duplicates.",
            },
            "key_skeleton_selection": {
                "observed_primary_skeletons": len(skeleton_frequency),
                "legal_contract_skeletons": len(legal_skeletons),
                "tools_with_multiple_legal_skeletons": tools_with_multiple_skeletons,
                "extra_call_skeletons_available": False,
                "need": "Select one exact legal key skeleton without adding, renaming, or conflating keys.",
            },
            "value_binding": {
                "argument_bearing_primary_units": argument_structure[
                    "argument_bearing_primary_unit_count"
                ],
                "typed_key_rules": typed_key_rules,
                "type_rule_forms": len(type_frequency),
                "concrete_argument_values_structurally_validated": True,
                "concrete_argument_values_used_as_analysis_features": False,
                "need": "Bind speech-grounded values while preserving exact JSON types and values.",
            },
            "default_and_omission": {
                "tools_with_declared_defaults": tools_with_defaults,
                "tools_with_optional_keys": tools_with_optional,
                "tools_with_conditional_keys": tools_with_conditional,
                "tools_permitting_no_argument_call": tools_permitting_no_argument,
                "need": "Distinguish omission, defaults, conditional keys, explicit null, and no-argument calls.",
            },
            "tier_conditioned_composition": tier_composition,
        },
    }
    canonical_json = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return A2tConstructionTaskInformationAudit(
        report=report,
        canonical_json=canonical_json,
    )


__all__ = [
    "AUDIT_SCHEMA",
    "A2tConstructionTaskInformationAudit",
    "A2tConstructionTaskInformationError",
    "DEFAULT_LONG_TAIL_MAX_UNIT_SUPPORT",
    "DEFAULT_TOP_K",
    "audit_construction_task_information",
]
