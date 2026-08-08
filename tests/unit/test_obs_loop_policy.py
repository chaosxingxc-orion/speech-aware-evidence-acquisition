"""obs-agent-loop policy (owner directive 2026-08-08): the model-driven OBS
segmentation loop, tested against a scripted fake adapter + a real TraceSink
+ a real SliceRegistry, with the parent decode monkeypatched to synthetic
PCM (no soundfile/ffmpeg, no model, no real audio).
"""

import hashlib
import json
import random
from array import array
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.core.base import POLICIES, SampleContext
from speech_aware_evidence_acquisition.core.base import EvidenceItem
from speech_aware_evidence_acquisition.core.model import SliceRegistry
from speech_aware_evidence_acquisition.core.tracing import TraceSink
from speech_aware_evidence_acquisition.data.loader import SampleRef
from speech_aware_evidence_acquisition.reproduction import obs_loop
from speech_aware_evidence_acquisition.reproduction.obs_loop import (
    OBS_LOOP_POLICY_NAME,
    OBS_TAIL_FRAME_V1,
    ObsAgentLoopPolicy,
    ObsLoopConfig,
    ObsLoopError,
)

RATE = 16000
RUN_ID = "SAEA-E-000-obsloop"
SAMPLE_ID = "4000001"
PARENT_RELPATH = "datasets/earnings21-22/earnings21/media/4000001.mp3"
TEMPLATE_RELPATH = "probes/obs_boundary_v1.txt"


def _noise(seconds: float, seed: int = 3) -> array:
    rng = random.Random(seed)
    return array(
        "h", (int(6000 * (2 * rng.random() - 1)) for _ in range(int(seconds * RATE)))
    )


def _silence(seconds: float) -> array:
    return array("h", [0] * int(seconds * RATE))


def _concat(*chunks: array) -> array:
    out = array("h")
    for chunk in chunks:
        out.extend(chunk)
    return out


class _FakeResponse:
    def __init__(self, text: str, tag: str) -> None:
        self.text = text
        self.request_sha256 = hashlib.sha256(f"req-{tag}".encode()).hexdigest()
        self.response_sha256 = hashlib.sha256(f"resp-{tag}".encode()).hexdigest()
        self.response_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()


class _ScriptedAdapter:
    """Returns the scripted texts in order and records every payload."""

    def __init__(self, texts: list[str]) -> None:
        self._texts = list(texts)
        self.payloads: list[dict] = []

    def request(self, payload):
        self.payloads.append(dict(payload))
        if not self._texts:
            raise AssertionError("policy sent more requests than the script expected")
        text = self._texts.pop(0)
        return _FakeResponse(text, tag=str(len(self.payloads)))


class _FlakyAdapter:
    """Wraps a scripted adapter: the given 1-based call indices raise
    TimeoutError('timed out') — the live E-001 slice-hang shape — exactly
    once each; a raised call consumes no scripted text (the real transport
    never returned bytes either)."""

    def __init__(self, inner, fail_calls) -> None:
        self._inner = inner
        self._fail = set(fail_calls)
        self.calls = 0
        self.failed_request_ids: list[str] = []

    def request(self, payload):
        self.calls += 1
        if self.calls in self._fail:
            self._fail.discard(self.calls)
            self.failed_request_ids.append(str(payload["request_id"]))
            raise TimeoutError("timed out")
        return self._inner.request(payload)


def _config_values(**overrides):
    values = {
        "obs_buffer_seconds": 60,
        "obs_min_advance_seconds": 20,
        "obs_max_advance_seconds": 55,
        "obs_silence_snap_seconds": 2.0,
        "obs_fallback_advance_seconds": 50,
        "obs_boundary_mode": "model",
        "obs_boundary_prompt": TEMPLATE_RELPATH,
        "obs_vad": "energy",
        "obs_vad_trim_min_seconds": 5.0,
        "obs_preprocess": [],
        "obs_condition_tail_chars": 0,
    }
    values.update(overrides)
    return values


