"""Scoring phase: outputs JSONL + reference layers -> frozen-scoring results.

This is the ONLY module allowed to import data.references (AST contract
test). It runs strictly after the runtime phase, on recorded outputs — never
inside a request loop.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from ..data.references import reference_tokens
from ..scoring import align, tokens_v1
from .base import SCORERS


class ScoringPhaseError(RuntimeError):
    """Outputs are malformed or reference/hypothesis pairing is impossible."""


def score_asr_outputs(
    outputs_path: Path, lock: Mapping[str, object], root: Path
) -> dict[str, object]:
    try:
        lines = Path(outputs_path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ScoringPhaseError(f"cannot read outputs {outputs_path}: {error}") from error
    if not lines:
        raise ScoringPhaseError(f"outputs file {outputs_path} is empty")
    per_sample: list[dict[str, object]] = []
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ScoringPhaseError(f"outputs line {number} malformed: {error}") from error
        ref = tokens_v1(
            " ".join(reference_tokens(lock, root, row["carrier_lock_key"], row["sample_id"]))
        )
        result = align(ref, tokens_v1(row["text"]))
        per_sample.append(
            {
                "sample_id": row["sample_id"],
                "wer": result.wer,
                "hits": result.hits,
                "substitutions": result.substitutions,
                "deletions": result.deletions,
                "insertions": result.insertions,
                "ref_hit_mask": list(result.ref_hit_mask),
            }
        )
    mean_wer = sum(entry["wer"] for entry in per_sample) / len(per_sample)
    return {
        "per_sample": per_sample,
        "aggregate": {"mean_wer": mean_wer, "samples": len(per_sample)},
    }


def transition_report(
    baseline: Mapping[str, object], treatment: Mapping[str, object]
) -> dict[str, int]:
    base_by_id = {entry["sample_id"]: entry for entry in baseline["per_sample"]}
    treat_by_id = {entry["sample_id"]: entry for entry in treatment["per_sample"]}
    if set(base_by_id) != set(treat_by_id):
        raise ScoringPhaseError("baseline/treatment sample sets differ")
    totals = {
        "correct_to_correct": 0,
        "correct_to_wrong": 0,
        "wrong_to_correct": 0,
        "wrong_to_wrong": 0,
    }
    for sample_id, base in base_by_id.items():
        base_mask = base["ref_hit_mask"]
        treat_mask = treat_by_id[sample_id]["ref_hit_mask"]
        if len(base_mask) != len(treat_mask):
            raise ScoringPhaseError(
                f"{sample_id}: reference masks differ in length — not the same reference"
            )
        for before, after in zip(base_mask, treat_mask):
            if before and after:
                totals["correct_to_correct"] += 1
            elif before and not after:
                totals["correct_to_wrong"] += 1
            elif not before and after:
                totals["wrong_to_correct"] += 1
            else:
                totals["wrong_to_wrong"] += 1
    return totals


SCORERS.register("asr-wer", score_asr_outputs)
