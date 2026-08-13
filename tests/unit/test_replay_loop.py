"""obs-replay-loop policy (listen-score-replay orchestration): tested
against a scripted fake adapter + a real TraceSink + a real SliceRegistry,
with the parent decode monkeypatched to synthetic PCM and
``core.span_surgery.align_words``/``cut_span`` monkeypatched to deterministic
fakes (no soundfile/ffmpeg/torch, no model, no real audio)."""

import hashlib
import json
from array import array
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.core.base import POLICIES, EvidenceItem, SampleContext
from speech_aware_evidence_acquisition.core.model import SliceRecord, SliceRegistry
from speech_aware_evidence_acquisition.core.tracing import TraceSink
from speech_aware_evidence_acquisition.data.loader import SampleRef
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
from speech_aware_evidence_acquisition.reproduction import obs_loop, replay_loop
from speech_aware_evidence_acquisition.reproduction.obs_loop import ObsAgentLoopPolicy
from speech_aware_evidence_acquisition.reproduction.replay_loop import (
    OBS_REPLAY_LOOP_POLICY_NAME,
    ObsReplayLoopPolicy,
    ReplayLoopConfig,
    ReplayLoopError,
    _extract_token_logprobs,
    _flag_spans_for_slice,
    _matching_exemplars,
    _word_logprob_scores,
)

RATE = 16000
RUN_ID = "SAEA-E-000-replayloop"
SAMPLE_ID = "4000001"
PARENT_RELPATH = "datasets/earnings21-22/earnings21/media/4000001.mp3"


def _noise(seconds: float, seed: int = 3) -> array:
    import random

    rng = random.Random(seed)
    return array(
        "h", (int(6000 * (2 * rng.random() - 1)) for _ in range(int(seconds * RATE)))
    )


class _FakeResponse:
    def __init__(self, text: str, tag: str, usage: dict | None = None, logprobs: object = None) -> None:
        self.text = text
        self.request_sha256 = hashlib.sha256(f"req-{tag}".encode()).hexdigest()
        self.response_sha256 = hashlib.sha256(f"resp-{tag}".encode()).hexdigest()
        self.response_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.usage = usage if usage is not None else {}
        self.logprobs = logprobs


class _ScriptedAdapter:
    """Returns the scripted texts in order and records every payload -- the
    SAME single ``.payloads``/``.texts`` stream serves BOTH PASS 1 slice
    requests (routed through the recorder wrapper) and REPLAY requests
    (sent directly via ``ctx.adapter``), since both ultimately call this
    one adapter's ``request`` in call order."""

    def __init__(self, texts: list[str], usages: list[dict | None] | None = None, logprobs: list[object] | None = None) -> None:
        self._texts = list(texts)
        self._usages = list(usages) if usages is not None else [None] * len(texts)
        self._logprobs = list(logprobs) if logprobs is not None else [None] * len(texts)
        self.payloads: list[dict] = []

    def request(self, payload):
        self.payloads.append(dict(payload))
        if not self._texts:
            raise AssertionError("policy sent more requests than the script expected")
        text = self._texts.pop(0)
        usage = self._usages.pop(0) if self._usages else None
        logprobs = self._logprobs.pop(0) if self._logprobs else None
        return _FakeResponse(text, tag=str(len(self.payloads)), usage=usage, logprobs=logprobs)


