"""Runtime session attestation (R0 repair T5, invariant I5).

Reproduced defect: the frozen-core gate re-hashes the pinned llama.cpp binary,
its runtime libraries and the GGUF files on disk -- then the transport simply
POSTs to whatever ``base_url`` the config names. Nothing binds the RESPONDING
PROCESS to those hashed artifacts. These probes exercise the fix: a
``SessionReceipt`` binding binary/model identity, pid, argv, host and port,
obtained ONLY via ``start_session`` (spawns and observes) or ``attach_session``
(re-verifies an on-disk receipt against the runtime receipt, a live pid,
process IMAGE identity, AND -- T5 fix-2, closing a materially equivalent gap
an independent re-review demonstrated live on both Windows and WSL2 -- kernel-
level SOCKET OWNERSHIP of ``(host, port)``) -- and re-checked independently by
``LlamaServerTransport`` at construction AND on every single send, plus a
complementary call site inside ``FrozenCoreAdapter`` (T5 fix-3).

NO MODEL TOUCH: every spawn in this file launches either a FAKE POSIX
shell-script "binary" (``TestStartSessionSpawn``, the same pattern
``tests/unit/test_e0_generators.py`` already uses for `llama-server
--version`) or a plain COPY of the current Python interpreter, invoked with
``-c "..."`` (the process-identity/socket-ownership tests below, some of
which additionally bind a REAL localhost TCP socket in the spawned child --
still never the real llama-server, never a real model file, never any
network I/O beyond localhost loopback plumbing internal to the test).

WINDOWS/WSL2 SPLIT (owner-approved, deliberate, not a coverage reduction):
tests that spawn a FRESH COPY of an executable (``_live_runtime_world``'s
``binary``, always at a NEW ``tmp_path`` each run) and have it genuinely bind
a LISTENING socket are marked POSIX-only below. On native Windows, that
combination makes Defender Firewall prompt for an unrecognized executable
image at a brand-new path on essentially every run -- the resulting allow
rule points at that run's now-deleted ``tmp_path``, so the very next run
prompts again. Those probes already run clean under WSL2, this program's
compute authority. Native Windows instead gets IN-PROCESS coverage of the
same underlying Windows API (``GetExtendedTcpTable`` via
``_windows_verify_pid_owns_listening_socket``) in
``TestWindowsSocketOwnershipInProcess`` below: a real loopback socket bound
inside THIS pytest process (no new executable image, so no new firewall
prompt -- python.exe running pytest is already a known, already-authorized
program on this host). Tests that spawn ``sys.executable`` DIRECTLY
(un-copied, a stable path across runs) are unaffected and keep running on
Windows -- only a freshly-copied-per-run image triggers the repeated-prompt
behavior. See ``docs/engineering.md`` for the summary.
"""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import (
    STUDY_SLUG,
    ExecutionPlan,
    ExecutionScopeError,
)
from speech_aware_evidence_acquisition.core.session import lifecycle as session_lifecycle
from speech_aware_evidence_acquisition.core.base import PayloadBindingContext
from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter, LlamaServerTransport
from speech_aware_evidence_acquisition.core.session import (
    EXT4_MODEL_SHA256_PINS,
    EXT4_MODELS_ROOT_DEFAULT,
    EXT4_MODELS_ROOT_ENV,
    FEAT_CACHE_DIR_DEFAULT,
    FEAT_CACHE_DIR_ENV,
    SESSION_RECEIPT_SCHEMA,
    SESSION_RECEIPT_SCHEMA_V2,
    ModelFileRef,
    SessionError,
    SessionReceipt,
    _model_file_argv,
    _resolve_model_file_source,
    audit_mmproj_free_inference,
    attach_session,
    feat_cache_dir,
    read_session_receipt,
    require_loopback,
    start_session,
    stop_session,
    verify_against_runtime_receipt,
    write_session_receipt,
)
from speech_aware_evidence_acquisition.core.tracing import TraceSink


