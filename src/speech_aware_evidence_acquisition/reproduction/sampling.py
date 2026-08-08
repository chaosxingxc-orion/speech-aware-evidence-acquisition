"""Seeded, order-independent stratified sampling + split-identity hashing (P0.D).

Pre-registration discipline: a probe's sample is fully determined by
(pool identity, per-stratum size, seed) — never by pool iteration order or
platform. The split identity hash follows the E0 convention: SHA-256 over
the LF-joined, sorted, carrier-prefixed item keys.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Callable, Iterable, Sequence, TypeVar

T = TypeVar("T")


def _default_key(item: object) -> str:
    return json.dumps(item, sort_keys=True, ensure_ascii=False)


def stratified_sample(
    pool: Sequence[T],
    *,
    per_stratum: int,
    seed: int,
    stratum_of: Callable[[T], str],
    key_of: Callable[[T], str] | None = None,
) -> list[T]:
    """Sample up to ``per_stratum`` items from each stratum, deterministically.

    Items within a stratum are sorted by their key before the seeded draw, so
    the selection is independent of pool order; strata smaller than
    ``per_stratum`` are taken whole. The result is sorted by key.
    """
    key_fn = key_of or _default_key
    strata: dict[str, list[T]] = {}
    for item in pool:
        strata.setdefault(stratum_of(item), []).append(item)

    selected: list[T] = []
    for stratum_name in sorted(strata):
        members = sorted(strata[stratum_name], key=key_fn)
        if len(members) <= per_stratum:
            selected.extend(members)
            continue
        rng = random.Random(f"{seed}:{stratum_name}")
        selected.extend(
            members[index] for index in sorted(rng.sample(range(len(members)), per_stratum))
        )
    return sorted(selected, key=key_fn)


def split_identity_hash(keys: Iterable[str]) -> str:
    """SHA-256 over the sorted, LF-joined item keys; duplicates are an error."""
    key_list = list(keys)
    if len(set(key_list)) != len(key_list):
        raise ValueError("duplicate sample-identity keys")
    return hashlib.sha256("\n".join(sorted(key_list)).encode("utf-8")).hexdigest()
