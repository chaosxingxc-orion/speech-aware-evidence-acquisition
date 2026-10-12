"""Always-on serving sessions: one resident llama-server, many attempts.

Owner rule, 2026-09-07: the model may stay always on, provided monitoring
numbers come back, so that GPU time is reused across agents instead of being
paid for again by every flight. Study ``CLAUDE.md`` already states the
pipeline half of the same rule -- "one resident server per serving geometry;
ready flights are queued by geometry so the GPU never idles".

Two facts shape this module:

* A detached WSL job dies with the shell that spawned it, so the resident
  server must be owned by a LIVE foreground wrapper the coordinator runs
  (``scripts/serving_session.sh start``), never by an agent's transient
  session.
* ``core.session.attach_session`` already knows how to bind to a server this
  process did not spawn, and refuses anything it cannot prove (loopback,
  runtime-receipt identity, live pid, real process image, socket ownership).
  What was missing was the SEMANTIC half: proving the resident server is
  serving the geometry and model identity THIS flight requires, and saying
  exactly which field disagrees when it is not.

This module is that semantic half plus the session's on-disk record:

``$SPEECHRL_DATA_DIR/serving/<session-id>/``
    ``session.json``          the serving session document (identity + /props)
    ``session-receipt.json``  the ordinary ``SessionReceipt`` ``start_session``
                              wrote -- what ``attach_session`` binds to
    ``server.log``            llama-server's own combined output
    ``monitor.jsonl``         ``scripts/serving_monitor.py`` samples
    ``session-stop.json``     written by ``stop``, or by the wrapper itself
                              when the server exits on its own; its presence
                              means "not resident any more"

Standard-library only, like the rest of ``core.session``: a flight runtime,
an operator script and a check may all import it without pulling ``rails``
or a heavy config path in.
"""

from __future__ import annotations

import fcntl
import json
import math
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...contracts import STUDY_SLUG
from . import SessionError
from .process import (
    PROCESS_STATE_DEFUNCT,
    PROCESS_STATE_GONE,
    PROCESS_STATE_RUNNING,
    _defunct_wait_status,
    process_state,
)

SERVING_SESSION_SCHEMA = "saea-serving-session-v1"
SERVING_SESSION_STOP_SCHEMA = "saea-serving-session-stop-v1"
SERVING_MONITOR_SAMPLE_SCHEMA = "saea-serving-monitor-sample-v1"
SERVING_MONITOR_SUMMARY_SCHEMA = "saea-serving-monitor-summary-v1"

#: Directory under the controlled data root holding every serving session.
SERVING_ROOT_NAME = "serving"

SESSION_DOCUMENT_NAME = "session.json"
SESSION_RECEIPT_NAME = "session-receipt.json"
SESSION_STOP_NAME = "session-stop.json"
SERVER_LOG_NAME = "server.log"
MONITOR_JSONL_NAME = "monitor.jsonl"
SESSION_STOP_LOCK_NAME = ".session-stop.lock"


@contextmanager
def _session_stop_lock(session_dir: Path):
    """Serialize operator stop and foreground-owner stop publication.

    The operator acquires this lock before signalling the child. That ordering
    lets the foreground owner distinguish an explicit stop already in progress
    from a server that exited independently.
    """

    lock_path = Path(session_dir) / SESSION_STOP_LOCK_NAME
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _read_explicit_stop_document(
    session_dir: Path,
    *,
    session,
    runtime_receipt: Mapping[str, object],
) -> dict[str, object] | None:
    """Return a matching operator stop document, if one is already durable."""

    from ..preparation_feature_provenance import canonical_receipt_sha256

    path = Path(session_dir) / SESSION_STOP_NAME
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    receipt = document.get("stop_receipt") if isinstance(document, Mapping) else None
    if not isinstance(document, Mapping) or not isinstance(receipt, Mapping):
        return None
    base_keys = {
        "schema", "study", "session_id", "session_role",
        "session_receipt_sha256", "runtime_receipt_sha256", "pid",
        "termination_signal", "forced", "stopped_at",
    }
    if (
        set(receipt) not in (base_keys, base_keys | {"final_process_state"})
        or document.get("schema") != SERVING_SESSION_STOP_SCHEMA
        or document.get("study") != STUDY_SLUG
        or document.get("session_id") != session.session_id
        or document.get("stale") is not False
        or document.get("server_exit") is not None
        or receipt.get("schema") != "saea-session-stop-receipt-v1"
        or receipt.get("study") != STUDY_SLUG
        or receipt.get("session_id") != session.session_id
        or receipt.get("session_role") != session.role
        or receipt.get("pid") != session.pid
        or receipt.get("session_receipt_sha256") != canonical_receipt_sha256(session.as_json())
        or receipt.get("runtime_receipt_sha256") != canonical_receipt_sha256(runtime_receipt)
        or receipt.get("termination_signal") not in {"SIGTERM", "SIGKILL", "ALREADY_EXITED"}
        or not isinstance(receipt.get("forced"), bool)
    ):
        return None
    return dict(document)

#: A sample counts as PARKED when every slot is idle AND the card reports
#: less than this much utilization. The owner's own idle signal is power
#: draw; utilization is the cheaper, monotone proxy sampled beside it, and
#: the summary reports mean/peak power so the two can be read together.
PARKED_UTILIZATION_PERCENT = 5.0

#: The fields a flight and the serving session must agree on before a flight
#: may attach. Every one of them is recorded in ``session.json``; a mismatch
#: names the field (see :func:`identity_mismatches`).
SERVING_IDENTITY_FIELDS: tuple[str, ...] = (
    "model_fragment",
    "model_fragment_sha256",
    "runtime_receipt_relpath",
    "runtime_receipt_sha256",
    "binary_path",
    "binary_sha256",
    "model_files",
    "session_role",
    "model_root",
    "server_argv",
    "server_env",
    "host",
    "port",
    "props_identity",
)


class ServingSessionError(SessionError):
    """A malformed, ambiguous or absent serving session record."""


class ServingIdentityMismatch(ServingSessionError):
    """The resident serving session does not serve what a flight requires.

    Carries ``mismatches``: one entry per differing identity field, each with
    the session's value and the flight's required value, so the operator is
    told which knob to change rather than merely that "the geometry differs".
    """

    def __init__(self, message: str, mismatches: Sequence[Mapping[str, object]]) -> None:
        super().__init__(message)
        self.mismatches = tuple(dict(entry) for entry in mismatches)


# ---------------------------------------------------------------------------
# The one server-argument merge (moved here from core.flight.runtime, which
# re-exports it: a resident server an operator starts and a server a flight
# starts must be built by the SAME function or the reuse predicate below is
# comparing two dialects).
# ---------------------------------------------------------------------------


def merge_server_args(
    server_args: Sequence[object], *, slots: int, context_tokens: int
) -> list[str]:
    """The model fragment's own ``server_args``, with ONLY ``-np``/``-c``
    replaced (or appended when absent) from the serving geometry.

    Nothing else is invented or discarded: ``-ngl``/``-fa``/``-ctk``/``-ctv``
    and every batch and cache flag the fragment declares ride through
    untouched (dropping them once served a whole flight on the CPU).
    """

    if isinstance(server_args, (str, bytes)) or not isinstance(server_args, Sequence):
        raise ServingSessionError("model config server_args must be a list of strings")
    merged = [str(value) for value in server_args]
    for flag, value in (("-np", slots), ("-c", context_tokens)):
        if flag in merged:
            index = merged.index(flag)
            if index + 1 >= len(merged):
                raise ServingSessionError(
                    f"model config server_args declares {flag} with no value"
                )
            merged[index + 1] = str(value)
        else:
            merged.extend([flag, str(value)])
    return merged


# ---------------------------------------------------------------------------
# Paths.
# ---------------------------------------------------------------------------


def serving_root(data_root: Path) -> Path:
    return Path(data_root) / SERVING_ROOT_NAME


def serving_session_dir(data_root: Path, session_id: str) -> Path:
    if not isinstance(session_id, str) or not session_id.strip():
        raise ServingSessionError("serving session id must be a non-empty string")
    if "/" in session_id or "\\" in session_id or session_id in (".", ".."):
        raise ServingSessionError(f"serving session id must be one path segment: {session_id!r}")
    return serving_root(data_root) / session_id


# ---------------------------------------------------------------------------
# Identity.
# ---------------------------------------------------------------------------


def props_identity(props: Mapping[str, object] | None) -> dict[str, object]:
    """The three ``GET /props`` fields that describe what a llama-server is
    actually serving: ``total_slots`` (the live ``-np``), the per-slot
    ``n_ctx`` under ``default_generation_settings`` (the live ``-c`` divided
    by the slots, AFTER llama.cpp's own rounding), and ``model_path``.

    ``build_info`` is recorded in ``session.json`` beside these but is not
    compared: a flight has no independent way to derive it, and the binary's
    re-hashed sha256 plus the runtime receipt already pin the build.
    """

    if props is None:
        return {}
    if not isinstance(props, Mapping):
        raise ServingSessionError("/props snapshot must be a JSON object")
    generation = props.get("default_generation_settings")
    slot_n_ctx = (
        generation.get("n_ctx") if isinstance(generation, Mapping) else None
    )
    return {
        "total_slots": props.get("total_slots"),
        "slot_n_ctx": slot_n_ctx,
        "model_path": props.get("model_path"),
    }