class _World:
    def __init__(self, tmp_path: Path, monkeypatch, *, pcm: array, texts: list[str], values=None, evidence=None, arm="bare-core"):
        self.data_root = tmp_path / "data"
        self.run_dir = tmp_path / "run"
        self.repo_root = tmp_path / "repo"
        parent = self.data_root / PARENT_RELPATH
        parent.parent.mkdir(parents=True)
        parent.write_bytes(b"fake-mp3-bytes-for-" + SAMPLE_ID.encode())
        template = self.repo_root / "configs" / TEMPLATE_RELPATH
        template.parent.mkdir(parents=True)
        template.write_text(
            "After the transcript report BOUNDARY_SECONDS as instructed.\n",
            encoding="utf-8",
        )
        self.duration = len(pcm) / RATE
        monkeypatch.setattr(obs_loop, "decode_parent_pcm", lambda path, rate=RATE: pcm)
        self.registry = SliceRegistry(
            data_root=self.data_root,
            run_id=RUN_ID,
            parent_facts={SAMPLE_ID: (PARENT_RELPATH, self.duration)},
        )
        self.adapter = _ScriptedAdapter(texts)
        self.sink = TraceSink(self.run_dir, RUN_ID)
        self.ctx = SampleContext(
            sample=SampleRef(
                carrier_lock_key="earnings21-original",
                sample_id=SAMPLE_ID,
                media_relpath=PARENT_RELPATH,
                audio_seconds=self.duration,
                sample_rate_hz=RATE,
            ),
            evidence=evidence or [],
            adapter=self.adapter,
            sink=self.sink,
            arm=arm,
            task_instruction="Transcribe the speech verbatim.",
            decoding_params={"temperature": 0},
            request_id_base="req-0001",
            extras={
                "slice_registry": self.registry,
                "data_root": self.data_root,
                "run_dir": self.run_dir,
                "repo_root": self.repo_root,
                "config_values": values or _config_values(),
            },
        )

    def run(self):
        return ObsAgentLoopPolicy().run_sample(self.ctx)


def _boundary_text(body: str, boundary: float) -> str:
    return f"TRANSCRIPT:\n{body}\nBOUNDARY_SECONDS: {boundary}"


def test_policy_is_registered():
    assert POLICIES.resolve(OBS_LOOP_POLICY_NAME) is not None


class TestModelModeLoop:
    def test_three_iteration_loop_stitches_and_chains(self, tmp_path, monkeypatch):
        # 150s of speech-like noise: it0 [0,60) boundary 45 -> advance 45;
        # it1 [45,105) boundary 50 -> advance 50 -> cursor 95; it2 [95,150) final.
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(150.0),
            texts=[
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
        )
        outcome = world.run()
        assert len(world.adapter.payloads) == 3
        relpaths = [p["media_relpath"] for p in world.adapter.payloads]
        assert relpaths == [
            f"derived/obs-slices/{RUN_ID}/{SAMPLE_ID}/i0000.wav",
            f"derived/obs-slices/{RUN_ID}/{SAMPLE_ID}/i0001.wav",
            f"derived/obs-slices/{RUN_ID}/{SAMPLE_ID}/i0002.wav",
        ]
        assert [p["audio_seconds"] for p in world.adapter.payloads] == [60.0, 60.0, 55.0]
        # accepted: cut at last '.' inside the boundary share; final accepts all
        assert outcome.text == "First span one. Second span two. Final span three."
        assert outcome.sample_id == SAMPLE_ID
        assert outcome.request_ids == ("req-0001-i0000", "req-0001-i0001", "req-0001-i0002")
        assert outcome.response_text_sha256 == hashlib.sha256(
            outcome.text.encode("utf-8")
        ).hexdigest()
        # every slice was written and registered under the run's slice tree
        for relpath in relpaths:
            assert (world.data_root / relpath).is_file()
            assert world.registry.lookup(SAMPLE_ID, relpath) is not None

    def test_stitch_trace_records_bind_the_outputs_row_shape(self, tmp_path, monkeypatch):
        """I7: {base}/request + {base}/response records carry exactly the
        hashes/text the outputs row will carry (the bundle cross-check reads
        these fields verbatim)."""

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                _boundary_text("Alpha beta. Gamma", 45),
                _boundary_text("Delta done.", 20),
            ],
        )
        outcome = world.run()
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = {
            document["record_id"]: document
            for document in (json.loads(line) for line in raw.splitlines() if line)
        }
        request_record = records["req-0001/request"]
        response_record = records["req-0001/response"]
        assert request_record["payload"]["payload_sha256"] == outcome.request_sha256
        assert request_record["payload"]["stitch"] is True
        assert response_record["payload"]["text"] == outcome.text
        assert response_record["payload"]["response_sha256"] == outcome.response_sha256
        assert (
            response_record["payload"]["response_text_sha256"]
            == outcome.response_text_sha256
        )
        assert records["req-0001/use"]["payload"]["use_admitted"] is True
        # per-iteration OBS records exist and carry the boundary tiers
        obs_payload = records["req-0001-i0000/obs"]["payload"]
        assert obs_payload["obs_boundary_estimate_seconds"] == 45.0
        assert obs_payload["obs_boundary_fallback"] is False

    def test_unparseable_boundary_falls_back_and_flags(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                "no boundary line at all here.",
                _boundary_text("Tail end.", 10),
            ],
        )
        world.run()
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = {
            document["record_id"]: document["payload"]
            for document in (json.loads(line) for line in raw.splitlines() if line)
        }
        first = records["req-0001-i0000/obs"]
        assert first["obs_boundary_fallback"] is True
        assert first["obs_boundary_advance_seconds"] == 50.0

    def test_derivation_record_is_written_lf(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(70.0),
            texts=[_boundary_text("One two. Three", 40), _boundary_text("Rest.", 5)],
        )
        world.run()
        record_path = world.run_dir / f"{RUN_ID}.obs-derivation.{SAMPLE_ID}.json"
        raw = record_path.read_bytes()
        assert b"\r" not in raw
        document = json.loads(raw.decode("utf-8"))
        assert document["schema"] == "saea-obs-derivation-v1"
        assert document["sample_id"] == SAMPLE_ID
        assert len(document["slices"]) == 2
        assert document["slices"][0]["parent_media_relpath"] == PARENT_RELPATH


