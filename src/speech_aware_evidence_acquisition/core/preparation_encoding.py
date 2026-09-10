"""Shared receipt-bound raw-audio encoding for verified window inventories."""
import hashlib
from pathlib import Path
from typing import Callable, Mapping
from .model import inspect_legacy_cached_speech_feature_cache, legacy_audio_feature_cache_key
from .model.slices import SliceRecord
from .preparation import PreparationError, canonical_bytes, digest, prepare_artifact
from .preparation_windows import WINDOW_FEATURE_INVENTORY_SCHEMA

SCHEMA = "saea-window-feature-encoding-record-v1"
KIND = "window-feature-encoding-v1"
INSTRUCTION = "Observe the complete speech signal for deterministic feature preprocessing. Respond with OK."
PARAMS = {"temperature": 0, "seed": 20260803, "max_tokens": 1}

def _sha(value, label):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise PreparationError(f"{label} must be lowercase SHA256")
    return value

def _sources(inventory):
    if inventory.get("schema") != WINDOW_FEATURE_INVENTORY_SCHEMA:
        raise PreparationError("window encoding requires a verified window feature inventory")
    result = {}
    for batch in inventory.get("batches", []):
        for request in batch.get("requests", []):
            source = request.get("source_provenance")
            if not isinstance(source, Mapping): raise PreparationError("window inventory request provenance is invalid")
            audio = _sha(source.get("sha256"), "window source audio_sha256")
            prior = result.setdefault(audio, source)
            if prior != source and prior.get("media_relpath") != source.get("media_relpath"):
                raise PreparationError("same window audio SHA256 has conflicting source provenance")
    if not result: raise PreparationError("window inventory contains no source audio")
    return result

def _slice(s):
    return SliceRecord(sample_id=s["sample_id"], parent_media_relpath=s["parent_media_relpath"], parent_sha256=s["parent_sha256"], start_seconds=s["start_seconds"], end_seconds=s["end_seconds"], audio_seconds=s["audio_seconds"], sample_rate_hz=s["sample_rate_hz"], media_relpath=s["media_relpath"], sha256=s["sha256"], bytes=s["bytes"], iteration=s["iteration"], preprocess=tuple(s["preprocess"]), pre_sha256=s["pre_sha256"])

