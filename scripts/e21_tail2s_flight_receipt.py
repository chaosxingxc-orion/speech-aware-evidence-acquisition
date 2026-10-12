"""Assemble the committed flight receipt for one Earnings-21 silence-tail cell.

Reads only the run's own sealed artifacts plus the attached session's monitor.
No model, GPU, tool, network or audio contact.

usage: flight_receipt.py <attempt_dir> <run_id> <t0> <t1> <falsifier.json> <out.json>
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.core.session.serving import (  # noqa: E402
    summarize_monitor_file,
)

DATA_ROOT = Path(os.environ.get(
    "SPEECHRL_DATA_DIR",
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
))
SESSION_ID = "e21-np6-c36864-20260907b"
SESSION_DIR = DATA_ROOT / "serving" / SESSION_ID


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main() -> int:
    attempt_dir = Path(sys.argv[1])
    run_id = sys.argv[2]
    t0, t1 = float(sys.argv[3]), float(sys.argv[4])
    falsifier = json.loads(Path(sys.argv[5]).read_text(encoding="utf-8"))
    out = Path(sys.argv[6])

    manifest_path = attempt_dir / f"{run_id}.run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    plan_path = attempt_dir / f"{run_id}.plan.json"
    outputs_path = attempt_dir / f"{run_id}.outputs.jsonl"
    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    scores_path = attempt_dir / f"{run_id}.scores.json"

    cost = manifest["cost"]
    monitor = summarize_monitor_file(
        SESSION_DIR / "monitor.jsonl", from_epoch=t0, to_epoch=t1
    )

    # per-window prompt/completion token distribution out of the trace's COST records
    prompt_tokens: list[int] = []
    completion_tokens: list[int] = []
    per_call_windows: dict[str, int] = {}
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        payload = record.get("payload") or {}
        if record.get("channel") == "COST":
            if payload.get("prompt_tokens") is not None:
                prompt_tokens.append(int(payload["prompt_tokens"]))
            if payload.get("completion_tokens") is not None:
                completion_tokens.append(int(payload["completion_tokens"]))
        if record.get("channel") == "MODEL_REQUEST" and not payload.get("stitch"):
            inner = payload.get("payload")
            if isinstance(inner, dict):
                sample_id = str(inner["sample_id"])
                per_call_windows[sample_id] = per_call_windows.get(sample_id, 0) + 1

    prompt_tokens.sort()

    def quantile(values, fraction):
        if not values:
            return None
        return values[min(len(values) - 1, int(fraction * (len(values) - 1)))]

    wall = t1 - t0
    receipt = {
        "schema": "saea-e21-tail2s-flight-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": run_id,
        "attempt_id": manifest["attempt"]["attempt_id"] if isinstance(
            manifest.get("attempt"), dict) else manifest.get("attempt"),
        "status": manifest["status"],
        "study_commit": manifest["study_commit"],
        "study_repo_dirt": manifest["study_repo_dirt"],
        "decides_nothing": (
            "This receipt reports the flight. The paired contrast, the intervals and the "
            "section 4.3 verdict live in verdict/result-summary.json and in the verdict note."
        ),
        "config_hash": manifest["config"]["config_hash"]
        if isinstance(manifest.get("config"), dict) else None,
        "protocol_hash": manifest["protocol_hash"],
        "split": manifest["split"],
        "plan": json.loads(plan_path.read_text(encoding="utf-8")),
        "scorers": manifest.get("scorers"),
        "legality": manifest.get("legality"),
        "windows": {
            "calls": len(per_call_windows),
            "windows": sum(per_call_windows.values()),
            "per_call": dict(sorted(per_call_windows.items())),
        },
        "tokens": {
            "prompt_total": sum(prompt_tokens),
            "completion_total": sum(completion_tokens),
            "prompt_min": prompt_tokens[0] if prompt_tokens else None,
            "prompt_median": quantile(prompt_tokens, 0.5),
            "prompt_max": prompt_tokens[-1] if prompt_tokens else None,
            "slot_tokens": 6144,
            "worst_request_margin_factor": round(6144 / prompt_tokens[-1], 4)
            if prompt_tokens else None,
        },
        "cost": {
            "calls_used": cost["calls_used"],
            "audio_seconds_used": cost["audio_seconds_used"],
            "delivered_audio_seconds": falsifier["delivered_seconds_total"],
            "gpu_seconds": cost["gpu_seconds"],
            "gpu_hours": round(cost["gpu_seconds"] / 3600.0, 4),
            "cpu_seconds": cost.get("cpu_seconds"),
            "latency_seconds_total": cost.get("latency_seconds_total"),
            "peak_vram_mib": cost.get("peak_vram_mib"),
            "gate_setup_seconds": cost.get("gate_setup_seconds"),
            "prompt_tokens_total": cost.get("prompt_tokens_total"),
            "completion_tokens_total": cost.get("completion_tokens_total"),
            "registered_calls": 1750,
            "registered_speech_audio_seconds": 150000,
            "registered_gpu_hours": 1.2,
            "comparator_gpu_hours": 0.9734,
            "kc_e1_gpu_hours": 0.9948,
            "ku_e1c_gpu_hours": 1.0087,
        },
        "throughput": {
            "run_wall_seconds": round(wall, 1),
            "run_wall_minutes": round(wall / 60.0, 2),
            "windows_per_minute": round(sum(per_call_windows.values()) / (wall / 60.0), 3),
            "realized_realtime_factor": round(
                cost["audio_seconds_used"] / cost["gpu_seconds"], 2),
            "realtime_factor_convention": (
                "metered cut audio seconds divided by the manifest's own nvidia-smi "
                "busy-time seconds -- the convention the KC-E1 and KU-E1c receipts use"
            ),
            "wall_clock_realtime_factor": round(
                falsifier["delivered_seconds_total"] / wall, 2),
            "comparator_windows_per_minute": 16.38,
            "kc_e1_windows_per_minute": 16.244,
            "ku_e1c_windows_per_minute": 16.482,
        },
        "serving": {
            "mode": "attached-serving-session",
            "session_id": SESSION_ID,
            "flight_started_a_server": False,
            "flight_stopped_a_server": False,
            "geometry": {"server_c": 36864, "server_np": 6, "slots": 6, "slot_tokens": 6144},
            "session_receipt": {
                "path": str(SESSION_DIR / "session-receipt.json"),
                "sha256": sha256(SESSION_DIR / "session-receipt.json"),
            },
            "monitor_summary": monitor,
            "monitor_summary_basis": (
                "scripts/serving_monitor.py's own summarizer over the attempt's run wall "
                f"window {int(t0)}-{int(t1)}; core.driver.run_experiment_bundled writes no "
                "session-attach receipt (that is core.flight.FlightRuntime's artifact and "
                "this carrier's 90-second OBS tiling cannot go through it), so head and "
                "tail idle count as parked against this flight rather than being hidden."
            ),
        },
        "saturation": {
            "saturated_slice_count": falsifier["saturated_slice_count"],
            "saturated_windows": falsifier["saturated_windows"],
            "skipped_slice_count": falsifier["skipped_slice_count"],
            "comparator_saturated_slice_count": 0,
            "kc_e1_saturated_slice_count": 2,
            "ku_e1c_saturated_slice_count": 2,
            "max_tokens": 1024,
            "rule": (
                "reproduction.obs_loop: a slice whose completion reaches the decode cap is a "
                "TRUNCATED decode, not a transcript end, so it contributes the empty string "
                "to the stitched hypothesis and is counted instead of scored silently."
            ),
        },
        "media_falsifier": falsifier,
        "artifacts": {
            "manifest": str(manifest_path), "manifest_sha256": sha256(manifest_path),
            "outputs": str(outputs_path), "outputs_sha256": sha256(outputs_path),
            "trace": str(trace_path), "trace_sha256": sha256(trace_path),
            "plan": str(plan_path), "plan_sha256": sha256(plan_path),
            **({"scores": str(scores_path), "scores_sha256": sha256(scores_path)}
               if scores_path.is_file() else {}),
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"],
        "windows": receipt["windows"]["windows"],
        "calls": receipt["windows"]["calls"],
        "gpu_hours": receipt["cost"]["gpu_hours"],
        "windows_per_minute": receipt["throughput"]["windows_per_minute"],
        "saturated": receipt["saturation"]["saturated_slice_count"],
        "parked_fraction": monitor.get("parked_fraction"),
        "out": str(out),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
