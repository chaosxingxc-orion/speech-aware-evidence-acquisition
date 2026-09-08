"""The obs-pipeline throughput fix (2026-09-08): prefetch + run dispatcher.

What the sealed comparator measured, and what this suite pins so it cannot
regress. On SAEA-E21-FULL44-DIRECT-BASELINE-V2 (44 calls, 1,593 fixed
90-second windows, -c 36864 -np 6) the obs loop occupied 4.664 of 6 server
slots on average, spent 15.40 % of its 5,378.8-second wall with ZERO slots
busy, and delivered 17.77 windows per minute; 828.4 of the 829 idle seconds
were the 43 CALL BOUNDARIES, where the next call's decode/cut/encode ran with
nothing in flight. ``obs_prefetch_depth`` overlaps that CPU phase with the
previous call's requests, and ``reproduction.obs_loop.ObsDispatcher`` keeps
the request slots occupied across the boundary.

The five proofs, in order:

a. depth 0 is byte-identical to declaring nothing at all -- the same trace
   bytes, the same outputs bytes, on the same synthetic run;
b. depth 1 sends the SAME set of request payloads and emits the SAME
   per-sample OBS records as depth 0, while actually overlapping two samples
   (a different arrival order / batch composition, which is the whole point);
c. the dispatcher never exceeds its width, and never hands the same
   ``id_slot`` to two live requests;
d. a failure in a PREFETCHED sample's own cut phase surfaces on that sample,
   in split order, and stops the run;
e. the window-hook seam still routes under a dispatcher (the unit-plan seam's
   own suite, ``tests/unit/test_obs_unit_plan.py``, is unchanged and green).
"""

import json
import random
import subprocess
import threading
from array import array
from collections import Counter

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.base import CoreError
from speech_aware_evidence_acquisition.core.config import ComposedConfig, protocol_hash
from speech_aware_evidence_acquisition.core.driver import load_split, run_experiment
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.splits import freeze_splits
from speech_aware_evidence_acquisition.reproduction import obs_loop
from speech_aware_evidence_acquisition.reproduction.obs_loop import (
    ObsDispatcher,
    ObsLoopConfig,
    ObsLoopError,
    build_run_dispatcher,
    resolve_dispatch_width,
    resolve_prefetch_depth,
)

RATE = 16000


def _noise(seconds: float, seed: int = 17) -> array:
    rng = random.Random(seed)
    return array(
        "h", (int(6000 * (2 * rng.random() - 1)) for _ in range(int(seconds * RATE)))
    )


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def _git(repo_root, *args):
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True, text=True)


@pytest.fixture()
def pipeline_repo(synthetic_world, tmp_path, monkeypatch):
    """The synthetic three-call world, cut into fixed 45-second windows.

    90 s of PCM per call (the file metadata says 100.5 s, inside the slice
    rail's parent-duration tolerance) -> exactly 2 windows per call, 6
    windows per run: small enough to run fast, wide enough that two samples
    can genuinely be in flight at once."""

    monkeypatch.setattr(obs_loop, "decode_parent_pcm", lambda path, rate=RATE: _noise(90.0))
    lock = load_lock(synthetic_world.lock_path)
    repo_root = tmp_path / "repo"
    receipts = repo_root / "docs" / "receipts"
    freeze_splits(lock, synthetic_world.data_root, receipts)
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "obs pipeline snapshot")
    return lock, repo_root


def _values(**overrides):
    values = {
        "carrier_lock_key": "earnings21-original",
        "split_name": "discovery",
        "arm": "bare-core",
        "policy": "obs-agent-loop",
        "evidence_source": "none",
        "evidence_mismatch": False,
        "scorers": ["asr-wer"],
        "task_instruction": "Transcribe the speech verbatim.",
        "decoding_params": {"temperature": 0, "seed": 20260803},
        "experiment_id": "SAEA-E-000",
        "obs_buffer_seconds": 45,
        "obs_min_advance_seconds": 20,
        "obs_max_advance_seconds": 45,
        "obs_silence_snap_seconds": 2.0,
        "obs_fallback_advance_seconds": 45,
        "obs_boundary_mode": "fixed",
        "obs_vad": "energy",
        "obs_vad_trim_min_seconds": 0,
        "obs_preprocess": [],
        "obs_condition_tail_chars": 0,
        "obs_batch_samples": 1,
        "obs_batch_slices": 4,
    }
    values.update(overrides)
    return values