class TestFixedModeAblation:
    def test_fixed_windows_no_boundary_prompt(self, tmp_path, monkeypatch):
        values = _config_values(
            obs_buffer_seconds=30,
            obs_min_advance_seconds=30,
            obs_max_advance_seconds=30,
            obs_fallback_advance_seconds=30,
            obs_silence_snap_seconds=0,
            obs_boundary_mode="fixed",
            obs_vad_trim_min_seconds=0,
        )
        values.pop("obs_boundary_prompt")
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(75.0),
            texts=["span one", "span two", "span three"],
            values=values,
        )
        outcome = world.run()
        assert [p["audio_seconds"] for p in world.adapter.payloads] == [30.0, 30.0, 15.0]
        for payload in world.adapter.payloads:
            assert payload["task_instruction"] == "Transcribe the speech verbatim."
        assert outcome.text == "span one span two span three"


class TestVadPreTrim:
    def test_long_leading_silence_is_skipped_and_not_metered(self, tmp_path, monkeypatch):
        # 10s leading silence + 55s speech: the trimmed window [~10, 65) fits
        # one final buffer (frame-granular trim can land at 9.99, still final).
        pcm = _concat(_silence(10.0), _noise(55.0))
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=pcm,
            texts=[_boundary_text("Speech only.", 30)],
        )
        outcome = world.run()
        assert len(world.adapter.payloads) == 1
        payload = world.adapter.payloads[0]
        # window starts after the trimmed silence and never re-covers it
        record = world.registry.lookup(SAMPLE_ID, payload["media_relpath"])
        assert record.start_seconds == pytest.approx(10.0, abs=0.6)
        assert payload["audio_seconds"] == pytest.approx(
            world.duration - record.start_seconds, abs=0.01
        )
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        trim_records = [line for line in raw.splitlines() if "obs_trim_to_seconds" in line]
        assert len(trim_records) == 1
        assert outcome.text == "Speech only."


class TestTailConditioning:
    def test_tail_rides_in_the_instruction(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                # boundary 50/60 -> share 0.833 -> the window includes the '.'
                # so the accepted span is exactly the first sentence
                _boundary_text("First accepted span ends here. Trailing", 50),
                _boundary_text("Second.", 10),
            ],
            values=_config_values(obs_condition_tail_chars=12),
        )
        world.run()
        first_instruction = world.adapter.payloads[0]["task_instruction"]
        second_instruction = world.adapter.payloads[1]["task_instruction"]
        assert OBS_TAIL_FRAME_V1.split("{tail}")[0][:30] not in first_instruction
        expected_tail = "First accepted span ends here."[-12:]
        assert OBS_TAIL_FRAME_V1.format(tail=expected_tail) in second_instruction

    def test_zero_tail_chars_reproduces_the_unconditioned_loop_exactly(
        self, tmp_path, monkeypatch
    ):
        texts = [
            _boundary_text("First accepted span ends here. Trailing", 45),
            _boundary_text("Second.", 10),
        ]
        conditioned = _World(
            tmp_path / "a", monkeypatch, pcm=_noise(90.0), texts=list(texts),
            values=_config_values(obs_condition_tail_chars=0),
        )
        conditioned.run()
        plain_instruction = conditioned.ctx.task_instruction
        for payload in conditioned.adapter.payloads:
            assert "transcript so far" not in payload["task_instruction"]
            assert payload["task_instruction"].startswith(plain_instruction)


