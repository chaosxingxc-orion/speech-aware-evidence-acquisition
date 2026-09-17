"""E2d (SLURP v2 base program M2): the bundle verifier's grouped-Solver
custody form, invariant I7g.

Model-free and offline: no model, tool, network or GPU contact, and no run
directory is read or written. Every fixture here is synthetic.

Background. Under E2/E2b/E2c one Solver visit may make N metered contacts and
deliver a registered, deterministic COMMIT policy's aggregate of the N
structured answers (``rails.commit_policies``,
``reproduction.ojw.native_group_solver``). That delivered text equals none of
the N raw response texts in general, so I7's original reading -- "the row's
text IS one recorded model response's bytes" -- cannot describe such a row.
I7 itself is untouched and still binds every row's ``text`` to its own
``response_text_sha256``; what E2d adds, for a row carrying a ``solver_group``
receipt only, is I7g: the delivered bytes must be RE-DERIVED from that row's
own recorded samples, and those samples must be pinned to real model
responses in the same bundle's trace.
"""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.base import COMMIT_POLICIES
from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _verify_outputs,
    _verify_outputs_trace_binding,
)

# Importing rails.commit_policies is what POPULATES core.base.COMMIT_POLICIES.
from speech_aware_evidence_acquisition.rails import commit_policies as _commit_policies  # noqa: F401
from speech_aware_evidence_acquisition.rails.commit_policies import (
    ParsedSlurpAnswer,
    SolverSampleVote,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

CARRIER = "slurp"
ARM = "speech-feature-query-native-tools"
SAMPLE_ID = "slurp:train:000001:audio-1"
POLICY = "saea-commit-plurality-support-v1"
PARAMS = {"min_support": 2, "similarity_threshold": 0.8}

#: Two "alarm/set" votes against one "alarm/cancel", a two-member
#: "six am"/"six a m" time cluster, and a lone "date" mention only one sample
#: makes. At min_support 2 the committed answer keeps the intent plurality and
#: the time cluster's medoid but DROPS the unsupported date, so the delivered
#: text is an aggregate that equals no single sample's own text -- which is the
#: whole reason a grouped row cannot be held to I7's original reading.
ANSWERS = (
    {
        "scenario": "alarm",
        "action": "set",
        "entities": [
            {"type": "time", "filler": "six am"},
            {"type": "date", "filler": "monday"},
        ],
    },
    {
        "scenario": "alarm",
        "action": "set",
        "entities": [{"type": "time", "filler": "six a m"}],
    },
    {"scenario": "alarm", "action": "cancel", "entities": []},
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sample_text(answer) -> str:
    return json.dumps(answer, ensure_ascii=False, sort_keys=True)


def _render(answer) -> str:
    """``reproduction.ojw.native_group_solver._default_render_answer``'s exact
    rendering -- the bytes the runner writes as a grouped row's ``text``."""

    return json.dumps(
        {
            "scenario": answer.scenario,
            "action": answer.action,
            "entities": [
                {"type": entity.type, "filler": entity.filler}
                for entity in answer.entities
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _grouped_fixture():
    """One grouped outputs row plus the trace its raw samples live in -- the
    exact pair ``core.flight.runtime`` seals for a samples-N Solver visit."""

    texts = [_sample_text(answer) for answer in ANSWERS]
    trace: dict[str, dict[str, object]] = {}
    contacts: list[dict[str, object]] = []
    records: list[dict[str, object]] = []
    votes: list[SolverSampleVote] = []
    for index, (answer, text) in enumerate(zip(ANSWERS, texts, strict=True)):
        request_id = f"flight-{index:04d}"
        contact = {
            "agent_contact_id": f"episode:solver:{index}",
            "request_id": request_id,
            "request_sha256": _sha(f"request-{index}"),
            "response_sha256": _sha(f"envelope-{index}"),
            "response_text_sha256": _sha(text),
        }
        trace[f"{request_id}/request"] = {
            "arm": ARM,
            "payload": {"sample_id": SAMPLE_ID},
            "payload_sha256": contact["request_sha256"],
        }
        trace[f"{request_id}/response"] = {
            "text": text,
            "response_sha256": contact["response_sha256"],
            "response_text_sha256": contact["response_text_sha256"],
        }
        votes.append(
            SolverSampleVote(
                sample_index=index,
                parsed=ParsedSlurpAnswer(
                    scenario=answer["scenario"],
                    action=answer["action"],
                    entities=tuple(
                        SlotEntity(type=entity["type"], filler=entity["filler"])
                        for entity in answer["entities"]
                    ),
                ),
            )
        )
        records.append(
            {
                "sample_index": index,
                "seed": 1249110493 + index,
                "temperature": 0.7,
                "parse_status": "ok",
                "parsed_answer": {
                    "scenario": answer["scenario"],
                    "action": answer["action"],
                    "entities": list(answer["entities"]),
                },
                "contacts": [contact],
            }
        )
        contacts.append(contact)

    outcome = COMMIT_POLICIES.resolve(POLICY)(votes, **PARAMS)
    delivered = _render(outcome.answer)
    last = contacts[-1]
    row = {
        "request_id": last["request_id"],
        "sample_id": SAMPLE_ID,
        "carrier_lock_key": CARRIER,
        "arm": ARM,
        "text": delivered,
        "admitted": True,
        "request_sha256": last["request_sha256"],
        "response_sha256": last["response_sha256"],
        "response_text_sha256": _sha(delivered),
        "solver_group": {
            "commit_policy_id": outcome.policy_id,
            "commit_params": dict(PARAMS),
            "samples": records,
            "delivered": {
                "intent_support": outcome.intent_support,
                "intent_member_sample_indices": list(
                    outcome.intent_member_sample_indices
                ),
                "intent_tie_break_sample_index": outcome.intent_tie_break_sample_index,
                "entities": [
                    {
                        "type": entity.type,
                        "filler": entity.filler,
                        "support": entity.support,
                        "member_sample_indices": list(entity.member_sample_indices),
                        "tie_break_sample_index": entity.tie_break_sample_index,
                    }
                    for entity in outcome.entities
                ],
            },
        },
    }
    return row, trace, texts


def _single_sample_fixture():
    """The samples-1 shape every config before this program produced: one
    contact, and the row's text IS that contact's recorded response text."""

    text = _sample_text(ANSWERS[0])
    request_id = "flight-0000"
    trace = {
        f"{request_id}/request": {
            "arm": ARM,
            "payload": {"sample_id": SAMPLE_ID},
            "payload_sha256": _sha("request-0"),
        },
        f"{request_id}/response": {
            "text": text,
            "response_sha256": _sha("envelope-0"),
            "response_text_sha256": _sha(text),
        },
    }
    row = {
        "request_id": request_id,
        "sample_id": SAMPLE_ID,
        "carrier_lock_key": CARRIER,
        "arm": ARM,
        "text": text,
        "admitted": True,
        "request_sha256": _sha("request-0"),
        "response_sha256": _sha("envelope-0"),
        "response_text_sha256": _sha(text),
    }
    return row, trace


def _verify(row, trace):
    """The two verifier stages ``core.bundle.verify.verify_bundle`` runs over
    an outputs artifact, in its own order."""

    raw = (json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    rows = _verify_outputs(raw, frozenset({row["sample_id"]}), CARRIER, ARM)
    _verify_outputs_trace_binding(rows, trace)
    return rows


def test_grouped_row_verifies_when_the_delivered_text_is_the_recomputation():
    """(a) The legitimate flow: a grouped row whose delivered text is exactly
    what its own recorded samples re-commit to."""

    row, trace, texts = _grouped_fixture()

    # The premise this whole invariant exists for: the delivered text is an
    # aggregate and equals NONE of the raw sample texts, so I7's original
    # "text is one model response's bytes" reading could never hold for it.
    assert row["text"] not in texts
    # ...while I7 itself still holds, because the runner hashes the DELIVERED
    # bytes for a grouped row (E2d).
    assert row["response_text_sha256"] == _sha(row["text"])

    rows = _verify(row, trace)
    assert len(rows) == 1
    assert rows[0]["solver_group"]["commit_policy_id"] == POLICY


def test_grouped_row_with_a_mutated_delivered_text_is_refused_with_i7g():
    """(b) The forgery I7 used to catch and could not catch here: a delivered
    text rewritten after the fact, with its row hash recomputed to match so
    that I7 itself is satisfied."""

    row, trace, _texts = _grouped_fixture()
    forged = json.loads(row["text"])
    forged["action"] = "cancel"
    row["text"] = json.dumps(forged, ensure_ascii=False, sort_keys=True)
    row["response_text_sha256"] = _sha(row["text"])

    with pytest.raises(BundleError) as error:
        _verify(row, trace)
    message = str(error.value)
    assert "I7g" in message
    assert "is not what commit policy" in message
    assert "first difference at character offset" in message


def test_grouped_row_keeps_i7_when_its_own_text_hash_is_stale():
    """I7 is untouched for a grouped row: mutate the delivered text WITHOUT
    recomputing its hash and the original invariant refuses it first."""

    row, trace, _texts = _grouped_fixture()
    row["text"] = row["text"] + " "

    with pytest.raises(BundleError, match=r"\(I7\)"):
        _verify(row, trace)


def test_grouped_row_is_refused_when_a_sample_hash_does_not_match_the_trace():
    """(c) The raw samples are custody, not decoration: a sample whose
    recorded response_text_sha256 is not the trace's own model response bytes
    is refused even though the commit recomputation still reproduces."""

    row, trace, _texts = _grouped_fixture()
    # The MIDDLE sample, so the row's own transport identity (its group's LAST
    # contact) is untouched and this can only fail on the sample binding.
    row["solver_group"]["samples"][1]["contacts"][0]["response_text_sha256"] = _sha(
        "some other response"
    )

    with pytest.raises(BundleError) as error:
        _verify(row, trace)
    message = str(error.value)
    assert "I7g" in message
    assert "does not match the trace" in message


def test_grouped_row_is_refused_when_a_sample_contact_is_missing_from_the_trace():
    """The same custody, from the other side: dropping a raw sample's trace
    records (self-consistently, as a forger would) is refused."""

    row, trace, _texts = _grouped_fixture()
    del trace["flight-0001/response"]

    with pytest.raises(BundleError) as error:
        _verify(row, trace)
    assert "I7g" in str(error.value)
    assert "must stay in the trace" in str(error.value)


def test_grouped_row_is_refused_when_its_commit_policy_is_not_registered():
    """(d) Only a policy registered in ``core.base.COMMIT_POLICIES`` can make
    a delivered aggregate custody; an unregistered id cannot be re-run."""

    row, trace, _texts = _grouped_fixture()
    row["solver_group"]["commit_policy_id"] = "saea-commit-not-registered-v1"

    with pytest.raises(BundleError) as error:
        _verify(row, trace)
    message = str(error.value)
    assert "I7g" in message
    assert "is not registered in core.base.COMMIT_POLICIES" in message


def test_grouped_row_is_refused_without_the_commit_parameters():
    """E2d's runner requirement, enforced: a grouped receipt that does not
    record the parameters its policy was applied with cannot be re-derived
    from the bundle alone, and a bundle carries no composed configuration to
    recover them from."""

    row, trace, _texts = _grouped_fixture()
    del row["solver_group"]["commit_params"]

    with pytest.raises(BundleError) as error:
        _verify(row, trace)
    message = str(error.value)
    assert "I7g" in message
    assert "commit_params" in message


def test_grouped_row_is_refused_when_its_transport_identity_is_not_its_last_sample():
    """A grouped row's delivered text is an aggregate, but its request/response
    identity is still ONE real contact: the group's last sample."""

    row, trace, _texts = _grouped_fixture()
    row["request_id"] = "flight-0000"
    row["request_sha256"] = _sha("request-0")
    row["response_sha256"] = _sha("envelope-0")

    with pytest.raises(BundleError) as error:
        _verify(row, trace)
    assert "I7g" in str(error.value)
    assert "LAST raw sample contact" in str(error.value)


def test_pre_e2d_grouped_row_shape_is_refused_by_i7():
    """The exact defect that failed cell B2 v3's four-row smoke: the pre-E2d
    runner sealed a grouped row whose ``response_text_sha256`` was the LAST
    RAW sample's text hash while ``text`` was the committed aggregate."""

    row, trace, texts = _grouped_fixture()
    row["response_text_sha256"] = _sha(texts[-1])

    with pytest.raises(BundleError) as error:
        _verify(row, trace)
    message = str(error.value)
    assert "(I7)" in message
    assert "does not match its recorded response_text_sha256" in message


def test_single_sample_row_still_verifies_and_a_mutated_one_is_refused_with_i7():
    """(e) Every row without a ``solver_group`` receipt is exactly as it was:
    it verifies against its one recorded response, and a mutated text is
    refused by I7, never by I7g."""

    row, trace = _single_sample_fixture()
    rows = _verify(row, trace)
    assert len(rows) == 1
    assert "solver_group" not in rows[0]

    mutated = copy.deepcopy(row)
    mutated["text"] = mutated["text"] + " "
    with pytest.raises(BundleError) as error:
        _verify(mutated, trace)
    message = str(error.value)
    assert "(I7)" in message
    assert "I7g" not in message

    # ...and a mutated text whose own hash was recomputed (so I7 passes) is
    # still refused, by the outputs<->trace binding I7 has always had.
    forged = copy.deepcopy(row)
    forged["text"] = forged["text"] + " "
    forged["response_text_sha256"] = _sha(forged["text"])
    with pytest.raises(BundleError) as error:
        _verify(forged, trace)
    assert "disagrees with the trace record" in str(error.value)
