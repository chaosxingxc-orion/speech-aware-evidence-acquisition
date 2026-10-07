"""Unit tests for ``core.session.serving`` -- the always-on serving session
(E7, owner rule 2026-09-07).

Nothing here starts a server, touches a GPU, or reaches the network: the
session document, the identity predicate, the profile resolver and the
monitor summary are all pure functions over files this module writes into
``tmp_path``. The one place a real llama-server would appear
(``build_server_command``) is exercised against a fake binary and a fake
runtime receipt, exactly as ``tests/unit/test_session.py`` already does.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import ConfigError, read_fragment
from speech_aware_evidence_acquisition.core.session import (
    PROCESS_STATE_DEFUNCT,
    PROCESS_STATE_GONE,
    PROCESS_STATE_RUNNING,
    SESSION_RECEIPT_SCHEMA,
    STUDY_SLUG,
    ModelFileRef,
    SessionError,
    SessionReceipt,
    _defunct_wait_status,
    _pid_alive,
    _pid_is_defunct,
    _process_image_path,
    build_server_command,
    describe_wait_status,
    process_state,
    reap_child,
    stop_session,
)
from speech_aware_evidence_acquisition.core.session.serving import (
    MONITOR_JSONL_NAME,
    NO_RESIDENT_SESSION_EXIT,
    SESSION_DOCUMENT_NAME,
    SESSION_STOP_NAME,
    SERVING_SESSION_SCHEMA,
    ServingIdentityMismatch,
    ServingSessionError,
    _hold_session_open,
    _resident_refusal,
    assert_identity_matches,
    build_parser,
    build_session_document,
    find_resident_session,
    identity_mismatches,
    merge_server_args,
    observe_session_process,
    props_identity,
    read_gpu_occupancy,
    read_host_memory,
    resolve_serving_profile,
    serving_identity,
    serving_session_dir,
    write_json_document,
    _read_explicit_stop_document,
    _session_stop_lock,
    _write_stop_document,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_receipt_sha256(document: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _runtime_world(tmp_path: Path):
    """A fake runtime root + data root + runtime receipt, mirroring
    ``tests/unit/test_session.py::_runtime_world``: fake bytes, no real
    binary, no real model."""

    runtime_root = tmp_path / "runtime"
    data_root = tmp_path / "data"
    binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
    binary.parent.mkdir(parents=True)
    binary_bytes = b"fake-llama-server"
    binary.write_bytes(binary_bytes)

    model_dir = data_root / "models" / "q4km"
    model_dir.mkdir(parents=True)
    main_relpath = "models/q4km/model.gguf"
    mmproj_relpath = "models/q4km/mmproj.gguf"
    (data_root / main_relpath).write_bytes(b"fake-main-gguf")
    (data_root / mmproj_relpath).write_bytes(b"fake-mmproj-gguf")

    runtime_receipt = {
        "schema": "saea-runtime-receipt-v2",
        "study": "speech-aware-evidence-acquisition",
        "model_lock_key": "fake-lock",
        "llama_cpp": {
            "build_commit": "a" * 40,
            "binary_path": "llama.cpp/build/bin/llama-server",
            "binary_sha256": _sha(binary_bytes),
        },
        "gguf_files": [
            {"path": main_relpath, "sha256": _sha(b"fake-main-gguf")},
            {"path": mmproj_relpath, "sha256": _sha(b"fake-mmproj-gguf")},
        ],
    }
    return runtime_root, data_root, runtime_receipt


def _write_model_fragment(repo_root: Path, name: str, document: dict) -> Path:
    path = repo_root / "configs" / "model" / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return path


def _fragment_document(runtime_receipt_relpath: str = "receipts/runtime-fake.json") -> dict:
    return {
        "model_lock_key": "fake-lock",
        "transport": "llama-server",
        "base_url": "http://127.0.0.1:8080",
        "runtime_receipt": runtime_receipt_relpath,
        "server_args": ["-c", "16384", "-np", "2", "-fa", "on", "-ngl", "999"],
        "serving_geometry": {"slots": 2, "slot_tokens": 8192, "max_tokens": 256},
        "server_env": {"GGML_CUDA_DISABLE_GRAPHS": "1"},
    }


def _identity(**overrides) -> dict:
    base = serving_identity(
        model_fragment="frag",
        model_fragment_sha256="f" * 64,
        runtime_receipt_relpath="receipts/runtime-fake.json",
        runtime_receipt_sha256="r" * 64,
        binary_path="llama.cpp/build/bin/llama-server",
        binary_sha256="b" * 64,
        model_files=[{"path": "models/q4km/model.gguf", "sha256": "m" * 64}],
        session_role="legacy",
        model_root="/home/chao",
        server_argv=[
            "/home/chao/llama.cpp/build/bin/llama-server",
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
            "-m",
            "/home/chao/models/q4km/model.gguf",
            "-c",
            "16384",
            "-np",
            "2",
        ],
        server_env={"GGML_CUDA_DISABLE_GRAPHS": "1"},
        host="127.0.0.1",
        port=8080,
        props={
            "total_slots": 2,
            "default_generation_settings": {"n_ctx": 8192},
            "model_path": "/home/chao/models/q4km/model.gguf",
            "build_info": "version: 1 (04ccc72a)",
        },
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# merge_server_args moved here; it must still behave exactly as before.
# ---------------------------------------------------------------------------


def test_merge_server_args_overrides_only_np_and_c():
    merged = merge_server_args(
        ["-c", "1024", "-np", "1", "-ngl", "999", "-fa", "on"], slots=8, context_tokens=40960
    )
    assert merged == ["-c", "40960", "-np", "8", "-ngl", "999", "-fa", "on"]


def test_merge_server_args_appends_missing_flags_and_refuses_a_dangling_one():
    assert merge_server_args(["-ngl", "999"], slots=2, context_tokens=4096) == [
        "-ngl",
        "999",
        "-np",
        "2",
        "-c",
        "4096",
    ]
    with pytest.raises(ServingSessionError, match="declares -np with no value"):
        merge_server_args(["-np"], slots=2, context_tokens=4096)


def test_the_flight_runtime_still_exports_merge_server_args_with_its_own_error_type():
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        FlightRuntimeError,
        merge_server_args as flight_merge,
    )

    assert flight_merge(["-ngl", "999"], slots=1, context_tokens=512) == [
        "-ngl",
        "999",
        "-np",
        "1",
        "-c",
        "512",
    ]
    with pytest.raises(FlightRuntimeError):
        flight_merge("-np 2", slots=1, context_tokens=512)


# ---------------------------------------------------------------------------
# build_server_command: ONE argument builder.
# ---------------------------------------------------------------------------


def test_build_server_command_is_the_argv_start_session_would_spawn(tmp_path):
    runtime_root, data_root, runtime_receipt = _runtime_world(tmp_path)
    command = build_server_command(
        runtime_root=runtime_root,
        data_root=data_root,
        runtime_receipt=runtime_receipt,
        host="127.0.0.1",
        port=8080,
        extra_argv=("-c", "16384", "-np", "2"),
    )
    assert command.argv[0] == str(runtime_root / "llama.cpp" / "build" / "bin" / "llama-server")
    assert command.argv[1:5] == ("--host", "127.0.0.1", "--port", "8080")
    assert "--mmproj" in command.argv
    assert command.argv[-4:] == ("-c", "16384", "-np", "2")
    assert command.binary_path == "llama.cpp/build/bin/llama-server"
    assert command.binary_sha256 == runtime_receipt["llama_cpp"]["binary_sha256"]
    assert len(command.model_files) == 2


def test_build_server_command_refuses_a_swapped_binary(tmp_path):
    runtime_root, data_root, runtime_receipt = _runtime_world(tmp_path)
    (runtime_root / "llama.cpp" / "build" / "bin" / "llama-server").write_bytes(b"other")
    with pytest.raises(SessionError, match="spawn refused"):
        build_server_command(
            runtime_root=runtime_root,
            data_root=data_root,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=8080,
        )


def test_build_server_command_drops_the_mmproj_for_an_inference_role(tmp_path):
    runtime_root, data_root, runtime_receipt = _runtime_world(tmp_path)
    command = build_server_command(
        runtime_root=runtime_root,
        data_root=data_root,
        runtime_receipt=runtime_receipt,
        host="127.0.0.1",
        port=8080,
        role="inference",
    )
    assert "--no-mmproj" in command.argv
    assert "--mmproj" not in command.argv
    assert [entry.path for entry in command.model_files] == ["models/q4km/model.gguf"]


# ---------------------------------------------------------------------------
# Session directory + discovery.
# ---------------------------------------------------------------------------


def test_serving_session_dir_refuses_an_id_that_is_not_one_path_segment(tmp_path):
    assert serving_session_dir(tmp_path, "s1") == tmp_path / "serving" / "s1"
    for bad in ("", "  ", "a/b", "..", "a\\b"):
        with pytest.raises(ServingSessionError):
            serving_session_dir(tmp_path, bad)


def _write_session(data_root: Path, session_id: str, *, stopped: bool = False) -> Path:
    session_dir = serving_session_dir(data_root, session_id)
    write_json_document(
        session_dir / SESSION_DOCUMENT_NAME,
        build_session_document(
            session_id=session_id,
            identity=_identity(),
            pid=4242,
            started_at="2026-09-07T00:00:00+00:00",
            serving_geometry={"slots": 2, "slot_tokens": 8192, "max_tokens": 256},
            props={"total_slots": 2, "default_generation_settings": {"n_ctx": 8192}},
            session_receipt_path=str(session_dir / "session-receipt.json"),
            server_log_path=str(session_dir / "server.log"),
            monitor_path=str(session_dir / MONITOR_JSONL_NAME),
        ),
    )
    if stopped:
        write_json_document(session_dir / SESSION_STOP_NAME, {"stopped": True})
    return session_dir


def test_find_resident_session_returns_none_without_a_serving_root(tmp_path):
    assert find_resident_session(tmp_path) is None


def test_find_resident_session_skips_a_stopped_session(tmp_path):
    _write_session(tmp_path, "stopped-one", stopped=True)
    assert find_resident_session(tmp_path) is None


def test_find_resident_session_returns_the_live_one(tmp_path):
    _write_session(tmp_path, "stopped-one", stopped=True)
    session_dir = _write_session(tmp_path, "live-one")
    found = find_resident_session(tmp_path)
    assert found is not None
    assert found[0] == session_dir
    assert found[1]["session_id"] == "live-one"
    assert found[1]["schema"] == SERVING_SESSION_SCHEMA


def test_find_resident_session_refuses_two_live_sessions(tmp_path):
    _write_session(tmp_path, "one")
    _write_session(tmp_path, "two")
    with pytest.raises(ServingSessionError, match="2 serving sessions"):
        find_resident_session(tmp_path)


# ---------------------------------------------------------------------------
# The reuse predicate.
# ---------------------------------------------------------------------------


def test_identical_identities_have_no_mismatches():
    assert identity_mismatches(_identity(), _identity()) == []


def test_a_differing_context_size_is_named_by_its_flag():
    required = _identity()
    session = _identity()
    argv = list(session["server_argv"])
    argv[argv.index("-c") + 1] = "40960"
    session["server_argv"] = argv
    session["props_identity"] = props_identity(
        {"total_slots": 2, "default_generation_settings": {"n_ctx": 20480}}
    )

    mismatches = identity_mismatches(session, required)
    fields = [entry["field"] for entry in mismatches]
    assert "server_argv[-c]" in fields
    assert "props_identity.slot_n_ctx" in fields
    entry = next(item for item in mismatches if item["field"] == "server_argv[-c]")
    assert entry["session"] == ["40960"]
    assert entry["required"] == ["16384"]


def test_a_differing_model_file_and_env_are_named(tmp_path):
    session = _identity(
        model_files=[{"path": "models/q4km/model.gguf", "sha256": "z" * 64}],
        server_env={"GGML_CUDA_DISABLE_GRAPHS": "0"},
    )
    fields = [entry["field"] for entry in identity_mismatches(session, _identity())]
    assert fields == ["model_files", "server_env"]


def test_a_reordered_argv_is_named_as_an_ordering_difference():
    session = _identity()
    argv = list(session["server_argv"])
    # Same flags and same values, different order.
    session["server_argv"] = argv[:5] + argv[7:] + argv[5:7]
    fields = [entry["field"] for entry in identity_mismatches(session, _identity())]
    assert fields == ["server_argv[order]"]


def test_an_ordering_difference_is_not_reported_when_a_flag_already_differs():
    """The order fallback must count THIS field's own mismatches, not the
    whole list: an unrelated model_files difference used to suppress it."""

    session = _identity(model_files=[{"path": "models/q4km/model.gguf", "sha256": "z" * 64}])
    argv = list(session["server_argv"])
    argv[argv.index("-c") + 1] = "40960"
    session["server_argv"] = argv
    fields = [entry["field"] for entry in identity_mismatches(session, _identity())]
    assert "server_argv[-c]" in fields
    assert "model_files" in fields
    assert "server_argv[order]" not in fields


def test_a_props_key_the_flight_cannot_derive_is_not_compared():
    session = _identity()
    session["props_identity"]["build_info"] = "version: 1 (deadbeef)"
    assert identity_mismatches(session, _identity()) == []


def test_assert_identity_matches_raises_with_every_differing_field(tmp_path):
    document = build_session_document(
        session_id="s1",
        identity=_identity(port=8081, host="127.0.0.1"),
        pid=1,
        started_at="2026-09-07T00:00:00+00:00",
        serving_geometry={"slots": 2, "slot_tokens": 8192, "max_tokens": 256},
        props=None,
        session_receipt_path="a",
        server_log_path="b",
        monitor_path="c",
    )
    with pytest.raises(ServingIdentityMismatch) as excinfo:
        assert_identity_matches(document, _identity())
    assert "port" in str(excinfo.value)
    assert [entry["field"] for entry in excinfo.value.mismatches] == ["port"]


def test_assert_identity_matches_refuses_a_document_without_an_identity():
    with pytest.raises(ServingSessionError, match="no identity object"):
        assert_identity_matches({"session_id": "s1"}, _identity())


# ---------------------------------------------------------------------------
# resolve_serving_profile: the fragment is the single source of the geometry.
# ---------------------------------------------------------------------------


def _repo_with_fragment(tmp_path: Path, runtime_receipt: dict, fragment: dict) -> Path:
    repo_root = tmp_path / "repo"
    _write_model_fragment(repo_root, "frag", fragment)
    receipt_path = repo_root / "docs" / str(fragment["runtime_receipt"])
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(runtime_receipt), encoding="utf-8")
    return repo_root


def test_resolve_serving_profile_merges_the_fragment_argv_and_pins_the_receipt(tmp_path):
    _runtime_root, _data_root, runtime_receipt = _runtime_world(tmp_path)
    repo_root = _repo_with_fragment(tmp_path, runtime_receipt, _fragment_document())
    profile = resolve_serving_profile(repo_root, "frag")
    assert profile["extra_argv"] == ["-c", "16384", "-np", "2", "-fa", "on", "-ngl", "999"]
    assert profile["serving_geometry"] == {"slots": 2, "slot_tokens": 8192, "max_tokens": 256}
    assert profile["server_env"] == {"GGML_CUDA_DISABLE_GRAPHS": "1"}
    assert profile["session_role"] == "legacy"
    assert len(profile["runtime_receipt_sha256"]) == 64
    assert len(profile["model_fragment_sha256"]) == 64


def test_resolve_serving_profile_refuses_argv_that_disagrees_with_the_geometry(tmp_path):
    _runtime_root, _data_root, runtime_receipt = _runtime_world(tmp_path)
    fragment = _fragment_document()
    fragment["server_args"] = ["-c", "8192", "-np", "2"]
    repo_root = _repo_with_fragment(tmp_path, runtime_receipt, fragment)
    with pytest.raises(ServingSessionError, match="disagree with its declared serving_geometry"):
        resolve_serving_profile(repo_root, "frag")


def test_resolve_serving_profile_refuses_a_malformed_declared_geometry(tmp_path):
    _runtime_root, _data_root, runtime_receipt = _runtime_world(tmp_path)
    fragment = _fragment_document()
    fragment["serving_geometry"] = {"slots": 2, "slot_tokens": 8192}
    repo_root = _repo_with_fragment(tmp_path, runtime_receipt, fragment)
    with pytest.raises(ServingSessionError, match="not an exact"):
        resolve_serving_profile(repo_root, "frag")


def test_resolve_serving_profile_derives_the_geometry_from_c_and_np(tmp_path):
    """Most pinned fragments (the whole hbmfree family) declare no
    ``serving_geometry`` key at all; ``server_args`` is what llama-server is
    actually handed, so it is the authority for the SERVING geometry."""

    _runtime_root, _data_root, runtime_receipt = _runtime_world(tmp_path)
    fragment = _fragment_document()
    del fragment["serving_geometry"]
    fragment["server_args"] = ["-c", "32768", "-np", "16", "-ngl", "999"]
    fragment["decoding_params"] = {"max_tokens": 1024}
    repo_root = _repo_with_fragment(tmp_path, runtime_receipt, fragment)
    profile = resolve_serving_profile(repo_root, "frag")
    assert profile["serving_geometry"] == {
        "slots": 16,
        "slot_tokens": 2048,
        "max_tokens": 1024,
    }


def test_resolve_serving_profile_refuses_a_context_that_is_not_a_multiple_of_the_slots(tmp_path):
    _runtime_root, _data_root, runtime_receipt = _runtime_world(tmp_path)
    fragment = _fragment_document()
    del fragment["serving_geometry"]
    fragment["server_args"] = ["-c", "1000", "-np", "3"]
    repo_root = _repo_with_fragment(tmp_path, runtime_receipt, fragment)
    with pytest.raises(ServingSessionError, match="positive multiple of -np"):
        resolve_serving_profile(repo_root, "frag")


def test_resolve_serving_profile_refuses_a_fragment_with_no_geometry_flags(tmp_path):
    _runtime_root, _data_root, runtime_receipt = _runtime_world(tmp_path)
    fragment = _fragment_document()
    del fragment["serving_geometry"]
    fragment["server_args"] = ["-ngl", "999"]
    repo_root = _repo_with_fragment(tmp_path, runtime_receipt, fragment)
    with pytest.raises(ServingSessionError, match="must declare -c and -np"):
        resolve_serving_profile(repo_root, "frag")


def test_read_fragment_refuses_a_duplicate_top_level_key(tmp_path):
    repo_root = tmp_path / "repo"
    path = repo_root / "configs" / "model" / "dupe.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    with pytest.raises(ConfigError, match="duplicate key"):
        read_fragment(repo_root, "model", "dupe")


# ---------------------------------------------------------------------------
# CLI shape.
# ---------------------------------------------------------------------------


def test_the_cli_accepts_shared_options_after_the_subcommand():
    args = build_parser().parse_args(["start", "q4km-hbmfree-np16", "--port", "9001"])
    assert args.model_fragment == "q4km-hbmfree-np16"
    assert args.port == 9001
    assert args.session_id is None
    stop_args = build_parser().parse_args(["stop", "--session-id", "serving-x"])
    assert stop_args.session_id == "serving-x"


def test_the_cli_requires_a_subcommand():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_the_cli_accepts_min_host_free_gb_only_on_start():
    args = build_parser().parse_args(["start", "frag"])
    assert args.min_host_free_gb == 4.0
    overridden = build_parser().parse_args(["start", "frag", "--min-host-free-gb", "20"])
    assert overridden.min_host_free_gb == 20.0
    with pytest.raises(SystemExit):
        build_parser().parse_args(["status", "--min-host-free-gb", "20"])


# ---------------------------------------------------------------------------
# A server that exited but was never reaped (E7b defect 1, observed
# 2026-09-07 on both sessions of the first day).
#
# The zombie below is real: a child of this test process that has exited and
# that nothing has waited on yet. Everything in this section is about the
# gap between "the OS still answers kill(pid, 0)" and "there is a process
# there", which is what made every stop and every start refuse for the rest
# of that day.
# ---------------------------------------------------------------------------

_POSIX_PROC = os.name != "nt" and Path("/proc").is_dir()
_NEEDS_PROC = pytest.mark.skipif(
    not _POSIX_PROC, reason="zombie states are observable only through a POSIX /proc"
)


@contextlib.contextmanager
def _unreaped_child():
    """A real, unreaped zombie: a child that has exited while this process
    has deliberately not waited on it (``Popen.poll`` would reap it, so it is
    never called)."""

    process = subprocess.Popen(
        [sys.executable, "-c", "raise SystemExit(7)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30.0
        while process_state(process.pid) != PROCESS_STATE_DEFUNCT:
            if time.monotonic() >= deadline:
                raise AssertionError("the child never became a zombie")
            time.sleep(0.02)
        yield process
    finally:
        try:
            process.kill()
            process.wait(timeout=5)
        except (OSError, ValueError, ChildProcessError, subprocess.SubprocessError):
            # Already reaped by the code under test; keep Popen quiet at GC.
            if process.returncode is None:
                process.returncode = 0


@_NEEDS_PROC
def test_a_zombie_is_alive_to_the_old_check_and_defunct_to_the_new_one():
    with _unreaped_child() as process:
        # This IS the 2026-09-07 refusal, reproduced: liveness says yes...
        assert _pid_alive(process.pid) is True
        # ...while the executable image every I5 check resolves is gone.
        with pytest.raises(SessionError, match="cannot resolve executable image"):
            _process_image_path(process.pid)
        assert _pid_is_defunct(process.pid) is True
        assert process_state(process.pid) == PROCESS_STATE_DEFUNCT
        # The kernel still holds the status the parent never collected.
        assert describe_wait_status(_defunct_wait_status(process.pid))["exit_code"] == 7


@_NEEDS_PROC
def test_a_reaped_child_is_gone_and_its_status_is_the_one_it_chose():
    with _unreaped_child() as process:
        reaped, status = reap_child(process.pid)
        assert reaped is True
        described = describe_wait_status(status)
        assert described["exit_code"] == 7
        assert described["signal"] is None
        assert "exited with code 7" in described["description"]
        assert process_state(process.pid) == PROCESS_STATE_GONE
        # Reaping is the parent's privilege and happens exactly once.
        assert reap_child(process.pid) == (False, None)


def test_a_live_process_is_running_and_an_impossible_pid_is_gone():
    assert process_state(os.getpid()) == PROCESS_STATE_RUNNING
    assert process_state(2**22 - 1) == PROCESS_STATE_GONE


def test_describe_wait_status_never_calls_an_unknown_status_a_clean_exit():
    unknown = describe_wait_status(None)
    assert unknown["exit_code"] is None and unknown["signal"] is None
    assert "unknown" in unknown["description"]


@_NEEDS_PROC
def test_stop_session_records_a_defunct_server_as_already_exited(monkeypatch, tmp_path):
    """The whole 2026-09-07 stop failure, in one test.

    Before this fix ``stop_session`` sent no signal (correct) but then waited
    its full timeout on a pid that ``_pid_alive`` insisted was alive, and
    finally raised out of the force path while re-verifying the pinned
    binary of a process that no longer had an executable image -- so no stop
    record was ever written for a server that had stopped.
    """

    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module

    with _unreaped_child() as process:
        receipt = SessionReceipt(
            schema=SESSION_RECEIPT_SCHEMA,
            study=STUDY_SLUG,
            session_id="serving-defunct",
            binary_path="llama.cpp/build/bin/llama-server",
            binary_sha256="c" * 64,
            argv=("llama-server", "--host", "127.0.0.1", "--port", "8080"),
            pid=process.pid,
            host="127.0.0.1",
            port=8080,
            model_files=(ModelFileRef(path="models/x/model.gguf", sha256="a" * 64),),
            started_at="2026-09-07T00:00:00+00:00",
            startup_stdout_sha256=hashlib.sha256(b"").hexdigest(),
        )
        monkeypatch.setattr(
            lifecycle_module, "verify_against_runtime_receipt", lambda *_args: None
        )
        monkeypatch.setattr(
            lifecycle_module,
            "assert_session_alive",
            lambda *_args: pytest.fail("a zombie can never pass a live-process audit"),
        )
        monkeypatch.setattr(
            lifecycle_module.os,
            "kill",
            lambda *_args: pytest.fail("an exited process must never be signalled"),
        )
        output = tmp_path / "stop.json"
        stopped = stop_session(
            receipt,
            runtime_receipt={"runtime": "pinned"},
            runtime_root=tmp_path,
            timeout_seconds=1.0,
            poll_interval_seconds=0.01,
            receipt_path=output,
        )

    assert stopped["termination_signal"] == "ALREADY_EXITED"
    assert stopped["forced"] is False
    # Reaped on the way out, so the record describes a pid that is truly gone.
    assert stopped["final_process_state"] == PROCESS_STATE_GONE
    assert json.loads(output.read_text(encoding="utf-8")) == stopped


# ---------------------------------------------------------------------------
# Proving a session is stale: the pid, the port and the card must all agree.
# ---------------------------------------------------------------------------


def _fake_gpu(*, memory_used_mib=0.0, processes=(), available=True, error=None):
    return lambda: {
        "available": available,
        "memory_used_mib": memory_used_mib,
        "compute_processes": list(processes),
        "error": error,
    }


def _observe(document, *, state=PROCESS_STATE_DEFUNCT, listening=False, gpu=None, status=None):
    return observe_session_process(
        document,
        process_state_probe=lambda _pid: state,
        port_probe=lambda _host, _port: listening,
        gpu_probe=gpu or _fake_gpu(),
        wait_status_probe=lambda _pid: status,
    )


def _session_document(session_id: str = "serving-stale") -> dict:
    return build_session_document(
        session_id=session_id,
        identity=_identity(),
        pid=4242,
        started_at="2026-09-07T00:00:00+00:00",
        serving_geometry={"slots": 2, "slot_tokens": 8192, "max_tokens": 256},
        props=None,
        session_receipt_path="session-receipt.json",
        server_log_path="server.log",
        monitor_path=MONITOR_JSONL_NAME,
    )


def test_a_defunct_pid_on_a_silent_port_and_an_empty_card_is_stale():
    observation = _observe(_session_document(), status=15)
    assert observation["stale"] is True
    assert observation["blockers"] == []
    assert observation["process_state"] == PROCESS_STATE_DEFUNCT
    assert observation["host"] == "127.0.0.1" and observation["port"] == 8080
    assert observation["port_listening"] is False
    # 15 == SIGTERM: the stop that DID land, which is what the coordinator
    # had to reconstruct by hand on 2026-09-07.
    assert observation["exit_status"]["signal"] == 15
    assert observation["exit_status"]["signal_name"] == "SIGTERM"
    assert "advisory" in observation["exit_status"]["source"]


def test_a_running_pid_is_never_stale():
    observation = _observe(_session_document(), state=PROCESS_STATE_RUNNING)
    assert observation["stale"] is False
    assert observation["blockers"] == ["pid 4242 is still running"]
    # A running server has no zombie status to read.
    assert observation["exit_status"]["raw"] is None


def test_a_listening_port_blocks_staleness_even_when_the_pid_is_gone():
    observation = _observe(_session_document(), state=PROCESS_STATE_GONE, listening=True)
    assert observation["stale"] is False
    assert observation["blockers"] == ["something is still listening on 127.0.0.1:8080"]


def test_a_card_that_still_holds_the_model_blocks_staleness():
    observation = _observe(_session_document(), gpu=_fake_gpu(memory_used_mib=18500.0))
    assert observation["stale"] is False
    assert "still holds 18500 MiB" in observation["blockers"][0]


def test_a_listed_compute_process_blocks_staleness():
    observation = _observe(
        _session_document(), gpu=_fake_gpu(processes=["63718, 18500, llama-server"])
    )
    assert observation["stale"] is False
    assert "still lists compute processes" in observation["blockers"][0]


def test_an_unreadable_card_blocks_staleness_rather_than_guessing():
    observation = _observe(
        _session_document(),
        gpu=_fake_gpu(
            available=False, memory_used_mib=None, error="FileNotFoundError: nvidia-smi"
        ),
    )
    assert observation["stale"] is False
    assert "nvidia-smi could not be read" in observation["blockers"][0]


class _FakeCompleted:
    def __init__(self, stdout: str, returncode: int = 0, stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_read_gpu_occupancy_reads_memory_and_the_process_table():
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):
        calls.append(list(argv))
        if "--query-gpu=memory.used" in argv:
            return _FakeCompleted("0\n")
        return _FakeCompleted("")

    gpu = read_gpu_occupancy(run=fake_run)
    assert gpu == {
        "available": True,
        "memory_used_mib": 0.0,
        "compute_processes": [],
        "error": None,
    }
    assert [argv[0] for argv in calls] == ["nvidia-smi", "nvidia-smi"]


def test_read_gpu_occupancy_reports_a_card_it_cannot_read_instead_of_raising():
    def fake_run(_argv, **_kwargs):
        raise FileNotFoundError("nvidia-smi")

    gpu = read_gpu_occupancy(run=fake_run)
    assert gpu["available"] is False
    assert gpu["memory_used_mib"] is None
    assert gpu["compute_processes"] is None
    assert "nvidia-smi" in str(gpu["error"])


# ---------------------------------------------------------------------------
# ``read_host_memory`` (E7c, 2026-09-07 incident): the Windows host's own
# total/free GB and the vmmemWSL working set, beside the VM's own
# MemTotal/MemAvailable -- neither side alone would have shown the host
# running out of headroom around an already-fat WSL VM.
# ---------------------------------------------------------------------------


def _windows_memory_json(
    *, total_kib: int = 46137344, free_kib: int = 6291456, vmmem_bytes: object = 19327352832
) -> str:
    vmmem = "null" if vmmem_bytes is None else str(vmmem_bytes)
    return (
        f'{{"TotalVisibleMemorySize":{total_kib},"FreePhysicalMemory":{free_kib},'
        f'"VmmemWorkingSet64":{vmmem}}}'
    )


def _write_meminfo(path: Path, *, total_kib: int = 46137344, available_kib: int = 41943040) -> Path:
    path.write_text(
        f"MemTotal:       {total_kib} kB\nMemFree:         2000000 kB\n"
        f"MemAvailable:   {available_kib} kB\n",
        encoding="utf-8",
    )
    return path


def test_read_host_memory_parses_the_powershell_json_and_the_vm_meminfo(tmp_path):
    meminfo = _write_meminfo(tmp_path / "meminfo")
    memory = read_host_memory(
        run=lambda *a, **k: _FakeCompleted(_windows_memory_json()), meminfo_path=meminfo
    )
    assert memory["host_total_gb"] == pytest.approx(44.0)
    assert memory["host_free_gb"] == pytest.approx(6.0)
    assert memory["vmmem_ws_gb"] == pytest.approx(18.0)
    assert memory["vm_total_gb"] == pytest.approx(44.0)
    assert memory["vm_available_gb"] == pytest.approx(40.0)
    assert memory["host_memory_source"] == "windows+vm"


def test_read_host_memory_reports_an_absent_vmmem_process_as_null_not_a_failure(tmp_path):
    meminfo = _write_meminfo(tmp_path / "meminfo")
    memory = read_host_memory(
        run=lambda *a, **k: _FakeCompleted(_windows_memory_json(vmmem_bytes=None)),
        meminfo_path=meminfo,
    )
    assert memory["vmmem_ws_gb"] is None
    assert memory["host_total_gb"] == pytest.approx(44.0)
    assert memory["host_memory_source"] == "windows+vm"


@pytest.mark.parametrize(
    "outcome",
    [_FakeCompleted("not json"), _FakeCompleted("", returncode=1)],
)
def test_read_host_memory_fails_soft_on_anything_unusable_from_powershell(outcome, tmp_path):
    meminfo = _write_meminfo(tmp_path / "meminfo")
    memory = read_host_memory(run=lambda *a, **k: outcome, meminfo_path=meminfo)
    assert memory["host_total_gb"] is None
    assert memory["host_free_gb"] is None
    assert memory["vmmem_ws_gb"] is None
    assert memory["host_memory_source"] == "vm-only"
    # The VM side is unaffected by the Windows side failing.
    assert memory["vm_total_gb"] == pytest.approx(44.0)


def test_read_host_memory_reports_one_malformed_field_as_null_not_a_whole_failure(tmp_path):
    """The interop call itself succeeded and returned valid JSON, so the
    Windows side still answers -- only the one field whose type is wrong
    comes back null, exactly like an absent ``vmmemWSL`` process does."""

    meminfo = _write_meminfo(tmp_path / "meminfo")
    memory = read_host_memory(
        run=lambda *a, **k: _FakeCompleted('{"TotalVisibleMemorySize": "oops"}'),
        meminfo_path=meminfo,
    )
    assert memory["host_total_gb"] is None
    assert memory["host_free_gb"] is None
    assert memory["vmmem_ws_gb"] is None
    assert memory["host_memory_source"] == "windows+vm"


def test_read_host_memory_fails_soft_when_powershell_is_absent(tmp_path):
    meminfo = _write_meminfo(tmp_path / "meminfo")

    def _boom(*_args, **_kwargs):
        raise FileNotFoundError("powershell.exe")

    memory = read_host_memory(run=_boom, meminfo_path=meminfo)
    assert memory["host_free_gb"] is None
    assert memory["vm_total_gb"] == pytest.approx(44.0)
    assert memory["host_memory_source"] == "vm-only"


def test_read_host_memory_fails_soft_when_the_vm_meminfo_is_unreadable(tmp_path):
    memory = read_host_memory(
        run=lambda *a, **k: _FakeCompleted(_windows_memory_json()),
        meminfo_path=tmp_path / "does-not-exist",
    )
    assert memory["vm_total_gb"] is None
    assert memory["vm_available_gb"] is None
    assert memory["host_total_gb"] == pytest.approx(44.0)
    assert memory["host_memory_source"] == "windows-only"


def test_read_host_memory_is_unavailable_when_neither_side_answers(tmp_path):
    def _boom(*_args, **_kwargs):
        raise FileNotFoundError("powershell.exe")

    memory = read_host_memory(run=_boom, meminfo_path=tmp_path / "does-not-exist")
    assert memory == {
        "host_total_gb": None,
        "host_free_gb": None,
        "vmmem_ws_gb": None,
        "vm_total_gb": None,
        "vm_available_gb": None,
        "host_memory_source": "unavailable",
        "host_memory_error": "os-error:FileNotFoundError",
    }


def test_read_host_memory_passes_the_pinned_timeout_and_command_shape(tmp_path):
    calls: list[dict[str, object]] = []

    def fake_run(argv, **kwargs):
        calls.append({"argv": list(argv), "kwargs": kwargs})
        return _FakeCompleted(_windows_memory_json())

    read_host_memory(run=fake_run, meminfo_path=_write_meminfo(tmp_path / "meminfo"))
    assert len(calls) == 1
    argv = calls[0]["argv"]
    assert argv[0].endswith("powershell.exe")
    assert "-NoProfile" in argv and "-NonInteractive" in argv
    assert "Microsoft.VisualBasic.Devices.ComputerInfo" in argv[-1] and "Get-Process" in argv[-1]
    assert calls[0]["kwargs"]["timeout"] == 8


# ---------------------------------------------------------------------------
# ``stop --stale``, ``status`` and ``start``: the three operator surfaces the
# defunct state reaches.
# ---------------------------------------------------------------------------


def _stop_world(tmp_path: Path, monkeypatch, **observe):
    """A data root holding one resident session, with the CLI's data-root
    resolution and its process observation both pointed at fakes."""

    import speech_aware_evidence_acquisition.core.session.serving as serving_module
    from speech_aware_evidence_acquisition.data import lock as lock_module

    session_dir = _write_session(tmp_path, "serving-defunct")
    monkeypatch.setattr(lock_module, "data_root", lambda: tmp_path)
    monkeypatch.setattr(
        serving_module,
        "observe_session_process",
        lambda document, **_kwargs: _observe(document, **observe),
    )
    return session_dir


def test_stop_records_a_stale_session_without_signalling_anything(tmp_path, monkeypatch):
    session_dir = _stop_world(tmp_path, monkeypatch, status=15)
    args = build_parser().parse_args(["stop"])

    assert args.handler(args) == 0

    document = json.loads((session_dir / SESSION_STOP_NAME).read_text(encoding="utf-8"))
    assert document["stale"] is True
    assert document["stop_receipt"] is None, "nothing was signalled, so there is no stop receipt"
    assert document["observed"]["process_state"] == PROCESS_STATE_DEFUNCT
    assert document["observed"]["exit_status"]["signal_name"] == "SIGTERM"
    assert document["session_id"] == "serving-defunct"
    assert document["monitor_summary"]["sample_count"] == 0
    # ...and the session is no longer resident, so the next geometry can start.
    assert find_resident_session(tmp_path) is None


def test_stop_stale_refuses_a_session_that_is_still_there(tmp_path, monkeypatch):
    session_dir = _stop_world(tmp_path, monkeypatch, state=PROCESS_STATE_RUNNING)
    args = build_parser().parse_args(["stop", "--stale"])

    with pytest.raises(ServingSessionError, match="is not stale"):
        args.handler(args)
    assert not (session_dir / SESSION_STOP_NAME).exists()
    assert find_resident_session(tmp_path) is not None


def test_stop_does_not_take_the_stale_path_for_a_running_server(tmp_path, monkeypatch):
    session_dir = _stop_world(tmp_path, monkeypatch, state=PROCESS_STATE_RUNNING)
    args = build_parser().parse_args(["stop"])

    # The ordinary path runs instead, and fails on this fake world's missing
    # runtime receipt -- the point is that NO stop record was written for a
    # server that is still running.
    with pytest.raises(SessionError):
        args.handler(args)
    assert not (session_dir / SESSION_STOP_NAME).exists()


def test_status_names_the_defunct_state_beside_the_old_liveness_flag(
    tmp_path, monkeypatch, capsys
):
    _stop_world(tmp_path, monkeypatch)
    args = build_parser().parse_args(["status"])

    assert args.handler(args) == 0

    reported = json.loads(capsys.readouterr().out)
    assert reported["process_state"] == PROCESS_STATE_DEFUNCT
    assert reported["observed"]["stale"] is True
    assert reported["stopped"] is False
    assert reported["session"]["session_id"] == "serving-defunct"


def test_start_explains_a_stale_resident_session_and_names_the_remedy(tmp_path):
    session_dir = _write_session(tmp_path, "serving-defunct")
    document = json.loads((session_dir / SESSION_DOCUMENT_NAME).read_text(encoding="utf-8"))
    message = _resident_refusal(
        session_dir, document, observer=lambda doc: _observe(doc, status=15)
    )
    assert "already recorded as resident" in message
    assert "defunct" in message
    assert "stop --stale --session-id serving-defunct" in message


def test_start_still_says_stop_it_for_a_session_that_is_actually_running(tmp_path):
    session_dir = _write_session(tmp_path, "serving-live")
    document = json.loads((session_dir / SESSION_DOCUMENT_NAME).read_text(encoding="utf-8"))
    message = _resident_refusal(
        session_dir,
        document,
        observer=lambda doc: _observe(doc, state=PROCESS_STATE_RUNNING),
    )
    assert "stop it before starting another" in message
    assert "--stale" not in message


def test_start_names_what_is_still_holding_a_defunct_session(tmp_path):
    session_dir = _write_session(tmp_path, "serving-defunct")
    document = json.loads((session_dir / SESSION_DOCUMENT_NAME).read_text(encoding="utf-8"))
    message = _resident_refusal(
        session_dir,
        document,
        observer=lambda doc: _observe(doc, gpu=_fake_gpu(memory_used_mib=18500.0)),
    )
    assert "not yet provably gone" in message
    assert "still holds 18500 MiB" in message


def test_only_the_stop_subcommand_takes_stale():
    assert build_parser().parse_args(["stop", "--stale"]).stale is True
    assert build_parser().parse_args(["stop"]).stale is False
    with pytest.raises(SystemExit):
        build_parser().parse_args(["status", "--stale"])


# ---------------------------------------------------------------------------
# The wrapper's own three jobs (E7b defect 2): reap the child, record the
# stop, report the exit. It did none of them on 2026-09-07.
# ---------------------------------------------------------------------------


class _WrapperSession:
    """Only what ``_hold_session_open`` reads off a session receipt."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.session_id = "serving-wrapper"
        self.role = "inference"

    def as_json(self) -> dict[str, object]:
        return {
            "schema": "saea-session-receipt-v2",
            "study": STUDY_SLUG,
            "session_id": self.session_id,
            "pid": self.pid,
            "role": self.role,
        }


