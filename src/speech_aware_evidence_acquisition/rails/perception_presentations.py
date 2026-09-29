"""Perception-branch PRESENTATION registry entries (same-flight instrument
phase 2, merge set C, item 6).

Canonical registration site for ``core.base.PERCEPTION_PRESENTATIONS``,
mirroring ``rails/delivery_normalisers.py``'s relationship to
``core.base.DELIVERY_NORMALISERS``: the registry lives in ``core.base``, the
concrete entries live beside their implementation here, and a caller resolves
a registered id through a function-local deferred import (the config loader,
``rails.native_episode_config``).

Two presentations are registered (design section 3, item 6):

* ``rank-visible-v1`` wraps the existing ``rails.runner.
  rank_visible_value_renderer`` -- no new rendering rule, just the SAME rank
  labelling that renderer already applies to a whole-episode
  ``knowledge_value_renderer``, now addressable per Perception branch.
* ``top2-contrast-v1`` renders one block for a branch's rank-1/rank-2
  candidate pair from a PINNED, model-free contrast-pair table -- built by
  ``scripts/build_slurp_intent_contrast_pairs.py`` (W3a's word-gap method,
  over the R01-excluded TRAIN pool, with its own receipt). That mining script
  is NOT part of this change: this module implements the renderer's contract
  (what it does with a table, including the O5 "no fallback" rule) against
  whatever table a caller pins and passes in; it does not mine or pin one.

ZERO CONTACT. Neither presentation makes any model, tokenizer, encoder, tool,
server or network contact: ``rank-visible-v1`` is a pure re-labelling of
already-resolved values, and ``top2-contrast-v1`` is a pure lookup into a
pre-built, already-pinned table.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..core.base import PERCEPTION_PRESENTATIONS

#: Wraps ``rails.runner.rank_visible_value_renderer`` (design section 3, item
#: 6): no new rendering rule, the SAME rank-labelling renderer already
#: applies to a whole-episode ``knowledge_value_renderer``.
RANK_VISIBLE_PRESENTATION_ID = "rank-visible-v1"
RANK_VISIBLE_PRESENTATION_VERSION = "1"

#: Renders one contrast block for a branch's rank-1/rank-2 candidate pair
#: from a pinned, model-free contrast-pair table (design section 3, item 6).
TOP2_CONTRAST_PRESENTATION_ID = "top2-contrast-v1"
TOP2_CONTRAST_PRESENTATION_VERSION = "1"

#: O5 ruling (docs/superpowers/specs/2026-09-28-same-flight-instrument-
#: phase2-perception-variants-design.md, "Coordinator rulings", O5): when a
#: candidate pair's pool support is under the registered floor,
#: ``top2-contrast-v1`` renders NOTHING for that row -- never a fallback to
#: W3a's closed contrast-card line. This is the receipted reason.
TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT = "insufficient-pool-support"

#: The two fields one pinned contrast-pair table ROW must carry for
#: ``top2-contrast-v1`` to render it: the activation sentence (what picks
#: THIS intent over the other) and the exclusion sentence (what rules the
#: other one out), exactly the two sentences design section 3 names ("their
#: activation/exclusion sentences, nothing else").
_CONTRAST_PAIR_ROW_KEYS = ("activation_sentence", "exclusion_sentence")


class _RankVisiblePresentation:
    """The ``rank-visible-v1`` registry entry (design section 3, item 6)."""

    id = RANK_VISIBLE_PRESENTATION_ID
    version = RANK_VISIBLE_PRESENTATION_VERSION

    def __call__(self, *, snapshot_sha256: str, stores: Sequence[str]):
        # Function-local: this is the SAME deferred-import discipline every
        # other registration in this module follows, and it keeps this
        # module's own import light (``rails.runner`` is a large module).
        from .runner import rank_visible_value_renderer  # noqa: PLC0415

        return rank_visible_value_renderer(snapshot_sha256=snapshot_sha256, stores=stores)


class _Top2ContrastPresentation:
    """The ``top2-contrast-v1`` registry entry (design section 3, item 6)."""

    id = TOP2_CONTRAST_PRESENTATION_ID
    version = TOP2_CONTRAST_PRESENTATION_VERSION

    def __call__(
        self,
        *,
        rank1_intent_id: str,
        rank2_intent_id: str,
        contrast_pairs: Mapping[frozenset, Mapping[str, object]],
    ) -> tuple[str | None, str | None]:
        """Render ONE contrast block for a branch's rank-1/rank-2 pair.

        Returns ``(text, skip_reason)``: exactly one of the two is ``None``.
        ``contrast_pairs`` is keyed by the FROZENSET of the two intent ids
        (order-independent, since the pair identifies the contrast, not which
        one is currently ranked first) to a row carrying at least
        :data:`_CONTRAST_PAIR_ROW_KEYS`. Per the O5 ruling: an absent pair, or
        a row missing either sentence (the receipted stand-in for
        "insufficient pool support" -- the caller that BUILDS the table is
        the one that knows the pool-support count and omits a row below its
        floor), renders NOTHING here rather than falling back to the closed
        W3a contrast-card line.
        """

        if not isinstance(rank1_intent_id, str) or not rank1_intent_id:
            raise ValueError("top2-contrast-v1 requires a non-empty rank1_intent_id")
        if not isinstance(rank2_intent_id, str) or not rank2_intent_id:
            raise ValueError("top2-contrast-v1 requires a non-empty rank2_intent_id")
        if rank1_intent_id == rank2_intent_id:
            raise ValueError(
                "top2-contrast-v1 requires two DISTINCT candidates; "
                f"both ranks named {rank1_intent_id!r}"
            )
        if not isinstance(contrast_pairs, Mapping):
            raise ValueError("top2-contrast-v1 requires a contrast_pairs mapping")
        key = frozenset({rank1_intent_id, rank2_intent_id})
        row = contrast_pairs.get(key)
        if not isinstance(row, Mapping):
            return None, TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT
        activation = row.get("activation_sentence")
        exclusion = row.get("exclusion_sentence")
        if (
            not isinstance(activation, str) or not activation.strip()
            or not isinstance(exclusion, str) or not exclusion.strip()
        ):
            return None, TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT
        return f"{activation}\n{exclusion}", None


PERCEPTION_PRESENTATIONS.register(RANK_VISIBLE_PRESENTATION_ID, _RankVisiblePresentation())
PERCEPTION_PRESENTATIONS.register(TOP2_CONTRAST_PRESENTATION_ID, _Top2ContrastPresentation())


__all__ = [
    "RANK_VISIBLE_PRESENTATION_ID",
    "RANK_VISIBLE_PRESENTATION_VERSION",
    "TOP2_CONTRAST_PRESENTATION_ID",
    "TOP2_CONTRAST_PRESENTATION_VERSION",
    "TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT",
]
