"""Build construction-conditioned Audio2Tool semantics without source text.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``build_construction_semantic_ground`` is catalog id
``saea-tool-a2t-construction-semantic-ground-v1`` on the ``SUPPLY`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re
from typing import Mapping, Sequence

from .knowledge_build_a2t import A2tKbRow, TIERS

DEFAULT_MAX_UTF8_BYTES = 100_000


class ConstructionSemanticGroundError(RuntimeError):
    """The construction-semantic ground refused malformed or unsafe input."""


@dataclass(frozen=True)
class ConstructionSemanticGroundArtifact:
    """Deterministic model-facing ground text and aggregate-only report."""

    text: str
    sha256: str
    report: Mapping[str, object]


_TIER_RULES: Mapping[str, str] = {
    "tier1_direct": "execute the directly requested operation without adding actions",
    "tier2_parametric": "preserve every spoken parameter and its canonical value form",
    "tier3_multi_intent": "emit every supported requested action in request order",
    "tier4_implicit": "infer the tool from the desired end state without inventing values",
    "tier5_needle": "ignore unrelated narrative and execute only the embedded request",
    "tier6_correction": "use the final corrected intent and values; discard superseded ones",
    "tier7_multiturn": "resolve the final user request from prior dialogue, never future turns",
    "tier8_intent_blending": "decompose the blended intent into ordered supported calls",
}

_HEADER = """AUDIO2TOOL CONSTRUCTION-SEMANTIC GROUND

OUTPUT CONTRACT
Return only one JSON array and no prose or Markdown; each element is exactly {"name":"toolName","arguments":{...}}. Use exact registry tool names and exact argument-key spelling. The arguments value must be a JSON object. Emit one element per requested action in request order. Copy values only from the speech or same-core observation; never copy construction values, invent defaults, or add an unrequested call.

EVIDENCE SCOPE
Every observed key set, serialized value form, call count, and tool sequence below is conditioned on its stated tier and primary tool. It is evidence of observed constructions, not a universal requirement. Serialized forms are observations, not required source JSON types.