def _wrapper_world(monkeypatch, tmp_path: Path):
    """A faked ``stop_session`` (the real one re-verifies a pinned binary
    that does not exist in a test world) plus the argv the wrapper runs
    under."""

    import speech_aware_evidence_acquisition.core.session as session_package

    calls: list[object] = []

    def fake_stop_session(session, **kwargs):
        calls.append((session, kwargs))
        return {
            "schema": "saea-session-stop-receipt-v1",
            "session_id": session.session_id,
            "pid": session.pid,
            "termination_signal": "ALREADY_EXITED",
            "forced": False,
            "final_process_state": PROCESS_STATE_GONE,
        }

    monkeypatch.setattr(session_package, "stop_session", fake_stop_session)
    args = build_parser().parse_args(["start", "frag"])
    return args, calls


@_NEEDS_PROC
def test_the_wrapper_reaps_the_server_and_records_why_it_exited(
    tmp_path, monkeypatch, capsys
):
    args, calls = _wrapper_world(monkeypatch, tmp_path)

    with _unreaped_child() as process:
        # The 2026-09-07 state exactly: the child has exited, the wrapper is
        # still its parent, and nothing has reaped it.
        assert _pid_alive(process.pid) is True
        status = _hold_session_open(
            args,
            profile={"runtime_receipt": {"schema": "fake"}},
            session=_WrapperSession(process.pid),
            session_id="serving-wrapper",
            session_dir=tmp_path,
            monitor_path=tmp_path / MONITOR_JSONL_NAME,
        )
        # Reaped: the zombie that broke every later stop is gone.
        assert process_state(process.pid) == PROCESS_STATE_GONE

    assert status == 1, "an unrequested exit must be visible to a job monitor"
    document = json.loads((tmp_path / SESSION_STOP_NAME).read_text(encoding="utf-8"))
    assert document["server_exit"]["reason"] == "server-exited"
    assert document["server_exit"]["reaped"] is True
    assert document["server_exit"]["status"]["exit_code"] == 7
    assert document["stale"] is False
    assert document["stop_receipt"]["termination_signal"] == "ALREADY_EXITED"
    assert len(calls) == 1

    captured = capsys.readouterr()
    lines = [line for line in captured.err.splitlines() if line.strip()]
    assert len(lines) == 1, "one operator line, not a traceback"
    assert lines[0].startswith("serving_session: server pid ")
    assert "exited with code 7" in lines[0]
    assert str(tmp_path / SESSION_STOP_NAME) in lines[0]
    # The document itself still goes to stdout, as every other command does.
    assert json.loads(captured.out)["session_id"] == "serving-wrapper"


