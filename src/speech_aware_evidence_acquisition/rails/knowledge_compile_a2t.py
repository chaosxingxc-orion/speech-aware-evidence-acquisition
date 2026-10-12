"""Compile source-bound Audio2Tool semantic-card artifacts offline.

Construction reads and artifact publication belong beside knowledge_build_a2t.
This API is not a pure runtime renderer or a model-visible tool. Consume its
source-bound outputs through registered knowledge providers after preparation.
"""

from __future__ import annotations

import argparse
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
from .hashing import content_hash
from .knowledge import (
    EXTERNAL_GOVERNED_PARTITION_ROLE,
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)
from .knowledge_build_a2t import A2tKbRow, a2t_pool_rows

MINIMUM_COMPATIBILITY_SUPPORT = 2
COMPILATION_RECEIPT_SCHEMA = "saea-a2t-semantic-card-compilation-receipt-v1"
PUBLIC_API_LEGALITY_PRESENTATION_V1 = "saea-a2t-public-api-legality-presentation-v1"
NATIVE_COMPATIBLE_PRESENTATION_V1 = "saea-a2t-native-compatible-presentation-v1"
NATIVE_CARD_SNAPSHOT_BUILDER_V1 = "saea-a2t-native-card-snapshot-v1"
NATIVE_CARD_SNAPSHOT_SOURCE_V1 = "saea-a2t-native-card-snapshot-source-v1"
NATIVE_SNAPSHOT_VALUE_VIEW_FULL = "full"
NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION = "tool-activation"
NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_CONTRAST_V1 = (
    "tool-activation-contrast-v1"
)
NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_SCOPE_V1 = "tool-activation-scope-v1"
NATIVE_SNAPSHOT_VALUE_VIEW_PARAMETER_MEANING = "parameter-meaning"
_NATIVE_SNAPSHOT_VALUE_VIEWS = frozenset(
    {
        NATIVE_SNAPSHOT_VALUE_VIEW_FULL,
        NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION,
        NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_CONTRAST_V1,
        NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_SCOPE_V1,
        NATIVE_SNAPSHOT_VALUE_VIEW_PARAMETER_MEANING,
    }
)
_ACTIVATION_CONTRAST_MAX_ALTERNATIVES = 3
_ACTIVATION_CONTRAST_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "on",
        "to",
        "for",
        "and",
        "or",
        "in",
        "is",
        "are",
        "this",
        "that",
        "with",
        "its",
    }
)
_ACTIVATION_CONTRAST_POLICY_V1 = (
    "Build each neighborhood from exact tool_name and complete choose_semantics "
    "across the authoritative native-compatible corpus. Split camelCase tool "
    "names; tokenize lowercase English alphanumeric words; remove only a, an, "
    "the, of, on, to, for, and, or, in, is, are, this, that, with, its; score "
    "positive-overlap alternatives by set-Jaccard; exclude self; sort by "
    "descending score then exact tool_name; retain at most 3."
)
_ACTIVATION_SCOPE_POLICY_V1 = (
    "Project exact tool_name, underscore-humanized public domain and category, "
    "and complete public registry description from an exact registry-to-corpus "
    "tool_name, signature, and description binding."
)
_COMPILATION_CONFIG_REQUIRED_FIELDS = frozenset(
    {
        "compilation_id",
        "dataset_lock_path",
        "dataset_lock_sha256",
        "data_root",
        "construction_receipt_path",
        "construction_receipt_sha256",
        "tool_registry_path",
        "tool_registry_sha256",
        "corpus_output_path",
        "receipt_output_path",
    }
)
_COMPILATION_CONFIG_OPTIONAL_FIELDS = frozenset(
    {
        "minimum_compatibility_support",
        "max_utf8_bytes",
        "presentation_version",
        "snapshot_output_path",
        "snapshot_value_view",
    }
)
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
    snapshot_output_path: Path | None = None
    snapshot_value_view: str | None = None


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


@dataclass(frozen=True)
class NativeCompatibleToolSemanticCard:
    """One card separating public documentation from native target evidence."""

    tool_name: str
    choose_semantics: str
    avoid_semantics: str
    signature: str
    constraints: str
    public_required_argument_keys: tuple[str, ...]
    public_optional_argument_keys: tuple[str, ...]
    construction_observed_argument_patterns: tuple[tuple[str, ...], ...]
    native_task_form_rules: tuple[CompatibilityRule, ...]
    role_guidance: tuple[str, ...]
    native_role_guidance: tuple[str, ...]
    public_examples: tuple[str, ...]
    native_task_form_examples: tuple[str, ...]
    examples: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class NativeCompatibleSemanticCardCorpus:
    """Deterministic corpus with public and native-task layers."""

    text: str
    sha256: str
    tool_cards: tuple[NativeCompatibleToolSemanticCard, ...]
    task_cards: tuple[TaskSemanticCard, ...]
    report: Mapping[str, object]

    @property
    def cards_by_name(self) -> dict[str, NativeCompatibleToolSemanticCard]:
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

