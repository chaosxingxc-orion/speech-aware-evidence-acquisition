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

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import ConfigError, read_fragment
from speech_aware_evidence_acquisition.core.session import (
    SessionError,
    build_server_command,
)
from speech_aware_evidence_acquisition.core.session.serving import (
    MONITOR_JSONL_NAME,
    SESSION_DOCUMENT_NAME,
    SESSION_STOP_NAME,
    SERVING_SESSION_SCHEMA,
    ServingIdentityMismatch,
    ServingSessionError,
    assert_identity_matches,
    build_parser,
    build_session_document,
    find_resident_session,
    identity_mismatches,
    merge_server_args,
    props_identity,
    resolve_serving_profile,
    serving_identity,
    serving_session_dir,
    write_json_document,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


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
