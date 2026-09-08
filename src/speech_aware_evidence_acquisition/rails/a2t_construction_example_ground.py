"""Build query-independent Audio2Tool construction-example family ground.

The builder joins construction-only :class:`A2tKbRow` language with the
already-frozen G5 family/contract mapping.  It reads no manifests, audio,
evaluation fields, model output, scorer, or network service.  Only a row's
final invocation ``text`` is eligible for rendering; for tier 7 that field is
already the final ``user_request`` selected by ``knowledge_build_a2t``.

Concrete construction argument values are used only to locate spans that can
be replaced by named placeholders.  A row whose complete primary-call value
set cannot be aligned is excluded rather than rendered approximately.  The
frozen registry contains one never-primary/no-gold tool, so registry-only
tools intentionally receive zero patterns; the aggregate report makes this
data-API limitation explicit.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``build_construction_example_family_ground`` is catalog id
``saea-tool-a2t-construction-example-ground-v1`` on the ``SUPPLY`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

from .knowledge_build_a2t import A2tKbRow, TIERS
from .probes.a2t_g6_corpus_renderer import G6CorpusRenderer, G6CorpusRendererError


DEFAULT_MAX_EXAMPLES_PER_TOOL = 3
DEFAULT_MAX_FAMILY_ASCII_BYTES = 24_576
DEFAULT_MAX_CORPUS_ASCII_BYTES = 524_288


class ConstructionExampleGroundError(ValueError):
    """The family-ground builder refused unsafe or inconsistent input."""


@dataclass(frozen=True)
class ConstructionLanguagePattern:
    """One positive primary-call pattern with construction values removed."""

    tier: str
    text: str
    placeholders: tuple[str, ...]


@dataclass(frozen=True)
class ConstructionExampleTool:
    """One exact G5 tool contract plus zero to three safe language patterns."""

    tool_name: str
    operation: str
    types: tuple[tuple[str, str], ...]
    legal_key_skeletons: tuple[tuple[str, ...], ...]
    patterns: tuple[ConstructionLanguagePattern, ...]


@dataclass(frozen=True)
class ConstructionExampleFamilyBundle:
    """A complete family-local surface suitable for one later SCAN prompt."""

    family_tag: str
    family_label: str
    tools: tuple[ConstructionExampleTool, ...]
    text: str
    sha256: str
    ascii_bytes: int

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Return included exact tool names in stable order."""

        return tuple(tool.tool_name for tool in self.tools)

    @property
    def example_count(self) -> int:
        """Return the number of selected construction patterns."""

        return sum(len(tool.patterns) for tool in self.tools)

    @property
    def tools_by_name(self) -> dict[str, ConstructionExampleTool]:
        """Return a fresh exact-name lookup without exposing mutable state."""

        return {tool.tool_name: tool for tool in self.tools}