def _fixed_mode_values(**overrides):
    """Deterministic fixed-mode config satisfying the policy's own legality
    matrix (obs_boundary_mode='fixed', obs_condition_tail_chars=0,
    obs_vad_trim_min_seconds=0) plus a permissive-by-default replay_*
    surface a happy-path test can override piecemeal."""

    values = {
        "obs_buffer_seconds": 40,
        "obs_min_advance_seconds": 40,
        "obs_max_advance_seconds": 40,
        "obs_fallback_advance_seconds": 40,
        "obs_silence_snap_seconds": 0,
        "obs_boundary_mode": "fixed",
        "obs_vad": "energy",
        "obs_vad_trim_min_seconds": 0,
        "obs_preprocess": [],
        "obs_condition_tail_chars": 0,
        "obs_batch_slices": 1,
        "replay_trigger": "wps",
        "replay_flag_low_threshold": -2.0,
        "replay_flag_min_run": 1,
        "replay_max_spans_per_slice": 3,
        "replay_span_pad_s": 0.1,
        "replay_context_s": 0.5,
        "replay_k": 3,
        "replay_min_score": 0.3,
        "replay_instruction": "Listen again and correct the flagged words.",
        "replay_len_ratio_max": 3.0,
        "replay_logprobs": False,
    }
    values.update(overrides)
    return values


def _fake_align_words(audio_path, words, device="cpu"):
    """One word per second, in input order -- deterministic, no torch/MMS_FA."""

    return [
        {"word": word, "start_s": float(index), "end_s": float(index) + 1.0}
        for index, word in enumerate(words)
    ]