@_NEEDS_PROC
@pytest.mark.parametrize(("termination_signal", "forced"), [("SIGTERM", False), ("SIGKILL", True)])
def test_explicit_stop_receipt_wins_when_owner_reaps_after_operator_stop(
    tmp_path, monkeypatch, capsys, termination_signal, forced
):
    args, calls = _wrapper_world(monkeypatch, tmp_path)

    with _unreaped_child() as process:
        explicit = _write_stop_document(
            tmp_path,
            session_id="serving-wrapper",
            stop_receipt={
                "schema": "saea-session-stop-receipt-v1",
                "study": STUDY_SLUG,
                "session_id": "serving-wrapper",
                "session_role": "inference",
                "session_receipt_sha256": _canonical_receipt_sha256(
                    _WrapperSession(process.pid).as_json()
                ),
                "runtime_receipt_sha256": _canonical_receipt_sha256(
                    {"schema": "fake"}
                ),
                "pid": process.pid,
                "termination_signal": termination_signal,
                "forced": forced,
                "stopped_at": "now",
                "final_process_state": PROCESS_STATE_GONE,
            },
            monitor_path=tmp_path / MONITOR_JSONL_NAME,
        )
        status = _hold_session_open(
            args,
            profile={"runtime_receipt": {"schema": "fake"}},
            session=_WrapperSession(process.pid),
            session_id="serving-wrapper",
            session_dir=tmp_path,
            monitor_path=tmp_path / MONITOR_JSONL_NAME,
        )
        assert process_state(process.pid) == PROCESS_STATE_GONE

    assert status == 0
    assert json.loads(
        (tmp_path / SESSION_STOP_NAME).read_text(encoding="utf-8")
    ) == explicit
    assert len(calls) == 0
    assert capsys.readouterr().err == ""


