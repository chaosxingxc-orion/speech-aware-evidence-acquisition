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
    ``session-stop.json``     written by ``stop``; its presence means "not
                              resident any more"

Standard-library only, like the rest of ``core.session``: a flight runtime,
an operator script and a check may all import it without pulling ``rails``
or a heavy config path in.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Mapping, Sequence

from ...contracts import STUDY_SLUG
from . import SessionError

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
            for flag in sorted(set(session_flags) | set(required_flags)):
                if session_flags.get(flag) != required_flags.get(flag):
                    mismatches.append(
                        {
                            "field": f"server_argv[{flag}]",
                            "session": session_flags.get(flag),
                            "required": required_flags.get(flag),
                        }
                    )
            if not mismatches and list(session_value or ()) != list(required_value or ()):
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
    return summary


def summarize_monitor_file(
    path: Path, *, from_epoch: float | None = None, to_epoch: float | None = None
) -> dict[str, object]:
    """:func:`summarize_monitor_samples` over a monitor JSONL on disk."""

    return summarize_monitor_samples(
        read_monitor_samples(path), from_epoch=from_epoch, to_epoch=to_epoch
    )


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
    from .paths import _sha256_file  # noqa: PLC0415 (CLI-only)

    values = read_fragment(repo_root, "model", model_fragment)
    geometry = values.get("serving_geometry")
    if not isinstance(geometry, Mapping) or set(geometry) != {
        "slots",
        "slot_tokens",
        "max_tokens",
    }:
        raise ServingSessionError(
            f"model fragment {model_fragment!r} must declare an exact serving_geometry "
            "{slots, slot_tokens, max_tokens} object"
        )
    slots = int(geometry["slots"])
    slot_tokens = int(geometry["slot_tokens"])
    server_args = [str(value) for value in values.get("server_args", ())]
    if "-c" in server_args and "-np" in server_args:
        declared_c = int(server_args[server_args.index("-c") + 1])
        declared_np = int(server_args[server_args.index("-np") + 1])
        if declared_np != slots or declared_c != slots * slot_tokens:
            raise ServingSessionError(
                f"model fragment {model_fragment!r} server_args (-c {declared_c} -np "
                f"{declared_np}) disagree with its declared serving_geometry "
                f"{dict(geometry)!r}"
            )
    receipt_path = resolve_runtime_receipt_path(repo_root, values)
    runtime_receipt = load_runtime_receipt(receipt_path)
    return {
        "values": values,
        "model_fragment": model_fragment,
        "model_fragment_sha256": fragment_hash(values),
        "serving_geometry": {
            "slots": slots,
            "slot_tokens": slot_tokens,
            "max_tokens": int(geometry["max_tokens"]),
        },
        "extra_argv": merge_server_args(
            server_args, slots=slots, context_tokens=slots * slot_tokens
        ),
        "server_env": {
            str(key): str(value) for key, value in dict(values.get("server_env", {})).items()
        },
        "runtime_receipt": runtime_receipt,
        "runtime_receipt_relpath": runtime_receipt_relpath(values),
        "runtime_receipt_sha256": _sha256_file(receipt_path),
        "session_role": str(runtime_receipt.get("role", "legacy")),
        "model_root": model_materialization_root(values),
    }


def _start(args) -> int:
    import signal  # noqa: PLC0415 (CLI-only)
    import time  # noqa: PLC0415 (CLI-only)
    from datetime import datetime, timezone  # noqa: PLC0415 (CLI-only)

    from ...data.lock import data_root as resolve_data_root  # noqa: PLC0415 (CLI-only)
    from . import start_session, stop_session  # noqa: PLC0415 (CLI-only)
    from .process import _pid_alive  # noqa: PLC0415 (CLI-only)

    repo_root = _repo_root()
    data_root = resolve_data_root()
    profile = resolve_serving_profile(repo_root, args.model_fragment)

    resident = find_resident_session(data_root)
    if resident is not None:
        raise ServingSessionError(
            f"serving session {resident[1]['session_id']!r} is already recorded as "
            f"resident at {resident[0]}; stop it before starting another"
        )
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
    props = _http_get_json(f"http://{args.host}:{args.port}/props", 30.0)
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
    document = build_session_document(
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
    write_json_document(session_dir / SESSION_DOCUMENT_NAME, document)
    print(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True))

    # The coordinator runs this as a background LIVE wrapper: a detached WSL
    # job dies with its shell, so the wrapper must stay in the foreground for
    # the whole life of the session (it also owns the pipe-draining thread
    # that keeps server.log flowing).
    stopping = {"asked": False}

    def _on_signal(_signum, _frame) -> None:
        stopping["asked"] = True

    for signal_name in ("SIGTERM", "SIGINT", "SIGHUP"):
        handler = getattr(signal, signal_name, None)
        if handler is not None:
            signal.signal(handler, _on_signal)

    while not stopping["asked"] and _pid_alive(session.pid):
        time.sleep(1.0)

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
    )
    print(json.dumps(stop_document, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if stopping["asked"] else 1


def _write_stop_document(
    session_dir: Path,
    *,
    session_id: str,
    stop_receipt: Mapping[str, object],
    monitor_path: Path,
) -> dict[str, object]:
    from datetime import datetime, timezone  # noqa: PLC0415 (CLI-only)

    document = {
        "schema": SERVING_SESSION_STOP_SCHEMA,
        "study": STUDY_SLUG,
        "session_id": session_id,
        "stopped_at": datetime.now(tz=timezone.utc).isoformat(),
        "stop_receipt": dict(stop_receipt),
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
    print(
        json.dumps(
            {
                "session": document,
                "pid_alive": _pid_alive(int(document["pid"])),
                "stopped": (session_dir / SESSION_STOP_NAME).is_file(),
                "monitor_sample_count": len(samples),
                "last_monitor_sample": samples[-1] if samples else None,
                "monitor_summary": summarize_monitor_samples(samples),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _stop(args) -> int:
    from ...data.lock import data_root as resolve_data_root  # noqa: PLC0415 (CLI-only)
    from . import attach_session, load_runtime_receipt, stop_session  # noqa: PLC0415

    data_root = resolve_data_root()
    session_dir, document = _resolve_session(data_root, args.session_id)
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
    start.set_defaults(handler=_start)
    subparsers.add_parser(
        "status", parents=[common], help="print the session document and the last sample"
    ).set_defaults(handler=_status)
    subparsers.add_parser(
        "stop", parents=[common], help="stop the session and write session-stop.json"
    ).set_defaults(handler=_stop)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    return int(args.handler(args))


if __name__ == "__main__":  # pragma: no cover -- operator entry point
    raise SystemExit(main())


__all__ = [
    "MONITOR_JSONL_NAME",
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
    "identity_mismatches",
    "main",
    "merge_server_args",
    "props_identity",
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