@dataclass(frozen=True)
class ConstructionExampleGround:
    """All complete family bundles and their aggregate receipt/report."""

    bundles: tuple[ConstructionExampleFamilyBundle, ...]
    text: str
    sha256: str
    report: Mapping[str, object]
    receipt: Mapping[str, object]

    @property
    def bundles_by_family(self) -> dict[str, ConstructionExampleFamilyBundle]:
        """Return a fresh family-tag lookup without exposing mutable state."""

        return {bundle.family_tag: bundle for bundle in self.bundles}

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Return every included exact tool name in family/tool order."""

        return tuple(name for bundle in self.bundles for name in bundle.tool_names)


@dataclass(frozen=True)
class _FrozenContract:
    family_tag: str
    tool_name: str
    operation: str
    types: tuple[tuple[str, str], ...]
    legal_key_skeletons: tuple[tuple[str, ...], ...]


_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_SPACE = re.compile(r"\s+")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _reject_json_constant(value: str) -> None:
    raise ValueError(value)


def _require_positive_int(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConstructionExampleGroundError(f"{label} must be a positive integer")
    return value


def _ascii_text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or not value.isascii():
        raise ConstructionExampleGroundError(f"{label} must be non-empty ASCII text")
    return value.strip()


def _load_frozen_mapping(
    path: Path,
) -> tuple[str, dict[str, str], dict[str, tuple[_FrozenContract, ...]]]:
    """Load only fields needed from a fully G6-validated frozen G5 corpus."""

    source = Path(path)
    try:
        renderer = G6CorpusRenderer.from_path(source)
        raw = source.read_bytes()
        document = json.loads(raw.decode("ascii"))
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        G6CorpusRendererError,
    ) as error:
        raise ConstructionExampleGroundError(
            f"invalid frozen G5 corpus: {error}"
        ) from error
    taxonomy = document["taxonomy"]
    contracts = document["contracts"]
    labels = {
        _ascii_text(row["tag"], label="family tag"): _ascii_text(
            row["label"], label="family label"
        )
        for row in taxonomy
    }
    grouped: dict[str, list[_FrozenContract]] = {tag: [] for tag in labels}
    for row in contracts:
        tag = _ascii_text(row["family_tag"], label="contract family tag")
        tool_name = _ascii_text(row["tool_name"], label="tool name")
        operation = _ascii_text(row["operation"], label=f"{tool_name} operation")
        typed = tuple(
            (
                _ascii_text(item[0], label=f"{tool_name} key"),
                _ascii_text(item[1], label=f"{tool_name} type"),
            )
            for item in row["types"]
        )
        skeletons = tuple(
            tuple(_ascii_text(key, label=f"{tool_name} legal key") for key in item)
            for item in row["legal_key_skeletons"]
        )
        grouped[tag].append(
            _FrozenContract(tag, tool_name, operation, typed, skeletons)
        )
    stable = {
        tag: tuple(sorted(items, key=lambda item: item.tool_name))
        for tag, items in sorted(grouped.items())
    }
    if renderer.corpus_sha256 != _sha256(raw):  # defensive identity assertion
        raise ConstructionExampleGroundError("frozen G5 corpus identity drift")
    return renderer.corpus_sha256, dict(sorted(labels.items())), stable


def _validate_boundary(
    rows: Sequence[A2tKbRow],
    *,
    forbidden_query_blocks: Collection[int],
    forbidden_source_ids: Collection[str],
) -> tuple[tuple[int, ...], tuple[str, ...], int]:
    if isinstance(forbidden_query_blocks, (str, bytes)) or not isinstance(
        forbidden_query_blocks, Collection
    ):
        raise ConstructionExampleGroundError(
            "forbidden query blocks must be a collection"
        )
    blocks = tuple(sorted(forbidden_query_blocks))
    if any(isinstance(value, bool) or not isinstance(value, int) for value in blocks):
        raise ConstructionExampleGroundError(
            "forbidden query blocks must contain integers"
        )
    if isinstance(forbidden_source_ids, (str, bytes)) or not isinstance(
        forbidden_source_ids, Collection
    ):
        raise ConstructionExampleGroundError(
            "forbidden source ids must be a collection"
        )
    sources = tuple(sorted(forbidden_source_ids))
    if any(not isinstance(value, str) or not value for value in sources):
        raise ConstructionExampleGroundError("forbidden source ids must contain text")
    block_overlap = sorted({row.query_idx for row in rows} & set(blocks))
    if block_overlap:
        raise ConstructionExampleGroundError("construction query-block overlap")
    # One carrier sample may legitimately support multiple construction rows
    # (notably multi-call decompositions).  Sample identities therefore form a
    # many-to-one overlap-check set.  ``unit_id`` occupies a distinct internal
    # namespace and its uniqueness is enforced separately by the builder.
    row_source_ids = {source_id for row in rows for source_id in row.sample_ids}
    if row_source_ids & set(sources):
        raise ConstructionExampleGroundError("construction source overlap")
    return blocks, sources, len(row_source_ids)


def _json_leaves(value: object) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        return tuple(
            leaf
            for key in sorted(value, key=str)
            for item in (str(key), value[key])
            for leaf in _json_leaves(item)
        )
    if isinstance(value, list):
        return tuple(leaf for item in value for leaf in _json_leaves(item))
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("true" if value else "false",)
    if isinstance(value, (int, float)):
        return (json.dumps(value, allow_nan=False),)
    if isinstance(value, str):
        return (value,)
    return ()


def _value_atoms(serialized: str) -> tuple[tuple[str, ...], ...]:
    """Return alternative surface forms for every concrete value atom."""

    if not isinstance(serialized, str) or not serialized:
        return ()
    try:
        decoded = json.loads(serialized, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError):
        leaves = (serialized,)
    else:
        leaves = _json_leaves(decoded)
    atoms: list[tuple[str, ...]] = []
    for leaf in leaves:
        if not leaf.strip():
            return ()
        variants = {leaf}
        separated = re.sub(r"[_-]+", " ", leaf)
        if separated != leaf:
            variants.add(separated)
        atoms.append(
            tuple(
                sorted(
                    variants,
                    key=lambda item: (-len(item), item.casefold(), item),
                )
            )
        )
    return tuple(atoms)


def _surface_pattern(surface: str) -> re.Pattern[str]:
    pieces = re.split(r"[ _-]+", surface)
    body = r"[ _-]+".join(re.escape(piece) for piece in pieces)
    left = r"(?<![A-Za-z0-9])" if surface[0].isalnum() else ""
    right = r"(?![A-Za-z0-9])" if surface[-1].isalnum() else ""
    return re.compile(left + body + right, re.IGNORECASE)


def _delexicalize(row: A2tKbRow) -> ConstructionLanguagePattern | None:
    text = _ascii_text(row.text, label="construction row text")
    if row.tier not in TIERS:
        raise ConstructionExampleGroundError("construction row has an unknown tier")
    if (
        not isinstance(row.arg_signature, tuple)
        or len(row.arg_signature) != len(set(row.arg_signature))
        or any(_IDENTIFIER.fullmatch(key) is None for key in row.arg_signature)
        or tuple(key for key, _value in row.arg_pairs) != row.arg_signature
    ):
        raise ConstructionExampleGroundError(
            "construction row argument keys are malformed"
        )
    rendered = text
    aligned_keys: list[str] = []
    replacements: list[tuple[str, tuple[tuple[str, ...], ...]]] = []
    for key, value in row.arg_pairs:
        atoms = _value_atoms(value)
        if atoms:
            replacements.append((key, atoms))
    replacements.sort(
        key=lambda item: (
            -max(len(surface) for atom in item[1] for surface in atom),
            item[0],
        )
    )
    for key, atoms in replacements:
        placeholder = "{" + key + "}"
        key_aligned = False
        for alternatives in atoms:
            match: re.Match[str] | None = None
            selected: re.Pattern[str] | None = None
            for surface in alternatives:
                candidate = _surface_pattern(surface)
                match = candidate.search(rendered)
                if match is not None:
                    selected = candidate
                    break
            if match is None or selected is None:
                continue
            rendered = selected.sub(placeholder, rendered)
            key_aligned = True
        if key_aligned:
            aligned_keys.append(key)
    rendered = _SPACE.sub(" ", rendered).strip()
    if not rendered or not rendered.isascii():
        return None
    if any("{" + key + "}" not in rendered for key in aligned_keys):
        return None
    for _key, value in row.arg_pairs:
        for alternatives in _value_atoms(value):
            if any(
                _surface_pattern(surface).search(rendered) for surface in alternatives
            ):
                return None
    return ConstructionLanguagePattern(
        tier=row.tier,
        text=rendered,
        placeholders=tuple(key for key in row.arg_signature if key in aligned_keys),
    )


def _tokens(pattern: ConstructionLanguagePattern) -> frozenset[str]:
    return frozenset(re.findall(r"[A-Za-z]+", pattern.text.casefold()))


def _distance(
    left: ConstructionLanguagePattern, right: ConstructionLanguagePattern
) -> Fraction:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    union = left_tokens | right_tokens
    return Fraction(len(union - (left_tokens & right_tokens)), len(union) or 1)


def _select_diverse(
    candidates: Collection[ConstructionLanguagePattern], *, limit: int
) -> tuple[ConstructionLanguagePattern, ...]:
    remaining = sorted(
        set(candidates),
        key=lambda item: (
            len(_tokens(item)),
            item.text.casefold(),
            item.text,
            item.tier,
        ),
    )
    if not remaining:
        return ()
    selected = [remaining.pop(0)]
    while remaining and len(selected) < limit:
        scores = {
            candidate: (
                int(candidate.tier not in {item.tier for item in selected}),
                min(_distance(candidate, item) for item in selected),
            )
            for candidate in remaining
        }
        best_score = max(scores.values())
        best = min(
            (candidate for candidate in remaining if scores[candidate] == best_score),
            key=lambda item: (item.text.casefold(), item.text, item.tier),
        )
        selected.append(best)
        remaining.remove(best)
    return tuple(selected)


def _source_rows_hash(rows: Sequence[A2tKbRow]) -> str:
    payload = [
        {
            "arg_pairs": list(row.arg_pairs),
            "arg_signature": list(row.arg_signature),
            "query_idx": row.query_idx,
            "sample_ids": sorted(row.sample_ids),
            "text": row.text,
            "tier": row.tier,
            "tool_name": row.tool_name,
            "unit_id": row.unit_id,
        }
        for row in sorted(
            rows, key=lambda item: (item.unit_id, item.tier, item.query_idx)
        )
    ]
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _sha256(raw.encode("ascii"))


def _identity_hash(values: Collection[object]) -> str:
    raw = json.dumps(sorted(values), separators=(",", ":"), ensure_ascii=True)
    return _sha256(raw.encode("ascii"))


def _render_family(
    family_tag: str,
    family_label: str,
    tools: tuple[ConstructionExampleTool, ...],
) -> str:
    lines = [
        "CONSTRUCTION-EXAMPLE FAMILY GROUND",
        f"Family: {family_label} ({family_tag})",
        "Use only as query-independent positive language and exact interface evidence.",
        "Family tool meanings (co-located sibling contrast):",
    ]
    lines.extend(f"- {tool.tool_name}: {tool.operation}" for tool in tools)
    for tool in tools:
        siblings = ", ".join(item.tool_name for item in tools if item != tool) or "none"
        types = "; ".join(f"{key}: {kind}" for key, kind in tool.types) or "none"
        skeletons = " | ".join(
            "{" + ", ".join(keys) + "}" for keys in tool.legal_key_skeletons
        )
        lines.extend(
            (
                "",
                f"Tool: {tool.tool_name}",
                f"Choose when: {tool.operation}",
                f"Sibling operation contrast: {siblings}",
                f"Key types: {types}",
                f"Legal key skeletons: {skeletons}",
                "Positive construction language patterns:",
            )
        )
        if tool.patterns:
            lines.extend(
                f"- [{pattern.tier}] {pattern.text}" for pattern in tool.patterns
            )
        else:
            lines.append("- none: no positive construction row is available")
    return "\n".join(lines) + "\n"


def build_construction_example_family_ground(
    construction_rows: Sequence[A2tKbRow],
    g5_corpus_path: Path,
    *,
    forbidden_query_blocks: Collection[int],
    forbidden_source_ids: Collection[str],
    max_examples_per_tool: int = DEFAULT_MAX_EXAMPLES_PER_TOOL,
    max_family_ascii_bytes: int = DEFAULT_MAX_FAMILY_ASCII_BYTES,
    max_total_ascii_bytes: int = DEFAULT_MAX_CORPUS_ASCII_BYTES,
) -> ConstructionExampleGround:
    """Build complete deterministic family bundles from disjoint construction rows.

    ``forbidden_query_blocks`` and ``forbidden_source_ids`` are mandatory so a
    caller must state both disjointness boundaries even when either set is empty.
    The function rejects overlap before rendering any row-derived language.
    """

    if isinstance(construction_rows, (str, bytes)) or not isinstance(
        construction_rows, Sequence
    ):
        raise ConstructionExampleGroundError("construction rows must be a sequence")
    if (
        isinstance(max_examples_per_tool, bool)
        or not isinstance(max_examples_per_tool, int)
        or not 1 <= max_examples_per_tool <= 3
    ):
        raise ConstructionExampleGroundError(
            "max_examples_per_tool must be between 1 and 3"
        )
    family_cap = _require_positive_int(max_family_ascii_bytes, label="family byte cap")
    corpus_cap = _require_positive_int(max_total_ascii_bytes, label="corpus byte cap")
    rows = tuple(construction_rows)
    if any(not isinstance(row, A2tKbRow) for row in rows):
        raise ConstructionExampleGroundError("construction rows must use A2tKbRow")
    blocks, sources, source_identity_count = _validate_boundary(
        rows,
        forbidden_query_blocks=forbidden_query_blocks,
        forbidden_source_ids=forbidden_source_ids,
    )
    unit_ids = [row.unit_id for row in rows]
    if len(unit_ids) != len(set(unit_ids)):
        raise ConstructionExampleGroundError("construction unit ids are duplicated")

    g5_hash, labels, contracts_by_family = _load_frozen_mapping(g5_corpus_path)
    by_tool = {
        contract.tool_name: contract
        for contracts in contracts_by_family.values()
        for contract in contracts
    }
    patterns_by_tool: dict[str, set[ConstructionLanguagePattern]] = {
        name: set() for name in by_tool
    }
    used_tools: set[str] = set()
    rejected_rows: Counter[str] = Counter()
    rejected_rows_by_tool: dict[str, Counter[str]] = {
        name: Counter() for name in by_tool
    }
    observed_legal_skeletons: set[tuple[str, tuple[str, ...]]] = set()
    for row in rows:
        contract = by_tool.get(row.tool_name)
        if contract is None:
            raise ConstructionExampleGroundError(
                f"construction tool {row.tool_name!r} is outside frozen G5"
            )
        used_tools.add(row.tool_name)
        if not isinstance(row.text, str) or not row.text.strip():
            rejected_rows["empty_construction_text"] += 1
            rejected_rows_by_tool[row.tool_name]["empty_construction_text"] += 1
            continue
        if not row.text.isascii():
            rejected_rows["non_ascii_construction_text"] += 1
            rejected_rows_by_tool[row.tool_name]["non_ascii_construction_text"] += 1
            continue
        if (
            not isinstance(row.arg_signature, tuple)
            or len(row.arg_signature) != len(set(row.arg_signature))
            or any(_IDENTIFIER.fullmatch(key) is None for key in row.arg_signature)
        ):
            rejected_rows["malformed_argument_key_skeleton"] += 1
            rejected_rows_by_tool[row.tool_name]["malformed_argument_key_skeleton"] += 1
            continue
        matching_skeletons = tuple(
            skeleton
            for skeleton in contract.legal_key_skeletons
            if frozenset(skeleton) == frozenset(row.arg_signature)
        )
        if len(matching_skeletons) != 1:
            rejected_rows["g5_incompatible_key_skeleton"] += 1
            rejected_rows_by_tool[row.tool_name]["g5_incompatible_key_skeleton"] += 1
            continue
        observed_legal_skeletons.add((row.tool_name, matching_skeletons[0]))
        pattern = _delexicalize(row)
        if pattern is None:
            rejected_rows["unaligned_argument_values"] += 1
            rejected_rows_by_tool[row.tool_name]["unaligned_argument_values"] += 1
            continue
        patterns_by_tool[row.tool_name].add(pattern)
    uncovered = sorted(name for name in used_tools if not patterns_by_tool[name])
    if uncovered:
        raise ConstructionExampleGroundError(
            "construction-used tools lack a safely aligned positive pattern: "
            + ", ".join(uncovered)
        )

    selected = {
        name: _select_diverse(patterns, limit=max_examples_per_tool)
        for name, patterns in patterns_by_tool.items()
    }
    bundles: list[ConstructionExampleFamilyBundle] = []
    family_coverage: list[dict[str, object]] = []
    for tag, contracts in contracts_by_family.items():
        tools = tuple(
            ConstructionExampleTool(
                tool_name=contract.tool_name,
                operation=contract.operation,
                types=contract.types,
                legal_key_skeletons=contract.legal_key_skeletons,
                patterns=selected[contract.tool_name],
            )
            for contract in contracts
        )
        text = _render_family(tag, labels[tag], tools)
        if not text.isascii():
            raise ConstructionExampleGroundError("rendered family ground is not ASCII")
        encoded = text.encode("ascii")
        if len(encoded) > family_cap:
            raise ConstructionExampleGroundError(
                f"family byte cap exceeded for {tag}: {len(encoded)} > {family_cap}"
            )
        bundle = ConstructionExampleFamilyBundle(
            family_tag=tag,
            family_label=labels[tag],
            tools=tools,
            text=text,
            sha256=_sha256(encoded),
            ascii_bytes=len(encoded),
        )
        bundles.append(bundle)
        family_coverage.append(
            {
                "family_tag": tag,
                "tool_count": len(tools),
                "construction_used_tool_count": sum(
                    tool.tool_name in used_tools for tool in tools
                ),
                "tools_with_examples": sum(bool(tool.patterns) for tool in tools),
                "example_count": bundle.example_count,
                "ascii_bytes": bundle.ascii_bytes,
                "sha256": bundle.sha256,
            }
        )
    corpus_text = "\n".join(bundle.text.rstrip("\n") for bundle in bundles) + "\n"
    corpus_bytes = corpus_text.encode("ascii")
    if len(corpus_bytes) > corpus_cap:
        raise ConstructionExampleGroundError(
            f"corpus byte cap exceeded: {len(corpus_bytes)} > {corpus_cap}"
        )
    registry_only = sorted(set(by_tool) - used_tools)
    example_count = sum(bundle.example_count for bundle in bundles)
    tool_coverage = [
        {
            "family_tag": contract.family_tag,
            "tool_name": contract.tool_name,
            "construction_used": contract.tool_name in used_tools,
            "pattern_count": len(selected[contract.tool_name]),
            "pattern_placeholder_keys": sorted(
                {
                    key
                    for pattern in selected[contract.tool_name]
                    for key in pattern.placeholders
                }
            ),
            "typed_key_count": len(contract.types),
            "legal_key_skeleton_count": len(contract.legal_key_skeletons),
        }
        for contracts in contracts_by_family.values()
        for contract in contracts
    ]
    report: dict[str, object] = {
        "schema": "saea-a2t-construction-example-ground-report-v1",
        "family_count": len(bundles),
        "tool_count": len(by_tool),
        "construction_row_count": len(rows),
        "construction_used_tool_count": len(used_tools),
        "tools_with_examples": sum(bool(patterns) for patterns in selected.values()),
        "task_used_tool_pattern_coverage": (
            sum(bool(selected[name]) for name in used_tools) / len(used_tools)
            if used_tools
            else 1.0
        ),
        "registry_only_tool_names": registry_only,
        "registry_only_tool_count": len(registry_only),
        "registry_only_tool_pattern_policy": (
            "zero patterns; no construction-positive language is available"
        ),
        "example_count": example_count,
        "maximum_examples_per_tool": max_examples_per_tool,
        "rejected_row_count": sum(rejected_rows.values()),
        "rejected_row_reason_counts": dict(sorted(rejected_rows.items())),
        "rejected_row_reason_counts_by_tool": {
            name: dict(sorted(reasons.items()))
            for name, reasons in sorted(rejected_rows_by_tool.items())
            if reasons
        },
        "unaligned_row_count": rejected_rows["unaligned_argument_values"],
        "g5_incompatible_key_skeleton_row_count": rejected_rows[
            "g5_incompatible_key_skeleton"
        ],
        "malformed_argument_key_skeleton_row_count": rejected_rows[
            "malformed_argument_key_skeleton"
        ],
        "unsafe_construction_text_row_count": (
            rejected_rows["empty_construction_text"]
            + rejected_rows["non_ascii_construction_text"]
        ),
        "placeholder_free_pattern_count": sum(
            not pattern.placeholders
            for patterns in selected.values()
            for pattern in patterns
        ),
        "typed_key_count": sum(
            len(contract.types)
            for contracts in contracts_by_family.values()
            for contract in contracts
        ),
        "legal_key_skeleton_count": sum(
            len(contract.legal_key_skeletons)
            for contracts in contracts_by_family.values()
            for contract in contracts
        ),
        "observed_legal_key_skeleton_count": len(observed_legal_skeletons),
        "family_coverage": family_coverage,
        "tool_coverage": tool_coverage,
        "construction_fields_consumed": [
            "arg_pairs",
            "arg_signature",
            "query_idx",
            "sample_ids",
            "text",
            "tier",
            "tool_name",
            "unit_id",
        ],
        "source_argument_values_rendered": 0,
        "source_sample_ids_rendered": 0,
        "source_unit_ids_rendered": 0,
        "registry_defaults_rendered": 0,
        "gold_or_evaluation_fields_consumed": 0,
        "tier7_chat_histories_consumed": 0,
        "query_independent": True,
        "primary_call_examples_only": True,
        "ascii_only": True,
        "maximum_family_ascii_bytes": max(bundle.ascii_bytes for bundle in bundles),
        "family_ascii_byte_cap": family_cap,
        "corpus_ascii_bytes": len(corpus_bytes),
        "corpus_ascii_byte_cap": corpus_cap,
        "reversed_input_rebuild_contract": "byte-identical",
    }
    corpus_hash = _sha256(corpus_bytes)
    receipt: dict[str, object] = {
        "schema": "saea-a2t-construction-example-ground-receipt-v1",
        "corpus_sha256": corpus_hash,
        "source_hashes": {
            "g5_corpus_sha256": g5_hash,
            "construction_rows_sha256": _source_rows_hash(rows),
            "forbidden_query_blocks_sha256": _identity_hash(blocks),
            "forbidden_source_ids_sha256": _identity_hash(sources),
        },
        "boundary": {
            "construction_query_block_count": len({row.query_idx for row in rows}),
            "construction_source_identity_count": source_identity_count,
            "forbidden_query_block_count": len(blocks),
            "forbidden_source_identity_count": len(sources),
            "query_block_intersection_count": 0,
            "source_identity_intersection_count": 0,
        },
        "coverage": report,
    }
    return ConstructionExampleGround(
        bundles=tuple(bundles),
        text=corpus_text,
        sha256=corpus_hash,
        report=report,
        receipt=receipt,
    )


__all__ = [
    "DEFAULT_MAX_CORPUS_ASCII_BYTES",
    "DEFAULT_MAX_EXAMPLES_PER_TOOL",
    "DEFAULT_MAX_FAMILY_ASCII_BYTES",
    "ConstructionExampleFamilyBundle",
    "ConstructionExampleGround",
    "ConstructionExampleGroundError",
    "ConstructionExampleTool",
    "ConstructionLanguagePattern",
    "build_construction_example_family_ground",
]
