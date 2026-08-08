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

Aggregation: corpus-level via ``toolcall_scoring.aggregate`` (Tool
Accuracy/Exact Match as item means, Slot-F1 micro), plus a ``per_tier``
breakdown — the P1 pre-registered success criteria (tier rank order, per-tier
|delta| vs the published Qwen-3-Omni-30B rows) are per-tier claims, and the
tier is recoverable from the sample id (``"{tier}:{id:06d}"``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from ..data.audio2tool import load_expected_calls
from ..data.lock import REPO_ROOT
from .toolcall_gold import A2T_GOLD_VERSION
from .toolcall_scoring import (
    A2T_SCORER_VERSION,
    AggregateScore,
    ItemScore,
    aggregate,
    parse_tool_calls_text,
    score_item,
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
        expected = expected_by_id.get(sample_id)
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
    overall["gold_version"] = A2T_GOLD_VERSION
    overall["parse_failures"] = parse_failures
    overall["per_tier"] = {
        tier: _aggregate_view(aggregate(tier_items))
        for tier, tier_items in sorted(items_by_tier.items())
    }
    return {"per_sample": per_sample, "aggregate": overall}
