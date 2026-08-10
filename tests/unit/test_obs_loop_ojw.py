"""obs-agent-loop-ojw: the openJiuwen executor against the plain reference.

Red line 3 of the adoption memo (docs/readiness/2026-08-08-openjiuwen-
adoption.md): the openJiuwen executor must reproduce the plain-Python
``obs-agent-loop`` policy's behaviour on the same inputs before any
registered run uses it. Both executors run here over the SAME synthetic
fixtures (scripted fake adapter, synthetic PCM, monkeypatched decode — the
exact ``_World`` harness of ``test_obs_loop_policy``) and must produce:

- identical accepted-span sequences (re-derived per side from that side's
  own OBS trace records through the frozen pure functions, and pinned a
  second way by the tail-conditioning scenario, whose 4000-char tail embeds
  the entire stitched-so-far text into every subsequent request payload);
- identical slice derivation records (byte-for-byte);
- identical stitched output text and outputs-row hashes;
- identical trace record sequences (only the fake adapter emits no
  MODEL_REQUEST/COST records on either side; the volatile
  ``latency_seconds`` field is stripped defensively).

Determinism: the framework body is a LINEAR four-node chain, so every
Pregel super-step has exactly one ready node; ``test_determinism_five_runs``
verifies empirically that five fresh executor runs produce byte-identical
artifacts (and match the plain reference).

Requires openjiuwen (skip marker otherwise — D2 gate: the suite must pass
with openjiuwen absent; see ``test_obs_loop_ojw_absent.py``).
"""

import dataclasses
import hashlib
import json
import threading
from pathlib import Path

import pytest

pytest.importorskip(
    "openjiuwen",
    reason="openjiuwen not installed; the ojw executor is exercised only in "
    "the pinned WSL research venv (D2: never a pyproject dependency)",
)

import speech_aware_evidence_acquisition.core  # noqa: F401,E402 (populate registries)
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    POLICIES,
    EvidenceItem,
    SampleContext,
)
from speech_aware_evidence_acquisition.core.model import SliceRegistry  # noqa: E402
from speech_aware_evidence_acquisition.core.tracing import (  # noqa: E402
    TraceBuffer,
    TraceSink,
)
from speech_aware_evidence_acquisition.data.loader import SampleRef  # noqa: E402
from speech_aware_evidence_acquisition.reproduction import obs_loop  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.obs_audio import (  # noqa: E402
    accept_up_to_boundary,
    parse_boundary_response,
)
from speech_aware_evidence_acquisition.reproduction.obs_loop import (  # noqa: E402
    OBS_LOOP_POLICY_NAME,
    ObsLoopError,
)
from speech_aware_evidence_acquisition.reproduction.ojw import OJW_POLICY_NAME  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.ojw.components import (  # noqa: E402
    FrozenCoreASR,
)

from test_obs_loop_policy import (  # noqa: E402
    RUN_ID,
    SAMPLE_ID,
    _FlakyAdapter,
    _World,
    _boundary_text,
    _concat,
    _config_values,
    _fixed_mode_skip_values,
    _noise,
    _obs_payloads,
    _silence,
)


