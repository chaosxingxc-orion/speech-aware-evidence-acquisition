"""Compile source-bound Audio2Tool executable semantic cards offline."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

from ..analysis.dev100_reviewer_audit import arm_offline_guard
from ..data.audio2tool import AUDIO2TOOL_LOCK_KEY, load_tool_registry
from ..data.loader import LoaderError
from ..data.lock import AssetResolutionError, asset_dir
from .a2t_executable_semantic_cards import (
    DEFAULT_MAX_UTF8_BYTES,
    REQUIRED_TOOL_COUNT,
    CompatibilityRule,
    ExecutableSemanticCardCorpus,
    ExecutableSemanticCardError,
    TaskSemanticCard,
    ToolSemanticCard,
    build_executable_semantic_card_corpus,
)
from .errors import RailsError
from .knowledge_build_a2t import A2tKbRow, a2t_pool_rows

MINIMUM_COMPATIBILITY_SUPPORT = 2
COMPILATION_RECEIPT_SCHEMA = "saea-a2t-semantic-card-compilation-receipt-v1"
PUBLIC_API_LEGALITY_PRESENTATION_V1 = "saea-a2t-public-api-legality-presentation-v1"
_ZERO_CONTACTS = {
    "audio_seconds": 0,
    "embedding_tool": 0,
    "frozen_core": 0,
    "gpu_hours": 0,
    "network": 0,
    "retriever": 0,
    "scorer": 0,
    "tokenizer": 0,
}


@dataclass(frozen=True)
class A2tSemanticCardCompilationConfig:
    """Explicit source and destination bindings for one offline compilation."""

    compilation_id: str
    dataset_lock_path: Path
    dataset_lock_sha256: str
    data_root: Path
    construction_receipt_path: Path
    construction_receipt_sha256: str
    tool_registry_path: Path
    tool_registry_sha256: str
    corpus_output_path: Path
    receipt_output_path: Path
    minimum_compatibility_support: int = MINIMUM_COMPATIBILITY_SUPPORT
    max_utf8_bytes: int = DEFAULT_MAX_UTF8_BYTES
    presentation_version: str | None = None


@dataclass(frozen=True)
class PublicLegalityToolSemanticCard:
    """One card with public legality separated from observed patterns."""

    tool_name: str
    choose_semantics: str
    avoid_semantics: str
    signature: str
    constraints: str
    public_required_argument_keys: tuple[str, ...]
    public_optional_argument_keys: tuple[str, ...]
    construction_observed_argument_patterns: tuple[tuple[str, ...], ...]
    compatibility_rules: tuple[CompatibilityRule, ...]
    role_guidance: tuple[str, ...]
    examples: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class PublicLegalitySemanticCardCorpus:
    """Deterministic corpus using registry facts as the legality authority."""

    text: str
    sha256: str
    tool_cards: tuple[PublicLegalityToolSemanticCard, ...]
    task_cards: tuple[TaskSemanticCard, ...]
    report: Mapping[str, object]

    @property
    def cards_by_name(self) -> dict[str, PublicLegalityToolSemanticCard]:
        """Return the complete card map keyed by exact registry name."""

        return {card.tool_name: card for card in self.tool_cards}


_LEGAL_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_VALUE_FORM_TO_COMPATIBILITY = {
    "boolean": "boolean",
    "integer": "integer",
    "list": "list",
    "map": "map",
    "number": "number",
    "string": "string",
}


class SemanticCardCompilationError(RuntimeError):
    """The deterministic semantic-card build refused unsafe or drifting input."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def _split_signature_arguments(text: str) -> tuple[str, ...]:
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
        elif character == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    if depth != 0:
        raise SemanticCardCompilationError("registry signature brackets are malformed")
    parts.append(text[start:].strip())
    return tuple(parts)


