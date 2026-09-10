"""Shared verification of role-specific runtime receipts for preparation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from .config import resolve_feature_encoder_runtime_receipt_path
from .model import FrozenCoreError
from .preparation import PreparationError, hash_stable_file
from .preparation_windows import WindowFeatureEncoderIdentity
from .model.paths import _normalized_relative_path, _resolve_confined

_RUNTIME_KEYS = {
    "schema",
    "study",
    "model_lock_key",
    "llama_cpp",
    "gguf_files",
    "runtime_libraries",
}
_HEX = set("0123456789abcdef")


@dataclass(frozen=True)
class VerifiedFeatureEncoderRuntime:
    encoder_identity: WindowFeatureEncoderIdentity
    receipt: Mapping[str, object]
    receipt_path: Path
    receipt_sha256: str


def _stable_receipt(path: Path, loader: Callable[[Path], Mapping[str, object]]) -> tuple[Mapping[str, object], str]:
    size, sha256, fingerprint = hash_stable_file(path, "feature encoder runtime receipt")
    if size == 0:
        raise PreparationError("feature encoder runtime receipt is empty")
    receipt = loader(path)
    try:
        current = path.stat()
    except OSError as error:
        raise PreparationError(f"cannot restat feature encoder runtime receipt {path}: {error}") from error
    if (current.st_ino, current.st_size, current.st_mtime_ns) != fingerprint:
        raise PreparationError("feature encoder runtime receipt changed while it was read")
    return receipt, sha256


def assert_stable_file_fingerprint(
    path: Path, fingerprint: tuple[int, int, int], label: str
) -> None:
    """Refuse a document that changed between hashing and loading."""

    try:
        current = path.stat()
    except OSError as error:
        raise PreparationError(f"cannot restat {label} {path}: {error}") from error
    if (current.st_ino, current.st_size, current.st_mtime_ns) != fingerprint:
        raise PreparationError(f"{label} changed while it was read")


def verify_pinned_file(
    path: Path, *, expected_size: object, expected_sha256: object, label: str
) -> str:
    """Verify one receipt-pinned file using the shared stable-file reader."""

    if (
        isinstance(expected_size, bool)
        or not isinstance(expected_size, int)
        or expected_size < 0
    ):
        raise PreparationError(f"{label} receipt size must be a non-negative integer")
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(char not in _HEX for char in expected_sha256)
    ):
        raise PreparationError(f"{label} receipt hash must be a lowercase SHA256")
    actual_size, actual_sha256, _ = hash_stable_file(path, label)
    if actual_size != expected_size:
        raise PreparationError(
            f"{label} size {actual_size} does not match receipt size {expected_size}"
        )
    if actual_sha256 != expected_sha256:
        raise PreparationError(f"{label} hash does not match the runtime receipt")
    return actual_sha256


def _runtime_files(
    receipt: Mapping[str, object],
    *,
    runtime_root: Path,
    materialization_root: Path,
    role: str,
    require_mmproj: bool = True,
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    actual_role = receipt.get("role", "legacy")
    if actual_role != role:
        raise PreparationError(f"runtime receipt role must be {role!r}")
    required_keys = _RUNTIME_KEYS | ({"role"} if role != "legacy" else set())
    if set(receipt) != required_keys:
        raise PreparationError("runtime receipt has unexpected keys")
    llama = receipt.get("llama_cpp")
    if not isinstance(llama, Mapping):
        raise PreparationError("runtime receipt lacks llama_cpp mapping")
    build_commit = llama.get("build_commit")
    if (
        not isinstance(build_commit, str)
        or len(build_commit) != 40
        or any(char not in _HEX for char in build_commit)
    ):
        raise PreparationError("runtime receipt build_commit is invalid")
    try:
        binary_rel = _normalized_relative_path(llama.get("binary_path"), "runtime binary path")
        binary = _resolve_confined(runtime_root, binary_rel, runtime_root, "runtime binary path", strict=True)
    except FrozenCoreError as error:
        raise PreparationError(str(error)) from error
    verify_pinned_file(
        binary,
        expected_size=llama.get("binary_bytes"),
        expected_sha256=llama.get("binary_sha256"),
        label="runtime binary",
    )

    ggufs = receipt.get("gguf_files")
    if not isinstance(ggufs, list) or not ggufs:
        raise PreparationError("runtime receipt gguf_files is invalid")
    decoder: dict[str, object] | None = None
    mmproj: dict[str, object] | None = None
    for entry in ggufs:
        if not isinstance(entry, Mapping):
            raise PreparationError("runtime receipt GGUF entry is invalid")
        try:
            relative = _normalized_relative_path(entry.get("path"), "runtime GGUF path")
            target = _resolve_confined(
                materialization_root, relative, materialization_root,
                "runtime GGUF path", strict=True
            )
        except FrozenCoreError as error:
            raise PreparationError(str(error)) from error
        verify_pinned_file(
            target,
            expected_size=entry.get("bytes"),
            expected_sha256=entry.get("sha256"),
            label="runtime GGUF",
        )
        if "mmproj" in Path(relative).name.lower():
            if mmproj is not None:
                raise PreparationError("runtime receipt has duplicate mmproj GGUF")
            mmproj = dict(entry)
        else:
            if decoder is not None:
                raise PreparationError("runtime receipt has duplicate decoder GGUF")
            decoder = dict(entry)
    if decoder is None or (require_mmproj and mmproj is None):
        raise PreparationError("runtime receipt is missing required decoder/mmproj GGUF")

    libraries = receipt.get("runtime_libraries")
    if not isinstance(libraries, list) or not libraries:
        raise PreparationError("runtime receipt runtime_libraries is invalid")
    normalized_libraries = []
    for entry in libraries:
        if not isinstance(entry, Mapping):
            raise PreparationError("runtime library entry is invalid")
        try:
            relative = _normalized_relative_path(entry.get("path"), "runtime library path")
            target = _resolve_confined(runtime_root, relative, runtime_root, "runtime library path", strict=True)
        except FrozenCoreError as error:
            raise PreparationError(str(error)) from error
        verify_pinned_file(
            target,
            expected_size=entry.get("bytes"),
            expected_sha256=entry.get("sha256"),
            label="runtime library",
        )
        normalized_libraries.append(dict(entry))
    return dict(llama), {"decoder": decoder, "mmproj": mmproj}, {
        "libraries": normalized_libraries
    }


def verify_feature_encoder_runtime(
    *,
    repo_root: Path,
    data_root: Path,
    runtime_root: Path,
    values: Mapping[str, object],
    generation_receipt: Mapping[str, object],
    receipt_loader: Callable[[Path], Mapping[str, object]],
) -> VerifiedFeatureEncoderRuntime | None:
    """Verify optional preprocess receipt against the generation runtime identity."""

    receipt_path = resolve_feature_encoder_runtime_receipt_path(repo_root, values)
    if receipt_path is None:
        return None
    encoder_receipt, receipt_sha256 = _stable_receipt(receipt_path, receipt_loader)
    if encoder_receipt.get("role") != "preprocess":
        raise PreparationError("feature encoder runtime receipt must have role preprocess")
    generation_llama, generation_ggufs, generation_libs = _runtime_files(
        generation_receipt,
        runtime_root=Path(runtime_root),
        materialization_root=Path(data_root),
        role=str(generation_receipt.get("role", "legacy")),
        require_mmproj=False,
    )
    encoder_llama, encoder_ggufs, encoder_libs = _runtime_files(
        encoder_receipt,
        runtime_root=Path(runtime_root),
        materialization_root=Path(data_root),
        role="preprocess",
    )
    if encoder_llama != generation_llama:
        raise PreparationError("feature encoder and generation build identities differ")
    if encoder_receipt.get("study") != generation_receipt.get("study"):
        raise PreparationError("feature encoder and generation study identities differ")
    if encoder_receipt.get("model_lock_key") != generation_receipt.get("model_lock_key"):
        raise PreparationError("feature encoder and generation model identities differ")
    if encoder_libs != generation_libs:
        raise PreparationError("feature encoder and generation runtime libraries differ")
    if encoder_ggufs["decoder"] != generation_ggufs["decoder"]:
        raise PreparationError("feature encoder and generation decoder identities differ")
    if (
        generation_ggufs["mmproj"] is not None
        and encoder_ggufs["mmproj"] != generation_ggufs["mmproj"]
    ):
        raise PreparationError("feature encoder and generation mmproj identities differ")
    decoder_sha256 = encoder_ggufs["decoder"]["sha256"]
    mmproj_sha256 = encoder_ggufs["mmproj"]["sha256"]
    if not isinstance(decoder_sha256, str) or not isinstance(mmproj_sha256, str):
        raise PreparationError("feature encoder GGUF identities are invalid")
    identity = WindowFeatureEncoderIdentity(
        runtime_receipt_sha256=receipt_sha256,
        build_commit=encoder_llama["build_commit"],
        decoder_gguf_sha256=decoder_sha256,
        mmproj_sha256=mmproj_sha256,
    )
    return VerifiedFeatureEncoderRuntime(
        encoder_identity=identity,
        receipt=encoder_receipt,
        receipt_path=receipt_path,
        receipt_sha256=receipt_sha256,
    )
