"""obs-agent-loop-ojw surfaces that must hold WITHOUT openjiuwen installed.

The D2 zero-dependency gate (docs/readiness/2026-08-08-openjiuwen-adoption.md
red line 2) requires the repo suite to pass with openjiuwen absent: the
policy registers, refuses at run time with the install hint, and the
openjiuwen-free state layer (the FuncCondition callable's exact semantics)
is fully testable. The openjiuwen-dependent executor tests live in
``test_obs_loop_ojw.py`` behind an importorskip marker.
"""

from array import array

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
import speech_aware_evidence_acquisition.reproduction.ojw as ojw_runtime
from speech_aware_evidence_acquisition.core.base import POLICIES
from speech_aware_evidence_acquisition.reproduction.obs_loop import (
    ObsLoopConfig,
    ObsLoopError,
)
from speech_aware_evidence_acquisition.reproduction.ojw import (
    DEFAULT_WORKFLOW_TIMEOUT_SECONDS,
    OJW_POLICY_NAME,
    OJW_WORKFLOW_TIMEOUT_KEY,
    openjiuwen_available,
)
from speech_aware_evidence_acquisition.reproduction.ojw.policy import (
    ObsAgentLoopOjwPolicy,
    workflow_timeout_seconds,
)
from speech_aware_evidence_acquisition.reproduction.ojw.state import ObsSampleState

from test_obs_loop_policy import _World, _boundary_text, _noise

RATE = 16000


def test_policy_is_registered_without_openjiuwen():
    assert isinstance(POLICIES.resolve(OJW_POLICY_NAME), ObsAgentLoopOjwPolicy)


def test_openjiuwen_runtime_version_mismatch_fails_closed(monkeypatch):
    monkeypatch.setattr(ojw_runtime, "version", lambda _name: "0.0.0")

    assert ojw_runtime.openjiuwen_available() is False
    with pytest.raises(ojw_runtime.OpenJiuwenExecutorError, match="version mismatch"):
        ojw_runtime.openjiuwen_runtime_version()


@pytest.mark.skipif(
    openjiuwen_available(),
    reason="refusal path only exists when openjiuwen is absent",
)
def test_run_sample_refuses_with_install_hint_when_openjiuwen_absent(
    tmp_path, monkeypatch
):
    world = _World(
        tmp_path, monkeypatch, pcm=_noise(30.0), texts=[_boundary_text("A.", 10)]
    )
    with pytest.raises(ObsLoopError, match="openjiuwen"):
        ObsAgentLoopOjwPolicy().run_sample(world.ctx)


# ---------------------------------------------------------------------------
# The per-sample workflow ceiling parser (real-run blocker 2026-08-08):
# openjiuwen-free, so the fragment-knob semantics are provable everywhere.
# ---------------------------------------------------------------------------


class TestWorkflowTimeoutParsing:
    def test_declared_value_wins(self):
        assert workflow_timeout_seconds({OJW_WORKFLOW_TIMEOUT_KEY: 900}) == 900.0

    def test_absent_key_defaults_to_the_generous_backstop(self):
        assert workflow_timeout_seconds({}) == DEFAULT_WORKFLOW_TIMEOUT_SECONDS
        assert DEFAULT_WORKFLOW_TIMEOUT_SECONDS == 21600.0

    def test_non_positive_passes_through_as_the_disable_convention(self):
        # framework semantics: Workflow._execute_with_timeout treats <= 0 as
        # no limit -- the knob deliberately admits it rather than inventing a
        # second disable spelling
        assert workflow_timeout_seconds({OJW_WORKFLOW_TIMEOUT_KEY: 0}) == 0.0
        assert workflow_timeout_seconds({OJW_WORKFLOW_TIMEOUT_KEY: -1}) == -1.0

    @pytest.mark.parametrize("bad", ["fast", True, float("nan"), float("inf"), None])
    def test_unusable_values_refuse_rather_than_reenable_the_60s_kill(self, bad):
        with pytest.raises(ObsLoopError, match=OJW_WORKFLOW_TIMEOUT_KEY):
            workflow_timeout_seconds({OJW_WORKFLOW_TIMEOUT_KEY: bad})


