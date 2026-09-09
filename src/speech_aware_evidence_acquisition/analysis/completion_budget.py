"""Pure metadata analysis for bounded completion-budget reads."""
from __future__ import annotations
import base64, hashlib, json
from collections.abc import Mapping, Sequence
from typing import Any

class CompletionBudgetError(ValueError): pass

def _records_by_channel(records: Sequence[Mapping[str, Any]], channel: str) -> list[Mapping[str, Any]]:
    return [record for record in records if record.get("channel") == channel]

def _request_id(record: Mapping[str, Any], suffix: str) -> str:
    value = record.get("record_id")
    if not isinstance(value, str) or not value.endswith(suffix):
        raise CompletionBudgetError("record_id has an unexpected suffix")
    return value[:-len(suffix)]

def _entities(value: object) -> bool:
    return isinstance(value, Mapping) and "entities" in value

def _wire(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = ("request_id", "sample_id", "response_b64", "response_sha256")
    if any(not isinstance(payload.get(key), str) for key in required):
        raise CompletionBudgetError("wire response is malformed")
    try:
        raw = base64.b64decode(payload["response_b64"], validate=True)
    except Exception as error:
        raise CompletionBudgetError("wire response has invalid base64") from error
    digest = hashlib.sha256(raw).hexdigest()
    valid = digest == payload["response_sha256"]
    result: dict[str, Any] = {"available": True, "sha256_valid": valid, "sha256": digest, "length": len(raw)}
    try:
        decoded = json.loads(raw.decode("utf-8"))
        result["raw_json_valid"] = True
    except (UnicodeDecodeError, json.JSONDecodeError):
        result["raw_json_valid"] = False
        return result
    choice = decoded.get("choices", [None])[0] if isinstance(decoded, Mapping) else None
    if not isinstance(choice, Mapping):
        result["raw_json_valid"] = False
        return result
    message = choice.get("message")
    content = message.get("content") if isinstance(message, Mapping) else None
    result["finish_reason"] = choice.get("finish_reason")
    result["content_sha256"] = hashlib.sha256(content.encode()).hexdigest() if isinstance(content, str) else None
    result["content_length"] = len(content) if isinstance(content, str) else None
    result["usage"] = decoded.get("usage") if isinstance(decoded.get("usage"), Mapping) else None
    return result

def analyze_completion_metadata(records: Sequence[Mapping[str, Any]], outputs: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    requests: dict[str, Mapping[str, Any]] = {}
    responses: dict[str, Mapping[str, Any]] = {}
    wires: dict[str, Mapping[str, Any]] = {}
    for record in records:
        channel = record.get("channel")
        payload = record.get("payload")
        if not isinstance(payload, Mapping): continue
        if channel == "MODEL_REQUEST":
            outer = payload.get("payload")
            if not isinstance(outer, Mapping): raise CompletionBudgetError("MODEL_REQUEST lacks nested request payload")
            rid = outer.get("request_id")
            if not isinstance(rid, str) or rid in requests: raise CompletionBudgetError("duplicate or invalid request id")
            requests[rid] = outer
        elif channel == "MODEL_RESPONSE":
            rid = _request_id(record, "/response")
            if rid in responses: raise CompletionBudgetError("duplicate response id")
            responses[rid] = payload
        elif channel == "MODEL_WIRE_RESPONSE":
            rid = payload.get("request_id")
            if not isinstance(rid, str) or rid in wires: raise CompletionBudgetError("duplicate or invalid wire id")
            wires[rid] = payload
    rows=[]
    for rid, request in requests.items():
        sample_id=request.get("sample_id")
        if not isinstance(sample_id,str): raise CompletionBudgetError("request lacks sample_id")
        response=responses.get(rid)
        if response is None: raise CompletionBudgetError("request lacks normalized response")
        if any(row.get("sample_id")==sample_id for row in rows): raise CompletionBudgetError("duplicate sample id")
        decoded=request.get("decoding_params")
        limit=decoded.get("max_tokens") if isinstance(decoded,Mapping) else None
        if isinstance(limit,bool) or not isinstance(limit,int) or limit<=0: raise CompletionBudgetError("request lacks positive max_tokens")
        w = _wire(wires[rid]) if rid in wires else {"available":False}
        if w.get("available") and wires[rid].get("sample_id") != sample_id: raise CompletionBudgetError("wire sample mismatch")
        normalized=response.get("text")
        if not isinstance(normalized,str): raise CompletionBudgetError("response lacks text")
        normalized_sha=hashlib.sha256(normalized.encode()).hexdigest()
        if response.get("response_text_sha256") not in (None, normalized_sha): raise CompletionBudgetError("normalized text hash mismatch")
        usage=response.get("usage") if isinstance(response.get("usage"),Mapping) else {}
        completion=usage.get("completion_tokens")
        at_cap=isinstance(completion,int) and completion==limit
        if w.get("available") and w.get("content_sha256") is not None and w["content_sha256"] != normalized_sha: w["content_matches_normalized"]=False
        elif w.get("available"): w["content_matches_normalized"]=True
        raw_json=None
        try: raw_json=json.loads(normalized)
        except json.JSONDecodeError: pass
        entities=_entities(raw_json)
        strict=isinstance(raw_json,Mapping) and set(raw_json)=={"entities"}
        finish=w.get("finish_reason") if w.get("available") else None
        metadata_finish=wires[rid].get("finish_reason") if rid in wires else None
        if metadata_finish is not None and metadata_finish != finish: raise CompletionBudgetError("wire finish metadata mismatch")
        rows.append({"request_id":rid,"sample_id":sample_id,"max_tokens":limit,"completion_tokens":completion,"at_cap":at_cap,"actual_length_stop": finish=="length","wire":w,"normalized_text_sha256":normalized_sha,"normalized_text_length":len(normalized),"normalized_json_valid":raw_json is not None,"entities_present":entities,"entities_only_phase_contract":strict,"cached_tokens":usage.get("cached_tokens"),"timings":usage.get("timings")})
    return {"rows":rows,"output_rows":len(outputs)}

def compare_request_payload_sets(left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def extract(records):
        result={}
        for r in _records_by_channel(records,"MODEL_REQUEST"):
            p=r.get("payload",{}); p=p.get("payload") if isinstance(p,Mapping) else None
            if not isinstance(p,Mapping) or not isinstance(p.get("sample_id"),str): raise CompletionBudgetError("invalid request")
            sid=p["sample_id"]
            if sid in result: raise CompletionBudgetError("duplicate sample id")
            result[sid]=p
        return result
    a,b=extract(left),extract(right)
    if set(a)!=set(b): return {"payloads_equal_except_allowed":False}
    for sid in a:
        def clean(x):
            y=json.loads(json.dumps(x)); y.pop("request_id",None)
            d=y.get("decoding_params",{})
            if isinstance(d,dict):
                d.pop("id_slot",None); d.pop("max_tokens",None)
            return y
        if clean(a[sid]) != clean(b[sid]): return {"payloads_equal_except_allowed":False}
    return {"payloads_equal_except_allowed":True}
