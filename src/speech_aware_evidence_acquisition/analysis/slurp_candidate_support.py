"""Deterministic candidate-support projections; no outcome or model input."""
from collections import Counter


def candidate_sets(candidates, exemplar_labels, caps):
    """Preserve candidates and append support labels by count, then lexical tie."""
    baseline = list(dict.fromkeys(candidates))
    counts = Counter(exemplar_labels)
    if not baseline or any(not isinstance(v, str) or not v for v in [*baseline, *counts]):
        raise ValueError("candidate and exemplar labels must be nonempty identifiers")
    if any(type(cap) is not int or cap < len(baseline) for cap in caps):
        raise ValueError("a diagnostic cap cannot remove original candidates")
    extra = sorted((label for label in counts if label not in baseline),
                   key=lambda label: (-counts[label], label))
    union = baseline + extra
    return {"baseline": baseline, **{f"cap{cap}": union[:cap] for cap in caps}, "union": union}
