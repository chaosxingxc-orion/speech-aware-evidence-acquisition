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
import json
import re
from typing import TYPE_CHECKING

from ..core.base import DELIVERY_NORMALISERS, DeliveryNormalisation, DeliveryNormaliserError
from .solver_citation import (
    DELIVER_CITED_ANSWER_NORMALISE_V3_V1,
    DELIVER_CITED_ANSWER_V1,
    SolverCitationError,
    parse_cited_answer,
)

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

#: Item E35 (owner decision 89, 2026-09-21): the Earnings21+ConEC delivery
#: normaliser this module registers alongside the SLURP one. A
#: ``native_episode.deliver_normaliser.normaliser`` value of this id resolves
#: here in ``core.base.DELIVERY_NORMALISERS``.
DELIVER_NORMALISE_EARNINGS_TEXT_V1 = "saea-deliver-earnings-text-v1"

#: Bumped when the HYGIENE RULE changes, never when this file is merely
#: edited: an admission receipt and a preregistration quote it.
DELIVER_NORMALISE_EARNINGS_TEXT_V1_VERSION = "1"


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


class EarningsTextDeliveryNormaliser:
    """``saea-deliver-earnings-text-v1``: deterministic Earnings21+ConEC
    delivery hygiene, applied once to the delivered transcript text,
    immediately before delivery.

    Item E35 (owner decision 89, 2026-09-21): the Earnings21+ConEC carrier's
    own delivery-time node, so it can fly the same six-node native episode
    SLURP flies through the shared harness. Unlike the SLURP v3 rule, this
    normaliser applies NO scoring-adjacent transform at all: the standard
    Earnings scorer (``asr-wer-whisper``) already owns Whisper text
    normalisation, and no entity or numeric rewriting belongs in an agent
    node (study CLAUDE.md's OBS/ORG/SUPPLY/USE separation). It removes only
    deterministic, documented TEXT HYGIENE the episode's own role-graph
    markup may have added around the Solver's final transcript, IN ORDER:

    1. strip one leading role/label wrapper the episode's own instruction
       vocabulary might add (``"Transcript:"``, ``"Answer:"``, ``"Final:"``,
       case-insensitive, at most once, only at the very start);
    2. strip one surrounding pair of XML-ish tags, if the WHOLE remaining
       text is wrapped (``<transcript>...</transcript>``,
       ``<answer>...</answer>``, case-insensitive);
    3. strip one surrounding pair of Markdown code fences, if the WHOLE
       remaining text is wrapped (```` ```...``` ````, with or without a
       language tag on the opening fence);
    4. collapse every run of ASCII whitespace (spaces, tabs, newlines) to a
       single space and strip leading/trailing whitespace.

    Byte-identical passthrough when none of the above matches anything: the
    delivered text equals the input exactly, and ``changed`` is false.

    E13 (``deliver-latest-or-abstain``): if the hygiene above leaves nothing
    (the input was empty, or contained only wrapper markup and whitespace),
    this normaliser REFUSES rather than deliver a blank transcript as if it
    were content -- the episode's own finite-completion policy is the layer
    authorized to decide an abstain outcome, not this node inventing one.
    """

    id = DELIVER_NORMALISE_EARNINGS_TEXT_V1
    version = DELIVER_NORMALISE_EARNINGS_TEXT_V1_VERSION
    #: The ONE carrier this rule is defined for. ``rails.native_episode_config``
    #: refuses a fragment that arms it on any other carrier, before contact.
    carrier_lock_key = "earnings21-original"

    _LABEL_PREFIX = re.compile(
        r"^\s*(transcript|answer|final)\s*:\s*", re.IGNORECASE
    )
    _TAG_WRAPPER = re.compile(
        r"^\s*<(transcript|answer)>(.*)</" r"\1" r">\s*$",
        re.IGNORECASE | re.DOTALL,
    )
    _FENCE_WRAPPER = re.compile(
        r"^\s*```(?:[A-Za-z0-9_-]*" "\n" r")?(.*?)```\s*$", re.DOTALL
    )
    _WHITESPACE_RUN = re.compile(r"\s+")

    def __call__(self, text: str) -> DeliveryNormalisation:
        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        hygiened = self._LABEL_PREFIX.sub("", text, count=1)
        tag_match = self._TAG_WRAPPER.match(hygiened)
        if tag_match is not None:
            hygiened = tag_match.group(2)
        fence_match = self._FENCE_WRAPPER.match(hygiened)
        if fence_match is not None:
            hygiened = fence_match.group(1)
        hygiened = self._WHITESPACE_RUN.sub(" ", hygiened).strip()
        if not hygiened:
            raise DeliveryNormaliserError(
                f"{self.id}: delivered text is empty after hygiene; abstain "
                "(E13 deliver-latest-or-abstain) rather than deliver a blank "
                "transcript"
            )
        changed = hygiened != text
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": "earnings-text-hygiene-v1",
            "carrier_lock_key": self.carrier_lock_key,
            "applied": changed,
            "changed": changed,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(hygiened),
            "reason": None,
        }
        return DeliveryNormalisation(text=hygiened, changed=changed, receipt=receipt).validate()