_COPIED_BINARY_LISTENER_SKIP_REASON = (
    "spawns a freshly-copied 'pinned binary' executable (a new file under a "
    "brand-new pytest tmp_path every run) that then binds a real listening "
    "socket; on native Windows this makes Defender Firewall prompt for an "
    "unrecognized executable image on essentially every run (the allow rule "
    "it creates points at that run's tmp_path, which no longer exists next "
    "run, so it prompts again next time). Runs clean under WSL2, this "
    "program's compute authority. Native Windows still covers the same "
    "underlying Windows socket-ownership API in-process -- see "
    "TestWindowsSocketOwnershipInProcess below."
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _model_files():
    return (
        ModelFileRef(path="models/x/model.gguf", sha256="a" * 64),
        ModelFileRef(path="models/x/mmproj.gguf", sha256="b" * 64),
    )


def _session(**overrides):
    base = dict(
        schema=SESSION_RECEIPT_SCHEMA,
        study=STUDY_SLUG,
        session_id="test-session-1",
        binary_path="llama.cpp/build/bin/llama-server",
        binary_sha256="c" * 64,
        argv=("llama-server", "--host", "127.0.0.1", "--port", "8080"),
        pid=os.getpid(),
        host="127.0.0.1",
        port=8080,
        model_files=_model_files(),
        started_at="2026-08-05T00:00:00+00:00",
        startup_stdout_sha256=hashlib.sha256(b"").hexdigest(),
    )
    base.update(overrides)
    return SessionReceipt(**base)


def _inference_session(**overrides):
    base = dict(
        schema=SESSION_RECEIPT_SCHEMA_V2,
        study=STUDY_SLUG,
        session_id="test-inference-session-1",
        binary_path="llama.cpp/build/bin/llama-server",
        binary_sha256="c" * 64,
        argv=(
            "llama-server",
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
            "-m",
            "models/x/model.gguf",
            "--no-mmproj",
        ),
        pid=os.getpid(),
        host="127.0.0.1",
        port=8080,
        model_files=(_model_files()[0],),
        started_at="2026-08-21T00:00:00+00:00",
        startup_stdout_sha256=hashlib.sha256(b"").hexdigest(),
        role="inference",
        server_env_keys=(),
    )
    base.update(overrides)
    return SessionReceipt(**base)


def _canned_response():
    return json.dumps(
        {
            "choices": [{"message": {"content": "hello world"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
    ).encode()


def test_stop_session_targets_only_the_reverified_receipt_pid(monkeypatch, tmp_path):
    import signal
    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    receipt = _session(pid=43210)
    verified = []
    signals = []
    alive = iter((True, False))
    monkeypatch.setattr(
        lifecycle_module,
        "assert_session_alive",
        lambda actual, runtime, root: verified.append((actual, runtime, root)),
    )
    monkeypatch.setattr(
        lifecycle_module, "verify_against_runtime_receipt", lambda *_args: None
    )
    monkeypatch.setattr(lifecycle_module, "_pid_alive", lambda _pid: next(alive, False))
    monkeypatch.setattr(
        lifecycle_module.os,
        "kill",
        lambda pid, sent_signal: signals.append((pid, sent_signal)),
    )
    monkeypatch.setattr(lifecycle_module.time, "sleep", lambda _seconds: None)
    output = tmp_path / "stop.json"
    stopped = stop_session(
        receipt,
        runtime_receipt={"runtime": "pinned"},
        runtime_root=tmp_path,
        timeout_seconds=1.0,
        poll_interval_seconds=0.01,
        receipt_path=output,
    )

    assert verified == [(receipt, {"runtime": "pinned"}, tmp_path)]
    assert signals == [(43210, signal.SIGTERM)]
    assert stopped["session_id"] == receipt.session_id
    assert stopped["pid"] == 43210
    assert stopped["termination_signal"] == "SIGTERM"
    assert len(stopped["session_receipt_sha256"]) == 64
    assert len(stopped["runtime_receipt_sha256"]) == 64
    assert json.loads(output.read_text(encoding="utf-8")) == stopped


def test_stop_session_never_signals_when_identity_reverification_fails(monkeypatch, tmp_path):
    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    receipt = _session(pid=43210)

    def refuse(*_args):
        raise SessionError("not the receipt-bound process")

    monkeypatch.setattr(
        lifecycle_module, "verify_against_runtime_receipt", lambda *_args: None
    )
    monkeypatch.setattr(lifecycle_module, "_pid_alive", lambda _pid: True)
    monkeypatch.setattr(lifecycle_module, "assert_session_alive", refuse)
    monkeypatch.setattr(
        lifecycle_module.os,
        "kill",
        lambda *_args: pytest.fail("an unverified process must never be signalled"),
    )
    with pytest.raises(SessionError, match="receipt-bound"):
        stop_session(
            receipt,
            runtime_receipt={"runtime": "pinned"},
            runtime_root=tmp_path,
        )


def test_stop_session_records_an_already_exited_owned_process(monkeypatch, tmp_path):
    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    receipt = _session(pid=43210)
    verified = []
    monkeypatch.setattr(lifecycle_module, "_pid_alive", lambda _pid: False)
    monkeypatch.setattr(
        lifecycle_module,
        "verify_against_runtime_receipt",
        lambda actual, runtime: verified.append((actual, runtime)),
    )
    monkeypatch.setattr(
        lifecycle_module,
        "assert_session_alive",
        lambda *_args: pytest.fail("an exited process cannot pass a live-process audit"),
    )
    monkeypatch.setattr(
        lifecycle_module.os,
        "kill",
        lambda *_args: pytest.fail("an exited process must not be signalled"),
    )
    output = tmp_path / "already-exited.json"

    stopped = stop_session(
        receipt,
        runtime_receipt={"runtime": "pinned"},
        runtime_root=tmp_path,
        receipt_path=output,
    )

    assert verified == [(receipt, {"runtime": "pinned"})]
    assert stopped["termination_signal"] == "ALREADY_EXITED"
    assert stopped["forced"] is False
    assert json.loads(output.read_text(encoding="utf-8")) == stopped


def test_packet_promotion_requires_a_matching_preprocess_stop_chain(tmp_path):
    from speech_aware_evidence_acquisition.core.driver.cli import (
        _canonical_sha256,
        _load_preprocess_stop_chain,
    )

    runtime = {
        "role": "preprocess",
        "llama_cpp": {
            "binary_path": "llama.cpp/build/bin/llama-server",
            "binary_sha256": "c" * 64,
        },
        "gguf_files": [
            {"path": item.path, "sha256": item.sha256} for item in _model_files()
        ],
    }
    session = SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA_V2,
        study=STUDY_SLUG,
        session_id="preprocess-session",
        binary_path="llama.cpp/build/bin/llama-server",
        binary_sha256="c" * 64,
        argv=("llama-server", "-m", "models/x/model.gguf", "--mmproj", "models/x/mmproj.gguf"),
        pid=43210,
        host="127.0.0.1",
        port=8080,
        model_files=_model_files(),
        started_at="2026-08-21T00:00:00+00:00",
        startup_stdout_sha256=hashlib.sha256(b"").hexdigest(),
        role="preprocess",
        server_env_keys=("LLAMA_MTMD_FEAT_CACHE_DIR",),
    ).validate()
    session_path = tmp_path / "session.json"
    write_session_receipt(session_path, session)
    stop = {
        "schema": "saea-session-stop-receipt-v1",
        "study": STUDY_SLUG,
        "session_id": session.session_id,
        "session_role": "preprocess",
        "session_receipt_sha256": _canonical_sha256(session.as_json()),
        "runtime_receipt_sha256": _canonical_sha256(runtime),
        "pid": session.pid,
        "termination_signal": "SIGTERM",
        "forced": False,
        "stopped_at": "2026-08-21T00:01:00+00:00",
    }
    stop_path = tmp_path / "stop.json"
    stop_path.write_text(json.dumps(stop), encoding="utf-8")

    loaded_session, loaded_stop = _load_preprocess_stop_chain(
        session_receipt_path=session_path,
        stop_receipt_path=stop_path,
        runtime_receipt=runtime,
    )
    assert loaded_session == session
    assert loaded_stop == stop

    stop["runtime_receipt_sha256"] = "0" * 64
    stop_path.write_text(json.dumps(stop), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        _load_preprocess_stop_chain(
            session_receipt_path=session_path,
            stop_receipt_path=stop_path,
            runtime_receipt=runtime,
        )


def test_packet_promotion_writes_a_complete_no_overwrite_handoff(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core.driver.cli import (
        _cli_promote_speech_packets,
    )

    data_root = tmp_path / "data"
    legacy_root = tmp_path / "legacy"
    feature_root = tmp_path / "packets"
    output = tmp_path / "promotion.json"
    data_root.mkdir()
    legacy_root.mkdir()
    gate = SimpleNamespace(
        runtime_view_sha256="1" * 64,
        samples=(
            SimpleNamespace(
                packet_id="slurp/train/1",
                media_relpath="datasets/slurp/one.flac",
            ),
        ),
    )
    runtime = {
        "role": "preprocess",
        "gguf_files": [
            {"path": "models/decoder.gguf", "sha256": "2" * 64},
            {"path": "models/mmproj.gguf", "sha256": "3" * 64},
        ],
    }
    session = SimpleNamespace(
        session_id="preprocess-session-1",
        as_json=lambda: {"session_id": "preprocess-session-1"},
    )
    stop = {"stopped": True}
    packet = SimpleNamespace(
        packet_id="slurp/train/1",
        packet_sha256="4" * 64,
        audio_sha256="5" * 64,
        decoder_gguf_sha256="2" * 64,
        mmproj_sha256="3" * 64,
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.data_root", lambda: data_root
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.slurp.load_slurp_engineering_gate",
        lambda *_args, **_kwargs: gate,
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.session.load_runtime_receipt",
        lambda _path: runtime,
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.driver.cli._load_preprocess_stop_chain",
        lambda **_kwargs: (session, stop),
    )
    captured = {}

    def materialize(**kwargs):
        captured.update(kwargs)
        return (packet,)

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.model."
        "materialize_legacy_cached_speech_feature_packets",
        materialize,
    )
    args = SimpleNamespace(
        dataset="slurp-speech-native-eng-gate8",
        runtime_receipt="receipts/runtime-q4km-preprocess.json",
        session_receipt=str(tmp_path / "session.json"),
        stop_receipt=str(tmp_path / "stop.json"),
        legacy_cache_dir=str(legacy_root),
        feature_root=str(feature_root),
        expected_count=1,
        expected_n_embd=2048,
        workers=8,
        receipt_output=str(output),
    )

    assert _cli_promote_speech_packets(args) == 0
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["schema"] == "saea-speech-packet-promotion-receipt-v1"
    assert receipt["preprocess_session_receipt_sha256"] == hashlib.sha256(
        b'{"session_id":"preprocess-session-1"}'
    ).hexdigest()
    assert receipt["count"] == 1
    assert receipt["packets"][0]["packet_sha256"] == "4" * 64
    assert captured["workers"] == 8

    with pytest.raises(ValueError, match="already exists"):
        _cli_promote_speech_packets(args)


def _runtime_world(tmp_path):
    """A tiny model/runtime file world plus a matching runtime receipt dict
    (no real network, no real model -- fake bytes, like gate_fixture.py).
    The 'binary' here is NOT a real executable -- fine for every test that
    is refused BEFORE reaching the process-identity check (declared-value
    mismatches, loopback/host-port mismatches), but NOT usable for a test
    that must actually reach ``_verify_pid_runs_pinned_binary`` -- those use
    ``_live_runtime_world`` below instead."""

    runtime_root = tmp_path / "runtime"
    data_root = tmp_path / "data"
    binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
    binary.parent.mkdir(parents=True)
    binary_bytes = b"fake-llama-server"
    binary.write_bytes(binary_bytes)
    (binary.parent / "lib-fake.so").write_bytes(b"fake-lib")

    model_dir = data_root / "models" / "qwen3-omni-30b-a3b-instruct-gguf"
    model_dir.mkdir(parents=True)
    main_relpath = "models/qwen3-omni-30b-a3b-instruct-gguf/model.gguf"
    mmproj_relpath = "models/qwen3-omni-30b-a3b-instruct-gguf/mmproj.gguf"
    main_bytes = b"fake-main-gguf"
    mmproj_bytes = b"fake-mmproj-gguf"
    (data_root / main_relpath).write_bytes(main_bytes)
    (data_root / mmproj_relpath).write_bytes(mmproj_bytes)

    runtime_receipt = {
        "schema": "saea-runtime-receipt-v2",
        "study": "speech-aware-evidence-acquisition",
        "model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf",
        "llama_cpp": {
            "build_commit": "a" * 40,
            "reported_build": "version: 1 (aaaaaaa)",
            "binary_path": "llama.cpp/build/bin/llama-server",
            "binary_bytes": len(binary_bytes),
            "binary_sha256": _sha(binary_bytes),
        },
        "gguf_files": [
            {"path": main_relpath, "bytes": len(main_bytes), "sha256": _sha(main_bytes)},
            {"path": mmproj_relpath, "bytes": len(mmproj_bytes), "sha256": _sha(mmproj_bytes)},
        ],
        "runtime_libraries": [
            {"path": "llama.cpp/build/bin/lib-fake.so", "bytes": 8, "sha256": _sha(b"fake-lib")},
        ],
    }
    return runtime_root, data_root, binary, runtime_receipt


def _live_runtime_world(tmp_path):
    """Like ``_runtime_world``, but the pinned binary is a REAL executable
    (a byte-for-byte copy of the CURRENTLY RUNNING interpreter) so process-
    IDENTITY checks (T5 fix-1) can be genuinely exercised: a real process
    spawned from this exact file legitimately matches it; any OTHER live
    process (e.g. this test's own interpreter, or a forger's chosen pid)
    legitimately does not. No model bytes, no network -- copying/spawning
    the test's own interpreter is the same idea as
    ``tests/unit/test_e0_generators.py``'s fake ``llama-server --version``
    shell script, just for a check that needs a REAL OS-reported image
    rather than merely an executable-and-exiting one (a shebang script's
    reported image is its INTERPRETER, e.g. ``/bin/sh``, not the script
    itself, so it cannot exercise this specific check)."""

    runtime_root = tmp_path / "runtime"
    binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
    binary.parent.mkdir(parents=True)
    shutil.copy(sys.executable, binary)
    if os.name != "nt":
        binary.chmod(0o755)
    binary_sha256 = _sha(binary.read_bytes())
    model_files = _model_files()
    runtime_receipt = {
        "llama_cpp": {
            "binary_path": "llama.cpp/build/bin/llama-server",
            "binary_sha256": binary_sha256,
        },
        "gguf_files": [{"path": f.path, "sha256": f.sha256} for f in model_files],
    }
    return runtime_root, binary, runtime_receipt


def _spawn_matching_process(binary):
    return subprocess.Popen(
        [str(binary), "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _terminate(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _listener_code(port: int, *, address: str = "127.0.0.1", family: str = "AF_INET") -> str:
    """A tiny real TCP listener, run inside a spawned child via ``-c`` --
    binds and LISTENs on ``(address, port)`` for real (loopback only, no
    external network reachability), then idles. T5 fix-2: socket-ownership
    verification needs a genuinely bound, kernel-visible listening socket to
    exercise at all -- a sleeping process alone (the T5 fix-1 pattern) is not
    enough. T5 fix-3: ``address``/``family`` are parametrized so tests can
    bind IPv4 (``127.0.0.1``/``AF_INET``), IPv6 (``::1``/``AF_INET6``), or a
    wildcard (``0.0.0.0``/``::``) -- the address-aware fix must distinguish
    all of these."""

    return (
        "import socket, time\n"
        f"s = socket.socket(socket.{family}, socket.SOCK_STREAM)\n"
        "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
        f"s.bind(({address!r}, {port}))\n"
        "s.listen(1)\n"
        "time.sleep(90)\n"
    )


def _wait_until_connectable(process, address: str, port: int, *, timeout_seconds: float = 15.0):
    """Block until ``(address, port)`` is genuinely accepting connections, or
    return ``None`` on timeout (caller decides whether to retry with a fresh
    spawn or give up)."""

    deadline = time.monotonic() + timeout_seconds
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((address, port), timeout=0.5):
                return process
        except OSError as error:
            last_error = error
            time.sleep(0.05)
    return last_error


def _spawn_listening_process(
    binary, port: int, *, address: str = "127.0.0.1", family: str = "AF_INET", attempts: int = 3
):
    """Spawn ``binary`` (any real executable -- the pinned copy OR an
    unrelated one, per test) running ``_listener_code``, and block until the
    socket is genuinely accepting connections before returning (removes the
    spawn/bind race). Retries with a FRESH spawn (not just a longer wait) up
    to ``attempts`` times -- this sandboxed Windows host occasionally stalls
    an individual spawned process for tens of seconds under load (observed
    empirically, not merely first-exec AV-scan latency: it also affects an
    un-copied, already-resident ``sys.executable`` spawn), and a fresh
    process is a more reliable recovery than waiting longer on a possibly
    wedged one."""

    last_error: OSError | str | None = None
    for _attempt in range(attempts):
        process = subprocess.Popen(
            [str(binary), "-c", _listener_code(port, address=address, family=family)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        result = _wait_until_connectable(process, address, port)
        if isinstance(result, subprocess.Popen):
            return result
        last_error = result
        _terminate(process)
    raise AssertionError(
        f"nothing ever listened on {address}:{port} after {attempts} spawn attempts: {last_error}"
    )


def _spawn_wildcard_listening_process(
    binary, port: int, *, family: str = "AF_INET", attempts: int = 3
):
    """Spawn a REAL listener bound to the WILDCARD address (``0.0.0.0`` for
    v4, ``::`` for v6) -- used only by the wildcard-bind design-decision
    probe (T5 fix-3 probe 5). Same fresh-spawn retry policy as
    ``_spawn_listening_process``."""

    wildcard = "0.0.0.0" if family == "AF_INET" else "::"
    probe_address = "127.0.0.1" if family == "AF_INET" else "::1"
    last_error: OSError | str | None = None
    for _attempt in range(attempts):
        process = subprocess.Popen(
            [str(binary), "-c", _listener_code(port, address=wildcard, family=family)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        result = _wait_until_connectable(process, probe_address, port)
        if isinstance(result, subprocess.Popen):
            return result
        last_error = result
        _terminate(process)
    raise AssertionError(
        f"nothing ever listened on {wildcard}:{port} (probed via {probe_address}) after "
        f"{attempts} spawn attempts: {last_error}"
    )


def _matching_session(runtime_receipt, **overrides):
    llama_cpp = runtime_receipt["llama_cpp"]
    base = dict(
        binary_path=llama_cpp["binary_path"],
        binary_sha256=llama_cpp["binary_sha256"],
        model_files=tuple(
            ModelFileRef(path=e["path"], sha256=e["sha256"]) for e in runtime_receipt["gguf_files"]
        ),
    )
    base.update(overrides)
    return _session(**base)


# ---------------------------------------------------------------------------
# _resolve_model_file_source / _model_file_argv -- ext4-first model path
# resolution (2026-08-16 perf fix). No real model bytes anywhere here: tiny
# fake files stand in for the multi-GB GGUFs, and the two constants are
# monkeypatched to the fake files' own hashes so the pass/fail branches are
# exercised without needing a hash preimage of the real production pins.
# ---------------------------------------------------------------------------


def test_ext4_models_root_default_matches_the_known_mirror_location():
    # Locks in the exact path the 2026-08-16 perf fix's operator set up --
    # a silent change here would misroute every future launch.
    assert EXT4_MODELS_ROOT_DEFAULT == Path("/home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km")


def test_ext4_model_sha256_pins_match_the_committed_runtime_receipt():
    """Regression guard against the two embedded constants drifting from the
    receipt (and, transitively, the umbrella lock note the module docstring
    cites) -- the exact failure mode ``_resolve_model_file_source`` is
    written to refuse toward safety on, caught here as a static check
    instead of only at run time."""

    receipt_path = (
        Path(__file__).resolve().parents[2] / "docs" / "receipts" / "runtime-q4km-featcache.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_pins = {Path(e["path"]).name: e["sha256"] for e in receipt["gguf_files"]}
    assert EXT4_MODEL_SHA256_PINS == receipt_pins


def test_resolve_model_file_source_prefers_ext4_when_present_and_hash_matches(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    data_bytes = b"cold-9p-copy"
    (data_root / "models" / "x").mkdir(parents=True)
    (data_root / "models" / "x" / "model.gguf").write_bytes(data_bytes)

    ext4_root = tmp_path / "ext4"
    ext4_root.mkdir()
    ext4_bytes = b"fast-local-copy"
    ext4_pin = _sha(ext4_bytes)
    (ext4_root / "model.gguf").write_bytes(ext4_bytes)

    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    monkeypatch.setattr(lifecycle_module, "EXT4_MODEL_SHA256_PINS", {"model.gguf": ext4_pin})

    entry = ModelFileRef(path="models/x/model.gguf", sha256=ext4_pin)
    resolved = _resolve_model_file_source(data_root, entry, ext4_root=ext4_root)
    assert resolved == ext4_root / "model.gguf"
    assert resolved.read_bytes() == ext4_bytes


def test_resolve_model_file_source_falls_back_when_ext4_file_missing(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_bytes = b"cold-9p-copy"
    (data_root / "models" / "x").mkdir(parents=True)
    (data_root / "models" / "x" / "model.gguf").write_bytes(data_bytes)

    ext4_root = tmp_path / "ext4-empty"  # never created: candidate file absent

    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    monkeypatch.setattr(lifecycle_module, "EXT4_MODEL_SHA256_PINS", {"model.gguf": "a" * 64})

    entry = ModelFileRef(path="models/x/model.gguf", sha256="a" * 64)
    resolved = _resolve_model_file_source(data_root, entry, ext4_root=ext4_root)
    assert resolved == (data_root / "models" / "x" / "model.gguf").resolve()


def test_resolve_model_file_source_falls_back_on_ext4_hash_mismatch(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_bytes = b"cold-9p-copy"
    (data_root / "models" / "x").mkdir(parents=True)
    (data_root / "models" / "x" / "model.gguf").write_bytes(data_bytes)

    ext4_root = tmp_path / "ext4"
    ext4_root.mkdir()
    # ext4 file present but its bytes do NOT hash to the pinned value --
    # a stale or partial mirror must never be trusted.
    (ext4_root / "model.gguf").write_bytes(b"corrupted-or-partial-copy")

    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    expected_pin = "a" * 64
    monkeypatch.setattr(lifecycle_module, "EXT4_MODEL_SHA256_PINS", {"model.gguf": expected_pin})

    entry = ModelFileRef(path="models/x/model.gguf", sha256=expected_pin)
    resolved = _resolve_model_file_source(data_root, entry, ext4_root=ext4_root)
    assert resolved == (data_root / "models" / "x" / "model.gguf").resolve()


def test_resolve_model_file_source_falls_back_when_receipt_pin_disagrees_with_constant(
    tmp_path, monkeypatch
):
    """A drift between the embedded constant and the runtime receipt's own
    per-file pin must fail toward data_root, never toward trusting the
    embedded constant over the receipt."""

    data_root = tmp_path / "data"
    data_bytes = b"cold-9p-copy"
    (data_root / "models" / "x").mkdir(parents=True)
    (data_root / "models" / "x" / "model.gguf").write_bytes(data_bytes)

    ext4_root = tmp_path / "ext4"
    ext4_root.mkdir()
    ext4_bytes = b"fast-local-copy"
    ext4_pin = _sha(ext4_bytes)
    (ext4_root / "model.gguf").write_bytes(ext4_bytes)

    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    monkeypatch.setattr(lifecycle_module, "EXT4_MODEL_SHA256_PINS", {"model.gguf": ext4_pin})

    # entry.sha256 (the receipt's own pin) disagrees with the constant above.
    entry = ModelFileRef(path="models/x/model.gguf", sha256="b" * 64)
    resolved = _resolve_model_file_source(data_root, entry, ext4_root=ext4_root)
    assert resolved == (data_root / "models" / "x" / "model.gguf").resolve()


def test_resolve_model_file_source_ignores_unpinned_filenames(tmp_path):
    """A filename absent from EXT4_MODEL_SHA256_PINS (e.g. any of the
    synthetic 'model.gguf'/'mmproj.gguf' fixtures used throughout the rest of
    this file) always resolves via data_root -- unchanged, pre-existing
    behavior for a host with no ext4 mirror configured at all."""

    data_root = tmp_path / "data"
    (data_root / "models" / "x").mkdir(parents=True)
    (data_root / "models" / "x" / "model.gguf").write_bytes(b"whatever")

    entry = ModelFileRef(path="models/x/model.gguf", sha256="a" * 64)
    resolved = _resolve_model_file_source(data_root, entry, ext4_root=Path("/does/not/exist"))
    assert resolved == (data_root / "models" / "x" / "model.gguf").resolve()


def test_ext4_models_root_env_override(monkeypatch, tmp_path):
    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    override = tmp_path / "custom-mirror"
    monkeypatch.setenv(EXT4_MODELS_ROOT_ENV, str(override))
    assert lifecycle_module._ext4_models_root() == override


def test_ext4_models_root_env_unset_uses_default(monkeypatch):
    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    monkeypatch.delenv(EXT4_MODELS_ROOT_ENV, raising=False)
    assert lifecycle_module._ext4_models_root() == EXT4_MODELS_ROOT_DEFAULT


# ---------------------------------------------------------------------------
# feat_cache_dir -- per-campaign feature-cache directory convention
# (2026-08-16, docs/featcache-directories.md). Same env-override-with-default
# shape as _ext4_models_root above, mirrored here for the same reason: an
# unset override must resolve to the exact legacy, already-warm literal path
# every existing q4km-family config fragment already hand-types.
# ---------------------------------------------------------------------------


def test_feat_cache_dir_default_matches_the_warm_legacy_cache():
    # Locks in the exact literal path every existing q4km-family model
    # fragment already hand-types in its own server_env -- a silent change
    # here would orphan those fragments' already-warm 26GB cache.
    assert FEAT_CACHE_DIR_DEFAULT == "/home/chao/feat-cache/q4km"


def test_feat_cache_dir_env_unset_uses_default(monkeypatch):
    monkeypatch.delenv(FEAT_CACHE_DIR_ENV, raising=False)
    assert feat_cache_dir() == FEAT_CACHE_DIR_DEFAULT


def test_feat_cache_dir_env_override(monkeypatch):
    monkeypatch.setenv(FEAT_CACHE_DIR_ENV, "/home/chao/feat-cache/slurp-q4km")
    assert feat_cache_dir() == "/home/chao/feat-cache/slurp-q4km"


def test_feat_cache_dir_env_empty_string_falls_back_to_default(monkeypatch):
    # An empty override is not a meaningful directory choice -- treat it the
    # same as unset rather than handing callers "".
    monkeypatch.setenv(FEAT_CACHE_DIR_ENV, "")
    assert feat_cache_dir() == FEAT_CACHE_DIR_DEFAULT


def test_model_file_argv_prefers_ext4_for_both_main_and_mmproj(tmp_path, monkeypatch):
    """End-to-end through the real ``_model_file_argv`` entry point
    ``start_session`` calls -- proves the ext4-first resolution is actually
    wired into the argv the server is launched with, for BOTH the main shard
    and the mmproj file."""

    data_root = tmp_path / "data"
    (data_root / "models" / "x").mkdir(parents=True)
    (data_root / "models" / "x" / "model.gguf").write_bytes(b"cold-main")
    (data_root / "models" / "x" / "mmproj.gguf").write_bytes(b"cold-mmproj")

    ext4_root = tmp_path / "ext4"
    ext4_root.mkdir()
    main_bytes, mmproj_bytes = b"fast-main", b"fast-mmproj"
    main_pin, mmproj_pin = _sha(main_bytes), _sha(mmproj_bytes)
    (ext4_root / "model.gguf").write_bytes(main_bytes)
    (ext4_root / "mmproj.gguf").write_bytes(mmproj_bytes)

    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    monkeypatch.setattr(
        lifecycle_module,
        "EXT4_MODEL_SHA256_PINS",
        {"model.gguf": main_pin, "mmproj.gguf": mmproj_pin},
    )
    monkeypatch.setattr(lifecycle_module, "_ext4_models_root", lambda: ext4_root)

    model_files = (
        ModelFileRef(path="models/x/model.gguf", sha256=main_pin),
        ModelFileRef(path="models/x/mmproj.gguf", sha256=mmproj_pin),
    )
    argv = _model_file_argv(data_root, model_files)
    assert argv == [
        "-m", str(ext4_root / "model.gguf"),
        "--mmproj", str(ext4_root / "mmproj.gguf"),
    ]


def test_model_file_argv_uses_explicit_materialization_root_without_legacy_fallback(tmp_path):
    data_root = tmp_path / "slow-data"
    model_root = tmp_path / "fast-models"
    relative = Path("models") / "x" / "model.gguf"
    (model_root / relative).parent.mkdir(parents=True)
    (model_root / relative).write_bytes(b"fast-main")
    entry = ModelFileRef(path=relative.as_posix(), sha256=_sha(b"fast-main"))

    argv = _model_file_argv(
        data_root,
        (entry,),
        role="inference",
        model_root=model_root,
    )

    assert argv == ["-m", str((model_root / relative).resolve()), "--no-mmproj"]


# ---------------------------------------------------------------------------
# require_loopback -- probe 1 (non-loopback base_url refused).
# ---------------------------------------------------------------------------


def test_require_loopback_accepts_127001():
    assert require_loopback("http://127.0.0.1:8080") == ("127.0.0.1", 8080)


def test_require_loopback_accepts_bracketed_ipv6_literal():
    assert require_loopback("http://[::1]:8080") == ("::1", 8080)


def test_require_loopback_accepts_localhost():
    host, port = require_loopback("http://localhost:8080")
    assert (host, port) == ("localhost", 8080)


@pytest.mark.parametrize(
    "base_url", ["http://10.0.0.5:8080", "http://example.com:8080", "http://192.168.1.5:8080"]
)
def test_require_loopback_refuses_non_loopback_host(base_url):
    with pytest.raises(SessionError, match="loopback"):
        require_loopback(base_url)


# ---------------------------------------------------------------------------
# SessionReceipt structural validation + JSON round trip.
# ---------------------------------------------------------------------------


def test_valid_session_receipt_round_trips_through_json(tmp_path):
    receipt = _session().validate()
    path = tmp_path / "runs" / "session.json"
    write_session_receipt(path, receipt)
    assert read_session_receipt(path) == receipt


def test_inference_session_receipt_round_trips_and_binds_decoder_only(tmp_path):
    receipt = _inference_session().validate()
    path = tmp_path / "inference-session.json"
    write_session_receipt(path, receipt)
    assert read_session_receipt(path) == receipt
    assert receipt.role == "inference"
    assert [entry.path for entry in receipt.model_files] == ["models/x/model.gguf"]


def test_inference_session_refuses_mmproj_argv_or_featcache_environment():
    with pytest.raises(SessionError, match="must not mention mmproj"):
        _inference_session(argv=("llama-server", "--mmproj", "models/x/mmproj.gguf")).validate()
    with pytest.raises(SessionError, match="LLAMA_MTMD_FEAT_CACHE_DIR"):
        _inference_session(server_env_keys=("LLAMA_MTMD_FEAT_CACHE_DIR",)).validate()


def test_inference_model_argv_excludes_mmproj_and_adds_explicit_disable(tmp_path):
    data_root = tmp_path / "data"
    for entry in _model_files():
        path = data_root / entry.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"placeholder")
    argv = _model_file_argv(data_root, _model_files(), role="inference")
    assert argv == ["-m", str(data_root / "models/x/model.gguf"), "--no-mmproj"]
    assert "--mmproj" not in argv


def test_inference_session_matches_decoder_subset_of_legacy_runtime_receipt():
    runtime = {
        "llama_cpp": {
            "binary_path": "llama.cpp/build/bin/llama-server",
            "binary_sha256": "c" * 64,
        },
        "gguf_files": [
            {"path": entry.path, "sha256": entry.sha256} for entry in _model_files()
        ],
    }
    assert verify_against_runtime_receipt(_inference_session(), runtime).role == "inference"


def test_inference_process_audit_proves_zero_mmproj_hits(tmp_path):
    session = _inference_session(pid=321)
    process_root = tmp_path / "proc" / "321"
    (process_root / "fd").mkdir(parents=True)
    (process_root / "cmdline").write_bytes(b"llama-server\0--no-mmproj\0-m\0model.gguf\0")
    (process_root / "maps").write_text(
        "00400000-00401000 r-xp 00000000 00:00 0 /runtime/llama-server\n",
        encoding="utf-8",
    )
    audit = audit_mmproj_free_inference(session, proc_root=tmp_path / "proc")
    assert audit["mmproj_loaded"] is False
    assert audit["mmproj_hit_count"] == 0


def test_inference_process_audit_fails_on_mapped_or_open_mmproj(tmp_path):
    session = _inference_session(pid=322)
    process_root = tmp_path / "proc" / "322"
    (process_root / "fd").mkdir(parents=True)
    (process_root / "cmdline").write_bytes(b"llama-server\0--no-mmproj\0")
    (process_root / "maps").write_text(
        "00400000-00401000 r--p 00000000 00:00 0 /models/mmproj.gguf\n",
        encoding="utf-8",
    )
    with pytest.raises(SessionError, match="mmproj hit"):
        audit_mmproj_free_inference(session, proc_root=tmp_path / "proc")


def test_session_receipt_refuses_non_loopback_host():
    with pytest.raises(SessionError, match="loopback"):
        _session(host="10.0.0.5").validate()


def test_session_receipt_refuses_wrong_schema():
    with pytest.raises(SessionError, match="schema"):
        _session(schema="wrong").validate()


def test_read_session_receipt_refuses_missing_file(tmp_path):
    with pytest.raises(SessionError, match="cannot read"):
        read_session_receipt(tmp_path / "does-not-exist.json")


# ---------------------------------------------------------------------------
# verify_against_runtime_receipt -- probe 3 (declared-value mismatch refused).
# Pure declared-value comparison: no pid/process involved at all.
# ---------------------------------------------------------------------------


def test_verify_against_runtime_receipt_accepts_matching_identity(tmp_path):
    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    verify_against_runtime_receipt(_matching_session(runtime_receipt), runtime_receipt)


def test_verify_against_runtime_receipt_refuses_binary_hash_mismatch(tmp_path):
    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, binary_sha256="f" * 64)
    with pytest.raises(SessionError, match="binary identity"):
        verify_against_runtime_receipt(session, runtime_receipt)


def test_verify_against_runtime_receipt_refuses_model_file_mismatch(tmp_path):
    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(
        runtime_receipt,
        model_files=(ModelFileRef(path="models/x/other.gguf", sha256="d" * 64),),
    )
    with pytest.raises(SessionError, match="model file set"):
        verify_against_runtime_receipt(session, runtime_receipt)


# ---------------------------------------------------------------------------
# Cross-model identity binding (the SESSION half of docs/readiness/
# 2026-08-09-int4-model-identity.md's gap; the GATE half is
# tests/contract/test_model_lock_key_binding.py). Nothing in this module's
# own identity checks is keyed by ``model_lock_key``, or by any hardcoded
# model constant at all -- ``verify_against_runtime_receipt``/
# ``_pinned_binary``/``_pinned_model_files`` compare a session ONLY against
# whichever ``runtime_receipt`` mapping the caller hands them, and
# ``core.driver.smoke._cli_smoke``/``core.driver.cli._cli_run`` always
# derive that mapping from the SAME composed model config that chose the
# receipt PATH (``core.config.resolve_runtime_receipt_path``) -- so a real
# Q4_K_M-declaring run has no path to reach a session verified against the
# Q8_0 receipt's files, or vice versa. This proves the underlying mechanism
# directly: a session genuinely started/matching one pinned model's runtime
# receipt is refused when checked against a DIFFERENT pinned model's runtime
# receipt, using realistic Q8_0-vs-Q4_K_M subdirectory shapes (not merely
# the single-file substitution ``test_verify_against_runtime_receipt_
# refuses_model_file_mismatch`` above already covers).
# ---------------------------------------------------------------------------


def _q4km_runtime_world(tmp_path):
    """A second pinned model's runtime-receipt dict, same shape as
    ``_runtime_world`` but at a distinct subdir/key -- the launcher/library
    block is irrelevant here (session identity for the MODEL half is decided
    entirely by ``gguf_files``), so it is omitted."""

    data_root = tmp_path / "data"
    model_dir = data_root / "models" / "qwen3-omni-30b-a3b-instruct-gguf-q4km"
    model_dir.mkdir(parents=True)
    main_relpath = "models/qwen3-omni-30b-a3b-instruct-gguf-q4km/model.gguf"
    mmproj_relpath = "models/qwen3-omni-30b-a3b-instruct-gguf-q4km/mmproj.gguf"
    main_bytes = b"fake-q4km-main-gguf"
    mmproj_bytes = b"fake-q4km-mmproj-gguf"
    (data_root / main_relpath).write_bytes(main_bytes)
    (data_root / mmproj_relpath).write_bytes(mmproj_bytes)
    return {
        "schema": "saea-runtime-receipt-v2",
        "study": "speech-aware-evidence-acquisition",
        "model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
        "llama_cpp": {
            "build_commit": "a" * 40,
            "reported_build": "version: 1 (aaaaaaa)",
            "binary_path": "llama.cpp/build/bin/llama-server",
            "binary_bytes": 17,
            "binary_sha256": _sha(b"fake-llama-server"),
        },
        "gguf_files": [
            {"path": main_relpath, "bytes": len(main_bytes), "sha256": _sha(main_bytes)},
            {"path": mmproj_relpath, "bytes": len(mmproj_bytes), "sha256": _sha(mmproj_bytes)},
        ],
        "runtime_libraries": [
            {"path": "llama.cpp/build/bin/lib-fake.so", "bytes": 8, "sha256": _sha(b"fake-lib")},
        ],
    }


def test_a_q8_matching_session_is_refused_against_the_q4km_runtime_receipt(tmp_path):
    """A session genuinely bound to the Q8_0 receipt (identical binary,
    identical GGUF paths/hashes) is refused when re-verified against the
    Q4_K_M receipt -- a run using the Q4_K_M config can never pass off the
    Q8_0 session's files as its own."""

    _, _, _, q8_receipt = _runtime_world(tmp_path)
    q4km_receipt = _q4km_runtime_world(tmp_path)
    session = _matching_session(q8_receipt)
    with pytest.raises(SessionError, match="model file set"):
        verify_against_runtime_receipt(session, q4km_receipt)


def test_a_q4km_matching_session_is_refused_against_the_q8_runtime_receipt(tmp_path):
    """The reverse pairing: a session genuinely bound to the Q4_K_M receipt
    is refused when re-verified against the Q8_0 receipt -- proves this is a
    real two-way binding, not a one-sided check that only catches one
    direction."""

    _, _, _, q8_receipt = _runtime_world(tmp_path)
    q4km_receipt = _q4km_runtime_world(tmp_path)
    session = _matching_session(q4km_receipt)
    with pytest.raises(SessionError, match="model file set"):
        verify_against_runtime_receipt(session, q8_receipt)


# ---------------------------------------------------------------------------
# LlamaServerTransport -- probes 1, 2, 3, 6, 7 at the send choke point.
# These declared-value/loopback probes are refused BEFORE the process-
# identity check is ever reached, so a placeholder (non-existent, non-real)
# runtime_root is fine for them -- it is never resolved.
# ---------------------------------------------------------------------------


def test_transport_refuses_without_a_session_receipt(tmp_path):
    """Probe 2: asked to send with no session receipt -> refused, before any
    __call__/send is even possible (construction itself fails closed)."""

    with pytest.raises(SessionError, match="session"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, None, {}, tmp_path, post=lambda u, b: b""
        )


def test_transport_refuses_non_loopback_base_url(tmp_path):
    """Probe 1 at the transport."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, host="127.0.0.1", port=8080)
    with pytest.raises(SessionError, match="loopback"):
        LlamaServerTransport(
            "http://10.0.0.5:8080", tmp_path, session, runtime_receipt, tmp_path,
            post=lambda u, b: b"",
        )


def test_transport_refuses_session_with_binary_hash_mismatch(tmp_path):
    """Probe 3 at the transport: even a hand-built SessionReceipt (bypassing
    start_session/attach_session entirely) is refused here."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, binary_sha256="0" * 64)
    with pytest.raises(SessionError, match="binary identity"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, session, runtime_receipt, tmp_path,
            post=lambda u, b: b"",
        )


def test_transport_refuses_session_port_mismatch_with_base_url(tmp_path):
    """Probe 6: a session receipt recorded for a different port than the
    transport's own base_url is refused, even though both are individually
    loopback-valid."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, host="127.0.0.1", port=9090)
    with pytest.raises(SessionError, match="does not match"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, session, runtime_receipt, tmp_path,
            post=lambda u, b: b"",
        )


def test_transport_refuses_session_host_mismatch_with_base_url(tmp_path):
    """Probe 6, host variant: 'localhost' and '127.0.0.1' are both loopback
    but not the SAME endpoint a session receipt was recorded for."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, host="localhost", port=8080)
    with pytest.raises(SessionError, match="does not match"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, session, runtime_receipt, tmp_path,
            post=lambda u, b: b"",
        )


@pytest.mark.skipif(os.name == "nt", reason=_COPIED_BINARY_LISTENER_SKIP_REASON)
def test_transport_accepts_a_valid_matching_session_and_sends(tmp_path):
    """Probe 7 (transport half) / T5 fix-2 probe 3 (legitimate ACCEPT): a
    session naming a process that is BOTH the pinned binary AND genuinely
    listening on the claimed port is accepted, and an actual send still
    works exactly as before T5."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    process = _spawn_listening_process(binary, 18190)
    try:
        session = _matching_session(runtime_receipt, host="127.0.0.1", port=18190, pid=process.pid)
        transport = LlamaServerTransport(
            "http://127.0.0.1:18190",
            tmp_path,
            session,
            runtime_receipt,
            runtime_root,
            post=lambda u, b: _canned_response(),
        )
        media = tmp_path / "media" / "5000001.mp3"
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(b"fake-mp3-bytes")
        payload = {
            "request_id": "req-1",
            "carrier_lock_key": "earnings22-original",
            "sample_id": "5000001",
            "speech_ref": "earnings22-original/5000001",
            "media_relpath": "media/5000001.mp3",
            "audio_seconds": 10.0,
            "sample_rate_hz": 16000,
            "task_instruction": "Transcribe the speech verbatim.",
            "history": [],
            "decoding_params": {"temperature": 0, "seed": 20260803},
        }
        raw = transport(json.dumps(payload).encode())
        assert json.loads(raw)["text"] == "hello world"
    finally:
        _terminate(process)


# ---------------------------------------------------------------------------
# CRITICAL, reviewer-demonstrated exploit: a forged SessionReceipt with the
# CORRECT, PUBLIC binary_path/binary_sha256/model_files (copied verbatim from
# the committed runtime receipt) but naming an unrelated LIVE pid (here: this
# very test process). Before the fix, attach_session and LlamaServerTransport
# construction both only checked declared-value agreement plus bare
# liveness -- both trivially satisfied by such a forgery -- and returned/
# accepted the receipt as genuine, letting an "answered-by-imposter" request
# round-trip successfully. Standing regressions, exercised at BOTH
# independent enforcement layers.
# ---------------------------------------------------------------------------


def test_attach_refuses_alive_but_unrelated_pid(tmp_path):
    runtime_root, _binary, runtime_receipt = _live_runtime_world(tmp_path)
    forged = _matching_session(runtime_receipt, pid=os.getpid())
    receipt_path = tmp_path / "forged-session.json"
    write_session_receipt(receipt_path, forged)
    with pytest.raises(SessionError, match="is running"):
        attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root)


def test_transport_refuses_alive_but_unrelated_pid(tmp_path):
    runtime_root, _binary, runtime_receipt = _live_runtime_world(tmp_path)
    forged = _matching_session(runtime_receipt, pid=os.getpid())
    with pytest.raises(SessionError, match="is running"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, forged, runtime_receipt, runtime_root,
            post=lambda u, b: b"",
        )


# ---------------------------------------------------------------------------
# T5 fix-2: socket-ownership binding. A materially equivalent, still-open
# gap in the SAME invariant an independent re-review demonstrated live on
# BOTH Windows and WSL2: _verify_pid_runs_pinned_binary proves "the process
# at this pid runs the pinned binary", but nothing bound that pid to the
# SOCKET the transport actually talks to -- session.host/port/argv are
# self-declared receipt fields. The re-reviewer spawned a SECOND genuine
# instance of the pinned binary (not listening on the target port at all),
# forged a SessionReceipt naming that pid with port=8080, and construction
# SUCCEEDED. Standing regressions below (probes 1/2 from that finding);
# probe 3 (legitimate ACCEPT) is exercised by
# test_transport_accepts_a_valid_matching_session_and_sends and
# test_attach_succeeds_for_a_live_matching_session above, both of which now
# spawn a process that REALLY binds the claimed port; probe 4 (undeterminable
# ownership) is the last test in this section.
# ---------------------------------------------------------------------------


def test_attach_refuses_pinned_binary_process_not_listening_on_claimed_port(tmp_path):
    """T5 fix-2 probe 1 -- THE re-reviewer's exact exploit: a SECOND genuine,
    live instance of the pinned binary (so the T5 fix-1 identity check ALONE
    would accept it) that is NOT listening on the claimed port at all. Must
    fail before this fix, pass (refuse) after it."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    idle_process = _spawn_matching_process(binary)  # alive, pinned binary, binds nothing
    try:
        forged = _matching_session(
            runtime_receipt, host="127.0.0.1", port=18193, pid=idle_process.pid
        )
        receipt_path = tmp_path / "forged-session.json"
        write_session_receipt(receipt_path, forged)
        with pytest.raises(SessionError, match="no LISTEN socket found"):
            attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root)
    finally:
        _terminate(idle_process)


def test_transport_refuses_pinned_binary_process_not_listening_on_claimed_port(tmp_path):
    """Same exploit, transport-construction layer."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    idle_process = _spawn_matching_process(binary)
    try:
        forged = _matching_session(
            runtime_receipt, host="127.0.0.1", port=18194, pid=idle_process.pid
        )
        with pytest.raises(SessionError, match="no LISTEN socket found"):
            LlamaServerTransport(
                "http://127.0.0.1:18194", tmp_path, forged, runtime_receipt, runtime_root,
                post=lambda u, b: b"",
            )
    finally:
        _terminate(idle_process)


def test_attach_refuses_listener_that_is_not_the_pinned_binary(tmp_path):
    """T5 fix-2 probe 2: a process IS genuinely listening on the claimed
    port, but it is NOT the pinned binary (a different real executable, the
    interpreter's own un-copied path). The EXISTING T5 fix-1 identity check
    must fire -- proving the two checks compose, neither alone sufficient."""

    runtime_root, _binary, runtime_receipt = _live_runtime_world(tmp_path)
    impostor = _spawn_listening_process(Path(sys.executable), 18195)
    try:
        forged = _matching_session(
            runtime_receipt, host="127.0.0.1", port=18195, pid=impostor.pid
        )
        receipt_path = tmp_path / "forged-session.json"
        write_session_receipt(receipt_path, forged)
        with pytest.raises(SessionError, match="is running"):
            attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root)
    finally:
        _terminate(impostor)


def test_transport_refuses_listener_that_is_not_the_pinned_binary(tmp_path):
    """Same composition proof, transport-construction layer."""

    runtime_root, _binary, runtime_receipt = _live_runtime_world(tmp_path)
    impostor = _spawn_listening_process(Path(sys.executable), 18196)
    try:
        forged = _matching_session(
            runtime_receipt, host="127.0.0.1", port=18196, pid=impostor.pid
        )
        with pytest.raises(SessionError, match="is running"):
            LlamaServerTransport(
                "http://127.0.0.1:18196", tmp_path, forged, runtime_receipt, runtime_root,
                post=lambda u, b: b"",
            )
    finally:
        _terminate(impostor)


@pytest.mark.skipif(os.name == "nt", reason=_COPIED_BINARY_LISTENER_SKIP_REASON)
def test_socket_ownership_undeterminable_fails_closed(tmp_path, monkeypatch):
    """T5 fix-2 probe 4: if socket ownership cannot be determined AT ALL
    (simulating a ``/proc/net/tcp`` read failure on POSIX, or a failed
    ``GetExtendedTcpTable`` lookup on Windows), the touch is refused --
    never silently treated as 'unknown, so allow'. (The OTHER undeterminable
    shape -- the lookup mechanism working fine but finding no entry at all --
    is exactly probe 1 above, already a standing regression via the real,
    unmocked code path.)"""

    from speech_aware_evidence_acquisition.core import session as session_module

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    process = _spawn_listening_process(binary, 18197)
    try:
        session = _matching_session(runtime_receipt, host="127.0.0.1", port=18197, pid=process.pid)

        def _boom(*_args, **_kwargs):
            raise SessionError("simulated socket-ownership lookup failure")

        if os.name == "nt":
            monkeypatch.setattr(session_module, "_windows_tcp_table_owners", _boom)
        else:
            monkeypatch.setattr(session_module, "_proc_net_listen_entries", _boom)

        with pytest.raises(SessionError, match="simulated socket-ownership lookup failure"):
            LlamaServerTransport(
                "http://127.0.0.1:18197", tmp_path, session, runtime_receipt, runtime_root,
                post=lambda u, b: b"",
            )
    finally:
        _terminate(process)


# ---------------------------------------------------------------------------
# T5 fix-3 (re-review round 3): a materially equivalent bypass IN the fix-2
# design itself. _verify_pid_owns_listening_socket accepted `host` but never
# used it -- POSIX discarded the decoded IP, keeping only the port; Windows
# read dwLocalAddr/ucLocalAddr into the row structs but never consulted
# them. The check therefore bound pid to "some LISTEN socket on that port
# number, in EITHER the v4 or v6 table" -- not to the socket the transport
# actually connects to. '127.0.0.1' and '::1' are DISTINCT, SIMULTANEOUSLY
# BINDABLE addresses (the fix-2 docstring's claim that require_loopback's
# fixed host set made address-filtering unnecessary was WRONG). Live-
# reproduced PoC: pinned-binary process P listening ONLY on [::1]:PORT,
# unrelated unverified process Q listening on 127.0.0.1:PORT; a session
# naming pid=P, host=127.0.0.1, port=PORT passed construction, and a real
# connect to 127.0.0.1:PORT was answered by Q. Secondary bug, same root
# cause, Windows-only: merging the v4 and v6 owner tables by port alone let
# a v6 listener silently overwrite the v4 owner for an identical port
# number, causing a FALSE REFUSAL of a legitimate v4 session.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.name == "nt", reason=_COPIED_BINARY_LISTENER_SKIP_REASON)
def test_attach_refuses_v6_v4_split_forgery(tmp_path):
    """T5 fix-3 probe 1 -- THE re-review's exact exploit, live-reproduced
    end to end on Windows: pinned-binary process P listens ONLY on
    [::1]:PORT; unrelated, unverified process Q listens on 127.0.0.1:PORT
    (same port number, different family). A forged session naming pid=P but
    host=127.0.0.1 must be refused -- P owns no socket at 127.0.0.1:PORT at
    all; only Q does, and Q is not the pinned binary. Verified below (see
    the disable/re-enable check in the fix report) to fail before this fix
    and pass after it."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    port = 18198
    p_process = _spawn_listening_process(binary, port, address="::1", family="AF_INET6")
    q_process = _spawn_listening_process(
        Path(sys.executable), port, address="127.0.0.1", family="AF_INET"
    )
    try:
        forged = _matching_session(runtime_receipt, host="127.0.0.1", port=port, pid=p_process.pid)
        receipt_path = tmp_path / "forged-session.json"
        write_session_receipt(receipt_path, forged)
        with pytest.raises(SessionError, match="does not own the listening socket|is owned by pid"):
            attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root)
    finally:
        _terminate(p_process)
        _terminate(q_process)


@pytest.mark.skipif(os.name == "nt", reason=_COPIED_BINARY_LISTENER_SKIP_REASON)
def test_attach_refuses_v4_v6_reverse_split_forgery(tmp_path):
    """T5 fix-3 probe 2 -- the reverse split: P listens ONLY on
    127.0.0.1:PORT; Q listens on [::1]:PORT. A forged session naming pid=P
    but host=::1 must be refused."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    port = 18199
    p_process = _spawn_listening_process(binary, port, address="127.0.0.1", family="AF_INET")
    q_process = _spawn_listening_process(
        Path(sys.executable), port, address="::1", family="AF_INET6"
    )
    try:
        forged = _matching_session(runtime_receipt, host="::1", port=port, pid=p_process.pid)
        receipt_path = tmp_path / "forged-session.json"
        write_session_receipt(receipt_path, forged)
        with pytest.raises(SessionError, match="does not own the listening socket|is owned by pid"):
            attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root)
    finally:
        _terminate(p_process)
        _terminate(q_process)


@pytest.mark.skipif(os.name == "nt", reason=_COPIED_BINARY_LISTENER_SKIP_REASON)
def test_attach_succeeds_for_v6_only_session(tmp_path):
    """T5 fix-3 probe 3: a legitimate session with host='::1' -- the pinned
    binary genuinely, exclusively listening on [::1]:PORT -- must be
    accepted."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    port = 18200
    process = _spawn_listening_process(binary, port, address="::1", family="AF_INET6")
    try:
        session = _matching_session(runtime_receipt, host="::1", port=port, pid=process.pid)
        receipt_path = tmp_path / "session.json"
        write_session_receipt(receipt_path, session)
        attached = attach_session(
            receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root
        )
        assert attached == session
    finally:
        _terminate(process)


@pytest.mark.skipif(os.name == "nt", reason=_COPIED_BINARY_LISTENER_SKIP_REASON)
def test_attach_succeeds_for_v4_session_despite_unrelated_v6_listener_same_port(tmp_path):
    """T5 fix-3 probe 4, THE SECONDARY bug: a legitimate v4 session must NOT
    be falsely refused merely because an unrelated process also listens on
    the SAME port number under IPv6 -- the fix-2 Windows table merge
    (``owners.update(v4); owners.update(v6)``) let a v6 entry silently
    overwrite the v4 owner for an identical port, producing exactly this
    false refusal for a completely legitimate session."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    port = 18201
    legit_process = _spawn_listening_process(binary, port, address="127.0.0.1", family="AF_INET")
    unrelated_process = _spawn_listening_process(
        Path(sys.executable), port, address="::1", family="AF_INET6"
    )
    try:
        session = _matching_session(
            runtime_receipt, host="127.0.0.1", port=port, pid=legit_process.pid
        )
        receipt_path = tmp_path / "session.json"
        write_session_receipt(receipt_path, session)
        attached = attach_session(
            receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root
        )
        assert attached == session
    finally:
        _terminate(legit_process)
        _terminate(unrelated_process)


@pytest.mark.skipif(os.name == "nt", reason=_COPIED_BINARY_LISTENER_SKIP_REASON)
def test_attach_refuses_wildcard_bound_listener_for_a_specific_loopback_claim(tmp_path):
    """T5 fix-3 probe 5 -- the wildcard-bind design decision, ASSERTED
    EXPLICITLY: a wildcard bind (0.0.0.0) is NEVER treated as satisfying a
    session's claim of the specific address 127.0.0.1, even though the OS
    would in fact route a 127.0.0.1 connection to a 0.0.0.0-bound listener
    in the absence of a more specific competing bind. See
    ``core.session._posix_verify_pid_owns_listening_socket``'s docstring
    for the reasoning: exact-address matching is the more conservative of
    the two choices the re-review explicitly allowed ('prefer refusing a
    wildcard bind'), and costs nothing for this study's actual usage --
    llama-server is always invoked with an explicit, specific --host, never
    a wildcard."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    port = 18202
    process = _spawn_wildcard_listening_process(binary, port, family="AF_INET")
    try:
        session = _matching_session(runtime_receipt, host="127.0.0.1", port=port, pid=process.pid)
        receipt_path = tmp_path / "session.json"
        write_session_receipt(receipt_path, session)
        with pytest.raises(SessionError, match="no LISTEN socket found"):
            attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root)
    finally:
        _terminate(process)


# ---------------------------------------------------------------------------
# Native-Windows, IN-PROCESS coverage of the Windows socket-ownership API
# (GetExtendedTcpTable / _windows_verify_pid_owns_listening_socket).
#
# Deliberate, owner-approved split (see docs/engineering.md, and the module
# docstring at the top of this file): every test above that needs a SECOND,
# genuinely spawned pinned-binary process -- a freshly COPIED executable
# image at a brand-new pytest tmp_path -- that also binds a LISTENING
# socket is POSIX-only, because that exact combination makes native
# Windows Defender Firewall prompt for an unrecognized program on
# essentially every run. Those probes already run clean under WSL2.
#
# The tests below instead bind a REAL loopback TCP listener INSIDE this
# very pytest process -- no new executable image at all, so no new
# firewall prompt (python.exe running pytest is already a known,
# already-network-authorized program on this host) -- and call
# ``_windows_verify_pid_owns_listening_socket`` directly against the REAL
# ``GetExtendedTcpTable`` Windows API and a REAL, kernel-visible listening
# socket. Covered: ownership correctly attributed to ``os.getpid()``;
# refusal of a different pid (the function under test never queries
# whether that OTHER pid is alive -- it only compares the TCP table's
# recorded owner pid, so an arbitrary distinct integer exercises the
# refusal exactly as well as a genuinely live unrelated process would, with
# no second process needed at all); and that the T5 fix-3
# (family, address, port)-keyed lookup correctly separates IPv4 from IPv6
# rather than matching by port number alone (a v4-only listener must NOT
# satisfy a v6 claim on the same port number, and vice versa).
#
# NOT covered here (still WSL2-only): the T5 fix-3 "secondary bug" scenario
# specifically -- a v4 listener and a v6 listener owned by TWO DIFFERENT
# pids sharing the exact same port number, proving the Windows owner-table
# merge no longer lets a v6 entry silently overwrite the v4 owner and
# falsely refuse a legitimate v4 session. Reproducing genuinely DIFFERING
# owner pids for that scenario needs a second process (an in-process test
# can only ever bind both sockets as itself, which would pass whether or
# not the merge bug were still present -- it cannot distinguish fixed from
# regressed code); ``test_attach_refuses_v6_v4_split_forgery``,
# ``test_attach_refuses_v4_v6_reverse_split_forgery`` and
# ``test_attach_succeeds_for_v4_session_despite_unrelated_v6_listener_same_port``
# above still exercise it end to end, under WSL2.
# ---------------------------------------------------------------------------


def _bind_loopback_listener(family: int, address: str) -> socket.socket:
    """Bind and LISTEN on an OS-assigned ephemeral port of ``address`` --
    genuinely, inside THIS process, no subprocess involved at all."""

    listener = socket.socket(family, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((address, 0))
    listener.listen(1)
    return listener


@pytest.mark.skipif(
    os.name != "nt",
    reason="exercises the Windows-only GetExtendedTcpTable socket-ownership "
    "API directly; the equivalent POSIX code path "
    "(_posix_verify_pid_owns_listening_socket, /proc/net/tcp[6]) is already "
    "exercised end to end by the real-spawn probes above under WSL2/POSIX",
)
class TestWindowsSocketOwnershipInProcess:
    def test_v4_listener_ownership_attributed_to_self(self):
        from speech_aware_evidence_acquisition.core import session as session_module

        listener = _bind_loopback_listener(socket.AF_INET, "127.0.0.1")
        try:
            port = listener.getsockname()[1]
            session_module._windows_verify_pid_owns_listening_socket(
                os.getpid(), "127.0.0.1", port
            )
        finally:
            listener.close()

    def test_v4_listener_refuses_a_different_pid(self):
        from speech_aware_evidence_acquisition.core import session as session_module

        listener = _bind_loopback_listener(socket.AF_INET, "127.0.0.1")
        try:
            port = listener.getsockname()[1]
            other_pid = os.getpid() + 1
            with pytest.raises(SessionError, match="is owned by pid"):
                session_module._windows_verify_pid_owns_listening_socket(
                    other_pid, "127.0.0.1", port
                )
        finally:
            listener.close()

    def test_v6_listener_ownership_attributed_to_self(self):
        from speech_aware_evidence_acquisition.core import session as session_module

        listener = _bind_loopback_listener(socket.AF_INET6, "::1")
        try:
            port = listener.getsockname()[1]
            session_module._windows_verify_pid_owns_listening_socket(os.getpid(), "::1", port)
        finally:
            listener.close()

    def test_v6_listener_refuses_a_different_pid(self):
        from speech_aware_evidence_acquisition.core import session as session_module

        listener = _bind_loopback_listener(socket.AF_INET6, "::1")
        try:
            port = listener.getsockname()[1]
            other_pid = os.getpid() + 1
            with pytest.raises(SessionError, match="is owned by pid"):
                session_module._windows_verify_pid_owns_listening_socket(other_pid, "::1", port)
        finally:
            listener.close()

    def test_family_keying_v4_listener_does_not_satisfy_a_v6_claim(self):
        """T5 fix-3 regression guard, in-process: only an IPv4 socket is
        bound; a claim of the SAME port number under ``::1`` must be
        refused as 'no LISTEN socket found', never satisfied by matching
        the v4 entry on port number alone -- the exact bug T5 fix-3 closed.
        (If the lookup ever regressed to a port-only key, this would
        instead SUCCEED, since the v4 entry happens to also be owned by
        ``os.getpid()``.)"""

        from speech_aware_evidence_acquisition.core import session as session_module

        listener = _bind_loopback_listener(socket.AF_INET, "127.0.0.1")
        try:
            port = listener.getsockname()[1]
            with pytest.raises(SessionError, match="no LISTEN socket found"):
                session_module._windows_verify_pid_owns_listening_socket(os.getpid(), "::1", port)
        finally:
            listener.close()

    def test_family_keying_v6_listener_does_not_satisfy_a_v4_claim(self):
        """Symmetric case: only an IPv6 socket is bound; a claim of the
        SAME port number under ``127.0.0.1`` must be refused the same
        way."""

        from speech_aware_evidence_acquisition.core import session as session_module

        listener = _bind_loopback_listener(socket.AF_INET6, "::1")
        try:
            port = listener.getsockname()[1]
            with pytest.raises(SessionError, match="no LISTEN socket found"):
                session_module._windows_verify_pid_owns_listening_socket(
                    os.getpid(), "127.0.0.1", port
                )
        finally:
            listener.close()


# ---------------------------------------------------------------------------
# IMPORTANT fix-2: the process dying MID-RUN must be caught on the NEXT
# send, not only at construction.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.name == "nt", reason=_COPIED_BINARY_LISTENER_SKIP_REASON)
def test_transport_send_refuses_after_process_dies_mid_run(tmp_path):
    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    process = _spawn_listening_process(binary, 18191)
    try:
        session = _matching_session(runtime_receipt, host="127.0.0.1", port=18191, pid=process.pid)
        transport = LlamaServerTransport(
            "http://127.0.0.1:18191",
            tmp_path,
            session,
            runtime_receipt,
            runtime_root,
            post=lambda u, b: _canned_response(),
        )
        media = tmp_path / "media" / "5000001.mp3"
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(b"fake-mp3-bytes")
        payload = {
            "request_id": "req-1",
            "carrier_lock_key": "earnings22-original",
            "sample_id": "5000001",
            "speech_ref": "earnings22-original/5000001",
            "media_relpath": "media/5000001.mp3",
            "audio_seconds": 10.0,
            "sample_rate_hz": 16000,
            "task_instruction": "Transcribe the speech verbatim.",
            "history": [],
            "decoding_params": {"temperature": 0, "seed": 20260803},
        }
        raw = transport(json.dumps(payload).encode())
        assert json.loads(raw)["text"] == "hello world"

        process.terminate()
        process.wait(timeout=5)
        with pytest.raises(SessionError, match="not a live process"):
            transport(json.dumps(payload).encode())
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


# ---------------------------------------------------------------------------
# attach_session -- probes 3, 4 (declared-value / dead-pid; refused before
# the process-identity check is reached, so the placeholder runtime_root is
# fine).
# ---------------------------------------------------------------------------


def test_attach_refuses_missing_receipt_file(tmp_path):
    with pytest.raises(SessionError, match="cannot read"):
        attach_session(tmp_path / "does-not-exist.json", runtime_receipt={}, runtime_root=tmp_path)


def test_attach_refuses_binary_hash_mismatch(tmp_path):
    """Probe 3 via attach."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, binary_sha256="0" * 64, pid=os.getpid())
    receipt_path = tmp_path / "session.json"
    write_session_receipt(receipt_path, session)
    with pytest.raises(SessionError, match="binary identity"):
        attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=tmp_path)


def test_attach_refuses_dead_pid(tmp_path):
    """Probe 4: attach to a dead PID -> refused."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    session = _matching_session(runtime_receipt, pid=proc.pid)
    receipt_path = tmp_path / "session.json"
    write_session_receipt(receipt_path, session)
    with pytest.raises(SessionError, match="not a live process"):
        attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=tmp_path)


@pytest.mark.skipif(os.name == "nt", reason=_COPIED_BINARY_LISTENER_SKIP_REASON)
def test_attach_succeeds_for_a_live_matching_session(tmp_path):
    """Fixed per reviewer feedback: the ORIGINAL version of this test used
    ``pid=os.getpid()`` (the test's own interpreter), which is exactly why
    the CRITICAL gap (attach_session trusting declared values + bare
    liveness) went uncaught. attach_session now ALSO requires the pid to be
    ACTUALLY RUNNING the pinned binary image AND to genuinely own the
    listening socket on the claimed port (T5 fix-2) -- proven here with a
    REAL spawned process running a genuine copy of that exact binary file,
    really bound to the claimed port."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    process = _spawn_listening_process(binary, 18192)
    try:
        session = _matching_session(runtime_receipt, host="127.0.0.1", port=18192, pid=process.pid)
        receipt_path = tmp_path / "session.json"
        write_session_receipt(receipt_path, session)
        attached = attach_session(
            receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root
        )
        assert attached == session
    finally:
        _terminate(process)


# ---------------------------------------------------------------------------
# IMPORTANT fix-3: FrozenCoreAdapter's complementary session-liveness check.
# ---------------------------------------------------------------------------


class _RecordingSessionTransport:
    """Duck-typed stand-in exposing assert_session_alive(), the SAME
    protocol LlamaServerTransport exposes -- proves FrozenCoreAdapter really
    calls it (construction + before every request) and never invokes the
    underlying transport when it raises, without needing a real llama-server
    or even a real subprocess."""

    def __init__(self) -> None:
        self.session_checks = 0
        self.calls = 0
        self.should_fail = False

    def assert_session_alive(self) -> None:
        self.session_checks += 1
        if self.should_fail:
            raise SessionError("forced session failure for the test")

    def __call__(self, request_bytes: bytes) -> bytes:
        self.calls += 1
        return _canned_response_as_core_response()


def _canned_response_as_core_response() -> bytes:
    return json.dumps(
        {"text": "hello world", "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
    ).encode()


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def _adapter_world(tmp_path):
    media = tmp_path / "media" / "5000001.mp3"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-mp3-bytes")
    binding = PayloadBindingContext(
        carrier_lock_key="earnings22-original",
        allowed_sample_ids=frozenset({"5000001"}),
        sample_facts={"5000001": (100.0, 16000)},
        data_root=tmp_path,
        carrier_root=tmp_path,
    )
    plan = ExecutionPlan(
        run_id="SAEA-E-000-session-adapter",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings22-original",
        split_role="dev",
        split_identity_hash="a" * 64,
        planned_model_calls=5,
        planned_gpu_hours=0.5,
        planned_speech_audio_seconds=500,
        protocol_hash="b" * 64,
        attempt_id="attempt-session-check",
    )
    payload = {
        "request_id": "req-1",
        "carrier_lock_key": "earnings22-original",
        "sample_id": "5000001",
        "speech_ref": "earnings22-original/5000001",
        "media_relpath": "media/5000001.mp3",
        "audio_seconds": 100.0,
        "sample_rate_hz": 16000,
        "task_instruction": "Transcribe.",
        "history": [],
        "decoding_params": {"temperature": 0, "seed": 20260803},
    }
    return binding, plan, payload


def test_adapter_checks_transport_session_at_construction(tmp_path):
    binding, plan, _payload = _adapter_world(tmp_path)
    transport = _RecordingSessionTransport()
    FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=transport,
        sink=TraceSink(tmp_path / "run", plan.run_id), binding=binding,
    )
    assert transport.session_checks == 1


def test_adapter_rechecks_transport_session_before_every_request(tmp_path):
    binding, plan, payload = _adapter_world(tmp_path)
    transport = _RecordingSessionTransport()
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=transport,
        sink=TraceSink(tmp_path / "run", plan.run_id), binding=binding,
    )
    assert transport.session_checks == 1
    adapter.request(payload)
    assert transport.session_checks == 2
    assert transport.calls == 1


def test_adapter_never_sends_when_the_session_check_fails(tmp_path):
    """A failing session check must refuse the request WITHOUT ever reaching
    the underlying transport -- no partial or leaked send."""

    binding, plan, payload = _adapter_world(tmp_path)
    transport = _RecordingSessionTransport()
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=transport,
        sink=TraceSink(tmp_path / "run", plan.run_id), binding=binding,
    )
    transport.should_fail = True
    with pytest.raises(SessionError, match="forced session failure"):
        adapter.request(payload)
    assert transport.calls == 0


def test_adapter_with_a_bare_callable_transport_is_unaffected(tmp_path):
    """A transport with no assert_session_alive() attribute at all (every
    fake/bare-callable transport used elsewhere in this repo's own tests)
    must behave EXACTLY as before T5 -- the duck-typed check is strictly
    additive, never mandatory for a transport that never claimed to have
    one."""

    binding, plan, payload = _adapter_world(tmp_path)

    def bare_transport(request_bytes: bytes) -> bytes:
        return _canned_response_as_core_response()

    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=bare_transport,
        sink=TraceSink(tmp_path / "run", plan.run_id), binding=binding,
    )
    response = adapter.request(payload)
    assert response.text == "hello world"


# ---------------------------------------------------------------------------
# Readiness wait (2026-08-08 fix): llama-server binds its port during model
# load and answers 503 until ready; the first REAL smoke aborted on exactly
# that. start_session must not hand out a receipt for a server that cannot
# answer yet.
# ---------------------------------------------------------------------------


class TestWaitUntilReady:
    def _url(self):
        return "http://127.0.0.1:18099/health"

    def test_returns_once_health_reports_200(self):
        from speech_aware_evidence_acquisition.core.session.lifecycle import _wait_until_ready

        statuses = iter([503, 503, 200])
        seen = []

        def fake_get(url, timeout):
            seen.append(url)
            return next(statuses)

        _wait_until_ready(
            self._url(),
            is_process_alive=lambda: True,
            http_get_status=fake_get,
            timeout_seconds=10.0,
            poll_interval_seconds=0.0,
        )
        assert seen == [self._url()] * 3

    def test_connection_errors_count_as_not_ready_then_recover(self):
        from speech_aware_evidence_acquisition.core.session.lifecycle import _wait_until_ready

        phases = iter(["refuse", "ok"])

        def fake_get(url, timeout):
            if next(phases) == "refuse":
                raise OSError("connection refused")
            return 200

        _wait_until_ready(
            self._url(),
            is_process_alive=lambda: True,
            http_get_status=fake_get,
            timeout_seconds=10.0,
            poll_interval_seconds=0.0,
        )

    def test_process_death_during_load_fails_closed(self):
        from speech_aware_evidence_acquisition.core.session.lifecycle import _wait_until_ready

        with pytest.raises(SessionError, match="exited"):
            _wait_until_ready(
                self._url(),
                is_process_alive=lambda: False,
                http_get_status=lambda url, timeout: 503,
                timeout_seconds=10.0,
                poll_interval_seconds=0.0,
            )

    def test_ready_timeout_fails_closed(self):
        from speech_aware_evidence_acquisition.core.session.lifecycle import _wait_until_ready

        with pytest.raises(SessionError, match="not ready"):
            _wait_until_ready(
                self._url(),
                is_process_alive=lambda: True,
                http_get_status=lambda url, timeout: 503,
                timeout_seconds=0.05,
                poll_interval_seconds=0.0,
            )


# ---------------------------------------------------------------------------
# Task 1 (2026-08-09 finding): llama-server's own stdout/stderr was captured
# for the startup window only (``_capture_startup_stdout``), then the reader
# thread that must keep draining it (so the pipe never fills and blocks the
# server) simply discarded every later chunk -- hours of server output were
# unrecoverable after exactly the kind of mid-run stall that killed two
# arms. These probes exercise the persistence seam in isolation (no real
# subprocess, OS-independent): every chunk the reader thread ever reads must
# reach ``on_chunk``, in order, and a raising/broken ``on_chunk`` must never
# stop the drain or the startup-window capture it does not otherwise affect.
# ---------------------------------------------------------------------------


class _FakeStdout:
    """A minimal stand-in for ``Popen.stdout``: ``.read1(n)`` (the call
    ``_capture_startup_stdout`` actually makes -- plain ``.read(n)`` on a
    real BufferedReader blocks accumulating bytes until EOF, a 2026-08-09
    finding this fake deliberately does NOT reproduce) hands out the given
    chunks in order, then empty bytes forever (real-pipe EOF shape)."""

    def __init__(self, chunks) -> None:
        self._chunks = list(chunks)

    def read1(self, _n: int) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class _FakeProcess:
    def __init__(self, chunks) -> None:
        self.stdout = _FakeStdout(chunks)


class TestCaptureStartupStdoutOnChunk:
    def test_every_chunk_reaches_on_chunk_in_order(self):
        from speech_aware_evidence_acquisition.core.session.lifecycle import (
            _capture_startup_stdout,
        )

        process = _FakeProcess([b"a", b"b", b"c"])
        seen: list[bytes] = []
        result = _capture_startup_stdout(
            process, max_bytes=65536, timeout_seconds=2.0, on_chunk=seen.append
        )
        assert result == b"abc"
        assert seen == [b"a", b"b", b"c"]

    def test_a_raising_on_chunk_never_breaks_collection(self):
        from speech_aware_evidence_acquisition.core.session.lifecycle import (
            _capture_startup_stdout,
        )

        process = _FakeProcess([b"a", b"b"])

        def boom(_chunk: bytes) -> None:
            raise RuntimeError("broken log writer")

        result = _capture_startup_stdout(
            process, max_bytes=65536, timeout_seconds=2.0, on_chunk=boom
        )
        assert result == b"ab"

    def test_on_chunk_is_optional(self):
        from speech_aware_evidence_acquisition.core.session.lifecycle import (
            _capture_startup_stdout,
        )

        process = _FakeProcess([b"x"])
        result = _capture_startup_stdout(process, max_bytes=65536, timeout_seconds=2.0)
        assert result == b"x"


class TestServerLogWriter:
    def test_persists_every_write_immediately_flushed(self, tmp_path):
        from speech_aware_evidence_acquisition.core.session.lifecycle import _ServerLogWriter

        path = tmp_path / "logs" / "server.log"
        writer = _ServerLogWriter(path)
        writer.write(b"line one\n")
        # unbuffered: visible on disk with no explicit flush/close needed --
        # the whole point is reading it while the server is still wedged.
        assert path.read_bytes() == b"line one\n"
        writer.write(b"line two\n")
        assert path.read_bytes() == b"line one\nline two\n"

    def test_none_path_is_a_silent_no_op(self):
        from speech_aware_evidence_acquisition.core.session.lifecycle import _ServerLogWriter

        writer = _ServerLogWriter(None)
        writer.write(b"never written anywhere")  # must not raise

    def test_unwritable_path_disables_writes_without_raising(self, tmp_path):
        """The log file cannot even be opened (its parent is a plain FILE, not
        a directory -- mkdir/open both refuse); the drain this writer feeds
        must never block or raise on that account (module docstring)."""

        from speech_aware_evidence_acquisition.core.session.lifecycle import _ServerLogWriter

        blocked = tmp_path / "blocked"
        blocked.write_text("not a directory", encoding="utf-8")
        writer = _ServerLogWriter(blocked / "server.log")
        writer.write(b"first\n")
        writer.write(b"second\n")  # repeated calls after the first failure are also safe


# ---------------------------------------------------------------------------
# start_session -- real spawn, POSIX-only, FAKE binary (never llama-server).
# start_session itself is unchanged by this fix (it directly hash-verifies
# then immediately Popen()s the exact same path -- no separate PID-identity
# gap to close there the way attach_session/LlamaServerTransport had), so
# these probes are unchanged. (2026-08-08: the spawn probe now injects an
# always-ready prober -- the FAKE binary serves no HTTP, and the readiness
# wait is exercised by TestWaitUntilReady above.)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.name == "nt", reason="POSIX shell-script fake executable required for a real spawn"
)
class TestStartSessionSpawn:
    def test_spawn_refuses_outside_wsl_before_any_process_or_asset_access(
        self, tmp_path, monkeypatch
    ):
        popen_called = False

        def refuse_non_wsl():
            raise ExecutionScopeError("formal execution requires WSL2")

        def forbidden_popen(*args, **kwargs):
            nonlocal popen_called
            popen_called = True
            raise AssertionError("popen must not run outside WSL2")

        monkeypatch.setattr(
            session_lifecycle,
            "assert_wsl_execution_environment",
            refuse_non_wsl,
        )
        with pytest.raises(ExecutionScopeError, match="WSL2"):
            start_session(
                runtime_root=tmp_path / "missing-runtime",
                data_root=tmp_path / "missing-data",
                runtime_receipt={},
                host="127.0.0.1",
                port=18080,
                session_id="must-not-start",
                popen=forbidden_popen,
            )
        assert popen_called is False

    def _fake_binary_world(self, tmp_path, *, sleep_seconds=5):
        runtime_root = tmp_path / "runtime"
        data_root = tmp_path / "data"
        binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.parent.mkdir(parents=True)
        binary.write_text(
            "#!/bin/sh\n"
            "echo 'server listening on 127.0.0.1'\n"
            f"sleep {sleep_seconds}\n",
            encoding="utf-8",
        )
        binary.chmod(0o755)
        binary_bytes = binary.read_bytes()

        model_dir = data_root / "models" / "qwen3-omni-30b-a3b-instruct-gguf"
        model_dir.mkdir(parents=True)
        main_relpath = "models/qwen3-omni-30b-a3b-instruct-gguf/model.gguf"
        mmproj_relpath = "models/qwen3-omni-30b-a3b-instruct-gguf/mmproj.gguf"
        (data_root / main_relpath).write_bytes(b"fake-main-gguf")
        (data_root / mmproj_relpath).write_bytes(b"fake-mmproj-gguf")

        runtime_receipt = {
            "llama_cpp": {
                "binary_path": "llama.cpp/build/bin/llama-server",
                "binary_sha256": _sha(binary_bytes),
            },
            "gguf_files": [
                {"path": main_relpath, "sha256": _sha(b"fake-main-gguf")},
                {"path": mmproj_relpath, "sha256": _sha(b"fake-mmproj-gguf")},
            ],
        }
        return runtime_root, data_root, runtime_receipt

    @pytest.mark.requires_wsl2_execution_authority
    def test_spawn_writes_a_session_receipt_bound_to_the_real_process(self, tmp_path):
        """Probe 7 (spawn half): a legitimate spawn of the FAKE pinned binary
        produces a SessionReceipt with a REAL pid/argv/binary hash/port/model
        paths, and the process is genuinely alive at that pid; the receipt is
        written to disk and re-reads identically."""

        runtime_root, data_root, runtime_receipt = self._fake_binary_world(tmp_path)
        receipt_path = tmp_path / "runs" / "session.json"
        receipt = start_session(
            runtime_root=runtime_root,
            data_root=data_root,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=18080,
            session_id="spawn-test-1",
            receipt_path=receipt_path,
            startup_timeout_seconds=2.0,
            http_get_status=lambda url, timeout: 200,
        )
        try:
            assert receipt.pid > 0
            assert receipt.host == "127.0.0.1"
            assert receipt.port == 18080
            assert receipt.binary_sha256 == runtime_receipt["llama_cpp"]["binary_sha256"]
            assert {f.path for f in receipt.model_files} == {
                e["path"] for e in runtime_receipt["gguf_files"]
            }
            assert "--host" in receipt.argv
            assert "127.0.0.1" in receipt.argv
            assert receipt_path.is_file()
            assert read_session_receipt(receipt_path) == receipt
            # no server_log_path was requested -- must default to None, not
            # a fabricated path (Task 1, 2026-08-09).
            assert receipt.server_log_path is None
            os.kill(receipt.pid, 0)  # the real subprocess is alive right now
        finally:
            try:
                os.kill(receipt.pid, 15)
            except OSError:
                pass
            try:
                os.waitpid(receipt.pid, 0)
            except OSError:
                pass

    @pytest.mark.requires_wsl2_execution_authority
    def test_spawn_passes_extra_env_to_the_server_process(self, tmp_path):
        """server_env (W3, 2026-08-11): a model-fragment environment variable
        (e.g. GGML_CUDA_DISABLE_GRAPHS) must reach the spawned server's
        environment — the fake binary writes the variable to a marker file."""

        runtime_root, data_root, runtime_receipt = self._fake_binary_world(tmp_path)
        marker = tmp_path / "env-marker.txt"
        binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.write_text(
            "#!/bin/sh\n"
            f"echo \"$SAEA_TEST_SERVER_ENV\" > {marker}\n"
            "echo 'server listening on 127.0.0.1'\n"
            "sleep 5\n",
            encoding="utf-8",
        )
        binary.chmod(0o755)
        runtime_receipt["llama_cpp"]["binary_sha256"] = _sha(binary.read_bytes())
        receipt = start_session(
            runtime_root=runtime_root,
            data_root=data_root,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=18084,
            session_id="spawn-env-test",
            extra_env={"SAEA_TEST_SERVER_ENV": "graphs-off"},
            startup_timeout_seconds=2.0,
            http_get_status=lambda url, timeout: 200,
        )
        try:
            assert marker.read_text(encoding="utf-8").strip() == "graphs-off"
        finally:
            try:
                os.kill(receipt.pid, 15)
                os.waitpid(receipt.pid, 0)
            except OSError:
                pass

    @pytest.mark.requires_wsl2_execution_authority
    def test_spawn_refuses_non_string_extra_env(self, tmp_path):
        """extra_env is str->str, fail-closed — an int value (a config typo)
        is refused before any process is spawned."""

        runtime_root, data_root, runtime_receipt = self._fake_binary_world(tmp_path)
        with pytest.raises(SessionError, match="extra_env"):
            start_session(
                runtime_root=runtime_root,
                data_root=data_root,
                runtime_receipt=runtime_receipt,
                host="127.0.0.1",
                port=18085,
                session_id="spawn-env-bad",
                extra_env={"GGML_CUDA_DISABLE_GRAPHS": 1},  # type: ignore[dict-item]
                startup_timeout_seconds=2.0,
                http_get_status=lambda url, timeout: 200,
            )

    @pytest.mark.requires_wsl2_execution_authority
    def test_spawn_of_a_binary_whose_hash_does_not_match_pinned_is_refused(self, tmp_path):
        """Probe 5: the binary on disk was swapped after the receipt captured
        a hash for the ORIGINAL bytes -- spawn must refuse, not execute it."""

        runtime_root, data_root, runtime_receipt = self._fake_binary_world(tmp_path)
        binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.write_text("#!/bin/sh\necho tampered\n", encoding="utf-8")
        binary.chmod(0o755)
        with pytest.raises(SessionError, match="hash"):
            start_session(
                runtime_root=runtime_root,
                data_root=data_root,
                runtime_receipt=runtime_receipt,
                host="127.0.0.1",
                port=18081,
                session_id="spawn-test-2",
            )

    @pytest.mark.requires_wsl2_execution_authority
    def test_start_session_refuses_non_loopback_host(self, tmp_path):
        """Probe 1 (spawn half): refused before any process is spawned."""

        runtime_root, data_root, runtime_receipt = self._fake_binary_world(tmp_path)
        with pytest.raises(SessionError, match="loopback"):
            start_session(
                runtime_root=runtime_root,
                data_root=data_root,
                runtime_receipt=runtime_receipt,
                host="10.0.0.5",
                port=18082,
                session_id="spawn-test-3",
            )

    @pytest.mark.requires_wsl2_execution_authority
    def test_spawn_persists_combined_stdout_after_the_startup_window(self, tmp_path):
        """Task 1 (2026-08-09): the startup-window bytes AND everything the
        server prints afterward (module docstring: the thread that must keep
        draining the pipe so it never blocks the server) now both land, in
        order, flushed as written, in ``server_log_path`` -- not merely the
        startup window, and not merely thrown away once that window closes."""

        runtime_root, data_root, runtime_receipt = self._fake_binary_world(tmp_path)
        binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.write_text(
            "#!/bin/sh\n"
            "echo 'server listening on 127.0.0.1'\n"
            "sleep 0.2\n"
            "echo 'post-startup diagnostic line'\n"
            "sleep 5\n",
            encoding="utf-8",
        )
        binary.chmod(0o755)
        runtime_receipt["llama_cpp"]["binary_sha256"] = _sha(binary.read_bytes())
        receipt_path = tmp_path / "runs" / "session.json"
        log_path = tmp_path / "runs" / "server.log"
        receipt = start_session(
            runtime_root=runtime_root,
            data_root=data_root,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=18083,
            session_id="spawn-test-log",
            receipt_path=receipt_path,
            server_log_path=log_path,
            # A tiny startup window that closes BEFORE the post-startup line
            # is printed -- proving that line reaches the file only via the
            # continued drain, not the startup-capture window itself.
            startup_timeout_seconds=0.05,
            http_get_status=lambda url, timeout: 200,
        )
        try:
            assert receipt.server_log_path == str(log_path)
            deadline = time.monotonic() + 5.0
            content = b""
            while time.monotonic() < deadline:
                if log_path.is_file():
                    content = log_path.read_bytes()
                    if b"post-startup diagnostic line" in content:
                        break
                time.sleep(0.05)
            assert b"server listening on 127.0.0.1" in content
            assert b"post-startup diagnostic line" in content
            assert content.index(b"server listening") < content.index(b"post-startup")
        finally:
            try:
                os.kill(receipt.pid, 15)
            except OSError:
                pass
            try:
                os.waitpid(receipt.pid, 0)
            except OSError:
                pass

    @pytest.mark.requires_wsl2_execution_authority
    def test_spawn_survives_an_unwritable_server_log_path(self, tmp_path):
        """The log path cannot be opened at all (its parent is a plain FILE);
        the spawn must still succeed and the server must still become ready
        -- losing the log is acceptable, stalling the experiment is not."""

        runtime_root, data_root, runtime_receipt = self._fake_binary_world(tmp_path)
        blocked = tmp_path / "blocked-parent"
        blocked.write_text("not a directory", encoding="utf-8")
        unwritable_log = blocked / "server.log"
        receipt_path = tmp_path / "runs" / "session.json"
        receipt = start_session(
            runtime_root=runtime_root,
            data_root=data_root,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=18084,
            session_id="spawn-test-badlog",
            receipt_path=receipt_path,
            server_log_path=unwritable_log,
            startup_timeout_seconds=0.5,
            http_get_status=lambda url, timeout: 200,
        )
        try:
            # the declared path is still recorded even though nothing could
            # ever be written there -- an operator checking it sees an
            # honest absence, not a fabricated location.
            assert receipt.server_log_path == str(unwritable_log)
            assert not unwritable_log.exists()
            os.kill(receipt.pid, 0)  # the spawn itself was never blocked
        finally:
            try:
                os.kill(receipt.pid, 15)
            except OSError:
                pass
            try:
                os.waitpid(receipt.pid, 0)
            except OSError:
                pass