def _fake_cut_span(audio_path, start_s, end_s, pad_s, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(f"cut:{start_s}:{end_s}:{pad_s}".encode("utf-8"))
    return out_path


class _World:
    def __init__(
        self,
        tmp_path: Path,
        monkeypatch,
        *,
        pcm: array,
        texts: list[str],
        values=None,
        evidence=None,
        arm="bare-core",
        usages=None,
        logprobs=None,
        exemplar_bank=None,
        decoding_params=None,
    ):
        self.data_root = tmp_path / "data"
        self.run_dir = tmp_path / "run"
        self.repo_root = tmp_path / "repo"
        parent = self.data_root / PARENT_RELPATH
        parent.parent.mkdir(parents=True)
        parent.write_bytes(b"fake-mp3-bytes-for-" + SAMPLE_ID.encode())
        self.duration = len(pcm) / RATE
        monkeypatch.setattr(obs_loop, "decode_parent_pcm", lambda path, rate=RATE: pcm)
        monkeypatch.setattr(replay_loop, "align_words", _fake_align_words)
        monkeypatch.setattr(replay_loop, "cut_span", _fake_cut_span)
        self.registry = SliceRegistry(
            data_root=self.data_root,
            run_id=RUN_ID,
            parent_facts={SAMPLE_ID: (PARENT_RELPATH, self.duration)},
        )
        self.adapter = _ScriptedAdapter(texts, usages=usages, logprobs=logprobs)
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
            decoding_params=decoding_params if decoding_params is not None else {"temperature": 0},
            request_id_base="req-0001",
            exemplar_bank=exemplar_bank,
            extras={
                "slice_registry": self.registry,
                "data_root": self.data_root,
                "run_dir": self.run_dir,
                "repo_root": self.repo_root,
                "config_values": values or _fixed_mode_values(),
            },
        )

    def run(self):
        return ObsReplayLoopPolicy().run_sample(self.ctx)

    def replay_records(self) -> list[dict]:
        raw = (self.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        return [
            json.loads(line)["payload"]
            for line in raw.splitlines()
            if line and json.loads(line)["channel"] == "REPLAY"
        ]


def test_policy_is_registered():
    assert POLICIES.resolve(OBS_REPLAY_LOOP_POLICY_NAME) is not None


# ---------------------------------------------------------------------------
# Legality matrix
# ---------------------------------------------------------------------------


class TestLegalityMatrix:
    @pytest.mark.parametrize(
        "override,message",
        [
            ({"obs_boundary_mode": "model"}, "obs_boundary_mode"),
            ({"obs_condition_tail_chars": 40}, "obs_condition_tail_chars"),
            ({"obs_vad_trim_min_seconds": 5.0}, "obs_vad_trim_min_seconds"),
        ],
    )
    def test_refuses_non_fixed_window_configuration(self, tmp_path, monkeypatch, override, message):
        values = _fixed_mode_values(**override)
        if override.get("obs_boundary_mode") == "model":
            values["obs_boundary_prompt"] = "probes/obs_boundary_v1.txt"
            template = tmp_path / "repo" / "configs" / "probes" / "obs_boundary_v1.txt"
            template.parent.mkdir(parents=True, exist_ok=True)
            template.write_text("BOUNDARY_SECONDS as instructed.\n", encoding="utf-8")
        world = _World(tmp_path, monkeypatch, pcm=_noise(40.0), texts=["one two."], values=values)
        with pytest.raises(ReplayLoopError, match=message):
            world.run()

    def test_unknown_replay_key_is_refused(self, tmp_path, monkeypatch):
        values = _fixed_mode_values()
        values["replay_typo_key"] = 1
        world = _World(tmp_path, monkeypatch, pcm=_noise(40.0), texts=["one two."], values=values)
        with pytest.raises(ReplayLoopError, match="unknown obs-replay-loop config keys"):
            world.run()

    def test_missing_flag_low_threshold_is_required_no_default(self, tmp_path, monkeypatch):
        values = _fixed_mode_values()
        del values["replay_flag_low_threshold"]
        world = _World(tmp_path, monkeypatch, pcm=_noise(40.0), texts=["one two."], values=values)
        with pytest.raises(ReplayLoopError, match="replay_flag_low_threshold"):
            world.run()

    def test_replay_instruction_is_required_non_empty(self, tmp_path, monkeypatch):
        values = _fixed_mode_values(replay_instruction="")
        world = _World(tmp_path, monkeypatch, pcm=_noise(40.0), texts=["one two."], values=values)
        with pytest.raises(ReplayLoopError, match="replay_instruction"):
            world.run()

    def test_replay_k_capped_at_five(self, tmp_path, monkeypatch):
        values = _fixed_mode_values(replay_k=6)
        world = _World(tmp_path, monkeypatch, pcm=_noise(40.0), texts=["one two."], values=values)
        with pytest.raises(ReplayLoopError, match="replay_k"):
            world.run()


# ---------------------------------------------------------------------------
# Config parsing (pure)
# ---------------------------------------------------------------------------


class TestReplayLoopConfigDefaults:
    def test_defaults_applied(self):
        cfg = ReplayLoopConfig.from_values(
            {
                "replay_trigger": "both",
                "replay_flag_low_threshold": -1.5,
                "replay_flag_min_run": 2,
                "replay_max_spans_per_slice": 2,
                "replay_instruction": "Listen again.",
            }
        )
        assert cfg.span_pad_s == 0.3
        assert cfg.context_s == 5.0
        assert cfg.k == 3
        assert cfg.min_score == 0.5
        assert cfg.len_ratio_max == 3.0
        assert cfg.logprobs is False


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


class TestWordLogprobScores:
    def test_bucket_mapping_is_positional_and_deterministic(self):
        token_logprobs = [-0.1, -0.2, -5.0, -0.3, -0.4, -0.1]
        scores = _word_logprob_scores(3, token_logprobs)
        assert scores == _word_logprob_scores(3, token_logprobs)  # deterministic
        assert len(scores) == 3
        # 6 tokens over 3 words -> 2 tokens/word; the middle bucket holds -5.0.
        assert scores[1] == -5.0

    def test_empty_or_zero_word_count_returns_none(self):
        assert _word_logprob_scores(0, [-0.1]) is None
        assert _word_logprob_scores(3, []) is None


class TestExtractTokenLogprobs:
    def test_filters_non_finite_and_malformed_entries(self):
        logprobs = {
            "content": [
                {"token": "a", "logprob": -0.1},
                {"token": "b", "logprob": float("nan")},
                {"token": "c"},
                "not-a-mapping",
                {"token": "d", "logprob": -0.2},
            ]
        }
        assert _extract_token_logprobs(logprobs) == [-0.1, -0.2]

    def test_missing_or_malformed_object_returns_empty(self):
        assert _extract_token_logprobs(None) == []
        assert _extract_token_logprobs({"no_content": True}) == []
        assert _extract_token_logprobs({"content": "not-a-list"}) == []


class TestFlagSpansForSlice:
    def _cfg(self, **overrides):
        return ReplayLoopConfig.from_values(
            {
                "replay_trigger": "both",
                "replay_flag_low_threshold": -2.0,
                "replay_flag_min_run": 1,
                "replay_max_spans_per_slice": 5,
                "replay_instruction": "x",
                **overrides,
            }
        )

    def test_wps_trigger_flags_the_whole_slice(self):
        words = ["a", "b"]  # 2 words over 40s -> catastrophic
        spans = _flag_spans_for_slice(words, None, 40.0, self._cfg(replay_trigger="wps"))
        assert spans == [((0, 2), "wps")]

    def test_healthy_wps_flags_nothing(self):
        words = [f"w{i}" for i in range(100)]  # 100 words / 40s = 2.5 wps, healthy
        spans = _flag_spans_for_slice(words, None, 40.0, self._cfg(replay_trigger="wps"))
        assert spans == []

    def test_logprob_trigger_flags_low_scoring_runs(self):
        words = [f"w{i}" for i in range(100)]  # healthy wps, so only logprob fires
        scores = [0.0] * 100
        scores[10] = -5.0
        spans = _flag_spans_for_slice(words, scores, 40.0, self._cfg(replay_trigger="logprob"))
        assert spans == [((10, 11), "logprob")]

    def test_both_trigger_labels_a_span_hit_by_both_families(self):
        words = ["a", "b"]
        scores = [-5.0, -5.0]
        spans = _flag_spans_for_slice(words, scores, 40.0, self._cfg(replay_trigger="both"))
        assert spans == [((0, 2), "logprob,wps")]

    def test_cap_truncates_in_ascending_start_order(self):
        words = [f"w{i}" for i in range(20)]
        scores = [0.0] * 20
        for i in (1, 5, 10):
            scores[i] = -5.0
        cfg = self._cfg(replay_trigger="logprob", replay_max_spans_per_slice=2)
        spans = _flag_spans_for_slice(words, scores, 40.0, cfg)
        assert [span for span, _label in spans] == [(1, 2), (5, 6)]


class TestMatchingExemplars:
    def test_matches_by_normalized_label(self):
        bank = ({"media_relpath": "x.wav", "label": "Acme Corp"},)
        assert _matching_exemplars(bank, ["acme corp"]) == [dict(bank[0])]

    def test_no_bank_or_no_retrieved_terms_yields_empty(self):
        assert _matching_exemplars(None, ["acme"]) == []
        assert _matching_exemplars(({"media_relpath": "x.wav", "label": "acme"},), []) == []

    def test_non_matching_label_is_excluded(self):
        bank = ({"media_relpath": "x.wav", "label": "zulu"},)
        assert _matching_exemplars(bank, ["acme"]) == []


# ---------------------------------------------------------------------------
# Empty-flag fast path: byte-identical to plain obs-agent-loop
# ---------------------------------------------------------------------------


class TestEmptyFlagFastPath:
    def test_zero_spans_makes_zero_replay_calls_and_matches_plain_obs_loop(
        self, tmp_path, monkeypatch
    ):
        # 100 words over 40s -> healthy wps, no logprobs supplied -> nothing
        # ever flagged for either trigger family.
        text = " ".join(f"w{i}" for i in range(100)) + "."
        world = _World(tmp_path / "replay", monkeypatch, pcm=_noise(40.0), texts=[text])
        replay_outcome = world.run()
        assert len(world.adapter.payloads) == 1  # PASS 1 only, zero REPLAY calls
        assert world.replay_records() == []

        # Same inputs through the plain obs-agent-loop policy must produce a
        # byte-identical SampleOutcome.
        plain_world = _World(tmp_path / "plain", monkeypatch, pcm=_noise(40.0), texts=[text])
        plain_outcome = ObsAgentLoopPolicy().run_sample(plain_world.ctx)

        assert replay_outcome.text == plain_outcome.text
        assert replay_outcome.request_ids == plain_outcome.request_ids
        assert replay_outcome.request_sha256 == plain_outcome.request_sha256
        assert replay_outcome.response_sha256 == plain_outcome.response_sha256
        assert replay_outcome.response_text_sha256 == plain_outcome.response_text_sha256


# ---------------------------------------------------------------------------
# Flag -> locate -> retrieve -> payload assembly (mocked transport)
# ---------------------------------------------------------------------------


def _fake_slice_record(iteration: int = 0, audio_seconds: float = 40.0) -> SliceRecord:
    return SliceRecord(
        sample_id=SAMPLE_ID,
        parent_media_relpath=PARENT_RELPATH,
        parent_sha256="0" * 64,
        start_seconds=0.0,
        end_seconds=audio_seconds,
        audio_seconds=audio_seconds,
        sample_rate_hz=RATE,
        media_relpath=f"derived/obs-slices/{RUN_ID}/{SAMPLE_ID}/i{iteration:04d}.wav",
        sha256="1" * 64,
        bytes=1234,
        iteration=iteration,
        preprocess=(),
        pre_sha256=None,
    )


def _stub_pass1(monkeypatch, *, accepted_spans, slice_records):
    """Replaces ``ObsAgentLoopPolicy._slice_parallel_pass`` with a canned
    result -- isolates SCORE/LOCATE/RETRIEVE/REPLAY payload assembly from
    PASS 1's own D2-frozen field-set constraints (see
    TestReplayPayloadAssembly's own module comment for why: PASS 1's call
    site, reused verbatim, never threads ``delta_candidates`` -- extending
    an arm's ARM_VISIBLE_FIELDS to require it for a successful REPLAY
    attachment would ALSO require every PASS 1 slice payload for that arm
    to carry the identical field, which the reused, unmodified
    ``reproduction.obs_loop`` call site cannot do without being forked)."""

    request_ids = [f"req-0001-i{r.iteration:04d}" for r in slice_records]
    hashes = [f"sha-{i}" for i in range(len(slice_records))]

    def fake(self, ctx, cfg, registry, data_root, sample, rate, pcm, duration, parent_sha256, engine_descriptor, evidence, max_tokens):
        return (list(accepted_spans), request_ids, list(hashes), list(hashes), list(slice_records), 0, 0, len(slice_records))

    monkeypatch.setattr(ObsAgentLoopPolicy, "_slice_parallel_pass", fake)


class TestReplayPayloadAssembly:
    """flag -> locate -> retrieve -> payload assembly, mocked-transport
    capture. PASS 1 itself is stubbed (see ``_stub_pass1``) so these tests
    isolate REPLAY's own payload assembly from PASS 1's D2-frozen field-set
    coupling -- ``TestReplayPayloadAssembly.
    test_replay_call_refused_when_arm_does_not_declare_the_attached_tier``
    below (which does NOT stub PASS 1) instead exercises the real,
    end-to-end fail-closed behaviour against today's registered arms."""

    _EVIDENCE = [
        EvidenceItem(
            evidence_id="conec/4000001",
            source_uri="conec://earnings21/contexts/4000001.txt",
            content="acme merger guidance revenue outlook",
            provenance={"lock_key": "conec", "relpath": "x.txt", "sha256": "0" * 64},
        )
    ]

    def _values(self, **overrides):
        return _fixed_mode_values(evidence_source="conec-contexts", **overrides)

    def test_flagged_span_triggers_one_replay_call_with_v3_shaped_payload(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setitem(
            ARM_VISIBLE_FIELDS,
            "bare-core",
            ARM_VISIBLE_FIELDS["bare-core"] + ("exemplar_bank", "delta_candidates"),
        )
        _stub_pass1(monkeypatch, accepted_spans=["acme zzz"], slice_records=[_fake_slice_record()])
        # "acme" exact-matches the evidence pack term, "zzz" does not.
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(40.0),
            texts=["corrected replay text"],  # only the REPLAY call consumes this
            values=self._values(),
            evidence=self._EVIDENCE,
            exemplar_bank=({"media_relpath": "derived/exemplar-pairs/mc2-v1/4000001/acme.wav", "label": "acme"},),
        )
        outcome = world.run()

        assert len(world.adapter.payloads) == 1  # only the REPLAY call
        replay_payload = world.adapter.payloads[0]
        assert replay_payload["task_instruction"] == "Listen again and correct the flagged words."
        assert replay_payload["media_relpath"] != PARENT_RELPATH
        assert "derived/obs-slices/" in replay_payload["media_relpath"]
        assert replay_payload["exemplar_bank"] == [
            {"media_relpath": "derived/exemplar-pairs/mc2-v1/4000001/acme.wav", "label": "acme"}
        ]
        assert replay_payload["delta_candidates"] == [{"text": "acme"}]

        records = world.replay_records()
        assert len(records) == 1
        record = records[0]
        assert record["replay_trigger"] == "wps"
        assert record["replay_pass1_text"] == "acme zzz"
        assert record["replay_replay_text"] == "corrected replay text"
        assert record["replay_accepted"] is True
        assert record["replay_candidates"] == [{"text": "acme", "score": 1.0}]
        assert record["replay_exemplars_attached"] == ["acme"]
        # Splice landed in the final stitched text.
        assert outcome.text == "corrected replay text"

    def test_delta_candidates_clamped_to_transport_cap_even_with_more_retrieved(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setitem(
            ARM_VISIBLE_FIELDS,
            "bare-core",
            ARM_VISIBLE_FIELDS["bare-core"] + ("delta_candidates",),
        )
        _stub_pass1(monkeypatch, accepted_spans=["acme"], slice_records=[_fake_slice_record()])
        evidence = [
            EvidenceItem(
                evidence_id="conec/4000001",
                source_uri="conec://x",
                content="acme acmeco acmetwo acmethree acmefour",
                provenance={"lock_key": "conec", "relpath": "x.txt", "sha256": "0" * 64},
            )
        ]
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(40.0),
            texts=["still acme"],
            values=self._values(replay_k=5, replay_min_score=0.1),
            evidence=evidence,
        )
        world.run()
        replay_payload = world.adapter.payloads[0]
        assert len(replay_payload["delta_candidates"]) <= replay_loop.TRANSPORT_DELTA_CANDIDATE_CAP
        records = world.replay_records()
        # Full retrieved set (up to replay_k) is still recorded for audit.
        assert len(records[0]["replay_candidates"]) >= len(replay_payload["delta_candidates"])
        assert len(records[0]["replay_candidates"]) > replay_loop.TRANSPORT_DELTA_CANDIDATE_CAP

    def test_no_pack_terms_means_no_candidates_and_no_exemplar_match(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(40.0),
            texts=["acme zzz.", "corrected"],
            values=self._values(),
            evidence=[],  # nothing to retrieve against
        )
        world.run()
        record = world.replay_records()[0]
        assert record["replay_candidates"] == []
        assert record["replay_exemplars_attached"] == []

    def test_unsupported_evidence_source_yields_an_empty_pack_not_an_error(
        self, tmp_path, monkeypatch
    ):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(40.0),
            texts=["acme zzz.", "corrected"],
            values=_fixed_mode_values(evidence_source="none"),
            evidence=self._EVIDENCE,
        )
        world.run()  # must not raise
        record = world.replay_records()[0]
        assert record["replay_candidates"] == []

    def test_replay_call_refused_when_arm_does_not_declare_the_attached_tier(
        self, tmp_path, monkeypatch
    ):
        """bare-core does NOT declare exemplar_bank/delta_candidates today
        (module docstring); a REPLAY call that has real content to attach
        fails closed rather than silently dropping it."""

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(40.0),
            texts=["acme zzz.", "corrected"],
            values=self._values(),
            evidence=self._EVIDENCE,
        )
        with pytest.raises(ReplayLoopError, match="delta_candidates"):
            world.run()