#: Bumped when the UNWRAP RULE changes, never when this file is merely
#: edited: an admission receipt and a preregistration quote it.
DELIVER_CITED_ANSWER_V1_VERSION = "1"
DELIVER_CITED_ANSWER_NORMALISE_V3_V1_VERSION = "1"


class CitedAnswerUnwrapDeliveryNormaliser:
    """``saea-deliver-cited-answer-v1``: deliver the ANSWER of a cited-answer
    envelope (``rails.solver_citation``), applied once, immediately before
    delivery.

    Gap G1 plumbing. Under the cited-answer contract the Solver's model
    response is ``{"schema", "answer", "citations"}``; the answer the row
    delivers is the ``answer`` member's OWN BYTES, cut from the raw response
    by :func:`rails.solver_citation.answer_span` -- the model's spacing and
    key order, never a re-serialisation -- so the citation is metadata beside
    the answer and never part of the delivered text. Pure and deterministic:
    the same recorded response always yields the same bytes, which is what
    invariant I7n replays at the seal and in the bundle.

    Text the contract's parser refuses is delivered VERBATIM with
    ``applied: false`` and the reason recorded, exactly as the v3 rule treats
    an unparsed answer: the only way such text reaches delivery is the
    finite-completion path (a truncated envelope the episode's own policy
    chose to deliver), and a normaliser that invented an answer would be the
    node writing one rather than unwrapping one.
    ``rails.native_episode_config`` refuses a fragment that arms this rule
    without the contract, or the contract without this rule (or its v3
    composition below), so an envelope is never delivered as an answer.
    """

    id = DELIVER_CITED_ANSWER_V1
    version = DELIVER_CITED_ANSWER_V1_VERSION
    #: The contract cites intents and entities, the SLURP task's own shape.
    carrier_lock_key = "slurp"

    def __call__(self, text: str) -> DeliveryNormalisation:
        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        try:
            parsed = parse_cited_answer(text)
        except SolverCitationError as error:
            delivered, applied, reason, cited = text, False, str(error), ()
        else:
            delivered, applied, reason, cited = (
                parsed.answer_text, True, None, parsed.cited_value_ids
            )
        changed = delivered != text
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": "cited-answer-unwrap-v1",
            "carrier_lock_key": self.carrier_lock_key,
            "applied": applied,
            "changed": changed,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(delivered),
            # Counts and a digest only; the ids themselves are sealed on the
            # Solver state's ``cited_value_ids`` and in the row's
            # ``solver_citations`` receipt block.
            "cited_value_ids_count": len(cited),
            "cited_value_ids_sha256": _sha256(json.dumps(list(cited))),
            "reason": reason,
        }
        return DeliveryNormalisation(text=delivered, changed=changed, receipt=receipt).validate()


