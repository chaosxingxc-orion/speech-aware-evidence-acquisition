"""SlurpAdapter (B0 rails): interface-complete stub -- constructible, isa
TaskAdapter, every method raises NotImplementedError with a TODO rather
than guessing at a loader that does not exist yet.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.rails import AudioRef, TaskAdapter
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter, SlurpSample

_SHA_A = "a" * 64


def _adapter() -> SlurpAdapter:
    return SlurpAdapter(lock={"datasets": []}, root="/nonexistent")


def test_slurp_adapter_is_constructible_and_is_a_task_adapter():
    adapter = _adapter()
    assert isinstance(adapter, TaskAdapter)


def test_slurp_adapter_load_split_is_not_implemented_yet():
    with pytest.raises(NotImplementedError, match="SLURP loader"):
        _adapter().load_split("discovery")


def test_slurp_adapter_build_query_is_not_implemented_yet():
    sample = SlurpSample(
        sample_id="slurp:000001",
        audio_ref=AudioRef(path="a.wav", sha256=_SHA_A),
        audio_seconds=3.0,
        utterance_id="u1",
        scenario="alarm",
    )
    with pytest.raises(NotImplementedError, match="ontology"):
        _adapter().build_query(sample, obs=None)


def test_slurp_adapter_assemble_prompt_is_not_implemented_yet():
    sample = SlurpSample(
        sample_id="slurp:000001",
        audio_ref=AudioRef(path="a.wav", sha256=_SHA_A),
        audio_seconds=3.0,
        utterance_id="u1",
        scenario="alarm",
    )
    with pytest.raises(NotImplementedError, match="media path"):
        _adapter().assemble_prompt(sample, None)


def test_slurp_adapter_score_is_not_implemented_yet():
    sample = SlurpSample(
        sample_id="slurp:000001",
        audio_ref=AudioRef(path="a.wav", sha256=_SHA_A),
        audio_seconds=3.0,
        utterance_id="u1",
        scenario="alarm",
    )
    with pytest.raises(NotImplementedError, match="gold"):
        _adapter().score(sample, "some response")


def test_slurp_adapter_extract_consumption_is_not_implemented_yet():
    sample = SlurpSample(
        sample_id="slurp:000001",
        audio_ref=AudioRef(path="a.wav", sha256=_SHA_A),
        audio_seconds=3.0,
        utterance_id="u1",
        scenario="alarm",
    )
    with pytest.raises(NotImplementedError, match="no SLURP response"):
        _adapter().extract_consumption(sample, None, "some response")


def test_slurp_sample_satisfies_the_task_sample_shape():
    sample = SlurpSample(
        sample_id="slurp:000001",
        audio_ref=AudioRef(path="a.wav", sha256=_SHA_A),
        audio_seconds=3.0,
        utterance_id="u1",
        scenario="alarm",
    )
    assert sample.sample_id == "slurp:000001"
    assert sample.audio_ref.path == "a.wav"
    assert sample.audio_seconds == 3.0