def _registry_argument_types(
    registry_rows: Sequence[Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    for row in registry_rows:
        name = row.get("tool_name")
        signature = row.get("signature")
        if not isinstance(name, str) or not name or name in registry:
            raise SemanticCardCompilationError(
                "registry tool names are empty or duplicated"
            )
        if not isinstance(signature, str):
            raise SemanticCardCompilationError(
                f"registry signature is missing for {name!r}"
            )
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\((.*)\)", signature)
        if match is None or match.group(1) != name:
            raise SemanticCardCompilationError(
                f"registry signature identity drift for {name!r}"
            )
        arguments: dict[str, str] = {}
        for raw in _split_signature_arguments(match.group(2)):
            argument = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)\??", raw)
            if argument is None or argument.group(1) in arguments:
                raise SemanticCardCompilationError(
                    f"registry signature arguments are malformed for {name!r}"
                )
            arguments[argument.group(1)] = argument.group(2).rstrip("?").strip()
        registry[name] = arguments
    return registry


def _registry_optional_keys(
    registry_rows: Sequence[Mapping[str, str]],
) -> dict[str, frozenset[str]]:
    optional: dict[str, frozenset[str]] = {}
    for row in registry_rows:
        name = row["tool_name"]
        signature = row["signature"]
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\((.*)\)", signature)
        if match is None or match.group(1) != name:
            raise SemanticCardCompilationError(
                f"registry signature identity drift for {name!r}"
            )
        keys = set()
        for raw in _split_signature_arguments(match.group(2)):
            argument = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*.+?(\?)?", raw)
            if argument is None:
                raise SemanticCardCompilationError(
                    f"registry signature arguments are malformed for {name!r}"
                )
            if argument.group(2) is not None:
                keys.add(argument.group(1))
        optional[name] = frozenset(keys)
    return optional


def _registry_constrained_keys(
    registry_rows: Sequence[Mapping[str, str]],
) -> dict[str, frozenset[str]]:
    constrained: dict[str, frozenset[str]] = {}
    for row in registry_rows:
        text = row.get("argument_constraints", "")
        if not isinstance(text, str):
            raise SemanticCardCompilationError("registry constraints must be text")
        constrained[row["tool_name"]] = frozenset(
            match.group(1)
            for match in re.finditer(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\[[^\]]+\]", text)
        )
    return constrained


def _serialized_value_form(value: str) -> str:
    """Classify a serialized construction value without retaining its literal."""

    if not isinstance(value, str):
        raise SemanticCardCompilationError(
            "construction summaries must carry serialized values as text"
        )
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return "string"
    if decoded is None:
        return "null"
    if isinstance(decoded, bool):
        return "boolean"
    if isinstance(decoded, int):
        return "integer"
    if isinstance(decoded, float):
        return "number"
    if isinstance(decoded, list):
        return "list"
    if isinstance(decoded, dict):
        return "map"
    return "string"


def _extra_key_form(forms: Counter[str]) -> tuple[str, int] | None:
    non_null = {name for name, count in forms.items() if name != "null" and count}
    null_count = forms.get("null", 0)
    if null_count and (not non_null or non_null == {"string"}):
        return "nullable-string", sum(forms.values())
    if non_null <= {"integer", "number"} and non_null:
        return (
            "number" if "number" in non_null else "integer",
            sum(forms.values()),
        )
    if len(non_null) == 1 and not null_count:
        form = next(iter(non_null))
        compatible = _VALUE_FORM_TO_COMPATIBILITY.get(form)
        if compatible is not None:
            return compatible, sum(forms.values())
    return None


def derive_compatibility_rules(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    minimum_support: int = MINIMUM_COMPATIBILITY_SUPPORT,
) -> tuple[tuple[CompatibilityRule, ...], dict[str, object]]:
    """Derive aggregate schema/value-form rules without retaining any literal."""

    if (
        isinstance(minimum_support, bool)
        or not isinstance(minimum_support, int)
        or minimum_support < 2
    ):
        raise SemanticCardCompilationError(
            "compatibility minimum support must be at least two"
        )
    registry = _registry_argument_types(registry_rows)
    optional_keys = _registry_optional_keys(registry_rows)
    constrained_keys = _registry_constrained_keys(registry_rows)
    pattern_support: Counter[tuple[str, tuple[str, ...]]] = Counter()
    value_forms: dict[tuple[str, tuple[str, ...], str], Counter[str]] = defaultdict(
        Counter
    )
    for row in construction_rows:
        if row.tool_name not in registry:
            raise SemanticCardCompilationError(
                f"construction tool {row.tool_name!r} is outside the registry"
            )
        skeleton = tuple(sorted(row.arg_signature))
        identity = (row.tool_name, skeleton)
        pattern_support[identity] += 1
        for key, value in row.arg_pairs:
            if key not in skeleton:
                raise SemanticCardCompilationError(
                    "construction argument pairs disagree with their key skeleton"
                )
            value_forms[(row.tool_name, skeleton, key)][
                _serialized_value_form(value)
            ] += 1

    rules: list[CompatibilityRule] = []
    singleton_excluded = 0
    malformed_excluded = 0
    ambiguous_excluded = 0
    public_boolean_rules = 0
    nullable_rules = 0
    constrained_nullable_excluded = 0
    extension_rules = 0
    for (tool_name, skeleton), support in sorted(pattern_support.items()):
        if support < minimum_support:
            singleton_excluded += 1
            continue
        if any(_LEGAL_KEY.fullmatch(key) is None for key in skeleton):
            malformed_excluded += 1
            continue
        public = registry[tool_name]
        extensions = tuple(sorted(set(skeleton) - set(public)))
        forms: dict[str, str] = {}
        supports: list[int] = [support]
        safe_extensions = True
        for key in extensions:
            inferred = _extra_key_form(value_forms[(tool_name, skeleton, key)])
            if inferred is None or inferred[1] < minimum_support:
                safe_extensions = False
                break
            forms[key] = inferred[0]
            supports.append(inferred[1])
        if not safe_extensions:
            ambiguous_excluded += 1
            continue
        for key in sorted(set(skeleton).intersection(public)):
            observed = value_forms[(tool_name, skeleton, key)]
            type_name = public[key].lower()
            null_count = observed.get("null", 0)
            boolean_count = observed.get("boolean", 0)
            if (
                null_count >= minimum_support
                and key in optional_keys[tool_name]
                and key not in constrained_keys[tool_name]
            ):
                forms[key] = "nullable-string"
                supports.append(null_count)
                nullable_rules += 1
            elif (
                null_count >= minimum_support
                and key in optional_keys[tool_name]
                and key in constrained_keys[tool_name]
            ):
                constrained_nullable_excluded += 1
            elif type_name in {"boolean", "bool"} and boolean_count >= minimum_support:
                forms[key] = "boolean-string"
                supports.append(boolean_count)
                public_boolean_rules += 1
        if not extensions and not forms:
            continue
        if extensions:
            extension_rules += 1
        rules.append(
            CompatibilityRule(
                tool_name=tool_name,
                legal_argument_key_set=skeleton,
                value_forms=tuple(sorted(forms.items())),
                construction_support_count=min(supports),
            )
        )
    ordered = tuple(
        sorted(
            rules,
            key=lambda rule: (
                rule.tool_name,
                len(rule.legal_argument_key_set),
                rule.legal_argument_key_set,
                rule.value_forms,
            ),
        )
    )
    report = {
        "schema": "saea-a2t-g4-compatibility-derivation-v1",
        "minimum_support": minimum_support,
        "rule_count": len(ordered),
        "tool_count": len({rule.tool_name for rule in ordered}),
        "extension_rule_count": extension_rules,
        "public_boolean_lexical_rule_count": public_boolean_rules,
        "nullable_lexical_rule_count": nullable_rules,
        "constrained_nullable_forms_excluded": constrained_nullable_excluded,
        "singleton_skeletons_excluded": singleton_excluded,
        "malformed_key_skeletons_excluded": malformed_excluded,
        "ambiguous_extension_skeletons_excluded": ambiguous_excluded,
        "source_utterances_rendered": 0,
        "source_sample_ids_rendered": 0,
        "call_renders_rendered": 0,
        "concrete_argument_values_rendered": 0,
        "reference_transcripts_rendered": 0,
        "evaluation_rows_consumed": 0,
    }
    return ordered, report


def _compatible_construction_rows(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    rules: Sequence[CompatibilityRule],
) -> tuple[A2tKbRow, ...]:
    registry = _registry_argument_types(registry_rows)
    extensions = {(rule.tool_name, rule.legal_argument_key_set) for rule in rules}
    kept = []
    for row in construction_rows:
        skeleton = tuple(sorted(row.arg_signature))
        public_keys = set(registry[row.tool_name])
        if (
            set(skeleton).issubset(public_keys)
            or (row.tool_name, skeleton) in extensions
        ):
            kept.append(row)
    return tuple(kept)


def build_from_partition(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    minimum_support: int = MINIMUM_COMPATIBILITY_SUPPORT,
    max_utf8_bytes: int = DEFAULT_MAX_UTF8_BYTES,
) -> tuple[ExecutableSemanticCardCorpus, dict[str, object]]:
    """Build twice under reversed input and return the byte-identity audit."""

    rules, derivation = derive_compatibility_rules(
        registry_rows, construction_rows, minimum_support=minimum_support
    )
    safe_rows = _compatible_construction_rows(registry_rows, construction_rows, rules)
    first = build_executable_semantic_card_corpus(
        registry_rows,
        safe_rows,
        compatibility_rules=rules,
        max_utf8_bytes=max_utf8_bytes,
    )
    reversed_rules, reversed_derivation = derive_compatibility_rules(
        tuple(reversed(registry_rows)),
        tuple(reversed(construction_rows)),
        minimum_support=minimum_support,
    )
    reversed_safe_rows = _compatible_construction_rows(
        tuple(reversed(registry_rows)),
        tuple(reversed(construction_rows)),
        reversed_rules,
    )
    second = build_executable_semantic_card_corpus(
        tuple(reversed(registry_rows)),
        reversed_safe_rows,
        compatibility_rules=reversed_rules,
        max_utf8_bytes=max_utf8_bytes,
    )
    if derivation != reversed_derivation or rules != reversed_rules:
        raise SemanticCardCompilationError(
            "compatibility derivation is order-dependent"
        )
    if first.text != second.text or first.sha256 != second.sha256:
        raise SemanticCardCompilationError(
            "semantic-card corpus is not byte deterministic"
        )
    pattern_families = {
        (row.tool_name, tuple(sorted(row.arg_signature))) for row in construction_rows
    }
    argument_keys = {key for row in construction_rows for key in row.arg_signature}
    report = {
        "deterministic_rebuild_equal": True,
        "construction_argument_pattern_family_count": len(pattern_families),
        "construction_argument_key_count": len(argument_keys),
        "safe_construction_row_count": len(safe_rows),
        "excluded_construction_row_count": len(construction_rows) - len(safe_rows),
        "compatibility": derivation,
    }
    return first, report


_LEGACY_OUTPUT_CONTRACT = (
    "Use an exact registered tool name, an exact legal argument-key set from its "
    "card, and JSON values with the public types and constraints."
)
_PUBLIC_LEGALITY_OUTPUT_CONTRACT = (
    "Use an exact registered tool name. For public signature keys, include every "
    "required key and any subset of optional keys; unobserved public combinations "
    "remain legal. Use JSON values with the public types and constraints. Construction "
    "compatibility evidence never changes public argument-key legality."
)
_LEGACY_CONSTRUCTION_BOUNDARY = (
    "The construction summaries contribute only observed legal argument-key sets;"
)
_PUBLIC_LEGALITY_CONSTRUCTION_BOUNDARY = (
    "The construction summaries contribute observed argument patterns as descriptive "
    "evidence only; their absence never prohibits a public required/optional combination;"
)


def _render_key_set(keys: Sequence[str]) -> str:
    return "{" + ", ".join(keys) + "}"


def _public_legality_header(legacy_text: str) -> str:
    header, marker, _remainder = legacy_text.partition(
        "\n\nTASK-WIDE EXECUTION CARDS\n"
    )
    if not marker:
        raise SemanticCardCompilationError(
            "legacy semantic-card header structure drift"
        )
    for old, new in (
        (_LEGACY_OUTPUT_CONTRACT, _PUBLIC_LEGALITY_OUTPUT_CONTRACT),
        (_LEGACY_CONSTRUCTION_BOUNDARY, _PUBLIC_LEGALITY_CONSTRUCTION_BOUNDARY),
    ):
        if old not in header:
            raise SemanticCardCompilationError(
                "legacy semantic-card header wording drift"
            )
        header = header.replace(old, new, 1)
    return header


def _public_legality_card(
    public_card: ToolSemanticCard,
    *,
    required_keys: tuple[str, ...],
    optional_keys: tuple[str, ...],
    observed_patterns: tuple[tuple[str, ...], ...],
    compatibility_rules: tuple[CompatibilityRule, ...],
) -> PublicLegalityToolSemanticCard:
    legacy_line = next(
        (
            line
            for line in public_card.text.splitlines()
            if line.startswith("Legal argument-key sets: ")
        ),
        None,
    )
    if legacy_line is None:
        raise SemanticCardCompilationError(
            f"legacy semantic-card legality line drift for {public_card.tool_name!r}"
        )
    observed_text = (
        "; ".join(_render_key_set(pattern) for pattern in observed_patterns)
        if observed_patterns
        else "none"
    )
    public_lines = (
        "Public argument legality: required keys "
        f"{_render_key_set(required_keys)}; optional keys "
        f"{_render_key_set(optional_keys)}. A call must include every public required "
        "key and may include any subset of the public optional keys.",
        f"Construction-observed argument patterns: {observed_text}. These patterns are "
        "descriptive only; unobserved public combinations remain legal.",
    )
    compatibility_lines = tuple(
        "- Observed keys "
        f"{_render_key_set(rule.legal_argument_key_set)}; value-form classes "
        + (
            ", ".join(f"{key}: {form}" for key, form in rule.value_forms)
            or "public types"
        )
        + f"; construction support count: {rule.construction_support_count}."
        for rule in compatibility_rules
    )
    lines = []
    for line in public_card.text.splitlines():
        if line == legacy_line:
            lines.extend(public_lines)
        elif line == "Aggregate compatibility rules:":
            lines.append("Construction-observed compatibility evidence:")
            lines.extend(compatibility_lines or ("- none.",))
            lines.append(
                "This evidence is descriptive and does not alter public argument legality."
            )
        elif line.startswith("Synthetic JSON examples: "):
            lines.append(
                "Synthetic examples illustrate public shapes only; omitted public "
                "optional combinations remain legal."
            )
            lines.append(line)
        else:
            lines.append(line)
    return PublicLegalityToolSemanticCard(
        tool_name=public_card.tool_name,
        choose_semantics=public_card.choose_semantics,
        avoid_semantics=public_card.avoid_semantics,
        signature=public_card.signature,
        constraints=public_card.constraints,
        public_required_argument_keys=required_keys,
        public_optional_argument_keys=optional_keys,
        construction_observed_argument_patterns=observed_patterns,
        compatibility_rules=compatibility_rules,
        role_guidance=public_card.role_guidance,
        examples=public_card.examples,
        text="\n".join(lines),
    )


def build_public_legality_semantic_card_corpus(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    compatibility_rules: Sequence[CompatibilityRule] = (),
    max_utf8_bytes: int = DEFAULT_MAX_UTF8_BYTES,
) -> PublicLegalitySemanticCardCorpus:
    """Render public signature legality and observed patterns as separate facts."""

    validated = build_executable_semantic_card_corpus(
        registry_rows,
        construction_rows,
        compatibility_rules=compatibility_rules,
        max_utf8_bytes=max_utf8_bytes,
    )
    public_only = build_executable_semantic_card_corpus(
        registry_rows,
        (),
        max_utf8_bytes=max_utf8_bytes,
    )
    public_keys = _registry_argument_types(registry_rows)
    optional_keys = _registry_optional_keys(registry_rows)
    observed_by_tool: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    for row in construction_rows:
        observed_by_tool[row.tool_name].add(tuple(sorted(row.arg_signature)))

    cards = []
    validated_cards = validated.cards_by_name
    for public_card in public_only.tool_cards:
        tool_name = public_card.tool_name
        public = frozenset(public_keys[tool_name])
        optional = optional_keys[tool_name]
        cards.append(
            _public_legality_card(
                public_card,
                required_keys=tuple(sorted(public - optional)),
                optional_keys=tuple(sorted(optional)),
                observed_patterns=tuple(
                    sorted(
                        observed_by_tool.get(tool_name, set()),
                        key=lambda keys: (len(keys), keys),
                    )
                ),
                compatibility_rules=validated_cards[tool_name].compatibility_rules,
            )
        )

    header = _public_legality_header(public_only.text)
    sections = [header.rstrip(), "TASK-WIDE EXECUTION CARDS"]
    sections.extend(
        f"TASK CARD {card.card_id}\n{card.text}" for card in public_only.task_cards
    )
    sections.extend(card.text for card in cards)
    text = "\n\n".join(sections) + "\n"
    if not text.isascii():
        raise SemanticCardCompilationError(
            "public-legality semantic-card corpus must be ASCII English"
        )
    rendered = text.encode("utf-8")
    if len(rendered) > max_utf8_bytes:
        raise SemanticCardCompilationError(
            "public-legality semantic-card corpus exceeds byte budget: "
            f"{len(rendered)} > {max_utf8_bytes}"
        )

    report = dict(validated.report)
    report.pop("legal_argument_key_set_count", None)
    report.update(
        {
            "schema": "saea-a2t-public-legality-semantic-card-corpus-report-v1",
            "presentation_version": PUBLIC_API_LEGALITY_PRESENTATION_V1,
            "public_legality_authority": "registry-required-and-optional-signature-facts",
            "construction_pattern_role": "descriptive-only",
            "unobserved_public_combinations_forbidden": False,
            "public_required_argument_key_count": sum(
                len(card.public_required_argument_keys) for card in cards
            ),
            "public_optional_argument_key_count": sum(
                len(card.public_optional_argument_keys) for card in cards
            ),
            "construction_observed_argument_pattern_count": sum(
                len(card.construction_observed_argument_patterns) for card in cards
            ),
            "utf8_bytes": len(rendered),
            "characters": len(text),
            "line_count": len(text.splitlines()),
        }
    )
    return PublicLegalitySemanticCardCorpus(
        text=text,
        sha256=hashlib.sha256(rendered).hexdigest(),
        tool_cards=tuple(cards),
        task_cards=public_only.task_cards,
        report=report,
    )


def build_from_partition_with_public_legality(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    minimum_support: int = MINIMUM_COMPATIBILITY_SUPPORT,
    max_utf8_bytes: int = DEFAULT_MAX_UTF8_BYTES,
) -> tuple[PublicLegalitySemanticCardCorpus, dict[str, object]]:
    """Compile the opt-in presentation and verify reversed-input identity."""

    rules, derivation = derive_compatibility_rules(
        registry_rows, construction_rows, minimum_support=minimum_support
    )
    safe_rows = _compatible_construction_rows(registry_rows, construction_rows, rules)
    first = build_public_legality_semantic_card_corpus(
        registry_rows,
        safe_rows,
        compatibility_rules=rules,
        max_utf8_bytes=max_utf8_bytes,
    )
    reversed_registry = tuple(reversed(registry_rows))
    reversed_construction = tuple(reversed(construction_rows))
    reversed_rules, reversed_derivation = derive_compatibility_rules(
        reversed_registry,
        reversed_construction,
        minimum_support=minimum_support,
    )
    reversed_safe_rows = _compatible_construction_rows(
        reversed_registry,
        reversed_construction,
        reversed_rules,
    )
    second = build_public_legality_semantic_card_corpus(
        reversed_registry,
        reversed_safe_rows,
        compatibility_rules=reversed_rules,
        max_utf8_bytes=max_utf8_bytes,
    )
    if derivation != reversed_derivation or rules != reversed_rules:
        raise SemanticCardCompilationError(
            "compatibility derivation is order-dependent"
        )
    if first != second:
        raise SemanticCardCompilationError(
            "public-legality semantic-card corpus is not byte deterministic"
        )
    pattern_families = {
        (row.tool_name, tuple(sorted(row.arg_signature))) for row in construction_rows
    }
    argument_keys = {key for row in construction_rows for key in row.arg_signature}
    report = {
        "deterministic_rebuild_equal": True,
        "presentation_version": PUBLIC_API_LEGALITY_PRESENTATION_V1,
        "public_legality_authority": "registry-required-and-optional-signature-facts",
        "construction_pattern_role": "descriptive-only",
        "unobserved_public_combinations_forbidden": False,
        "construction_argument_pattern_family_count": len(pattern_families),
        "construction_argument_key_count": len(argument_keys),
        "safe_construction_row_count": len(safe_rows),
        "excluded_construction_row_count": len(construction_rows) - len(safe_rows),
        "compatibility": derivation,
    }
    return first, report


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_config(config: A2tSemanticCardCompilationConfig) -> None:
    if (
        not isinstance(config.compilation_id, str)
        or not config.compilation_id
        or not config.compilation_id.isascii()
    ):
        raise SemanticCardCompilationError(
            "compilation_id must be non-empty ASCII text"
        )
    for label, value in (
        ("dataset lock", config.dataset_lock_sha256),
        ("construction receipt", config.construction_receipt_sha256),
        ("tool registry", config.tool_registry_sha256),
    ):
        if not _is_sha256(value):
            raise SemanticCardCompilationError(
                f"{label} SHA-256 must be 64 lowercase hex digits"
            )
    if Path(config.corpus_output_path) == Path(config.receipt_output_path):
        raise SemanticCardCompilationError(
            "corpus and receipt output paths must be different"
        )
    if config.presentation_version not in {
        None,
        PUBLIC_API_LEGALITY_PRESENTATION_V1,
    }:
        raise SemanticCardCompilationError(
            "presentation_version must be None or "
            f"{PUBLIC_API_LEGALITY_PRESENTATION_V1!r}"
        )
    for path in (config.corpus_output_path, config.receipt_output_path):
        if Path(path).exists():
            raise SemanticCardCompilationError(f"output already exists: {path}")


def _read_pinned_bytes(path: Path, expected_sha256: str, *, label: str) -> bytes:
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise SemanticCardCompilationError(
            f"cannot read {label} {path}: {error}"
        ) from error
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != expected_sha256:
        raise SemanticCardCompilationError(
            f"{label} SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    return raw


def _load_pinned_lock(path: Path, expected_sha256: str) -> Mapping[str, object]:
    raw = _read_pinned_bytes(path, expected_sha256, label="dataset lock")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SemanticCardCompilationError(
            f"cannot parse dataset lock {path}: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise SemanticCardCompilationError("dataset lock must be a JSON object")
    return document


def _validate_registry_binding(
    config: A2tSemanticCardCompilationConfig,
    lock: Mapping[str, object],
) -> tuple[dict[str, str], ...]:
    try:
        public_path = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, config.data_root) / (
            "tools_registry.csv"
        )
    except AssetResolutionError as error:
        raise SemanticCardCompilationError(str(error)) from error
    configured_path = Path(config.tool_registry_path)
    if configured_path.resolve() != public_path.resolve():
        raise SemanticCardCompilationError(
            "tool_registry_path does not match the resolved public tool registry"
        )
    _read_pinned_bytes(
        configured_path,
        config.tool_registry_sha256,
        label="tool registry",
    )
    try:
        registry = load_tool_registry(lock, config.data_root)
    except (AssetResolutionError, LoaderError) as error:
        raise SemanticCardCompilationError(str(error)) from error
    if _sha256_file(configured_path) != config.tool_registry_sha256:
        raise SemanticCardCompilationError(
            "tool registry SHA-256 changed while it was being parsed"
        )
    return registry


def _write_pair_exclusive(
    corpus_path: Path,
    corpus_bytes: bytes,
    receipt_path: Path,
    receipt_bytes: bytes,
) -> None:
    corpus_path = Path(corpus_path)
    receipt_path = Path(receipt_path)
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_handle = None
    receipt_handle = None
    created_corpus = False
    created_receipt = False
    completed = False
    try:
        corpus_handle = corpus_path.open("xb")
        created_corpus = True
        receipt_handle = receipt_path.open("xb")
        created_receipt = True
        corpus_handle.write(corpus_bytes)
        receipt_handle.write(receipt_bytes)
        completed = True
    except FileExistsError as error:
        raise SemanticCardCompilationError(
            f"output already exists: {error.filename}"
        ) from error
    except OSError as error:
        raise SemanticCardCompilationError(
            f"cannot write semantic-card artifacts: {error}"
        ) from error
    finally:
        if corpus_handle is not None:
            corpus_handle.close()
        if receipt_handle is not None:
            receipt_handle.close()
        if created_receipt and not completed:
            receipt_path.unlink(missing_ok=True)
        if created_corpus and not completed:
            corpus_path.unlink(missing_ok=True)


def compile_a2t_semantic_card_artifacts(
    config: A2tSemanticCardCompilationConfig,
) -> dict[str, object]:
    """Compile one hash-pinned construction selection without model contact."""

    if not isinstance(config, A2tSemanticCardCompilationConfig):
        raise SemanticCardCompilationError(
            "config must be an A2tSemanticCardCompilationConfig"
        )
    _validate_config(config)
    offline = arm_offline_guard()
    lock = _load_pinned_lock(config.dataset_lock_path, config.dataset_lock_sha256)
    registry = _validate_registry_binding(config, lock)
    try:
        construction_rows, pool_report = a2t_pool_rows(
            lock,
            config.data_root,
            construction_receipt_path=config.construction_receipt_path,
            construction_receipt_sha256=config.construction_receipt_sha256,
        )
    except (AssetResolutionError, LoaderError, RailsError) as error:
        raise SemanticCardCompilationError(str(error)) from error
    if _sha256_file(config.tool_registry_path) != config.tool_registry_sha256:
        raise SemanticCardCompilationError(
            "tool registry SHA-256 changed while selected construction was parsed"
        )
    selection = pool_report.get("construction_selection")
    if not isinstance(selection, Mapping):
        raise SemanticCardCompilationError(
            "construction pool omitted its source-bound selection provenance"
        )
    try:
        build = (
            build_from_partition
            if config.presentation_version is None
            else build_from_partition_with_public_legality
        )
        corpus, compiler_report = build(
            registry,
            construction_rows,
            minimum_support=config.minimum_compatibility_support,
            max_utf8_bytes=config.max_utf8_bytes,
        )
    except (ExecutableSemanticCardError, KeyError) as error:
        raise SemanticCardCompilationError(str(error)) from error
    if len(registry) != REQUIRED_TOOL_COUNT:
        raise SemanticCardCompilationError(
            f"public tool registry must contain exactly {REQUIRED_TOOL_COUNT} tools"
        )
    selected_target_tools = {row.tool_name for row in construction_rows}
    registry_tools = {row["tool_name"] for row in registry}
    if not selected_target_tools <= registry_tools:
        raise SemanticCardCompilationError(
            "selected construction targets are outside the public tool registry"
        )
    if len(corpus.tool_cards) != len(registry_tools):
        raise SemanticCardCompilationError(
            "semantic-card corpus does not cover the complete public tool registry"
        )
    if offline.count != 0:
        raise SemanticCardCompilationError("offline guard observed an outbound attempt")

    receipt: dict[str, object] = {
        "schema": COMPILATION_RECEIPT_SCHEMA,
        "compilation_id": config.compilation_id,
        "execution_profile": "model-free-check",
        "sources": {
            "dataset_lock": {
                "path": str(config.dataset_lock_path),
                "sha256": config.dataset_lock_sha256,
            },
            "construction_selection": {
                "path": str(config.construction_receipt_path),
                "sha256": config.construction_receipt_sha256,
            },
            "tool_registry": {
                "path": str(config.tool_registry_path),
                "sha256": config.tool_registry_sha256,
            },
        },
        "construction_selection": dict(selection),
        "selected_pool": dict(pool_report),
        "registry": {
            "tool_count": len(registry_tools),
            "selected_target_tool_count": len(selected_target_tools),
            "selected_target_tools": sorted(selected_target_tools),
            "schema_only_tool_count": len(registry_tools - selected_target_tools),
            "schema_only_tools": sorted(registry_tools - selected_target_tools),
        },
        "compiler": {
            **compiler_report,
            "minimum_compatibility_support": config.minimum_compatibility_support,
            "max_utf8_bytes": config.max_utf8_bytes,
        },
        "corpus": {
            "path": str(config.corpus_output_path),
            "sha256": corpus.sha256,
            "utf8_bytes": len(corpus.text.encode("utf-8")),
            "report": dict(corpus.report),
        },
        "contacts": dict(_ZERO_CONTACTS),
    }
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    _write_pair_exclusive(
        config.corpus_output_path,
        corpus.text.encode("utf-8"),
        config.receipt_output_path,
        receipt_bytes,
    )
    return receipt


__all__ = [
    "A2tSemanticCardCompilationConfig",
    "COMPILATION_RECEIPT_SCHEMA",
    "MINIMUM_COMPATIBILITY_SUPPORT",
    "PUBLIC_API_LEGALITY_PRESENTATION_V1",
    "CompatibilityRule",
    "ExecutableSemanticCardCorpus",
    "PublicLegalitySemanticCardCorpus",
    "PublicLegalityToolSemanticCard",
    "SemanticCardCompilationError",
    "build_from_partition",
    "build_from_partition_with_public_legality",
    "build_public_legality_semantic_card_corpus",
    "compile_a2t_semantic_card_artifacts",
    "derive_compatibility_rules",
]
