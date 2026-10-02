"""Reward attribution follows a verified delivery transform, without changing scores."""
import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.reward_links import _trace, RewardLinkError
from speech_aware_evidence_acquisition.rails.delivery_normalisers import EarningsTextDeliveryNormaliser


def fixture(*, runtime=False):
    sample, request_id = "earnings21:fixture", "request-1"
    raw_text = "  Hello world.  "
    normalized = EarningsTextDeliveryNormaliser()(raw_text)
    assert normalized.text != raw_text
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
    request = {"request_id": request_id, "sample_id": sample, "history": []}
    contact_id = "program:solver:" + sample
    if runtime:
        request["history"] = [{"role": "control", "contact_id": contact_id}]
    response = {"text": raw_text, "response_text_sha256": sha(raw_text), "response_sha256": "a" * 64}
    documents = [
        {"channel": "MODEL_REQUEST", "record_id": request_id + "/request",
         "payload": {"payload": request, "payload_sha256": content_hash(request)}},
        {"channel": "MODEL_RESPONSE", "record_id": request_id + "/response", "payload": response}]
    output = {"sample_id": sample, "request_id": request_id, "text": normalized.text,
              "response_text_sha256": sha(normalized.text), "response_sha256": "a" * 64,
              "carrier_lock_key": "earnings21-original",
              "native_episode_receipt": {"deliver_normaliser": normalized.receipt}}
    if runtime:
        documents.append({"channel": "USE", "record_id": sample + "/agent-loop/runtime-use",
                          "payload": {"use_final_response_sha256": sha(normalized.text),
                                      "use_contacts": [{"plan": {"contact_id": contact_id},
                                                        "response_sha256": sha(raw_text)}],
                                      "use_waves": [{"selected_final_contact_id": contact_id}]}})
    bundle = SimpleNamespace(outputs_rows=[output], trace_records={r["record_id"]: r["payload"] for r in documents})
    raw = "\n".join(json.dumps(r) for r in documents).encode()
    return bundle, {sample}, raw


def test_runtime_terminal_can_name_verified_delivered_hash():
    bundle, samples, raw = fixture(runtime=True)
    saved = copy.deepcopy(bundle.outputs_rows)
    events, _ = _trace(bundle, samples, raw)
    assert len(events[next(iter(samples))]) == 3
    assert bundle.outputs_rows == saved


def test_runtime_terminal_rejects_unrelated_final_hash():
    bundle, samples, raw = fixture(runtime=True)
    documents = [json.loads(line) for line in raw.splitlines()]
    documents[-1]["payload"]["use_final_response_sha256"] = "e" * 64
    bundle.trace_records = {r["record_id"]: r["payload"] for r in documents}
    with pytest.raises(RewardLinkError):
        _trace(bundle, samples, "\n".join(json.dumps(r) for r in documents).encode())


def test_replayable_delivery_normalization_retains_final_identity():
    bundle, samples, raw = fixture()
    saved = copy.deepcopy(bundle.outputs_rows)
    events, _ = _trace(bundle, samples, raw)
    assert len(events[next(iter(samples))]) == 2
    assert bundle.outputs_rows == saved


@pytest.mark.parametrize("case", ["missing", "input", "output", "rule", "wire", "text"])
def test_delivery_custody_cannot_be_forged(case):
    bundle, samples, raw = fixture()
    output = bundle.outputs_rows[0]
    receipt = output["native_episode_receipt"]["deliver_normaliser"]
    if case == "missing": output.pop("native_episode_receipt")
    elif case == "wire": output["response_sha256"] = "b" * 64
    elif case == "text": output["text"] = "Changed answer"
    elif case == "rule": receipt["normaliser_id"] = "unregistered"
    else: receipt[case + "_sha256"] = "c" * 64
    with pytest.raises(RewardLinkError):
        _trace(bundle, samples, raw)
