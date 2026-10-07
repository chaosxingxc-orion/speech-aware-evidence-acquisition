"""Fail-closed resource admission owned by the resident service, not a chat."""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path

from . import SessionError

SNAPSHOT_NAME = "resource-state.json"
LOG_NAME = "resource-history.jsonl"
LEGACY_SCHEMA = "saea-serving-resource-state-v1"
SCHEMA = "saea-serving-resource-state-v2"
FIELDS = {
    "schema",
    "windows_start_gib",
    "windows_admit_gib",
    "windows_stop_gib",
    "gpu_admit_free_mib",
    "gpu_stop_free_mib",
    "max_sample_age_seconds",
}


class ResourceAdmissionError(SessionError):
    """Refuse contact or stop the owned service without automatic replay."""


def _number(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value >= 0
    )


def resource_limits(values):
    if "serving_resource_limits" not in values:
        return None
    limits = values["serving_resource_limits"]
    if (
        not isinstance(limits, Mapping)
        or set(limits) != FIELDS
        or limits["schema"] != "saea-serving-resource-limits-v1"
        or not all(_number(limits[k]) for k in FIELDS - {"schema"})
    ):
        raise ResourceAdmissionError("invalid serving resource limits")
    if not (
        limits["windows_start_gib"]
        >= limits["windows_admit_gib"]
        >= limits["windows_stop_gib"]
        >= 4
        and limits["gpu_admit_free_mib"] > limits["gpu_stop_free_mib"] > 0
        and 0 < limits["max_sample_age_seconds"] <= 15
    ):
        raise ResourceAdmissionError("resource floors or freshness bounds are invalid")
    return dict(limits)


def _policy_hash(limits):
    resource_limits({"serving_resource_limits": limits})
    return hashlib.sha256(json.dumps(limits, sort_keys=True).encode()).hexdigest()


def _identity(session):
    return {
        "session_id": session.session_id,
        "pid": session.pid,
        "started_at": session.started_at,
    }


def _host():
    from .serving import read_host_memory

    return read_host_memory()


def _gpu():
    from .telemetry import read_gpu

    return read_gpu(include_capacity=True)


def _boottime():
    # Linux boot time includes suspend, unlike a process-local elapsed timer.
    # UTC remains useful for audit but can jump during WSL clock correction.
    return time.clock_gettime(time.CLOCK_BOOTTIME)


def _boot_id():
    try:
        value = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError as error:
        raise ResourceAdmissionError("resource clock boot identity unavailable") from error
    if not value:
        raise ResourceAdmissionError("resource clock boot identity unavailable")
    return value


def assert_start(limits, *, host_reader=None):
    """Reserve loading headroom separately from the post-load running floor."""
    _policy_hash(limits)
    sample = (host_reader or _host)() or {}
    available = sample.get("host_free_gb")
    if not _number(available) or available < limits["windows_start_gib"]:
        raise ResourceAdmissionError(
            "Windows loading headroom is unavailable or below its floor"
        )


def _decision(host, gpu, limits):
    available = (host or {}).get("host_free_gb")
    free_gpu = (gpu or {}).get("memory_free_mib")
    if not _number(available) or not _number(free_gpu):
        return "stop", ["resource-reading-unavailable"]
    if available < limits["windows_stop_gib"]:
        return "stop", ["windows-hard-floor"]
    if free_gpu < limits["gpu_stop_free_mib"]:
        return "stop", ["gpu-hard-floor"]
    if available < limits["windows_admit_gib"]:
        return "drain", ["windows-admission-floor"]
    if free_gpu < limits["gpu_admit_free_mib"]:
        return "drain", ["gpu-admission-floor"]
    return "admit", []


def _read(path):
    # DrvFS replacement can briefly hide the destination from another reader.
    # Reopen only ENOENT, with at most 40 ms of waiting. Never reuse cached
    # permission: the returned receipt still passes identity, age and floors.
    for attempt in range(5):
        try:
            doc = json.loads(Path(path).read_text())
            if not isinstance(doc, Mapping):
                raise ValueError("not an object")
        except FileNotFoundError as error:
            if attempt == 4:
                raise ResourceAdmissionError(
                    "resource receipt unavailable after bounded reopen"
                ) from error
            time.sleep(0.01)
            continue
        except (OSError, ValueError, UnicodeError) as error:
            raise ResourceAdmissionError(
                "resource receipt unavailable or malformed"
            ) from error
        if attempt:
            logging.getLogger(__name__).warning(
                "Resource receipt replacement gap resolved after %d reopen(s): %s",
                attempt, path,
            )
        return doc