def _scenario(name):
    """(pcm, texts, values, evidence, arm) per scenario — every behavioural
    surface of the plain policy the ojw executor must reproduce."""

    if name == "model-tails":
        return dict(
            pcm=_noise(150.0),
            texts=[
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
            # 4000-char tail >= any stitched text here: every request payload
            # embeds the FULL accumulated span text, so payload equality pins
            # the accepted-span sequence directly.
            values=_config_values(obs_condition_tail_chars=4000),
        )
    if name == "vad-trim":
        return dict(
            pcm=_concat(_silence(10.0), _noise(55.0)),
            texts=[_boundary_text("Speech only.", 30)],
            values=_config_values(),
        )
    if name == "fixed-ablation":
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
        return dict(
            pcm=_noise(75.0),
            texts=["span one", "span two", "span three"],
            values=values,
        )
    if name == "evidence-arm":
        item = EvidenceItem(
            evidence_id="conec/4000001",
            source_uri="conec://earnings21/contexts/4000001.txt",
            content="ACME Corp, Q3, John Smith",
            provenance={"lock_key": "conec", "relpath": "x", "sha256": "e" * 64},
        )
        return dict(
            pcm=_noise(90.0),
            texts=[_boundary_text("A. spill", 45), _boundary_text("B.", 10)],
            values=_config_values(obs_condition_tail_chars=400),
            evidence=[item],
            arm="fixed-legal-context",
        )
    if name == "rms-norm":
        return dict(
            pcm=_noise(40.0),
            texts=[_boundary_text("Quiet speech.", 20)],
            values=_config_values(obs_preprocess=["rms-norm"]),
        )
    if name == "fallback-boundary":
        return dict(
            pcm=_noise(90.0),
            texts=["no boundary line at all here.", _boundary_text("Tail end.", 10)],
            values=_config_values(),
        )
    if name == "retry-flaky":
        # live E-001 finding (2026-08-08): call #2 times out once, the retry
        # succeeds under a fresh request id -- both executors must retry
        # IDENTICALLY (same retry id, same trace, same metered sequence)
        return dict(
            pcm=_noise(150.0),
            texts=[
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
            values=_config_values(obs_condition_tail_chars=4000),
            flaky_calls=(2,),
        )
    if name == "retry-exhausted-skip":
        # Task 2 (2026-08-09): call #2 AND its retry (#3) both time out --
        # exhausted, skipped (never aborted) -- both executors must reach
        # byte-identical records for the surviving slices AND the skip
        # itself (obs_skipped, skipped_slices, the shortened stitch).
        return dict(
            pcm=_noise(150.0),
            texts=[
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
            values=_config_values(obs_condition_tail_chars=4000),
            flaky_calls=(2, 3),
        )
    raise AssertionError(name)


SCENARIOS = (
    "model-tails",
    "vad-trim",
    "fixed-ablation",
    "evidence-arm",
    "rms-norm",
    "fallback-boundary",
    "retry-flaky",
    "retry-exhausted-skip",
)


def _run(tmp_path, monkeypatch, policy_name, scenario):
    world = _World(
        tmp_path,
        monkeypatch,
        pcm=scenario["pcm"],
        texts=list(scenario["texts"]),
        values=dict(scenario["values"]),
        evidence=scenario.get("evidence"),
        arm=scenario.get("arm", "bare-core"),
    )
    if scenario.get("flaky_calls"):
        world.ctx.adapter = _FlakyAdapter(world.adapter, scenario["flaky_calls"])
    outcome = POLICIES.resolve(policy_name).run_sample(world.ctx)
    return world, outcome


def _trace_records(world):
    raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
    records = [json.loads(line) for line in raw.splitlines() if line]
    for record in records:
        payload = record.get("payload")
        if isinstance(payload, dict):
            payload.pop("latency_seconds", None)  # volatile (COST); defensive
    return records


def _derivation_bytes(world):
    return (world.run_dir / f"{RUN_ID}.obs-derivation.{SAMPLE_ID}.json").read_bytes()


def _accepted_spans(world, scenario):
    """Re-derive the accepted-span sequence from this world's own OBS trace
    records through the frozen pure functions (module docstring)."""

    obs = [
        record["payload"]
        for record in _trace_records(world)
        if record["record_id"].startswith("req-0001-i")
        and record["record_id"].endswith("/obs")
    ]
    obs.sort(key=lambda payload: payload["obs_iteration"])
    values = scenario["values"]
    spans = []
    for payload, text in zip(obs, list(scenario["texts"]), strict=True):
        if values.get("obs_boundary_mode", "model") == "model":
            transcript, _ = parse_boundary_response(text)
        else:
            transcript = text.strip()
        if payload["obs_final_window"] or values.get("obs_boundary_mode") == "fixed":
            accepted = transcript
        else:
            slice_seconds = (
                payload["obs_window_end_seconds"] - payload["obs_window_start_seconds"]
            )
            accepted, _ = accept_up_to_boundary(
                transcript, payload["obs_boundary_advance_seconds"] / slice_seconds
            )
        spans.append(accepted.strip())
    return spans


def _fingerprint(world, outcome):
    document = {
        "trace": _trace_records(world),
        "derivation": _derivation_bytes(world).decode("utf-8"),
        "outcome": dataclasses.asdict(outcome),
    }
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TestEquivalence:
    @pytest.mark.parametrize("name", SCENARIOS)
    def test_ojw_reproduces_the_plain_policy(self, tmp_path, monkeypatch, name):
        scenario = _scenario(name)
        plain_world, plain_outcome = _run(
            tmp_path / "plain", monkeypatch, OBS_LOOP_POLICY_NAME, scenario
        )
        ojw_world, ojw_outcome = _run(
            tmp_path / "ojw", monkeypatch, OJW_POLICY_NAME, scenario
        )
        # accepted-span sequences
        assert _accepted_spans(ojw_world, scenario) == _accepted_spans(
            plain_world, scenario
        )
        # every request payload (slice relpaths, metered seconds, rendered
        # instruction incl. boundary template + tail, evidence fields)
        assert ojw_world.adapter.payloads == plain_world.adapter.payloads
        # slice derivation records, byte for byte
        assert _derivation_bytes(ojw_world) == _derivation_bytes(plain_world)
        # written slice bytes
        for payload in plain_world.adapter.payloads:
            relpath = payload["media_relpath"]
            assert (ojw_world.data_root / relpath).read_bytes() == (
                plain_world.data_root / relpath
            ).read_bytes()
        # stitched output text + the full outputs-row shape
        assert ojw_outcome == plain_outcome
        # the complete trace record sequence (OBS incl. trims, stitch, USE)
        assert _trace_records(ojw_world) == _trace_records(plain_world)

    def test_stitched_text_and_registry_state(self, tmp_path, monkeypatch):
        scenario = _scenario("model-tails")
        ojw_world, ojw_outcome = _run(tmp_path, monkeypatch, OJW_POLICY_NAME, scenario)
        assert ojw_outcome.text == "First span one. Second span two. Final span three."
        assert ojw_outcome.request_ids == (
            "req-0001-i0000",
            "req-0001-i0001",
            "req-0001-i0002",
        )
        for payload in ojw_world.adapter.payloads:
            record = ojw_world.registry.lookup(SAMPLE_ID, payload["media_relpath"])
            assert record is not None
            assert record.parent_sha256


class TestDeterminism:
    def test_determinism_five_runs(self, tmp_path, monkeypatch):
        """Five fresh executor runs over the same fixture must be
        byte-identical (and identical to the plain reference) — the
        empirical check behind the linear-chain determinism argument."""

        scenario = _scenario("model-tails")
        plain_world, plain_outcome = _run(
            tmp_path / "plain", monkeypatch, OBS_LOOP_POLICY_NAME, scenario
        )
        reference = _fingerprint(plain_world, plain_outcome)
        fingerprints = []
        for index in range(5):
            world, outcome = _run(
                tmp_path / f"ojw{index}", monkeypatch, OJW_POLICY_NAME, scenario
            )
            fingerprints.append(_fingerprint(world, outcome))
        assert fingerprints == [reference] * 5


class TestSingleDoor:
    def test_frozen_core_asr_requires_an_injected_callable(self):
        with pytest.raises(ObsLoopError, match="callable adapter request"):
            FrozenCoreASR(adapter_request=None, state=None)


class TestSaturation:
    """Per-slice decode-cap saturation reaches the ojw executor through the
    SAME shared seam (obs_loop.request_slice_with_retry) as the plain
    policy: FrozenCoreASR.invoke computes it, runner.py's ``${asr.saturated}``
    wiring carries it to AcceptAdvance, which emits it and mirrors it onto
    ObsSampleState.saturated_slices for policy._finalize_sample to read back
    into the outputs-row SampleOutcome -- proven directly against the ojw
    policy, not merely inferred from TestEquivalence (whose fake responses
    carry no usage at all, so saturated_slices stays 0 on both sides
    regardless of whether this wiring exists)."""

    def test_saturated_slice_reaches_the_outcome_and_the_obs_record(
        self, tmp_path, monkeypatch
    ):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                _boundary_text("First span done. Tail", 45),
                _boundary_text("Second done.", 10),
            ],
            usages=[{"completion_tokens": 5}, {"completion_tokens": 2}],
            decoding_params={"temperature": 0, "max_tokens": 5},
        )
        outcome = POLICIES.resolve(OJW_POLICY_NAME).run_sample(world.ctx)
        assert outcome.saturated_slices == 1
        obs = _obs_payloads(world)
        assert obs["req-0001-i0000/obs"]["obs_saturated"] is True
        assert obs["req-0001-i0001/obs"]["obs_saturated"] is False


class TestSkip:
    """Exhausted-slice skip (Task 2, 2026-08-09) reaches the ojw executor
    through the SAME shared seam (obs_loop.request_slice_with_retry) as the
    plain policy: FrozenCoreASR.invoke passes the skip through,
    runner.py's ``${asr.skipped}`` wiring carries it to AcceptAdvance, which
    emits it and mirrors it onto ObsSampleState.skipped_slices/
    skip_exceeded, and policy._finalize_sample raises the SAME
    ObsLoopError (obs_loop._skip_bound_exceeded_message, the ONE function
    both executors call) when the bound is crossed -- proven directly
    against the ojw policy here, not merely inferred from TestEquivalence's
    "retry-exhausted-skip" scenario."""

    def test_exhausted_slice_reaches_the_outcome_and_the_obs_record(
        self, tmp_path, monkeypatch
    ):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[_boundary_text("A.", 45), _boundary_text("B.", 10)],
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={2, 3})
        world.ctx.adapter = flaky
        outcome = POLICIES.resolve(OJW_POLICY_NAME).run_sample(world.ctx)
        assert outcome.skipped_slices == 1
        assert outcome.request_ids == ("req-0001-i0000",)
        obs = _obs_payloads(world)
        assert obs["req-0001-i0000/obs"]["obs_skipped"] is False
        assert obs["req-0001-i0001-r1/obs"]["obs_skipped"] is True
        assert obs["req-0001-i0001-r1/obs"]["obs_retry_of"] == "req-0001-i0001"

    def test_exceeding_the_skip_bound_raises_the_same_message_as_the_plain_policy(
        self, tmp_path, monkeypatch
    ):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(120.0),
            texts=["one", "two", "three"],
            values=_fixed_mode_skip_values(),
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={2, 3, 4, 5})
        world.ctx.adapter = flaky
        with pytest.raises(ObsLoopError, match="obs_slice_skip_max=1"):
            POLICIES.resolve(OJW_POLICY_NAME).run_sample(world.ctx)


