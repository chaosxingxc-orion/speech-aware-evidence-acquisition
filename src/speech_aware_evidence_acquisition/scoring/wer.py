"""Word error rate with a deterministic alignment (E0 D3 freeze).

Levenshtein alignment over token sequences with unit costs. The backtrace is
deterministic: at equal cost the operation preference is fixed as
match/substitution, then deletion, then insertion — so the same inputs always
produce the same alignment, hit mask and counts on every platform.

The per-reference-token hit mask is the frozen substrate for the
correct-to-wrong / wrong-to-correct transition accounting in
:mod:`speech_aware_evidence_acquisition.scoring.transitions`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class WerResult:
    hits: int
    substitutions: int
    deletions: int
    insertions: int
    reference_length: int
    ref_hit_mask: tuple[bool, ...]

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def wer(self) -> float:
        if self.reference_length == 0:
            return 0.0 if self.errors == 0 else float(self.errors)
        return self.errors / self.reference_length


def align(ref: Sequence[str], hyp: Sequence[str]) -> WerResult:
    """Align ``hyp`` against ``ref``; both are already-normalized token sequences."""

    for label, seq in (("ref", ref), ("hyp", hyp)):
        if not all(isinstance(token, str) for token in seq):
            raise TypeError(f"{label} tokens must all be str")
    rows, cols = len(ref) + 1, len(hyp) + 1
    cost = [[0] * cols for _ in range(rows)]
    for i in range(1, rows):
        cost[i][0] = i
    for j in range(1, cols):
        cost[0][j] = j
    for i in range(1, rows):
        for j in range(1, cols):
            diagonal = cost[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1)
            deletion = cost[i - 1][j] + 1
            insertion = cost[i][j - 1] + 1
            cost[i][j] = min(diagonal, deletion, insertion)

    hits = substitutions = deletions = insertions = 0
    mask = [False] * len(ref)
    i, j = len(ref), len(hyp)
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            diagonal = cost[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1)
            if cost[i][j] == diagonal:
                if ref[i - 1] == hyp[j - 1]:
                    hits += 1
                    mask[i - 1] = True
                else:
                    substitutions += 1
                i, j = i - 1, j - 1
                continue
        if i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            deletions += 1
            i -= 1
            continue
        insertions += 1
        j -= 1

    return WerResult(
        hits=hits,
        substitutions=substitutions,
        deletions=deletions,
        insertions=insertions,
        reference_length=len(ref),
        ref_hit_mask=tuple(mask),
    )