class CitedAnswerNormaliseV3DeliveryNormaliser:
    """``saea-deliver-cited-answer-normalise-v3-v1``: the unwrap above, then
    the locked plan's own ``saea-deliver-normalise-v3`` over the unwrapped
    answer, as ONE registered rule.

    ``native_episode.deliver_normaliser`` names exactly one normaliser and the
    v2.0 lock already spends it on projection v3, so a cell that arms the
    cited-answer contract on the locked plan needs the composition under one
    id. It composes the two REGISTERED callables rather than restating either
    rule (one implementation, two callers, the discipline this module states
    for v3 itself); the receipt carries both stage receipts under ``stages``
    beside the top-level input/output digests I7n binds.
    """

    id = DELIVER_CITED_ANSWER_NORMALISE_V3_V1
    version = DELIVER_CITED_ANSWER_NORMALISE_V3_V1_VERSION
    carrier_lock_key = "slurp"

    def __call__(
        self, text: str, *, inventory: "LegalIntentInventory | None" = None
    ) -> DeliveryNormalisation:
        if not isinstance(text, str):
            raise TypeError("a delivery normaliser takes the delivered answer text")
        unwrap = DELIVERY_NORMALISERS.resolve(DELIVER_CITED_ANSWER_V1)(text)
        projected = DELIVERY_NORMALISERS.resolve(DELIVER_NORMALISE_V3)(
            unwrap.text, inventory=inventory
        )
        delivered = projected.text
        changed = delivered != text
        receipt: dict[str, object] = {
            "schema": DELIVER_NORMALISER_RECEIPT_SCHEMA,
            "normaliser_id": self.id,
            "version": self.version,
            "rule_id": "cited-answer-unwrap-then-slurp-use-projection-v3",
            "carrier_lock_key": self.carrier_lock_key,
            "applied": bool(unwrap.receipt["applied"]) or bool(projected.receipt["applied"]),
            "changed": changed,
            "input_sha256": _sha256(text),
            "output_sha256": _sha256(delivered),
            "labels_changed": projected.receipt["labels_changed"],
            "label_branch": projected.receipt["label_branch"],
            "fillers_changed": projected.receipt["fillers_changed"],
            "stages": [dict(unwrap.receipt), dict(projected.receipt)],
            "reason": None,
        }
        return DeliveryNormalisation(text=delivered, changed=changed, receipt=receipt).validate()


DELIVERY_NORMALISERS.register(
    DELIVER_NORMALISE_V3, SlurpProjectionV3DeliveryNormaliser()
)
DELIVERY_NORMALISERS.register(
    DELIVER_NORMALISE_EARNINGS_TEXT_V1, EarningsTextDeliveryNormaliser()
)
DELIVERY_NORMALISERS.register(
    DELIVER_CITED_ANSWER_V1, CitedAnswerUnwrapDeliveryNormaliser()
)
DELIVERY_NORMALISERS.register(
    DELIVER_CITED_ANSWER_NORMALISE_V3_V1, CitedAnswerNormaliseV3DeliveryNormaliser()
)


__all__ = [
    "DELIVER_NORMALISER_RECEIPT_SCHEMA",
    "DELIVER_NORMALISE_V3",
    "DELIVER_NORMALISE_V3_VERSION",
    "DELIVER_NORMALISE_EARNINGS_TEXT_V1",
    "DELIVER_NORMALISE_EARNINGS_TEXT_V1_VERSION",
    "DELIVER_CITED_ANSWER_V1",
    "DELIVER_CITED_ANSWER_V1_VERSION",
    "DELIVER_CITED_ANSWER_NORMALISE_V3_V1",
    "DELIVER_CITED_ANSWER_NORMALISE_V3_V1_VERSION",
    "SlurpProjectionV3DeliveryNormaliser",
    "EarningsTextDeliveryNormaliser",
    "CitedAnswerUnwrapDeliveryNormaliser",
    "CitedAnswerNormaliseV3DeliveryNormaliser",
]