# ---------------------------------------------------------------------------
# The FuncCondition callable (state.should_continue): openjiuwen-free, so its
# exact loop-head semantics are provable in every environment.
# ---------------------------------------------------------------------------


class _FakeSink:
    def __init__(self):
        self.records = []

    def emit(self, channel, record_id, payload):
        self.records.append((channel, record_id, dict(payload)))


def _fixed_cfg(tmp_path, **overrides):
    values = {
        "obs_buffer_seconds": 30,
        "obs_min_advance_seconds": 30,
        "obs_max_advance_seconds": 30,
        "obs_fallback_advance_seconds": 30,
        "obs_silence_snap_seconds": 0,
        "obs_boundary_mode": "fixed",
        "obs_vad": "energy",
        "obs_vad_trim_min_seconds": 5.0,
        "obs_preprocess": [],
        "obs_condition_tail_chars": 0,
    }
    values.update(overrides)
    return ObsLoopConfig.from_values(values, tmp_path)


def _state(tmp_path, *, seconds: float, trim_spans=(), **cfg_overrides):
    pcm = array("h", [1000] * int(seconds * RATE))
    return ObsSampleState(
        cfg=_fixed_cfg(tmp_path, **cfg_overrides),
        pcm=pcm,
        rate=RATE,
        duration=len(pcm) / RATE,
        parent_sha256="0" * 64,
        transitions=[],
        trim_spans=list(trim_spans),
        engine_descriptor="energy-vad-v1",
        sample=None,
        arm="bare-core",
        evidence=None,
        task_instruction="t",
        decoding_params={},
        request_id_base="req-0001",
        retrieval_query=None,
        registry=None,
        data_root=tmp_path,
        sink=_FakeSink(),
        effective_min=30.0,
        max_iterations=10,
    )


class TestShouldContinue:
    def test_audio_remaining_continues(self, tmp_path):
        state = _state(tmp_path, seconds=45.0)
        assert state.should_continue() is True
        assert state.runaway is False

    def test_exhausted_cursor_exits(self, tmp_path):
        state = _state(tmp_path, seconds=45.0)
        state.cursor = state.duration
        assert state.should_continue() is False
        assert state.runaway is False

    def test_runaway_flags_and_exits_before_anything_else(self, tmp_path):
        state = _state(tmp_path, seconds=45.0, trim_spans=[(0.0, 10.0)])
        state.iteration = state.max_iterations + 1
        assert state.should_continue() is False
        assert state.runaway is True
        # the runaway exit consumed no trims: the plain policy raises right
        # after the offending iteration, before any further trim round
        assert state.trims == 0
        assert state.sink.records == []

    def test_trims_are_consumed_with_identical_records(self, tmp_path):
        # one long non-speech span at the head: the condition consumes it,
        # emits exactly the plain policy's trim record, then continues
        state = _state(tmp_path, seconds=45.0, trim_spans=[(0.0, 10.0)])
        assert state.should_continue() is True
        assert state.cursor == 10.0
        assert state.trims == 1
        assert state.trim_events == [
            {"from_seconds": 0.0, "to_seconds": 10.0, "engine": "energy-vad-v1"}
        ]
        channel, record_id, payload = state.sink.records[0]
        assert (channel, record_id) == ("OBS", "req-0001-trim0000/obs")
        assert payload == {
            "obs_trim_from_seconds": 0.0,
            "obs_trim_to_seconds": 10.0,
            "obs_trim_span_start_seconds": 0.0,
            "obs_trim_span_end_seconds": 10.0,
            "obs_vad_engine": "energy-vad-v1",
        }

    def test_trim_to_exhaustion_exits_without_a_body_round(self, tmp_path):
        state = _state(tmp_path, seconds=20.0, trim_spans=[(0.0, 20.0)])
        assert state.should_continue() is False
        assert state.trims == 1
        assert state.cursor == pytest.approx(state.duration)

    def test_degenerate_zero_length_window_exits(self, tmp_path):
        # cursor within half a sample of the end: still < duration - epsilon,
        # but the rounded frame window collapses -- the plain loop's `break`
        state = _state(tmp_path, seconds=45.0, obs_vad_trim_min_seconds=0)
        state.cursor = state.duration - 2e-6
        assert state.should_continue() is False
        assert state.runaway is False
