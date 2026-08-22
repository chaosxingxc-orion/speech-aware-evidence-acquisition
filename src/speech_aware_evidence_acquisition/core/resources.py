"""Injectable GPU/CPU resource sampling seam (R0 repair T7, invariant I8).

``core.model.FrozenCoreAdapter.cost_summary()`` reported only calls / audio
seconds / latency / prompt+completion tokens -- the owner entry contract also
requires accounting for GPU/CPU, processed speech seconds and evidence
volume. This module supplies the GPU/VRAM half of that gap as an injectable
``ResourceSampler`` seam so ``core.driver.run_experiment`` (the run-level
orchestrator, not the per-request adapter) can measure it without any test
ever shelling out to a real ``nvidia-smi``:

- :class:`NvidiaSmiSampler` polls
  ``nvidia-smi --id=<device_index> --query-gpu=utilization.gpu,memory.used
  --format=csv,noheader,nounits`` on a background thread at a fixed interval,
  accumulating a utilization-weighted GPU-seconds figure
  (``elapsed * utilization_pct / 100`` per interval) and the peak reported
  VRAM (MiB). Its subprocess runner is injectable
  (``runner: Callable[[str, float], str]``) so ``tests/unit/
  test_resources.py`` never spawns a real process.

  **Disclosed, bounded approximations (not defects):**

  1. *Undercounts by at most one interval.* The background loop records each
     completed ``[last poll, this poll]`` span; the final partial span between
     the LAST recorded poll and :meth:`~NvidiaSmiSampler.stop` being called is
     never recorded. ``gpu_seconds`` is therefore always <= the true
     utilization-weighted total, by at most ``interval_seconds`` (default
     1.0s). Chosen deliberately over polling once more inside ``stop()``: this
     is a coarse instrumentation figure measured in GPU-*hours*, not a
     precise billing meter (no numeric GPU-hours ceiling is enforced since
     the 2026-08-06 owner amendment, ``SAEA-OWNER-AMENDMENT-2026-08-06-
     BUDGET-CAPS``, retired the first-slice caps the consolidated execution
     contract used to state here), and a bounded ~1-second-per-attempt
     undercount is negligible regardless -- simplicity and one fewer failure
     mode inside shutdown won the tradeoff.
  2. *Device-wide, not process-scoped, single device.* ``utilization.gpu``/
  ``memory.used`` are ``nvidia-smi``'s DEVICE totals (every process on that
     GPU), not this run's share alone -- there is no per-process attribution
     here. ``device_index`` (default ``0``) pins WHICH device is queried
     (``--id=<device_index>``), removing the earlier ambiguity of "whichever
     line nvidia-smi prints first" on a multi-GPU host; it does not change the
     device-wide-total nature of the reading. Correct and sufficient for this
     study's documented single-GPU dev box (``CLAUDE.md``: one RTX 5090); a
     shared or multi-tenant GPU host would need real per-process attribution
     this module does not attempt.
  3. *Optional exact server-slot binding.* Speech-native profiles pass the
     receipt-bound llama-server ``/slots`` URL. Each request-window GPU sample
     is then paired with the number of rows whose strict boolean
     ``is_processing`` field is true, plus both timestamps and their skew.
     Slot-probe failure is recorded independently and never disables the GPU
     sampler; the profile admission gate decides whether coverage is adequate.
- :class:`NullSampler` records the literal ``NOT_AVAILABLE`` plus a reason
  string and touches nothing. It is both the explicit "no sampling" choice
  and what :class:`NvidiaSmiSampler` itself degrades to, on the FIRST
  failure (missing binary, non-zero exit, malformed output, an exception
  inside the polling thread) -- ``start()``/``stop()``/``summary()`` never
  raise out of this module, so a broken or absent ``nvidia-smi`` can never
  crash a run.
- :func:`resolve_resource_sampler` is the factory a REAL run uses (called
  only from ``core.driver._cli_run``, the live-run CLI entry point): a real
  :class:`NvidiaSmiSampler` if the binary is discoverable on ``PATH``, else a
  :class:`NullSampler` recording why. Every other caller -- library code,
  every test -- gets ``core.driver.run_experiment``'s own default (a
  :class:`NullSampler`) unless it explicitly passes a sampler, so no test
  ever silently starts polling a real GPU.
- :func:`cpu_seconds_snapshot` returns this process's cumulative CPU time
  (user + system, process + children) via ``os.times()`` -- a snapshot, not a
  delta; callers take one at the start and one at the end of the window they
  want to measure and subtract.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import statistics
import subprocess
import threading
import time
import urllib.request
from typing import Callable, Mapping, Protocol

NOT_AVAILABLE = "NOT_AVAILABLE"
WSL_NVIDIA_SMI = "/usr/lib/wsl/lib/nvidia-smi"


class ResourceSampler(Protocol):
    """The injectable seam ``core.driver.run_experiment`` depends on."""

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def begin_request_window(self) -> None: ...

    def end_request_window(self) -> None: ...

    def summary(self) -> Mapping[str, object]: ...


class NullSampler:
    """Records ``NOT_AVAILABLE`` plus a reason; never touches ``nvidia-smi``."""

    def __init__(self, reason: str) -> None:
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("NullSampler reason must be a non-empty string")
        self._reason = reason

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def begin_request_window(self) -> None:
        return None

    def end_request_window(self) -> None:
        return None

    def summary(self) -> dict[str, object]:
        return {
            "gpu_seconds": NOT_AVAILABLE,
            "peak_vram_mib": NOT_AVAILABLE,
            "gpu_sampling_reason": self._reason,
            "request_gpu_utilization_median_pct": NOT_AVAILABLE,
            "request_gpu_utilization_p10_pct": NOT_AVAILABLE,
            "request_gpu_sample_count": 0,
            "request_gpu_samples": [],
            "server_slot_sampling_configured": False,
            "server_slot_sampling_reason": NOT_AVAILABLE,
            "server_slot_probe_failure_count": 0,
            "server_slot_sample_count": 0,
        }


def _default_runner(device_index: int) -> Callable[[str, float], str]:
    """Bind ``device_index`` into a runner matching the injectable
    ``Callable[[str, float], str]`` shape :class:`NvidiaSmiSampler` calls
    ``self._runner(self._binary, self._timeout_seconds)`` against -- pinning
    the device does not change that shape, so an injected TEST runner (which
    never sees ``device_index`` at all) is completely unaffected."""

    def runner(binary: str, timeout_seconds: float) -> str:
        completed = subprocess.run(
            [
                binary,
                f"--id={device_index}",
                "--query-gpu=utilization.gpu,memory.used",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return completed.stdout

    return runner


def _default_slot_runner(url: str, timeout_seconds: float) -> str:
    """Read llama-server's local slot state without adding a dependency."""

    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8")


