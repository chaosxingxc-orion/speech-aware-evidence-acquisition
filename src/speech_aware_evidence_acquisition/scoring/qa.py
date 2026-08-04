"""Spoken-QA scoring: exact match and token F1 under normalization v1 (E0 D3).

SQuAD-style semantics: a prediction is scored against every acceptable answer and
the best score wins. Token F1 uses multiset overlap of normalization-v1 tokens.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from .normalize import normalize_text_v1, tokens_v1


def qa_exact_match(prediction: str, acceptable_answers: Iterable[str]) -> bool:
    answers = list(acceptable_answers)
    if not answers:
        raise ValueError("qa_exact_match requires at least one acceptable answer")
    normalized_prediction = normalize_text_v1(prediction)
    return any(normalized_prediction == normalize_text_v1(answer) for answer in answers)


def qa_token_f1(prediction: str, acceptable_answers: Iterable[str]) -> float:
    answers = list(acceptable_answers)
    if not answers:
        raise ValueError("qa_token_f1 requires at least one acceptable answer")
    prediction_tokens = Counter(tokens_v1(prediction))
    best = 0.0
    for answer in answers:
        answer_tokens = Counter(tokens_v1(answer))
        if not prediction_tokens and not answer_tokens:
            best = max(best, 1.0)
            continue
        overlap = sum((prediction_tokens & answer_tokens).values())
        if overlap == 0:
            continue
        precision = overlap / sum(prediction_tokens.values())
        recall = overlap / sum(answer_tokens.values())
        best = max(best, 2 * precision * recall / (precision + recall))
    return best
