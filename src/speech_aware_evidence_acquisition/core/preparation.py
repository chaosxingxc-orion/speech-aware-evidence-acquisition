"""Shared immutable preparation artifacts and actual-envelope token measurement.

Prepared bytes are local artifacts, never authorization for a model contact.
Receipt pins and per-cell readiness records are excluded from the input-config
digest to avoid self-reference; every model/request configuration remains bound. Endpoint access is supplied only by an
already-attested caller. Template/tokenizer and multimodal input-count routes
measure requests without generation.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

SCHEMA = "saea-prepared-artifact-v1"
_RECEIPT_KEYS = frozenset(
    {
        "prepared_phase_supply",
        "prepared_request_fit",
        "prompt_fit_receipt",
        "prompt_fit_receipt_sha256",
    }
)


class PreparationError(ValueError):
    """Refuse stale, incomplete, or incompatible prepared material."""


def hash_stable_file(
    path: Path, label: str
) -> tuple[int, str, tuple[int, int, int]]:
    """Hash one file and refuse if its identity changes during the read."""

    path = Path(path)
    try:
        before = path.stat()
    except OSError as error:
        raise PreparationError(f"cannot stat {label} {path}: {error}") from error
    measured = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                size += len(chunk)
                measured.update(chunk)
    except OSError as error:
        raise PreparationError(f"cannot read {label} {path}: {error}") from error
    try:
        after = path.stat()
    except OSError as error:
        raise PreparationError(f"cannot restat {label} {path}: {error}") from error
    fingerprint = (after.st_ino, after.st_size, after.st_mtime_ns)
    if (before.st_ino, before.st_size, before.st_mtime_ns) != fingerprint:
        raise PreparationError(f"{label} changed while it was read")
    return size, measured.hexdigest(), fingerprint


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def artifact_inputs(
    *,
    config: Mapping[str, object],
    split_identity_hash: str,
    sources: Mapping[str, object],
) -> dict[str, object]:
    if len(split_identity_hash) != 64 or any(
        c not in "0123456789abcdef" for c in split_identity_hash
    ):
        raise PreparationError("split identity must be a lowercase SHA256")
    normalized = {k: v for k, v in config.items() if k not in _RECEIPT_KEYS}
    # Admission records may acquire THIS artifact's digest after preparation.
    # Remove only that operational field, never a cell's actual fragments,
    # model parameters, or other configuration. The composed protocol hash
    # remains separate and continues to bind the complete campaign document.
    if isinstance(normalized.get("cells"), list):
        normalized["cells"] = [
            {k: v for k, v in cell.items() if k != "readiness"}
            if isinstance(cell, Mapping)
            else cell
            for cell in normalized["cells"]
        ]
    return {
        "config_sha256": digest(normalized),
        "split_identity_hash": split_identity_hash,
        "sources": dict(sources),
    }


def load_artifact(
    path: Path, *, expected_sha256: str, kind: str, inputs: Mapping[str, object]
) -> object:
    try:
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise PreparationError("prepared artifact file hash mismatch")
        document = json.loads(raw)
        required = {
            "schema",
            "kind",
            "inputs",
            "contact_class",
            "output",
            "output_sha256",
        }
        if (
            not isinstance(document, dict)
            or set(document) != required
            or document["schema"] != SCHEMA
            or document["kind"] != kind
            or document["inputs"] != json.loads(canonical_bytes(inputs))
        ):
            raise PreparationError("prepared artifact identity mismatch")
        if document["contact_class"] not in {"model-free", "tokenizer", "encoder"}:
            raise PreparationError("unknown preparation contact class")
        if digest(document["output"]) != document["output_sha256"]:
            raise PreparationError("prepared artifact output hash mismatch")
        return document["output"]
    except (OSError, json.JSONDecodeError, TypeError) as error:
        raise PreparationError(f"cannot load prepared artifact: {error}") from error


def prepare_artifact(
    path: Path,
    *,
    kind: str,
    inputs: Mapping[str, object],
    producer: Callable[[], object],
    contact_class: str = "model-free",
) -> dict[str, object]:
    """Exclude other producers before checking warm state or doing any work.

    A competing producer is refused immediately. The kernel lock is released
    on process death; an encoder start marker survives, so interruption never
    turns into automatic replay of a potentially spent contact.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path.with_name(path.name + ".producer.lock"), os.O_CREAT | os.O_RDWR, 0o600
    )
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise PreparationError("prepared artifact producer is busy") from error
        return _prepare_artifact_locked(
            path,
            kind=kind,
            inputs=inputs,
            producer=producer,
            contact_class=contact_class,
        )
    finally:
        os.close(descriptor)


def _prepare_artifact_locked(
    path: Path,
    *,
    kind: str,
    inputs: Mapping[str, object],
    producer: Callable[[], object],
    contact_class: str,
):
    """Persist once, or verify an existing artifact without invoking producer."""
    path = Path(path)
    if contact_class not in {"model-free", "tokenizer", "encoder"}:
        raise PreparationError("unknown preparation contact class")
    if path.exists():
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        load_artifact(path, expected_sha256=sha, kind=kind, inputs=inputs)
        if json.loads(path.read_bytes())["contact_class"] != contact_class:
            raise PreparationError("prepared artifact contact class mismatch")
        return {
            "path": str(path),
            "sha256": sha,
            "cache": "warm",
            "contact_class": contact_class,
        }
    if contact_class == "encoder":
        started = path.with_name(path.name + ".encoder-started.json")
        try:
            with started.open("x", encoding="utf-8") as stream:
                stream.write(canonical_bytes({"kind": kind, "inputs": inputs}).decode())
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as error:
            raise PreparationError(
                "prior encoder preparation requires a new registered attempt"
            ) from error
    output = producer()
    document = {
        "schema": SCHEMA,
        "kind": kind,
        "inputs": dict(inputs),
        "contact_class": contact_class,
        "output": output,
        "output_sha256": digest(output),
    }
    raw = canonical_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".prepared-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)  # no replacement of a concurrently published artifact
        except FileExistsError:
            if path.read_bytes() != raw:
                raise PreparationError(
                    "concurrent preparation produced different bytes"
                ) from None
    finally:
        os.unlink(temp)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "cache": "cold",
        "contact_class": contact_class,
    }


