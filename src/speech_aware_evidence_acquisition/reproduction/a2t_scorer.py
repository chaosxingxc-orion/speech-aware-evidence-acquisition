"""Audio2Tool tool-call scorer (P1 scaffold): outputs JSONL -> a2t-scorer-v1 results.

The registered ``a2t-toolcall`` scorer function (``core.scorers`` binds it
into ``core.base.SCORERS``) with the uniform ``scorer(outputs_path, lock,
root)`` signature ``core.scorers.score_bundle`` calls every scorer with.
Strictly post-hoc: it runs over recorded outputs, never inside a request
loop, and it is the only place Audio2Tool gold is consumed
(``data.audio2tool.load_expected_calls`` — scorer-side by construction, D2).

Deliberately OUTSIDE the E0 D3 frozen scoring package: metric semantics live
in ``reproduction.toolcall_scoring`` (a2t-scorer-v1) and gold interpretation
in ``reproduction.toolcall_gold`` (a2t-gold-v1); both version constants are
echoed into the aggregate so a ledger row pins them.

A THIRD entry point, :func:`score_audio2tool_outputs_official`, runs the
pinned Audio2Tool release's OWN parse and metric code
(``reproduction.audio2tool_official``, commit ``b9d5383c``) over the same
sealed outputs, and registers as ``a2t-toolcall-official``. It is the
paper-facing scorer for the Audio2Tool carrier; v1 and v2 are reported
beside it and are never replaced.

Aggregation: corpus-level via ``toolcall_scoring.aggregate`` (Tool
Accuracy/Exact Match as item means, Slot-F1 micro), plus a ``per_tier``
breakdown — the P1 pre-registered success criteria (tier rank order, per-tier
|delta| vs the published Qwen-3-Omni-30B rows) are per-tier claims, and the
tier is recoverable from the sample id (``"{tier}:{id:06d}"``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Mapping, Sequence

from ..data.audio2tool import load_expected_calls, load_official_gold, load_tool_registry
from ..data.lock import REPO_ROOT
from ..data.variant_ids import published_sample_key
from .audio2tool_official import (
    AUDIO2TOOL_OFFICIAL_COMMIT,
    AUDIO2TOOL_OFFICIAL_METRICS_BLOB_SHA1,
    AUDIO2TOOL_OFFICIAL_SCORER_VERSION,
)
from .audio2tool_official import metrics as official_metrics
from .audio2tool_official.parse import parse_tool_call as official_parse_tool_call
from .toolcall_gold import A2T_GOLD_VERSION
from .toolcall_scoring import (
    A2T_PARSE_VERSION,
    A2T_SCORER_VERSION,
    AggregateScore,
    ItemScore,
    aggregate,
    parse_tool_calls_text,
    score_item,
)
#: VARIANT-ID RAIL (2026-09-07 cross-carrier silence-tail preregistration
#: section 6.2). A derived-media population carries ``<published id>@<variant>``
#: ids (``data.variant_ids``); all three scorer entry points below recover the
#: published key before the gold lookup and keep the RAW id in every per-sample
#: row and every refusal message, so a receipt still records exactly which media
#: was flown. Inert for unsuffixed ids by construction, and never a skeleton key:
#: a foreign published key refuses exactly as it did before. The tier is read
#: from the id's ``<tier>:<number>`` prefix, which the suffix never touches.

from .toolcall_scoring_v2 import (
    A2T_SCORER_V2_VERSION,
    AggregateScoreV2,
    ItemScoreV2,
    RegistryDriftError,
    aggregate_v2,
    build_registry_defaults,
    score_item_v2,
)


class ToolCallScoringError(RuntimeError):
    """Outputs are malformed or cannot be paired with frozen-receipt gold."""


def _aggregate_view(score: AggregateScore) -> dict[str, object]:
    return {
        "samples": score.n_items,
        "tool_accuracy": score.tool_accuracy,
        "exact_match": score.exact_match,
        "slot_precision": score.slot_precision,
        "slot_recall": score.slot_recall,
        "slot_f1": score.slot_f1,
        "slot_true_positives": score.slot_true_positives,
        "slot_expected_total": score.slot_expected_total,
        "slot_predicted_total": score.slot_predicted_total,
    }


def _aggregate_view_v2(score: AggregateScoreV2) -> dict[str, object]:
    return {
        "samples": score.n_items,
        "tool_accuracy": score.tool_accuracy_ordered,
        "tool_accuracy_multiset": score.tool_accuracy_multiset,
        "exact_match": score.exact_match,
        "slot_precision": score.slot_precision,
        "slot_recall": score.slot_recall,
        "slot_f1": score.slot_f1,
        "slot_f1_raw": score.slot_f1_raw,
        "slot_true_positives": score.slot_true_positives,
        "slot_expected_total": score.slot_expected_total,
        "slot_predicted_total": score.slot_predicted_total,
        "extra_keys_stripped": score.extra_keys_stripped,
        "coerced_values": score.coerced_values,
    }


def score_audio2tool_outputs(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Score one run's outputs JSONL against the frozen-receipt gold.

    ``repo_root`` defaults to this study checkout (where the committed probe
    receipt lives) and exists as a keyword only so tests can bind a synthetic
    repo; ``score_bundle`` always calls through the three-positional-argument
    registry shape and therefore always gets the real default.
    """

    resolved_repo_root = Path(REPO_ROOT if repo_root is None else repo_root)
    try:
        text = Path(outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ToolCallScoringError(f"cannot read outputs {outputs_path}: {error}") from error
    # Same record-separator discipline as core.scorers.score_asr_outputs:
    # split on "\n" only, so raw U+2028/U+2029 inside JSON strings never cut
    # a row in two.
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise ToolCallScoringError(f"outputs file {outputs_path} is empty")

    expected_by_id = load_expected_calls(lock, root, repo_root=resolved_repo_root)

    per_sample: list[dict[str, object]] = []
    items: list[ItemScore] = []
    items_by_tier: dict[str, list[ItemScore]] = {}
    seen: set[str] = set()
    parse_failures = 0
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ToolCallScoringError(f"outputs line {number} malformed: {error}") from error
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ToolCallScoringError(f"outputs line {number} lacks a sample_id")
        if sample_id in seen:
            raise ToolCallScoringError(f"outputs carry a duplicate sample_id {sample_id!r}")
        seen.add(sample_id)
        expected = expected_by_id.get(published_sample_key(sample_id))
        if expected is None:
            raise ToolCallScoringError(
                f"outputs sample_id {sample_id!r} is not in the frozen audio2tool "
                "probe receipt; refusing to score outside the pre-registered sample"
            )
        model_text = row.get("text")
        if not isinstance(model_text, str):
            raise ToolCallScoringError(f"outputs line {number} lacks a text field")
        predicted, parsed = parse_tool_calls_text(model_text)
        if not parsed:
            parse_failures += 1
        item = score_item(expected, predicted)
        tier = sample_id.rsplit(":", 1)[0]
        items.append(item)
        items_by_tier.setdefault(tier, []).append(item)
        per_sample.append(
            {
                "sample_id": sample_id,
                "tier": tier,
                "tool_accuracy": item.tool_accuracy,
                "exact_match": item.exact_match,
                "slot_precision": item.slot_precision,
                "slot_recall": item.slot_recall,
                "slot_f1": item.slot_f1,
                "parsed": parsed,
            }
        )

    overall = _aggregate_view(aggregate(items))
    overall["scorer_version"] = A2T_SCORER_VERSION
    overall["parse_version"] = A2T_PARSE_VERSION
    overall["gold_version"] = A2T_GOLD_VERSION
    overall["parse_failures"] = parse_failures
    overall["per_tier"] = {
        tier: _aggregate_view(aggregate(tier_items))
        for tier, tier_items in sorted(items_by_tier.items())
    }
    return {"per_sample": per_sample, "aggregate": overall}


# ---------------------------------------------------------------------------
# v2 entry point (slice C3c): the slice-S1 zero-contact re-scoring study's
# adopted V2e semantics (docs/readiness/2026-09-03-a2t-scorer-v2-zero-
# contact-study.md), reached through ``reproduction.toolcall_scoring_v2``
# (``a2t-scorer-v2``). v1 above is UNCHANGED -- this function reads the same
# outputs.jsonl and the same frozen-receipt gold, and reports v2 numbers
# side by side, never a replacement.
# ---------------------------------------------------------------------------


def score_audio2tool_outputs_v2(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Score one run's outputs JSONL against the frozen-receipt gold under
    ``a2t-scorer-v2`` semantics -- same JSONL reading, same refusals, and
    the same ``repo_root``/frozen-receipt gold contract as
    :func:`score_audio2tool_outputs` (v1) above; only the scoring machinery
    differs (``reproduction.toolcall_scoring_v2.score_item_v2``/
    ``aggregate_v2``). Registry defaults (``tools_registry.csv``, the same
    carrier ``load_tool_registry`` already exposes) are loaded ONCE, before
    the per-row loop.

    A registry-drift refusal (a gold tool name absent from the registry
    defaults -- ``toolcall_scoring_v2.RegistryDriftError``) is re-raised as
    :class:`ToolCallScoringError`, the same exception every other refusal in
    this module already uses, so a caller of either scorer function handles
    exactly one exception type.
    """

    resolved_repo_root = Path(REPO_ROOT if repo_root is None else repo_root)
    try:
        text = Path(outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ToolCallScoringError(f"cannot read outputs {outputs_path}: {error}") from error
    # Same record-separator discipline as core.scorers.score_asr_outputs:
    # split on "\n" only, so raw U+2028/U+2029 inside JSON strings never cut
    # a row in two.
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise ToolCallScoringError(f"outputs file {outputs_path} is empty")

    expected_by_id = load_expected_calls(lock, root, repo_root=resolved_repo_root)
    registry_defaults = build_registry_defaults(load_tool_registry(lock, root))

    per_sample: list[dict[str, object]] = []
    items: list[ItemScoreV2] = []
    items_by_tier: dict[str, list[ItemScoreV2]] = {}
    seen: set[str] = set()
    parse_failures = 0
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ToolCallScoringError(f"outputs line {number} malformed: {error}") from error
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ToolCallScoringError(f"outputs line {number} lacks a sample_id")
        if sample_id in seen:
            raise ToolCallScoringError(f"outputs carry a duplicate sample_id {sample_id!r}")
        seen.add(sample_id)
        expected = expected_by_id.get(published_sample_key(sample_id))
        if expected is None:
            raise ToolCallScoringError(
                f"outputs sample_id {sample_id!r} is not in the frozen audio2tool "
                "probe receipt; refusing to score outside the pre-registered sample"
            )
        model_text = row.get("text")
        if not isinstance(model_text, str):
            raise ToolCallScoringError(f"outputs line {number} lacks a text field")
        predicted, parsed = parse_tool_calls_text(model_text)
        if not parsed:
            parse_failures += 1
        try:
            item = score_item_v2(expected, predicted, registry_defaults=registry_defaults)
        except RegistryDriftError as error:
            raise ToolCallScoringError(
                f"outputs line {number} ({sample_id!r}): {error}"
            ) from error
        tier = sample_id.rsplit(":", 1)[0]
        items.append(item)
        items_by_tier.setdefault(tier, []).append(item)
        per_sample.append(
            {
                "sample_id": sample_id,
                "tier": tier,
                "tool_accuracy": item.tool_accuracy_ordered,
                "tool_accuracy_multiset": item.tool_accuracy_multiset,
                "exact_match": item.exact_match,
                "slot_precision": item.slot_precision,
                "slot_recall": item.slot_recall,
                "slot_f1": item.slot_f1,
                "slot_f1_raw": item.slot_f1_raw,
                "parsed": parsed,
                "extra_keys_stripped": item.extra_keys_stripped,
                "coerced_values": item.coerced_values,
            }
        )

    overall = _aggregate_view_v2(aggregate_v2(items))
    overall["scorer_version"] = A2T_SCORER_V2_VERSION
    overall["parse_version"] = A2T_PARSE_VERSION
    overall["gold_version"] = A2T_GOLD_VERSION
    overall["parse_failures"] = parse_failures
    overall["per_tier"] = {
        tier: _aggregate_view_v2(aggregate_v2(tier_items))
        for tier, tier_items in sorted(items_by_tier.items())
    }
    return {"per_sample": per_sample, "aggregate": overall}


# ---------------------------------------------------------------------------
# Audio2Tool tool-call scorer, OFFICIAL (2026-09-04): the pinned Audio2Tool
# release's own metric functions, run over this repository's sealed outputs.
#
# v1 (``a2t-toolcall``) and v2 (``a2t-toolcall-v2``) above are UNCHANGED and
# stay registered. This third entry point exists because the owner's standard-
# scoring rule requires the paper-facing number to be the dataset's standard
# scorer, and that scorer was published on 2026-09-03: nothing below
# reimplements a metric. Parsing comes from
# ``reproduction.audio2tool_official.parse`` (``BaseAudioModel.
# parse_tool_call``) and every metric from
# ``reproduction.audio2tool_official.metrics`` (byte-for-byte
# ``audio_benchmark/evaluation/metrics.py``); this function only reads the
# JSONL, resolves gold, and aggregates the way
# ``audio_benchmark/evaluation/evaluator.py`` aggregates.
#
# Gold: ``data.audio2tool.load_official_gold`` -- the release's OWN
# ``QuerySample`` shape (primary ``tool_name`` + verbatim
# ``extracted_params`` + ``additional_tool_calls``), NOT ``a2t-gold-v1``.
# See that function's docstring for why the two differ and why using
# ``a2t-gold-v1`` here would be scoring a different gold.
# ---------------------------------------------------------------------------

_OFFICIAL_CALL_PATTERN = re.compile(r"(\w+)\s*\((.*?)\)")


def _official_param_counts(
    predicted: Mapping[str, object], gold: Mapping[str, object]
) -> tuple[int, int, int]:
    """``(correct, predicted, gold)`` key counts under the official
    normalization -- the raw ingredients of a MICRO average.

    The published evaluator averages per-sample precision/recall/F1 over
    samples (``evaluator._compute_metrics``: ``np.mean`` of each row's
    ``param_metrics``), which is a MACRO average even though the paper's
    prose says "micro". Both are reported by the scorer below; the macro
    figure is the published code's own, and these counts feed the micro one
    beside it. Normalization is the official ``normalize_parameters``, so the
    two averages differ only in how they are pooled, never in what counts as
    correct.
    """

    pred_norm = official_metrics.normalize_parameters(dict(predicted))
    gold_norm = official_metrics.normalize_parameters(dict(gold))
    correct = sum(1 for key, value in gold_norm.items() if key in pred_norm and pred_norm[key] == value)
    return correct, len(pred_norm), len(gold_norm)


def _official_aggregate(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Aggregate a set of per-sample rows the way ``evaluator.
    _compute_metrics`` does (plain means over samples), plus the micro
    parameter figures and the parse/diagnostic counters this repository needs
    to read a replication."""

    total = len(rows)
    if total == 0:
        raise ToolCallScoringError("cannot aggregate an empty set of official rows")

    def mean(field: str) -> float:
        return sum(float(row[field]) for row in rows) / total

    correct = sum(int(row["param_correct_keys"]) for row in rows)
    predicted_keys = sum(int(row["param_predicted_keys"]) for row in rows)
    gold_keys = sum(int(row["param_gold_keys"]) for row in rows)
    micro_precision = correct / predicted_keys if predicted_keys else 0.0
    micro_recall = correct / gold_keys if gold_keys else 0.0
    micro_f1 = (
        2 * micro_precision * micro_recall / (micro_precision + micro_recall)
        if (micro_precision + micro_recall) > 0
        else 0.0
    )

    multi_rows = [row for row in rows if row["is_multi_tool"]]
    view: dict[str, object] = {
        "samples": total,
        "tool_accuracy": mean("tool_correct"),
        "exact_match": mean("exact_match"),
        "param_exact_match": mean("param_exact_match"),
        "param_precision": mean("param_precision"),
        "param_recall": mean("param_recall"),
        "param_f1": mean("param_f1"),
        "param_precision_micro": micro_precision,
        "param_recall_micro": micro_recall,
        "param_f1_micro": micro_f1,
        "param_correct_keys": correct,
        "param_predicted_keys": predicted_keys,
        "param_gold_keys": gold_keys,
        "parse_rate": mean("parsed"),
        "parse_failures": sum(1 for row in rows if not row["parsed"]),
        "rows_with_multiple_call_matches": sum(
            1 for row in rows if int(row["official_call_matches"]) > 1
        ),
        "multi_tool_samples": len(multi_rows),
    }
    if multi_rows:
        count = len(multi_rows)
        view["multi_tool_all_match"] = (
            sum(float(row["multi_tool_all_match"]) for row in multi_rows) / count
        )
        view["multi_tool_recall"] = (
            sum(float(row["multi_tool_recall"]) for row in multi_rows) / count
        )
        view["multi_tool_precision"] = (
            sum(float(row["multi_tool_precision"]) for row in multi_rows) / count
        )
        view["multi_tool_f1"] = (
            sum(float(row["multi_tool_f1"]) for row in multi_rows) / count
        )
    else:
        view["multi_tool_all_match"] = None
        view["multi_tool_recall"] = None
        view["multi_tool_precision"] = None
        view["multi_tool_f1"] = None
    return view


def score_audio2tool_outputs_official(
    outputs_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path | None = None,
) -> dict[str, object]:
    """Score one run's outputs JSONL with the PINNED Audio2Tool release's own
    parse and metric functions.

    Same uniform ``scorer(outputs_path, lock, root)`` signature, same JSONL
    reading and the same refusals as :func:`score_audio2tool_outputs` (v1)
    and :func:`score_audio2tool_outputs_v2` above; ``repo_root`` is a keyword
    only so tests can bind a synthetic repo.

    Per row, mirroring ``evaluator._evaluate_sample``:

    * ``parse_tool_call(text)`` -> predicted primary tool name and
      parameters. The upstream HF adapter never populates ``all_tool_calls``,
      so a multi-call response is judged on its FIRST parsed call -- that is
      a property of the published protocol, faithfully reproduced, not a
      simplification made here.
    * ``compute_tool_accuracy(predicted_tool, gold.tool_name)``.
    * ``compute_parameter_accuracy(predicted_params, gold.extracted_params)``.
    * ``exact_match = tool_correct and param_metrics["exact_match"]``.
    * ``compute_multi_tool_metrics`` only when gold carries
      ``additional_tool_calls`` (upstream also triggers it when the model
      returns more than one tool, which the HF path cannot do).

    ``official_call_matches`` is a DIAGNOSTIC, not an official metric: the
    number of call-shaped spans the official regex finds in the raw output,
    which is how a response that named several tools while being scored on
    its first one becomes visible in the verdict.
    """

    resolved_repo_root = Path(REPO_ROOT if repo_root is None else repo_root)
    try:
        text = Path(outputs_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ToolCallScoringError(f"cannot read outputs {outputs_path}: {error}") from error
    # Same record-separator discipline as core.scorers.score_asr_outputs:
    # split on "\n" only, so raw U+2028/U+2029 inside JSON strings never cut
    # a row in two.
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines:
        raise ToolCallScoringError(f"outputs file {outputs_path} is empty")

    gold_by_id = load_official_gold(lock, root, repo_root=resolved_repo_root)

    per_sample: list[dict[str, object]] = []
    rows_by_tier: dict[str, list[dict[str, object]]] = {}
    seen: set[str] = set()
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ToolCallScoringError(f"outputs line {number} malformed: {error}") from error
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ToolCallScoringError(f"outputs line {number} lacks a sample_id")
        if sample_id in seen:
            raise ToolCallScoringError(f"outputs carry a duplicate sample_id {sample_id!r}")
        seen.add(sample_id)
        gold = gold_by_id.get(published_sample_key(sample_id))
        if gold is None:
            raise ToolCallScoringError(
                f"outputs sample_id {sample_id!r} is not in the frozen audio2tool "
                "probe receipt; refusing to score outside the pre-registered sample"
            )
        model_text = row.get("text")
        if not isinstance(model_text, str):
            raise ToolCallScoringError(f"outputs line {number} lacks a text field")

        predicted_tool, predicted_call, predicted_params = official_parse_tool_call(model_text)
        tool_correct = official_metrics.compute_tool_accuracy(predicted_tool, gold.tool_name)
        param_metrics = official_metrics.compute_parameter_accuracy(
            predicted_params, dict(gold.extracted_params)
        )
        correct_keys, predicted_keys, gold_keys = _official_param_counts(
            predicted_params, gold.extracted_params
        )
        all_expected = [gold.tool_name, *gold.additional_tool_calls]
        # ModelOutput.all_tool_names on the HF path: [tool_name] when a name
        # was parsed, [] otherwise (its all_tool_calls is never populated).
        all_predicted = [predicted_tool] if predicted_tool else []
        is_multi_tool = bool(gold.additional_tool_calls)
        multi_metrics = (
            official_metrics.compute_multi_tool_metrics(all_predicted, all_expected)
            if (is_multi_tool or len(all_predicted) > 1)
            else {}
        )
        tier = sample_id.rsplit(":", 1)[0]
        entry = {
            "sample_id": sample_id,
            "tier": tier,
            "predicted_tool": predicted_tool,
            "predicted_tool_call": predicted_call,
            "gold_tool": gold.tool_name,
            "tool_correct": bool(tool_correct),
            "exact_match": bool(tool_correct and param_metrics["exact_match"]),
            "param_exact_match": bool(param_metrics["exact_match"]),
            "param_precision": float(param_metrics["precision"]),
            "param_recall": float(param_metrics["recall"]),
            "param_f1": float(param_metrics["f1"]),
            "param_correct_keys": correct_keys,
            "param_predicted_keys": predicted_keys,
            "param_gold_keys": gold_keys,
            "parsed": bool(predicted_tool),
            "official_call_matches": len(_OFFICIAL_CALL_PATTERN.findall(model_text)),
            "is_multi_tool": is_multi_tool,
            "num_expected_tools": len(all_expected),
            "multi_tool_all_match": bool(multi_metrics.get("all_tools_match", False)),
            "multi_tool_recall": float(multi_metrics.get("tool_recall", 0.0)),
            "multi_tool_precision": float(multi_metrics.get("tool_precision", 0.0)),
            "multi_tool_f1": float(multi_metrics.get("tool_f1", 0.0)),
        }
        per_sample.append(entry)
        rows_by_tier.setdefault(tier, []).append(entry)

    overall = _official_aggregate(per_sample)
    overall["scorer_version"] = AUDIO2TOOL_OFFICIAL_SCORER_VERSION
    overall["gold_version"] = "a2t-gold-official-release-loader"
    overall["official_commit"] = AUDIO2TOOL_OFFICIAL_COMMIT
    overall["official_metrics_blob_sha1"] = AUDIO2TOOL_OFFICIAL_METRICS_BLOB_SHA1
    overall["per_tier"] = {
        tier: _official_aggregate(tier_rows)
        for tier, tier_rows in sorted(rows_by_tier.items())
    }
    return {"per_sample": per_sample, "aggregate": overall}
