"""Render compact, value-safe decision cards for selected Audio2Tool tools.

Retrieval or a frozen planning contact may nominate a small ordered tool set.
This module is the common supply boundary after that nomination: it verifies the
frozen G5 contract corpus and qualified compatibility rules, then exposes only
the selected public contracts and an exact structured-response grammar.  It
does not read speech, examples, samples, labels, scores, or concrete task values.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``SelectedToolDecisionGround.build`` is catalog id
``saea-tool-a2t-selected-tool-ground-v1`` on the ``SUPPLY`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .a2t_canonical_family_ground import (
    CanonicalContract,
    CanonicalFamilyGround,
    CanonicalFamilyGroundError,
)
from .a2t_executable_semantic_cards import CompatibilityRule, ToolSemanticCard
from .a2t_response_schema import audio2tool_call_array_response_format


SELECTED_TOOL_MAX_COUNT = 16
SELECTED_TOOL_MAX_CALLS = 7
SELECTED_TOOL_GROUND_ASCII_BYTE_CAP = 32_768

_NO_DECLARATION = frozenset({"", "none", "none declared", "(none)"})
_COMPATIBILITY_GUIDANCE = {
    "boolean": "JSON Boolean",
    "boolean-string": 'JSON string "True" or "False"',
    "integer": "JSON integer",
    "list": "JSON array of strings",
    "map": "JSON object",
    "nullable-string": "JSON string or null",
    "number": "JSON number",
    "string": "JSON string",
}


class SelectedToolGroundError(ValueError):
    """The frozen corpus cannot form the requested selected-tool ground."""


@dataclass(frozen=True)
class SelectedToolDecisionPacket:
    """One hash-bound selected-tool card and its strict response format."""

    selected_tool_names: tuple[str, ...]
    text: str
    text_sha256: str
    response_format: Mapping[str, object]
    response_format_sha256: str
    report: Mapping[str, object]


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _compatibility_sort_key(
    rule: CompatibilityRule,
) -> tuple[str, tuple[str, ...], tuple[tuple[str, str], ...], int]:
    return (
        rule.tool_name,
        tuple(rule.legal_argument_key_set),
        tuple(rule.value_forms),
        rule.construction_support_count,
    )


def _compatibility_payload(
    rules: Sequence[CompatibilityRule],
) -> list[dict[str, object]]:
    return [
        {
            "tool_name": rule.tool_name,
            "legal_argument_key_set": list(rule.legal_argument_key_set),
            "value_forms": [list(item) for item in rule.value_forms],
            "construction_support_count": rule.construction_support_count,
        }
        for rule in rules
    ]


def _render_keys(keys: Sequence[str]) -> str:
    return "{" + ", ".join(keys) + "}"


def _render_role(label: str, keys: Sequence[str]) -> str:
    return f"{label}: {', '.join(keys) if keys else '(none)'}"


def _is_no_declaration(value: str) -> bool:
    normalized = value.strip().casefold()
    return normalized in _NO_DECLARATION or normalized.startswith("no public ")


class SelectedToolDecisionGround:
    """Verified G5 corpus view for one ordered selection of up to 16 tools."""

    def __init__(
        self,
        *,
        ground: CanonicalFamilyGround,
        compatibility_rules: tuple[CompatibilityRule, ...],
        byte_cap: int,
    ) -> None:
        self._ground = ground
        self._compatibility_rules = compatibility_rules
        self.byte_cap = byte_cap
        self.corpus_sha256 = ground.corpus_sha256
        self.compatibility_sha256 = hashlib.sha256(
            _canonical_json_bytes(_compatibility_payload(compatibility_rules))
        ).hexdigest()
        contracts = tuple(
            contract
            for family_tag in ground.family_tags
            for contract in ground._contracts_by_family[family_tag]
        )
        self._contracts_by_tool = {
            contract.tool_name: contract for contract in contracts
        }
        self._family_labels = {
            family_tag: ground._labels[family_tag] for family_tag in ground.family_tags
        }
        self._canonicalizers = dict(ground._canonicalizers)
        self._rules_by_tool = {
            tool_name: tuple(
                rule for rule in compatibility_rules if rule.tool_name == tool_name
            )
            for tool_name in ground.tool_names
        }

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        compatibility_rules: Sequence[CompatibilityRule],
        byte_cap: int = SELECTED_TOOL_GROUND_ASCII_BYTE_CAP,
    ) -> "SelectedToolDecisionGround":
        """Load the passed frozen corpus and bind exactly 43 qualified rules."""

        if isinstance(byte_cap, bool) or not isinstance(byte_cap, int) or byte_cap <= 0:
            raise SelectedToolGroundError("byte cap must be a positive integer")
        try:
            ordered_rules = tuple(
                sorted(compatibility_rules, key=_compatibility_sort_key)
            )
        except (AttributeError, TypeError) as error:
            raise SelectedToolGroundError(
                "compatibility rules must use the qualified structured type"
            ) from error
        try:
            ground = CanonicalFamilyGround.from_path(
                Path(path), compatibility_rules=ordered_rules
            )
        except CanonicalFamilyGroundError as error:
            raise SelectedToolGroundError(str(error)) from error
        return cls(
            ground=ground,
            compatibility_rules=ordered_rules,
            byte_cap=byte_cap,
        )

    def _selection(
        self, selected_tool_names: Sequence[str]
    ) -> tuple[CanonicalContract, ...]:
        if isinstance(selected_tool_names, (str, bytes)):
            raise SelectedToolGroundError(
                "selection must contain between 1 and 16 registered tools"
            )
        try:
            names = tuple(selected_tool_names)
        except TypeError as error:
            raise SelectedToolGroundError(
                "selection must contain between 1 and 16 registered tools"
            ) from error
        if not 1 <= len(names) <= SELECTED_TOOL_MAX_COUNT:
            raise SelectedToolGroundError(
                "selection must contain between 1 and 16 registered tools"
            )
        if any(
            not isinstance(name, str) or not name or not name.isascii()
            for name in names
        ):
            raise SelectedToolGroundError(
                "selection must contain ASCII registered tool names"
            )
        if len(names) != len(set(names)):
            raise SelectedToolGroundError("selection contains a duplicate tool")
        unknown = tuple(name for name in names if name not in self._contracts_by_tool)
        if unknown:
            raise SelectedToolGroundError(
                "selection contains an unknown registered tool: " + ", ".join(unknown)
            )
        return tuple(self._contracts_by_tool[name] for name in names)

    def _render(self, contracts: Sequence[CanonicalContract]) -> str:
        lines = [
            "SELECTED-TOOL DECISION CARDS",
            "Use only the speech and same-core observation to decide the requested actions.",
            "Return [] only when no registered action is requested.",
            "Otherwise emit one exact registered call per requested action and preserve their spoken order.",
            "A final correction supersedes an earlier value or action.",
            "Preserve distinct simultaneous intents; do not merge or invent calls.",
            "Never add an action or argument value supplied only by these cards.",
            "A declared public default may complete an explicitly requested operation when speech omits that argument.",
            "A default never proves that the operation itself was requested; invent no other task value.",
            "Selected-sibling contrast meanings:",
        ]
        lines.extend(
            f"- {contract.tool_name}: {contract.operation}" for contract in contracts
        )
        lines.append("Canonicalization rules:")
        applicable_canonicalizers = {
            name for contract in contracts for name in contract.canonicalization_rules
        }
        lines.extend(
            f"- {name}: {description}"
            for name, description in self._canonicalizers.items()
            if name in applicable_canonicalizers
        )
        lines.append(
            "Qualified compatibility forms are listed only when an aggregate-qualified rule applies."
        )

        for contract in contracts:
            lines.extend(
                (
                    "",
                    f"Exact tool: {contract.tool_name}",
                    f"Family: {self._family_labels[contract.family_tag]} ({contract.family_tag})",
                    f"Operation: {contract.operation}",
                    "Key types: "
                    + (
                        "; ".join(f"{key}: {kind}" for key, kind in contract.types)
                        or "(none)"
                    ),
                    "Legal key sets: "
                    + " | ".join(
                        _render_keys(skeleton)
                        for skeleton in contract.legal_key_skeletons
                    ),
                    f"Constraints: {contract.constraints or '(none)'}",
                    _render_role("Required keys", contract.required_keys),
                    _render_role("Optional keys", contract.optional_keys),
                    _render_role("Conditional keys", contract.conditional_keys),
                    _render_role("Forbidden keys", contract.forbidden_keys),
                    _render_role("Canonical key order", contract.ordered_keys),
                    "Declared defaults for omission semantics: "
                    + (contract.defaults or "(none)"),
                    "Omission rules: " + " ".join(contract.omission_rules),
                    "Applicable canonicalizers: "
                    + (
                        ", ".join(contract.canonicalization_rules)
                        if contract.canonicalization_rules
                        else "(none)"
                    ),
                )
            )
            for rule in self._rules_by_tool.get(contract.tool_name, ()):
                forms = (
                    "; ".join(
                        f"{key}: {_COMPATIBILITY_GUIDANCE[form]}"
                        for key, form in rule.value_forms
                    )
                    or "public declared types"
                )
                lines.append(
                    "Qualified compatibility for "
                    f"{_render_keys(rule.legal_argument_key_set)}: {forms}."
                )

        rendered = "\n".join(lines) + "\n"
        if not rendered.isascii():
            raise SelectedToolGroundError("rendered selected-tool ground is not ASCII")
        if len(rendered.encode("ascii")) > self.byte_cap:
            raise SelectedToolGroundError(
                "rendered selected-tool ground exceeds byte cap"
            )
        return rendered

    def _response_format(
        self, contracts: Sequence[CanonicalContract]
    ) -> dict[str, object]:
        rows: list[dict[str, str]] = []
        cards: list[ToolSemanticCard] = []
        for contract in contracts:
            signature = (
                contract.tool_name
                + "("
                + ", ".join(f"{key}: {kind}" for key, kind in contract.types)
                + ")"
            )
            constraints = (
                "" if _is_no_declaration(contract.constraints) else contract.constraints
            )
            rows.append(
                {
                    "tool_name": contract.tool_name,
                    "signature": signature,
                    "argument_constraints": constraints,
                }
            )
            cards.append(
                ToolSemanticCard(
                    tool_name=contract.tool_name,
                    choose_semantics=contract.operation,
                    avoid_semantics="Choose only for its exact operation meaning.",
                    signature=signature,
                    constraints=constraints,
                    legal_argument_key_sets=contract.legal_key_skeletons,
                    compatibility_rules=self._rules_by_tool.get(contract.tool_name, ()),
                    role_guidance=(),
                    examples=(),
                    text="Selected public contract.",
                )
            )
        return audio2tool_call_array_response_format(
            rows,
            cards,
            schema_name="audio2tool_selected_calls",
            min_calls=0,
            max_calls=SELECTED_TOOL_MAX_CALLS,
        )

    def build(self, selected_tool_names: Sequence[str]) -> SelectedToolDecisionPacket:
        """Render one deterministic packet for an ordered unique selection."""

        contracts = self._selection(selected_tool_names)
        names = tuple(contract.tool_name for contract in contracts)
        rendered = self._render(contracts)
        response_format = self._response_format(contracts)
        selected_rules = tuple(
            rule
            for contract in contracts
            for rule in self._rules_by_tool.get(contract.tool_name, ())
        )
        report = {
            "corpus_sha256": self.corpus_sha256,
            "compatibility_sha256": self.compatibility_sha256,
            "registered_family_count": len(self._ground.family_tags),
            "registered_tool_count": len(self._ground.tool_names),
            "qualified_compatibility_rule_count": len(self._compatibility_rules),
            "selected_tool_count": len(contracts),
            "selected_family_count": len({item.family_tag for item in contracts}),
            "selected_legal_skeleton_count": sum(
                len(item.legal_key_skeletons) for item in contracts
            ),
            "selected_compatibility_rule_count": len(selected_rules),
            "rendered_ascii_bytes": len(rendered.encode("ascii")),
            "rendered_byte_cap": self.byte_cap,
            "construction_examples_rendered": 0,
            "sample_ids_rendered": 0,
            "source_utterances_rendered": 0,
            "reference_or_gold_labels_rendered": 0,
            "construction_concrete_values_rendered": 0,
        }
        return SelectedToolDecisionPacket(
            selected_tool_names=names,
            text=rendered,
            text_sha256=hashlib.sha256(rendered.encode("ascii")).hexdigest(),
            response_format=response_format,
            response_format_sha256=hashlib.sha256(
                _canonical_json_bytes(response_format)
            ).hexdigest(),
            report=report,
        )


__all__ = [
    "SELECTED_TOOL_GROUND_ASCII_BYTE_CAP",
    "SELECTED_TOOL_MAX_CALLS",
    "SELECTED_TOOL_MAX_COUNT",
    "SelectedToolDecisionGround",
    "SelectedToolDecisionPacket",
    "SelectedToolGroundError",
]
