"""Build deterministic, executable Audio2Tool semantic cards without labels.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``build_executable_semantic_card_corpus`` is catalog id
``saea-tool-a2t-executable-semantic-cards-v1`` on the ``SUPPLY`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping, Sequence

from .knowledge_build_a2t import A2tKbRow

REQUIRED_TOOL_COUNT = 152
DEFAULT_MAX_UTF8_BYTES = 524_288
SYNTHETIC_LITERAL_PREFIX = "SYNTHETIC_"


class ExecutableSemanticCardError(RuntimeError):
    """The semantic-card builder refused incomplete or unsafe input."""


@dataclass(frozen=True)
class CompatibilityRule:
    """One aggregate, training-supported schema compatibility rule.

    The rule names keys and value-form classes only. It has no field capable of
    carrying a source utterance, sample identity, or concrete argument value.
    """

    tool_name: str
    legal_argument_key_set: tuple[str, ...]
    value_forms: tuple[tuple[str, str], ...]
    construction_support_count: int


@dataclass(frozen=True)
class ToolSemanticCard:
    """One registry-bound executable tool card."""

    tool_name: str
    choose_semantics: str
    avoid_semantics: str
    signature: str
    constraints: str
    legal_argument_key_sets: tuple[tuple[str, ...], ...]
    compatibility_rules: tuple[CompatibilityRule, ...]
    role_guidance: tuple[str, ...]
    examples: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class TaskSemanticCard:
    """One task-wide execution rule independent of any evaluation item."""

    card_id: str
    text: str


@dataclass(frozen=True)
class ExecutableSemanticCardCorpus:
    """Deterministic model-facing corpus and aggregate-only build report."""

    text: str
    sha256: str
    tool_cards: tuple[ToolSemanticCard, ...]
    task_cards: tuple[TaskSemanticCard, ...]
    report: Mapping[str, object]

    @property
    def cards_by_name(self) -> dict[str, ToolSemanticCard]:
        """Return the complete card map keyed by exact registry name."""

        return {card.tool_name: card for card in self.tool_cards}


@dataclass(frozen=True)
class _SignatureArgument:
    key: str
    type_name: str
    optional: bool


@dataclass(frozen=True)
class _RegistryTool:
    name: str
    domain: str
    category: str
    signature: str
    description: str
    constraints: str
    arguments: tuple[_SignatureArgument, ...]


_TASK_CARDS = (
    TaskSemanticCard(
        card_id="multi-call-ordering",
        text=(
            "For multiple supported actions, emit one call per action and preserve the "
            "spoken action order. Do not merge distinct actions or add an unrequested call."
        ),
    ),
    TaskSemanticCard(
        card_id="correction-resolution",
        text=(
            "A final correction supersedes the earlier value or action. Emit only the "
            "corrected call state and do not retain a superseded argument."
        ),
    ),
    TaskSemanticCard(
        card_id="implicit-end-state-resolution",
        text=(
            "For an implicit request, select the operation that reaches the desired end state. "
            "Do not invent an argument value that was not spoken or observed by the same core."
        ),
    ),
    TaskSemanticCard(
        card_id="multiturn-carryover",
        text=(
            "Carry forward only relevant facts explicitly established in earlier user turns, "
            "then apply the final user request. Never use future turns or invented assistant facts."
        ),
    ),
)

_HEADER = """AUDIO2TOOL EXECUTABLE SEMANTIC-CARD CORPUS

OUTPUT CONTRACT
Return only one JSON array. Every element must be exactly {"name":"registeredToolName","arguments":{...}}. Use an exact registered tool name, an exact legal argument-key set from its card, and JSON values with the public types and constraints. Copy task values only from the speech or its same-core observation. Never copy a value from a synthetic example.

