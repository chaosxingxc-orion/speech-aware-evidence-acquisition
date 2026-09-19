"""E11 (owner directive 26, 2026-09-18): the bundle verifier's delivery-time
normalisation custody form, invariant I7n.

Model-free and offline: no model, tool, network or GPU contact, and no run
directory is read or written. Every fixture here is synthetic and the real
TRAIN-mined legal intent inventory is replaced by a three-scenario one.

Background. The delivery node rewrites the accepted answer immediately before
delivery, so a normalised row's ``text`` is a deterministic function of the
recorded model response rather than its bytes -- exactly the situation E2d
met one step earlier with the grouped Solver's COMMIT policy. I7 itself is
untouched and still binds every row's ``text`` to its own
``response_text_sha256``; what I7n adds, for a row carrying a
``native_episode_receipt.deliver_normaliser`` block only, is strictly
STRONGER custody: the trace's own response bytes must be the rule's recorded
input, the rule must be registered and deterministic, and re-running it must
reproduce the delivered bytes byte for byte.
"""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS
from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    DELIVER_NORMALISER_INVARIANT,
    _verify_outputs,
    _verify_outputs_trace_binding,
)

# Importing rails.delivery_normalisers is what POPULATES
# core.base.DELIVERY_NORMALISERS.
from speech_aware_evidence_acquisition.rails import (  # noqa: F401
    delivery_normalisers as _delivery_normalisers,
)
from speech_aware_evidence_acquisition.rails import slurp_projection_v3 as v3
from speech_aware_evidence_acquisition.rails.delivery_normalisers import (
    DELIVER_NORMALISE_V3,
    DELIVER_NORMALISER_RECEIPT_SCHEMA,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import (
    legal_intent_inventory,
)

CARRIER = "slurp"
ARM = "speech-feature-query-native-tools"
SAMPLE_ID = "slurp:train:000001:audio-1"
REQUEST_ID = "flight-0000"

INVENTORY = legal_intent_inventory(
    {
        "music": ("likeness", "dislikeness", "play", "query", "settings"),
        "play": ("audiobook", "game", "music", "podcasts", "radio"),
        "alarm": ("set", "remove", "query"),
    }
)

#: The accepted Solver answer: an ILLEGAL (music, play_music) pair with an
#: unnormalised time filler, so the node changes BOTH halves and the
#: delivered bytes equal no model response's own.
RAW_ANSWER = json.dumps(
    {
        "scenario": "music",
        "action": "play_music",
        "entities": [{"type": "time", "filler": "6:30AM"}],
    },
    ensure_ascii=False,
    sort_keys=True,
)


@pytest.fixture(autouse=True)
def _synthetic_inventory(monkeypatch):
    monkeypatch.setattr(v3, "_default_legal_intent_inventory", lambda: INVENTORY)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalised_fixture():
    """One normalised outputs row plus the trace its accepted answer lives in
    -- the exact pair ``core.flight.runtime`` seals for an armed delivery
    node."""

    outcome = DELIVERY_NORMALISERS.resolve(DELIVER_NORMALISE_V3)(RAW_ANSWER)
    assert outcome.changed is True
    delivered = outcome.text
    envelope = _sha("envelope-0")
    request_sha256 = _sha("request-0")
    trace = {
        f"{REQUEST_ID}/request": {
            "arm": ARM,
            "payload": {"sample_id": SAMPLE_ID},
            "payload_sha256": request_sha256,
        },
        f"{REQUEST_ID}/response": {
            "text": RAW_ANSWER,
            "response_sha256": envelope,
            "response_text_sha256": _sha(RAW_ANSWER),
        },
    }
    row = {
        "request_id": REQUEST_ID,
        "sample_id": SAMPLE_ID,
        "carrier_lock_key": CARRIER,
        "arm": ARM,
        "text": delivered,
        "admitted": True,
        "request_sha256": request_sha256,
        "response_sha256": envelope,
        "response_text_sha256": _sha(delivered),
        "native_episode_receipt": {
            "role_visits": [{"stage": "solver"}],
            "planner_routes": [{"action": "ACCEPT"}],
            "deliver_normaliser": dict(outcome.receipt),
        },
    }
    return row, trace, delivered


def _ordinary_fixture():
    """A row whose episode ran no delivery node: its text IS the recorded
    response's bytes, and nothing about it changes under E11."""

    envelope = _sha("envelope-0")
    request_sha256 = _sha("request-0")
    trace = {
        f"{REQUEST_ID}/request": {
            "arm": ARM,
            "payload": {"sample_id": SAMPLE_ID},
            "payload_sha256": request_sha256,
        },
        f"{REQUEST_ID}/response": {
            "text": RAW_ANSWER,
            "response_sha256": envelope,
            "response_text_sha256": _sha(RAW_ANSWER),
        },
    }
    row = {
        "request_id": REQUEST_ID,
        "sample_id": SAMPLE_ID,
        "carrier_lock_key": CARRIER,
        "arm": ARM,
        "text": RAW_ANSWER,
        "admitted": True,
        "request_sha256": request_sha256,
        "response_sha256": envelope,
        "response_text_sha256": _sha(RAW_ANSWER),
        "native_episode_receipt": {"role_visits": [{"stage": "solver"}]},
    }
    return row, trace


def _verify(row, trace):
    """The two verifier stages ``core.bundle.verify.verify_bundle`` runs over
    an outputs artifact, in its own order."""

    raw = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    rows = _verify_outputs(raw, frozenset({row["sample_id"]}), CARRIER, ARM)
    _verify_outputs_trace_binding(rows, trace)
    return rows


def test_a_normalised_row_verifies_when_its_text_is_the_recomputation():
    row, trace, delivered = _normalised_fixture()

    # The premise the invariant exists for: the delivered text is the rule's
    # output and is NOT the recorded model response's bytes, so I7's original
    # "text is one model response's bytes" reading could never hold for it.
    assert delivered != RAW_ANSWER
    # ...while I7 itself still holds, because the runner hashes the DELIVERED
    # bytes for a normalised row (the same move E2d makes for a grouped one).
    assert row["response_text_sha256"] == _sha(delivered)
    assert row["native_episode_receipt"]["deliver_normaliser"]["schema"] == (
        DELIVER_NORMALISER_RECEIPT_SCHEMA
    )

    assert _verify(row, trace)[0]["text"] == delivered


def test_an_ordinary_row_is_untouched_by_the_new_invariant():
    row, trace = _ordinary_fixture()
    assert _verify(row, trace)[0]["text"] == RAW_ANSWER

    # ...and still owes I7's full three-field binding: a delivered text that
    # is not the recorded response's is refused exactly as before E11.
    tampered = copy.deepcopy(row)
    tampered["text"] = RAW_ANSWER.replace("6:30AM", "six thirty am")
    tampered["response_text_sha256"] = _sha(tampered["text"])
    with pytest.raises(BundleError, match="disagrees with the trace"):
        _verify(tampered, trace)


def test_a_normalised_row_is_refused_when_the_text_is_not_the_recomputation():
    row, trace, delivered = _normalised_fixture()
    tampered = copy.deepcopy(row)
    hand_edited = delivered.replace("six thirty am", "seven thirty am")
    assert hand_edited != delivered
    tampered["text"] = hand_edited
    tampered["response_text_sha256"] = _sha(hand_edited)
    tampered["native_episode_receipt"]["deliver_normaliser"]["output_sha256"] = _sha(
        hand_edited
    )
    with pytest.raises(BundleError) as error:
        _verify(tampered, trace)
    message = str(error.value)
    assert DELIVER_NORMALISER_INVARIANT in message
    assert "first difference at character offset" in message
    # The refusal names WHERE, never the text.
    assert "seven thirty am" not in message
    assert "six thirty am" not in message


def test_a_normalised_row_is_refused_when_the_rule_did_not_run_on_the_response():
    row, trace, _delivered = _normalised_fixture()
    tampered = copy.deepcopy(row)
    tampered["native_episode_receipt"]["deliver_normaliser"]["input_sha256"] = _sha(
        "some other answer"
    )
    with pytest.raises(BundleError, match="ran on the recorded model response"):
        _verify(tampered, trace)


def test_a_normalised_row_is_refused_when_the_rule_is_not_registered():
    row, trace, _delivered = _normalised_fixture()
    tampered = copy.deepcopy(row)
    tampered["native_episode_receipt"]["deliver_normaliser"]["normaliser_id"] = (
        "saea-deliver-normalise-v99"
    )
    with pytest.raises(BundleError, match="is not registered"):
        _verify(tampered, trace)


def test_a_normalised_row_is_refused_without_the_digests_it_is_re_derived_from():
    row, trace, _delivered = _normalised_fixture()
    tampered = copy.deepcopy(row)
    del tampered["native_episode_receipt"]["deliver_normaliser"]["input_sha256"]
    with pytest.raises(BundleError, match="is missing"):
        _verify(tampered, trace)


def test_a_normalised_row_is_refused_when_its_output_digest_is_not_its_text():
    row, trace, _delivered = _normalised_fixture()
    tampered = copy.deepcopy(row)
    tampered["native_episode_receipt"]["deliver_normaliser"]["output_sha256"] = _sha(
        "something else"
    )
    with pytest.raises(BundleError, match="output digest"):
        _verify(tampered, trace)


def test_a_grouped_row_may_not_also_be_normalised():
    row, trace, _delivered = _normalised_fixture()
    tampered = copy.deepcopy(row)
    tampered["solver_group"] = {"commit_policy_id": "saea-commit-plurality-support-v1"}
    with pytest.raises(BundleError, match="cannot also carry a delivery"):
        _verify(tampered, trace)


def test_a_malformed_receipt_block_is_refused_by_name():
    row, trace, _delivered = _normalised_fixture()
    tampered = copy.deepcopy(row)
    tampered["native_episode_receipt"]["deliver_normaliser"] = "saea-deliver-normalise-v3"
    with pytest.raises(BundleError, match="must be a JSON object"):
        _verify(tampered, trace)
