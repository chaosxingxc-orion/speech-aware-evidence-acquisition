"""Client-side validation for a hash-pinned raw-audio cache audit.

The guard verifies the exact raw audio and cache files used by an actual
rendered request. It is a model-free input rail and does not establish encoder
provenance or server-side cache-hit qualification.
"""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from ..preparation import PreparationError, load_artifact
from ..preparation_windows import WindowFeatureEncoderIdentity
from . import FrozenCoreError
from .speech_features import inspect_legacy_cached_speech_feature_cache
from .paths import _canonical_window_route_path, _normalized_relative_path


class PreparedFeatureCacheError(FrozenCoreError):
    """Refuse an unregistered or changed raw-audio cache request."""


@dataclass(frozen=True)
class _RegisteredRequest:
    audio_path: Path = field(compare=False)
    audio_sha256: str
    source: Mapping[str, object]
    cache_key: str
    chunks: tuple[Mapping[str, object], ...]


@dataclass(frozen=True)
class PreparedFeatureCacheGuard:
    """Validate one actual raw-audio request against a prepared audit."""

    data_root: Path
    cache_dir: Path
    expected_n_embd: int
    requests: Mapping[tuple[object, ...], _RegisteredRequest]

    @staticmethod
    def _request_identity(
        sample_id: object, media_relpath: object, duration: object, rate: object
    ) -> tuple[object, ...]:
        return (
            sample_id,
            _canonical_window_route_path(media_relpath),
            duration,
            rate,
        )

    @classmethod
    def from_artifact(
        cls,
        *,
        artifact_path: Path,
        artifact_sha256: str,
        encoder_identity: WindowFeatureEncoderIdentity,
        expected_cache_dir: Path,
        expected_n_embd: int,
        data_root: Path,
    ) -> "PreparedFeatureCacheGuard":
        try:
            document = json.loads(Path(artifact_path).read_bytes())
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise PreparedFeatureCacheError(
                f"cannot read feature-cache audit artifact: {error}"
            ) from error
        if not isinstance(document, Mapping) or "inputs" not in document:
            raise PreparedFeatureCacheError("feature-cache audit artifact inputs are missing")
        inputs = document["inputs"]
        if not isinstance(inputs, Mapping):
            raise PreparedFeatureCacheError("feature-cache audit artifact inputs are invalid")
        try:
            output = load_artifact(
                Path(artifact_path),
                expected_sha256=artifact_sha256,
                kind="window-feature-cache-audit-v1",
                inputs=inputs,
            )
        except PreparationError as error:
            raise PreparedFeatureCacheError(
                f"feature-cache audit artifact is invalid: {error}"
            ) from error
        if not isinstance(output, Mapping):
            raise PreparedFeatureCacheError("feature-cache audit output is invalid")
        if output.get("state") != "cache-files-verified-runtime-unqualified":
            raise PreparedFeatureCacheError("feature-cache audit state is not runtime-unqualified")
        identity = encoder_identity.as_json()
        if output.get("encoder_identity") != identity:
            raise PreparedFeatureCacheError("feature-cache audit encoder identity mismatch")
        try:
            cache_dir = Path(expected_cache_dir).resolve(strict=True)
            root = Path(data_root).resolve(strict=True)
        except OSError as error:
            raise PreparedFeatureCacheError(f"guard root is unavailable: {error}") from error
        if not cache_dir.is_dir() or not root.is_dir():
            raise PreparedFeatureCacheError("guard roots must be directories")
        if output.get("legacy_cache_dir") != str(cache_dir):
            raise PreparedFeatureCacheError("feature-cache audit cache root mismatch")
        if output.get("expected_n_embd") != expected_n_embd:
            raise PreparedFeatureCacheError("feature-cache audit embedding width mismatch")
        inventory = output.get("inventory")
        entries = output.get("entries")
        if not isinstance(inventory, Mapping) or not isinstance(entries, list):
            raise PreparedFeatureCacheError("feature-cache audit coverage is invalid")
        batches = inventory.get("batches")
        if not isinstance(batches, list):
            raise PreparedFeatureCacheError("feature-cache audit inventory is invalid")
        sources: dict[tuple[str, str], Mapping[str, object]] = {}
        for batch in batches:
            if not isinstance(batch, Mapping) or not isinstance(batch.get("name"), str):
                raise PreparedFeatureCacheError("feature-cache audit batch is invalid")
            for request in batch.get("requests", []):
                if not isinstance(request, Mapping):
                    raise PreparedFeatureCacheError("feature-cache audit request is invalid")
                request_key = request.get("request_key")
                source = request.get("source_provenance")
                if not isinstance(request_key, str) or not isinstance(source, Mapping):
                    raise PreparedFeatureCacheError("feature-cache audit source binding is invalid")
                sources[(batch["name"], request_key)] = source

        registered: dict[tuple[object, ...], _RegisteredRequest] = {}
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise PreparedFeatureCacheError("feature-cache audit entry is invalid")
            audio_sha256 = entry.get("audio_sha256")
            cache_key = entry.get("cache_key")
            chunks = entry.get("chunks")
            refs = entry.get("requests")
            if (
                not isinstance(audio_sha256, str)
                or not isinstance(cache_key, str)
                or not isinstance(chunks, list)
                or not isinstance(refs, list)
            ):
                raise PreparedFeatureCacheError("feature-cache audit entry fields are invalid")
            for ref in refs:
                if not isinstance(ref, Mapping):
                    raise PreparedFeatureCacheError("feature-cache audit request reference is invalid")
                source = sources.get((ref.get("batch"), ref.get("request_key")))
                if source is None:
                    raise PreparedFeatureCacheError("feature-cache audit request reference is unbound")
                sample_id = source.get("sample_id")
                media_relpath = source.get("media_relpath")
                duration = source.get("audio_seconds")
                rate = source.get("sample_rate_hz")
                if not isinstance(sample_id, str) or not isinstance(media_relpath, str):
                    raise PreparedFeatureCacheError("feature-cache audit source identity is invalid")
                identity_key = cls._request_identity(
                    sample_id, media_relpath, duration, rate
                )
                source = {
                    **source,
                    "media_relpath": _canonical_window_route_path(media_relpath),
                }
                try:
                    audio_path = (root / _normalized_relative_path(
                        media_relpath, "feature-cache audit media_relpath"
                    )).resolve(strict=True)
                    audio_path.relative_to(root)
                except (OSError, ValueError) as error:
                    raise PreparedFeatureCacheError(
                        "feature-cache audit media path escapes data_root"
                    ) from error
                candidate = _RegisteredRequest(
                    audio_path=audio_path,
                    audio_sha256=audio_sha256,
                    source=source,
                    cache_key=cache_key,
                    chunks=tuple(chunks),
                )
                prior = registered.get(identity_key)
                if prior is not None and prior != candidate:
                    raise PreparedFeatureCacheError(
                        "feature-cache audit has ambiguous request identity"
                    )
                registered[identity_key] = candidate
        return cls(
            data_root=root,
            cache_dir=cache_dir,
            expected_n_embd=expected_n_embd,
            requests=registered,
        )

    def validate(self, payload: Mapping[str, object], body: Mapping[str, object]) -> None:
        """Refuse unless body audio and cache files match the registered request."""

        if payload.get("query_source") == "speech_features":
            raise PreparedFeatureCacheError("raw-audio cache guard does not support feature packets")
        if not isinstance(payload, Mapping) or not isinstance(body, Mapping):
            raise PreparedFeatureCacheError("prepared cache guard requires mapping payload and body")
        sample_id = payload.get("sample_id")
        media_relpath = payload.get("media_relpath")
        duration = payload.get("audio_seconds")
        rate = payload.get("sample_rate_hz")
        if not isinstance(sample_id, str) or not isinstance(media_relpath, str):
            raise PreparedFeatureCacheError("raw-audio payload identity is incomplete")
        identity_key = self._request_identity(sample_id, media_relpath, duration, rate)
        registered = self.requests.get(identity_key)
        if registered is None:
            raise PreparedFeatureCacheError("raw-audio request is not registered in the cache audit")
        try:
            audio_path = (self.data_root / _normalized_relative_path(
                media_relpath, "transport media_relpath"
            )).resolve(strict=True)
            audio_path.relative_to(self.data_root)
            raw = audio_path.read_bytes()
        except (OSError, ValueError) as error:
            raise PreparedFeatureCacheError("raw-audio payload path is unavailable or escapes data_root") from error
        if hashlib.sha256(raw).hexdigest() != registered.audio_sha256:
            raise PreparedFeatureCacheError("raw-audio source SHA256 differs from the audit")

        audio_parts = []
        for message in body.get("messages", []):
            if not isinstance(message, Mapping):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            audio_parts.extend(
                part for part in content
                if isinstance(part, Mapping) and part.get("type") == "input_audio"
            )
        if len(audio_parts) != 1:
            raise PreparedFeatureCacheError(
                "raw-audio cache guard requires exactly one registered input_audio part"
            )
        wire_audio = audio_parts[0].get("input_audio")
        if not isinstance(wire_audio, Mapping) or not isinstance(wire_audio.get("data"), str):
            raise PreparedFeatureCacheError("rendered input_audio data is invalid")
        try:
            wire_bytes = base64.b64decode(wire_audio["data"], validate=True)
        except (ValueError, TypeError) as error:
            raise PreparedFeatureCacheError("rendered input_audio is not valid base64") from error
        if wire_bytes != raw:
            raise PreparedFeatureCacheError("rendered input_audio bytes differ from the registered audio")

        try:
            inspection = inspect_legacy_cached_speech_feature_cache(
                audio_path=audio_path,
                legacy_cache_dir=self.cache_dir,
                expected_n_embd=self.expected_n_embd,
            )
        except FrozenCoreError as error:
            raise PreparedFeatureCacheError(
                f"registered raw-audio cache is unavailable: {error}"
            ) from error
        actual_chunks = tuple(
            {
                "ordinal": chunk.ordinal,
                "relative_filename": chunk.relative_filename,
                "file_sha256": chunk.file_sha256,
                "file_size": chunk.file_size,
                "n_tokens": chunk.n_tokens,
                "n_embd": chunk.n_embd,
            }
            for chunk in inspection.chunks
        )
        if inspection.audio_sha256 != registered.audio_sha256:
            raise PreparedFeatureCacheError("cache inspection audio SHA256 differs from the audit")
        if inspection.cache_key != registered.cache_key:
            raise PreparedFeatureCacheError("cache inspection key differs from the audit")
        if actual_chunks != registered.chunks:
            raise PreparedFeatureCacheError(
                "cache chunks are missing, modified, or additional versus the audit"
            )
