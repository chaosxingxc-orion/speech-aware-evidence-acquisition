"""Deterministic tool-call scoring, v2 (``a2t-scorer-v2``): a paper-closer
re-reading of the same Audio2Tool outputs the v1 scorer
(:mod:`reproduction.toolcall_scoring`, ``a2t-scorer-v1``) scores, adopted
from the slice-S1 zero-contact re-scoring study's V2e candidate rule
(``analysis.a2t_scorer_v2_study``, verdict:
``docs/readiness/2026-09-03-a2t-scorer-v2-zero-contact-study.md``). v1 itself
is UNCHANGED (this module never edits it, imports it read-only) and stays
registered; v2 is reported side by side, never a replacement.

Semantics (``a2t-scorer-v2`` -- any further change needs a new version
constant):

- **Tool accuracy, ordered** (``tool_accuracy_ordered``): the SEQUENCE of
  predicted tool names equals the sequence of expected tool names,
  position-for-position -- the paper's own wording ("for multi-call cases,
  the ordered sequence of tools must match"), unlike v1's order-insensitive
  multiset check.
- **Tool accuracy, multiset** (``tool_accuracy_multiset``): v1's own
  ``toolcall_scoring.score_item`` tool-accuracy field, carried through
  unmodified for continuity/comparison -- never used to gate ``exact_match``
  here.
- **Exact match**: the MULTISET of ``(tool_name, arguments)`` calls equals
  the expected multiset -- v1's own Counter-based comparison, unchanged --
  once (a) any predicted argument key absent from every same-tool gold call
  in this row is DROPPED when its value canonically equals that tool's
  registry default (``V2b``: an omitted-but-defaulted argument is not an
  error), and (b) both sides' values are compared under type coercion
  (``V2d``: a numeric-looking string equals its numeric value,
  ``"true"``/``"false"`` strings equal the matching booleans). Exact match
  is deliberately NOT gated on ``tool_accuracy_ordered``: this is exactly
  the S1 study's adopted V2e rule (``V2a`` ordered tool accuracy, reported
  as its own field, is never ANDed into ``V2b``/``V2d``'s own multiset-based
  EM check -- see ``analysis.a2t_scorer_v2_study.score_under_rule``'s ``V2e``
  branch, which this module's ``score_item_v2`` reproduces exactly). A row
  whose tool-call multiset matches after stripping/coercion but whose call
  ORDER differs from gold therefore scores ``exact_match=1.0`` with
  ``tool_accuracy_ordered=0.0`` -- order is reported, not enforced, by EM.
- **Slot-F1**: micro P/R/F1 over ``(tool_name, argument_key, canonical
  value)`` triples, with the SAME stripping (drop default-valued extra
  predicted keys) and coercion applied to the predicted side before forming
  triples -- documented choice: this keeps Slot-F1 answering the same
  question Exact Match does ("how much of the argument content is actually
  wrong, once registry-default omissions and string/number type drift are
  no longer counted against the model"), rather than a metric with its own,
  looser notion of correctness. Gold-side values are canonicalized the same
  way (a no-op for the non-string values gold already carries). The
  UNSTRIPPED, UNCOERCED variant (byte-identical to v1's own Slot-F1) is
  still computed and exposed (``slot_true_positives_raw`` etc., surfaced by
  ``reproduction.a2t_scorer.score_audio2tool_outputs_v2`` as
  ``slot_f1_raw``) so a caller can see what stripping/coercion actually
  moved.
- **Registry defaults**: parsed from ``tools_registry.csv``'s
  ``argument_defaults`` cell (``parse_argument_defaults``/
  ``build_registry_defaults``, moved here byte-for-byte from the S1 study
  module, which now imports them back). Fail-closed: a gold call whose tool
  name has no entry at all in the supplied registry-defaults mapping raises
  :class:`RegistryDriftError` -- the registry and the gold manifest have
  drifted apart, and silently treating an unknown tool as "no defaults"
  would let stripping/coercion decisions rest on missing data. A PREDICTED
  call naming a tool absent from the registry is NOT an error: it simply
  never matches (no default to strip against, never appears in gold), which
  is exactly how a genuinely wrong tool name should score.
- **Canonical values**: reuses v1's own ``_canonical_value`` for the
  registry-default equality check (unchanged semantics: strings
  strip+casefold, numbers compare as float, bools stay bools); a separate
  ``_coerced_canonical_value`` widens only string values further (numeric-
  looking -> number, ``true``/``false`` -> bool) for the exact-match and
  Slot-F1 comparisons described above. Fail-closed parsing of the raw model
  text is unchanged -- ``reproduction.toolcall_scoring.parse_tool_calls_text``
  is reused verbatim, never reimplemented here.
"""

