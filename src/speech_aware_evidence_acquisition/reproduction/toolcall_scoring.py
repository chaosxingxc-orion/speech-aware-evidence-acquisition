r"""Deterministic tool-call scoring for the Audio2Tool-style probes (P1/R1).

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
  sequences recurse. Fail-closed parsing: model text that carries neither
  contract below scores as an empty prediction.

Any change to these semantics requires a new version constant.

Two OUTPUT CONTRACTS, one parse (2026-09-04, ``A2T_PARSE_VERSION``)
--------------------------------------------------------------------
``parse_tool_calls_text`` originally read exactly one contract: the JSON
array this repository's own reconstructed prompt asked for. The Audio2Tool
benchmark's released code asks for a different one -- a CALL STRING,
``tool_name(param1=value1, param2=value2)`` -- and on the 2026-09-04
official-protocol replication every one of the 400 sealed rows was a call
string, so ``a2t-toolcall`` and ``a2t-toolcall-v2`` reported 0.0 with 400
parse failures. That was a format mismatch, not a model result, and it made
the repository's own scorers unable to read its own paper-facing runs.

The parse now reads BOTH contracts, JSON first:

1. a fenced or bare JSON array/object of ``{"name", "arguments"}`` entries
   (unchanged, and still tried first, so every sealed JSON-array row scores
   byte-identically to before);
2. otherwise, one or more call-shaped spans, IN ORDER, under the released
   code's own regexes -- ``(\w+)\s*\((.*?)\)`` for the spans and
   ``(\w+)\s*=\s*['\"]?([^,'\"]+)['\"]?`` for the arguments inside one,
   values ``.strip()``ed exactly as upstream does
   (``reproduction.audio2tool_official.parse``). Unlike the official parser,
   which is a single ``re.search`` and therefore reads only the FIRST call,
   this returns every span, because ``a2t-toolcall``/``a2t-toolcall-v2``
   score whole call SEQUENCES and a multi-intent row's second call is a real
   prediction rather than noise. The official scorer's first-call-only
   reading is preserved where it belongs: in
   ``reproduction.a2t_scorer.score_audio2tool_outputs_official``, which keeps
   using the vendored upstream parser untouched.

Argument values arrive from a call string as text, so they are coerced at
parse time the way ``toolcall_scoring_v2`` compares them anyway: ``true``/
``false`` (case-insensitive) become booleans and numeric literals become
``int``/``float``, which is what the JSON contract would have produced for
the same call. Everything else stays a string.

``A2T_SCORER_VERSION`` is deliberately NOT bumped: the metric semantics
above are unchanged, and that constant is the ``scorer_version`` string
already sealed into every prior Audio2Tool receipt. The parse layer carries
its own version constant, ``A2T_PARSE_VERSION``, which both registered
scorers surface as ``parse_version`` in their aggregate.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

A2T_SCORER_VERSION = "a2t-scorer-v1"
# Bumped whenever parse_tool_calls_text changes what it accepts; the metric
# version above is bumped only when the metrics themselves change.
A2T_PARSE_VERSION = "a2t-parse-v2-json-or-callstring"

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
# The released Audio2Tool code's own two regexes, character for character
# (audio_benchmark/models/base.py at commit b9d5383c, vendored verbatim as
# reproduction.audio2tool_official.parse). No re.DOTALL: upstream has none,
# so a span never runs across a newline here either.
_CALL_SPAN_RE = re.compile(r"(\w+)\s*\((.*?)\)")
_CALL_ARGUMENT_RE = re.compile(r"(\w+)\s*=\s*['\"]?([^,'\"]+)['\"]?")


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


def _coerce_call_string_value(text: str) -> object:
    """One call-string argument value, coerced the way the JSON contract
    would have carried it: booleans, then integers, then floats, else the
    stripped string."""

    value = text.strip()
    lowered = value.casefold()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def parse_call_string_calls(text: str) -> list[ToolCall]:
    """Every call-shaped span of ``text``, in order, under the released
    Audio2Tool code's own regexes (module docstring).

    Returns ``[]`` when the text carries no span at all, which is what makes
    it usable as the second branch of a fail-closed parse.
    """

    calls: list[ToolCall] = []
    for span in _CALL_SPAN_RE.finditer(text):
        name = span.group(1)
        arguments_text = span.group(2)
        arguments: dict[str, object] = {}
        if arguments_text.strip():
            for argument in _CALL_ARGUMENT_RE.finditer(arguments_text):
                arguments[argument.group(1)] = _coerce_call_string_value(
                    argument.group(2)
                )
        calls.append(ToolCall(name=name, arguments=arguments))
    return calls


def parse_tool_calls_text(text: str) -> tuple[list[ToolCall], bool]:
    """Extract tool calls from model output text; fail closed to ``([], False)``.

    Two contracts, JSON first (module docstring): a fenced or bare JSON
    array/object of ``{"name", "arguments"}`` entries, otherwise the
    released benchmark's call-string contract. JSON keeps priority, so every
    output that parsed before parses identically now.
    """

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
    call_string_calls = parse_call_string_calls(text)
    if call_string_calls:
        return call_string_calls, True
    return [], False