def _fly(
    synthetic_world, repo_root, lock, run_dir, transport, run_id,
    attempt_suffix="a", **overrides,
):
    """One synthetic run through the real ``core.driver.run_experiment``.

    ``attempt_suffix`` exists so two runs can share ONE run id (and therefore
    one slice tree, one set of ``media_relpath`` strings and one set of
    payload hashes) in two different run directories -- which is what makes
    a byte-for-byte trace comparison meaningful at all.
    """

    ids, split_hash, _ = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    composed = ComposedConfig(
        values=_values(**overrides),
        config_hash="d" * 64,
        fragments={"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"},
    )
    plan = ExecutionPlan(
        run_id=run_id,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash=split_hash,
        planned_model_calls=40,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=5000,
        protocol_hash=protocol_hash(composed.config_hash, "bare-core", split_hash),
        attempt_id=f"attempt-{run_id.lower()}-{attempt_suffix}",
    )
    assert len(ids) == 3
    return run_experiment(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        run_dir, transport, repo_root=repo_root,
    )


def _static_transport(request_bytes):
    """Deterministic answer keyed by the slice actually sent, so two runs of
    the same roster produce byte-identical traces."""

    payload = json.loads(request_bytes.decode("utf-8"))
    slice_name = str(payload["media_relpath"]).rsplit("/", 1)[-1]
    return json.dumps(
        {"text": f"hello world {slice_name}.", "usage": {"prompt_tokens": 3}}
    ).encode()


