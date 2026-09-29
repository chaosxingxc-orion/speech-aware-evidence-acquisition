"""Shared immutable preparation artifacts and actual-envelope token measurement.

Prepared bytes are local artifacts, never authorization for a model contact.
Receipt pins and per-cell readiness records are excluded from the input-config
digest to avoid self-reference; every model/request configuration remains bound. Endpoint access is supplied only by an
already-attested caller. Template/tokenizer and multimodal input-count routes
measure requests without generation.

The ``speech-tool`` contact class provides one-shot artifact storage only. Its
caller must separately hold a registered ``ExecutionPlan`` and perform governed
contact accounting before invoking a speech tool.
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
_CONTACT_CLASSES = frozenset({"model-free", "tokenizer", "encoder", "speech-tool"})
_SPEECH_TOOL_START_SCHEMA = "saea-speech-tool-preparation-start-v1"
_RECEIPT_KEYS = frozenset(
    {
        "prepared_phase_supply",
        "prepared_phase_recall",
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


#: The per-branch receipt key of a Perception branch group
#: (``native_episode.roles.perception.branches.branches[*]``): the pin of the
#: prepared branch-seed artifact, written onto the B branches AFTER that
#: artifact is prepared. It is the nested twin of ``prepared_phase_supply``
#: in :data:`_RECEIPT_KEYS` and is excluded from every artifact identity for
#: the same reason.
BRANCH_SEED_RECEIPT_KEY = "prepared_seed"


def without_branch_seed_receipts(branches_block: object) -> object:
    """``branches_block`` with every branch row's ``prepared_seed`` removed.

    ``branches_block`` is a declared ``native_episode.roles.perception.
    branches`` mapping. The pin names an artifact PRODUCED from an identity
    that includes this block, so it must never be one of that identity's own
    inputs: binding it made the identity circular (2026-09-29, P-SV-1 smoke
    re-pin). The branch-seed re-pin drops the pin before producing and
    writes a new one after, so every artifact whose identity carried the pin
    -- the cell's own prepared first-phase supply, loaded by the branch-seed
    producer, and the branch seed itself, verified at flight time with the
    pin present -- stopped verifying. Every other key, including each
    branch's real axes (knobs, release_swap, presentation_id,
    min_candidates, contrast_pairs), is kept. Returned unchanged (the same
    object) when no row carries the key, so no identity of a cell without a
    pinned branch seed moves.
    """

    if not isinstance(branches_block, Mapping):
        return branches_block
    rows = branches_block.get("branches")
    if not isinstance(rows, list) or not any(
        isinstance(row, Mapping) and BRANCH_SEED_RECEIPT_KEY in row for row in rows
    ):
        return branches_block
    return {
        **branches_block,
        "branches": [
            {k: v for k, v in row.items() if k != BRANCH_SEED_RECEIPT_KEY}
            if isinstance(row, Mapping)
            else row
            for row in rows
        ],
    }


def _without_nested_branch_seed_receipts(config: dict[str, object]) -> dict[str, object]:
    native_episode = config.get("native_episode")
    roles = native_episode.get("roles") if isinstance(native_episode, Mapping) else None
    perception = roles.get("perception") if isinstance(roles, Mapping) else None
    block = perception.get("branches") if isinstance(perception, Mapping) else None
    stripped = without_branch_seed_receipts(block)
    if stripped is block:
        return config
    return {
        **config,
        "native_episode": {
            **native_episode,
            "roles": {**roles, "perception": {**perception, "branches": stripped}},
        },
    }


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
    # The nested twin of ``prepared_phase_supply``: a Perception branch's
    # ``prepared_seed`` pin is a receipt written after preparation, never an
    # input (see :func:`without_branch_seed_receipts`).
    normalized = _without_nested_branch_seed_receipts(normalized)
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
        if document["contact_class"] not in _CONTACT_CLASSES:
            raise PreparationError("unknown preparation contact class")
        if digest(document["output"]) != document["output_sha256"]:
            raise PreparationError("prepared artifact output hash mismatch")
        return document["output"]
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as error:
        raise PreparationError(f"cannot load prepared artifact: {error}") from error


def read_artifact_inputs(path: Path) -> Mapping[str, object]:
    """Return the ``inputs`` document one prepared artifact was built with.

    Read-only and independent of :func:`load_artifact`: it is what an identity
    refusal is DIFFED against, so it must stay readable exactly when
    :func:`load_artifact` has already refused the file.
    """

    try:
        document = json.loads(Path(path).read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as error:
        raise PreparationError(
            f"cannot read prepared artifact inputs: {error}"
        ) from error
    if not isinstance(document, dict) or not isinstance(document.get("inputs"), dict):
        raise PreparationError("prepared artifact carries no inputs document")
    return document["inputs"]


def _canonical_value(value: object) -> object:
    try:
        return json.loads(canonical_bytes(value))
    except (TypeError, ValueError, OverflowError) as error:
        raise PreparationError(
            f"identity document is not canonically serializable: {error}"
        ) from error


def _first_difference(expected: object, actual: object, prefix: str) -> str | None:
    if isinstance(expected, Mapping) and isinstance(actual, Mapping):
        for key in sorted(set(expected) | set(actual)):
            here = f"{prefix}{key}"
            if key not in expected:
                return f"{here} (absent from the recomputed identity)"
            if key not in actual:
                return f"{here} (absent from the prepared artifact)"
            found = _first_difference(expected[key], actual[key], here + ".")
            if found is not None:
                return found
        return None
    if expected == actual:
        return None
    return prefix[:-1] if prefix else "<root>"


def first_input_difference(expected: object, actual: object) -> str | None:
    """Dotted key path of the FIRST difference between two ``inputs`` documents.

    ``expected`` is the identity recomputed from the current implementation and
    config; ``actual`` is what the prepared artifact carries. Keys are walked in
    sorted order, so a stale artifact always names the same key path -- e.g.
    ``config_sha256`` after a config edit, or ``sources.implementation.runtime``
    after a merge moved ``core/flight/runtime.py``. ``None`` means the two
    documents are identical.
    """

    return _first_difference(_canonical_value(expected), _canonical_value(actual), "")


def verify_artifact_identity(
    path: Path, *, expected_sha256: str, kind: str, inputs: Mapping[str, object]
) -> dict[str, object]:
    """Verify one prepared artifact WITHOUT building, writing or raising.

    The same three facts :func:`load_artifact` enforces -- the file exists, its
    bytes hash to the pinned digest, and its embedded identity equals the one
    recomputed here -- reported as data so one caller can list every artifact
    (``core.flight.cli check``) while another refuses on the first failure
    (``FlightRuntime.preflight``). A failure additionally names the first
    differing identity key (:func:`first_input_difference`).
    """

    path = Path(path)
    if not path.is_file():
        return {
            "sha256": None,
            "identity_ok": False,
            "reason": f"prepared artifact is absent on disk: {path}",
            "difference": None,
        }
    try:
        measured = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        return {
            "sha256": None,
            "identity_ok": False,
            "reason": f"cannot read prepared artifact {path}: {error}",
            "difference": None,
        }
    if measured != expected_sha256:
        return {
            "sha256": measured,
            "identity_ok": False,
            "reason": (
                f"prepared artifact {path} hashes to {measured}, not the pinned "
                f"{expected_sha256}"
            ),
            "difference": None,
        }
    try:
        load_artifact(path, expected_sha256=measured, kind=kind, inputs=inputs)
    except PreparationError as error:
        difference = None
        try:
            difference = first_input_difference(inputs, read_artifact_inputs(path))
        except PreparationError:
            difference = None
        reason = str(error)
        if difference is not None:
            reason = f"{reason}; first differing identity key: {difference}"
        return {
            "sha256": measured,
            "identity_ok": False,
            "reason": reason,
            "difference": difference,
        }
    return {
        "sha256": measured,
        "identity_ok": True,
        "reason": None,
        "difference": None,
    }


def _acquire_artifact_locks(entries) -> list[int]:
    """Acquire every unique producer lock without waiting, in path order."""

    descriptors: list[int] = []
    try:
        for entry in sorted(entries, key=lambda row: str(row["resolved"])):
            resolved = entry["resolved"]
            resolved.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                resolved.with_name(resolved.name + ".producer.lock"),
                os.O_CREAT | os.O_RDWR,
                0o600,
            )
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                os.close(descriptor)
                raise PreparationError("prepared artifact producer is busy") from error
            descriptors.append(descriptor)
        return descriptors
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _warm_artifact_receipt(
    path: Path,
    *,
    kind: str,
    inputs: Mapping[str, object],
    contact_class: str,
) -> dict[str, object]:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    load_artifact(path, expected_sha256=sha, kind=kind, inputs=inputs)
    if json.loads(raw)["contact_class"] != contact_class:
        raise PreparationError("prepared artifact contact class mismatch")
    return {
        "path": str(path),
        "sha256": sha,
        "cache": "warm",
        "contact_class": contact_class,
    }


def _validate_start_state(
    path: Path,
    *,
    kind: str,
    inputs: Mapping[str, object],
    contact_class: str,
) -> None:
    speech_tool_started = path.with_name(path.name + ".speech-tool-started.json")
    encoder_started = path.with_name(path.name + ".encoder-started.json")
    if speech_tool_started.exists():
        _refuse_started_speech_tool(
            speech_tool_started,
            kind=kind,
            inputs=inputs,
            contact_class=contact_class,
        )
    if contact_class == "speech-tool" and encoder_started.exists():
        raise PreparationError("preparation start marker contact class mismatch")
    if contact_class == "encoder" and encoder_started.exists():
        raise PreparationError(
            "prior encoder preparation requires a new registered attempt"
        )


def _persist_start_marker(
    path: Path,
    *,
    kind: str,
    inputs: Mapping[str, object],
    contact_class: str,
    prevalidated: bool = False,
) -> None:
    speech_tool_started = path.with_name(path.name + ".speech-tool-started.json")
    encoder_started = path.with_name(path.name + ".encoder-started.json")
    if not prevalidated:
        _validate_start_state(
            path, kind=kind, inputs=inputs, contact_class=contact_class
        )
    if contact_class == "encoder":
        try:
            with encoder_started.open("x", encoding="utf-8") as stream:
                stream.write(canonical_bytes({"kind": kind, "inputs": inputs}).decode())
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as error:
            raise PreparationError(
                "prior encoder preparation requires a new registered attempt"
            ) from error
    elif contact_class == "speech-tool":
        marker = {
            "schema": _SPEECH_TOOL_START_SCHEMA,
            "kind": kind,
            "inputs": dict(inputs),
            "contact_class": contact_class,
        }
        try:
            with speech_tool_started.open("x", encoding="utf-8") as stream:
                stream.write(canonical_bytes(marker).decode())
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            _refuse_started_speech_tool(
                speech_tool_started,
                kind=kind,
                inputs=inputs,
                contact_class=contact_class,
            )


def _artifact_bytes(
    *,
    kind: str,
    inputs: Mapping[str, object],
    output: object,
    contact_class: str,
) -> bytes:
    return canonical_bytes(
        {
            "schema": SCHEMA,
            "kind": kind,
            "inputs": dict(inputs),
            "contact_class": contact_class,
            "output": output,
            "output_sha256": digest(output),
        }
    )


def _publish_artifact(
    path: Path, raw: bytes, *, contact_class: str
) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".prepared-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temp, path)
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
    on process death; encoder and speech-tool start markers survive, so an
    interruption never turns into automatic replay of a potentially spent
    contact. This storage helper does not authorize the contact: speech-tool
    callers still need a registered ``ExecutionPlan`` and governed accounting.
    """
    path = Path(path)
    entry = {"path": path, "resolved": path.resolve()}
    descriptors = _acquire_artifact_locks([entry])
    try:
        return _prepare_artifact_locked(
            path,
            kind=kind,
            inputs=inputs,
            producer=producer,
            contact_class=contact_class,
        )
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def prepare_artifact_batch(
    items,
    *,
    kind: str,
    producer: Callable[[list[int]], Sequence[object]],
    contact_class: str = "speech-tool",
) -> list[dict[str, object]]:
    """Prepare a locked batch once and return receipts in caller order.

    The producer receives the original index of each missing unique path.
    Authorization, lease ownership and pre-contact accounting remain the
    caller's responsibility.
    """

    if contact_class not in _CONTACT_CLASSES:
        raise PreparationError("unknown preparation contact class")
    if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
        raise PreparationError("preparation batch items must be a sequence")

    entries_by_resolved: dict[Path, dict[str, object]] = {}
    original_entries: list[dict[str, object]] = []
    for index, item in enumerate(items):
        if (
            not isinstance(item, Mapping)
            or set(item) != {"path", "inputs"}
            or not isinstance(item["inputs"], Mapping)
        ):
            raise PreparationError("malformed preparation batch item")
        path = Path(item["path"])
        inputs = item["inputs"]
        try:
            normalized_inputs = canonical_bytes(inputs)
        except (TypeError, ValueError, OverflowError) as error:
            raise PreparationError(
                "preparation batch item inputs are not serializable"
            ) from error
        resolved = path.resolve()
        entry = entries_by_resolved.get(resolved)
        if entry is None:
            entry = {
                "path": path,
                "resolved": resolved,
                "inputs": inputs,
                "normalized_inputs": normalized_inputs,
                "first_index": index,
            }
            entries_by_resolved[resolved] = entry
        elif entry["normalized_inputs"] != normalized_inputs:
            raise PreparationError(
                "duplicate preparation batch path has different inputs"
            )
        original_entries.append(entry)

    unique_entries = list(entries_by_resolved.values())
    if not unique_entries:
        return []
    descriptors = _acquire_artifact_locks(unique_entries)
    try:
        receipts_by_resolved: dict[Path, dict[str, object]] = {}
        missing: list[dict[str, object]] = []
        for entry in unique_entries:
            path = entry["path"]
            if path.exists():
                receipts_by_resolved[entry["resolved"]] = _warm_artifact_receipt(
                    path,
                    kind=kind,
                    inputs=entry["inputs"],
                    contact_class=contact_class,
                )
            else:
                missing.append(entry)

        if missing:
            for entry in missing:
                _validate_start_state(
                    entry["path"],
                    kind=kind,
                    inputs=entry["inputs"],
                    contact_class=contact_class,
                )
            for entry in missing:
                _persist_start_marker(
                    entry["path"],
                    kind=kind,
                    inputs=entry["inputs"],
                    contact_class=contact_class,
                    prevalidated=True,
                )
            indices = [entry["first_index"] for entry in missing]
            outputs = producer(indices)
            if (
                isinstance(outputs, (str, bytes, Mapping))
                or not isinstance(outputs, Sequence)
                or len(outputs) != len(missing)
            ):
                raise PreparationError(
                    "batch producer output count differs from missing item count"
                )
            raws = []
            try:
                for entry, output in zip(missing, outputs, strict=True):
                    raws.append(
                        _artifact_bytes(
                            kind=kind,
                            inputs=entry["inputs"],
                            output=output,
                            contact_class=contact_class,
                        )
                    )
            except (TypeError, ValueError, OverflowError) as error:
                raise PreparationError(
                    "batch producer outputs are not serializable"
                ) from error
            for entry, raw in zip(missing, raws, strict=True):
                receipts_by_resolved[entry["resolved"]] = _publish_artifact(
                    entry["path"], raw, contact_class=contact_class
                )

        return [
            dict(receipts_by_resolved[entry["resolved"]])
            for entry in original_entries
        ]
    finally:
        for descriptor in reversed(descriptors):
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
    if contact_class not in _CONTACT_CLASSES:
        raise PreparationError("unknown preparation contact class")
    if path.exists():
        return _warm_artifact_receipt(
            path, kind=kind, inputs=inputs, contact_class=contact_class
        )
    _persist_start_marker(
        path, kind=kind, inputs=inputs, contact_class=contact_class
    )
    output = producer()
    raw = _artifact_bytes(
        kind=kind,
        inputs=inputs,
        output=output,
        contact_class=contact_class,
    )
    return _publish_artifact(path, raw, contact_class=contact_class)


def _refuse_started_speech_tool(
    marker_path: Path,
    *,
    kind: str,
    inputs: Mapping[str, object],
    contact_class: str,
) -> None:
    """Validate one durable start marker, then refuse automatic replay."""

    try:
        marker = json.loads(marker_path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as error:
        raise PreparationError(
            f"cannot load speech-tool preparation start marker: {error}"
        ) from error
    required = {"schema", "kind", "inputs", "contact_class"}
    if (
        not isinstance(marker, dict)
        or set(marker) != required
        or marker.get("schema") != _SPEECH_TOOL_START_SCHEMA
        or marker.get("contact_class") != "speech-tool"
    ):
        raise PreparationError("speech-tool preparation start marker identity mismatch")
    if contact_class != "speech-tool":
        raise PreparationError("preparation start marker contact class mismatch")
    if (
        marker["kind"] != kind
        or marker["inputs"] != json.loads(canonical_bytes(inputs))
    ):
        raise PreparationError("speech-tool preparation start marker identity mismatch")
    raise PreparationError(
        "prior speech-tool preparation requires a new registered attempt"
    )


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