class NvidiaSmiSampler:
    """Background-thread ``nvidia-smi`` poller.

    Reads ``device_index``'s (default ``0``) ``utilization.gpu`` /
    ``memory.used`` on a fixed interval -- a DEVICE-wide total, not
    process-scoped (see the module docstring's disclosed-approximations
    list). Any failure -- at construction time (never raises), on the very
    first synchronous poll inside :meth:`start`, or later inside the
    background thread -- degrades this instance to reporting the same
    ``NOT_AVAILABLE`` + reason shape :class:`NullSampler` reports, and stops
    polling; it never raises out of :meth:`start`/:meth:`stop`/:meth:`summary`.
    """

    def __init__(
        self,
        *,
        interval_seconds: float = 1.0,
        binary: str = "nvidia-smi",
        device_index: int = 0,
        runner: Callable[[str, float], str] | None = None,
        timeout_seconds: float = 5.0,
        slots_url: str | None = None,
        slot_runner: Callable[[str, float], str] | None = None,
    ) -> None:
        if not isinstance(interval_seconds, (int, float)) or interval_seconds <= 0:
            raise ValueError("interval_seconds must be a positive number")
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive number")
        if isinstance(device_index, bool) or not isinstance(device_index, int) or device_index < 0:
            raise ValueError(f"device_index must be a non-negative integer, got {device_index!r}")
        if slots_url is not None and (
            not isinstance(slots_url, str) or not slots_url.strip()
        ):
            raise ValueError("slots_url must be a non-empty string when configured")
        if slots_url is None and slot_runner is not None:
            raise ValueError("slot_runner requires slots_url")
        self._interval_seconds = float(interval_seconds)
        self._binary = binary
        self._device_index = device_index
        self._runner = runner or _default_runner(device_index)
        self._timeout_seconds = float(timeout_seconds)
        self._slots_url = slots_url
        self._slot_runner = (
            slot_runner or _default_slot_runner if slots_url is not None else None
        )
        self._lock = threading.Lock()
        self._gpu_seconds = 0.0
        self._peak_vram_mib = 0.0
        self._samples_taken = 0
        self._request_window_active = False
        self._request_utilization_samples: list[float] = []
        self._request_gpu_samples: list[dict[str, object]] = []
        self._server_slot_sampling_reason: str | None = None
        self._server_slot_probe_failure_count = 0
        self._available = True
        self._reason: str | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _poll_once(self) -> tuple[bool, float, float]:
        try:
            raw = self._runner(self._binary, self._timeout_seconds)
            line = next(candidate for candidate in raw.strip().splitlines() if candidate.strip())
            util_str, mem_str = (part.strip() for part in line.split(","))
            utilization = float(util_str)
            memory_used = float(mem_str)
        except Exception as error:  # noqa: BLE001 -- any failure disables sampling, never crashes the run
            with self._lock:
                self._available = False
                self._reason = (
                    f"nvidia-smi sampling failed and was disabled for the rest of this "
                    f"run: {error}"
                )
            return False, 0.0, 0.0
        return True, utilization, memory_used

    def _poll_server_slots_once(self) -> dict[str, int | float] | None:
        """Return one strict llama-server ``/slots`` snapshot.

        Slot sampling is an independent diagnostic. A malformed or unavailable
        endpoint is recorded but never disables the GPU sampler itself.
        """

        if self._slots_url is None or self._slot_runner is None:
            return None
        try:
            raw = self._slot_runner(self._slots_url, self._timeout_seconds)
            rows = json.loads(raw)
            if not isinstance(rows, list) or not rows:
                raise ValueError("/slots response must be a non-empty list")
            slot_ids: set[int] = set()
            busy_slots = 0
            for row in rows:
                if not isinstance(row, Mapping):
                    raise ValueError("/slots row must be an object")
                slot_id = row.get("id")
                is_processing = row.get("is_processing")
                if (
                    isinstance(slot_id, bool)
                    or not isinstance(slot_id, int)
                    or slot_id < 0
                    or slot_id in slot_ids
                ):
                    raise ValueError("/slots row has an invalid or duplicate id")
                if not isinstance(is_processing, bool):
                    raise ValueError("/slots row lacks boolean is_processing")
                slot_ids.add(slot_id)
                busy_slots += int(is_processing)
            return {
                "server_slot_sampled_at_unix_seconds": time.time(),
                "server_busy_slots": busy_slots,
                "server_total_slots": len(rows),
            }
        except Exception as error:  # noqa: BLE001 -- diagnostic failure stays isolated
            with self._lock:
                self._server_slot_probe_failure_count += 1
                if self._server_slot_sampling_reason is None:
                    self._server_slot_sampling_reason = (
                        f"llama-server slot sampling failed: {error}"
                    )
            return None

    def _record(
        self,
        utilization: float,
        memory_used: float,
        elapsed: float,
        *,
        sampled_at_unix_seconds: float | None = None,
        server_slot_snapshot: Mapping[str, int | float] | None = None,
    ) -> None:
        sampled_at = (
            time.time()
            if sampled_at_unix_seconds is None
            else float(sampled_at_unix_seconds)
        )
        with self._lock:
            bounded_utilization = max(0.0, min(utilization, 100.0))
            self._gpu_seconds += elapsed * bounded_utilization / 100.0
            self._peak_vram_mib = max(self._peak_vram_mib, memory_used)
            self._samples_taken += 1
            if self._request_window_active:
                self._request_utilization_samples.append(bounded_utilization)
                sample: dict[str, object] = {
                    "sampled_at_unix_seconds": sampled_at,
                    "utilization_pct": bounded_utilization,
                    "memory_used_mib": memory_used,
                }
                if server_slot_snapshot is not None:
                    slot_sampled_at = float(
                        server_slot_snapshot["server_slot_sampled_at_unix_seconds"]
                    )
                    sample.update(server_slot_snapshot)
                    sample["server_slot_gpu_skew_milliseconds"] = (
                        abs(slot_sampled_at - sampled_at) * 1000.0
                    )
                self._request_gpu_samples.append(sample)

    def begin_request_window(self) -> None:
        """Start collecting utilization distribution samples for requests only."""

        with self._lock:
            self._request_window_active = True

    def end_request_window(self) -> None:
        """Stop request-only utilization sampling without stopping run sampling."""

        with self._lock:
            self._request_window_active = False

    def _run_loop(self) -> None:
        last = time.monotonic()
        while not self._stop_event.wait(self._interval_seconds):
            ok, utilization, memory_used = self._poll_once()
            now = time.monotonic()
            elapsed = now - last
            last = now
            if not ok:
                return
            sampled_at = time.time()
            with self._lock:
                request_window_active = self._request_window_active
            server_slot_snapshot = (
                self._poll_server_slots_once() if request_window_active else None
            )
            self._record(
                utilization,
                memory_used,
                elapsed,
                sampled_at_unix_seconds=sampled_at,
                server_slot_snapshot=server_slot_snapshot,
            )

    def start(self) -> None:
        if self._thread is not None:
            return  # already started -- idempotent
        # Synchronous first poll: a missing/broken nvidia-smi is detected
        # immediately, at zero elapsed-time cost (no interval to wait out),
        # and start() itself still never raises. This first sample
        # contributes 0 gpu_seconds by design (there is no prior instant for
        # it to span) but does establish peak_vram_mib immediately.
        ok, utilization, memory_used = self._poll_once()
        if not ok:
            return
        self._record(utilization, memory_used, 0.0)
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_seconds * 2 + self._timeout_seconds)

    def summary(self) -> dict[str, object]:
        with self._lock:
            if not self._available or self._samples_taken == 0:
                reason = self._reason or "nvidia-smi produced no samples before this run ended"
                return {
                    "gpu_seconds": NOT_AVAILABLE,
                    "peak_vram_mib": NOT_AVAILABLE,
                    "gpu_sampling_reason": reason,
                    "request_gpu_utilization_median_pct": NOT_AVAILABLE,
                    "request_gpu_utilization_p10_pct": NOT_AVAILABLE,
                    "request_gpu_sample_count": 0,
                    "request_gpu_samples": [],
                    "server_slot_sampling_configured": self._slots_url is not None,
                    "server_slot_sampling_reason": self._server_slot_sampling_reason,
                    "server_slot_probe_failure_count": self._server_slot_probe_failure_count,
                    "server_slot_sample_count": 0,
                }
            request_samples = sorted(self._request_utilization_samples)
            request_sample_count = len(request_samples)
            if request_samples:
                request_median: float | str = float(statistics.median(request_samples))
                nearest_rank_index = max(0, math.ceil(0.10 * request_sample_count) - 1)
                request_p10: float | str = float(request_samples[nearest_rank_index])
            else:
                request_median = NOT_AVAILABLE
                request_p10 = NOT_AVAILABLE
            server_slot_sample_count = sum(
                "server_busy_slots" in sample for sample in self._request_gpu_samples
            )
            return {
                "gpu_seconds": self._gpu_seconds,
                "peak_vram_mib": self._peak_vram_mib,
                "gpu_sampling_reason": None,
                "request_gpu_utilization_median_pct": request_median,
                "request_gpu_utilization_p10_pct": request_p10,
                "request_gpu_sample_count": request_sample_count,
                "request_gpu_samples": [dict(sample) for sample in self._request_gpu_samples],
                "server_slot_sampling_configured": self._slots_url is not None,
                "server_slot_sampling_reason": self._server_slot_sampling_reason,
                "server_slot_probe_failure_count": self._server_slot_probe_failure_count,
                "server_slot_sample_count": server_slot_sample_count,
            }


