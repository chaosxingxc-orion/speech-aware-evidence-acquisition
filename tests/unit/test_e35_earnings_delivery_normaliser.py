"""Item E35 (owner decision 89, 2026-09-21): the Earnings21+ConEC carrier's
own delivery-time normaliser, ``saea-deliver-earnings-text-v1``.

Mirrors ``tests/unit/test_deliver_normaliser_node.py``'s layering for the
SLURP v3 rule, scoped to what this rule actually is: deterministic text
HYGIENE only (strip role/markup wrappers the episode's own instruction
vocabulary might add; collapse whitespace) -- never Whisper normalisation
(the scorer, ``asr-wer-whisper``, owns that) and never entity/numeric
rewriting (no ORG/USE crossover; study CLAUDE.md). Model-free and offline:
no model, tokenizer, encoder, tool, server or network contact.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.base import (
    DELIVERY_NORMALISERS,
    DeliveryNormalisation,
    DeliveryNormaliserError,
    assert_delivery_normaliser,
)

# Importing rails.delivery_normalisers is what POPULATES
# core.base.DELIVERY_NORMALISERS.
from speech_aware_evidence_acquisition.rails import (  # noqa: F401
    delivery_normalisers as _delivery_normalisers,
)
from speech_aware_evidence_acquisition.rails.delivery_normalisers import (
    DELIVER_NORMALISE_EARNINGS_TEXT_V1,
    DELIVER_NORMALISE_EARNINGS_TEXT_V1_VERSION,
    DELIVER_NORMALISER_RECEIPT_SCHEMA,
    EarningsTextDeliveryNormaliser,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)

from test_native_episode_config import config as _episode_values, program as _program

ARM = {"normaliser": DELIVER_NORMALISE_EARNINGS_TEXT_V1}


def _normaliser() -> EarningsTextDeliveryNormaliser:
    return EarningsTextDeliveryNormaliser()


# ---------------------------------------------------------------------------
# 1. Registration: callable, identified, carrier-scoped (core.base's own door).
# ---------------------------------------------------------------------------


def test_it_is_registered_and_passes_the_registration_door():
    normaliser = DELIVERY_NORMALISERS.resolve(DELIVER_NORMALISE_EARNINGS_TEXT_V1)
    assert isinstance(normaliser, EarningsTextDeliveryNormaliser)
    assert assert_delivery_normaliser(normaliser, name=DELIVER_NORMALISE_EARNINGS_TEXT_V1) is normaliser
    assert normaliser.id == DELIVER_NORMALISE_EARNINGS_TEXT_V1
    assert normaliser.version == DELIVER_NORMALISE_EARNINGS_TEXT_V1_VERSION
    assert normaliser.carrier_lock_key == "earnings21-original"


# ---------------------------------------------------------------------------
# 2. The rule: byte-identical passthrough, documented hygiene only, refusal
#    on nothing left to deliver (E13).
# ---------------------------------------------------------------------------


def test_plain_transcript_text_is_delivered_byte_identically():
    raw = "the quarter closed strong across every segment"
    outcome = _normaliser()(raw)
    assert isinstance(outcome, DeliveryNormalisation)
    assert outcome.text == raw
    assert outcome.changed is False
    assert outcome.receipt["applied"] is False
    assert outcome.receipt["schema"] == DELIVER_NORMALISER_RECEIPT_SCHEMA
    assert outcome.receipt["normaliser_id"] == DELIVER_NORMALISE_EARNINGS_TEXT_V1
    assert outcome.receipt["carrier_lock_key"] == "earnings21-original"
    assert outcome.receipt["input_sha256"] == outcome.receipt["output_sha256"]


@pytest.mark.parametrize(
    "wrapped, hygiened",
    (
        ("Transcript: revenue grew nine percent", "revenue grew nine percent"),
        ("Answer:  revenue grew nine percent", "revenue grew nine percent"),
        ("FINAL:\nrevenue grew nine percent", "revenue grew nine percent"),
        ("<transcript>revenue grew nine percent</transcript>", "revenue grew nine percent"),
        ("<answer>revenue grew nine percent</answer>", "revenue grew nine percent"),
        ("```\nrevenue grew nine percent\n```", "revenue grew nine percent"),
        ("```text\nrevenue grew nine percent\n```", "revenue grew nine percent"),
        ("  revenue   grew\n\nnine   percent  ", "revenue grew nine percent"),
    ),
)
def test_documented_hygiene_forms_are_stripped(wrapped, hygiened):
    outcome = _normaliser()(wrapped)
    assert outcome.text == hygiened
    assert outcome.changed is True
    assert outcome.receipt["applied"] is True


def test_the_rule_never_touches_content_it_does_not_recognise_as_wrapper():
    # A colon mid-sentence, or tags/fences that do not wrap the WHOLE text,
    # are content, not markup, and must survive untouched (apart from
    # whitespace collapse, which does not fire here either).
    raw = "the CEO said: guidance is unchanged for <transcript> quarter"
    outcome = _normaliser()(raw)
    assert outcome.text == raw
    assert outcome.changed is False


@pytest.mark.parametrize("blank", ("", "   ", "\n\n", "Transcript:", "```\n```", "<answer></answer>"))
def test_nothing_left_after_hygiene_is_refused_not_delivered_blank(blank):
    with pytest.raises(DeliveryNormaliserError, match="empty after hygiene"):
        _normaliser()(blank)


def test_it_is_idempotent_on_its_own_output():
    raw = "Transcript: revenue   grew nine percent"
    once = _normaliser()(raw).text
    twice = _normaliser()(once).text
    assert once == twice


# ---------------------------------------------------------------------------
# 3. The carrier gate: rails.native_episode_config binds this rule to
#    earnings21-original only, before contact -- the same door the SLURP v3
#    rule's own carrier gate is proven through
#    (tests/unit/test_deliver_normaliser_node.py::test_the_loader_refuses_the_wrong_carrier).
# ---------------------------------------------------------------------------


def test_the_loader_accepts_the_earnings_rule_on_the_earnings_carrier():
    values = _episode_values()
    values["carrier_lock_key"] = "earnings21-original"
    values["native_episode"]["deliver_normaliser"] = dict(ARM)
    config = load_native_episode_config(values, _program())
    assert config.deliver_normaliser_id == DELIVER_NORMALISE_EARNINGS_TEXT_V1


def test_the_loader_refuses_the_earnings_rule_on_a_different_carrier():
    values = _episode_values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["deliver_normaliser"] = dict(ARM)
    with pytest.raises(ValueError, match="is defined for carrier"):
        load_native_episode_config(values, _program())