def publish_sample(
    session_dir, session, limits, *, now=time.time, host_reader=None, gpu_reader=None,
    elapsed_clock=_boottime, boot_id_reader=_boot_id,
):
    """Write one sample atomically; any pressure is latched for this process."""
    boot_id = boot_id_reader()
    elapsed_start = elapsed_clock()
    started = now()
    host, gpu = (host_reader or _host)(), (gpu_reader or _gpu)()
    finished = now()
    elapsed_end = elapsed_clock()
    decision, reasons = _decision(host, gpu, limits)
    if (not _number(elapsed_start) or not _number(elapsed_end)
            or not 0 <= elapsed_end - elapsed_start <= limits["max_sample_age_seconds"]):
        decision, reasons = "stop", ["observation-too-old"]
    observed = decision
    root = Path(session_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / SNAPSHOT_NAME
    identity, policy_hash = _identity(session), _policy_hash(limits)
    if path.exists():
        old = _read(path)
        if old.get("session") == identity and old.get("policy_sha256") == policy_hash:
            if old.get("decision") not in {"admit", "drain", "stop"}:
                raise ResourceAdmissionError("invalid prior resource decision")
            if old["decision"] == "stop" or (
                old["decision"] == "drain" and decision == "admit"
            ):
                decision = old["decision"]
                reasons = list(old["reasons"])

    def clean(measurement):
        if not isinstance(measurement, Mapping):
            return None
        return {
            key: (
                None if isinstance(value, float) and not math.isfinite(value) else value
            )
            for key, value in measurement.items()
        }

    doc = {
        "schema": SCHEMA,
        "session": identity,
        "policy_sha256": policy_hash,
        "sampled_at": started,
        "completed_at": finished,
        "elapsed_clock": {
            "kind": "linux-boottime", "boot_id": boot_id,
            "sampled_at": elapsed_start, "completed_at": elapsed_end,
        },
        "host_memory": clean(host),
        "gpu": clean(gpu),
        "observed_decision": observed,
        "decision": decision,
        "reasons": reasons,
    }
    # Retain the sample before publishing permission. One service owner writes it.
    encoded = json.dumps(doc, sort_keys=True, allow_nan=False) + "\n"
    with (root / LOG_NAME).open("a") as handle:
        handle.write(encoded)
    fd, name = tempfile.mkstemp(prefix=".resource-", dir=root)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(encoded)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return doc


def assert_admission(
    session_dir, session, limits, *, now=time.time,
    elapsed_clock=_boottime, boot_id_reader=_boot_id,
):
    doc = _read(Path(session_dir) / SNAPSHOT_NAME)
    age = float("inf")
    if doc.get("schema") == SCHEMA:
        clock = doc.get("elapsed_clock")
        current = elapsed_clock()
        if (isinstance(clock, Mapping) and clock.get("kind") == "linux-boottime"
                and clock.get("boot_id") == boot_id_reader()
                and _number(current) and _number(clock.get("sampled_at"))
                and _number(clock.get("completed_at"))
                and clock["sampled_at"] <= clock["completed_at"] <= current):
            age = current - clock["sampled_at"]
    elif doc.get("schema") == LEGACY_SCHEMA:
        # Read old pinned receipts without rewriting or upgrading their bytes.
        sampled = doc.get("sampled_at")
        age = now() - sampled if _number(sampled) else float("inf")
    if (
        doc.get("schema") not in {SCHEMA, LEGACY_SCHEMA}
        or doc.get("session") != _identity(session)
        or doc.get("policy_sha256") != _policy_hash(limits)
        or not 0 <= age <= limits["max_sample_age_seconds"]
    ):
        raise ResourceAdmissionError(
            "resource receipt is stale or has the wrong service identity"
        )
    # Recompute from observations too; a forged admit label cannot hide low memory.
    actual, _ = _decision(doc.get("host_memory"), doc.get("gpu"), limits)
    if doc.get("decision") != "admit" or actual != "admit":
        raise ResourceAdmissionError(
            "resource admission is latched closed: "
            + ",".join(doc.get("reasons") or [actual])
        )


class ResourceCheckedTransport:
    """Keep rendering and request bytes unchanged; gate only actual dispatch."""

    def __init__(
        self, transport, session_dir, session, limits, *, now=time.time,
        elapsed_clock=_boottime, boot_id_reader=_boot_id,
    ):
        self.transport, self.session_dir = transport, session_dir
        self.session, self.limits, self.now = session, limits, now
        self.elapsed_clock, self.boot_id_reader = elapsed_clock, boot_id_reader

    def __call__(self, request_bytes):
        assert_admission(
            self.session_dir, self.session, self.limits, now=self.now,
            elapsed_clock=self.elapsed_clock, boot_id_reader=self.boot_id_reader,
        )
        return self.transport(request_bytes)

    def __getattr__(self, name):
        return getattr(self.transport, name)


def wrap_transport(transport, values, data_root, session):
    limits = resource_limits(values)
    if limits is None:
        return transport
    from .serving import serving_session_dir

    return ResourceCheckedTransport(
        transport, serving_session_dir(data_root, session.session_id), session, limits
    )
