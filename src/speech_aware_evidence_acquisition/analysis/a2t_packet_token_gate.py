"""Deterministic token accounting for complete Audio2Tool speech packets."""

from __future__ import annotations

import math
from collections.abc import Mapping
from statistics import mean, median


def _nearest_rank(values: list[int], quantile: float) -> int:
    """Return the conventional one-indexed nearest-rank percentile."""

    index = max(1, math.ceil(quantile * len(values))) - 1
    return values[index]


def summarize_packet_tokens(
    packet_tokens: Mapping[str, int], *, ceiling: int
) -> dict[str, object]:
    """Summarize complete packet sizes without transforming any packet."""

    if isinstance(ceiling, bool) or not isinstance(ceiling, int) or ceiling <= 0:
        raise ValueError("ceiling must be a positive integer")
    if not packet_tokens:
        raise ValueError("packet_tokens must not be empty")
    normalized: list[dict[str, object]] = []
    for packet_id, n_tokens in sorted(packet_tokens.items()):
        if not isinstance(packet_id, str) or not packet_id:
            raise ValueError("packet_id must be a non-empty string")
        if isinstance(n_tokens, bool) or not isinstance(n_tokens, int) or n_tokens <= 0:
            raise ValueError("packet n_tokens must be a positive integer")
        normalized.append({"packet_id": packet_id, "n_tokens": n_tokens})
    values = sorted(int(item["n_tokens"]) for item in normalized)
    return {
        "ceiling": ceiling,
        "within_ceiling": max(values) <= ceiling,
        "distribution": {
            "count": len(values),
            "max": max(values),
            "mean": round(mean(values), 6),
            "median": float(median(values)),
            "min": min(values),
            "p90": _nearest_rank(values, 0.90),
            "p95": _nearest_rank(values, 0.95),
            "sum": sum(values),
        },
        "packets": normalized,
    }
