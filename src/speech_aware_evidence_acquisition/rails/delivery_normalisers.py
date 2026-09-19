"""Deterministic DELIVERY normalisers: the delivery-time node of the native
episode (E11, 2026-09-18, owner directive 26).

Owner directive 26 of 2026-09-18 ("analyses into nodes"): an offline analysis
this program trusts must be placed INSIDE an agent node, not only reported
beside the number. Owner decision 23 of 2026-09-18 fixes the bar and every
final evaluation on the OFFICIAL, unprojected SLURP ``evaluate.py`` number.
Together those two make the SLURP USE projection v3 (module M3) a runtime
question rather than a scorer question: while the rule lives in the scorer
(``slurp-slu-official-projected-v3[-train]``, item E4) the official scorer
does not credit it, and the same rule applied INSIDE the episode, before the
answer is delivered, is credited by the official scorer like any other
answer the system produced.

This module is the canonical registration site for
``core.base.DELIVERY_NORMALISERS``, mirroring ``rails/commit_policies.py``'s
relationship to ``core.base.COMMIT_POLICIES``: the registry lives in
``core.base``, the concrete entry lives beside its implementation, and a
caller resolves the registered id through a function-local deferred import
(``rails.native_episode_config.load_native_episode_config``).

ONE IMPLEMENTATION, TWO CALLERS. The entry registered here does NOT restate
projection v3. It calls
:func:`rails.slurp_projection_v3.apply_slurp_projection_v3_delivery`, which
is the same pair of functions
(:func:`rails.slurp_projection_v3.project_slu_label_v3`,
:func:`rails.slurp_projection_v3.normalize_filler_p2`) the v3 SCORER applies
in ``reproduction.slurp_official_eval``. A second implementation of the rule
is exactly what would let the runtime form and the scorer form drift apart,
and the E11 byte-equality test
(``tests/unit/test_deliver_normaliser_node.py``) pins that they do not.

ZERO CONTACT. Applying the node makes no model, tokenizer, encoder, tool,
server or network contact of any kind, and reads no gold for the row it is
rewriting: the label half needs the 60-id legal intent inventory (mined from
TRAIN, the same closed list the task contract already renders into the
prompt) and the filler half needs nothing beyond the text. It therefore
changes no request byte, spends no budget and is replayable offline from
sealed bytes (``analysis.deliver_normaliser_replay``).
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from ..core.base import DELIVERY_NORMALISERS, DeliveryNormalisation

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..reproduction.slurp_scoring import LegalIntentInventory

#: The receipt schema the episode seals under
#: ``native_episode_receipt.deliver_normaliser``. Bumped only when the
#: receipt's FIELD SET changes; the rule's own identity travels in
#: ``rule_id`` / ``normaliser_id`` / ``version``.
DELIVER_NORMALISER_RECEIPT_SCHEMA = "saea-deliver-normaliser-v1"

#: The one normaliser this module registers (E11). A
#: ``native_episode.deliver_normaliser.normaliser`` value resolves to this id
#: in ``core.base.DELIVERY_NORMALISERS``.
DELIVER_NORMALISE_V3 = "saea-deliver-normalise-v3"

#: Bumped when the RULE changes, never when this file is merely edited: an
#: admission receipt and a preregistration quote it.
DELIVER_NORMALISE_V3_VERSION = "1"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SlurpProjectionV3DeliveryNormaliser:
    """``saea-deliver-normalise-v3``: SLURP USE projection v3, applied once to
    the accepted answer, immediately before delivery.

    Pure and deterministic. The input is the delivered structured answer of
    the native episode (``{"scenario", "action", "entities": [{type,
    filler}]}``, the shape
    :func:`reproduction.slurp_scoring.parse_slu_response` parses); the output
    is the same answer after the label rule ``R_action`` then the registered
    legal-label projection v2, and then the filler normalisation P2 (case,
    whitespace, punctuation, meridiem, numeric words; NO support filter,
    rejected by the A1 audit). An answer the parser refuses is returned
    byte-identically, with ``applied: false`` and the reason recorded --
    there is no label or filler to project, and inventing one would be the
    node writing an answer rather than normalising one.

    IDEMPOTENT by construction and pinned by test: the label rule leaves an
    already-legal pair alone and the filler rule is a fixed point on its own
    output, so re-applying the node (or running the v3 SCORER over an
    already-normalised row) changes nothing.

    ONE FACTOR, DOWN TO THE BYTE: when the rule repairs neither a label nor a
    filler, the accepted answer is delivered VERBATIM rather than re-rendered
    in the canonical JSON shape (see :meth:`__call__`), so an ON arm differs
    from its comparator exactly on the rows the rule repairs.
    """

    id = DELIVER_NORMALISE_V3
    version = DELIVER_NORMALISE_V3_VERSION
    #: The ONE carrier this rule is defined for. ``rails.native_episode_config``
    #: refuses a fragment that arms it on any other carrier, before contact.
    carrier_lock_key = "slurp"

    def __call__(
        self, text: str, *, inventory: "LegalIntentInventory | None" = None
    ) -> DeliveryNormalisation:
        """Normalise one delivered answer.

        ``inventory`` is an optional injection point for tests and for the
        offline replay: left ``None`` (every runtime call) the rule loads the
        real TRAIN-mined legal intent inventory once per process, exactly as
        the v3 scorer does.
        """

        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        # Deferred: rails.slurp_projection_v3 pulls reproduction.slurp_scoring,
        # and this module is imported for its REGISTRATION side effect from
        # config loading and bundle verification, which must stay import-light.
        from .slurp_projection_v3 import (  # noqa: PLC0415
            apply_slurp_projection_v3_delivery,
        )

        outcome = apply_slurp_projection_v3_delivery(
            text, carrier_lock_key=self.carrier_lock_key, inventory=inventory
        )
        metadata = dict(outcome.metadata)
        applied = bool(metadata.get("applied"))
        labels_changed = int(bool(metadata.get("label_changed"))) if applied else 0
        fillers_changed = int(metadata.get("fillers_changed") or 0) if applied else 0
        # ONE FACTOR, DOWN TO THE BYTE. ``apply_slurp_projection_v3_delivery``
        # always RE-RENDERS the answer it parsed, so on a row the rule does
        # not repair it still returns different bytes -- the model's own JSON
        # spacing and key order replaced by the canonical rendering. On the
        # sealed B1 arm that is 1,076 of 1,080 rows against 24 repaired
        # labels and 82 repaired fillers, i.e. almost the whole arm changed
        # for no reason a verdict could read. The NODE therefore delivers the
        # accepted answer VERBATIM whenever the rule moved neither a label
        # nor a filler, so the ON arm differs from its comparator exactly on
        # the rows the rule actually repairs, and ``changed`` means "the rule
        # repaired this row" rather than "the serialiser disagreed". The
        # scored triple is identical either way -- the official scorer parses
        # both renderings to the same (scenario, action, entities) -- which is
        # why suppressing the re-render costs nothing and is pinned by the
        # sealed-byte equality test. The SEAL-time E4 transform keeps its own
        # behaviour; only this node suppresses.
        rendering_suppressed = bool(outcome.changed) and not (
            labels_changed or fillers_changed
        )
        delivered = text if rendering_suppressed else outcome.text
        changed = delivered != text
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": str(metadata.get("rule_id")),
            "carrier_lock_key": self.carrier_lock_key,
            "applied": applied,
            "changed": changed,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(delivered),
            # Intent accuracy may move ONLY through the label half and the
            # entity block never changes labels (the A1 audit's own contract),
            # so the two counts are kept apart rather than summed.
            "labels_changed": labels_changed,
            "label_branch": metadata.get("label_branch") if applied else None,
            "fillers_changed": fillers_changed,
            # True when the rule repaired nothing and the accepted answer was
            # therefore delivered verbatim rather than re-rendered.
            "rendering_suppressed": rendering_suppressed,
            "reason": None if applied else str(metadata.get("reason")),
        }
        return DeliveryNormalisation(
            text=delivered, changed=changed, receipt=receipt
        ).validate()


DELIVERY_NORMALISERS.register(
    DELIVER_NORMALISE_V3, SlurpProjectionV3DeliveryNormaliser()
)


__all__ = [
    "DELIVER_NORMALISER_RECEIPT_SCHEMA",
    "DELIVER_NORMALISE_V3",
    "DELIVER_NORMALISE_V3_VERSION",
    "SlurpProjectionV3DeliveryNormaliser",
]
