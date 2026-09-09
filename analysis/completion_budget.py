"""Pure, model-free completion metadata readout."""
from __future__ import annotations
import base64, hashlib, json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

def _p(r):
    v=r.get("payload",r); return v if isinstance(v,Mapping) else {}
def _ids(r):
    p=_p(r); rid=p.get("request_id") or str(r.get("record_id","" )).split("/",1)[0]
    return (str(rid) if rid else None, str(p["sample_id"]) if p.get("sample_id") is not None else None)
def _wire(r):
    p=_p(r); b=p.get("response_b64",p.get("wire_response_b64",p.get("raw_base64"))); d=p.get("response_sha256",p.get("wire_response_sha256",p.get("raw_sha256")))
    out={"available":b is not None,"sha256_valid":None,"raw_json_valid":None,"raw_json_error":None}
    if b is None:return out
    try: raw=base64.b64decode(b,validate=True)
    except Exception as e: out.update(sha256_valid=False,raw_json_error=f"invalid base64: {e}"); return out
    out["sha256"]=hashlib.sha256(raw).hexdigest(); out["sha256_valid"]=isinstance(d,str) and out["sha256"]==d
    try:
        x=json.loads(raw.decode()); out.update(raw_json_valid=True)
        c=x.get("choices") if isinstance(x,Mapping) else None; c=c[0] if isinstance(c,list) and c and isinstance(c[0],Mapping) else {}
        out["finish_reason"]=c.get("finish_reason"); m=c.get("message"); out["text"]=m.get("content") if isinstance(m,Mapping) else c.get("text"); out["usage"]=x.get("usage") if isinstance(x,Mapping) else None
    except Exception as e: out.update(raw_json_valid=False,raw_json_error=str(e))
    return out
def _entities(v):
    return isinstance(v,Mapping) and isinstance(v.get("entities",[]),list) and all(isinstance(e,Mapping) and isinstance(e.get("type"),str) and isinstance(e.get("filler"),str) for e in v["entities"])
def analyze_completion_metadata(records:Iterable[Mapping[str,Any]],*,max_tokens:int|None=None,parse_slu:bool=False)->dict[str,Any]:
    groups=defaultdict(list)
    for r in records:
        if r.get("channel") in {"MODEL_REQUEST","MODEL_RESPONSE","MODEL_WIRE_RESPONSE"}:
            rid,sid=_ids(r)
            if rid: groups[rid].append(r)
    rows=[]
    for rid, rs in sorted(groups.items()):
        ch=defaultdict(list)
        for r in rs: ch[r["channel"]].append(r)
        req=_p(ch["MODEL_REQUEST"][0]) if ch["MODEL_REQUEST"] else {}; resp=_p(ch["MODEL_RESPONSE"][0]) if ch["MODEL_RESPONSE"] else {}; sid=req.get("sample_id") or next((_p(r).get("sample_id") for r in rs if _p(r).get("sample_id") is not None),None)
        w=_wire(ch["MODEL_WIRE_RESPONSE"][0]) if ch["MODEL_WIRE_RESPONSE"] else {"available":False,"sha256_valid":None,"raw_json_valid":None,"raw_json_error":None}
        u=resp.get("usage") if isinstance(resp.get("usage"),Mapping) else {}; ct=u.get("completion_tokens"); text=resp.get("text")
        row={"request_id":rid,"sample_id":sid,"request_available":bool(req),"response_available":bool(resp),"wire":w,"completion_tokens":ct,"usage":u,"at_cap":max_tokens is not None and ct==max_tokens,"actual_length_stop":w.get("finish_reason")=="length" if w.get("raw_json_valid") else None,"stop_reason":w.get("finish_reason") if w.get("available") else None,"delivered_text_sha256":hashlib.sha256(text.encode()).hexdigest() if isinstance(text,str) else None}
        try: val=json.loads(text); row.update(delivered_strict_json_valid=True,delivered_entities_schema_valid=_entities(val))
        except Exception: row.update(delivered_strict_json_valid=False if isinstance(text,str) else None,delivered_entities_schema_valid=False if isinstance(text,str) else None)
        row["duplicate_channels"]={k:len(v) for k,v in ch.items() if len(v)>1}; row["parse_slu_response_valid"]=None
        if parse_slu and isinstance(text,str):
            from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response
            row["parse_slu_response_valid"]=parse_slu_response(text)[3]
        rows.append(row)
    return {"rows":rows,"row_count":len(rows),"duplicate_request_groups":[r["request_id"] for r in rows if r["duplicate_channels"]]}
def compare_request_payload_sets(left:Iterable[Mapping[str,Any]],right:Iterable[Mapping[str,Any]])->dict[str,Any]:
    def c(rs):
        out={}
        for r in rs:
            if r.get("channel")!="MODEL_REQUEST":continue
            rid,sid=_ids(r); key=sid or rid
            if not key or key in out: raise ValueError(f"duplicate or missing sample id: {key!r}")
            out[key]=dict(_p(r))
        return out
    a,b=c(left),c(right)
    if set(a)!=set(b): return {"equal_sample_set":False,"payloads_equal_except_allowed":False,"missing_left":sorted(set(b)-set(a)),"missing_right":sorted(set(a)-set(b))}
    mm={}
    for rid in sorted(a):
        x,y=dict(a[rid]),dict(b[rid]); x.pop("request_id",None); y.pop("request_id",None); x.pop("max_tokens",None); y.pop("max_tokens",None)
        for key in set(x)|set(y):
            xv,yv=x.get(key),y.get(key)
            if key=="decoding_params" and isinstance(xv,Mapping) and isinstance(yv,Mapping): xv,yv={k:v for k,v in xv.items() if k!="id_slot"},{k:v for k,v in yv.items() if k!="id_slot"}
            if xv!=yv:mm[rid]={"key":key,"left":xv,"right":yv}
    return {"equal_sample_set":True,"payloads_equal_except_allowed":not mm,"mismatches":mm}