COMPACT EVIDENCE CODE
U codes map to exact tool names; K codes map to exact argument keys; T codes map to tiers. A P row is one exact (tier, primary-tool) condition. K lists observed key sets (comma joins keys, slash joins alternatives, dash means empty). V lists only sound canonical JSON token shapes as key:codes (i integer, n other number, b boolean, 0 null, a array, o object, s string); omitted V means no sound canonical JSON token shape was observed. C lists observed call counts. S lists observed secondary-tool suffixes (comma joins tools, slash joins alternatives, dash means no secondary call); prepend the P row's primary tool to obtain each complete observed sequence. Q lists at most the configured number of distinctive, delexicalized construction cues; a tilde joins a bigram. Q cues are hints for choosing a tool, never argument values.
"""

_STOPWORDS = frozenset(
    "a an and are as at be been but by can could did do does for from had has have he her here him his how i if in into is it its me my of on or our please she should that the their them then there these they this those to us was we were what when where which who why will with would you your".split()
)


def _required_ascii_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConstructionSemanticGroundError(f"registry {field} must be non-empty text")
    result = value.strip()
    if not result.isascii():
        raise ConstructionSemanticGroundError(
            f"registry {field} must be ASCII English before model use"
        )
    return result


def _reject_json_constant(_value: str) -> None:
    raise ValueError("non-finite JSON constant")


def _serialized_value_form(value: str) -> str:
    """Classify only the serialized token shape, never its original type."""

    try:
        decoded = json.loads(value, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError):
        return "text-token"
    canonical = json.dumps(
        decoded,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if canonical != value:
        return "text-token"
    if decoded is None:
        label = "null"
    elif isinstance(decoded, bool):
        label = "boolean"
    elif isinstance(decoded, int):
        label = "integer"
    elif isinstance(decoded, float):
        label = "number"
    elif isinstance(decoded, str):
        label = "string"
    elif isinstance(decoded, list):
        label = "array"
    elif isinstance(decoded, dict):
        label = "object"
    else:  # pragma: no cover - json.loads returns only the cases above
        return "text-token"
    return f"canonical-json-{label}-token"


def _words(text: str) -> tuple[str, ...]:
    camel_split = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return tuple(token.lower() for token in re.findall(r"[A-Za-z]+|[0-9]+", camel_split))


def _argument_value_exclusions(rows: Sequence[A2tKbRow]) -> frozenset[str]:
    excluded: set[str] = set()
    for row in rows:
        for _key, value in row.arg_pairs:
            tokens = _words(value)
            excluded.update(tokens)
            excluded.update("~".join(tokens[index : index + 2]) for index in range(len(tokens) - 1))
            if tokens:
                excluded.add("".join(tokens))
            for token in tokens:
                if len(token) > 3 and token.endswith("s"):
                    excluded.add(token[:-1])
                if len(token) > 4 and token.endswith("es"):
                    excluded.add(token[:-2])
    return frozenset(excluded)


def _row_cue_terms(row: A2tKbRow, exclusions: frozenset[str]) -> frozenset[str]:
    tokens = _words(row.text)
    admissible = tuple(
        token
        for token in tokens
        if token not in _STOPWORDS
        and token not in exclusions
        and token.isalpha()
        and len(token) > 1
    )
    terms = set(admissible)
    for left, right in zip(tokens, tokens[1:], strict=False):
        if (
            left in admissible
            and right in admissible
            and left not in exclusions
            and right not in exclusions
        ):
            terms.add(f"{left}~{right}")
    normalized_full = "~".join(tokens)
    terms.discard(normalized_full)
    return frozenset(terms)


_FORM_CODES: Mapping[str, str] = {
    "canonical-json-integer-token": "i",
    "canonical-json-number-token": "n",
    "canonical-json-boolean-token": "b",
    "canonical-json-null-token": "0",
    "canonical-json-array-token": "a",
    "canonical-json-object-token": "o",
    "canonical-json-string-token": "s",
}


def _validate_registry(
    registry_rows: Sequence[Mapping[str, str]],
) -> dict[str, dict[str, str]]:
    registry: dict[str, dict[str, str]] = {}
    for raw in registry_rows:
        name = _required_ascii_text(raw.get("tool_name"), field="tool_name")
        if name in registry:
            raise ConstructionSemanticGroundError(f"duplicate registry tool {name!r}")
        registry[name] = {
            "domain": _required_ascii_text(raw.get("domain"), field=f"{name}.domain"),
            "category": _required_ascii_text(
                raw.get("category"), field=f"{name}.category"
            ),
            "signature": _required_ascii_text(
                raw.get("signature"), field=f"{name}.signature"
            ),
            "description": _required_ascii_text(
                raw.get("description"), field=f"{name}.description"
            ),
        }
    if not registry:
        raise ConstructionSemanticGroundError("registry must contain at least one tool")
    return registry


def build_construction_semantic_ground(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    max_utf8_bytes: int = DEFAULT_MAX_UTF8_BYTES,
    max_cues_per_pair: int = 3,
) -> ConstructionSemanticGroundArtifact:
    """Render registry meanings and tier-conditioned construction evidence."""

    if (
        isinstance(max_utf8_bytes, bool)
        or not isinstance(max_utf8_bytes, int)
        or max_utf8_bytes <= 0
    ):
        raise ConstructionSemanticGroundError("max_utf8_bytes must be a positive integer")
    if (
        isinstance(max_cues_per_pair, bool)
        or not isinstance(max_cues_per_pair, int)
        or max_cues_per_pair < 0
    ):
        raise ConstructionSemanticGroundError(
            "max_cues_per_pair must be a non-negative integer"
        )
    registry = _validate_registry(registry_rows)

    value_exclusions = _argument_value_exclusions(construction_rows)

    patterns: dict[tuple[str, str], set[tuple[str, ...]]] = defaultdict(set)
    value_forms: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    call_counts: dict[tuple[str, str], set[int]] = defaultdict(set)
    sequences: dict[tuple[str, str], set[tuple[str, ...]]] = defaultdict(set)
    rows_by_tier: Counter[str] = Counter()
    unit_ids: set[str] = set()
    sample_count = 0
    construction_tools: set[str] = set()
    cue_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for row in construction_rows:
        if row.tier not in _TIER_RULES:
            raise ConstructionSemanticGroundError(
                f"construction tier {row.tier!r} is not recognized"
            )
        if row.tool_name not in registry:
            raise ConstructionSemanticGroundError(
                f"construction tool {row.tool_name!r} is outside the registry"
            )
        sequence = (row.tool_name, *row.extra_call_names)
        unknown_sequence_tools = sorted(set(sequence) - set(registry))
        if unknown_sequence_tools:
            raise ConstructionSemanticGroundError(
                f"construction sequence names tools outside the registry: "
                f"{unknown_sequence_tools!r}"
            )
        if row.call_count != len(sequence) or row.call_count <= 0:
            raise ConstructionSemanticGroundError(
                "construction call count disagrees with the primary/secondary sequence"
            )
        if not isinstance(row.call_render, str) or not row.call_render.strip():
            raise ConstructionSemanticGroundError(
                "construction call rendering must be non-empty"
            )
        keys = tuple(key for key, _value in row.arg_pairs)
        if (
            keys != row.arg_signature
            or len(keys) != len(set(keys))
            or any(not isinstance(key, str) or not key or not key.isascii() for key in keys)
        ):
            raise ConstructionSemanticGroundError(
                "construction argument keys disagree, repeat, or are not ASCII"
            )
        if row.unit_id in unit_ids:
            raise ConstructionSemanticGroundError("construction unit identity is duplicated")
        unit_ids.add(row.unit_id)

        pair = (row.tier, row.tool_name)
        patterns[pair].add(keys)
        for key, value in row.arg_pairs:
            if not isinstance(value, str):
                raise ConstructionSemanticGroundError(
                    "construction serialized argument values must be text"
                )
            value_forms[pair][key].add(_serialized_value_form(value))
        call_counts[pair].add(row.call_count)
        sequences[pair].add(sequence)
        rows_by_tier[row.tier] += 1
        sample_count += len(row.sample_ids)
        construction_tools.add(row.tool_name)
        cue_counts[pair].update(_row_cue_terms(row, value_exclusions))

    if tuple(_TIER_RULES) != TIERS:
        raise ConstructionSemanticGroundError("tier behavior rules do not cover frozen tiers")

    sections = [_HEADER.rstrip()]
    sections.append(
        "GLOBAL TIER BEHAVIOR RULES\n"
        + "\n".join(f"{tier}: {_TIER_RULES[tier]}." for tier in TIERS)
    )
    ordered_tools = sorted(registry)
    tool_width = max(3, len(str(len(ordered_tools) - 1)))
    tool_codes = {
        name: f"U{index:0{tool_width}d}" for index, name in enumerate(ordered_tools)
    }
    all_keys = sorted(
        {key for patterns_for_pair in patterns.values() for keys in patterns_for_pair for key in keys}
    )
    key_width = max(2, len(str(max(0, len(all_keys) - 1))))
    key_codes = {
        key: f"K{index:0{key_width}d}" for index, key in enumerate(all_keys)
    }
    tier_codes = {tier: f"T{index}" for index, tier in enumerate(TIERS, start=1)}
    cue_pair_frequency: Counter[str] = Counter()
    for counts in cue_counts.values():
        cue_pair_frequency.update(counts.keys())
    selected_cues: dict[tuple[str, str], tuple[str, ...]] = {}
    for pair, counts in cue_counts.items():
        selected_cues[pair] = tuple(
            sorted(
                counts,
                key=lambda term: (
                    -Fraction(counts[term], cue_pair_frequency[term]),
                    -counts[term],
                    -term.count("~"),
                    term,
                ),
            )[:max_cues_per_pair]
        )

    tool_lines = ["REGISTRY TOOL MEANINGS"]
    for name in ordered_tools:
        entry = registry[name]
        tool_lines.append(
            f"{tool_codes[name]}={name} | Meaning: {entry['description']}"
        )
    sections.append("\n".join(tool_lines))
    sections.append(
        "ARGUMENT KEY CODE\n"
        + ("\n".join(f"{key_codes[key]}={key}" for key in all_keys) or "none")
    )
    sections.append(
        "TIER CODE\n" + "\n".join(f"{tier_codes[tier]}={tier}" for tier in TIERS)
    )

    pair_sections: list[str] = ["TIER-CONDITIONED CONSTRUCTION EVIDENCE"]
    for pair in sorted(patterns, key=lambda item: (TIERS.index(item[0]), item[1])):
        tier, tool = pair
        rendered_patterns = "/".join(
            ",".join(key_codes[key] for key in keys) or "-"
            for keys in sorted(patterns[pair], key=lambda item: (len(item), item))
        )
        sound_forms = {
            key: {_FORM_CODES[item] for item in forms_for_key if item in _FORM_CODES}
            for key, forms_for_key in value_forms[pair].items()
        }
        sound_forms = {key: values for key, values in sound_forms.items() if values}
        forms = ";".join(
            f"{key_codes[key]}:{''.join(sorted(forms_for_key))}"
            for key, forms_for_key in sorted(sound_forms.items())
        )
        rendered_counts = ",".join(str(count) for count in sorted(call_counts[pair]))
        rendered_sequences = "/".join(
            ",".join(tool_codes[name] for name in sequence[1:]) or "-"
            for sequence in sorted(sequences[pair])
        )
        form_field = f" V={forms}" if forms else ""
        cue_field = (
            f" Q={','.join(selected_cues[pair])}" if selected_cues[pair] else ""
        )
        pair_sections.append(
            f"P {tier_codes[tier]} {tool_codes[tool]} K={rendered_patterns}"
            f"{form_field} C={rendered_counts} S={rendered_sequences}{cue_field}"
        )
    sections.append("\n".join(pair_sections))

    text = "\n\n".join(sections) + "\n"
    if not text.isascii():
        raise ConstructionSemanticGroundError(
            "construction-semantic ground must be ASCII English before model use"
        )
    rendered = text.encode("utf-8")
    if len(rendered) > max_utf8_bytes:
        raise ConstructionSemanticGroundError(
            f"construction-semantic ground exceeds byte budget: "
            f"{len(rendered)} > {max_utf8_bytes}"
        )

    report = {
        "schema": "saea-a2t-construction-semantic-ground-report-v1",
        "registry_tool_count": len(registry),
        "construction_primary_tool_count": len(construction_tools),
        "registry_only_tool_count": len(set(registry) - construction_tools),
        "source_row_count": len(construction_rows),
        "source_unit_count": len(unit_ids),
        "source_sample_count": sample_count,
        "source_rows_by_tier": dict(sorted(rows_by_tier.items())),
        "source_tier_count": len(rows_by_tier),
        "tier_tool_pair_count": len(patterns),
        "argument_key_pattern_count": sum(len(items) for items in patterns.values()),
        "value_form_evidence_count": sum(
            sum(item in _FORM_CODES for item in forms_for_key)
            for forms_by_key in value_forms.values()
            for forms_for_key in forms_by_key.values()
        ),
        "call_count_pattern_count": sum(len(items) for items in call_counts.values()),
        "tool_sequence_pattern_count": sum(len(items) for items in sequences.values()),
        "invocation_texts_rendered": 0,
        "sample_ids_rendered": 0,
        "argument_values_rendered": 0,
        "lexical_cues_rendered": sum(len(items) for items in selected_cues.values()),
        "max_cues_per_pair": max_cues_per_pair,
        "ascii_only": text.isascii(),
        "utf8_bytes": len(rendered),
        "characters": len(text),
        "line_count": len(text.splitlines()),
        "max_utf8_bytes": max_utf8_bytes,
    }
    return ConstructionSemanticGroundArtifact(
        text=text,
        sha256=hashlib.sha256(rendered).hexdigest(),
        report=report,
    )


__all__ = [
    "DEFAULT_MAX_UTF8_BYTES",
    "ConstructionSemanticGroundArtifact",
    "ConstructionSemanticGroundError",
    "build_construction_semantic_ground",
]