def measure_request(
    client: object,
    body: Mapping[str, object],
    *,
    media_marker: str,
    speech_tokens: Sequence[int],
    slot_tokens: int,
    fit_multiple: float = 1.0,
    special_tokens: int = 2,
) -> dict[str, object]:
    """Count the real transport body, including all media and completion reserve.

    Raw media and packet bodies are never persisted by this function. The caller
    supplies exact encoder token counts, one for every media marker, in order.
    A fit certificate records hashes and counts only.
    """
    if not media_marker:
        raise PreparationError("media marker must be nonempty")
    maximum = body.get("max_tokens")
    for value in (maximum, slot_tokens, special_tokens, *speech_tokens):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise PreparationError("token counts must be nonnegative integers")
    if slot_tokens == 0 or not math.isfinite(fit_multiple) or fit_multiple < 1:
        raise PreparationError("invalid slot or fit multiple")
    template = {k: body[k] for k in ("messages", "tools") if k in body}
    if "messages" not in template:
        raise PreparationError("actual request must carry messages")
    rendered = client.request_json("POST", "/apply-template", template)
    prompt = rendered.get("prompt") if isinstance(rendered, Mapping) else None
    if not isinstance(prompt, str):
        raise PreparationError("apply-template returned no prompt")
    parts = prompt.split(media_marker)
    if len(parts) - 1 != len(speech_tokens):
        raise PreparationError("media marker count differs from actual encoder packets")
    text_tokens = 0
    for part in parts:
        tokenized = client.request_json(
            "POST",
            "/tokenize",
            {"content": part, "add_special": False, "parse_special": True},
        )
        tokens = tokenized.get("tokens") if isinstance(tokenized, Mapping) else None
        if not isinstance(tokens, list):
            raise PreparationError("tokenize returned no token list")
        text_tokens += len(tokens)
    required = text_tokens + sum(speech_tokens) + maximum + special_tokens
    margin = slot_tokens - math.ceil(fit_multiple * required)
    return {
        "request_body_sha256": digest(body),
        "text_tokens": text_tokens,
        "speech_tokens": sum(speech_tokens),
        "media_count": len(speech_tokens),
        "maximum_completion_tokens": maximum,
        "special_tokens": special_tokens,
        "required_tokens": required,
        "slot_tokens": slot_tokens,
        "fit_multiple": fit_multiple,
        "margin_tokens": margin,
        "fits": margin >= 0,
    }


def verify_source_receipts(pins, *, repo_root: Path, data_root: Path):
    """Verify complete frozen source receipts, never a partial or placeholder digest."""
    from .model.paths import _normalized_relative_path, _resolve_confined

    if not isinstance(pins, list) or not pins:
        raise PreparationError("preparation requires frozen source receipt pins")
    roots = {"repository": Path(repo_root), "data": Path(data_root)}
    for pin in pins:
        if (
            not isinstance(pin, dict)
            or set(pin) != {"root", "relpath", "sha256"}
            or pin["root"] not in roots
        ):
            raise PreparationError("malformed frozen source receipt pin")
        root = roots[pin["root"]]
        try:
            relative = _normalized_relative_path(pin["relpath"], "source receipt")
            path = _resolve_confined(
                root, relative, root, "source receipt", strict=True
            )
            if hashlib.sha256(path.read_bytes()).hexdigest() != pin["sha256"]:
                raise PreparationError("frozen source receipt file hash mismatch")
        except (OSError, ValueError, RuntimeError) as error:
            raise PreparationError(
                "frozen source receipt is not valid and confined"
            ) from error
    return pins


def measure_multimodal_request(
    client,
    body: Mapping[str, object],
    *,
    slot_tokens: int,
    fit_multiple: float = 1.0,
    special_tokens: int = 2,
):
    """Count the complete actual request on the resident mmproj tokenizer.

    The pinned server's input_tokens route uses its own chat parser and
    multimodal tokenizer, including the supplied WAV. It never queues a
    generation. Missing capability is a refusal, never a duration estimate.
    The study's additional reserve and margin remain separately visible.
    """
    maximum = body.get("max_tokens")
    for value in (maximum, slot_tokens, special_tokens):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise PreparationError("token counts must be nonnegative integers")
    if (
        slot_tokens == 0
        or not math.isfinite(fit_multiple)
        or fit_multiple < 1
        or "messages" not in body
    ):
        raise PreparationError("invalid multimodal fit request")
    try:
        response = client.request_json(
            "POST", "/v1/chat/completions/input_tokens", dict(body)
        )
    except Exception as error:
        raise PreparationError(
            "multimodal count capability unavailable; FIT_READY refused"
        ) from error
    count = response.get("input_tokens") if isinstance(response, Mapping) else None
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise PreparationError("multimodal count capability returned no valid count")
    required = count + maximum + special_tokens
    margin = slot_tokens - math.ceil(fit_multiple * required)
    return {
        "request_body_sha256": digest(body),
        "measured_prompt_tokens": count,
        "measurement": "resident-multimodal-input-tokens",
        "maximum_completion_tokens": maximum,
        "special_tokens": special_tokens,
        "required_tokens": required,
        "slot_tokens": slot_tokens,
        "fit_multiple": fit_multiple,
        "margin_tokens": margin,
        "fits": margin >= 0,
    }
