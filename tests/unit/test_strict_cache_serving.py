"""Refuse incompatible raw-audio cache serving before any process starts."""

import hashlib

import pytest

from speech_aware_evidence_acquisition.core.session import SessionError
from speech_aware_evidence_acquisition.core.session.lifecycle import (
    build_server_command,
    start_session,
)

STRICT = "LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT"
CACHE = "LLAMA_MTMD_FEAT_CACHE_DIR"
VALIDATE = "LLAMA_MTMD_FEAT_CACHE_VALIDATE"


@pytest.fixture
def serving(tmp_path, monkeypatch):
    for key in (STRICT, CACHE, VALIDATE, "LLAMA_ARG_MMPROJ_OFFLOAD"):
        monkeypatch.delenv(key, raising=False)
    binary = tmp_path / "llama-server"
    binary.write_bytes(b"synthetic binary; never execute")
    for name in ("model.gguf", "mmproj.gguf"):
        (tmp_path / name).write_bytes(b"synthetic weights")
    cache = tmp_path / "cache"
    cache.mkdir()
    return dict(
        runtime_root=tmp_path,
        data_root=tmp_path,
        model_root=tmp_path,
        runtime_receipt={
            "llama_cpp": {
                "binary_path": "llama-server",
                "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            },
            "gguf_files": [
                {"path": name, "sha256": "a" * 64}
                for name in ("model.gguf", "mmproj.gguf")
            ],
        },
        host="127.0.0.1",
        port=8080,
        role="legacy",
        extra_argv=("--no-mmproj-offload", "-c", "36864", "-np", "6"),
        extra_env={STRICT: "1", CACHE: str(cache)},
    )


def test_accept_cpu_projector_and_keep_geometry(serving):
    command = build_server_command(**serving)
    assert "--no-mmproj-offload" in command.argv
    assert "--mmproj" in command.argv
    assert command.argv[-4:] == ("-c", "36864", "-np", "6")


@pytest.mark.parametrize("args", [(), ("--mmproj-offload",),
    ("--no-mmproj-offload", "--mmproj-offload"),
    ("--no-mmproj-offload", "--mmproj-offload=true"),
    ("--no-mmproj-offload", "--no-mmproj"),
    ("--no-mmproj-offload", "--mmproj", "different.gguf")])
def test_refuse_gpu_or_conflicting_projector_before_spawn(serving, args):
    serving["extra_argv"] = args
    def forbidden_spawn(*args, **kwargs):
        pytest.fail("incompatible serving configuration reached process creation")
    with pytest.raises(SessionError, match="strict feature-cache"):
        start_session(**serving, session_id="strict-test", popen=forbidden_spawn)


@pytest.mark.parametrize("role", ["inference", "preprocess"])
def test_strict_cache_role_is_raw_generation_only(serving, role):
    serving["role"] = role
    with pytest.raises(SessionError, match="strict feature-cache"):
        build_server_command(**serving)


@pytest.mark.parametrize("value", ["1", "0", ""])
def test_validate_presence_refused_even_when_false_looking(serving, value):
    serving["extra_env"][VALIDATE] = value
    with pytest.raises(SessionError, match="VALIDATE"):
        build_server_command(**serving)


def test_inherited_validate_refused(serving, monkeypatch):
    monkeypatch.setenv(VALIDATE, "0")
    with pytest.raises(SessionError, match="VALIDATE"):
        build_server_command(**serving)


def test_strict_mode_cannot_be_implicitly_inherited(serving, monkeypatch):
    serving["extra_env"].pop(STRICT)
    monkeypatch.setenv(STRICT, "1")
    with pytest.raises(SessionError, match="explicit"):
        build_server_command(**serving)


@pytest.mark.parametrize("value", [None, "", "relative/cache", "/does/not/exist"])
def test_cache_must_be_explicit_existing_absolute_directory(serving, value):
    if value is None:
        serving["extra_env"].pop(CACHE)
    else:
        serving["extra_env"][CACHE] = value
    with pytest.raises(SessionError, match="cache directory"):
        build_server_command(**serving)


def test_inherited_cache_root_cannot_replace_bound_root(serving, monkeypatch):
    monkeypatch.setenv(CACHE, serving["extra_env"].pop(CACHE))
    with pytest.raises(SessionError, match="cache directory"):
        build_server_command(**serving)


def test_receipt_without_projector_refused(serving):
    serving["runtime_receipt"]["gguf_files"] = serving["runtime_receipt"]["gguf_files"][:1]
    with pytest.raises(SessionError, match="pinned mmproj"):
        build_server_command(**serving)


def test_legacy_without_opt_in_retains_gpu_arguments(serving):
    serving["extra_env"] = {}
    serving["extra_argv"] = ("-c", "36864", "-np", "6")
    command = build_server_command(**serving)
    assert "--mmproj" in command.argv
    assert "--no-mmproj-offload" not in command.argv


def test_packet_inference_without_opt_in_retains_no_projector(serving):
    serving["role"] = "inference"
    serving["extra_env"] = {}
    serving["extra_argv"] = ()
    command = build_server_command(**serving)
    assert "--no-mmproj" in command.argv
    assert len(command.model_files) == 1


def test_non_string_environment_refused(serving):
    serving["extra_env"][STRICT] = True
    with pytest.raises(SessionError, match="str->str"):
        build_server_command(**serving)


@pytest.mark.parametrize("value", ["0", ""])
def test_strict_presence_requires_cpu_even_with_false_looking_value(serving, value):
    serving["extra_env"][STRICT] = value
    serving["extra_argv"] = ()
    with pytest.raises(SessionError, match="no-mmproj-offload"):
        build_server_command(**serving)


@pytest.mark.parametrize("flag", ["-mm", "-mmu", "-m", "--model", "--model-url", "-mu", "-hf"])
def test_refuse_model_or_projector_overrides_in_extra_arguments(serving, flag):
    serving["extra_argv"] = ("--no-mmproj-offload", flag, "unbound-file")
    with pytest.raises(SessionError, match="strict feature-cache"):
        build_server_command(**serving)


@pytest.mark.parametrize("flag", ["-hfr", "-dr", "--docker-repo", "-hfrv", "-hffv", "--hf-file-v", "-mv", "--model-vocoder", "--model_url", "--hf_repo"])
def test_refuse_remaining_model_aliases(serving, flag):
    serving["extra_argv"] = ("--no-mmproj-offload", flag, "unbound-file")
    with pytest.raises(SessionError, match="strict feature-cache"):
        build_server_command(**serving)


@pytest.mark.parametrize("key", ["LLAMA_ARG_MMPROJ_OFFLOAD", "LLAMA_ARG_MMPROJ_AUTO", "LLAMA_ARG_NO_MMPROJ_AUTO", "LLAMA_ARG_MODEL_URL", "LLAMA_ARG_HF_REPO"])
@pytest.mark.parametrize("inherited", [True, False])
def test_refuse_extra_model_configuration_environments(serving, monkeypatch, key, inherited):
    if inherited:
        monkeypatch.setenv(key, "1")
    else:
        serving["extra_env"][key] = "1"
    with pytest.raises(SessionError, match="model.*environment"):
        build_server_command(**serving)