class TestEvidenceEveryIteration:
    def test_supplied_evidence_rides_every_request(self, tmp_path, monkeypatch):
        item = EvidenceItem(
            evidence_id="conec/4000001",
            source_uri="conec://earnings21/contexts/4000001.txt",
            content="ACME Corp, Q3, John Smith",
            provenance={"lock_key": "conec", "relpath": "x", "sha256": "e" * 64},
        )
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[_boundary_text("A.", 45), _boundary_text("B.", 10)],
            evidence=[item],
            arm="fixed-legal-context",
        )
        world.run()
        for payload in world.adapter.payloads:
            assert payload["supplied_evidence"][0]["content"] == "ACME Corp, Q3, John Smith"


class TestPreprocess:
    def test_rms_norm_records_pre_and_post_hashes(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(40.0),
            texts=[_boundary_text("Quiet speech.", 20)],
            values=_config_values(obs_preprocess=["rms-norm"]),
        )
        world.run()
        record = world.registry.lookup(
            SAMPLE_ID, world.adapter.payloads[0]["media_relpath"]
        )
        assert record.preprocess == ("rms-norm",)
        assert record.pre_sha256 is not None
        assert record.pre_sha256 != record.sha256


class TestConfigValidation:
    def test_min_above_max_refused(self, tmp_path):
        with pytest.raises(ObsLoopError, match="min <= max"):
            ObsLoopConfig.from_values(
                _config_values(obs_min_advance_seconds=56), tmp_path
            )

    def test_unknown_obs_key_refused(self, tmp_path):
        with pytest.raises(ObsLoopError, match="unknown obs-loop config keys"):
            ObsLoopConfig.from_values(
                _config_values(obs_bufffer_seconds=60), tmp_path
            )

    def test_model_mode_requires_a_boundary_prompt(self, tmp_path):
        values = _config_values()
        values.pop("obs_boundary_prompt")
        with pytest.raises(ObsLoopError, match="obs_boundary_prompt"):
            ObsLoopConfig.from_values(values, tmp_path)

    def test_missing_template_file_refused(self, tmp_path):
        with pytest.raises(ObsLoopError, match="cannot read"):
            ObsLoopConfig.from_values(_config_values(), tmp_path)

    def test_unsupported_preprocess_refused(self, tmp_path):
        with pytest.raises(ObsLoopError, match="unsupported transforms"):
            ObsLoopConfig.from_values(
                _config_values(obs_preprocess=["denoise"]), tmp_path
            )

    def test_slice_retry_max_parses_and_bad_values_refuse(self, tmp_path):
        fixed = {
            "obs_boundary_mode": "fixed",
            "obs_buffer_seconds": 30,
            "obs_min_advance_seconds": 30,
            "obs_max_advance_seconds": 30,
            "obs_fallback_advance_seconds": 30,
        }
        assert ObsLoopConfig.from_values(fixed, tmp_path).slice_retry_max == 1
        assert (
            ObsLoopConfig.from_values(
                dict(fixed, obs_slice_retry_max=0), tmp_path
            ).slice_retry_max
            == 0
        )
        assert (
            ObsLoopConfig.from_values(
                dict(fixed, obs_slice_retry_max=2), tmp_path
            ).slice_retry_max
            == 2
        )
        for bad in (-1, True, 1.5, "once"):
            with pytest.raises(ObsLoopError, match="obs_slice_retry_max"):
                ObsLoopConfig.from_values(dict(fixed, obs_slice_retry_max=bad), tmp_path)

    def test_missing_slice_registry_refused(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path, monkeypatch, pcm=_noise(30.0), texts=[_boundary_text("A.", 10)]
        )
        world.ctx.extras["slice_registry"] = None
        with pytest.raises(ObsLoopError, match="SliceRegistry"):
            world.run()


