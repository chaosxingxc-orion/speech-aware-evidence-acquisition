"""Build the registered transport with optional prepared-cache enforcement."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Mapping

from .base import TRANSPORTS
from .config import model_materialization_root, prepared_window_feature_cache
from .model import FrozenCoreError, PreparedFeatureCacheGuard
from .model.paths import _resolve_confined
from .preparation import PreparationError, load_artifact
from .preparation_feature_cache import FEATURE_CACHE_AUDIT_KIND
from .preparation_feature_provenance import (
    PROVENANCE_KIND,
    PROVENANCE_SCHEMA,
    PROVENANCE_STATE,
)
from .preparation_runtime import verify_feature_encoder_runtime
from .session import SessionReceipt, load_runtime_receipt
from .session.feature_cache_serving import validate_strict_feature_cache_serving


def _load_pinned_artifact(
    path: Path, *, sha256: str, kind: str, label: str
) -> Mapping[str, object]:
    try:
        document = json.loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PreparationError(f"cannot read {label}: {error}") from error
    inputs = document.get("inputs") if isinstance(document, Mapping) else None
    if not isinstance(inputs, Mapping):
        raise PreparationError(f"{label} inputs are invalid")
    output = load_artifact(path, expected_sha256=sha256, kind=kind, inputs=inputs)
    if not isinstance(output, Mapping):
        raise PreparationError(f"{label} output is invalid")
    return output


def _feature_map(entries: object, label: str) -> dict[tuple[str, str], object]:
    if not isinstance(entries, list) or not entries:
        raise PreparationError(f"{label} feature descriptors are missing")
    result = {}
    for item in entries:
        if not isinstance(item, Mapping):
            raise PreparationError(f"{label} feature descriptor is invalid")
        identity = (item.get("audio_sha256"), item.get("cache_key"))
        if not all(isinstance(value, str) and value for value in identity):
            raise PreparationError(f"{label} feature identity is invalid")
        if identity in result:
            raise PreparationError(f"{label} feature identity is duplicated")
        chunks = item.get("chunks")
        if not isinstance(chunks, list) or not chunks:
            raise PreparationError(f"{label} feature chunks are missing")
        result[identity] = chunks
    return result


def build_configured_transport(
    values: Mapping[str, object],
    data_root: Path,
    *,
    repo_root: Path,
    session: SessionReceipt,
    runtime_receipt: Mapping[str, object],
    runtime_root: Path,
    transport_factory: Callable[..., object] | None = None,
):
    """Build one registered transport and enforce an opted-in prepared cache."""

    from .session.resource_guard import wrap_transport

    factory = transport_factory or TRANSPORTS.resolve(str(values["transport"]))
    configured = prepared_window_feature_cache(values)
    historical = {
        "session": session,
        "runtime_receipt": runtime_receipt,
        "runtime_root": runtime_root,
    }
    if configured is None:
        return wrap_transport(factory(values, data_root, **historical), values, data_root, session)

    server_env = values.get("server_env")
    server_args = values.get("server_args")
    if not isinstance(server_env, Mapping) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in server_env.items()
    ):
        raise PreparationError("prepared cache requires explicit string server_env")
    if not isinstance(server_args, (list, tuple)) or not all(
        isinstance(value, str) for value in server_args
    ):
        raise PreparationError("prepared cache requires explicit string server_args")
    cache_value = server_env.get("LLAMA_MTMD_FEAT_CACHE_DIR")
    if not isinstance(cache_value, str) or not cache_value:
        raise PreparationError(
            "prepared cache root must come from server_env.LLAMA_MTMD_FEAT_CACHE_DIR"
        )
    if "LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT" not in server_env:
        raise PreparationError(
            "prepared cache requires explicit LLAMA_MTMD_FEAT_CACHE_REQUIRE_HIT"
        )
    try:
        validate_strict_feature_cache_serving(
            role=session.role,
            extra_argv=server_args,
            extra_env=server_env,
            model_files=session.model_files,
        )
        actual_projector_flags = [
            value.replace("_", "-")
            for value in session.argv
            if isinstance(value, str) and "mmproj-offload" in value.replace("_", "-")
        ]
        if actual_projector_flags != ["--no-mmproj-offload"]:
            raise PreparationError(
                "prepared cache session must carry exactly --no-mmproj-offload"
            )
        root = Path(data_root).resolve(strict=True)
        cache_dir = Path(cache_value).resolve(strict=True)
        audit_pin = configured["audit"]
        provenance_pin = configured["provenance"]
        assert isinstance(audit_pin, Mapping) and isinstance(provenance_pin, Mapping)
        audit_path = _resolve_confined(
            root, audit_pin["relpath"], root, "prepared cache audit", strict=True
        )
        provenance_path = _resolve_confined(
            root,
            provenance_pin["relpath"],
            root,
            "prepared cache provenance",
            strict=True,
        )
    except (OSError, FrozenCoreError, AttributeError) as error:
        raise PreparationError(f"prepared cache configuration is invalid: {error}") from error

    configured_model_root = model_materialization_root(values)
    verified = verify_feature_encoder_runtime(
        repo_root=Path(repo_root),
        data_root=(
            Path(configured_model_root)
            if configured_model_root is not None
            else root
        ),
        runtime_root=Path(runtime_root),
        values=values,
        generation_receipt=runtime_receipt,
        receipt_loader=load_runtime_receipt,
    )
    if verified is None:
        raise PreparationError(
            "prepared cache requires feature_encoder_runtime_receipt"
        )
    audit = _load_pinned_artifact(
        audit_path,
        sha256=str(audit_pin["sha256"]),
        kind=FEATURE_CACHE_AUDIT_KIND,
        label="prepared cache audit",
    )
    provenance = _load_pinned_artifact(
        provenance_path,
        sha256=str(provenance_pin["sha256"]),
        kind=PROVENANCE_KIND,
        label="prepared cache provenance",
    )
    identity = verified.encoder_identity.as_json()
    if (
        provenance.get("schema") != PROVENANCE_SCHEMA
        or provenance.get("state") != PROVENANCE_STATE
    ):
        raise PreparationError("prepared cache provenance is not complete")
    if audit.get("encoder_identity") != identity or provenance.get(
        "encoder_identity"
    ) != identity:
        raise PreparationError("prepared cache encoder identities differ")
    if provenance.get("cache_audit_file_sha256") != audit_pin["sha256"]:
        raise PreparationError("prepared cache provenance does not bind the audit")
    if audit.get("inventory_sha256") != provenance.get("inventory_sha256"):
        raise PreparationError("prepared cache inventory identities differ")
    if _feature_map(audit.get("entries"), "audit") != _feature_map(
        provenance.get("feature_outputs"), "provenance"
    ):
        raise PreparationError("prepared cache feature descriptors differ")

    guard = PreparedFeatureCacheGuard.from_artifact(
        artifact_path=audit_path,
        artifact_sha256=str(audit_pin["sha256"]),
        encoder_identity=verified.encoder_identity,
        expected_cache_dir=cache_dir,
        expected_n_embd=configured["expected_n_embd"],
        data_root=root,
    )
    return wrap_transport(factory(values, data_root, feature_cache_guard=guard, **historical),
                          values, data_root, session)
