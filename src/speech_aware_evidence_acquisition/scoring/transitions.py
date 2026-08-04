"""Correct-to-wrong / wrong-to-correct transition accounting (E0 D3 freeze).

The evaluation contract requires reporting not only aggregate scores but how an
intervention *moves* individual units: a system that fixes some errors while
breaking previously-correct units is different from one that only fixes. Two frozen
granularities:

- token level (ASR): a unit is one reference token; a unit is *correct* in one
  system iff the deterministic alignment marks it as a hit
  (:func:`speech_aware_evidence_acquisition.scoring.wer.align` ``ref_hit_mask``);
- item level (QA/entity tasks): a unit is one item with a boolean correctness flag
  per system (for example QA exact match).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .wer import align


@dataclass(frozen=True)
class TransitionCounts:
    correct_to_correct: int
    correct_to_wrong: int
    wrong_to_correct: int
    wrong_to_wrong: int

    @property
    def units(self) -> int:
        return (
            self.correct_to_correct
            + self.correct_to_wrong
            + self.wrong_to_correct
            + self.wrong_to_wrong
        )


def flag_transitions(
    baseline_correct: Sequence[bool], treatment_correct: Sequence[bool]
) -> TransitionCounts:
    if len(baseline_correct) != len(treatment_correct):
        raise ValueError(
            "transition accounting requires the same unit list for both systems: "
            f"{len(baseline_correct)} != {len(treatment_correct)}"
        )
    c2c = c2w = w2c = w2w = 0
    for before, after in zip(baseline_correct, treatment_correct):
        if before and after:
            c2c += 1
        elif before and not after:
            c2w += 1
        elif not before and after:
            w2c += 1
        else:
            w2w += 1
    return TransitionCounts(c2c, c2w, w2c, w2w)


def token_transitions(
    reference_tokens: Sequence[str],
    baseline_tokens: Sequence[str],
    treatment_tokens: Sequence[str],
) -> TransitionCounts:
    """Per-reference-token transitions between two hypotheses of the same utterance."""

    baseline_mask = align(reference_tokens, baseline_tokens).ref_hit_mask
    treatment_mask = align(reference_tokens, treatment_tokens).ref_hit_mask
    return flag_transitions(baseline_mask, treatment_mask)
