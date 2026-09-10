"""Actual independent speech windows for model-free request preparation.

Use the live cutter, lineage registry, and per-window instruction factory.
No adapter request, response, acceptance, scoring, or model trace is produced.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Mapping, Sequence

if TYPE_CHECKING:
    from .driver.run import EvidenceBinding

from .model import FrozenCoreError
from .model.paths import _normalized_relative_path, _resolve_confined
from .preparation import (
    PreparationError,
    canonical_bytes,
    digest,
    hash_stable_file as _sha256_file,
    prepare_artifact,
)

WINDOW_FEATURE_INVENTORY_SCHEMA = "saea-window-feature-inventory-v1"
WINDOW_FEATURE_INVENTORY_KIND = "exact-window-feature-inventory-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_BUILD_COMMIT = re.compile(r"[0-9a-f]{40}")
_BATCH_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_REQUEST_KEY = re.compile(r"(.+)#w([0-9]+)")
_SOURCE_KEYS = {
    "sample_id",
    "parent_media_relpath",
    "parent_sha256",
    "start_seconds",
    "end_seconds",
    "audio_seconds",
    "sample_rate_hz",
    "media_relpath",
    "sha256",
    "bytes",
    "iteration",
    "preprocess",
    "pre_sha256",
}


@dataclass(frozen=True)
class WindowFeatureEncoderIdentity:
    """The four pinned identities shared by every input in one inventory."""

    runtime_receipt_sha256: str
    build_commit: str
    decoder_gguf_sha256: str
    mmproj_sha256: str

    def as_json(self) -> dict[str, str]:
        for name, value in (
            ("runtime_receipt_sha256", self.runtime_receipt_sha256),
            ("decoder_gguf_sha256", self.decoder_gguf_sha256),
            ("mmproj_sha256", self.mmproj_sha256),
        ):
            if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
                raise PreparationError(f"window encoder {name} must be a lowercase SHA256")
        if (
            not isinstance(self.build_commit, str)
            or _BUILD_COMMIT.fullmatch(self.build_commit) is None
        ):
            raise PreparationError(
                "window encoder build_commit must be a lowercase 40-hex Git commit"
            )
        return {
            "runtime_receipt_sha256": self.runtime_receipt_sha256,
            "build_commit": self.build_commit,
            "decoder_gguf_sha256": self.decoder_gguf_sha256,
            "mmproj_sha256": self.mmproj_sha256,
        }


@dataclass(frozen=True)
class WindowRequestBatch:
    payloads: tuple[Mapping[str, object], ...]
    request_keys: tuple[str, ...]
    source_bindings: tuple[Mapping[str, object], ...]
    evidence_binding: EvidenceBinding | None = None

    def bound_requests(
        self,
    ) -> tuple[tuple[str, Mapping[str, object], Mapping[str, object]], ...]:
        """Return each request with its source, refusing ambiguous batch identity."""

        if not (
            len(self.payloads) == len(self.request_keys) == len(self.source_bindings)
        ):
            raise PreparationError(
                "window batch payload, request-key and source counts differ"
            )
        if not self.payloads:
            raise PreparationError("window batch is empty")
        if any(not isinstance(key, str) or not key for key in self.request_keys):
            raise PreparationError("window batch request key must be non-empty")
        if len(set(self.request_keys)) != len(self.request_keys):
            raise PreparationError("window batch repeats a request key")
        result = []
        for request_key, payload, source in zip(
            self.request_keys, self.payloads, self.source_bindings, strict=True
        ):
            if not isinstance(payload, Mapping) or not isinstance(source, Mapping):
                raise PreparationError("window batch payload and source must be mappings")
            result.append((request_key, payload, source))
        return tuple(result)

    def request_key(self, payload):
        identity = (payload["sample_id"], payload["media_relpath"])
        for key, source in zip(self.request_keys, self.source_bindings, strict=True):
            if identity == (source["sample_id"], source["media_relpath"]):
                return key
        raise PreparationError("request does not belong to this window batch")


def _read_bytes(
    path: Path, label: str
) -> tuple[bytes, str, tuple[int, int, int]]:
    try:
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
    except OSError as error:
        raise PreparationError(f"cannot read {label} {path}: {error}") from error
    if (
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise PreparationError(f"{label} changed while it was read")
    fingerprint = (after.st_ino, after.st_size, after.st_mtime_ns)
    return content, hashlib.sha256(content).hexdigest(), fingerprint


def _confined_file(data_root: Path, value: object, label: str) -> tuple[str, Path]:
    try:
        relative = _normalized_relative_path(value, label)
        path = _resolve_confined(data_root, relative, data_root, label, strict=True)
    except FrozenCoreError as error:
        raise PreparationError(str(error)) from error
    if not path.is_file():
        raise PreparationError(f"{label} is not a file: {path}")
    return relative, path


def _positive_int(value: object, label: str, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise PreparationError(f"window source {label} must be an integer >= {minimum}")
    return value


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PreparationError(f"window source {label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise PreparationError(f"window source {label} must be a finite number")
    return result


def _normalized_source(
    *,
    batch_name: str,
    request_key: str,
    payload: Mapping[str, object],
    source: Mapping[str, object],
    data_root: Path,
    parent_cache: dict[Path, tuple[int, str, tuple[int, int, int]]],
    observed_files: dict[Path, tuple[int, int, int]],
) -> tuple[dict[str, object], bytes, Path]:
    if set(source) != _SOURCE_KEYS:
        raise PreparationError(
            f"window source for {batch_name!r}/{request_key!r} must have exact keys "
            f"{sorted(_SOURCE_KEYS)}"
        )
    sample_id = source["sample_id"]
    if not isinstance(sample_id, str) or not sample_id:
        raise PreparationError("window source sample_id must be non-empty")
    match = _REQUEST_KEY.fullmatch(request_key)
    if match is None or match.group(1) != sample_id or int(match.group(2)) < 1:
        raise PreparationError("window request key does not bind its parent sample")
    if payload.get("sample_id") != sample_id:
        raise PreparationError("window payload and source sample ids differ")

    media_relpath, media_path = _confined_file(
        data_root, source["media_relpath"], "window source media path"
    )
    if payload.get("media_relpath") != media_relpath:
        raise PreparationError("window payload and source media paths differ")
    parent_relpath, parent_path = _confined_file(
        data_root, source["parent_media_relpath"], "window parent media path"
    )
    audio_bytes, source_sha256, source_fingerprint = _read_bytes(
        media_path, "window source media"
    )
    observed_files[media_path] = source_fingerprint
    source_size = len(audio_bytes)
    if parent_path in parent_cache:
        parent_size, parent_sha256, fingerprint = parent_cache[parent_path]
        try:
            current = parent_path.stat()
        except OSError as error:
            raise PreparationError(
                f"cannot restat window parent media {parent_path}: {error}"
            ) from error
        if (current.st_ino, current.st_size, current.st_mtime_ns) != fingerprint:
            raise PreparationError("window parent media changed during inventory")
    else:
        parent_size, parent_sha256, fingerprint = _sha256_file(
            parent_path, "window parent media"
        )
        parent_cache[parent_path] = (parent_size, parent_sha256, fingerprint)
    observed_files[parent_path] = fingerprint
    for label, claimed, measured in (
        ("sha256", source["sha256"], source_sha256),
        ("parent_sha256", source["parent_sha256"], parent_sha256),
    ):
        if not isinstance(claimed, str) or _SHA256.fullmatch(claimed) is None:
            raise PreparationError(f"window source {label} must be a lowercase SHA256")
        if claimed != measured:
            raise PreparationError(f"window source {label} differs from actual bytes")
    _positive_int(source["bytes"], "bytes")
    if source["bytes"] != source_size:
        raise PreparationError("window source byte count differs from actual bytes")

    start = _finite_number(source["start_seconds"], "start_seconds")
    end = _finite_number(source["end_seconds"], "end_seconds")
    seconds = _finite_number(source["audio_seconds"], "audio_seconds")
    if start < 0 or end <= start or seconds <= 0 or abs((end - start) - seconds) > 1e-3:
        raise PreparationError("window source time bounds are inconsistent")
    sample_rate = _positive_int(source["sample_rate_hz"], "sample_rate_hz")
    iteration = _positive_int(source["iteration"], "iteration", allow_zero=True)
    if int(match.group(2)) != iteration + 1:
        raise PreparationError(
            "window request key suffix disagrees with source iteration"
        )
    payload_seconds = _finite_number(
        payload.get("audio_seconds"), "payload audio_seconds"
    )
    if abs(payload_seconds - seconds) > 1e-6:
        raise PreparationError(
            "window payload audio_seconds disagrees with source audio_seconds"
        )
    payload_rate = payload.get("sample_rate_hz")
    if (
        isinstance(payload_rate, bool)
        or not isinstance(payload_rate, int)
        or payload_rate != sample_rate
    ):
        raise PreparationError(
            "window payload sample_rate_hz disagrees with source sample_rate_hz"
        )
    preprocess = source["preprocess"]
    if (
        not isinstance(preprocess, (list, tuple))
        or any(not isinstance(item, str) or not item for item in preprocess)
    ):
        raise PreparationError("window source preprocess must be a list of names")
    pre_sha256 = source["pre_sha256"]
    if pre_sha256 is not None and (
        not isinstance(pre_sha256, str) or _SHA256.fullmatch(pre_sha256) is None
    ):
        raise PreparationError("window source pre_sha256 must be null or lowercase SHA256")

    provenance = {
        "sample_id": sample_id,
        "parent_media_relpath": parent_relpath,
        "parent_sha256": parent_sha256,
        "parent_bytes": parent_size,
        "start_seconds": start,
        "end_seconds": end,
        "audio_seconds": seconds,
        "sample_rate_hz": sample_rate,
        "media_relpath": media_relpath,
        "sha256": source_sha256,
        "bytes": source_size,
        "iteration": iteration,
        "preprocess": list(preprocess),
        "pre_sha256": pre_sha256,
    }
    # Round-trip now so caller-provided Mapping subclasses and numeric types
    # cannot create a different persisted identity later.
    normalized = json.loads(canonical_bytes(provenance))
    return normalized, audio_bytes, media_path


def build_window_feature_inventory(
    *,
    batches: Mapping[str, WindowRequestBatch],
    data_root: Path,
    encoder_identity: WindowFeatureEncoderIdentity,
) -> dict[str, object]:
    """Inventory exact bytes to encode; never read or create neural features."""

    if not isinstance(batches, Mapping) or not batches:
        raise PreparationError("window feature inventory requires named batches")
    root = Path(data_root)
    if not root.is_dir():
        raise PreparationError("window feature inventory data_root is unavailable")
    identity = encoder_identity.as_json()
    if any(
        not isinstance(batch_name, str)
        or _BATCH_NAME.fullmatch(batch_name) is None
        for batch_name in batches
    ):
        raise PreparationError("window feature batch name is not a plain identifier")
    batch_rows: list[dict[str, object]] = []
    unique: dict[str, dict[str, object]] = {}
    unique_paths: dict[str, Path] = {}
    parent_cache: dict[Path, tuple[int, str, tuple[int, int, int]]] = {}
    observed_files: dict[Path, tuple[int, int, int]] = {}
    request_count = 0
    for batch_name in sorted(batches):
        batch = batches[batch_name]
        if not isinstance(batch, WindowRequestBatch):
            raise PreparationError("window feature inventory requires WindowRequestBatch values")
        requests = []
        for request_key, payload, source in batch.bound_requests():
            provenance, audio_bytes, media_path = _normalized_source(
                batch_name=batch_name,
                request_key=request_key,
                payload=payload,
                source=source,
                data_root=root,
                parent_cache=parent_cache,
                observed_files=observed_files,
            )
            audio_sha256 = str(provenance["sha256"])
            encoding_key = digest(
                {"encoder_identity": identity, "audio_sha256": audio_sha256}
            )
            reference = {"batch": batch_name, "request_key": request_key}
            if audio_sha256 in unique:
                first_bytes, first_sha256, first_fingerprint = _read_bytes(
                    unique_paths[audio_sha256], "deduplicated window source media"
                )
                observed_files[unique_paths[audio_sha256]] = first_fingerprint
                if first_sha256 != audio_sha256 or first_bytes != audio_bytes:
                    raise PreparationError("window audio SHA256 collision")
                unique[audio_sha256]["requests"].append(reference)
            else:
                unique_paths[audio_sha256] = media_path
                unique[audio_sha256] = {
                    "audio_sha256": audio_sha256,
                    "audio_byte_count": len(audio_bytes),
                    "encoding_key_sha256": encoding_key,
                    "requests": [reference],
                }
            requests.append(
                {
                    "request_key": request_key,
                    "payload_sha256": digest(payload),
                    "encoding_key_sha256": encoding_key,
                    "source_provenance": provenance,
                }
            )
            request_count += 1
        batch_rows.append({"name": batch_name, "requests": requests})
    for path, fingerprint in observed_files.items():
        try:
            current = path.stat()
        except OSError as error:
            raise PreparationError(
                f"cannot restat inventoried window source {path}: {error}"
            ) from error
        if (current.st_ino, current.st_size, current.st_mtime_ns) != fingerprint:
            raise PreparationError("window source changed during inventory")
    return {
        "schema": WINDOW_FEATURE_INVENTORY_SCHEMA,
        "state": "inputs-verified-features-not-materialized",
        "encoder_identity": identity,
        "request_count": request_count,
        "unique_audio_count": len(unique),
        "batches": batch_rows,
        "encoding_inputs": [unique[key] for key in sorted(unique)],
    }


def prepare_window_feature_inventory(
    path: Path,
    *,
    batches: Mapping[str, WindowRequestBatch],
    data_root: Path,
    encoder_identity: WindowFeatureEncoderIdentity,
) -> dict[str, object]:
    """Persist one immutable model-free inventory of exact encoding inputs."""

    output = build_window_feature_inventory(
        batches=batches, data_root=data_root, encoder_identity=encoder_identity
    )
    inputs = {
        "encoder_identity": output["encoder_identity"],
        "window_sources_sha256": digest(output["batches"]),
    }
    return prepare_artifact(
        path,
        kind=WINDOW_FEATURE_INVENTORY_KIND,
        inputs=inputs,
        producer=lambda: output,
        contact_class="model-free",
    )


def materialize_window_requests(
    contexts: Sequence[object], *, expected_sample_ids: Sequence[str], hook_factory=None,
    evidence_binding: EvidenceBinding | None = None,
    max_workers: int = 1,
) -> WindowRequestBatch:
    """Prepare the entire verified call roster without opening a model client."""
    from ..reproduction import obs_loop
    from ..reproduction.repair_loop import build_repair_window_hook

    ids = [ctx.sample.sample_id for ctx in contexts]
    if (
        not ids
        or len(ids) != len(set(ids))
        or len(expected_sample_ids) != len(set(expected_sample_ids))
        or set(ids) != set(expected_sample_ids)
    ):
        raise PreparationError("window fit requires the complete unique call roster")
    if isinstance(max_workers, bool) or not isinstance(max_workers, int) or not 1 <= max_workers <= 20:
        raise PreparationError("window preparation max_workers must be between 1 and 20")

    def materialize_call(ctx):
        payloads, keys, sources = [], [], []
        values = ctx.extras["config_values"]
        cfg = obs_loop.ObsLoopConfig.from_values(values, Path(ctx.extras["repo_root"]))
        if (
            cfg.boundary_mode != "fixed"
            or cfg.condition_tail_chars != 0
            or cfg.vad_trim_min_seconds != 0
            or cfg.batch_slices <= 1
        ):
            raise PreparationError(
                "window fit requires independent fixed parallel windows"
            )
        root = Path(ctx.extras["data_root"])
        sample = ctx.sample
        relative = _normalized_relative_path(sample.media_relpath, "window parent")
        parent = _resolve_confined(root, relative, root, "window parent", strict=True)
        rate = obs_loop.SLICE_SAMPLE_RATE_HZ
        pcm = obs_loop.decode_parent_pcm(parent, rate)
        if not len(pcm):
            raise PreparationError("window parent decoded to zero samples")
        hook = (hook_factory or build_repair_window_hook)(ctx, cfg, root, sample)
        registry = ctx.extras["slice_registry"]
        windows, records = obs_loop.materialize_fixed_windows(
            cfg,
            registry,
            root,
            sample,
            rate,
            pcm,
            len(pcm) / rate,
            obs_loop._sha256_file(parent),
        )
        evidence = ctx.evidence if ctx.arm != "bare-core" else None
        allow_empty = (
            evidence is not None
            and not evidence
            and values.get("evidence_source") == "derived-candidates"
        )
        for window, record in zip(windows, records, strict=True):
            request_id, factory = obs_loop.window_request_factory(
                ctx,
                window,
                sample=sample,
                rate=rate,
                evidence=evidence,
                allow_empty_evidence=allow_empty,
                window_hook=hook,
                slot=0 if ctx.decoding_params.get("id_slot") == "per-sample" else None,
            )
            payloads.append(factory(request_id))
            keys.append(f"{sample.sample_id}#w{record.iteration + 1:04d}")
            sources.append(record.trace_view())
        return payloads, keys, sources

    if max_workers == 1:
        batches = [materialize_call(ctx) for ctx in contexts]
    else:
        from concurrent.futures import ThreadPoolExecutor
        # Each unique call owns its slice paths and hook. Executor.map keeps
        # the frozen roster order regardless of CPU completion order.
        with ThreadPoolExecutor(max_workers=min(max_workers, len(contexts))) as pool:
            batches = list(pool.map(materialize_call, contexts))
    payloads = tuple(row for batch in batches for row in batch[0])
    keys = tuple(row for batch in batches for row in batch[1])
    sources = tuple(row for batch in batches for row in batch[2])
    if not payloads:
        raise PreparationError("window fit materialized no requests")
    for ctx in contexts:
        prepared = ctx.extras.get("window_feature_packets")
        if prepared is not None:
            expected = {
                key for key, binding in prepared.by_request_key.items()
                if binding.sources[0]["source_provenance"]["sample_id"] == ctx.sample.sample_id
            }
            actual = {key for key, source in zip(keys, sources, strict=True)
                      if source["sample_id"] == ctx.sample.sample_id}
            if expected != actual:
                raise PreparationError("prepared window packets do not exactly cover selected requests")
    return WindowRequestBatch(payloads, keys, sources, evidence_binding=evidence_binding)
