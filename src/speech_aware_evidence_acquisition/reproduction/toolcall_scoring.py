"""Deterministic tool-call scoring for the Audio2Tool-style probes (P1/R1).

Reimplements the three metrics of arXiv:2604.22821 (official eval scripts
unreleased at survey time — placeholder repo only). Interpretation choices,
recorded here because the paper text does not fully pin them down:

- **Tool Accuracy** (item-level, binary): the multiset of predicted tool
  names equals the multiset of expected tool names. Order-insensitive;
  duplicates must be matched one-for-one; tool names compare exactly
  (case-sensitive — they are API identifiers).
- **Exact Match** (item-level, binary): the multiset of canonicalized calls
  (name + arguments) equals the expected multiset.
- **Slot-F1**: micro-averaged P/R/F1 over the multiset of
  ``(tool_name, argument_key, canonical_value)`` triples; corpus-level
  aggregation sums the raw counts across items (micro), while Tool
  Accuracy / Exact Match aggregate as item means.
- **Canonical values**: strings strip+casefold; ints/floats compare
  numerically; bools are bools, never numbers or strings; mappings and
  sequences recurse. Fail-closed parsing: model text that does not contain
  valid JSON tool calls scores as an empty prediction.

Any change to these semantics requires a new version constant.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

A2T_SCORER_VERSION = "a2t-scorer-v1"

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: Mapping[str, object] = field(default_factory=dict)


def _canonical_value(value: object) -> object:
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return ("num", float(value))
    if isinstance(value, str):
        return ("str", value.strip().casefold())
    if isinstance(value, Mapping):
        return (
            "map",
            tuple(sorted((str(key), _canonical_value(val)) for key, val in value.items())),
        )
    if isinstance(value, (list, tuple)):
        return ("seq", tuple(_canonical_value(item) for item in value))
    if value is None:
        return ("null",)
    return ("other", repr(value))


def _canonical_call(call: ToolCall) -> object:
    return (call.name, _canonical_value(call.arguments))


def _slot_triples(calls: Sequence[ToolCall]) -> Counter[object]:
    triples: Counter[object] = Counter()
    for call in calls:
        for key, value in call.arguments.items():
            triples[(call.name, str(key), _canonical_value(value))] += 1
    return triples


def _prf(true_positives: int, predicted_total: int, expected_total: int) -> tuple[float, float, float]:
    precision = true_positives / predicted_total if predicted_total else 0.0
    recall = true_positives / expected_total if expected_total else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


@dataclass(frozen=True)
class ItemScore:
    tool_accuracy: float
    exact_match: float
    slot_true_positives: int
    slot_expected_total: int
    slot_predicted_total: int

    @property
    def slot_precision(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[0]

    @property
    def slot_recall(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[1]

    @property
    def slot_f1(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[2]


@dataclass(frozen=True)
class AggregateScore:
    n_items: int
    tool_accuracy: float
    exact_match: float
    slot_true_positives: int
    slot_expected_total: int
    slot_predicted_total: int

    @property
    def slot_precision(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[0]

    @property
    def slot_recall(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[1]

    @property
    def slot_f1(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[2]


def score_item(expected: Sequence[ToolCall], predicted: Sequence[ToolCall]) -> ItemScore:
    expected_names = Counter(call.name for call in expected)
    predicted_names = Counter(call.name for call in predicted)
    tool_accuracy = 1.0 if expected_names == predicted_names else 0.0

    expected_calls = Counter(_canonical_call(call) for call in expected)
    predicted_calls = Counter(_canonical_call(call) for call in predicted)
    exact_match = 1.0 if expected_calls == predicted_calls else 0.0

    expected_triples = _slot_triples(expected)
    predicted_triples = _slot_triples(predicted)
    overlap = sum((expected_triples & predicted_triples).values())
    return ItemScore(
        tool_accuracy=tool_accuracy,
        exact_match=exact_match,
        slot_true_positives=overlap,
        slot_expected_total=sum(expected_triples.values()),
        slot_predicted_total=sum(predicted_triples.values()),
    )


def aggregate(scores: Iterable[ItemScore]) -> AggregateScore:
    items = list(scores)
    if not items:
        return AggregateScore(0, 0.0, 0.0, 0, 0, 0)
    return AggregateScore(
        n_items=len(items),
        tool_accuracy=sum(score.tool_accuracy for score in items) / len(items),
        exact_match=sum(score.exact_match for score in items) / len(items),
        slot_true_positives=sum(score.slot_true_positives for score in items),
        slot_expected_total=sum(score.slot_expected_total for score in items),
        slot_predicted_total=sum(score.slot_predicted_total for score in items),
    )


def _as_tool_calls(payload: object) -> list[ToolCall] | None:
    entries = payload if isinstance(payload, list) else [payload]
    calls: list[ToolCall] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            return None
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            return None
        arguments = entry.get("arguments", {})
        if not isinstance(arguments, Mapping):
            return None
        calls.append(ToolCall(name=name, arguments=dict(arguments)))
    return calls


def parse_tool_calls_text(text: str) -> tuple[list[ToolCall], bool]:
    """Extract tool calls from model output text; fail closed to ``([], False)``."""
    candidates = [match.strip() for match in _FENCE_RE.findall(text)]
    candidates.append(text.strip())
    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        calls = _as_tool_calls(payload)
        if calls is not None:
            return calls, True
    return [], False
