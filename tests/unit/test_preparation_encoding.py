import hashlib
from dataclasses import dataclass
import pytest
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_encoding import encode_window_feature_cache
from speech_aware_evidence_acquisition.core.preparation_windows import WINDOW_FEATURE_INVENTORY_SCHEMA

SHA = "a" * 64

def inventory(tmp_path, duplicate=False):
    data = tmp_path / "data"; data.mkdir(); media = data / "slices" / "one.wav"; media.parent.mkdir(); media.write_bytes(b"synthetic pcm")
    audio = hashlib.sha256(media.read_bytes()).hexdigest()
    source = {"sample_id":"s","parent_media_relpath":"parent.wav","parent_sha256":SHA,"start_seconds":0.0,"end_seconds":1.0,"audio_seconds":1.0,"sample_rate_hz":16000,"media_relpath":"slices/one.wav","sha256":audio,"bytes":len(media.read_bytes()),"iteration":0,"preprocess":[],"pre_sha256":None}
    req = {"source_provenance":source}
    rows = [req, {"source_provenance":dict(source)}] if duplicate else [req]
    return data, {"schema":WINDOW_FEATURE_INVENTORY_SCHEMA,"batches":[{"requests":rows}]}, audio

@dataclass
class Timing: request_id: str
class Client:
    def __init__(self): self.calls=[]; self.timings=[]; self.closed=0
    def register_slice(self, r): self.calls.append(("slice", r))
    def complete(self, messages, *, decoding_params=None): self.calls.append(("complete", messages)); self.timings.append(Timing(f"request-{len(self.timings)+1}")); return "ignored"
    def close(self): self.closed+=1; return {"trace_manifest_hash":"b"*64,"cost":{"calls_used":len(self.timings)}}

def kwargs(tmp_path, data, inv, client):
    cache=tmp_path/"cache"; cache.mkdir()
    return dict(inventory=inv,data_root=data,client=client,custody_guard=lambda:None,encoder_identity={"build":"x"},legacy_cache_dir=cache,expected_n_embd=4,output_path=tmp_path/"result.json",run_id="run",attempt_id="attempt",session_id="session",runtime_receipt_file_sha256=SHA,runtime_receipt_document_sha256=SHA,session_receipt_file_sha256=SHA)

def test_encodes_deduplicated_audio_and_closes(tmp_path, monkeypatch):
    data, inv, _ = inventory(tmp_path, duplicate=True); client=Client()
    monkeypatch.setattr("speech_aware_evidence_acquisition.core.preparation_encoding.inspect_legacy_cached_speech_feature_cache", lambda **_: None)
    result=encode_window_feature_cache(**kwargs(tmp_path,data,inv,client))
    assert result["contact_class"] == "encoder"
    assert client.closed == 1 and len([x for x in client.calls if x[0]=="complete"]) == 1

def test_existing_unproven_cache_refuses_before_contact(tmp_path, monkeypatch):
    data, inv, audio = inventory(tmp_path); client=Client(); args=kwargs(tmp_path,data,inv,client)
    monkeypatch.setattr("speech_aware_evidence_acquisition.core.preparation_encoding.legacy_audio_feature_cache_key", lambda _: "key")
    (args["legacy_cache_dir"] / "key_o0.feat").write_bytes(b"bad")
    with pytest.raises(PreparationError, match="unproven"):
        encode_window_feature_cache(**args)
    assert not client.calls and client.closed == 1
