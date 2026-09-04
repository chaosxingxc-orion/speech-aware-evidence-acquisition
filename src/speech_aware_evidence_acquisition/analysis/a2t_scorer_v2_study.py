"""Slice S1: zero-contact re-scoring study of sealed Audio2Tool outputs.

Model-free, read-only: this module never opens a model session, embedding
service, or network connection. It re-scores already-written, already-sealed
``outputs.jsonl`` files with the UNCHANGED v1 scorer
(``reproduction.toolcall_scoring`` -- ``parse_tool_calls_text``,
``score_item``, ``aggregate``) and the unchanged v1 gold parser
(``reproduction.toolcall_gold``, reached only through
``data.audio2tool.load_expected_calls``), then asks two questions the paper
comparison (arXiv:2604.22821 Table 3) cannot answer on its own:

1. How much of the Tier-1 tool-acc/EM gap this repo's frozen A0 read shows
   (58.0/12.0 vs the paper's 92.4/92.4) is v1 SCORER SEMANTICS -- order
   sensitivity, registry-default argument omission, string/number type
   drift -- rather than genuine model error?
2. Do any of those semantics changes flip the paired conclusions the two
   September 104-row AgentLoop flights already reached under v1?

Design (mirrors the failure-taxonomy and candidate-rule spec in the study's
own preregistration note, ``docs/readiness/2026-09-03-a2t-scorer-v2-zero-
contact-study.md``):

- :func:`classify_row` assigns exactly one PRIMARY failure category to a
  single ``exact_match == 0`` row, in a fixed priority order (parse failure
  first, then empty prediction, then tool-set mismatch, then tool-ORDER
  mismatch when the multiset already matches, then four key/value-level
  categories that require the predicted and gold call sequences to already
  match position-for-position, and a ``MIXED`` catch-all). It raises on an
  already-exact row -- the taxonomy is defined only for v1 failures.
- :func:`score_under_rule` scores ONE row under one of six candidate
  scorer semantics (``V1`` unchanged, ``V2a`` ordered tool accuracy,
  ``V2b`` default-valued-extra-key tolerant EM, ``V2c`` any-extra-key
  tolerant EM (lenient), ``V2d`` V2b plus numeric/boolean string type
  coercion, ``V2e`` the proposed v2 = V2a + V2b + V2d combined). Every rule
  is built ONLY from the unchanged ``score_item``/``_canonical_value``
  machinery plus a value-preserving transform of the PREDICTED call list;
  gold is never touched, and V1 itself is never re-derived, only called.
- :func:`run_study` is the pure orchestration entry point: given already-
  resolved gold (``data.audio2tool.load_expected_calls``) and already-
  resolved tool-registry rows (``data.audio2tool.load_tool_registry``), it
  loads each named arm's ``outputs.jsonl``, runs the v1 identity check
  against a caller-supplied sealed target, the Step-2 taxonomy, and the
  Step-3 rule table, and (for a source with a designated baseline arm) the
  paired exact-match saves/harms/ties between every other arm and that
  baseline under ``V1`` and ``V2e``.

No function in this module performs import-time I/O; ``main`` is the only
place that touches the umbrella lock, the controlled data root, or the
committed sealed-summary JSON files, and it refuses to overwrite an
existing ``summary.json`` (one-shot read discipline, same pattern as
``analysis.a2t_read``).

Registry-default parsing (``parse_argument_defaults``) implements exactly
the rule the study brief pins: split ``tools_registry.csv``'s
``argument_defaults`` cell on commas OUTSIDE quotes/brackets, each
``key=value`` segment's value via ``ast.literal_eval`` with a JSON-style
fallback for the literal tokens ``null``/``true``/``false`` that
``ast.literal_eval`` itself rejects (the CSV's defaults are JSON-shaped,
not Python-shaped -- ``pin=null`` is common in the real registry). That
parser, plus the type-coercing canonical value and extra-key-stripping
helpers ``score_under_rule`` builds V2b-V2e from, now live in
``reproduction.toolcall_scoring_v2`` (slice C3c, the registered
``a2t-scorer-v2`` adopts this study's V2e verdict) and are imported back
here byte-identical; this module's own behaviour is unchanged.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..reproduction.toolcall_scoring import (
    ToolCall,
    aggregate,
    parse_tool_calls_text,
    score_item,
)
from ..reproduction.toolcall_scoring import _canonical_value  # house pattern, see a2t_pop_read.py / a2t_s2_read.py / pphon_decomp.py
# Registry-default parsing, type-coercing canonical value, and extra-key
# stripping now live in ``reproduction.toolcall_scoring_v2`` (slice C3c,
# shared with the registered ``a2t-scorer-v2`` scorer); re-imported here
# byte-identical so this study's own behaviour is unchanged.
from ..reproduction.toolcall_scoring_v2 import (
    _coerced_canonical_value,
    _exact_match_coerced,
    _strip_extra_keys,
    build_registry_defaults,
    parse_argument_defaults,
)

RESULT_SCHEMA = "saea-a2t-scorer-v2-study-v1"

RULES: tuple[str, ...] = ("V1", "V2a", "V2b", "V2c", "V2d", "V2e")

CATEGORIES: tuple[str, ...] = (
    "PARSE_FAIL",
    "EMPTY",
    "TOOL_SET_WRONG",
    "TOOL_ORDER_ONLY",
    "EXTRA_KEYS_DEFAULT_ONLY",
    "EXTRA_KEYS_NONDEFAULT",
    "MISSING_KEYS_ONLY",
    "CASE_OR_TYPE_ONLY",
    "VALUE_WRONG",
    "MIXED",
)

_ROUND_DECIMALS = 4


class ScorerV2StudyError(RuntimeError):
    """An outputs file, sealed target, or registry row cannot be read/used."""


# ---------------------------------------------------------------------------
# Step 2 -- failure taxonomy.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RowClassification:
    category: str
    n_gold_calls: int
    n_pred_calls: int
    keys_extra: tuple[str, ...]
    keys_missing: tuple[str, ...]
    tool_names: tuple[str, ...]


def classify_row(
    expected: Sequence[ToolCall],
    predicted: Sequence[ToolCall],
    parsed: bool,
    defaults_by_tool: Mapping[str, Mapping[str, object]],
) -> RowClassification:
    """Assign the single primary failure category (spec order, first match).

    Defined only for a v1 ``exact_match == 0`` row; raises
    :class:`ScorerV2StudyError` if the row is actually already exact (a
    caller bug, since the taxonomy has no "exact" bucket).
    """

    n_gold_calls = len(expected)
    n_pred_calls = len(predicted)
    tool_names = tuple(sorted({call.name for call in expected} | {call.name for call in predicted}))

    if not parsed:
        return RowClassification("PARSE_FAIL", n_gold_calls, n_pred_calls, (), (), tool_names)
    if n_pred_calls == 0:
        return RowClassification("EMPTY", n_gold_calls, n_pred_calls, (), (), tool_names)

    expected_names = Counter(call.name for call in expected)
    predicted_names = Counter(call.name for call in predicted)
    if expected_names != predicted_names:
        return RowClassification("TOOL_SET_WRONG", n_gold_calls, n_pred_calls, (), (), tool_names)

    expected_order = [call.name for call in expected]
    predicted_order = [call.name for call in predicted]
    if expected_order != predicted_order:
        return RowClassification("TOOL_ORDER_ONLY", n_gold_calls, n_pred_calls, (), (), tool_names)

    # Names AND order match position-for-position (implies equal length):
    # a well-defined per-call key/value comparison is now possible.
    keys_extra: list[str] = []
    keys_missing: list[str] = []
    any_extra = False
    any_missing = False
    all_extra_default = True
    shared_mismatch_count = 0
    shared_mismatch_resolved_count = 0

    for gold_call, pred_call in zip(expected, predicted):
        gold_args = gold_call.arguments
        pred_args = pred_call.arguments
        gold_keys = set(gold_args)
        pred_keys = set(pred_args)
        extras = pred_keys - gold_keys
        missing = gold_keys - pred_keys
        shared = gold_keys & pred_keys

        if extras:
            any_extra = True
        if missing:
            any_missing = True

        tool_defaults = defaults_by_tool.get(pred_call.name, {})
        for key in sorted(extras):
            keys_extra.append(key)
            has_default = key in tool_defaults
            if not has_default or _canonical_value(pred_args[key]) != _canonical_value(tool_defaults[key]):
                all_extra_default = False

        for key in sorted(missing):
            keys_missing.append(key)

        for key in sorted(shared):
            gold_value = gold_args[key]
            pred_value = pred_args[key]
            if _canonical_value(gold_value) == _canonical_value(pred_value):
                continue
            shared_mismatch_count += 1
            if _coerced_canonical_value(gold_value) == _coerced_canonical_value(pred_value):
                shared_mismatch_resolved_count += 1

    exact = not any_extra and not any_missing and shared_mismatch_count == 0
    if exact:
        raise ScorerV2StudyError(
            "classify_row called on an already-exact-match row; the taxonomy is "
            "defined only for v1 exact_match == 0 rows"
        )

    keys_extra_t = tuple(keys_extra)
    keys_missing_t = tuple(keys_missing)

    if any_extra and any_missing:
        category = "MIXED"
    elif any_extra:
        if shared_mismatch_count > 0:
            category = "MIXED"
        elif all_extra_default:
            category = "EXTRA_KEYS_DEFAULT_ONLY"
        else:
            category = "EXTRA_KEYS_NONDEFAULT"
    elif any_missing:
        category = "MIXED" if shared_mismatch_count > 0 else "MISSING_KEYS_ONLY"
    else:
        # Equal key sets; shared_mismatch_count must be > 0 (else "exact" above).
        category = (
            "CASE_OR_TYPE_ONLY"
            if shared_mismatch_count == shared_mismatch_resolved_count
            else "VALUE_WRONG"
        )

    return RowClassification(category, n_gold_calls, n_pred_calls, keys_extra_t, keys_missing_t, tool_names)


# ---------------------------------------------------------------------------
# Step 3 -- candidate v2 semantics.
# ---------------------------------------------------------------------------


def score_under_rule(
    rule: str,
    expected: Sequence[ToolCall],
    predicted: Sequence[ToolCall],
    defaults_by_tool: Mapping[str, Mapping[str, object]],
) -> tuple[float, float]:
    """(tool_accuracy, exact_match) for ONE row under one candidate rule.

    ``V1`` calls the unchanged ``score_item`` and returns its two fields
    verbatim. Every other rule still calls ``score_item``/``_canonical_value``
    (imported, never re-derived) over a value-preserving transform of the
    predicted call list (or, for tool accuracy, an ordered-sequence check
    the paper's own wording asks for) -- gold is never touched.
    """

    if rule not in RULES:
        raise ScorerV2StudyError(f"unknown rule {rule!r}; expected one of {RULES}")

    v1_item = score_item(expected, predicted)
    if rule == "V1":
        return v1_item.tool_accuracy, v1_item.exact_match

    ordered_tool_accuracy = (
        1.0 if [call.name for call in predicted] == [call.name for call in expected] else 0.0
    )
    if rule == "V2a":
        return ordered_tool_accuracy, v1_item.exact_match

    if rule == "V2b":
        stripped = _strip_extra_keys(expected, predicted, defaults_by_tool, default_only=True)
        em = score_item(expected, stripped).exact_match
        return v1_item.tool_accuracy, em

    if rule == "V2c":
        stripped = _strip_extra_keys(expected, predicted, defaults_by_tool, default_only=False)
        em = score_item(expected, stripped).exact_match
        return v1_item.tool_accuracy, em

    if rule == "V2d":
        stripped = _strip_extra_keys(expected, predicted, defaults_by_tool, default_only=True)
        em = _exact_match_coerced(expected, stripped)
        return v1_item.tool_accuracy, em

    # V2e = V2a (ordered tool accuracy) + V2b (default-extra strip) + V2d (type coercion).
    stripped = _strip_extra_keys(expected, predicted, defaults_by_tool, default_only=True)
    em = _exact_match_coerced(expected, stripped)
    return ordered_tool_accuracy, em


# ---------------------------------------------------------------------------
# Row loading and per-source/per-arm orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoadedRow:
    sample_id: str
    tier: str
    parsed: bool
    predicted: tuple[ToolCall, ...]
    expected: tuple[ToolCall, ...]


def _model_text(row: Mapping[str, object], text_field: str, *, context: str) -> str:
    value = row.get(text_field)
    if not isinstance(value, str):
        raise ScorerV2StudyError(f"{context}: row lacks a string {text_field!r} field")
    return value


def load_outputs_rows(
    path: Path,
    gold_by_sample_id: Mapping[str, Sequence[ToolCall]],
    *,
    text_field: str,
) -> list[LoadedRow]:
    """Every row of one sealed ``outputs.jsonl``, re-parsed under the
    UNCHANGED v1 ``parse_tool_calls_text`` and paired with its frozen gold.

    ``text_field`` names the row's raw-model-text key: A0's older flight
    shape carries ``response_text``; the September AgentLoop flights carry
    ``text`` (the same field ``reproduction.a2t_scorer.
    score_audio2tool_outputs`` reads for the registered ``a2t-toolcall``
    scorer). Fail-closed: a missing/duplicate sample_id or a sample_id
    outside the supplied gold map raises.
    """

    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ScorerV2StudyError(f"cannot read outputs {path}: {error}") from error
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise ScorerV2StudyError(f"outputs file {path} is empty")

    rows: list[LoadedRow] = []
    seen: set[str] = set()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ScorerV2StudyError(f"{path} line {number} malformed: {error}") from error
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ScorerV2StudyError(f"{path} line {number} lacks a sample_id")
        if sample_id in seen:
            raise ScorerV2StudyError(f"{path} has a duplicate sample_id {sample_id!r}")
        seen.add(sample_id)
        expected = gold_by_sample_id.get(sample_id)
        if expected is None:
            raise ScorerV2StudyError(
                f"{path} sample_id {sample_id!r} has no frozen gold in the supplied map"
            )
        model_text = _model_text(row, text_field, context=f"{path} line {number} ({sample_id})")
        predicted, parsed = parse_tool_calls_text(model_text)
        tier = sample_id.rsplit(":", 1)[0]
        rows.append(
            LoadedRow(
                sample_id=sample_id,
                tier=tier,
                parsed=parsed,
                predicted=tuple(predicted),
                expected=tuple(expected),
            )
        )
    return rows


def _tiered(rows: Sequence[LoadedRow]) -> dict[str, list[LoadedRow]]:
    by_tier: dict[str, list[LoadedRow]] = {}
    for row in rows:
        by_tier.setdefault(row.tier, []).append(row)
    return by_tier


def _aggregate_v1(rows: Sequence[LoadedRow]) -> dict[str, object]:
    items = [score_item(row.expected, row.predicted) for row in rows]
    agg = aggregate(items)
    return {"n": agg.n_items, "tool_accuracy": agg.tool_accuracy, "exact_match": agg.exact_match}


def per_tier_v1(rows: Sequence[LoadedRow]) -> dict[str, dict[str, object]]:
    return {tier: _aggregate_v1(tier_rows) for tier, tier_rows in sorted(_tiered(rows).items())}


def _round4(value: float) -> float:
    return round(float(value), _ROUND_DECIMALS)


def identity_check(
    rows: Sequence[LoadedRow],
    target_overall: Mapping[str, float] | None,
    target_per_tier: Mapping[str, Mapping[str, float]] | None,
) -> dict[str, object]:
    """Recompute v1 overall/per-tier tool_accuracy+exact_match and compare
    (rounded to 4 decimals) against a caller-supplied sealed target."""

    overall = _aggregate_v1(rows)
    per_tier = per_tier_v1(rows)
    mismatches: list[dict[str, object]] = []

    for key, expected_value in (target_overall or {}).items():
        actual_value = overall.get(key)
        if actual_value is None or _round4(actual_value) != _round4(expected_value):
            mismatches.append(
                {"scope": "overall", "field": key, "expected": expected_value, "actual": actual_value}
            )

    for tier, targets in (target_per_tier or {}).items():
        actual = per_tier.get(tier)
        if actual is None:
            mismatches.append({"scope": tier, "field": "presence", "expected": "present", "actual": "missing"})
            continue
        for key, expected_value in targets.items():
            actual_value = actual.get(key)
            if actual_value is None or _round4(actual_value) != _round4(expected_value):
                mismatches.append(
                    {"scope": tier, "field": key, "expected": expected_value, "actual": actual_value}
                )

    return {"overall": overall, "per_tier": per_tier, "match": not mismatches, "mismatches": mismatches}


def taxonomy_counts(
    rows: Sequence[LoadedRow], defaults_by_tool: Mapping[str, Mapping[str, object]]
) -> dict[str, dict[str, int]]:
    """``{tier: {category: count}}`` over every v1 ``exact_match == 0`` row."""

    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        if score_item(row.expected, row.predicted).exact_match == 1.0:
            continue
        classification = classify_row(row.expected, row.predicted, row.parsed, defaults_by_tool)
        tier_counts = counts.setdefault(row.tier, {})
        tier_counts[classification.category] = tier_counts.get(classification.category, 0) + 1
    return counts


def rule_table(
    rows: Sequence[LoadedRow], defaults_by_tool: Mapping[str, Mapping[str, object]]
) -> dict[str, dict[str, dict[str, object]]]:
    """``{rule: {tier_or_overall: {n, tool_accuracy, exact_match}}}``."""

    by_tier = _tiered(rows)
    scopes: list[tuple[str, Sequence[LoadedRow]]] = [(tier, by_tier[tier]) for tier in sorted(by_tier)]
    scopes.append(("overall", rows))

    table: dict[str, dict[str, dict[str, object]]] = {}
    for rule in RULES:
        table[rule] = {}
        for scope, scope_rows in scopes:
            n = len(scope_rows)
            tool_total = 0.0
            em_total = 0.0
            for row in scope_rows:
                tool_acc, em = score_under_rule(rule, row.expected, row.predicted, defaults_by_tool)
                tool_total += tool_acc
                em_total += em
            table[rule][scope] = {
                "n": n,
                "tool_accuracy": (tool_total / n) if n else 0.0,
                "exact_match": (em_total / n) if n else 0.0,
            }
    return table


def build_per_row_entries(
    source: str,
    arm: str,
    rows: Sequence[LoadedRow],
    defaults_by_tool: Mapping[str, Mapping[str, object]],
) -> list[dict[str, object]]:
    """One row per sample: v1 identity, primary category (``EXACT_MATCH`` for
    a v1-exact row), key/tool-name facts (names only, never argument
    values), and the V2e counterfactual score."""

    entries: list[dict[str, object]] = []
    for row in rows:
        item = score_item(row.expected, row.predicted)
        if item.exact_match == 1.0:
            category = "EXACT_MATCH"
            keys_extra: tuple[str, ...] = ()
            keys_missing: tuple[str, ...] = ()
            tool_names = tuple(sorted({c.name for c in row.expected} | {c.name for c in row.predicted}))
        else:
            classification = classify_row(row.expected, row.predicted, row.parsed, defaults_by_tool)
            category = classification.category
            keys_extra = classification.keys_extra
            keys_missing = classification.keys_missing
            tool_names = classification.tool_names
        v2e_tool_acc, v2e_em = score_under_rule("V2e", row.expected, row.predicted, defaults_by_tool)
        entries.append(
            {
                "source": source,
                "arm": arm,
                "sample_id": row.sample_id,
                "tier": row.tier,
                "category": category,
                "n_gold_calls": len(row.expected),
                "n_pred_calls": len(row.predicted),
                "keys_extra": list(keys_extra),
                "keys_missing": list(keys_missing),
                "tool_names": list(tool_names),
                "v1_tool_accuracy": item.tool_accuracy,
                "v1_exact_match": item.exact_match,
                "v2e_tool_accuracy": v2e_tool_acc,
                "v2e_exact_match": v2e_em,
            }
        )
    return entries


def paired_counts(
    baseline_rows_by_id: Mapping[str, LoadedRow],
    treatment_rows_by_id: Mapping[str, LoadedRow],
    rule: str,
    defaults_by_tool: Mapping[str, Mapping[str, object]],
) -> dict[str, int]:
    """Paired exact-match saves/harms/ties (treatment vs. baseline) under one rule."""

    common = sorted(set(baseline_rows_by_id) & set(treatment_rows_by_id))
    saves = harms = ties = 0
    for sample_id in common:
        _, baseline_em = score_under_rule(
            rule,
            baseline_rows_by_id[sample_id].expected,
            baseline_rows_by_id[sample_id].predicted,
            defaults_by_tool,
        )
        _, treatment_em = score_under_rule(
            rule,
            treatment_rows_by_id[sample_id].expected,
            treatment_rows_by_id[sample_id].predicted,
            defaults_by_tool,
        )
        if baseline_em == 0.0 and treatment_em == 1.0:
            saves += 1
        elif baseline_em == 1.0 and treatment_em == 0.0:
            harms += 1
        else:
            ties += 1
    return {"n": len(common), "saves": saves, "harms": harms, "ties": ties}


# ---------------------------------------------------------------------------
# Step 4 -- top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmInput:
    arm: str
    outputs_path: Path
    text_field: str
    target_overall: Mapping[str, float] | None = None
    target_per_tier: Mapping[str, Mapping[str, float]] | None = None


@dataclass(frozen=True)
class SourceInput:
    source: str
    arms: tuple[ArmInput, ...]
    baseline_arm: str | None = None


def run_study(
    *,
    sources: Sequence[SourceInput],
    gold_by_sample_id: Mapping[str, Sequence[ToolCall]],
    registry_rows: Sequence[Mapping[str, str]],
) -> dict[str, object]:
    """Pure orchestration entry point (all I/O confined to reading the
    caller-named ``outputs_path`` files): Step 1 identity check, Step 2
    taxonomy, Step 3 rule table, and the September paired-conclusion check,
    for every arm of every named source. An arm whose outputs file cannot
    be read is SKIPPED (never crashes the whole study) and recorded under
    ``residuals``."""

    defaults_by_tool = build_registry_defaults(registry_rows)
    per_row_entries: list[dict[str, object]] = []
    sources_out: dict[str, object] = {}
    residuals: list[str] = []

    for source_input in sources:
        arm_rows: dict[str, list[LoadedRow]] = {}
        arms_out: dict[str, object] = {}
        for arm_input in source_input.arms:
            try:
                rows = load_outputs_rows(
                    arm_input.outputs_path, gold_by_sample_id, text_field=arm_input.text_field
                )
            except ScorerV2StudyError as error:
                residuals.append(f"{source_input.source}/{arm_input.arm}: skipped -- {error}")
                arms_out[arm_input.arm] = {"skipped": True, "reason": str(error)}
                continue
            arm_rows[arm_input.arm] = rows
            per_row_entries.extend(
                build_per_row_entries(source_input.source, arm_input.arm, rows, defaults_by_tool)
            )
            arms_out[arm_input.arm] = {
                "n_rows": len(rows),
                "identity_check": identity_check(
                    rows, arm_input.target_overall, arm_input.target_per_tier
                ),
                "taxonomy": taxonomy_counts(rows, defaults_by_tool),
                "rule_table": rule_table(rows, defaults_by_tool),
            }

        paired_out: dict[str, object] = {}
        baseline_arm = source_input.baseline_arm
        if baseline_arm is not None and baseline_arm in arm_rows:
            baseline_by_id = {row.sample_id: row for row in arm_rows[baseline_arm]}
            for arm_input in source_input.arms:
                if arm_input.arm == baseline_arm or arm_input.arm not in arm_rows:
                    continue
                treatment_by_id = {row.sample_id: row for row in arm_rows[arm_input.arm]}
                paired_out[arm_input.arm] = {
                    "V1": paired_counts(baseline_by_id, treatment_by_id, "V1", defaults_by_tool),
                    "V2e": paired_counts(baseline_by_id, treatment_by_id, "V2e", defaults_by_tool),
                }

        sources_out[source_input.source] = {
            "baseline_arm": baseline_arm,
            "arms": arms_out,
            "paired_vs_baseline": paired_out,
        }

    return {
        "schema": RESULT_SCHEMA,
        "sources": sources_out,
        "residuals": residuals,
        "per_row": per_row_entries,
    }


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Mapping[str, object]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ScorerV2StudyError(f"cannot read {path}: {error}") from error


def _arm_target(arms: Mapping[str, object], arm: str) -> dict[str, float]:
    payload = arms.get(arm)
    if not isinstance(payload, Mapping):
        raise ScorerV2StudyError(f"sealed summary lacks an arms[{arm!r}] entry")
    return {"tool_accuracy": float(payload["tool_accuracy"]), "exact_match": float(payload["exact_match"])}


def _build_sources(repo_root: Path, root: Path) -> tuple[SourceInput, ...]:
    """The three sealed sources named in the study brief, wired to their
    real (already-located, see the brief's ``find`` instructions) outputs
    paths and to their committed sealed-summary targets."""

    a0_verdict = _load_json(
        repo_root
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-08-18-pa2t-a0-read"
        / "verdict.json"
    )
    a0_overall = a0_verdict["overall"]
    a0_by_tier = a0_verdict["by_tier"]
    a0_source = SourceInput(
        source="a0",
        baseline_arm=None,
        arms=(
            ArmInput(
                arm="zero_supply",
                outputs_path=root
                / "runs"
                / "SAEA-BASE-a2t-a0-400"
                / "attempt-20260818T055500Z-res315"
                / "outputs.jsonl",
                text_field="response_text",
                target_overall={
                    "tool_accuracy": a0_overall["tool_accuracy"],
                    "exact_match": a0_overall["exact_match"],
                },
                target_per_tier={
                    tier: {"tool_accuracy": values["tool_accuracy"], "exact_match": values["exact_match"]}
                    for tier, values in a0_by_tier.items()
                },
            ),
        ),
    )

    semantic_summary = _load_json(
        repo_root
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-03-a2t-semantic-agentloop-104-v1"
        / "postseal-result-summary.json"
    )
    semantic_arms = semantic_summary["arms"]
    semantic_base = (
        root
        / "runs"
        / "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1"
        / "mission-20260903t190000z-semantic104-v1"
        / "zero-contact-recovery-v2"
    )
    semantic_arm_names = (
        "direct_m0",
        "transcript_top16_use",
        "model_query_top16_use",
        "rrf_fused_top16_use",
        "same_stratum_shuffled_fused_use",
    )
    semantic_source = SourceInput(
        source="semantic104",
        baseline_arm="direct_m0",
        arms=tuple(
            ArmInput(
                arm=arm,
                outputs_path=semantic_base / arm / "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1.outputs.jsonl",
                text_field="text",
                target_overall=_arm_target(semantic_arms, arm),
                target_per_tier=None,
            )
            for arm in semantic_arm_names
        ),
    )

    sf_summary = _load_json(
        repo_root
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-03-a2t-select-fill-agentloop-104-v1"
        / "result-summary.json"
    )
    sf_arms = sf_summary["arms"]
    sf_mission = (
        root
        / "runs"
        / "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5"
        / "mission-20260903t204700z-selectfill104-recovery-v5"
    )
    sf_paths = {
        "DIRECT_M0": sf_mission
        / "recovered-direct-m0"
        / "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V2.outputs.jsonl",
        "JOINT_ONE_CALL": sf_mission
        / "zero-contact-seal-recovery-v1"
        / "joint_one_call"
        / "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5.outputs.jsonl",
        "JOINT_DRAFT_REVISE": sf_mission
        / "zero-contact-seal-recovery-v1"
        / "joint_draft_revise"
        / "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5.outputs.jsonl",
        "SELECT_THEN_FILL": sf_mission
        / "zero-contact-seal-recovery-v1"
        / "select_then_fill"
        / "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5.outputs.jsonl",
    }
    sf_source = SourceInput(
        source="selectfill104",
        baseline_arm="DIRECT_M0",
        arms=tuple(
            ArmInput(
                arm=arm,
                outputs_path=path,
                text_field="text",
                target_overall=_arm_target(sf_arms, arm),
                target_per_tier=None,
            )
            for arm, path in sf_paths.items()
        ),
    )

    return (a0_source, semantic_source, sf_source)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    from ..data.audio2tool import load_expected_calls, load_tool_registry
    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT, write_json_artifact

    parser = argparse.ArgumentParser(
        prog="a2t-scorer-v2-study",
        description=(
            "Slice S1 zero-contact re-scoring study: re-score the sealed A0-400, "
            "semantic-AgentLoop-104, and select-fill-AgentLoop-104 outputs under "
            "unchanged v1 semantics plus five candidate v2 rules; write summary.json "
            "and per_row.jsonl. Model-free, read-only; never opens a model session."
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=None, help="TEST-ONLY override")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else repo_root
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-03-a2t-scorer-v2-zero-contact-study"
    )

    summary_path = output_dir / "summary.json"
    if summary_path.exists():
        print(
            f"REFUSED: {summary_path} already exists -- this study refuses to run twice "
            "against the same output dir (one-shot read discipline); choose a fresh "
            "--output-dir if a genuinely new read is intended",
            file=sys.stderr,
        )
        return 1

    lock = load_lock(umbrella_lock_path(repo_root))
    root = data_root()

    try:
        sources = _build_sources(repo_root, root)
        gold_by_sample_id = load_expected_calls(lock, root, repo_root=repo_root)
        registry_rows = load_tool_registry(lock, root)
        report = run_study(
            sources=sources, gold_by_sample_id=gold_by_sample_id, registry_rows=registry_rows
        )
    except ScorerV2StudyError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    per_row_path = output_dir / "per_row.jsonl"
    with per_row_path.open("w", encoding="utf-8", newline="\n") as handle:
        for entry in report["per_row"]:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    summary_payload = {key: value for key, value in report.items() if key != "per_row"}
    summary_payload["per_row_count"] = len(report["per_row"])
    summary_sha = write_json_artifact(summary_path, summary_payload)

    print(f"wrote {summary_path} sha256={summary_sha}")
    print(f"wrote {per_row_path} ({len(report['per_row'])} rows)")
    if report["residuals"]:
        print("residuals:")
        for note in report["residuals"]:
            print(f"  {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
