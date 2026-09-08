"""Route bounded executable semantic cards without gold or learned control.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``route_semantic_microground`` is catalog id
``saea-tool-a2t-semantic-microground-v1`` on the ``SUPPLY`` axis, scope
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
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Mapping, Sequence

from ..analysis.a2t_lexical_ceiling import Bm25Index
from ..reproduction.toolcall_scoring import parse_tool_calls_text
from .a2t_executable_semantic_cards import (
    ExecutableSemanticCardCorpus,
    SYNTHETIC_LITERAL_PREFIX,
    ToolSemanticCard,
)

POLICY_ID = "saea-a2t-semantic-microground-bm25-v1"
DEFAULT_MAX_UTF8_BYTES = 16_384
MIN_CANDIDATES = 2
MAX_CANDIDATES = 8

_FACET_WEIGHTS: Mapping[str, float] = {
    "choose": 5.0,
    "avoid": -0.5,
    "role": 2.0,
    "tool": 3.0,
    "category": 0.5,
}
_FORBIDDEN_STATE_KEYS = frozenset(
    {
        "expected",
        "expected_call",
        "expected_calls",
        "gold",
        "gold_call",
        "gold_calls",
        "gold_tool",
        "prior_outcome",
        "prior_reward",
        "reference_transcript",
        "reward",
        "sample_id",
        "test_annotation",
        "tier",
        "tier_hint",
    }
)
_FORBIDDEN_STATE_KEY_PREFIXES = (
    "expected_",
    "gold_",
    "prior_outcome",
    "reference_",
    "reward_",
    "sample_",
    "test_",
    "tier_",
)
_SYNTHETIC_LITERAL_RE = re.compile(
    rf"\b{re.escape(SYNTHETIC_LITERAL_PREFIX)}[A-Z0-9_]+\b", re.IGNORECASE
)


class SemanticMicrogroundError(RuntimeError):
    """The router refused an unsafe query, corpus, route, or packet."""


@dataclass(frozen=True)
class ActionFacetScore:
    """One candidate's frozen faceted BM25 score for one active action."""

    action_index: int
    rank: int
    total: float
    choose: float
    avoid: float
    role: float
    tool: float
    category: float


@dataclass(frozen=True)
class RoutedCandidate:
    """One selected candidate with auditable selection reasons and scores."""

    tool_name: str
    packet_rank: int
    reasons: tuple[str, ...]
    action_scores: tuple[ActionFacetScore, ...]


@dataclass(frozen=True)
class SemanticMicrogroundRoute:
    """The bounded packet and its stable, non-gold route trace."""

    policy_id: str
    corpus_sha256: str
    representation: str
    action_queries: tuple[str, ...]
    candidate_names: tuple[str, ...]
    candidates: tuple[RoutedCandidate, ...]
    task_card_ids: tuple[str, ...]
    packet: str
    packet_utf8_bytes: int
    packet_sha256: str
    trace_sha256: str


@dataclass(frozen=True)
class Stage1StructuralOutcome:
    """Gold-free structural validity for one response."""

    parsed: bool
    registry_names_only: bool
    legal_key_sets_only: bool
    call_count: int


@dataclass(frozen=True)
class Stage1StructuralMetrics:
    """Aggregate gold-free structural counts for a preregistered screen."""

    total_count: int
    parse_count: int
    registry_names_only_count: int
    legal_key_sets_only_count: int

    @property
    def parse_rate(self) -> float:
        """Return the fraction of responses parsed by the unchanged parser."""

        return self.parse_count / self.total_count if self.total_count else 0.0

    @property
    def registry_names_only_rate(self) -> float:
        """Return the fraction containing only nonempty registered calls."""

        return (
            self.registry_names_only_count / self.total_count
            if self.total_count
            else 0.0
        )

    @property
    def legal_key_sets_only_rate(self) -> float:
        """Return the fraction using only registered legal argument-key sets."""

        return (
            self.legal_key_sets_only_count / self.total_count
            if self.total_count
            else 0.0
        )


@dataclass(frozen=True)
class _FacetIndexes:
    names: tuple[str, ...]
    choose: Bm25Index
    avoid: Bm25Index
    role: Bm25Index
    tool: Bm25Index
    category: Bm25Index


def _humanize_identifier(value: str) -> str:
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return expanded.replace("_", " ")


