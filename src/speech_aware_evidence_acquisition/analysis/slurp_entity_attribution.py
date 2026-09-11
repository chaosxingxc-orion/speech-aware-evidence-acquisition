"""Model-free SLURP entity loss attribution using official distance matching."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from ..reproduction.slurp_scoring import (
    _char_distance,
    _lowest_distance,
    _word_distance,
)
from ..reproduction.slurp_value_projection import normalize_filler


def _match_block(gold, predicted, distance_fn):
    """Match one official distance block, retaining consumed pairs."""
    remaining_types = [entity.type for entity in gold]
    remaining_fillers = [entity.filler for entity in gold]
    matched, unmatched_predictions = [], []
    tp = fp = fn = 0.0
    for entity in predicted:
        if entity.type in remaining_types:
            index, distance = _lowest_distance(
                entity, remaining_types, remaining_fillers, distance_fn
            )
            tp += 1.0
            fp += distance
            fn += distance
            matched.append(
                (entity.type, remaining_fillers[index], entity.filler, float(distance))
            )
            del remaining_types[index]
            del remaining_fillers[index]
        else:
            unmatched_predictions.append((entity.type, entity.filler))
            fp += 1.0
    leftover = list(zip(remaining_types, remaining_fillers))
    fn += float(len(remaining_types))
    return matched, unmatched_predictions, leftover, (tp, fp, fn)


def attribute_row(gold, predicted):
    """Partition official word/character FP+FN mass into four loss buckets.

    Surface loss follows the scorer's separate greedy same-type matches.
    A type swap pairs remaining entities with equal normalized fillers and
    different types; it is a diagnostic matching heuristic, not a causal
    explanation. Remaining predictions and references are spurious and missing.
    """
    word = _match_block(gold, predicted, _word_distance)
    char = _match_block(gold, predicted, _char_distance)
    if len(word[1]) != len(char[1]) or len(word[2]) != len(char[2]):
        raise ValueError("the word and char blocks disagree on how many spans matched")
    surface_mass = 2.0 * sum(pair[3] for pair in word[0]) + 2.0 * sum(
        pair[3] for pair in char[0]
    )
    remaining_gold = list(char[2])
    remaining_predictions = []
    type_swaps = []
    for pred_type, pred_filler in char[1]:
        normalized = normalize_filler(pred_filler)
        hit = None
        for index, (gold_type, gold_filler) in enumerate(remaining_gold):
            if gold_type != pred_type and normalize_filler(gold_filler) == normalized:
                hit = index
                break
        if hit is None:
            remaining_predictions.append((pred_type, pred_filler))
            continue
        gold_type, gold_filler = remaining_gold.pop(hit)
        type_swaps.append(
            {
                "gold_type": gold_type,
                "gold_filler": gold_filler,
                "predicted_type": pred_type,
                "predicted_filler": pred_filler,
            }
        )
    surface_pairs = [
        {
            "type": w[0],
            "gold_filler": w[1],
            "gold_filler_char_block": c[1],
            "predicted_filler": w[2],
            "word_distance": w[3],
            "char_distance": c[3],
        }
        for w, c in zip(word[0], char[0])
    ]
    total_mass = sum(word[3][1:]) + sum(char[3][1:])
    accounted = (
        surface_mass
        + 4.0 * len(type_swaps)
        + 2.0 * len(remaining_predictions)
        + 2.0 * len(remaining_gold)
    )
    if abs(total_mass - accounted) > 1e-9:
        raise ValueError(
            f"the loss attribution does not close: mass {total_mass} against {accounted}"
        )
    return {
        "tp": word[3][0] + char[3][0],
        "mass": total_mass,
        "surface_mass": surface_mass,
        "surface_pairs": surface_pairs,
        "type_swaps": type_swaps,
        "spurious": remaining_predictions,
        "missing": remaining_gold,
        "predicted_count": len(predicted),
        "gold_count": len(gold),
    }


def _nonnegative_finite(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError(f"{name} must be a finite nonnegative number")
    return float(value)


def attribute_parsed_rows(
    gold_by_id: Mapping[str, Sequence],
    predicted_by_id: Mapping[str, Sequence],
    official_rows: Mapping[str, Mapping[str, object]],
    *,
    tolerance: float = 1e-6,
):
    """Reconcile all six saved official ingredients before reporting attribution.

    Require exactly the same nonempty roster across inputs. This function
    performs deterministic arithmetic only; it never invokes an official scorer
    or reads annotations, predictions, or model services itself.
    """
    tolerance = _nonnegative_finite(tolerance, "tolerance")
    ids = set(gold_by_id)
    if ids != set(predicted_by_id) or ids != set(official_rows) or not ids:
        raise ValueError("gold, predicted, and official row IDs must match exactly")
    rows = {}
    totals = {"tp": 0.0, "fp_fn": 0.0}
    mass = {"surface": 0.0, "type_swap": 0.0, "spurious": 0.0, "missing": 0.0}
    fields = (
        "slu_f1_word_tp",
        "slu_f1_word_fp",
        "slu_f1_word_fn",
        "slu_f1_char_tp",
        "slu_f1_char_fp",
        "slu_f1_char_fn",
    )
    for sample_id in sorted(ids):
        gold = gold_by_id[sample_id]
        predicted = predicted_by_id[sample_id]
        official = official_rows[sample_id]
        if any(field not in official for field in fields):
            raise ValueError(
                f"official row {sample_id!r} lacks required SLU ingredients"
            )
        reconstructed = (
            *_match_block(gold, predicted, _word_distance)[3],
            *_match_block(gold, predicted, _char_distance)[3],
        )
        for field, expected in zip(fields, reconstructed):
            actual = _nonnegative_finite(
                official[field], f"official row {sample_id!r} {field}"
            )
            if abs(actual - expected) > tolerance:
                raise ValueError(
                    f"official row {sample_id!r} {field} does not match "
                    "reconstructed attribution"
                )
        row = attribute_row(gold, predicted)
        rows[sample_id] = row
        totals["tp"] += row["tp"]
        totals["fp_fn"] += row["mass"]
        mass["surface"] += row["surface_mass"]
        mass["type_swap"] += 4.0 * len(row["type_swaps"])
        mass["spurious"] += 2.0 * len(row["spurious"])
        mass["missing"] += 2.0 * len(row["missing"])
    return {"rows": rows, "totals": totals, "mass": mass}


__all__ = ["attribute_row", "attribute_parsed_rows"]