def test_stop_publication_lock_serializes_operator_and_owner(tmp_path):
    import threading

    session = _WrapperSession(4242)
    runtime_receipt = {"schema": "fake"}
    operator_started = threading.Event()
    release_operator = threading.Event()
    owner_seen: list[bool] = []

    def operator_publish() -> None:
        with _session_stop_lock(tmp_path):
            _write_stop_document(
                tmp_path,
                session_id=session.session_id,
                stop_receipt={
                    "schema": "saea-session-stop-receipt-v1",
                    "study": STUDY_SLUG,
                    "session_id": session.session_id,
                    "session_role": session.role,
                    "session_receipt_sha256": _canonical_receipt_sha256(session.as_json()),
                    "runtime_receipt_sha256": _canonical_receipt_sha256(runtime_receipt),
                    "pid": session.pid,
                    "termination_signal": "SIGTERM",
                    "forced": False,
                    "stopped_at": "now",
                    "final_process_state": PROCESS_STATE_GONE,
                },
                monitor_path=tmp_path / MONITOR_JSONL_NAME,
            )
            operator_started.set()
            release_operator.wait(timeout=2)

    def owner_publish() -> None:
        operator_started.wait(timeout=2)
        with _session_stop_lock(tmp_path):
            owner_seen.append(
                _read_explicit_stop_document(
                    tmp_path, session=session, runtime_receipt=runtime_receipt
                )
                is not None
            )

    operator = threading.Thread(target=operator_publish)
    owner = threading.Thread(target=owner_publish)
    operator.start()
    assert operator_started.wait(timeout=2)
    owner.start()
    time.sleep(0.05)
    assert owner_seen == []
    release_operator.set()
    operator.join(timeout=2)
    owner.join(timeout=2)
    assert owner_seen == [True]