def _required_ascii(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticMicrogroundError(f"{field} must be non-empty ASCII English")
    text = " ".join(value.split())
    if not text.isascii():
        raise SemanticMicrogroundError(f"{field} must be ASCII English")
    if _SYNTHETIC_LITERAL_RE.search(text):
        raise SemanticMicrogroundError(
            f"{field} contains a forbidden synthetic-example literal"
        )
    return text


def _validate_corpus(
    corpus: ExecutableSemanticCardCorpus,
) -> tuple[tuple[ToolSemanticCard, ...], tuple[object, ...]]:
    if not isinstance(corpus, ExecutableSemanticCardCorpus):
        raise SemanticMicrogroundError("corpus must be an ExecutableSemanticCardCorpus")
    cards = tuple(sorted(corpus.tool_cards, key=lambda card: card.tool_name))
    names = tuple(card.tool_name for card in cards)
    if len(cards) < MIN_CANDIDATES or len(names) != len(set(names)):
        raise SemanticMicrogroundError(
            "corpus must contain at least two unique tool cards"
        )
    for card in cards:
        for field, value in (
            ("tool name", card.tool_name),
            (f"{card.tool_name} choose semantics", card.choose_semantics),
            (f"{card.tool_name} avoid semantics", card.avoid_semantics),
            (f"{card.tool_name} card text", card.text),
        ):
            if not isinstance(value, str) or not value or not value.isascii():
                raise SemanticMicrogroundError(
                    f"{field} must be non-empty ASCII English"
                )
    tasks = tuple(sorted(corpus.task_cards, key=lambda card: card.card_id))
    task_ids = tuple(card.card_id for card in tasks)
    if len(tasks) != 4 or len(task_ids) != len(set(task_ids)):
        raise SemanticMicrogroundError(
            "semantic microground requires exactly four unique task cards"
        )
    if any(
        not isinstance(card.text, str)
        or not card.text
        or not card.text.isascii()
        or not card.card_id.isascii()
        for card in tasks
    ):
        raise SemanticMicrogroundError("task cards must be non-empty ASCII English")
    return cards, tasks


def _reject_forbidden_state(value: object, *, path: str = "state") -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if not isinstance(raw_key, str) or not raw_key.isascii():
                raise SemanticMicrogroundError(
                    "structured-state keys must be ASCII English"
                )
            normalized = raw_key.strip().lower().replace("-", "_")
            if normalized in _FORBIDDEN_STATE_KEYS or normalized.startswith(
                _FORBIDDEN_STATE_KEY_PREFIXES
            ):
                raise SemanticMicrogroundError(
                    f"structured state contains forbidden runtime feature {raw_key!r}"
                )
            _reject_forbidden_state(child, path=f"{path}.{raw_key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _reject_forbidden_state(child, path=f"{path}[{index}]")
        return
    if isinstance(value, str):
        if not value.isascii():
            raise SemanticMicrogroundError(f"{path} must be ASCII English")
        if _SYNTHETIC_LITERAL_RE.search(value):
            raise SemanticMicrogroundError(
                f"{path} contains a forbidden synthetic-example literal"
            )


def _action_queries(structured_state: Mapping[str, object]) -> tuple[str, ...]:
    _reject_forbidden_state(structured_state)
    actions = structured_state.get("active_actions")
    if (
        not isinstance(actions, Sequence)
        or isinstance(actions, (str, bytes, bytearray))
    ):
        raise SemanticMicrogroundError(
            "structured state active_actions must be a sequence"
        )
    if not actions:
        current = structured_state.get("current_request")
        if not isinstance(current, Mapping):
            raise SemanticMicrogroundError(
                "structured state without active actions requires current_request"
            )
        query = current.get("normalized")
        if query in (None, ""):
            query = current.get("surface")
        return (_required_ascii(query, field="current request"),)
    if len(actions) > MAX_CANDIDATES:
        raise SemanticMicrogroundError(
            "structured state permits at most eight active actions"
        )
    queries: list[str] = []
    for action_index, action in enumerate(actions):
        if not isinstance(action, Mapping):
            raise SemanticMicrogroundError(
                f"active action {action_index} must be a mapping"
            )
        action_phrase = action.get("action_phrase")
        if action_phrase in (None, ""):
            action_phrase = action.get("normalized")
        if action_phrase in (None, ""):
            action_phrase = action.get("surface")
        parts = [_required_ascii(action_phrase, field="action phrase")]
        target = action.get("target_phrase")
        if target not in (None, ""):
            parts.append(_required_ascii(target, field="target phrase"))
        values = action.get("values", ())
        if not isinstance(values, Sequence) or isinstance(
            values, (str, bytes, bytearray)
        ):
            raise SemanticMicrogroundError("active-action values must be a sequence")
        for value_index, value in enumerate(values):
            if not isinstance(value, Mapping):
                raise SemanticMicrogroundError(
                    f"active-action value {value_index} must be a mapping"
                )
            for key in ("role", "surface", "normalized"):
                item = value.get(key)
                if item not in (None, ""):
                    parts.append(_required_ascii(item, field=f"value {key}"))
        queries.append(" ".join(parts))
    return tuple(queries)


def _sibling_names(card: ToolSemanticCard, names: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        name
        for name in names
        if name != card.tool_name
        and re.search(
            rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", card.avoid_semantics
        )
    )


def _build_indexes(cards: Sequence[ToolSemanticCard]) -> _FacetIndexes:
    names = tuple(card.tool_name for card in cards)
    by_name = {card.tool_name: card for card in cards}
    siblings = {card.tool_name: _sibling_names(card, names) for card in cards}
    category_text: dict[str, str] = {}
    for name in names:
        group = (name, *siblings[name])
        category_text[name] = " ".join(
            f"{_humanize_identifier(member)} {by_name[member].choose_semantics}"
            for member in sorted(set(group))
        )

    def index(text_by_name: Mapping[str, str]) -> Bm25Index:
        return Bm25Index.build(tuple((name, text_by_name[name]) for name in names))

    return _FacetIndexes(
        names=names,
        choose=index({card.tool_name: card.choose_semantics for card in cards}),
        avoid=index({card.tool_name: card.avoid_semantics for card in cards}),
        role=index({card.tool_name: " ".join(card.role_guidance) for card in cards}),
        tool=index(
            {
                card.tool_name: f"{card.tool_name} {_humanize_identifier(card.tool_name)}"
                for card in cards
            }
        ),
        category=index(category_text),
    )


def _dense_scores(index: Bm25Index, query: str) -> tuple[float, ...]:
    sparse = index.scores(query)
    return tuple(sparse.get(position, 0.0) for position in range(len(index.doc_ids)))


def _rank_action(
    indexes: _FacetIndexes, query: str, action_index: int
) -> tuple[tuple[str, ...], Mapping[str, ActionFacetScore]]:
    by_facet = {
        "choose": _dense_scores(indexes.choose, query),
        "avoid": _dense_scores(indexes.avoid, query),
        "role": _dense_scores(indexes.role, query),
        "tool": _dense_scores(indexes.tool, query),
        "category": _dense_scores(indexes.category, query),
    }
    totals = {
        name: sum(
            _FACET_WEIGHTS[facet] * by_facet[facet][position]
            for facet in _FACET_WEIGHTS
        )
        for position, name in enumerate(indexes.names)
    }
    ranking = tuple(sorted(indexes.names, key=lambda name: (-totals[name], name)))
    ranks = {name: rank for rank, name in enumerate(ranking, start=1)}
    scores: dict[str, ActionFacetScore] = {}
    positions = {name: index for index, name in enumerate(indexes.names)}
    for name in indexes.names:
        position = positions[name]
        scores[name] = ActionFacetScore(
            action_index=action_index,
            rank=ranks[name],
            total=round(totals[name], 12),
            choose=round(by_facet["choose"][position], 12),
            avoid=round(by_facet["avoid"][position], 12),
            role=round(by_facet["role"][position], 12),
            tool=round(by_facet["tool"][position], 12),
            category=round(by_facet["category"][position], 12),
        )
    return ranking, scores


def _legal_key_union(card: ToolSemanticCard) -> frozenset[str]:
    return frozenset(key for key_set in card.legal_argument_key_sets for key in key_set)


def _select_candidates(
    cards: Sequence[ToolSemanticCard],
    rankings: Sequence[tuple[str, ...]],
    action_scores: Sequence[Mapping[str, ActionFacetScore]],
) -> tuple[tuple[str, ...], Mapping[str, tuple[str, ...]]]:
    by_name = {card.tool_name: card for card in cards}
    names = tuple(by_name)
    reasons: dict[str, list[str]] = defaultdict(list)
    selected: list[str] = []

    def add(name: str, reason: str) -> None:
        if reason not in reasons[name]:
            reasons[name].append(reason)
        if name not in selected and len(selected) < MAX_CANDIDATES:
            selected.append(name)

    # Top-one preservation is the only mandatory allocation when many actions compete.
    for action_index, ranking in enumerate(rankings):
        add(ranking[0], f"action-{action_index}-top1")
    for action_index, ranking in enumerate(rankings):
        add(ranking[1], f"action-{action_index}-top2")

    for action_index, ranking in enumerate(rankings):
        top = ranking[0]
        siblings = _sibling_names(by_name[top], names)
        if siblings:
            sibling = min(
                siblings,
                key=lambda name: (
                    action_scores[action_index][name].rank,
                    name,
                ),
            )
            add(sibling, f"action-{action_index}-sibling-contrast")

    for action_index, ranking in enumerate(rankings):
        top_keys = _legal_key_union(by_name[ranking[0]])
        alternatives = []
        for name in ranking[1:]:
            score = action_scores[action_index][name]
            overlap = len(top_keys.intersection(_legal_key_union(by_name[name])))
            if score.role > 0.0 or overlap:
                alternatives.append((name, overlap, score))
        if alternatives:
            alternative = min(
                alternatives,
                key=lambda item: (
                    -int(item[2].role > 0.0),
                    -item[1],
                    item[2].rank,
                    item[0],
                ),
            )[0]
            add(alternative, f"action-{action_index}-schema-compatible")

    if len(selected) < MIN_CANDIDATES:
        for name in rankings[0]:
            add(name, "minimum-candidate-fill")
            if len(selected) == MIN_CANDIDATES:
                break
    selected.sort(
        key=lambda name: (
            min(scores[name].rank for scores in action_scores),
            name,
        )
    )
    return tuple(selected), {
        name: tuple(reasons[name]) for name in sorted(reasons) if name in selected
    }


def _render_packet(
    cards: Sequence[ToolSemanticCard],
    tasks: Sequence[object],
    candidate_names: Sequence[str],
    *,
    max_utf8_bytes: int,
) -> tuple[str, int, str, tuple[str, ...]]:
    by_name = {card.tool_name: card for card in cards}
    sections = [
        "AUDIO2TOOL EXECUTABLE SEMANTIC MICROGROUND",
        (
            "Return only one nonempty JSON array of registered tool calls. Select only "
            "from the supplied tool cards. Copy task values only from the speech or its "
            "validated English observation; never copy a synthetic example literal."
        ),
    ]
    task_ids: list[str] = []
    for task in tasks:
        card_id = getattr(task, "card_id")
        text = getattr(task, "text")
        task_ids.append(card_id)
        sections.append(f"TASK CARD {card_id}\n{text}")
    sections.extend(by_name[name].text for name in candidate_names)
    packet = "\n\n".join(sections) + "\n"
    if not packet.isascii():
        raise SemanticMicrogroundError("rendered packet must be ASCII English")
    rendered = packet.encode("utf-8")
    if len(rendered) > max_utf8_bytes:
        raise SemanticMicrogroundError(
            f"semantic microground packet exceeds byte budget: "
            f"{len(rendered)} > {max_utf8_bytes}; partial truncation is forbidden"
        )
    return (
        packet,
        len(rendered),
        hashlib.sha256(rendered).hexdigest(),
        tuple(task_ids),
    )


def route_semantic_microground(
    corpus: ExecutableSemanticCardCorpus,
    *,
    structured_state: Mapping[str, object] | None = None,
    observation: str | None = None,
    max_utf8_bytes: int = DEFAULT_MAX_UTF8_BYTES,
) -> SemanticMicrogroundRoute:
    """Route and render one deterministic microground without reward features."""

    if (structured_state is None) == (observation is None):
        raise SemanticMicrogroundError(
            "supply exactly one of structured_state or observation"
        )
    if (
        isinstance(max_utf8_bytes, bool)
        or not isinstance(max_utf8_bytes, int)
        or not 1 <= max_utf8_bytes <= DEFAULT_MAX_UTF8_BYTES
    ):
        raise SemanticMicrogroundError("max_utf8_bytes must be between one and 16384")
    cards, tasks = _validate_corpus(corpus)
    if structured_state is not None:
        if not isinstance(structured_state, Mapping):
            raise SemanticMicrogroundError("structured_state must be a mapping")
        action_queries = _action_queries(structured_state)
        representation = (
            "structured-state:current-request-fallback"
            if not structured_state.get("active_actions")
            else "structured-state"
        )
    else:
        assert observation is not None
        action_queries = (_required_ascii(observation, field="observation"),)
        representation = "task-blind-English-OBS"

    indexes = _build_indexes(cards)
    ranked = tuple(
        _rank_action(indexes, query, action_index)
        for action_index, query in enumerate(action_queries)
    )
    rankings = tuple(item[0] for item in ranked)
    scores = tuple(item[1] for item in ranked)
    candidate_names, reasons = _select_candidates(cards, rankings, scores)
    packet, byte_count, packet_sha256, task_ids = _render_packet(
        cards,
        tasks,
        candidate_names,
        max_utf8_bytes=max_utf8_bytes,
    )
    candidates = tuple(
        RoutedCandidate(
            tool_name=name,
            packet_rank=packet_rank,
            reasons=reasons[name],
            action_scores=tuple(action_score[name] for action_score in scores),
        )
        for packet_rank, name in enumerate(candidate_names, start=1)
    )
    trace_payload = {
        "policy_id": POLICY_ID,
        "corpus_sha256": corpus.sha256,
        "representation": representation,
        "action_queries": action_queries,
        "candidate_names": candidate_names,
        "candidates": tuple(asdict(candidate) for candidate in candidates),
        "task_card_ids": task_ids,
        "packet_utf8_bytes": byte_count,
        "packet_sha256": packet_sha256,
    }
    trace_bytes = json.dumps(
        trace_payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return SemanticMicrogroundRoute(
        policy_id=POLICY_ID,
        corpus_sha256=corpus.sha256,
        representation=representation,
        action_queries=action_queries,
        candidate_names=candidate_names,
        candidates=candidates,
        task_card_ids=task_ids,
        packet=packet,
        packet_utf8_bytes=byte_count,
        packet_sha256=packet_sha256,
        trace_sha256=hashlib.sha256(trace_bytes).hexdigest(),
    )


def evaluate_stage1_structure(
    response_text: str, corpus: ExecutableSemanticCardCorpus
) -> Stage1StructuralOutcome:
    """Evaluate parse/name/key validity without expected calls or reward."""

    cards, _tasks = _validate_corpus(corpus)
    calls, parsed = parse_tool_calls_text(response_text)
    by_name = {card.tool_name: card for card in cards}
    nonempty = parsed and bool(calls)
    registry_names_only = nonempty and all(call.name in by_name for call in calls)
    legal_key_sets_only = registry_names_only and all(
        tuple(sorted(str(key) for key in call.arguments))
        in by_name[call.name].legal_argument_key_sets
        for call in calls
    )
    return Stage1StructuralOutcome(
        parsed=parsed,
        registry_names_only=registry_names_only,
        legal_key_sets_only=legal_key_sets_only,
        call_count=len(calls),
    )


def aggregate_stage1_structure(
    outcomes: Sequence[Stage1StructuralOutcome],
) -> Stage1StructuralMetrics:
    """Aggregate structural outcomes without opening any task label."""

    rows = tuple(outcomes)
    if any(not isinstance(row, Stage1StructuralOutcome) for row in rows):
        raise SemanticMicrogroundError(
            "stage-1 aggregation requires Stage1StructuralOutcome rows"
        )
    return Stage1StructuralMetrics(
        total_count=len(rows),
        parse_count=sum(row.parsed for row in rows),
        registry_names_only_count=sum(row.registry_names_only for row in rows),
        legal_key_sets_only_count=sum(row.legal_key_sets_only for row in rows),
    )


__all__ = [
    "DEFAULT_MAX_UTF8_BYTES",
    "MAX_CANDIDATES",
    "MIN_CANDIDATES",
    "POLICY_ID",
    "ActionFacetScore",
    "RoutedCandidate",
    "SemanticMicrogroundError",
    "SemanticMicrogroundRoute",
    "Stage1StructuralMetrics",
    "Stage1StructuralOutcome",
    "aggregate_stage1_structure",
    "evaluate_stage1_structure",
    "route_semantic_microground",
]
