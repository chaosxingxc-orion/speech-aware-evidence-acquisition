"""The derived-media variant-id convention, in ONE place.

A probe MEDIA variant re-encodes the SAME published sample and must never
share an identifier with its source population -- section 1.4 of
``docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-preregistration.md``
fixes the convention as ``<published id>@<variant>``, and the 2026-09-07
cross-carrier silence-tail preregistration reuses it unchanged for the
``@ts2`` populations of SLURP, Audio2Tool and Earnings-21.

Every population therefore carries its own split identity, distinct from its
comparator's -- which is the whole point of the suffix -- while the GOLD a
row is scored against stays the published sample's own. Recovering the
published key is a one-line rule, and this module is the one place it lives:
``reproduction.esb_reference.published_segment_key`` (the Earnings-22 name
for it), ``rails.adapters.audio2tool``, ``reproduction.a2t_scorer`` and
``reproduction.slurp_official_eval`` all resolve gold through this function,
so the three carriers can never drift into three spellings of one rule.

Deliberately dependency-free (stdlib only, no package-internal imports): the
scorer modules that call it are kept light on purpose, and a gold-lookup rail
must never be the thing that drags a heavy import into a paper-facing path.
"""

from __future__ import annotations

VARIANT_ID_SEPARATOR = "@"
"""The one separator between a published sample id and a media-variant tag."""


def published_sample_key(sample_id: str) -> str:
    """The published sample id a derived-media id is scored against.

    The published key is recovered by splitting on ``@``, which is what keeps
    a gold lookup, a reference lookup and a paired join against a sealed arm
    exact.

    An id without a suffix is returned unchanged, so every population that
    existed before the convention is byte-for-byte unaffected -- this
    function is INERT on the whole pre-2026-09 corpus, which is the property
    that makes applying it at a paper-facing gold lookup safe.

    It is also not a skeleton key: it only strips a suffix, it never widens
    the gold closure. An id whose PUBLISHED key is foreign to a carrier's
    frozen gold still fails closed at the call site's own refusal, suffix or
    no suffix.
    """

    if not isinstance(sample_id, str):
        raise TypeError(f"sample id must be a string, got {type(sample_id).__name__}")
    return sample_id.split(VARIANT_ID_SEPARATOR, 1)[0]


def variant_suffix(sample_id: str) -> str | None:
    """``"ts2"`` for ``"tier1_direct:000045@ts2"``; ``None`` when unsuffixed.

    Diagnostic only -- receipts and verdicts name which variant a row came
    from. No gold lookup branches on it.
    """

    if not isinstance(sample_id, str):
        raise TypeError(f"sample id must be a string, got {type(sample_id).__name__}")
    published, separator, suffix = sample_id.partition(VARIANT_ID_SEPARATOR)
    del published
    return suffix if separator else None


__all__ = ["VARIANT_ID_SEPARATOR", "published_sample_key", "variant_suffix"]