from __future__ import annotations

import ast
import json
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .toolcall_scoring import ToolCall, _canonical_value, _prf, score_item

A2T_SCORER_V2_VERSION = "a2t-scorer-v2"

# ``{tool_name: {argument_key: default_value}}`` -- the shape
# ``build_registry_defaults`` produces and ``score_item_v2`` consumes.
RegistryDefaults = Mapping[str, Mapping[str, object]]


class RegistryDriftError(RuntimeError):
    """A gold tool name has no entry in the supplied registry defaults."""


# ---------------------------------------------------------------------------
# Registry-default parsing (moved here from ``analysis.a2t_scorer_v2_study``,
# which now imports these two public functions back -- byte-identical
# behaviour, shared by the study and this scorer so they never drift apart).
# ---------------------------------------------------------------------------


def _split_top_level(text: str) -> list[str]:
    """Split ``text`` on commas that are outside quotes and outside any
    bracket/brace/paren nesting (the real registry only ever nests an empty
    ``{}``, but this stays correct for a value that legitimately embeds a
    comma inside a container)."""

    parts: list[str] = []
    current: list[str] = []
    depth = 0
    quote: str | None = None
    for char in text:
        if quote is not None:
            current.append(char)
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
            current.append(char)
            continue
        if char in "([{":
            depth += 1
            current.append(char)
            continue
        if char in ")]}":
            depth -= 1
            current.append(char)
            continue
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(char)
    if current:
        parts.append("".join(current))
    return parts


def _parse_default_literal(text: str) -> tuple[bool, object]:
    """(ok, value) for one default's raw value text: Python literal first,
    then the JSON-style tokens ``ast.literal_eval`` itself rejects."""

    stripped = text.strip()
    try:
        return True, ast.literal_eval(stripped)
    except (ValueError, SyntaxError):
        pass
    lowered = stripped.casefold()
    if lowered == "null":
        return True, None
    if lowered == "true":
        return True, True
    if lowered == "false":
        return True, False
    try:
        return True, json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return False, None


def parse_argument_defaults(text: str) -> dict[str, object]:
    """One registry row's ``argument_defaults`` cell -> ``{key: value}``.

    A segment that is blank, lacks ``=``, or whose value cannot be parsed by
    either path above is silently skipped (never crashes over one
    unparseable default) rather than raising -- this function only ever
    WIDENS what counts as a known default; skipping a stray one degrades a
    downstream rule to be slightly more conservative (fewer keys recognised
    as default-valued), never incorrect.
    """

    result: dict[str, object] = {}
    raw = (text or "").strip()
    if not raw:
        return result
    for part in _split_top_level(raw):
        segment = part.strip()
        if not segment or "=" not in segment:
            continue
        key, _, value_text = segment.partition("=")
        key = key.strip()
        if not key:
            continue
        ok, value = _parse_default_literal(value_text)
        if ok:
            result[key] = value
    return result


def build_registry_defaults(registry_rows: Sequence[Mapping[str, str]]) -> dict[str, dict[str, object]]:
    """``{tool_name: {argument_key: default_value}}`` over every registry row."""

    defaults: dict[str, dict[str, object]] = {}
    for row in registry_rows:
        tool_name = row.get("tool_name")
        if not tool_name:
            continue
        defaults[tool_name] = parse_argument_defaults(row.get("argument_defaults", ""))
    return defaults


# ---------------------------------------------------------------------------
# Type-coercing canonical value (moved here from
# ``analysis.a2t_scorer_v2_study``, which now imports ``_coerced_canonical_
# value``/``_exact_match_coerced`` back; v1's own ``_canonical_value`` is
# never modified or bypassed elsewhere).
# ---------------------------------------------------------------------------


def _coerced_canonical_value(value: object) -> object:
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return ("num", float(value))
    if isinstance(value, str):
        text = value.strip()
        lowered = text.casefold()
        if lowered in ("true", "false"):
            return ("bool", lowered == "true")
        try:
            return ("num", float(text))
        except ValueError:
            return ("str", lowered)
    if isinstance(value, Mapping):
        return (
            "map",
            tuple(sorted((str(k), _coerced_canonical_value(v)) for k, v in value.items())),
        )
    if isinstance(value, (list, tuple)):
        return ("seq", tuple(_coerced_canonical_value(item) for item in value))
    if value is None:
        return ("null",)
    return ("other", repr(value))


