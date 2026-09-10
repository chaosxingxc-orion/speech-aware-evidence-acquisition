from hashlib import sha256
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis import e21_selective_loop_windows as subject
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.predecessor_snapshot import PredecessorSnapshot, PredecessorWindow
from speech_aware_evidence_acquisition.reproduction.obs_loop import PlannedUnit
from speech_aware_evidence_acquisition.core.repair_alignment import accept_entity_repair
from speech_aware_evidence_acquisition.core.bundle.delivery_replay import canonical


def _window(i, text):
    return PredecessorWindow(f"s#w{i:04d}", "s", i, f"old-{i}", (i-1)*10, i*10, 10, False, text, sha256(text.encode()).hexdigest(), None, None)


def _bundle(obs, response="b", request_id="root-i0000"):
    payload = {"request_id": request_id, "sample_id": "s", "decoding_params": {"max_tokens": 8}}
    records = {
        f"{request_id}/request": {"payload": payload, "payload_sha256": sha256(canonical(payload)).hexdigest()},
        f"{request_id}/obs": obs,
        "root/request": {"stitch": True, "stitched_request_ids": [] if obs["obs_skipped"] else [request_id]},
    }
    if response is not None:
        records[f"{request_id}/response"] = {"text": response, "response_text_sha256": sha256(response.encode()).hexdigest(), "usage": {"completion_tokens": 1}}
    return SimpleNamespace(outputs_rows=({"sample_id": "s", "request_id": "root", "text": "a b c"},), split_ids=frozenset({"s"}), trace_records=records)


def _patch(monkeypatch):
    windows = (_window(1, "a"), _window(2, "b"), _window(3, "c"))
    snapshot = SimpleNamespace(for_sample=lambda sample: windows)
    unit = PlannedUnit("s#u0001", 1, 11.0, 19.0, None, "recut", 2, 0, 1)
    plan = SimpleNamespace(units_for=lambda sample, duration: (unit,))
    monkeypatch.setattr(subject, "VerifiedBundle", SimpleNamespace)
    monkeypatch.setattr(subject, "_values", lambda bundle, root: {"obs_unit_plan":"p","obs_unit_plan_sha256":"h","obs_buffer_seconds":90,"response_postprocessor":"p","response_postprocessor_params":{}})
    monkeypatch.setattr(subject, "binding_from_values", lambda values: ("x", "d"))
    monkeypatch.setattr(subject, "load_predecessor_binding", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr(subject, "_load_unit_plan", lambda *args, **kwargs: plan)
    monkeypatch.setattr(subject, "REPAIR_FRAMES", {"e21-entity-repair-frame-v1": "x"})
    monkeypatch.setattr(subject, "RESPONSE_POSTPROCESSORS", SimpleNamespace(resolve=lambda name: lambda **kwargs: lambda old, new: accept_entity_repair(old, new, max_substituted_fraction=1.0)))


def _obs(**overrides):
    value = {"obs_iteration": 0, "obs_retry_of": None, "obs_repair_predecessor_window_id": "s#w0002", "obs_repair_predecessor_text_sha256": sha256(b"b").hexdigest(), "obs_window_start_seconds": 11.0, "obs_window_end_seconds": 19.0, "obs_skipped": False, "obs_saturated": False, "obs_relisten_window_text": "b", "obs_delivered_text": "a b c"}
    value.update(overrides)
    return value


def test_reconstructs_all_predecessor_windows_and_retry(monkeypatch, tmp_path):
    _patch(monkeypatch)
    bundle = _bundle(_obs(obs_retry_of="root-i0000"), request_id="root-i0000-r1")
    spans = subject.verified_selective_loop_windows(bundle, repo_root=tmp_path, data_root=tmp_path)
    assert [span.text for span in spans["s"]] == ["a", "b", "c"]


@pytest.mark.parametrize("field,value,match", [
    ("obs_repair_predecessor_text_sha256", "0"*64, "predecessor"),
    ("obs_delivered_text", "tampered", "delivery"),
    ("obs_relisten_window_text", "tampered", "delivery"),
])
def test_refuses_tampered_selective_trace(monkeypatch, tmp_path, field, value, match):
    _patch(monkeypatch)
    with pytest.raises(subject.SelectiveLoopWindowsError, match=match):
        subject.verified_selective_loop_windows(_bundle(_obs(**{field:value})), repo_root=tmp_path, data_root=tmp_path)


@pytest.mark.parametrize("skipped,saturated", [(False, True), (True, False)])
def test_saturation_or_skip_falls_back_to_predecessor(monkeypatch, tmp_path, skipped, saturated):
    _patch(monkeypatch)
    obs = _obs(obs_skipped=skipped, obs_saturated=saturated)
    bundle = _bundle(obs, response=None if skipped else "")
    spans = subject.verified_selective_loop_windows(bundle, repo_root=tmp_path, data_root=tmp_path)
    assert [span.text for span in spans["s"]] == ["a", "b", "c"]


@pytest.mark.parametrize("field,value", [
    ("obs_unit_id", "wrong-unit"),
    ("obs_relisten_parent_window_index", 1),
    ("obs_relisten_predecessor_word_start", 1),
    ("obs_relisten_predecessor_word_end", 2),
    ("obs_window_start_seconds", 10.0),
])
def test_refuses_plan_identity_or_range_drift(monkeypatch, tmp_path, field, value):
    _patch(monkeypatch)
    with pytest.raises(subject.SelectiveLoopWindowsError):
        subject.verified_selective_loop_windows(_bundle(_obs(**{field: value})), repo_root=tmp_path, data_root=tmp_path)


def test_refuses_extra_terminal_obs(monkeypatch, tmp_path):
    _patch(monkeypatch)
    bundle = _bundle(_obs())
    bundle.trace_records["root-i0000-r1/obs"] = _obs(obs_retry_of="root-i0000")
    bundle.trace_records["root-i0000-r1/request"] = {"payload": {"sample_id": "s"}}
    bundle.trace_records["root-i0000-r1/response"] = {"text": "b", "response_text_sha256": sha256(b"b").hexdigest()}
    with pytest.raises(subject.SelectiveLoopWindowsError):
        subject.verified_selective_loop_windows(bundle, repo_root=tmp_path, data_root=tmp_path)
