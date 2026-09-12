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
    build_executable_semantic_card_corpus,
)
from .errors import RailsError
from .knowledge_build_a2t import A2tKbRow, a2t_pool_rows

MINIMUM_COMPATIBILITY_SUPPORT = 2
COMPILATION_RECEIPT_SCHEMA = "saea-a2t-semantic-card-compilation-receipt-v1"
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
        corpus, compiler_report = build_from_partition(
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
    "CompatibilityRule",
    "ExecutableSemanticCardCorpus",
    "SemanticCardCompilationError",
    "build_from_partition",
    "compile_a2t_semantic_card_artifacts",
    "derive_compatibility_rules",
]
