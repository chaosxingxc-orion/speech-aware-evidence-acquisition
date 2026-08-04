"""Entity-list scoring: multiset precision/recall/F1 under normalization v1 (E0 D3).

Entities are compared as normalized strings with multiset semantics: each expected
occurrence can be matched at most once, so repeating one correct entity never
inflates recall.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .normalize import normalize_text_v1


@dataclass(frozen=True)
class EntityScore:
    true_positives: int
    expected_total: int
    predicted_total: int

    @property
    def precision(self) -> float:
        return self.true_positives / self.predicted_total if self.predicted_total else 0.0

    @property
    def recall(self) -> float:
        return self.true_positives / self.expected_total if self.expected_total else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def _normalized_counter(entities: Iterable[str]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for entity in entities:
        normalized = normalize_text_v1(entity)
        if normalized:
            counter[normalized] += 1
    return counter


def score_entities(expected: Iterable[str], predicted: Iterable[str]) -> EntityScore:
    expected_counts = _normalized_counter(expected)
    predicted_counts = _normalized_counter(predicted)
    overlap = sum((expected_counts & predicted_counts).values())
    return EntityScore(
        true_positives=overlap,
        expected_total=sum(expected_counts.values()),
        predicted_total=sum(predicted_counts.values()),
    )