# ---------------------------------------------------------------------------
# ACCEPT: splice matrix
# ---------------------------------------------------------------------------


class TestAcceptRejectSplice:
    def _world(self, tmp_path, monkeypatch, replay_text, **value_overrides):
        return _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(40.0),
            texts=["acme zzz", replay_text],
            values=_fixed_mode_values(**value_overrides),
        )

    def test_accepted_replacement_splices_into_the_stitched_text(self, tmp_path, monkeypatch):
        world = self._world(tmp_path, monkeypatch, "corrected words here")
        outcome = world.run()
        assert outcome.text == "corrected words here"
        assert world.replay_records()[0]["replay_accepted"] is True
        assert world.replay_records()[0]["replay_reject_reason"] is None

    def test_empty_replay_output_is_rejected(self, tmp_path, monkeypatch):
        world = self._world(tmp_path, monkeypatch, "   ")
        outcome = world.run()
        assert outcome.text == "acme zzz"
        record = world.replay_records()[0]
        assert record["replay_accepted"] is False
        assert record["replay_reject_reason"] == "empty-replay-output"

    def test_unchanged_text_is_rejected(self, tmp_path, monkeypatch):
        world = self._world(tmp_path, monkeypatch, "Acme ZZZ")  # same words, different case
        outcome = world.run()
        assert outcome.text == "acme zzz"
        record = world.replay_records()[0]
        assert record["replay_accepted"] is False
        assert record["replay_reject_reason"] == "replay-text-unchanged"

    def test_length_ratio_guard_rejects_a_runaway_replay(self, tmp_path, monkeypatch):
        runaway = " ".join(["word"] * 10)  # 10 words vs 2 flagged * 3.0 ratio = max 6
        world = self._world(tmp_path, monkeypatch, runaway, replay_len_ratio_max=3.0)
        outcome = world.run()
        assert outcome.text == "acme zzz"
        record = world.replay_records()[0]
        assert record["replay_accepted"] is False
        assert record["replay_reject_reason"] == "length-ratio-exceeded"

    def test_length_ratio_guard_boundary_is_inclusive(self, tmp_path, monkeypatch):
        exactly_at_ratio = " ".join(["word"] * 6)  # 6 == 2 * 3.0, must be accepted
        world = self._world(tmp_path, monkeypatch, exactly_at_ratio, replay_len_ratio_max=3.0)
        outcome = world.run()
        assert outcome.text == exactly_at_ratio
        assert world.replay_records()[0]["replay_accepted"] is True


