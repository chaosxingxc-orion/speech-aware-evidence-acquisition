"""Validate opt-in raw-audio serving configuration before process creation.

This check is necessary but insufficient for live cache qualification. Require
separate complete cache receipts and a runtime-tested, pinned refusal boundary.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, Sequence

from . import SessionError
from .receipt import ModelFileRef

_REQUIRE_HIT = "LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT"
_CACHE_DIR = "LLAMA_MTMD_FEAT_CACHE_DIR"
_VALIDATE = "LLAMA_MTMD_FEAT_CACHE_VALIDATE"
_CPU_PROJECTOR = "--no-mmproj-offload"


def validate_strict_feature_cache_serving(
    *,
    role: str,
    extra_argv: Sequence[str],
    extra_env: Mapping[str, str] | None,
    model_files: Sequence[ModelFileRef],
) -> None:
    """Bind strict cache use explicitly and keep its projector outside GPU memory.

    llama.cpp tests environment-variable presence, including empty or "0"
    values. Inspect inherited VALIDATE too because the launcher inherits the
    process environment. Never activate strict mode from an unbound shell value.
    Preserve historical serving behavior when strict mode is absent.
    """

    declared = extra_env or {}
    if _REQUIRE_HIT not in declared:
        if _REQUIRE_HIT in os.environ:
            raise SessionError(
                "strict feature-cache serving requires an explicit server_env binding"
            )
        return
    if role != "legacy":
        raise SessionError(
            "strict feature-cache raw-audio serving requires the legacy session role; "
            "preprocessing must encode and packet inference must omit mmproj"
        )
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in declared.items()):
        raise SessionError("strict feature-cache server_env entries must be str->str")
    if _VALIDATE in declared or _VALIDATE in os.environ:
        raise SessionError(
            "strict feature-cache serving refuses VALIDATE, which re-encodes audio"
        )
    cache = declared.get(_CACHE_DIR)
    if not cache or not Path(cache).is_absolute() or not Path(cache).is_dir():
        raise SessionError(
            "strict feature-cache cache directory must be explicit, absolute and existing"
        )
    model_env = {
        "LLAMA_ARG_MODEL", "LLAMA_ARG_MODEL_URL", "LLAMA_ARG_DOCKER_REPO",
        "LLAMA_ARG_HF_REPO", "LLAMA_ARG_HF_FILE", "LLAMA_ARG_HF_REPO_V",
        "LLAMA_ARG_HF_FILE_V", "LLAMA_ARG_MODEL_VOCODER", "LLAMA_ARG_MMPROJ",
        "LLAMA_ARG_MMPROJ_URL", "LLAMA_ARG_MMPROJ_AUTO",
        "LLAMA_ARG_NO_MMPROJ_AUTO", "LLAMA_ARG_MMPROJ_OFFLOAD",
        "LLAMA_ARG_NO_MMPROJ_OFFLOAD",
    }
    if model_env.intersection(declared) or model_env.intersection(os.environ):
        raise SessionError(
            "strict feature-cache serving refuses extra model/projector environment "
            "settings; bind model paths through the runtime receipt and CPU flag"
        )
    model_overrides = {
        "-m", "--model", "-mu", "--model-url", "-mm", "-mmu", "-hf",
        "--hf-repo", "-hfr", "-hff", "--hf-file", "-hfv", "--hf-repo-v",
        "-dr", "--docker-repo", "-hfrv", "-hffv", "--hf-file-v",
        "-mv", "--model-vocoder",
    }
    normalized_args = [
        arg.replace("_", "-") if arg.startswith("--") else arg for arg in extra_argv
    ]
    if any(arg.split("=", 1)[0] in model_overrides for arg in normalized_args):
        raise SessionError(
            "strict feature-cache serving refuses model or projector overrides"
        )
    projector_args = [arg for arg in normalized_args if "mmproj" in arg.lower()]
    if projector_args != [_CPU_PROJECTOR]:
        raise SessionError(
            "strict feature-cache serving requires exactly --no-mmproj-offload and "
            "refuses conflicting projector flags or paths"
        )
    if not any("mmproj" in Path(entry.path).name.lower() for entry in model_files):
        raise SessionError("strict feature-cache serving requires a runtime-pinned mmproj")
