"""Plain-English Audio2Tool knowledge cards and hierarchical retrieval.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``retrieve_plain_english_packets`` is catalog id
``saea-tool-a2t-plain-english-retrieval-v1`` on the ``SUPPLY`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re
from typing import Collection, Mapping, Sequence

from ..analysis.a2t_lexical_ceiling import BM25_B, BM25_K1, Bm25Index
from .knowledge_build_a2t import A2tKbRow, TIERS

DEFAULT_MAX_CORPUS_UTF8_BYTES = 512_000
DEFAULT_MAX_TOOL_CARD_UTF8_BYTES = 6_000
DEFAULT_PACKET_UTF8_BYTE_CAP = 64_000
DEFAULT_OBSERVATION_CHARACTER_CAP = 4_096
MAX_DETAILED_TOOLS = 32
MAX_BEHAVIOR_CARDS = 4


class PlainEnglishCardError(RuntimeError):
    """The plain-English corpus or retrieval request is invalid."""


@dataclass(frozen=True)
class ToolKnowledgeCard:
    """One model-facing tool card and its model-free retrieval features."""

    tool_name: str
    group_name: str
    text: str
    name_terms: tuple[str, ...]
    meaning_terms: tuple[str, ...]
    argument_terms: tuple[str, ...]
    cue_terms: tuple[str, ...]
    group_terms: tuple[str, ...]


@dataclass(frozen=True)
class BehaviorKnowledgeCard:
    """One tier behavior card."""

    card_id: str
    tier: str
    text: str
    search_terms: tuple[str, ...]


@dataclass(frozen=True)
class PlainEnglishCardCorpus:
    """Complete index, detailed cards, behaviors, and aggregate receipt."""

    index_text: str
    tool_cards: tuple[ToolKnowledgeCard, ...]
    behavior_cards: tuple[BehaviorKnowledgeCard, ...]
    construction_index: Bm25Index
    construction_sequences: tuple[tuple[str, tuple[str, ...]], ...]
    corpus_text: str
    sha256: str
    construction_access_sha256: str
    report: Mapping[str, object]

    @property
    def tool_cards_by_name(self) -> Mapping[str, ToolKnowledgeCard]:
        """Detailed cards keyed by exact tool name."""

        return {card.tool_name: card for card in self.tool_cards}


@dataclass(frozen=True)
class PlainEnglishPacketRoute:
    """Matched and deterministic mismatched packets for one observation."""

    matched_packet: str
    shuffled_packet: str
    matched_tool_names: tuple[str, ...]
    shuffled_tool_names: tuple[str, ...]
    matched_behavior_ids: tuple[str, ...]
    shuffled_behavior_ids: tuple[str, ...]
    group_ranking: tuple[tuple[str, int], ...]
    tool_ranking: tuple[tuple[str, int], ...]
    behavior_ranking: tuple[tuple[str, int], ...]
    construction_unit_ranking: tuple[tuple[str, float], ...]
    packet_utf8_byte_cap: int


_TIER_RULES: Mapping[str, str] = {
    "tier1_direct": "Execute only the directly requested operation.",
    "tier2_parametric": "Preserve every explicitly spoken parameter without inventing one.",
    "tier3_multi_intent": "Emit every supported requested action in request order.",
    "tier4_implicit": "Infer the operation from the desired end state, but do not invent values.",
    "tier5_needle": "Ignore unrelated narrative and execute only the embedded request.",
    "tier6_correction": "Use the final corrected intent and values; discard superseded content.",
    "tier7_multiturn": "Resolve the final user request from prior dialogue and never use future turns.",
    "tier8_intent_blending": "Decompose the blended intent into ordered supported actions.",
}

_STOPWORDS = frozenset(
    "a an and are as at be been but by can could did do does for from had has have he her here him his how i if in into is it its me my of on or our please she should that the their them then there these they this those to us was we were what when where which who why will with would you your".split()
)


def _words(text: str) -> tuple[str, ...]:
    camel_split = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return tuple(token.lower() for token in re.findall(r"[A-Za-z]+|[0-9]+", camel_split))


def _feature_terms(text: str) -> tuple[str, ...]:
    terms: list[str] = []
    for token in _words(text):
        terms.append(token)
        if len(token) > 4 and token.endswith("ing"):
            stem = token[:-3]
            terms.extend((stem, stem + "e"))
        elif len(token) > 3 and token.endswith("es"):
            terms.append(token[:-2])
        elif len(token) > 3 and token.endswith("s"):
            terms.append(token[:-1])
    return tuple(terms)


def _required_ascii(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlainEnglishCardError(f"registry {field} must be non-empty text")
    result = value.strip()
    if not result.isascii():
        raise PlainEnglishCardError(f"registry {field} must be ASCII English")
    return result


def _parse_signature(signature: str, tool_name: str) -> tuple[tuple[str, str], ...]:
    match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_]*)\((.*)\)", signature.strip())
    if match is None or match.group(1) != tool_name:
        raise PlainEnglishCardError(f"registry signature for {tool_name!r} is malformed")
    body = match.group(2).strip()
    if not body:
        return ()
    arguments: list[tuple[str, str]] = []
    for item in body.split(","):
        name, separator, type_name = item.strip().partition(":")
        if (
            not separator
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name.strip())
            or not type_name.strip()
        ):
            raise PlainEnglishCardError(f"registry signature for {tool_name!r} is malformed")
        arguments.append((name.strip(), type_name.strip()))
    if len({name for name, _type in arguments}) != len(arguments):
        raise PlainEnglishCardError(f"registry signature for {tool_name!r} repeats an argument")
    return tuple(arguments)


def _parse_registry_defaults(raw: str, tool_name: str) -> Mapping[str, object]:
    if not raw.strip():
        return {}
    try:
        parsed = ast.parse(f"f({raw})", mode="eval").body
        if not isinstance(parsed, ast.Call) or parsed.args:
            raise ValueError
        defaults: dict[str, object] = {}
        for keyword in parsed.keywords:
            if keyword.arg is None:
                continue
            if isinstance(keyword.value, ast.Name) and keyword.value.id in {
                "null",
                "true",
                "false",
            }:
                value = {"null": None, "true": True, "false": False}[
                    keyword.value.id
                ]
            else:
                value = ast.literal_eval(keyword.value)
            defaults[keyword.arg] = value
    except (SyntaxError, ValueError) as error:
        raise PlainEnglishCardError(
            f"registry defaults for {tool_name!r} are malformed"
        ) from error
    if len(defaults) != len(parsed.keywords):
        raise PlainEnglishCardError(f"registry defaults for {tool_name!r} are malformed")
    return defaults


def _serialized_value(value: object) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _render_default(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _validate_registry(
    rows: Sequence[Mapping[str, str]],
) -> dict[str, dict[str, object]]:
    registry: dict[str, dict[str, object]] = {}
    for raw in rows:
        name = _required_ascii(raw.get("tool_name"), field="tool_name")
        if name in registry:
            raise PlainEnglishCardError(f"duplicate registry tool {name!r}")
        signature = _required_ascii(raw.get("signature"), field=f"{name}.signature")
        registry[name] = {
            "domain": _required_ascii(raw.get("domain"), field=f"{name}.domain"),
            "category": _required_ascii(raw.get("category"), field=f"{name}.category"),
            "description": _required_ascii(
                raw.get("description"), field=f"{name}.description"
            ),
            "arguments": _parse_signature(signature, name),
            "defaults": _parse_registry_defaults(
                str(raw.get("argument_defaults") or ""), name
            ),
            "constraints": str(raw.get("argument_constraints") or "").strip(),
        }
        constraints = registry[name]["constraints"]
        if not isinstance(constraints, str) or not constraints.isascii():
            raise PlainEnglishCardError(
                f"registry {name}.argument_constraints must be ASCII English"
            )
    if not registry:
        raise PlainEnglishCardError("registry must contain at least one tool")
    return registry


def _value_exclusions(rows: Sequence[A2tKbRow]) -> frozenset[str]:
    excluded: set[str] = set()
    for row in rows:
        for _key, value in row.arg_pairs:
            tokens = _words(value)
            excluded.update(tokens)
            excluded.update(" ".join(tokens[index : index + 2]) for index in range(len(tokens) - 1))
            if tokens:
                excluded.add("".join(tokens))
    return frozenset(excluded)


def _aggregate_cues(
    rows: Sequence[A2tKbRow], *, maximum_per_tool: int = 8
) -> Mapping[str, tuple[str, ...]]:
    exclusions = _value_exclusions(rows)
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    tool_presence: Counter[str] = Counter()
    for row in rows:
        tokens = tuple(
            token
            for token in _words(row.text)
            if token.isalpha()
            and len(token) > 1
            and token not in _STOPWORDS
            and token not in exclusions
        )
        terms = set(tokens)
        terms.update(
            f"{left} {right}"
            for left, right in zip(tokens, tokens[1:], strict=False)
            if f"{left} {right}" not in exclusions
        )
        terms.discard(" ".join(_words(row.text)))
        counts[row.tool_name].update(terms)
    for tool_counts in counts.values():
        tool_presence.update(tool_counts.keys())
    return {
        tool: tuple(
            sorted(
                tool_counts,
                key=lambda term: (
                    tool_presence[term],
                    -tool_counts[term],
                    -term.count(" "),
                    term,
                ),
            )[:maximum_per_tool]
        )
        for tool, tool_counts in sorted(counts.items())
    }


def _nearest_tools(
    tool_name: str,
    registry: Mapping[str, Mapping[str, object]],
    *,
    limit: int = 3,
) -> tuple[str, ...]:
    current = registry[tool_name]
    candidates = [
        name
        for name, entry in registry.items()
        if name != tool_name
        and entry["domain"] == current["domain"]
    ]
    if not candidates:
        candidates = [name for name in registry if name != tool_name]
    current_terms = set(_feature_terms(f"{tool_name} {current['description']}"))

    def similarity(name: str) -> tuple[Fraction, int, str]:
        terms = set(_feature_terms(f"{name} {registry[name]['description']}"))
        union = current_terms | terms
        score = Fraction(len(current_terms & terms), len(union)) if union else Fraction()
        group_penalty = int(registry[name]["category"] != current["category"])
        return (-score, group_penalty, name)

    return tuple(sorted(candidates, key=similarity)[:limit])


def _plain_key_set(keys: tuple[str, ...]) -> str:
    if not keys:
        return "no arguments"
    if len(keys) == 1:
        return keys[0]
    return ", ".join(keys[:-1]) + f" and {keys[-1]}"


def _stable_defaults(
    tool_name: str,
    registry_entry: Mapping[str, object],
    rows: Sequence[A2tKbRow],
    *,
    minimum_observations: int,
) -> tuple[tuple[str, object, int], ...]:
    declared = registry_entry["defaults"]
    if not isinstance(declared, Mapping):
        return ()
    observations: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row.tool_name != tool_name:
            continue
        for key, value in row.arg_pairs:
            observations[key].append(value)
    stable: list[tuple[str, object, int]] = []
    for key, value in sorted(declared.items()):
        observed = observations.get(key, [])
        if (
            len(observed) >= minimum_observations
            and len(set(observed)) == 1
            and observed[0] == _serialized_value(value)
        ):
            stable.append((key, value, len(observed)))
    return tuple(stable)


def build_plain_english_card_corpus(
    registry_rows: Sequence[Mapping[str, str]],
    construction_rows: Sequence[A2tKbRow],
    *,
    forbidden_sample_ids: Collection[str] = (),
    stable_default_min_observations: int = 5,
    max_corpus_utf8_bytes: int = DEFAULT_MAX_CORPUS_UTF8_BYTES,
    max_tool_card_utf8_bytes: int = DEFAULT_MAX_TOOL_CARD_UTF8_BYTES,
) -> PlainEnglishCardCorpus:
    """Build complete cards from registry metadata and construction aggregates."""

    for value, label in (
        (stable_default_min_observations, "stable_default_min_observations"),
        (max_corpus_utf8_bytes, "max_corpus_utf8_bytes"),
        (max_tool_card_utf8_bytes, "max_tool_card_utf8_bytes"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise PlainEnglishCardError(f"{label} must be a positive integer")
    registry = _validate_registry(registry_rows)
    forbidden = frozenset(forbidden_sample_ids)
    intersection = sorted(
        forbidden.intersection(
            sample_id for row in construction_rows for sample_id in row.sample_ids
        )
    )
    if intersection:
        raise PlainEnglishCardError("construction intersects a forbidden sample identity")

    rows_by_tool_tier: dict[tuple[str, str], list[A2tKbRow]] = defaultdict(list)
    unit_ids: set[str] = set()
    source_sample_count = 0
    for row in construction_rows:
        if row.tool_name not in registry:
            raise PlainEnglishCardError(
                f"construction tool {row.tool_name!r} is outside the registry"
            )
        if row.tier not in _TIER_RULES:
            raise PlainEnglishCardError(f"construction tier {row.tier!r} is unknown")
        if row.unit_id in unit_ids:
            raise PlainEnglishCardError("construction unit identity is duplicated")
        unit_ids.add(row.unit_id)
        if tuple(key for key, _value in row.arg_pairs) != row.arg_signature:
            raise PlainEnglishCardError("construction argument keys disagree")
        sequence = (row.tool_name, *row.extra_call_names)
        if row.call_count != len(sequence) or any(
            tool_name not in registry for tool_name in sequence
        ):
            raise PlainEnglishCardError(
                "construction call sequence is inconsistent with the registry"
            )
        rows_by_tool_tier[(row.tool_name, row.tier)].append(row)
        source_sample_count += len(row.sample_ids)

    construction_documents: list[tuple[str, str]] = []
    construction_sequences: list[tuple[str, tuple[str, ...]]] = []
    for row in sorted(construction_rows, key=lambda item: item.unit_id):
        sequence = (row.tool_name, *row.extra_call_names)
        document_id = hashlib.sha256(
            f"{row.unit_id}\0{row.text}\0{'|'.join(sequence)}".encode("utf-8")
        ).hexdigest()
        construction_documents.append((document_id, row.text))
        construction_sequences.append((document_id, sequence))
    if not construction_documents:
        raise PlainEnglishCardError("construction corpus must contain at least one unit")
    if len({document_id for document_id, _text in construction_documents}) != len(
        construction_documents
    ):
        raise PlainEnglishCardError("construction retrieval document identity collided")
    construction_index = Bm25Index.build(construction_documents)
    construction_access_payload = json.dumps(
        construction_sequences,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    construction_access_sha256 = hashlib.sha256(
        construction_access_payload
    ).hexdigest()

    cues = _aggregate_cues(construction_rows)
    index_lines = ["COMPLETE TOOL NAME AND MEANING INDEX"]
    for name in sorted(registry):
        index_lines.append(f"{name} - {registry[name]['description']}")
    index_text = "\n".join(index_lines)

    tool_cards: list[ToolKnowledgeCard] = []
    stable_default_count = 0
    for name in sorted(registry):
        entry = registry[name]
        arguments = entry["arguments"]
        if not isinstance(arguments, tuple):
            raise PlainEnglishCardError("internal registry argument shape is invalid")
        lines = [
            f"Tool name: {name}",
            f"Meaning: {entry['description']}",
            f"Domain: {entry['domain']}",
            f"Category: {entry['category']}",
            "Nearest tool contrasts:",
        ]
        nearest = _nearest_tools(name, registry)
        if nearest:
            lines.extend(
                f"- {other}: {registry[other]['description']}" for other in nearest
            )
        else:
            lines.append("- No other registry tool is available for contrast.")
        lines.append("Arguments and types:")
        if arguments:
            lines.extend(f"- {key} ({type_name})" for key, type_name in arguments)
        else:
            lines.append("- No arguments.")
        constraints = entry["constraints"]
        if isinstance(constraints, str) and constraints:
            lines.append(f"Public argument constraints: {constraints}")
        lines.append("Tier-conditioned argument inclusion rules:")
        found_tier = False
        for tier in TIERS:
            tier_rows = rows_by_tool_tier.get((name, tier), ())
            if not tier_rows:
                continue
            found_tier = True
            patterns = sorted(
                {row.arg_signature for row in tier_rows}, key=lambda item: (len(item), item)
            )
            rendered = "; or ".join(_plain_key_set(pattern) for pattern in patterns)
            lines.append(
                f"- For {tier}, observed argument inclusion patterns: {rendered}."
            )
        if not found_tier:
            lines.append("- No construction observation is available; follow the registry signature.")
        defaults = _stable_defaults(
            name,
            entry,
            construction_rows,
            minimum_observations=stable_default_min_observations,
        )
        lines.append("Construction-aggregate stable defaults:")
        if defaults:
            stable_default_count += len(defaults)
            lines.extend(
                f"- Construction-stable default: {key} = {_render_default(value)} "
                f"({count} consistent construction observations)."
                for key, value, count in defaults
            )
        else:
            lines.append("- None. Do not invent an omitted value.")
        if cues.get(name):
            lines.append("Distinctive construction language: " + ", ".join(cues[name]) + ".")
        lines.append(
            f'Exact output shape: {{"name":"{name}","arguments":{{...}}}}'
        )
        text = "\n".join(lines)
        size = len(text.encode("utf-8"))
        if size > max_tool_card_utf8_bytes:
            raise PlainEnglishCardError(
                f"tool-card byte budget exceeded for {name!r}: "
                f"{size} > {max_tool_card_utf8_bytes}"
            )
        argument_terms = tuple(
            term for key, type_name in arguments for term in _words(f"{key} {type_name}")
        )
        tool_cards.append(
            ToolKnowledgeCard(
                tool_name=name,
                group_name=f"{entry['domain']}/{entry['category']}",
                text=text,
                name_terms=_feature_terms(name),
                meaning_terms=_feature_terms(str(entry["description"])),
                argument_terms=argument_terms,
                cue_terms=tuple(
                    term for cue in cues.get(name, ()) for term in _feature_terms(cue)
                ),
                group_terms=_feature_terms(f"{entry['domain']} {entry['category']}"),
            )
        )

    behavior_cards = tuple(
        BehaviorKnowledgeCard(
            card_id=f"behavior-{tier}",
            tier=tier,
            text=f"Behavior for {tier}: {_TIER_RULES[tier]}",
            search_terms=_feature_terms(f"{tier} {_TIER_RULES[tier]}"),
        )
        for tier in TIERS
    )
    corpus_text = "\n\n".join(
        (
            index_text,
            "\n".join(card.text for card in behavior_cards),
            "\n\n".join(card.text for card in tool_cards),
        )
    ) + "\n"
    corpus_size = len(corpus_text.encode("utf-8"))
    if corpus_size > max_corpus_utf8_bytes:
        raise PlainEnglishCardError(
            f"corpus byte budget exceeded: {corpus_size} > {max_corpus_utf8_bytes}"
        )
    report = {
        "schema": "saea-a2t-plain-english-card-corpus-report-v1",
        "registry_tool_count": len(registry),
        "detailed_tool_card_count": len(tool_cards),
        "behavior_card_count": len(behavior_cards),
        "construction_tool_count": len({row.tool_name for row in construction_rows}),
        "source_unit_count": len(unit_ids),
        "source_sample_count": source_sample_count,
        "construction_retrieval_document_count": len(construction_documents),
        "construction_access_sha256": construction_access_sha256,
        "construction_retriever": {
            "algorithm": "Okapi BM25 over construction-unit English text",
            "k1": BM25_K1,
            "b": BM25_B,
            "tokenizer": "lowercase ASCII alphanumeric runs",
        },
        "forbidden_sample_intersection_count": len(intersection),
        "stable_default_count": stable_default_count,
        "source_utterances_rendered": 0,
        "sample_ids_rendered": 0,
        "row_argument_values_rendered": 0,
        "corpus_utf8_bytes": corpus_size,
        "index_utf8_bytes": len(index_text.encode("utf-8")),
        "largest_tool_card_utf8_bytes": max(
            len(card.text.encode("utf-8")) for card in tool_cards
        ),
        "max_corpus_utf8_bytes": max_corpus_utf8_bytes,
        "max_tool_card_utf8_bytes": max_tool_card_utf8_bytes,
    }
    rendered = corpus_text.encode("utf-8")
    bound_identity = rendered + b"\0" + construction_access_sha256.encode("ascii")
    return PlainEnglishCardCorpus(
        index_text=index_text,
        tool_cards=tuple(tool_cards),
        behavior_cards=behavior_cards,
        construction_index=construction_index,
        construction_sequences=tuple(construction_sequences),
        corpus_text=corpus_text,
        sha256=hashlib.sha256(bound_identity).hexdigest(),
        construction_access_sha256=construction_access_sha256,
        report=report,
    )


def _tool_score(query: frozenset[str], card: ToolKnowledgeCard) -> int:
    return (
        8 * len(query.intersection(card.name_terms))
        + 4 * len(query.intersection(card.meaning_terms))
        + 5 * len(query.intersection(card.cue_terms))
        + 2 * len(query.intersection(card.argument_terms))
        + len(query.intersection(card.group_terms))
    )


def _deterministic_mismatch(
    identities: Sequence[str], selected: Sequence[str], *, seed_material: str
) -> tuple[str, ...]:
    selected_set = set(selected)
    candidates = [identity for identity in identities if identity not in selected_set]
    candidates.sort(
        key=lambda identity: (
            hashlib.sha256(f"{seed_material}:{identity}".encode("utf-8")).hexdigest(),
            identity,
        )
    )
    if len(candidates) < len(selected):
        raise PlainEnglishCardError(
            "corpus is too small for a disjoint shuffled detailed-card control"
        )
    return tuple(candidates[: len(selected)])


def _render_packet(
    corpus: PlainEnglishCardCorpus,
    tool_names: Sequence[str],
    behavior_ids: Sequence[str],
) -> str:
    tools = corpus.tool_cards_by_name
    behaviors = {card.card_id: card for card in corpus.behavior_cards}
    sections = [
        "AUDIO2TOOL PLAIN-ENGLISH FULL-GROUND PACKET",
        (
            "Return only one JSON array. Every element must be exactly "
            '{"name":"exactToolName","arguments":{...}}. Use the observation for '
            "argument values; never copy a card example or invent a value."
        ),
        f"COMPLETE TOOL NAME AND MEANING INDEX ({len(corpus.tool_cards)} tools)\n"
        + "\n".join(corpus.index_text.splitlines()[1:]),
        "RETRIEVED DETAILED TOOL CARDS\n"
        + "\n\n".join(tools[name].text for name in tool_names),
        "RETRIEVED BEHAVIOR CARDS\n"
        + "\n".join(behaviors[card_id].text for card_id in behavior_ids),
    ]
    return "\n\n".join(sections) + "\n"


def retrieve_plain_english_packets(
    observation_text: str,
    corpus: PlainEnglishCardCorpus,
    *,
    detailed_tool_limit: int = MAX_DETAILED_TOOLS,
    behavior_card_limit: int = MAX_BEHAVIOR_CARDS,
    shuffle_seed: int = 0,
    observation_character_cap: int = DEFAULT_OBSERVATION_CHARACTER_CAP,
    packet_utf8_byte_cap: int = DEFAULT_PACKET_UTF8_BYTE_CAP,
) -> PlainEnglishPacketRoute:
    """Retrieve bounded matched cards and a deterministic mismatched control."""

    if not isinstance(observation_text, str) or not observation_text.strip():
        raise PlainEnglishCardError("observation must be non-empty text")
    if not observation_text.isascii():
        raise PlainEnglishCardError("observation must be bounded ASCII English")
    if len(observation_text) > observation_character_cap:
        raise PlainEnglishCardError("observation exceeds its character cap")
    if (
        isinstance(detailed_tool_limit, bool)
        or not isinstance(detailed_tool_limit, int)
        or not 1 <= detailed_tool_limit <= MAX_DETAILED_TOOLS
    ):
        raise PlainEnglishCardError("detailed_tool_limit must be between one and thirty-two")
    if (
        isinstance(behavior_card_limit, bool)
        or not isinstance(behavior_card_limit, int)
        or not 1 <= behavior_card_limit <= MAX_BEHAVIOR_CARDS
    ):
        raise PlainEnglishCardError("behavior_card_limit must be between one and four")
    for value, label in (
        (observation_character_cap, "observation_character_cap"),
        (packet_utf8_byte_cap, "packet_utf8_byte_cap"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise PlainEnglishCardError(f"{label} must be a positive integer")

    query = frozenset(_feature_terms(observation_text))
    raw_tool_scores = {
        card.tool_name: _tool_score(query, card) for card in corpus.tool_cards
    }
    cards_by_group: dict[str, list[ToolKnowledgeCard]] = defaultdict(list)
    for card in corpus.tool_cards:
        cards_by_group[card.group_name].append(card)
    group_scores = {
        group: max(raw_tool_scores[card.tool_name] for card in group_cards)
        + 10 * len(query.intersection(term for card in group_cards for term in card.group_terms))
        for group, group_cards in cards_by_group.items()
    }
    group_ranking = tuple(sorted(group_scores.items(), key=lambda item: (-item[1], item[0])))
    combined_tool_scores = {
        card.tool_name: raw_tool_scores[card.tool_name] * 100
        + group_scores[card.group_name]
        for card in corpus.tool_cards
    }
    ranked_cards = sorted(
        corpus.tool_cards,
        key=lambda card: (
            -combined_tool_scores[card.tool_name],
            card.group_name,
            card.tool_name,
        ),
    )
    tool_ranking = tuple(
        (card.tool_name, combined_tool_scores[card.tool_name]) for card in ranked_cards
    )
    construction_scores = corpus.construction_index.scores(observation_text)
    ranked_document_indices = corpus.construction_index.ranking(observation_text)
    sequence_by_document_id = dict(corpus.construction_sequences)
    selection_cap = min(detailed_tool_limit, len(corpus.tool_cards) // 2)
    projected_tools: list[str] = []
    scanned_units: list[tuple[str, float]] = []
    for index in ranked_document_indices:
        document_id = corpus.construction_index.doc_ids[index]
        scanned_units.append((document_id, float(construction_scores.get(index, 0.0))))
        for tool_name in sequence_by_document_id[document_id]:
            if tool_name not in projected_tools:
                projected_tools.append(tool_name)
                if len(projected_tools) == selection_cap:
                    break
        if len(projected_tools) == selection_cap:
            break
    construction_unit_ranking = tuple(scanned_units)
    matched_tool_names = tuple(projected_tools[:selection_cap])
    if not matched_tool_names:
        raise PlainEnglishCardError("construction BM25 projected no tool card")

    behavior_scores = {
        card.card_id: 3 * len(query.intersection(card.search_terms))
        for card in corpus.behavior_cards
    }
    behavior_ranking = tuple(
        sorted(behavior_scores.items(), key=lambda item: (-item[1], item[0]))
    )
    matched_behavior_ids = tuple(
        card_id for card_id, _score in behavior_ranking[:behavior_card_limit]
    )
    seed_material = f"{shuffle_seed}:{observation_text}"
    shuffled_tool_names = _deterministic_mismatch(
        tuple(card.tool_name for card in corpus.tool_cards),
        matched_tool_names,
        seed_material=f"{seed_material}:tools",
    )
    shuffled_behavior_ids = _deterministic_mismatch(
        tuple(card.card_id for card in corpus.behavior_cards),
        matched_behavior_ids,
        seed_material=f"{seed_material}:behaviors",
    )
    matched_packet = _render_packet(
        corpus, matched_tool_names, matched_behavior_ids
    )
    shuffled_packet = _render_packet(
        corpus, shuffled_tool_names, shuffled_behavior_ids
    )
    for packet in (matched_packet, shuffled_packet):
        size = len(packet.encode("utf-8"))
        if size > packet_utf8_byte_cap:
            raise PlainEnglishCardError(
                f"packet byte budget exceeded: {size} > {packet_utf8_byte_cap}"
            )
    return PlainEnglishPacketRoute(
        matched_packet=matched_packet,
        shuffled_packet=shuffled_packet,
        matched_tool_names=matched_tool_names,
        shuffled_tool_names=shuffled_tool_names,
        matched_behavior_ids=matched_behavior_ids,
        shuffled_behavior_ids=shuffled_behavior_ids,
        group_ranking=group_ranking,
        tool_ranking=tool_ranking,
        behavior_ranking=behavior_ranking,
        construction_unit_ranking=construction_unit_ranking,
        packet_utf8_byte_cap=packet_utf8_byte_cap,
    )


__all__ = [
    "DEFAULT_MAX_CORPUS_UTF8_BYTES",
    "DEFAULT_MAX_TOOL_CARD_UTF8_BYTES",
    "DEFAULT_OBSERVATION_CHARACTER_CAP",
    "DEFAULT_PACKET_UTF8_BYTE_CAP",
    "MAX_BEHAVIOR_CARDS",
    "MAX_DETAILED_TOOLS",
    "BehaviorKnowledgeCard",
    "PlainEnglishCardCorpus",
    "PlainEnglishCardError",
    "PlainEnglishPacketRoute",
    "ToolKnowledgeCard",
    "build_plain_english_card_corpus",
    "retrieve_plain_english_packets",
]
