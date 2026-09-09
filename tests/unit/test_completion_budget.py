import base64, hashlib, json, pytest
from speech_aware_evidence_acquisition.analysis.completion_budget import analyze_completion_metadata, compare_request_payload_sets, CompletionBudgetError
def records(finish="stop", text='{"entities":[]}', limit=64):
 raw=json.dumps({"choices":[{"message":{"content":text},"finish_reason":finish}],"usage":{"completion_tokens":limit}}).encode()
 return [{"channel":"MODEL_REQUEST","record_id":"r/a/request","payload":{"arm":"x","payload":{"request_id":"r/a","sample_id":"s","decoding_params":{"max_tokens":limit,"id_slot":"x"}}}},{"channel":"MODEL_RESPONSE","record_id":"r/a/response","payload":{"text":text,"response_text_sha256":hashlib.sha256(text.encode()).hexdigest(),"usage":{"completion_tokens":limit}}},{"channel":"MODEL_WIRE_RESPONSE","record_id":"r/a/wire-response","payload":{"request_id":"r/a","sample_id":"s","response_b64":base64.b64encode(raw).decode(),"response_sha256":hashlib.sha256(raw).hexdigest()}}]
def test_schema_and_cap(): assert analyze_completion_metadata(records("length"))["rows"][0]["actual_length_stop"]
def test_malformed_and_extra_contract(): assert not analyze_completion_metadata(records(text='{"scenario":"x","entities":[]}'))["rows"][0]["entities_only_phase_contract"]
def test_hash_and_duplicate_reject(): 
 r=records(); r[-1]["payload"]["response_sha256"]="0"*64; assert not analyze_completion_metadata(r)["rows"][0]["wire"]["sha256_valid"]; r.append(r[-1]); 
 with pytest.raises(CompletionBudgetError): analyze_completion_metadata(r)
def test_missing_wire_and_payload_difference():
 r=records()[:-1]; assert not analyze_completion_metadata(r)["rows"][0]["wire"]["available"]
 a,b=records()[:1],records()[:1]; b[0]["payload"]["payload"]["arm"]="no"; assert not compare_request_payload_sets(a,b)["payloads_equal_except_allowed"]