# ---------------------------------------------------------------------------
# Trace record shapes
# ---------------------------------------------------------------------------


class TestTraceRecordShapes:
    def test_replay_channel_payload_keys_are_all_replay_prefixed(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path, monkeypatch, pcm=_noise(40.0), texts=["acme zzz.", "corrected words"]
        )
        world.run()
        record = world.replay_records()[0]
        assert all(key.startswith("replay_") for key in record)

    def test_replay_derivation_artifact_is_written(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path, monkeypatch, pcm=_noise(40.0), texts=["acme zzz.", "corrected words"]
        )
        world.run()
        artifact_path = world.run_dir / f"{RUN_ID}.replay-derivation.{SAMPLE_ID}.json"
        assert artifact_path.is_file()
        document = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert document["schema"] == replay_loop.REPLAY_DERIVATION_SCHEMA
        assert len(document["pass1_slices"]) == 1
        assert len(document["replay_windows"]) == 1

    def test_stitch_records_still_carry_only_pass1_request_ids(self, tmp_path, monkeypatch):
        """Design-boundary check (module docstring): the top-level
        stitch's own MODEL_REQUEST/RESPONSE records name only PASS 1's
        slice request ids -- REPLAY's own hashes live in the REPLAY
        channel, never folded into the stitch descriptor."""

        world = _World(
            tmp_path, monkeypatch, pcm=_noise(40.0), texts=["acme zzz.", "corrected words"]
        )
        outcome = world.run()
        assert outcome.request_ids == ("req-0001-i0000",)
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = {
            json.loads(line)["record_id"]: json.loads(line)
            for line in raw.splitlines()
            if line
        }
        assert records["req-0001/request"]["payload"]["stitched_request_ids"] == ["req-0001-i0000"]

    def test_replay_call_gets_its_own_model_request_response_cost_records(
        self, tmp_path, monkeypatch
    ):
        """Cost accounting: REPLAY calls ride ctx.adapter.request() directly
        -- but this test's fake adapter is not the real metering
        FrozenCoreAdapter, so the assertion here is scoped to what this
        policy controls: exactly one adapter.request() call per flagged
        span, in addition to PASS 1's own calls (test_frozen_core_adapter.py
        covers the real adapter's own MODEL_REQUEST/MODEL_RESPONSE/COST
        emission for every request() call uniformly, REPLAY included)."""

        world = _World(
            tmp_path, monkeypatch, pcm=_noise(40.0), texts=["acme zzz.", "corrected words"]
        )
        world.run()
        assert len(world.adapter.payloads) == 2


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_inputs_produce_the_same_outcome_and_trace(self, tmp_path, monkeypatch):
        world_a = _World(
            tmp_path / "a", monkeypatch, pcm=_noise(40.0), texts=["acme zzz.", "corrected words"]
        )
        outcome_a = world_a.run()
        world_b = _World(
            tmp_path / "b", monkeypatch, pcm=_noise(40.0), texts=["acme zzz.", "corrected words"]
        )
        outcome_b = world_b.run()

        assert outcome_a.text == outcome_b.text
        assert outcome_a.response_text_sha256 == outcome_b.response_text_sha256
        records_a = [
            {k: v for k, v in record.items() if k != "replay_window_relpath"}
            for record in world_a.replay_records()
        ]
        records_b = [
            {k: v for k, v in record.items() if k != "replay_window_relpath"}
            for record in world_b.replay_records()
        ]
        assert records_a == records_b