class _FakeResponseById:
    """Deterministic, ORDER-INDEPENDENT fake hashes (keyed by request id +
    text): interleaved batch execution and per-sample sequential reference
    runs must produce identical outcome/stitch hashes."""

    def __init__(self, text, request_id):
        self.text = text
        self.request_sha256 = hashlib.sha256(f"req-{request_id}".encode()).hexdigest()
        self.response_sha256 = hashlib.sha256(
            f"resp-{request_id}-{text}".encode()
        ).hexdigest()
        self.response_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()


class _SampleScriptedAdapter:
    """Per-sample scripts, thread-safe (batch mode calls request from
    asyncio.to_thread workers); records every payload in arrival order."""

    def __init__(self, scripts):
        self._scripts = {sid: list(texts) for sid, texts in scripts.items()}
        self._lock = threading.Lock()
        self.payloads = []

    def request(self, payload):
        with self._lock:
            self.payloads.append(dict(payload))
            texts = self._scripts[payload["sample_id"]]
            if not texts:
                raise AssertionError(
                    f"sample {payload['sample_id']} sent more requests than scripted"
                )
            text = texts.pop(0)
        return _FakeResponseById(text, payload["request_id"])


def _parent_relpath(sample_id):
    return f"datasets/earnings21-22/earnings21/media/{sample_id}.mp3"


