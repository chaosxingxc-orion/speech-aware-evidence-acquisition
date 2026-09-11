"""Shared receipt-bound raw-audio encoding for verified window inventories."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable, Mapping

from .model import (
    inspect_legacy_cached_speech_feature_cache,
    legacy_audio_feature_cache_key,
)
from .model.slices import SliceRecord
from .preparation import PreparationError, canonical_bytes, digest, prepare_artifact
from .preparation_media_inventory import (
    SOURCE_MEDIA_FEATURE_INVENTORY_SCHEMA,
    source_media_encoding_sources,
)
from .preparation_windows import WINDOW_FEATURE_INVENTORY_SCHEMA

SCHEMA = "saea-window-feature-encoding-record-v1"
PARTIAL_SCHEMA = "saea-window-feature-encoding-partial-v1"
KIND = "window-feature-encoding-v1"
DEFAULT_INSTRUCTION = "Observe the complete speech signal for deterministic feature preprocessing. Respond with OK."


def _sha(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise PreparationError(f"{label} must be lowercase SHA256")
    return value


def window_encoding_sources(
    inventory: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    """Use inventory.encoding_inputs, not path equality, as dedup authority."""
    if inventory.get("schema") == SOURCE_MEDIA_FEATURE_INVENTORY_SCHEMA:
        return source_media_encoding_sources(inventory)
    if inventory.get("schema") != WINDOW_FEATURE_INVENTORY_SCHEMA:
        raise PreparationError(
            "window encoding requires a verified window feature inventory"
        )
    request_sources = {}
    for batch in inventory.get("batches", []):
        if not isinstance(batch, Mapping) or not isinstance(batch.get("name"), str):
            raise PreparationError("window inventory batch is invalid")
        for request in batch.get("requests", []):
            if not isinstance(request, Mapping) or not isinstance(
                request.get("request_key"), str
            ):
                raise PreparationError("window inventory request is invalid")
            source = request.get("source_provenance")
            if not isinstance(source, Mapping):
                raise PreparationError("window inventory request provenance is invalid")
            reference = (batch["name"], request["request_key"])
            if reference in request_sources:
                raise PreparationError(
                    "window inventory repeats a batch/request reference"
                )
            request_sources[reference] = source
    result = {}
    covered = set()
    for entry in inventory.get("encoding_inputs", []):
        if not isinstance(entry, Mapping) or not isinstance(
            entry.get("requests"), list
        ):
            raise PreparationError("window inventory encoding input is invalid")
        audio = _sha(entry.get("audio_sha256"), "window source audio_sha256")
        refs = entry["requests"]
        if not refs or not isinstance(refs[0], Mapping):
            raise PreparationError(
                "window inventory encoding input has no request reference"
            )
        for ref in refs:
            if not isinstance(ref, Mapping):
                raise PreparationError("window inventory encoding reference is invalid")
            reference = (ref.get("batch"), ref.get("request_key"))
            source = request_sources.get(reference)
            if (
                source is None
                or _sha(source.get("sha256"), "window source audio_sha256") != audio
            ):
                raise PreparationError(
                    "window inventory encoding reference disagrees with source"
                )
            if reference in covered:
                raise PreparationError(
                    "window inventory repeats an encoding request reference"
                )
            covered.add(reference)
        source = request_sources[(refs[0].get("batch"), refs[0].get("request_key"))]
        if audio in result:
            raise PreparationError("window inventory repeats encoding input audio")
        result[audio] = source
    if not result:
        raise PreparationError("window inventory contains no encoding inputs")
    if covered != set(request_sources):
        raise PreparationError(
            "window inventory request coverage differs from encoding inputs"
        )
    return result


def _slice(source: Mapping[str, object]) -> SliceRecord:
    return SliceRecord(
        sample_id=source["sample_id"],
        parent_media_relpath=source["parent_media_relpath"],
        parent_sha256=source["parent_sha256"],
        start_seconds=source["start_seconds"],
        end_seconds=source["end_seconds"],
        audio_seconds=source["audio_seconds"],
        sample_rate_hz=source["sample_rate_hz"],
        media_relpath=source["media_relpath"],
        sha256=source["sha256"],
        bytes=source["bytes"],
        iteration=source["iteration"],
        preprocess=tuple(source["preprocess"]),
        pre_sha256=source["pre_sha256"],
    )


def _descriptors(inspection):
    return [
        {
            "ordinal": c.ordinal,
            "relative_filename": c.relative_filename,
            "file_sha256": c.file_sha256,
            "file_size": c.file_size,
            "n_tokens": c.n_tokens,
            "n_embd": c.n_embd,
        }
        for c in inspection.chunks
    ]


def _checked_media(root: Path, source: Mapping[str, object], audio_sha256: str):
    media = (root / str(source["media_relpath"])).resolve(strict=True)
    try:
        media.relative_to(root)
    except ValueError as error:
        raise PreparationError("window media path escapes data_root") from error
    content = media.read_bytes()
    if hashlib.sha256(content).hexdigest() != audio_sha256:
        raise PreparationError("window source bytes changed after inventory")
    return media, content, legacy_audio_feature_cache_key(content)


def validate_window_encoding_parameters(decoding_params, instruction):
    """Validate the registered preprocessing request before opening an attempt."""
    if (
        not isinstance(decoding_params, Mapping)
        or type(decoding_params.get("max_tokens")) is not int
        or decoding_params.get("max_tokens") != 1
    ):
        raise PreparationError(
            "window encoding decoding_params must set max_tokens to 1"
        )
    if not isinstance(instruction, str) or not instruction:
        raise PreparationError(
            "window encoding instruction must be non-empty English text"
        )


def encode_window_feature_cache(
    *,
    inventory: Mapping[str, object],
    data_root: Path,
    client: object,
    custody_guard: Callable[[], None],
    encoder_identity: Mapping[str, object],
    legacy_cache_dir: Path,
    expected_n_embd: int,
    output_path: Path,
    run_id: str,
    attempt_id: str,
    session_id: str,
    runtime_receipt_file_sha256: str,
    runtime_receipt_document_sha256: str,
    session_receipt_file_sha256: str,
    decoding_params: Mapping[str, object],
    instruction: str = DEFAULT_INSTRUCTION,
    warm_provenance: Mapping[str, Mapping[str, object]] | None = None,
):
    """Encode every unique exact input once; caller owns gate, service and lease."""
    root = Path(data_root).resolve(strict=True)
    cache = Path(legacy_cache_dir).resolve(strict=True)
    if not cache.is_dir() or not callable(custody_guard):
        raise PreparationError(
            "window encoding requires an existing cache and custody guard"
        )
    validate_window_encoding_parameters(decoding_params, instruction)
    identity = dict(encoder_identity)
    if identity != inventory.get("encoder_identity"):
        raise PreparationError(
            "encoder identity must equal the verified inventory identity"
        )
    for label, value in (
        ("runtime receipt file", runtime_receipt_file_sha256),
        ("runtime receipt document", runtime_receipt_document_sha256),
        ("session receipt file", session_receipt_file_sha256),
    ):
        _sha(value, label)
    sources = window_encoding_sources(inventory)
    inventory_sha256 = digest(inventory)
    warm = warm_provenance or {}
    inputs = {
        "inventory_sha256": inventory_sha256,
        "encoder_identity": identity,
        "legacy_cache_dir": str(cache),
        "expected_n_embd": expected_n_embd,
        "run_id": run_id,
        "attempt_id": attempt_id,
        "session_id": session_id,
        "runtime_receipt_file_sha256": runtime_receipt_file_sha256,
        "runtime_receipt_document_sha256": runtime_receipt_document_sha256,
        "session_receipt_file_sha256": session_receipt_file_sha256,
        "instruction": instruction,
        "decoding_params": dict(decoding_params),
    }
    if warm:
        inputs["warm_provenance_sha256"] = digest(warm)
    # Generic prepare_artifact may return an existing encoder artifact without
    # running its producer. Recheck live source bytes and validated cache chunks
    # before allowing that warm return.
    if Path(output_path).exists():
        # Reuse is terminal for this supplied client too. Never leave its trace
        # sink open, and never fall through to fresh encoding if the artifact
        # disappears during validation.
        def refuse_missing_artifact():
            raise PreparationError(
                "prepared encoding artifact disappeared during reuse"
            )

        try:
            try:
                prior_output = json.loads(
                    Path(output_path).read_text(encoding="utf-8")
                )["output"]
                prior_features = {
                    (item["audio_sha256"], item["cache_key"]): item["chunks"]
                    for item in prior_output["feature_outputs"]
                }
            except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
                raise PreparationError(
                    "prepared encoding artifact lacks feature output descriptors"
                ) from error
            for audio, source in sources.items():
                media, _content, key = _checked_media(root, source, audio)
                if not tuple(cache.glob(f"{key}_o*.feat")):
                    raise PreparationError(
                        "prepared encoding cache is missing before warm reuse"
                    )
                checked = inspect_legacy_cached_speech_feature_cache(
                    audio_path=media,
                    legacy_cache_dir=cache,
                    expected_n_embd=expected_n_embd,
                )
                if checked.audio_sha256 != audio or checked.cache_key != key:
                    raise PreparationError(
                        "prepared encoding cache differs from current source"
                    )
                if prior_features.get((audio, key)) != _descriptors(checked):
                    raise PreparationError(
                        "prepared encoding cache descriptors changed"
                    )
            return prepare_artifact(
                Path(output_path),
                kind=KIND,
                inputs=inputs,
                producer=refuse_missing_artifact,
                contact_class="encoder",
            )
        finally:
            if client is not None:
                client.close()

    if client is None:
        raise PreparationError("a cold encoding artifact requires an authorized client")

    client_close_started = False
    closed_receipt = None

    def close_client():
        nonlocal client_close_started, closed_receipt
        if not client_close_started:
            client_close_started = True
            closed_receipt = client.close()
        return closed_receipt or {}

    def produce():
        entries = []
        feature_outputs = []
        fresh = []
        closed = None
        active = None
        try:
            for audio, source in sorted(sources.items()):
                media, content, key = _checked_media(root, source, audio)
                prior = warm.get(audio)
                if tuple(cache.glob(f"{key}_o*.feat")) and prior is None:
                    raise PreparationError(
                        "unproven existing legacy cache entry refuses before encoder contact"
                    )
                if prior is None:
                    fresh.append((audio, source))
                    continue
                required = {
                    "audio_sha256",
                    "cache_key",
                    "encoder_identity",
                    "source_contact_id",
                    "source_provenance_receipt_sha256",
                }
                if (
                    not required <= set(prior)
                    or prior["audio_sha256"] != audio
                    or prior["cache_key"] != key
                    or prior["encoder_identity"] != identity
                ):
                    raise PreparationError(
                        "warm provenance does not bind this audio, cache key and encoder identity"
                    )
                _sha(
                    prior["source_provenance_receipt_sha256"], "warm provenance receipt"
                )
                if (
                    not isinstance(prior["source_contact_id"], str)
                    or not prior["source_contact_id"]
                ):
                    raise PreparationError("warm provenance source contact is missing")
                checked = inspect_legacy_cached_speech_feature_cache(
                    audio_path=media,
                    legacy_cache_dir=cache,
                    expected_n_embd=expected_n_embd,
                )
                if checked.audio_sha256 != audio or checked.cache_key != key:
                    raise PreparationError(
                        "warm cache inspection does not match inventory audio and key"
                    )
                feature_outputs.append(
                    {
                        "audio_sha256": audio,
                        "cache_key": key,
                        "chunks": _descriptors(checked),
                    }
                )
                entries.append(
                    {
                        "audio_sha256": audio,
                        "cache_key": key,
                        "status": "verified-warm-reuse",
                        "success": True,
                        "current_contact_id": None,
                        "source_contact_id": prior["source_contact_id"],
                        "source_provenance_receipt_sha256": prior[
                            "source_provenance_receipt_sha256"
                        ],
                    }
                )
            for audio, source in fresh:
                # Re-read immediately before each request; earlier contacts cannot stale it.
                media, _content, key = _checked_media(root, source, audio)
                active = (audio, key)
                custody_guard()
                if source.get("source_kind") != "registered-media":
                    client.register_slice(_slice(source))
                client.complete(
                    (
                        {"role": "system", "content": instruction},
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_audio",
                                    "media_relpath": source["media_relpath"],
                                }
                            ],
                        },
                    ),
                    decoding_params=dict(decoding_params),
                )
                checked = inspect_legacy_cached_speech_feature_cache(
                    audio_path=media,
                    legacy_cache_dir=cache,
                    expected_n_embd=expected_n_embd,
                )
                if checked.audio_sha256 != audio or checked.cache_key != key:
                    raise PreparationError(
                        "produced cache inspection does not match registered audio and key"
                    )
                contact = getattr(tuple(client.timings)[-1], "request_id", None)
                if not isinstance(contact, str) or not contact:
                    raise PreparationError(
                        "encoder client did not expose a contact request_id"
                    )
                feature_outputs.append(
                    {
                        "audio_sha256": audio,
                        "cache_key": key,
                        "chunks": _descriptors(checked),
                    }
                )
                entries.append(
                    {
                        "audio_sha256": audio,
                        "cache_key": key,
                        "status": "encoded",
                        "success": True,
                        "current_contact_id": contact,
                        "source_contact_id": None,
                        "source_provenance_receipt_sha256": None,
                    }
                )
            closed = close_client()
            charged = sum(entry["current_contact_id"] is not None for entry in entries)
            if (
                not isinstance(closed.get("cost"), Mapping)
                or closed["cost"].get("calls_used") != charged
            ):
                raise PreparationError(
                    "encoder cost.calls_used must equal successful current contacts"
                )
            return {
                "schema": SCHEMA,
                "study": "speech-aware-evidence-acquisition",
                "run_id": run_id,
                "attempt_id": attempt_id,
                "session_id": session_id,
                "runtime_receipt_file_sha256": runtime_receipt_file_sha256,
                "runtime_receipt_document_sha256": runtime_receipt_document_sha256,
                "session_receipt_file_sha256": session_receipt_file_sha256,
                "inventory_sha256": inventory_sha256,
                "encoder_identity": identity,
                "trace_manifest_hash": closed.get("trace_manifest_hash"),
                "cost": closed.get("cost"),
                "current_contact_count": charged,
                "entries": entries,
                "feature_outputs": feature_outputs,
            }
        except BaseException as error:
            if closed is None:
                try:
                    closed = close_client()
                except BaseException:
                    closed = {}
            attempted_id = getattr(client, "last_attempted_request_id", None)
            if (
                isinstance(attempted_id, str)
                and attempted_id
                and attempted_id
                not in {entry["current_contact_id"] for entry in entries}
            ):
                entries.append(
                    {
                        "audio_sha256": active[0] if active else None,
                        "cache_key": active[1] if active else None,
                        "status": "failed",
                        "success": False,
                        "current_contact_id": attempted_id,
                        "source_contact_id": None,
                        "source_provenance_receipt_sha256": None,
                    }
                )
            partial = {
                "schema": PARTIAL_SCHEMA,
                "state": "failed",
                "study": "speech-aware-evidence-acquisition",
                "run_id": run_id,
                "attempt_id": attempt_id,
                "session_id": session_id,
                "runtime_receipt_file_sha256": runtime_receipt_file_sha256,
                "runtime_receipt_document_sha256": runtime_receipt_document_sha256,
                "session_receipt_file_sha256": session_receipt_file_sha256,
                "inventory_sha256": inventory_sha256,
                "encoder_identity": identity,
                "current_contact_count": sum(
                    entry["status"] == "encoded" for entry in entries
                ),
                "entries": entries,
                "trace_manifest_hash": closed.get("trace_manifest_hash"),
                "cost": closed.get("cost"),
                "error_type": type(error).__name__,
            }
            try:
                with (
                    Path(output_path)
                    .with_name(Path(output_path).name + ".partial.json")
                    .open("xb") as stream
                ):
                    stream.write(canonical_bytes(partial))
            except FileExistsError:
                pass
            raise

    try:
        return prepare_artifact(
            Path(output_path),
            kind=KIND,
            inputs=inputs,
            producer=produce,
            contact_class="encoder",
        )
    finally:
        # The artifact lock can refuse before produce() has taken ownership.
        close_client()