@_NEEDS_PROC
def test_same_pid_stop_with_wrong_runtime_binding_is_untrusted(
    tmp_path, monkeypatch, capsys
):
    args, calls = _wrapper_world(monkeypatch, tmp_path)

    with _unreaped_child() as process:
        session = _WrapperSession(process.pid)
        stop_receipt = {
            "schema": "saea-session-stop-receipt-v1",
            "study": STUDY_SLUG,
            "session_id": session.session_id,
            "session_role": session.role,
            "session_receipt_sha256": _canonical_receipt_sha256(session.as_json()),
            "runtime_receipt_sha256": "0" * 64,
            "pid": process.pid,
            "termination_signal": "SIGTERM",
            "forced": False,
            "stopped_at": "now",
            "final_process_state": PROCESS_STATE_GONE,
        }
        _write_stop_document(
            tmp_path,
            session_id=session.session_id,
            stop_receipt=stop_receipt,
            monitor_path=tmp_path / MONITOR_JSONL_NAME,
        )
        status = _hold_session_open(
            args,
            profile={"runtime_receipt": {"schema": "fake"}},
            session=session,
            session_id=session.session_id,
            session_dir=tmp_path,
            monitor_path=tmp_path / MONITOR_JSONL_NAME,
        )
        assert process_state(process.pid) == PROCESS_STATE_GONE

    assert status == 1
    document = json.loads((tmp_path / SESSION_STOP_NAME).read_text(encoding="utf-8"))
    assert document["server_exit"] is not None
    assert len(calls) == 1
    assert "exited with code 7" in capsys.readouterr().err


