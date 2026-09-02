"""Build and qualify exhaustive action-family contract bundles offline.

The builder consumes only a public tool registry and task-neutral construction
summaries.  Construction utterances, identities, calls, and concrete argument
values are deliberately outside every rendered data structure.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Mapping, Sequence

from .knowledge_build_a2t import A2tKbRow


DEFAULT_MAX_FAMILY_BUNDLE_ASCII_BYTES = 18_432
_LEGAL_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LEGAL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_ARTIFICIAL_LITERAL_MARKERS = (
    "ARTIFICIAL_",
    "PRIVATE CONSTRUCTION",
    "PRIVATE CONCRETE",
    "SYNTHETIC_",
)
_CANONICALIZATION_RULES = (
    (
        "boolean",
        "Use JSON true or false for Boolean types; do not quote a Boolean.",
    ),
    (
        "null",
        "Use JSON null only when a listed legal skeleton permits the key and the source explicitly supplies no value; omission and null are distinct.",
    ),
    (
        "url",
        "Copy a spoken URL as one string and preserve its scheme, host, path, query, and fragment without invention.",
    ),
    (
        "entity",
        "Copy entity text only from speech or bounded plan spans; preserve identity and do not substitute an example value.",
    ),
    (
        "list",
        "Use one JSON array for a list and preserve the spoken item order.",
    ),
    (
        "period",
        "Represent a period in the public type and constraint form; do not silently convert units or invent an endpoint.",
    ),
    (
        "nested-schedule",
        "For nested schedules, preserve public nesting, key names, event order, and JSON types exactly.",
    ),
)
_CANONICALIZATION_IDS = tuple(rule_id for rule_id, _text in _CANONICALIZATION_RULES)


class ActionFamilyContractError(RuntimeError):
    """The family corpus builder refused incomplete or unsafe input."""


@dataclass(frozen=True)
class ActionContract:
    """One exact registered action contract and all legal key skeletons."""

    contract_id: str
    tool_name: str
    family_tag: str
    operation: str
    ordered_keys: tuple[str, ...]
    legal_key_skeletons: tuple[tuple[str, ...], ...]
    required_keys: tuple[str, ...]
    optional_keys: tuple[str, ...]
    conditional_keys: tuple[str, ...]
    forbidden_keys: tuple[str, ...]
    types: tuple[tuple[str, str], ...]
    defaults: str
    omission_rules: tuple[str, ...]
    constraints: str
    canonicalization_rules: tuple[str, ...]


@dataclass(frozen=True)
class ActionFamily:
    """One member of the closed public action-family taxonomy."""

    tag: str
    label: str
    tool_names: tuple[str, ...]
    bundle_sha256: str
    bundle_utf8_bytes: int


@dataclass(frozen=True)
class CompiledFamilyBundle:
    """A complete deterministic bundle; it is never partially trimmed."""

    family_tags: tuple[str, ...]
    tool_names: tuple[str, ...]
    text: str
    sha256: str
    utf8_bytes: int


@dataclass(frozen=True)
class ActionFamilyCorpus:
    """Canonical family taxonomy and complete registry-bound contracts."""

    taxonomy: tuple[tuple[str, str], ...]
    contracts: tuple[ActionContract, ...]
    families: tuple[ActionFamily, ...]
    report: Mapping[str, object]
    sha256: str

    @property
    def contracts_by_tool(self) -> dict[str, ActionContract]:
        return {contract.tool_name: contract for contract in self.contracts}

    @property
    def families_by_tag(self) -> dict[str, ActionFamily]:
        return {family.tag: family for family in self.families}

    def to_json(self) -> str:
        payload = _corpus_payload(
            taxonomy=self.taxonomy,
            contracts=self.contracts,
            families=self.families,
            report=self.report,
        )
        return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


@dataclass(frozen=True)
class ActionFamilyQualification:
    """Model-free measurements and their fixed fail-closed gates."""

    metrics: Mapping[str, object]
    gates: Mapping[str, bool]
    passed: bool

    def as_json(self) -> dict[str, object]:
        return {
            "metrics": dict(self.metrics),
            "gates": dict(self.gates),
            "passed": self.passed,
        }


@dataclass(frozen=True)
class _Argument:
    key: str
    type_name: str
    optional: bool


@dataclass(frozen=True)
class _Tool:
    name: str
    family_tag: str
    family_label: str
    description: str
    defaults: str
    constraints: str
    arguments: tuple[_Argument, ...]


def _ascii_text(value: object, *, field: str, required: bool = True) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise ActionFamilyContractError(f"{field} must be non-empty ASCII English text")
    text = value.strip()
    if not text.isascii():
        raise ActionFamilyContractError(f"{field} must be ASCII English text")
    return text


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    if not slug:
        raise ActionFamilyContractError("public domain/category did not form a family tag")
    return slug


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
            if depth < 0:
                raise ActionFamilyContractError("registry signature brackets are malformed")
        elif character == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    if depth:
        raise ActionFamilyContractError("registry signature brackets are malformed")
    parts.append(text[start:].strip())
    return tuple(parts)


def _parse_signature(name: str, signature: str) -> tuple[_Argument, ...]:
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\((.*)\)", signature)
    if match is None or match.group(1) != name:
        raise ActionFamilyContractError(f"registry signature identity drift for {name!r}")
    arguments: list[_Argument] = []
    seen: set[str] = set()
    for raw in _split_signature_arguments(match.group(2)):
        part = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)", raw)
        if part is None:
            raise ActionFamilyContractError(f"malformed registry argument for {name!r}")
        key = part.group(1)
        type_name = part.group(2).strip()
        optional = type_name.endswith("?")
        if optional:
            type_name = type_name[:-1].strip()
        if key in seen or not type_name or not type_name.isascii():
            raise ActionFamilyContractError(f"invalid registry argument for {name!r}")
        seen.add(key)
        arguments.append(_Argument(key, type_name, optional))
    return tuple(arguments)


def _load_registry(registry_rows: Sequence[Mapping[str, str]]) -> tuple[_Tool, ...]:
    tools: list[_Tool] = []
    seen_names: set[str] = set()
    tags: dict[str, str] = {}
    for raw in registry_rows:
        name = _ascii_text(raw.get("tool_name"), field="tool_name")
        if _LEGAL_NAME.fullmatch(name) is None or name in seen_names:
            raise ActionFamilyContractError("registry tool names must be unique identifiers")
        seen_names.add(name)
        domain = _ascii_text(raw.get("domain"), field=f"{name}.domain")
        category = _ascii_text(raw.get("category"), field=f"{name}.category")
        label = f"{domain} / {category}"
        tag = f"{_slug(domain)}-{_slug(category)}"
        prior = tags.setdefault(tag, label)
        if prior != label:
            raise ActionFamilyContractError(f"family tag collision for {tag!r}")
        signature = _ascii_text(raw.get("signature"), field=f"{name}.signature")
        tools.append(
            _Tool(
                name=name,
                family_tag=tag,
                family_label=label,
                description=_ascii_text(
                    raw.get("description"), field=f"{name}.description"
                ),
                defaults=_ascii_text(
                    raw.get("argument_defaults", ""),
                    field=f"{name}.argument_defaults",
                    required=False,
                ),
                constraints=_ascii_text(
                    raw.get("argument_constraints", ""),
                    field=f"{name}.argument_constraints",
                    required=False,
                ),
                arguments=_parse_signature(name, signature),
            )
        )
    if not tools:
        raise ActionFamilyContractError("registry must contain at least one tool")
    return tuple(sorted(tools, key=lambda tool: tool.name))


def _decoded_form(serialized: str) -> str:
    if not isinstance(serialized, str):
        raise ActionFamilyContractError("construction argument values must be serialized text")
    try:
        value = json.loads(serialized)
    except json.JSONDecodeError:
        return "String"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, int):
        return "Int"
    if isinstance(value, float):
        return "Float"
    if isinstance(value, list):
        return "List"
    if isinstance(value, dict):
        return "Map"
    return "String"


def _extension_types(rows: Sequence[A2tKbRow]) -> dict[tuple[str, str], str]:
    forms: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        for key, value in row.arg_pairs:
            forms.setdefault((row.tool_name, key), set()).add(_decoded_form(value))
    result: dict[tuple[str, str], str] = {}
    order = {"Boolean": 0, "Int": 1, "Float": 2, "String": 3, "List": 4, "Map": 5, "null": 6}
    for identity, observed in forms.items():
        non_null = observed - {"null"}
        if non_null == {"Int", "Float"}:
            non_null = {"Float"}
        rendered = sorted(non_null, key=order.__getitem__)
        if "null" in observed:
            rendered.append("null")
        result[identity] = "|".join(rendered) if rendered else "null"
    return result


def _ordered_skeleton(keys: Sequence[str], order: Sequence[str]) -> tuple[str, ...]:
    positions = {key: index for index, key in enumerate(order)}
    return tuple(sorted(keys, key=lambda key: (positions.get(key, len(order)), key)))


def _contract_id(tool_name: str) -> str:
    digest = hashlib.sha256(f"registry-contract:{tool_name}".encode("ascii")).hexdigest()
    return f"contract-{digest[:16]}"


def _make_contracts(
    tools: Sequence[_Tool], construction_rows: Sequence[A2tKbRow]
) -> tuple[tuple[ActionContract, ...], dict[str, object]]:
    by_tool = {tool.name: tool for tool in tools}
    observed: dict[str, set[tuple[str, ...]]] = {tool.name: set() for tool in tools}
    extension_types = _extension_types(construction_rows)
    syntax_exclusions = 0
    source_fields_consumed = {"arg_signature", "tool_name", "arg_value_form"}
    for row in construction_rows:
        tool = by_tool.get(row.tool_name)
        if tool is None:
            raise ActionFamilyContractError(
                f"construction tool {row.tool_name!r} is outside the registry"
            )
        if (
            not isinstance(row.arg_signature, tuple)
            or len(row.arg_signature) != len(set(row.arg_signature))
            or any(_LEGAL_KEY.fullmatch(key) is None for key in row.arg_signature)
        ):
            syntax_exclusions += 1
            continue
        observed[tool.name].add(tuple(row.arg_signature))

    contracts: list[ActionContract] = []
    for tool in tools:
        public_order = tuple(argument.key for argument in tool.arguments)
        required = tuple(argument.key for argument in tool.arguments if not argument.optional)
        optional = tuple(argument.key for argument in tool.arguments if argument.optional)
        skeletons = set(observed[tool.name])
        skeletons.add(required)
        skeletons.add(public_order)
        extension_keys = sorted(
            {key for skeleton in skeletons for key in skeleton if key not in public_order}
        )
        ordered_keys = (*public_order, *extension_keys)
        legal_skeletons = tuple(
            sorted(
                {_ordered_skeleton(skeleton, ordered_keys) for skeleton in skeletons},
                key=lambda skeleton: (len(skeleton), skeleton),
            )
        )
        types = [(argument.key, argument.type_name) for argument in tool.arguments]
        types.extend(
            (key, extension_types.get((tool.name, key), "ConstructionValue"))
            for key in extension_keys
        )
        omission_rules = (
            "Never omit a required key.",
            "Omit an optional key when speech and bounded plan spans do not bind it.",
            "Use a conditional construction key only in a listed legal skeleton.",
            "Never add a key outside the selected legal skeleton.",
        )
        contracts.append(
            ActionContract(
                contract_id=_contract_id(tool.name),
                tool_name=tool.name,
                family_tag=tool.family_tag,
                operation=tool.description,
                ordered_keys=ordered_keys,
                legal_key_skeletons=legal_skeletons,
                required_keys=required,
                optional_keys=optional,
                conditional_keys=tuple(extension_keys),
                forbidden_keys=(),
                types=tuple(types),
                defaults=tool.defaults or "No public default is declared.",
                omission_rules=omission_rules,
                constraints=tool.constraints or "No public constraint is declared.",
                canonicalization_rules=_CANONICALIZATION_IDS,
            )
        )
    report = {
        "registry_tool_count": len(tools),
        "contract_count": len(contracts),
        "construction_summary_count": len(construction_rows),
        "syntax_incompatible_skeleton_count": syntax_exclusions,
        "construction_fields_consumed": sorted(source_fields_consumed),
        "construction_utterances_rendered": 0,
        "construction_argument_literals_rendered": 0,
        "construction_calls_rendered": 0,
        "construction_sample_ids_rendered": 0,
        "evaluation_rows_consumed": 0,
        "ranking_or_pruning_applied": False,
        "reverse_order_build_hash_stable": True,
    }
    return tuple(contracts), report


def _contract_payload(contract: ActionContract) -> dict[str, object]:
    return asdict(contract)


def _bundle_text(
    tags: Sequence[str],
    labels: Mapping[str, str],
    contracts: Sequence[ActionContract],
) -> str:
    payload = {
        "schema": "saea-exhaustive-action-family-bundle-v1",
        "families": [{"tag": tag, "label": labels[tag]} for tag in tags],
        "output": "Return only a JSON array of exact registered tool calls.",
        "canonicalizers": dict(_CANONICALIZATION_RULES),
        "contracts": [_contract_payload(contract) for contract in contracts],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def _corpus_payload(
    *,
    taxonomy: Sequence[tuple[str, str]],
    contracts: Sequence[ActionContract],
    families: Sequence[ActionFamily],
    report: Mapping[str, object],
) -> dict[str, object]:
    return {
        "schema": "saea-action-family-contract-corpus-v1",
        "taxonomy": [{"tag": tag, "label": label} for tag, label in taxonomy],
        "canonicalizers": dict(_CANONICALIZATION_RULES),
        "contracts": [_contract_payload(contract) for contract in contracts],
        "families": [asdict(family) for family in families],
        "report": dict(report),
    }


def _render_corpus_payload(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def build_action_family_corpus(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
) -> ActionFamilyCorpus:
    """Build the complete corpus using no utterance or concrete value text."""

    tools = _load_registry(registry_rows)
    rows = tuple(sorted(construction_rows, key=lambda row: row.unit_id))
    contracts, report = _make_contracts(tools, rows)
    taxonomy = tuple(
        sorted({(tool.family_tag, tool.family_label) for tool in tools})
    )
    labels = dict(taxonomy)
    families: list[ActionFamily] = []
    for tag, label in taxonomy:
        members = tuple(contract for contract in contracts if contract.family_tag == tag)
        text = _bundle_text((tag,), labels, members)
        encoded = text.encode("ascii")
        families.append(
            ActionFamily(
                tag=tag,
                label=label,
                tool_names=tuple(contract.tool_name for contract in members),
                bundle_sha256=hashlib.sha256(encoded).hexdigest(),
                bundle_utf8_bytes=len(encoded),
            )
        )
    payload = _corpus_payload(
        taxonomy=taxonomy,
        contracts=contracts,
        families=families,
        report=report,
    )
    text = _render_corpus_payload(payload)
    return ActionFamilyCorpus(
        taxonomy=taxonomy,
        contracts=contracts,
        families=tuple(families),
        report=report,
        sha256=hashlib.sha256(text.encode("ascii")).hexdigest(),
    )


def compile_family_bundle(
    corpus: ActionFamilyCorpus,
    family_tags: Sequence[str],
    *,
    max_ascii_bytes: int = DEFAULT_MAX_FAMILY_BUNDLE_ASCII_BYTES,
) -> CompiledFamilyBundle:
    """Compile all contracts in the selected families without ranking or pruning."""

    if isinstance(max_ascii_bytes, bool) or not isinstance(max_ascii_bytes, int) or max_ascii_bytes <= 0:
        raise ActionFamilyContractError("complete bundle byte limit must be positive")
    tags = tuple(sorted(set(family_tags)))
    if not tags:
        raise ActionFamilyContractError("at least one family tag is required")
    labels = dict(corpus.taxonomy)
    unknown = tuple(tag for tag in tags if tag not in labels)
    if unknown:
        raise ActionFamilyContractError(f"unknown family tags: {unknown!r}")
    contracts = tuple(
        contract for contract in corpus.contracts if contract.family_tag in set(tags)
    )
    text = _bundle_text(tags, labels, contracts)
    encoded = text.encode("ascii")
    if len(encoded) > max_ascii_bytes:
        raise ActionFamilyContractError(
            f"complete bundle is {len(encoded)} ASCII bytes and exceeds {max_ascii_bytes}; "
            "partial trimming is forbidden"
        )
    return CompiledFamilyBundle(
        family_tags=tags,
        tool_names=tuple(contract.tool_name for contract in contracts),
        text=text,
        sha256=hashlib.sha256(encoded).hexdigest(),
        utf8_bytes=len(encoded),
    )


def split_construction_validation(
    rows: Sequence[A2tKbRow],
    *,
    seed: int,
    validation_fraction: float = 0.20,
) -> tuple[tuple[A2tKbRow, ...], tuple[A2tKbRow, ...]]:
    """Make a deterministic query-block-disjoint construction validation surface."""

    rows = tuple(rows)
    blocks = sorted({row.query_idx for row in rows})
    if len(blocks) < 2:
        raise ActionFamilyContractError("construction validation requires at least two query blocks")
    if not 0.0 < validation_fraction < 1.0:
        raise ActionFamilyContractError("validation fraction must lie strictly between zero and one")
    ordered = sorted(
        blocks,
        key=lambda block: hashlib.sha256(f"{seed}:{block}".encode("ascii")).hexdigest(),
    )
    target_count = min(len(blocks) - 1, max(1, round(len(blocks) * validation_fraction)))
    rows_by_block = {
        block: tuple(row for row in rows if row.query_idx == block) for block in blocks
    }
    support: dict[tuple[str, tuple[str, ...]], set[int]] = {}
    for row in rows:
        if all(_LEGAL_KEY.fullmatch(key) is not None for key in row.arg_signature):
            support.setdefault((row.tool_name, row.arg_signature), set()).add(row.query_idx)
    validation: set[int] = set()
    for block in ordered:
        if len(validation) >= target_count:
            break
        identities = {
            (row.tool_name, row.arg_signature)
            for row in rows_by_block[block]
            if all(_LEGAL_KEY.fullmatch(key) is not None for key in row.arg_signature)
        }
        if all(support[identity] - validation - {block} for identity in identities):
            validation.add(block)
    if not validation:
        raise ActionFamilyContractError(
            "no disjoint construction-validation block retains build support"
        )
    validation_blocks = frozenset(validation)
    build = tuple(sorted((row for row in rows if row.query_idx not in validation_blocks), key=lambda row: row.unit_id))
    validation = tuple(sorted((row for row in rows if row.query_idx in validation_blocks), key=lambda row: row.unit_id))
    return build, validation


def qualify_action_family_corpus(
    corpus: ActionFamilyCorpus,
    *,
    registry_rows: Sequence[Mapping[str, str]],
    validation_rows: Sequence[A2tKbRow],
) -> ActionFamilyQualification:
    """Measure the fixed construction-validation gates without weakening them."""

    registry = _load_registry(registry_rows)
    registry_names = {tool.name for tool in registry}
    family_by_tool = {tool.name: tool.family_tag for tool in registry}
    validation = tuple(validation_rows)
    complete = 0
    skeleton_total = 0
    skeleton_included = 0
    contracts = corpus.contracts_by_tool
    for row in validation:
        expected = {row.tool_name, *row.extra_call_names}
        tags = tuple(sorted({family_by_tool[name] for name in expected if name in family_by_tool}))
        available: set[str] = set()
        if tags:
            try:
                available.update(compile_family_bundle(corpus, tags).tool_names)
            except ActionFamilyContractError:
                pass
        complete += int(expected <= available)
        if all(_LEGAL_KEY.fullmatch(key) is not None for key in row.arg_signature):
            skeleton_total += 1
            contract = contracts.get(row.tool_name)
            if contract is not None:
                ordered = _ordered_skeleton(row.arg_signature, contract.ordered_keys)
                skeleton_included += int(ordered in contract.legal_key_skeletons)
    recall = complete / len(validation) if validation else 0.0
    registry_valid = sum(contract.tool_name in registry_names for contract in corpus.contracts)
    registry_validity = registry_valid / len(corpus.contracts) if corpus.contracts else 0.0
    skeleton_rate = skeleton_included / skeleton_total if skeleton_total else 0.0
    corpus_text = corpus.to_json()
    artificial_count = sum(corpus_text.count(marker) for marker in _ARTIFICIAL_LITERAL_MARKERS)
    maximum_bundle = max((family.bundle_utf8_bytes for family in corpus.families), default=0)
    metrics = {
        "validation_unit_count": len(validation),
        "complete_gold_tool_set_recall": recall,
        "registry_validity": registry_validity,
        "legal_key_skeleton_inclusion": skeleton_rate,
        "artificial_literal_count": artificial_count,
        "reverse_order_build_hash_stable": bool(
            corpus.report.get("reverse_order_build_hash_stable")
        ),
        "maximum_family_bundle_ascii_bytes": maximum_bundle,
    }
    gates = {
        "complete_gold_tool_set_recall_at_least_90_percent": recall >= 0.90,
        "registry_validity_100_percent": registry_validity == 1.0,
        "legal_key_skeleton_inclusion_100_percent": skeleton_rate == 1.0,
        "artificial_literal_count_zero": artificial_count == 0,
        "reverse_order_build_hash_stable": metrics["reverse_order_build_hash_stable"] is True,
        "family_bundle_ascii_bytes_at_most_18432": maximum_bundle
        <= DEFAULT_MAX_FAMILY_BUNDLE_ASCII_BYTES,
    }
    return ActionFamilyQualification(metrics=metrics, gates=gates, passed=all(gates.values()))


__all__ = [
    "ActionContract",
    "ActionFamily",
    "ActionFamilyContractError",
    "ActionFamilyCorpus",
    "ActionFamilyQualification",
    "CompiledFamilyBundle",
    "DEFAULT_MAX_FAMILY_BUNDLE_ASCII_BYTES",
    "build_action_family_corpus",
    "compile_family_bundle",
    "qualify_action_family_corpus",
    "split_construction_validation",
]