def _canonical_call_coerced(call: ToolCall) -> object:
    return (call.name, _coerced_canonical_value(dict(call.arguments)))


def _exact_match_coerced(expected: Sequence[ToolCall], predicted: Sequence[ToolCall]) -> float:
    expected_calls = Counter(_canonical_call_coerced(call) for call in expected)
    predicted_calls = Counter(_canonical_call_coerced(call) for call in predicted)
    return 1.0 if expected_calls == predicted_calls else 0.0


def _is_coercible_string(value: object) -> bool:
    """``True`` iff ``value`` is a string ``_coerced_canonical_value`` maps
    to a number or a boolean rather than leaving it a plain string -- the
    ``coerced_values`` counter's definition: a value on the PREDICTED side
    (after stripping) whose type coercion actually widened its reading,
    independent of whether it goes on to match gold."""

    if not isinstance(value, str):
        return False
    text = value.strip()
    if text.casefold() in ("true", "false"):
        return True
    try:
        float(text)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Extra-key stripping (moved here from ``analysis.a2t_scorer_v2_study``,
# which now imports ``_strip_extra_keys`` back).
# ---------------------------------------------------------------------------


def _gold_keys_by_tool(expected: Sequence[ToolCall]) -> dict[str, set[str]]:
    keys_by_tool: dict[str, set[str]] = {}
    for call in expected:
        keys_by_tool.setdefault(call.name, set()).update(call.arguments)
    return keys_by_tool


def _strip_extra_keys(
    expected: Sequence[ToolCall],
    predicted: Sequence[ToolCall],
    defaults_by_tool: Mapping[str, Mapping[str, object]],
    *,
    default_only: bool,
) -> tuple[ToolCall, ...]:
    """Drop, from every predicted call, argument keys the SAME-NAMED gold
    call(s) in this row never carry -- either only the default-valued ones
    (``default_only=True``, V2b/V2d/v2) or all of them regardless of value
    (``default_only=False``, the study's V2c, unused by v2 itself). Tool
    names/order are never touched, so tool accuracy under either mode is
    identical to the untouched-predicted computation."""

    gold_keys_by_tool = _gold_keys_by_tool(expected)
    stripped: list[ToolCall] = []
    for call in predicted:
        gold_keys = gold_keys_by_tool.get(call.name, set())
        tool_defaults = defaults_by_tool.get(call.name, {})
        new_args: dict[str, object] = {}
        for key, value in call.arguments.items():
            if key in gold_keys:
                new_args[key] = value
                continue
            if default_only:
                has_default = key in tool_defaults
                if has_default and _canonical_value(value) == _canonical_value(tool_defaults[key]):
                    continue  # drop: default-valued extra
                new_args[key] = value  # keep: non-default extra
            # default_only is False (study's V2c): unconditionally drop the extra key.
        stripped.append(ToolCall(name=call.name, arguments=new_args))
    return tuple(stripped)


def _slot_triples_coerced(calls: Sequence[ToolCall]) -> "Counter[object]":
    triples: Counter[object] = Counter()
    for call in calls:
        for key, value in call.arguments.items():
            triples[(call.name, str(key), _coerced_canonical_value(value))] += 1
    return triples


# ---------------------------------------------------------------------------
# v2 item/aggregate scoring.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ItemScoreV2:
    tool_accuracy_ordered: float
    tool_accuracy_multiset: float
    exact_match: float
    slot_true_positives: int
    slot_expected_total: int
    slot_predicted_total: int
    slot_true_positives_raw: int
    slot_expected_total_raw: int
    slot_predicted_total_raw: int
    extra_keys_stripped: int
    coerced_values: int

    @property
    def slot_precision(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[0]

    @property
    def slot_recall(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[1]

    @property
    def slot_f1(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[2]

    @property
    def slot_precision_raw(self) -> float:
        return _prf(self.slot_true_positives_raw, self.slot_predicted_total_raw, self.slot_expected_total_raw)[0]

    @property
    def slot_recall_raw(self) -> float:
        return _prf(self.slot_true_positives_raw, self.slot_predicted_total_raw, self.slot_expected_total_raw)[1]

    @property
    def slot_f1_raw(self) -> float:
        return _prf(self.slot_true_positives_raw, self.slot_predicted_total_raw, self.slot_expected_total_raw)[2]


@dataclass(frozen=True)
class AggregateScoreV2:
    n_items: int
    tool_accuracy_ordered: float
    tool_accuracy_multiset: float
    exact_match: float
    slot_true_positives: int
    slot_expected_total: int
    slot_predicted_total: int
    slot_true_positives_raw: int
    slot_expected_total_raw: int
    slot_predicted_total_raw: int
    extra_keys_stripped: int
    coerced_values: int

    @property
    def slot_precision(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[0]

    @property
    def slot_recall(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[1]

    @property
    def slot_f1(self) -> float:
        return _prf(self.slot_true_positives, self.slot_predicted_total, self.slot_expected_total)[2]

    @property
    def slot_precision_raw(self) -> float:
        return _prf(self.slot_true_positives_raw, self.slot_predicted_total_raw, self.slot_expected_total_raw)[0]

    @property
    def slot_recall_raw(self) -> float:
        return _prf(self.slot_true_positives_raw, self.slot_predicted_total_raw, self.slot_expected_total_raw)[1]

    @property
    def slot_f1_raw(self) -> float:
        return _prf(self.slot_true_positives_raw, self.slot_predicted_total_raw, self.slot_expected_total_raw)[2]


def score_item_v2(
    expected: Sequence[ToolCall],
    predicted: Sequence[ToolCall],
    *,
    registry_defaults: RegistryDefaults,
) -> ItemScoreV2:
    """One item's v2 score. Fail-closed: raises :class:`RegistryDriftError`
    if any GOLD tool name has no entry in ``registry_defaults`` (the
    registry and the gold manifest have drifted apart); a predicted call
    naming an unknown tool is tolerated -- it simply has no default to
    strip against and never matches gold, which is exactly how a genuinely
    wrong tool name should score."""

    for call in expected:
        if call.name not in registry_defaults:
            raise RegistryDriftError(
                f"gold tool name {call.name!r} has no entry in the supplied registry "
                "defaults; refusing to score under a2t-scorer-v2 with a drifted registry"
            )

    v1_item = score_item(expected, predicted)

    expected_names = [call.name for call in expected]
    predicted_names = [call.name for call in predicted]
    tool_accuracy_ordered = 1.0 if expected_names == predicted_names else 0.0

    stripped = _strip_extra_keys(expected, predicted, registry_defaults, default_only=True)
    extra_keys_stripped = sum(len(call.arguments) for call in predicted) - sum(
        len(call.arguments) for call in stripped
    )
    coerced_values = sum(
        1 for call in stripped for value in call.arguments.values() if _is_coercible_string(value)
    )

    # Multiset-based, exactly the S1 study's adopted V2e EM rule (module
    # docstring's "Exact match" bullet): NOT gated by tool_accuracy_ordered.
    exact_match = _exact_match_coerced(expected, stripped)

    expected_triples = _slot_triples_coerced(expected)
    predicted_triples = _slot_triples_coerced(stripped)
    overlap = sum((expected_triples & predicted_triples).values())

    return ItemScoreV2(
        tool_accuracy_ordered=tool_accuracy_ordered,
        tool_accuracy_multiset=v1_item.tool_accuracy,
        exact_match=exact_match,
        slot_true_positives=overlap,
        slot_expected_total=sum(expected_triples.values()),
        slot_predicted_total=sum(predicted_triples.values()),
        slot_true_positives_raw=v1_item.slot_true_positives,
        slot_expected_total_raw=v1_item.slot_expected_total,
        slot_predicted_total_raw=v1_item.slot_predicted_total,
        extra_keys_stripped=extra_keys_stripped,
        coerced_values=coerced_values,
    )


def aggregate_v2(scores: Iterable[ItemScoreV2]) -> AggregateScoreV2:
    items = list(scores)
    if not items:
        return AggregateScoreV2(0, 0.0, 0.0, 0.0, 0, 0, 0, 0, 0, 0, 0, 0)
    n = len(items)
    return AggregateScoreV2(
        n_items=n,
        tool_accuracy_ordered=sum(item.tool_accuracy_ordered for item in items) / n,
        tool_accuracy_multiset=sum(item.tool_accuracy_multiset for item in items) / n,
        exact_match=sum(item.exact_match for item in items) / n,
        slot_true_positives=sum(item.slot_true_positives for item in items),
        slot_expected_total=sum(item.slot_expected_total for item in items),
        slot_predicted_total=sum(item.slot_predicted_total for item in items),
        slot_true_positives_raw=sum(item.slot_true_positives_raw for item in items),
        slot_expected_total_raw=sum(item.slot_expected_total_raw for item in items),
        slot_predicted_total_raw=sum(item.slot_predicted_total_raw for item in items),
        extra_keys_stripped=sum(item.extra_keys_stripped for item in items),
        coerced_values=sum(item.coerced_values for item in items),
    )