def _trace_documents(run_dir, run_id):
    raw = (run_dir / f"{run_id}.trace.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in raw.splitlines() if line]


def _request_payload_sha256s(documents):
    """Every per-window request's payload hash. The terminal per-sample
    ``/request`` stitch record is excluded: it hashes a descriptor of the
    window requests, not a request of its own."""

    return sorted(
        document["payload"]["payload_sha256"]
        for document in documents
        if document["channel"] == "MODEL_REQUEST" and "-i" in document["record_id"]
    )


def _trace_lines_modulo_latency(run_dir, run_id):
    """Every trace line verbatim, except the COST record's own stopwatch
    reading.

    ``latency_seconds`` is a wall-clock measurement of the transport call, so
    no two runs can ever agree on it to the last float digit -- it is the one
    field in the whole trace that is not a protocol byte. Everything else,
    including every ``payload_sha256`` (which is what actually proves the
    requests are the same requests), is compared raw and untouched."""

    lines = []
    raw = (run_dir / f"{run_id}.trace.jsonl").read_text(encoding="utf-8")
    for line in raw.splitlines():
        if not line:
            continue
        document = json.loads(line)
        if document["channel"] != "COST":
            lines.append(line)
            continue
        document["payload"]["latency_seconds"] = "<measured>"
        lines.append(
            json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
    return lines


def _obs_records(documents):
    return [
        (document["record_id"], document["payload"])
        for document in documents
        if document["channel"] == "OBS" and document["record_id"].endswith("/obs")
    ]


# ---------------------------------------------------------------------------
# Config resolution (fail-closed)
# ---------------------------------------------------------------------------


class TestKnobResolution:
    def test_depth_defaults_to_zero_and_bad_values_refuse(self):
        assert resolve_prefetch_depth({}) == 0
        assert resolve_prefetch_depth({"obs_prefetch_depth": 3}) == 3
        for bad in (-1, 1.0, True, "1", None):
            with pytest.raises(ObsLoopError, match="obs_prefetch_depth"):
                resolve_prefetch_depth({"obs_prefetch_depth": bad})

    def test_width_is_the_wider_of_slice_width_and_server_slots(self):
        assert resolve_dispatch_width({"obs_batch_slices": 8}) == 8
        assert resolve_dispatch_width(
            {"obs_batch_slices": 8, "serving_geometry": {"slots": 6}}
        ) == 8, "never narrower than the width the config already declares"
        assert resolve_dispatch_width(
            {"obs_batch_slices": 4, "serving_geometry": {"slots": 6}}
        ) == 6, "never narrower than the server's own slots"
        with pytest.raises(ObsLoopError, match="serving_geometry.slots"):
            resolve_dispatch_width(
                {"obs_batch_slices": 4, "serving_geometry": {"slots": 0}}
            )
        with pytest.raises(ObsLoopError, match="serving_geometry"):
            resolve_dispatch_width({"obs_batch_slices": 4, "serving_geometry": [6]})

    def test_no_dispatcher_at_depth_zero(self):
        assert build_run_dispatcher({"obs_batch_slices": 8}) is None
        dispatcher = build_run_dispatcher(
            {"obs_batch_slices": 8, "obs_prefetch_depth": 1}
        )
        assert dispatcher is not None and dispatcher.width == 8

    def test_policy_config_refuses_an_illegal_combination(self, tmp_path):
        base = _values(obs_prefetch_depth=1)
        assert ObsLoopConfig.from_values(base, tmp_path).prefetch_depth == 1
        assert ObsLoopConfig.from_values(_values(), tmp_path).prefetch_depth == 0
        with pytest.raises(ObsLoopError, match="obs_batch_slices > 1"):
            ObsLoopConfig.from_values(
                _values(obs_prefetch_depth=1, obs_batch_slices=1), tmp_path
            )
        with pytest.raises(ObsLoopError, match="obs_batch_samples 1"):
            ObsLoopConfig.from_values(
                _values(obs_prefetch_depth=1, obs_batch_samples=2), tmp_path
            )

    def test_driver_refuses_prefetch_for_a_non_obs_policy(
        self, synthetic_world, pipeline_repo, tmp_path
    ):
        lock, repo_root = pipeline_repo
        with pytest.raises(CoreError, match="obs-agent-loop"):
            _fly(
                synthetic_world, repo_root, lock, tmp_path / "refused",
                _static_transport, "SAEA-E-000-pipe-refuse",
                policy="fixed", obs_prefetch_depth=1,
            )


# ---------------------------------------------------------------------------
# (a) depth 0 is byte-identical
# ---------------------------------------------------------------------------


def test_depth_zero_reproduces_the_sequential_trace_byte_for_byte(
    synthetic_world, pipeline_repo, tmp_path
):
    """A run that never heard of the knob and a run that declares it as 0
    must produce the same trace file and the same outputs file.

    One 90-second window per call, so the trace is fully deterministic: with
    a single request per sample there is no arrival-order interleaving left
    to explain away, and the two files can be compared line for line. Both
    runs carry the SAME run id in two different run directories, so the slice
    tree, every ``media_relpath`` and therefore every payload hash are
    comparable at all; only the COST record's measured latency is normalized
    out (see ``_trace_lines_modulo_latency``)."""

    lock, repo_root = pipeline_repo
    run_id = "SAEA-E-000-pipe-zero"
    baseline_dir = tmp_path / "baseline"
    zero_dir = tmp_path / "zero"
    baseline = _fly(
        synthetic_world, repo_root, lock, baseline_dir, _static_transport, run_id,
        attempt_suffix="unset", obs_buffer_seconds=90, obs_max_advance_seconds=90,
        obs_fallback_advance_seconds=90,
    )
    zero = _fly(
        synthetic_world, repo_root, lock, zero_dir, _static_transport, run_id,
        attempt_suffix="zero", obs_prefetch_depth=0, obs_buffer_seconds=90,
        obs_max_advance_seconds=90, obs_fallback_advance_seconds=90,
    )
    assert _trace_lines_modulo_latency(baseline_dir, run_id) == (
        _trace_lines_modulo_latency(zero_dir, run_id)
    )
    assert baseline.outputs_path.read_bytes() == zero.outputs_path.read_bytes()
    assert baseline.cost["calls_used"] == zero.cost["calls_used"] == 3


def test_depth_zero_reproduces_every_record_of_a_multi_window_run(
    synthetic_world, pipeline_repo, tmp_path
):
    """The same claim where a sample really does fan out.

    Two 45-second windows per call means two concurrent requests per sample
    even at depth 0, so the MODEL/COST records interleave in arrival order --
    which is the pass's own documented contract and already varies between two
    runs of the unchanged code. What must NOT vary is any record's CONTENT:
    every trace line is identical as a set, the per-sample OBS records are
    identical AND still in slice order, and the outputs rows are identical
    bytes."""

    lock, repo_root = pipeline_repo
    run_id = "SAEA-E-000-pipe-multi"
    baseline_dir = tmp_path / "baseline"
    zero_dir = tmp_path / "zero"
    baseline = _fly(
        synthetic_world, repo_root, lock, baseline_dir, _static_transport, run_id,
        attempt_suffix="unset",
    )
    zero = _fly(
        synthetic_world, repo_root, lock, zero_dir, _static_transport, run_id,
        attempt_suffix="zero", obs_prefetch_depth=0,
    )
    assert sorted(_trace_lines_modulo_latency(baseline_dir, run_id)) == sorted(
        _trace_lines_modulo_latency(zero_dir, run_id)
    )
    assert _obs_records(_trace_documents(baseline_dir, run_id)) == _obs_records(
        _trace_documents(zero_dir, run_id)
    )
    assert baseline.outputs_path.read_bytes() == zero.outputs_path.read_bytes()
    assert baseline.cost["calls_used"] == zero.cost["calls_used"] == 6


def test_depth_zero_builds_no_pipeline_at_all(
    synthetic_world, pipeline_repo, tmp_path, monkeypatch
):
    """The structural half of the same claim: at depth 0 the driver enters
    the historical sequential branch, so no dispatcher is constructed, no
    trace buffer is interposed, and the slice-parallel pass takes its own
    per-sample slot pool."""

    lock, repo_root = pipeline_repo
    built = []
    real_build = obs_loop.build_run_dispatcher

    def _spy_build(values):
        dispatcher = real_build(values)
        built.append(dispatcher)
        return dispatcher

    monkeypatch.setattr(obs_loop, "build_run_dispatcher", _spy_build)
    seen_dispatchers = []
    original = obs_loop.ObsAgentLoopPolicy._slice_parallel_pass

    def _spy(self, *args, **kwargs):
        seen_dispatchers.append(kwargs.get("dispatcher"))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(obs_loop.ObsAgentLoopPolicy, "_slice_parallel_pass", _spy)
    result = _fly(
        synthetic_world, repo_root, lock, tmp_path / "structural", _static_transport,
        "SAEA-E-000-pipe-struct", obs_prefetch_depth=0,
    )
    assert result.cost["calls_used"] == 6
    assert built == [], "the driver even asked for a dispatcher at depth 0"
    assert seen_dispatchers == [None, None, None]


# ---------------------------------------------------------------------------
# (b) depth 1 sends the same payloads with a different arrival order
# ---------------------------------------------------------------------------


class _OverlapTransport:
    """Blocks every request until two DIFFERENT samples are in flight at
    once, then releases all of them. At depth 1 that happens; the timeout is
    the failure mode, never a hang."""

    def __init__(self, timeout_seconds: float = 20.0) -> None:
        self._lock = threading.Lock()
        self._in_flight: Counter = Counter()
        self._timeout = timeout_seconds
        self.saw_two_samples = threading.Event()
        self.max_distinct_samples = 0

    def __call__(self, request_bytes):
        payload = json.loads(request_bytes.decode("utf-8"))
        sample = str(payload["request_id"]).split("-i")[0]
        with self._lock:
            self._in_flight[sample] += 1
            distinct = sum(1 for count in self._in_flight.values() if count)
            self.max_distinct_samples = max(self.max_distinct_samples, distinct)
            if distinct >= 2:
                self.saw_two_samples.set()
        try:
            self.saw_two_samples.wait(timeout=self._timeout)
        finally:
            with self._lock:
                self._in_flight[sample] -= 1
        return _static_transport(request_bytes)


def test_depth_one_sends_the_same_payloads_and_overlaps_two_samples(
    synthetic_world, pipeline_repo, tmp_path
):
    lock, repo_root = pipeline_repo
    run_id = "SAEA-E-000-pipe-one"
    zero_dir = tmp_path / "zero"
    one_dir = tmp_path / "one"
    zero = _fly(
        synthetic_world, repo_root, lock, zero_dir, _static_transport, run_id,
        attempt_suffix="seq",
    )
    overlap = _OverlapTransport()
    one = _fly(
        synthetic_world, repo_root, lock, one_dir, overlap, run_id,
        attempt_suffix="pipe", obs_prefetch_depth=1,
    )

    zero_documents = _trace_documents(zero_dir, run_id)
    one_documents = _trace_documents(one_dir, run_id)

    # The requests themselves: the SAME set of payload hashes, so not one
    # byte of what the frozen core was asked moved.
    assert _request_payload_sha256s(zero_documents) == _request_payload_sha256s(
        one_documents
    )
    # The per-sample OBS records: identical ids, identical payloads, still in
    # slice order within each sample.
    assert _obs_records(zero_documents) == _obs_records(one_documents)
    # And the rows the scorers read.
    assert zero.outputs_path.read_bytes() == one.outputs_path.read_bytes()
    assert zero.cost["calls_used"] == one.cost["calls_used"] == 6

    # What DID change: the batch composition. Two different samples had
    # requests in flight at the same time, which is exactly what keeps the
    # server's slots occupied across a call boundary.
    assert overlap.saw_two_samples.is_set(), "the pipeline never overlapped two samples"
    assert overlap.max_distinct_samples >= 2


# ---------------------------------------------------------------------------
# (c) the dispatcher never exceeds its width
# ---------------------------------------------------------------------------


class _CountingTransport:
    """Sleeps inside every request and records the peak number of concurrent
    requests plus the ``id_slot`` values live at each moment."""

    def __init__(self, hold_seconds: float = 0.03) -> None:
        self._lock = threading.Lock()
        self._hold = hold_seconds
        self._live: Counter = Counter()
        self.in_flight = 0
        self.peak_in_flight = 0
        self.max_duplicate_slot = 0
        self.slots_seen: set = set()

    def __call__(self, request_bytes):
        import time

        payload = json.loads(request_bytes.decode("utf-8"))
        slot = dict(payload.get("decoding_params") or {}).get("id_slot")
        with self._lock:
            self.in_flight += 1
            self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
            if slot is not None:
                self.slots_seen.add(slot)
                self._live[slot] += 1
                self.max_duplicate_slot = max(self.max_duplicate_slot, self._live[slot])
        time.sleep(self._hold)
        with self._lock:
            self.in_flight -= 1
            if slot is not None:
                self._live[slot] -= 1
        return _static_transport(request_bytes)


def test_dispatcher_bounds_concurrency_and_never_reuses_a_live_slot(
    synthetic_world, pipeline_repo, tmp_path
):
    """Six windows over three samples, two samples in flight, a dispatch
    width of 3: the transport must never see a fourth concurrent request, and
    never two live requests pinned to one ``id_slot``."""

    lock, repo_root = pipeline_repo
    transport = _CountingTransport()
    result = _fly(
        synthetic_world, repo_root, lock, tmp_path / "bounded", transport,
        "SAEA-E-000-pipe-bound",
        obs_prefetch_depth=1,
        obs_batch_slices=3,
        decoding_params={"temperature": 0, "seed": 20260803, "id_slot": "per-sample"},
    )
    assert result.cost["calls_used"] == 6
    assert transport.peak_in_flight <= 3, transport.peak_in_flight
    assert transport.peak_in_flight >= 2, "the pipeline never dispatched concurrently"
    assert transport.max_duplicate_slot == 1, "two live requests shared one id_slot"
    assert transport.slots_seen <= {0, 1, 2}


def test_dispatch_slot_is_released_when_a_request_raises():
    """A raised request must never leak a slot: the width is a property of
    the run, not of how many requests happened to succeed."""

    dispatcher = ObsDispatcher(2)
    for _ in range(5):
        with pytest.raises(RuntimeError):
            with dispatcher.dispatch_slot():
                raise RuntimeError("boom")
    assert dispatcher.in_flight == 0
    with dispatcher.dispatch_slot() as first, dispatcher.dispatch_slot() as second:
        assert {first, second} == {0, 1}
    assert dispatcher.in_flight == 0
    with pytest.raises(ObsLoopError, match="dispatch width"):
        ObsDispatcher(0)


def test_dispatcher_blocks_the_width_plus_one_th_request():
    """The bound is enforced by BLOCKING, not by dropping: a request that
    finds no free slot waits for one."""

    dispatcher = ObsDispatcher(1)
    entered = threading.Event()
    released = threading.Event()
    observed = []

    def _second():
        entered.set()
        with dispatcher.dispatch_slot():
            observed.append(dispatcher.in_flight)
        released.set()

    with dispatcher.dispatch_slot():
        worker = threading.Thread(target=_second)
        worker.start()
        assert entered.wait(timeout=5.0)
        assert not released.wait(timeout=0.2), "the second acquire did not block"
        assert dispatcher.in_flight == 1
    assert released.wait(timeout=5.0)
    worker.join(timeout=5.0)
    assert observed == [1]
    assert dispatcher.peak_in_flight == 1


# ---------------------------------------------------------------------------
# (d) a prefetch failure is attributed to its own sample and stops the run
# ---------------------------------------------------------------------------


def test_prefetch_failure_surfaces_on_its_own_sample_and_stops_the_run(
    synthetic_world, pipeline_repo, tmp_path, monkeypatch
):
    """The second call's decode fails while the first call's windows are
    still in flight. The run must raise THAT sample's error -- in split
    order, after the first sample's block is flushed -- never swallow it and
    never blame a neighbour."""

    lock, repo_root = pipeline_repo
    ids, _split_hash, _ = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    doomed = sorted(ids)[1]
    good_pcm = _noise(90.0)

    def _decode(path, rate=RATE):
        if doomed in str(path):
            raise obs_loop.ObsLoopError(f"synthetic decode failure for {doomed}")
        return good_pcm

    monkeypatch.setattr(obs_loop, "decode_parent_pcm", _decode)
    run_dir = tmp_path / "failing"
    with pytest.raises(obs_loop.ObsLoopError, match=doomed):
        _fly(
            synthetic_world, repo_root, lock, run_dir, _static_transport,
            "SAEA-E-000-pipe-fail", obs_prefetch_depth=1,
        )
    # The first sample completed and its whole block is in the trace; the
    # doomed sample contributed nothing at all.
    documents = _trace_documents(run_dir, "SAEA-E-000-pipe-fail")
    assert documents, "the completed first sample never reached the trace"
    assert all(
        document["record_id"].startswith("req-0001") for document in documents
    ), "a lookahead sample's records leaked into the sealed trace"
    rows = [
        json.loads(line)
        for line in (run_dir / "SAEA-E-000-pipe-fail.outputs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    assert [row["request_id"] for row in rows] == ["req-0001"]


# ---------------------------------------------------------------------------
# (e) the window-hook seam still routes under a dispatcher
# ---------------------------------------------------------------------------


class _RecordingHook:
    def __init__(self) -> None:
        self.iterations = []

    def instruction(self, *, iteration, record, default):
        return f"{default} [window {iteration}]"

    def accept(self, *, iteration, record, transcript, saturated, skipped):
        self.iterations.append(iteration)
        return f"[{iteration}] {transcript}", {"obs_hook_iteration": iteration}


def test_window_hook_still_routes_under_a_dispatcher(tmp_path, monkeypatch):
    """The KC-E1f window-hook seam is orthogonal to the dispatcher: with a
    run dispatcher supplied, the hook still renders every window's
    instruction, still decides every window's delivered text, and still
    merges its own fields into that window's OBS record."""

    from test_obs_loop_policy import _World, _config_values, _obs_payloads

    values = _config_values(
        obs_boundary_mode="fixed",
        obs_condition_tail_chars=0,
        obs_vad_trim_min_seconds=0,
        obs_batch_slices=2,
        obs_prefetch_depth=1,
    )
    hook = _RecordingHook()
    world = _World(
        tmp_path, monkeypatch, pcm=_noise(150.0), texts=["X."] * 3, values=values
    )
    monkeypatch.setattr(
        obs_loop.ObsAgentLoopPolicy, "_window_hook",
        lambda self, ctx, cfg, data_root, sample: hook,
    )
    world.ctx.extras["obs_dispatcher"] = ObsDispatcher(2)
    outcome = world.run()

    assert sorted(hook.iterations) == [0, 1, 2]
    assert outcome.text == "[0] X. [1] X. [2] X."
    payloads = _obs_payloads(world)
    for index in range(3):
        record = payloads[f"req-0001-i{index:04d}/obs"]
        assert record["obs_hook_iteration"] == index
        assert record["obs_dispatch"] == "slice-parallel"
    assert all(
        payload["decoding_params"] == {"temperature": 0}
        for payload in world.adapter.payloads
    ), "no id_slot is written when the model profile never asked for one"


def test_prefetch_depth_composes_with_a_unit_plan(tmp_path):
    """The unit-plan seam and the pipeline are independent knobs: a
    hash-pinned plan run may be pipelined, and neither knob relaxes the
    other's legality."""

    from test_obs_unit_plan import _load, _plan_document

    document = _plan_document(duration=100.0, edges=[40.0, 70.0])
    cfg = _load(tmp_path, document, obs_batch_slices=8, obs_prefetch_depth=2)
    assert cfg.prefetch_depth == 2
    assert cfg.unit_plan is not None and cfg.unit_plan.unit_count == 3
    with pytest.raises(ObsLoopError, match="obs_batch_slices > 1"):
        _load(tmp_path, document, obs_batch_slices=1, obs_prefetch_depth=1)