@_NEEDS_PROC
def test_the_wrapper_returns_zero_and_restores_signals_when_asked_to_stop(
    tmp_path, monkeypatch, capsys
):
    import signal as signal_module
    import threading

    import speech_aware_evidence_acquisition.core.session.lifecycle as lifecycle_module
    import speech_aware_evidence_acquisition.core.session.serving as serving_module

    args, calls = _wrapper_world(monkeypatch, tmp_path)
    # A server that is running and stays running: only the operator's signal
    # can end this loop.
    monkeypatch.setattr(serving_module, "process_state", lambda _pid: PROCESS_STATE_RUNNING)
    monkeypatch.setattr(lifecycle_module, "reap_child", lambda _pid: (False, None))

    def _test_handler(_signum, _frame):  # pragma: no cover -- only if mistimed
        return None

    # Installed before the timer so a signal that arrives early cannot kill
    # the test run; _hold_session_open restores exactly this handler.
    previous = signal_module.signal(signal_module.SIGTERM, _test_handler)
    timer = threading.Timer(0.3, lambda: os.kill(os.getpid(), signal_module.SIGTERM))
    timer.start()
    try:
        status = _hold_session_open(
            args,
            profile={"runtime_receipt": {"schema": "fake"}},
            session=_WrapperSession(4242),
            session_id="serving-wrapper",
            session_dir=tmp_path,
            monitor_path=tmp_path / MONITOR_JSONL_NAME,
        )
        assert signal_module.getsignal(signal_module.SIGTERM) is _test_handler
    finally:
        timer.cancel()
        signal_module.signal(signal_module.SIGTERM, previous)

    assert status == 0
    document = json.loads((tmp_path / SESSION_STOP_NAME).read_text(encoding="utf-8"))
    assert document["server_exit"] is None, "the operator asked; nothing exited unasked"
    assert len(calls) == 1
    assert capsys.readouterr().err == ""