def _write_template(repo_root):
    template = repo_root / "configs" / "probes/obs_boundary_v1.txt"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text(
        "After the transcript report BOUNDARY_SECONDS as instructed.\n",
        encoding="utf-8",
    )


def _batch_specs():
    """Two whole-call samples with different lengths/scripts."""

    return {
        "4000001": (
            _noise(150.0, seed=3),
            [
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
        ),
        "4000002": (
            _noise(90.0, seed=11),
            [
                _boundary_text("Other call alpha. spill", 45),
                _boundary_text("Other call omega.", 10),
            ],
        ),
    }


def _ctx_for(sample_id, base, pcm, values, *, data_root, run_dir, repo_root,
             registry, adapter, sink, pcm_map):
    parent = data_root / _parent_relpath(sample_id)
    parent.parent.mkdir(parents=True, exist_ok=True)
    parent.write_bytes(b"fake-audio-" + sample_id.encode())
    pcm_map[f"{sample_id}.mp3"] = pcm
    duration = len(pcm) / 16000
    return SampleContext(
        sample=SampleRef(
            carrier_lock_key="earnings21-original",
            sample_id=sample_id,
            media_relpath=_parent_relpath(sample_id),
            audio_seconds=duration,
            sample_rate_hz=16000,
        ),
        evidence=[],
        adapter=adapter,
        sink=sink,
        arm="bare-core",
        task_instruction="Transcribe the speech verbatim.",
        decoding_params={"temperature": 0},
        request_id_base=base,
        extras={
            "slice_registry": registry,
            "data_root": data_root,
            "run_dir": run_dir,
            "repo_root": repo_root,
            "config_values": values,
        },
    )


class TestBatchExecution:
    """Owner batching directive (2026-08-08): sample-level concurrency in
    the ojw executor via run_samples (asyncio.gather + semaphore); per
    sample everything must stay byte-identical to the sequential plain
    reference, and rows/trace stay in split-id order."""

    def _reference(self, root, sample_id, base, pcm, texts, values, pcm_map):
        """The plain policy run sequentially over ONE sample — the
        per-sample ground truth the batch run must reproduce exactly."""

        data_root, run_dir, repo_root = root / "data", root / "run", root / "repo"
        _write_template(repo_root)
        registry = SliceRegistry(
            data_root=data_root,
            run_id=RUN_ID,
            parent_facts={sample_id: (_parent_relpath(sample_id), len(pcm) / 16000)},
        )
        adapter = _SampleScriptedAdapter({sample_id: texts})
        sink = TraceSink(run_dir, RUN_ID)
        ctx = _ctx_for(
            sample_id, base, pcm, values, data_root=data_root, run_dir=run_dir,
            repo_root=repo_root, registry=registry, adapter=adapter, sink=sink,
            pcm_map=pcm_map,
        )
        outcome = POLICIES.resolve(OBS_LOOP_POLICY_NAME).run_sample(ctx)
        raw = (run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = [
            (doc["channel"], doc["record_id"], doc["payload"])
            for doc in (json.loads(line) for line in raw.splitlines() if line)
        ]
        derivation = (
            run_dir / f"{RUN_ID}.obs-derivation.{sample_id}.json"
        ).read_bytes()
        return outcome, records, derivation

    def _batch_world(self, root, specs, values, pcm_map):
        data_root, run_dir, repo_root = root / "data", root / "run", root / "repo"
        _write_template(repo_root)
        registry = SliceRegistry(
            data_root=data_root,
            run_id=RUN_ID,
            parent_facts={
                sid: (_parent_relpath(sid), len(pcm) / 16000)
                for sid, (pcm, _) in specs.items()
            },
        )
        adapter = _SampleScriptedAdapter(
            {sid: texts for sid, (_, texts) in specs.items()}
        )
        contexts, buffers = [], {}
        for index, sid in enumerate(sorted(specs), start=1):
            pcm, _ = specs[sid]
            buffer = TraceBuffer(RUN_ID)
            buffers[sid] = buffer
            contexts.append(
                _ctx_for(
                    sid, f"req-{index:04d}", pcm, values, data_root=data_root,
                    run_dir=run_dir, repo_root=repo_root, registry=registry,
                    adapter=adapter, sink=buffer, pcm_map=pcm_map,
                )
            )
        return contexts, buffers, adapter, registry, data_root, run_dir

    def test_batch_of_two_matches_sequential_plain_per_sample(
        self, tmp_path, monkeypatch
    ):
        pcm_map = {}
        monkeypatch.setattr(
            obs_loop,
            "decode_parent_pcm",
            lambda path, rate=16000: pcm_map[Path(path).name],
        )
        specs = _batch_specs()
        values = _config_values(obs_condition_tail_chars=400, obs_batch_samples=2)

        references = {}
        for index, sid in enumerate(sorted(specs), start=1):
            pcm, texts = specs[sid]
            references[sid] = self._reference(
                tmp_path / f"ref-{sid}", sid, f"req-{index:04d}", pcm, texts,
                dict(values), pcm_map,
            )

        contexts, buffers, adapter, registry, data_root, run_dir = self._batch_world(
            tmp_path / "batch", specs, dict(values), pcm_map
        )
        outcomes = POLICIES.resolve(OJW_POLICY_NAME).run_samples(contexts)

        assert len(outcomes) == len(contexts)
        for ctx, outcome in zip(contexts, outcomes):
            sid = ctx.sample.sample_id
            ref_outcome, ref_records, ref_derivation = references[sid]
            assert outcome == ref_outcome
            assert buffers[sid].records == ref_records
            assert (
                run_dir / f"{RUN_ID}.obs-derivation.{sid}.json"
            ).read_bytes() == ref_derivation

        # slice-file collision check (item 4): per-sample-unique paths, all
        # registered, all written under the shared data root
        by_sample = {}
        for payload in adapter.payloads:
            by_sample.setdefault(payload["sample_id"], set()).add(
                payload["media_relpath"]
            )
        sids = sorted(by_sample)
        assert len(sids) == 2
        assert by_sample[sids[0]].isdisjoint(by_sample[sids[1]])
        for sid, relpaths in by_sample.items():
            for relpath in relpaths:
                assert f"/{sid}/" in relpath
                assert (data_root / relpath).is_file()
                assert registry.lookup(sid, relpath) is not None

        # deterministic per-run trace file: flush in split-id order
        sink = TraceSink(run_dir, RUN_ID)
        for ctx in contexts:
            buffers[ctx.sample.sample_id].flush_into(sink)
        raw = (run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        flushed_ids = [json.loads(line)["record_id"] for line in raw.splitlines() if line]
        expected_ids = [
            record_id
            for sid in sorted(specs)
            for _, record_id, _ in references[sid][1]
        ]
        assert flushed_ids == expected_ids

    def test_batch_size_one_is_todays_behaviour(self, tmp_path, monkeypatch):
        pcm_map = {}
        monkeypatch.setattr(
            obs_loop,
            "decode_parent_pcm",
            lambda path, rate=16000: pcm_map[Path(path).name],
        )
        specs = _batch_specs()
        results = {}
        for batch in (1, 2):
            values = _config_values(
                obs_condition_tail_chars=400, obs_batch_samples=batch
            )
            contexts, buffers, _, _, _, _ = self._batch_world(
                tmp_path / f"batch-{batch}", specs, values, pcm_map
            )
            outcomes = POLICIES.resolve(OJW_POLICY_NAME).run_samples(contexts)
            results[batch] = (
                outcomes,
                {sid: list(buffer.records) for sid, buffer in buffers.items()},
            )
        assert results[1] == results[2]

    def test_batch_failure_surfaces_first_sample_in_split_order(
        self, tmp_path, monkeypatch
    ):
        """When SEVERAL samples fail concurrently, the error that surfaces is
        deterministically the FIRST in split-id order — never whichever task
        happened to fail first in wall-clock time. (The framework wraps a
        component failure as ExecutionError 100054, the same shape the live
        run showed; the batch runner preserves that error, only choosing
        WHICH one propagates.)"""

        pcm_map = {}
        monkeypatch.setattr(
            obs_loop,
            "decode_parent_pcm",
            lambda path, rate=16000: pcm_map[Path(path).name],
        )
        specs = _batch_specs()
        values = _config_values(obs_condition_tail_chars=400, obs_batch_samples=2)
        contexts, _, adapter, _, _, _ = self._batch_world(
            tmp_path / "batch", specs, values, pcm_map
        )
        # Exhaust BOTH scripts so both samples fail; the LONGER sample
        # (4000001, 3 slices) necessarily fails LATER in wall-clock time than
        # the shorter one (4000002, 2 slices) -- so "first in split-id order"
        # and "first to fail" are genuinely different answers here.
        for sample_id in specs:
            adapter._scripts[sample_id].pop()
        with pytest.raises(Exception) as failure:
            POLICIES.resolve(OJW_POLICY_NAME).run_samples(contexts)
        message = str(failure.value)
        assert "more requests than scripted" in message
        assert "4000001" in message  # split-id order wins
        assert "4000002" not in message


class TestWorkflowTimeout:
    """Real-run blocker (2026-08-08): the framework kills each per-sample
    workflow at a builtin 60 s WORKFLOW_EXECUTE_TIMEOUT (error 100101). The
    fragment knob ``ojw_workflow_timeout_seconds`` must genuinely reach the
    framework session env, default to the generous backstop when absent,
    and a real kill must surface as an actionable ObsLoopError."""

    def _spy_envs(self, monkeypatch):
        from speech_aware_evidence_acquisition.reproduction.ojw import runner

        captured = {}
        real = runner.create_workflow_session

        def spy(*args, **kwargs):
            captured.update(kwargs.get("envs") or {})
            return real(*args, **kwargs)

        monkeypatch.setattr(runner, "create_workflow_session", spy)
        return captured

    def test_configured_value_reaches_the_framework_session_env(
        self, tmp_path, monkeypatch
    ):
        from openjiuwen.core.session import WORKFLOW_EXECUTE_TIMEOUT

        captured = self._spy_envs(monkeypatch)
        scenario = _scenario("vad-trim")
        scenario["values"]["ojw_workflow_timeout_seconds"] = 1234.5
        _run(tmp_path, monkeypatch, OJW_POLICY_NAME, scenario)
        assert captured[WORKFLOW_EXECUTE_TIMEOUT] == 1234.5

    def test_absent_key_defaults_to_the_generous_backstop(
        self, tmp_path, monkeypatch
    ):
        from openjiuwen.core.session import WORKFLOW_EXECUTE_TIMEOUT

        from speech_aware_evidence_acquisition.reproduction.ojw import (
            DEFAULT_WORKFLOW_TIMEOUT_SECONDS,
        )

        captured = self._spy_envs(monkeypatch)
        scenario = _scenario("vad-trim")
        assert "ojw_workflow_timeout_seconds" not in scenario["values"]
        _run(tmp_path, monkeypatch, OJW_POLICY_NAME, scenario)
        assert captured[WORKFLOW_EXECUTE_TIMEOUT] == DEFAULT_WORKFLOW_TIMEOUT_SECONDS
        assert DEFAULT_WORKFLOW_TIMEOUT_SECONDS == 21600.0

    def test_framework_kill_surfaces_as_actionable_obs_loop_error(
        self, tmp_path, monkeypatch
    ):
        """End to end against the REAL framework limit: a tiny configured
        ceiling plus a slow adapter must reproduce the live incident's
        100101 kill, translated to an ObsLoopError naming the knob."""

        import time

        scenario = _scenario("vad-trim")
        scenario["values"]["ojw_workflow_timeout_seconds"] = 0.2
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=scenario["pcm"],
            texts=list(scenario["texts"]),
            values=dict(scenario["values"]),
        )
        real_request = world.adapter.request

        def slow_request(payload):
            time.sleep(0.6)
            return real_request(payload)

        world.adapter.request = slow_request
        with pytest.raises(ObsLoopError, match="ojw_workflow_timeout_seconds"):
            POLICIES.resolve(OJW_POLICY_NAME).run_sample(world.ctx)
