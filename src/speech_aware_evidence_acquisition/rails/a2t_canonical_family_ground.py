"""Render a value-safe canonical Audio2Tool ground one family at a time.

The renderer is a thin model-facing view over the frozen G5 contract corpus.
It adds no examples, evaluation rows, task values, retrieval, ranking, or learned
policy.  Every family is paired with a strict response schema that permits an
empty array when the speech requests no action from that family.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``CanonicalFamilyGround.render_family`` is catalog id
``saea-tool-a2t-canonical-family-ground-v1`` on the ``SUPPLY`` axis, scope
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

from .a2t_executable_semantic_cards import CompatibilityRule, ToolSemanticCard
from .a2t_response_schema import audio2tool_call_array_response_format
from .probes.a2t_g6_corpus_renderer import G6CorpusRenderer


FAMILY_GROUND_ASCII_BYTE_CAP = 18_432
REQUIRED_COMPATIBILITY_RULE_COUNT = 43
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


class CanonicalFamilyGroundError(ValueError):
    """The frozen action corpus cannot form a canonical family-local ground."""


@dataclass(frozen=True)
class CanonicalContract:
    """One frozen public action contract used by a family-local model contact."""

    contract_id: str
    family_tag: str
    tool_name: str
    operation: str
    types: tuple[tuple[str, str], ...]
    constraints: str
    legal_key_skeletons: tuple[tuple[str, ...], ...]
    required_keys: tuple[str, ...]
    optional_keys: tuple[str, ...]
    conditional_keys: tuple[str, ...]
    forbidden_keys: tuple[str, ...]
    ordered_keys: tuple[str, ...]
    defaults: str
    omission_rules: tuple[str, ...]
    canonicalization_rules: tuple[str, ...]


def _text(value: object, *, field: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not allow_empty):
        raise CanonicalFamilyGroundError(f"{field} must be text")
    if not value.isascii():
        raise CanonicalFamilyGroundError(f"{field} must be ASCII English")
    return value


def _text_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise CanonicalFamilyGroundError(f"{field} must be a list")
    result = tuple(_text(item, field=field) for item in value)
    if len(result) != len(set(result)):
        raise CanonicalFamilyGroundError(f"{field} must not contain duplicates")
    return result


def _types(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise CanonicalFamilyGroundError("contract types must be a list")
    result: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            raise CanonicalFamilyGroundError("contract type entry is malformed")
        result.append(
            (
                _text(item[0], field="argument key"),
                _text(item[1], field="argument type"),
            )
        )
    if len({key for key, _kind in result}) != len(result):
        raise CanonicalFamilyGroundError("contract argument keys are duplicated")
    return tuple(result)


def _skeletons(
    value: object, *, known_keys: frozenset[str]
) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, list) or not value:
        raise CanonicalFamilyGroundError("legal key skeletons must be a non-empty list")
    result: list[tuple[str, ...]] = []
    for item in value:
        if not isinstance(item, list):
            raise CanonicalFamilyGroundError("legal key skeleton is malformed")
        keys = tuple(_text(key, field="legal argument key") for key in item)
        if len(keys) != len(set(keys)) or not set(keys).issubset(known_keys):
            raise CanonicalFamilyGroundError(
                "legal key skeleton is outside declared types"
            )
        result.append(keys)
    if len(result) != len(set(result)):
        raise CanonicalFamilyGroundError("legal key skeletons are duplicated")
    return tuple(result)


def _load_contract(row: object) -> CanonicalContract:
    if not isinstance(row, Mapping):
        raise CanonicalFamilyGroundError("contract row is malformed")
    typed = _types(row.get("types"))
    known_keys = frozenset(key for key, _kind in typed)
    contract = CanonicalContract(
        contract_id=_text(row.get("contract_id"), field="contract id"),
        family_tag=_text(row.get("family_tag"), field="family tag"),
        tool_name=_text(row.get("tool_name"), field="tool name"),
        operation=_text(row.get("operation"), field="operation"),
        types=typed,
        constraints=_text(
            row.get("constraints"), field="constraints", allow_empty=True
        ),
        legal_key_skeletons=_skeletons(
            row.get("legal_key_skeletons"), known_keys=known_keys
        ),
        required_keys=_text_tuple(row.get("required_keys"), field="required keys"),
        optional_keys=_text_tuple(row.get("optional_keys"), field="optional keys"),
        conditional_keys=_text_tuple(
            row.get("conditional_keys"), field="conditional keys"
        ),
        forbidden_keys=_text_tuple(row.get("forbidden_keys"), field="forbidden keys"),
        ordered_keys=_text_tuple(row.get("ordered_keys"), field="ordered keys"),
        defaults=_text(row.get("defaults"), field="defaults", allow_empty=True),
        omission_rules=_text_tuple(row.get("omission_rules"), field="omission rules"),
        canonicalization_rules=_text_tuple(
            row.get("canonicalization_rules"), field="canonicalization rules"
        ),
    )
    declared = (
        set(contract.required_keys)
        | set(contract.optional_keys)
        | set(contract.conditional_keys)
        | set(contract.forbidden_keys)
        | set(contract.ordered_keys)
    )
    if not declared.issubset(known_keys):
        raise CanonicalFamilyGroundError(
            "contract key roles are outside declared types"
        )
    return contract


def _render_keys(keys: Sequence[str]) -> str:
    return "{" + ", ".join(keys) + "}"


def _render_role(label: str, keys: Sequence[str]) -> str:
    return f"{label}: {', '.join(keys) if keys else '(none)'}"


def _is_no_declaration(value: str) -> bool:
    normalized = value.strip().casefold()
    return normalized in _NO_DECLARATION or normalized.startswith("no public ")


class CanonicalFamilyGround:
    """Validated family-local canonical cards and strict response schemas."""

    def __init__(
        self,
        *,
        corpus_sha256: str,
        family_tags: Sequence[str],
        labels: Mapping[str, str],
        contracts_by_family: Mapping[str, tuple[CanonicalContract, ...]],
        canonicalizers: Mapping[str, str],
        compatibility_rules_by_tool: Mapping[str, tuple[CompatibilityRule, ...]],
    ) -> None:
        self.corpus_sha256 = corpus_sha256
        self.family_tags = tuple(family_tags)
        self._labels = dict(labels)
        self._contracts_by_family = dict(contracts_by_family)
        self._canonicalizers = dict(canonicalizers)
        self._compatibility_rules_by_tool = dict(compatibility_rules_by_tool)
        self.tool_names = tuple(
            contract.tool_name
            for tag in self.family_tags
            for contract in self._contracts_by_family[tag]
        )

    @property
    def contracts_by_tool(self) -> dict[str, CanonicalContract]:
        """Return a copy of the validated public contracts keyed by tool name."""

        return {
            contract.tool_name: contract
            for family_tag in self.family_tags
            for contract in self._contracts_by_family[family_tag]
        }

    @property
    def canonicalizers(self) -> dict[str, str]:
        """Return a copy of the validated public canonicalizer descriptions."""

        return dict(self._canonicalizers)

    @classmethod
    def from_path(
        cls,
        path: Path,
        *,
        compatibility_rules: Sequence[CompatibilityRule],
    ) -> "CanonicalFamilyGround":
        """Load the hash-stable 28-family, 152-tool contract corpus."""

        source = Path(path)
        validated = G6CorpusRenderer.from_path(source)
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != validated.corpus_sha256:
            raise CanonicalFamilyGroundError("corpus changed during validation")
        try:
            document = json.loads(raw.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CanonicalFamilyGroundError("corpus must be ASCII JSON") from error
        taxonomy = document.get("taxonomy")
        rows = document.get("contracts")
        canonicalizers = document.get("canonicalizers")
        if not isinstance(taxonomy, list) or not isinstance(rows, list):
            raise CanonicalFamilyGroundError("corpus collections are malformed")
        if not isinstance(canonicalizers, Mapping):
            raise CanonicalFamilyGroundError("canonicalizers are malformed")
        labels = {
            _text(row.get("tag"), field="family tag"): _text(
                row.get("label"), field="family label"
            )
            for row in taxonomy
            if isinstance(row, Mapping)
        }
        if tuple(labels) != validated.family_tags:
            raise CanonicalFamilyGroundError("family taxonomy drift")
        parsed = tuple(_load_contract(row) for row in rows)
        grouped = {
            tag: tuple(contract for contract in parsed if contract.family_tag == tag)
            for tag in validated.family_tags
        }
        if any(not contracts for contracts in grouped.values()):
            raise CanonicalFamilyGroundError("family has no contracts")
        if (
            tuple(
                contract.tool_name
                for tag in validated.family_tags
                for contract in grouped[tag]
            )
            != validated.tool_names
        ):
            raise CanonicalFamilyGroundError("contract ordering or identity drift")
        canonicalizer_text = {
            _text(key, field="canonicalizer name"): _text(
                value, field="canonicalizer description"
            )
            for key, value in canonicalizers.items()
        }
        if len(compatibility_rules) != REQUIRED_COMPATIBILITY_RULE_COUNT:
            raise CanonicalFamilyGroundError(
                "exactly 43 qualified compatibility rules are required"
            )
        contracts_by_tool = {contract.tool_name: contract for contract in parsed}
        rules_by_tool: dict[str, list[CompatibilityRule]] = {}
        seen_rules: set[tuple[str, tuple[str, ...]]] = set()
        for rule in compatibility_rules:
            if not isinstance(rule, CompatibilityRule):
                raise CanonicalFamilyGroundError(
                    "compatibility rules must use the qualified structured type"
                )
            contract = contracts_by_tool.get(rule.tool_name)
            identity = (rule.tool_name, tuple(sorted(rule.legal_argument_key_set)))
            if contract is None or frozenset(rule.legal_argument_key_set) not in {
                frozenset(skeleton) for skeleton in contract.legal_key_skeletons
            }:
                raise CanonicalFamilyGroundError(
                    "compatibility rule is outside the frozen family contracts"
                )
            if identity in seen_rules:
                raise CanonicalFamilyGroundError("compatibility rules are duplicated")
            if rule.construction_support_count < 2 or any(
                key not in rule.legal_argument_key_set
                or form not in _COMPATIBILITY_GUIDANCE
                for key, form in rule.value_forms
            ):
                raise CanonicalFamilyGroundError("compatibility rule is malformed")
            seen_rules.add(identity)
            rules_by_tool.setdefault(rule.tool_name, []).append(rule)
        return cls(
            corpus_sha256=validated.corpus_sha256,
            family_tags=validated.family_tags,
            labels=labels,
            contracts_by_family=grouped,
            canonicalizers=canonicalizer_text,
            compatibility_rules_by_tool={
                tool_name: tuple(rules) for tool_name, rules in rules_by_tool.items()
            },
        )

    def _family(self, family_tag: str) -> tuple[CanonicalContract, ...]:
        try:
            return self._contracts_by_family[family_tag]
        except KeyError as error:
            raise CanonicalFamilyGroundError("unknown family") from error

    def render_family(self, family_tag: str) -> str:
        """Render one example-free canonical action card for a model contact."""

        contracts = self._family(family_tag)
        family_tools = tuple(contract.tool_name for contract in contracts)
        shared_omission_rules = (
            contracts[0].omission_rules
            if all(
                contract.omission_rules == contracts[0].omission_rules
                for contract in contracts
            )
            else ()
        )
        shared_canonicalization_rules = (
            contracts[0].canonicalization_rules
            if all(
                contract.canonicalization_rules == contracts[0].canonicalization_rules
                for contract in contracts
            )
            else ()
        )
        lines = [
            "CANONICAL FAMILY ACTION GROUND",
            f"Family: {self._labels[family_tag]} ({family_tag})",
            "Use only the speech and same-core observation to decide whether this family applies.",
            "Return [] when no operation from this family is requested.",
            "Otherwise return one exact registered call per requested family action in spoken order.",
            "Never add an action or argument value supplied only by this reference.",
            "A final correction supersedes the earlier value or action.",
            "Preserve distinct simultaneous intents; do not merge or invent calls.",
            "A public default may complete an explicitly requested operation when speech omits that argument.",
            "A default never proves that the operation itself was requested; never invent any other task value.",
            "Family tools: " + ", ".join(family_tools),
            "Sibling contrast: compare every Choose when meaning and reject shared nouns alone.",
            "Canonicalization rules:",
        ]
        lines.extend(
            f"- {name}: {description}"
            for name, description in self._canonicalizers.items()
        )
        lines.append("Compatibility forms: listed per tool when aggregate-qualified.")
        if shared_omission_rules:
            lines.append("Omission rules: " + " ".join(shared_omission_rules))
        if shared_canonicalization_rules:
            lines.append(
                "Applicable canonicalizers: " + ", ".join(shared_canonicalization_rules)
            )
        for contract in contracts:
            lines.extend(
                (
                    "",
                    f"Contract: {contract.contract_id}",
                    f"Exact tool: {contract.tool_name}",
                    f"Choose when: {contract.operation}",
                    "Key types: "
                    + (
                        "; ".join(f"{key}: {kind}" for key, kind in contract.types)
                        or "(none)"
                    ),
                    "Legal key sets: "
                    + " | ".join(
                        _render_keys(keys) for keys in contract.legal_key_skeletons
                    ),
                    f"Constraints: {contract.constraints or '(none)'}",
                    _render_role("Required keys", contract.required_keys),
                    _render_role("Optional keys", contract.optional_keys),
                    _render_role("Conditional keys", contract.conditional_keys),
                    _render_role("Forbidden keys", contract.forbidden_keys),
                    _render_role("Canonical key order", contract.ordered_keys),
                    f"Declared defaults for omission semantics: {contract.defaults or '(none)'}",
                    *(
                        ()
                        if shared_omission_rules
                        else ("Omission rules: " + " ".join(contract.omission_rules),)
                    ),
                    *(
                        ()
                        if shared_canonicalization_rules
                        else (
                            "Applicable canonicalizers: "
                            + (
                                ", ".join(contract.canonicalization_rules)
                                if contract.canonicalization_rules
                                else "(none)"
                            ),
                        )
                    ),
                )
            )
            for rule in self._compatibility_rules_by_tool.get(contract.tool_name, ()):
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
            raise CanonicalFamilyGroundError("rendered family ground is not ASCII")
        if len(rendered.encode("ascii")) > FAMILY_GROUND_ASCII_BYTE_CAP:
            raise CanonicalFamilyGroundError("rendered family ground exceeds byte cap")
        return rendered

    def response_format(
        self,
        family_tag: str,
        *,
        max_calls: int = 4,
    ) -> dict[str, object]:
        """Compile the exact family contracts into a strict optional-call schema."""

        contracts = self._family(family_tag)
        rows = []
        cards = []
        for contract in contracts:
            signature = (
                contract.tool_name
                + "("
                + ", ".join(f"{key}: {kind}" for key, kind in contract.types)
                + ")"
            )
            constraint_text = (
                "" if _is_no_declaration(contract.constraints) else contract.constraints
            )
            rows.append(
                {
                    "tool_name": contract.tool_name,
                    "signature": signature,
                    "argument_constraints": constraint_text,
                }
            )
            cards.append(
                ToolSemanticCard(
                    tool_name=contract.tool_name,
                    choose_semantics=contract.operation,
                    avoid_semantics="Use only for its exact operation meaning.",
                    signature=signature,
                    constraints=constraint_text,
                    legal_argument_key_sets=contract.legal_key_skeletons,
                    compatibility_rules=self._compatibility_rules_by_tool.get(
                        contract.tool_name, ()
                    ),
                    role_guidance=(),
                    examples=(),
                    text="Canonical family-local contract.",
                )
            )
        return audio2tool_call_array_response_format(
            rows,
            cards,
            schema_name="audio2tool_family_calls",
            min_calls=0,
            max_calls=max_calls,
        )


__all__ = [
    "FAMILY_GROUND_ASCII_BYTE_CAP",
    "REQUIRED_COMPATIBILITY_RULE_COUNT",
    "CanonicalContract",
    "CanonicalFamilyGround",
    "CanonicalFamilyGroundError",
]
