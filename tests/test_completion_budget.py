import base64, hashlib, json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
from analysis.completion_budget import analyze_completion_metadata, compare_request_payload_sets

def wire(obj, digest=True):
    raw=json.dumps(obj,separators=(",",":")).encode(); b=base64.b64encode(raw).decode()
    return {"channel":"MODEL_WIRE_RESPONSE","payload":{"request_id":"r1","sample_id":"s1","response_b64":b,"response_sha256":hashlib.sha256(raw).hexdigest() if digest else "0"*64}}
def records(finish="stop", raw=True):
    text='{"scenario":"x","action":"y","entities":[]}'
    rs=[{"channel":"MODEL_REQUEST","payload":{"request_id":"r1","sample_id":"s1","max_tokens":64,"decoding_params":{"id_slot":"a","temperature":0}}}, {"channel":"MODEL_RESPONSE","record_id":"r1/response","payload":{"text":text,"usage":{"completion_tokens":64}}}]
    if raw: rs.append(wire({"choices":[{"message":{"content":text},"finish_reason":finish}],"usage":{"completion_tokens":64}}))
    return rs
def test_length_stop_and_json_schema():
    row=analyze_completion_metadata(records("length"),max_tokens=64)["rows"][0]
    assert row["at_cap"] is True and row["actual_length_stop"] is True
    assert row["delivered_strict_json_valid"] and row["delivered_entities_schema_valid"]
def test_missing_wire_is_unavailable():
    row=analyze_completion_metadata(records(raw=False),max_tokens=64)["rows"][0]
    assert row["at_cap"] is True and row["actual_length_stop"] is None and row["wire"]["available"] is False
def test_malformed_json_and_hash_mismatch_are_flagged():
    rs=records(); rs[-1]=wire({"choices":[{"finish_reason":"stop"}]},False); rs[-1]["payload"]["response_b64"]=base64.b64encode(b"{").decode()
    row=analyze_completion_metadata(rs)["rows"][0]
    assert row["wire"]["sha256_valid"] is False and row["wire"]["raw_json_valid"] is False
def test_only_allowed_request_changes_pass():
    a=records(raw=False); b=records(raw=False); b[0]["payload"]["max_tokens"]=256; b[0]["payload"]["decoding_params"]["id_slot"]="b"
    assert compare_request_payload_sets(a,b)["payloads_equal_except_allowed"]
    b[0]["payload"]["temperature"]=1
    assert not compare_request_payload_sets(a,b)["payloads_equal_except_allowed"]