# ---------------------------------------------------------------------------
# Multi-span splice within one slice
# ---------------------------------------------------------------------------


class TestMultiSpanSplice:
    def test_two_accepted_spans_in_one_slice_both_apply_without_index_drift(
        self, tmp_path, monkeypatch
    ):
        # 8 words, healthy wps (8/40=0.2 -> actually catastrophic; use logprob
        # trigger only with two independent low-scoring runs so wps never
        # fires and only the two explicit spans are flagged.
        words = ["one", "two", "three", "four", "five", "six", "seven", "eight"]
        text = " ".join(words)
        scores = [0.0] * 8
        scores[1] = -5.0  # flags word index 1 ("two")
        scores[6] = -5.0  # flags word index 6 ("seven")

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(40.0),
            texts=[text, "TWO-REPLACED", "SEVEN-REPLACED"],
            values=_fixed_mode_values(
                replay_trigger="logprob", replay_flag_low_threshold=-2.0, replay_flag_min_run=1
            ),
        )

        # Inject logprobs on the PASS-1 response so the logprob trigger has
        # something to bucket: 8 tokens, one per word, matching `scores`.
        world.adapter._logprobs[0] = {
            "content": [{"token": w, "logprob": s} for w, s in zip(words, scores)]
        }
        world.ctx.extras["config_values"] = _fixed_mode_values(
            replay_trigger="logprob",
            replay_flag_low_threshold=-2.0,
            replay_flag_min_run=1,
            replay_logprobs=True,
        )

        outcome = world.run()
        assert outcome.text == "one TWO-REPLACED three four five six SEVEN-REPLACED eight"
        records = world.replay_records()
        assert len(records) == 2
        assert records[0]["replay_span_start_word"] == 1
        assert records[1]["replay_span_start_word"] == 6
