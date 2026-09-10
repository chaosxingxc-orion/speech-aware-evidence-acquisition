"""Synthetic coverage for verified legacy OBS delivery-window reconstruction."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis import delivery_windows as subject
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.bundle.delivery_replay import canonical
from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
    PredecessorSnapshot,
    PredecessorWindow,
)


class _RuleRegistry:
    def resolve(self, name):
        def factory(**params):
            mode = params["mode"]

            def rule(predecessor, response):
                return SimpleNamespace(
                    text=predecessor
                    if mode == "constrained" or not response
                    else response,
                    refusal_reason=None,
                )

            return rule

        return factory


def _digest(value):
    return sha256(canonical(value)).hexdigest()


def _window(sample_id, index, text):
    return PredecessorWindow(
        window_id=f"{sample_id}#w{index:04d}",
        sample_id=sample_id,
        window_index=index,
        request_id=f"prior-{index}",
        start_seconds=float((index - 1) * 90),
        end_seconds=float(index * 90),
        audio_seconds=90.0,
        saturated=False,
        text=text,
        text_sha256=sha256(text.encode()).hexdigest(),
    )


def _fixture(mode="free", retry=False, states=("normal",)):
    sample_id = "call-1"
    predecessors = tuple(
        _window(sample_id, index, f"draft {index}")
        for index in range(1, len(states) + 1)
    )
    snapshot = PredecessorSnapshot(
        run_id="prior",
        attempt_id="prior-attempt",
        receipt_relpath="receipt.json",
        receipt_sha256="a" * 64,
        artifact_relpath="artifact.json",
        artifact_sha256="b" * 64,
        source={},
        windows={item.window_id: item for item in predecessors},
        order={sample_id: tuple(item.window_id for item in predecessors)},
    )
    records, windows, delivered = {}, [], []
    for zero, (predecessor, state) in enumerate(zip(predecessors, states)):
        base = f"root-i{zero:04d}"
        request_id = f"{base}-r1" if retry and zero == 0 else base
        payload = {"request_id": request_id, "sample_id": sample_id}
        request = {"payload": payload, "payload_sha256": _digest(payload)}
        skipped = state == "skipped"
        saturated = state == "saturated"
        obs = {
            "obs_skipped": skipped,
            "obs_saturated": saturated,
            "obs_retry_of": base if request_id != base else None,
            "obs_repair_predecessor_window_id": predecessor.window_id,
            "obs_repair_predecessor_text_sha256": predecessor.text_sha256,
            "obs_window_start_seconds": predecessor.start_seconds,
            "obs_window_end_seconds": predecessor.end_seconds,
        }
        records[f"{request_id}/request"] = request
        records[f"{request_id}/obs"] = obs
        response = None
        if not skipped:
            text = f"response {zero + 1}"
            response = {
                "text": text,
                "response_text_sha256": sha256(text.encode()).hexdigest(),
                "usage": {"completion_tokens": 1},
            }
            records[f"{request_id}/response"] = response
        delivered_text = (
            predecessor.text
            if mode == "constrained" or skipped or saturated
            else response["text"]
        )
        delivered.append(delivered_text)
        windows.append(
            {
                "sample_id": sample_id,
                "window_id": predecessor.window_id,
                "window_index": predecessor.window_index,
                "terminal_request_id": request_id,
                "retry_of": obs["obs_retry_of"],
                "skipped": skipped,
                "saturated": saturated,
                "request_record_sha256": _digest(request),
                "response_record_sha256": None
                if response is None
                else _digest(response),
                "obs_record_sha256": _digest(obs),
                "predecessor_text_sha256": predecessor.text_sha256,
                "delivered_text_sha256": sha256(delivered_text.encode()).hexdigest(),
            }
        )
    parent = VerifiedBundle(
        Path("parent.json"), {}, None, (), records, frozenset({sample_id}), "COMPLETED"
    )
    manifest = {
        "schema": "saea-derived-delivery-v1",
        "parent": {"path": "/synthetic/parent.json"},
        "predecessor_receipt": {"path": "/synthetic/receipt.json", "sha256": "a" * 64},
        "data_root": "/synthetic/data",
        "declaration": {
            "response_postprocessor": "synthetic",
            "response_postprocessor_params": {"mode": mode},
        },
        "windows": windows,
    }
    derived = VerifiedBundle(
        Path("derived.json"),
        manifest,
        None,
        ({"sample_id": sample_id, "text": " ".join(delivered)},),
        records,
        frozenset({sample_id}),
        "DERIVED",
    )
    return parent, snapshot, derived


def _patch(monkeypatch, parent, snapshot):
    monkeypatch.setattr(subject, "verify_bundle", lambda _path: parent)
    monkeypatch.setattr(
        subject, "load_predecessor_binding", lambda *_args, **_kwargs: snapshot
    )
    monkeypatch.setattr(subject, "RESPONSE_POSTPROCESSORS", _RuleRegistry())


@pytest.mark.parametrize(
    "mode, expected", [("constrained", "draft 1"), ("free", "response 1")]
)
def test_registered_delivery_rule_reconstructs_distinct_constrained_and_free_text(
    monkeypatch, mode, expected
):
    parent, snapshot, derived = _fixture(mode)
    _patch(monkeypatch, parent, snapshot)
    spans = subject.verified_delivery_windows(derived)
    assert spans["call-1"][0].text == expected
    assert spans["call-1"][0].request_id == "root-i0000"


def test_manifest_terminal_retry_is_used_without_reselecting_a_response(monkeypatch):
    parent, snapshot, derived = _fixture("free", retry=True)
    _patch(monkeypatch, parent, snapshot)
    spans = subject.verified_delivery_windows(derived)
    assert spans["call-1"][0].request_id == "root-i0000-r1"
    assert spans["call-1"][0].text == "response 1"


def test_saturated_and_skipped_windows_keep_fallbacks_and_bounds(monkeypatch):
    parent, snapshot, derived = _fixture(
        "free", states=("saturated", "skipped", "normal")
    )
    _patch(monkeypatch, parent, snapshot)
    spans = subject.verified_delivery_windows(derived)["call-1"]
    assert [span.text for span in spans] == ["draft 1", "draft 2", "response 3"]
    assert [span.saturated for span in spans] == [True, False, False]
    assert [(span.start_seconds, span.end_seconds) for span in spans] == [
        (0.0, 90.0),
        (90.0, 180.0),
        (180.0, 270.0),
    ]


def test_mismatched_delivered_hash_refuses(monkeypatch):
    parent, snapshot, derived = _fixture("free")
    _patch(monkeypatch, parent, snapshot)
    derived.manifest["windows"][0]["delivered_text_sha256"] = "0" * 64
    with pytest.raises(
        subject.DeliveryWindowsError, match="delivery text hash mismatch"
    ):
        subject.verified_delivery_windows(derived)


def test_phase_sources_are_explicitly_unsupported(monkeypatch):
    parent, snapshot, derived = _fixture("free")
    _patch(monkeypatch, parent, snapshot)
    derived.manifest["phase_sources"] = []
    with pytest.raises(subject.DeliveryWindowsError, match="phase_sources"):
        subject.verified_delivery_windows(derived)
