"""Shared read-only GPU telemetry for serving and preparation."""

import subprocess

GPU_FIELDS = (
    "utilization_percent",
    "memory_used_mib",
    "power_watts",
    "pstate",
    "clocks_sm_mhz",
)
NVIDIA_SMI_QUERY = "utilization.gpu,memory.used,power.draw,pstate,clocks.sm"


def _number(text: object) -> float | None:
    try:
        return float(str(text))
    except (TypeError, ValueError):
        return None


def read_gpu(run=subprocess.run, *, include_capacity=False) -> dict[str, object] | None:
    """One nvidia-smi row, or None when the card cannot be read (a monitor
    that cannot see the GPU keeps sampling the server rather than dying)."""

    fields = GPU_FIELDS + (("memory_total_mib", "memory_free_mib") if include_capacity else ())
    query = NVIDIA_SMI_QUERY + (",memory.total,memory.free" if include_capacity else "")
    try:
        completed = run(
            [
                "nvidia-smi",
                f"--query-gpu={query}",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    rows = (completed.stdout or "").strip().splitlines()
    if getattr(completed, "returncode", 1) != 0 or not rows:
        return None
    parts = [part.strip() for part in rows[0].split(",")]
    if len(parts) != len(fields):
        return None
    sample = dict(zip(fields, parts))
    return {
        name: (sample[name] if name == "pstate" else _number(sample[name]))
        for name in fields
    }
