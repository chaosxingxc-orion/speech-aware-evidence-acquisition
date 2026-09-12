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


def read_gpu(run=subprocess.run) -> dict[str, object] | None:
    """One nvidia-smi row, or None when the card cannot be read (a monitor
    that cannot see the GPU keeps sampling the server rather than dying)."""

    try:
        completed = run(
            [
                "nvidia-smi",
                f"--query-gpu={NVIDIA_SMI_QUERY}",
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
    if len(parts) != len(GPU_FIELDS):
        return None
    sample = dict(zip(GPU_FIELDS, parts))
    return {
        name: (sample[name] if name == "pstate" else _number(sample[name]))
        for name in GPU_FIELDS
    }