def test_the_wrapper_has_no_restart_on_exit_option():
    """An unexpected exit must be visible, not papered over (owner rule:
    monitoring numbers are the price of leaving the model on)."""

    with pytest.raises(SystemExit):
        build_parser().parse_args(["start", "frag", "--restart-on-exit"])


# ---------------------------------------------------------------------------
# `resident`: the question a script must ask before it kills llama-server
# (E7b defect 3's audit -- scripts/run_arm_sequence.sh).
# ---------------------------------------------------------------------------


def test_resident_exits_zero_and_describes_the_session_it_found(tmp_path, monkeypatch, capsys):
    _stop_world(tmp_path, monkeypatch, state=PROCESS_STATE_RUNNING)
    args = build_parser().parse_args(["resident"])

    assert args.handler(args) == 0

    reported = json.loads(capsys.readouterr().out)
    assert reported["resident"] is True
    assert reported["session_id"] == "serving-defunct"
    assert reported["process_state"] == PROCESS_STATE_RUNNING
    assert reported["stale"] is False


def test_resident_exits_three_when_nothing_is_resident(tmp_path, monkeypatch, capsys):
    from speech_aware_evidence_acquisition.data import lock as lock_module

    monkeypatch.setattr(lock_module, "data_root", lambda: tmp_path)
    args = build_parser().parse_args(["resident"])

    # 3, never 0 and never 2: a killer script may only kill on this one code.
    assert args.handler(args) == NO_RESIDENT_SESSION_EXIT
    assert json.loads(capsys.readouterr().out)["resident"] is False