class TestSliceRetry:
    """Bounded per-slice retry (live E-001 finding, 2026-08-08): one slice
    request hung server-side and the whole attempt died. A retryable failure
    (timeout / FrozenCoreError) now gets ONE fresh, separately-metered
    request under a new request id; the second failure propagates
    fail-closed as before."""

    def test_flaky_slice_retries_once_and_completes(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                _boundary_text("First span done. Tail", 45),
                _boundary_text("Second done.", 10),
            ],
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={2})
        world.ctx.adapter = flaky
        outcome = world.run()
        # three attempts total: i0000 ok, i0001 timed out, i0001-r1 ok
        assert flaky.calls == 3
        assert flaky.failed_request_ids == ["req-0001-i0001"]
        assert outcome.request_ids == ("req-0001-i0000", "req-0001-i0001-r1")
        # the retry was a FRESH request: new request_id in the resent payload
        assert [p["request_id"] for p in world.adapter.payloads] == [
            "req-0001-i0000",
            "req-0001-i0001-r1",
        ]
        assert outcome.text == "First span done. Second done."
        # audit visibility: the OBS record carries retry_of
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = {
            document["record_id"]: document["payload"]
            for document in (json.loads(line) for line in raw.splitlines() if line)
        }
        assert records["req-0001-i0000/obs"]["obs_retry_of"] is None
        assert records["req-0001-i0001-r1/obs"]["obs_retry_of"] == "req-0001-i0001"

    def test_second_failure_propagates_fail_closed(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[_boundary_text("A.", 45), _boundary_text("B.", 10)],
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={2, 3})
        world.ctx.adapter = flaky
        with pytest.raises(TimeoutError):
            world.run()
        assert flaky.calls == 3
        assert flaky.failed_request_ids == ["req-0001-i0001", "req-0001-i0001-r1"]
        # only the first slice's text was ever consumed
        assert len(world.adapter.payloads) == 1

    def test_retry_zero_disables(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(30.0),
            texts=[_boundary_text("A.", 10)],
            values=_config_values(obs_slice_retry_max=0),
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={1})
        world.ctx.adapter = flaky
        with pytest.raises(TimeoutError):
            world.run()
        assert flaky.calls == 1

    def test_helper_retries_frozen_core_error_but_not_foreign_errors(self):
        from speech_aware_evidence_acquisition.core.model import FrozenCoreError
        from speech_aware_evidence_acquisition.reproduction.obs_loop import (
            request_slice_with_retry,
        )

        # FrozenCoreError (e.g. malformed response) is retryable
        outcomes = [FrozenCoreError("malformed"), "ok"]
        built = []

        def build(rid):
            built.append(rid)
            return {"request_id": rid}

        def flaky_request(payload):
            result = outcomes.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        rid, response, retry_of = request_slice_with_retry(
            flaky_request, build, "req-0001-i0007", 1
        )
        assert (rid, response, retry_of) == (
            "req-0001-i0007-r1",
            "ok",
            "req-0001-i0007",
        )
        assert built == ["req-0001-i0007", "req-0001-i0007-r1"]

        # a foreign error (a bug, not a transport/core failure) never retries
        def broken_request(payload):
            raise ValueError("bug")

        with pytest.raises(ValueError):
            request_slice_with_retry(broken_request, build, "req-0001-i0008", 1)

    def test_first_attempt_success_reports_no_retry(self):
        from speech_aware_evidence_acquisition.reproduction.obs_loop import (
            request_slice_with_retry,
        )

        rid, response, retry_of = request_slice_with_retry(
            lambda payload: "ok", lambda rid: {"request_id": rid}, "req-0001-i0000", 1
        )
        assert (rid, response, retry_of) == ("req-0001-i0000", "ok", None)


class TestBudgetArithmeticSanity:
    def test_iteration_count_matches_the_ceiling_model(self, tmp_path, monkeypatch):
        """~duration/mean_advance requests: every boundary resolves to 45s
        over 200s of audio -> cursors 0,45,90,135,180; [180,200) is final =
        5 windows; metered = 4x60 + 20 = 260s = 1.3x the call's duration
        (the tail-overlap fraction the runbook's budget arithmetic uses)."""

        texts = [_boundary_text(f"S{i}.", 45) for i in range(4)] + [
            _boundary_text("Last.", 10)
        ]
        world = _World(tmp_path, monkeypatch, pcm=_noise(200.0), texts=texts)
        world.run()
        assert len(world.adapter.payloads) == 5
        metered = sum(p["audio_seconds"] for p in world.adapter.payloads)
        assert metered == pytest.approx(60 * 4 + 20, abs=0.01)
        assert metered / world.duration == pytest.approx(1.3, abs=0.01)
