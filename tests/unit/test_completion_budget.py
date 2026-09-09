"""Validate readout against the actual nested trace envelope."""
import base64
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.analysis.completion_budget import (
    CompletionBudgetError, analyze_completion_metadata, compare_request_payload_sets,
)


def fixture(*, text='{"entities":[]}', finish="stop", cap=64, tokens=20):
    usage = {"completion_tokens": tokens, "prompt_tokens": 100}
    document = {"choices": [{"message": {"content": text}, "finish_reason": finish}],
                "usage": {**usage, "prompt_tokens_details": {"cached_tokens": 99}},
                "timings": {"cache_n": 99, "prompt_n": 1}}
    raw = json.dumps(document).encode()
    digest = hashlib.sha256(text.encode()).hexdigest()
    rows = [
        {"channel": "MODEL_REQUEST", "record_id": "r/a/request",
         "payload": {"arm": "speech-feature-query", "payload": {
             "request_id": "r/a", "sample_id": "s", "decoding_params": {
                 "max_tokens": cap, "id_slot": 0, "temperature": 0}, "history": []}}},
        {"channel": "MODEL_RESPONSE", "record_id": "r/a/response",
         "payload": {"text": text, "response_text_sha256": digest, "usage": usage}},
        {"channel": "MODEL_WIRE_RESPONSE", "record_id": "r/a/wire-response",
         "payload": {"request_id": "r/a", "sample_id": "s", "finish_reason": finish,
                     "response_b64": base64.b64encode(raw).decode(),
                     "response_sha256": hashlib.sha256(raw).hexdigest()}},
    ]
    outputs = [{"request_id": "r/a", "sample_id": "s", "text": text,
                "response_text_sha256": digest}]
    return rows, outputs


def test_stop_at_cap_is_not_length_stop_and_cache_is_raw_metadata():
    rows, outputs = fixture(tokens=64)
    result = analyze_completion_metadata(rows, outputs)["rows"][0]
    assert result["request_id"] == "r/a"
    assert result["at_cap"] and result["actual_length_stop"] is False
    assert result["wire"]["cached_tokens"] == 99
    assert result["wire"]["timings"]["prompt_n"] == 1
    assert result["normalized"]["entities_only_phase_contract"]


def test_length_stop_preserves_invalid_text_and_delivery_is_separate():
    rows, outputs = fixture(text='{"entities":[', finish="length", tokens=64)
    outputs[0]["text"] = '{"entities":[]}'
    outputs[0]["response_text_sha256"] = hashlib.sha256(outputs[0]["text"].encode()).hexdigest()
    result = analyze_completion_metadata(rows, outputs)["rows"][0]
    assert result["actual_length_stop"] and result["raw_matches_normalized"]
    assert not result["wire"]["text"]["json_syntax_valid"]
    assert result["delivered"]["entities_only_phase_contract"]
    assert result["normalized_matches_delivered"] is False


@pytest.mark.parametrize("text", ['{}', '{"entities":{}}', '{"entities":[{}]}',
                                  '{"scenario":"iot","action":"off","entities":[]}'])
def test_phase_contract_is_stricter_than_json_syntax(text):
    result = analyze_completion_metadata(fixture(text=text)[0])["rows"][0]
    assert result["normalized"]["json_syntax_valid"]
    assert not result["normalized"]["entities_only_phase_contract"]


def test_missing_wire_keeps_stop_unavailable():
    rows, _ = fixture(tokens=64)
    result = analyze_completion_metadata(rows[:-1])["rows"][0]
    assert result["at_cap"] and result["actual_length_stop"] is None


@pytest.mark.parametrize("change", ["hash", "base64", "duplicate", "finish", "sample", "usage", "output"])
def test_inconsistent_sources_are_rejected(change):
    rows, outputs = fixture()
    if change == "hash": rows[-1]["payload"]["response_sha256"] = "0" * 64
    if change == "base64": rows[-1]["payload"]["response_b64"] = "???"
    if change == "duplicate": rows.append(rows[-1])
    if change == "finish": rows[-1]["payload"]["finish_reason"] = "length"
    if change == "sample": rows[-1]["payload"]["sample_id"] = "other"
    if change == "usage": rows[1]["payload"]["usage"]["completion_tokens"] = 21
    if change == "output": outputs[0]["response_text_sha256"] = "0" * 64
    with pytest.raises(CompletionBudgetError):
        analyze_completion_metadata(rows, outputs)


def test_malformed_wire_remains_hash_addressable():
    rows, _ = fixture()
    raw = b"{"
    rows[-1]["payload"]["response_b64"] = base64.b64encode(raw).decode()
    rows[-1]["payload"]["response_sha256"] = hashlib.sha256(raw).hexdigest()
    result = analyze_completion_metadata(rows)["rows"][0]
    assert not result["wire"]["response_json_valid"]
    assert result["wire"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["actual_length_stop"] is None


def test_pair_allows_only_registered_differences():
    left, _ = fixture()
    right, _ = fixture(cap=256)
    right[0]["payload"]["payload"]["decoding_params"]["id_slot"] = 3
    assert compare_request_payload_sets(left, right)["sample_count"] == 1
    right[0]["payload"]["payload"]["history"] = ["changed prompt"]
    with pytest.raises(CompletionBudgetError, match="unregistered"):
        compare_request_payload_sets(left, right)