_NATIVE_SEMANTIC_VALUE_FORMS = frozenset(
    {"boolean", "integer", "list", "map", "number", "string"}
)
_NATIVE_VALUE_FORM_GUIDANCE = {
    "boolean": "JSON Boolean",
    "integer": "JSON integer",
    "list": "JSON array",
    "map": "JSON object",
    "number": "JSON number",
    "string": "JSON string",
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
    "required key and any subset of optional keys, subject to documented constraints and dependencies; unobserved public combinations "
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
        "key and may include any subset of the public optional keys, subject to documented constraints and dependencies.",
        f"Construction-observed argument patterns: {observed_text}. These patterns are "
        "descriptive only; unobserved public combinations remain legal, subject to documented constraints and dependencies.",
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
                "optional combinations remain legal, subject to documented constraints and dependencies."
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
            "example_count": sum(len(card.examples) for card in cards),
            "spoken_role_guidance_count": sum(
                len(card.role_guidance) for card in cards
            ),
            "public_constraint_example_literal_count": public_only.report[
                "public_constraint_example_literal_count"
            ],
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


_NATIVE_OUTPUT_CONTRACT = (
    "Use an exact registered tool name. Public signatures describe documented API "
    "shapes. For the native task, a separately labelled source-supported observed "
    "form may guide the argument shape when the user request grounds every named "
    "role. Do not force public required keys omitted from an observed replacement "
    "form. Observations are scoped positive evidence, not exhaustive, and do not "
    "prohibit public combinations. Use JSON values with documented public types and "
    "constraints for public keys and the displayed semantic JSON form for extension "
    "keys."
)
_NATIVE_CONSTRUCTION_BOUNDARY = (
    "The construction summaries contribute source-supported native task forms as "
    "positive evidence only; absence never prohibits a public combination, and small "
    "support counts are narrow evidence that must not be generalized;"
)


def _native_compatible_header(legacy_text: str) -> str:
    header = _public_legality_header(legacy_text)
    for old, new in (
        (_PUBLIC_LEGALITY_OUTPUT_CONTRACT, _NATIVE_OUTPUT_CONTRACT),
        (_PUBLIC_LEGALITY_CONSTRUCTION_BOUNDARY, _NATIVE_CONSTRUCTION_BOUNDARY),
    ):
        if old not in header:
            raise SemanticCardCompilationError(
                "public-legality semantic-card header wording drift"
            )
        header = header.replace(old, new, 1)
    return header


def _select_native_task_form_rules(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    derived_rules: Sequence[CompatibilityRule],
    *,
    minimum_support: int,
) -> tuple[tuple[CompatibilityRule, ...], dict[str, int]]:
    """Select positive native-task forms without scorer lexical artifacts."""

    public_keys = _registry_argument_types(registry_rows)
    optional_keys = _registry_optional_keys(registry_rows)
    support_by_pattern = Counter(
        (row.tool_name, tuple(sorted(row.arg_signature))) for row in construction_rows
    )
    derived_by_pattern = {
        (rule.tool_name, rule.legal_argument_key_set): rule for rule in derived_rules
    }
    selected: list[CompatibilityRule] = []
    small_support_excluded = 0
    unsafe_extension_excluded = 0
    scorer_lexical_excluded = 0
    empty_replacement_excluded = 0
    extension_count = 0
    replacement_count = 0
    for (tool_name, skeleton), support in sorted(support_by_pattern.items()):
        public = set(public_keys[tool_name])
        required = public - set(optional_keys[tool_name])
        extensions = set(skeleton) - public
        missing_required = required - set(skeleton)
        if not extensions and not missing_required:
            continue
        if support < minimum_support:
            small_support_excluded += 1
            continue
        if not skeleton:
            empty_replacement_excluded += 1
            continue
        if extensions:
            derived = derived_by_pattern.get((tool_name, skeleton))
            if derived is None:
                unsafe_extension_excluded += 1
                continue
            forms = dict(derived.value_forms)
            extension_forms = tuple(
                sorted((key, forms[key]) for key in extensions if key in forms)
            )
            if len(extension_forms) != len(extensions):
                unsafe_extension_excluded += 1
                continue
            if any(
                value_form not in _NATIVE_SEMANTIC_VALUE_FORMS
                for _key, value_form in extension_forms
            ):
                scorer_lexical_excluded += 1
                continue
        else:
            extension_forms = ()
        canonical = CompatibilityRule(
            tool_name=tool_name,
            legal_argument_key_set=skeleton,
            value_forms=extension_forms,
            construction_support_count=support,
        )
        selected.append(canonical)
        if missing_required:
            replacement_count += 1
        else:
            extension_count += 1
    ordered = tuple(
        sorted(
            selected,
            key=lambda rule: (
                rule.tool_name,
                len(rule.legal_argument_key_set),
                rule.legal_argument_key_set,
                rule.value_forms,
            ),
        )
    )
    return ordered, {
        "selected_native_task_form_count": len(ordered),
        "selected_extension_form_count": extension_count,
        "selected_replacement_form_count": replacement_count,
        "small_support_native_patterns_excluded": small_support_excluded,
        "unsafe_extension_patterns_excluded": unsafe_extension_excluded,
        "scorer_lexical_form_patterns_excluded": scorer_lexical_excluded,
        "empty_replacement_patterns_excluded": empty_replacement_excluded,
    }


def _native_rule_kind(
    required_keys: Sequence[str],
    rule: CompatibilityRule,
) -> str:
    return (
        "extension"
        if set(required_keys).issubset(rule.legal_argument_key_set)
        else "replacement"
    )


def _humanize_native_key(key: str) -> str:
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", key).replace("_", " ")
    return " ".join(
        "identifier" if word == "id" else word for word in expanded.lower().split()
    )


def _native_rule_example(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    rule: CompatibilityRule,
    *,
    max_utf8_bytes: int,
) -> str:
    matching_rows = tuple(
        row
        for row in construction_rows
        if row.tool_name == rule.tool_name
        and tuple(sorted(row.arg_signature)) == rule.legal_argument_key_set
    )
    rendered = build_executable_semantic_card_corpus(
        registry_rows,
        matching_rows,
        compatibility_rules=(rule,),
        max_utf8_bytes=max_utf8_bytes,
    )
    for example in rendered.cards_by_name[rule.tool_name].examples:
        document = json.loads(example)
        if set(document["arguments"]) == set(rule.legal_argument_key_set):
            return example
    raise SemanticCardCompilationError(
        f"no synthetic example rendered for native task form {rule.tool_name!r} "
        f"{rule.legal_argument_key_set!r}"
    )


def _native_compatible_card(
    public_card: ToolSemanticCard,
    *,
    required_keys: tuple[str, ...],
    optional_keys: tuple[str, ...],
    observed_patterns: tuple[tuple[str, ...], ...],
    native_rules: tuple[CompatibilityRule, ...],
    native_examples: tuple[str, ...],
) -> NativeCompatibleToolSemanticCard:
    public_type_line = next(
        (
            line
            for line in public_card.text.splitlines()
            if line.startswith("Public types: ")
        ),
        None,
    )
    if public_type_line is None:
        raise SemanticCardCompilationError(
            f"legacy semantic-card public type line drift for {public_card.tool_name!r}"
        )
    observed_text = (
        "; ".join(_render_key_set(pattern) for pattern in observed_patterns)
        if observed_patterns
        else "none"
    )
    native_rule_lines: list[str] = []
    native_guidance: list[str] = []
    public = set(required_keys) | set(optional_keys)
    for rule in native_rules:
        kind = _native_rule_kind(required_keys, rule)
        extension_forms = tuple(
            (key, value_form)
            for key, value_form in rule.value_forms
            if key not in public
        )
        form_text = (
            ", ".join(
                f"{key}: {_NATIVE_VALUE_FORM_GUIDANCE[value_form]}"
                for key, value_form in extension_forms
            )
            or "documented public types for the displayed public keys"
        )
        native_rule_lines.append(
            f"- Observed native {kind} form "
            f"{_render_key_set(rule.legal_argument_key_set)}; extension key forms: "
            f"{form_text}; construction support count: "
            f"{rule.construction_support_count}; source scope: hash-pinned, "
            "evaluation-excluded construction units. Use only when the user request "
            "grounds every named role."
        )
        native_guidance.extend(
            f"Observed native role: {_humanize_native_key(key)} -> {key} "
            f"({_NATIVE_VALUE_FORM_GUIDANCE[value_form]}), only when grounded in "
            "the user request."
            for key, value_form in extension_forms
        )

    public_examples = public_card.examples
    examples = public_examples + native_examples
    lines = (
        f"TOOL CARD {public_card.tool_name}",
        f"Exact tool name: {public_card.tool_name}",
        f"Choose when: {public_card.choose_semantics}",
        f"Avoid when: {public_card.avoid_semantics}",
        f"Public signature: {public_card.signature}",
        public_type_line,
        f"Public constraints: {public_card.constraints or 'none declared'}",
        "Public API documentation: required keys "
        f"{_render_key_set(required_keys)}; optional keys "
        f"{_render_key_set(optional_keys)}. A public-shape call must include every "
        "public required key and may include any subset of the public optional keys, "
        "subject to documented constraints and dependencies.",
        f"Construction-observed argument patterns: {observed_text}. Their absence "
        "does not prohibit public combinations.",
        *(
            ("Observed native task forms:", *native_rule_lines)
            if native_rule_lines
            else ("Observed native task forms: none supported.",)
        ),
        "Native task form scope: observed forms are positive, source-scoped evidence "
        "and not exhaustive. For an observed replacement form, do not force omitted "
        "public required keys into it. Small support counts are narrow evidence and "
        "must not be generalized.",
        "Public spoken-role-to-key guidance:",
        *(f"- {guidance}" for guidance in public_card.role_guidance),
        "Observed native-role-to-key guidance:",
        *(f"- {guidance}" for guidance in native_guidance),
        *(("- none.",) if not native_guidance else ()),
        "Public synthetic JSON examples: Every example is artificial; never copy "
        "its values.",
        *(f"- {example}" for example in public_examples),
        "Native-form synthetic JSON examples: Every example is artificial; use a "
        "displayed form only when the user request grounds every named role.",
        *(f"- {example}" for example in native_examples),
        *(("- none.",) if not native_examples else ()),
    )
    return NativeCompatibleToolSemanticCard(
        tool_name=public_card.tool_name,
        choose_semantics=public_card.choose_semantics,
        avoid_semantics=public_card.avoid_semantics,
        signature=public_card.signature,
        constraints=public_card.constraints,
        public_required_argument_keys=required_keys,
        public_optional_argument_keys=optional_keys,
        construction_observed_argument_patterns=observed_patterns,
        native_task_form_rules=native_rules,
        role_guidance=public_card.role_guidance + tuple(native_guidance),
        native_role_guidance=tuple(native_guidance),
        public_examples=public_examples,
        native_task_form_examples=native_examples,
        examples=examples,
        text="\n".join(lines),
    )


def build_native_compatible_semantic_card_corpus(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    compatibility_rules: Sequence[CompatibilityRule] = (),
    scorer_lexical_form_patterns_excluded: int = 0,
    max_utf8_bytes: int = DEFAULT_MAX_UTF8_BYTES,
) -> NativeCompatibleSemanticCardCorpus:
    """Render public API documentation and source-supported native task forms."""

    public_keys = _registry_argument_types(registry_rows)
    optional_keys = _registry_optional_keys(registry_rows)
    rules_by_tool: dict[str, list[CompatibilityRule]] = defaultdict(list)
    for rule in compatibility_rules:
        if rule.tool_name not in public_keys:
            raise SemanticCardCompilationError(
                f"native task form tool {rule.tool_name!r} is outside the registry"
            )
        public = set(public_keys[rule.tool_name])
        required = public - set(optional_keys[rule.tool_name])
        extensions = set(rule.legal_argument_key_set) - public
        forms = dict(rule.value_forms)
        if (
            (not extensions and required.issubset(rule.legal_argument_key_set))
            or set(forms) != extensions
            or any(
                value_form not in _NATIVE_SEMANTIC_VALUE_FORMS
                for value_form in forms.values()
            )
        ):
            raise SemanticCardCompilationError(
                "native task form rules must be observed replacements or extensions "
                "using semantic JSON value forms only"
            )
        rules_by_tool[rule.tool_name].append(rule)

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
    observed_by_tool: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    for row in construction_rows:
        observed_by_tool[row.tool_name].add(tuple(sorted(row.arg_signature)))

    cards: list[NativeCompatibleToolSemanticCard] = []
    for public_card in public_only.tool_cards:
        tool_name = public_card.tool_name
        public = frozenset(public_keys[tool_name])
        optional = optional_keys[tool_name]
        tool_rules = tuple(
            sorted(
                rules_by_tool.get(tool_name, ()),
                key=lambda rule: (
                    len(rule.legal_argument_key_set),
                    rule.legal_argument_key_set,
                    rule.value_forms,
                ),
            )
        )
        native_examples = tuple(
            _native_rule_example(
                registry_rows,
                construction_rows,
                rule,
                max_utf8_bytes=max_utf8_bytes,
            )
            for rule in tool_rules
        )
        cards.append(
            _native_compatible_card(
                public_card,
                required_keys=tuple(sorted(public - optional)),
                optional_keys=tuple(sorted(optional)),
                observed_patterns=tuple(
                    sorted(
                        observed_by_tool.get(tool_name, set()),
                        key=lambda keys: (len(keys), keys),
                    )
                ),
                native_rules=tool_rules,
                native_examples=native_examples,
            )
        )

    header = _native_compatible_header(public_only.text)
    sections = [header.rstrip(), "TASK-WIDE EXECUTION CARDS"]
    sections.extend(
        f"TASK CARD {card.card_id}\n{card.text}" for card in public_only.task_cards
    )
    sections.extend(card.text for card in cards)
    text = "\n\n".join(sections) + "\n"
    if not text.isascii():
        raise SemanticCardCompilationError(
            "native-compatible semantic-card corpus must be ASCII English"
        )
    rendered = text.encode("utf-8")
    if len(rendered) > max_utf8_bytes:
        raise SemanticCardCompilationError(
            "native-compatible semantic-card corpus exceeds byte budget: "
            f"{len(rendered)} > {max_utf8_bytes}"
        )

    replacement_count = sum(
        _native_rule_kind(card.public_required_argument_keys, rule) == "replacement"
        for card in cards
        for rule in card.native_task_form_rules
    )
    native_form_count = sum(len(card.native_task_form_rules) for card in cards)
    native_form_support_count = sum(
        rule.construction_support_count
        for card in cards
        for rule in card.native_task_form_rules
    )
    observed_pattern_count = sum(
        len(card.construction_observed_argument_patterns) for card in cards
    )
    rendered_example_count = sum(len(card.examples) for card in cards)
    native_example_count = sum(len(card.native_task_form_examples) for card in cards)
    role_guidance_count = sum(len(card.role_guidance) for card in cards)
    native_role_guidance_count = sum(len(card.native_role_guidance) for card in cards)
    constrained_keys = _registry_constrained_keys(registry_rows)
    native_constraint_literal_count = sum(
        key in constrained_keys[card.tool_name]
        for card in cards
        for example in card.native_task_form_examples
        for key in json.loads(example)["arguments"]
    )
    report = dict(validated.report)
    report.pop("legal_argument_key_set_count", None)
    report.update(
        {
            "schema": "saea-a2t-native-compatible-semantic-card-corpus-report-v1",
            "presentation_version": NATIVE_COMPATIBLE_PRESENTATION_V1,
            "registry_tool_count": len(cards),
            "tool_card_count": len(cards),
            "task_card_count": len(public_only.task_cards),
            "construction_summary_count": len(construction_rows),
            "construction_tool_count": sum(
                bool(card.construction_observed_argument_patterns) for card in cards
            ),
            "compatibility_rule_count": native_form_count,
            "compatibility_rule_construction_support_count": (
                native_form_support_count
            ),
            "example_count": rendered_example_count,
            "spoken_role_guidance_count": role_guidance_count,
            "public_constraint_example_literal_count": (
                public_only.report["public_constraint_example_literal_count"]
                + native_constraint_literal_count
            ),
            "public_api_role": "documented-api-shapes",
            "construction_pattern_role": "source-supported-native-task-guidance",
            "native_form_evidence_scope": (
                "hash-pinned-evaluation-excluded-construction-units"
            ),
            "observations_exhaustive": False,
            "unobserved_public_combinations_forbidden": False,
            "public_required_keys_forced_into_observed_replacements": False,
            "scorer_parsing_tricks_rendered": 0,
            "scorer_lexical_form_patterns_excluded": (
                scorer_lexical_form_patterns_excluded
            ),
            "rendered_native_task_form_count": native_form_count,
            "rendered_native_extension_form_count": (
                native_form_count - replacement_count
            ),
            "rendered_native_replacement_form_count": replacement_count,
            "rendered_native_task_form_support_count": native_form_support_count,
            "rendered_observed_argument_pattern_count": observed_pattern_count,
            "rendered_example_count": rendered_example_count,
            "rendered_native_task_form_example_count": native_example_count,
            "rendered_role_guidance_count": role_guidance_count,
            "rendered_native_role_guidance_count": native_role_guidance_count,
            "utf8_bytes": len(rendered),
            "characters": len(text),
            "line_count": len(text.splitlines()),
        }
    )
    return NativeCompatibleSemanticCardCorpus(
        text=text,
        sha256=hashlib.sha256(rendered).hexdigest(),
        tool_cards=tuple(cards),
        task_cards=public_only.task_cards,
        report=report,
    )


def build_from_partition_with_native_compatibility(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    minimum_support: int = MINIMUM_COMPATIBILITY_SUPPORT,
    max_utf8_bytes: int = DEFAULT_MAX_UTF8_BYTES,
) -> tuple[NativeCompatibleSemanticCardCorpus, dict[str, object]]:
    """Compile the opt-in native-compatible presentation deterministically."""

    derived, derivation = derive_compatibility_rules(
        registry_rows, construction_rows, minimum_support=minimum_support
    )
    rules, selection = _select_native_task_form_rules(
        registry_rows,
        construction_rows,
        derived,
        minimum_support=minimum_support,
    )
    safe_rows = _compatible_construction_rows(registry_rows, construction_rows, rules)
    first = build_native_compatible_semantic_card_corpus(
        registry_rows,
        safe_rows,
        compatibility_rules=rules,
        scorer_lexical_form_patterns_excluded=selection[
            "scorer_lexical_form_patterns_excluded"
        ],
        max_utf8_bytes=max_utf8_bytes,
    )

    reversed_registry = tuple(reversed(registry_rows))
    reversed_construction = tuple(reversed(construction_rows))
    reversed_derived, reversed_derivation = derive_compatibility_rules(
        reversed_registry,
        reversed_construction,
        minimum_support=minimum_support,
    )
    reversed_rules, reversed_selection = _select_native_task_form_rules(
        reversed_registry,
        reversed_construction,
        reversed_derived,
        minimum_support=minimum_support,
    )
    reversed_safe_rows = _compatible_construction_rows(
        reversed_registry, reversed_construction, reversed_rules
    )
    second = build_native_compatible_semantic_card_corpus(
        reversed_registry,
        reversed_safe_rows,
        compatibility_rules=reversed_rules,
        scorer_lexical_form_patterns_excluded=reversed_selection[
            "scorer_lexical_form_patterns_excluded"
        ],
        max_utf8_bytes=max_utf8_bytes,
    )
    if (
        derivation != reversed_derivation
        or rules != reversed_rules
        or selection != reversed_selection
    ):
        raise SemanticCardCompilationError(
            "native task form derivation is order-dependent"
        )
    if first != second:
        raise SemanticCardCompilationError(
            "native-compatible semantic-card corpus is not byte deterministic"
        )

    pattern_families = {
        (row.tool_name, tuple(sorted(row.arg_signature))) for row in construction_rows
    }
    argument_keys = {key for row in construction_rows for key in row.arg_signature}
    report: dict[str, object] = {
        "deterministic_rebuild_equal": True,
        "presentation_version": NATIVE_COMPATIBLE_PRESENTATION_V1,
        "public_api_role": "documented-api-shapes",
        "construction_pattern_role": "source-supported-native-task-guidance",
        "observations_exhaustive": False,
        "unobserved_public_combinations_forbidden": False,
        "public_required_keys_forced_into_observed_replacements": False,
        "construction_argument_pattern_family_count": len(pattern_families),
        "construction_argument_key_count": len(argument_keys),
        "safe_construction_row_count": len(safe_rows),
        "excluded_construction_row_count": len(construction_rows) - len(safe_rows),
        "compatibility": derivation,
        "native_task_form_selection": selection,
    }
    for key in (
        "rendered_native_task_form_count",
        "rendered_native_extension_form_count",
        "rendered_native_replacement_form_count",
        "rendered_native_task_form_support_count",
        "rendered_observed_argument_pattern_count",
        "rendered_example_count",
        "rendered_native_task_form_example_count",
        "rendered_role_guidance_count",
        "rendered_native_role_guidance_count",
        "scorer_lexical_form_patterns_excluded",
        "scorer_parsing_tricks_rendered",
    ):
        report[key] = first.report[key]
    return first, report


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


def _humanize_tool_name(tool_name: str) -> str:
    words = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", tool_name)
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", words)
    words = re.sub(r"([A-Za-z])([0-9])", r"\1 \2", words)
    words = re.sub(r"([0-9])([A-Za-z])", r"\1 \2", words)
    return " ".join(words.replace("_", " ").lower().split())


def _native_snapshot_key_text(card: NativeCompatibleToolSemanticCard) -> str:
    native_count = len(card.native_role_guidance)
    if native_count:
        if card.role_guidance[-native_count:] != card.native_role_guidance:
            raise SemanticCardCompilationError(
                f"native role guidance is not a suffix for {card.tool_name!r}"
            )
        public_guidance = card.role_guidance[:-native_count]
    else:
        public_guidance = card.role_guidance
    lines = [
        f"Exact tool name: {card.tool_name} ({_humanize_tool_name(card.tool_name)}).",
        f"Choose semantics: {card.choose_semantics}",
    ]
    if public_guidance:
        lines.append("Public spoken-role guidance:")
        lines.extend(f"- {guidance}" for guidance in public_guidance)
    if card.native_role_guidance:
        lines.append("Source-supported native-role guidance:")
        lines.extend(f"- {guidance}" for guidance in card.native_role_guidance)
    text = "\n".join(lines)
    if not text.isascii():
        raise SemanticCardCompilationError(
            f"snapshot key text must be ASCII English for {card.tool_name!r}"
        )
    return text


def _native_snapshot_value_text(
    card: NativeCompatibleToolSemanticCard,
    *,
    value_view: str,
    contrast_alternatives: Sequence[NativeCompatibleToolSemanticCard] = (),
    activation_scope: tuple[str, str] | None = None,
) -> str:
    """Project a compiler-owned native card without parsing external text."""

    if value_view == NATIVE_SNAPSHOT_VALUE_VIEW_FULL:
        return card.text
    if value_view == NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_CONTRAST_V1:
        selected = (
            f"TOOL ACTIVATION CONTRAST {card.tool_name}",
            f"Exact tool name: {card.tool_name}",
            f"Choose semantics: {card.choose_semantics}",
            "Related operations (lexical search aid; up to 3, non-exhaustive and "
            "non-exclusive):",
            "Compare the requested operation, object, and scope with the listed "
            "public descriptions.",
            *(
                line
                for index, alternative in enumerate(contrast_alternatives, start=1)
                for line in (
                    "Lexically related alternative "
                    f"{index} exact tool name: {alternative.tool_name}",
                    "Lexically related alternative "
                    f"{index} choose semantics: {alternative.choose_semantics}",
                )
            ),
        )
    elif value_view == NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_SCOPE_V1:
        if activation_scope is None:
            raise SemanticCardCompilationError(
                f"public registry scope is missing for {card.tool_name!r}"
            )
        domain, category = activation_scope
        selected = (
            f"TOOL ACTIVATION SCOPE {card.tool_name}",
            f"Exact tool name: {card.tool_name}",
            f"Public domain: {domain.replace('_', ' ')}",
            f"Public category: {category.replace('_', ' ')}",
            "Operation and scope (public description): "
            f"{card.choose_semantics}",
        )
    else:
        expected_prefix = (
            f"TOOL CARD {card.tool_name}",
            f"Exact tool name: {card.tool_name}",
            f"Choose when: {card.choose_semantics}",
            f"Avoid when: {card.avoid_semantics}",
        )
        lines = tuple(card.text.splitlines())
        if (
            lines[:4] != expected_prefix
            or len(lines) <= 4
            or lines[4] != f"Public signature: {card.signature}"
        ):
            raise SemanticCardCompilationError(
                f"native semantic-card activation prefix drift for {card.tool_name!r}"
            )
        if value_view == NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION:
            selected = expected_prefix
        elif value_view == NATIVE_SNAPSHOT_VALUE_VIEW_PARAMETER_MEANING:
            selected = (*expected_prefix[:2], *lines[4:])
        else:
            raise SemanticCardCompilationError(
                f"unsupported native snapshot value view {value_view!r}"
            )
    text = "\n".join(selected)
    if not text.isascii():
        raise SemanticCardCompilationError(
            f"snapshot value text must be ASCII English for {card.tool_name!r}"
        )
    return text


def _activation_contrast_tokens(
    card: NativeCompatibleToolSemanticCard,
) -> frozenset[str]:
    text = f"{_humanize_tool_name(card.tool_name)} {card.choose_semantics}"
    return frozenset(
        token
        for token in re.findall(r"[A-Za-z0-9]+", text.lower())
        if token not in _ACTIVATION_CONTRAST_STOPWORDS
    )


def _activation_contrast_neighborhoods(
    cards: Sequence[NativeCompatibleToolSemanticCard],
) -> dict[str, tuple[NativeCompatibleToolSemanticCard, ...]]:
    tokens_by_name = {
        card.tool_name: _activation_contrast_tokens(card) for card in cards
    }
    neighborhoods: dict[str, tuple[NativeCompatibleToolSemanticCard, ...]] = {}
    for card in cards:
        own_tokens = tokens_by_name[card.tool_name]
        scored: list[tuple[float, str, NativeCompatibleToolSemanticCard]] = []
        for alternative in cards:
            if alternative.tool_name == card.tool_name:
                continue
            alternative_tokens = tokens_by_name[alternative.tool_name]
            overlap = own_tokens & alternative_tokens
            if not overlap:
                continue
            union = own_tokens | alternative_tokens
            scored.append(
                (len(overlap) / len(union), alternative.tool_name, alternative)
            )
        scored.sort(key=lambda item: (-item[0], item[1]))
        neighborhoods[card.tool_name] = tuple(
            item[2] for item in scored[:_ACTIVATION_CONTRAST_MAX_ALTERNATIVES]
        )
    return neighborhoods


def _activation_scope_bindings(
    corpus: NativeCompatibleSemanticCardCorpus,
    registry_rows: Sequence[Mapping[str, str]] | None,
) -> dict[str, tuple[str, str]]:
    if (
        registry_rows is None
        or isinstance(registry_rows, (str, bytes))
        or not isinstance(registry_rows, Sequence)
        or not registry_rows
    ):
        raise SemanticCardCompilationError(
            "activation scope view requires a nonempty public registry row set"
        )
    cards_by_name = corpus.cards_by_name
    bindings: dict[str, tuple[str, str]] = {}
    for row in registry_rows:
        if not isinstance(row, Mapping):
            raise SemanticCardCompilationError(
                "activation scope public registry rows must be objects"
            )
        tool_name = row.get("tool_name")
        if not isinstance(tool_name, str) or not tool_name or tool_name in bindings:
            raise SemanticCardCompilationError(
                "activation scope public registry tool names are empty or duplicated"
            )
        domain = row.get("domain")
        category = row.get("category")
        if (
            not isinstance(domain, str)
            or not domain.strip()
            or not domain.isascii()
            or not isinstance(category, str)
            or not category.strip()
            or not category.isascii()
        ):
            raise SemanticCardCompilationError(
                "activation scope public registry domain and category must be "
                "nonempty ASCII text"
            )
        card = cards_by_name.get(tool_name)
        if card is not None and (
            row.get("signature") != card.signature
            or row.get("description") != card.choose_semantics
        ):
            raise SemanticCardCompilationError(
                "activation scope public registry signature or description differs "
                f"for {tool_name!r}"
            )
        bindings[tool_name] = (domain, category)
    if set(bindings) != set(cards_by_name):
        raise SemanticCardCompilationError(
            "activation scope public registry tool names do not exactly match the corpus"
        )
    return bindings


def build_native_compatible_knowledge_snapshot(
    corpus: NativeCompatibleSemanticCardCorpus,
    *,
    compilation_source: Mapping[str, object],
    value_view: str | None = None,
    registry_rows: Sequence[Mapping[str, str]] | None = None,
) -> KnowledgeSnapshot:
    """Project native cards into positive keys and complete supplied values.

    ``compilation_source`` is output-path independent and excludes both the
    compilation receipt and snapshot hash. Its own content hash can therefore
    bind the snapshot without a circular artifact dependency.
    """

    effective_value_view = (
        NATIVE_SNAPSHOT_VALUE_VIEW_FULL if value_view is None else value_view
    )
    if effective_value_view not in _NATIVE_SNAPSHOT_VALUE_VIEWS:
        raise SemanticCardCompilationError(
            f"unsupported native snapshot value view {value_view!r}"
        )
    expected_source_keys = {
        "schema",
        "compilation_id",
        "presentation_version",
        "dataset_lock_sha256",
        "construction_selection_sha256",
        "tool_registry_sha256",
        "corpus_sha256",
        "minimum_compatibility_support",
        "max_utf8_bytes",
    }
    if effective_value_view != NATIVE_SNAPSHOT_VALUE_VIEW_FULL:
        expected_source_keys.add("value_view")
    if set(compilation_source) != expected_source_keys:
        raise SemanticCardCompilationError(
            "native snapshot compilation source has malformed fields"
        )
    if compilation_source.get("schema") != NATIVE_CARD_SNAPSHOT_SOURCE_V1:
        raise SemanticCardCompilationError(
            "native snapshot compilation source schema is unsupported"
        )
    source_value_view = compilation_source.get(
        "value_view", NATIVE_SNAPSHOT_VALUE_VIEW_FULL
    )
    if source_value_view != effective_value_view:
        raise SemanticCardCompilationError(
            "native snapshot compilation source value view does not match the requested view"
        )
    if (
        compilation_source.get("presentation_version")
        != NATIVE_COMPATIBLE_PRESENTATION_V1
        or compilation_source.get("corpus_sha256") != corpus.sha256
    ):
        raise SemanticCardCompilationError(
            "native snapshot compilation source does not bind its corpus"
        )
    if (
        not isinstance(compilation_source.get("compilation_id"), str)
        or not compilation_source["compilation_id"]
        or not str(compilation_source["compilation_id"]).isascii()
    ):
        raise SemanticCardCompilationError(
            "native snapshot compilation source has invalid compilation_id"
        )
    for field in (
        "dataset_lock_sha256",
        "construction_selection_sha256",
        "tool_registry_sha256",
        "corpus_sha256",
    ):
        if not _is_sha256(compilation_source.get(field)):
            raise SemanticCardCompilationError(
                f"native snapshot compilation source has invalid {field}"
            )
    for field in ("minimum_compatibility_support", "max_utf8_bytes"):
        value = compilation_source.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise SemanticCardCompilationError(
                f"native snapshot compilation source has invalid {field}"
            )
    if len(corpus.tool_cards) != REQUIRED_TOOL_COUNT:
        raise SemanticCardCompilationError(
            f"native snapshot requires exactly {REQUIRED_TOOL_COUNT} tool cards"
        )
    ordered_cards = tuple(sorted(corpus.tool_cards, key=lambda card: card.tool_name))
    if len({card.tool_name for card in ordered_cards}) != len(ordered_cards):
        raise SemanticCardCompilationError(
            "native snapshot tool cards must have unique names"
        )

    source_document = dict(compilation_source)
    source_sha256 = content_hash(source_document)
    source_id = f"external:a2t-native-card-source:{source_sha256}"
    contrast_neighborhoods = (
        _activation_contrast_neighborhoods(ordered_cards)
        if effective_value_view
        == NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_CONTRAST_V1
        else {}
    )
    activation_scopes = (
        _activation_scope_bindings(corpus, registry_rows)
        if effective_value_view == NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_SCOPE_V1
        else {}
    )
    facets: list[KeyFacet] = []
    values: list[ValueBundle] = []
    for card in ordered_cards:
        facet_id = f"a2t-native-card:{card.tool_name}:content"
        value_id = f"a2t-native-card:{card.tool_name}:value"
        value_text = _native_snapshot_value_text(
            card,
            value_view=effective_value_view,
            contrast_alternatives=contrast_neighborhoods.get(card.tool_name, ()),
            activation_scope=activation_scopes.get(card.tool_name),
        )
        facets.append(
            KeyFacet(
                facet_id=facet_id,
                dimension="content",
                representation_kind="text",
                representation=_native_snapshot_key_text(card),
                source_sample_ids=(source_id,),
            ).validate()
        )
        values.append(
            ValueBundle(
                value_id=value_id,
                content=value_text,
                associated_facet_ids=(facet_id,),
                source_sample_ids=(source_id,),
                provenance_refs=(
                    f"a2t-native-card-compilation-source-sha256:{source_sha256}",
                    f"a2t-native-card-corpus-sha256:{corpus.sha256}",
                    "a2t-native-card-sha256:"
                    f"{hashlib.sha256(value_text.encode('utf-8')).hexdigest()}",
                    *(
                        (f"a2t-native-card-value-view:{effective_value_view}",)
                        if effective_value_view != NATIVE_SNAPSHOT_VALUE_VIEW_FULL
                        else ()
                    ),
                ),
                task_target=card.tool_name,
                prior_score=None,
            ).validate()
        )
    return KnowledgeSnapshot(
        snapshot_id=f"a2t-native-cards-{source_sha256[:16]}",
        source_split_identity_hash=source_sha256,
        source_sample_ids=(source_id,),
        builder_policy_id=NATIVE_CARD_SNAPSHOT_BUILDER_V1,
        facets=tuple(facets),
        values=tuple(values),
        source_partition_role=EXTERNAL_GOVERNED_PARTITION_ROLE,
    ).validate()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _compiled_mapping(value: object, *, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RailsError(f"{name} must be an object")
    return value


def validate_compiled_knowledge_snapshot(
    receipt: Mapping[str, object],
    snapshot: KnowledgeSnapshot,
    *,
    store_role: str,
    snapshot_file_sha256: str,
    snapshot_path: Path,
) -> Mapping[str, object]:
    """Validate compiler receipt custody against one already-loaded snapshot.

    This pure check never reads any declared path. Callers that publish or
    load source bytes retain responsibility for path confinement and rehashing.
    """

    if not isinstance(receipt, Mapping):
        raise RailsError("compiler receipt must be an object")
    if store_role not in {
        NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION,
        NATIVE_SNAPSHOT_VALUE_VIEW_PARAMETER_MEANING,
    }:
        raise RailsError("compiled store role is unsupported")
    if not _is_sha256(snapshot_file_sha256):
        raise RailsError("compiled snapshot file SHA-256 is malformed")
    if not isinstance(snapshot_path, Path):
        raise RailsError("compiled snapshot path must be a Path")
    if not isinstance(snapshot, KnowledgeSnapshot):
        raise RailsError("compiled snapshot must be a KnowledgeSnapshot")
    snapshot.validate()

    info = _compiled_mapping(
        receipt.get("knowledge_snapshot"), name="knowledge_snapshot"
    )
    source = _compiled_mapping(info.get("source"), name="snapshot source")
    if set(source) != {"metadata", "sha256"}:
        raise RailsError("snapshot source fields differ from the compiler schema")
    metadata = _compiled_mapping(
        source.get("metadata"), name="snapshot source metadata"
    )
    expected_metadata_fields = {
        "schema",
        "compilation_id",
        "presentation_version",
        "dataset_lock_sha256",
        "construction_selection_sha256",
        "tool_registry_sha256",
        "corpus_sha256",
        "minimum_compatibility_support",
        "max_utf8_bytes",
        "value_view",
    }
    if set(metadata) != expected_metadata_fields:
        raise RailsError("snapshot source metadata fields differ from the compiler schema")
    receipt_value_view = info.get("value_view")
    metadata_value_view = metadata.get("value_view")
    allowed_value_views_by_role = {
        NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION: {
            NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION,
            NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_CONTRAST_V1,
            NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_SCOPE_V1,
        },
        NATIVE_SNAPSHOT_VALUE_VIEW_PARAMETER_MEANING: {
            NATIVE_SNAPSHOT_VALUE_VIEW_PARAMETER_MEANING,
        },
    }
    if (
        receipt.get("schema") != COMPILATION_RECEIPT_SCHEMA
        or receipt.get("execution_profile") != "model-free-check"
        or metadata.get("schema") != NATIVE_CARD_SNAPSHOT_SOURCE_V1
        or metadata.get("presentation_version")
        != NATIVE_COMPATIBLE_PRESENTATION_V1
        or not isinstance(receipt_value_view, str)
        or not isinstance(metadata_value_view, str)
        or receipt_value_view != metadata_value_view
        or metadata_value_view not in allowed_value_views_by_role[store_role]
        or (
            metadata_value_view
            == NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_CONTRAST_V1
            and info.get("value_view_policy") != _ACTIVATION_CONTRAST_POLICY_V1
        )
        or (
            metadata_value_view
            == NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_SCOPE_V1
            and info.get("value_view_policy") != _ACTIVATION_SCOPE_POLICY_V1
        )
        or (
            metadata_value_view
            not in {
                NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_CONTRAST_V1,
                NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_SCOPE_V1,
            }
            and "value_view_policy" in info
        )
    ):
        raise RailsError("compiled store role or compiler schema differs")
    if (
        not isinstance(metadata.get("compilation_id"), str)
        or not metadata["compilation_id"]
        or not str(metadata["compilation_id"]).isascii()
    ):
        raise RailsError("snapshot source compilation identity is malformed")
    for field in (
        "dataset_lock_sha256",
        "construction_selection_sha256",
        "tool_registry_sha256",
        "corpus_sha256",
    ):
        if not _is_sha256(metadata.get(field)):
            raise RailsError(f"snapshot source metadata {field} is malformed")
    for field in ("minimum_compatibility_support", "max_utf8_bytes"):
        value = metadata.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise RailsError(f"snapshot source metadata {field} is malformed")

    info_path = info.get("path")
    if (
        info.get("file_sha256") != snapshot_file_sha256
        or info.get("snapshot_sha256") != snapshot.content_hash()
        or not isinstance(info_path, str)
        or Path(info_path).absolute() != snapshot_path.absolute()
        or info.get("builder_policy_id") != snapshot.builder_policy_id
        or snapshot.builder_policy_id != NATIVE_CARD_SNAPSHOT_BUILDER_V1
        or snapshot.source_partition_role != EXTERNAL_GOVERNED_PARTITION_ROLE
        or info.get("source_partition_role") != snapshot.source_partition_role
        or source.get("sha256") != snapshot.source_split_identity_hash
        or content_hash(metadata) != snapshot.source_split_identity_hash
    ):
        raise RailsError("compiled snapshot and receipt bindings differ")

    corpus = _compiled_mapping(receipt.get("corpus"), name="compiler receipt corpus")
    compiler = _compiled_mapping(
        receipt.get("compiler"), name="compiler receipt settings"
    )
    registry = _compiled_mapping(
        receipt.get("registry"), name="compiler receipt registry"
    )
    if (
        receipt.get("compilation_id") != metadata.get("compilation_id")
        or corpus.get("sha256") != metadata.get("corpus_sha256")
        or any(
            compiler.get(key) != metadata.get(key)
            for key in ("minimum_compatibility_support", "max_utf8_bytes")
        )
        or registry.get("tool_count") != len(snapshot.values)
        or info.get("value_count") != len(snapshot.values)
        or info.get("positive_content_facet_count") != len(snapshot.facets)
        or info.get("key_text_row_count") != len(snapshot.facets)
    ):
        raise RailsError("compiler receipt describes another compilation")

    for value in snapshot.values:
        target = value.task_target
        if (
            not isinstance(target, str) or not target
            or value.value_id != f"a2t-native-card:{target}:value"
            or value.associated_facet_ids != (f"a2t-native-card:{target}:content",)
        ):
            raise RailsError("compiled tool-to-card association differs from its builder")

    sources = _compiled_mapping(receipt.get("sources"), name="compiler sources")
    source_fields = {
        "dataset_lock": "dataset_lock_sha256",
        "construction_selection": "construction_selection_sha256",
        "tool_registry": "tool_registry_sha256",
    }
    if set(sources) != set(source_fields):
        raise RailsError("compiler sources fields differ from the compiler schema")
    for name, metadata_key in source_fields.items():
        pin = _compiled_mapping(sources[name], name=name)
        if set(pin) != {"path", "sha256"}:
            raise RailsError(f"compiler source {name} fields are malformed")
        if (
            not isinstance(pin.get("path"), str)
            or not pin["path"]
            or not _is_sha256(pin.get("sha256"))
            or pin.get("sha256") != metadata.get(metadata_key)
        ):
            raise RailsError(f"compiler source {name} SHA-256 differs")

    return dict(metadata)


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
        NATIVE_COMPATIBLE_PRESENTATION_V1,
    }:
        raise SemanticCardCompilationError(
            "presentation_version must be None or one of "
            f"{PUBLIC_API_LEGALITY_PRESENTATION_V1!r}, "
            f"{NATIVE_COMPATIBLE_PRESENTATION_V1!r}"
        )
    if (
        config.snapshot_value_view is not None
        and (
            not isinstance(config.snapshot_value_view, str)
            or config.snapshot_value_view not in _NATIVE_SNAPSHOT_VALUE_VIEWS
        )
    ):
        raise SemanticCardCompilationError(
            "snapshot_value_view must be None or one of "
            f"{sorted(_NATIVE_SNAPSHOT_VALUE_VIEWS)!r}"
        )
    if (
        config.snapshot_value_view
        not in {None, NATIVE_SNAPSHOT_VALUE_VIEW_FULL}
        and (
            config.presentation_version != NATIVE_COMPATIBLE_PRESENTATION_V1
            or config.snapshot_output_path is None
        )
    ):
        raise SemanticCardCompilationError(
            "non-default snapshot_value_view requires native-compatible snapshot export"
        )
    if (
        config.snapshot_output_path is not None
        and config.presentation_version != NATIVE_COMPATIBLE_PRESENTATION_V1
    ):
        raise SemanticCardCompilationError(
            "snapshot export requires the native-compatible presentation"
        )
    output_paths = [config.corpus_output_path, config.receipt_output_path]
    if config.snapshot_output_path is not None:
        output_paths.append(config.snapshot_output_path)
    if len({Path(path) for path in output_paths}) != len(output_paths):
        raise SemanticCardCompilationError("artifact output paths must be different")
    for path in output_paths:
        if Path(path).exists():
            raise SemanticCardCompilationError(f"output already exists: {path}")


def _required_config_text(document: Mapping[str, object], field: str) -> str:
    value = document.get(field)
    if not isinstance(value, str) or not value:
        raise SemanticCardCompilationError(
            f"semantic-card compilation config {field} must be non-empty text"
        )
    return value


def _optional_config_text(
    document: Mapping[str, object], field: str
) -> str | None:
    value = document.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise SemanticCardCompilationError(
            f"semantic-card compilation config {field} must be null or non-empty text"
        )
    return value


def _config_positive_integer(
    document: Mapping[str, object], field: str, default: int
) -> int:
    value = document.get(field, default)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SemanticCardCompilationError(
            f"semantic-card compilation config {field} must be a positive integer"
        )
    return value


def load_a2t_semantic_card_compilation_config(
    config_path: Path,
) -> A2tSemanticCardCompilationConfig:
    """Load one exact JSON config for the shared offline compiler."""

    path = Path(config_path)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise SemanticCardCompilationError(
            f"cannot read semantic-card compilation config {path}: {error}"
        ) from error
    try:
        from ..core.data_root_placeholder import expand_data_root

        document = expand_data_root(json.loads(raw.decode("utf-8")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SemanticCardCompilationError(
            f"cannot parse semantic-card compilation config {path}: {error}"
        ) from error
    allowed = _COMPILATION_CONFIG_REQUIRED_FIELDS | _COMPILATION_CONFIG_OPTIONAL_FIELDS
    if (
        not isinstance(document, Mapping)
        or not _COMPILATION_CONFIG_REQUIRED_FIELDS <= set(document)
        or not set(document) <= allowed
    ):
        raise SemanticCardCompilationError(
            "semantic-card compilation config has missing or unknown fields"
        )

    snapshot_output = _optional_config_text(document, "snapshot_output_path")
    value_view = document.get("snapshot_value_view")
    if value_view is not None and (
        not isinstance(value_view, str) or not value_view
    ):
        raise SemanticCardCompilationError(
            "semantic-card compilation config snapshot_value_view must be "
            "null or non-empty text"
        )
    config = A2tSemanticCardCompilationConfig(
        compilation_id=_required_config_text(document, "compilation_id"),
        dataset_lock_path=Path(_required_config_text(document, "dataset_lock_path")),
        dataset_lock_sha256=_required_config_text(
            document, "dataset_lock_sha256"
        ),
        data_root=Path(_required_config_text(document, "data_root")),
        construction_receipt_path=Path(
            _required_config_text(document, "construction_receipt_path")
        ),
        construction_receipt_sha256=_required_config_text(
            document, "construction_receipt_sha256"
        ),
        tool_registry_path=Path(
            _required_config_text(document, "tool_registry_path")
        ),
        tool_registry_sha256=_required_config_text(
            document, "tool_registry_sha256"
        ),
        corpus_output_path=Path(
            _required_config_text(document, "corpus_output_path")
        ),
        receipt_output_path=Path(
            _required_config_text(document, "receipt_output_path")
        ),
        minimum_compatibility_support=_config_positive_integer(
            document,
            "minimum_compatibility_support",
            MINIMUM_COMPATIBILITY_SUPPORT,
        ),
        max_utf8_bytes=_config_positive_integer(
            document, "max_utf8_bytes", DEFAULT_MAX_UTF8_BYTES
        ),
        presentation_version=_optional_config_text(
            document, "presentation_version"
        ),
        snapshot_output_path=(
            Path(snapshot_output) if snapshot_output is not None else None
        ),
        snapshot_value_view=value_view,
    )
    _validate_config(config)
    return config


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
    _write_artifacts_exclusive(
        ((corpus_path, corpus_bytes), (receipt_path, receipt_bytes))
    )


def _write_artifacts_exclusive(
    artifacts: Sequence[tuple[Path, bytes]],
) -> None:
    paths = tuple(Path(path) for path, _payload in artifacts)
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    handles = []
    created: list[Path] = []
    completed = False
    try:
        for path, payload in artifacts:
            handle = Path(path).open("xb")
            handles.append(handle)
            created.append(Path(path))
            handle.write(payload)
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
        for handle in handles:
            handle.close()
        if not completed:
            for path in created:
                path.unlink(missing_ok=True)


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
        if config.presentation_version is None:
            build = build_from_partition
        elif config.presentation_version == PUBLIC_API_LEGALITY_PRESENTATION_V1:
            build = build_from_partition_with_public_legality
        else:
            build = build_from_partition_with_native_compatibility
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

    snapshot = None
    snapshot_source = None
    snapshot_bytes = None
    if config.snapshot_output_path is not None:
        if not isinstance(corpus, NativeCompatibleSemanticCardCorpus):
            raise SemanticCardCompilationError(
                "snapshot export requires a native-compatible corpus"
            )
        snapshot_source = {
            "schema": NATIVE_CARD_SNAPSHOT_SOURCE_V1,
            "compilation_id": config.compilation_id,
            "presentation_version": NATIVE_COMPATIBLE_PRESENTATION_V1,
            "dataset_lock_sha256": config.dataset_lock_sha256,
            "construction_selection_sha256": config.construction_receipt_sha256,
            "tool_registry_sha256": config.tool_registry_sha256,
            "corpus_sha256": corpus.sha256,
            "minimum_compatibility_support": config.minimum_compatibility_support,
            "max_utf8_bytes": config.max_utf8_bytes,
        }
        if config.snapshot_value_view not in {
            None,
            NATIVE_SNAPSHOT_VALUE_VIEW_FULL,
        }:
            snapshot_source["value_view"] = config.snapshot_value_view
        snapshot = build_native_compatible_knowledge_snapshot(
            corpus,
            compilation_source=snapshot_source,
            value_view=config.snapshot_value_view,
            registry_rows=(
                registry
                if config.snapshot_value_view
                == NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_SCOPE_V1
                else None
            ),
        )
        snapshot_target_tools = {value.task_target for value in snapshot.values}
        if snapshot_target_tools != registry_tools:
            raise SemanticCardCompilationError(
                "native snapshot does not cover the complete public tool registry"
            )
        frozen_snapshot = snapshot.frozen_json()
        snapshot_bytes = (
            json.dumps(frozen_snapshot, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")

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
    if (
        snapshot is not None
        and snapshot_source is not None
        and snapshot_bytes is not None
    ):
        receipt["knowledge_snapshot"] = {
            "path": str(config.snapshot_output_path),
            "file_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
            "snapshot_sha256": snapshot.content_hash(),
            "source": {
                "metadata": snapshot_source,
                "sha256": snapshot.source_split_identity_hash,
            },
            "builder_policy_id": snapshot.builder_policy_id,
            "source_partition_role": snapshot.source_partition_role,
            "positive_content_facet_count": len(snapshot.facets),
            "key_text_row_count": len(snapshot.facets),
            "value_count": len(snapshot.values),
            "schema_only_tool_count": len(
                snapshot_target_tools - selected_target_tools
            ),
            "positive_key_fields": [
                "humanized_exact_tool_name",
                "choose_semantics",
                "public_role_guidance",
                "native_role_guidance",
            ],
            "avoid_semantics_in_positive_keys": False,
            "supplied_value": "full-native-compatible-tool-card",
            "encoded_vectors_written": 0,
        }
        if config.snapshot_value_view not in {
            None,
            NATIVE_SNAPSHOT_VALUE_VIEW_FULL,
        }:
            receipt["knowledge_snapshot"].update(
                {
                    "value_view": config.snapshot_value_view,
                    "positive_key_reuse": (
                        "unchanged-existing-mixed-tool-activation-and-parameter-role-guidance"
                    ),
                    "supplied_value": config.snapshot_value_view,
                }
            )
            if (
                config.snapshot_value_view
                == NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_CONTRAST_V1
            ):
                receipt["knowledge_snapshot"]["value_view_policy"] = (
                    _ACTIVATION_CONTRAST_POLICY_V1
                )
            elif (
                config.snapshot_value_view
                == NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_SCOPE_V1
            ):
                receipt["knowledge_snapshot"]["value_view_policy"] = (
                    _ACTIVATION_SCOPE_POLICY_V1
                )
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    if snapshot_bytes is None:
        _write_pair_exclusive(
            config.corpus_output_path,
            corpus.text.encode("utf-8"),
            config.receipt_output_path,
            receipt_bytes,
        )
    else:
        assert config.snapshot_output_path is not None
        _write_artifacts_exclusive(
            (
                (config.corpus_output_path, corpus.text.encode("utf-8")),
                (config.snapshot_output_path, snapshot_bytes),
                (config.receipt_output_path, receipt_bytes),
            )
        )
    return receipt


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile source-bound Audio2Tool semantic-card artifacts offline."
    )
    parser.add_argument("--config", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the shared Audio2Tool semantic-card compiler from strict JSON."""

    args = _cli_parser().parse_args(argv)
    config_path = Path(args.config)
    config = load_a2t_semantic_card_compilation_config(config_path)
    receipt = compile_a2t_semantic_card_artifacts(config)
    snapshot_receipt = receipt.get("knowledge_snapshot")
    summary: dict[str, object] = {
        "compilation_id": config.compilation_id,
        "config_path": str(config_path),
        "config_sha256": _sha256_file(config_path),
        "corpus_output_path": str(config.corpus_output_path),
        "receipt_output_path": str(config.receipt_output_path),
        "snapshot_output_path": (
            str(config.snapshot_output_path)
            if config.snapshot_output_path is not None
            else None
        ),
        "snapshot_value_view": (
            NATIVE_SNAPSHOT_VALUE_VIEW_FULL
            if config.snapshot_value_view is None
            else config.snapshot_value_view
        ),
        "tool_count": receipt["registry"]["tool_count"],
    }
    if isinstance(snapshot_receipt, Mapping):
        summary.update(
            {
                "snapshot_sha256": snapshot_receipt["snapshot_sha256"],
                "value_count": snapshot_receipt["value_count"],
            }
        )
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0


__all__ = [
    "A2tSemanticCardCompilationConfig",
    "COMPILATION_RECEIPT_SCHEMA",
    "MINIMUM_COMPATIBILITY_SUPPORT",
    "NATIVE_COMPATIBLE_PRESENTATION_V1",
    "NATIVE_CARD_SNAPSHOT_BUILDER_V1",
    "NATIVE_CARD_SNAPSHOT_SOURCE_V1",
    "NATIVE_SNAPSHOT_VALUE_VIEW_FULL",
    "NATIVE_SNAPSHOT_VALUE_VIEW_PARAMETER_MEANING",
    "NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION",
    "NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_CONTRAST_V1",
    "NATIVE_SNAPSHOT_VALUE_VIEW_TOOL_ACTIVATION_SCOPE_V1",
    "PUBLIC_API_LEGALITY_PRESENTATION_V1",
    "CompatibilityRule",
    "ExecutableSemanticCardCorpus",
    "NativeCompatibleSemanticCardCorpus",
    "NativeCompatibleToolSemanticCard",
    "PublicLegalitySemanticCardCorpus",
    "PublicLegalityToolSemanticCard",
    "SemanticCardCompilationError",
    "build_from_partition",
    "build_from_partition_with_native_compatibility",
    "build_from_partition_with_public_legality",
    "build_native_compatible_semantic_card_corpus",
    "build_native_compatible_knowledge_snapshot",
    "build_public_legality_semantic_card_corpus",
    "compile_a2t_semantic_card_artifacts",
    "load_a2t_semantic_card_compilation_config",
    "main",
    "validate_compiled_knowledge_snapshot",
    "derive_compatibility_rules",
]


if __name__ == "__main__":
    raise SystemExit(main())