def resolve_resource_sampler(
    *,
    binary: str = "nvidia-smi",
    interval_seconds: float = 1.0,
    device_index: int = 0,
    slots_url: str | None = None,
) -> ResourceSampler:
    """The seam a REAL live run uses: a real
    :class:`NvidiaSmiSampler` if ``binary`` resolves on ``PATH``, else a
    :class:`NullSampler` recording why (I8 deviation discipline -- never
    silently omit the field). Every other caller of ``core.driver.
    run_experiment`` -- including every test -- gets that function's own
    default (a :class:`NullSampler`) unless it explicitly passes a sampler;
    this factory is never invoked implicitly, so no test can be surprised
    into shelling out to a real GPU tool.

    ``device_index`` defaults to ``0`` (the study's documented single-GPU dev
    box); pass a different index only if a future host genuinely has more
    than one device and this run should be attributed to a specific one.
    ``slots_url`` enables the independent exact-slot timeline used by the
    speech-native engineering gate; generic runs leave it unset."""

    resolved_binary = shutil.which(binary)
    if (
        resolved_binary is None
        and binary == "nvidia-smi"
        and os.path.isfile(WSL_NVIDIA_SMI)
        and os.access(WSL_NVIDIA_SMI, os.X_OK)
    ):
        # WSL exposes the host GPU bridge here, but fail-closed experiment
        # launchers may intentionally supply a minimal PATH that omits it.
        resolved_binary = WSL_NVIDIA_SMI
    if resolved_binary is None:
        return NullSampler(f"{binary!r} not found on PATH; GPU/VRAM sampling unavailable")
    return NvidiaSmiSampler(
        binary=resolved_binary,
        interval_seconds=interval_seconds,
        device_index=device_index,
        slots_url=slots_url,
    )


def cpu_seconds_snapshot() -> float:
    """Process + children cumulative CPU time (user + system) via
    ``os.times()`` (I8). A snapshot, not a delta -- callers take one at the
    start and one at the end of the window they want to measure and
    subtract. Standard-library, cross-platform (Windows included; children
    figures read 0.0 there since it has no fork-based process accounting,
    which is a platform fact, not a sampling failure)."""

    times = os.times()
    return times.user + times.system + times.children_user + times.children_system
