"""Aggregate-only paired headroom audit for post-contact arbitration."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

MIN_SAVES = 4
MIN_HARMS = 2
MIN_ALWAYS_MATCHED_NET = 2
MIN_ORACLE_NET_OVER_M0 = 4
MIN_ORACLE_NET_OVER_MATCHED = 2


class PostContactHeadroomError(RuntimeError):
    """The aggregate-only paired audit refused malformed input."""


@dataclass(frozen=True)
class PairedExactRecord:
    """One sealed pair represented without publishing its identity or outcome."""

    sample_id: str
    m0_exact: int
    matched_exact: int
    m0_text: str
    matched_text: str
    m0_parsed: bool
    matched_parsed: bool

    def __post_init__(self) -> None:
        if not isinstance(self.sample_id, str) or not self.sample_id:
            raise ValueError("sample_id must be non-empty text")
        for label, value in (
            ("m0_exact", self.m0_exact),
            ("matched_exact", self.matched_exact),
        ):
            if isinstance(value, bool) or value not in (0, 1):
                raise ValueError(f"{label} must be binary")
        if not isinstance(self.m0_text, str) or not isinstance(
            self.matched_text, str
        ):
            raise ValueError("paired outputs must be text")
        if not isinstance(self.m0_parsed, bool) or not isinstance(
            self.matched_parsed, bool
        ):
            raise ValueError("parse indicators must be booleans")


@dataclass(frozen=True)
class HeadroomResult:
    n_samples: int
    paired_counts: Mapping[str, int]
    parse_counts: Mapping[str, int]
    changed_count: int
    unchanged_count: int
    m0_exact_count: int
    matched_exact_count: int
    always_matched_net: int
    oracle_exact_count: int
    oracle_minus_m0: int
    oracle_minus_matched: int
    gates: Mapping[str, bool]
    postcontact_headroom_present: bool

    def as_json(self) -> dict[str, object]:
        return asdict(self)


def _paired_label(record: PairedExactRecord) -> str:
    pair = (record.m0_exact, record.matched_exact)
    return {
        (0, 1): "save",
        (1, 0): "harm",
        (1, 1): "both_correct",
        (0, 0): "both_wrong",
    }[pair]


def _parse_label(record: PairedExactRecord) -> str:
    pair = (record.m0_parsed, record.matched_parsed)
    return {
        (False, True): "parse_rescue",
        (True, False): "parse_loss",
        (True, True): "both_parse",
        (False, False): "neither_parse",
    }[pair]


def analyse(records: Sequence[PairedExactRecord]) -> HeadroomResult:
    """Return only aggregate paired counts and exact headroom identities."""

    rows = tuple(records)
    if not rows:
        raise PostContactHeadroomError("paired audit requires records")
    identities = [row.sample_id for row in rows]
    duplicates = sorted(
        sample_id
        for sample_id, count in Counter(identities).items()
        if count > 1
    )
    if duplicates:
        raise PostContactHeadroomError(
            f"paired audit contains duplicate identities: {duplicates!r}"
        )
    pair_counter = Counter(_paired_label(row) for row in rows)
    parse_counter = Counter(_parse_label(row) for row in rows)
    paired_counts = {
        label: pair_counter[label]
        for label in ("save", "harm", "both_correct", "both_wrong")
    }
    parse_counts = {
        label: parse_counter[label]
        for label in ("parse_rescue", "parse_loss", "both_parse", "neither_parse")
    }
    changed_count = sum(row.m0_text != row.matched_text for row in rows)
    m0_exact_count = sum(row.m0_exact for row in rows)
    matched_exact_count = sum(row.matched_exact for row in rows)
    oracle_exact_count = m0_exact_count + paired_counts["save"]
    always_matched_net = matched_exact_count - m0_exact_count
    oracle_minus_m0 = oracle_exact_count - m0_exact_count
    oracle_minus_matched = oracle_exact_count - matched_exact_count
    if (
        sum(paired_counts.values()) != len(rows)
        or sum(parse_counts.values()) != len(rows)
        or always_matched_net
        != paired_counts["save"] - paired_counts["harm"]
        or oracle_minus_matched != paired_counts["harm"]
    ):
        raise PostContactHeadroomError("paired headroom arithmetic drift")
    gates = {
        "minimum_saves": paired_counts["save"] >= MIN_SAVES,
        "minimum_harms": paired_counts["harm"] >= MIN_HARMS,
        "always_matched_net": always_matched_net >= MIN_ALWAYS_MATCHED_NET,
        "oracle_net_over_m0": oracle_minus_m0 >= MIN_ORACLE_NET_OVER_M0,
        "oracle_net_over_matched": (
            oracle_minus_matched >= MIN_ORACLE_NET_OVER_MATCHED
        ),
    }
    return HeadroomResult(
        n_samples=len(rows),
        paired_counts=paired_counts,
        parse_counts=parse_counts,
        changed_count=changed_count,
        unchanged_count=len(rows) - changed_count,
        m0_exact_count=m0_exact_count,
        matched_exact_count=matched_exact_count,
        always_matched_net=always_matched_net,
        oracle_exact_count=oracle_exact_count,
        oracle_minus_m0=oracle_minus_m0,
        oracle_minus_matched=oracle_minus_matched,
        gates=gates,
        postcontact_headroom_present=all(gates.values()),
    )


__all__ = [
    "HeadroomResult",
    "PairedExactRecord",
    "PostContactHeadroomError",
    "analyse",
]