def encode_window_feature_cache(*, inventory: Mapping[str, object], data_root: Path, client, custody_guard: Callable[[], None], encoder_identity: Mapping[str, object], legacy_cache_dir: Path, expected_n_embd: int, output_path: Path, run_id: str, attempt_id: str, session_id: str, runtime_receipt_file_sha256: str, runtime_receipt_document_sha256: str, session_receipt_file_sha256: str, warm_provenance: Mapping[str, Mapping[str, object]] | None = None):
    """Encode each unique inventory input; caller owns gate, attachment, lease and stop."""
    root = Path(data_root).resolve(strict=True); cache = Path(legacy_cache_dir).resolve(strict=True)
    if not cache.is_dir() or not callable(custody_guard): raise PreparationError("window encoding requires an existing cache and custody guard")
    if isinstance(expected_n_embd, bool) or not isinstance(expected_n_embd, int) or expected_n_embd < 1: raise PreparationError("expected_n_embd must be positive")
    for label, value in (("runtime receipt file", runtime_receipt_file_sha256), ("runtime receipt document", runtime_receipt_document_sha256), ("session receipt file", session_receipt_file_sha256)): _sha(value, label)
    sources = _sources(inventory); identity = dict(encoder_identity); inventory_sha256 = digest(inventory); warm = warm_provenance or {}
    inputs = {"inventory_sha256": inventory_sha256, "encoder_identity": identity, "legacy_cache_dir": str(cache), "expected_n_embd": expected_n_embd, "run_id": run_id, "attempt_id": attempt_id, "session_id": session_id, "runtime_receipt_file_sha256": runtime_receipt_file_sha256, "runtime_receipt_document_sha256": runtime_receipt_document_sha256, "session_receipt_file_sha256": session_receipt_file_sha256}
    def produce():
        entries=[]; attempted=0; closed=None
        try:
            planned=[]
            for audio, source in sorted(sources.items()):
                media=(root/source["media_relpath"]).resolve(strict=True)
                try: media.relative_to(root)
                except ValueError as error: raise PreparationError("window media path escapes data_root") from error
                content=media.read_bytes()
                if hashlib.sha256(content).hexdigest()!=audio: raise PreparationError("window source bytes changed after inventory")
                key=legacy_audio_feature_cache_key(content); prior=warm.get(audio)
                if tuple(cache.glob(f"{key}_o*.feat")) and prior is None: raise PreparationError("unproven existing legacy cache entry refuses before encoder contact")
                if prior is not None:
                    required={"audio_sha256","cache_key","encoder_identity","source_contact_id","source_provenance_receipt_sha256"}
                    if not required <= set(prior) or prior["audio_sha256"]!=audio or prior["cache_key"]!=key or prior["encoder_identity"]!=identity: raise PreparationError("warm provenance does not bind this audio, cache key and encoder identity")
                    _sha(prior["source_provenance_receipt_sha256"], "warm provenance receipt")
                    if not isinstance(prior["source_contact_id"],str) or not prior["source_contact_id"]: raise PreparationError("warm provenance source contact is missing")
                    inspect_legacy_cached_speech_feature_cache(audio_path=media,legacy_cache_dir=cache,expected_n_embd=expected_n_embd)
                    entries.append({"audio_sha256":audio,"cache_key":key,"status":"verified-warm-reuse","success":True,"current_contact_id":None,"source_contact_id":prior["source_contact_id"],"source_provenance_receipt_sha256":prior["source_provenance_receipt_sha256"]})
                else: planned.append((audio,source,media,key))
            for audio,source,media,key in planned:
                custody_guard(); client.register_slice(_slice(source)); client.complete(({"role":"system","content":INSTRUCTION},{"role":"user","content":[{"type":"input_audio","media_relpath":source["media_relpath"]}]}),decoding_params=PARAMS); attempted+=1
                inspect_legacy_cached_speech_feature_cache(audio_path=media,legacy_cache_dir=cache,expected_n_embd=expected_n_embd)
                contact=getattr(tuple(client.timings)[-1],"request_id",None)
                if not isinstance(contact,str) or not contact: raise PreparationError("encoder client did not expose a contact request_id")
                entries.append({"audio_sha256":audio,"cache_key":key,"status":"encoded","success":True,"current_contact_id":contact,"source_contact_id":None,"source_provenance_receipt_sha256":None})
            closed=client.close()
            if not isinstance(closed.get("cost"), Mapping) or closed["cost"].get("calls_used") != attempted: raise PreparationError("encoder cost.calls_used must equal fresh contact count")
            if len({e["current_contact_id"] for e in entries if e["current_contact_id"]})!=attempted: raise PreparationError("encoder contact IDs must be unique")
            return {"schema":SCHEMA,"study":"speech-aware-evidence-acquisition","run_id":run_id,"attempt_id":attempt_id,"session_id":session_id,"runtime_receipt_file_sha256":runtime_receipt_file_sha256,"runtime_receipt_document_sha256":runtime_receipt_document_sha256,"session_receipt_file_sha256":session_receipt_file_sha256,"inventory_sha256":inventory_sha256,"encoder_identity":identity,"trace_manifest_hash":closed.get("trace_manifest_hash"),"cost":closed.get("cost"),"current_contact_count":attempted,"entries":entries}
        except BaseException as error:
            if closed is None:
                try: closed=client.close()
                except BaseException: closed={}
            partial={"schema":SCHEMA,"state":"failed","inventory_sha256":inventory_sha256,"attempted_contacts":attempted,"entries":entries,"trace_manifest_hash":closed.get("trace_manifest_hash"),"cost":closed.get("cost"),"error_type":type(error).__name__}
            try:
                with Path(output_path).with_name(Path(output_path).name+".partial.json").open("xb") as stream: stream.write(canonical_bytes(partial))
            except FileExistsError: pass
            raise
    return prepare_artifact(Path(output_path),kind=KIND,inputs=inputs,producer=produce,contact_class="encoder")