def serving_identity(
    *,
    model_fragment: str,
    model_fragment_sha256: str,
    runtime_receipt_relpath: str,
    runtime_receipt_sha256: str,
    binary_path: str,
    binary_sha256: str,
    model_files: Sequence[Mapping[str, object]],
    session_role: str,
    model_root: str | None,
    server_argv: Sequence[str],
    server_env: Mapping[str, str],
    host: str,
    port: int,
    props: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """The comparable identity of ONE serving session, in exactly the shape
    ``session.json`` stores and :func:`identity_mismatches` compares."""

    return {
        "model_fragment": str(model_fragment),
        "model_fragment_sha256": str(model_fragment_sha256),
        "runtime_receipt_relpath": str(runtime_receipt_relpath),
        "runtime_receipt_sha256": str(runtime_receipt_sha256),
        "binary_path": str(binary_path),
        "binary_sha256": str(binary_sha256),
        "model_files": [
            {"path": str(entry["path"]), "sha256": str(entry["sha256"])}
            for entry in model_files
        ],
        "session_role": str(session_role),
        "model_root": str(model_root) if model_root is not None else None,
        "server_argv": [str(part) for part in server_argv],
        "server_env": {str(key): str(value) for key, value in dict(server_env).items()},
        "host": str(host),
        "port": int(port),
        "props_identity": props_identity(props),
    }


def _argv_map(argv: Sequence[str]) -> dict[str, object]:
    """``[binary, --host, h, --port, p, -m, X, -fa, on, ...]`` as
    ``{"<binary>": path, "--host": [h], "-fa": ["on"], ...}`` so a diff can
    name the FLAG that differs (``-c``) instead of an argv index."""

    mapped: dict[str, object] = {"<binary>": str(argv[0]) if argv else None}
    index = 1
    parts = [str(part) for part in argv]
    while index < len(parts):
        token = parts[index]
        if not token.startswith("-"):
            mapped.setdefault("<positional>", []).append(token)  # type: ignore[union-attr]
            index += 1
            continue
        value: object = True
        if index + 1 < len(parts) and not parts[index + 1].startswith("-"):
            value = parts[index + 1]
            index += 2
        else:
            index += 1
        mapped.setdefault(token, []).append(value)  # type: ignore[union-attr]
    return mapped


def identity_mismatches(
    session_identity: Mapping[str, object], required: Mapping[str, object]
) -> list[dict[str, object]]:
    """Every identity field on which a resident session and a flight's
    requirement disagree, most specific first.

    ``server_argv`` is diffed FLAG BY FLAG (``-c``, ``-np``, ``--mmproj``,
    ...) rather than as an opaque list, because "which flag differs" is the
    operator's actual question; a same-flags-different-order argv is reported
    as ``server_argv[order]``.
    """

    mismatches: list[dict[str, object]] = []
    for field in SERVING_IDENTITY_FIELDS:
        session_value = session_identity.get(field)
        required_value = required.get(field)
        if field == "server_argv":
            session_flags = _argv_map(list(session_value or ()))
            required_flags = _argv_map(list(required_value or ()))
            flag_mismatches = 0
            for flag in sorted(set(session_flags) | set(required_flags)):
                if session_flags.get(flag) != required_flags.get(flag):
                    flag_mismatches += 1
                    mismatches.append(
                        {
                            "field": f"server_argv[{flag}]",
                            "session": session_flags.get(flag),
                            "required": required_flags.get(flag),
                        }
                    )
            # Only when every flag agrees can an argv difference be pure
            # ORDER; counting this field's own mismatches (not the whole
            # list, which may already carry an unrelated model_files entry)
            # is what makes that true.
            if not flag_mismatches and list(session_value or ()) != list(required_value or ()):
                mismatches.append(
                    {
                        "field": "server_argv[order]",
                        "session": list(session_value or ()),
                        "required": list(required_value or ()),
                    }
                )
            continue
        if field == "props_identity":
            session_props = dict(session_value or {})
            required_props = dict(required_value or {})
            for key in sorted(set(session_props) | set(required_props)):
                if key not in required_props or required_props[key] is None:
                    # A requirement that declares nothing for this key (a
                    # flight cannot derive build_info) checks nothing.
                    continue
                if session_props.get(key) != required_props[key]:
                    mismatches.append(
                        {
                            "field": f"props_identity.{key}",
                            "session": session_props.get(key),
                            "required": required_props[key],
                        }
                    )
            continue
        if session_value != required_value:
            mismatches.append(
                {"field": field, "session": session_value, "required": required_value}
            )
    return mismatches


def assert_identity_matches(
    session_document: Mapping[str, object], required: Mapping[str, object]
) -> None:
    """Fail closed unless the resident session serves exactly what ``required``
    describes, naming every differing field."""

    session_identity = session_document.get("identity")
    if not isinstance(session_identity, Mapping):
        raise ServingSessionError("serving session document carries no identity object")
    mismatches = identity_mismatches(session_identity, required)
    if mismatches:
        rendered = "; ".join(
            f"{entry['field']}: session={entry['session']!r} required={entry['required']!r}"
            for entry in mismatches
        )
        raise ServingIdentityMismatch(
            "the resident serving session "
            f"{session_document.get('session_id')!r} cannot serve this flight -- "
            f"{rendered}",
            mismatches,
        )


# ---------------------------------------------------------------------------
# The session document.
# ---------------------------------------------------------------------------


def build_session_document(
    *,
    session_id: str,
    identity: Mapping[str, object],
    pid: int,
    started_at: str,
    serving_geometry: Mapping[str, object],
    props: Mapping[str, object] | None,
    session_receipt_path: str,
    server_log_path: str,
    monitor_path: str,
) -> dict[str, object]:
    return {
        "schema": SERVING_SESSION_SCHEMA,
        "study": STUDY_SLUG,
        "session_id": str(session_id),
        "identity": dict(identity),
        "pid": int(pid),
        "started_at": str(started_at),
        # Recorded, never compared: ``max_tokens`` is a request parameter, so
        # two flights with different completion ceilings share one server.
        "serving_geometry": dict(serving_geometry),
        "props": dict(props) if props is not None else None,
        "session_receipt_path": str(session_receipt_path),
        "server_log_path": str(server_log_path),
        "monitor_path": str(monitor_path),
    }


def write_json_document(path: Path, document: Mapping[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def read_session_document(path: Path) -> dict[str, object]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ServingSessionError(f"serving session document is unreadable ({path}): {error}") from error
    if not isinstance(document, dict):
        raise ServingSessionError(f"serving session document must be a JSON object: {path}")
    if document.get("schema") != SERVING_SESSION_SCHEMA:
        raise ServingSessionError(
            f"serving session document {path} declares schema "
            f"{document.get('schema')!r}, expected {SERVING_SESSION_SCHEMA!r}"
        )
    if document.get("study") != STUDY_SLUG:
        raise ServingSessionError(
            f"serving session document {path} belongs to study {document.get('study')!r}"
        )
    return document


def find_resident_session(data_root: Path) -> tuple[Path, dict[str, object]] | None:
    """The ONE serving session that is still resident, or ``None``.

    Resident means: a ``session.json`` exists and no ``session-stop.json``
    sits beside it. Two live sessions cannot share this host's VRAM, so
    finding two is a fail-closed error rather than a choice; a session whose
    process has died without a stop record is still returned, because
    ``attach_session`` refusing a dead pid is a far better operator signal
    than silently spawning a second 18.5 GB server.
    """

    root = serving_root(data_root)
    if not root.is_dir():
        return None
    live: list[tuple[Path, dict[str, object]]] = []
    for candidate in sorted(root.iterdir()):
        document_path = candidate / SESSION_DOCUMENT_NAME
        if not document_path.is_file():
            continue
        if (candidate / SESSION_STOP_NAME).is_file():
            continue
        live.append((candidate, read_session_document(document_path)))
    if not live:
        return None
    if len(live) > 1:
        names = ", ".join(str(path.name) for path, _ in live)
        raise ServingSessionError(
            f"{len(live)} serving sessions are recorded as resident ({names}); this host "
            "serves one geometry at a time -- stop the stale session before continuing"
        )
    return live[0]


# ---------------------------------------------------------------------------
# Monitor samples.
# ---------------------------------------------------------------------------


def read_monitor_samples(path: Path) -> list[dict[str, object]]:
    """Every well-formed sample in a monitor JSONL, in file order.

    A truncated final line (the monitor is appending while this reads) is
    skipped rather than raising: a summary is a report, and losing the last
    10 seconds of it must never fail a flight's seal.
    """

    samples: list[dict[str, object]] = []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return samples
    except (OSError, UnicodeError) as error:
        raise ServingSessionError(f"monitor samples are unreadable ({path}): {error}") from error
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            sample = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(sample, dict) and isinstance(sample.get("sampled_at"), (int, float)):
            samples.append(sample)
    return samples


def _sample_is_parked(sample: Mapping[str, object]) -> bool:
    slots = sample.get("slots")
    busy = slots.get("busy") if isinstance(slots, Mapping) else None
    gpu = sample.get("gpu")
    utilization = gpu.get("utilization_percent") if isinstance(gpu, Mapping) else None
    if not isinstance(busy, (int, float)) or not isinstance(utilization, (int, float)):
        return False
    return busy == 0 and float(utilization) < PARKED_UTILIZATION_PERCENT


def _numeric(sample: Mapping[str, object], *path: str) -> float | None:
    cursor: object = sample
    for key in path:
        if not isinstance(cursor, Mapping):
            return None
        cursor = cursor.get(key)
    if isinstance(cursor, bool) or not isinstance(cursor, (int, float)):
        return None
    return float(cursor) if math.isfinite(float(cursor)) else None


def summarize_monitor_samples(
    samples: Sequence[Mapping[str, object]],
    *,
    from_epoch: float | None = None,
    to_epoch: float | None = None,
) -> dict[str, object]:
    """How the card spent a window: parked vs active seconds, what the server
    got through, and what it drew.

    Seconds are attributed by INTERVAL: each sample owns the gap to the next
    sample, so a 10-second cadence attributes 10 parked seconds to a sample
    that found every slot idle and the card under
    :data:`PARKED_UTILIZATION_PERCENT`. The final sample owns no interval, so
    ``parked_seconds + active_seconds == wall_seconds`` exactly.

    ``requests_delta`` and ``tokens_delta`` are last-minus-first over the
    monitor's own cumulative counters; both are ``None`` when the window has
    fewer than two samples carrying that counter (``tokens_predicted_total``
    needs llama-server's ``--metrics`` endpoint, which the pinned fragments
    do not enable by default).

    HOST memory (E7c, 2026-09-07 incident): ``host_free_gb_min`` /
    ``host_free_gb_min_at`` / ``host_free_gb_last`` track the Windows host's
    own free memory across the window (the number the watchdog acted on);
    ``vm_available_gb_min`` and ``vmmem_ws_gb_max`` are the VM-side and
    VM-footprint-on-host companions. ``host_memory_samples`` counts samples
    carrying a non-null ``host_free_gb`` reading -- a monitor run entirely on
    a host with WSL interop disabled reports ``0`` here rather than a
    misleadingly present-but-empty minimum.
    """

    selected = [
        sample
        for sample in samples
        if (from_epoch is None or float(sample["sampled_at"]) >= float(from_epoch))
        and (to_epoch is None or float(sample["sampled_at"]) <= float(to_epoch))
    ]
    selected.sort(key=lambda sample: float(sample["sampled_at"]))

    summary: dict[str, object] = {
        "schema": SERVING_MONITOR_SUMMARY_SCHEMA,
        "window": {"from": from_epoch, "to": to_epoch},
        "sample_count": len(selected),
        "first_sample_at": float(selected[0]["sampled_at"]) if selected else None,
        "last_sample_at": float(selected[-1]["sampled_at"]) if selected else None,
        "wall_seconds": 0.0,
        "parked_seconds": 0.0,
        "active_seconds": 0.0,
        "parked_fraction": None,
        "requests_delta": None,
        "tokens_delta": None,
        "mean_power_watts": None,
        "peak_power_watts": None,
        "mean_utilization_percent": None,
        "host_free_gb_min": None,
        "host_free_gb_min_at": None,
        "host_free_gb_last": None,
        "vm_available_gb_min": None,
        "vmmem_ws_gb_max": None,
        "host_memory_samples": 0,
        "parked_definition": (
            "every slot idle AND nvidia-smi utilization.gpu < "
            f"{PARKED_UTILIZATION_PERCENT:g}%"
        ),
    }
    if not selected:
        return summary

    parked = 0.0
    active = 0.0
    for index in range(len(selected) - 1):
        span = float(selected[index + 1]["sampled_at"]) - float(selected[index]["sampled_at"])
        if span <= 0:
            continue
        if _sample_is_parked(selected[index]):
            parked += span
        else:
            active += span
    wall = parked + active
    summary["wall_seconds"] = wall
    summary["parked_seconds"] = parked
    summary["active_seconds"] = active
    summary["parked_fraction"] = (parked / wall) if wall > 0 else None

    for name, path in (
        ("requests_delta", ("requests_total",)),
        ("tokens_delta", ("metrics", "tokens_predicted_total")),
    ):
        values = [
            value
            for value in (_numeric(sample, *path) for sample in selected)
            if value is not None
        ]
        if len(values) >= 2:
            summary[name] = values[-1] - values[0]

    powers = [
        value
        for value in (_numeric(sample, "gpu", "power_watts") for sample in selected)
        if value is not None
    ]
    if powers:
        summary["mean_power_watts"] = sum(powers) / len(powers)
        summary["peak_power_watts"] = max(powers)
    utilizations = [
        value
        for value in (_numeric(sample, "gpu", "utilization_percent") for sample in selected)
        if value is not None
    ]
    if utilizations:
        summary["mean_utilization_percent"] = sum(utilizations) / len(utilizations)

    host_free_series = [
        (float(sample["sampled_at"]), value)
        for sample in selected
        for value in (_numeric(sample, "host_memory", "host_free_gb"),)
        if value is not None
    ]
    summary["host_memory_samples"] = len(host_free_series)
    if host_free_series:
        min_at, min_value = min(host_free_series, key=lambda pair: pair[1])
        summary["host_free_gb_min"] = min_value
        summary["host_free_gb_min_at"] = min_at
        summary["host_free_gb_last"] = host_free_series[-1][1]

    vm_available_values = [
        value
        for value in (_numeric(sample, "host_memory", "vm_available_gb") for sample in selected)
        if value is not None
    ]
    if vm_available_values:
        summary["vm_available_gb_min"] = min(vm_available_values)

    vmmem_values = [
        value
        for value in (_numeric(sample, "host_memory", "vmmem_ws_gb") for sample in selected)
        if value is not None
    ]
    if vmmem_values:
        summary["vmmem_ws_gb_max"] = max(vmmem_values)

    return summary


def summarize_monitor_file(
    path: Path, *, from_epoch: float | None = None, to_epoch: float | None = None
) -> dict[str, object]:
    """:func:`summarize_monitor_samples` over a monitor JSONL on disk."""

    return summarize_monitor_samples(
        read_monitor_samples(path), from_epoch=from_epoch, to_epoch=to_epoch
    )


# ---------------------------------------------------------------------------
# Is the recorded server still there? (E7b defect 1, observed 2026-09-07)
#
# Both sessions of the first day ended the same way: llama-server exited,
# its foreground wrapper never reaped it, and the resulting ZOMBIE was
# "alive" to ``kill(pid, 0)`` but had no ``/proc/<pid>/exe`` -- so ``stop``
# refused (I5), ``session.json`` kept no stop record, and ``start`` refused
# the next geometry as "already resident". The coordinator had to write the
# stop records by hand.
#
# A stop record for a server nobody can signal any more is only honest if
# the absence is PROVEN, so this section observes three independent facts
# and refuses to call a session stale unless all three agree: the recorded
# pid is defunct or gone, nothing is listening on the session's port, and
# the card is empty.
# ---------------------------------------------------------------------------

#: A card holding less than this is serving nothing. The pinned q4km server
#: resides at ~18.5 GB, so this is nowhere near a close call; the threshold
#: exists only to tolerate a display/compositor's few MiB.
GPU_IDLE_MEMORY_MIB = 512.0


def read_gpu_occupancy(*, run: Callable[..., object] | None = None) -> dict[str, object]:
    """What the card is holding right now, as nvidia-smi reports it.

    TWO queries, because on WSL2 the compute-process table is not
    trustworthy: ``--query-compute-apps`` comes back empty on this host even
    while an 18.5 GB llama-server is resident, so "no process listed" alone
    is not evidence of an empty card. ``memory.used`` is the better of the
    two -- it is the number the coordinator read by hand ("nvidia-smi
    0 MiB") before writing each manual stop record, and the one
    ``scripts/serving_monitor.py`` samples. The process list is still
    reported, because when it DOES list something that is decisive evidence
    in the other direction.

    Neither reading is trusted ALONE, and this is why: ``scripts/
    run_arm_sequence.sh::gpu_is_clean`` records a 2026-08-10 measurement in
    which a llama-server with the model resident and answering /health
    reported "0 MiB" through the WSL2 dxgkrnl paravirtualisation path,
    minutes after the same process reported 23,312 MiB. An intermittently
    low reading can only WEAKEN this corroborating condition; the verdict in
    :func:`observe_session_process` rests on the pid state and the silent
    port, which cannot both be wrong about a server that is still serving.

    Never raises: a host with no nvidia-smi returns ``available: False`` with
    the error, and the caller refuses to declare anything stale on that
    basis rather than guessing.
    """

    import subprocess  # noqa: PLC0415 (CLI-only)

    runner = run if run is not None else subprocess.run

    def query(flag: str) -> tuple[bool, list[str], str | None]:
        try:
            completed = runner(
                ["nvidia-smi", flag, "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return False, [], f"{type(error).__name__}: {error}"
        returncode = getattr(completed, "returncode", None)
        if not isinstance(returncode, int) or returncode != 0:
            detail = str(getattr(completed, "stderr", "") or "").strip()
            return False, [], detail[:200] or f"nvidia-smi {flag} exited {returncode!r}"
        rows = [
            row.strip()
            for row in str(getattr(completed, "stdout", "") or "").splitlines()
            if row.strip()
        ]
        return True, rows, None

    memory_ok, memory_rows, memory_error = query("--query-gpu=memory.used")
    apps_ok, app_rows, apps_error = query("--query-compute-apps=pid,used_memory,process_name")
    memory_used: float | None = None
    if memory_ok and memory_rows:
        try:
            memory_used = float(memory_rows[0].split(",")[0].strip())
        except ValueError:
            memory_used = None
    return {
        "available": bool(memory_ok and memory_used is not None),
        "memory_used_mib": memory_used,
        "compute_processes": list(app_rows) if apps_ok else None,
        "error": memory_error or apps_error,
    }


# ---------------------------------------------------------------------------
# HOST memory (E7c, 2026-09-07 incident): the VM's own 20 GB GGUF mmap plus
# page cache filled the 56 GB the WSL VM was then allowed, Windows ran out of
# headroom around it, and the Claude Code host watchdog killed the serving
# wrapper and its llama-server child -- the KC-E1 flight aborted at 42/44
# calls with no seal. Neither side alone would have shown this coming: the VM
# side (``/proc/meminfo``) never runs low (the VM itself has headroom), and
# nothing before this read the WINDOWS side at all. `.wslconfig` was lowered
# to ``memory=44GB`` with ``[experimental] autoMemoryReclaim=gradual``
# afterwards; this section is what makes the next flight not blind to either
# side again.
# ---------------------------------------------------------------------------

#: The physical-memory wire fields report memory in KiB; ``vmmemWSL``'s working set in
#: bytes. Both are converted to GiB here (binary, matching this module's other
#: size fields such as ``GPU_IDLE_MEMORY_MIB``), so "GB" below always means
#: GiB.
_KIB_PER_GIB = 1024.0 * 1024.0
_BYTES_PER_GIB = 1024.0**3

#: Query physical memory through the Windows .NET ComputerInfo API. Avoid a
#: WMI/CIM round trip on every five-second guard sample. Keep one bounded
#: interop process and the historical KiB wire fields; never reuse old values.
_HOST_MEMORY_POWERSHELL_SCRIPT = (
    "$ErrorActionPreference='Stop'; "
    "Add-Type -AssemblyName Microsoft.VisualBasic; "
    "$memoryInfo = New-Object Microsoft.VisualBasic.Devices.ComputerInfo; "
    "$totalKiB = $memoryInfo.TotalPhysicalMemory / 1024; "
    "$freeKiB = $memoryInfo.AvailablePhysicalMemory / 1024; "
    "$vmmemWs = Get-Process -Name 'vmmem*' -ErrorAction SilentlyContinue | "
    "Select-Object -First 1 -ExpandProperty WorkingSet64; "
    "[PSCustomObject]@{"
    "TotalVisibleMemorySize=$totalKiB;"
    "FreePhysicalMemory=$freeKiB;"
    "VmmemWorkingSet64=$vmmemWs"
    "} | ConvertTo-Json -Compress"
)

#: The WSL interop call is capped at 8 seconds: it is sampled every monitor
#: interval, and a hung ``powershell.exe`` must never stall the monitor loop
#: (or a flight's contact window) waiting on the host side.
_HOST_MEMORY_POWERSHELL_TIMEOUT_SECONDS = 8

#: WSL login shells on the study host do not carry the Windows PATH
#: (``which powershell.exe`` is empty there, measured 2026-09-07), while the
#: interop binary itself is always reachable at its canonical mount. PATH is
#: tried first so a test or a differently configured host can shadow it.
_HOST_MEMORY_POWERSHELL_FALLBACK = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"


def _powershell_executable() -> str:
    """``powershell.exe`` from PATH, else the canonical WSL interop mount when
    that file exists, else the bare name (so the caller's ``FileNotFoundError``
    branch still fails soft)."""

    import shutil  # noqa: PLC0415 (CLI-only)

    found = shutil.which("powershell.exe")
    if found:
        return found
    if Path(_HOST_MEMORY_POWERSHELL_FALLBACK).is_file():
        return _HOST_MEMORY_POWERSHELL_FALLBACK
    return "powershell.exe"


def _read_windows_memory(
    *, run: Callable[..., object], errors: list[str] | None = None
) -> dict[str, float | None] | None:
    """Windows total/free GB and the ``vmmemWSL`` working set GB, via the ONE
    interop call above, or ``None`` when the interop is unavailable -- no
    ``powershell.exe`` on PATH, a non-zero exit, a timeout, or output that is
    not the JSON object the script above always emits. This probe fails
    SOFT, never raises: a host with WSL interop disabled (or a Linux-only
    test/CI host) must keep sampling the VM side instead of dying.
    """

    import subprocess  # noqa: PLC0415 (CLI-only)

    def fail(reason):
        if errors is not None:
            errors.append(reason)
        return None

    try:
        completed = run(
            [
                _powershell_executable(),
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                _HOST_MEMORY_POWERSHELL_SCRIPT,
            ],
            capture_output=True,
            text=True,
            timeout=_HOST_MEMORY_POWERSHELL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return fail("timeout")
    except OSError as error:
        return fail("os-error:" + type(error).__name__)
    except subprocess.SubprocessError:
        return fail("subprocess-error")
    returncode = getattr(completed, "returncode", None)
    if isinstance(returncode, bool) or not isinstance(returncode, int) or returncode != 0:
        return fail("exit-nonzero")
    try:
        parsed = json.loads(str(getattr(completed, "stdout", "") or "").strip())
    except json.JSONDecodeError:
        return fail("invalid-json")
    if not isinstance(parsed, Mapping):
        return fail("not-object")

    def _field(key: str) -> float | None:
        value = parsed.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value) if math.isfinite(value) and value >= 0 else None

    total_kib = _field("TotalVisibleMemorySize")
    free_kib = _field("FreePhysicalMemory")
    vmmem_bytes = _field("VmmemWorkingSet64")
    if free_kib is None:
        fail("invalid-free-memory")
    return {
        "host_total_gb": (total_kib / _KIB_PER_GIB) if total_kib is not None else None,
        "host_free_gb": (free_kib / _KIB_PER_GIB) if free_kib is not None else None,
        "vmmem_ws_gb": (vmmem_bytes / _BYTES_PER_GIB) if vmmem_bytes is not None else None,
    }


def _read_vm_memory(meminfo_path: Path) -> dict[str, float | None] | None:
    """This WSL VM's own ``MemTotal``/``MemAvailable`` from ``/proc/meminfo``
    (kB, per the kernel's own convention), or ``None`` when the file cannot
    be read -- any non-Linux host, most plainly."""

    try:
        text = Path(meminfo_path).read_text(encoding="utf-8")
    except OSError:
        return None
    values: dict[str, float] = {}
    for line in text.splitlines():
        name, _, rest = line.partition(":")
        name = name.strip()
        if name not in ("MemTotal", "MemAvailable"):
            continue
        parts = rest.strip().split()
        if not parts:
            continue
        try:
            values[name] = float(parts[0])
        except ValueError:
            continue
    if not values:
        return None
    return {
        "vm_total_gb": (values["MemTotal"] / _KIB_PER_GIB) if "MemTotal" in values else None,
        "vm_available_gb": (
            (values["MemAvailable"] / _KIB_PER_GIB) if "MemAvailable" in values else None
        ),
    }


def read_host_memory(
    *,
    run: Callable[..., object] | None = None,
    meminfo_path: Path | str = "/proc/meminfo",
) -> dict[str, object]:
    """The host/VM memory pair the 2026-09-07 incident showed was missing:
    the VM side never looked short of memory (it had headroom of its own),
    while nothing here read the WINDOWS side at all until the host itself
    ran out and the coordinator's watchdog took the serving wrapper down
    with it.

    Always returns a dict -- never ``None`` -- so every monitor sample and
    every ``status``/``start`` reading carries a ``host_memory`` object; the
    two SIDES fail soft independently (``_read_windows_memory``,
    ``_read_vm_memory``), and ``host_memory_source`` names which side(s)
    actually answered (``"windows+vm"``, ``"windows-only"``, ``"vm-only"``,
    or ``"unavailable"``) so a sample with every field ``None`` is
    distinguishable from one where interop is simply switched off.
    """

    import subprocess  # noqa: PLC0415 (CLI-only)

    errors: list[str] = []
    windows = _read_windows_memory(
        run=run if run is not None else subprocess.run, errors=errors
    )
    vm = _read_vm_memory(Path(meminfo_path))
    if windows is not None and vm is not None:
        source = "windows+vm"
    elif windows is not None:
        source = "windows-only"
    elif vm is not None:
        source = "vm-only"
    else:
        source = "unavailable"
    return {
        "host_total_gb": windows.get("host_total_gb") if windows else None,
        "host_free_gb": windows.get("host_free_gb") if windows else None,
        "vmmem_ws_gb": windows.get("vmmem_ws_gb") if windows else None,
        "vm_total_gb": vm.get("vm_total_gb") if vm else None,
        "vm_available_gb": vm.get("vm_available_gb") if vm else None,
        "host_memory_source": source,
        "host_memory_error": errors[0] if errors else None,
    }


def observe_session_process(
    document: Mapping[str, object],
    *,
    process_state_probe: Callable[[int], str] | None = None,
    port_probe: Callable[[str, int], bool] | None = None,
    gpu_probe: Callable[[], Mapping[str, object]] | None = None,
    wait_status_probe: Callable[[int], int | None] | None = None,
) -> dict[str, object]:
    """The three ground-truth facts about a recorded serving session, plus
    the verdict they add up to.

    ``stale`` is true only when NOTHING of the session is left: the pid is
    ``defunct``/``gone``, the port answers nothing, and the card is provably
    empty. Every reason it is NOT stale is listed in ``blockers``, in the
    operator's own terms, because "refused" without the failing condition is
    what made the 2026-09-07 refusals so expensive.

    ``exit_status`` is best-effort and advisory: only the parent can reap a
    zombie, so a stopper that is not the wrapper reads the kernel's own
    ``exit_code`` field instead (see ``process._defunct_wait_status``).
    """

    from datetime import datetime, timezone  # noqa: PLC0415 (CLI-only)

    from .lifecycle import describe_wait_status  # noqa: PLC0415 (CLI-only)

    identity_value = document.get("identity")
    identity = dict(identity_value) if isinstance(identity_value, Mapping) else {}
    pid = int(document["pid"])
    host = str(identity.get("host") or "127.0.0.1")
    port = int(identity.get("port") or 0)

    state = (process_state_probe or process_state)(pid)
    listening = bool((port_probe or _port_is_listening)(host, port)) if port else False
    gpu = dict((gpu_probe or read_gpu_occupancy)())

    raw_status = None
    if state == PROCESS_STATE_DEFUNCT:
        raw_status = (wait_status_probe or _defunct_wait_status)(pid)
    exit_status = dict(describe_wait_status(raw_status))
    exit_status["source"] = (
        "/proc/<pid>/stat exit_code (advisory; the parent holds the real status)"
        if raw_status is not None
        else None
    )

    blockers: list[str] = []
    if state == PROCESS_STATE_RUNNING:
        blockers.append(f"pid {pid} is still running")
    if listening:
        blockers.append(f"something is still listening on {host}:{port}")
    if not gpu.get("available"):
        blockers.append(
            f"nvidia-smi could not be read ({gpu.get('error')}), so an empty card "
            "cannot be proven"
        )
    else:
        memory_used = gpu.get("memory_used_mib")
        if isinstance(memory_used, (int, float)) and memory_used >= GPU_IDLE_MEMORY_MIB:
            blockers.append(
                f"the card still holds {float(memory_used):.0f} MiB "
                f"(idle threshold {GPU_IDLE_MEMORY_MIB:.0f} MiB)"
            )
        processes = gpu.get("compute_processes")
        if processes:
            blockers.append(f"nvidia-smi still lists compute processes: {list(processes)!r}")

    return {
        "observed_at": datetime.now(tz=timezone.utc).isoformat(),
        "pid": pid,
        "process_state": state,
        "host": host,
        "port": port,
        "port_listening": listening,
        "gpu": gpu,
        "exit_status": exit_status,
        "stale": not blockers,
        "blockers": blockers,
    }


# ---------------------------------------------------------------------------
# The operator CLI behind ``scripts/serving_session.sh``.
#
# Every heavy import below is function-local: this module stays a light,
# stdlib-only seam for the flight runtime and the checks, and only the CLI
# path pays for reading the umbrella lock or a config fragment.
# ---------------------------------------------------------------------------

#: ``<repo>/src/speech_aware_evidence_acquisition/core/session/serving.py``
REPO_ROOT = Path(__file__).resolve().parents[4]


def _repo_root() -> Path:
    import os  # noqa: PLC0415 (CLI-only)

    override = os.environ.get("SAEA_REPO_ROOT")
    return Path(override) if override else REPO_ROOT


def _http_get_json(url: str, timeout_seconds: float) -> dict[str, object]:
    import urllib.request  # noqa: PLC0415 (CLI-only)

    with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _port_is_listening(host: str, port: int, timeout_seconds: float = 1.0) -> bool:
    import socket  # noqa: PLC0415 (CLI-only)

    try:
        with socket.create_connection((host, int(port)), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def resolve_serving_profile(repo_root: Path, model_fragment: str) -> dict[str, object]:
    """Everything ONE model fragment says about how to serve it: the merged
    ``server_args``, the runtime receipt, the role, the model root and the
    geometry -- resolved through exactly the functions a flight uses
    (``core.config.read_fragment``, :func:`merge_server_args`,
    ``core.session.load_runtime_receipt``).

    Fail-closed on the same disagreement every flight launcher already
    refuses: a fragment whose ``server_args`` ``-c``/``-np`` do not match its
    own declared ``serving_geometry``.
    """

    from ..config import (  # noqa: PLC0415 (CLI-only)
        fragment_hash,
        model_materialization_root,
        read_fragment,
        resolve_runtime_receipt_path,
        runtime_receipt_relpath,
    )
    from . import load_runtime_receipt  # noqa: PLC0415 (CLI-only)
    from ..data_root_placeholder import expand_data_root  # noqa: PLC0415 (CLI-only)
    from .paths import _sha256_file  # noqa: PLC0415 (CLI-only)

    values = read_fragment(repo_root, "model", model_fragment)
    server_args = [str(value) for value in values.get("server_args", ())]
    if "-c" not in server_args or "-np" not in server_args:
        raise ServingSessionError(
            f"model fragment {model_fragment!r} must declare -c and -np in server_args; "
            "a serving session is exactly one (-c, -np) geometry"
        )
    declared_c = int(server_args[server_args.index("-c") + 1])
    declared_np = int(server_args[server_args.index("-np") + 1])
    if declared_np <= 0 or declared_c % declared_np != 0:
        raise ServingSessionError(
            f"model fragment {model_fragment!r} declares -c {declared_c} -np {declared_np}; "
            "-c must be a positive multiple of -np (a slot's window is -c / -np)"
        )
    # ``server_args`` is the authority for the SERVING geometry, because it is
    # literally what llama-server is handed. Most fragments (the SLURP/
    # Earnings hbmfree family, for one) declare no ``serving_geometry`` key at
    # all -- for those, the adapter's own class constants are the flight-side
    # geometry and the fragment's -c/-np the server-side one. A fragment that
    # DOES declare the key is cross-checked against its own flags, exactly as
    # the flight launchers already do (scripts/flights/run_e22_esb_cell.py),
    # so a drifting pair is refused rather than silently served.
    slots, slot_tokens = declared_np, declared_c // declared_np
    declared_geometry = values.get("serving_geometry")
    if declared_geometry is not None:
        if not isinstance(declared_geometry, Mapping) or set(declared_geometry) != {
            "slots",
            "slot_tokens",
            "max_tokens",
        }:
            raise ServingSessionError(
                f"model fragment {model_fragment!r} declares a serving_geometry that is not "
                "an exact {slots, slot_tokens, max_tokens} object"
            )
        if (
            int(declared_geometry["slots"]) != slots
            or int(declared_geometry["slot_tokens"]) != slot_tokens
        ):
            raise ServingSessionError(
                f"model fragment {model_fragment!r} server_args (-c {declared_c} -np "
                f"{declared_np}) disagree with its declared serving_geometry "
                f"{dict(declared_geometry)!r}"
            )
    decoding = values.get("decoding_params")
    max_tokens = (
        declared_geometry["max_tokens"]
        if isinstance(declared_geometry, Mapping)
        else (decoding.get("max_tokens") if isinstance(decoding, Mapping) else None)
    )
    geometry = {"slots": slots, "slot_tokens": slot_tokens, "max_tokens": max_tokens}
    receipt_path = resolve_runtime_receipt_path(repo_root, values)
    runtime_receipt = load_runtime_receipt(receipt_path)
    return {
        "values": values,
        "model_fragment": model_fragment,
        "model_fragment_sha256": fragment_hash(values),
        "serving_geometry": dict(geometry),
        "extra_argv": merge_server_args(
            server_args, slots=slots, context_tokens=slots * slot_tokens
        ),
        "server_env": {
            str(key): str(value) for key, value in dict(expand_data_root(values.get("server_env", {}))).items()
        },
        "runtime_receipt": runtime_receipt,
        "runtime_receipt_relpath": runtime_receipt_relpath(values),
        "runtime_receipt_sha256": _sha256_file(receipt_path),
        "session_role": str(runtime_receipt.get("role", "legacy")),
        "model_root": model_materialization_root(values),
    }


def _resident_refusal(
    session_dir: Path,
    document: Mapping[str, object],
    *,
    observer: Callable[..., Mapping[str, object]] | None = None,
) -> str:
    """Why ``start`` refuses, and what to do about it.

    The old message ("already recorded as resident ... stop it before
    starting another") was true and useless on 2026-09-07: the session it
    named could NOT be stopped, because its pid was a zombie every stop
    refused. A refusal that names the observed state and the remedy is the
    difference between a 30-second fix and a hand-written record.
    """

    session_id = str(document.get("session_id"))
    head = (
        f"serving session {session_id!r} is already recorded as resident at {session_dir}"
    )
    observation = (observer or observe_session_process)(document)
    state = observation["process_state"]
    if state == PROCESS_STATE_RUNNING:
        return f"{head}; stop it before starting another (scripts/serving_session.sh stop)"
    remedy = (
        "record the stop with `bash scripts/serving_session.sh stop --stale "
        f"--session-id {session_id}`"
    )
    if observation["stale"]:
        return (
            f"{head}, but its pid {observation['pid']} is {state} and nothing is left of "
            f"the session (port {observation['host']}:{observation['port']} silent, card "
            f"empty) -- {remedy}, then start this geometry again"
        )
    return (
        f"{head}; its pid {observation['pid']} is {state}, but the session is not yet "
        "provably gone ("
        + "; ".join(str(reason) for reason in observation["blockers"])
        + f") -- resolve that first, then {remedy}"
    )


def _validate_host_memory_policy(min_host_free_gb: float, margin_gb: float = 0.0) -> None:
    for name, value, minimum in (
        ("min_host_free_gb", min_host_free_gb, 4), ("margin_gb", margin_gb, 0)
    ):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < minimum):
            raise ServingSessionError(f"{name} must be finite and at least {minimum} GiB")
    if not math.isfinite(min_host_free_gb + margin_gb):
        raise ServingSessionError("combined host memory minimum must be finite")


def _refuse_low_host_memory(min_host_free_gb: float) -> None:
    """Refuse to start a new 18.5 GB resident server on a host that does not
    provably have room for it (E7c, the 2026-09-07 incident: the VM's mmap
    plus page cache filled the host's headroom and the coordinator's
    watchdog killed the serving wrapper mid-flight).

    Fails OPEN when the reading itself is unavailable (WSL interop off, no
    ``powershell.exe``): a probe that cannot prove the host is short of
    memory must never block a start on that basis, exactly as an unreadable
    GPU never proves staleness in :func:`observe_session_process`.
    """

    _validate_host_memory_policy(min_host_free_gb)
    host_memory = read_host_memory()
    free_gb = host_memory.get("host_free_gb")
    if isinstance(free_gb, bool) or not isinstance(free_gb, (int, float)):
        return
    if float(free_gb) < min_host_free_gb:
        raise ServingSessionError(
            f"refusing to start: the host's free memory is {float(free_gb):.1f} GB, below "
            f"--min-host-free-gb {float(min_host_free_gb):.1f} GB -- a serving wrapper is a "
            "host-watchdog target (2026-09-07: the VM's mmap plus page cache filled the "
            "host's headroom and the watchdog killed the wrapper mid-flight); free host "
            "memory, or lower the VM's .wslconfig memory cap, before starting this geometry"
        )


#: ``host-memory`` exits with this when the reading PROVES the start guard
#: would refuse -- distinct from 0 (admits, or the reading is unavailable and
#: ``start`` fails open) and from 2 (a usage or configuration refusal).
HOST_MEMORY_SHORT_EXIT = 4


def host_memory_verdict(
    host_memory: Mapping[str, object], *, min_host_free_gb: float, margin_gb: float = 0.0
) -> dict[str, object]:
    """Would ``start``'s host-memory guard admit a new server right now?

    ``admits`` is ``True``/``False`` on a numeric Windows reading and ``None``
    when the reading is unavailable -- the same fail-open rule as
    :func:`_refuse_low_host_memory`, so a swap never refuses on a reading the
    start itself would ignore. ``margin_gb`` is headroom demanded ON TOP of
    the guard: a geometry swap reads the host while the OLD server is still
    resident and must not stop it on a reading that sits exactly at the line
    (2026-09-27: 11.7 GB and 10.1 GB against 12.0 left the card empty twice).
    """

    _validate_host_memory_policy(min_host_free_gb, margin_gb)
    free_gb = host_memory.get("host_free_gb")
    required = float(min_host_free_gb) + float(margin_gb)
    numeric = not isinstance(free_gb, bool) and isinstance(free_gb, (int, float))
    return {
        "schema": "saea-serving-host-memory-check-v1",
        "host_free_gb": float(free_gb) if numeric else None,
        "min_host_free_gb": float(min_host_free_gb),
        "margin_gb": float(margin_gb),
        "required_gb": required,
        "admits": (float(free_gb) >= required) if numeric else None,
        "host_memory": dict(host_memory),
    }


def _host_memory(args) -> int:
    """Print the start guard's verdict on the CURRENT host reading without
    starting anything (scripts/flights/batch/serving_swap.sh asks this BEFORE
    it stops the resident geometry)."""

    verdict = host_memory_verdict(
        read_host_memory(), min_host_free_gb=args.min_host_free_gb, margin_gb=args.margin_gb
    )
    print(json.dumps(verdict, ensure_ascii=False, sort_keys=True))
    return HOST_MEMORY_SHORT_EXIT if verdict["admits"] is False else 0


def _start(args) -> int:
    from datetime import datetime, timezone  # noqa: PLC0415 (CLI-only)

    from ...data.lock import data_root as resolve_data_root  # noqa: PLC0415 (CLI-only)
    from . import start_session, stop_session  # noqa: PLC0415 (CLI-only)

    _refuse_low_host_memory(args.min_host_free_gb)

    repo_root = _repo_root()
    data_root = resolve_data_root()
    profile = resolve_serving_profile(repo_root, args.model_fragment)
    from .resource_guard import assert_start, resource_limits
    limits = resource_limits(profile.get("values", {}))
    if limits is not None:
        assert_start(limits)

    resident = find_resident_session(data_root)
    if resident is not None:
        raise ServingSessionError(_resident_refusal(resident[0], resident[1]))
    if _port_is_listening(args.host, args.port):
        raise ServingSessionError(
            f"something is already listening on {args.host}:{args.port}; refusing to "
            "start a second server (the resident one may be an orphan -- check it "
            "before killing it)"
        )

    session_id = args.session_id or (
        f"serving-{args.model_fragment}-"
        f"{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    session_dir = serving_session_dir(data_root, session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = session_dir / SESSION_RECEIPT_NAME
    log_path = session_dir / SERVER_LOG_NAME
    monitor_path = session_dir / MONITOR_JSONL_NAME

    session = start_session(
        runtime_root=Path(args.runtime_root),
        data_root=data_root,
        runtime_receipt=profile["runtime_receipt"],
        host=args.host,
        port=args.port,
        session_id=session_id,
        extra_argv=tuple(profile["extra_argv"]),
        extra_env=dict(profile["server_env"]),
        receipt_path=receipt_path,
        server_log_path=log_path,
        role=str(profile["session_role"]),
        model_root=(
            Path(str(profile["model_root"])) if profile["model_root"] is not None else None
        ),
    )
    # Everything between the spawn and the written session.json runs under
    # this guard: a failure here (an unreachable /props, an unwritable
    # session directory) would otherwise leave an 18.5 GB llama-server
    # resident with NO record naming it -- an orphan nothing can attach to
    # and nothing knows to stop.
    try:
        if limits is not None:
            from .resource_guard import ResourceAdmissionError, publish_sample
            resource = publish_sample(session_dir, session, limits)
            if resource["decision"] != "admit":
                raise ResourceAdmissionError("post-load resources do not admit a flight")
        props = _http_get_json(f"http://{args.host}:{args.port}/props", 30.0)
        document = _session_document_for(
            args, profile=profile, session=session, session_id=session_id,
            props=props, receipt_path=receipt_path, log_path=log_path,
            monitor_path=monitor_path,
        )
        write_json_document(session_dir / SESSION_DOCUMENT_NAME, document)
    except BaseException:
        _write_stop_document(
            session_dir,
            session_id=session_id,
            stop_receipt=stop_session(
                session,
                runtime_receipt=profile["runtime_receipt"],
                runtime_root=Path(args.runtime_root),
                force_after_timeout=True,
            ),
            monitor_path=monitor_path,
        )
        raise
    print(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True))
    return _hold_session_open(
        args, profile=profile, session=session, session_id=session_id,
        session_dir=session_dir, monitor_path=monitor_path,
    )


def _session_document_for(
    args,
    *,
    profile: Mapping[str, object],
    session,
    session_id: str,
    props: Mapping[str, object] | None,
    receipt_path: Path,
    log_path: Path,
    monitor_path: Path,
) -> dict[str, object]:
    identity = serving_identity(
        model_fragment=str(profile["model_fragment"]),
        model_fragment_sha256=str(profile["model_fragment_sha256"]),
        runtime_receipt_relpath=str(profile["runtime_receipt_relpath"]),
        runtime_receipt_sha256=str(profile["runtime_receipt_sha256"]),
        binary_path=session.binary_path,
        binary_sha256=session.binary_sha256,
        model_files=[
            {"path": entry.path, "sha256": entry.sha256} for entry in session.model_files
        ],
        session_role=str(profile["session_role"]),
        model_root=profile["model_root"],
        server_argv=session.argv,
        server_env=dict(profile["server_env"]),
        host=args.host,
        port=args.port,
        props=props,
    )
    return build_session_document(
        session_id=session_id,
        identity=identity,
        pid=session.pid,
        started_at=session.started_at,
        serving_geometry=dict(profile["serving_geometry"]),
        props=props,
        session_receipt_path=str(receipt_path),
        server_log_path=str(log_path),
        monitor_path=str(monitor_path),
    )


def _hold_session_open(
    args,
    *,
    profile: Mapping[str, object],
    session,
    session_id: str,
    session_dir: Path,
    monitor_path: Path,
) -> int:
    """Stay in the foreground for the whole life of the session, then stop it.

    The coordinator runs this as a background LIVE wrapper: a detached WSL
    job dies with its shell, so the wrapper must outlive every flight that
    attaches (it also owns the pipe-draining thread that keeps server.log
    flowing). Returns 0 when the operator asked it to stop, 1 when the
    server exited on its own -- an unrequested exit is a failure, and the
    exit status is what a coordinator's job monitor sees.

    E7b defect 2 (2026-09-07): this loop is the server's PARENT, and until
    now it did none of a parent's three jobs. It polled ``_pid_alive``,
    which a zombie satisfies forever, so when llama-server exited the loop
    kept spinning: the child was never reaped (leaving the ``<defunct>``
    entry that then made every ``stop`` refuse -- see
    :func:`observe_session_process`), no ``session-stop.json`` was written,
    and the wrapper never exited, so nothing a coordinator watches could
    tell that the session was over. It now reaps the child, records the stop
    with the reaped exit status, and exits non-zero with ONE operator line.

    Deliberately NOT added: a ``--restart-on-exit`` option. A server that
    exits unasked is a fact the coordinator must see -- an OOM, a crash, a
    stray signal -- and restarting it silently would hide exactly the thing
    that needs looking at.
    """

    import signal  # noqa: PLC0415 (CLI-only)
    import sys  # noqa: PLC0415 (CLI-only)
    import time  # noqa: PLC0415 (CLI-only)
    from datetime import datetime, timezone  # noqa: PLC0415 (CLI-only)

    from . import stop_session  # noqa: PLC0415 (CLI-only)
    from .lifecycle import describe_wait_status, reap_child  # noqa: PLC0415 (CLI-only)

    from .resource_guard import publish_sample, resource_limits
    limits = resource_limits(profile.get("values", {}))
    resource_failure = None
    stopping = {"asked": False}

    def _on_signal(_signum, _frame) -> None:
        stopping["asked"] = True

    installed: list[tuple[int, object]] = []
    for signal_name in ("SIGTERM", "SIGINT", "SIGHUP"):
        number = getattr(signal, signal_name, None)
        if number is not None:
            installed.append((number, signal.signal(number, _on_signal)))

    try:
        exit_status: int | None = None
        exited_unasked = False
        while not stopping["asked"]:
            # Reaping FIRST, because this process is the parent: waitpid is
            # the only thing that turns an exited child into a real exit
            # status instead of a zombie, and it is non-blocking here.
            reaped, exit_status = reap_child(session.pid)
            if reaped:
                exited_unasked = True
                break
            state = process_state(session.pid)
            if state in (PROCESS_STATE_GONE, PROCESS_STATE_DEFUNCT):
                # Gone: already reaped by someone else. Defunct without a
                # successful reap: not this process's child after all (an
                # adopted pid). Either way the server has exited.
                exited_unasked = True
                break
            if limits is not None:
                try:
                    resource = publish_sample(session_dir, session, limits)
                except Exception as error:
                    resource = {"decision": "stop", "reasons": ["resource-observer-failed"],
                                "error_type": type(error).__name__}
                if resource["decision"] == "stop":
                    resource_failure = resource
                    exited_unasked = True
                    break
            time.sleep(1.0)

        server_exit = None
        if exited_unasked:
            server_exit = {
                "reason": "resource-guard" if resource_failure is not None else "server-exited",
                **({"resource": resource_failure} if resource_failure is not None else {}),
                "reaped": exit_status is not None,
                "status": describe_wait_status(exit_status),
                "detected_at": datetime.now(tz=timezone.utc).isoformat(),
            }

        with _session_stop_lock(session_dir):
            explicit_stop = _read_explicit_stop_document(
                session_dir, session=session, runtime_receipt=profile["runtime_receipt"]
            )
            if explicit_stop is not None:
                stop_document = explicit_stop
                exited_unasked = False
            else:
                stop_document = _write_stop_document(
                    session_dir,
                    session_id=session_id,
                    stop_receipt=stop_session(
                        session,
                        runtime_receipt=profile["runtime_receipt"],
                        runtime_root=Path(args.runtime_root),
                        force_after_timeout=True,
                    ),
                    monitor_path=monitor_path,
                    server_exit=server_exit,
                )
        print(json.dumps(stop_document, ensure_ascii=False, indent=2, sort_keys=True))
        if not exited_unasked:
            return 0
        print(
            f"serving_session: server pid {session.pid} of session {session_id!r} exited "
            f"or was stopped by {server_exit['reason']} ({server_exit['status']['description']}); "
            f"the stop is recorded in "
            f"{session_dir / SESSION_STOP_NAME} and nothing was restarted",
            file=sys.stderr,
        )
        return 1
    finally:
        # Hand the signals back: everything above this point is the only
        # window in which they mean "stop the session" rather than "stop
        # this process".
        for number, handler in installed:
            signal.signal(number, handler)


def _write_stop_document(
    session_dir: Path,
    *,
    session_id: str,
    stop_receipt: Mapping[str, object] | None,
    monitor_path: Path,
    stale: bool = False,
    observed: Mapping[str, object] | None = None,
    server_exit: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Write ``session-stop.json`` -- the file whose PRESENCE is what makes a
    session no longer resident.

    Three keys were added on 2026-09-07 (E7b) without bumping the schema,
    because nothing reads this document's shape -- ``find_resident_session``
    only tests that the file exists:

    ``stale``        the stop was RECORDED, not performed: nothing was left
                     to signal (:func:`observe_session_process` proved it).
    ``observed``     that proof, in full.
    ``server_exit``  the wrapper's own account of a server that exited on its
                     own, including the reaped wait status.
    """

    from datetime import datetime, timezone  # noqa: PLC0415 (CLI-only)

    document = {
        "schema": SERVING_SESSION_STOP_SCHEMA,
        "study": STUDY_SLUG,
        "session_id": session_id,
        "stopped_at": datetime.now(tz=timezone.utc).isoformat(),
        "stop_receipt": dict(stop_receipt) if stop_receipt is not None else None,
        "stale": bool(stale),
        "observed": dict(observed) if observed is not None else None,
        "server_exit": dict(server_exit) if server_exit is not None else None,
        # The whole session's monitor summary, so the day's GPU accounting
        # survives the session it describes.
        "monitor_summary": summarize_monitor_file(monitor_path),
    }
    write_json_document(session_dir / SESSION_STOP_NAME, document)
    return document


def _resolve_session(data_root: Path, session_id: str | None) -> tuple[Path, dict[str, object]]:
    if session_id:
        session_dir = serving_session_dir(data_root, session_id)
        return session_dir, read_session_document(session_dir / SESSION_DOCUMENT_NAME)
    resident = find_resident_session(data_root)
    if resident is None:
        raise ServingSessionError(
            f"no resident serving session under {serving_root(data_root)}"
        )
    return resident


def _status(args) -> int:
    from ...data.lock import data_root as resolve_data_root  # noqa: PLC0415 (CLI-only)
    from .process import _pid_alive  # noqa: PLC0415 (CLI-only)

    data_root = resolve_data_root()
    session_dir, document = _resolve_session(data_root, args.session_id)
    samples = read_monitor_samples(session_dir / MONITOR_JSONL_NAME)
    # ``pid_alive`` is kept (it is what every earlier receipt reported) but
    # it is no longer the answer: it says "alive" for a zombie. The state
    # beside it -- running / defunct / gone -- plus the port and card
    # readings are what an operator has to see, and are exactly the facts
    # ``stop`` itself acts on.
    observation = observe_session_process(document)
    print(
        json.dumps(
            {
                "session": document,
                "pid_alive": _pid_alive(int(document["pid"])),
                "process_state": observation["process_state"],
                "observed": observation,
                "stopped": (session_dir / SESSION_STOP_NAME).is_file(),
                "monitor_sample_count": len(samples),
                "last_monitor_sample": samples[-1] if samples else None,
                "monitor_summary": summarize_monitor_samples(samples),
                # The CURRENT host reading (E7c), not the window's: an
                # operator running `status` wants to know whether the host
                # has room right now, same question `start` asks before it
                # spawns a second 18.5 GB server.
                "host_memory": read_host_memory(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


#: ``resident`` exits with this when NOTHING is resident -- distinct from 0
#: (a session is resident) and from 2 (the question could not be answered).
#: A killer script must be able to tell "no session" from "cannot tell".
NO_RESIDENT_SESSION_EXIT = 3


def _resident(args) -> int:
    """Is the coordinator's session resident? -- for scripts that would
    otherwise kill llama-server blindly.

    ``scripts/run_arm_sequence.sh`` runs ``pkill -9 -f llama-server`` around
    every arm. That predates the always-on session (E7) and would take an
    18.5 GB resident server away from every queued flight, with no stop
    record and a zombie left behind -- the exact damage E7b is about. It now
    asks this first, and refuses the arm rather than killing.
    """

    from ...data.lock import data_root as resolve_data_root  # noqa: PLC0415 (CLI-only)

    data_root = resolve_data_root()
    resident = find_resident_session(data_root)
    if resident is None:
        print(
            json.dumps(
                {"resident": False, "serving_root": str(serving_root(data_root))},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return NO_RESIDENT_SESSION_EXIT
    session_dir, document = resident
    observation = observe_session_process(document)
    print(
        json.dumps(
            {
                "resident": True,
                "session_id": document.get("session_id"),
                "session_dir": str(session_dir),
                "process_state": observation["process_state"],
                "stale": observation["stale"],
                "blockers": observation["blockers"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _stale_stop(
    session_dir: Path, document: Mapping[str, object], observation: Mapping[str, object]
) -> int:
    """Record the stop of a session there is nothing left to stop.

    Refuses unless :func:`observe_session_process` proved every one of its
    three conditions -- a stop record is a durable claim that the geometry is
    free, and writing one while a server is still holding the card would let
    ``start`` bring up a second 18.5 GB server on top of it.
    """

    session_id = str(document.get("session_id"))
    if not observation["stale"]:
        raise ServingSessionError(
            f"serving session {session_id!r} is not stale: "
            + "; ".join(str(reason) for reason in observation["blockers"])
            + " -- refusing to record a stop for a session that is still there"
        )
    stop_document = _write_stop_document(
        session_dir,
        session_id=session_id,
        stop_receipt=None,
        monitor_path=session_dir / MONITOR_JSONL_NAME,
        stale=True,
        observed=observation,
    )
    print(json.dumps(stop_document, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _stop(args) -> int:
    from ...data.lock import data_root as resolve_data_root  # noqa: PLC0415 (CLI-only)
    from . import attach_session, load_runtime_receipt, stop_session  # noqa: PLC0415

    data_root = resolve_data_root()
    session_dir, document = _resolve_session(data_root, args.session_id)
    observation = observe_session_process(document)

    # A defunct or gone pid cannot be attached to (``/proc/<pid>/exe`` is
    # unreadable for a zombie, so every I5 check refuses it) and cannot be
    # signalled into stopping any harder than it already has. Recording the
    # stop is then the ONLY correct action, and it is taken automatically --
    # 2026-09-07 cost the coordinator two hand-written records for exactly
    # this state. ``--stale`` asks for that path explicitly and refuses to
    # fall back to signalling.
    if args.stale or observation["process_state"] in (PROCESS_STATE_DEFUNCT, PROCESS_STATE_GONE):
        return _stale_stop(session_dir, document, observation)

    repo_root = _repo_root()
    identity = document["identity"]
    runtime_receipt = load_runtime_receipt(
        repo_root / "docs" / str(identity["runtime_receipt_relpath"])
    )
    session = attach_session(
        session_dir / SESSION_RECEIPT_NAME,
        runtime_receipt=runtime_receipt,
        runtime_root=Path(args.runtime_root),
    )
    with _session_stop_lock(session_dir):
        stop_document = _write_stop_document(
            session_dir,
            session_id=str(document["session_id"]),
            stop_receipt=stop_session(
                session,
                runtime_receipt=runtime_receipt,
                runtime_root=Path(args.runtime_root),
                force_after_timeout=True,
            ),
            monitor_path=session_dir / MONITOR_JSONL_NAME,
        )
    print(json.dumps(stop_document, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser():
    import argparse  # noqa: PLC0415 (CLI-only)

    # The shared options live on the SUBPARSERS only, never on both: an
    # option declared in both places has its top-level value silently
    # overwritten by the subparser's own default (argparse semantics), which
    # would turn `--port 9001 start ...` into a session on 8080.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--host", default="127.0.0.1")
    common.add_argument("--port", type=int, default=8080)
    common.add_argument(
        "--runtime-root",
        default="/home/chao",
        help="root holding the runtime-receipt-pinned llama.cpp checkout",
    )
    common.add_argument(
        "--session-id",
        default=None,
        help="serving session id (start: generated when absent; status/stop: the resident one)",
    )

    parser = argparse.ArgumentParser(
        prog="saea-serving-session",
        description=(
            "Start, inspect and stop the ONE always-on llama-server every flight "
            "attaches to (owner rule 2026-09-07)."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser(
        "start",
        parents=[common],
        help="start the session and stay in the foreground",
    )
    start.add_argument("model_fragment", help="a configs/model/<name>.json fragment id")
    start.add_argument(
        "--min-host-free-gb",
        type=float,
        default=4.0,
        help=(
            "refuse to start when the Windows host's free memory is below this (owner "
            "cap, 2026-09-07: a serving wrapper is a host-watchdog target, so the running "
            "cap must always leave this much for Windows)"
        ),
    )
    start.set_defaults(handler=_start)
    subparsers.add_parser(
        "status", parents=[common], help="print the session document and the last sample"
    ).set_defaults(handler=_status)
    subparsers.add_parser(
        "resident",
        parents=[common],
        help=(
            "exit 0 when a serving session is resident, "
            f"{NO_RESIDENT_SESSION_EXIT} when none is (for scripts that kill servers)"
        ),
    ).set_defaults(handler=_resident)
    host_memory = subparsers.add_parser(
        "host-memory",
        help=(
            "print whether start's host-memory guard would admit a new server now; exit "
            f"{HOST_MEMORY_SHORT_EXIT} when the reading proves it would refuse"
        ),
    )
    host_memory.add_argument("--min-host-free-gb", type=float, default=4.0)
    host_memory.add_argument(
        "--margin-gb",
        type=float,
        default=0.0,
        help="headroom demanded on top of --min-host-free-gb (a swap reads before its stop)",
    )
    host_memory.set_defaults(handler=_host_memory)
    stop = subparsers.add_parser(
        "stop", parents=[common], help="stop the session and write session-stop.json"
    )
    stop.add_argument(
        "--stale",
        action="store_true",
        help=(
            "record the stop of a session whose server is already gone or defunct "
            "(refuses unless the pid, the port and the card all agree it is gone); "
            "taken automatically when the recorded pid is defunct or gone"
        ),
    )
    stop.set_defaults(handler=_stop)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """A refusal is an OPERATOR message, not a traceback: every fail-closed
    condition this CLI can hit (a fragment that declares no geometry, a
    session already resident, a port already taken, a dead session receipt)
    is a thing the coordinator must act on, so it is printed as one line on
    stderr with exit status 2."""

    args = build_parser().parse_args(list(argv) if argv is not None else None)
    import sys  # noqa: PLC0415 (CLI-only)

    from ..config import ConfigError  # noqa: PLC0415 (CLI-only)

    try:
        return int(args.handler(args))
    except (SessionError, ConfigError) as error:
        print(f"serving_session: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover -- operator entry point
    raise SystemExit(main())


__all__ = [
    "GPU_IDLE_MEMORY_MIB",
    "HOST_MEMORY_SHORT_EXIT",
    "MONITOR_JSONL_NAME",
    "NO_RESIDENT_SESSION_EXIT",
    "REPO_ROOT",
    "PARKED_UTILIZATION_PERCENT",
    "SERVER_LOG_NAME",
    "SERVING_IDENTITY_FIELDS",
    "SERVING_MONITOR_SAMPLE_SCHEMA",
    "SERVING_MONITOR_SUMMARY_SCHEMA",
    "SERVING_ROOT_NAME",
    "SERVING_SESSION_SCHEMA",
    "SERVING_SESSION_STOP_SCHEMA",
    "SESSION_DOCUMENT_NAME",
    "SESSION_RECEIPT_NAME",
    "SESSION_STOP_NAME",
    "ServingIdentityMismatch",
    "ServingSessionError",
    "assert_identity_matches",
    "build_parser",
    "build_session_document",
    "find_resident_session",
    "host_memory_verdict",
    "identity_mismatches",
    "main",
    "merge_server_args",
    "observe_session_process",
    "props_identity",
    "read_gpu_occupancy",
    "read_host_memory",
    "read_monitor_samples",
    "read_session_document",
    "resolve_serving_profile",
    "serving_identity",
    "serving_root",
    "serving_session_dir",
    "summarize_monitor_file",
    "summarize_monitor_samples",
    "write_json_document",
]