CARD USE
Choose a tool by its operation meaning. Use Avoid guidance to reject nearby tools that share nouns but perform a different operation. The construction summaries contribute only observed legal argument-key sets; no source utterance, sample identity, transcript, call label, or argument value is available to this builder.
"""

_COMPATIBILITY_VALUE_FORM_TYPES: Mapping[str, str] = {
    "boolean": "Boolean",
    "boolean-string": "String",
    "integer": "Int",
    "list": "List<String>",
    "map": "Map",
    "nullable-string": "String",
    "number": "Float",
    "string": "String",
}

_COMPATIBILITY_VALUE_FORM_GUIDANCE: Mapping[str, str] = {
    "boolean": "use a JSON Boolean",
    "boolean-string": "accepts a Boolean lexical form encoded as a JSON string",
    "integer": "use a JSON integer",
    "list": "use a JSON array of artificial strings",
    "map": "use a JSON object with artificial keys and values",
    "nullable-string": "accepts JSON null or an artificial JSON string",
    "number": "use a JSON number",
    "string": "use an artificial JSON string",
}


def _required_ascii(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutableSemanticCardError(f"registry {field} must be non-empty text")
    text = value.strip()
    if not text.isascii():
        raise ExecutableSemanticCardError(
            f"registry {field} must be ASCII English before model use"
        )
    return text


def _optional_ascii(value: object, *, field: str) -> str:
    if value is None or value == "":
        return ""
    if not isinstance(value, str) or not value.isascii():
        raise ExecutableSemanticCardError(
            f"registry {field} must be ASCII English before model use"
        )
    return value.strip()


def _split_arguments(text: str) -> tuple[str, ...]:
    if not text.strip():
        return ()
    parts: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(text):
        if character in "<[{(":
            depth += 1
        elif character in ">]})":
            depth -= 1
            if depth < 0:
                raise ExecutableSemanticCardError("registry signature brackets are malformed")
        elif character == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    if depth != 0:
        raise ExecutableSemanticCardError("registry signature brackets are malformed")
    parts.append(text[start:].strip())
    return tuple(parts)


def _parse_signature(name: str, signature: str) -> tuple[_SignatureArgument, ...]:
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\((.*)\)", signature)
    if match is None or match.group(1) != name:
        raise ExecutableSemanticCardError(
            f"registry signature for {name!r} must start with its exact tool name"
        )
    arguments: list[_SignatureArgument] = []
    seen: set[str] = set()
    for raw in _split_arguments(match.group(2)):
        part = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)", raw)
        if part is None:
            raise ExecutableSemanticCardError(
                f"registry signature for {name!r} has a malformed argument"
            )
        key = part.group(1)
        type_name = part.group(2).strip()
        optional = type_name.endswith("?")
        if optional:
            type_name = type_name[:-1].strip()
        if not type_name or key in seen or not type_name.isascii():
            raise ExecutableSemanticCardError(
                f"registry signature for {name!r} repeats or omits an argument"
            )
        seen.add(key)
        arguments.append(
            _SignatureArgument(key=key, type_name=type_name, optional=optional)
        )
    return tuple(arguments)


def _load_registry(
    registry_rows: Sequence[Mapping[str, str]],
) -> dict[str, _RegistryTool]:
    registry: dict[str, _RegistryTool] = {}
    for raw in registry_rows:
        name = _required_ascii(raw.get("tool_name"), field="tool_name")
        if name in registry:
            raise ExecutableSemanticCardError(f"duplicate registry tool {name!r}")
        signature = _required_ascii(raw.get("signature"), field=f"{name}.signature")
        registry[name] = _RegistryTool(
            name=name,
            domain=_required_ascii(raw.get("domain"), field=f"{name}.domain"),
            category=_required_ascii(raw.get("category"), field=f"{name}.category"),
            signature=signature,
            description=_required_ascii(
                raw.get("description"), field=f"{name}.description"
            ),
            constraints=_optional_ascii(
                raw.get("argument_constraints"), field=f"{name}.argument_constraints"
            ),
            arguments=_parse_signature(name, signature),
        )
    if len(registry) != REQUIRED_TOOL_COUNT:
        raise ExecutableSemanticCardError(
            f"registry must contain exactly {REQUIRED_TOOL_COUNT} distinct tools"
        )
    return registry


def _load_compatibility_rules(
    raw_rules: Sequence[CompatibilityRule],
    registry: Mapping[str, _RegistryTool],
) -> dict[str, tuple[CompatibilityRule, ...]]:
    by_tool: dict[str, list[CompatibilityRule]] = defaultdict(list)
    seen: set[tuple[str, frozenset[str]]] = set()
    for raw in raw_rules:
        if not isinstance(raw, CompatibilityRule):
            raise ExecutableSemanticCardError(
                "compatibility rules must use the structured CompatibilityRule type"
            )
        tool_name = raw.tool_name
        if tool_name not in registry:
            raise ExecutableSemanticCardError(
                f"compatibility tool {tool_name!r} is outside the registry"
            )
        if (
            isinstance(raw.construction_support_count, bool)
            or not isinstance(raw.construction_support_count, int)
            or raw.construction_support_count < 2
        ):
            raise ExecutableSemanticCardError(
                "compatibility rules require aggregate support from at least two "
                "decontaminated construction units"
            )
        keys = raw.legal_argument_key_set
        if (
            not isinstance(keys, tuple)
            or not keys
            or len(keys) != len(set(keys))
            or any(not isinstance(key, str) or not key or not key.isascii() for key in keys)
        ):
            raise ExecutableSemanticCardError(
                "compatibility legal argument-key set must be non-empty unique ASCII keys"
            )
        forms: dict[str, str] = {}
        for item in raw.value_forms:
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], str)
                or item[0] not in keys
                or item[0] in forms
                or item[1] not in _COMPATIBILITY_VALUE_FORM_TYPES
            ):
                raise ExecutableSemanticCardError(
                    "compatibility value form must name one legal key and one registered "
                    "value form"
                )
            forms[item[0]] = item[1]
        public_keys = {argument.key for argument in registry[tool_name].arguments}
        uncovered_extensions = sorted(set(keys) - public_keys - set(forms))
        if uncovered_extensions:
            raise ExecutableSemanticCardError(
                "compatibility keys outside the public signature require explicit value "
                f"forms: {uncovered_extensions!r}"
            )
        identity = (tool_name, frozenset(keys))
        if identity in seen:
            raise ExecutableSemanticCardError(
                f"duplicate compatibility key skeleton for {tool_name!r}"
            )
        seen.add(identity)
        canonical = CompatibilityRule(
            tool_name=tool_name,
            legal_argument_key_set=tuple(sorted(keys)),
            value_forms=tuple(sorted(forms.items())),
            construction_support_count=raw.construction_support_count,
        )
        by_tool[tool_name].append(canonical)
    return {
        name: tuple(
            sorted(
                rules,
                key=lambda rule: (
                    len(rule.legal_argument_key_set),
                    rule.legal_argument_key_set,
                    rule.value_forms,
                ),
            )
        )
        for name, rules in sorted(by_tool.items())
    }


def _construction_patterns(
    construction_rows: Sequence[A2tKbRow],
    registry: Mapping[str, _RegistryTool],
    compatibility_rules: Mapping[str, tuple[CompatibilityRule, ...]],
) -> dict[str, set[frozenset[str]]]:
    patterns: dict[str, set[frozenset[str]]] = defaultdict(set)
    for row in construction_rows:
        tool_name = row.tool_name
        if tool_name not in registry:
            raise ExecutableSemanticCardError(
                f"construction tool {tool_name!r} is outside the registry"
            )
        keys = row.arg_signature
        if (
            not isinstance(keys, tuple)
            or len(keys) != len(set(keys))
            or any(not isinstance(key, str) or not key or not key.isascii() for key in keys)
        ):
            raise ExecutableSemanticCardError(
                f"construction summary for {tool_name!r} has invalid argument keys"
            )
        signature_keys = {argument.key for argument in registry[tool_name].arguments}
        unknown = sorted(set(keys) - signature_keys)
        compatible_skeletons = {
            frozenset(rule.legal_argument_key_set)
            for rule in compatibility_rules.get(tool_name, ())
        }
        if unknown and frozenset(keys) not in compatible_skeletons:
            raise ExecutableSemanticCardError(
                f"construction argument keys {unknown!r} are outside its signature "
                f"for {tool_name!r}"
            )
        patterns[tool_name].add(frozenset(keys))
    return patterns


def _legal_key_sets(
    tool: _RegistryTool,
    observed: set[frozenset[str]] | None,
    compatibility_rules: Sequence[CompatibilityRule],
) -> tuple[tuple[str, ...], ...]:
    if observed:
        candidates = set(observed)
    else:
        required = frozenset(
            argument.key for argument in tool.arguments if not argument.optional
        )
        complete = frozenset(argument.key for argument in tool.arguments)
        candidates = {required, complete}
    candidates.update(
        frozenset(rule.legal_argument_key_set) for rule in compatibility_rules
    )
    return tuple(
        tuple(sorted(keys))
        for keys in sorted(candidates, key=lambda item: (len(item), sorted(item)))
    )


def _constraint_map(tool: _RegistryTool) -> tuple[dict[str, str], int]:
    if not tool.constraints:
        return {}, 0
    constraints = {
        match.group(1): match.group(2).strip()
        for match in re.finditer(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\[([^\]]+)\]",
            tool.constraints,
        )
    }
    signature_keys = {argument.key for argument in tool.arguments}
    unknown = sorted(set(constraints) - signature_keys)
    if unknown:
        raise ExecutableSemanticCardError(
            f"registry constraints for {tool.name!r} name unknown keys {unknown!r}"
        )
    return constraints, int(not constraints)


def _humanize_key(key: str) -> str:
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key).replace("_", " ")
    words = expanded.lower().split()
    return " ".join("identifier" if word == "id" else word for word in words)


def _numeric_range(constraint: str) -> tuple[float, float] | None:
    match = re.fullmatch(
        r"\s*(-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+))\s*-\s*"
        r"(-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+))\s*",
        constraint,
    )
    if match is None:
        return None
    return float(match.group(1)), float(match.group(2))


def _synthetic_value(
    tool: _RegistryTool,
    argument: _SignatureArgument,
    constraint: str | None,
    compatibility_form: str | None = None,
) -> tuple[object, bool]:
    """Return one type-correct value and whether it uses a public constraint literal."""

    type_lower = argument.type_name.lower()
    if compatibility_form == "boolean-string":
        return "True", True
    if compatibility_form == "nullable-string":
        return None, True
    if constraint:
        range_value = _numeric_range(constraint)
        if range_value is not None:
            low, high = range_value
            midpoint = (low + high) / 2
            if type_lower in {"int", "integer"}:
                return int(midpoint), True
            if type_lower in {"float", "number", "double"}:
                return float(midpoint), True
            return str(int(midpoint)).zfill(4), True
        choices = tuple(part.strip() for part in constraint.split(",") if part.strip())
        if choices:
            selected = choices[0]
            if type_lower.startswith("list") or type_lower.endswith("[]"):
                return [selected], True
            if type_lower in {"boolean", "bool"} and selected in {"True", "False"}:
                return selected == "True", True
            if type_lower in {"int", "integer"} and re.fullmatch(r"-?[0-9]+", selected):
                return int(selected), True
            if type_lower in {"float", "number", "double"}:
                try:
                    return float(selected), True
                except ValueError:
                    pass
            return selected, True
    marker = (
        f"{SYNTHETIC_LITERAL_PREFIX}{tool.name}_{argument.key}_001".upper()
    )
    if type_lower in {"boolean", "bool"}:
        return False, False
    if type_lower in {"int", "integer"}:
        return 7, False
    if type_lower in {"float", "number", "double"}:
        return 7.5, False
    if type_lower.startswith("list") or type_lower.endswith("[]"):
        return [marker], False
    if type_lower.startswith("map") or type_lower in {"object", "dict"}:
        return {"syntheticKey": marker}, False
    return marker, False


def _constraint_accepts(value: object, argument: _SignatureArgument, text: str) -> bool:
    range_value = _numeric_range(text)
    type_lower = argument.type_name.lower()
    if range_value is not None:
        low, high = range_value
        if type_lower in {"int", "integer", "float", "number", "double"}:
            return isinstance(value, (int, float)) and not isinstance(value, bool) and low <= value <= high
        return isinstance(value, str) and value.isdigit() and low <= int(value) <= high
    choices = tuple(part.strip() for part in text.split(",") if part.strip())
    if type_lower.startswith("list") or type_lower.endswith("[]"):
        return (
            isinstance(value, list)
            and bool(value)
            and all(str(item) in choices for item in value)
        )
    rendered = "True" if value is True else "False" if value is False else str(value)
    return rendered in choices


def _compatibility_form_accepts(value: object, value_form: str) -> bool:
    if value_form == "boolean-string":
        return value in {"True", "False"}
    if value_form == "nullable-string":
        return value is None or isinstance(value, str)
    return _type_accepts(value, _COMPATIBILITY_VALUE_FORM_TYPES[value_form])


def _type_accepts(value: object, type_name: str) -> bool:
    lowered = type_name.lower()
    if lowered in {"boolean", "bool"}:
        return isinstance(value, bool)
    if lowered in {"int", "integer"}:
        return isinstance(value, int) and not isinstance(value, bool)
    if lowered in {"float", "number", "double"}:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if lowered.startswith("list") or lowered.endswith("[]"):
        return isinstance(value, list)
    if lowered.startswith("map") or lowered in {"object", "dict"}:
        return isinstance(value, dict)
    return isinstance(value, str)


def _leaf_values(value: object) -> tuple[object, ...]:
    if isinstance(value, Mapping):
        return tuple(item for child in value.values() for item in _leaf_values(child))
    if isinstance(value, list):
        return tuple(item for child in value for item in _leaf_values(child))
    return (value,)


def _render_card(
    tool: _RegistryTool,
    *,
    siblings: Sequence[str],
    legal_sets: tuple[tuple[str, ...], ...],
    compatibility_rules: tuple[CompatibilityRule, ...],
    forbidden_literals: frozenset[str],
) -> tuple[ToolSemanticCard, int, int]:
    arguments_by_key = {argument.key: argument for argument in tool.arguments}
    compatibility_forms: dict[str, str] = {}
    for rule in compatibility_rules:
        for key, value_form in rule.value_forms:
            prior = compatibility_forms.get(key)
            if prior is not None and prior != value_form:
                raise ExecutableSemanticCardError(
                    f"compatibility rules disagree on the value form for {tool.name}.{key}"
                )
            compatibility_forms[key] = value_form
            arguments_by_key.setdefault(
                key,
                _SignatureArgument(
                    key=key,
                    type_name=_COMPATIBILITY_VALUE_FORM_TYPES[value_form],
                    optional=False,
                ),
            )
    constraints, unparsed_constraint_count = _constraint_map(tool)
    avoid = (
        "Avoid when the requested operation matches another registered meaning, "
        f"especially {', '.join(siblings)}; shared nouns alone are insufficient."
        if siblings
        else "Avoid when the requested operation does not match this meaning; shared nouns alone are insufficient."
    )
    role_guidance = tuple(
        f"Spoken role: {_humanize_key(argument.key)} -> {argument.key} ({argument.type_name})."
        for argument in sorted(arguments_by_key.values(), key=lambda item: item.key)
    )
    examples: list[str] = []
    public_literal_count = 0
    for legal_keys in legal_sets[:3]:
        generated: dict[str, object] = {}
        for key in legal_keys:
            argument = arguments_by_key[key]
            compatibility_form = compatibility_forms.get(key)
            value, used_public_literal = _synthetic_value(
                tool,
                argument,
                constraints.get(key),
                compatibility_form,
            )
            value_form_valid = (
                _compatibility_form_accepts(value, compatibility_form)
                if compatibility_form is not None
                else _type_accepts(value, argument.type_name)
            )
            if not value_form_valid or (
                key in constraints
                and not _constraint_accepts(value, argument, constraints[key])
            ):
                raise ExecutableSemanticCardError(
                    f"synthetic example for {tool.name!r} violates the public type or constraint"
                )
            for leaf in _leaf_values(value):
                if isinstance(leaf, str) and any(
                    sentinel in leaf for sentinel in forbidden_literals
                ):
                    raise ExecutableSemanticCardError(
                        f"forbidden example literal detected for {tool.name!r}"
                    )
            public_literal_count += int(used_public_literal)
            generated[key] = value
        examples.append(
            json.dumps(
                {"name": tool.name, "arguments": generated},
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    key_sets = "; ".join(
        "{" + ", ".join(keys) + "}" for keys in legal_sets
    )
    type_text = "; ".join(
        f"{argument.key}: {argument.type_name}"
        + (" (optional)" if argument.optional else "")
        for argument in tool.arguments
    ) or "none"
    compatibility_lines = tuple(
        "Training-supported compatibility rule; construction support count: "
        f"{rule.construction_support_count}; legal keys "
        "{" + ", ".join(rule.legal_argument_key_set) + "}; "
        + (
            "; ".join(
                f"{key} {_COMPATIBILITY_VALUE_FORM_GUIDANCE[value_form]}"
                for key, value_form in rule.value_forms
            )
            or "use the public value types"
        )
        + "."
        for rule in compatibility_rules
    )
    lines = (
        f"TOOL CARD {tool.name}",
        f"Exact tool name: {tool.name}",
        f"Choose when: {tool.description}",
        f"Avoid when: {avoid}",
        f"Public signature: {tool.signature}",
        f"Public types: {type_text}",
        f"Public constraints: {tool.constraints or 'none declared'}",
        f"Legal argument-key sets: {key_sets}",
        "Aggregate compatibility rules:",
        *(f"- {rule}" for rule in compatibility_lines),
        "Spoken-role-to-key guidance:",
        *(f"- {guidance}" for guidance in role_guidance),
        "Synthetic JSON examples: Every example is artificial; never copy its values.",
        *(f"- {example}" for example in examples),
    )
    text = "\n".join(lines)
    return (
        ToolSemanticCard(
            tool_name=tool.name,
            choose_semantics=tool.description,
            avoid_semantics=avoid,
            signature=tool.signature,
            constraints=tool.constraints,
            legal_argument_key_sets=legal_sets,
            compatibility_rules=compatibility_rules,
            role_guidance=role_guidance,
            examples=tuple(examples),
            text=text,
        ),
        public_literal_count,
        unparsed_constraint_count,
    )


def build_executable_semantic_card_corpus(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    compatibility_rules: Sequence[CompatibilityRule] = (),
    forbidden_example_literals: Sequence[str] | set[str] | frozenset[str] = (),
    max_utf8_bytes: int = DEFAULT_MAX_UTF8_BYTES,
) -> ExecutableSemanticCardCorpus:
    """Render label-free cards from registry facts and decontaminated key summaries.

    Only ``tool_name`` and ``arg_signature`` are read from construction rows.
    Their utterances, identities, argument values, calls, and media stay unreachable
    from the rendering path.
    """

    if (
        isinstance(max_utf8_bytes, bool)
        or not isinstance(max_utf8_bytes, int)
        or max_utf8_bytes <= 0
    ):
        raise ExecutableSemanticCardError("max_utf8_bytes must be a positive integer")
    sentinels = frozenset(
        _required_ascii(value, field="forbidden_example_literal")
        for value in forbidden_example_literals
    )
    registry = _load_registry(registry_rows)
    rules_by_tool = _load_compatibility_rules(compatibility_rules, registry)
    patterns = _construction_patterns(construction_rows, registry, rules_by_tool)
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for tool in registry.values():
        groups[(tool.domain, tool.category)].append(tool.name)

    tool_cards: list[ToolSemanticCard] = []
    public_literal_count = 0
    unparsed_constraint_count = 0
    for name in sorted(registry):
        tool = registry[name]
        tool_rules = rules_by_tool.get(name, ())
        siblings = tuple(
            sibling
            for sibling in sorted(groups[(tool.domain, tool.category)])
            if sibling != name
        )
        card, literal_count, gap_count = _render_card(
            tool,
            siblings=siblings,
            legal_sets=_legal_key_sets(tool, patterns.get(name), tool_rules),
            compatibility_rules=tool_rules,
            forbidden_literals=sentinels,
        )
        tool_cards.append(card)
        public_literal_count += literal_count
        unparsed_constraint_count += gap_count

    sections = [_HEADER.rstrip(), "TASK-WIDE EXECUTION CARDS"]
    sections.extend(
        f"TASK CARD {card.card_id}\n{card.text}" for card in _TASK_CARDS
    )
    sections.extend(card.text for card in tool_cards)
    text = "\n\n".join(sections) + "\n"
    if not text.isascii():
        raise ExecutableSemanticCardError(
            "semantic-card corpus must be ASCII English before model use"
        )
    rendered = text.encode("utf-8")
    if len(rendered) > max_utf8_bytes:
        raise ExecutableSemanticCardError(
            f"semantic-card corpus exceeds byte budget: {len(rendered)} > {max_utf8_bytes}"
        )
    report = {
        "schema": "saea-a2t-executable-semantic-card-corpus-report-v1",
        "registry_tool_count": len(registry),
        "tool_card_count": len(tool_cards),
        "task_card_count": len(_TASK_CARDS),
        "construction_summary_count": len(construction_rows),
        "construction_fields_consumed": ["arg_signature", "tool_name"],
        "construction_tool_count": len(patterns),
        "compatibility_rule_count": len(compatibility_rules),
        "compatibility_rule_construction_support_count": sum(
            rule.construction_support_count
            for rules in rules_by_tool.values()
            for rule in rules
        ),
        "compatibility_rule_value_literals_rendered": 0,
        "legal_argument_key_set_count": sum(
            len(card.legal_argument_key_sets) for card in tool_cards
        ),
        "spoken_role_guidance_count": sum(
            len(card.role_guidance) for card in tool_cards
        ),
        "example_count": sum(len(card.examples) for card in tool_cards),
        "examples_validated": True,
        "public_constraint_example_literal_count": public_literal_count,
        "forbidden_example_literal_count": len(sentinels),
        "unparsed_constraint_field_count": unparsed_constraint_count,
        "source_utterances_rendered": 0,
        "reference_transcripts_rendered": 0,
        "source_argument_values_rendered": 0,
        "gold_values_rendered": 0,
        "source_sample_ids_rendered": 0,
        "evaluation_samples_consumed": 0,
        "ascii_only": True,
        "reversed_input_rebuild_contract": "byte-identical",
        "utf8_bytes": len(rendered),
        "characters": len(text),
        "line_count": len(text.splitlines()),
        "max_utf8_bytes": max_utf8_bytes,
    }
    return ExecutableSemanticCardCorpus(
        text=text,
        sha256=hashlib.sha256(rendered).hexdigest(),
        tool_cards=tuple(tool_cards),
        task_cards=_TASK_CARDS,
        report=report,
    )


__all__ = [
    "DEFAULT_MAX_UTF8_BYTES",
    "REQUIRED_TOOL_COUNT",
    "SYNTHETIC_LITERAL_PREFIX",
    "CompatibilityRule",
    "ExecutableSemanticCardCorpus",
    "ExecutableSemanticCardError",
    "TaskSemanticCard",
    "ToolSemanticCard",
    "build_executable_semantic_card_corpus",
]