def test_resident_refuses_rather_than_answering_when_two_sessions_are_recorded(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.data import lock as lock_module

    _write_session(tmp_path, "one")
    _write_session(tmp_path, "two")
    monkeypatch.setattr(lock_module, "data_root", lambda: tmp_path)
    args = build_parser().parse_args(["resident"])

    with pytest.raises(ServingSessionError, match="2 serving sessions"):
        args.handler(args)


def test_the_arm_launcher_only_kills_llama_server_behind_the_resident_check():
    """``scripts/run_arm_sequence.sh`` used to ``pkill -9 -f llama-server``
    twice per arm, unconditionally -- the one path in this repository that
    could have killed the coordinator's resident server."""

    script = (
        Path(__file__).resolve().parents[2] / "scripts" / "run_arm_sequence.sh"
    ).read_text(encoding="utf-8")
    body = "\n".join(
        line for line in script.splitlines() if not line.lstrip().startswith("#")
    )
    assert body.count("pkill -9") == 1, "the one kill must live inside the guard"
    guard = body.split("kill_stray_llama_servers () {", 1)[1].split("\n}", 1)[0]
    assert "serving_session.sh" in guard and "pkill" in guard
    assert 'rc" -ne 3' in guard, "only 'no session resident' (exit 3) may permit the kill"


# ---------------------------------------------------------------------------
# Host memory (E7c, 2026-09-07 incident): ``start`` refuses to bring up
# another 18.5 GB resident server on a host that provably does not have room
# for it; ``status`` reports the CURRENT reading beside the session document.
# ---------------------------------------------------------------------------

_HEALTHY_HOST_MEMORY = {
    "host_total_gb": 44.0,
    "host_free_gb": 30.0,
    "vmmem_ws_gb": 10.0,
    "vm_total_gb": 40.0,
    "vm_available_gb": 32.0,
    "host_memory_source": "windows+vm",
}

_LOW_HOST_MEMORY = {
    "host_total_gb": 44.0,
    "host_free_gb": 4.0,
    "vmmem_ws_gb": 20.0,
    "vm_total_gb": 40.0,
    "vm_available_gb": 8.0,
    "host_memory_source": "windows+vm",
}

_UNAVAILABLE_HOST_MEMORY = {
    "host_total_gb": None,
    "host_free_gb": None,
    "vmmem_ws_gb": None,
    "vm_total_gb": None,
    "vm_available_gb": None,
    "host_memory_source": "unavailable",
    "host_memory_error": "os-error:FileNotFoundError",
}


def test_start_refuses_when_the_host_free_memory_is_below_the_floor(monkeypatch):
    import speech_aware_evidence_acquisition.core.session.serving as serving_module

    monkeypatch.setattr(serving_module, "read_host_memory", lambda: dict(_LOW_HOST_MEMORY))
    args = build_parser().parse_args(["start", "frag", "--min-host-free-gb", "12"])

    with pytest.raises(ServingSessionError, match=r"host's free memory is 4\.0 GB"):
        serving_module._start(args)


def test_start_proceeds_past_the_host_memory_check_on_a_healthy_reading(tmp_path, monkeypatch):
    """A healthy reading must not block ``start``: this proves it by letting
    the (faked) check pass and observing the NEXT refusal in line -- resolving
    ``frag`` against a repo that declares no such fragment -- instead of the
    host-memory one."""

    import speech_aware_evidence_acquisition.core.session.serving as serving_module
    from speech_aware_evidence_acquisition.data import lock as lock_module

    monkeypatch.setattr(serving_module, "read_host_memory", lambda: dict(_HEALTHY_HOST_MEMORY))
    monkeypatch.setattr(lock_module, "data_root", lambda: tmp_path)
    monkeypatch.setattr(serving_module, "_repo_root", lambda: tmp_path / "no-such-repo")
    args = build_parser().parse_args(["start", "frag"])

    with pytest.raises(ConfigError, match="missing config fragment"):
        serving_module._start(args)


def test_start_fails_open_on_the_host_memory_check_when_the_reading_is_unavailable(
    tmp_path, monkeypatch
):
    """An unreadable host must never be treated as a low one: fail-soft
    ``None`` fields fail OPEN here, exactly as an unreadable GPU never proves
    staleness in :func:`observe_session_process`."""

    import speech_aware_evidence_acquisition.core.session.serving as serving_module
    from speech_aware_evidence_acquisition.data import lock as lock_module

    monkeypatch.setattr(
        serving_module, "read_host_memory", lambda: dict(_UNAVAILABLE_HOST_MEMORY)
    )
    monkeypatch.setattr(lock_module, "data_root", lambda: tmp_path)
    monkeypatch.setattr(serving_module, "_repo_root", lambda: tmp_path / "no-such-repo")
    args = build_parser().parse_args(["start", "frag"])

    with pytest.raises(ConfigError, match="missing config fragment"):
        serving_module._start(args)


def test_status_reports_the_current_host_reading_beside_the_session(
    tmp_path, monkeypatch, capsys
):
    import speech_aware_evidence_acquisition.core.session.serving as serving_module

    _stop_world(tmp_path, monkeypatch, state=PROCESS_STATE_RUNNING)
    monkeypatch.setattr(serving_module, "read_host_memory", lambda: dict(_HEALTHY_HOST_MEMORY))
    args = build_parser().parse_args(["status"])

    assert args.handler(args) == 0

    reported = json.loads(capsys.readouterr().out)
    assert reported["host_memory"] == _HEALTHY_HOST_MEMORY


# ---------------------------------------------------------------------------
# ``host-memory`` (owner decision 163): the start guard's verdict on the
# CURRENT reading, asked by serving_swap.sh BEFORE it stops the resident
# geometry (2026-09-27: two restarts refused at 11.7 and 10.1 GB after the
# running server had already been stopped).
# ---------------------------------------------------------------------------


def test_host_memory_verdict_applies_the_guard_plus_the_margin():
    from speech_aware_evidence_acquisition.core.session.serving import host_memory_verdict

    short = host_memory_verdict({"host_free_gb": 12.3}, min_host_free_gb=12.0, margin_gb=0.5)
    assert short["admits"] is False and short["required_gb"] == 12.5
    enough = host_memory_verdict({"host_free_gb": 12.6}, min_host_free_gb=12.0, margin_gb=0.5)
    assert enough["admits"] is True
    bare = host_memory_verdict({"host_free_gb": 12.3}, min_host_free_gb=12.0)
    assert bare["admits"] is True


def test_host_memory_verdict_fails_open_like_the_start_guard():
    from speech_aware_evidence_acquisition.core.session.serving import host_memory_verdict

    for reading in ({"host_free_gb": None}, {}, {"host_free_gb": True}):
        verdict = host_memory_verdict(reading, min_host_free_gb=12.0, margin_gb=0.5)
        assert verdict["admits"] is None and verdict["host_free_gb"] is None


def test_the_host_memory_command_exits_four_only_on_a_proven_shortfall(monkeypatch, capsys):
    import speech_aware_evidence_acquisition.core.session.serving as serving_module

    args = build_parser().parse_args(["host-memory", "--min-host-free-gb", "12", "--margin-gb", "0.5"])
    assert args.min_host_free_gb == 12.0 and args.margin_gb == 0.5
    monkeypatch.setattr(serving_module, "read_host_memory", lambda: {"host_free_gb": 11.7})
    assert args.handler(args) == serving_module.HOST_MEMORY_SHORT_EXIT == 4
    assert json.loads(capsys.readouterr().out)["admits"] is False
    monkeypatch.setattr(serving_module, "read_host_memory", lambda: {"host_free_gb": 20.0})
    assert args.handler(args) == 0
    monkeypatch.setattr(serving_module, "read_host_memory", lambda: {"host_free_gb": None})
    assert args.handler(args) == 0
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1])["admits"] is None
